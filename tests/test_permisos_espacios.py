import pytest

from src import app as app_module


@pytest.mark.parametrize("rol,puede_administrar", [("estudiante", False), ("administrador", True)])
def test_acciones_de_espacios_se_muestran_solo_a_administradores(monkeypatch, rol, puede_administrar):
    monkeypatch.setattr(app_module.campus, "listar", lambda: [dict(c) for c in app_module.campus.CAMPUS])
    monkeypatch.setattr(app_module.tipos_recurso, "listar", lambda **kwargs: [])
    monkeypatch.setattr(app_module.reservas, "listar", lambda **kwargs: [])
    monkeypatch.setattr(app_module.recursos, "listar", lambda *args, **kwargs: [{
        "_id": "r1", "nombre": "Sala", "ubicacion": "Campus", "capacidad": 5, "tipo": "sala"
    }])
    app_module.app.config.update(TESTING=True, SECRET_KEY="test")
    client = app_module.app.test_client()
    with client.session_transaction() as sesion:
        sesion["usuario"] = {"nombre": "Ana", "correo": "ana@example.com", "rol": rol}

    respuesta = client.get("/spaces")
    contenido = respuesta.get_data(as_text=True)

    assert respuesta.status_code == 200
    assert "Reservar espacio" in contenido
    assert ('/resources/edit/r1' in contenido) is puede_administrar
    assert ('/resources/delete/r1' in contenido) is puede_administrar


@pytest.mark.parametrize("metodo,ruta", [("get", "/resources/edit/r1"), ("post", "/resources/delete/r1")])
def test_cliente_no_puede_modificar_espacios_directamente(metodo, ruta):
    app_module.app.config.update(TESTING=True, SECRET_KEY="test")
    client = app_module.app.test_client()
    with client.session_transaction() as sesion:
        sesion["usuario"] = {"nombre": "Ana", "correo": "ana@example.com", "rol": "estudiante"}

    respuesta = getattr(client, metodo)(ruta)

    assert respuesta.status_code == 302
    assert respuesta.location.endswith("/dashboard")
