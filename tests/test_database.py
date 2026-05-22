"""Tests du module storage.database et du flow report."""
import os
import tempfile
from datetime import datetime
from unittest.mock import patch

from storage import Database
from classifier.rules_engine import BounceCategory, ClassificationResult
from parser import ParsedBounce


def _result(category, email, method="rules", confidence=0.95, new_email=None):
    return ClassificationResult(
        category=category,
        confidence=confidence,
        new_email=new_email,
        reason="test",
        method=method,
        failed_recipient=email,
        received_date=datetime.now(),
    )


def _parsed(email):
    return ParsedBounce(
        failed_recipient=email,
        subject="", from_="", received_date=datetime.now(),
        status_code=None, dsn_status=None, dsn_action=None,
        diagnostic_text=None, body_text="",
        forwarded_to=None, reporting_mta=None, raw_headers={},
    )


def _fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return Database(path), path


def test_save_and_aggregate():
    db, path = _fresh_db()
    try:
        db.save_result(_result(BounceCategory.HARD_BOUNCE, "a@x.com"), _parsed("a@x.com"))
        db.save_result(_result(BounceCategory.SOFT_BOUNCE, "b@x.com",
                               method="llm", confidence=0.8), _parsed("b@x.com"))
        db.save_result(_result(BounceCategory.ADDRESS_CHANGE, "c@x.com",
                               new_email="c@y.com"), _parsed("c@x.com"))
        stats = db.compute_daily_stats()
        assert stats["total"] == 3
        assert stats["n_hard"] == 1
        assert stats["n_soft"] == 1
        assert stats["n_changes"] == 1
        assert stats["n_rules"] == 2
        assert stats["n_llm"] == 1
    finally:
        db.close()
        os.unlink(path)


def test_soft_bounce_threshold_cross_day():
    db, path = _fresh_db()
    try:
        for _ in range(5):
            db.save_result(_result(BounceCategory.SOFT_BOUNCE, "repeat@x.com"),
                           _parsed("repeat@x.com"))
        rows = db.get_soft_bounces_above_threshold(5)
        assert len(rows) == 1
        assert rows[0]["email_address"] == "repeat@x.com"
        assert rows[0]["failures"] == 5
    finally:
        db.close()
        os.unlink(path)


def test_clear_results_only_when_report_ok():
    """clear_results doit être appelé seulement si l'envoi a réussi."""
    db, path = _fresh_db()
    try:
        db.save_result(_result(BounceCategory.HARD_BOUNCE, "a@x.com"),
                       _parsed("a@x.com"))
        assert db.compute_daily_stats()["total"] == 1
        db.save_stats(db.compute_daily_stats(), "2025-01-15",
                      report_sent_ok=False)
        # Pas de clear : les données sont conservées
        assert db.compute_daily_stats()["total"] == 1
        # Si envoi OK, clear_results
        db.save_stats(db.compute_daily_stats(), "2025-01-15",
                      report_sent_ok=True)
        db.clear_results()
        assert db.compute_daily_stats()["total"] == 0
    finally:
        db.close()
        os.unlink(path)


def test_soft_bounce_tracking_stats():
    """n_tracked / n_warning du compteur global."""
    db, path = _fresh_db()
    try:
        # 1 adresse à 1 échec (suivie, hors alerte)
        db.save_result(_result(BounceCategory.SOFT_BOUNCE, "low@x.com"),
                       _parsed("low@x.com"))
        # 1 adresse à 3 échecs (zone d'alerte si warning=3, threshold=5)
        for _ in range(3):
            db.save_result(_result(BounceCategory.SOFT_BOUNCE, "mid@x.com"),
                           _parsed("mid@x.com"))
        # 1 adresse à 5 échecs (atteint le seuil → n'est plus "tracked")
        for _ in range(5):
            db.save_result(_result(BounceCategory.SOFT_BOUNCE, "high@x.com"),
                           _parsed("high@x.com"))
        stats = db.get_soft_bounce_tracking_stats(threshold=5, warning=3)
        # 2 adresses < 5 (low, mid). high est exclu car ≥ seuil.
        assert stats["n_tracked"] == 2
        # 1 adresse dans [3, 5) — mid
        assert stats["n_warning"] == 1
    finally:
        db.close()
        os.unlink(path)


def test_increment_forwarded_counter():
    db, path = _fresh_db()
    try:
        for _ in range(3):
            db.increment_forwarded()
        assert db.get_counter("forwarded_today") == 3
        db.clear_results()
        assert db.get_counter("forwarded_today") == 0
    finally:
        db.close()
        os.unlink(path)
