from tests.conftest import load_fixture
from parser import EmailParser
from detector import BounceDetector


def _msg(name: str):
    return EmailParser.parse_bytes(load_fixture(name))


def test_hard_exchange_is_bounce():
    assert BounceDetector.is_bounce(_msg("hard_exchange_511.eml")) is True


def test_soft_quota_is_bounce():
    assert BounceDetector.is_bounce(_msg("soft_quota_422.eml")) is True


def test_address_change_is_bounce():
    assert BounceDetector.is_bounce(_msg("address_change_explicit.eml")) is True


def test_dkim_redirect_is_bounce():
    assert BounceDetector.is_bounce(_msg("dkim_redirect.eml")) is True


def test_oof_vacation_not_bounce():
    assert BounceDetector.is_bounce(_msg("oof_vacation.eml")) is False


def test_contact_email_not_bounce():
    assert BounceDetector.is_bounce(_msg("contact_email.eml")) is False


def test_ndr_freetext_is_bounce():
    # From contient MAILER-DAEMON + Subject "Returned mail"
    assert BounceDetector.is_bounce(_msg("ndr_freetext.eml")) is True
