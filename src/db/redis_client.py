"""Cliente Redis compartido y operaciones de lock con token seguro."""

import redis

from src.config import Config


def cliente():
    if Config.REDIS_URL:
        return redis.Redis.from_url(
            Config.REDIS_URL, decode_responses=True, socket_connect_timeout=3
        )
    return redis.Redis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=3,
    )


def acquire_lock(key, ttl=10, client=None):
    """Intenta adquirir ``key`` y devuelve un token, o ``None`` si está ocupada."""
    client = client or cliente()
    token = __import__("uuid").uuid4().hex
    return token if client.set(key, token, nx=True, ex=ttl) else None


def release_lock(key, token, client=None):
    """Libera solo el lock cuyo token pertenece al llamador."""
    client = client or cliente()
    if client.get(key) != token:
        return False
    return bool(client.delete(key))
