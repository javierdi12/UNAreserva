import pytest

from src import app as app_module
from src.servicios import ConflictoReserva, RecursoOcupado


@pytest.fixture
def client():
    app_module.app.config.update(TESTING=True, SECRET_KEY="test")
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session["usuario"] = {
            "_id": "u1", "correo": "ana@example.com", "rol": "estudiante"
        }
    return client


def test_reserva_en_horario_ocupado_responde_409(client, monkeypatch):
    def conflicto(*args):
        raise ConflictoReserva("Ya existe una reserva en ese horario")

    monkeypatch.setattr(app_module.servicios, "reservar", conflicto)
    respuesta = client.post("/api/reservas", json={
        "id_recurso": "r1",
        "fecha_inicio": "2099-01-01T10:00",
        "fecha_fin": "2099-01-01T11:00",
    })
    assert respuesta.status_code == 409
    assert "horario" in respuesta.get_json()["error"]


def test_lock_activo_responde_423_y_no_inserta(client, monkeypatch):
    llamadas = []

    def ocupado(*args):
        llamadas.append(args)
        raise RecursoOcupado("Otro usuario esta reservando este recurso")

    monkeypatch.setattr(app_module.servicios, "reservar", ocupado)
    respuesta = client.post("/api/reservas", json={
        "id_recurso": "r1",
        "fecha_inicio": "2099-01-01T10:00",
        "fecha_fin": "2099-01-01T11:00",
    })
    assert respuesta.status_code == 423
    assert len(llamadas) == 1
