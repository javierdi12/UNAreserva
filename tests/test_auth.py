import pytest

from src import app as app_module


@pytest.fixture
def client(monkeypatch):
    app_module.app.config.update(TESTING=True, SECRET_KEY="test-secret")
    return app_module.app.test_client()


def test_login_guarda_usuario_en_sesion(client, monkeypatch):
    usuario = {"_id": "u1", "nombre": "Ana", "correo": "ana@example.com", "rol": "estudiante"}
    monkeypatch.setattr(app_module.usuarios, "autenticar", lambda correo, password: usuario)

    respuesta = client.post("/login", data={"correo": "ana@example.com", "password": "correcta"})

    assert respuesta.status_code == 302
    with client.session_transaction() as sesion:
        assert sesion["usuario"]["correo"] == "ana@example.com"


def test_login_rechaza_credenciales_invalidas(client, monkeypatch):
    monkeypatch.setattr(app_module.usuarios, "autenticar", lambda correo, password: None)

    respuesta = client.post("/login", data={"correo": "ana@example.com", "password": "incorrecta"})

    assert respuesta.status_code == 200
    assert "incorrectos" in respuesta.get_data(as_text=True)


def test_registro_publico_crea_estudiante(client, monkeypatch):
    datos = {}
    def crear_estudiante(data):
        datos.update(data)

    monkeypatch.setattr(app_module.usuarios, "crear_estudiante", crear_estudiante)
    respuesta = client.post("/register", data={
        "nombre": "Ana", "correo": "ana@example.com", "password": "secreto123"
    })

    assert respuesta.status_code == 302
    assert datos["password"] == "secreto123"
    assert "rol" not in datos


def test_api_requiere_sesion(client):
    respuesta = client.get("/api/recursos")
    assert respuesta.status_code == 401
    assert respuesta.get_json()["error"]


def test_estudiante_no_accede_a_administracion(client):
    with client.session_transaction() as sesion:
        sesion["usuario"] = {"_id": "u1", "nombre": "Ana", "correo": "ana@example.com", "rol": "estudiante"}

    respuesta = client.get("/users")

    assert respuesta.status_code == 302
    assert respuesta.location.endswith("/dashboard")


def test_api_reserva_usa_usuario_de_sesion(client, monkeypatch):
    with client.session_transaction() as sesion:
        sesion["usuario"] = {"_id": "u1", "nombre": "Ana", "correo": "ana@example.com", "rol": "estudiante"}
    capturado = {}

    def reservar(*args):
        capturado["id_usuario"] = args[1]
        return {"estado": "confirmada", "id": "r1"}

    monkeypatch.setattr(app_module.servicios, "reservar", reservar)
    respuesta = client.post("/api/reservas", json={
        "id_recurso": "recurso-1",
        "id_usuario": "atacante@example.com",
        "fecha_inicio": "2099-01-01T10:00",
        "fecha_fin": "2099-01-01T11:00",
    })

    assert respuesta.status_code == 201
    assert capturado["id_usuario"] == "ana@example.com"


def test_logout_limpia_sesion(client):
    with client.session_transaction() as sesion:
        sesion["usuario"] = {"correo": "ana@example.com"}

    respuesta = client.get("/logout")

    assert respuesta.status_code == 302
    with client.session_transaction() as sesion:
        assert "usuario" not in sesion
