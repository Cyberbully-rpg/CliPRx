"""
FastAPI Entry Point (Phase 1)
Wires the DIPPA Data Ingestion, ML, and Output layers into a single execution pipeline.
"""
import os
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv

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


@app.post("/api/v1/test-pipeline")
async def run_core_pipeline(
    file: UploadFile = File(...),
    cloud_provider: str = Form(...)
):
    """
    Phase 1 End-to-End Test Endpoint.
    Ingests a CSV, runs all 5 layers of the DIPPA framework in memory, 
    and returns the final ranked DevOps sprint tickets.
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

        # 3. Intelligent Preprocessing & Predictive Modeling
        # Get threshold from env or default to 0.65
        threshold = float(os.getenv("ANOMALY_THRESHOLD", 0.65))
        df_scored = run_anomaly_detection(df, threshold=threshold)

        # 4. Performance Analytics (Pattern Matching)
        raw_prescriptions = match_patterns(df_scored, cloud_provider=provider, anomaly_threshold=threshold)
        
        if not raw_prescriptions:
            return {"status": "success", "message": "No anomalies found requiring action.", "data": []}

        # 5. Risk Assessment
        usage_variance_flags = compute_usage_variance_flags(df_scored)
        risk_scored_prescriptions = apply_failure_scores(raw_prescriptions, usage_variance_flags)

        # 6. Conflict Resolution
        resolved_prescriptions = resolve_conflicts(risk_scored_prescriptions)

        # 7. ROI Ranking
        ranked_prescriptions = calculate_roi_and_rank(resolved_prescriptions)

        # 8. Actionable Insights (Gemini LLM Rendering)
        final_prescriptions = render_sprint_tickets(ranked_prescriptions)

        return {
            "status": "success",
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