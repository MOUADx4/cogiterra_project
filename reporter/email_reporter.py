"""Envoi du rapport quotidien par email (texte + HTML) avec pièces jointes CSV."""
import os
import smtplib
import logging
from datetime import datetime
from email.message import EmailMessage
from email.utils import make_msgid, formatdate
from typing import List


class EmailReporter:
    """Composeur + expéditeur SMTP du rapport quotidien."""

    def __init__(self, config_module):
        self.cfg = config_module

    def send(self, csv_files: List[str], stats: dict, date_str: str) -> bool:
        """Retourne True si l'envoi SMTP a réussi."""
        subject = (
            f"[Equipe 3][Bounce Report] {date_str} — "
            f"{stats['total']} bounces traités"
        )
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.cfg.REPORT_SENDER
        msg["To"] = self.cfg.REPORT_RECIPIENT
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()

        text_body = self._render_text(stats, date_str)
        html_body = self._render_html(stats, date_str)
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")

        for path in csv_files:
            if not os.path.isfile(path):
                logging.warning("EmailReporter: pièce jointe absente %s", path)
                continue
            with open(path, "rb") as f:
                data = f.read()
            msg.add_attachment(
                data,
                maintype="text",
                subtype="csv",
                filename=os.path.basename(path),
            )

        try:
            with smtplib.SMTP(self.cfg.REPORT_SMTP_HOST,
                              self.cfg.REPORT_SMTP_PORT,
                              timeout=30) as smtp:
                if self.cfg.REPORT_SMTP_USE_TLS:
                    smtp.starttls()
                if self.cfg.REPORT_SMTP_USER:
                    smtp.login(self.cfg.REPORT_SMTP_USER,
                               self.cfg.REPORT_SMTP_PASSWORD)
                smtp.send_message(msg)
            logging.info("EmailReporter: rapport envoyé à %s",
                         self.cfg.REPORT_RECIPIENT)
            return True
        except Exception as e:
            logging.error("EmailReporter: échec SMTP — %s", e, exc_info=True)
            return False

    # ------------------------------------------------------------------
    def _render_text(self, stats: dict, date_str: str) -> str:
        total = stats["total"]
        n_forwarded = stats["n_forwarded"]
        total_received = total + n_forwarded
        n_rules = stats["n_rules"]
        n_llm = stats["n_llm"]
        total_classified = max(n_rules + n_llm, 1)
        pct_rules = 100.0 * n_rules / total_classified
        pct_llm = 100.0 * n_llm / total_classified
        return (
            f"Rapport automatique de traitement des bounces\n"
            f"Date : {date_str}\n"
            f"Généré à : {datetime.now().strftime('%H:%M:%S')}\n"
            f"══════════════════════════════════════════════\n\n"
            f"TRAITEMENT DU JOUR\n"
            f"──────────────────\n"
            f"  Emails reçus au total         : {total_received}\n"
            f"  dont emails de contact (transférés) : {n_forwarded}\n"
            f"  dont bounces traités          : {total}\n\n"
            f"CLASSIFICATION DES BOUNCES\n"
            f"───────────────────────────\n"
            f"  Hard bounces (→ suppression)  : {stats['n_hard']}\n"
            f"  Soft bounces (→ compteur)     : {stats['n_soft']}\n"
            f"    dont au-dessus du seuil ({self.cfg.SOFT_BOUNCE_THRESHOLD}) : "
            f"{stats['n_soft_above_threshold']}\n"
            f"  Changements d'adresse         : {stats['n_changes']}\n"
            f"  Erreurs techniques            : {stats['n_technical']}\n"
            f"  Non classifiés                : {stats['n_unknown']}\n\n"
            f"STOCK GLOBAL SOFT BOUNCES (suivi cross-jours)\n"
            f"──────────────────────────────────────────────\n"
            f"  Adresses suivies              : {stats.get('n_tracked', 0)}\n"
            f"    dont à {self.cfg.SOFT_BOUNCE_WARNING}+/{self.cfg.SOFT_BOUNCE_THRESHOLD} "
            f"(zone d'alerte)  : {stats.get('n_warning', 0)}\n\n"
            f"MÉTHODE DE CLASSIFICATION\n"
            f"──────────────────────────\n"
            f"  Par règles déterministes      : {n_rules} ({pct_rules:.1f}%)\n"
            f"  Par LLM ({self.cfg.LLM_MODEL})      : {n_llm} ({pct_llm:.1f}%)\n"
            f"  Confiance moyenne LLM         : {stats['avg_confidence']:.2f}\n\n"
            f"FICHIERS JOINTS (3 CSV)\n"
            f"────────────────────────\n"
            f"  to_be_deleted_{date_str}.csv      : {stats['n_hard']} adresse(s)\n"
            f"  to_be_paused_{date_str}.csv       : {stats['n_soft_above_threshold']} adresse(s)\n"
            f"  to_be_modified_{date_str}.csv     : {stats['n_changes']} adresse(s)\n\n"
            f"──────────────────────────────────────────────\n"
            f"Ce rapport est généré automatiquement.\n"
            f"La table result a été vidée après génération.\n"
        )

    def _render_html(self, stats: dict, date_str: str) -> str:
        """Email HTML avec CSS inline (compatibilité Outlook, Gmail, etc.)."""
        n_rules = stats["n_rules"]
        n_llm = stats["n_llm"]
        total_classified = max(n_rules + n_llm, 1)
        pct_rules = 100.0 * n_rules / total_classified
        pct_llm = 100.0 * n_llm / total_classified
        n_forwarded = stats["n_forwarded"]
        total_received = stats["total"] + n_forwarded
        n_tracked = stats.get("n_tracked", 0)
        n_warning = stats.get("n_warning", 0)
        warning_pct = (100.0 * n_warning / n_tracked) if n_tracked else 0.0

        def card(label, value, color, sub=""):
            sub_html = (
                f"<div style='font-size:11px;color:#6b7280;margin-top:4px;'>{sub}</div>"
                if sub else ""
            )
            return (
                f"<td align='center' valign='top' "
                f"style='padding:14px 8px;background:#ffffff;"
                f"border:1px solid #e5e7eb;border-radius:8px;width:33%;'>"
                f"<div style='font-size:12px;color:#6b7280;"
                f"text-transform:uppercase;letter-spacing:.5px;'>{label}</div>"
                f"<div style='font-size:28px;font-weight:700;color:{color};"
                f"line-height:1.1;margin-top:6px;'>{value}</div>"
                f"{sub_html}</td>"
            )

        def row(label, value, color="#111827", strong=False):
            v_style = (
                f"font-weight:600;color:{color};text-align:right;padding:8px 12px;"
                "font-variant-numeric:tabular-nums;"
            )
            if strong:
                v_style += "font-size:16px;"
            return (
                "<tr>"
                f"<td style='padding:8px 12px;color:#374151;'>{label}</td>"
                f"<td style='{v_style}'>{value}</td>"
                "</tr>"
            )

        warning_bar = ""
        if n_tracked:
            bar_pct = min(100, warning_pct)
            warning_bar = (
                f"<div style='margin:10px 12px 4px;'>"
                f"<div style='height:6px;background:#e5e7eb;border-radius:3px;overflow:hidden;'>"
                f"<div style='height:6px;width:{bar_pct:.1f}%;"
                f"background:{'#dc2626' if warning_pct > 30 else '#f59e0b' if warning_pct > 0 else '#10b981'};"
                f"'></div></div>"
                f"<div style='font-size:11px;color:#6b7280;margin-top:4px;'>"
                f"{warning_pct:.1f}% des adresses suivies sont en zone d'alerte"
                f"</div></div>"
            )

        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rapport bounces {date_str}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#111827;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f7;padding:24px 0;">
  <tr><td align="center">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);">

      <!-- Header -->
      <tr><td style="background:linear-gradient(135deg,#1e293b 0%,#334155 100%);padding:28px 32px;color:#ffffff;">
        <div style="font-size:12px;text-transform:uppercase;letter-spacing:1.5px;color:#94a3b8;">Rapport quotidien</div>
        <div style="font-size:24px;font-weight:700;margin-top:6px;">Traitement des bounces</div>
        <div style="font-size:14px;color:#cbd5e1;margin-top:8px;">{date_str} · généré à {datetime.now().strftime('%H:%M:%S')}</div>
      </td></tr>

      <!-- KPI cards -->
      <tr><td style="padding:24px 24px 8px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="8">
          <tr>
            {card("Reçus", total_received, "#1e293b", f"dont {n_forwarded} contact(s)")}
            {card("Bounces traités", stats["total"], "#0f766e")}
            {card("À suspendre", stats["n_soft_above_threshold"], "#dc2626" if stats["n_soft_above_threshold"] else "#9ca3af", f"seuil = {self.cfg.SOFT_BOUNCE_THRESHOLD}")}
          </tr>
        </table>
      </td></tr>

      <!-- Section : Classification -->
      <tr><td style="padding:24px 24px 8px;">
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#6b7280;font-weight:600;margin-bottom:8px;">Classification des bounces</div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:8px;border-collapse:separate;border-spacing:0;">
          {row("Hard bounces (suppression)", stats["n_hard"], "#dc2626", strong=True)}
          {row(f"Soft bounces du jour", stats["n_soft"], "#f59e0b")}
          {row(f"↳ dont au-dessus du seuil ({self.cfg.SOFT_BOUNCE_THRESHOLD})", stats["n_soft_above_threshold"], "#dc2626" if stats["n_soft_above_threshold"] else "#9ca3af")}
          {row("Changements d'adresse", stats["n_changes"], "#2563eb")}
          {row("Erreurs techniques", stats["n_technical"], "#6b7280")}
          {row("Non classifiés", stats["n_unknown"], "#6b7280")}
        </table>
      </td></tr>

      <!-- Section : Stock soft bounces -->
      <tr><td style="padding:16px 24px 8px;">
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#6b7280;font-weight:600;margin-bottom:8px;">Stock global soft bounces (suivi cross-jours)</div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:8px;border-collapse:separate;border-spacing:0;">
          {row("Adresses sous surveillance", n_tracked, "#111827", strong=True)}
          {row(f"↳ en zone d'alerte ({self.cfg.SOFT_BOUNCE_WARNING}+ / {self.cfg.SOFT_BOUNCE_THRESHOLD})", n_warning, "#dc2626" if n_warning else "#9ca3af")}
        </table>
        {warning_bar}
      </td></tr>

      <!-- Section : Méthode -->
      <tr><td style="padding:16px 24px 8px;">
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#6b7280;font-weight:600;margin-bottom:8px;">Méthode de classification</div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:8px;border-collapse:separate;border-spacing:0;">
          {row("Règles déterministes", f"{n_rules}  <span style='color:#9ca3af;font-weight:400;'>({pct_rules:.1f}%)</span>", "#0f766e")}
          {row(f"LLM ({self.cfg.LLM_MODEL})", f"{n_llm}  <span style='color:#9ca3af;font-weight:400;'>({pct_llm:.1f}%)</span>", "#7c3aed")}
          {row("Confiance moyenne LLM", f"{stats['avg_confidence']:.2f}", "#374151")}
        </table>
      </td></tr>

      <!-- Pièces jointes -->
      <tr><td style="padding:16px 24px 24px;">
        <div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#6b7280;font-weight:600;margin-bottom:8px;">Pièces jointes</div>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:8px;border-collapse:separate;border-spacing:0;">
          {row("📎 to_be_deleted_" + date_str + ".csv", f"{stats['n_hard']} adresse(s)", "#374151")}
          {row("📎 to_be_paused_" + date_str + ".csv", f"{stats['n_soft_above_threshold']} adresse(s)", "#374151")}
          {row("📎 to_be_modified_" + date_str + ".csv", f"{stats['n_changes']} adresse(s)", "#374151")}
        </table>
      </td></tr>

      <!-- Footer -->
      <tr><td style="padding:20px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;text-align:center;">
        <div style="font-size:12px;color:#6b7280;line-height:1.5;">
          Rapport généré automatiquement par <strong>bounce_processor2</strong>.<br>
          La table <code style="background:#e5e7eb;padding:1px 5px;border-radius:3px;font-family:monospace;">result</code> a été vidée après génération.
        </div>
      </td></tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""
