"""개발 도구가 명시한 개발 환경에서만 제공되는지 검증한다."""

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("environment", [None, "production", "staging"])
def test_production_does_not_load_or_serve_debug_tools(
    web_database, monkeypatch, environment
):
    if environment is None:
        monkeypatch.delenv("LIBRARY_ENV", raising=False)
    else:
        monkeypatch.setenv("LIBRARY_ENV", environment)
    application = importlib.import_module("library_service.main").create_app()
    with TestClient(application) as client:
        for path in ["/", "/login", "/signup"]:
            response = client.get(path)
            assert response.status_code == 200
            assert "/_dev/" not in response.text
        for path in ["/_dev/debug.js", "/_dev/debug.css", "/static/debug.js"]:
            assert client.get(path).status_code == 404


def test_development_loads_debug_module_on_pages_and_errors(web_database, monkeypatch):
    monkeypatch.setenv("LIBRARY_ENV", "development")
    application = importlib.import_module("library_service.main").create_app()
    with TestClient(application) as client:
        for path in ["/", "/login", "/signup"]:
            response = client.get(path)
            assert response.status_code == 200
            assert 'type="module" src="/_dev/debug.js"' in response.text
        invalid = client.post("/login", data={"username": "x", "password": "x"})
        assert invalid.status_code == 401
        assert 'src="/_dev/debug.js"' in invalid.text
        for path in ["/_dev/debug.js", "/_dev/debug.css"]:
            assert client.get(path).status_code == 200
        assert client.get("/static/debug.js").status_code == 404
