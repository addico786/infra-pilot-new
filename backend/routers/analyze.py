"""
backend/routers/analyze.py
─────────────────────────────────────────────────────────────────
POST /analyze — Layer 2 Navigation.
Orchestrates the full drift analysis pipeline by calling atomic tools.
"""

import uuid
import os
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()

# .tmp dir setup
TMP = Path(".tmp")
(TMP / "logs").mkdir(parents=True, exist_ok=True)
(TMP / "snapshots").mkdir(parents=True, exist_ok=True)


# ── Request / Response Models ──────────────────────────────────

class AnalyzeRequest(BaseModel):
    content: str                      # Raw file content (pasted or from GitHub)
    file_name: str = "infra.tf"       # Logical file name for labeling
    email_recipients: Optional[List[str]] = None  # Override email list
    model: Optional[str] = None       # e.g. "ollama:llama3", "gemini", None=auto

class DriftEventResponse(BaseModel):
    event_id: str
    resource_type: str
    resource_name: str
    drift_type: str
    severity: str
    changed_field: str
    baseline_value: Optional[str]
    current_value: Optional[str]
    ai_summary: str
    risk_score: float
    recommendation: str
    model_used: str

class SummaryResponse(BaseModel):
    total: int
    critical: int
    high: int
    medium: int
    low: int

class AnalyzeResponse(BaseModel):
    run_id: str
    generated_at: str
    file_name: str
    drift_score: float
    summary: SummaryResponse
    drift_events: List[DriftEventResponse]
    sheet_url: Optional[str]
    email_sent: bool
    email_recipients: List[str]
    model_used: str


# ── Pipeline Orchestration ─────────────────────────────────────

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    """
    Layer 2 — Navigation:
    1. Ingest  → tools/ingest_files.py
    2. Detect  → tools/detect_drift.py
    3. Analyze → tools/analyze_with_ai.py
    4. Deliver → tools/deliver_sheet.py + tools/deliver_email.py
    """

    run_id = str(uuid.uuid4())
    generated_at = datetime.utcnow().isoformat()

    # ── Step 1: Ingest ────────────────────────────────────────
    try:
        from tools.ingest_files import ingest
        ingested = ingest(
            content=req.content,
            file_path=req.file_name,
            file_type="auto",
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"File ingestion failed: {e}")

    if ingested.get("parse_errors"):
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse file: {ingested['parse_errors']}",
        )

    # ── Step 2: Detect drift (vs empty baseline for now) ─────
    try:
        from tools.detect_drift import detect_drift
        drift_events = detect_drift(
            current=ingested["resources"],
            baseline={},
            file_path=req.file_name,
            file_type=ingested["file_type"],
            run_id=run_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drift detection failed: {e}")

    # ── Step 3: AI Analysis ───────────────────────────────────
    try:
        from tools.analyze_with_ai import analyze_events
        drift_events = analyze_events(drift_events, model_override=req.model)
    except Exception as e:
        # AI analysis failure is non-fatal — continue with placeholder
        for ev in drift_events:
            if ev.get("ai_analysis") is None:
                ev["ai_analysis"] = {
                    "summary": "AI analysis unavailable",
                    "risk_score": -1,
                    "recommendation": "Manual review required",
                    "model_used": "none",
                }

    # ── Compute Drift Score ───────────────────────────────────
    severity_weights = {"critical": 10, "high": 7, "medium": 4, "low": 1}
    if drift_events:
        raw_score = sum(
            severity_weights.get(e.get("severity", "low"), 1)
            for e in drift_events
        )
        drift_score = round(min(raw_score / max(len(drift_events), 1), 10.0), 1)
    else:
        drift_score = 0.0

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for e in drift_events:
        sev = e.get("severity", "low")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # ── Step 4A: Deliver to Google Sheets ────────────────────
    sheet_url = None
    try:
        from tools.deliver_sheet import write_report
        sheet_url = write_report(
            run_id=run_id,
            generated_at=generated_at,
            file_name=req.file_name,
            drift_score=drift_score,
            severity_counts=severity_counts,
            drift_events=drift_events,
        )
    except Exception:
        pass  # Sheet delivery is non-fatal

    # ── Step 4B: Send Email ───────────────────────────────────
    recipients = req.email_recipients or os.getenv("EMAIL_RECIPIENTS", "").split(",")
    recipients = [r.strip() for r in recipients if r.strip()]
    email_sent = False
    try:
        from tools.deliver_email import send_report
        send_report(
            run_id=run_id,
            generated_at=generated_at,
            file_name=req.file_name,
            drift_score=drift_score,
            severity_counts=severity_counts,
            drift_events=drift_events,
            sheet_url=sheet_url,
            recipients=recipients,
        )
        email_sent = True
    except Exception:
        pass  # Email delivery is non-fatal

    # ── Build Response ────────────────────────────────────────
    model_used = drift_events[0]["ai_analysis"]["model_used"] if drift_events else "none"

    events_response = [
        DriftEventResponse(
            event_id=e["event_id"],
            resource_type=e["resource_type"],
            resource_name=e["resource_name"],
            drift_type=e["drift_type"],
            severity=e["severity"],
            changed_field=e.get("changed_field", ""),
            baseline_value=str(e.get("baseline_value", "")) or None,
            current_value=str(e.get("current_value", "")) or None,
            ai_summary=e["ai_analysis"]["summary"],
            risk_score=e["ai_analysis"]["risk_score"],
            recommendation=e["ai_analysis"]["recommendation"],
            model_used=e["ai_analysis"]["model_used"],
        )
        for e in drift_events
    ]

    return AnalyzeResponse(
        run_id=run_id,
        generated_at=generated_at,
        file_name=req.file_name,
        drift_score=drift_score,
        summary=SummaryResponse(
            total=len(drift_events),
            **severity_counts,
        ),
        drift_events=events_response,
        sheet_url=sheet_url,
        email_sent=email_sent,
        email_recipients=recipients,
        model_used=model_used,
    )
