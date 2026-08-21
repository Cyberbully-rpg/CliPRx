"""
Ownership Checks
The backend reads/writes via the service-role client, which bypasses RLS, so
"does this row belong to this user" has to be checked explicitly here rather
than relied upon from the database. 404 (not 403) on any mismatch, so a
request can't distinguish "doesn't exist" from "exists but isn't yours."
"""
from fastapi import HTTPException


def get_owned_upload(admin_client, upload_id: str, user_id: str) -> dict:
    resp = (
        admin_client.table("uploads")
        .select("*")
        .eq("id", upload_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Upload not found.")
    return resp.data[0]


def get_owned_report(admin_client, report_id: str, user_id: str, include_deleted: bool = False) -> dict:
    query = (
        admin_client.table("reports")
        .select("*")
        .eq("id", report_id)
        .eq("user_id", user_id)
    )
    if not include_deleted:
        query = query.is_("deleted_at", "null")
    resp = query.execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Report not found.")
    return resp.data[0]
