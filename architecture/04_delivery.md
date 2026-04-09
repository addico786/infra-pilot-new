# 📐 SOP-04: Delivery

## Tools: `tools/deliver_sheet.py` + `tools/deliver_email.py`

## Purpose
Deliver the final `DriftReport` payload to Google Sheets (primary) and Email (secondary).

---

## 4A — Google Sheets Delivery

### Tool: `tools/deliver_sheet.py`

### Setup Requirements
1. Google Cloud project with Sheets API + Drive API enabled.
2. Service account JSON at path in `GOOGLE_SERVICE_ACCOUNT_JSON`.
3. Share the target Google Sheet with the service account email (Editor access).

### Sheet Structure

**Tab 1: "Run Summary"**
| Run ID | Timestamp | Files Scanned | Total Drifts | Critical | High | Medium | Low | Trend | Sheet URL |
|--------|-----------|---------------|-------------|---------|------|--------|-----|-------|-----------|

**Tab 2: "Drift Events"**  
| Run ID | File | Type | Resource | Drift Type | Severity | Field | Old Value | New Value | AI Summary | Risk Score | Recommendation | Model |
|--------|------|------|----------|-----------|---------|-------|-----------|-----------|------------|-----------|----------------|-------|

### Logic
1. Authenticate with `gspread.service_account(filename=...)`.
2. Open sheet by `GOOGLE_SHEET_ID`.
3. Append a row to "Run Summary".
4. Append one row per drift event to "Drift Events".
5. Return the sheet URL.

### Error Handling
- Retry 3x with backoff on `gspread.exceptions.APIError`.
- Log delivery status to `.tmp/logs/delivery.json`.
- If sheet write fails, do not block email delivery.

---

## 4B — Email Delivery

### Tool: `tools/deliver_email.py`

### Email Content
- **Subject:** `[Infra-Pilot] Drift Report — <timestamp> | Score: <X>/10`
- **Body (HTML):**
  - Summary table: total drifts, severity counts
  - Top 5 highest-risk drift events
  - Link to Google Sheet for full report
  - Footer: model used, run ID

### Logic
1. Use `yagmail.SMTP(user=SMTP_USER, password=SMTP_PASSWORD)`.
2. Build HTML email body from `DriftReport`.
3. Send to all addresses in `EMAIL_RECIPIENTS`.

### Error Handling
- If email fails, log error but do not raise — delivery is best-effort.
- Log to `.tmp/logs/delivery.json`.
