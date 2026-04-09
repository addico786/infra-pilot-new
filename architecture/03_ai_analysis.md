# 📐 SOP-03: AI Analysis

## Tool: `tools/analyze_with_ai.py`

## Purpose
Enrich each `DriftEvent` with AI-generated analysis: a plain-English summary, a risk score (0–10), and an actionable recommendation.

## Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| `drift_events` | `list[DriftEvent]` | List of drift events from SOP-02 |
| `engine` | `str` | `"ollama"` (primary) or `"gemini"` (fallback) |

## Outputs
Each `DriftEvent.ai_analysis` is populated:
```json
{
  "summary": "The instance type was upgraded from t2.micro to t2.large, indicating a 4x CPU/RAM increase.",
  "risk_score": 6.5,
  "recommendation": "Verify this change is intentional and cost-budgeted. Tag this resource with a change ticket ID.",
  "model_used": "llama3"
}
```

## Logic

### Prompt Template
```
You are an expert cloud infrastructure reviewer.
Analyze this infrastructure drift event and return ONLY a valid JSON object.

Drift Event:
- File: {file_path}
- Resource: {resource_type}.{resource_name}
- Change Type: {drift_type}
- Field Changed: {changed_field}
- Old Value: {baseline_value}
- New Value: {current_value}

Return exactly this JSON shape:
{
  "summary": "one sentence plain English explanation",
  "risk_score": float between 0.0 and 10.0,
  "recommendation": "one actionable sentence"
}
```

### Routing Logic
1. **Try Ollama first:**
   - Check `OLLAMA_HOST` is reachable (`GET /api/tags`).
   - If reachable, use `ollama.chat(model=OLLAMA_DEFAULT_MODEL, ...)`.
   - Parse the JSON response.
2. **Fallback to Gemini:**
   - If Ollama is unreachable or times out, call Gemini API.
   - Use `google.generativeai.GenerativeModel("gemini-pro")`.
   - Parse the JSON response.
3. **Error fallback:**
   - If both fail after 3 retries, set `ai_analysis` to `{"summary": "Analysis unavailable", "risk_score": -1, "recommendation": "Manual review required", "model_used": "none"}`.

### Retry Policy
- Max retries: 3
- Backoff: 2s, 4s, 8s (exponential via `tenacity`)

## Edge Cases
- LLM returns invalid JSON → try to extract JSON with regex, else use error fallback
- Empty drift events list → return immediately, no API calls
- Rate limit hit → wait and retry with backoff

## Error Handling
- Log all AI calls (model, prompt, response, latency) to `.tmp/logs/ai_analysis.json`
