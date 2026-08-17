from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import load_database_config

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        db_config = load_database_config()
        _engine = create_engine(db_config.sqlalchemy_url, pool_pre_ping=True)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def get_session():
    return get_session_factory()()


def check_connection() -> None:
    """Verifies the connection; raises on failure (caught by main.py)."""
    engine = get_engine()
    with engine.connect():
        pass
