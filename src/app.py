"""
UNAreserva (Flask): API REST (main) + vistas web (developer).

Ejecutar desde la raiz del proyecto:
    python -m src.app
"""
from datetime import date, datetime
from email.message import EmailMessage
from functools import wraps
import smtplib

from bson import ObjectId
from flask import (
    Flask, flash, jsonify, redirect, render_template, request, session, url_for,
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

# =====================================================================
# API REST (main)
# =====================================================================


def _es_api():
    return request.path.startswith("/api/")


def _usuario_actual():
    return session.get("usuario")


@app.context_processor
def contexto_autenticacion():
    return {"usuario_actual": _usuario_actual()}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not _usuario_actual():
            if _es_api():
                return jsonify(error="Autenticación requerida"), 401
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        usuario = _usuario_actual()
        if not usuario:
            if _es_api():
                return jsonify(error="Autenticación requerida"), 401
            return redirect(url_for("login", next=request.path))
        if usuario.get("rol") != "administrador":
            if _es_api():
                return jsonify(error="Permisos insuficientes"), 403
            flash("No tienes permisos para acceder a esta sección", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


@app.after_request
def no_cache_protected_pages(response):
    if session.get("usuario"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


def _enviar_recuperacion(correo, enlace):
    if not Config.SMTP_HOST:
        app.logger.warning("SMTP no configurado; enlace de recuperación: %s", enlace)
        return False
    mensaje = EmailMessage()
    mensaje["Subject"] = "Recuperación de contraseña - UNAreserva"
    mensaje["From"] = Config.SMTP_FROM
    mensaje["To"] = correo
    mensaje.set_content(
        "Solicitaste restablecer tu contraseña de UNAreserva.\n\n"
        f"Abre este enlace antes de que expire:\n{enlace}\n\n"
        "Si no hiciste esta solicitud, ignora este correo."
    )
    with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as servidor:
        if Config.SMTP_USE_TLS:
            servidor.starttls()
        if Config.SMTP_USERNAME:
            servidor.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        servidor.send_message(mensaje)
    return True


@app.route("/login", methods=["GET", "POST"])
def login():
    if _usuario_actual():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        usuario = usuarios.autenticar(request.form.get("correo"), request.form.get("password"))
        if usuario:
            session.clear()
            session["usuario"] = usuario
            return redirect(url_for("dashboard"))
        flash("Correo o contraseña incorrectos", "danger")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if _usuario_actual():
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        try:
            usuarios.crear_estudiante({
                "nombre": request.form.get("nombre"),
                "correo": request.form.get("correo"),
                "password": request.form.get("password"),
            })
            flash("Cuenta creada. Ya puedes iniciar sesión", "success")
            return redirect(url_for("login"))
        except ErrorValidacion as e:
            flash(str(e), "danger")
    return render_template("register.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        resultado = usuarios.crear_token_recuperacion(request.form.get("correo"))
        if resultado:
            token, usuario = resultado
            enlace = f"{Config.APP_BASE_URL.rstrip('/')}{url_for('reset_password', token=token)}"
            try:
                _enviar_recuperacion(usuario["correo"], enlace)
            except (OSError, smtplib.SMTPException):
                app.logger.exception("No fue posible enviar recuperación")
        flash("Si el correo existe, recibirás instrucciones para recuperar la contraseña", "info")
        return redirect(url_for("forgot_password"))
    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "POST":
        try:
            if request.form.get("password") != request.form.get("password_confirm"):
                raise ErrorValidacion("Las contraseñas no coinciden")
            usuarios.restablecer_password(token, request.form.get("password"))
            flash("Contraseña actualizada. Ya puedes iniciar sesión", "success")
            return redirect(url_for("login"))
        except ErrorValidacion as e:
            flash(str(e), "danger")
    return render_template("reset_password.html", token=token)

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
@login_required
def listar_recursos():
    lista = servicios.listar_recursos(request.args.get("tipo"))
    return jsonify(_serializar(lista))


@app.post("/api/recursos")
@admin_required
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
@login_required
def disponibilidad(id_recurso):
    libres = servicios.consultar_disponibilidad(id_recurso, _fecha_param())
    return jsonify([{"inicio": a.isoformat(), "fin": b.isoformat()} for a, b in libres])


@app.post("/api/reservas")
@login_required
def reservar():
    d = _json_requerido("id_recurso", "fecha_inicio", "fecha_fin")
    d["id_usuario"] = _usuario_actual()["correo"]
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
@login_required
def reservas_del_dia():
    lista = servicios.reservas_del_dia(_fecha_param(), request.args.get("id_recurso"))
    return jsonify(_serializar(lista))


@app.delete("/api/reservas/<id_reserva>")
@login_required
def cancelar(id_reserva):
    reserva = reservas.obtener(id_reserva)
    actual = _usuario_actual()
    if actual["rol"] != "administrador" and reserva.get("id_usuario") != actual["correo"]:
        return jsonify(error="Permisos insuficientes"), 403
    if servicios.cancelar_reserva(id_reserva):
        return jsonify(estado="cancelada")
    return jsonify(error="Reserva no encontrada o ya cancelada"), 404


@app.post("/api/sincronizar")
@admin_required
def sincronizar():
    confirmadas, rechazadas = servicios.sincronizar_pendientes()
    return jsonify(confirmadas=confirmadas, rechazadas=rechazadas)


# =====================================================================
# VISTAS WEB (developer)
# =====================================================================

# --- MAIN VIEWS ---
@app.route('/')
def home():
    return render_template('home.html', total_espacios=len(recursos.listar()))


# --- Utilidades para el dashboard ---
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _a_datetime(texto):
    """Convierte 'YYYY-MM-DDTHH:MM...' a datetime; None si no se puede."""
    try:
        return datetime.fromisoformat(str(texto)[:16])
    except ValueError:
        return None


def _ocupados_ahora():
    """IDs (str) de los recursos con una reserva activa en este momento."""
    ahora = datetime.now()
    ocupados = set()
    for b in reservas.listar():
        if b.get("estado") != "activa":
            continue
        ini, fin = _a_datetime(b.get("fecha_inicio")), _a_datetime(b.get("fecha_fin"))
        if ini and fin and ini <= ahora < fin:
            ocupados.add(str(b.get("id_recurso")))
    return ocupados


@app.route('/dashboard')
@login_required
def dashboard():
    ahora = datetime.now()
    mis_reservas = reservas.listar(id_usuario=_usuario_actual()["correo"])

    activas, horas_mes = 0, 0.0
    for b in mis_reservas:
        if b.get("estado") != "activa":
            continue
        ini, fin = _a_datetime(b.get("fecha_inicio")), _a_datetime(b.get("fecha_fin"))
        if not ini or not fin:
            continue
        if fin >= ahora:                                   # próximas y en curso
            activas += 1
        if ini.year == ahora.year and ini.month == ahora.month:
            horas_mes += (fin - ini).total_seconds() / 3600

    todos = recursos.listar()
    ocupados = _ocupados_ahora()
    libres = [r for r in todos if str(r["_id"]) not in ocupados]

    return render_template(
        'dashboard.html',
        resources=libres[:4],
        stats={"activas": activas, "horas_mes": round(horas_mes, 1)},
        disponibles_total=len(libres),
        total_espacios=len(todos),
        hoy_texto=f"{DIAS[ahora.weekday()].capitalize()}, {ahora.day} de {MESES[ahora.month - 1]}",
        reservas_activas=activas,   # el contador rojo del sidebar
        usuario=_usuario_actual(),
    )


@app.route('/spaces')
@login_required
def spaces():
    tipo = request.args.get('tipo')  # filtro opcional: /spaces?tipo=laboratorio
    return render_template('spaces.html', resources=recursos.listar(tipo))


# --- CRUD RESOURCES ---
@app.route('/resources/new', methods=['GET', 'POST'])
@admin_required
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
@admin_required
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
@admin_required
def delete_resource(id):
    try:
        recursos.eliminar(id)
        flash('Recurso eliminado', 'info')
    except (NoEncontrado, ErrorValidacion) as e:
        flash(str(e), 'danger')
    return redirect(url_for('spaces'))


# --- BOOKINGS ---
@app.route('/bookings/new/<id_recurso>', methods=['POST'])
@login_required
def create_booking(id_recurso):
    try:
        reservas.crear(
            id_recurso, _usuario_actual()["correo"],
            request.form['fecha_inicio'], request.form['fecha_fin']
        )
        flash('Reserva creada exitosamente', 'success')
    except (NoEncontrado, ErrorValidacion) as e:
        flash(str(e), 'danger')
    return redirect(url_for('my_bookings'))


@app.route('/my-bookings')
@login_required
def my_bookings():
    return render_template('bookings.html', bookings=reservas.listar(id_usuario=_usuario_actual()["correo"]))


@app.route('/bookings/edit/<id>', methods=['POST'])
@login_required
def edit_booking(id):
    try:
        reserva = reservas.obtener(id)
        if reserva.get("id_usuario") != _usuario_actual()["correo"]:
            raise ErrorValidacion("No puedes modificar una reserva de otro usuario")
        reservas.actualizar(id, request.form['fecha_inicio'], request.form['fecha_fin'])
        flash('Reserva actualizada', 'success')
    except (NoEncontrado, ErrorValidacion) as e:
        flash(str(e), 'danger')
    return redirect(url_for('my_bookings'))


@app.route('/bookings/cancel/<id>', methods=['POST'])
@login_required
def cancel_booking(id):
    try:
        reserva = reservas.obtener(id)
        if (reserva.get("id_usuario") != _usuario_actual()["correo"] and
                _usuario_actual().get("rol") != "administrador"):
            raise ErrorValidacion("No puedes cancelar una reserva de otro usuario")
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
    for b in reservas.listar():
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
@admin_required
def users():
    return render_template('user.html', users=usuarios.listar())


@app.route('/users/new', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        try:
            if not request.form.get('password'):
                raise ErrorValidacion('La contraseña es obligatoria al crear un usuario')
            usuarios.crear({
                "nombre": request.form['nombre'],
                "correo": request.form['correo'],
                "rol": request.form['rol'],
                "password": request.form.get('password'),
            })
            flash('Usuario creado exitosamente', 'success')
            return redirect(url_for('users'))
        except ErrorValidacion as e:
            flash(str(e), 'danger')
    return render_template('user_form.html', user=None)


@app.route('/users/edit/<id>', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    try:
        user = usuarios.obtener(id)
    except (NoEncontrado, ErrorValidacion) as e:
        flash(str(e), 'danger')
        return redirect(url_for('users'))

    if request.method == 'POST':
        try:
            cambios = {
                "nombre": request.form['nombre'],
                "rol": request.form['rol'],
            }
            if request.form.get('password'):
                cambios["password"] = request.form['password']
            usuarios.actualizar(id, cambios)
            flash('Usuario actualizado', 'success')
            return redirect(url_for('users'))
        except (NoEncontrado, ErrorValidacion) as e:
            flash(str(e), 'danger')
    return render_template('user_form.html', user=user)


@app.route('/users/delete/<id>', methods=['POST'])
@admin_required
def delete_user(id):
    try:
        usuarios.eliminar(id)
        flash('Usuario eliminado', 'info')
    except (NoEncontrado, ErrorValidacion) as e:
        flash(str(e), 'danger')
    return redirect(url_for('users'))


@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', usuario=_usuario_actual())


@app.route('/settings/password', methods=['POST'])
@login_required
def change_password():
    try:
        if request.form.get('password') != request.form.get('password_confirm'):
            raise ErrorValidacion("Las contraseñas no coinciden")
        usuarios.cambiar_password(_usuario_actual()["_id"], request.form.get("password"))
        flash("Contraseña actualizada", "success")
    except (ErrorValidacion, NoEncontrado) as e:
        flash(str(e), "danger")
    return redirect(url_for("settings"))


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    flash('Has cerrado sesión', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    print("Iniciando servidor web de UNAreserva...")
    app.run(debug=True, use_reloader=True)    # Pasar a True para debuguear.
