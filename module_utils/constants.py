# constants.py

# Define valid API groups
VALID_API_GROUPS = {"", "v1", "v2", "apps", "batch", "rbac.authorization.k8s.io"}
# Define valid verbs
VALID_VERBS = {"get", "list", "watch", "create", "update", "patch", "delete", "deletecollection"}
# Define valid environment-cluster mappings
VALID_ENV_CLUSTER_MAP = {
    "engineering": {"ukgcpe1", "ukgcpe2"},  # Define valid clusters for each environment
    "staging": {"ukgcpe3", "ukgcpe4"}  # Define valid clusters for each environment
}