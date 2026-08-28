"""
FOCUS 1.0 CSV Parser
Normalizes a FinOps Open Cost and Usage Specification (FOCUS) export into the
standard CliPRx 8-column DataFrame -- PLUS one extra column, detected_provider,
that the other three parsers never produce (see below).

FOCUS is not itself a cloud -- it's a vendor-neutral schema that can describe
billing data from any provider (it carries its own ProviderName column; see
sample data at https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS-Sample-Data).
That creates two problems the other parsers don't have:

1. Which pattern library (backend/patterns/{aws,azure,gcp}_patterns.json)
   should a FOCUS row match against? Answered by reading ProviderName per row
   and stamping a `detected_provider` column -- ml/pattern_matcher.py checks
   for this column and, when present, matches each provider's rows against
   its own pattern library instead of a single one passed in by the caller.
   This is the one deliberate exception to the "standard 8-column schema"
   noted in CLAUDE.md: every other stage ignores the extra column by name,
   so it doesn't break the "field names are the contract" rule, it extends it.

2. FOCUS's ServiceName is a full human-readable product name (e.g. "Amazon
   Simple Queue Service"), not the compact native form the pattern libraries
   are written against (e.g. "amazonsqs"). SERVICE_NAME_TRANSLATIONS maps the
   normalized display name back to that compact form per provider, for every
   service any pattern actually triggers on. A FOCUS service with no entry
   here still gets parsed and scored -- it just won't match a
   service_name-keyed pattern, the same as any unrecognized service today.

Known limitation: patterns keyed on `usage_type` (not `service_name`) expect
each provider's own granular usage-type string (e.g. AWS's
"USW2-BoxUsage:m2.2xlarge"), which FOCUS does not carry -- ChargeDescription
is the closest analog but is free text, not that specific format. Those
patterns are unlikely to match FOCUS-derived rows regardless of translation.
"""
import pandas as pd
from io import BytesIO
from datetime import datetime

from ._column_utils import any_candidate_present, resolve_columns

COLUMN_PRIORITY = {
    'service_name': ['servicename', 'servicecategory'],
    'cost_usd': ['billedcost', 'effectivecost'],
    'usage_quantity': ['consumedquantity', 'pricingquantity'],
    'usage_type': ['chargedescription'],
    'region': ['regionid', 'regionname'],
    'provider_name': ['providername'],
}

# FOCUS's ProviderName values, mapped to CliPRx's internal provider keys (used
# to pick which patterns/<provider>_patterns.json to match a row against).
PROVIDER_NAME_MAP = {
    'aws': 'aws',
    'amazon web services': 'aws',
    'amazon web services, inc.': 'aws',
    'azure': 'azure',
    'microsoft': 'azure',
    'microsoft azure': 'azure',
    'gcp': 'gcp',
    'google': 'gcp',
    'google cloud': 'gcp',
    'google cloud platform': 'gcp',
}

# Real display names -> the compact form backend/patterns/aws_patterns.json's
# trigger_condition values and PATTERN_ALLOWED_SERVICES (ml/pattern_matcher.py)
# are written against. Keys are already lowercased/underscored, matching how
# _translate_service_name() normalizes the incoming FOCUS ServiceName.
AWS_SERVICE_NAME_TRANSLATIONS = {
    'amazon_elastic_compute_cloud': 'amazonec2',
    'amazon_elastic_compute_cloud_compute': 'amazonec2',
    'ec2_other': 'amazonec2',
    'amazon_elastic_block_store': 'amazonebs',
    'amazon_simple_storage_service': 'amazons3',
    'amazon_relational_database_service': 'amazonrds',
    'amazon_virtual_private_cloud': 'amazonvpc',
    'amazon_dynamodb': 'amazondynamodb',
    'amazon_redshift': 'amazonredshift',
    'elastic_load_balancing': 'amazonelasticloadbalancing',
    'aws_vpn': 'awsvpn',
    'aws_site_to_site_vpn': 'awsvpn',
    'amazon_cloudwatch': 'amazoncloudwatch',
    'amazoncloudwatch': 'amazoncloudwatch',
    'aws_cloudtrail': 'awscloudtrail',
    'aws_backup': 'awsbackup',
    'aws_lambda': 'awslambda',
    'amazon_elastic_container_service': 'amazonecs',
    'amazon_elasticache': 'amazonelasticache',
    'amazon_cloudfront': 'amazoncloudfront',
    'amazon_sagemaker': 'amazonsagemaker',
    'amazon_elastic_file_system': 'amazonefs',
}

AZURE_SERVICE_NAME_TRANSLATIONS = {
    'storage': 'storage',
    'virtual_machines': 'virtual_machines',
    'sql_database': 'sql_database',
    'azure_sql_database': 'sql_database',
    'azure_app_service': 'azure_app_service',
    'app_service': 'azure_app_service',
    'azure_cosmos_db': 'cosmos_db',
    'cosmos_db': 'cosmos_db',
    'azure_functions': 'azure_functions',
    'functions': 'azure_functions',
    'azure_kubernetes_service': 'azure_kubernetes_service',
    'load_balancer': 'load_balancer',
    'vpn_gateway': 'vpn_gateway',
    'azure_backup': 'azure_backup',
    'backup': 'azure_backup',
    'azure_synapse_analytics': 'synapse_analytics',
    'synapse_analytics': 'synapse_analytics',
    'devtest_labs': 'devtest_labs',
    'azure_lab_services': 'devtest_labs',
    'container_registry': 'container_registry',
    'azure_databricks': 'azure_databricks',
    'event_hubs': 'event_hubs',
    'azure_cache_for_redis': 'azure_cache_for_redis',
    'expressroute': 'expressroute',
}

GCP_SERVICE_NAME_TRANSLATIONS = {
    'compute_engine': 'compute_engine',
    'cloud_storage': 'cloud_storage',
    'cloud_sql': 'cloud_sql',
    'bigquery': 'bigquery',
    'kubernetes_engine': 'kubernetes_engine',
    'cloud_functions': 'cloud_functions',
    'cloud_run': 'cloud_run',
    'cloud_load_balancing': 'cloud_load_balancing',
    'cloud_interconnect': 'cloud_interconnect',
    'cloud_dataflow': 'dataflow',
    'dataflow': 'dataflow',
    'cloud_dataproc': 'dataproc',
    'dataproc': 'dataproc',
    'cloud_memorystore_for_redis': 'memorystore',
    'memorystore': 'memorystore',
    'cloud_composer': 'cloud_composer',
    'artifact_registry': 'artifact_registry',
    'cloud_spanner': 'cloud_spanner',
    'cloud_filestore': 'filestore',
    'filestore': 'filestore',
}

SERVICE_NAME_TRANSLATIONS = {
    'aws': AWS_SERVICE_NAME_TRANSLATIONS,
    'azure': AZURE_SERVICE_NAME_TRANSLATIONS,
    'gcp': GCP_SERVICE_NAME_TRANSLATIONS,
}


def _translate_service_name(raw_name: str, provider) -> str:
    normalized = str(raw_name).strip().lower().replace(' ', '_').replace('-', '_')
    table = SERVICE_NAME_TRANSLATIONS.get(provider, {})
    return table.get(normalized, normalized)


def parse_focus_csv(file_content: bytes) -> pd.DataFrame:
    """
    Parses raw FOCUS 1.0 CSV bytes into a normalized DataFrame. Returns the
    standard 8 columns required by the ML engine, PLUS `detected_provider`
    (one of 'aws'/'azure'/'gcp'/None per row) -- see module docstring.
    """
    try:
        df = pd.read_csv(BytesIO(file_content))

        df.columns = df.columns.str.lower().str.strip()

        original_columns = set(df.columns)
        if not any_candidate_present(original_columns, COLUMN_PRIORITY):
            raise ValueError(
                "No recognizable FOCUS billing columns found. Expected a FOCUS "
                "1.0 export with columns like 'ServiceName', 'BilledCost', "
                "'ConsumedQuantity', 'ProviderName' -- got: "
                f"{', '.join(sorted(original_columns)) or '(no columns)'}. "
                "This looks like a different export format (e.g. a native "
                "AWS/Azure/GCP export rather than FOCUS)."
            )

        df = resolve_columns(df, COLUMN_PRIORITY)

        required_string_cols = ['service_name', 'usage_type', 'region', 'provider_name']
        for col in required_string_cols:
            if col not in df.columns:
                df[col] = 'unknown'

        required_numeric_cols = ['cost_usd', 'usage_quantity']
        for col in required_numeric_cols:
            if col not in df.columns:
                df[col] = 0.0

        df['detected_provider'] = (
            df['provider_name'].astype(str).str.strip().str.lower().map(PROVIDER_NAME_MAP)
        )

        df['service_name'] = df.apply(
            lambda r: _translate_service_name(r['service_name'], r['detected_provider']), axis=1
        )

        # Strip thousands separators / currency symbols before numeric coercion, so
        # values like "1,240.50" or "$450.00" don't silently become NaN -> 0.0
        df['cost_usd'] = pd.to_numeric(
            df['cost_usd'].astype(str).str.replace(',', '', regex=False).str.replace('$', '', regex=False).str.strip(),
            errors='coerce'
        ).fillna(0.0)
        df['usage_quantity'] = pd.to_numeric(
            df['usage_quantity'].astype(str).str.replace(',', '', regex=False).str.strip(),
            errors='coerce'
        ).fillna(0.0)

        df = df[df['cost_usd'] > 0]

        current_time = datetime.now()
        df['billing_period_start'] = current_time.replace(day=1)
        df['billing_period_end'] = current_time

        # Honor a 'tier' column if the source CSV provides one (e.g. "tier1", "2"),
        # defaulting to 3 (fully mutable) for missing/unrecognized values.
        if 'tier' in df.columns:
            extracted_tier = pd.to_numeric(
                df['tier'].astype(str).str.extract(r'(\d)', expand=False), errors='coerce'
            )
            df['tier'] = extracted_tier.where(extracted_tier.isin([1, 2, 3]), 3).astype(int)
        else:
            df['tier'] = 3

        final_columns = [
            'service_name',
            'cost_usd',
            'usage_quantity',
            'usage_type',
            'region',
            'billing_period_start',
            'billing_period_end',
            'tier',
            'detected_provider',
        ]

        return df[final_columns].reset_index(drop=True)

    except pd.errors.EmptyDataError:
        raise ValueError("The uploaded FOCUS CSV file is empty.")
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to parse FOCUS CSV: {str(e)}")
