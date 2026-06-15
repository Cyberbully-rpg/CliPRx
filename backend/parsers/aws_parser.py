"""
AWS Cost Explorer CSV Parser
Normalizes raw AWS billing data into the standard CliPRx 8-column DataFrame.
"""
import pandas as pd
from io import BytesIO
from datetime import datetime

def parse_aws_csv(file_content: bytes) -> pd.DataFrame:
    """
    Parses raw AWS Cost Explorer CSV bytes into a normalized DataFrame.
    Returns the standard 8-column DataFrame required by the ML engine.
    """
    try:
        df = pd.read_csv(BytesIO(file_content))

        df.columns = df.columns.str.lower().str.strip()

        col_map = {
            'service': 'service_name',
            'unblendedcost': 'cost_usd',
            'usagequantity': 'usage_quantity',
            'usagetype': 'usage_type',
            'region': 'region'
        }

        df = df.rename(columns=col_map)

        required_string_cols = ['service_name', 'usage_type', 'region']
        for col in required_string_cols:
            if col not in df.columns:
                df[col] = 'unknown'

        required_numeric_cols = ['cost_usd', 'usage_quantity']
        for col in required_numeric_cols:
            if col not in df.columns:
                df[col] = 0.0

        df['service_name'] = df['service_name'].astype(str).str.lower().str.replace(' ', '_')

        df['cost_usd'] = pd.to_numeric(df['cost_usd'], errors='coerce').fillna(0.0)
        df['usage_quantity'] = pd.to_numeric(df['usage_quantity'], errors='coerce').fillna(0.0)

        df = df[~df['service_name'].str.contains('total', na=False)]

        df = df[df['cost_usd'] > 0]

        current_time = datetime.now()
        df['billing_period_start'] = current_time.replace(day=1)
        df['billing_period_end'] = current_time

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
    except Exception as e:
        raise RuntimeError(f"Failed to parse AWS CSV: {str(e)}")