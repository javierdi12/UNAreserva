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
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "")
    RESEND_TIMEOUT = int(os.getenv("RESEND_TIMEOUT", 10))
