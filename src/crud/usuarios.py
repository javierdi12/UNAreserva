"""CRUD de la coleccion `usuarios`."""
import re
import hashlib
import secrets
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash, generate_password_hash

from src.core import cache
from src.core.errores import ErrorValidacion, NoEncontrado
from src.core.utils import oid, serializar
from src.database import get_mongo_db

ROLES_VALIDOS = {"estudiante", "administrador"}
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
PASSWORD_MIN_LENGTH = 8


def _col():
    return get_mongo_db()["usuarios"]


def _tokens_col():
    return get_mongo_db()["password_reset_tokens"]


def _usuario_publico(usuario):
    """Devuelve un usuario sin campos internos de autenticación."""
    if not usuario:
        return usuario
    usuario = dict(usuario)
    usuario.pop("password_hash", None)
    return serializar(usuario)


def _validar_password(password):
    if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
        raise ErrorValidacion(
            f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres"
        )


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
    if "password" in data and data["password"]:
        _validar_password(data["password"])


def crear(data):
    """CREATE administrativo. data: nombre, correo, rol y password opcional."""
    _validar(data)
    correo = data["correo"].strip().lower()
    if _col().find_one({"correo": correo}):
        raise ErrorValidacion("Ya existe un usuario con ese correo")

    ahora = datetime.now()
    documento = {
        "nombre": data["nombre"].strip(),
        "correo": correo,
        "rol": data["rol"],
        "activo": True,
        "fecha_creacion": ahora.isoformat(),
        "fecha_actualizacion": ahora.isoformat(),
    }
    if data.get("password"):
        documento["password_hash"] = generate_password_hash(data["password"])
    res = _col().insert_one(documento)
    cache.invalidar("usuarios:*")
    return str(res.inserted_id)


def crear_estudiante(data):
    """Registra un estudiante sin permitir que el cliente elija el rol."""
    nombre = (data.get("nombre") or "").strip()
    correo = (data.get("correo") or "").strip().lower()
    password = data.get("password")
    _validar({"nombre": nombre, "correo": correo, "rol": "estudiante", "password": password})
    _validar_password(password)
    if _col().find_one({"correo": correo}):
        raise ErrorValidacion("Ya existe un usuario con ese correo")

    ahora = datetime.now()
    res = _col().insert_one({
        "nombre": nombre,
        "correo": correo,
        "rol": "estudiante",
        "password_hash": generate_password_hash(password),
        "activo": True,
        "fecha_creacion": ahora.isoformat(),
        "fecha_actualizacion": ahora.isoformat(),
    })
    cache.invalidar("usuarios:*")
    return str(res.inserted_id)


def autenticar(correo, password):
    """Retorna el usuario público si las credenciales son válidas."""
    correo = (correo or "").strip().lower()
    usuario = _col().find_one({"correo": correo, "activo": {"$ne": False}})
    if not usuario or not usuario.get("password_hash"):
        return None
    if not check_password_hash(usuario["password_hash"], password or ""):
        return None
    return _usuario_publico(usuario)


def cambiar_password(id_usuario, password):
    _validar_password(password)
    res = _col().update_one(
        {"_id": oid(id_usuario)},
        {"$set": {
            "password_hash": generate_password_hash(password),
            "fecha_actualizacion": datetime.now().isoformat(),
        }},
    )
    if res.matched_count == 0:
        raise NoEncontrado("Usuario no encontrado")
    _tokens_col().delete_many({"usuario_id": oid(id_usuario)})
    cache.invalidar("usuarios:*")
    return True


def crear_token_recuperacion(correo, minutos=60):
    """Crea un token de recuperación y retorna (token_plano, usuario)."""
    correo = (correo or "").strip().lower()
    usuario = _col().find_one({"correo": correo, "activo": {"$ne": False}})
    if not usuario:
        return None
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    ahora = datetime.now()
    _tokens_col().delete_many({"usuario_id": usuario["_id"]})
    _tokens_col().insert_one({
        "token_hash": token_hash,
        "usuario_id": usuario["_id"],
        "correo": correo,
        "creado_en": ahora,
        "expira_en": ahora + timedelta(minutes=minutos),
        "usado": False,
    })
    return token, _usuario_publico(usuario)


def restablecer_password(token, password):
    _validar_password(password)
    token_hash = hashlib.sha256((token or "").encode("utf-8")).hexdigest()
    documento = _tokens_col().find_one({"token_hash": token_hash, "usado": False})
    if not documento or documento.get("expira_en", datetime.min) < datetime.now():
        raise ErrorValidacion("El enlace de recuperación no es válido o ya expiró")
    cambiar_password(str(documento["usuario_id"]), password)
    _tokens_col().update_one({"_id": documento["_id"]}, {"$set": {"usado": True}})
    return True


def listar(rol=None):
    """READ (lista) con cache."""
    k = cache.key("usuarios", "lista", rol or "todos")
    cached = cache.get(k)
    if cached is not None:
        return cached

    filtro = {"rol": rol} if rol else {}
    lista = [_usuario_publico(u) for u in _col().find(filtro).sort("nombre", 1)]
    cache.set(k, lista)
    return lista


def obtener(id_usuario):
    """READ (uno)."""
    doc = _col().find_one({"_id": oid(id_usuario)})
    if not doc:
        raise NoEncontrado("Usuario no encontrado")
    return _usuario_publico(doc)


def actualizar(id_usuario, data):
    """UPDATE parcial. El correo no se modifica porque las reservas lo usan como id_usuario."""
    permitidos = {"nombre", "rol", "password", "activo"}
    cambios = {k: v for k, v in data.items() if k in permitidos}
    if not cambios:
        raise ErrorValidacion("No hay campos para actualizar")
    _validar(cambios, parcial=True)
    if "nombre" in cambios:
        cambios["nombre"] = cambios["nombre"].strip()
    if "password" in cambios:
        cambios["password_hash"] = generate_password_hash(cambios.pop("password"))
    cambios["fecha_actualizacion"] = datetime.now().isoformat()

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
