"""database.py — SQLite engine initialization and session management.
exports: DatabaseManager
used_by: pipeline.py → DatabaseManager, app.py → DatabaseManager
rules:
Initialize SQLite with pragmas for safety (foreign_keys=ON) and performance.
"""

from contextlib import contextmanager
from typing import Generator
import sqlite3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy import event

from optictriage.models import Base

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if type(dbapi_connection) is sqlite3.Connection:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

from optictriage.database_migration import migrate_db

class DatabaseManager:
    """Manages the SQLAlchemy engine and provides sessions."""

    def __init__(self, db_path: str = "sqlite:///optictriage.db"):
        self.db_path = db_path
        self.engine = create_engine(db_path, echo=False)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def create_all(self):
        """Creates all tables defined in models.py."""
        migrate_db(self.db_path)
        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provides a transactional scope around a series of operations."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
