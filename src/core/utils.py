"""Utilidades compartidas por los CRUD."""
from datetime import datetime

from bson.errors import InvalidId
from bson.objectid import ObjectId

from src.core.errores import ErrorValidacion


def oid(id_str):
    """Convierte un str a ObjectId o lanza ErrorValidacion."""
    try:
        return ObjectId(id_str)
    except (InvalidId, TypeError):
        raise ErrorValidacion(f"ID invalido: {id_str}")


def serializar(doc):
    """Convierte _id (ObjectId) a str para JSON, cache y templates."""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def parse_fecha(valor, campo):
    """Convierte un str ISO 8601 a datetime."""
    try:
        return datetime.fromisoformat(valor) if isinstance(valor, str) else valor
    except ValueError:
        raise ErrorValidacion(f"Formato de fecha invalido en '{campo}' (use ISO 8601)")