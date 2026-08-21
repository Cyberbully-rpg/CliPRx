"""
Pipeline Endpoints (TRD 3.3)
"""
import os
import time
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import get_current_user
from conflict_resolver import resolve_conflicts
from db.migrations.supabase_client import get_supabase_admin_client
from ml.failure_scorer import apply_failure_scores, compute_usage_variance_flags
from ml.isolation_forest import run_anomaly_detection
from ml.pattern_matcher import match_patterns
from roi_ranker import calculate_roi_and_rank
from services.csv_ingest import fetch_upload_dataframe
from services.gemini_service import render_sprint_tickets
from services.ownership import get_owned_report, get_owned_upload
from services.persistence import create_pending_report, finalize_report, mark_report_failed

router = APIRouter()


class EssentialService(BaseModel):
    service_name: str
    tier: Literal[1, 2, 3]
    notes: Optional[str] = None


class PipelineRunRequest(BaseModel):
    upload_id: str
    essential_services: list[EssentialService] = []


@router.post("/pipeline/run")
async def run_pipeline(body: PipelineRunRequest, user: dict = Depends(get_current_user)):
    """
    TRD 3.3: runs the full DIPPA pipeline against a previously-uploaded CSV,
    applying essential_services tier declarations, and persists the report.

    Runs synchronously in-process -- no background job queue exists anywhere
    in this codebase, and the work itself takes seconds. Status goes straight
    from 'running' to 'complete'/'failed', skipping 'pending' since there's no
    queueing delay before work starts. Known limitation: if the process is
    killed mid-request, the report stays stuck at 'running' -- fixing that for
    real needs a timeout/heartbeat mechanism, which is out of scope here.
    """
    admin_client = get_supabase_admin_client()
    upload = get_owned_upload(admin_client, body.upload_id, user["user_id"])
    df = fetch_upload_dataframe(admin_client, upload)

    # Essential-services declarations OVERRIDE the parser's default tier
    # (which itself may already be 3, or read from a tier column in the source
    # CSV as a stopgap) -- services not mentioned here keep whatever tier the
    # parser already assigned.
    overrides = {es.service_name: es.tier for es in body.essential_services}
    if overrides:
        df["tier"] = df["service_name"].map(overrides).fillna(df["tier"]).astype(int)

    report_id = create_pending_report(admin_client, user["user_id"], body.upload_id)
    started_at = time.time()

    try:
        threshold = float(os.getenv("ANOMALY_THRESHOLD", 0.65))
        df_scored = run_anomaly_detection(df, threshold=threshold)

        raw_prescriptions = match_patterns(
            df_scored, cloud_provider=upload["cloud_provider"], anomaly_threshold=threshold
        )

        if raw_prescriptions:
            usage_variance_flags = compute_usage_variance_flags(df_scored)
            risk_scored = apply_failure_scores(raw_prescriptions, usage_variance_flags)
            resolved = resolve_conflicts(risk_scored)
            ranked = calculate_roi_and_rank(resolved)
            final_prescriptions = render_sprint_tickets(ranked)
        else:
            final_prescriptions = []

        finalize_report(admin_client, report_id, final_prescriptions)

    except ValueError as ve:
        mark_report_failed(admin_client, report_id)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        mark_report_failed(admin_client, report_id)
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "report_id": report_id,
        "status": "complete",
        "estimated_seconds": round(time.time() - started_at, 2),
    }


@router.get("/pipeline/{report_id}/status")
async def get_pipeline_status(report_id: str, user: dict = Depends(get_current_user)):
    """TRD 3.3. Deliberately minimal -- full data lives at GET /reports/{id}."""
    admin_client = get_supabase_admin_client()
    report = get_owned_report(admin_client, report_id, user["user_id"])
    return {"report_id": report_id, "status": report["status"]}
