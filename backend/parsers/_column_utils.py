"""
Shared column-resolution helper for the provider parsers.

Real-world billing exports (AWS CUR, Azure cost details, GCP BigQuery export)
commonly include MULTIPLE columns that could plausibly map to the same
normalized field -- e.g. Azure cost-details rows carry both MeterCategory and
ConsumedService, either of which could be "service_name". A plain
`df.rename(columns=col_map)` with two source keys mapping to the same target
produces duplicate-named columns, and pandas' resulting resolution order is
an implementation detail, not a documented one -- so which source column
"wins" a given field ends up unpredictable rather than deliberately chosen.
"""
import pandas as pd


def resolve_columns(df: pd.DataFrame, priority: dict) -> pd.DataFrame:
    """priority: {target_col: [candidate source col names, most preferred first]}.
    Renames the first present candidate for each target column; every other
    candidate for that target is left untouched (and dropped later by the
    caller's final column selection). Returns the renamed DataFrame."""
    rename = {}
    for target, candidates in priority.items():
        for candidate in candidates:
            if candidate in df.columns and candidate not in rename:
                rename[candidate] = target
                break
    return df.rename(columns=rename)


def any_candidate_present(df_columns, priority: dict) -> bool:
    """True if at least one candidate column for any target field is present
    -- used to distinguish "wrong schema entirely" from "partially matched"."""
    columns = set(df_columns)
    return any(candidate in columns for candidates in priority.values() for candidate in candidates)
