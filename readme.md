# Infra-Pilot 🛸

> AI-powered Terraform & Kubernetes drift pattern analyzer with glassmorphism UI.

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env
# → Fill in your API keys in .env

# 2. Install Python deps
pip install -r requirements.txt

# 3. Verify all connections
python tools/verify_connections.py

# 4. Start FastAPI backend (from project root)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 5. Start React frontend (new terminal)
cd frontend && npm run dev
# → Open http://localhost:5173
```

## Stack
- **Frontend:** React 18 + Vite + Glassmorphism CSS
- **Backend:** FastAPI + Uvicorn
- **AI:** Ollama (local) + Google Gemini (cloud fallback)
- **Delivery:** Google Sheets + Email (SMTP)
- **Protocol:** B.L.A.S.T. · Architecture: A.N.T. 3-Layer