"""Lit les emails UNSEEN depuis la boîte IMAP bounces et les passe au pipeline."""
import logging
from typing import Callable, Tuple, Union


# Le handler retourne :
#   True              → succès, marquer \Seen ET déplacer vers Processed
#   "seen"            → succès, marquer \Seen mais NE PAS déplacer (ex: emails de contact)
#   False             → échec, laisser UNSEEN pour retry au prochain poll
HandlerResult = Union[bool, str]


class ImapPoller:
    """Récupère les nouveaux emails de la boîte bounces via IMAP.

    Pour chaque message UNSEEN :
      - télécharge le brut RFC 2822
      - appelle `handler(raw_bytes)` qui retourne True / "seen" / False
      - True   : marque \\Seen + déplace vers le dossier processed si configuré
      - "seen" : marque \\Seen seulement (le message reste en INBOX)
      - False  : laisse UNSEEN pour relance ultérieure

    Ne lève jamais : tous les échecs sont logués.
    """

    def __init__(self, config_module):
        self.cfg = config_module

    def poll(self, handler: Callable[[bytes], bool]) -> Tuple[int, int]:
        """Retourne (nb_traités_ok, nb_traités_ko)."""
        try:
            from imapclient import IMAPClient
        except ImportError:
            logging.error("ImapPoller: imapclient non installé — pip install imapclient")
            return 0, 0

        ok = 0
        ko = 0
        try:
            with IMAPClient(self.cfg.BOUNCE_IMAP_HOST,
                            port=self.cfg.BOUNCE_IMAP_PORT,
                            ssl=True) as client:
                client.login(self.cfg.BOUNCE_IMAP_USER,
                             self.cfg.BOUNCE_IMAP_PASSWORD)
                client.select_folder(self.cfg.BOUNCE_IMAP_FOLDER)

                # Vérifie/crée le dossier de destination une seule fois
                processed = self._ensure_processed_folder(client)

                uids = list(client.search(["UNSEEN"]))
                limit = self.cfg.POLL_BATCH_LIMIT
                if limit and len(uids) > limit:
                    logging.info("ImapPoller: %d messages UNSEEN, limité à %d",
                                 len(uids), limit)
                    uids = uids[:limit]
                else:
                    logging.info("ImapPoller: %d messages UNSEEN à traiter",
                                 len(uids))

                if not uids:
                    return 0, 0

                fetched = client.fetch(uids, [b"RFC822"])
                for uid in uids:
                    raw = fetched.get(uid, {}).get(b"RFC822")
                    if not raw:
                        logging.warning("ImapPoller: UID %s sans corps RFC822", uid)
                        ko += 1
                        continue
                    try:
                        outcome = handler(raw)
                    except Exception as e:
                        logging.error("ImapPoller: handler crash UID %s — %s",
                                      uid, e, exc_info=True)
                        outcome = False

                    # Normalisation : True/"seen" = succès, False = échec
                    if outcome is False:
                        ko += 1
                        continue
                    should_move = (outcome is True) and processed is not None

                    try:
                        client.add_flags(uid, [b"\\Seen"])
                    except Exception as e:
                        logging.warning("ImapPoller: add_flags UID %s — %s",
                                        uid, e)
                    if should_move:
                        self._move_or_copy(client, uid, processed)
                    ok += 1
        except Exception as e:
            logging.error("ImapPoller: erreur de connexion IMAP — %s",
                          e, exc_info=True)
        return ok, ko

    # ------------------------------------------------------------------
    def _ensure_processed_folder(self, client):
        """Retourne le nom du dossier processed s'il existe (ou est créable),
        sinon retourne None pour désactiver le déplacement."""
        processed = (self.cfg.BOUNCE_IMAP_PROCESSED_FOLDER or "").strip()
        if not processed:
            return None
        try:
            if client.folder_exists(processed):
                return processed
            client.create_folder(processed)
            logging.info("ImapPoller: dossier IMAP créé → %s", processed)
            return processed
        except Exception as e:
            logging.warning(
                "ImapPoller: dossier '%s' inaccessible et non créable (%s) — "
                "les messages seront seulement marqués \\Seen.",
                processed, e,
            )
            return None

    def _move_or_copy(self, client, uid, processed) -> None:
        """Déplace un UID vers `processed`. Ne lève pas en cas d'échec."""
        try:
            client.move(uid, processed)
            return
        except Exception as e:
            logging.debug("ImapPoller: MOVE %s échoué (%s), tentative COPY+DEL",
                          uid, e)
        try:
            client.copy(uid, processed)
            client.delete_messages(uid)
            client.expunge()
        except Exception as e:
            logging.warning("ImapPoller: COPY+DEL UID %s échoué — %s "
                            "(le message reste dans INBOX mais est \\Seen)",
                            uid, e)
