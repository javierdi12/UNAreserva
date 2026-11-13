"""CRUD de la coleccion `reservas`. Depende de crud.recursos."""
import json
from datetime import datetime

from src.core import cache
from src.core.errores import ErrorValidacion, NoEncontrado
from src.core.utils import oid, parse_fecha, serializar
from src.crud import recursos
from src.database import get_mongo_db


def _col():
    return get_mongo_db()["reservas"]


def _validar_horario(recurso, inicio, fin):
    if inicio >= fin:
        raise ErrorValidacion("La fecha de inicio debe ser anterior a la de fin")
    if inicio < datetime.now():
        raise ErrorValidacion("No se puede reservar en el pasado")
    if inicio.date() != fin.date():
        raise ErrorValidacion("La reserva debe iniciar y terminar el mismo dia")

    horario = recurso.get("horario", {})
    apertura = datetime.strptime(horario.get("apertura", "07:00"), "%H:%M").time()
    cierre = datetime.strptime(horario.get("cierre", "21:00"), "%H:%M").time()
    if inicio.time() < apertura or fin.time() > cierre:
        raise ErrorValidacion(f"Fuera de horario ({apertura:%H:%M} - {cierre:%H:%M})")


def _hay_traslape(id_recurso, inicio_iso, fin_iso, excluir_id=None):
    """Traslape si: inicio_existente < fin_nuevo Y fin_existente > inicio_nuevo."""
    filtro = {
        "id_recurso": id_recurso,
        "estado": "activa",
        "fecha_inicio": {"$lt": fin_iso},
        "fecha_fin": {"$gt": inicio_iso},
    }
    if excluir_id:
        filtro["_id"] = {"$ne": oid(excluir_id)}
    return _col().count_documents(filtro) > 0


def crear(id_recurso, id_usuario, fecha_inicio, fecha_fin):
    """CREATE. Fechas en formato ISO 8601 (str)."""
    if not id_usuario:
        raise ErrorValidacion("Falta el usuario")
    recurso = recursos.obtener(id_recurso)  # lanza NoEncontrado si no existe
    inicio = parse_fecha(fecha_inicio, "fecha_inicio")
    fin = parse_fecha(fecha_fin, "fecha_fin")
    _validar_horario(recurso, inicio, fin)

    with cache.Candado(id_recurso):
        if _hay_traslape(id_recurso, inicio.isoformat(), fin.isoformat()):
            raise ErrorValidacion("El recurso ya esta reservado en ese horario")
        res = _col().insert_one({
            "id_recurso": id_recurso,
            "id_usuario": id_usuario,
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "estado": "activa",
            "fecha_creacion": datetime.now().isoformat(),
            "actualizado_en": datetime.now().isoformat(),
            "origen": "web",
            "historial": [{"estado": "activa", "fecha": datetime.now().isoformat()}],
        })

    cache.invalidar("reservas:*")
    return str(res.inserted_id)


def listar(id_usuario=None, id_recurso=None, estado=None, limite=0):
    """READ (lista) con cache. Agrega `nombre_recurso` a cada reserva."""
    filtro = {}
    if id_usuario:
        filtro["id_usuario"] = id_usuario
    if id_recurso:
        filtro["id_recurso"] = id_recurso
    if estado:
        filtro["estado"] = estado

    k = cache.key("reservas", "lista", json.dumps(filtro, sort_keys=True), str(limite))
    cached = cache.get(k)
    if cached is not None:
        return cached

    lista = [serializar(r) for r in _col().find(filtro).sort("fecha_inicio", 1).limit(limite)]
    for r in lista:
        try:
            r["nombre_recurso"] = recursos.obtener(r["id_recurso"])["nombre"]
        except (NoEncontrado, ErrorValidacion):
            r["nombre_recurso"] = "Recurso eliminado"

    cache.set(k, lista)
    return lista


def obtener(id_reserva):
    """READ (uno)."""
    doc = _col().find_one({"_id": oid(id_reserva)})
    if not doc:
        raise NoEncontrado("Reserva no encontrada")
    return serializar(doc)


def actualizar(id_reserva, fecha_inicio, fecha_fin):
    """UPDATE: reprogramar una reserva activa."""
    reserva = obtener(id_reserva)
    if reserva["estado"] != "activa":
        raise ErrorValidacion("Solo se pueden modificar reservas activas")

    recurso = recursos.obtener(reserva["id_recurso"])
    inicio = parse_fecha(fecha_inicio, "fecha_inicio")
    fin = parse_fecha(fecha_fin, "fecha_fin")
    _validar_horario(recurso, inicio, fin)

    with cache.Candado(reserva["id_recurso"]):
        if _hay_traslape(reserva["id_recurso"], inicio.isoformat(), fin.isoformat(),
                         excluir_id=id_reserva):
            raise ErrorValidacion("El recurso ya esta reservado en ese horario")
        _col().update_one(
            {"_id": oid(id_reserva)},
            {"$set": {
                "fecha_inicio": inicio.isoformat(), "fecha_fin": fin.isoformat(),
                "actualizado_en": datetime.now().isoformat(),
            }, "$push": {"historial": {
                "estado": "reprogramada", "fecha": datetime.now().isoformat(),
                "fecha_inicio": inicio.isoformat(), "fecha_fin": fin.isoformat(),
            }}},
        )

    cache.invalidar("reservas:*")
    return True


def cancelar(id_reserva):
    """UPDATE de estado (baja logica, conserva el historial)."""
    ahora = datetime.now().isoformat()
    res = _col().update_one(
        {"_id": oid(id_reserva)},
        {"$set": {"estado": "cancelada", "cancelado_en": ahora, "actualizado_en": ahora},
         "$push": {"historial": {"estado": "cancelada", "fecha": ahora}}},
    )
    if res.matched_count == 0:
        raise NoEncontrado("Reserva no encontrada")
    cache.invalidar("reservas:*")
    return True


def eliminar(id_reserva):
    """DELETE fisico (solo administracion)."""
    res = _col().delete_one({"_id": oid(id_reserva)})
    if res.deleted_count == 0:
        raise NoEncontrado("Reserva no encontrada")
    cache.invalidar("reservas:*")
    return True
