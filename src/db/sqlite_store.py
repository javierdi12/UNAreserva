"""Almacenamiento local de solicitudes pendientes.

SQLite es una cola durable: una fila con estado ``pendiente`` nunca implica
que la reserva haya sido confirmada en MongoDB.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone

from src.config import Config


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS solicitudes_pendientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payload TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente', 'aceptada', 'rechazada', 'conflicto')),
    creado_en TEXT NOT NULL
)
"""


def conectar():
    """Abre la base local y garantiza el esquema de la cola."""
    path = os.path.abspath(Config.SQLITE_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conexion = sqlite3.connect(path)
    conexion.row_factory = sqlite3.Row
    conexion.execute(CREATE_TABLE)
    conexion.commit()
    return conexion


def guardar(payload, estado="pendiente"):
    """Guarda un payload JSON y devuelve el id local asignado."""
    if estado not in {"pendiente", "aceptada", "rechazada", "conflicto"}:
        raise ValueError("estado de solicitud no valido")
    with conectar() as conexion:
        cursor = conexion.execute(
            "INSERT INTO solicitudes_pendientes (payload, estado, creado_en) VALUES (?, ?, ?)",
            (json.dumps(payload, ensure_ascii=False, default=str), estado,
             datetime.now(timezone.utc).isoformat()),
        )
        return cursor.lastrowid


def listar(estado=None):
    """Lista solicitudes, opcionalmente filtradas por estado."""
    with conectar() as conexion:
        if estado is None:
            filas = conexion.execute(
                "SELECT id, payload, estado, creado_en FROM solicitudes_pendientes ORDER BY id"
            ).fetchall()
        else:
            filas = conexion.execute(
                "SELECT id, payload, estado, creado_en FROM solicitudes_pendientes "
                "WHERE estado = ? ORDER BY id", (estado,)
            ).fetchall()
    return [_fila_a_dict(fila) for fila in filas]


def cambiar_estado(solicitud_id, estado):
    """Cambia el estado de una solicitud y devuelve si existía."""
    if estado not in {"pendiente", "aceptada", "rechazada", "conflicto"}:
        raise ValueError("estado de solicitud no valido")
    with conectar() as conexion:
        resultado = conexion.execute(
            "UPDATE solicitudes_pendientes SET estado = ? WHERE id = ?",
            (estado, solicitud_id),
        )
        return resultado.rowcount == 1


def _fila_a_dict(fila):
    return {
        "id": fila["id"],
        "payload": json.loads(fila["payload"]),
        "estado": fila["estado"],
        "creado_en": fila["creado_en"],
    }
