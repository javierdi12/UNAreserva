"""
UNAreserva (Flask): API REST (main) + vistas web (developer).

Ejecutar desde la raiz del proyecto:
    python -m src.app
"""
from datetime import date, datetime

from bson import ObjectId
from flask import (
    Flask, flash, jsonify, redirect, render_template, request, url_for,
)
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

# --- main (API REST) ---
from src import servicios
from src.config import Config
from src.models import Recurso
from src.servicios import ConflictoReserva, RecursoOcupado

# --- developer (vistas web) ---
from src.crud import recursos, reservas, usuarios
from src.core.errores import ErrorValidacion, NoEncontrado

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)
app.config["SECRET_KEY"] = Config.SECRET_KEY

USER_EMAIL = "estudiante_1@una.ac.cr"  # TODO: reemplazar por el usuario en sesion


# =====================================================================
# API REST (main)
# =====================================================================

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


# errores
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


# rutas API
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
    lista = servicios.listar_recursos(request.args.get("tipo"))
    return jsonify(_serializar(lista))


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
    lista = servicios.reservas_del_dia(_fecha_param(), request.args.get("id_recurso"))
    return jsonify(_serializar(lista))


@app.delete("/api/reservas/<id_reserva>")
def cancelar(id_reserva):
    if servicios.cancelar_reserva(id_reserva):
        return jsonify(estado="cancelada")
    return jsonify(error="Reserva no encontrada o ya cancelada"), 404


@app.post("/api/sincronizar")
def sincronizar():
    confirmadas, rechazadas = servicios.sincronizar_pendientes()
    return jsonify(confirmadas=confirmadas, rechazadas=rechazadas)


# =====================================================================
# VISTAS WEB (developer)
# =====================================================================

# --- MAIN VIEWS ---
@app.route('/')
def dashboard():
    resources = recursos.listar()
    bookings = reservas.listar(limite=5)
    active_bookings = reservas.listar(estado="activa")
    now = datetime.now()
    hours_this_month = 0.0

    for booking in active_bookings:
        try:
            start = booking.get("fecha_inicio")
            end = booking.get("fecha_fin")
            start = datetime.fromisoformat(start) if isinstance(start, str) else start
            end = datetime.fromisoformat(end) if isinstance(end, str) else end
            if start and end and start.year == now.year and start.month == now.month:
                hours_this_month += (end - start).total_seconds() / 3600
        except (TypeError, ValueError):
            # Ignora registros antiguos con fechas incompletas o invalidas.
            continue

    return render_template(
        'dashboard.html',
        resources=resources,
        bookings=bookings,
        stats={
            "activas": len(active_bookings),
            "horas_mes": round(hours_this_month, 1),
        },
        disponibles_total=len(resources),
        total_espacios=len(resources),
        hoy_texto=now.strftime("%d/%m/%Y"),
    )


@app.route('/spaces')
def spaces():
    tipo = request.args.get('tipo')  # filtro opcional: /spaces?tipo=laboratorio
    return render_template('spaces.html', resources=recursos.listar(tipo))


# --- CRUD RESOURCES ---
@app.route('/resources/new', methods=['GET', 'POST'])
def create_resource():
    if request.method == 'POST':
        try:
            recursos.crear({
                "nombre": request.form['nombre'],
                "tipo": request.form['tipo'],
                "capacidad": request.form['capacidad'],
                "ubicacion": request.form['ubicacion'],
            })
            flash('Recurso creado exitosamente', 'success')
            return redirect(url_for('spaces'))
        except ErrorValidacion as e:
            flash(str(e), 'danger')
    return render_template('create_resource.html', resource=None)


@app.route('/resources/edit/<id>', methods=['GET', 'POST'])
def edit_resource(id):
    try:
        resource = recursos.obtener(id)
    except (NoEncontrado, ErrorValidacion) as e:
        flash(str(e), 'danger')
        return redirect(url_for('spaces'))

    if request.method == 'POST':
        try:
            recursos.actualizar(id, {
                "nombre": request.form['nombre'],
                "tipo": request.form['tipo'],
                "capacidad": request.form['capacidad'],
                "ubicacion": request.form['ubicacion'],
            })
            flash('Recurso actualizado', 'success')
            return redirect(url_for('spaces'))
        except (NoEncontrado, ErrorValidacion) as e:
            flash(str(e), 'danger')
    return render_template('create_resource.html', resource=resource)


@app.route('/resources/delete/<id>', methods=['POST'])
def delete_resource(id):
    try:
        recursos.eliminar(id)
        flash('Recurso eliminado', 'info')
    except (NoEncontrado, ErrorValidacion) as e:
        flash(str(e), 'danger')
    return redirect(url_for('spaces'))


# --- BOOKINGS ---
@app.route('/bookings/new/<id_recurso>', methods=['POST'])
def create_booking(id_recurso):
    try:
        reservas.crear(
            id_recurso, USER_EMAIL,
            request.form['fecha_inicio'], request.form['fecha_fin']
        )
        flash('Reserva creada exitosamente', 'success')
    except (NoEncontrado, ErrorValidacion) as e:
        flash(str(e), 'danger')
    return redirect(url_for('my_bookings'))


@app.route('/my-bookings')
def my_bookings():
    return render_template('bookings.html', bookings=reservas.listar(id_usuario=USER_EMAIL))


@app.route('/bookings/edit/<id>', methods=['POST'])
def edit_booking(id):
    try:
        reservas.actualizar(id, request.form['fecha_inicio'], request.form['fecha_fin'])
        flash('Reserva actualizada', 'success')
    except (NoEncontrado, ErrorValidacion) as e:
        flash(str(e), 'danger')
    return redirect(url_for('my_bookings'))


@app.route('/bookings/cancel/<id>', methods=['POST'])
def cancel_booking(id):
    try:
        reservas.cancelar(id)
        flash('Reserva cancelada exitosamente', 'info')
    except (NoEncontrado, ErrorValidacion) as e:
        flash(str(e), 'danger')
    return redirect(url_for('my_bookings'))


# --- CALENDAR ---
@app.route('/calendar')
def calendar():
    return render_template('calendar.html')


@app.route('/api/bookings')
def api_bookings():
    events = []
    for b in reservas.listar(id_usuario=USER_EMAIL):
        color = "#D32F2F" if b["estado"] == "activa" else "#9e9e9e"
        events.append({
            "id": b["_id"],
            "title": b["nombre_recurso"],
            "start": b["fecha_inicio"],
            "end": b["fecha_fin"],
            "backgroundColor": color,
            "borderColor": color,
        })
    return jsonify(events)


# --- CRUD USERS ---
@app.route('/users')
def users():
    return render_template('user.html', users=usuarios.listar())


@app.route('/users/new', methods=['GET', 'POST'])
def create_user():
    if request.method == 'POST':
        try:
            usuarios.crear({
                "nombre": request.form['nombre'],
                "correo": request.form['correo'],
                "rol": request.form['rol'],
            })
            flash('Usuario creado exitosamente', 'success')
            return redirect(url_for('users'))
        except ErrorValidacion as e:
            flash(str(e), 'danger')
    return render_template('user_form.html', user=None)


@app.route('/users/edit/<id>', methods=['GET', 'POST'])
def edit_user(id):
    try:
        user = usuarios.obtener(id)
    except (NoEncontrado, ErrorValidacion) as e:
        flash(str(e), 'danger')
        return redirect(url_for('users'))

    if request.method == 'POST':
        try:
            usuarios.actualizar(id, {
                "nombre": request.form['nombre'],
                "rol": request.form['rol'],
            })
            flash('Usuario actualizado', 'success')
            return redirect(url_for('users'))
        except (NoEncontrado, ErrorValidacion) as e:
            flash(str(e), 'danger')
    return render_template('user_form.html', user=user)


@app.route('/users/delete/<id>', methods=['POST'])
def delete_user(id):
    try:
        usuarios.eliminar(id)
        flash('Usuario eliminado', 'info')
    except (NoEncontrado, ErrorValidacion) as e:
        flash(str(e), 'danger')
    return redirect(url_for('users'))


@app.route('/settings')
def settings():
    return render_template('settings.html')


@app.route('/logout')
def logout():
    flash('Has cerrado sesión', 'success')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    print("Iniciando servidor web de UNAreserva...")
    app.run(debug=True, use_reloader=False)    # Pasar a True para debuguear.
    
