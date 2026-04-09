"""
tools/deliver_email.py
─────────────────────────────────────────────────────────────────
Layer 3 — Tool | SOP-04B: Email Delivery

Sends a professional HTML drift report email via SMTP (Gmail).
Non-fatal: if delivery fails, logs error but does not raise.

Usage:
    from tools.deliver_email import send_report
    send_report(run_id=..., drift_score=7.4, summary={...}, drift_events=[...], ...)
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone

log = logging.getLogger(__name__)

# ── Severity styling ───────────────────────────────────────────
SEV_COLORS = {
    "critical": "#ff4757",
    "high":     "#ff6b35",
    "medium":   "#ffa502",
    "low":      "#2ed573",
}

SEV_BG = {
    "critical": "#2a0a0f",
    "high":     "#2a150a",
    "medium":   "#2a1f0a",
    "low":      "#0a2a15",
}

DRIFT_PILL_COLOR = {
    "added":      "#2ed573",
    "removed":    "#ff4757",
    "modified":   "#ffa502",
    "deprecated": "#ff6b35",
}

SCORE_COLOR = {
    range(0, 3):  "#2ed573",
    range(3, 6):  "#ffa502",
    range(6, 11): "#ff4757",
}

def _score_to_color(score: float) -> str:
    s = int(score)
    if s < 3:    return "#2ed573"
    if s < 6:    return "#ffa502"
    return "#ff4757"

def _verdict(score: float) -> str:
    if score >= 7.5: return "CRITICAL RISK"
    if score >= 5:   return "HIGH RISK"
    if score >= 2.5: return "MEDIUM RISK"
    return "LOW RISK"


# ── HTML Builder ───────────────────────────────────────────────

def _build_html(
    run_id: str,
    generated_at: str,
    file_name: str,
    drift_score: float,
    severity_counts: dict,
    drift_events: list,
    sheet_url: str | None,
) -> str:
    score_color = _score_to_color(drift_score)
    verdict     = _verdict(drift_score)

    # Top 5 highest-risk events for the email summary
    sorted_events = sorted(
        drift_events,
        key=lambda e: e.get("ai_analysis", {}).get("risk_score", -1),
        reverse=True,
    )[:5]

    # ── Event rows ────────────────────────────────────────────
    event_rows = ""
    for ev in sorted_events:
        sev   = ev.get("severity", "low")
        dtype = ev.get("drift_type", "modified")
        ai    = ev.get("ai_analysis", {})
        rs    = ai.get("risk_score", -1)
        rs_display = f"{rs:.1f}" if rs >= 0 else "—"

        event_rows += f"""
        <tr style="border-bottom:1px solid rgba(255,255,255,0.06);">
          <td style="padding:10px 12px; font-family:monospace; font-size:12px; color:#a0aec0;">
            <span style="display:block; font-size:10px; color:#718096;">{ev.get('resource_type','')}</span>
            <strong style="color:#e2e8f0;">{ev.get('resource_name','')}</strong>
          </td>
          <td style="padding:10px 12px;">
            <span style="background:{DRIFT_PILL_COLOR.get(dtype,'#718096')}22; color:{DRIFT_PILL_COLOR.get(dtype,'#718096')};
                         padding:3px 8px; border-radius:4px; font-size:11px; font-weight:700; text-transform:uppercase;">
              {dtype}
            </span>
          </td>
          <td style="padding:10px 12px;">
            <span style="color:{SEV_COLORS.get(sev,'#718096')}; font-weight:700; font-size:12px; text-transform:uppercase;">
              {sev}
            </span>
          </td>
          <td style="padding:10px 12px; color:#a0aec0; font-size:12px; line-height:1.5; max-width:240px;">
            {ai.get('summary','—')}
          </td>
          <td style="padding:10px 12px; text-align:center; font-weight:700; color:{_score_to_color(rs if rs >= 0 else 0)}; font-size:13px;">
            {rs_display}
          </td>
        </tr>"""

    # ── Sheet button ─────────────────────────────────────────
    sheet_button = ""
    if sheet_url:
        sheet_button = f"""
        <a href="{sheet_url}"
           style="display:inline-block; margin-top:8px; padding:10px 24px; background:linear-gradient(135deg,#7c3aed,#06b6d4);
                  color:#fff; text-decoration:none; border-radius:24px; font-weight:700; font-size:13px;">
          View Full Report in Google Sheets ↗
        </a>"""

    # ── Full HTML ─────────────────────────────────────────────
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Infra-Pilot Drift Report</title></head>
<body style="margin:0;padding:0;background:#06060f;font-family:'Segoe UI',Arial,sans-serif;color:#e2e8f0;">

<div style="max-width:680px;margin:0 auto;padding:32px 16px;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,rgba(124,58,237,0.15),rgba(6,182,212,0.1));
              border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:28px 32px; margin-bottom:20px;">
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:16px;">
      <span style="font-size:24px;">🛸</span>
      <div>
        <h1 style="margin:0; font-size:20px; font-weight:800; color:#fff;">Infra-Pilot</h1>
        <p style="margin:0; font-size:12px; color:#718096;">AI-Powered Drift Analysis Report</p>
      </div>
    </div>
    <div style="font-size:12px; color:#718096;">
      Run ID: <code style="color:#a0aec0;">{run_id}</code><br>
      File: <code style="color:#a78bfa;">{file_name}</code> &nbsp;·&nbsp;
      Generated: {generated_at[:19].replace('T',' ')} UTC
    </div>
  </div>

  <!-- Score Banner -->
  <div style="background:rgba(0,0,0,0.4); border:1px solid {score_color}44;
              border-radius:16px; padding:24px 32px; margin-bottom:20px; text-align:center;">
    <p style="margin:0 0 4px; font-size:11px; font-weight:700; text-transform:uppercase;
              letter-spacing:0.1em; color:#718096;">Overall Drift Score</p>
    <div style="font-size:56px; font-weight:900; color:{score_color}; line-height:1; margin:8px 0;">
      {drift_score:.1f}<span style="font-size:22px; color:#718096;">/10</span>
    </div>
    <span style="display:inline-block; padding:4px 16px; border-radius:99px;
                 background:{score_color}20; color:{score_color}; font-weight:700; font-size:13px;">
      {verdict}
    </span>
  </div>

  <!-- Severity Breakdown -->
  <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:20px;">
    {''.join(f"""
    <div style="background:rgba(0,0,0,0.35); border:1px solid {SEV_COLORS.get(s,'#718096')}33;
                border-radius:12px; padding:16px; text-align:center;">
      <div style="font-size:22px; font-weight:800; color:{SEV_COLORS.get(s,'#718096')};">
        {severity_counts.get(s, 0)}
      </div>
      <div style="font-size:10px; font-weight:700; text-transform:uppercase;
                  letter-spacing:0.08em; color:{SEV_COLORS.get(s,'#718096')}; margin-top:4px;">
        {s}
      </div>
    </div>""" for s in ['critical','high','medium','low'])}
  </div>

  <!-- Top Events Table -->
  <div style="background:rgba(0,0,0,0.3); border:1px solid rgba(255,255,255,0.07);
              border-radius:16px; overflow:hidden; margin-bottom:20px;">
    <div style="padding:16px 20px; border-bottom:1px solid rgba(255,255,255,0.07);">
      <h2 style="margin:0; font-size:14px; font-weight:700; color:#e2e8f0;">
        📊 Top Drift Events <span style="font-size:11px; color:#718096; font-weight:400;">(highest risk first)</span>
      </h2>
    </div>
    <table style="width:100%; border-collapse:collapse;">
      <thead>
        <tr style="background:rgba(0,0,0,0.2);">
          <th style="padding:8px 12px; text-align:left; font-size:10px; font-weight:700;
                     text-transform:uppercase; letter-spacing:0.08em; color:#718096;">Resource</th>
          <th style="padding:8px 12px; text-align:left; font-size:10px; font-weight:700;
                     text-transform:uppercase; letter-spacing:0.08em; color:#718096;">Type</th>
          <th style="padding:8px 12px; text-align:left; font-size:10px; font-weight:700;
                     text-transform:uppercase; letter-spacing:0.08em; color:#718096;">Severity</th>
          <th style="padding:8px 12px; text-align:left; font-size:10px; font-weight:700;
                     text-transform:uppercase; letter-spacing:0.08em; color:#718096;">AI Summary</th>
          <th style="padding:8px 12px; text-align:center; font-size:10px; font-weight:700;
                     text-transform:uppercase; letter-spacing:0.08em; color:#718096;">Risk</th>
        </tr>
      </thead>
      <tbody>{event_rows or '<tr><td colspan="5" style="padding:16px; text-align:center; color:#718096;">No drift events detected.</td></tr>'}</tbody>
    </table>
  </div>

  <!-- CTA / Sheet Link -->
  <div style="text-align:center; padding:8px 0 16px;">
    {sheet_button}
  </div>

  <!-- Footer -->
  <div style="text-align:center; font-size:11px; color:#4a5568; margin-top:16px; line-height:1.6;">
    Infra-Pilot &nbsp;·&nbsp; B.L.A.S.T. Protocol &nbsp;·&nbsp; A.N.T. Architecture<br>
    This report is AI-advisory only. All decisions remain with the operator.
  </div>

</div>
</body>
</html>"""


# ── Public API ─────────────────────────────────────────────────

def send_report(
    run_id:          str,
    generated_at:    str,
    file_name:       str,
    drift_score:     float,
    severity_counts: dict,
    drift_events:    list,
    sheet_url:       str | None = None,
    recipients:      list       = None,
) -> bool:
    """
    Send HTML drift report email via SMTP.

    Returns True if sent successfully, False otherwise (non-fatal).
    """
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")

    if not smtp_user or not smtp_pass:
        log.warning("Email not configured (SMTP_USER / SMTP_PASSWORD missing). Skipping.")
        return False

    if not recipients:
        env_recipients = os.getenv("EMAIL_RECIPIENTS", "")
        recipients = [r.strip() for r in env_recipients.split(",") if r.strip()]

    if not recipients:
        log.warning("No email recipients configured. Skipping.")
        return False

    subject = (
        f"[Infra-Pilot] Drift Report — "
        f"{generated_at[:10]} | File: {file_name} | Score: {drift_score:.1f}/10 | {_verdict(drift_score)}"
    )

    html_body = _build_html(
        run_id, generated_at, file_name,
        drift_score, severity_counts, drift_events, sheet_url,
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = smtp_user
    msg["To"]      = ", ".join(recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipients, msg.as_string())
        log.info("Email sent to %s", recipients)
        return True
    except Exception as e:
        log.error("Email delivery failed: %s", e)
        return False
