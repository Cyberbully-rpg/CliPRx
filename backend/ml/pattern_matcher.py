"""
Prescription Pattern Matcher
Bridges the ML anomaly detection with the deterministic JSON pattern libraries.
"""
import pandas as pd
import json
import os

# Maps a normalized service_name to the broad category patterns declare via
# 'service_type'. Only needed for providers/patterns whose trigger_condition matches
# on a field OTHER than service_name (e.g. Azure patterns keyed on 'usage_type') --
# otherwise the field match already IS the service check. This is a coarse check
# (e.g. "database") -- see PATTERN_ALLOWED_SERVICES below for AWS, which needs
# service-level (not just category-level) precision, since two different services in
# the same broad category (e.g. RDS vs Redshift, both "database") can still have
# usage_type strings that coincidentally overlap.
SERVICE_CATEGORY_MAP = {
    'azure': {
        'storage': 'storage',
        'virtual_machines': 'compute',
        'sql_database': 'database',
        'azure_app_service': 'compute',
    },
    # GCP's own patterns match on service_name directly (a single GCP service, e.g.
    # "compute_engine", legitimately spans multiple service_types like compute + disk
    # storage), so no category map is needed/safe to apply there.
}

# AWS patterns are almost all keyed on 'usage_type', so a broad category isn't
# precise enough to prevent cross-service false positives (e.g. an RDS row whose
# usage_type coincidentally contains "Node:ra3" matching the Redshift pattern, even
# though both are "database"). This maps each usage_type-keyed pattern_id to exactly
# which normalized service_name(s) can legitimately produce that usage_type.
#
# Some services legitimately span multiple patterns' categories -- e.g. EBS volume
# and Elastic IP costs bill under the AmazonEC2 service line in real AWS billing, so
# 'amazonec2' appears alongside 'amazonebs' for those patterns.
#
# Patterns not listed here (e.g. aws_data_transfer_cross_az_001) are intentionally
# left unrestricted: their usage_type genuinely occurs across many unrelated services
# and can't be tied to a specific one.
PATTERN_ALLOWED_SERVICES = {
    'aws': {
        'aws_ebs_unattached_001': {'amazonec2', 'amazonebs'},
        'aws_ec2_graviton_upgrade_001': {'amazonec2'},
        'aws_s3_infrequent_access_001': {'amazons3'},
        'aws_rds_multiaz_dev_001': {'amazonrds'},
        'aws_vpc_endpoint_001': {'amazonvpc'},
        'aws_ec2_previous_gen_m3_001': {'amazonec2'},
        'aws_ec2_previous_gen_c3_001': {'amazonec2'},
        'aws_ec2_idle_elastic_ip_001': {'amazonec2'},
        'aws_ec2_spot_eligible_workload_001': {'amazonec2'},
        'aws_ec2_gpu_underutilized_001': {'amazonec2'},
        'aws_ebs_gp2_to_gp3_001': {'amazonec2', 'amazonebs'},
        'aws_ebs_snapshot_cleanup_001': {'amazonec2', 'amazonebs'},
        'aws_ebs_io1_overprovisioned_001': {'amazonec2', 'amazonebs'},
        'aws_s3_glacier_transition_001': {'amazons3'},
        'aws_s3_incomplete_multipart_001': {'amazons3'},
        'aws_rds_reserved_instance_gap_001': {'amazonrds'},
        'aws_rds_storage_autoscaling_001': {'amazonrds'},
        'aws_rds_idle_read_replica_001': {'amazonrds'},
        'aws_dynamodb_provisioned_idle_001': {'amazondynamodb'},
        'aws_dynamodb_ondemand_high_volume_001': {'amazondynamodb'},
        'aws_redshift_pause_dev_001': {'amazonredshift'},
        'aws_elb_idle_loadbalancer_001': {'amazonelasticloadbalancing'},
        'aws_vpn_idle_connection_001': {'awsvpn'},
        'aws_cloudwatch_log_retention_001': {'amazoncloudwatch'},
        'aws_cloudtrail_duplicate_trails_001': {'awscloudtrail'},
        'aws_backup_retention_excess_001': {'awsbackup'},
        'aws_lambda_graviton_001': {'awslambda'},
        'aws_lambda_memory_overprovisioned_001': {'awslambda'},
        'aws_fargate_spot_001': {'amazonecs'},
        'aws_elasticache_rightsizing_001': {'amazonelasticache'},
    },
}

def match_patterns(df: pd.DataFrame, cloud_provider: str, anomaly_threshold: float = 0.65) -> list[dict]:
    """
    Filters DataFrame for anomalies, loads the correct cloud pattern library,
    and returns a list of raw prescription dictionaries for matching conditions.

    A FOCUS-derived DataFrame (parsers/focus_parser.py) carries an extra
    `detected_provider` column, since FOCUS is provider-agnostic and a single
    upload can (in principle) mix rows from different clouds. When present,
    each provider's rows are matched against that provider's own pattern
    library instead of the single `cloud_provider` passed in; rows whose
    ProviderName didn't map to a known provider are skipped (no library to
    match them against). Every non-FOCUS upload has no such column and hits
    the original single-provider path unchanged.
    """
    try:
        # 1. Filter out normal traffic to save compute time
        anomalies = df[df['anomaly_score'] >= anomaly_threshold].copy()

        if anomalies.empty:
            return []

        if 'detected_provider' in anomalies.columns:
            raw_prescriptions = []
            for provider in anomalies['detected_provider'].dropna().unique():
                subset = anomalies[anomalies['detected_provider'] == provider]
                raw_prescriptions.extend(_match_against_provider(subset, provider))
            return raw_prescriptions

        return _match_against_provider(anomalies, cloud_provider)

    except Exception as e:
        raise RuntimeError(f"Pattern matching engine failed: {str(e)}")


def _match_against_provider(anomalies: pd.DataFrame, cloud_provider: str) -> list[dict]:
    # Resolve absolute path to the JSON pattern file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pattern_file = os.path.join(base_dir, '..', 'patterns', f"{cloud_provider.lower()}_patterns.json")

    if not os.path.exists(pattern_file):
        raise FileNotFoundError(f"Pattern library not found for provider: {cloud_provider}")

    with open(pattern_file, 'r', encoding='utf-8') as f:
        patterns = json.load(f)

    category_map = SERVICE_CATEGORY_MAP.get(cloud_provider.lower(), {})
    pattern_allowed_services = PATTERN_ALLOWED_SERVICES.get(cloud_provider.lower(), {})

    raw_prescriptions = []

    # Evaluate each anomaly against the pattern library
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

            # When the trigger isn't already keyed on service_name, cross-check the
            # row's actual service against what the pattern is meant for, so a
            # usage_type substring coincidence can't produce a wrong-service
            # recommendation. Unknown/uncatalogued services are let through as before.
            if is_match and target_field != 'service_name':
                allowed_services = pattern_allowed_services.get(pattern.get('pattern_id'))
                if allowed_services is not None:
                    # Exact, service-level allowlist (precise enough to tell RDS
                    # apart from Redshift even though both are "database").
                    if row['service_name'] not in allowed_services:
                        is_match = False
                else:
                    # Fallback for patterns/providers without an explicit
                    # allowlist: broad category comparison.
                    row_category = category_map.get(row['service_name'])
                    if row_category is not None and row_category != pattern.get('service_type'):
                        is_match = False

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
                    'complexity': pattern.get('complexity', 'Low'),
                    'immutable_blockers': pattern['immutable_blockers']
                })

    return raw_prescriptions
