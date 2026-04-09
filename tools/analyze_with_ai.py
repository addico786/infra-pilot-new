"""
tools/analyze_with_ai.py
─────────────────────────────────────────────────────────────────
Layer 3 — Tool | SOP-03: AI Analysis

Routes each DriftEvent through the AI engine:
  1. Try Ollama first (local — Llama3 / WizardLM / Gemma4)
  2. Fallback to Google Gemini (cloud)
  3. If both fail → placeholder with manual review flag

Uses tenacity for retry with exponential backoff.

Usage:
    from tools.analyze_with_ai import analyze_events
    enriched_events = analyze_events(drift_events)
"""

import os
import re
import json
import logging
from datetime import datetime, timezone

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = logging.getLogger(__name__)

# ── Prompt template ────────────────────────────────────────────
PROMPT_TEMPLATE = """You are an expert cloud infrastructure security engineer. Analyze this drift event.
Return ONLY a raw JSON object. No markdown, no code fences, no explanation. Start your response with {{ and end with }}.

Drift Event:
- Resource: {resource_type}.{resource_name} in {file_path}
- Change Type: {drift_type}
- Field: {changed_field}
- Before: {baseline_value}
- After: {current_value}
- Severity: {severity}

JSON output (start with {{, end with }}):
{{
  "summary": "one sentence explaining what changed and why it matters",
  "risk_score": 5.0,
  "recommendation": "one actionable sentence for the operator"
}}"""

# ── Error fallback ─────────────────────────────────────────────
def _error_analysis(reason: str) -> dict:
    return {
        "summary":        f"AI analysis unavailable: {reason}",
        "risk_score":     -1.0,
        "recommendation": "Manual review required — AI engine could not process this event.",
        "model_used":     "none",
    }


# ── JSON extraction ────────────────────────────────────────────
def _extract_json(text: str) -> dict | None:
    """Extract JSON from LLM output, handling markdown code fences and surrounding text."""
    if not text:
        return None

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    cleaned = re.sub(r'```(?:json)?\s*', '', text)
    cleaned = re.sub(r'```', '', cleaned).strip()

    # Direct parse of the whole cleaned string
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Find first {...} block in the text
    match = re.search(r'\{[^{}]*"summary"[^{}]*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    # Broader search for any {...} block
    match = re.search(r'\{[\s\S]*?\}', cleaned)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    return None


def _validate_analysis(raw: dict) -> dict:
    """Ensure the parsed JSON has the required shape."""
    return {
        "summary":        str(raw.get("summary", "No summary provided.")),
        "risk_score":     float(raw.get("risk_score", 5.0)),
        "recommendation": str(raw.get("recommendation", "Review this change manually.")),
    }


# ── Ollama (local) ─────────────────────────────────────────────
def _ollama_reachable() -> bool:
    try:
        import httpx
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        r = httpx.get(f"{host}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _call_ollama(prompt: str, model: str) -> str:
    import ollama
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0, "num_predict": 512},
    )
    return response["message"]["content"]


# ── Gemini (cloud) ─────────────────────────────────────────────
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    try:
        import google.genai as genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        err_str = str(e)
        # Don't retry on quota/auth errors
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "401" in err_str:
            raise RuntimeError(f"Gemini quota/auth error (non-retryable): {err_str[:120]}")
        try:
            # Fallback to legacy SDK
            import warnings
            warnings.filterwarnings("ignore")
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=api_key)
            model_obj = genai_legacy.GenerativeModel("gemini-2.0-flash")
            response = model_obj.generate_content(prompt)
            return response.text
        except Exception as e2:
            raise RuntimeError(f"Both Gemini SDKs failed: {e2}") from e2


# ── Single event analysis ──────────────────────────────────────
def _analyze_one(event: dict, model_override: str | None = None) -> dict:
    """Run AI analysis for a single drift event. Returns the ai_analysis dict."""
    prompt = PROMPT_TEMPLATE.format(
        file_path      = event.get("file_path", "unknown"),
        resource_type  = event.get("resource_type", "unknown"),
        resource_name  = event.get("resource_name", "unknown"),
        drift_type     = event.get("drift_type", "unknown"),
        changed_field  = event.get("changed_field", "unknown"),
        baseline_value = event.get("baseline_value") or "N/A",
        current_value  = event.get("current_value") or "N/A",
        severity       = event.get("severity", "unknown"),
    )

    # ── Forced model override ────────────────────────────────
    if model_override and model_override.startswith("gemini"):
        try:
            raw_text = _call_gemini(prompt)
            parsed   = _extract_json(raw_text)
            if parsed:
                result = _validate_analysis(parsed)
                result["model_used"] = "gemini-2.0-flash"
                return result
        except Exception as e:
            log.warning("Gemini(forced) failed: %s", e)
        return _error_analysis("Gemini forced but failed")

    if model_override and model_override.startswith("ollama:"):
        forced_model = model_override.split("ollama:", 1)[1]
        try:
            raw_text = _call_ollama(prompt, forced_model)
            parsed   = _extract_json(raw_text)
            if parsed:
                result = _validate_analysis(parsed)
                result["model_used"] = forced_model
                return result
        except Exception as e:
            log.warning("Ollama(forced:%s) failed: %s", forced_model, e)
        return _error_analysis(f"Ollama model {forced_model} forced but failed")

    # ── Auto routing: Ollama first ───────────────────────────
    model   = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3")
    if _ollama_reachable():
        try:
            raw_text = _call_ollama(prompt, model)
            parsed   = _extract_json(raw_text)
            if parsed:
                result = _validate_analysis(parsed)
                result["model_used"] = model
                log.debug("Ollama analysis OK for %s.%s", event.get("resource_type"), event.get("resource_name"))
                return result
            else:
                log.warning("Ollama returned non-JSON response, falling back to Gemini")
        except Exception as e:
            log.warning("Ollama call failed (%s), falling back to Gemini", e)

    # ── Fallback: Gemini ─────────────────────────────────────
    try:
        raw_text = _call_gemini(prompt)
        parsed   = _extract_json(raw_text)
        if parsed:
            result = _validate_analysis(parsed)
            result["model_used"] = "gemini-2.0-flash"
            log.debug("Gemini analysis OK for %s.%s", event.get("resource_type"), event.get("resource_name"))
            return result
        else:
            log.warning("Gemini returned non-JSON response")
    except Exception as e:
        log.warning("Gemini call also failed: %s", e)

    # ── Both failed ──────────────────────────────────────────
    return _error_analysis("Both Ollama and Gemini unavailable or returned invalid JSON")


# ── Public API ─────────────────────────────────────────────────
def analyze_events(drift_events: list, model_override: str | None = None) -> list:
    """
    Enrich each DriftEvent with AI analysis.

    Args:
        drift_events:   List of DriftEvent dicts from detect_drift.
        model_override: Force a specific model. Examples:
                        - "ollama:llama3"        → use llama3 via Ollama
                        - "ollama:wizardlm2:7b"  → use wizardlm2 via Ollama
                        - "gemini"               → force Gemini cloud
                        - None (default)         → auto (Ollama → Gemini fallback)

    Returns:
        Same list with each event's 'ai_analysis' field populated.
    """
    if not drift_events:
        return drift_events

    enriched = []
    for i, event in enumerate(drift_events):
        log.info(
            "Analyzing event %d/%d: %s.%s (%s) [model=%s]",
            i + 1, len(drift_events),
            event.get("resource_type"), event.get("resource_name"),
            event.get("drift_type"),
            model_override or "auto",
        )
        analysis = _analyze_one(event, model_override=model_override)
        enriched_event = {**event, "ai_analysis": analysis}
        enriched.append(enriched_event)

    return enriched
