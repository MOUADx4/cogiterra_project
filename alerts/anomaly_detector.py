"""Détection d'anomalies + envoi d'alertes Slack."""
from __future__ import annotations

import json
import logging
import urllib.request
from statistics import mean
from typing import Optional


class AnomalyDetector:
    """Détecte les pics inhabituels et alerte sur Slack."""

    def __init__(self, cfg):
        self.slack_url = cfg.SLACK_WEBHOOK_URL
        self.spike_mult = cfg.ALERT_SPIKE_MULTIPLIER
        self.min_baseline = cfg.ALERT_MIN_BASELINE

    def is_enabled(self) -> bool:
        return bool(self.slack_url)

    def check_and_alert(self, db, stats_today: dict, date_str: str) -> Optional[dict]:
        """Compare stats du jour à la moyenne 7j. Si pic → POST Slack.

        Retourne un dict de diagnostic, ou None si pas d'anomalie.
        """
        if not self.is_enabled():
            return None

        baseline = self._compute_baseline(db)
        if baseline is None:
            logging.info("ALERT | pas assez d'historique pour comparer (< 3 jours)")
            return None

        total_today = int(stats_today.get("total", 0))
        if baseline < self.min_baseline:
            logging.info(
                "ALERT | baseline %.1f trop faible (< %d), pas d'alerte déclenchée",
                baseline, self.min_baseline,
            )
            return None

        ratio = total_today / baseline if baseline else 0
        anomalies = []

        if ratio >= self.spike_mult:
            anomalies.append(
                f"📈 *Pic de bounces* : {total_today} aujourd'hui vs "
                f"{baseline:.0f} en moyenne sur 7 jours (×{ratio:.1f})"
            )

        hard_pct = (stats_today.get("n_hard", 0) / total_today) if total_today else 0
        if hard_pct > 0.75:
            anomalies.append(
                f"🔴 *Taux hard élevé* : {hard_pct:.0%} des bounces sont des hard bounces"
            )

        unknown_pct = (stats_today.get("n_unknown", 0) / total_today) if total_today else 0
        if unknown_pct > 0.20:
            anomalies.append(
                f"❓ *Beaucoup d'inconnus* : {unknown_pct:.0%} non classifiés"
            )

        if not anomalies:
            logging.info(
                "ALERT | aucune anomalie (today=%d, baseline=%.0f, ratio=%.2f)",
                total_today, baseline, ratio,
            )
            return None

        sent = self._send_slack(date_str, total_today, baseline, anomalies, stats_today)
        return {
            "date": date_str,
            "total_today": total_today,
            "baseline_7d": baseline,
            "ratio": ratio,
            "anomalies": anomalies,
            "slack_sent": sent,
        }

    @staticmethod
    def _compute_baseline(db) -> Optional[float]:
        rows = db._conn.execute(
            "SELECT total_processed FROM stats "
            "ORDER BY report_date DESC LIMIT 7"
        ).fetchall()
        # On exclut la ligne du jour si présente (la dernière)
        values = [int(r["total_processed"] or 0) for r in rows[1:]]
        if len(values) < 3:
            return None
        return mean(values)

    def _send_slack(self, date_str, total, baseline, anomalies, stats) -> bool:
        anomaly_lines = "\n".join(f"  • {a}" for a in anomalies)
        text = (
            f":rotating_light: *Alerte Cogiterra Bounces — {date_str}*\n\n"
            f"{anomaly_lines}\n\n"
            f"*Détail du jour :*\n"
            f"  • Total : {total}\n"
            f"  • Hard : {stats.get('n_hard', 0)}\n"
            f"  • Soft : {stats.get('n_soft', 0)}\n"
            f"  • Unknown : {stats.get('n_unknown', 0)}\n"
            f"  • Moyenne 7j : {baseline:.0f}\n"
        )
        body = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(
            self.slack_url, data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                ok = 200 <= resp.status < 300
                logging.info("ALERT | Slack %s (status=%s)", "OK" if ok else "ECHEC", resp.status)
                return ok
        except Exception as e:
            logging.error("ALERT | échec POST Slack : %s", e)
            return False
