"""CRUD de la coleccion `tipos_recurso` (reemplaza el set TIPOS_VALIDOS quemado)."""
import re
import unicodedata
from datetime import datetime

from src.core import cache
from src.core.errores import ErrorValidacion, NoEncontrado
from src.core.utils import oid, serializar
from src.crud import campus
from src.database import get_mongo_db

# Opciones visuales que el formulario ofrece (iconos de Bootstrap Icons y paleta de colores)
ICONOS = [
    "book", "pc-display", "dribbble", "easel", "projector", "headset",
    "music-note-beamed", "camera-video", "people", "building", "cup-hot",
    "controller", "tools", "mortarboard", "door-open", "bicycle",
    "three-dots",  # "Otros": para cuando ningun icono encaja
]
ICONO_POR_DEFECTO = "three-dots"
COLORES = ["red", "blue", "green", "purple", "orange", "teal", "gray"]

# Se insertan solo si la coleccion esta vacia (primer arranque). Mantienen los codigos
# que ya usan los recursos existentes.
POR_DEFECTO = [
    {"codigo": "sala_estudio", "nombre": "Sala de Estudio", "icono": "book", "color": "red"},
    {"codigo": "laboratorio", "nombre": "Laboratorio", "icono": "pc-display", "color": "blue"},
    {"codigo": "cancha", "nombre": "Cancha Deportiva", "icono": "dribbble", "color": "green"},
]


def _col():
    return get_mongo_db()["tipos_recurso"]


def _slug(texto):
    """'Sala de Reuniones' -> 'sala_de_reuniones'."""
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_.lower()).strip("_")


def _sembrar():
    # Inicializa cada campus una sola vez, incluso si se agregó después del arranque.
    for c in campus.listar():
        campus_id = c["id"]
        if _col().count_documents({"campus_id": campus_id}) == 0:
            ahora = datetime.now().isoformat()
            for tipo in POR_DEFECTO:
                _col().update_one(
                    {"campus_id": campus_id, "codigo": tipo["codigo"]},
                    {"$setOnInsert": {**tipo, "campus_id": campus_id, "fecha_creacion": ahora}},
                    upsert=True,
                )
            cache.invalidar("tipos:*")


def _validar(data, parcial=False, campus_id=None):
    if not parcial and not (data.get("nombre") or "").strip():
        raise ErrorValidacion("El nombre es obligatorio")
    if "nombre" in data:
        if not (data["nombre"] or "").strip():
            raise ErrorValidacion("El nombre no puede estar vacio")
        if len(data["nombre"].strip()) > 40:
            raise ErrorValidacion("El nombre no puede superar 40 caracteres")
    if data.get("icono") and data["icono"] not in ICONOS:
        raise ErrorValidacion("Icono invalido")
    if data.get("color") and data["color"] not in COLORES:
        raise ErrorValidacion("Color invalido")
    campus_id = data.get("campus_id", campus_id)
    if not campus.es_valido(campus_id):
        raise ErrorValidacion("Campus invalido")


def crear(data):
    """CREATE. El codigo es unico dentro del campus."""
    data = dict(data)
    data["campus_id"] = campus.normalizar(data.get("campus_id"))
    _validar(data)
    nombre = data["nombre"].strip()
    codigo = _slug(nombre)
    if not codigo:
        raise ErrorValidacion("El nombre debe incluir letras o numeros")
    campus_id = campus.normalizar(data.get("campus_id"))
    if _col().find_one({"codigo": codigo, "campus_id": campus_id}):
        raise ErrorValidacion("Ya existe un tipo con ese nombre")

    res = _col().insert_one({
        "codigo": codigo,
        "nombre": nombre,
        "icono": data.get("icono") or ICONO_POR_DEFECTO,
        "color": data.get("color") or "red",
        "campus_id": campus_id,
        "fecha_creacion": datetime.now().isoformat(),
    })
    cache.invalidar("tipos:*")
    return str(res.inserted_id)


def listar(campus_id=None):
    """READ (lista) con cache. Siembra los tipos por defecto la primera vez."""
    k = cache.key("tipos", "lista", campus_id or "todos")
    cached = cache.get(k)
    if cached is not None:
        return cached

    _sembrar()
    filtro = {"campus_id": campus_id} if campus_id else {}
    lista = [serializar(t) for t in _col().find(filtro).sort("nombre", 1)]
    cache.set(k, lista)
    return lista


def codigos(campus_id=None):
    """Set de codigos validos (lo usa crud.recursos para validar)."""
    return {t["codigo"] for t in listar(campus_id=campus_id)}


def obtener(id_tipo, campus_id=None):
    """READ (uno)."""
    filtro = {"_id": oid(id_tipo)}
    if campus_id:
        filtro["campus_id"] = campus_id
    doc = _col().find_one(filtro)
    if not doc:
        raise NoEncontrado("Tipo de recurso no encontrado")
    return serializar(doc)


def actualizar(id_tipo, data, campus_id=None):
    """UPDATE parcial. El codigo no cambia porque los recursos lo referencian."""
    cambios = {k: v for k, v in data.items() if k in {"nombre", "icono", "color", "campus_id"} and v}
    if not cambios:
        raise ErrorValidacion("No hay campos para actualizar")
    tipo_actual = obtener(id_tipo, campus_id=campus_id)
    destino = cambios.get("campus_id", tipo_actual.get("campus_id", campus.DEFAULT_CAMPUS_ID))
    _validar(cambios, parcial=True, campus_id=destino)
    origen = tipo_actual.get("campus_id", campus.DEFAULT_CAMPUS_ID)
    if destino != origen:
        usados = get_mongo_db()["recursos"].count_documents({
            "tipo": tipo_actual["codigo"], "campus_id": origen,
        })
        if usados:
            raise ErrorValidacion(
                "No se puede cambiar de campus: hay espacios que usan este tipo"
            )
    if "nombre" in cambios:
        cambios["nombre"] = cambios["nombre"].strip()
        repetido = _col().find_one({
            "nombre": cambios["nombre"], "campus_id": destino,
            "_id": {"$ne": oid(id_tipo)},
        })
        if repetido:
            raise ErrorValidacion("Ya existe un tipo con ese nombre")

    if "campus_id" in cambios or "nombre" in cambios:
        repetido = _col().find_one({
            "codigo": tipo_actual["codigo"], "campus_id": destino,
            "_id": {"$ne": oid(id_tipo)},
        })
        if repetido:
            raise ErrorValidacion("Ya existe un tipo con ese codigo en el campus")

    res = _col().update_one({"_id": oid(id_tipo)}, {"$set": cambios})
    if res.matched_count == 0:
        raise NoEncontrado("Tipo de recurso no encontrado")
    cache.invalidar("tipos:*")
    return True


def eliminar(id_tipo, campus_id=None):
    """DELETE. No permite borrar si hay recursos con ese tipo ni si es el unico que queda."""
    tipo = obtener(id_tipo, campus_id=campus_id)
    usados = get_mongo_db()["recursos"].count_documents({
        "tipo": tipo["codigo"], "campus_id": tipo["campus_id"],
    })
    if usados:
        raise ErrorValidacion(f"No se puede eliminar: {usados} espacio(s) usan este tipo")
    if _col().count_documents({"campus_id": tipo["campus_id"]}) <= 1:
        raise ErrorValidacion("Debe existir al menos un tipo de recurso")

    _col().delete_one({"_id": oid(id_tipo), "campus_id": tipo["campus_id"]})
    cache.invalidar("tipos:*")
    return True
