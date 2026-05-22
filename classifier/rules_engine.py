"""Moteur de règles déterministes — Niveau 1 de classification."""
import json
import os
import re
import logging
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple


USER_RULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "user_rules.json",
)


class BounceCategory(str, Enum):
    HARD_BOUNCE    = "hard_bounce"
    SOFT_BOUNCE    = "soft_bounce"
    ADDRESS_CHANGE = "address_change"
    TECHNICAL      = "technical_error"
    UNKNOWN        = "unknown"


@dataclass
class ClassificationResult:
    category: BounceCategory
    confidence: float
    new_email: Optional[str]
    reason: str
    method: str                         # "rules" | "llm" | "llm_error"
    failed_recipient: Optional[str]
    received_date: datetime


# ---------- Patterns ----------
HARD_PATTERNS = [
    re.compile(r"user unknown", re.IGNORECASE),
    re.compile(r"no such user", re.IGNORECASE),
    re.compile(r"mailbox not found", re.IGNORECASE),
    re.compile(r"invalid (?:address|recipient)", re.IGNORECASE),
    re.compile(r"address (?:does not exist|rejected|not found)", re.IGNORECASE),
    re.compile(r"account (?:does not exist|has been disabled|is disabled)", re.IGNORECASE),
    re.compile(r"recipient (?:not found|address rejected)", re.IGNORECASE),
    re.compile(r"unknown user", re.IGNORECASE),
    re.compile(r"\bNXDOMAIN\b"),
    re.compile(r"does not exist", re.IGNORECASE),
]

SOFT_PATTERNS = [
    re.compile(r"mailbox full", re.IGNORECASE),
    re.compile(r"over quota", re.IGNORECASE),
    re.compile(r"quota exceeded", re.IGNORECASE),
    re.compile(r"storage limit", re.IGNORECASE),
    re.compile(r"temporarily unavailable", re.IGNORECASE),
    re.compile(r"try again later", re.IGNORECASE),
    re.compile(r"greylisted", re.IGNORECASE),
    re.compile(r"deferred", re.IGNORECASE),
]

ADDRESS_CHANGE_CONTEXT = [
    re.compile(r"new (?:email|address)", re.IGNORECASE),
    re.compile(r"nouvelle adresse", re.IGNORECASE),
    re.compile(r"forwarded to", re.IGNORECASE),
    re.compile(r"please update", re.IGNORECASE),
    re.compile(r"moved to", re.IGNORECASE),
    re.compile(r"désormais joignable", re.IGNORECASE),
    re.compile(r"contact me at", re.IGNORECASE),
    re.compile(r"my new email is", re.IGNORECASE),
]

TECHNICAL_PATTERNS = [
    re.compile(r"\bDKIM\b", re.IGNORECASE),
    re.compile(r"\bSPF\b", re.IGNORECASE),
    re.compile(r"\bDMARC\b", re.IGNORECASE),
    re.compile(r"signature.*fail", re.IGNORECASE),
    re.compile(r"authentication.*fail", re.IGNORECASE),
]


def _load_user_rules() -> List[Tuple[re.Pattern, str, float, str]]:
    """Charge les règles regex apprises depuis user_rules.json.

    Format attendu :
        [{"pattern": "...", "category": "hard_bounce",
          "confidence": 0.92, "reason": "Apprise de LLM le ..."}]
    Retourne [(compiled_regex, category, confidence, reason), ...]
    """
    if not os.path.isfile(USER_RULES_PATH):
        return []
    try:
        with open(USER_RULES_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logging.warning("user_rules.json illisible : %s", e)
        return []
    rules = []
    for entry in raw if isinstance(raw, list) else []:
        try:
            pat = re.compile(entry["pattern"], re.IGNORECASE)
            rules.append((
                pat,
                entry.get("category", "hard_bounce"),
                float(entry.get("confidence", 0.85)),
                entry.get("reason", "Règle apprise"),
            ))
        except (re.error, KeyError, TypeError, ValueError) as e:
            logging.warning("Règle utilisateur invalide ignorée : %s — %s", entry, e)
    return rules


# Cache simple (rechargé à chaque appel de classify pour la démo live)
_USER_RULES_CACHE: Optional[List[Tuple[re.Pattern, str, float, str]]] = None


def reload_user_rules() -> int:
    """Recharge le cache des règles utilisateur. Retourne le nombre chargé."""
    global _USER_RULES_CACHE
    _USER_RULES_CACHE = _load_user_rules()
    return len(_USER_RULES_CACHE)


def _get_user_rules() -> List[Tuple[re.Pattern, str, float, str]]:
    global _USER_RULES_CACHE
    if _USER_RULES_CACHE is None:
        _USER_RULES_CACHE = _load_user_rules()
    return _USER_RULES_CACHE


class RulesEngine:
    """Applique les règles déterministes au ParsedBounce."""

    @staticmethod
    def classify(parsed) -> ClassificationResult:
        diagnostic = (parsed.diagnostic_text or "")
        body = (parsed.body_text or "")
        subject = (parsed.subject or "")
        haystack = " ".join([diagnostic, body, subject])
        dsn = parsed.dsn_status or ""
        code = parsed.status_code or ""

        # 0. RÈGLES UTILISATEUR (apprises via LLM, prioritaires)
        for pat, category_str, confidence, reason in _get_user_rules():
            if pat.search(haystack):
                try:
                    category = BounceCategory(category_str)
                except ValueError:
                    category = BounceCategory.HARD_BOUNCE
                return RulesEngine._mk(
                    category, confidence, None,
                    f"Règle apprise: {reason}",
                    parsed,
                )

        # 1. ADDRESS CHANGE — adresse alternative détectée + contexte explicite
        if parsed.forwarded_to and any(p.search(body) for p in ADDRESS_CHANGE_CONTEXT):
            return RulesEngine._mk(
                BounceCategory.ADDRESS_CHANGE, 0.85,
                parsed.forwarded_to,
                f"Redirection détectée vers {parsed.forwarded_to}",
                parsed,
            )

        # 2. HARD BOUNCE — code 5xx + statut DSN 5.1.x / 5.7.1
        if (code.startswith("5") or dsn.startswith("5.")) and (
            dsn.startswith("5.1.") or dsn == "5.7.1"
        ):
            return RulesEngine._mk(
                BounceCategory.HARD_BOUNCE, 0.95, None,
                f"Code SMTP {code or 'n/a'} / DSN {dsn or 'n/a'}",
                parsed,
            )

        # 3. HARD BOUNCE — pattern explicite d'adresse invalide
        for pat in HARD_PATTERNS:
            if pat.search(haystack):
                return RulesEngine._mk(
                    BounceCategory.HARD_BOUNCE, 0.95, None,
                    f"Pattern hard match: {pat.pattern}",
                    parsed,
                )

        # 4. SOFT BOUNCE — statut DSN 4.x.x
        if dsn.startswith(("4.2.2", "4.3.1", "4.3.2", "4.4.1")) or dsn.startswith("4."):
            return RulesEngine._mk(
                BounceCategory.SOFT_BOUNCE, 0.90, None,
                f"DSN {dsn} = erreur temporaire",
                parsed,
            )

        # 5. SOFT BOUNCE — code 4xx
        if code.startswith("4"):
            return RulesEngine._mk(
                BounceCategory.SOFT_BOUNCE, 0.90, None,
                f"Code SMTP {code} = erreur temporaire",
                parsed,
            )

        # 6. SOFT BOUNCE — patterns explicites
        for pat in SOFT_PATTERNS:
            if pat.search(haystack):
                return RulesEngine._mk(
                    BounceCategory.SOFT_BOUNCE, 0.90, None,
                    f"Pattern soft match: {pat.pattern}",
                    parsed,
                )

        # 7. TECHNICAL — DKIM/SPF/DMARC : confiance faible, déléguer au LLM
        for pat in TECHNICAL_PATTERNS:
            if pat.search(haystack):
                return RulesEngine._mk(
                    BounceCategory.TECHNICAL, 0.50, None,
                    f"Erreur technique détectée: {pat.pattern}",
                    parsed,
                )

        # 8. HARD BOUNCE fallback si code 5xx générique sans pattern précis
        if code.startswith("5") or dsn.startswith("5."):
            return RulesEngine._mk(
                BounceCategory.HARD_BOUNCE, 0.75, None,
                f"Code 5xx générique ({code or dsn})",
                parsed,
            )

        # 9. UNKNOWN — délégation au LLM
        logging.debug("RulesEngine: aucun critère atteint, délégation LLM")
        return RulesEngine._mk(
            BounceCategory.UNKNOWN, 0.0, None,
            "Aucun critère déterministe atteint",
            parsed,
        )

    @staticmethod
    def _mk(category: BounceCategory, confidence: float,
            new_email: Optional[str], reason: str, parsed) -> ClassificationResult:
        return ClassificationResult(
            category=category,
            confidence=confidence,
            new_email=new_email,
            reason=reason,
            method="rules",
            failed_recipient=parsed.failed_recipient,
            received_date=parsed.received_date,
        )
