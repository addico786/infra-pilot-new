# 📐 SOP-05: Frontend (React + Glassmorphism UI)

## Stack: React 18 + Vite + Axios

## Purpose
Provide a stunning, glassmorphism-styled web UI where users paste infrastructure files, view the instant drift score, and see a full breakdown — all without leaving the browser.

---

## Page Layout: Single Page Application

```
┌────────────────────────────────────────────────┐
│  🧭 Infra-Pilot                    [Status LED]│  ← Navbar (glass)
├────────────────────────────────────────────────┤
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │  📄 Paste your .tf or .yaml file here   │  │  ← FileInput (glass card)
│  │  [textarea]                              │  │
│  │                    [Analyze Drift ▶]     │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  ┌─────────────┐  ┌──────────────────────────┐ │
│  │ DRIFT SCORE │  │  SEVERITY BREAKDOWN       │ │  ← DriftScore + bars
│  │   [ 7.4 ]   │  │  🔴 Critical: 2           │ │
│  │  ▓▓▓▓▓░░░   │  │  🟠 High: 5              │ │
│  └─────────────┘  │  🟡 Medium: 3             │ │
│                   │  🟢 Low: 1               │ │
│                   └──────────────────────────┘ │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │  📊 Drift Events Table                   │  │  ← DriftTable
│  │  Resource | Type | Severity | AI Summary │  │
│  │  ...      | ...  | 🔴 HIGH  | ...        │  │
│  └──────────────────────────────────────────┘  │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │  ✉️ Report emailed to: you@gmail.com ✅  │  │  ← EmailBadge
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

---

## Design System

### Color Palette (Dark Mode Glassmorphism)
- **Background:** Deep space gradient `#0a0a1a → #1a0a2e → #0a1a2e`
- **Glass cards:** `rgba(255,255,255,0.05)` with `backdrop-filter: blur(20px)`
- **Glass border:** `1px solid rgba(255,255,255,0.1)`
- **Accent — Critical:** `#ff4757`
- **Accent — High:** `#ff6b35`
- **Accent — Medium:** `#ffa502`
- **Accent — Low:** `#2ed573`
- **Score gauge color:** transitions from green → amber → red based on score
- **Font:** `Inter` (Google Fonts)

### Animations
- Drift score gauge: animated fill on load
- Severity bars: slide-in with staggered delays
- Table rows: fade-in one by one
- Analyze button: pulse glow on hover
- Loading state: orbital spinner with glass card

---

## API Contract (Frontend ↔ Backend)

### Request
```
POST http://localhost:8000/analyze
Content-Type: application/json

{
  "content": "<raw file content string>",
  "file_name": "main.tf",
  "email_recipients": ["user@gmail.com"]
}
```

### Response
```json
{
  "run_id": "uuid",
  "drift_score": 7.4,
  "summary": { "total": 11, "critical": 2, "high": 5, "medium": 3, "low": 1 },
  "drift_events": [...],
  "sheet_url": "https://docs.google.com/...",
  "email_sent": true
}
```

---

## Component Rules
- All API calls through Axios in `src/api/analyze.js`
- Loading, error, and success states handled in `App.jsx`
- No inline styles — all CSS in `index.css` (CSS custom properties)
- All interactive elements have unique `id` attributes for testability
