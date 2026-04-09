"""
tools/verify_connections.py
─────────────────────────────────────────────────────────────────
Phase 2 — Link: Handshake all external services.

Run: python tools/verify_connections.py

Checks:
  1. Ollama   → GET http://localhost:11434/api/tags
  2. Gemini   → List available models
  3. GitHub   → Verify token is valid
  4. Google Sheets → Open sheet by ID
  5. Email    → SMTP connection test (no email sent)

Outputs a colored status table to stdout.
Writes results to .tmp/logs/connections.json
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# ── Force UTF-8 output on Windows ──────────────────────────────
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Load .env ─────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# ── Ensure .tmp/logs exists ────────────────────────────────────
LOG_DIR = Path(".tmp/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── ANSI color helpers ─────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    return f"{GREEN}✅ {msg}{RESET}"
def fail(msg):  return f"{RED}❌ {msg}{RESET}"
def warn(msg):  return f"{YELLOW}⚠️  {msg}{RESET}"


# ══════════════════════════════════════════════════════════════
# 1. Ollama
# ══════════════════════════════════════════════════════════════
def check_ollama() -> dict:
    result = {"service": "Ollama", "status": "unknown", "detail": ""}
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        import httpx
        r = httpx.get(f"{host}/api/tags", timeout=5)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            result["status"] = "ok"
            result["detail"] = f"Running at {host} | Models: {', '.join(models) if models else 'none pulled yet'}"
        else:
            result["status"] = "error"
            result["detail"] = f"HTTP {r.status_code}"
    except Exception as e:
        result["status"] = "error"
        result["detail"] = f"Cannot reach {host} — Is Ollama running? ({e})"
    return result


# ══════════════════════════════════════════════════════════════
# 2. Google Gemini
# ══════════════════════════════════════════════════════════════
def check_gemini() -> dict:
    result = {"service": "Google Gemini", "status": "unknown", "detail": ""}
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "AIza_your_key_here":
        result["status"] = "missing"
        result["detail"] = "GEMINI_API_KEY not set in .env"
        return result
    try:
        import google.genai as genai
        client = genai.Client(api_key=api_key)
        models = [m.name for m in client.models.list()]
        gemini_models = [m for m in models if "gemini" in m.lower()][:3]
        result["status"] = "ok"
        result["detail"] = f"Key valid | Available: {', '.join(gemini_models)}"
    except ImportError:
        # Fallback to legacy SDK if google.genai not available
        try:
            import google.generativeai as genai  # noqa
            import warnings; warnings.filterwarnings("ignore")
            genai.configure(api_key=api_key)
            models = [m.name for m in genai.list_models()]
            gemini_models = [m for m in models if "gemini" in m.lower()][:3]
            result["status"] = "ok"
            result["detail"] = f"Key valid (legacy SDK) | Available: {', '.join(gemini_models)}"
        except Exception as e:
            result["status"] = "error"
            result["detail"] = str(e)
    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)
    return result


# ══════════════════════════════════════════════════════════════
# 3. GitHub
# ══════════════════════════════════════════════════════════════
def check_github() -> dict:
    result = {"service": "GitHub API", "status": "unknown", "detail": ""}
    token = os.getenv("GITHUB_TOKEN", "")
    if not token or token == "ghp_your_token_here":
        result["status"] = "missing"
        result["detail"] = "GITHUB_TOKEN not set in .env"
        return result
    try:
        from github import Github, Auth
        auth = Auth.Token(token)
        g = Github(auth=auth)
        user = g.get_user()
        # PyGithub v2: rate_limit returns a dict-like object
        rl = g.get_rate_limit()
        remaining = getattr(getattr(rl, 'core', None), 'remaining', None)
        if remaining is None:
            remaining = "N/A"
        result["status"] = "ok"
        result["detail"] = f"Authenticated as: {user.login} | Rate limit remaining: {remaining}"
        g.close()
    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)
    return result


# ══════════════════════════════════════════════════════════════
# 4. Google Sheets
# ══════════════════════════════════════════════════════════════
def check_sheets() -> dict:
    result = {"service": "Google Sheets", "status": "unknown", "detail": ""}
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./credentials/gcp_service_account.json")
    sheet_id   = os.getenv("GOOGLE_SHEET_ID", "")
    if not Path(creds_path).exists():
        result["status"] = "missing"
        result["detail"] = f"Service account JSON not found at: {creds_path}"
        return result
    if not sheet_id or sheet_id == "your_sheet_id_here":
        result["status"] = "missing"
        result["detail"] = "GOOGLE_SHEET_ID not set in .env"
        return result
    try:
        import gspread
        gc = gspread.service_account(filename=creds_path)
        sh = gc.open_by_key(sheet_id)
        result["status"] = "ok"
        result["detail"] = f"Sheet opened: '{sh.title}' | URL: {sh.url}"
    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)
    return result


# ══════════════════════════════════════════════════════════════
# 5. Email (SMTP)
# ══════════════════════════════════════════════════════════════
def check_email() -> dict:
    result = {"service": "Email (SMTP)", "status": "unknown", "detail": ""}
    host     = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port     = int(os.getenv("SMTP_PORT", 587))
    user     = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    if not user or not password or user == "your_email@gmail.com":
        result["status"] = "missing"
        result["detail"] = "SMTP_USER or SMTP_PASSWORD not set in .env"
        return result
    try:
        import smtplib
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(user, password)
        result["status"] = "ok"
        result["detail"] = f"SMTP connection verified ({host}:{port}) as {user}"
    except Exception as e:
        result["status"] = "error"
        result["detail"] = str(e)
    return result


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════
def main():
    print(f"\n{BOLD}{CYAN}======================================{RESET}")
    print(f"{BOLD}{CYAN}  Infra-Pilot -- Connection Verifier{RESET}")
    print(f"{BOLD}{CYAN}  Phase 2 -- Link Handshake{RESET}")
    print(f"{BOLD}{CYAN}======================================{RESET}\n")

    checks = [
        check_ollama,
        check_gemini,
        check_github,
        check_sheets,
        check_email,
    ]

    results = []
    for check_fn in checks:
        print(f"  Checking {check_fn.__name__.replace('check_', '').replace('_', ' ').title()}...", end=" ", flush=True)
        t0 = time.time()
        res = check_fn()
        elapsed = round(time.time() - t0, 2)
        res["elapsed_s"] = elapsed
        res["checked_at"] = datetime.now(tz=__import__('datetime').timezone.utc).isoformat()
        results.append(res)

        if res["status"] == "ok":
            print(ok(res["detail"]))
        elif res["status"] == "missing":
            print(warn(res["detail"]))
        else:
            print(fail(res["detail"]))

    # ── Summary ──────────────────────────────────────────────
    ok_count      = sum(1 for r in results if r["status"] == "ok")
    missing_count = sum(1 for r in results if r["status"] == "missing")
    err_count     = sum(1 for r in results if r["status"] == "error")
    total         = len(results)

    print(f"\n{BOLD}{'─'*40}{RESET}")
    print(f"  {GREEN}[OK]     Ready:  {ok_count}/{total}{RESET}")
    if missing_count:
        print(f"  {YELLOW}[WARN]  Missing: {missing_count}/{total} -- fill in .env{RESET}")
    if err_count:
        print(f"  {RED}[ERROR] Errors:  {err_count}/{total} -- see details above{RESET}")
    print(f"{BOLD}{'─'*40}{RESET}\n")

    # ── Write log ────────────────────────────────────────────
    log_path = LOG_DIR / "connections.json"
    with open(log_path, "w") as f:
        json.dump({"timestamp": datetime.now(tz=__import__('datetime').timezone.utc).isoformat(), "results": results}, f, indent=2)
    print(f"  📄 Full results written to: {log_path}\n")

    # Exit with error code if any service is in error state
    if err_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
