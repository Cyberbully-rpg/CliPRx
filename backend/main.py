"""
FastAPI Entry Point (Phase 1)
Wires the DIPPA Data Ingestion, ML, and Output layers into a single execution pipeline.
"""
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Import Data Ingestion Parsers
from parsers.aws_parser import parse_aws_csv
from parsers.azure_parser import parse_azure_csv
from parsers.gcp_parser import parse_gcp_csv

# Import ML & Analytics Engines
from ml.isolation_forest import run_anomaly_detection
from ml.pattern_matcher import match_patterns
from ml.failure_scorer import apply_failure_scores
from conflict_resolver import resolve_conflicts
from roi_ranker import calculate_roi_and_rank

# Import Output Renderer
from services.gemini_service import render_sprint_tickets

# Load environment variables (GEMINI_API_KEY)
load_dotenv()

app = FastAPI(title="CliPRx API", version="1.0")

# Allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        risk_scored_prescriptions = apply_failure_scores(raw_prescriptions)

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

    except ValueError as ve:
        # Catches our specific parser errors (e.g., empty CSV)
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Catches unexpected ML or pipeline crashes
        raise HTTPException(status_code=500, detail=str(e))