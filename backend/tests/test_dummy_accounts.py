import csv

import pytest
from sqlalchemy import func, select

from app.auth import verify_password
from app.database import SessionLocal
from app.models import Activity, AuthAccount
from app import provision_dummy_accounts as provisioning
from app.provision_dummy_accounts import provision_dummy_accounts
from app.schemas import ActivityCreate, AuthRegister, UserCreate
from app.services import create_activity, register_account, register_user


def test_legacy_dummy_login_preserves_history(client):
    with SessionLocal() as db:
        user = register_user(db, UserCreate(firstName="Legacy", lastName="Runner"))
        create_activity(db, ActivityCreate(
            userId=user.id, sport="running", metricType="distance", value=3,
        ))
        uid = user.id
        credentials = provision_dummy_accounts(db)
        db.commit()
        assert len(credentials) == 1
        login = credentials[0]
        assert login["email"] == "legacy.runner@example.com"
        assert verify_password(login["password"], user.auth_account.password_hash)
        assert user.auth_account.password_hash != login["password"]
        assert db.scalar(select(func.count()).select_from(Activity)) == 1

    response = client.post("/api/auth/login", json={
        "email": login["email"], "password": login["password"],
    })
    assert response.status_code == 200
    assert response.json()["user"]["userId"] == uid
    assert response.json()["user"]["totalPoints"] == 300
    assert response.json()["user"]["activityCount"] == 1
    assert "password" not in response.json()["user"]


def test_backfill_preserves_working_accounts_and_is_idempotent(client):
    with SessionLocal() as db:
        existing = register_account(db, AuthRegister(
            firstName="Current", lastName="Runner", email="current@example.com",
            password="OriginalPassword123",
        ))
        original_hash = existing.auth_account.password_hash
        legacy = register_user(db, UserCreate(firstName="Legacy", lastName="Runner"))
        credentials = provision_dummy_accounts(db)
        db.commit()
        assert [row["userId"] for row in credentials] == [legacy.id]
        assert existing.email == "current@example.com"
        assert existing.auth_account.password_hash == original_hash
        assert provision_dummy_accounts(db) == []
        db.commit()
        assert db.scalar(select(func.count()).select_from(AuthAccount)) == 2


def test_dummy_emails_avoid_case_insensitive_collisions(client):
    with SessionLocal() as db:
        register_account(db, AuthRegister(
            firstName="Current", lastName="Runner", email="legacy.runner@example.com",
            password="OriginalPassword123",
        ))
        register_user(db, UserCreate(
            firstName="Email", lastName="Owner", email="LEGACY.RUNNER.2@example.com",
        ))
        legacy = register_user(db, UserCreate(firstName="Legacy", lastName="Runner"))
        credentials = provision_dummy_accounts(db)
        db.commit()
        login = next(row for row in credentials if row["userId"] == legacy.id)
        assert login["email"] == "legacy.runner.3@example.com"
        assert len({row["email"] for row in credentials}) == len(credentials)
        assert len({row["password"] for row in credentials}) == len(credentials)


def test_backfill_can_be_rolled_back(client):
    with SessionLocal() as db:
        user = register_user(db, UserCreate(
            firstName="Legacy", lastName="Runner", email="old@example.com",
        ))
        provision_dummy_accounts(db)
        db.rollback()
        db.refresh(user)
        assert user.email == "old@example.com"
        assert user.auth_account is None


def test_cli_exports_credentials_and_never_overwrites_them(client, tmp_path, monkeypatch):
    output = tmp_path / "local.dummy-credentials.csv"
    monkeypatch.setattr(provisioning, "IS_MEMORY", False)
    monkeypatch.setattr("sys.argv", ["provision_dummy_accounts", "--output", str(output)])
    with SessionLocal() as db:
        register_user(db, UserCreate(firstName="Legacy", lastName="Runner"))
    provisioning.main()
    original = output.read_bytes()
    with output.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 1
    assert client.post("/api/auth/login", json={
        "email": rows[0]["email"], "password": rows[0]["password"],
    }).status_code == 200
    with pytest.raises(SystemExit) as error:
        provisioning.main()
    assert error.value.code == 2
    assert output.read_bytes() == original
    second = tmp_path / "second.dummy-credentials.csv"
    monkeypatch.setattr("sys.argv", ["provision_dummy_accounts", "--output", str(second)])
    provisioning.main()
    assert not second.exists()


def test_cli_export_failure_rolls_back_accounts(client, tmp_path, monkeypatch):
    output = tmp_path / "local.dummy-credentials.csv"
    monkeypatch.setattr(provisioning, "IS_MEMORY", False)
    monkeypatch.setattr("sys.argv", ["provision_dummy_accounts", "--output", str(output)])
    with SessionLocal() as db:
        user = register_user(db, UserCreate(firstName="Legacy", lastName="Runner"))
        uid = user.id

    def fail_write(self):
        raise OSError("disk full")

    monkeypatch.setattr(csv.DictWriter, "writeheader", fail_write)
    with pytest.raises(OSError, match="disk full"):
        provisioning.main()
    assert not output.exists()
    with SessionLocal() as db:
        assert db.get(AuthAccount, uid) is None


def test_cli_rejects_memory_database(tmp_path, monkeypatch):
    output = tmp_path / "local.dummy-credentials.csv"
    monkeypatch.setattr(provisioning, "IS_MEMORY", True)
    monkeypatch.setattr("sys.argv", ["provision_dummy_accounts", "--output", str(output)])
    with pytest.raises(SystemExit) as error:
        provisioning.main()
    assert error.value.code == 2
    assert not output.exists()
