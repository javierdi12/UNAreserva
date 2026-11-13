"""CRUD de solicitudes pendientes almacenadas localmente."""

from src.db import sqlite_store

ESTADOS = frozenset(("pendiente", "aceptada", "rechazada", "conflicto"))


def crear(payload):
    """Registra una solicitud nueva y devuelve su identificador local."""
    if not isinstance(payload, dict) or not payload:
        raise ValueError("el payload debe ser un objeto no vacio")
    return sqlite_store.guardar(payload)


def listar(estado=None):
    """Devuelve solicitudes ordenadas por creación."""
    if estado is not None and estado not in ESTADOS:
        raise ValueError("estado de solicitud no valido")
    return sqlite_store.listar(estado)


def obtener(solicitud_id):
    """Busca una solicitud por id local."""
    solicitudes = sqlite_store.listar()
    return next((item for item in solicitudes if item["id"] == int(solicitud_id)), None)


def cambiar_estado(solicitud_id, estado):
    """Actualiza el estado y devuelve la solicitud actualizada."""
    if estado not in ESTADOS:
        raise ValueError("estado de solicitud no valido")
    if not sqlite_store.cambiar_estado(solicitud_id, estado):
        return None
    return obtener(solicitud_id)
