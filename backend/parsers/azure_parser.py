"""
Azure Cost Management CSV Parser
Normalizes raw Azure billing data into the standard CliPRx 8-column DataFrame.
"""
import pandas as pd
from io import BytesIO
from datetime import datetime

from ._column_utils import any_candidate_present, resolve_columns

# MeterCategory ("Virtual Machines", "Storage") is preferred over
# ConsumedService ("Microsoft.Compute", "Microsoft.Storage") for service_name:
# it's what backend/patterns/azure_patterns.json's trigger_condition values
# are actually written against (e.g. "virtual_machines"), and real exports
# carry both columns together, so which one wins has to be a deliberate
# choice, not whichever pandas keeps on a duplicate-column rename.
# MeterName is the modern (Cost Management / MCA / EA) field for the specific
# meter; "Meter" is the older Enterprise Reporting API's name for the same
# concept, kept as a fallback for that legacy format.
COLUMN_PRIORITY = {
    'service_name': ['metercategory', 'consumedservice'],
    'cost_usd': ['costinbillingcurrency', 'cost'],
    'usage_quantity': ['quantity'],
    'usage_type': ['metername', 'meter'],
    'region': ['resourcelocation'],
}


def parse_azure_csv(file_content: bytes) -> pd.DataFrame:
    """
    Parses raw Azure Cost Management CSV bytes into a normalized DataFrame.
    Returns the standard 8-column DataFrame required by the ML engine.
    """
    try:
        df = pd.read_csv(BytesIO(file_content))

        df.columns = df.columns.str.lower().str.strip()

        original_columns = set(df.columns)
        if not any_candidate_present(original_columns, COLUMN_PRIORITY):
            raise ValueError(
                "No recognizable Azure billing columns found. Expected an Azure "
                "Cost Management export with columns like 'MeterCategory', "
                "'ConsumedService', 'Cost'/'CostInBillingCurrency', 'Quantity', "
                "'MeterName'/'Meter', 'ResourceLocation' -- got: "
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
        raise ValueError("The uploaded Azure CSV file is empty.")
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to parse Azure CSV: {str(e)}")