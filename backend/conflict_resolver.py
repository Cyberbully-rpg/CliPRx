"""
Conflict Resolution Layer
Applies the three-tier classification to prevent unsafe infrastructure modifications.
"""

RISK_LEVELS = {'Low': 1, 'Medium': 2, 'High': 3}


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
            # The action introduces MORE risk than the service currently carries, at
            # any level (Low->Medium, Low->High, Medium->High) -- not just Low->High.
            # A baseline that's already High can't register a further increase (High
            # is the ceiling), but Low/Medium baselines are no longer exempt just
            # because the jump doesn't happen to land exactly on Low->High.
            elif RISK_LEVELS.get(action_risk, 1) > RISK_LEVELS.get(base_risk, 1):
                p['is_conflicted'] = True
                p['conflict_reason'] = f"Risk delta exceeds threshold ({base_risk} to {action_risk})"

            resolved_prescriptions.append(p)

        return resolved_prescriptions

    except Exception as e:
        raise RuntimeError(f"Conflict resolution failed: {str(e)}")