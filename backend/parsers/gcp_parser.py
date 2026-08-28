"""
GCP Billing CSV Parser
Normalizes raw GCP billing data into the standard CliPRx 8-column DataFrame.
"""
import pandas as pd
from io import BytesIO
from datetime import datetime

from ._column_utils import any_candidate_present, resolve_columns

# service.description ("Compute Engine") is the real BigQuery billing export's
# field name and is preferred over the generic "description" fallback (which
# in a real export is a line-item-level description, not a service name).
#
# 'service name'/'usage quantity'/'usage unit'/'region/zone' and the cost
# columns below are a third real-world GCP shape seen in the wild: a
# spaced-header report/BI-tool export rather than the dotted BigQuery export
# or the Billing Reports console's own field names. Its "Unrounded Cost ($)"
# and "Rounded Cost ($)" are both USD -- deliberately preferred over the
# unrounded value's extra precision -- but this same export also carries a
# "Total Cost (INR)" column that must NEVER be treated as cost_usd: it's a
# different currency, and mapping it in would silently overstate every cost
# by roughly the USD/INR exchange rate (~80-90x) rather than fail loudly.
COLUMN_PRIORITY = {
    'service_name': ['service.description', 'description', 'service name'],
    'cost_usd': ['cost', 'unrounded cost ($)', 'rounded cost ($)'],
    'usage_quantity': ['usage.amount', 'usage', 'usage quantity'],
    'usage_type': ['usage.unit', 'usage unit'],
    'region': ['location.region', 'region', 'region/zone'],
}


def parse_gcp_csv(file_content: bytes) -> pd.DataFrame:
    """
    Parses raw GCP Billing export CSV bytes into a normalized DataFrame.
    Returns the standard 8-column DataFrame required by the ML engine.
    """
    try:
        df = pd.read_csv(BytesIO(file_content))

        df.columns = df.columns.str.lower().str.strip()

        original_columns = set(df.columns)
        if not any_candidate_present(original_columns, COLUMN_PRIORITY):
            raise ValueError(
                "No recognizable GCP billing columns found. Expected a GCP "
                "Billing export with columns like 'Service.description'/"
                "'Description', 'Cost', 'Usage.amount'/'Usage', 'Usage.unit', "
                "'Location.region'/'Region' -- got: "
                f"{', '.join(sorted(original_columns)) or '(no columns)'}. "
                "This looks like a different export format (e.g. FOCUS, a raw "
                "billing file, or another cloud provider)."
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
        raise ValueError("The uploaded GCP CSV file is empty.")
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to parse GCP CSV: {str(e)}")
        