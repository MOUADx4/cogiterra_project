from tests.conftest import load_fixture
from parser import EmailParser


def _parse(name: str):
    msg = EmailParser.parse_bytes(load_fixture(name))
    return EmailParser.parse(msg)


def test_parse_hard_exchange():
    p = _parse("hard_exchange_511.eml")
    assert p.failed_recipient == "john.doe@oldcompany.com"
    assert p.dsn_status == "5.1.1"
    assert p.status_code == "550"
    assert p.dsn_action == "failed"
    assert "User unknown" in (p.diagnostic_text or "")


def test_parse_soft_quota():
    p = _parse("soft_quota_422.eml")
    assert p.dsn_status == "4.2.2"
    assert p.dsn_action == "delayed"
    assert p.status_code in ("452", "422")


def test_parse_address_change():
    p = _parse("address_change_explicit.eml")
    assert p.forwarded_to == "jane.doe@newcorp.io"


def test_parse_dkim():
    p = _parse("dkim_redirect.eml")
    assert p.dsn_status == "5.7.0"
    assert p.failed_recipient == "contact@newdomain.io"


def test_parse_ndr_freetext():
    p = _parse("ndr_freetext.eml")
    # Le parser doit extraire l'adresse du corps
    assert p.failed_recipient == "obscure_recipient@strangedomain.zz"
