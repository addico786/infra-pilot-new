# 📐 SOP-00: System Overview

## Purpose
This document is the master SOP for Infra-Pilot. It describes the end-to-end system architecture, data flow, and the role of each component.

## System Description
Infra-Pilot is a full-stack AI-powered drift analysis tool for Terraform and Kubernetes YAML files.

**User Journey:**
1. User opens the React frontend in their browser.
2. User pastes a Terraform `.tf` or Kubernetes `.yaml` file into the editor.
3. User clicks "Analyze Drift".
4. React sends the file content to the FastAPI backend via `POST /analyze`.
5. The backend orchestrates the 3-layer pipeline:
   - **Ingest** → parse the file into structured resources.
   - **Detect** → compare against baseline (prior commit or snapshot) using `deepdiff`.
   - **Analyze** → route each drift event through the AI engine (Ollama → Gemini fallback).
   - **Deliver** → write report to Google Sheets + send email.
6. Backend returns the `drift_report` JSON to the frontend.
7. Frontend renders the Drift Score gauge, severity badges, and per-event table.
8. Email is sent to configured recipients automatically.

## Layer Map

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Layer 1 (SOPs) | `architecture/*.md` | Document all logic before coding |
| Layer 2 (Navigation) | `backend/routers/analyze.py` | Orchestrate tool calls |
| Layer 3 (Tools) | `tools/*.py` | Atomic, testable Python scripts |

## Key Invariants
- The system is **read-only** on source files.
- All secrets come from `.env` only.
- `.tmp/` is cleared at the start of each run.
- AI output is **advisory** — never commands.
- Every tool retries up to 3 times with exponential backoff.
