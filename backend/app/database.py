"""Database engine, session handling and SQLite tuning.

Reliability notes
-----------------
* In-memory SQLite: every connection normally gets its *own* empty database,
  so we use StaticPool to share one connection across the app. A single
  sqlite3 connection must not run two transactions at once, so access is
  serialised with a process-wide lock (``get_db``). Throughput is still far
  above what this app needs (each request holds the lock for ~1 ms).
* File SQLite: normal connection pool, WAL journal mode and a busy timeout so
  concurrent writers wait instead of failing with "database is locked".
* Foreign keys are switched on for every connection (SQLite default is off).
"""
import threading
from typing import Iterator

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


# threading.Lock (not RLock) on purpose: FastAPI may run the setup and the
# teardown of a sync dependency on different worker threads, and a plain Lock
# can be released from any thread.
_memory_db_lock = threading.Lock()


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session; always rolled back/closed."""
    if IS_MEMORY:
        _memory_db_lock.acquire()
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        if IS_MEMORY:
            _memory_db_lock.release()


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)
    Base.metadata.create_all(bind=engine)
