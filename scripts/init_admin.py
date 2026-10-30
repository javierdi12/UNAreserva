"""Crea o actualiza el administrador inicial desde variables de entorno."""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from src.crud import usuarios
from src.database import get_mongo_db


def main():
    load_dotenv()
    correo = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    nombre = (os.getenv("ADMIN_NAME") or "Administrador UNAreserva").strip()
    password = os.getenv("ADMIN_PASSWORD") or ""
    if not correo or not password:
        raise SystemExit("Configure ADMIN_EMAIL y ADMIN_PASSWORD en el entorno")

    existente = get_mongo_db()["usuarios"].find_one({"correo": correo})
    if existente:
        usuarios.actualizar(str(existente["_id"]), {
            "nombre": nombre,
            "rol": "administrador",
            "password": password,
            "activo": True,
        })
        print(f"[OK] Administrador actualizado: {correo}")
        return

    usuarios.crear({
        "nombre": nombre,
        "correo": correo,
        "rol": "administrador",
        "password": password,
    })
    print(f"[OK] Administrador creado: {correo}")


if __name__ == "__main__":
    main()
