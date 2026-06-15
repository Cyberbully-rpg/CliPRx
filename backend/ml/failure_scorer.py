"""
Failure Risk Scorer
Estimates the business risk and financial impact of system failure for flagged services.
"""

def calculate_risk(service_name: str, cost_usd: float, tier: int) -> dict:
    """
    Applies TRD Section 5.4 rule-based heuristics to estimate failure risk.
    """
    try:
        risk_level = "Low"
        failure_cost_estimate = None

        # TRD Rule: cost > $500/month triggers High risk
        if cost_usd > 500.0:
            risk_level = "High"
        
        # TRD Rule: Tier 2 (Immutable Core) carries inherently higher structural risk
        elif tier == 2:
            risk_level = "Medium"

        # Calculate failure cost estimate for High risk items (TRD: 4x monthly cost)
        if risk_level == "High":
            failure_cost_estimate = round(cost_usd * 4.0, 2)

        return {
            "risk_level": risk_level,
            "failure_cost_estimate": failure_cost_estimate
        }

    except Exception as e:
        raise RuntimeError(f"Failure risk calculation failed for {service_name}: {str(e)}")

def apply_failure_scores(prescriptions: list[dict]) -> list[dict]:
    """
    Iterates over the raw prescriptions and injects failure risk scores.
    Reconciles the infrastructure risk with the pattern's inherent action risk.
    """
    for p in prescriptions:
        # Calculate the base infrastructure risk
        risk_data = calculate_risk(
            service_name=p['service_name'],
            cost_usd=p['cost_usd'],
            tier=p['tier']
        )
        
        # The JSON pattern library also provided an inherent 'downtime_risk' for the action.
        pattern_risk = p.get('downtime_risk', 'Low')
        
        # Risk hierarchy: We take the higher of the two risks. 
        # You shouldn't downgrade a High-risk database action just because the DB is cheap.
        risk_hierarchy = {'Low': 1, 'Medium': 2, 'High': 3}
        
        if risk_hierarchy[risk_data['risk_level']] > risk_hierarchy[pattern_risk]:
            final_risk = risk_data['risk_level']
        else:
            final_risk = pattern_risk
            
        p['risk_level'] = final_risk
        
        # Only apply failure cost estimate if the final reconciled risk is High
        if final_risk == "High":
            p['failure_cost_estimate'] = risk_data['failure_cost_estimate'] or round(p['cost_usd'] * 4.0, 2)
        else:
            p['failure_cost_estimate'] = None
            
    return prescriptions