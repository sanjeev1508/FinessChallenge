import os

os.environ.setdefault("SEED_DEMO", "false")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    with TestClient(app) as c:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        yield c


@pytest.fixture()
def user_id(client):
    r = client.post("/api/users", json={"firstName": "Test", "lastName": "Runner"})
    assert r.status_code == 201
    return r.json()["userId"]
