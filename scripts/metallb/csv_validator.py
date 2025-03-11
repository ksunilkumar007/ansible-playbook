import argparse
import csv
import sys
import ipaddress
import ast

def validate_csv(csv_file):
    errors = []

    required_columns = {
        "cluster_name", "namespace", "ip_address_pool_name", "ip_addresses",
        "l2_advertisement_name", "labels_key", "labels_value"
    }

    with open(csv_file, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        # Check for missing columns
        missing_columns = required_columns - set(reader.fieldnames)
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
            sys.exit(1)

        for row_num, row in enumerate(reader, start=2):
            # Validate namespace
            if not row.get("namespace"):
                errors.append(f"Row {row_num}: 'namespace' is required and must be 'metallb-system'.")
            elif row["namespace"] != "metallb-system":
                errors.append(f"Row {row_num}: Invalid namespace '{row['namespace']}'. Must be 'metallb-system'.")

            # Validate IP addresses and CIDR range
            if not row.get("ip_addresses"):
                errors.append(f"Row {row_num}: 'ip_addresses' field is missing or empty.")
            else:
                try:
                    ip_list = ast.literal_eval(row["ip_addresses"])  # Convert string list to actual list
                    if not isinstance(ip_list, list):
                        raise ValueError

                    for ip in ip_list:
                        try:
                            network = ipaddress.ip_network(ip, strict=False)  # Validate CIDR
                            if network.prefixlen < 16 or network.prefixlen > 32:
                                errors.append(f"Row {row_num}: CIDR '{ip}' has an unsupported prefix. Use /16 to /32.")
                        except ValueError:
                            errors.append(f"Row {row_num}: Invalid CIDR format '{ip}'.")
                except (ValueError, SyntaxError):
                    errors.append(f"Row {row_num}: Invalid IP addresses format '{row['ip_addresses']}'. Expected a list format.")

            # Validate labels
            if not row.get("labels_key") or not row.get("labels_value"):
                errors.append(f"Row {row_num}: 'labels_key' and 'labels_value' fields are required.")

    if errors:
        for error in errors:
            print(f"❌ {error}")
        sys.exit(1)
    else:
        print("✅ CSV validation passed successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate MetalLB CSV")
    parser.add_argument("--csv_file", required=True, help="Path to the CSV file")
    args = parser.parse_args()
    validate_csv(args.csv_file)