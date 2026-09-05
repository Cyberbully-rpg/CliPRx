"""
Synthetic Cloud Billing Data Generator (PRD 6.10 / TRD file structure: data/generator.py)

Produces realistic-looking AWS, Azure, GCP, and FOCUS 1.0 billing export CSVs for
testing and demonstration. Each output uses the same raw column headers and casing the real
console exports use (before CliPRx's parsers normalize them), mixes in a large
block of ordinary background spend, and seeds a handful of intentional anomalies
that are known to trigger specific patterns in backend/patterns/*.json -- so a
generated file can be fed straight into the pipeline and produce real prescriptions.

Usage:
    python data/generator.py                      # writes all four formats
    python data/generator.py --provider aws        # writes just one
    python data/generator.py --rows 300 --seed 7   # override size / reproducibility
"""
import argparse
import os
import numpy as np
import pandas as pd

DEFAULT_ROWS = 150
DEFAULT_SEED = 42

AWS_REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-south-1", "sa-east-1"]
AZURE_REGIONS = ["East US", "West Europe", "Southeast Asia", "Central India"]
GCP_REGIONS = ["us-central1", "europe-west1", "asia-south1"]

# (service, usage_type, cost_range) tuples used as ordinary background noise --
# deliberately chosen to NOT match any pattern trigger, so the anomaly rows below
# stand out the way a real anomaly would against a normal bill.
AWS_NOISE = [
    ("AmazonEC2", "BoxUsage:t3.micro", (0.5, 15.0)),
    ("AmazonEC2", "DataTransfer-Out-Bytes", (0.1, 8.0)),
    ("AmazonS3", "Requests-Tier1", (0.1, 5.0)),
    ("AmazonDynamoDB", "WriteCapacityUnit-Hrs", (0.5, 12.0)),
    ("AmazonCloudWatch", "MetricMonitorUsage", (0.5, 6.0)),
    ("AmazonSNS", "PublishUsage", (0.1, 3.0)),
    ("AmazonSQS", "SQS-APIRequest", (0.1, 3.0)),
    ("AWSLambda", "Lambda-GB-Second", (0.5, 10.0)),
]
AWS_ANOMALIES = [
    ("AmazonEC2", "EBS:VolumeUsage.gp2", (400.0, 900.0)),
    ("AmazonEC2", "BoxUsage:m4.2xlarge", (700.0, 1200.0)),
    ("AmazonS3", "TimedStorage-ByteHrs", (400.0, 700.0)),
    ("AmazonRDS", "Multi-AZ-UsageHours", (600.0, 1000.0)),
    ("AmazonVPC", "NatGateway-Bytes", (500.0, 900.0)),
    ("AmazonDynamoDB", "ReadCapacityUnit-Hrs", (300.0, 600.0)),
    ("AmazonRedshift", "Node:ra3.xlplus", (700.0, 1100.0)),
    ("AmazonEC2", "ElasticIP:IdleAddress", (50.0, 150.0)),
    ("AmazonElastiCache", "NodeUsage:cache.r5.xlarge", (400.0, 800.0)),
    ("AmazonEFS", "TimedStorage-ByteHrs", (300.0, 600.0)),
    ("AmazonECS", "Fargate-vCPU-Hours:perCPU", (500.0, 900.0)),
]

AZURE_NOISE = [
    ("Virtual Machines", "B-Series Compute Hours", (0.5, 15.0)),
    ("Storage", "General Purpose v2 Transactions", (0.1, 5.0)),
    ("Azure App Service", "Basic Plan", (1.0, 10.0)),
    ("SQL Database", "Basic DTU", (0.5, 8.0)),
    ("Azure Monitor", "Data Ingestion", (0.5, 6.0)),
]
AZURE_ANOMALIES = [
    ("Storage", "Premium SSD Managed Disks", (400.0, 800.0)),
    ("Virtual Machines", "D-Series VM Compute Hours", (600.0, 1200.0)),
    ("Storage", "Blob Storage Hot Tier", (400.0, 700.0)),
    ("SQL Database", "vCore Provisioned Compute", (600.0, 1000.0)),
    ("Azure App Service", "Premium v3 Plan", (500.0, 900.0)),
    ("Azure Kubernetes Service", "Standard Node Pool Compute Hours", (500.0, 900.0)),
    ("Azure Cache for Redis", "Premium Tier Cache Hours", (300.0, 600.0)),
    ("ExpressRoute", "Circuit Bandwidth Hours", (400.0, 700.0)),
]

GCP_NOISE = [
    ("Compute Engine", "N1 Standard Instance Core", (0.5, 15.0)),
    ("Cloud Storage", "Standard Storage US Multi-Region", (0.1, 5.0)),
    ("Cloud Functions", "Invocations", (0.1, 4.0)),
    ("Cloud Logging", "Log Volume", (0.5, 6.0)),
]
GCP_ANOMALIES = [
    ("Compute Engine", "N1 Standard Instance Core Hours", (500.0, 1000.0)),
    ("Compute Engine", "Persistent Disk SSD", (400.0, 800.0)),
    ("Cloud Storage", "Standard Storage US Multi-Region", (400.0, 700.0)),
    ("Cloud SQL", "Regional HA Instance Hours", (600.0, 1000.0)),
    ("BigQuery", "Analysis On Demand", (700.0, 1300.0)),
    ("Kubernetes Engine", "Standard Node Pool Compute Hours", (500.0, 900.0)),
    ("Cloud Spanner", "Node Compute Hours", (600.0, 1100.0)),
    ("Filestore", "Enterprise Tier Provisioned Capacity", (300.0, 600.0)),
]


# ---------------------------------------------------------------------------
# FOCUS 1.0 (backend/parsers/focus_parser.py)
#
# FOCUS is a vendor-neutral schema, not a cloud -- so unlike the three above, a
# single export legitimately mixes providers, and the parser reads ProviderName
# per row to decide which pattern library each row is matched against. This
# generator mirrors that: every row carries its own provider.
#
# Two further differences from the native generators:
#   * ServiceName is the full human-readable product name FOCUS actually emits
#     ("Amazon Simple Storage Service"), not the compact form the pattern files
#     are keyed on -- focus_parser's SERVICE_NAME_TRANSLATIONS bridges the two,
#     so the names below must stay in that table to trigger anything.
#   * Only service_name-keyed patterns are reachable. FOCUS has no equivalent of
#     AWS's granular usage-type strings (ChargeDescription is free text), so the
#     usage_type-keyed patterns that drive most of the AWS anomalies above simply
#     cannot fire here. The anomaly pool is picked accordingly.
# Keyed by ProviderName so an AWS row doesn't get handed an Azure region. The
# unrecognized-provider entry has no native region vocabulary, hence its own.
FOCUS_REGIONS = {
    "AWS": ["us-east-1", "us-west-2", "eu-west-1"],
    "Microsoft Azure": ["eastus", "westeurope", "southeastasia"],
    "Google Cloud": ["us-central1", "europe-west1", "asia-south1"],
    "Oracle Cloud Infrastructure": ["us-ashburn-1", "eu-frankfurt-1"],
}

# (provider, ServiceName, ChargeDescription, cost_range)
FOCUS_NOISE = [
    ("AWS", "Amazon Simple Queue Service", "Requests", (0.1, 4.0)),
    ("AWS", "Amazon Simple Notification Service", "Notifications delivered", (0.1, 3.0)),
    ("Microsoft Azure", "Azure Monitor", "Data ingestion", (0.5, 6.0)),
    ("Microsoft Azure", "Azure DNS", "Hosted zone", (0.1, 2.0)),
    ("Google Cloud", "Cloud Logging", "Log volume ingested", (0.5, 6.0)),
    ("Google Cloud", "Cloud Pub/Sub", "Message delivery", (0.2, 5.0)),
]

FOCUS_ANOMALIES = [
    ("AWS", "Amazon Simple Storage Service", "Timed storage, standard tier", (400.0, 800.0)),
    ("AWS", "Amazon CloudFront", "Data transfer out to internet", (350.0, 700.0)),
    ("AWS", "Amazon SageMaker", "Notebook instance hours, ml.t3.xlarge", (500.0, 950.0)),
    ("AWS", "Amazon Elastic File System", "Timed storage, standard tier", (300.0, 600.0)),
    ("Microsoft Azure", "Virtual Machines", "D8s v3 compute hours", (700.0, 1200.0)),
    ("Microsoft Azure", "Storage", "Premium SSD managed disks", (400.0, 850.0)),
    ("Microsoft Azure", "SQL Database", "vCore general purpose", (600.0, 1000.0)),
    ("Microsoft Azure", "Azure Kubernetes Service", "Node pool compute hours", (500.0, 900.0)),
    ("Google Cloud", "Compute Engine", "N2 instance core hours", (700.0, 1150.0)),
    ("Google Cloud", "Cloud Storage", "Standard storage, multi-region", (400.0, 750.0)),
    ("Google Cloud", "BigQuery", "Analysis slots, on-demand", (500.0, 900.0)),
    ("Google Cloud", "Cloud Spanner", "Node compute hours", (600.0, 1050.0)),
    # Deliberately a provider PROVIDER_NAME_MAP does not recognize. These rows
    # parse and score normally but can never match a pattern, which is exactly
    # the case services/csv_ingest.py::build_upload_warnings exists to surface --
    # so the sample file exercises that path instead of hiding it.
    ("Oracle Cloud Infrastructure", "Oracle Autonomous Database", "OCPU hours", (400.0, 700.0)),
]


def _build_records(rng, noise_pool, anomaly_pool, regions, rows):
    """Returns a list of {service, usage_type, cost, quantity, region} dicts."""
    records = []
    for _ in range(rows):
        service, usage_type, cost_range = noise_pool[rng.integers(0, len(noise_pool))]
        records.append({
            "service": service,
            "usage_type": usage_type,
            "cost": round(float(rng.uniform(*cost_range)), 4),
            "quantity": round(float(rng.uniform(1.0, 500.0)), 2),
            "region": regions[rng.integers(0, len(regions))],
        })
    for service, usage_type, cost_range in anomaly_pool:
        records.append({
            "service": service,
            "usage_type": usage_type,
            "cost": round(float(rng.uniform(*cost_range)), 2),
            "quantity": round(float(rng.uniform(50.0, 1000.0)), 2),
            "region": regions[rng.integers(0, len(regions))],
        })
    rng.shuffle(records)
    return records


def generate_aws(rows: int = DEFAULT_ROWS, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records = _build_records(rng, AWS_NOISE, AWS_ANOMALIES, AWS_REGIONS, rows)
    return pd.DataFrame([{
        "Service": r["service"],
        "UnblendedCost": r["cost"],
        "UsageQuantity": r["quantity"],
        "UsageType": r["usage_type"],
        "Region": r["region"],
    } for r in records])


def generate_azure(rows: int = DEFAULT_ROWS, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records = _build_records(rng, AZURE_NOISE, AZURE_ANOMALIES, AZURE_REGIONS, rows)
    return pd.DataFrame([{
        "MeterCategory": r["service"],
        "Cost": r["cost"],
        "Quantity": r["quantity"],
        "Meter": r["usage_type"],
        "ResourceLocation": r["region"],
    } for r in records])


def generate_gcp(rows: int = DEFAULT_ROWS, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records = _build_records(rng, GCP_NOISE, GCP_ANOMALIES, GCP_REGIONS, rows)
    return pd.DataFrame([{
        "service.description": r["service"],
        "cost": r["cost"],
        "usage.amount": r["quantity"],
        "usage.unit": r["usage_type"],
        "location.region": r["region"],
    } for r in records])


def _focus_region(rng, provider: str) -> str:
    regions = FOCUS_REGIONS.get(provider, ["us-east-1"])
    return regions[rng.integers(0, len(regions))]


def generate_focus(rows: int = DEFAULT_ROWS, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    """
    Emits FOCUS 1.0 column names (BilledCost/ConsumedQuantity/ProviderName/...),
    which focus_parser resolves via its own COLUMN_PRIORITY table. Rows carry a
    per-row provider rather than a single file-level one -- see FOCUS_NOISE above.
    """
    rng = np.random.default_rng(seed)

    records = []
    for _ in range(rows):
        provider, service, charge, cost_range = FOCUS_NOISE[rng.integers(0, len(FOCUS_NOISE))]
        records.append((provider, service, charge, round(float(rng.uniform(*cost_range)), 4)))
    for provider, service, charge, cost_range in FOCUS_ANOMALIES:
        records.append((provider, service, charge, round(float(rng.uniform(*cost_range)), 2)))
    rng.shuffle(records)

    return pd.DataFrame([{
        "ProviderName": provider,
        "ServiceName": service,
        "ChargeDescription": charge,
        "BilledCost": cost,
        "ConsumedQuantity": round(float(rng.uniform(1.0, 800.0)), 2),
        "RegionId": _focus_region(rng, provider),
        "BillingCurrency": "USD",
    } for provider, service, charge, cost in records])


GENERATORS = {
    "aws": generate_aws,
    "azure": generate_azure,
    "gcp": generate_gcp,
    "focus": generate_focus,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["aws", "azure", "gcp", "focus", "all"], default="all")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS, help="Background noise rows (anomalies are added on top)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out-dir", default=os.path.join(os.path.dirname(__file__), "samples"))
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    providers = list(GENERATORS.keys()) if args.provider == "all" else [args.provider]

    for provider in providers:
        df = GENERATORS[provider](rows=args.rows, seed=args.seed)
        out_path = os.path.join(args.out_dir, f"sample_{provider}.csv")
        df.to_csv(out_path, index=False)
        print(f"Wrote {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()
