"""

- MongoDB: catalogo de recursos y reservas.
- Redis:   bloqueo temporal (TTL) mientras se valida y guarda una reserva.
- SQLite:  respaldo local cuando MongoDB o Redis no estan disponibles.

"""
import sqlite3
import uuid
from datetime import date, datetime, time, timedelta

import certifi
import redis
from bson import ObjectId
from bson.errors import InvalidId
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from src.config import Config
from src.models import Recurso, Reserva

LOCK_TTL = 10  # segundos que dura el bloqueo en Redis

_mongo = None


# errores
class ReservaError(Exception):
    """Error de negocio al reservar."""


class ConflictoReserva(ReservaError):
    """El horario solicitado choca con otra reserva activa."""


class RecursoOcupado(ReservaError):
    """Otro usuario tiene el bloqueo temporal del recurso."""


# conexiones
def get_db():
    global _mongo
    if _mongo is None:
        _mongo = MongoClient(
            Config.MONGO_URI,
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where(),
        )
    return _mongo.unareserva_db


def get_redis():
    return redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=3,
    )


def _conn_sqlite():
    return sqlite3.connect(Config.SQLITE_PATH)


#  utilidades
def _oid(id_recurso):
    try:
        return ObjectId(id_recurso)
    except (InvalidId, TypeError):
        raise ValueError("id_recurso invalido")


def _hora(texto):
    return datetime.strptime(texto, "%H:%M").time()


def _obtener_recurso(db, id_recurso):
    recurso = db.recursos.find_one({"_id": _oid(id_recurso)})
    if recurso is None:
        raise ValueError("El recurso no existe")
    return recurso


def _validar_rango(inicio, fin):
    if inicio >= fin:
        raise ValueError("La hora de inicio debe ser menor que la de fin")
    if inicio.date() != fin.date():
        raise ValueError("La reserva debe empezar y terminar el mismo dia")


def _validar_horario(recurso, inicio, fin):
    apertura = _hora(recurso["horario"]["apertura"])
    cierre = _hora(recurso["horario"]["cierre"])
    if inicio.time() < apertura or fin.time() > cierre:
        raise ValueError(
            f"Fuera del horario del recurso ({apertura:%H:%M} - {cierre:%H:%M})"
        )


# recursos
def crear_recurso(recurso: Recurso):
    """Guarda un recurso y devuelve su id (str)."""
    return str(get_db().recursos.insert_one(recurso.to_dict()).inserted_id)


def listar_recursos(tipo=None):
    filtro = {"tipo": tipo} if tipo else {}
    return list(get_db().recursos.find(filtro).sort("nombre", 1))


# disponibilidad
def consultar_disponibilidad(id_recurso, dia: date):
    """Devuelve la lista de bloques libres [(inicio, fin), ...] del dia."""
    db = get_db()
    recurso = _obtener_recurso(db, id_recurso)
    apertura = datetime.combine(dia, _hora(recurso["horario"]["apertura"]))
    cierre = datetime.combine(dia, _hora(recurso["horario"]["cierre"]))

    ocupadas = db.reservas.find({
        "id_recurso": str(id_recurso),
        "estado": "activa",
        "fecha_inicio": {"$lt": cierre},
        "fecha_fin": {"$gt": apertura},
    }).sort("fecha_inicio", 1)

    libres, cursor = [], apertura
    for r in ocupadas:
        if r["fecha_inicio"] > cursor:
            libres.append((cursor, r["fecha_inicio"]))
        cursor = max(cursor, r["fecha_fin"])
    if cursor < cierre:
        libres.append((cursor, cierre))
    return libres


# reservar
def _intentar_reserva(id_recurso, id_usuario, inicio, fin):
    """Reserva con bloqueo en Redis y validacion de choques en MongoDB."""
    db = get_db()
    r = get_redis()
    clave = f"{Config.REDIS_PREFIX}lock:{id_recurso}"
    token = uuid.uuid4().hex

    if not r.set(clave, token, nx=True, ex=LOCK_TTL):
        raise RecursoOcupado("Otro usuario esta reservando este recurso, intenta de nuevo")
    try:
        recurso = _obtener_recurso(db, id_recurso)
        _validar_horario(recurso, inicio, fin)

        choque = db.reservas.find_one({
            "id_recurso": str(id_recurso),
            "estado": "activa",
            "fecha_inicio": {"$lt": fin},
            "fecha_fin": {"$gt": inicio},
        })
        if choque:
            raise ConflictoReserva("Ya existe una reserva en ese horario")

        reserva = Reserva(str(id_recurso), id_usuario, inicio, fin)
        return str(db.reservas.insert_one(reserva.to_dict()).inserted_id)
    finally:
        try:
            if r.get(clave) == token:
                r.delete(clave)
        except RedisError:
            pass  # el TTL liberara el bloqueo solo


def _guardar_pendiente(id_recurso, id_usuario, inicio, fin):
    conn = _conn_sqlite()
    conn.execute(
        "INSERT INTO pendientes (id_recurso, id_usuario, fecha_inicio, fecha_fin) "
        "VALUES (?, ?, ?, ?)",
        (str(id_recurso), id_usuario, inicio.isoformat(), fin.isoformat()),
    )
    conn.commit()
    conn.close()


def reservar(id_recurso, id_usuario, inicio: datetime, fin: datetime):
    """
    Intenta reservar. Devuelve {"estado": "confirmada", "id": ...} o, si hay
    caida de red (Mongo/Redis), {"estado": "pendiente", "id": None} guardada
    en SQLite para sincronizar despues.
    Lanza ValueError / ConflictoReserva / RecursoOcupado en errores de negocio.
    """
    _validar_rango(inicio, fin)
    try:
        return {"estado": "confirmada",
                "id": _intentar_reserva(id_recurso, id_usuario, inicio, fin)}
    except (PyMongoError, RedisError):
        _guardar_pendiente(id_recurso, id_usuario, inicio, fin)
        return {"estado": "pendiente", "id": None}


def cancelar_reserva(id_reserva):
    """Marca la reserva como cancelada. True si se cancelo."""
    res = get_db().reservas.update_one(
        {"_id": _oid(id_reserva), "estado": "activa"},
        {"$set": {"estado": "cancelada"}},
    )
    return res.modified_count == 1


def reservas_del_dia(dia: date, id_recurso=None):
    desde = datetime.combine(dia, time.min)
    filtro = {"estado": "activa",
              "fecha_inicio": {"$gte": desde, "$lt": desde + timedelta(days=1)}}
    if id_recurso:
        filtro["id_recurso"] = str(id_recurso)
    return list(get_db().reservas.find(filtro).sort("fecha_inicio", 1))


# sincronizacion
def sincronizar_pendientes():
    """
    Reenvia a MongoDB lo guardado en SQLite.
    sincronizado: 0 = pendiente, 1 = confirmada, -1 = rechazada (choque o dato invalido).
    Devuelve (confirmadas, rechazadas).
    """
    conn = _conn_sqlite()
    filas = conn.execute(
        "SELECT id, id_recurso, id_usuario, fecha_inicio, fecha_fin "
        "FROM pendientes WHERE sincronizado = 0"
    ).fetchall()

    ok = rechazadas = 0
    for id_, id_recurso, id_usuario, ini, fin in filas:
        try:
            _intentar_reserva(id_recurso, id_usuario,
                              datetime.fromisoformat(ini), datetime.fromisoformat(fin))
            estado = 1
            ok += 1
        except (ReservaError, ValueError):
            estado = -1
            rechazadas += 1
        except (PyMongoError, RedisError):
            break  # sigue sin red; se reintenta luego
        conn.execute("UPDATE pendientes SET sincronizado = ? WHERE id = ?", (estado, id_))
        conn.commit()
    conn.close()
    return ok, rechazadas


# demo
if __name__ == "__main__":
    hoy = date.today()
    id_sala = crear_recurso(Recurso("Sala de estudio 1", "sala", 8, "Biblioteca, piso 2"))
    print("Recurso creado:", id_sala)

    r1 = reservar(id_sala, "est-001",
                  datetime.combine(hoy, time(9, 0)), datetime.combine(hoy, time(11, 0)))
    print("Reserva 1:", r1)

    try:
        reservar(id_sala, "est-002",
                 datetime.combine(hoy, time(10, 0)), datetime.combine(hoy, time(12, 0)))
    except ReservaError as e:
        print("Reserva 2 rechazada:", e)

    print("Bloques libres:")
    for a, b in consultar_disponibilidad(id_sala, hoy):
        print(f"  {a:%H:%M} - {b:%H:%M}")

    print("Reservas de hoy:", len(reservas_del_dia(hoy)))
    print("Cancelada:", cancelar_reserva(r1["id"]))
    print("Sincronizacion (ok, rechazadas):", sincronizar_pendientes())