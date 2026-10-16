"""
Modelos de datos para UNAreserva.
Define las entidades principales: Recurso y Reserva.
"""
from datetime import datetime
class Recurso:
    """Representa un espacio o recurso reservable."""
    def __init__(self, nombre, tipo, capacidad, ubicacion,
                 horario_apertura="07:00", horario_cierre="21:00"):
        self.nombre = nombre
        self.tipo = tipo
        self.capacidad = capacidad
        self.ubicacion = ubicacion
        self.horario_apertura = horario_apertura
        self.horario_cierre = horario_cierre
    def to_dict(self):
        return {
            "nombre": self.nombre,
            "tipo": self.tipo,
            "capacidad": self.capacidad,
            "ubicacion": self.ubicacion,
            "horario": {
                "apertura": self.horario_apertura,
                "cierre": self.horario_cierre
            }
        }
    @staticmethod
    def from_dict(data):
        return Recurso(
            nombre=data.get("nombre"),
            tipo=data.get("tipo"),
            capacidad=data.get("capacidad"),
            ubicacion=data.get("ubicacion"),
            horario_apertura=data.get("horario", {}).get("apertura", "07:00"),
            horario_cierre=data.get("horario", {}).get("cierre", "21:00")
        )
    def __repr__(self):
        return f"<Recurso {self.nombre} ({self.tipo})>"
class Reserva:
    """Representa una reserva de un recurso por un usuario."""
    def __init__(self, id_recurso, id_usuario, fecha_inicio, fecha_fin, estado="activa"):
        self.id_recurso = id_recurso
        self.id_usuario = id_usuario
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.estado = estado
        self.fecha_creacion = datetime.now()
    def to_dict(self):
        return {
            "id_recurso": self.id_recurso,
            "id_usuario": self.id_usuario,
            "fecha_inicio": self.fecha_inicio,
            "fecha_fin": self.fecha_fin,
            "estado": self.estado,
            "fecha_creacion": self.fecha_creacion
        }
    @staticmethod
    def from_dict(data):
        return Reserva(
            id_recurso=data.get("id_recurso"),
            id_usuario=data.get("id_usuario"),
            fecha_inicio=data.get("fecha_inicio"),
            fecha_fin=data.get("fecha_fin"),
            estado=data.get("estado", "activa")
        )
    def __repr__(self):
        return f"<Reserva {self.id_recurso} por {self.id_usuario}>"
