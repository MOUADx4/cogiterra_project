"""Simule 5 inserts soft_bounce pour la même adresse → to_be_paused."""
import os
import csv
import tempfile
from datetime import datetime

from storage import Database
from exporter import CsvExporter
from classifier.rules_engine import BounceCategory, ClassificationResult
from parser import ParsedBounce


def test_five_soft_bounces_produce_paused_row():
    out = tempfile.mkdtemp()
    fd, dbp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(dbp)
    try:
        for _ in range(5):
            r = ClassificationResult(
                category=BounceCategory.SOFT_BOUNCE,
                confidence=0.91, new_email=None, reason="quota",
                method="rules", failed_recipient="loyal@x.com",
                received_date=datetime.now(),
            )
            p = ParsedBounce(failed_recipient="loyal@x.com", subject="",
                             from_="", received_date=datetime.now(),
                             status_code="452", dsn_status="4.2.2",
                             dsn_action="delayed", diagnostic_text="full",
                             body_text="", forwarded_to=None,
                             reporting_mta=None, raw_headers={})
            db.save_result(r, p)

        ex = CsvExporter(db, out, "2025-01-15", threshold=5)
        paused_path = ex.generate_to_be_paused()
        rows = list(csv.DictReader(open(paused_path, encoding="utf-8")))
        assert len(rows) == 1
        assert rows[0]["email"] == "loyal@x.com"
        assert int(rows[0]["consecutive_failures"]) == 5
    finally:
        db.close()
        os.unlink(dbp)


def test_four_soft_bounces_do_not_trigger():
    out = tempfile.mkdtemp()
    fd, dbp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(dbp)
    try:
        for _ in range(4):
            r = ClassificationResult(
                category=BounceCategory.SOFT_BOUNCE, confidence=0.91,
                new_email=None, reason="x", method="rules",
                failed_recipient="patient@x.com",
                received_date=datetime.now(),
            )
            p = ParsedBounce(failed_recipient="patient@x.com", subject="",
                             from_="", received_date=datetime.now(),
                             status_code=None, dsn_status=None,
                             dsn_action=None, diagnostic_text=None,
                             body_text="", forwarded_to=None,
                             reporting_mta=None, raw_headers={})
            db.save_result(r, p)

        ex = CsvExporter(db, out, "2025-01-15", threshold=5)
        paused_path = ex.generate_to_be_paused()
        rows = list(csv.DictReader(open(paused_path, encoding="utf-8")))
        assert rows == []
    finally:
        db.close()
        os.unlink(dbp)
