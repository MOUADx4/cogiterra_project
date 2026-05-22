"""Classification LLM — Niveau 2 (cas ambigus)."""
import json
import re
import logging
from typing import Optional

from .rules_engine import BounceCategory, ClassificationResult


SYSTEM_PROMPT = """\
Tu es un système expert en analyse d'emails de retour en erreur (bounces) pour une liste de diffusion.

Analyse le bounce fourni et classifie-le dans exactement l'une de ces 4 catégories :

1. "hard_bounce" — Adresse définitivement invalide : utilisateur inexistant, domaine inexistant, adresse supprimée. Ne plus jamais envoyer à cette adresse.

2. "soft_bounce" — Erreur temporaire : boîte pleine, quota dépassé, serveur momentanément indisponible. L'adresse est valide.

3. "address_change" — Le destinataire a changé d'adresse. Un message indique explicitement ou implicitement (redirection permanente) une nouvelle adresse.

4. "technical_error" — Échec technique pur : DKIM/SPF/DMARC, erreur de signature lors d'une redirection de domaine. L'adresse peut être valide.

BONUS - Self-improving : si tu identifies une expression OU un mot-clé caractéristique qui permettrait de classer un bounce du même type sans appeler l'IA la prochaine fois, propose-le dans "suggested_pattern" (regex Python valide, casse insensible, court et générique, ex: "no longer with our company"). Si rien d'évident, laisse null.

Réponds UNIQUEMENT avec ce JSON, sans texte avant ni après :
{
  "category": "<hard_bounce|soft_bounce|address_change|technical_error>",
  "confidence": <0.0 à 1.0>,
  "new_email": "<adresse si address_change, sinon null>",
  "reason": "<explication courte en français, max 120 caractères>",
  "suggested_pattern": "<regex pour matcher ce type de bounce, ou null>"
}

Règle de sécurité : si confiance < 0.70, utilise "hard_bounce" par défaut.
"""


def _build_user_prompt(parsed) -> str:
    return (
        f"Adresse en échec : {parsed.failed_recipient or 'inconnue'}\n"
        f"Sujet : {parsed.subject}\n"
        f"Code SMTP : {parsed.status_code or 'n/a'}\n"
        f"Statut DSN : {parsed.dsn_status or 'n/a'}\n"
        f"Diagnostic : {parsed.diagnostic_text or 'n/a'}\n"
        f"Corps (extrait) : {(parsed.body_text or '')[:800]}"
    )


class LLMClassifier:
    """Wrapper LLM avec fallback hard_bounce en cas d'erreur."""

    @staticmethod
    def classify(parsed) -> ClassificationResult:
        import config
        user_prompt = _build_user_prompt(parsed)
        try:
            if config.LLM_PROVIDER == "anthropic":
                raw = LLMClassifier._call_anthropic(user_prompt)
            elif config.LLM_PROVIDER == "openai":
                raw = LLMClassifier._call_openai(user_prompt)
            else:
                raise ValueError(f"LLM_PROVIDER inconnu : {config.LLM_PROVIDER}")
            data = LLMClassifier._parse_json(raw)
            return LLMClassifier._to_result(data, parsed, method="llm")
        except Exception as e:
            logging.error("LLMClassifier: erreur — %s", e, exc_info=True)
            return ClassificationResult(
                category=BounceCategory.HARD_BOUNCE,
                confidence=0.0,
                new_email=None,
                reason=f"Erreur LLM : {type(e).__name__}",
                method="llm_error",
                failed_recipient=parsed.failed_recipient,
                received_date=parsed.received_date,
            )

    # ------------------------------------------------------------------
    # Appels API
    # ------------------------------------------------------------------
    @staticmethod
    def _call_anthropic(user_prompt: str) -> str:
        import config
        from anthropic import Anthropic
        client = Anthropic(api_key=config.LLM_API_KEY)
        resp = client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=config.LLM_MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        # Concatène les blocs texte
        parts = []
        for block in resp.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "".join(parts)

    @staticmethod
    def _call_openai(user_prompt: str) -> str:
        import config
        from openai import OpenAI
        client = OpenAI(api_key=config.LLM_API_KEY)
        resp = client.chat.completions.create(
            model=config.LLM_MODEL,
            max_tokens=config.LLM_MAX_TOKENS,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content or ""

    # ------------------------------------------------------------------
    # Parsing de la réponse
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        # Si encadré de ```json ... ```
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        # Capter le premier objet JSON balanced
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            raise ValueError(f"Pas de JSON dans la réponse LLM : {text!r}")
        return json.loads(m.group(0))

    @staticmethod
    def _to_result(data: dict, parsed, method: str) -> ClassificationResult:
        cat_raw = (data.get("category") or "hard_bounce").lower()
        try:
            category = BounceCategory(cat_raw)
        except ValueError:
            category = BounceCategory.HARD_BOUNCE
        confidence = float(data.get("confidence") or 0.0)
        # Règle de sécurité du prompt
        if confidence < 0.70 and category != BounceCategory.HARD_BOUNCE:
            category = BounceCategory.HARD_BOUNCE
        new_email: Optional[str] = data.get("new_email") or None
        if isinstance(new_email, str):
            new_email = new_email.strip() or None
        reason = (data.get("reason") or "")[:200]

        # Self-improving : stocker la suggestion de pattern si présente
        suggested = data.get("suggested_pattern")
        if suggested and isinstance(suggested, str) and suggested.strip():
            LLMClassifier._save_suggestion(
                pattern=suggested.strip(),
                category=category.value,
                confidence=max(confidence - 0.05, 0.70),
                parsed=parsed,
                reason=reason,
            )

        return ClassificationResult(
            category=category,
            confidence=confidence,
            new_email=new_email,
            reason=reason,
            method=method,
            failed_recipient=parsed.failed_recipient,
            received_date=parsed.received_date,
        )

    @staticmethod
    def _save_suggestion(*, pattern: str, category: str, confidence: float,
                         parsed, reason: str) -> None:
        """Persiste une suggestion de pattern dans la table rule_suggestions."""
        try:
            # Validation regex avant insertion
            re.compile(pattern)
        except re.error as e:
            logging.warning("Pattern LLM invalide ignoré : %r — %s", pattern, e)
            return
        try:
            import config
            from storage import Database
            db = Database(config.DB_PATH)
            try:
                added = db.add_rule_suggestion(
                    pattern=pattern, category=category, confidence=confidence,
                    sample_email=parsed.failed_recipient or "n/a",
                    sample_text=(parsed.diagnostic_text or parsed.body_text or "")[:400],
                    llm_reason=reason,
                )
                if added:
                    logging.info("Nouvelle suggestion de règle enregistrée: %r → %s",
                                 pattern, category)
            finally:
                db.close()
        except Exception as e:
            logging.warning("Sauvegarde suggestion échouée : %s", e)
