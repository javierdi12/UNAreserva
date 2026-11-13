from datetime import datetime
from types import SimpleNamespace

from src import app as app_module, servicios
from src.crud import reservas


def test_lista_normaliza_fechas_de_mongo_y_permite_mostrar_reservas(monkeypatch):
    reserva = {
        "_id": "reserva-1", "id_recurso": "recurso-1",
        "id_usuario": "ana@example.com", "estado": "activa",
        "fecha_inicio": datetime(2099, 1, 1, 10),
        "fecha_fin": datetime(2099, 1, 1, 11),
    }

    class Cursor:
        def sort(self, *args):
            return self

        def limit(self, *args):
            return [reserva.copy()]

    monkeypatch.setattr(reservas, "_col", lambda: SimpleNamespace(find=lambda filtro: Cursor()))
    monkeypatch.setattr(reservas.cache, "get", lambda key: None)
    monkeypatch.setattr(reservas.cache, "set", lambda key, value: None)
    monkeypatch.setattr(reservas.recursos, "listar", lambda **kwargs: [{"_id": "recurso-1"}])
    monkeypatch.setattr(reservas.recursos, "obtener", lambda *args, **kwargs: {"nombre": "Sala"})
    monkeypatch.setattr(app_module.tipos_recurso, "listar", lambda **kwargs: [])
    monkeypatch.setattr(app_module.campus, "listar", lambda: [dict(c) for c in app_module.campus.CAMPUS])
    app_module.app.config.update(TESTING=True, SECRET_KEY="test")
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session["usuario"] = {"nombre": "Ana", "correo": "ana@example.com", "rol": "estudiante"}

    respuesta = client.get("/my-bookings")

    assert respuesta.status_code == 200
    assert "Sala" in respuesta.get_data(as_text=True)
    assert "2099-01-01" in respuesta.get_data(as_text=True)


def test_lista_normaliza_fechas_guardadas_en_cache(monkeypatch):
    monkeypatch.setattr(reservas.cache, "get", lambda key: [{
        "fecha_inicio": "2099-01-01 10:00:00", "fecha_fin": "2099-01-01 11:00:00"
    }])
    assert reservas.listar()[0]["fecha_fin"] == "2099-01-01T11:00:00"


def test_reserva_confirmada_invalida_cache(monkeypatch):
    invalidados = []
    redis = SimpleNamespace(set=lambda *args, **kwargs: True, get=lambda key: None)
    coleccion = SimpleNamespace(insert_one=lambda doc: SimpleNamespace(inserted_id="reserva-1"),
                                 find_one=lambda filtro: None)
    monkeypatch.setattr(servicios, "get_db", lambda: SimpleNamespace(reservas=coleccion))
    monkeypatch.setattr(servicios, "get_redis", lambda: redis)
    monkeypatch.setattr(servicios, "_obtener_recurso", lambda *args: {})
    monkeypatch.setattr(servicios, "_validar_horario", lambda *args: None)
    monkeypatch.setattr(servicios.cache, "invalidar", lambda patron: invalidados.append(patron))

    servicios._intentar_reserva("r1", "ana@example.com", datetime(2099, 1, 1, 10), datetime(2099, 1, 1, 11))

    assert invalidados == ["reservas:*"]
