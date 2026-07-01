from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import get_settings, resolve_database_url

settings = get_settings()
database_url = resolve_database_url(settings.database_url)

_connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
