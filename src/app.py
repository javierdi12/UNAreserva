import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from src.config import Config
from src.crud import recursos, reservas, usuarios
from src.core.errores import ErrorValidacion, NoEncontrado

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config.from_object(Config)

USER_EMAIL = "estudiante_1@una.ac.cr"  # TODO: reemplazar por el usuario en sesion


# --- MAIN VIEWS ---
@app.route('/')
def dashboard():
    return render_template(
        'dashboard.html',
        resources=recursos.listar(),
        bookings=reservas.listar(limite=5),
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


# --- CALENDAR API ---
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
    app.run(debug=True)