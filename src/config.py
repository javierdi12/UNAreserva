import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    REDIS_URL = os.getenv("REDIS_URL", "")
    MONGO_URI = os.getenv("MONGO_URI")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PREFIX = os.getenv("REDIS_PREFIX", "UNAreserva:")
    SQLITE_PATH = os.getenv("SQLITE_PATH", "./data/unareserva_local.db")
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev")
    APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000")
    MAILERLITE_API_TOKEN = os.getenv("MAILERLITE_API_TOKEN", "")
    MAILERLITE_API_BASE_URL = os.getenv(
        "MAILERLITE_API_BASE_URL", "https://connect.mailerlite.com/api"
    )
    MAILERLITE_RESET_GROUP_ID = os.getenv("MAILERLITE_RESET_GROUP_ID", "")
    MAILERLITE_RESET_FIELD_KEY = os.getenv("MAILERLITE_RESET_FIELD_KEY", "reset_link")
    MAILERLITE_API_VERSION = os.getenv("MAILERLITE_API_VERSION", "")
    MAILERLITE_TIMEOUT = int(os.getenv("MAILERLITE_TIMEOUT", 10))
