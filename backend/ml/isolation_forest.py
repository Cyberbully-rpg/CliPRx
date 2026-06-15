"""
Isolation Forest Anomaly Detection Engine
Applies unsupervised ML to flag statistically abnormal cloud spending patterns.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

def run_anomaly_detection(df: pd.DataFrame, threshold: float = 0.65) -> pd.DataFrame:
    """
    Ingests normalized 8-column billing DataFrame.
    Applies Isolation Forest to score anomalies between 0.0 and 1.0.
    Falls back to a median-multiplier rule for very small datasets.
    """
    try:
        # Fallback condition for small datasets (TRD 5.2)
        if len(df) < 10:
            median_cost = df['cost_usd'].median()
            # If cost is more than double the median, flag as severe anomaly (0.99)
            df['anomaly_score'] = np.where(df['cost_usd'] > (2 * median_cost), 0.99, 0.10)
            return df

        # Feature Engineering: Derive cost per unit
        df['cost_per_unit'] = np.where(df['usage_quantity'] > 0, 
                                       df['cost_usd'] / df['usage_quantity'], 
                                       0.0)
        
        features = ['cost_usd', 'usage_quantity', 'cost_per_unit']
        X = df[features].copy()

        # Scale features so large usage quantities don't overpower small USD costs
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Initialize and fit the Isolation Forest
        model = IsolationForest(n_estimators=100, contamination='auto', random_state=42)
        model.fit(X_scaled)

        # Scikit-learn returns lower (negative) scores for anomalies. 
        # We negate it so higher = more anomalous.
        raw_scores = -model.decision_function(X_scaled)
        
        # Min-Max normalization to constrain scores between 0.0 and 1.0
        min_score = raw_scores.min()
        max_score = raw_scores.max()
        
        if max_score > min_score:
            normalized_scores = (raw_scores - min_score) / (max_score - min_score)
        else:
            normalized_scores = np.zeros(len(raw_scores))
            
        df['anomaly_score'] = normalized_scores.round(4)

        # Clean up the derived column so we don't pollute the downstream DataFrame
        df = df.drop(columns=['cost_per_unit'])
        
        return df

    except Exception as e:
        raise RuntimeError(f"Anomaly detection engine failed: {str(e)}")