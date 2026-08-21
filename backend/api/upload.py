"""
Upload Endpoints (TRD 3.2)
"""
from fastapi import APIRouter, Depends, File, Form, UploadFile

from api.auth import get_current_user
from db.migrations.supabase_client import get_supabase_admin_client
from services.csv_ingest import (
    build_service_rows,
    enforce_upload_size,
    fetch_upload_dataframe,
    parse_by_provider,
)
from services.ownership import get_owned_upload
from services.persistence import persist_upload

router = APIRouter()


@router.post("/upload/csv")
async def upload_csv(
    file: UploadFile = File(...),
    cloud_provider: str = Form(...),
    user: dict = Depends(get_current_user),
):
    """TRD 3.2: accepts a CSV, parses and stores it, and returns a per-service
    breakdown for the essential-services declaration step."""
    file_bytes = await file.read()
    enforce_upload_size(file_bytes)

    provider = cloud_provider.lower()
    df = parse_by_provider(provider, file_bytes)

    admin_client = get_supabase_admin_client()
    upload_id = persist_upload(admin_client, user["user_id"], provider, file.filename, file_bytes, df)

    return {
        "upload_id": upload_id,
        "cloud_provider": provider,
        "service_count": int(df["service_name"].nunique()),
        "services": build_service_rows(df),
        "warnings": [],
    }


@router.get("/upload/{upload_id}/services")
async def get_upload_services(upload_id: str, user: dict = Depends(get_current_user)):
    """TRD 3.2: re-derives the same services breakdown for an existing upload
    (e.g. the user navigating back to the declaration screen)."""
    admin_client = get_supabase_admin_client()
    upload = get_owned_upload(admin_client, upload_id, user["user_id"])
    df = fetch_upload_dataframe(admin_client, upload)

    return {
        "upload_id": upload_id,
        "cloud_provider": upload["cloud_provider"],
        "service_count": int(df["service_name"].nunique()),
        "services": build_service_rows(df),
    }
