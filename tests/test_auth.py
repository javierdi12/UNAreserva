import pytest
from types import SimpleNamespace

from src import app as app_module
from src.resend_mail import ResendError, enviar_recuperacion


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


def test_dashboard_acepta_fechas_iso_en_reservas(client, monkeypatch):
    usuario = {
        "_id": "u1", "nombre": "Ana", "correo": "ana@example.com",
        "rol": "administrador",
    }
    with client.session_transaction() as sesion:
        sesion["usuario"] = usuario

    monkeypatch.setattr(app_module.reservas, "listar", lambda **kwargs: [{
        "id_recurso": "r1",
        "id_usuario": "ana@example.com",
        "fecha_inicio": "2099-01-01T10:00:00",
        "fecha_fin": "2099-01-01T11:00:00",
        "estado": "activa",
    }])
    monkeypatch.setattr(app_module.recursos, "listar", lambda tipo=None, campus_id=None: [])
    monkeypatch.setattr(app_module.tipos_recurso, "listar", lambda campus_id=None: [])

    respuesta = client.get("/dashboard")

    assert respuesta.status_code == 200
    assert "{'id_recurso':" not in respuesta.get_data(as_text=True)


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


def test_calendario_es_publico(client):
    respuesta = client.get("/calendar")
    assert respuesta.status_code == 200
    assert "Consultá la disponibilidad" in respuesta.get_data(as_text=True)


def test_sidebar_no_muestra_logout_sin_sesion(client):
    respuesta = client.get("/calendar")
    contenido = respuesta.get_data(as_text=True)
    assert "Cerrar sesión" not in contenido


def test_resend_envia_correo_con_enlace(monkeypatch):
    import json
    capturado = {}

    class Respuesta:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        capturado["request"] = request
        capturado["timeout"] = timeout
        return Respuesta()

    monkeypatch.setattr("src.resend_mail.urlopen", fake_urlopen)
    config = SimpleNamespace(RESEND_API_KEY="token", RESEND_FROM_EMAIL="app@example.com", RESEND_TIMEOUT=10)
    assert enviar_recuperacion(config, "ana@example.com", "Ana <script>", "https://app/reset?a=1&b=2")
    request = capturado["request"]
    payload = json.loads(request.data)
    assert request.full_url == "https://api.resend.com/emails"
    assert request.get_header("Authorization") == "Bearer token"
    assert request.method == "POST"
    assert payload["from"] == "app@example.com"
    assert payload["to"] == ["ana@example.com"]
    assert "Ana &lt;script&gt;" in payload["html"]
    assert "https://app/reset?a=1&amp;b=2" in payload["html"]
    assert capturado["timeout"] == 10


def test_resend_requiere_configuracion():
    config = SimpleNamespace(RESEND_API_KEY="", RESEND_FROM_EMAIL="", RESEND_TIMEOUT=10)
    with pytest.raises(ResendError):
        enviar_recuperacion(config, "ana@example.com", "Ana", "https://app/reset")


def test_recuperacion_oculta_error_de_envio(client, monkeypatch):
    monkeypatch.setattr(app_module.usuarios, "crear_token_recuperacion", lambda correo: (
        "token", {"correo": correo, "nombre": "Ana"}
    ))
    def fallar(*args):
        raise ResendError("Error de envío")
    monkeypatch.setattr(app_module, "enviar_recuperacion", fallar)
    respuesta = client.post("/forgot-password", data={"correo": "ana@example.com"})
    assert respuesta.status_code == 302
    with client.session_transaction() as sesion:
        assert any("Si el correo existe" in mensaje for _, mensaje in sesion["_flashes"])
