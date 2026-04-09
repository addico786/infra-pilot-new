"""
tools/detect_drift.py
─────────────────────────────────────────────────────────────────
Layer 3 — Tool | SOP-02: Drift Detection

Compares current vs baseline resource dictionaries using deepdiff
and produces a typed list of DriftEvent objects.

Usage:
    from tools.detect_drift import detect_drift
    events = detect_drift(current={...}, baseline={}, file_path="main.tf",
                          file_type="terraform", run_id="uuid")
"""

import uuid
import logging
from deepdiff import DeepDiff

log = logging.getLogger(__name__)

# ── Security-sensitive field patterns ──────────────────────────
SECURITY_FIELDS = {
    "port", "ports", "cidr", "cidr_blocks", "ingress", "egress",
    "policy", "role", "iam", "permission", "access", "secret",
    "key", "password", "token", "certificate", "tls", "ssl",
    "security_group", "firewall", "acl", "public", "expose",
    "privileged", "allow", "deny", "encryption", "kms",
}

SIZING_FIELDS = {
    "instance_type", "machine_type", "size", "tier",
    "replicas", "min_replicas", "max_replicas",
    "cpu", "memory", "limits", "requests", "storage",
}


# ── Severity logic ─────────────────────────────────────────────

def _classify_severity(drift_type: str, changed_field: str, resource_type: str) -> str:
    """
    Deterministically assign severity based on drift type and field name.
    No AI — this is pure rule-based logic.
    """
    field_lower = changed_field.lower()

    if drift_type == "removed":
        return "critical"

    if any(sf in field_lower for sf in SECURITY_FIELDS):
        return "high"

    if any(sf in field_lower for sf in SIZING_FIELDS):
        return "medium"

    if drift_type == "added":
        return "low"

    return "low"


# ── DeepDiff result → DriftEvent ──────────────────────────────

def _parse_deepdiff(dd: DeepDiff, file_path: str, file_type: str, run_id: str) -> list:
    """Convert a DeepDiff result into a flat list of DriftEvent dicts."""
    events = []

    def _extract_key_parts(path_str: str):
        """
        Parse a DeepDiff path like "root['aws_instance.web']['instance_type']"
        into (resource_key, field).
        """
        import re
        parts = re.findall(r"\['([^']+)'\]", path_str)
        if len(parts) >= 2:
            resource_key = parts[0]
            field        = ".".join(parts[1:])
        elif len(parts) == 1:
            resource_key = parts[0]
            field        = "(root)"
        else:
            resource_key = path_str
            field        = "(unknown)"
        return resource_key, field

    def _split_resource_key(resource_key: str):
        """Split 'aws_instance.web' → ('aws_instance', 'web')."""
        parts = resource_key.split(".", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return resource_key, resource_key

    def _make_event(drift_type, resource_key, field, baseline_val=None, current_val=None):
        rtype, rname = _split_resource_key(resource_key)
        severity = _classify_severity(drift_type, field, rtype)
        return {
            "event_id":       str(uuid.uuid4()),
            "run_id":         run_id,
            "file_path":      file_path,
            "file_type":      file_type,
            "resource_type":  rtype,
            "resource_name":  rname,
            "drift_type":     drift_type,
            "severity":       severity,
            "changed_field":  field,
            "baseline_value": str(baseline_val) if baseline_val is not None else None,
            "current_value":  str(current_val) if current_val is not None else None,
            "ai_analysis":    None,
        }

    # values_changed → "modified"
    for path, change in dd.get("values_changed", {}).items():
        resource_key, field = _extract_key_parts(str(path))
        events.append(_make_event(
            "modified", resource_key, field,
            change.get("old_value"), change.get("new_value"),
        ))

    # dictionary_item_added → "added"
    for path in dd.get("dictionary_item_added", set()):
        resource_key, field = _extract_key_parts(str(path))
        events.append(_make_event("added", resource_key, field, None, "(new)"))

    # dictionary_item_removed → "removed"
    for path in dd.get("dictionary_item_removed", set()):
        resource_key, field = _extract_key_parts(str(path))
        events.append(_make_event("removed", resource_key, field, "(was present)", None))

    # type_changes → treat as "modified"
    for path, change in dd.get("type_changes", {}).items():
        resource_key, field = _extract_key_parts(str(path))
        events.append(_make_event(
            "modified", resource_key, field,
            f"{change.get('old_value')} ({change.get('old_type', '').__name__ if change.get('old_type') else ''})",
            f"{change.get('new_value')} ({change.get('new_type', '').__name__ if change.get('new_type') else ''})",
        ))

    # iterable_item_added / removed → "added" / "removed"
    for path in dd.get("iterable_item_added", {}).keys():
        resource_key, field = _extract_key_parts(str(path))
        events.append(_make_event("added", resource_key, field, None, "(list item added)"))

    for path in dd.get("iterable_item_removed", {}).keys():
        resource_key, field = _extract_key_parts(str(path))
        events.append(_make_event("removed", resource_key, field, "(list item)", None))

    return events


# ── Public API ─────────────────────────────────────────────────

def detect_drift(
    current:   dict,
    baseline:  dict,
    file_path: str = "unknown",
    file_type: str = "terraform",
    run_id:    str = None,
) -> list:
    """
    Compare current vs baseline resource dicts and return DriftEvent list.

    Args:
        current:   Parsed current resources  (from ingest_files.ingest).
        baseline:  Parsed baseline resources (empty {} = new baseline).
        file_path: File label for events.
        file_type: "terraform" | "kubernetes"
        run_id:    UUID for this analysis run.

    Returns:
        List of DriftEvent dicts (ai_analysis=None — filled by analyze_with_ai).
    """
    if run_id is None:
        import uuid
        run_id = str(uuid.uuid4())

    # Identical → no drift
    if current == baseline:
        log.info("No drift detected in %s", file_path)
        return []

    # Empty baseline → every resource is "added"
    if not baseline:
        events = []
        for resource_key, attrs in current.items():
            rtype, rname = resource_key.split(".", 1) if "." in resource_key else (resource_key, resource_key)
            events.append({
                "event_id":       str(uuid.uuid4()),
                "run_id":         run_id,
                "file_path":      file_path,
                "file_type":      file_type,
                "resource_type":  rtype,
                "resource_name":  rname,
                "drift_type":     "added",
                "severity":       "low",
                "changed_field":  "(entire resource)",
                "baseline_value": None,
                "current_value":  "(new resource)",
                "ai_analysis":    None,
            })
        return events

    # Standard deepdiff
    try:
        dd = DeepDiff(baseline, current, ignore_order=True, verbose_level=2)
        events = _parse_deepdiff(dd, file_path, file_type, run_id)
        log.info("Detected %d drift events in %s", len(events), file_path)
        return events
    except Exception as e:
        log.error("DeepDiff error for %s: %s", file_path, e)
        return []
