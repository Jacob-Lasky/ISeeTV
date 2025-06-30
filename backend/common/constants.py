import os

DATA_PATH = os.getenv("DATA_PATH", "/app/data")
DATABASE_URL = f"sqlite:///{DATA_PATH}/iseetv.db"
