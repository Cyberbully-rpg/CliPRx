"""
FastAPI Entry Point (Phase 1)
Wires the DIPPA Data Ingestion, ML, and Output layers into a single execution pipeline.
"""
import os
import uuid
from fastapi import Depends, FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv

from api.auth import get_current_user
from db.migrations.supabase_client import get_supabase_admin_client

# Import Data Ingestion Parsers
from parsers.aws_parser import parse_aws_csv
from parsers.azure_parser import parse_azure_csv
from parsers.gcp_parser import parse_gcp_csv

# Import ML & Analytics Engines
from ml.isolation_forest import run_anomaly_detection
from ml.pattern_matcher import match_patterns
from ml.failure_scorer import apply_failure_scores, compute_usage_variance_flags
from conflict_resolver import resolve_conflicts
from roi_ranker import calculate_roi_and_rank

# Import Output Renderer
from services.gemini_service import render_sprint_tickets

# Load environment variables (GEMINI_API_KEY)
load_dotenv()

app = FastAPI(title="CliPRx API", version="1.0")

# Allow frontend to communicate with backend. TRD 7.1: comma-separated origin list
# via ALLOWED_ORIGINS; falls back to "*" for local development if unset.
allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TRD 9 Non-Functional Requirements: "API error format: JSON: {error, detail, code}.
# All FastAPI exception handlers must follow this schema."
ERROR_CODE_LABELS = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    413: "payload_too_large",
    422: "validation_error",
    500: "internal_server_error",
}


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": ERROR_CODE_LABELS.get(exc.status_code, "http_error"),
            "detail": exc.detail,
            "code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc), "code": 500},
    )


@app.get("/health")
async def health_check():
    """Render/UptimeRobot keepalive target (TRD 8.2)."""
    return {"status": "ok"}


@app.get("/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    """TRD 3.1: returns user_id and email extracted from the verified JWT."""
    return {"user_id": user["user_id"], "email": user["email"]}


def _persist_upload(admin_client, user_id: str, provider: str, filename: str,
                     file_bytes: bytes, df) -> str:
    """Stores the raw CSV in Supabase Storage and records the upload (TRD 4.2)."""
    upload_id = str(uuid.uuid4())
    storage_path = f"{user_id}/{upload_id}/{filename}"

    admin_client.storage.from_("cliprx-uploads").upload(
        storage_path, file_bytes, {"content-type": "text/csv"}
    )

    admin_client.table("uploads").insert({
        "id": upload_id,
        "user_id": user_id,
        "cloud_provider": provider,
        "file_path": storage_path,
        "file_size_bytes": len(file_bytes),
        "service_count": int(df["service_name"].nunique()),
    }).execute()

    return upload_id


def _persist_report(admin_client, user_id: str, upload_id: str, prescriptions: list) -> str:
    """Records the report + its prescription rows (TRD 4.3, 4.4)."""
    report_id = str(uuid.uuid4())

    non_conflicted = [p for p in prescriptions if not p.get("is_conflicted", False)]
    total_savings_min = sum(p["savings_min"] for p in non_conflicted)
    total_savings_max = sum(p["savings_max"] for p in non_conflicted)
    conflict_count = sum(1 for p in prescriptions if p.get("is_conflicted", False))

    admin_client.table("reports").insert({
        "id": report_id,
        "user_id": user_id,
        "upload_id": upload_id,
        "status": "complete",
        "total_savings_min": round(total_savings_min, 2),
        "total_savings_max": round(total_savings_max, 2),
        "prescription_count": len(prescriptions),
        "conflict_count": conflict_count,
    }).execute()

    if prescriptions:
        rows = [{
            "report_id": report_id,
            "service_name": p["service_name"],
            "anomaly_score": p["anomaly_score"],
            "pattern_id": p["pattern_id"],
            "recommended_action": p["recommended_action"],
            "savings_min": p["savings_min"],
            "savings_max": p["savings_max"],
            "engineering_hours": round(
                (p["engineering_hours_min"] + p["engineering_hours_max"]) / 2, 2
            ),
            "risk_level": p["risk_level"],
            "failure_cost_estimate": p["failure_cost_estimate"],
            "roi_score": p["roi_score"],
            "rank_position": p["rank_position"],
            "is_conflicted": p["is_conflicted"],
            "conflict_reason": p["conflict_reason"],
            "tier": p["tier"],
        } for p in prescriptions]
        admin_client.table("prescriptions").insert(rows).execute()

    return report_id


@app.post("/api/v1/test-pipeline")
async def run_core_pipeline(
    file: UploadFile = File(...),
    cloud_provider: str = Form(...),
    user: dict = Depends(get_current_user),
):
    """
    Phase 1 End-to-End Test Endpoint.
    Ingests a CSV, runs all 5 layers of the DIPPA framework in memory,
    persists the upload/report/prescriptions (TRD 4), and returns the final
    ranked DevOps sprint tickets.
    """
    try:
        # 1. Read file bytes
        file_bytes = await file.read()

        max_upload_mb = float(os.getenv("MAX_UPLOAD_SIZE_MB", 50))
        max_upload_bytes = max_upload_mb * 1024 * 1024
        if len(file_bytes) > max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {max_upload_mb:.0f}MB upload limit."
            )

        # 2. Data Ingestion (Dynamic Routing)
        provider = cloud_provider.lower()
        if provider == "aws":
            df = parse_aws_csv(file_bytes)
        elif provider == "azure":
            df = parse_azure_csv(file_bytes)
        elif provider == "gcp":
            df = parse_gcp_csv(file_bytes)
        else:
            raise HTTPException(status_code=400, detail="Invalid cloud provider. Use aws, azure, or gcp.")

        admin_client = get_supabase_admin_client()
        upload_id = _persist_upload(admin_client, user["user_id"], provider, file.filename, file_bytes, df)

        # 3. Intelligent Preprocessing & Predictive Modeling
        # Get threshold from env or default to 0.65
        threshold = float(os.getenv("ANOMALY_THRESHOLD", 0.65))
        df_scored = run_anomaly_detection(df, threshold=threshold)

        # 4. Performance Analytics (Pattern Matching)
        raw_prescriptions = match_patterns(df_scored, cloud_provider=provider, anomaly_threshold=threshold)

        if not raw_prescriptions:
            report_id = _persist_report(admin_client, user["user_id"], upload_id, [])
            return {
                "status": "success",
                "upload_id": upload_id,
                "report_id": report_id,
                "message": "No anomalies found requiring action.",
                "data": []
            }

        # 5. Risk Assessment
        usage_variance_flags = compute_usage_variance_flags(df_scored)
        risk_scored_prescriptions = apply_failure_scores(raw_prescriptions, usage_variance_flags)

        # 6. Conflict Resolution
        resolved_prescriptions = resolve_conflicts(risk_scored_prescriptions)

        # 7. ROI Ranking
        ranked_prescriptions = calculate_roi_and_rank(resolved_prescriptions)

        # 8. Actionable Insights (Gemini LLM Rendering)
        final_prescriptions = render_sprint_tickets(ranked_prescriptions)

        report_id = _persist_report(admin_client, user["user_id"], upload_id, final_prescriptions)

        return {
            "status": "success",
            "upload_id": upload_id,
            "report_id": report_id,
            "prescription_count": len(final_prescriptions),
            "data": final_prescriptions
        }

    except HTTPException:
        # Deliberately raised above (bad provider, oversized file, etc.) -- let it
        # pass through as-is instead of being rewrapped into a 500 below.
        raise
    except ValueError as ve:
        # Catches our specific parser errors (e.g., empty CSV)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Catches unexpected ML or pipeline crashes
        raise HTTPException(status_code=500, detail=str(e))