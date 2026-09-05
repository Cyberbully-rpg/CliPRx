"""
Parser tests -- stage 1 of the DIPPA pipeline.

Every downstream stage assumes the normalized 8-column schema, so these cover
the schema contract itself plus the specific real-world coercion bugs the
parsers were fixed for (comma/currency-formatted costs, padded service names,
duplicate candidate columns, INR vs USD cost columns).
"""
import pandas as pd
import pytest

from parsers.aws_parser import parse_aws_csv
from parsers.azure_parser import parse_azure_csv
from parsers.focus_parser import parse_focus_csv
from parsers.gcp_parser import parse_gcp_csv

STANDARD_COLUMNS = [
    "service_name",
    "cost_usd",
    "usage_quantity",
    "usage_type",
    "region",
    "billing_period_start",
    "billing_period_end",
    "tier",
]


def csv(text: str) -> bytes:
    return text.strip().encode("utf-8")


# --------------------------------------------------------------------------- AWS

AWS_SIMPLE = csv(
    """
Service,UnblendedCost,UsageQuantity,UsageType,Region
AmazonEC2,450.00,720,BoxUsage:m5.large,us-east-1
AmazonS3,120.50,900,TimedStorage-ByteHrs,us-east-1
"""
)


def test_aws_simple_export_emits_the_standard_schema():
    df = parse_aws_csv(AWS_SIMPLE)

    assert list(df.columns) == STANDARD_COLUMNS
    assert len(df) == 2
    assert df.loc[0, "service_name"] == "amazonec2"
    assert df.loc[0, "cost_usd"] == 450.00
    assert df.loc[0, "usage_type"] == "BoxUsage:m5.large"


def test_aws_cur_slash_delimited_columns_map_to_the_same_schema():
    """The real Cost and Usage Report shape, not the Cost Explorer quick download."""
    df = parse_aws_csv(
        csv(
            """
lineItem/ProductCode,lineItem/UnblendedCost,lineItem/UsageAmount,lineItem/UsageType,product/region
AmazonRDS,830.25,744,InstanceUsage:db.m5.xlarge,eu-west-1
"""
        )
    )

    assert list(df.columns) == STANDARD_COLUMNS
    assert df.loc[0, "service_name"] == "amazonrds"
    assert df.loc[0, "cost_usd"] == 830.25
    assert df.loc[0, "region"] == "eu-west-1"


def test_aws_prefers_clean_region_over_availability_zone():
    """product/region (us-east-1) wins over lineItem/AvailabilityZone (us-east-1a)."""
    df = parse_aws_csv(
        csv(
            """
lineItem/ProductCode,lineItem/UnblendedCost,lineItem/UsageAmount,lineItem/UsageType,product/region,lineItem/AvailabilityZone
AmazonEC2,10.00,5,BoxUsage:m5.large,us-east-1,us-east-1a
"""
        )
    )

    assert df.loc[0, "region"] == "us-east-1"


@pytest.mark.parametrize(
    "raw_cost, expected",
    [
        ("1,240.50", 1240.50),
        ("$450.00", 450.00),
        ("$1,240.50", 1240.50),
        (" 99.99 ", 99.99),
    ],
)
def test_aws_strips_thousands_separators_and_currency_symbols(raw_cost, expected):
    """A comma-formatted cost must not silently coerce to NaN -> 0.0 and vanish."""
    df = parse_aws_csv(
        csv(
            f"""
Service,UnblendedCost,UsageQuantity,UsageType,Region
AmazonEC2,"{raw_cost}",720,BoxUsage:m5.large,us-east-1
"""
        )
    )

    assert len(df) == 1, "row was dropped by the cost_usd > 0 filter after bad coercion"
    assert df.loc[0, "cost_usd"] == expected


def test_aws_strips_padding_before_normalizing_service_name():
    """A padded service name must not become a second, separate service."""
    df = parse_aws_csv(
        csv(
            """
Service,UnblendedCost,UsageQuantity,UsageType,Region
  AmazonEC2  ,450.00,720,BoxUsage:m5.large,us-east-1
AmazonEC2,120.00,300,BoxUsage:m5.large,us-east-1
"""
        )
    )

    assert set(df["service_name"]) == {"amazonec2"}


def test_aws_drops_spreadsheet_total_rows():
    df = parse_aws_csv(
        csv(
            """
Service,UnblendedCost,UsageQuantity,UsageType,Region
AmazonEC2,450.00,720,BoxUsage:m5.large,us-east-1
Total,570.50,1020,,
"""
        )
    )

    assert len(df) == 1
    assert df.loc[0, "service_name"] == "amazonec2"


def test_aws_drops_zero_and_negative_cost_rows():
    df = parse_aws_csv(
        csv(
            """
Service,UnblendedCost,UsageQuantity,UsageType,Region
AmazonEC2,450.00,720,BoxUsage:m5.large,us-east-1
AmazonS3,0.00,0,TimedStorage-ByteHrs,us-east-1
AWSCredits,-25.00,0,Credit,us-east-1
"""
        )
    )

    assert list(df["service_name"]) == ["amazonec2"]


def test_aws_defaults_every_row_to_tier_3_when_the_csv_has_no_tier_column():
    df = parse_aws_csv(AWS_SIMPLE)

    assert set(df["tier"]) == {3}
    assert df["tier"].dtype.kind == "i"


@pytest.mark.parametrize(
    "raw_tier, expected",
    [("1", 1), ("tier1", 1), ("2", 2), ("Tier 2", 2), ("3", 3), ("banana", 3), ("9", 3)],
)
def test_aws_honors_a_tier_column_and_defaults_unrecognized_values_to_3(raw_tier, expected):
    df = parse_aws_csv(
        csv(
            f"""
Service,UnblendedCost,UsageQuantity,UsageType,Region,tier
AmazonEC2,450.00,720,BoxUsage:m5.large,us-east-1,{raw_tier}
"""
        )
    )

    assert df.loc[0, "tier"] == expected


def test_aws_rejects_a_csv_with_no_recognizable_billing_columns():
    """A wrong-format upload must fail loudly, not return an empty result set."""
    with pytest.raises(ValueError, match="No recognizable AWS billing columns"):
        parse_aws_csv(csv("name,email\nada,ada@example.com"))


def test_aws_rejects_an_empty_file():
    with pytest.raises(ValueError, match="empty"):
        parse_aws_csv(b"")


# ------------------------------------------------------------------------- Azure


def test_azure_prefers_metercategory_over_consumedservice():
    """
    Real exports carry both. MeterCategory (Virtual Machines) is what
    azure_patterns.json triggers on; ConsumedService (Microsoft.Compute) is not.
    """
    df = parse_azure_csv(
        csv(
            """
MeterCategory,ConsumedService,Cost,Quantity,MeterName,ResourceLocation
Virtual Machines,Microsoft.Compute,300.00,720,D4s v3,eastus
"""
        )
    )

    assert list(df.columns) == STANDARD_COLUMNS
    assert df.loc[0, "service_name"] == "virtual_machines"
    assert df.loc[0, "usage_type"] == "D4s v3"


def test_azure_falls_back_to_consumedservice_when_metercategory_is_absent():
    df = parse_azure_csv(
        csv(
            """
ConsumedService,CostInBillingCurrency,Quantity,Meter,ResourceLocation
Microsoft.Storage,42.10,1000,Hot LRS,westeurope
"""
        )
    )

    assert df.loc[0, "service_name"] == "microsoft.storage"
    assert df.loc[0, "cost_usd"] == 42.10


def test_azure_rejects_an_unrecognized_schema():
    with pytest.raises(ValueError, match="No recognizable Azure billing columns"):
        parse_azure_csv(csv("Service,UnblendedCost\nAmazonEC2,1.00"))


# --------------------------------------------------------------------------- GCP


def test_gcp_bigquery_export_shape():
    df = parse_gcp_csv(
        csv(
            """
service.description,cost,usage.amount,usage.unit,location.region
Compute Engine,220.00,744,hour,us-central1
"""
        )
    )

    assert list(df.columns) == STANDARD_COLUMNS
    assert df.loc[0, "service_name"] == "compute_engine"
    assert df.loc[0, "cost_usd"] == 220.00


def test_gcp_never_reads_the_inr_column_as_usd():
    """
    The spaced-header export carries both a USD and an INR cost column. Picking
    the INR one would overstate every cost ~85x instead of failing loudly.
    """
    df = parse_gcp_csv(
        csv(
            """
Service name,Rounded Cost ($),Total Cost (INR),Usage quantity,Usage unit,Region/Zone
Cloud Storage,100.00,8500.00,500,gibibyte month,asia-south1
"""
        )
    )

    assert df.loc[0, "cost_usd"] == 100.00
    assert df.loc[0, "service_name"] == "cloud_storage"


def test_gcp_rejects_an_unrecognized_schema():
    with pytest.raises(ValueError, match="No recognizable GCP billing columns"):
        parse_gcp_csv(csv("MeterCategory,Quantity\nStorage,5"))


# ------------------------------------------------------------------------- FOCUS

FOCUS_MIXED = csv(
    """
ProviderName,ServiceName,BilledCost,ConsumedQuantity,ChargeDescription,RegionId
Amazon Web Services,Amazon Simple Storage Service,410.00,900,Storage,us-east-1
Microsoft Azure,Virtual Machines,275.00,720,Compute,eastus
Google Cloud,Compute Engine,180.00,744,Compute,us-central1
Oracle Cloud,Object Storage,95.00,300,Storage,ap-mumbai-1
"""
)


def test_focus_emits_the_standard_schema_plus_provider_columns():
    df = parse_focus_csv(FOCUS_MIXED)

    assert list(df.columns) == STANDARD_COLUMNS + ["detected_provider", "provider_name"]


def test_focus_detects_the_provider_per_row():
    df = parse_focus_csv(FOCUS_MIXED)

    assert list(df["detected_provider"][:3]) == ["aws", "azure", "gcp"]


def test_focus_translates_display_names_to_the_compact_pattern_form():
    """Patterns are keyed on amazons3, not FOCUS's Amazon Simple Storage Service."""
    df = parse_focus_csv(FOCUS_MIXED)

    assert df.loc[0, "service_name"] == "amazons3"
    assert df.loc[2, "service_name"] == "compute_engine"


def test_focus_leaves_unmappable_providers_null_rather_than_guessing():
    """A null detected_provider is what the upload endpoint warns about."""
    df = parse_focus_csv(FOCUS_MIXED)
    oracle = df[df["provider_name"] == "Oracle Cloud"].iloc[0]

    assert pd.isna(oracle["detected_provider"])
    assert oracle["service_name"] == "object_storage"


def test_focus_rejects_a_native_provider_export():
    with pytest.raises(ValueError, match="No recognizable FOCUS billing columns"):
        parse_focus_csv(csv("Service,UnblendedCost\nAmazonEC2,1.00"))
