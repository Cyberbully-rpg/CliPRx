import asyncio
import os
import sys
from dotenv import load_dotenv

# Windows consoles default to cp1252, which can't encode the emoji printed below
sys.stdout.reconfigure(encoding="utf-8")

# Load environment variables from backend/.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "backend", ".env"))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.parsers.aws_parser import parse_aws_csv
from backend.ml.isolation_forest import run_anomaly_detection
from backend.ml.pattern_matcher import match_patterns
from backend.ml.failure_scorer import apply_failure_scores, compute_usage_variance_flags
from backend.conflict_resolver import resolve_conflicts
from backend.roi_ranker import calculate_roi_and_rank
from backend.services.gemini_service import render_sprint_tickets


async def run_test():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY is missing from backend/.env")
        return
    print(f"✅ Loaded GEMINI_API_KEY (starts with: {api_key[:6]}...)")

    mock_csv_data = """service_name,cost_usd,usage_quantity,usage_type,region,billing_period_start,billing_period_end,tier
AmazonEC2,0.01,1.0,BoxUsage:t2.micro,us-east-1,2026-03-01,2026-03-02,standard
AmazonEC2,0.01,1.0,BoxUsage:t2.micro,us-east-1,2026-03-01,2026-03-02,standard
AmazonEC2,450.00,1000.0,EBS:VolumeUsage.gp2,us-east-1,2026-03-01,2026-03-02,standard
"""
    file_bytes = mock_csv_data.encode("utf-8")

    df = parse_aws_csv(file_bytes)
    df_scored = run_anomaly_detection(df, threshold=0.0)
    raw_prescriptions = match_patterns(df_scored, cloud_provider="aws", anomaly_threshold=0.0)
    usage_variance_flags = compute_usage_variance_flags(df_scored)
    risk_scored = apply_failure_scores(raw_prescriptions, usage_variance_flags)
    resolved = resolve_conflicts(risk_scored)
    ranked = calculate_roi_and_rank(resolved)

    print("\n" + "=" * 60)
    print("STEP 7: Gemini Sprint Ticket Renderer")
    print("=" * 60)
    tickets = await render_sprint_tickets(ranked)
    print(tickets)


if __name__ == "__main__":
    asyncio.run(run_test())