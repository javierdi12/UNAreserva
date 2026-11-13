from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import sleep

from src.db.redis_client import acquire_lock, release_lock


class RedisConcurrente:
    def __init__(self):
        self.valor = None
        self.lock = Lock()

    def set(self, key, value, nx=False, ex=None):
        with self.lock:
            if nx and self.valor is not None:
                return False
            self.valor = value
            return True

    def get(self, key):
        with self.lock:
            return self.valor

    def delete(self, key):
        with self.lock:
            self.valor = None
            return 1


def test_solo_una_solicitud_adquiere_el_slot_concurrente():
    redis = RedisConcurrente()
    contador = {"activos": 0, "maximo": 0}
    contador_lock = Lock()

    def intentar(numero):
        token = acquire_lock("recurso:fecha:franja", ttl=10, client=redis)
        if token is None:
            return "rechazada"
        try:
            with contador_lock:
                contador["activos"] += 1
                contador["maximo"] = max(contador["maximo"], contador["activos"])
            sleep(0.002)
            with contador_lock:
                contador["activos"] -= 1
            return "confirmada"
        finally:
            release_lock("recurso:fecha:franja", token, client=redis)

    with ThreadPoolExecutor(max_workers=20) as executor:
        estados = list(executor.map(intentar, range(20)))

    assert estados.count("confirmada") >= 1
    assert contador["maximo"] == 1
