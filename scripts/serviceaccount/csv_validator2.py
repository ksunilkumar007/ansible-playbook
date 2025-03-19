import csv
import ast
import argparse
import re
import json

# OpenShift Naming Validation (DNS-1123 Subset)
NAME_PATTERN = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")

# Define CSV schema
CSV_SCHEMA = [
    "env", "cluster_name", "namespace", "service_account",
    "role", "role_binding", "api_groups", "verbs"
]

def load_validation_data(json_file):
    """Load validation constants from a JSON file."""
    with open(json_file, "r") as f:
        data = json.load(f)

    required_keys = {"VALID_API_GROUPS", "VALID_VERBS", "VALID_ENV_CLUSTER_MAP"}
    if not required_keys.issubset(data.keys()):
        raise ValueError(f"❌ JSON file is missing required keys: {required_keys - set(data.keys())}")

    return data["VALID_API_GROUPS"], data["VALID_VERBS"], data["VALID_ENV_CLUSTER_MAP"]

def is_valid_name(name):
    """Check if a name follows OpenShift DNS-1123 naming conventions."""
    return bool(NAME_PATTERN.match(name)) and len(name) <= 63

def validate_csv(file_path, json_file):
    """Validate the CSV file structure, naming, API groups, verbs, and env-cluster mapping, while checking for duplicates."""
    VALID_API_GROUPS, VALID_VERBS, VALID_ENV_CLUSTER_MAP = load_validation_data(json_file)

    seen_rows = set()

    with open(file_path, newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)

        # Ensure the headers match the defined schema
        if headers != CSV_SCHEMA:
            raise ValueError(f"❌ CSV headers do not match expected format: {CSV_SCHEMA}")

        for i, row in enumerate(reader, start=1):
            if len(row) != len(CSV_SCHEMA):
                raise ValueError(f"❌ Row {i} has incorrect columns: {row}")

            env, cluster, namespace, sa, role, rb, api_groups, verbs = row

            # Validate environment
            if env not in VALID_ENV_CLUSTER_MAP:
                valid_envs = list(VALID_ENV_CLUSTER_MAP.keys())
                raise ValueError(f"❌ Invalid environment in row {i}: {env} (must be one of {valid_envs})")

            # Validate cluster mapping
            valid_clusters = list(VALID_ENV_CLUSTER_MAP[env])
            if cluster not in valid_clusters:
                raise ValueError(f"❌ Invalid cluster for environment '{env}' in row {i}: {cluster} (valid clusters: {valid_clusters})")

            # Validate OpenShift naming conventions
            if not all(map(is_valid_name, [cluster, namespace, sa, role, rb])):
                raise ValueError(f"❌ Invalid naming in row {i}: {row}")

            # Validate API Groups and Verbs
            try:
                api_group_list = ast.literal_eval(api_groups)
                verbs_list = ast.literal_eval(verbs)
            except (SyntaxError, ValueError):
                raise ValueError(f"❌ Invalid list formatting in row {i}: {api_groups}, {verbs}")

            if not all(group in VALID_API_GROUPS for group in api_group_list):
                raise ValueError(f"❌ Invalid API group(s) in row {i}: {api_groups}")

            if not all(verb in VALID_VERBS for verb in verbs_list):
                raise ValueError(f"❌ Invalid verb(s) in row {i}: {verbs}")

            # Check for duplicates based on unique key
            unique_key = (env, cluster, namespace, sa, role, rb, tuple(api_group_list), tuple(verbs_list))
            if unique_key in seen_rows:
                raise ValueError(f"❌ Duplicate row detected at {i}: {row}")

            seen_rows.add(unique_key)

    print("✅ CSV validation passed without duplicates.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Kubernetes CSV schema and check for duplicates")
    parser.add_argument("--csv_file", required=True, help="Path to the CSV file")
    parser.add_argument("--json_file", required=True, help="Path to the JSON validation file")
    args = parser.parse_args()

    validate_csv(args.csv_file, args.json_file)
