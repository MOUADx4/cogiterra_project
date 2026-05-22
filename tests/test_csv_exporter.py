import os
import tempfile
import csv
from datetime import datetime

from storage import Database
from exporter import CsvExporter
from classifier.rules_engine import BounceCategory, ClassificationResult
from parser import ParsedBounce


def _r(category, email, **kw):
    return ClassificationResult(
        category=category, confidence=kw.get("confidence", 0.9),
        new_email=kw.get("new_email"), reason=kw.get("reason", ""),
        method=kw.get("method", "rules"),
        failed_recipient=email, received_date=datetime.now(),
    )


def _p(email):
    return ParsedBounce(failed_recipient=email, subject="", from_="",
                        received_date=datetime.now(), status_code=None,
                        dsn_status=None, dsn_action=None,
                        diagnostic_text=None, body_text="",
                        forwarded_to=None, reporting_mta=None, raw_headers={})


def test_three_csv_generated():
    out = tempfile.mkdtemp()
    fd, dbp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(dbp)
    try:
        db.save_result(_r(BounceCategory.HARD_BOUNCE, "h@x.com"), _p("h@x.com"))
        for _ in range(5):
            db.save_result(_r(BounceCategory.SOFT_BOUNCE, "s@x.com"), _p("s@x.com"))
        db.save_result(_r(BounceCategory.ADDRESS_CHANGE, "a@x.com",
                          new_email="a@y.com"), _p("a@x.com"))

        ex = CsvExporter(db, out, "2025-01-15", threshold=5)
        paths = ex.generate_all()
        assert len(paths) == 3
        # Présence
        for p in paths:
            assert os.path.isfile(p)
        # Contenu
        deleted = list(csv.DictReader(open(paths[0], encoding="utf-8")))
        paused = list(csv.DictReader(open(paths[1], encoding="utf-8")))
        modified = list(csv.DictReader(open(paths[2], encoding="utf-8")))
        assert len(deleted) == 1 and deleted[0]["email"] == "h@x.com"
        assert len(paused) == 1 and paused[0]["email"] == "s@x.com"
        assert int(paused[0]["consecutive_failures"]) == 5
        assert len(modified) == 1 and modified[0]["new_email"] == "a@y.com"
    finally:
        db.close()
        os.unlink(dbp)


def test_empty_csv_keeps_header():
    out = tempfile.mkdtemp()
    fd, dbp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(dbp)
    try:
        ex = CsvExporter(db, out, "2025-01-15", threshold=5)
        ex.generate_all()
        for fname in (
            "to_be_deleted_2025-01-15.csv",
            "to_be_paused_2025-01-15.csv",
            "to_be_modified_2025-01-15.csv",
        ):
            path = os.path.join(out, fname)
            assert os.path.isfile(path)
            with open(path, encoding="utf-8") as f:
                lines = f.read().strip().splitlines()
            assert len(lines) == 1  # header seul
    finally:
        db.close()
        os.unlink(dbp)
