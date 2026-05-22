"""Transfère les emails non-bounce vers la boîte de réception classique."""
import os
import logging
from datetime import datetime
from typing import Optional


class EmailForwarder:
    """Dépose l'email brut via IMAP APPEND. Fallback fichier .eml en cas d'échec."""

    @staticmethod
    def forward(raw_email_bytes: bytes,
                imap_host: Optional[str] = None,
                imap_port: Optional[int] = None,
                imap_user: Optional[str] = None,
                imap_password: Optional[str] = None,
                imap_folder: Optional[str] = None,
                failure_dir: Optional[str] = None) -> bool:
        """Retourne True si le forwarding a réussi, False sinon.

        Ne lève jamais d'exception (le pipeline doit continuer).
        Si le IMAP échoue, sauvegarde l'email dans failure_dir.
        """
        # Lazy import de config pour permettre l'injection dans les tests
        if imap_host is None:
            import config
            imap_host = config.FORWARD_IMAP_HOST
            imap_port = config.FORWARD_IMAP_PORT
            imap_user = config.FORWARD_IMAP_USER
            imap_password = config.FORWARD_IMAP_PASSWORD
            imap_folder = config.FORWARD_IMAP_FOLDER
            failure_dir = config.FORWARDING_FAILURES_DIR

        try:
            from imapclient import IMAPClient
            with IMAPClient(imap_host, port=imap_port, ssl=True) as client:
                client.login(imap_user, imap_password)
                client.append(imap_folder, raw_email_bytes)
            logging.info("EmailForwarder: IMAP APPEND OK → %s/%s",
                         imap_user, imap_folder)
            return True
        except Exception as e:
            logging.error("EmailForwarder: échec IMAP — %s", e, exc_info=True)
            EmailForwarder._save_failure(raw_email_bytes, failure_dir)
            return False

    @staticmethod
    def _save_failure(raw_email_bytes: bytes, failure_dir: str) -> None:
        try:
            os.makedirs(failure_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%dT%H%M%S_%f")
            path = os.path.join(failure_dir, f"{ts}.eml")
            with open(path, "wb") as f:
                f.write(raw_email_bytes)
            logging.warning("EmailForwarder: sauvegarde de secours → %s", path)
        except Exception as e:
            logging.error("EmailForwarder: impossible de sauver le fichier de secours — %s", e)
