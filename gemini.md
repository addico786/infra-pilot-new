# 📜 gemini.md — Project Constitution

> **This file is law.** All schemas, rules, and architectural invariants live here.
> Only update when: a schema changes, a rule is added, or architecture is modified.

---

## 🏷️ Project Identity

| Field | Value |
|-------|-------|
| **Project Name** | Infra-Pilot |
| **Tagline** | AI-powered Terraform & Kubernetes drift pattern analyzer with glassmorphism UI |
| **Protocol** | B.L.A.S.T. (Blueprint → Link → Architect → Stylize → Trigger) |
| **Architecture** | A.N.T. 3-Layer (Architecture / Navigation / Tools) |
| **Stack** | React (Vite) frontend · FastAPI backend · Python tools |
| **Status** | 🟢 Phase 2 — Link (Blueprint Approved ✅) |
| **Last Updated** | 2026-04-09 |

---

## 🌟 North Star

> **Singular Desired Outcome:**
> A full-stack **Infra-Pilot tool** where the user:
> 1. **Pastes** Terraform (`.tf`) or Kubernetes (`.yaml`/`.yml`) content into a React UI.
> 2. Sees an **instant Drift Score** and per-event breakdown on the screen (glassmorphism dashboard).
> 3. Gets a **professional drift report emailed** to their inbox automatically.
> 4. Can also pull files from a **GitHub repo** for long-term drift pattern analysis.
> 5. AI analysis is powered by **Ollama (local)** + **Google Gemini (cloud fallback)**.

---

## 🗺️ Data Schema — **LOCKED ✅**

### Schema 1: Scan Request (Input)

```json
{
  "scan_request": {
    "run_id": "uuid-v4",
    "timestamp": "ISO8601",
    "source": {
      "type": "github | local",
      "github_repo_url": "string | null",
      "github_branch": "string",
      "local_path": "string | null",
      "file_patterns": ["*.tf", "*.yaml", "*.yml"]
    },
    "baseline": {
      "strategy": "git_commit | snapshot",
      "commit_sha": "string | null",
      "lookback_commits": "integer"
    },
    "ai_engine": {
      "primary": "gemini | ollama",
      "ollama_model": "llama3 | wizardlm | gemma4 | auto",
      "fallback": "gemini | none"
    },
    "delivery": {
      "google_sheet_id": "string | null",
      "email_recipients": ["string"]
    }
  }
}
```

### Schema 2: Drift Event (Intermediate — stored in `.tmp/`)

```json
{
  "drift_event": {
    "event_id": "uuid-v4",
    "run_id": "uuid-v4",
    "file_path": "string",
    "file_type": "terraform | kubernetes",
    "resource_type": "string",
    "resource_name": "string",
    "drift_type": "added | removed | modified | deprecated",
    "severity": "low | medium | high | critical",
    "changed_field": "string",
    "baseline_value": "any | null",
    "current_value": "any | null",
    "ai_analysis": {
      "summary": "string",
      "risk_score": "float (0.0–10.0)",
      "recommendation": "string",
      "model_used": "string"
    }
  }
}
```

### Schema 3: Drift Report (Output Payload — delivered to Google Sheets + Email)

```json
{
  "drift_report": {
    "run_id": "uuid-v4",
    "generated_at": "ISO8601",
    "source_summary": {
      "repo_or_path": "string",
      "files_scanned": "integer",
      "baseline_commit": "string"
    },
    "summary": {
      "total_drift_events": "integer",
      "by_severity": {
        "critical": "integer",
        "high": "integer",
        "medium": "integer",
        "low": "integer"
      },
      "by_file_type": {
        "terraform": "integer",
        "kubernetes": "integer"
      },
      "trend": "improving | stable | degrading | new_baseline"
    },
    "drift_events": ["drift_event[]"],
    "delivery_status": {
      "google_sheet_url": "string | null",
      "email_sent": "boolean",
      "email_recipients": ["string"]
    }
  }
}
```

---

## 🔌 Integrations & Credentials

| Service | Purpose | Library | Key Status |
|---------|---------|---------|------------|
| **GitHub API** | Clone/fetch repos, read commit history | `PyGithub` / `gitpython` | ❌ Needs setup |
| **Google Gemini API** | Cloud LLM drift analysis (free tier) | `google-generativeai` | ❌ Needs setup |
| **Ollama (local)** | Offline LLM analysis — Llama 3, WizardLM, Gemma 4 | `ollama` (pip) | ⚠️ Installed locally, needs verify |
| **Google Sheets API** | Deliver drift report payload | `gspread` | ❌ Needs service account |
| **Google Drive API** | Create/find sheets | `google-auth` | ❌ Needs service account |
| **SMTP / Email** | Send email summary | `smtplib` / `yagmail` | ❌ Needs setup |
| **React + Vite** | Glassmorphism frontend UI | `react`, `vite`, `axios` | ❌ Needs scaffold |
| **FastAPI** | Backend API bridge (Python ↔ React) | `fastapi`, `uvicorn` | ❌ Needs scaffold |

### Credential File Map (`.env`)
```env
# GitHub
GITHUB_TOKEN=

# Google Gemini
GEMINI_API_KEY=

# Google Sheets (path to service account JSON)
GOOGLE_SERVICE_ACCOUNT_JSON=./credentials/gcp_service_account.json
GOOGLE_SHEET_ID=

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_RECIPIENTS=

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_DEFAULT_MODEL=llama3
```

---

## ⚖️ Behavioral Rules — **LOCKED ✅**

1. **Never delete or mutate source files.** The system is read-only with respect to all input files.
2. **Never hallucinate drift.** If a diff cannot be deterministically computed, log it as `UNDETERMINED` — never fabricate a value.
3. **AI is advisory, not authoritative.** Risk scores and recommendations are labels, not commands to apply changes.
4. **Retry logic:** All API calls (Gemini, GitHub, Sheets) retry up to 3 times with exponential backoff before failing and logging the error.
5. **Ollama-first for local runs:** When `OLLAMA_HOST` is reachable, prefer local models to conserve Gemini quota. Fall back to Gemini if Ollama is unreachable.
6. **Rate limit awareness:** Google Sheets API: max 300 req/60s. Gemini API: respect free-tier limits. All tools implement throttling.
7. **Secrets are never hardcoded.** All credentials come from `.env` exclusively. `.env` is in `.gitignore`.
8. **`.tmp/` is ephemeral.** All intermediate files are written there. The `.tmp/` folder is never committed and cleared on each new run.
9. **Idempotent runs.** Running the same scan twice on the same commit should produce identical output.
10. **Log everything.** All tool executions write structured JSON logs to `.tmp/logs/`.

---

## 🏗️ Architectural Invariants

| Layer | Location | Rule |
|-------|----------|------|
| **Layer 1 — SOPs** | `architecture/*.md` | All logic documented before code is written. If logic changes, update SOP first. |
| **Layer 2 — Navigation** | Main orchestration script | Routes data between tools. No heavy business logic inline. |
| **Layer 3 — Tools** | `tools/*.py` | Atomic, single-purpose, testable scripts. Each tool does ONE thing. |

---

## 📂 File Structure (Approved)

```
infra-pilot-new/
├── gemini.md                    # ← Project Constitution (this file)
├── .env                         # API Keys/Secrets (never committed)
├── .env.example                 # Template (committed)
├── .gitignore
├── requirements.txt             # Python deps
│
├── architecture/                # Layer 1: SOPs
│   ├── 00_overview.md
│   ├── 01_file_ingestion.md
│   ├── 02_drift_detection.md
│   ├── 03_ai_analysis.md
│   ├── 04_delivery.md
│   └── 05_frontend.md
│
├── backend/                     # FastAPI — bridges frontend ↔ Python tools
│   ├── main.py                  # App entry point + CORS
│   └── routers/
│       ├── analyze.py           # POST /analyze → runs drift pipeline
│       └── health.py            # GET /health → connection checks
│
├── tools/                       # Layer 3: Python Scripts (atomic)
│   ├── verify_connections.py    # Phase 2: handshake all services
│   ├── ingest_files.py          # Parse .tf / .yaml files
│   ├── detect_drift.py          # deepdiff engine
│   ├── analyze_with_ai.py       # Ollama + Gemini router
│   ├── deliver_sheet.py         # Google Sheets writer
│   └── deliver_email.py         # Email sender
│
├── frontend/                    # React (Vite) — Glassmorphism UI
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css            # Glassmorphism design system
│       └── components/
│           ├── FileInput.jsx    # Paste / upload area
│           ├── DriftScore.jsx   # Score gauge widget
│           ├── DriftTable.jsx   # Per-event breakdown table
│           └── EmailBadge.jsx   # Email sent confirmation
│
├── credentials/                 # GCP service account (never committed)
│   └── gcp_service_account.json
└── .tmp/                        # Ephemeral workspace
    ├── logs/
    └── snapshots/
```

---

## 🛠️ Maintenance Log

| Date | Change | Author |
|------|--------|--------|
| 2026-04-09 | File initialized. Awaiting discovery. | System Pilot |
| 2026-04-09 | Discovery answers received. Full schema locked. Blueprint pending approval. | System Pilot |
