"""Catalogo de campus disponibles en UNAreserva."""

from urllib.parse import urlparse
import re
import unicodedata

from pymongo.errors import DuplicateKeyError
from src.core.errores import ErrorValidacion
from src.database import get_mongo_db


CAMPUS = (
    {"id": "omar_dengo", "nombre": "Campus Omar Dengo"},
    {"id": "benjamin_nunez", "nombre": "Campus Benjamín Núñez"},
)
DEFAULT_CAMPUS_ID = CAMPUS[0]["id"]



def listar():
    adicionales = get_mongo_db()["campus"].find({}, {"_id": 0, "id": 1, "nombre": 1}).sort("nombre", 1)
    return [dict(c) for c in CAMPUS] + list(adicionales)


def crear(nombre):
    nombre = (nombre or "").strip()
    if not nombre:
        raise ErrorValidacion("El nombre es obligatorio")
    if len(nombre) > 80:
        raise ErrorValidacion("El nombre no puede superar 80 caracteres")
    ascii_ = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    identificador = re.sub(r"[^a-z0-9]+", "_", ascii_.lower()).strip("_")
    if not identificador:
        raise ErrorValidacion("El nombre debe incluir letras o números")
    nombres_base = {re.sub(r"[^a-z0-9]+", "_",
                       unicodedata.normalize("NFKD", c["nombre"]).encode("ascii", "ignore").decode().lower()).strip("_")
                    for c in CAMPUS}
    if identificador in {c["id"] for c in CAMPUS} or identificador in nombres_base:
        raise ErrorValidacion("Ya existe un campus con ese nombre")
    try:
        get_mongo_db()["campus"].insert_one({"_id": identificador, "id": identificador, "nombre": nombre})
    except DuplicateKeyError:
        raise ErrorValidacion("Ya existe un campus con ese nombre")
    return identificador


def es_valido(campus_id):
    if campus_id in {c["id"] for c in CAMPUS}:
        return True
    return bool(campus_id and get_mongo_db()["campus"].find_one({"_id": campus_id}))


def normalizar(campus_id):
    return campus_id if es_valido(campus_id) else DEFAULT_CAMPUS_ID


def url_local(url):
    """Evita usar una URL externa como destino después de cambiar campus."""
    parsed = urlparse(url or "")
    if parsed.scheme or parsed.netloc:
        return "/dashboard"
    return url or "/dashboard"
