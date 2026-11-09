"""Catalogo de campus disponibles en UNAreserva."""

from urllib.parse import urlparse


CAMPUS = (
    {"id": "omar_dengo", "nombre": "Campus Omar Dengo"},
    {"id": "benjamin_nunez", "nombre": "Campus Benjamín Núñez"},
)
DEFAULT_CAMPUS_ID = CAMPUS[0]["id"]
_CAMPUS_IDS = {campus["id"] for campus in CAMPUS}


def listar():
    return [dict(campus) for campus in CAMPUS]


def es_valido(campus_id):
    return campus_id in _CAMPUS_IDS


def normalizar(campus_id):
    return campus_id if es_valido(campus_id) else DEFAULT_CAMPUS_ID


def url_local(url):
    """Evita usar una URL externa como destino después de cambiar campus."""
    parsed = urlparse(url or "")
    if parsed.scheme or parsed.netloc:
        return "/dashboard"
    return url or "/dashboard"
