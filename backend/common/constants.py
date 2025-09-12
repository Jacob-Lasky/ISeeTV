import os

DATA_PATH = os.getenv("DATA_PATH", "/app/data")
DATABASE_URL = f"sqlite:///{DATA_PATH}/iseetv.db"

# Meilisearch configuration
# Feature flag to enable/disable Meilisearch integration
MEILI_ENABLED = os.getenv("MEILI_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
# Host URL for the Meilisearch instance (e.g., http://meilisearch:7700)
MEILI_HOST = os.getenv("MEILI_HOST", "http://localhost:7700")
# Master/Admin key for server-side access. Leave blank for unsecured dev setups.
MEILI_MASTER_KEY = os.getenv("MEILI_MASTER_KEY", "")
