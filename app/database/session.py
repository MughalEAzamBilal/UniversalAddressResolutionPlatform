import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import get_settings
from app.database.base import Base

settings = get_settings()

# Ensure data directory exists
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite"):
    db_path = db_url.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

connect_args = {"check_same_thread": False, "timeout": 15} if db_url.startswith("sqlite") else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False,
    future=True
)

# Enable foreign keys and safe journal mode for SQLite (avoid WAL on NFS/PythonAnywhere)
if db_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        if settings.APP_ENV != "production":
            try:
                cursor.execute("PRAGMA journal_mode=WAL")
            except Exception:
                pass
        else:
            try:
                cursor.execute("PRAGMA journal_mode=DELETE")
            except Exception:
                pass
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db() -> Session:
    """Returns database session scoped to Flask request context (g.db), or a new session."""
    try:
        from flask import g, has_request_context
        if has_request_context():
            if not hasattr(g, "db") or g.db is None:
                g.db = SessionLocal()
            return g.db
    except ImportError:
        pass
    return SessionLocal()


def close_db(e=None):
    """Teardown handler to close request database session."""
    try:
        from flask import g
        db = getattr(g, "db", None)
        if db is not None:
            db.close()
            g.db = None
    except ImportError:
        pass


def init_db():
    """Create all tables in database if they don't exist."""
    import app.models  # Ensure all models are registered with Base
    Base.metadata.create_all(bind=engine)
