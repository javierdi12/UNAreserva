from pymongo import MongoClient
import redis
import sqlite3
import os
import certifi
from dotenv import load_dotenv
from src.crud import recursos, reservas
from src.core.errores import ErrorValidacion, NoEncontrado


load_dotenv()


def conectar_mongo():
    try:
        client = MongoClient(
            os.getenv("MONGO_URI"),
            serverSelectionTimeoutMS=10000,
            tlsCAFile=certifi.where()
        )
        client.admin.command('ping')
        print("[OK] Conexion a MongoDB exitosa")
        return client
    except Exception as e:
        print(f"[ERROR] MongoDB: {e}")
        return None


def conectar_redis():
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )
        r.ping()
        print("[OK] Conexion a Redis exitosa")
        return r
    except Exception as e:
        print(f"[ERROR] Redis: {e}")
        return None


def conectar_sqlite():
    try:
        path = os.getenv("SQLITE_PATH", "./data/unareserva_local.db")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        conn = sqlite3.connect(path)
        print("[OK] Conexion a SQLite exitosa")
        return conn
    except Exception as e:
        print(f"[ERROR] SQLite: {e}")
        return None


if __name__ == "__main__":
    print("=" * 50)
    print("   UNAreserva - Sistema de Reservacion")
    print("=" * 50)
    conectar_mongo()
    conectar_redis()
    conectar_sqlite()
    print("=" * 50)