"""CRUD de la coleccion `recursos`."""
from datetime import datetime

from src.core import cache
from src.core.errores import ErrorValidacion, NoEncontrado
from src.core.utils import oid, serializar
from src.crud import campus, tipos_recurso
from src.database import get_mongo_db


def _col():
    return get_mongo_db()["recursos"]


def _filtro_id(id_recurso, campus_id=None):
    filtro = {"_id": oid(id_recurso)}
    if campus_id == campus.DEFAULT_CAMPUS_ID:
        filtro["$or"] = [
            {"campus_id": campus_id},
            {"campus_id": {"$exists": False}},
        ]
    elif campus_id:
        filtro["campus_id"] = campus_id
    return filtro


def _validar(data, parcial=False, campus_id=None):
    if not parcial:
        faltan = [c for c in ("nombre", "tipo", "capacidad", "ubicacion", "campus_id") if not data.get(c)]
        if faltan:
            raise ErrorValidacion(f"Faltan campos: {', '.join(faltan)}")
    if "campus_id" in data and not campus.es_valido(data["campus_id"]):
        raise ErrorValidacion("Campus invalido")
    campus_id = data.get("campus_id", campus_id)
    if not campus.es_valido(campus_id):
        raise ErrorValidacion("Campus invalido")
    if "tipo" in data:
        validos = tipos_recurso.codigos(campus_id=campus_id)
        if data["tipo"] not in validos:
            raise ErrorValidacion(f"Tipo invalido. Opciones: {', '.join(sorted(validos))}")
    if "capacidad" in data:
        try:
            data["capacidad"] = int(data["capacidad"])
        except (ValueError, TypeError):
            raise ErrorValidacion("La capacidad debe ser un numero entero")
        if data["capacidad"] <= 0:
            raise ErrorValidacion("La capacidad debe ser mayor a 0")


def crear(data):
    """CREATE. data: nombre, tipo, capacidad, ubicacion, campus_id, [horario]."""
    _validar(data, campus_id=data.get("campus_id"))
    doc = {
        "nombre": data["nombre"].strip(),
        "tipo": data["tipo"],
        "capacidad": data["capacidad"],
        "ubicacion": data["ubicacion"].strip(),
        "campus_id": data["campus_id"],
        "horario": data.get("horario", {"apertura": "07:00", "cierre": "21:00"}),
    }
    res = _col().insert_one(doc)
    cache.invalidar("recursos:*")
    return str(res.inserted_id)


def listar(tipo=None, campus_id=None):
    """READ (lista) con cache."""
    k = cache.key("recursos", "lista", tipo or "todos", campus_id or "todos")
    cached = cache.get(k)
    if cached is not None:
        return cached

    filtro = {}
    if tipo:
        filtro["tipo"] = tipo
    if campus_id == campus.DEFAULT_CAMPUS_ID:
        filtro["$or"] = [
            {"campus_id": campus_id},
            {"campus_id": {"$exists": False}},
        ]
    elif campus_id:
        filtro["campus_id"] = campus_id
    recursos = [serializar(r) for r in _col().find(filtro)]
    cache.set(k, recursos)
    return recursos


def obtener(id_recurso, campus_id=None):
    """READ (uno) con cache."""
    k = cache.key("recursos", "detalle", id_recurso, campus_id or "todos")
    cached = cache.get(k)
    if cached is not None:
        return cached

    filtro = _filtro_id(id_recurso, campus_id)
    doc = _col().find_one(filtro)
    if not doc:
        raise NoEncontrado("Recurso no encontrado")
    serializar(doc)
    cache.set(k, doc)
    return doc


def actualizar(id_recurso, data):
    """UPDATE parcial: solo se modifican los campos enviados."""
    permitidos = {"nombre", "tipo", "capacidad", "ubicacion", "horario", "campus_id"}
    cambios = {k: v for k, v in data.items() if k in permitidos}
    if not cambios:
        raise ErrorValidacion("No hay campos para actualizar")
    recurso_actual = obtener(id_recurso)
    campus_destino = cambios.get("campus_id", recurso_actual.get("campus_id", campus.DEFAULT_CAMPUS_ID))
    _validar(cambios, parcial=True, campus_id=campus_destino)

    res = _col().update_one({"_id": oid(id_recurso)}, {"$set": cambios})
    if res.matched_count == 0:
        raise NoEncontrado("Recurso no encontrado")
    # Las listas de reservas incluyen el nombre del recurso, tambien se invalidan
    cache.invalidar("recursos:*", "reservas:*")
    return True


def eliminar(id_recurso, campus_id=None):
    """DELETE. No permite borrar si hay reservas activas futuras."""
    pendientes = get_mongo_db()["reservas"].count_documents({
        "id_recurso": id_recurso,
        "estado": "activa",
        "fecha_fin": {"$gt": datetime.now().isoformat()},
    })
    if pendientes:
        raise ErrorValidacion(f"No se puede eliminar: tiene {pendientes} reserva(s) activa(s)")

    res = _col().delete_one(_filtro_id(id_recurso, campus_id))
    if res.deleted_count == 0:
        raise NoEncontrado("Recurso no encontrado")
    cache.invalidar("recursos:*", "reservas:*")
    return True
