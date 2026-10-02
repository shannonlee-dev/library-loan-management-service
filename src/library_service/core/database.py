import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from library_service.core.paths import PROJECT_DIR

BASE_DIR = PROJECT_DIR
DEFAULT_DATABASE_PATH = BASE_DIR / "library.db"
DATABASE_URL = os.getenv("LIBRARY_DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
