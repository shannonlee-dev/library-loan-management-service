"""Error contracts, bcrypt compatibility, filters and OAuth security boundaries."""

import hashlib
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from sqlalchemy import select

from library_service.models import Book, User
from library_service.models.entities import OAuthIdentity
from library_service.routers import oauth_routes
from library_service.services import auth_service, oauth_service


def test_bcrypt_and_legacy_passwords():
    encoded = auth_service.hash_password("password123")
    assert encoded.startswith("$2b$")
    assert auth_service.verify_password("password123", encoded)
    assert not auth_service.verify_password("wrong", encoded)
    salt = b"legacy-salt"
    digest = hashlib.pbkdf2_hmac("sha256", b"password123", salt, 260000)
    legacy = f"pbkdf2_sha256$260000${salt.hex()}${digest.hex()}"
    assert auth_service.verify_password("password123", legacy)
    for value in ("!", "pbkdf2_sha256$bad$xx$xx", "$2b$broken"):
        assert not auth_service.verify_password("password123", value)


def test_signup_bounds(client):
    for password in ("short", "한" * 25):
        response = client.post(
            "/signup",
            data={"username": "bounds", "display_name": "이름", "password": password},
        )
        assert response.status_code == 400
    response = client.post(
        "/signup",
        data={
            "username": "github:123",
            "display_name": "이름",
            "password": "password123",
        },
    )
    assert response.status_code == 400


def test_consistent_errors(client):
    for path, status in (("/missing", 404), ("/logout", 405)):
        response = client.get(path)
        assert response.status_code == status
        assert "요청을 처리할 수 없습니다" in response.text
        response = client.get(path, headers={"Accept": "application/json"})
        assert response.json()["error"]["status"] == status
    client.post("/login", data={"username": "demo", "password": "demo1234"})
    response = client.post("/app/books/not-an-integer/borrow")
    assert response.status_code == 422 and "입력 형식" in response.text
    assert client.get("/app?availability=invalid").status_code == 422


def test_combined_filters(client, web_database):
    client.post("/login", data={"username": "demo", "password": "demo1234"})
    with web_database() as db:
        book = db.scalar(select(Book).order_by(Book.id))
        book_id, title = book.id, book.title
    client.post(f"/app/books/{book_id}/borrow")
    response = client.get(
        "/app", params={"q": title, "availability": "available", "status": "returned"}
    )
    assert "검색 조건에 맞는 도서가 없습니다" in response.text
    response = client.get("/app", params={"q": title, "availability": "borrowed"})
    assert title in response.text
    response = client.get("/app", params={"q": "%", "status": "returned"})
    assert "검색 조건에 맞는 도서가 없습니다" in response.text


@pytest.fixture
def oauth_config(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("GITHUB_REDIRECT_URI", "http://testserver/auth/github/callback")


def start_oauth(client):
    response = client.get("/auth/github", follow_redirects=False)
    assert response.status_code == 303
    params = parse_qs(urlsplit(response.headers["location"]).query)
    assert params["code_challenge_method"] == ["S256"]
    assert "test-secret" not in response.headers["location"]
    return params["state"][0]


def test_oauth_unconfigured(client, monkeypatch):
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    assert client.get("/auth/github").status_code == 503


def test_oauth_login_repeat_and_replay(client, web_database, oauth_config, monkeypatch):
    async def profile(code, verifier):
        assert code == "valid-code" and len(verifier) >= 43
        return {"id": 12345, "login": "demo", "name": "소셜 사용자"}

    monkeypatch.setattr(oauth_service, "github_profile", profile)
    for _ in range(2):
        state = start_oauth(client)
        response = client.get(
            "/auth/github/callback", params={"state": state, "code": "valid-code"}
        )
        assert (
            response.status_code == 200 and "소셜 사용자님 환영합니다" in response.text
        )
        assert (
            client.get(
                "/auth/github/callback", params={"state": state, "code": "valid-code"}
            ).status_code
            == 400
        )
        client.post("/logout")
    with web_database() as db:
        identities = list(db.scalars(select(OAuthIdentity)))
        assert len(identities) == 1
        assert identities[0].user.username != "demo"
        assert identities[0].user.password_hash == "!"
        assert (
            db.scalar(select(User).where(User.username == "demo")).id
            != identities[0].user_id
        )


def test_oauth_state_cancellation_expiry(client, oauth_config, monkeypatch):
    state = start_oauth(client)
    assert (
        client.get(
            "/auth/github/callback", params={"state": "wrong", "code": "x"}
        ).status_code
        == 400
    )
    state = start_oauth(client)
    assert (
        client.get(
            "/auth/github/callback", params={"state": state, "error": "access_denied"}
        ).status_code
        == 400
    )
    state = start_oauth(client)
    now = oauth_routes.time.time()
    monkeypatch.setattr(oauth_routes.time, "time", lambda: now + 601)
    assert (
        client.get(
            "/auth/github/callback", params={"state": state, "code": "x"}
        ).status_code
        == 400
    )


def test_oauth_token_exchange(client, oauth_config, monkeypatch):
    original_client = httpx.AsyncClient

    def transport(request):
        if request.url.path.endswith("access_token"):
            assert b"code_verifier=" in request.content
            return httpx.Response(200, json={"access_token": "private-token"})
        assert request.headers["authorization"] == "Bearer private-token"
        return httpx.Response(200, json={"id": 998, "login": "reader"})

    monkeypatch.setattr(
        oauth_service.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(transport), **kwargs
        ),
    )
    state = start_oauth(client)
    response = client.get(
        "/auth/github/callback", params={"state": state, "code": "ok"}
    )
    assert response.status_code == 200
    assert "private-token" not in response.text
    assert "private-token" not in str(client.cookies)


def test_oauth_provider_failure(client, oauth_config, monkeypatch):
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        oauth_service.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(lambda request: httpx.Response(503)), **kwargs
        ),
    )
    state = start_oauth(client)
    response = client.get(
        "/auth/github/callback", params={"state": state, "code": "ok"}
    )
    assert response.status_code == 502
    assert client.get("/app", follow_redirects=False).status_code == 303


def test_cross_origin_forms_rejected(client):
    response = client.post(
        "/login",
        data={"username": "demo", "password": "demo1234"},
        headers={"Origin": "https://other.example"},
    )
    assert response.status_code == 403
    assert client.get("/app", follow_redirects=False).status_code == 303
    assert (
        client.post("/logout", headers={"Origin": "http://testserver"}).status_code
        == 200
    )


def test_unexpected_error_is_sanitized(client):
    from fastapi.testclient import TestClient

    @client.app.get("/test-failure")
    def fail():
        raise RuntimeError("private-database-password")

    with TestClient(client.app, raise_server_exceptions=False) as failing_client:
        response = failing_client.get(
            "/test-failure", headers={"Accept": "application/json"}
        )
    assert response.status_code == 500
    assert response.json()["error"]["status"] == 500
    assert "private-database-password" not in response.text


def test_production_cookies_and_no_demo(web_database, monkeypatch):
    from fastapi.testclient import TestClient

    from library_service.main import create_app

    monkeypatch.setenv("LIBRARY_ENV", "production")
    application = create_app()
    with web_database() as db:
        assert db.scalar(select(User).where(User.username == "demo")) is None
    with TestClient(application, base_url="https://testserver") as production:
        response = production.post(
            "/signup",
            data={
                "username": "production",
                "display_name": "독자",
                "password": "password123",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "secure" in response.headers["set-cookie"].lower()
        assert "httponly" in response.headers["set-cookie"].lower()
        assert production.get("/app").status_code == 200
    monkeypatch.setenv("SESSION_SECRET_KEY", "short")
    with pytest.raises(RuntimeError):
        create_app()
