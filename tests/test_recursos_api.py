import pytest

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
