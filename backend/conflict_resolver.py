"""
Conflict Resolution Layer
Applies the three-tier classification to prevent unsafe infrastructure modifications.
"""

def resolve_conflicts(prescriptions: list[dict]) -> list[dict]:
    """
    Evaluates prescriptions against user-declared service tiers and risk thresholds.
    Filters out Tier 1 entirely. Flags Tier 2 and high-risk deltas as conflicted.
    """
    try:
        resolved_prescriptions = []

        for p in prescriptions:
            tier = p.get('tier', 3)
            blockers = p.get('immutable_blockers', [])
            action_risk = p.get('downtime_risk', 'Low')
            cost_usd = p.get('cost_usd', 0.0)
            
            # Recalculate baseline infrastructure risk (from TRD 5.4 heuristics)
            base_risk = 'Low'
            if cost_usd > 500.0:
                base_risk = 'High'
            elif tier == 2:
                base_risk = 'Medium'

            # Condition 1: Tier 1 - Fully Immutable
            # We skip generating a prescription entirely. It drops out of the list.
            if tier == 1:
                continue

            # Initialize conflict flags for the remaining tiers
            p['is_conflicted'] = False
            p['conflict_reason'] = None

            # Condition 2: Tier 2 Core Modification
            # The user said the core is immutable, and the pattern library says 
            # this specific action modifies the core.
            if tier == 2 and 'tier2' in blockers:
                p['is_conflicted'] = True
                p['conflict_reason'] = "Service core is immutable"

            # Condition 3: Unacceptable Risk Delta 
            # The service is currently low risk, but the action introduces high risk.
            elif base_risk == 'Low' and action_risk == 'High':
                p['is_conflicted'] = True
                p['conflict_reason'] = "Risk delta exceeds threshold (Low to High)"

            resolved_prescriptions.append(p)

        return resolved_prescriptions

    except Exception as e:
        raise RuntimeError(f"Conflict resolution failed: {str(e)}")