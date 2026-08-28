"""
AWS Cost Explorer CSV Parser
Normalizes raw AWS billing data into the standard CliPRx 8-column DataFrame.
"""
import pandas as pd
from io import BytesIO
from datetime import datetime

from ._column_utils import any_candidate_present, resolve_columns

# Two real AWS export shapes are supported:
#  - the simplified "Service,UnblendedCost,UsageQuantity,UsageType,Region"
#    layout (Cost Explorer's own quick CSV download, and most tutorials/demos)
#  - the actual AWS Cost and Usage Report (CUR), whose CSV columns are
#    slash-delimited category/field pairs, e.g. "lineItem/UnblendedCost" --
#    the format most real billing pipelines and FinOps tools ingest.
# product/region (a clean region like "us-east-1") is preferred over
# lineItem/AvailabilityZone (an AZ like "us-east-1a") for the region field,
# since the latter would need suffix-stripping to be usable as a region.
COLUMN_PRIORITY = {
    'service_name': ['service', 'lineitem/productcode', 'product/productname'],
    'cost_usd': ['unblendedcost', 'lineitem/unblendedcost'],
    'usage_quantity': ['usagequantity', 'lineitem/usageamount'],
    'usage_type': ['usagetype', 'lineitem/usagetype'],
    'region': ['region', 'product/region'],
}


def parse_aws_csv(file_content: bytes) -> pd.DataFrame:
    """
    Parses raw AWS Cost Explorer or Cost and Usage Report (CUR) CSV bytes into
    a normalized DataFrame. Returns the standard 8-column DataFrame required
    by the ML engine.
    """
    try:
        df = pd.read_csv(BytesIO(file_content))

        df.columns = df.columns.str.lower().str.strip()

        original_columns = set(df.columns)
        if not any_candidate_present(original_columns, COLUMN_PRIORITY):
            raise ValueError(
                "No recognizable AWS billing columns found. Expected an AWS Cost "
                "Explorer export (columns like 'Service', 'UnblendedCost', "
                "'UsageQuantity', 'UsageType', 'Region') or a Cost and Usage Report "
                "(columns like 'lineItem/UnblendedCost', 'lineItem/UsageType') "
                f"-- got: {', '.join(sorted(original_columns)) or '(no columns)'}. "
                "This looks like a different export format (e.g. FOCUS, or another "
                "cloud provider)."
            )

        df = resolve_columns(df, COLUMN_PRIORITY)

        required_string_cols = ['service_name', 'usage_type', 'region']
        for col in required_string_cols:
            if col not in df.columns:
                df[col] = 'unknown'

        required_numeric_cols = ['cost_usd', 'usage_quantity']
        for col in required_numeric_cols:
            if col not in df.columns:
                df[col] = 0.0

        df['service_name'] = df['service_name'].astype(str).str.strip().str.lower().str.replace(' ', '_')

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

        df = df[~df['service_name'].str.contains('total', na=False)]

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
            'tier'
        ]
        
        return df[final_columns].reset_index(drop=True)

    except pd.errors.EmptyDataError:
        raise ValueError("The uploaded AWS CSV file is empty.")
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to parse AWS CSV: {str(e)}")