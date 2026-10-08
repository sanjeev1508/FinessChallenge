"""Database engine, session handling and SQLite tuning.

Reliability notes
-----------------
* In-memory SQLite: every connection normally gets its *own* empty database,
  so we use StaticPool to share one connection across the app. A single
  sqlite3 connection must not run two transactions at once, so access is
  serialised with an async request gate (``get_db``). Waiting requests do not
  occupy the worker threads needed to run the request holding the connection.
* File SQLite: normal connection pool, WAL journal mode and a busy timeout so
  concurrent writers wait instead of failing with "database is locked".
* Foreign keys are switched on for every connection (SQLite default is off).
"""
from typing import AsyncIterator

import anyio
from fastapi import Request
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import DATABASE_URL

IS_MEMORY = ":memory:" in DATABASE_URL or "mode=memory" in DATABASE_URL

if IS_MEMORY:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 15},
        pool_pre_ping=True,
    )


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    if not IS_MEMORY:
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=15000")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db(request: Request) -> AsyncIterator[Session]:
    """FastAPI dependency yielding a session; always rolled back/closed."""
    lock = request.app.state.memory_db_lock if IS_MEMORY else None
    if lock is not None:
        await lock.acquire()
    try:
        db = SessionLocal()
        try:
            yield db
        finally:
            # close() rolls back uncommitted work. Finish it before handing the
            # shared connection to another request, even after cancellation.
            with anyio.CancelScope(shield=True):
                # Like FastAPI's sync dependency teardown, cleanup must not
                # compete with workers waiting for a pooled DB connection.
                await anyio.to_thread.run_sync(db.close, limiter=anyio.CapacityLimiter(1))
    finally:
        if lock is not None:
            lock.release()


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)
    Base.metadata.create_all(bind=engine)
