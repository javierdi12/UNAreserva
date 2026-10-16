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
