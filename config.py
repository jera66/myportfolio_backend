import os
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "development")

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

if not MONGO_URL or not DB_NAME:
    raise RuntimeError("Missing required database environment variables")
