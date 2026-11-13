import pytest
from datetime import datetime

from src import app as app_module


@pytest.fixture
def client(monkeypatch):
    app_module.app.config.update(TESTING=True, SECRET_KEY="test")
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session["usuario"] = {"correo": "admin@example.com", "rol": "administrador"}
    return client


def test_crear_recurso_valida_campos_requeridos(client):
    respuesta = client.post("/api/recursos", json={"nombre": "Sala"})

    assert respuesta.status_code == 400
    assert "Faltan campos" in respuesta.get_json()["error"]


def test_listar_recursos_aplica_filtro(client, monkeypatch):
    capturado = {}

    def listar(tipo=None):
        capturado["tipo"] = tipo
        return [{"_id": "r1", "tipo": tipo}]

    monkeypatch.setattr(app_module.servicios, "listar_recursos", listar)
    respuesta = client.get("/api/recursos?tipo=sala")

    assert respuesta.status_code == 200
    assert capturado["tipo"] == "sala"
    assert respuesta.get_json()[0]["_id"] == "r1"


def test_consultar_disponibilidad_devuelve_franjas_y_duracion(client, monkeypatch):
    monkeypatch.setattr(
        app_module.servicios,
        "consultar_disponibilidad",
        lambda _id, _fecha: [(datetime(2099, 1, 1, 8), datetime(2099, 1, 1, 9))],
    )

    respuesta = client.get("/api/disponibilidad/r1?fecha=2099-01-01")

    assert respuesta.status_code == 200
    assert respuesta.get_json() == [{
        "inicio": "2099-01-01T08:00:00",
        "fin": "2099-01-01T09:00:00",
    }]
    assert float(respuesta.headers["X-Availability-Duration-Ms"]) >= 0


def test_sincronizar_pendientes_expone_resumen(client, monkeypatch):
    monkeypatch.setattr(
        app_module.servicios,
        "sincronizar_pendientes",
        lambda detallado=False: {
            "aceptadas": 1,
            "rechazadas": 0,
            "conflictos": 1,
            "pendientes": 0,
            "duracion_ms": 2.5,
        },
    )

    respuesta = client.post("/api/sincronizar")

    assert respuesta.status_code == 200
    assert respuesta.get_json()["conflictos"] == 1
    assert respuesta.get_json()["duracion_ms"] == 2.5
