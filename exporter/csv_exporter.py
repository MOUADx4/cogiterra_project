"""Génère les 3 CSV à partir de la table result."""
import os
import csv
import logging
from typing import List, Tuple


class CsvExporter:
    """Génère to_be_deleted, to_be_paused, to_be_modified."""

    def __init__(self, db, output_dir: str, date_str: str, threshold: int = 5):
        self.db = db
        self.output_dir = output_dir
        self.date_str = date_str
        self.threshold = threshold
        os.makedirs(output_dir, exist_ok=True)

    def generate_all(self) -> List[str]:
        return [
            self.generate_to_be_deleted(),
            self.generate_to_be_paused(),
            self.generate_to_be_modified(),
        ]

    # ------------------------------------------------------------------
    def generate_to_be_deleted(self) -> str:
        path = os.path.join(self.output_dir, f"to_be_deleted_{self.date_str}.csv")
        rows = self.db.get_results_by_category("hard_bounce")
        header = ["email", "category", "dsn_status", "diagnostic_code",
                  "bounce_date", "confidence", "method"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for r in rows:
                writer.writerow([
                    r["email_address"],
                    r["category"],
                    "",                       # dsn_status non stocké dans result
                    r.get("reason") or "",
                    r["processed_at"],
                    f"{r['confidence']:.2f}",
                    r["method"],
                ])
        logging.info("CSV to_be_deleted: %d lignes → %s", len(rows), path)
        return path

    def generate_to_be_paused(self) -> str:
        path = os.path.join(self.output_dir, f"to_be_paused_{self.date_str}.csv")
        rows = self.db.get_soft_bounces_above_threshold(self.threshold)
        header = ["email", "category", "consecutive_failures", "threshold",
                  "first_seen_today", "confidence", "method"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for r in rows:
                writer.writerow([
                    r["email_address"],
                    "soft_bounce",
                    r["failures"],
                    self.threshold,
                    r["first_seen_today"],
                    f"{float(r['confidence']):.2f}",
                    r["method"],
                ])
        logging.info("CSV to_be_paused: %d lignes → %s", len(rows), path)
        return path

    def generate_to_be_modified(self) -> str:
        path = os.path.join(self.output_dir, f"to_be_modified_{self.date_str}.csv")
        rows = [r for r in self.db.get_results_by_category("address_change")
                if r.get("new_email")]
        header = ["old_email", "new_email", "confidence", "method",
                  "detected_at", "reason"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for r in rows:
                writer.writerow([
                    r["email_address"],
                    r["new_email"],
                    f"{r['confidence']:.2f}",
                    r["method"],
                    r["processed_at"],
                    r.get("reason") or "",
                ])
        logging.info("CSV to_be_modified: %d lignes → %s", len(rows), path)
        return path
