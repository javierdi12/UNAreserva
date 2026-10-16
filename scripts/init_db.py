import os
import sqlite3

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
def init_mongo():
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client.unareserva_db
    if "recursos" not in db.list_collection_names():
        db.create_collection("recursos")
    if "reservas" not in db.list_collection_names():
        db.create_collection("reservas")
    print("[OK] Colecciones MongoDB listas: recursos, reservas")
def init_sqlite():
    path = os.getenv("SQLITE_PATH", "./data/unareserva_local.db")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pendientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_recurso TEXT NOT NULL,
            id_usuario TEXT NOT NULL,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT NOT NULL,
            sincronizado INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
    print("[OK] Tabla SQLite 'pendientes' lista")
if __name__ == "__main__":
    print("Inicializando bases de datos de UNAreserva...")
    init_mongo()
    init_sqlite()
    print("Listo.")
