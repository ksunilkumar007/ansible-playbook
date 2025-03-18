# ansible-playbook

ansible-playbook -i localhost main.yml -e "enable_serviceaccount=true"
ansible-playbook -i localhost main.yml -e "enable_metallb=true"
ansible-playbook -i localhost main.yml -e "enable_serviceaccount=true enable_metallb=true"


python3 scripts/metallb/generate_k8s_yaml.py --csv_file input/metallb/input.csv --template_dir=templates/metallb --output_dir=output
python3 scripts/metallb/csv_validator.py --csv_file input/metallb/input.csv

python3 scripts/serviceaccount/generate_k8s_yaml.py --csv_file input/serviceaccount/input.csv --template_dir=templates/serviceaccount --output_dir=output
python3 scripts/serviceaccount/csv_validator.py --csv_file input/serviceaccount/input.csv
