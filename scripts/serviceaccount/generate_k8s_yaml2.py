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

def validate_csv(csv_file):
    """Validate CSV headers."""
    expected_headers = ["env", "cluster_name", "namespace", "service_account", "role", "role_binding", "api_groups", "verbs"]

    with open(csv_file, newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)

        if headers != expected_headers:
            raise ValueError(f"CSV headers do not match expected format: {expected_headers}")

def generate_manifests(csv_file, template_dir, output_dir):
    """Generate Kubernetes manifests from CSV while ensuring unique entries and proper file structure."""
    namespace_template = load_template(template_dir, "namespace.j2")
    sa_template = load_template(template_dir, "serviceaccount.j2")
    role_template = load_template(template_dir, "role.j2")
    role_binding_template = load_template(template_dir, "rolebinding.j2")

    # Store unique resources
    manifests = defaultdict(lambda: {
        "namespaces": set(),
        "service_accounts": defaultdict(set),
        "roles": defaultdict(lambda: {"api_groups": set(), "verbs": set()}),
        "role_bindings": defaultdict(set),
    })

    with open(csv_file, newline='') as f:
        reader = csv.reader(f)
        headers = next(reader)  # Skip header row

        for row in reader:
            env, cluster, namespace, sa_name, role, role_binding, api_groups, verbs = row
            verbs_list = ast.literal_eval(verbs)
            api_group_list = ast.literal_eval(api_groups)

            key = (cluster, namespace)  # Unique folder path key
            manifests[key]["namespaces"].add(namespace)
            manifests[key]["service_accounts"][namespace].add(sa_name)
            manifests[key]["roles"][(namespace, role)]["verbs"].update(verbs_list)
            manifests[key]["roles"][(namespace, role)]["api_groups"].update(api_group_list)
            manifests[key]["role_bindings"][(namespace, role_binding)].add((sa_name, role))

    # Generate YAML files
    for (cluster, namespace), data in manifests.items():
        cluster_dir = os.path.join(output_dir, "engineering", cluster, namespace)
        os.makedirs(cluster_dir, exist_ok=True)

        # Namespace File
        namespace_file = os.path.join(cluster_dir, "namespace.yaml")
        with open(namespace_file, "w") as f:
            f.write(f"---\n")
            f.write(namespace_template.render({"namespace": namespace}))
        print(f"✅ Created {namespace_file}")

        # Service Account File
        sa_file = os.path.join(cluster_dir, "serviceaccount.yaml")
        with open(sa_file, "w") as f:
            f.write("---\n")
            f.write("\n---\n".join(
                sa_template.render({"sa_name": sa_name, "namespace": namespace})
                for sa_name in data["service_accounts"][namespace]
            ))
        print(f"✅ Created {sa_file}")

        # Role File
        role_file = os.path.join(cluster_dir, "role.yaml")
        with open(role_file, "w") as f:
            f.write("---\n")
            f.write("\n---\n".join(
                role_template.render({
                    "role": role,
                    "namespace": namespace,
                    "api_groups": list(role_data["api_groups"]),
                    "verbs": list(role_data["verbs"])
                })
                for (namespace, role), role_data in data["roles"].items()
            ))
        print(f"✅ Created {role_file}")

        # Role Binding File
        rb_file = os.path.join(cluster_dir, "rolebinding.yaml")
        with open(rb_file, "w") as f:
            f.write("---\n")
            f.write("\n---\n".join(
                role_binding_template.render({
                    "role_binding": role_binding,
                    "namespace": namespace,
                    "bindings": [{"sa_name": sa, "role": role} for sa, role in bindings]
                })
                for (namespace, role_binding), bindings in data["role_bindings"].items()
            ))
        print(f"✅ Created {rb_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Kubernetes manifests from CSV.")
    parser.add_argument("--csv_file", required=True, help="Path to the CSV file")
    parser.add_argument("--template_dir", required=True, help="Path to Jinja2 templates")
    parser.add_argument("--output_dir", required=True, help="Path to output manifest directory")
    args = parser.parse_args()

    validate_csv(args.csv_file)
    generate_manifests(args.csv_file, args.template_dir, args.output_dir)
