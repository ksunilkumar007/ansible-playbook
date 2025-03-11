import os
import csv
import ast
import argparse
from jinja2 import Template
from collections import defaultdict

VALID_API_GROUPS = {"", "v1", "apps", "batch", "rbac.authorization.k8s.io"}
VALID_VERBS = {"get", "list", "watch", "create", "update", "patch", "delete", "deletecollection"}

def validate_csv(data):
    for i, row in enumerate(data, start=1):
        if len(row) != 7:
            raise ValueError("Row {} has an incorrect number of columns: {}".format(i, row))
        cluster, namespace, sa_name, role, role_binding, api_groups, verbs = row

        # Validate API groups
        api_group_list = ast.literal_eval(api_groups)
        if not isinstance(api_group_list, list) or not all(group in VALID_API_GROUPS for group in api_group_list):
            raise ValueError("Invalid API group(s) in row {}: {}".format(i, api_groups))

        # Validate verbs
        verbs_list = ast.literal_eval(verbs)
        if not isinstance(verbs_list, list) or not all(verb in VALID_VERBS for verb in verbs_list):
            raise ValueError("Invalid verb(s) in row {}: {}".format(i, verbs))

def load_template(template_path):
    with open(template_path, "r") as f:
        return Template(f.read())

def safe_makedirs(path):
    try:
        os.makedirs(path)
    except OSError:
        pass  # Ignore if directory exists

def create_k8s_yaml(data, output_dir, template_dir):
    sa_template = load_template(os.path.join(template_dir, "serviceaccount.j2"))
    role_template = load_template(os.path.join(template_dir, "role.j2"))
    role_binding_template = load_template(os.path.join(template_dir, "rolebinding.j2"))
    namespace_template = load_template(os.path.join(template_dir, "namespace.j2"))

    seen_namespaces = set()
    seen_service_accounts = set()
    role_definitions = defaultdict(lambda: {"api_groups": set(), "verbs": set()})
    role_binding_definitions = defaultdict(set)

    for row in data:
        cluster, namespace, sa_name, role, role_binding, api_groups, verbs = row
        verbs_list = ast.literal_eval(verbs)
        api_group_list = ast.literal_eval(api_groups)

        dir_path = os.path.join(output_dir, cluster, namespace)
        safe_makedirs(dir_path)

        # Generate Namespace per (cluster, namespace)
        ns_key = (cluster, namespace)
        if ns_key not in seen_namespaces:
            seen_namespaces.add(ns_key)
            ns_file_path = os.path.join(dir_path, "namespace.yaml")
            with open(ns_file_path, "w") as f:
                f.write(namespace_template.render({"namespace": namespace}))
            print("Generated {}".format(ns_file_path))

        # Generate Service Account per (cluster, namespace, sa_name)
        sa_key = (cluster, namespace, sa_name)
        if sa_key not in seen_service_accounts:
            seen_service_accounts.add(sa_key)
            sa_file_path = os.path.join(dir_path, "serviceaccount.yaml")
            with open(sa_file_path, "w") as f:
                f.write(sa_template.render({"sa_name": sa_name, "namespace": namespace}))
            print("Generated {}".format(sa_file_path))

        # Collect Role and RoleBinding information
        role_key = (cluster, namespace, role)
        role_definitions[role_key]["verbs"].update(verbs_list)
        role_definitions[role_key]["api_groups"].update(api_group_list)

        role_binding_key = (cluster, namespace, role_binding)
        role_binding_definitions[role_binding_key].add((sa_name, role, tuple(api_group_list)))

    # Write consolidated Role YAML files per (cluster, namespace, role)
    for (cluster, namespace, role), role_data in role_definitions.items():
        role_file_path = os.path.join(output_dir, cluster, namespace, "role.yaml")
        with open(role_file_path, "w") as f:
            f.write(role_template.render({
                "role": role,
                "namespace": namespace,
                "api_groups": list(role_data["api_groups"]),
                "verbs": list(role_data["verbs"])
            }))
        print("Generated {}".format(role_file_path))

    # Write consolidated RoleBinding YAML files per (cluster, namespace, role_binding)
    for (cluster, namespace, role_binding), bindings in role_binding_definitions.items():
        role_binding_file_path = os.path.join(output_dir, cluster, namespace, "rolebinding.yaml")
        with open(role_binding_file_path, "w") as f:
            f.write(role_binding_template.render({
                "role_binding": role_binding,
                "namespace": namespace,
                "bindings": [{"sa_name": sa, "role": role, "api_groups": list(api_groups)} for sa, role, api_groups in bindings]
            }))
        print("Generated {}".format(role_binding_file_path))

def main():
    parser = argparse.ArgumentParser(description="Generate Kubernetes YAML from CSV")
    parser.add_argument("--csv_file", required=True, help="Path to the CSV file")
    parser.add_argument("--template_dir", required=True, help="Path to Jinja2 templates")
    parser.add_argument("--output_dir", default="./output_k8s_yaml", help="Output directory for YAML files")
    args = parser.parse_args()

    with open(args.csv_file, newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)  # Skip the header row
        data = [row for row in reader]

    validate_csv(data)  # Validate CSV before processing
    create_k8s_yaml(data, args.output_dir, args.template_dir)

if __name__ == "__main__":
    main()
