import pytest

from src import app as app_module


@pytest.fixture
def client():
    app_module.app.config.update(TESTING=True, SECRET_KEY="test")
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session["usuario"] = {"correo": "ana@example.com", "rol": "estudiante"}
    return client


def test_crear_reserva_usa_usuario_de_sesion(client, monkeypatch):
    capturado = {}

    def reservar(*args):
        capturado["usuario"] = args[1]
        return {"estado": "confirmada", "id": "res-1"}

    monkeypatch.setattr(app_module.servicios, "reservar", reservar)
    respuesta = client.post("/api/reservas", json={
        "id_recurso": "r1",
        "id_usuario": "atacante@example.com",
        "fecha_inicio": "2099-01-01T10:00",
        "fecha_fin": "2099-01-01T11:00",
    })

    assert respuesta.status_code == 201
    assert capturado["usuario"] == "ana@example.com"


def test_cancelar_reserva_rechaza_reserva_de_otro_usuario(client, monkeypatch):
    monkeypatch.setattr(app_module.reservas, "obtener", lambda _id: {
        "id_usuario": "otro@example.com", "estado": "activa"
    })

    respuesta = client.delete("/api/reservas/res-1")

    assert respuesta.status_code == 403
    assert respuesta.get_json()["error"] == "Permisos insuficientes"
