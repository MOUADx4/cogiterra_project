"""SQLite storage : tables result, stats, et compteur cross-jours."""
import os
import sqlite3
import logging
from datetime import datetime, timezone
from typing import List, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS result (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_address  TEXT NOT NULL,
    category       TEXT NOT NULL,
    confidence     REAL NOT NULL,
    new_email      TEXT,
    reason         TEXT,
    method         TEXT NOT NULL,
    processed_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stats (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date       TEXT NOT NULL UNIQUE,
    total_processed   INTEGER DEFAULT 0,
    n_hard_bounce     INTEGER DEFAULT 0,
    n_soft_bounce     INTEGER DEFAULT 0,
    n_address_change  INTEGER DEFAULT 0,
    n_technical       INTEGER DEFAULT 0,
    n_unknown         INTEGER DEFAULT 0,
    n_forwarded       INTEGER DEFAULT 0,
    n_by_rules        INTEGER DEFAULT 0,
    n_by_llm          INTEGER DEFAULT 0,
    avg_confidence    REAL DEFAULT 0.0,
    n_soft_above_threshold INTEGER DEFAULT 0,
    report_sent_at    TEXT,
    report_sent_ok    INTEGER DEFAULT 0
);

-- Compteur permanent par adresse pour gérer le seuil soft-bounce cross-jours
CREATE TABLE IF NOT EXISTS soft_bounce_counter (
    email_address  TEXT PRIMARY KEY,
    failures       INTEGER NOT NULL DEFAULT 0,
    last_failure   TEXT NOT NULL
);

-- Compteur du jour pour les emails de contact transférés (vidé après rapport)
CREATE TABLE IF NOT EXISTS counters (
    name  TEXT PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0
);

-- Suggestions de règles regex proposées par le LLM (self-improving system)
CREATE TABLE IF NOT EXISTS rule_suggestions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern         TEXT NOT NULL,
    category        TEXT NOT NULL,
    confidence      REAL DEFAULT 0.85,
    sample_email    TEXT,
    sample_text     TEXT,
    llm_reason      TEXT,
    suggested_at    TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending|adopted|rejected
    decided_at      TEXT
);

CREATE INDEX IF NOT EXISTS idx_result_category    ON result(category);
CREATE INDEX IF NOT EXISTS idx_result_processed   ON result(processed_at);
CREATE INDEX IF NOT EXISTS idx_result_email       ON result(email_address);
CREATE INDEX IF NOT EXISTS idx_suggestions_status ON rule_suggestions(status);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


class Database:
    """Wrapper SQLite. Crée le schéma au premier usage."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Écriture des résultats du jour
    # ------------------------------------------------------------------
    def save_result(self, result, parsed=None) -> None:
        """
        INSERT d'un ClassificationResult dans table result.
        Met également à jour le compteur soft_bounce_counter si pertinent.
        Si l'email est hard_bounce ou address_change, on remet le compteur à 0.
        """
        email = getattr(result, "failed_recipient", None)
        if not email and parsed is not None:
            email = getattr(parsed, "failed_recipient", None)
        if not email:
            email = "unknown@unknown"

        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO result (email_address, category, confidence, new_email,
                                reason, method, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email,
                str(result.category.value) if hasattr(result.category, "value") else str(result.category),
                float(result.confidence),
                result.new_email,
                result.reason,
                result.method,
                _now_iso(),
            ),
        )

        category = result.category.value if hasattr(result.category, "value") else str(result.category)
        if category == "soft_bounce":
            cur.execute(
                """
                INSERT INTO soft_bounce_counter (email_address, failures, last_failure)
                VALUES (?, 1, ?)
                ON CONFLICT(email_address) DO UPDATE SET
                    failures = failures + 1,
                    last_failure = excluded.last_failure
                """,
                (email, _now_iso()),
            )
        elif category in ("hard_bounce", "address_change"):
            cur.execute(
                "DELETE FROM soft_bounce_counter WHERE email_address = ?",
                (email,),
            )

        self._conn.commit()

    def increment_forwarded(self) -> None:
        """Incrémente le compteur du jour des emails de contact transférés."""
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO counters (name, value) VALUES ('forwarded_today', 1)
            ON CONFLICT(name) DO UPDATE SET value = value + 1
            """
        )
        self._conn.commit()

    def get_counter(self, name: str) -> int:
        row = self._conn.execute(
            "SELECT value FROM counters WHERE name = ?", (name,)
        ).fetchone()
        return int(row["value"]) if row else 0

    def reset_counter(self, name: str) -> None:
        self._conn.execute(
            "INSERT INTO counters (name, value) VALUES (?, 0) "
            "ON CONFLICT(name) DO UPDATE SET value = 0",
            (name,),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Lectures pour la génération des CSV
    # ------------------------------------------------------------------
    def get_results_by_category(self, category: str) -> List[dict]:
        rows = self._conn.execute(
            "SELECT * FROM result WHERE category = ? ORDER BY processed_at",
            (category,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_soft_bounces_above_threshold(self, threshold: int) -> List[dict]:
        """
        Retourne les adresses dont le compteur cumulé de soft bounces
        dépasse le seuil. La première occurrence du jour est retournée
        avec son timestamp `first_seen_today`.
        """
        rows = self._conn.execute(
            """
            SELECT c.email_address,
                   c.failures,
                   COALESCE(r.first_seen, c.last_failure) AS first_seen_today,
                   COALESCE(r.confidence, 0.0)            AS confidence,
                   COALESCE(r.method, 'rules')            AS method
            FROM soft_bounce_counter c
            LEFT JOIN (
                SELECT email_address,
                       MIN(processed_at) AS first_seen,
                       AVG(confidence)   AS confidence,
                       MAX(method)       AS method
                FROM result
                WHERE category = 'soft_bounce'
                GROUP BY email_address
            ) r ON r.email_address = c.email_address
            WHERE c.failures >= ?
            ORDER BY c.failures DESC
            """,
            (threshold,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Statistiques quotidiennes
    # ------------------------------------------------------------------
    def compute_daily_stats(self) -> dict:
        """Agrège la table result pour produire les compteurs du rapport."""
        cur = self._conn.cursor()
        row = cur.execute(
            """
            SELECT
                COUNT(*)                                                    AS total,
                SUM(CASE WHEN category = 'hard_bounce'      THEN 1 ELSE 0 END) AS n_hard,
                SUM(CASE WHEN category = 'soft_bounce'      THEN 1 ELSE 0 END) AS n_soft,
                SUM(CASE WHEN category = 'address_change'   THEN 1 ELSE 0 END) AS n_changes,
                SUM(CASE WHEN category = 'technical_error'  THEN 1 ELSE 0 END) AS n_technical,
                SUM(CASE WHEN category = 'unknown'          THEN 1 ELSE 0 END) AS n_unknown,
                SUM(CASE WHEN method   = 'rules'            THEN 1 ELSE 0 END) AS n_rules,
                SUM(CASE WHEN method LIKE 'llm%'            THEN 1 ELSE 0 END) AS n_llm,
                AVG(CASE WHEN method LIKE 'llm%' THEN confidence END)         AS avg_conf_llm
            FROM result
            """
        ).fetchone()

        from config import SOFT_BOUNCE_THRESHOLD, SOFT_BOUNCE_WARNING
        n_above = len(self.get_soft_bounces_above_threshold(SOFT_BOUNCE_THRESHOLD))
        tracking = self.get_soft_bounce_tracking_stats(
            SOFT_BOUNCE_THRESHOLD, SOFT_BOUNCE_WARNING,
        )
        n_forwarded = self.get_counter("forwarded_today")

        return {
            "total": int(row["total"] or 0),
            "n_hard": int(row["n_hard"] or 0),
            "n_soft": int(row["n_soft"] or 0),
            "n_changes": int(row["n_changes"] or 0),
            "n_technical": int(row["n_technical"] or 0),
            "n_unknown": int(row["n_unknown"] or 0),
            "n_rules": int(row["n_rules"] or 0),
            "n_llm": int(row["n_llm"] or 0),
            "avg_confidence": float(row["avg_conf_llm"] or 0.0),
            "n_soft_above_threshold": n_above,
            "n_forwarded": n_forwarded,
            # Stock global du compteur cross-jours (indépendant du flux du jour)
            "n_tracked": tracking["n_tracked"],
            "n_warning": tracking["n_warning"],
        }

    def get_soft_bounce_tracking_stats(self, threshold: int, warning: int) -> dict:
        """Statistiques du compteur global soft_bounce_counter.

        - n_tracked : adresses sous surveillance (1 ≤ failures < threshold)
        - n_warning : adresses dans la zone d'alerte (warning ≤ failures < threshold)
        """
        row = self._conn.execute(
            """
            SELECT
                SUM(CASE WHEN failures >= 1 AND failures < ? THEN 1 ELSE 0 END) AS n_tracked,
                SUM(CASE WHEN failures >= ? AND failures < ? THEN 1 ELSE 0 END) AS n_warning
            FROM soft_bounce_counter
            """,
            (threshold, warning, threshold),
        ).fetchone()
        return {
            "n_tracked": int(row["n_tracked"] or 0),
            "n_warning": int(row["n_warning"] or 0),
        }

    def save_stats(self, stats: dict, date_str: str,
                   report_sent_ok: bool = True,
                   report_sent_at: Optional[str] = None) -> None:
        """INSERT OR REPLACE dans table stats."""
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO stats (
                report_date, total_processed,
                n_hard_bounce, n_soft_bounce, n_address_change,
                n_technical, n_unknown, n_forwarded,
                n_by_rules, n_by_llm, avg_confidence,
                n_soft_above_threshold,
                report_sent_at, report_sent_ok
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(report_date) DO UPDATE SET
                total_processed = excluded.total_processed,
                n_hard_bounce = excluded.n_hard_bounce,
                n_soft_bounce = excluded.n_soft_bounce,
                n_address_change = excluded.n_address_change,
                n_technical = excluded.n_technical,
                n_unknown = excluded.n_unknown,
                n_forwarded = excluded.n_forwarded,
                n_by_rules = excluded.n_by_rules,
                n_by_llm = excluded.n_by_llm,
                avg_confidence = excluded.avg_confidence,
                n_soft_above_threshold = excluded.n_soft_above_threshold,
                report_sent_at = excluded.report_sent_at,
                report_sent_ok = excluded.report_sent_ok
            """,
            (
                date_str,
                stats["total"],
                stats["n_hard"],
                stats["n_soft"],
                stats["n_changes"],
                stats["n_technical"],
                stats["n_unknown"],
                stats["n_forwarded"],
                stats["n_rules"],
                stats["n_llm"],
                stats["avg_confidence"],
                stats["n_soft_above_threshold"],
                report_sent_at or _now_iso(),
                1 if report_sent_ok else 0,
            ),
        )
        self._conn.commit()

    def clear_results(self) -> None:
        """DELETE FROM result + remise à zéro des compteurs du jour.

        Le compteur soft_bounce_counter est conservé (cross-jours).
        Les adresses ayant déclenché le seuil voient leur compteur remis à zéro
        pour éviter de les re-flagger jour après jour.
        """
        cur = self._conn.cursor()
        from config import SOFT_BOUNCE_THRESHOLD
        cur.execute(
            "DELETE FROM soft_bounce_counter WHERE failures >= ?",
            (SOFT_BOUNCE_THRESHOLD,),
        )
        cur.execute("DELETE FROM result")
        cur.execute("UPDATE counters SET value = 0")
        self._conn.commit()
        logging.info("Table result vidée et compteurs du jour remis à zéro.")

    # ------------------------------------------------------------------
    # Self-improving rules : suggestions de patterns regex
    # ------------------------------------------------------------------
    def add_rule_suggestion(self, *, pattern: str, category: str,
                            confidence: float, sample_email: str,
                            sample_text: str, llm_reason: str) -> bool:
        """Ajoute une suggestion. Ignore si pattern + category déjà existant."""
        cur = self._conn.cursor()
        existing = cur.execute(
            "SELECT id FROM rule_suggestions WHERE pattern = ? AND category = ?",
            (pattern, category),
        ).fetchone()
        if existing:
            return False
        cur.execute(
            """INSERT INTO rule_suggestions
               (pattern, category, confidence, sample_email, sample_text,
                llm_reason, suggested_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (pattern, category, float(confidence), sample_email,
             (sample_text or "")[:500], llm_reason, _now_iso()),
        )
        self._conn.commit()
        return True

    def list_rule_suggestions(self, status: str = "pending") -> List[dict]:
        rows = self._conn.execute(
            "SELECT * FROM rule_suggestions WHERE status = ? ORDER BY suggested_at DESC",
            (status,),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_rule_suggestion_status(self, suggestion_id: int, status: str) -> None:
        self._conn.execute(
            "UPDATE rule_suggestions SET status = ?, decided_at = ? WHERE id = ?",
            (status, _now_iso(), suggestion_id),
        )
        self._conn.commit()
