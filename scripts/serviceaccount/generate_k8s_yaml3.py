import os
import csv
import ast
import argparse
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader

def load_template(template_dir, filename):
    """Load Jinja2 template from the specified directory."""
    env = Environment(loader=FileSystemLoader(template_dir))
    return env.get_template(filename)

def generate_manifests(csv_file, template_dir, output_dir):
    """Generate individual YAML manifest files per environment and cluster."""
    sa_template = load_template(template_dir, "serviceaccount.j2")
    role_template = load_template(template_dir, "role.j2")
    role_binding_template = load_template(template_dir, "rolebinding.j2")
    namespace_template = load_template(template_dir, "namespace.j2")

    # Store data in memory to avoid duplicates
    manifests = defaultdict(lambda: {
        "namespaces": set(),
        "service_accounts": set(),
        "roles": defaultdict(lambda: {"api_groups": set(), "verbs": set()}),
        "role_bindings": defaultdict(set),
    })

    with open(csv_file, newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)

        if headers != ["env", "cluster_name", "namespace", "service_account", "role", "role_binding", "api_groups", "verbs"]:
            raise ValueError("CSV headers do not match expected format")

        for row in reader:
            env, cluster, namespace, sa_name, role, role_binding, api_groups, verbs = row
            verbs_list = ast.literal_eval(verbs)
            api_group_list = ast.literal_eval(api_groups)

            # Track unique resources per (env, cluster)
            key = (env, cluster)
            manifests[key]["namespaces"].add(namespace)
            manifests[key]["service_accounts"].add((namespace, sa_name))
            manifests[key]["roles"][(namespace, role)]["verbs"].update(verbs_list)
            manifests[key]["roles"][(namespace, role)]["api_groups"].update(api_group_list)
            manifests[key]["role_bindings"][(namespace, role_binding)].add((sa_name, role))

    # Generate YAML files
    for (env, cluster), data in manifests.items():
        cluster_dir = os.path.join(output_dir, env, cluster)
        os.makedirs(cluster_dir, exist_ok=True)

        # Namespace Files
        for namespace in data["namespaces"]:
            file_path = os.path.join(cluster_dir, f"namespace-{namespace}.yaml")
            with open(file_path, "w") as f:
                f.write(namespace_template.render({"namespace": namespace}))
            print(f"✅ Created {file_path}")

        # Service Account Files
        for namespace, sa_name in data["service_accounts"]:
            file_path = os.path.join(cluster_dir, f"serviceaccount-{sa_name}.yaml")
            with open(file_path, "w") as f:
                f.write(sa_template.render({"sa_name": sa_name, "namespace": namespace}))
            print(f"✅ Created {file_path}")

        # Role Files
        for (namespace, role), role_data in data["roles"].items():
            file_path = os.path.join(cluster_dir, f"role-{role}.yaml")
            with open(file_path, "w") as f:
                f.write(role_template.render({
                    "role": role,
                    "namespace": namespace,
                    "api_groups": list(role_data["api_groups"]),
                    "verbs": list(role_data["verbs"])
                }))
            print(f"✅ Created {file_path}")

        # Role Binding Files
        for (namespace, role_binding), bindings in data["role_bindings"].items():
            file_path = os.path.join(cluster_dir, f"rolebinding-{role_binding}.yaml")
            with open(file_path, "w") as f:
                f.write(role_binding_template.render({
                    "role_binding": role_binding,
                    "namespace": namespace,
                    "bindings": [{"sa_name": sa, "role": role} for sa, role in bindings]
                }))
            print(f"✅ Created {file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Kubernetes manifests from CSV.")
    parser.add_argument("--csv_file", required=True, help="Path to the CSV file")
    parser.add_argument("--template_dir", required=True, help="Path to Jinja2 templates")
    parser.add_argument("--output_dir", required=True, help="Path to output manifest directory")
    args = parser.parse_args()

    generate_manifests(args.csv_file, args.template_dir, args.output_dir)
