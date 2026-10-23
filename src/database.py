import os
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv
from src.config import Config

load_dotenv()

_client = None


def get_mongo_db():
    """Returns the MongoDB Atlas database instance (single shared client)."""
    global _client
    if _client is None:
        _client = MongoClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
    return _client[Config.MONGO_DB_NAME]
