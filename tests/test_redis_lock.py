from time import monotonic, sleep

from src.db.redis_client import acquire_lock, release_lock


class FakeRedis:
    def __init__(self):
        self.values = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = (value, monotonic() + ex if ex is not None else None)
        return True

    def get(self, key):
        item = self.values.get(key)
        if item is None:
            return None
        value, expires_at = item
        if expires_at is not None and monotonic() >= expires_at:
            self.values.pop(key, None)
            return None
        return value

    def delete(self, key):
        return int(self.values.pop(key, None) is not None)


def test_lock_rechaza_segundo_adquiriente_y_exige_token():
    redis = FakeRedis()
    token = acquire_lock("slot", ttl=10, client=redis)

    assert token
    assert acquire_lock("slot", ttl=10, client=redis) is None
    assert release_lock("slot", "token-equivocado", client=redis) is False
    assert release_lock("slot", token, client=redis) is True


def test_lock_expira_y_puede_adquirirse_de_nuevo():
    redis = FakeRedis()
    token = acquire_lock("slot", ttl=0.01, client=redis)

    assert token
    sleep(0.02)
    nuevo_token = acquire_lock("slot", ttl=10, client=redis)

    assert nuevo_token
    assert nuevo_token != token
