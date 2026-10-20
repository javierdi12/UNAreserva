import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
from datetime import datetime, timedelta
from src.database import get_mongo_db

def generate_test_data():
    db = get_mongo_db()
    resources_collection = db["recursos"]
    bookings_collection = db["reservas"]

    print("Limpiando colecciones anteriores...")
    resources_collection.delete_many({})
    bookings_collection.delete_many({})

    print("Generando 50 recursos...")
    types = ["sala_estudio", "laboratorio", "cancha"]
    resource_ids = []
    
    for i in range(50):
        resource = {
            "nombre": f"Recurso {i+1}",
            "tipo": random.choice(types),
            "capacidad": random.randint(2, 30),
            "ubicacion": f"Edificio {random.choice(['A', 'B', 'C'])}, piso {random.randint(1, 3)}",
            "horario": {"apertura": "07:00", "cierre": "21:00"}
        }
        result = resources_collection.insert_one(resource)
        resource_ids.append(str(result.inserted_id))

    print("Generando 100 reservas...")
    for i in range(100):
        resource_id = random.choice(resource_ids)
        start_date = datetime.now() + timedelta(days=random.randint(1, 30), hours=random.randint(7, 20))
        end_date = start_date + timedelta(hours=random.randint(1, 3))
        
        booking = {
            "id_recurso": resource_id,
            "id_usuario": f"estudiante_{random.randint(1, 100)}@una.ac.cr",
            "fecha_inicio": start_date.isoformat(),
            "fecha_fin": end_date.isoformat(),
            "estado": "activa"
        }
        bookings_collection.insert_one(booking)

    print("[OK] Datos generados: 50 recursos y 100 reservas.")

if __name__ == "__main__":
    generate_test_data()