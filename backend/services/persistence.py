"""
Persistence Helpers (TRD section 4)
Shared by /api/v1/test-pipeline and the split /upload, /pipeline, /reports
endpoints. All writes use the service-role admin client (bypasses RLS) -- the
backend enforces ownership itself via the already-verified user_id, not the
database (see services/ownership.py).
"""
import uuid


def persist_upload(admin_client, user_id: str, provider: str, filename: str,
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


def create_pending_report(admin_client, user_id: str, upload_id: str) -> str:
    """
    Inserts a 'running' report row before the pipeline starts, so a mid-run
    crash leaves an honest status behind instead of a stale/missing row.
    Skips 'pending' -- there's no queueing delay before work starts (no
    background job system exists), so 'pending' would never be observably true.
    """
    report_id = str(uuid.uuid4())
    admin_client.table("reports").insert({
        "id": report_id,
        "user_id": user_id,
        "upload_id": upload_id,
        "status": "running",
    }).execute()
    return report_id


def finalize_report(admin_client, report_id: str, prescriptions: list) -> None:
    """
    Computes totals and marks the report complete, persisting one prescriptions
    row per item -- including conflicted ones, which still carry real data
    (is_conflicted/conflict_reason/roi_score: 0) that's the point of keeping.
    """
    non_conflicted = [p for p in prescriptions if not p.get("is_conflicted", False)]
    total_savings_min = sum(p["savings_min"] for p in non_conflicted)
    total_savings_max = sum(p["savings_max"] for p in non_conflicted)
    conflict_count = sum(1 for p in prescriptions if p.get("is_conflicted", False))

    admin_client.table("reports").update({
        "status": "complete",
        "total_savings_min": round(total_savings_min, 2),
        "total_savings_max": round(total_savings_max, 2),
        "prescription_count": len(prescriptions),
        "conflict_count": conflict_count,
    }).eq("id", report_id).execute()

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
            # The Gemini-authored ticket (pipeline stage 7). Falls back to the
            # raw recommended_action if the renderer never ran -- gemini_service
            # already substitutes its own plain-text stub on API failure, so a
            # missing key here means the stage was skipped entirely, not that
            # Gemini errored.
            "sprint_ticket": p.get("sprint_ticket") or p["recommended_action"],
        } for p in prescriptions]
        admin_client.table("prescriptions").insert(rows).execute()


def mark_report_failed(admin_client, report_id: str) -> None:
    """Best-effort -- swallows its own errors so a secondary DB failure never
    masks the original exception that triggered this call."""
    try:
        admin_client.table("reports").update({"status": "failed"}).eq("id", report_id).execute()
    except Exception:
        pass
