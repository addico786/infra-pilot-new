"""
tools/deliver_sheet.py
─────────────────────────────────────────────────────────────────
Layer 3 — Tool | SOP-04A: Google Sheets Delivery (Disabled)

Google Sheets is not configured for this deployment.
This module is a non-fatal no-op stub that returns None
so the rest of the pipeline is unaffected.

To enable: add credentials/gcp_service_account.json and
           set GOOGLE_SHEET_ID in .env
"""

import logging
log = logging.getLogger(__name__)


def write_report(
    run_id:          str,
    generated_at:    str,
    file_name:       str,
    drift_score:     float,
    severity_counts: dict,
    drift_events:    list,
) -> None:
    """
    No-op stub. Returns None (sheet_url will be None in the response).
    Pipeline continues normally.
    """
    log.info("Google Sheets delivery is disabled. Skipping sheet write for run %s.", run_id)
    return None
