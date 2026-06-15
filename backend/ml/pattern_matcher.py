"""
Prescription Pattern Matcher
Bridges the ML anomaly detection with the deterministic JSON pattern libraries.
"""
import pandas as pd
import json
import os

def match_patterns(df: pd.DataFrame, cloud_provider: str, anomaly_threshold: float = 0.65) -> list[dict]:
    """
    Filters DataFrame for anomalies, loads the correct cloud pattern library,
    and returns a list of raw prescription dictionaries for matching conditions.
    """
    try:
        # 1. Filter out normal traffic to save compute time
        anomalies = df[df['anomaly_score'] >= anomaly_threshold].copy()
        
        if anomalies.empty:
            return []

        # 2. Resolve absolute path to the JSON pattern files
        base_dir = os.path.dirname(os.path.abspath(__file__))
        pattern_file = os.path.join(base_dir, '..', 'patterns', f"{cloud_provider.lower()}_patterns.json")
        
        if not os.path.exists(pattern_file):
            raise FileNotFoundError(f"Pattern library not found for provider: {cloud_provider}")

        with open(pattern_file, 'r', encoding='utf-8') as f:
            patterns = json.load(f)

        raw_prescriptions = []

        # 3. Evaluate each anomaly against the pattern library
        for index, row in anomalies.iterrows():
            for pattern in patterns:
                condition = pattern.get('trigger_condition', {})
                target_field = condition.get('field')
                operator = condition.get('operator')
                target_value = condition.get('value', '').lower()

                # Ensure the field exists in our normalized DataFrame
                if target_field not in row:
                    continue

                actual_value = str(row[target_field]).lower()
                is_match = False

                # Dynamic operator evaluation
                if operator == 'equals' and actual_value == target_value:
                    is_match = True
                elif operator == 'contains' and target_value in actual_value:
                    is_match = True

                # If the logic triggers, build the raw prescription object
                if is_match:
                    savings_min = row['cost_usd'] * pattern['savings_range_min_pct']
                    savings_max = row['cost_usd'] * pattern['savings_range_max_pct']

                    raw_prescriptions.append({
                        'service_name': row['service_name'],
                        'tier': row['tier'],
                        'anomaly_score': row['anomaly_score'],
                        'cost_usd': row['cost_usd'],
                        'pattern_id': pattern['pattern_id'],
                        'recommended_action': pattern['recommended_action'],
                        'savings_min': round(savings_min, 2),
                        'savings_max': round(savings_max, 2),
                        'engineering_hours_min': pattern['engineering_hours_min'],
                        'engineering_hours_max': pattern['engineering_hours_max'],
                        'downtime_risk': pattern['downtime_risk'],
                        'immutable_blockers': pattern['immutable_blockers']
                    })

        return raw_prescriptions

    except Exception as e:
        raise RuntimeError(f"Pattern matching engine failed: {str(e)}")