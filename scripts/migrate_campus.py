"""Asocia recursos existentes al campus Omar Dengo por compatibilidad."""

import os

from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv()


def main():
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client.unareserva_db
    result = db.recursos.update_many(
        {"campus_id": {"$exists": False}},
        {"$set": {"campus_id": "omar_dengo"}},
    )
    tipos = db.tipos_recurso
    tipos.update_many(
        {"campus_id": {"$exists": False}},
        {"$set": {"campus_id": "omar_dengo"}},
    )
    creados = 0
    for tipo in tipos.find({"campus_id": "omar_dengo"}):
        copia = dict(tipo)
        copia.pop("_id", None)
        copia["campus_id"] = "benjamin_nunez"
        if not tipos.find_one({"codigo": copia["codigo"], "campus_id": "benjamin_nunez"}):
            tipos.insert_one(copia)
            creados += 1
    print(f"Recursos actualizados: {result.modified_count}; tipos duplicados para Benjamín Núñez: {creados}")


if __name__ == "__main__":
    main()
