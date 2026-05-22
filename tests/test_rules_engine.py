from tests.conftest import load_fixture
from parser import EmailParser
from classifier import RulesEngine, BounceCategory


def _classify(name: str):
    msg = EmailParser.parse_bytes(load_fixture(name))
    parsed = EmailParser.parse(msg)
    return RulesEngine.classify(parsed)


def test_rules_hard_exchange():
    r = _classify("hard_exchange_511.eml")
    assert r.category == BounceCategory.HARD_BOUNCE
    assert r.confidence >= 0.95
    assert r.method == "rules"


def test_rules_soft_quota():
    r = _classify("soft_quota_422.eml")
    assert r.category == BounceCategory.SOFT_BOUNCE
    assert r.confidence >= 0.90
    assert r.method == "rules"


def test_rules_address_change_explicit():
    r = _classify("address_change_explicit.eml")
    assert r.category == BounceCategory.ADDRESS_CHANGE
    assert r.new_email == "jane.doe@newcorp.io"
    assert r.confidence >= 0.85


def test_rules_dkim_delegates_to_llm():
    """DKIM/SPF → technical, confiance basse → délégation LLM."""
    r = _classify("dkim_redirect.eml")
    # Soit technical (sera délégué), soit hard_bounce 5.7.0 — accepte les deux
    assert r.category in (BounceCategory.TECHNICAL, BounceCategory.HARD_BOUNCE)


def test_rules_freetext_unknown():
    r = _classify("ndr_freetext.eml")
    # Aucun code, aucun pattern → unknown ou hard générique
    assert r.category in (BounceCategory.UNKNOWN, BounceCategory.HARD_BOUNCE)
