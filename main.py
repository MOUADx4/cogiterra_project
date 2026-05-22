"""Point d'entrée : --mode pipe (Postfix) ou --mode report (cron quotidien)."""
import sys
import os
import argparse
import logging
import time
import shutil
from datetime import datetime
from logging.handlers import RotatingFileHandler

import config


# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
def setup_logging() -> None:
    os.makedirs(os.path.dirname(os.path.abspath(config.LOG_PATH)), exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(module)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler = RotatingFileHandler(
        config.LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    # Console : forcer UTF-8 (sinon cp1252 sous Windows plante sur "→" / accents)
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    root.addHandler(stream)


# ----------------------------------------------------------------------
# Pipeline unitaire : détecte → forward OU classify+save.
# Réutilisé par --mode pipe et --mode poll.
# ----------------------------------------------------------------------
def process_email(raw_bytes: bytes, db, source: str):
    """Retourne :
       - True   : bounce traité avec succès (poll: \\Seen + déplacement)
       - "seen" : email de contact transféré (poll: \\Seen sans déplacement)
       - False  : échec — laisse UNSEEN pour retry (mode poll)
    En mode pipe, la valeur de retour est ignorée (exit 0 garanti côté Postfix).
    """
    from detector import BounceDetector
    from forwarder import EmailForwarder
    from parser import EmailParser
    from classifier import RulesEngine, LLMClassifier

    t0 = time.time()
    try:
        msg = EmailParser.parse_bytes(raw_bytes)
        from_ = (msg.get("From") or "").strip()

        if not BounceDetector.is_bounce(msg):
            ok = EmailForwarder.forward(raw_bytes)
            try:
                db.increment_forwarded()
            except Exception as e:
                logging.error("%s | compteur forwarded — %s", source, e)
            duration = time.time() - t0
            logging.info(
                "%s | from=%s | bounce=False | action=%s | duration=%.3fs",
                source, from_,
                "forwarded" if ok else "forward_failed", duration,
            )
            if source == "POLL":
                # Les emails de contact classique restent toujours UNSEEN
                # dans la boîte bounces@, même si le forwarding a réussi.
                # Conséquence : ils seront retransmis à chaque poll (doublons
                # acceptés dans contact@) tant qu'ils ne sont pas marqués
                # lus manuellement via le webmail.
                return False
            return True

        parsed = EmailParser.parse(msg)
        result = RulesEngine.classify(parsed)
        if result.confidence < config.LLM_CONFIDENCE_THRESHOLD:
            if not config.LLM_API_KEY:
                logging.info(
                    "%s | confiance rules=%.2f < %.2f mais LLM_API_KEY vide, "
                    "on garde le résultat rules",
                    source, result.confidence, config.LLM_CONFIDENCE_THRESHOLD,
                )
            else:
                logging.info(
                    "%s | confiance rules=%.2f < %.2f → délégation LLM",
                    source, result.confidence, config.LLM_CONFIDENCE_THRESHOLD,
                )
                result = LLMClassifier.classify(parsed)

        db.save_result(result, parsed)
        duration = time.time() - t0
        logging.info(
            "%s | from=%s | bounce=True | recipient=%s | category=%s | "
            "method=%s | confidence=%.2f | duration=%.3fs",
            source, from_, parsed.failed_recipient,
            result.category.value if hasattr(result.category, "value") else result.category,
            result.method, result.confidence, duration,
        )
        return True
    except Exception as e:
        logging.error("%s | erreur pipeline : %s", source, e, exc_info=True)
        # En pipe on retourne True pour exit 0. En poll on retourne False
        # pour laisser le message UNSEEN et retenter plus tard.
        return True if source == "PIPE" else False


# ----------------------------------------------------------------------
# Mode pipe : appelé par Postfix pour chaque email
# ----------------------------------------------------------------------
def mode_pipe() -> int:
    from storage import Database

    raw_bytes = sys.stdin.buffer.read()
    if not raw_bytes:
        logging.warning("PIPE | stdin vide, rien à traiter")
        return 0

    db = None
    try:
        db = Database(config.DB_PATH)
        process_email(raw_bytes, db, source="PIPE")
    except Exception as e:
        logging.error("PIPE | erreur fatale : %s", e, exc_info=True)
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass
    return 0  # Toujours 0 pour Postfix


# ----------------------------------------------------------------------
# Mode poll : lit les emails UNSEEN depuis IMAP et les passe au pipeline
# ----------------------------------------------------------------------
def mode_poll() -> int:
    from storage import Database
    from poller import ImapPoller

    t0 = time.time()
    db = Database(config.DB_PATH)
    try:
        poller = ImapPoller(config)
        ok, ko = poller.poll(lambda raw: process_email(raw, db, source="POLL"))
        duration = time.time() - t0
        logging.info(
            "POLL | terminé | ok=%d | ko=%d | duration=%.3fs",
            ok, ko, duration,
        )
    finally:
        db.close()
    return 0


# ----------------------------------------------------------------------
# Mode report : appelé par cron à 6h00
# ----------------------------------------------------------------------
def mode_report() -> int:
    from exporter import CsvExporter
    from reporter import EmailReporter
    from storage import Database
    from webhook import WebhookSender
    from alerts import AnomalyDetector

    date_str = datetime.now().strftime("%Y-%m-%d")
    db = Database(config.DB_PATH)
    try:
        _weekly_backup_if_needed()

        exporter = CsvExporter(
            db, config.OUTPUT_DIR, date_str,
            threshold=config.SOFT_BOUNCE_THRESHOLD,
        )
        csv_files = exporter.generate_all()
        stats = db.compute_daily_stats()

        # Mapping nominal pour la fonction webhook (l'ordre est garanti)
        csv_map = {
            "to_be_deleted":  csv_files[0],
            "to_be_paused":   csv_files[1],
            "to_be_modified": csv_files[2],
        }

        reporter = EmailReporter(config)
        sent_ok = reporter.send(csv_files, stats, date_str)

        # --- Bonus 1 : Webhook vers le CMS Cogiterra ---
        webhook = WebhookSender(config)
        if webhook.is_enabled():
            ok = webhook.push(csv_map, stats, date_str)
            logging.info("REPORT | webhook %s",
                         "OK" if ok else "ECHEC (CSV envoyés par mail malgré tout)")
        else:
            logging.debug("REPORT | webhook désactivé (WEBHOOK_URL vide)")

        # --- Bonus 2 : Détection d'anomalies + alerte Slack ---
        # IMPORTANT : on appelle AVANT save_stats pour que la baseline 7j
        # n'inclue pas le jour courant.
        detector = AnomalyDetector(config)
        if detector.is_enabled():
            try:
                detector.check_and_alert(db, stats, date_str)
            except Exception as e:
                logging.warning("ALERT | erreur détecteur : %s", e)

        db.save_stats(stats, date_str, report_sent_ok=sent_ok)

        if sent_ok:
            db.clear_results()
            logging.info(
                "REPORT | %s | total=%d | hard=%d soft=%d (>seuil=%d) "
                "changes=%d tech=%d unknown=%d | forwarded=%d | "
                "rules=%d llm=%d | envoi OK, table result vidée.",
                date_str, stats["total"], stats["n_hard"], stats["n_soft"],
                stats["n_soft_above_threshold"], stats["n_changes"],
                stats["n_technical"], stats["n_unknown"], stats["n_forwarded"],
                stats["n_rules"], stats["n_llm"],
            )
        else:
            logging.error(
                "REPORT | %s | échec d'envoi SMTP. Table result CONSERVÉE.",
                date_str,
            )
    finally:
        db.close()
    return 0


def _weekly_backup_if_needed() -> None:
    """Sauvegarde hebdomadaire de la base SQLite."""
    try:
        if not os.path.isfile(config.DB_PATH):
            return
        os.makedirs(config.BACKUPS_DIR, exist_ok=True)
        # Une sauvegarde par semaine ISO
        week_tag = datetime.now().strftime("%G-W%V")
        backup_path = os.path.join(config.BACKUPS_DIR, f"bounces_{week_tag}.db")
        if os.path.exists(backup_path):
            return
        shutil.copy2(config.DB_PATH, backup_path)
        logging.info("Backup SQLite hebdomadaire → %s", backup_path)
    except Exception as e:
        logging.warning("Backup SQLite échoué : %s", e)


# ----------------------------------------------------------------------
# Entrée CLI
# ----------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Bounce processor")
    parser.add_argument(
        "--mode", required=True, choices=("pipe", "poll", "report"),
        help="pipe = temps réel via Postfix (stdin), "
             "poll = lecture IMAP périodique (Gandi, OVH...), "
             "report = rapport quotidien (cron)",
    )
    args = parser.parse_args()
    setup_logging()
    if args.mode == "pipe":
        return mode_pipe()
    if args.mode == "poll":
        return mode_poll()
    return mode_report()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        # Garantie absolue : ne jamais cracher avec un code non-zéro en mode pipe
        try:
            logging.error("FATAL : %s", e, exc_info=True)
        except Exception:
            pass
        sys.exit(0)
