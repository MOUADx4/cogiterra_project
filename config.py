"""Configuration centralisée du système de traitement des bounces."""
import os
from dotenv import load_dotenv

load_dotenv()


# --- Boîte mail de réception des bounces ---
# Utilisée comme valeur d'identification dans les logs.
BOUNCE_EMAIL = os.getenv("BOUNCE_EMAIL", "bounces@example.com")

# --- IMAP de la boîte bounces (utilisé uniquement en --mode poll) ---
# Permet de récupérer les emails via IMAP quand le pipeline Postfix n'est
# pas disponible (ex : hébergement chez Gandi, OVH, Office 365).
BOUNCE_IMAP_HOST = os.getenv("BOUNCE_IMAP_HOST", "mail.example.com")
BOUNCE_IMAP_PORT = int(os.getenv("BOUNCE_IMAP_PORT", 993))
BOUNCE_IMAP_USER = os.getenv("BOUNCE_IMAP_USER", BOUNCE_EMAIL)
BOUNCE_IMAP_PASSWORD = os.getenv("BOUNCE_IMAP_PASSWORD", "")
BOUNCE_IMAP_FOLDER = os.getenv("BOUNCE_IMAP_FOLDER", "INBOX")
# Dossier où déplacer les messages traités (chaîne vide = pas de déplacement,
# seulement marqués comme lus). Doit exister côté serveur IMAP.
BOUNCE_IMAP_PROCESSED_FOLDER = os.getenv("BOUNCE_IMAP_PROCESSED_FOLDER", "")
# Nombre maximum d'emails à traiter par exécution (0 = pas de limite).
POLL_BATCH_LIMIT = int(os.getenv("POLL_BATCH_LIMIT", 200))

# --- Boîte de réception classique (forwarding des emails non-bounce) ---
FORWARD_IMAP_HOST = os.getenv("FORWARD_IMAP_HOST", "mail.example.com")
FORWARD_IMAP_PORT = int(os.getenv("FORWARD_IMAP_PORT", 993))
FORWARD_IMAP_USER = os.getenv("FORWARD_IMAP_USER", "contact@example.com")
FORWARD_IMAP_PASSWORD = os.getenv("FORWARD_IMAP_PASSWORD", "")
FORWARD_IMAP_FOLDER = os.getenv("FORWARD_IMAP_FOLDER", "INBOX")

# --- LLM API ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")   # "anthropic" | "openai"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5")
LLM_MAX_TOKENS = 300
LLM_CONFIDENCE_THRESHOLD = 0.80

# --- Seuils de traitement ---
SOFT_BOUNCE_THRESHOLD = int(os.getenv("SOFT_BOUNCE_THRESHOLD", 5))
SOFT_BOUNCE_WINDOW_DAYS = int(os.getenv("SOFT_BOUNCE_WINDOW_DAYS", 30))
# Zone d'alerte : adresses au-dessus de ce niveau apparaissent dans le rapport
# comme "à risque" (par défaut : seuil - 2, plancher à 1).
SOFT_BOUNCE_WARNING = int(os.getenv(
    "SOFT_BOUNCE_WARNING", max(1, SOFT_BOUNCE_THRESHOLD - 2)
))

# --- Rapport quotidien ---
REPORT_RECIPIENT = os.getenv("REPORT_RECIPIENT", "bounces@example.com")
REPORT_SENDER = os.getenv("REPORT_SENDER", "bounces@example.com")
REPORT_SMTP_HOST = os.getenv("REPORT_SMTP_HOST", "smtp.example.com")
REPORT_SMTP_PORT = int(os.getenv("REPORT_SMTP_PORT", 587))
REPORT_SMTP_USER = os.getenv("REPORT_SMTP_USER", "")
REPORT_SMTP_PASSWORD = os.getenv("REPORT_SMTP_PASSWORD", "")
REPORT_SMTP_USE_TLS = True

# --- Webhook vers le CMS Cogiterra (optionnel) ---
# Si configuré, le rapport quotidien pousse aussi les 3 listes en JSON.
# Le CMS reçoit un POST avec body : {to_delete: [...], to_pause: [...], to_modify: [...]}
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_AUTH_TOKEN = os.getenv("WEBHOOK_AUTH_TOKEN", "")
WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", 15))

# --- Alertes Slack sur anomalies (optionnel) ---
# Pic de bounces > ALERT_SPIKE_MULTIPLIER × moyenne 7j → POST sur SLACK_WEBHOOK_URL
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
ALERT_SPIKE_MULTIPLIER = float(os.getenv("ALERT_SPIKE_MULTIPLIER", 2.0))
ALERT_MIN_BASELINE = int(os.getenv("ALERT_MIN_BASELINE", 10))

# --- Chemins ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "data", "bounces.db"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(BASE_DIR, "output"))
LOG_PATH = os.getenv("LOG_PATH", os.path.join(BASE_DIR, "logs", "bounce_processor.log"))
FORWARDING_FAILURES_DIR = os.path.join(OUTPUT_DIR, "forwarding_failures")
BACKUPS_DIR = os.path.join(BASE_DIR, "data", "backups")
