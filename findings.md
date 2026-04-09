# 🔍 findings.md — Research & Discoveries Log

> Stores discoveries, constraints, API quirks, and research notes.
> Updated throughout the project lifecycle. Never delete entries — only annotate.

---

## 📌 Project Context

- **Project:** Infra-Pilot — AI-powered Terraform & Kubernetes drift analyzer
- **Initialized:** 2026-04-09
- **Status:** ✅ Discovery complete. Schema locked. Blueprint pending approval.

---

## 🧠 Discovery Findings

> To be populated after Phase 1 — Blueprint discovery questions are answered.

### 1. North Star
- Build a system that accepts Terraform (`.tf`) or Kubernetes (`.yaml/.yml`) files
- Analyzes **drift patterns** — how those files change over time compared to a historical baseline
- Produces a structured AI-enriched report per drift event
- Long-term use: track infra evolution and flag risk proactively

### 2. Integration Notes
- **Google Gemini API** (free tier) — cloud LLM for analysis
- **Ollama** — local LLM runtime; user has Llama 3, WizardLM, Gemma 4 installed locally
- **GitHub API** — primary data source (repos + commit history)
- **Google Sheets API** — primary payload delivery
- **Email (SMTP)** — secondary payload delivery
- ⚠️ Ollama is already installed on the user's PC at `localhost:11434` (default port)
- API keys for Gemini/GitHub/GSheets still need to be configured by user

### 3. Data Source Notes
- **Primary:** GitHub repositories (public or private with PAT)
- **Secondary:** Local files on the user's desktop / local paths
- Baseline for drift = prior Git commit(s) — configurable lookback depth
- Files of interest: `*.tf`, `*.yaml`, `*.yml`

### 4. Delivery / Payload Notes
- **Primary:** Google Sheets — one sheet per run, drift events as rows
- **Secondary:** Email summary with key stats and link to sheet
- Format must be professional and organized (not raw JSON)

### 5. Behavioral Constraints
- Follow best organization practices (clean code, separation of concerns)
- System is **read-only** — never modifies source files
- AI results are advisory labels, not commands
- Retry 3x with backoff before failing any external call

---

## 🔬 Research Log

> External research, GitHub repos, libraries, and references found during Blueprint phase.

| Date | Source | Finding | Relevance |
|------|--------|---------|-----------|
| 2026-04-09 | — | Project initialized | Setup |
| 2026-04-09 | devgenius.io / spacelift.io | `terraform plan -detailed-exitcode` is the industry standard for drift detection. Exit code 2 = drift. | Core detection strategy |
| 2026-04-09 | kubernetes.io / dev.to | `deepdiff` Python library ideal for comparing Kubernetes manifest dicts. Must strip noise fields (`resourceVersion`, `uid`, `managedFields`). | K8s drift logic |
| 2026-04-09 | ollama.com / realpython.com | `ollama` pip package provides `ollama.chat()` API. Needs `OLLAMA_HOST` pointing to `localhost:11434`. Stream support available. | AI engine layer |
| 2026-04-09 | gspread.org / dev.to | `gspread` v6.0+ uses named args for `.update()`. Requires Google Sheets + Drive API enabled + Service Account JSON. Rate limit: 300 req/60s. | Delivery layer |
| 2026-04-09 | github.com | `gitpython` library for cloning and walking Git commit history programmatically. | Git ingestion layer |

---

## ⚠️ Known Constraints & Gotchas

> Populated during Link and Architect phases.

| Component | Constraint | Discovered On |
|-----------|-----------|---------------|
| Google Sheets API | Max 300 requests per 60 seconds per project | 2026-04-09 |
| gspread v6.0+ | `.update()` must use named args: `range_name=`, `values=` | 2026-04-09 |
| Kubernetes YAML diff | Must strip noise fields before diffing or get false positives | 2026-04-09 |
| Ollama | Requires local daemon running (`ollama serve`) on port 11434 | 2026-04-09 |
| Gemini free tier | Has per-minute and per-day token limits — implement backoff | 2026-04-09 |
| `credentials.json` | Must NEVER be committed to Git — add to `.gitignore` | 2026-04-09 |

---

## 🐛 Error Log

> When errors occur, document them here alongside the fix. Prevents repeat failures.

| Date | Tool/Script | Error | Fix Applied |
|------|-------------|-------|-------------|
| — | — | — | — |
