import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from bson.objectid import ObjectId
from src.database import get_mongo_db
from src.config import Config

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config.from_object(Config)

# --- MAIN VIEWS ---
@app.route('/')
def dashboard():
    db = get_mongo_db()
    resources = list(db["recursos"].find())
    bookings = list(db["reservas"].find().limit(5))
    return render_template('dashboard.html', resources=resources, bookings=bookings)

@app.route('/spaces')
def spaces():
    db = get_mongo_db()
    resources = list(db["recursos"].find())
    return render_template('spaces.html', resources=resources)

# --- BOOKINGS ---
@app.route('/my-bookings')
def my_bookings():
    db = get_mongo_db()
    user_email = "estudiante_1@una.ac.cr" 
    bookings = list(db["reservas"].find({"id_usuario": user_email}))
    
    for b in bookings:
        resource = db["recursos"].find_one({"_id": ObjectId(b["id_recurso"])})
        b["nombre_recurso"] = resource["nombre"] if resource else "Recurso eliminado"
        
    return render_template('bookings.html', bookings=bookings)

@app.route('/bookings/cancel/<id>')
def cancel_booking(id):
    db = get_mongo_db()
    db["reservas"].update_one({"_id": ObjectId(id)}, {"$set": {"estado": "cancelada"}})
    flash('Reserva cancelada exitosamente', 'info')
    return redirect(url_for('my_bookings'))

# --- CALENDAR API ---
@app.route('/calendar')
def calendar():
    return render_template('calendar.html')

@app.route('/api/bookings')
def api_bookings():
    db = get_mongo_db()
    user_email = "estudiante_1@una.ac.cr"
    bookings = list(db["reservas"].find({"id_usuario": user_email}))
    
    events = []
    for b in bookings:
        resource = db["recursos"].find_one({"_id": ObjectId(b["id_recurso"])})
        resource_name = resource["nombre"] if resource else "Recurso"
        color = "#D32F2F" if b["estado"] == "activa" else "#9e9e9e" 
        
        events.append({
            "id": str(b["_id"]),
            "title": resource_name,
            "start": b["fecha_inicio"], 
            "end": b["fecha_fin"],
            "backgroundColor": color,
            "borderColor": color
        })
    return jsonify(events)

# --- ADMIN VIEWS ---
@app.route('/users')
def users():
    return render_template('users.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/logout')
def logout():
    flash('Has cerrado sesión', 'success')
    return redirect(url_for('dashboard'))

# --- CRUD RESOURCES ---
@app.route('/resources/new', methods=['GET', 'POST'])
def create_resource():
    if request.method == 'POST':
        db = get_mongo_db()
        new_resource = {
            "nombre": request.form['nombre'],
            "tipo": request.form['tipo'],
            "capacidad": int(request.form['capacidad']),
            "ubicacion": request.form['ubicacion'],
            "horario": {"apertura": "07:00", "cierre": "21:00"}
        }
        db["recursos"].insert_one(new_resource)
        flash('Recurso creado exitosamente', 'success')
        return redirect(url_for('dashboard'))
    return render_template('create_resource.html')

@app.route('/resources/delete/<id>')
def delete_resource(id):
    db = get_mongo_db()
    db["recursos"].delete_one({"_id": ObjectId(id)})
    flash('Recurso eliminado', 'info')
    return redirect(url_for('spaces'))

if __name__ == '__main__':
    print("Iniciando servidor web de UNAreserva...")
    app.run(debug=True)