from src.db.redis_client import acquire_lock, release_lock


class FakeRedis:
    def __init__(self):
        self.values = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        return int(self.values.pop(key, None) is not None)


def test_lock_rechaza_segundo_adquiriente_y_exige_token():
    redis = FakeRedis()
    token = acquire_lock("slot", ttl=10, client=redis)

    assert token
    assert acquire_lock("slot", ttl=10, client=redis) is None
    assert release_lock("slot", "token-equivocado", client=redis) is False
    assert release_lock("slot", token, client=redis) is True
