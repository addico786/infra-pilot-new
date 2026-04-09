"""
tools/ingest_files.py
─────────────────────────────────────────────────────────────────
Layer 3 — Tool | SOP-01: File Ingestion

Parses Terraform (.tf) or Kubernetes (.yaml/.yml) content
into a normalized flat resource dictionary.

Usage:
    from tools.ingest_files import ingest
    result = ingest(content="...", file_path="main.tf", file_type="auto")
"""

import re
import yaml
import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────

K8S_NOISE_FIELDS = {
    "resourceVersion", "uid", "managedFields", "creationTimestamp",
    "generation", "selfLink", "annotations", "finalizers",
}


def _auto_detect(content: str) -> str:
    """Detect file type from content heuristics."""
    stripped = content.strip()
    if re.search(r'\bresource\s+"', stripped) or re.search(r'\bvariable\s+"', stripped):
        return "terraform"
    if "apiVersion:" in stripped or "kind:" in stripped:
        return "kubernetes"
    # Secondary TF checks
    if re.search(r'\bprovider\s+"', stripped) or re.search(r'\bmodule\s+"', stripped):
        return "terraform"
    return "terraform"  # safe default


def _strip_noise(obj, noise_fields=K8S_NOISE_FIELDS):
    """Recursively remove Kubernetes metadata noise to prevent false-positive diffs."""
    if isinstance(obj, dict):
        return {
            k: _strip_noise(v, noise_fields)
            for k, v in obj.items()
            if k not in noise_fields
        }
    if isinstance(obj, list):
        return [_strip_noise(i, noise_fields) for i in obj]
    return obj


# ── Terraform Parser ───────────────────────────────────────────

def _preprocess_hcl(content: str) -> str:
    """
    Fix common HCL2 syntax issues that cause parse failures.
    Runs BEFORE hcl2.load so the parser sees valid input.
    """
    import re

    # Fix: resource aws_instance my_res { → resource "aws_instance" "my_res" {
    # Handles: resource / data / module with two unquoted identifiers
    content = re.sub(
        r'^(resource|data)\s+([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_\-]*)\s*\{',
        r'\1 "\2" "\3" {',
        content,
        flags=re.MULTILINE,
    )

    # Fix: resource "aws_instance" my_res { → resource "aws_instance" "my_res" {
    # (type already quoted but name is not)
    content = re.sub(
        r'^(resource|data)\s+"([^"]+)"\s+([A-Za-z_][A-Za-z0-9_\-]*)\s*\{',
        r'\1 "\2" "\3" {',
        content,
        flags=re.MULTILINE,
    )

    # Fix: variable my_var { → variable "my_var" {
    # Fix: output my_out { → output "my_out" {
    content = re.sub(
        r'^(variable|output|module|locals|provider)\s+([A-Za-z_][A-Za-z0-9_\-]*)\s*\{',
        r'\1 "\2" {',
        content,
        flags=re.MULTILINE,
    )

    return content


def _parse_terraform(content: str) -> tuple[dict, list]:
    """
    Parse HCL2 Terraform content into a flat resource dict.
    Returns (resources, errors).

    python-hcl2 v4+ returns:
      {"resource": [{"aws_instance": {"web": {...}}}, ...]}
    """
    resources = {}
    errors = []
    try:
        import hcl2
        import io
        clean = _preprocess_hcl(content)
        parsed = hcl2.load(io.StringIO(clean))

        def _flatten(val):
            """hcl2 wraps single values in lists — unwrap them."""
            if isinstance(val, list) and len(val) == 1:
                return _flatten(val[0])
            if isinstance(val, dict):
                return {k: _flatten(v) for k, v in val.items()}
            return val

        def _iter_blocks(block_list):
            """
            Iterate over hcl2 block lists:
              block_list = [{"type_name": {"resource_name": {...}}}, ...]
            Yields (type_name, resource_name, config_dict)
            """
            if not isinstance(block_list, list):
                return
            for item in block_list:
                if not isinstance(item, dict):
                    continue
                for type_name, instances in item.items():
                    if isinstance(instances, dict):
                        for res_name, config in instances.items():
                            yield type_name, res_name, _flatten(config)
                    elif isinstance(instances, list):
                        for sub in instances:
                            if isinstance(sub, dict):
                                for res_name, config in sub.items():
                                    yield type_name, res_name, _flatten(config)

        # resource blocks
        for rtype, rname, config in _iter_blocks(parsed.get("resource", [])):
            resources[f"{rtype}.{rname}"] = config

        # variable blocks
        for _, vname, config in _iter_blocks(parsed.get("variable", [])):
            resources[f"variable.{vname}"] = config

        # output blocks
        for _, oname, config in _iter_blocks(parsed.get("output", [])):
            resources[f"output.{oname}"] = config

        # locals blocks (flat dict per block)
        for loc_block in parsed.get("locals", []):
            if isinstance(loc_block, dict):
                for loc_name, loc_val in loc_block.items():
                    resources[f"local.{loc_name}"] = {"value": loc_val}

    except Exception as e:
        errors.append(f"Terraform parse error: {e}")
        log.warning("Terraform parse error: %s", e)

    return resources, errors



# ── Kubernetes Parser ──────────────────────────────────────────

def _parse_kubernetes(content: str) -> tuple[dict, list]:
    """
    Parse multi-document YAML (separated by ---) into a flat resource dict.
    Returns (resources, errors).
    """
    resources = {}
    errors = []
    try:
        docs = list(yaml.safe_load_all(content))
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            kind     = doc.get("kind", "Unknown")
            name     = doc.get("metadata", {}).get("name", "unnamed")
            ns       = doc.get("metadata", {}).get("namespace", "default")
            key      = f"{kind}/{ns}/{name}"
            cleaned  = _strip_noise(doc)
            resources[key] = cleaned
    except yaml.YAMLError as e:
        errors.append(f"Kubernetes YAML parse error: {e}")
        log.warning("K8s parse error: %s", e)
    except Exception as e:
        errors.append(f"Kubernetes unexpected error: {e}")

    return resources, errors


# ── Public API ─────────────────────────────────────────────────

def ingest(content: str, file_path: str = "unknown", file_type: str = "auto") -> dict:
    """
    Parse infrastructure file content into a normalized resource dict.

    Args:
        content:   Raw file text.
        file_path: Logical file name (for labeling only).
        file_type: "terraform" | "kubernetes" | "auto"

    Returns:
        {
            "file_path":    str,
            "file_type":    "terraform" | "kubernetes",
            "resources":    dict,   # {resource_key: attribute_dict}
            "resource_count": int,
            "parse_errors": list,
        }
    """
    if not content or not content.strip():
        return {
            "file_path":      file_path,
            "file_type":      file_type if file_type != "auto" else "unknown",
            "resources":      {},
            "resource_count": 0,
            "parse_errors":   ["Empty file — no content to parse."],
        }

    # Auto-detect if needed
    resolved_type = file_type
    if file_type == "auto":
        resolved_type = _auto_detect(content)

    # Parse
    if resolved_type == "terraform":
        resources, errors = _parse_terraform(content)
    elif resolved_type == "kubernetes":
        resources, errors = _parse_kubernetes(content)
    else:
        resources, errors = {}, [f"Unsupported file_type: '{file_type}'"]

    # Soft-handle: if parse failed but we got some resources, continue with a warning
    # Only hard-fail if we got zero resources AND there were errors
    parse_warnings = errors if resources else []
    hard_errors    = errors if not resources else []

    return {
        "file_path":      file_path,
        "file_type":      resolved_type,
        "resources":      resources,
        "resource_count": len(resources),
        "parse_errors":   hard_errors,
        "parse_warnings": parse_warnings,
    }
