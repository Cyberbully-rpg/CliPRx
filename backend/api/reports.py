"""
Report Endpoints (TRD 3.4)
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response

from api.auth import get_current_user
from db.migrations.supabase_client import get_supabase_admin_client
from services.ownership import get_owned_report
from services.pdf_service import generate_report_pdf

router = APIRouter()


@router.get("/reports")
async def list_reports(user: dict = Depends(get_current_user)):
    """
    TRD 3.4: lists the user's reports, newest first. No extra date filter is
    needed for "last 30 days" -- expires_at defaults to created_at + 30 days
    and the nightly pg_cron retention job already hard-deletes anything past
    that, so nothing older can exist in the table to filter out.
    """
    admin_client = get_supabase_admin_client()
    resp = (
        admin_client.table("reports")
        .select(
            "id, upload_id, status, total_savings_min, total_savings_max, "
            "prescription_count, conflict_count, created_at, expires_at"
        )
        .eq("user_id", user["user_id"])
        .is_("deleted_at", "null")
        .order("created_at", desc=True)
        .execute()
    )
    return {"reports": resp.data}


@router.get("/reports/{report_id}")
async def get_report(report_id: str, user: dict = Depends(get_current_user)):
    """
    TRD 3.4: full report with all prescription cards. Returns the persisted,
    DB-column subset -- a smaller shape than /api/v1/test-pipeline's in-memory
    data array (e.g. a single averaged engineering_hours, no
    engineering_hours_min/max, no downtime_risk, no immutable_blockers).
    """
    admin_client = get_supabase_admin_client()
    report = get_owned_report(admin_client, report_id, user["user_id"])

    resp = (
        admin_client.table("prescriptions")
        .select("*")
        .eq("report_id", report_id)
        .order("rank_position")
        .execute()
    )
    report["prescriptions"] = resp.data
    return report


@router.get("/reports/{report_id}/pdf")
async def download_report_pdf(report_id: str, user: dict = Depends(get_current_user)):
    """
    TRD 3.4: returns the report as a branded PDF (PRD 6.8). Generated once and
    cached in the cliprx-reports Storage bucket (reports.pdf_path) -- a report
    is immutable after finalize_report() runs, so there's no reason to
    regenerate it on every download.
    """
    admin_client = get_supabase_admin_client()
    report = get_owned_report(admin_client, report_id, user["user_id"])
    storage_path = f"{user['user_id']}/{report_id}.pdf"

    if report.get("pdf_path"):
        try:
            pdf_bytes = admin_client.storage.from_("cliprx-reports").download(storage_path)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="cliprx-report-{report_id}.pdf"'},
            )
        except Exception:
            pass  # cached file missing/corrupt -- fall through and regenerate

    prescriptions = (
        admin_client.table("prescriptions")
        .select("*")
        .eq("report_id", report_id)
        .order("rank_position")
        .execute()
    ).data

    upload_resp = admin_client.table("uploads").select("cloud_provider").eq("id", report["upload_id"]).execute()
    cloud_provider = upload_resp.data[0]["cloud_provider"] if upload_resp.data else ""

    pdf_bytes = generate_report_pdf(report, prescriptions, cloud_provider)

    admin_client.storage.from_("cliprx-reports").upload(
        storage_path, pdf_bytes, {"content-type": "application/pdf", "upsert": "true"}
    )
    admin_client.table("reports").update({"pdf_path": storage_path}).eq("id", report_id).execute()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cliprx-report-{report_id}.pdf"'},
    )


@router.delete("/reports/{report_id}")
async def delete_report(report_id: str, user: dict = Depends(get_current_user)):
    """
    TRD 3.4: soft-delete (sets deleted_at). Prescriptions rows are untouched --
    real cascade delete only happens when the nightly retention job hard-deletes
    the parent report row after expires_at.
    """
    admin_client = get_supabase_admin_client()
    get_owned_report(admin_client, report_id, user["user_id"])  # 404 if missing/not owned/already deleted

    admin_client.table("reports").update({
        "deleted_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", report_id).execute()

    return {"report_id": report_id, "deleted": True}
