"""Carga datos sintéticos deterministas en MongoDB.

La carga reemplaza el contenido de ``recursos`` y ``reservas`` para que cada
ejecución produzca el mismo conjunto de datos con la misma semilla.
"""

import argparse
import os
import random
import sys
from datetime import date, datetime, time, timedelta

from bson import ObjectId

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_mongo_db


DEFAULT_SEED = 42
DEFAULT_BASE_DATE = date(2030, 1, 7)
RESOURCE_TYPES = ("sala_estudio", "laboratorio", "cancha")
BUILDINGS = ("A", "B", "C")


def _argumentos():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--base-date", type=date.fromisoformat, default=DEFAULT_BASE_DATE,
        metavar="YYYY-MM-DD",
    )
    parser.add_argument("--resources", type=int, default=50)
    parser.add_argument("--reservations", type=int, default=100)
    return parser.parse_args()


def _validar_cantidad(nombre, cantidad):
    if cantidad < 0:
        raise ValueError(f"--{nombre} debe ser mayor o igual que 0")


def _crear_recursos(cantidad, rng, seed):
    recursos = []
    for i in range(cantidad):
        recursos.append({
            "_id": ObjectId(f"{seed % 2**32:08x}{i:016x}"),
            "nombre": f"Recurso {i + 1}",
            "tipo": rng.choice(RESOURCE_TYPES),
            "capacidad": rng.randint(2, 30),
            "ubicacion": f"Edificio {rng.choice(BUILDINGS)}, piso {rng.randint(1, 3)}",
            "horario": {"apertura": "07:00", "cierre": "21:00"},
        })
    return recursos


def _crear_reservas(recursos, cantidad, rng, base_date, seed):
    if cantidad and not recursos:
        raise ValueError("No se pueden crear reservas sin recursos")

    reservas = []
    for i in range(cantidad):
        recurso = recursos[rng.randrange(len(recursos))]
        inicio = datetime.combine(
            base_date + timedelta(days=rng.randint(0, 29)),
            time(rng.randint(7, 18), 0),
        )
        fin = inicio + timedelta(hours=rng.randint(1, 3))
        reservas.append({
            "_id": ObjectId(f"{(seed + 1) % 2**32:08x}{i:016x}"),
            "id_recurso": str(recurso["_id"]),
            "id_usuario": f"estudiante_{rng.randint(1, 100)}@una.ac.cr",
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "estado": "activa",
            "fecha_creacion": inicio.isoformat(),
        })
    return reservas


def generate_test_data(seed=DEFAULT_SEED, resources=50, reservations=100,
                       base_date=DEFAULT_BASE_DATE):
    """Reemplaza las colecciones con datos sintéticos deterministas."""
    _validar_cantidad("resources", resources)
    _validar_cantidad("reservations", reservations)

    rng = random.Random(seed)
    db = get_mongo_db()
    resources_collection = db["recursos"]
    bookings_collection = db["reservas"]

    print("Limpiando colecciones anteriores...")
    resources_collection.delete_many({})
    bookings_collection.delete_many({})

    recursos = _crear_recursos(resources, rng, seed)
    if recursos:
        resources_collection.insert_many(recursos)

    reservas = _crear_reservas(recursos, reservations, rng, base_date, seed)
    if reservas:
        bookings_collection.insert_many(reservas)

    print(
        f"[OK] Datos generados: {len(recursos)} recursos y {len(reservas)} "
        f"reservas (semilla={seed}, fecha_base={base_date.isoformat()})."
    )
    return len(recursos), len(reservas)


if __name__ == "__main__":
    args = _argumentos()
    generate_test_data(
        seed=args.seed,
        resources=args.resources,
        reservations=args.reservations,
        base_date=args.base_date,
    )
