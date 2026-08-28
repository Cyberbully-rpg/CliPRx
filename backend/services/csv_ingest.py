"""
CSV Ingestion Helpers
Shared by /api/v1/test-pipeline and the split /upload, /pipeline endpoints:
provider dispatch, upload-size enforcement, and reconstructing a parsed
DataFrame from a previously-stored upload.
"""
import os
import pandas as pd
from fastapi import HTTPException

from parsers.aws_parser import parse_aws_csv
from parsers.azure_parser import parse_azure_csv
from parsers.focus_parser import parse_focus_csv
from parsers.gcp_parser import parse_gcp_csv


def enforce_upload_size(file_bytes: bytes) -> None:
    max_upload_mb = float(os.getenv("MAX_UPLOAD_SIZE_MB", 50))
    max_upload_bytes = max_upload_mb * 1024 * 1024
    if len(file_bytes) > max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {max_upload_mb:.0f}MB upload limit."
        )


def parse_by_provider(provider: str, file_bytes: bytes) -> pd.DataFrame:
    provider = provider.lower()
    if provider == "aws":
        return parse_aws_csv(file_bytes)
    elif provider == "azure":
        return parse_azure_csv(file_bytes)
    elif provider == "gcp":
        return parse_gcp_csv(file_bytes)
    elif provider == "focus":
        return parse_focus_csv(file_bytes)
    else:
        raise HTTPException(status_code=400, detail="Invalid cloud provider. Use aws, azure, gcp, or focus.")


def fetch_upload_dataframe(admin_client, upload: dict) -> pd.DataFrame:
    """
    Re-fetches the raw CSV from Storage and re-parses it. The parsers are pure
    functions of the bytes, so this deterministically reproduces the same
    DataFrame /upload/csv originally produced -- no caching layer needed, since
    /pipeline/run and /upload/csv may happen minutes apart on different workers.
    """
    file_bytes = admin_client.storage.from_("cliprx-uploads").download(upload["file_path"])
    return parse_by_provider(upload["cloud_provider"], file_bytes)


def build_service_rows(df: pd.DataFrame) -> list[dict]:
    """
    Aggregates the parsed DataFrame by service_name for the essential-services
    declaration UI (one row per service, not one per CSV line item). default_tier
    is the MINIMUM tier seen across that service's line items -- the only way a
    single service_name group has mixed tier values today is the CSV tier-column
    stopgap, and biasing the pre-filled default toward "assume protected" (tier 1)
    is safer than biasing toward "assume safe to touch."
    """
    grouped = df.groupby("service_name").agg(
        total_cost_usd=("cost_usd", "sum"),
        line_item_count=("cost_usd", "count"),
        default_tier=("tier", "min"),
    ).reset_index()

    return [
        {
            "service_name": row["service_name"],
            "total_cost_usd": round(float(row["total_cost_usd"]), 2),
            "line_item_count": int(row["line_item_count"]),
            "default_tier": int(row["default_tier"]),
        }
        for _, row in grouped.iterrows()
    ]
