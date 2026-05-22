"""Pousse les 3 listes (to_delete, to_pause, to_modify) au CMS Cogiterra.

Format du POST :
    POST {WEBHOOK_URL}
    Headers: Authorization: Bearer {token}, Content-Type: application/json
    Body: {
        "report_date": "2026-05-22",
        "total": 194,
        "to_delete": [{"email": "...", "reason": "...", "category": "hard_bounce"}, ...],
        "to_pause":  [{"email": "...", "failures": 5, ...}],
        "to_modify": [{"email": "...", "new_email": "...", ...}]
    }

Le CMS répond 200 OK et applique les changements (suppression, déconfirmation, MAJ).
"""
from __future__ import annotations

import csv
import json
import logging
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class WebhookSender:
    def __init__(self, cfg):
        self.url = cfg.WEBHOOK_URL
        self.token = cfg.WEBHOOK_AUTH_TOKEN
        self.timeout = cfg.WEBHOOK_TIMEOUT

    def is_enabled(self) -> bool:
        return bool(self.url)

    def push(self, csv_files: Dict[str, str], stats: dict, date_str: str) -> bool:
        """Lit les 3 CSV et POST le payload JSON. Retourne True si HTTP 2xx."""
        if not self.is_enabled():
            return False

        payload = {
            "report_date": date_str,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total": stats.get("total", 0),
            "to_delete": self._read_csv(csv_files.get("to_be_deleted")),
            "to_pause":  self._read_csv(csv_files.get("to_be_paused")),
            "to_modify": self._read_csv(csv_files.get("to_be_modified")),
        }

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "cogiterra-bounce-processor/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                if 200 <= status < 300:
                    logging.info(
                        "WEBHOOK | OK %s | %d to_delete · %d to_pause · %d to_modify",
                        status,
                        len(payload["to_delete"]),
                        len(payload["to_pause"]),
                        len(payload["to_modify"]),
                    )
                    return True
                logging.warning("WEBHOOK | HTTP %s sur %s", status, self.url)
                return False
        except Exception as e:
            logging.error("WEBHOOK | échec POST %s : %s", self.url, e)
            return False

    @staticmethod
    def _read_csv(path) -> List[dict]:
        if not path:
            return []
        p = Path(path)
        if not p.exists():
            return []
        with p.open("r", encoding="utf-8") as f:
            return [dict(row) for row in csv.DictReader(f)]
