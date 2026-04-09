"""
Smoke test: runs the full pipeline (ingest → detect → AI analyze) on a sample
Terraform file WITHOUT starting the server.
Run from project root: python smoke_test.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

SAMPLE_TF = """
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"
  tags = {
    Name = "WebServer"
    Env  = "production"
  }
}

resource "aws_security_group" "web_sg" {
  name = "web-sg"
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
"""

BASELINE_TF = """
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.nano"
  tags = {
    Name = "WebServer"
    Env  = "staging"
  }
}
"""

print("\n[1] Ingesting current file...")
from tools.ingest_files import ingest
current  = ingest(content=SAMPLE_TF,   file_path="main.tf", file_type="terraform")
baseline = ingest(content=BASELINE_TF, file_path="main.tf", file_type="terraform")
print(f"    Current resources:  {list(current['resources'].keys())}")
print(f"    Baseline resources: {list(baseline['resources'].keys())}")
print(f"    Parse errors: {current['parse_errors']}")

print("\n[2] Detecting drift...")
from tools.detect_drift import detect_drift
events = detect_drift(
    current   = current['resources'],
    baseline  = baseline['resources'],
    file_path = "main.tf",
    file_type = "terraform",
    run_id    = "smoke-test-run",
)
print(f"    Drift events found: {len(events)}")
for e in events:
    print(f"    - [{e['severity'].upper()}] {e['resource_type']}.{e['resource_name']} | {e['drift_type']} | field={e['changed_field']}")

print("\n[3] Running AI analysis (first event only for speed)...")
from tools.analyze_with_ai import analyze_events
if events:
    enriched = analyze_events([events[0]])
    ai = enriched[0].get("ai_analysis", {})
    print(f"    Model:          {ai.get('model_used','?')}")
    print(f"    Summary:        {ai.get('summary','?')}")
    print(f"    Risk Score:     {ai.get('risk_score','?')}")
    print(f"    Recommendation: {ai.get('recommendation','?')}")

print("\n[OK] Smoke test passed!\n")
