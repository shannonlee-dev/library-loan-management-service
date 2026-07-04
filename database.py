from collections.abc import Generator
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


BASE_DIR = Path(__file__).resolve().parent
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
