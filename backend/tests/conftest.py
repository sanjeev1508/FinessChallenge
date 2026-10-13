import os

os.environ.setdefault("SEED_DEMO", "false")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-for-fitness-challenge")

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
    r = client.post("/api/users", json={
        "firstName": "Test", "lastName": "Runner",
        "email": "test.runner@example.com", "password": "TestPassword123",
    })
    assert r.status_code == 201
    body = r.json()
    client.headers.update({"Authorization": f"Bearer {body['accessToken']}"})
    return body["user"]["userId"]
