import argparse
import csv
import os
import ast
import jinja2

def load_template(template_dir, template_name):
    """Load a Jinja2 template from the specified directory."""
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    return env.get_template(template_name)

def generate_yaml(csv_file, template_dir, output_dir):
    """Generate MetalLB YAML files from CSV input while ensuring namespaces are created."""
    os.makedirs(output_dir, exist_ok=True)

    existing_files = set()  # Track generated filenames to avoid duplicates
    existing_namespaces = set()  # Track namespaces per cluster

    with open(csv_file, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for row in reader:
            cluster_name = row["cluster_name"]
            namespace = row["namespace"]
            ip_address_pool_name = row["ip_address_pool_name"]
            ip_addresses = ast.literal_eval(row["ip_addresses"])  # Convert string list to list
            l2_advertisement_name = row["l2_advertisement_name"]
            labels_key = row["labels_key"]
            labels_value = row["labels_value"]

            # Load Jinja templates
            namespace_template = load_template(template_dir, "namespace.j2")
            ip_pool_template = load_template(template_dir, "ipaddresspool.j2")
            l2_adv_template = load_template(template_dir, "l2advertisement.j2")

            # Define output paths
            cluster_output_dir = os.path.join(output_dir, cluster_name, namespace)
            os.makedirs(cluster_output_dir, exist_ok=True)

            namespace_path = os.path.join(cluster_output_dir, f"{namespace}.yaml")
            ip_pool_path = os.path.join(cluster_output_dir, f"{ip_address_pool_name}.yaml")
            l2_adv_path = os.path.join(cluster_output_dir, f"{l2_advertisement_name}.yaml")

            # Create namespace **per cluster**
            namespace_key = f"{cluster_name}:{namespace}"
            if namespace_key not in existing_namespaces:
                namespace_yaml = namespace_template.render(namespace=namespace)
                with open(namespace_path, "w", encoding="utf-8") as f:
                    f.write(namespace_yaml)
                existing_namespaces.add(namespace_key)
                print(f"✅ Created Namespace YAML: {namespace_path}")
            else:
                print(f"⚠️ Namespace already exists in cluster {cluster_name}, skipping: {namespace}")

            # Check and prevent duplicate IPAddressPool
            if ip_pool_path in existing_files:
                print(f"⚠️ Skipping duplicate IPAddressPool: {ip_pool_path}")
            else:
                ip_pool_yaml = ip_pool_template.render(
                    namespace=namespace,
                    name=ip_address_pool_name,
                    addresses=ip_addresses,
                    labels={labels_key: labels_value}
                )
                with open(ip_pool_path, "w", encoding="utf-8") as f:
                    f.write(ip_pool_yaml)
                existing_files.add(ip_pool_path)
                print(f"✅ Generated: {ip_pool_path}")

            # Check and prevent duplicate L2Advertisement
            if l2_adv_path in existing_files:
                print(f"⚠️ Skipping duplicate L2Advertisement: {l2_adv_path}")
            else:
                l2_adv_yaml = l2_adv_template.render(
                    namespace=namespace,
                    name=l2_advertisement_name,
                    match_key=labels_key,
                    match_value=labels_value
                )
                with open(l2_adv_path, "w", encoding="utf-8") as f:
                    f.write(l2_adv_yaml)
                existing_files.add(l2_adv_path)
                print(f"✅ Generated: {l2_adv_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate MetalLB YAML from CSV")
    parser.add_argument("--csv_file", required=True, help="Path to the CSV file")
    parser.add_argument("--template_dir", required=True, help="Path to Jinja2 templates")
    parser.add_argument("--output_dir", required=True, help="Output directory for YAML files")
    args = parser.parse_args()

    generate_yaml(args.csv_file, args.template_dir, args.output_dir)