import os
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv

load_dotenv()

def get_mongo_db():
    """Returns the MongoDB Atlas database instance."""
    client = MongoClient(
        os.getenv("MONGO_URI"), 
        tlsCAFile=certifi.where()
    )
    return client.unareserva_db