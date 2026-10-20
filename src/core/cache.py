"""
Redis: cache de lecturas y candado distribuido.
Si Redis no esta disponible, todo funciona sin cache ni candado.
"""
import json
import uuid
from functools import lru_cache

import redis

from src.config import Config
from src.core.errores import ErrorValidacion

CACHE_TTL = 60   # segundos
LOCK_TTL = 10    # segundos


@lru_cache(maxsize=1)
def get_redis():
    """Devuelve el cliente Redis o None si no hay conexion."""
    try:
        r = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        r.ping()
        return r
    except Exception as e:
        print(f"[WARN] Redis no disponible, se trabaja sin cache: {e}")
        return None


def key(*parts):
    """Arma una llave con el prefijo del proyecto: UNAreserva:a:b:c"""
    return Config.REDIS_PREFIX + ":".join(parts)


def get(k):
    r = get_redis()
    if not r:
        return None
    try:
        data = r.get(k)
        return json.loads(data) if data else None
    except Exception:
        return None


def set(k, value):
    r = get_redis()
    if not r:
        return
    try:
        r.setex(k, CACHE_TTL, json.dumps(value, default=str))
    except Exception:
        pass


def invalidar(*patrones):
    """Borra las llaves que coincidan con cada patron (ej. 'recursos:*')."""
    r = get_redis()
    if not r:
        return
    try:
        for patron in patrones:
            for k in r.scan_iter(match=key(patron)):
                r.delete(k)
    except Exception:
        pass


class Candado:
    """Candado distribuido por recurso (SET NX EX). Uso: with Candado(id): ..."""

    def __init__(self, id_recurso):
        self.k = key("lock", "reserva", id_recurso)
        self.token = str(uuid.uuid4())
        self.r = get_redis()

    def __enter__(self):
        if self.r:
            try:
                if not self.r.set(self.k, self.token, nx=True, ex=LOCK_TTL):
                    raise ErrorValidacion(
                        "El recurso esta siendo reservado por otro usuario, intente de nuevo"
                    )
            except redis.RedisError:
                self.r = None  # sin Redis, se continua sin candado
        return self

    def __exit__(self, *exc):
        if self.r:
            try:
                if self.r.get(self.k) == self.token:
                    self.r.delete(self.k)
            except redis.RedisError:
                pass