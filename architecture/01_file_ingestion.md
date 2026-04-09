# 📐 SOP-01: File Ingestion

## Tool: `tools/ingest_files.py`

## Purpose
Parse Terraform (`.tf`) and Kubernetes (`.yaml`/`.yml`) file content into a normalized dictionary structure ready for drift detection.

## Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| `content` | `str` | Raw file content (from frontend paste or GitHub fetch) |
| `file_type` | `str` | `"terraform"` or `"kubernetes"` (or `"auto"` to detect) |
| `file_path` | `str` | Logical file path for labeling |

## Outputs
```json
{
  "file_path": "main.tf",
  "file_type": "terraform",
  "resources": {
    "aws_instance.web": {
      "instance_type": "t2.micro",
      "ami": "ami-0c55b159cbfafe1f0"
    }
  },
  "parse_errors": []
}
```

## Logic
1. **Auto-detect file type** if `file_type == "auto"`:
   - Contains `resource "` or `variable "` → Terraform
   - Contains `apiVersion:` → Kubernetes
2. **Terraform**: Use `hcl2.load()` from `python-hcl2`.
3. **Kubernetes**: Use `yaml.safe_load_all()` to handle multi-document YAML.
4. Normalize output into flat `{resource_key: attributes}` dict.
5. Collect any parse errors into `parse_errors[]` — do not raise, return gracefully.

## Edge Cases
- Empty file → return `{"resources": {}, "parse_errors": ["Empty file"]}`
- Invalid HCL/YAML → capture exception, return error in `parse_errors`
- Multi-document YAML (separated by `---`) → parse each document separately

## Error Handling
- Wrap all parsing in try/except
- Log errors to `.tmp/logs/ingest.json`
- Never raise uncaught exceptions
