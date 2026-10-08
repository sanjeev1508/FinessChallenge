import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest


@pytest.fixture(params=["memory", "file"])
def database_url(request, tmp_path):
    if request.param == "memory":
        return "sqlite:///:memory:"
    return f"sqlite:///{(tmp_path / 'requests.db').as_posix()}"


def run_probe(source, database_url):
    env = {**os.environ, "DATABASE_URL": database_url, "SEED_DEMO": "false"}
    # A regressed worker-pool deadlock must fail the test, not hang pytest itself.
    try:
        result = subprocess.run(
            [sys.executable, "-c", textwrap.dedent(source)],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("Database requests failed to complete: possible worker-pool deadlock.")
    assert result.returncode == 0, result.stdout + result.stderr


def test_concurrent_requests_do_not_starve_database_worker(database_url):
    run_probe("""
        import asyncio
        import logging

        import anyio
        import httpx

        from app.main import app

        logging.getLogger("httpx").setLevel(logging.WARNING)

        async def main():
            anyio.to_thread.current_default_thread_limiter().total_tokens = 4
            async with app.router.lifespan_context(app):
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    registered = await client.post("/api/users", json={
                        "firstName": "Concurrent", "lastName": "Athlete",
                    })
                    assert registered.status_code == 201
                    uid = registered.json()["userId"]
                    writes = [client.post("/api/activities", json={
                        "userId": uid, "sport": "running", "metricType": "distance",
                        "value": 1, "clientRequestId": f"burst-{i}",
                    }) for i in range(64)]
                    reads = [client.get("/api/health") for _ in range(64)]
                    results = await asyncio.gather(*writes, *reads)
                    assert all(r.status_code == 201 for r in results[:64])
                    assert all(r.status_code == 200 for r in results[64:])
                    user = (await client.get(f"/api/users/{uid}")).json()
                    assert user["totalPoints"] == 6400
                    assert user["activityCount"] == 64
                    assert (await client.get("/api/health")).status_code == 200

        anyio.run(main)
    """, database_url)


def test_database_gate_recovers_after_cancellation_and_errors(database_url):
    run_probe("""
        from contextlib import asynccontextmanager
        from unittest.mock import patch

        import anyio
        import httpx
        from starlette.requests import Request

        from app.database import IS_MEMORY, get_db
        from app.main import app
        from app.models import User

        managed_session = asynccontextmanager(get_db)

        async def add_uncommitted(db, last_name):
            db.add(User(
                first_name="Uncommitted", last_name=last_name,
                first_name_key="uncommitted", last_name_key=last_name.lower(),
            ))
            await anyio.to_thread.run_sync(db.flush)

        async def main():
            async with app.router.lifespan_context(app):
                request = Request({"type": "http", "app": app})
                if IS_MEMORY:
                    started, entered = anyio.Event(), anyio.Event()

                    async def waiter():
                        started.set()
                        async with managed_session(request):
                            entered.set()

                    async with managed_session(request):
                        async with anyio.create_task_group() as tasks:
                            tasks.start_soon(waiter)
                            await started.wait()
                            await anyio.sleep(0)
                            tasks.cancel_scope.cancel()
                        assert not entered.is_set()

                with anyio.CancelScope() as scope:
                    async with managed_session(request) as db:
                        await add_uncommitted(db, "Cancelled")
                        scope.cancel()
                        await anyio.sleep(0)

                try:
                    async with managed_session(request) as db:
                        await add_uncommitted(db, "Failed")
                        raise ValueError("request failed")
                except ValueError as exc:
                    assert str(exc) == "request failed"
                else:
                    raise AssertionError("Request exception was swallowed")

                for fail_at in ("create", "close"):
                    class BrokenSession:
                        def close(self):
                            raise RuntimeError("close failed")

                    options = ({"side_effect": RuntimeError("create failed")}
                               if fail_at == "create" else {"return_value": BrokenSession()})
                    try:
                        with patch("app.database.SessionLocal", **options):
                            async with managed_session(request):
                                pass
                    except RuntimeError as exc:
                        assert str(exc) == f"{fail_at} failed"
                    else:
                        raise AssertionError("Session failure was swallowed")

                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    assert (await client.get("/api/health")).status_code == 200
                    users = await client.get("/api/users")
                    assert users.status_code == 200
                    assert users.json() == [], "Uncommitted users survived cleanup"

        anyio.run(main)
    """, database_url)
