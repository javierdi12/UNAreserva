"""
API REST de UNAreserva (Flask).

Ejecutar desde la raiz del proyecto:
    python src/app.py
"""
from datetime import date, datetime

from bson import ObjectId
from flask import Flask, jsonify, request
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

import servicios
from config import Config
from models import Recurso
from servicios import ConflictoReserva, RecursoOcupado

app = Flask(__name__)
app.config["SECRET_KEY"] = Config.SECRET_KEY


# utilidades
def _serializar(valor):
    """Convierte ObjectId y datetime a tipos aptos para JSON."""
    if isinstance(valor, ObjectId):
        return str(valor)
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {k: _serializar(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_serializar(v) for v in valor]
    return valor


def _fecha_param(nombre="fecha"):
    """Lee ?fecha=YYYY-MM-DD; si no viene, usa hoy."""
    texto = request.args.get(nombre)
    if not texto:
        return date.today()
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise ValueError(f"'{nombre}' debe tener formato YYYY-MM-DD")


def _json_requerido(*campos):
    datos = request.get_json(silent=True) or {}
    faltan = [c for c in campos if c not in datos]
    if faltan:
        raise ValueError(f"Faltan campos: {', '.join(faltan)}")
    return datos


def _datetime_campo(datos, campo):
    try:
        return datetime.fromisoformat(datos[campo])
    except (ValueError, TypeError):
        raise ValueError(f"'{campo}' debe tener formato ISO (YYYY-MM-DDTHH:MM)")


#  errores
@app.errorhandler(ValueError)
def error_validacion(e):
    return jsonify(error=str(e)), 400


@app.errorhandler(ConflictoReserva)
def error_conflicto(e):
    return jsonify(error=str(e)), 409


@app.errorhandler(RecursoOcupado)
def error_ocupado(e):
    return jsonify(error=str(e)), 423


@app.errorhandler(PyMongoError)
@app.errorhandler(RedisError)
def error_servicio(e):
    return jsonify(error="Servicio no disponible, intenta de nuevo"), 503


#  rutas
@app.get("/api/salud")
def salud():
    estado = {}
    try:
        servicios.get_db().client.admin.command("ping")
        estado["mongodb"] = "ok"
    except PyMongoError:
        estado["mongodb"] = "error"
    try:
        servicios.get_redis().ping()
        estado["redis"] = "ok"
    except RedisError:
        estado["redis"] = "error"
    return jsonify(estado)


@app.get("/api/recursos")
def listar_recursos():
    recursos = servicios.listar_recursos(request.args.get("tipo"))
    return jsonify(_serializar(recursos))


@app.post("/api/recursos")
def crear_recurso():
    d = _json_requerido("nombre", "tipo", "capacidad", "ubicacion")
    recurso = Recurso(
        nombre=d["nombre"],
        tipo=d["tipo"],
        capacidad=int(d["capacidad"]),
        ubicacion=d["ubicacion"],
        horario_apertura=d.get("horario_apertura", "07:00"),
        horario_cierre=d.get("horario_cierre", "21:00"),
    )
    return jsonify(id=servicios.crear_recurso(recurso)), 201


@app.get("/api/recursos/<id_recurso>/disponibilidad")
def disponibilidad(id_recurso):
    libres = servicios.consultar_disponibilidad(id_recurso, _fecha_param())
    return jsonify([{"inicio": a.isoformat(), "fin": b.isoformat()} for a, b in libres])


@app.post("/api/reservas")
def reservar():
    d = _json_requerido("id_recurso", "id_usuario", "fecha_inicio", "fecha_fin")
    resultado = servicios.reservar(
        d["id_recurso"],
        d["id_usuario"],
        _datetime_campo(d, "fecha_inicio"),
        _datetime_campo(d, "fecha_fin"),
    )
    # 201 = confirmada en MongoDB, 202 = aceptada y guardada en SQLite (pendiente)
    codigo = 201 if resultado["estado"] == "confirmada" else 202
    return jsonify(resultado), codigo


@app.get("/api/reservas/dia")
def reservas_del_dia():
    reservas = servicios.reservas_del_dia(_fecha_param(), request.args.get("id_recurso"))
    return jsonify(_serializar(reservas))


@app.delete("/api/reservas/<id_reserva>")
def cancelar(id_reserva):
    if servicios.cancelar_reserva(id_reserva):
        return jsonify(estado="cancelada")
    return jsonify(error="Reserva no encontrada o ya cancelada"), 404


@app.post("/api/sincronizar")
def sincronizar():
    confirmadas, rechazadas = servicios.sincronizar_pendientes()
    return jsonify(confirmadas=confirmadas, rechazadas=rechazadas)


if __name__ == "__main__":
    app.run(debug=True)