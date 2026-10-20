"""CRUD de la coleccion `usuarios`."""
import re
from datetime import datetime

from src.core import cache
from src.core.errores import ErrorValidacion, NoEncontrado
from src.core.utils import oid, serializar
from src.database import get_mongo_db

ROLES_VALIDOS = {"estudiante", "administrador"}
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


def _col():
    return get_mongo_db()["usuarios"]


def _validar(data, parcial=False):
    if not parcial:
        faltan = [c for c in ("nombre", "correo", "rol") if not data.get(c)]
        if faltan:
            raise ErrorValidacion(f"Faltan campos: {', '.join(faltan)}")
    if "nombre" in data and not data["nombre"].strip():
        raise ErrorValidacion("El nombre no puede estar vacio")
    if "correo" in data and not EMAIL_RE.match(data["correo"].strip()):
        raise ErrorValidacion("El correo no es valido")
    if "rol" in data and data["rol"] not in ROLES_VALIDOS:
        raise ErrorValidacion(f"Rol invalido. Opciones: {', '.join(sorted(ROLES_VALIDOS))}")


def crear(data):
    """CREATE. data: nombre, correo, rol."""
    _validar(data)
    correo = data["correo"].strip().lower()
    if _col().find_one({"correo": correo}):
        raise ErrorValidacion("Ya existe un usuario con ese correo")

    res = _col().insert_one({
        "nombre": data["nombre"].strip(),
        "correo": correo,
        "rol": data["rol"],
        "fecha_creacion": datetime.now().isoformat(),
    })
    cache.invalidar("usuarios:*")
    return str(res.inserted_id)


def listar(rol=None):
    """READ (lista) con cache."""
    k = cache.key("usuarios", "lista", rol or "todos")
    cached = cache.get(k)
    if cached is not None:
        return cached

    filtro = {"rol": rol} if rol else {}
    lista = [serializar(u) for u in _col().find(filtro).sort("nombre", 1)]
    cache.set(k, lista)
    return lista


def obtener(id_usuario):
    """READ (uno)."""
    doc = _col().find_one({"_id": oid(id_usuario)})
    if not doc:
        raise NoEncontrado("Usuario no encontrado")
    return serializar(doc)


def actualizar(id_usuario, data):
    """UPDATE parcial. El correo no se modifica porque las reservas lo usan como id_usuario."""
    permitidos = {"nombre", "rol"}
    cambios = {k: v for k, v in data.items() if k in permitidos}
    if not cambios:
        raise ErrorValidacion("No hay campos para actualizar")
    _validar(cambios, parcial=True)
    if "nombre" in cambios:
        cambios["nombre"] = cambios["nombre"].strip()

    res = _col().update_one({"_id": oid(id_usuario)}, {"$set": cambios})
    if res.matched_count == 0:
        raise NoEncontrado("Usuario no encontrado")
    cache.invalidar("usuarios:*")
    return True


def eliminar(id_usuario):
    """DELETE. No permite borrar si tiene reservas activas futuras."""
    usuario = obtener(id_usuario)
    pendientes = get_mongo_db()["reservas"].count_documents({
        "id_usuario": usuario["correo"],
        "estado": "activa",
        "fecha_fin": {"$gt": datetime.now().isoformat()},
    })
    if pendientes:
        raise ErrorValidacion(f"No se puede eliminar: tiene {pendientes} reserva(s) activa(s)")

    _col().delete_one({"_id": oid(id_usuario)})
    cache.invalidar("usuarios:*")
    return True