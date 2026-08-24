"""
ROI Ranker Engine
Calculates Return on Investment for each prescription and sorts them by priority.
"""

def calculate_roi_and_rank(prescriptions: list[dict]) -> list[dict]:
    """
    Applies TRD 5.6 ROI formula: (monthly_savings / engineering_hours) * risk_multiplier.
    Sorts the output descending by ROI. Conflicted items get ROI 0 and drop to the bottom.
    """
    try:
        risk_multipliers = {
            'Low': 1.0,
            'Medium': 0.7,
            'High': 0.4
        }

        for p in prescriptions:
            # Condition 1: Conflicted items are instantly deprioritized
            if p.get('is_conflicted', False):
                p['roi_score'] = 0.0
                continue

            # Calculate average estimated savings
            savings_min = p.get('savings_min', 0.0)
            savings_max = p.get('savings_max', 0.0)
            monthly_savings = (savings_min + savings_max) / 2.0

            # Calculate average estimated engineering effort
            hours_min = p.get('engineering_hours_min', 0.0)
            hours_max = p.get('engineering_hours_max', 0.0)
            engineering_hours = (hours_min + hours_max) / 2.0

            # Prevent DivisionByZero exception if a pattern claims 0 hours of work
            if engineering_hours <= 0:
                engineering_hours = 0.1 

            risk_level = p.get('risk_level', 'High')
            multiplier = risk_multipliers.get(risk_level, 0.4)

            # EMV-style confidence weighting (PMI PMBOK Expected Monetary Value:
            # EMV = Probability x Impact): anomaly_score is the isolation forest's
            # confidence that this row is genuinely anomalous, so a borderline match
            # right at the threshold counts for less than a highly-confident one.
            confidence = p.get('anomaly_score', 1.0)

            # Core TRD ROI Formula, extended with EMV-style confidence weighting
            raw_roi = (monthly_savings / engineering_hours) * multiplier * confidence
            p['roi_score'] = round(raw_roi, 4)

        # Sort the prescriptions: Primary sort by ROI, secondary sort by max savings to break ties
        sorted_prescriptions = sorted(
            prescriptions, 
            key=lambda x: (x.get('roi_score', 0.0), x.get('savings_max', 0.0)), 
            reverse=True
        )

        # Inject the final rank position back into the dictionaries
        for index, p in enumerate(sorted_prescriptions):
            p['rank_position'] = index + 1

        return sorted_prescriptions

    except Exception as e:
        raise RuntimeError(f"ROI ranking failed: {str(e)}")