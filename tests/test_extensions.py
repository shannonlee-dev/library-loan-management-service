"""Error contracts, bcrypt compatibility, filters and OAuth security boundaries."""


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
