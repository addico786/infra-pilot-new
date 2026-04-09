# 📐 SOP-02: Drift Detection

## Tool: `tools/detect_drift.py`

## Purpose
Compare a current file's parsed resources against a baseline snapshot and produce a list of `DriftEvent` objects.

## Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| `current` | `dict` | Parsed current resources (from SOP-01) |
| `baseline` | `dict` | Parsed baseline resources (from prior commit or empty `{}` for new baseline) |
| `file_path` | `str` | File path label |
| `file_type` | `str` | `"terraform"` or `"kubernetes"` |

## Outputs
```json
[
  {
    "event_id": "uuid",
    "run_id": "uuid",
    "file_path": "main.tf",
    "file_type": "terraform",
    "resource_type": "aws_instance",
    "resource_name": "web",
    "drift_type": "modified",
    "severity": "high",
    "changed_field": "instance_type",
    "baseline_value": "t2.micro",
    "current_value": "t2.large",
    "ai_analysis": null
  }
]
```

## Logic
1. Use `deepdiff.DeepDiff(baseline, current, ignore_order=True)` to compute structural differences.
2. Parse the DeepDiff result into typed `DriftEvent` objects:
   - `dictionary_item_added` → `drift_type: "added"`
   - `dictionary_item_removed` → `drift_type: "removed"`
   - `values_changed` → `drift_type: "modified"`
3. **Severity assignment:**
   | Condition | Severity |
   |-----------|---------|
   | Resource entirely removed | `critical` |
   | Security-sensitive field changed (e.g., `port`, `policy`, `role`) | `high` |
   | Instance sizing changed | `medium` |
   | Tag or label changed | `low` |
   | Resource added | `low` |
4. Strip Kubernetes noise fields before diffing: `resourceVersion`, `uid`, `managedFields`, `creationTimestamp`, `generation`.

## Edge Cases
- Empty baseline → all resources are `drift_type: "added"` with severity `low`
- Identical files → return empty list `[]`
- Nested arrays in K8s (e.g., `env`, `args`) → compare element-by-element, not position-by-position

## Error Handling
- Log all events to `.tmp/logs/drift.json`
- If DeepDiff raises, catch and log — return empty list with error flag
