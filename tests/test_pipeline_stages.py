"""
Tests for pipeline stages 2-6: anomaly detection, pattern matching, risk
scoring, conflict resolution, and ROI ranking.

Nothing here uses typed models -- field names are the only contract between
stages -- so these tests double as the executable spec for that contract.
"""
import pandas as pd
import pytest

from conflict_resolver import resolve_conflicts
from ml.failure_scorer import apply_failure_scores, calculate_risk, compute_usage_variance_flags
from ml.isolation_forest import run_anomaly_detection
from ml.pattern_matcher import match_patterns
from roi_ranker import calculate_roi_and_rank


def billing_row(**overrides) -> dict:
    row = {
        "service_name": "amazonec2",
        "cost_usd": 100.0,
        "usage_quantity": 720.0,
        "usage_type": "BoxUsage:m5.large",
        "region": "us-east-1",
        "tier": 3,
    }
    row.update(overrides)
    return row


def prescription(**overrides) -> dict:
    """A stage-3 output, as ml/pattern_matcher.py builds it."""
    p = {
        "service_name": "amazonec2",
        "tier": 3,
        "anomaly_score": 1.0,
        "cost_usd": 100.0,
        "pattern_id": "aws_ebs_gp2_to_gp3_001",
        "recommended_action": "Migrate gp2 volumes to gp3.",
        "savings_min": 20.0,
        "savings_max": 40.0,
        "engineering_hours_min": 1.0,
        "engineering_hours_max": 3.0,
        "downtime_risk": "Low",
        "complexity": "Low",
        "immutable_blockers": ["tier1"],
        "infrastructure_risk_level": "Low",
        "risk_level": "Low",
    }
    p.update(overrides)
    return p


# ------------------------------------------------- stage 2: anomaly detection


def test_small_datasets_skip_the_forest_and_use_the_median_heuristic():
    """Under 10 rows there are too few points to fit a meaningful forest."""
    df = pd.DataFrame([billing_row(cost_usd=c) for c in [10, 10, 10, 10, 500]])

    scored = run_anomaly_detection(df)

    assert scored.loc[4, "anomaly_score"] == 0.99, "cost > 2x median should be flagged"
    assert set(scored.loc[:3, "anomaly_score"]) == {0.10}


def test_forest_scores_are_normalized_into_the_zero_to_one_range():
    df = pd.DataFrame(
        [billing_row(cost_usd=100.0 + i, usage_quantity=700.0 + i) for i in range(20)]
        + [billing_row(cost_usd=9_000.0, usage_quantity=5.0)]
    )

    scored = run_anomaly_detection(df)

    assert scored["anomaly_score"].min() == pytest.approx(0.0)
    assert scored["anomaly_score"].max() == pytest.approx(1.0)
    assert scored["anomaly_score"].idxmax() == 20, "the outlier row should score highest"


def test_anomaly_detection_does_not_leak_its_derived_feature_column():
    """cost_per_unit is internal to the model; downstream stages never see it."""
    df = pd.DataFrame([billing_row(cost_usd=100.0 + i) for i in range(15)])

    scored = run_anomaly_detection(df)

    assert "cost_per_unit" not in scored.columns
    assert "anomaly_score" in scored.columns


# --------------------------------------------------- stage 3: pattern matching


def scored_frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_rows_below_the_anomaly_threshold_are_never_matched():
    df = scored_frame([billing_row(service_name="amazons3", usage_type="TimedStorage-ByteHrs", anomaly_score=0.10)])

    assert match_patterns(df, "aws", anomaly_threshold=0.65) == []


def test_a_matching_row_produces_a_prescription_with_cost_scaled_savings():
    df = scored_frame(
        [billing_row(service_name="amazons3", usage_type="TimedStorage-ByteHrs", cost_usd=200.0, anomaly_score=0.9)]
    )

    matches = match_patterns(df, "aws", anomaly_threshold=0.65)
    ia = next(m for m in matches if m["pattern_id"] == "aws_s3_infrequent_access_001")

    assert ia["service_name"] == "amazons3"
    assert ia["savings_min"] < ia["savings_max"] <= 200.0
    assert ia["engineering_hours_min"] <= ia["engineering_hours_max"]
    assert ia["immutable_blockers"] == ["tier1"]


def test_a_usage_type_pattern_cannot_fire_on_the_wrong_aws_service():
    """
    The cross-service guard: an RDS row whose usage_type happens to contain
    "Node:ra3" (Redshift's marker) must not produce a Redshift recommendation,
    even though both services are in the same broad "database" category.
    """
    df = scored_frame([billing_row(service_name="amazonrds", usage_type="Node:ra3.xlarge", anomaly_score=0.9)])

    matches = match_patterns(df, "aws", anomaly_threshold=0.65)

    assert not any(m["pattern_id"] == "aws_redshift_pause_dev_001" for m in matches)


def test_the_same_usage_type_does_fire_on_the_service_it_belongs_to():
    df = scored_frame([billing_row(service_name="amazonredshift", usage_type="Node:ra3.xlarge", anomaly_score=0.9)])

    matches = match_patterns(df, "aws", anomaly_threshold=0.65)

    assert any(m["pattern_id"] == "aws_redshift_pause_dev_001" for m in matches)


def test_azure_falls_back_to_the_broad_category_guard():
    """
    Azure has no per-pattern allowlist, so a usage_type-keyed storage pattern is
    rejected for a compute-category service by SERVICE_CATEGORY_MAP instead.
    """
    df = scored_frame([billing_row(service_name="virtual_machines", usage_type="Blob Storage", anomaly_score=0.9)])

    matches = match_patterns(df, "azure", anomaly_threshold=0.65)

    assert not any(m["pattern_id"] == "azure_blob_cool_tier_001" for m in matches)


def test_focus_rows_are_matched_against_each_detected_providers_own_library():
    """
    A single FOCUS upload can describe several clouds, so detected_provider --
    not the caller-supplied provider -- picks the pattern library per row.
    """
    df = scored_frame(
        [
            billing_row(service_name="cloud_storage", detected_provider="gcp", anomaly_score=0.9),
            billing_row(service_name="virtual_machines", detected_provider="azure", anomaly_score=0.9),
        ]
    )

    matches = match_patterns(df, "focus", anomaly_threshold=0.65)
    ids = {m["pattern_id"] for m in matches}

    assert any(i.startswith("gcp_") for i in ids)
    assert any(i.startswith("azure_") for i in ids)


def test_focus_rows_with_an_unmapped_provider_are_skipped_not_guessed_at():
    df = scored_frame([billing_row(service_name="object_storage", detected_provider=None, anomaly_score=0.9)])

    assert match_patterns(df, "focus", anomaly_threshold=0.65) == []


def test_an_unknown_provider_raises_rather_than_silently_matching_nothing():
    df = scored_frame([billing_row(anomaly_score=0.9)])

    with pytest.raises(RuntimeError):
        match_patterns(df, "oracle", anomaly_threshold=0.65)


# ----------------------------------------------------- stage 4: risk assessment


@pytest.mark.parametrize(
    "cost, tier, variance, complexity, expected",
    [
        (600.0, 3, False, "Low", "High"),      # TRD: cost > $500 -> High
        (50.0, 2, True, "Low", "High"),        # TRD: tier 2 + high usage variance -> High
        (50.0, 2, False, "Low", "Medium"),     # TRD: tier 2 alone -> Medium
        (50.0, 3, False, "Low", "Low"),        # cheap, mutable, simple -> Low
        (50.0, 3, False, "High", "Medium"),    # ITIL extension: complex action promotes Low -> Medium
        (200.0, 3, False, "Low", "Medium"),    # cost band extension: $100-500 promotes Low -> Medium
        (50.0, 3, True, "Low", "Low"),         # variance only matters for tier 2
    ],
)
def test_risk_level_heuristics(cost, tier, variance, complexity, expected):
    result = calculate_risk("svc", cost, tier, high_usage_variance=variance, action_complexity=complexity)

    assert result["risk_level"] == expected


def test_high_risk_carries_a_four_times_monthly_failure_cost_estimate():
    high = calculate_risk("svc", 600.0, 3)
    low = calculate_risk("svc", 50.0, 3)

    assert high["failure_cost_estimate"] == 2400.0
    assert low["failure_cost_estimate"] is None


def test_usage_variance_needs_at_least_two_line_items_to_measure():
    df = pd.DataFrame(
        [
            billing_row(service_name="single", usage_quantity=100.0),
            billing_row(service_name="steady", usage_quantity=100.0),
            billing_row(service_name="steady", usage_quantity=101.0),
            billing_row(service_name="spiky", usage_quantity=1.0),
            billing_row(service_name="spiky", usage_quantity=5000.0),
        ]
    )

    flags = compute_usage_variance_flags(df)

    assert flags["single"] is False, "one line item has no variance to measure"
    assert flags["steady"] is False
    assert flags["spiky"] is True


def test_risk_reconciliation_never_downgrades_a_risky_action_on_a_cheap_service():
    """A High-risk action on a $50 service stays High."""
    scored = apply_failure_scores([prescription(cost_usd=50.0, tier=3, downtime_risk="High")])

    assert scored[0]["infrastructure_risk_level"] == "Low"
    assert scored[0]["risk_level"] == "High"
    assert scored[0]["failure_cost_estimate"] == 200.0


def test_risk_reconciliation_takes_the_infrastructure_risk_when_it_is_higher():
    scored = apply_failure_scores([prescription(cost_usd=600.0, tier=3, downtime_risk="Low")])

    assert scored[0]["infrastructure_risk_level"] == "High"
    assert scored[0]["risk_level"] == "High"


def test_the_pre_reconciliation_baseline_is_preserved_for_conflict_resolution():
    """
    conflict_resolver compares the action's risk against the service's own
    baseline; if that baseline were the reconciled value the comparison could
    never fire, since the reconciled value is >= the action risk by construction.
    """
    scored = apply_failure_scores([prescription(cost_usd=50.0, tier=3, downtime_risk="Medium")])

    assert scored[0]["infrastructure_risk_level"] == "Low"
    assert scored[0]["risk_level"] == "Medium"


# -------------------------------------------------- stage 5: conflict resolution


def test_tier_1_prescriptions_are_dropped_entirely():
    """Fully immutable services are never surfaced, not even flagged."""
    resolved = resolve_conflicts([prescription(tier=1), prescription(tier=3)])

    assert len(resolved) == 1
    assert resolved[0]["tier"] == 3


def test_tier_2_is_flagged_when_the_pattern_modifies_the_core():
    resolved = resolve_conflicts([prescription(tier=2, immutable_blockers=["tier1", "tier2"])])

    assert resolved[0]["is_conflicted"] is True
    assert resolved[0]["conflict_reason"] == "Service core is immutable"


def test_tier_2_survives_unflagged_when_the_pattern_does_not_block_tier_2():
    resolved = resolve_conflicts([prescription(tier=2, immutable_blockers=["tier1"], infrastructure_risk_level="Medium")])

    assert resolved[0]["is_conflicted"] is False
    assert resolved[0]["conflict_reason"] is None


@pytest.mark.parametrize(
    "base_risk, action_risk",
    [("Low", "Medium"), ("Medium", "High"), ("Low", "High")],
)
def test_any_single_step_risk_increase_is_flagged_not_just_low_to_high(base_risk, action_risk):
    """
    A deliberate deviation from TRD 5.5, which only specifies the 2-step
    Low -> High case.
    """
    resolved = resolve_conflicts(
        [prescription(infrastructure_risk_level=base_risk, downtime_risk=action_risk)]
    )

    assert resolved[0]["is_conflicted"] is True
    assert "Risk delta exceeds threshold" in resolved[0]["conflict_reason"]


@pytest.mark.parametrize("risk", ["Low", "Medium", "High"])
def test_an_action_no_riskier_than_its_service_is_not_flagged(risk):
    resolved = resolve_conflicts([prescription(infrastructure_risk_level=risk, downtime_risk=risk)])

    assert resolved[0]["is_conflicted"] is False


def test_commitment_and_spot_pricing_on_the_same_service_conflict():
    """
    Vendor-documented as mutually exclusive: commitment discounts do not apply
    to spot/preemptible capacity, so recommending both is a contradiction.
    """
    resolved = resolve_conflicts(
        [
            prescription(service_name="amazonec2", pattern_id="aws_rds_reserved_instance_gap_001"),
            prescription(service_name="amazonec2", pattern_id="aws_ec2_spot_eligible_workload_001"),
        ]
    )

    assert all(p["is_conflicted"] for p in resolved)
    assert all("Mutually exclusive" in p["conflict_reason"] for p in resolved)


def test_commitment_and_spot_on_different_services_do_not_conflict():
    resolved = resolve_conflicts(
        [
            prescription(service_name="amazonec2", pattern_id="aws_rds_reserved_instance_gap_001"),
            prescription(service_name="amazonrds", pattern_id="aws_ec2_spot_eligible_workload_001"),
        ]
    )

    assert not any(p["is_conflicted"] for p in resolved)


# ------------------------------------------------------- stage 6: ROI ranking


def test_roi_is_savings_per_engineering_hour_weighted_by_risk_and_confidence():
    ranked = calculate_roi_and_rank(
        [
            prescription(
                savings_min=100.0,
                savings_max=300.0,   # avg 200
                engineering_hours_min=1.0,
                engineering_hours_max=3.0,  # avg 2
                risk_level="Medium",  # multiplier 0.7
                anomaly_score=1.0,
            )
        ]
    )

    assert ranked[0]["roi_score"] == pytest.approx(70.0)


def test_a_borderline_anomaly_scores_lower_than_a_confident_one():
    """EMV-style confidence weighting: a match right at the threshold counts for less."""
    confident = prescription(anomaly_score=1.0, service_name="confident")
    borderline = prescription(anomaly_score=0.65, service_name="borderline")

    ranked = calculate_roi_and_rank([borderline, confident])

    assert [p["service_name"] for p in ranked] == ["confident", "borderline"]


def test_conflicted_items_are_zeroed_and_sink_to_the_bottom():
    """They survive in the list -- being able to see them is the point."""
    ranked = calculate_roi_and_rank(
        [
            prescription(service_name="conflicted", is_conflicted=True, savings_max=10_000.0),
            prescription(service_name="clean", is_conflicted=False),
        ]
    )

    assert [p["service_name"] for p in ranked] == ["clean", "conflicted"]
    assert ranked[-1]["roi_score"] == 0.0


def test_a_zero_hour_pattern_does_not_divide_by_zero():
    ranked = calculate_roi_and_rank(
        [prescription(engineering_hours_min=0.0, engineering_hours_max=0.0, savings_min=1.0, savings_max=1.0)]
    )

    assert ranked[0]["roi_score"] == pytest.approx(10.0)


def test_savings_breaks_a_roi_tie():
    """Equal savings-per-hour: the bigger absolute saving wins."""
    small = prescription(
        service_name="small", savings_min=10.0, savings_max=10.0,
        engineering_hours_min=1.0, engineering_hours_max=1.0,
    )
    big = prescription(
        service_name="big", savings_min=20.0, savings_max=20.0,
        engineering_hours_min=2.0, engineering_hours_max=2.0,
    )

    ranked = calculate_roi_and_rank([small, big])

    assert ranked[0]["roi_score"] == ranked[1]["roi_score"] == pytest.approx(10.0)
    assert [p["service_name"] for p in ranked] == ["big", "small"]


def test_rank_position_is_injected_starting_at_one():
    ranked = calculate_roi_and_rank(
        [prescription(savings_max=float(s), service_name=f"svc{s}") for s in (10, 500, 100)]
    )

    assert [p["rank_position"] for p in ranked] == [1, 2, 3]
    assert ranked[0]["service_name"] == "svc500"


def test_the_full_chain_from_matching_to_ranking_holds_its_field_contract():
    """
    Stages 3 -> 4 -> 5 -> 6 end to end on a hand-built frame: a tier-1 service
    must vanish, a tier-2 core modification must survive but be flagged and
    zeroed, and the mutable service must rank first.
    """
    df = scored_frame(
        [
            billing_row(service_name="cloud_sql", tier=1, cost_usd=800.0, anomaly_score=0.9),
            billing_row(service_name="compute_engine", tier=2, cost_usd=600.0, anomaly_score=0.9),
            billing_row(service_name="cloud_storage", tier=3, cost_usd=400.0, anomaly_score=0.9),
        ]
    )

    matched = match_patterns(df, "gcp", anomaly_threshold=0.65)
    scored = apply_failure_scores(matched, compute_usage_variance_flags(df))
    resolved = resolve_conflicts(scored)
    ranked = calculate_roi_and_rank(resolved)

    services = {p["service_name"] for p in ranked}
    assert "cloud_sql" not in services, "tier 1 must be dropped entirely"
    assert {"compute_engine", "cloud_storage"} <= services

    core_mods = [p for p in ranked if p["service_name"] == "compute_engine" and "tier2" in p["immutable_blockers"]]
    assert core_mods, "expected at least one tier-2-blocking pattern to match compute_engine"
    assert all(p["is_conflicted"] and p["roi_score"] == 0.0 for p in core_mods)

    assert ranked[0]["roi_score"] > 0.0
    assert [p["rank_position"] for p in ranked] == list(range(1, len(ranked) + 1))
    for p in ranked:
        assert {"service_name", "recommended_action", "savings_min", "savings_max", "risk_level", "roi_score"} <= p.keys()
