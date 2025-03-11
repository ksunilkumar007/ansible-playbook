import csv
import ast
import argparse
import re

# Valid Kubernetes API groups and verbs
VALID_API_GROUPS = {"", "v1", "apps", "batch", "rbac.authorization.k8s.io"}
VALID_VERBS = {"get", "list", "watch", "create", "update", "patch", "delete", "deletecollection"}

# OpenShift Naming Validation (DNS-1123 Subset)
NAME_PATTERN = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")

def is_valid_name(name):
    return bool(NAME_PATTERN.match(name)) and len(name) <= 63

def validate_csv(file_path):
    with open(file_path, newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)
        for i, row in enumerate(reader, start=1):
            if len(row) != 7:
                raise ValueError(f"Row {i} has incorrect columns: {row}")
            cluster, namespace, sa, role, rb, api_groups, verbs = row

            if not all(map(is_valid_name, [cluster, namespace, sa, role, rb])):
                raise ValueError(f"Invalid naming in row {i}: {row}")

            try:
                api_group_list = ast.literal_eval(api_groups)
                verbs_list = ast.literal_eval(verbs)
            except (SyntaxError, ValueError):
                raise ValueError(f"Invalid list formatting in row {i}: {api_groups}, {verbs}")

            if not all(group in VALID_API_GROUPS for group in api_group_list):
                raise ValueError(f"Invalid API group(s) in row {i}: {api_groups}")

            if not all(verb in VALID_VERBS for verb in verbs_list):
                raise ValueError(f"Invalid verb(s) in row {i}: {verbs}")

    print("CSV validation passed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Kubernetes CSV schema")
    parser.add_argument("--csv_file", required=True, help="Path to the CSV file")
    args = parser.parse_args()
    
    validate_csv(args.csv_file)
