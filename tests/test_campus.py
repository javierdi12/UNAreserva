import pytest
from pymongo.errors import DuplicateKeyError

from src import app as app_module
from src.core.errores import ErrorValidacion
from src.crud import campus


class ColeccionCampus:
    def __init__(self):
        self.docs = {}

    def insert_one(self, doc):
        if doc["_id"] in self.docs:
            raise DuplicateKeyError("duplicado")
        self.docs[doc["_id"]] = doc

    def find_one(self, filtro):
        return self.docs.get(filtro["_id"])

    def find(self, filtro, proyeccion):
        class Cursor(list):
            def sort(self, campo, orden):
                return sorted(self, key=lambda d: d[campo])
        return Cursor({"id": d["id"], "nombre": d["nombre"]} for d in self.docs.values())


@pytest.fixture
def entorno(monkeypatch):
    coleccion = ColeccionCampus()
    monkeypatch.setattr(campus, "get_mongo_db", lambda: {"campus": coleccion})
    monkeypatch.setattr(app_module.tipos_recurso, "listar", lambda campus_id=None: [])
    monkeypatch.setattr(app_module.reservas, "listar", lambda **kwargs: [])
    app_module.app.config.update(TESTING=True, SECRET_KEY="test-secret")
    return app_module.app.test_client(), coleccion


def test_creacion_valida_y_detecta_duplicados(entorno):
    _, coleccion = entorno
    assert campus.crear(" Campus Libería ") == "campus_liberia"
    assert campus.es_valido("campus_liberia")
    assert campus.listar()[-1]["nombre"] == "Campus Libería"
    with pytest.raises(ErrorValidacion):
        campus.crear("campus liberia")
    with pytest.raises(ErrorValidacion):
        campus.crear("Campus Omar Dengo")
    with pytest.raises(ErrorValidacion):
        campus.crear("   ")
    assert len(coleccion.docs) == 1


def test_administrador_crea_y_selecciona_campus(entorno):
    client, _ = entorno
    with client.session_transaction() as sesion:
        sesion["usuario"] = {"nombre": "Admin", "correo": "a@example.com", "rol": "administrador"}
    respuesta = client.post("/campus", data={"nombre": "Campus Liberia"}, follow_redirects=True)
    assert respuesta.status_code == 200
    assert 'value="campus_liberia" selected' in respuesta.get_data(as_text=True)
    with client.session_transaction() as sesion:
        assert sesion["campus_id"] == "campus_liberia"


def test_estudiante_no_puede_crear_campus(entorno):
    client, coleccion = entorno
    with client.session_transaction() as sesion:
        sesion["usuario"] = {"nombre": "Ana", "correo": "a@example.com", "rol": "estudiante"}
    respuesta = client.post("/campus", data={"nombre": "Campus Liberia"})
    assert respuesta.status_code == 302
    assert not coleccion.docs


def test_visitante_no_puede_crear_campus(entorno):
    client, coleccion = entorno
    assert client.post("/campus", data={"nombre": "Campus Liberia"}).status_code == 302
    assert not coleccion.docs
