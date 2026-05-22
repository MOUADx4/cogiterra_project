"""Extraction des champs DSN depuis un email brut RFC 2822."""
import re
import email
from email import policy
from email.message import Message
from email.utils import parsedate_to_datetime, getaddresses
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


EMAIL_REGEX = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
STATUS_CODE_REGEX = re.compile(r"\b([45]\d{2})\b")
DSN_STATUS_REGEX = re.compile(r"\b([245]\.\d{1,3}\.\d{1,3})\b")


@dataclass
class ParsedBounce:
    failed_recipient: Optional[str]
    subject: str
    from_: str
    received_date: datetime
    status_code: Optional[str]
    dsn_status: Optional[str]
    dsn_action: Optional[str]
    diagnostic_text: Optional[str]
    body_text: str
    forwarded_to: Optional[str]
    reporting_mta: Optional[str]
    raw_headers: dict = field(default_factory=dict)


class EmailParser:
    """Parse un email RFC 2822 (objet email.message.Message) en ParsedBounce."""

    @staticmethod
    def parse_bytes(raw_bytes: bytes) -> Message:
        """Convertit des bytes RFC 2822 en objet email.message.Message."""
        return email.message_from_bytes(raw_bytes, policy=policy.default)

    @classmethod
    def parse(cls, msg: Message) -> ParsedBounce:
        subject = cls._safe_header(msg, "Subject")
        from_ = cls._safe_header(msg, "From")
        date_header = cls._safe_header(msg, "Date")
        received_date = cls._parse_date(date_header)

        # X-Failed-Recipients (Exchange / O365)
        failed_recipient = cls._safe_header(msg, "X-Failed-Recipients") or None

        delivery_status = cls._find_part(msg, "message/delivery-status")
        diagnostic_text = None
        dsn_status = None
        dsn_action = None
        reporting_mta = None
        status_code = None

        if delivery_status is not None:
            ds_text = cls._delivery_status_to_text(delivery_status)
            # Final-Recipient ou Original-Recipient
            for header_name in ("Final-Recipient", "Original-Recipient"):
                m = re.search(rf"^{header_name}:\s*(?:rfc822;)?\s*([^\s]+)",
                              ds_text, re.IGNORECASE | re.MULTILINE)
                if m and not failed_recipient:
                    failed_recipient = m.group(1).strip().rstrip(">").lstrip("<")
                    break
            m = re.search(r"^Status:\s*([245]\.\d+\.\d+)", ds_text,
                          re.IGNORECASE | re.MULTILINE)
            if m:
                dsn_status = m.group(1)
            m = re.search(r"^Action:\s*(\w+)", ds_text,
                          re.IGNORECASE | re.MULTILINE)
            if m:
                dsn_action = m.group(1).lower()
            m = re.search(r"^Diagnostic-Code:\s*(.+)", ds_text,
                          re.IGNORECASE | re.MULTILINE)
            if m:
                diagnostic_text = m.group(1).strip()
            m = re.search(r"^Reporting-MTA:\s*(?:dns;)?\s*(.+)", ds_text,
                          re.IGNORECASE | re.MULTILINE)
            if m:
                reporting_mta = m.group(1).strip()

        # Corps texte principal
        body_text = cls._extract_body_text(msg)

        # Fallback failed_recipient :
        # - si le From est une vraie personne (pas un mailer-daemon),
        #   c'est elle qui rebondit → failed = From (cas auto-reply / address-change)
        # - sinon, on cherche dans le corps une adresse plausible
        if not failed_recipient:
            from_addr = cls._extract_email_from_field(from_)
            if from_addr and not cls._is_daemon_address(from_addr):
                failed_recipient = from_addr
            else:
                failed_recipient = cls._guess_failed_recipient(body_text, subject)

        # Code SMTP : depuis diagnostic ou corps
        haystack = " ".join(filter(None, [diagnostic_text, body_text, subject]))
        m = STATUS_CODE_REGEX.search(haystack)
        if m:
            status_code = m.group(1)
        if not dsn_status:
            m = DSN_STATUS_REGEX.search(haystack)
            if m:
                dsn_status = m.group(1)

        # Adresse de redirection si address-change explicite
        forwarded_to = cls._guess_forwarded_address(body_text, failed_recipient)

        return ParsedBounce(
            failed_recipient=failed_recipient,
            subject=subject or "",
            from_=from_ or "",
            received_date=received_date,
            status_code=status_code,
            dsn_status=dsn_status,
            dsn_action=dsn_action,
            diagnostic_text=diagnostic_text,
            body_text=body_text[:4000],  # limite raisonnable de stockage
            forwarded_to=forwarded_to,
            reporting_mta=reporting_mta,
            raw_headers={k: v for k, v in msg.items()},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_header(msg: Message, name: str) -> str:
        value = msg.get(name)
        if value is None:
            return ""
        try:
            return str(value).strip()
        except Exception:
            return ""

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        if not date_str:
            return datetime.now(timezone.utc)
        try:
            d = parsedate_to_datetime(date_str)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d
        except Exception:
            return datetime.now(timezone.utc)

    @staticmethod
    def _find_part(msg: Message, content_type: str) -> Optional[Message]:
        for part in msg.walk():
            if part.get_content_type().lower() == content_type.lower():
                return part
        return None

    @classmethod
    def _delivery_status_to_text(cls, part: Message) -> str:
        """
        Sérialise un bloc message/delivery-status.
        Le parser email Python expose chaque sous-bloc DSN comme un Message
        dont les champs (Status, Action, Final-Recipient...) sont des headers.
        On les ré-émet en texte ligne par ligne.
        """
        chunks = []
        if part.is_multipart():
            for sub in part.get_payload():
                if isinstance(sub, Message):
                    for k, v in sub.items():
                        chunks.append(f"{k}: {v}")
                    chunks.append("")
            return "\n".join(chunks)
        return cls._payload_to_text(part)

    @staticmethod
    def _payload_to_text(part: Message) -> str:
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                # Multipart : concaténer les sous-parties
                if part.is_multipart():
                    chunks = []
                    for sub in part.get_payload():
                        if isinstance(sub, Message):
                            chunks.append(EmailParser._payload_to_text(sub))
                    return "\n".join(chunks)
                return str(part.get_payload() or "")
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
        except Exception:
            return ""

    @classmethod
    def _extract_body_text(cls, msg: Message) -> str:
        """Récupère le texte brut principal, ignore les attachments."""
        if msg.is_multipart():
            # On préfère text/plain, sinon text/html nettoyé
            plain = None
            html = None
            for part in msg.walk():
                ctype = part.get_content_type().lower()
                disp = (part.get("Content-Disposition") or "").lower()
                if "attachment" in disp:
                    continue
                if ctype == "text/plain" and plain is None:
                    plain = cls._payload_to_text(part)
                elif ctype == "text/html" and html is None:
                    html = cls._payload_to_text(part)
            if plain:
                return plain
            if html:
                # Nettoyage HTML basique
                return re.sub(r"<[^>]+>", " ", html)
            return ""
        return cls._payload_to_text(msg)

    @staticmethod
    def _extract_email_from_field(field_value: str) -> Optional[str]:
        if not field_value:
            return None
        m = EMAIL_REGEX.search(field_value)
        return m.group(0) if m else None

    @staticmethod
    def _is_daemon_address(addr: str) -> bool:
        low = addr.lower()
        return any(x in low for x in ("postmaster", "mailer-daemon",
                                      "noreply", "no-reply"))

    @staticmethod
    def _guess_failed_recipient(body: str, subject: str) -> Optional[str]:
        for src in (body, subject):
            if not src:
                continue
            matches = EMAIL_REGEX.findall(src)
            for addr in matches:
                # Filtrer les adresses techniques évidentes
                low = addr.lower()
                if any(x in low for x in ("postmaster", "mailer-daemon",
                                          "noreply", "no-reply")):
                    continue
                return addr
        return None

    @staticmethod
    def _guess_forwarded_address(body: str, failed: Optional[str]) -> Optional[str]:
        if not body:
            return None
        # Patterns d'indication explicite d'une nouvelle adresse
        context_patterns = [
            r"new (?:email|address)[^\n]{0,40}?({email})",
            r"nouvelle adresse[^\n]{0,40}?({email})",
            r"forwarded to[^\n]{0,40}?({email})",
            r"please update[^\n]{0,40}?({email})",
            r"moved to[^\n]{0,40}?({email})",
            r"désormais joignable[^\n]{0,40}?({email})",
            r"contact me at[^\n]{0,40}?({email})",
            r"reach me at[^\n]{0,40}?({email})",
            r"my new email is\s*({email})",
        ]
        email_pat = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
        for pat in context_patterns:
            pat = pat.replace("{email}", f"({email_pat})")
            # Le regex peut contenir 2 groupes captures (un imbriqué) → on prend le dernier
            m = re.search(pat, body, re.IGNORECASE)
            if m:
                candidate = m.groups()[-1]
                if failed and candidate.lower() == failed.lower():
                    continue
                return candidate
        return None
