"""DB와 세션을 테스트별 임시 환경으로 격리한다."""

import importlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from library_service import bootstrap
from library_service.core import database


@pytest.fixture
def web_database(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'library.db'}",
        connect_args={"check_same_thread": False},
    )
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessions)
    monkeypatch.setattr(bootstrap, "engine", engine)
    monkeypatch.setattr(bootstrap, "SessionLocal", sessions)
    monkeypatch.setenv("SESSION_SECRET_KEY", "isolated-test-session-secret")
    try:
        yield sessions
    finally:
        engine.dispose()


@pytest.fixture
def client(web_database):
    application = importlib.import_module("library_service.main").create_app()
    with TestClient(application) as test_client:
        yield test_client
