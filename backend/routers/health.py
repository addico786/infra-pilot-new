"""
backend/routers/health.py
─────────────────────────────────────────────────────────────────
GET /health — Returns connection status for all services.
Used by the frontend status LED indicator.
"""

import os
import httpx
from fastapi import APIRouter
from pathlib import Path

router = APIRouter()


@router.get("/health")
async def health_check():
    """Check connectivity to all external services."""
    status = {}

    # Ollama
    try:
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{host}/api/tags")
        models = [m["name"] for m in r.json().get("models", [])]
        status["ollama"] = {"ok": True, "models": models}
    except Exception as e:
        status["ollama"] = {"ok": False, "error": str(e)}

    # Gemini key present
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    status["gemini"] = {"ok": bool(gemini_key and gemini_key != "AIza_your_key_here")}

    # GitHub token present
    gh_token = os.getenv("GITHUB_TOKEN", "")
    status["github"] = {"ok": bool(gh_token and gh_token != "ghp_your_token_here")}

    # GCP credentials file present
    creds_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "./credentials/gcp_service_account.json")
    status["google_sheets"] = {"ok": Path(creds_path).exists()}

    # SMTP configured
    smtp_user = os.getenv("SMTP_USER", "")
    status["email"] = {"ok": bool(smtp_user and smtp_user != "your_email@gmail.com")}

    all_ok = all(v.get("ok", False) for v in status.values())
    return {"overall": "ok" if all_ok else "partial", "services": status}
