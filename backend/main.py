"""
backend/main.py
─────────────────────────────────────────────────────────────────
Infra-Pilot FastAPI Backend
Bridges the React frontend ↔ Python tool pipeline.

Start: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from backend.routers import analyze, health

app = FastAPI(
    title="Infra-Pilot API",
    description="AI-powered Terraform & Kubernetes drift analyzer",
    version="1.0.0",
)

# ── CORS (allow React dev server) ─────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(health.router, tags=["Health"])
app.include_router(analyze.router, tags=["Analyze"])


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "Infra-Pilot API",
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
    }
