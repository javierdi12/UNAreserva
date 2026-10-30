import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    MONGO_URI = os.getenv("MONGO_URI")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PREFIX = os.getenv("REDIS_PREFIX", "UNAreserva:")
    SQLITE_PATH = os.getenv("SQLITE_PATH", "./data/unareserva_local.db")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev")
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME)
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000")
