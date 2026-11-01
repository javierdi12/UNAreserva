"""Asocia recursos existentes al campus Omar Dengo por compatibilidad."""

import os

from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv()


def main():
    client = MongoClient(os.getenv("MONGO_URI"))
    result = client.unareserva_db.recursos.update_many(
        {"campus_id": {"$exists": False}},
        {"$set": {"campus_id": "omar_dengo"}},
    )
    print(f"Recursos actualizados: {result.modified_count}")


if __name__ == "__main__":
    main()
