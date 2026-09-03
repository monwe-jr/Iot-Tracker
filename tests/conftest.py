from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import app, get_db_pool, get_redis


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def set(self, key, value):
        self.store[key] = value

    async def get(self, key):
        return self.store.get(key)


class FakeConnection:
    def __init__(self, rows):
        self._rows = rows

    async def execute(self, query, device_id, voltage_v, frequency_mhz, temperature_c, status):
        self._rows.append(
            {
                "device_id": device_id,
                "timestamp": datetime.now(timezone.utc),
                "voltage_v": voltage_v,
                "frequency_mhz": frequency_mhz,
                "temperature_c": temperature_c,
                "status": status,
            }
        )

    async def fetch(self, query, device_id, limit):
        matched = [row for row in self._rows if row["device_id"] == device_id]
        matched.sort(key=lambda row: row["timestamp"], reverse=True)
        return matched[:limit]


class FakeAcquireContext:
    def __init__(self, rows):
        self._rows = rows

    async def __aenter__(self):
        return FakeConnection(self._rows)

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self):
        self.rows = []

    def acquire(self):
        return FakeAcquireContext(self.rows)


@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.fixture
def fake_pool():
    return FakePool()


@pytest.fixture
def client(fake_redis, fake_pool):
    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_db_pool] = lambda: fake_pool
    yield TestClient(app)
    app.dependency_overrides.clear()
