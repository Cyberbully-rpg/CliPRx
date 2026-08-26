"""
FastAPI Entry Point (Phase 1 + Phase 2)
Wires the DIPPA Data Ingestion, ML, and Output layers into a single execution
pipeline, plus the Phase 2 auth/upload/pipeline/reports endpoints (TRD 3).
"""
import os
from fastapi import Depends, FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv

from api import pipeline as pipeline_router
from api import reports as reports_router
from api import upload as upload_router
from api.auth import get_current_user
from db.migrations.supabase_client import get_supabase_admin_client

# Import ML & Analytics Engines
from ml.isolation_forest import run_anomaly_detection
from ml.pattern_matcher import match_patterns
from ml.failure_scorer import apply_failure_scores, compute_usage_variance_flags
from conflict_resolver import resolve_conflicts
from roi_ranker import calculate_roi_and_rank

# Import Output Renderer
from services.gemini_service import render_sprint_tickets
from services.csv_ingest import enforce_upload_size, parse_by_provider
from services.persistence import create_pending_report, finalize_report, mark_report_failed, persist_upload

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

app.include_router(upload_router.router)
app.include_router(pipeline_router.router)
app.include_router(reports_router.router)

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
    # Starlette runs the base-Exception handler in ServerErrorMiddleware, which
    # sits OUTSIDE CORSMiddleware -- so responses from here never get CORS
    # headers applied automatically (unlike HTTPException responses, which do
    # pass through CORSMiddleware). Without this, any unhandled exception on a
    # route looks like a network failure ("Failed to fetch") in the browser
    # instead of a readable error, because the response is missing
    # Access-Control-Allow-Origin. Reflect the request's Origin manually,
    # matching CORSMiddleware's own behavior for allow_credentials=True.
    response = JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc), "code": 500},
    )
    origin = request.headers.get("origin")
    if origin and ("*" in allowed_origins or origin in allowed_origins):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"
    return response


@app.get("/health")
async def health_check():
    """Render/UptimeRobot keepalive target (TRD 8.2)."""
    return {"status": "ok"}


@app.get("/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    """TRD 3.1: returns user_id and email extracted from the verified JWT."""
    return {"user_id": user["user_id"], "email": user["email"]}


@app.post("/api/v1/test-pipeline")
async def run_core_pipeline(
    file: UploadFile = File(...),
    cloud_provider: str = Form(...),
    user: dict = Depends(get_current_user),
):
    """
    Phase 1 End-to-End Test Endpoint. Ingests a CSV, runs all 5 layers of the
    DIPPA framework in memory, persists the upload/report/prescriptions (TRD
    4), and returns the final ranked DevOps sprint tickets -- all in one call.

    This is the quick one-shot convenience path (no essential-services
    declaration step); POST /upload/csv + POST /pipeline/run is the real,
    TRD-documented multi-step flow, and shares all the same underlying
    persistence/parsing helpers as this endpoint.
    """
    report_id = None
    admin_client = None
    try:
        file_bytes = await file.read()
        enforce_upload_size(file_bytes)

        provider = cloud_provider.lower()
        df = parse_by_provider(provider, file_bytes)

        admin_client = get_supabase_admin_client()
        upload_id = persist_upload(admin_client, user["user_id"], provider, file.filename, file_bytes, df)
        report_id = create_pending_report(admin_client, user["user_id"], upload_id)

        threshold = float(os.getenv("ANOMALY_THRESHOLD", 0.65))
        df_scored = run_anomaly_detection(df, threshold=threshold)

        raw_prescriptions = match_patterns(df_scored, cloud_provider=provider, anomaly_threshold=threshold)

        if not raw_prescriptions:
            finalize_report(admin_client, report_id, [])
            return {
                "status": "success",
                "upload_id": upload_id,
                "report_id": report_id,
                "message": "No anomalies found requiring action.",
                "data": []
            }

        usage_variance_flags = compute_usage_variance_flags(df_scored)
        risk_scored_prescriptions = apply_failure_scores(raw_prescriptions, usage_variance_flags)
        resolved_prescriptions = resolve_conflicts(risk_scored_prescriptions)
        ranked_prescriptions = calculate_roi_and_rank(resolved_prescriptions)
        final_prescriptions = render_sprint_tickets(ranked_prescriptions)

        finalize_report(admin_client, report_id, final_prescriptions)

        return {
            "status": "success",
            "upload_id": upload_id,
            "report_id": report_id,
            "prescription_count": len(final_prescriptions),
            "data": final_prescriptions
        }

    except HTTPException:
        # Deliberately raised above (bad provider, oversized file, etc.) -- let it
        # pass through as-is instead of being rewrapped into a 500 below. Only
        # mark the report failed if it was actually created (a bad-provider/
        # oversized-file error happens before create_pending_report runs).
        if report_id and admin_client:
            mark_report_failed(admin_client, report_id)
        raise
    except ValueError as ve:
        # Catches our specific parser errors (e.g., empty CSV)
        if report_id and admin_client:
            mark_report_failed(admin_client, report_id)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Catches unexpected ML or pipeline crashes
        if report_id and admin_client:
            mark_report_failed(admin_client, report_id)
        raise HTTPException(status_code=500, detail=str(e))
