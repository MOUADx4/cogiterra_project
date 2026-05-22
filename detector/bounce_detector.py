"""Distingue les bounces/NDR des emails de contact classiques."""
import re
import logging
from email.message import Message


class BounceDetector:
    """6 critères de détection. Un seul suffit pour classer l'email comme bounce."""

    BOUNCE_CONTENT_TYPES = ("multipart/report", "delivery-status")
    BOUNCE_HEADERS_PRESENT = ("X-Failed-Recipients", "X-Original-To")
    BOUNCE_AUTO_SUBMITTED = ("auto-replied", "auto-generated")

    BOUNCE_FROM_PATTERNS = [
        re.compile(r"mailer-daemon", re.IGNORECASE),
        re.compile(r"postmaster", re.IGNORECASE),
        re.compile(r"\bnoreply\b", re.IGNORECASE),
        re.compile(r"\bno-reply\b", re.IGNORECASE),
        re.compile(r"mail delivery", re.IGNORECASE),
    ]

    BOUNCE_SUBJECT_PATTERNS = [
        re.compile(r"undeliverable", re.IGNORECASE),
        re.compile(r"mail delivery failed", re.IGNORECASE),
        re.compile(r"delivery status notification", re.IGNORECASE),
        re.compile(r"non[- ]delivery report", re.IGNORECASE),
        re.compile(r"message non distribué", re.IGNORECASE),
        re.compile(r"échec de remise", re.IGNORECASE),
        re.compile(r"delivery failure", re.IGNORECASE),
        re.compile(r"returned mail", re.IGNORECASE),
        re.compile(r"\bNDR\b"),
        re.compile(r"\bbounce\b", re.IGNORECASE),
    ]

    # Patterns indiquant un changement d'adresse explicite dans le corps :
    # ces messages doivent passer par le pipeline de classification.
    ADDRESS_CHANGE_PATTERNS = [
        re.compile(r"my new (?:email|address)", re.IGNORECASE),
        re.compile(r"new email (?:is|address)", re.IGNORECASE),
        re.compile(r"nouvelle adresse", re.IGNORECASE),
        re.compile(r"désormais joignable", re.IGNORECASE),
        re.compile(r"please update (?:your )?(?:records|contacts|address)",
                   re.IGNORECASE),
        re.compile(r"moved to .+@", re.IGNORECASE),
    ]

    @classmethod
    def is_bounce(cls, msg: Message) -> bool:
        """Retourne True si l'email est un bounce ou NDR.

        Vérifie dans l'ordre :
          1. Content-Type multipart/report ou delivery-status
          2. Présence de X-Failed-Recipients ou X-Original-To
          3. From contient un pattern MAILER-DAEMON / postmaster / noreply
          4. Sujet correspond à un pattern de NDR
          5. Header Auto-Submitted = auto-replied / auto-generated
        """
        # 1. Content-Type
        ctype = (msg.get_content_type() or "").lower()
        for needle in cls.BOUNCE_CONTENT_TYPES:
            if needle in ctype:
                logging.debug("BounceDetector: match Content-Type=%s", ctype)
                return True
        # Vérification également sur les sous-parties
        if msg.is_multipart():
            for part in msg.walk():
                sub_ctype = (part.get_content_type() or "").lower()
                if "delivery-status" in sub_ctype or "report" in sub_ctype:
                    logging.debug("BounceDetector: sous-partie %s", sub_ctype)
                    return True

        # 2. Headers spécifiques
        for header in cls.BOUNCE_HEADERS_PRESENT:
            if msg.get(header):
                logging.debug("BounceDetector: header %s présent", header)
                return True

        # 3. From
        from_ = (msg.get("From") or "").lower()
        for pat in cls.BOUNCE_FROM_PATTERNS:
            if pat.search(from_):
                logging.debug("BounceDetector: From match %s", pat.pattern)
                return True

        # 4. Subject
        subject = msg.get("Subject") or ""
        for pat in cls.BOUNCE_SUBJECT_PATTERNS:
            if pat.search(subject):
                logging.debug("BounceDetector: Subject match %s", pat.pattern)
                return True

        # 5. Auto-Submitted = auto-generated (machine-only, jamais une vacance)
        auto = (msg.get("Auto-Submitted") or "").lower()
        if "auto-generated" in auto:
            logging.debug("BounceDetector: Auto-Submitted=%s", auto)
            return True

        # 6. Auto-reply ou message libre dont le corps annonce un changement
        #    d'adresse → on doit le traiter via le classifier address_change.
        body = cls._extract_text(msg)
        if "auto-replied" in auto or body:
            for pat in cls.ADDRESS_CHANGE_PATTERNS:
                if pat.search(body):
                    logging.debug("BounceDetector: body match %s", pat.pattern)
                    return True

        logging.debug("BounceDetector: aucun critère atteint → email de contact")
        return False

    @staticmethod
    def _extract_text(msg) -> str:
        """Récupère le corps texte pour les vérifications de patterns."""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type().lower() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            return payload.decode(charset, errors="replace")
                return ""
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
            return str(msg.get_payload() or "")
        except Exception:
            return ""
