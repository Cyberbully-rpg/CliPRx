"""
Conflict Resolution Layer
Applies the three-tier classification to prevent unsafe infrastructure modifications.
"""

RISK_LEVELS = {'Low': 1, 'Medium': 2, 'High': 3}


def _is_commitment_pricing(pattern_id: str) -> bool:
    return any(m in pattern_id for m in ('reserved_instance', 'committed_use_discount', 'reserved_capacity'))


def _is_spot_pricing(pattern_id: str) -> bool:
    return any(m in pattern_id for m in ('spot', 'preemptible'))


def resolve_conflicts(prescriptions: list[dict]) -> list[dict]:
    """
    Evaluates prescriptions against user-declared service tiers and risk thresholds.
    Filters out Tier 1 entirely. Flags Tier 2, high-risk deltas, and mutually
    exclusive pricing-model recommendations as conflicted.
    """
    try:
        resolved_prescriptions = []

        # Pre-pass: find services recommended for both a commitment-pricing action
        # (Reserved Instance / Savings Plan / Committed Use Discount) and a
        # spot/preemptible-pricing action. Cloud vendors document these as mutually
        # exclusive -- AWS Savings Plans don't apply to Spot usage, Azure offers no
        # Reservations for Spot VMs, and GCP CUDs explicitly can't combine with
        # Spot/preemptible VMs -- so recommending both for the same service is a
        # genuine contradiction, not just overlapping advice.
        commitment_services = set()
        spot_services = set()
        for p in prescriptions:
            pattern_id = p.get('pattern_id', '')
            service_name = p.get('service_name')
            if _is_commitment_pricing(pattern_id):
                commitment_services.add(service_name)
            elif _is_spot_pricing(pattern_id):
                spot_services.add(service_name)
        pricing_conflict_services = commitment_services & spot_services

        for p in prescriptions:
            tier = p.get('tier', 3)
            blockers = p.get('immutable_blockers', [])
            action_risk = p.get('downtime_risk', 'Low')

            # Baseline infrastructure risk, as computed by failure_scorer.py (TRD 5.4
            # heuristics plus the complexity/cost-impact extensions) -- reused as-is
            # rather than re-derived here, so the two stages can't drift out of sync.
            base_risk = p.get('infrastructure_risk_level', 'Low')

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

            # Condition 4: Mutually Exclusive Pricing Model
            # This service has both a commitment-pricing and a spot/preemptible
            # recommendation -- vendor-documented as incompatible (see module docstring).
            elif p.get('service_name') in pricing_conflict_services and (
                _is_commitment_pricing(p.get('pattern_id', '')) or _is_spot_pricing(p.get('pattern_id', ''))
            ):
                p['is_conflicted'] = True
                p['conflict_reason'] = (
                    "Mutually exclusive with another recommended pricing model for this "
                    "service (commitment discounts don't apply to spot/preemptible capacity)"
                )

            resolved_prescriptions.append(p)

        return resolved_prescriptions

    except Exception as e:
        raise RuntimeError(f"Conflict resolution failed: {str(e)}")
