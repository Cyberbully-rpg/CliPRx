"""
Tests for services/csv_ingest.py -- the shared ingestion layer both entry
points (/api/v1/test-pipeline and the split /upload + /pipeline endpoints) call.

These cover the HTTP-facing contracts (provider dispatch, the size limit) and
the two derived views the dashboard renders: the per-service aggregation behind
the tier-declaration screen, and the warnings array.
"""
import pandas as pd
import pytest
from fastapi import HTTPException

from services.csv_ingest import (
    build_service_rows,
    build_upload_warnings,
    enforce_upload_size,
    parse_by_provider,
)

AWS_CSV = b"Service,UnblendedCost,UsageQuantity,UsageType,Region\nAmazonEC2,450.00,720,BoxUsage:m5.large,us-east-1\n"
AZURE_CSV = b"MeterCategory,Cost,Quantity,MeterName,ResourceLocation\nVirtual Machines,300.00,720,D4s v3,eastus\n"
GCP_CSV = b"service.description,cost,usage.amount,usage.unit,location.region\nCompute Engine,220.00,744,hour,us-central1\n"
FOCUS_CSV = (
    b"ProviderName,ServiceName,BilledCost,ConsumedQuantity,ChargeDescription,RegionId\n"
    b"Amazon Web Services,Amazon Simple Storage Service,410.00,900,Storage,us-east-1\n"
)


@pytest.mark.parametrize(
    "provider, content, expected_service",
    [
        ("aws", AWS_CSV, "amazonec2"),
        ("AWS", AWS_CSV, "amazonec2"),
        ("azure", AZURE_CSV, "virtual_machines"),
        ("gcp", GCP_CSV, "compute_engine"),
        ("focus", FOCUS_CSV, "amazons3"),
    ],
)
def test_provider_dispatch_routes_to_the_right_parser(provider, content, expected_service):
    df = parse_by_provider(provider, content)

    assert df.loc[0, "service_name"] == expected_service


def test_an_unknown_provider_is_a_400_not_a_crash():
    with pytest.raises(HTTPException) as exc:
        parse_by_provider("oracle", AWS_CSV)

    assert exc.value.status_code == 400
    assert "aws, azure, gcp, or focus" in exc.value.detail


def test_an_oversized_upload_is_rejected_with_413(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "1")

    with pytest.raises(HTTPException) as exc:
        enforce_upload_size(b"x" * (1024 * 1024 + 1))

    assert exc.value.status_code == 413


def test_an_upload_within_the_limit_passes(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "1")

    assert enforce_upload_size(b"x" * 1024) is None


# ------------------------------------------------- the tier-declaration screen


def test_service_rows_aggregate_line_items_per_service():
    df = pd.DataFrame(
        [
            {"service_name": "amazonec2", "cost_usd": 100.0, "tier": 3},
            {"service_name": "amazonec2", "cost_usd": 50.5, "tier": 3},
            {"service_name": "amazons3", "cost_usd": 20.0, "tier": 3},
        ]
    )

    rows = {r["service_name"]: r for r in build_service_rows(df)}

    assert rows["amazonec2"]["total_cost_usd"] == 150.5
    assert rows["amazonec2"]["line_item_count"] == 2
    assert rows["amazons3"]["line_item_count"] == 1


def test_default_tier_takes_the_minimum_so_the_ui_defaults_to_assume_protected():
    df = pd.DataFrame(
        [
            {"service_name": "amazonrds", "cost_usd": 10.0, "tier": 3},
            {"service_name": "amazonrds", "cost_usd": 10.0, "tier": 1},
        ]
    )

    assert build_service_rows(df)[0]["default_tier"] == 1


def test_service_rows_are_json_safe_primitives():
    """These go straight out over the wire; numpy scalars would not serialize."""
    df = pd.DataFrame([{"service_name": "amazonec2", "cost_usd": 100.0, "tier": 3}])

    row = build_service_rows(df)[0]

    assert isinstance(row["total_cost_usd"], float)
    assert isinstance(row["line_item_count"], int)
    assert isinstance(row["default_tier"], int)


# ------------------------------------------------------------------- warnings


def test_a_non_focus_upload_produces_no_warnings():
    assert build_upload_warnings(parse_by_provider("aws", AWS_CSV)) == []


def test_a_fully_mapped_focus_upload_produces_no_warnings():
    assert build_upload_warnings(parse_by_provider("focus", FOCUS_CSV)) == []


def test_unmappable_focus_rows_are_warned_about_by_name():
    """
    Those rows parse and score but can never match a pattern, which otherwise
    looks identical to "we analyzed it and found nothing."
    """
    df = parse_by_provider(
        "focus",
        FOCUS_CSV + b"Oracle Cloud,Object Storage,95.00,300,Storage,ap-mumbai-1\n",
    )

    warnings = build_upload_warnings(df)

    assert len(warnings) == 1
    assert "1 of 2 rows" in warnings[0]
    assert "Oracle Cloud" in warnings[0]
