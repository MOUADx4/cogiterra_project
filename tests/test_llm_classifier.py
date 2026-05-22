"""Tests du classifier LLM en isolation (sans appel API réel)."""
from datetime import datetime
from unittest.mock import patch

from classifier.llm_classifier import LLMClassifier
from classifier.rules_engine import BounceCategory
from parser import ParsedBounce


def _parsed():
    return ParsedBounce(
        failed_recipient="x@y.com",
        subject="Undeliverable", from_="md@server", received_date=datetime.now(),
        status_code="550", dsn_status="5.1.1", dsn_action="failed",
        diagnostic_text="User unknown", body_text="N/A",
        forwarded_to=None, reporting_mta=None, raw_headers={},
    )


def test_llm_parses_clean_json():
    raw = '{"category":"hard_bounce","confidence":0.92,"new_email":null,"reason":"adresse inconnue"}'
    with patch.object(LLMClassifier, "_call_anthropic", return_value=raw):
        r = LLMClassifier.classify(_parsed())
    assert r.category == BounceCategory.HARD_BOUNCE
    assert r.confidence == 0.92
    assert r.method == "llm"


def test_llm_parses_json_in_markdown_block():
    raw = '```json\n{"category":"soft_bounce","confidence":0.85,"new_email":null,"reason":"quota"}\n```'
    with patch.object(LLMClassifier, "_call_anthropic", return_value=raw):
        r = LLMClassifier.classify(_parsed())
    assert r.category == BounceCategory.SOFT_BOUNCE


def test_llm_security_threshold_forces_hard():
    # Confiance < 0.70 sur autre catégorie → forcé hard_bounce
    raw = '{"category":"soft_bounce","confidence":0.5,"new_email":null,"reason":"x"}'
    with patch.object(LLMClassifier, "_call_anthropic", return_value=raw):
        r = LLMClassifier.classify(_parsed())
    assert r.category == BounceCategory.HARD_BOUNCE


def test_llm_api_error_fallback():
    with patch.object(LLMClassifier, "_call_anthropic",
                      side_effect=RuntimeError("api down")):
        r = LLMClassifier.classify(_parsed())
    assert r.category == BounceCategory.HARD_BOUNCE
    assert r.method == "llm_error"
    assert r.confidence == 0.0


def test_llm_invalid_json_fallback():
    with patch.object(LLMClassifier, "_call_anthropic",
                      return_value="not even json"):
        r = LLMClassifier.classify(_parsed())
    assert r.method == "llm_error"
