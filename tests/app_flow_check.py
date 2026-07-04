from __future__ import annotations

import http.cookiejar
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import uvicorn
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import SessionLocal
from main import app
from models import Book, Loan, User


def choose_port() -> int:
    if os.getenv("APP_FLOW_PORT"):
        return int(os.environ["APP_FLOW_PORT"])
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


PORT = choose_port()
BASE_URL = f"http://127.0.0.1:{PORT}"


def assert_contains(text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError(f"expected {expected!r} in response")


def request(
    opener: urllib.request.OpenerDirector,
    path: str,
    method: str = "GET",
    data: dict[str, str] | None = None,
):
    encoded = None
    headers = {}
    if data is not None:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(f"{BASE_URL}{path}", data=encoded, headers=headers, method=method)
    try:
        with opener.open(req, timeout=5) as response:
            return response.status, response.read().decode("utf-8"), response.headers
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8"), exc.headers


def wait_for_server(opener: urllib.request.OpenerDirector) -> None:
    for _ in range(30):
        try:
            status, _, _ = request(opener, "/")
            if status == 200:
                return
        except OSError:
            pass
        time.sleep(0.2)
    raise RuntimeError("server did not become ready")


config = uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")
server = uvicorn.Server(config)
thread = threading.Thread(target=server.run, daemon=True)
thread.start()

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

try:
    wait_for_server(opener)

    status, body, _ = request(opener, "/")
    assert status == 200
    assert_contains(body, "로그인")
    assert_contains(body, "비로그인 사용자는")

    status, body, _ = request(opener, "/app")
    assert status == 200
    assert_contains(body, "로그인")

    status, body, _ = request(
        opener,
        "/login",
        method="POST",
        data={"username": "demo", "password": "wrong"},
    )
    assert status == 401
    assert_contains(body, "올바르지")

    status, body, _ = request(
        opener,
        "/signup",
        method="POST",
        data={"username": "flowuser", "display_name": "흐름 사용자", "password": "flowpass123"},
    )
    assert status == 200
    assert_contains(body, "흐름 사용자님 환영합니다")

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == "flowuser"))
        if user is None or user.password_hash == "flowpass123":
            raise AssertionError("signup password was not stored as a hash")
    finally:
        db.close()

    status, body, _ = request(
        opener,
        "/app/books",
        method="POST",
        data={"title": "관계 검증 도서", "author": "자동 테스트", "description": "대여 관계 출력 확인"},
    )
    assert status == 200
    assert_contains(body, "관계 검증 도서")
    assert_contains(body, "대여 가능")

    db = SessionLocal()
    try:
        book_id = db.scalar(select(Book.id).where(Book.title == "관계 검증 도서").order_by(Book.id.desc()))
    finally:
        db.close()
    if book_id is None:
        raise AssertionError("created book was not stored")

    status, body, _ = request(opener, f"/app/books/{book_id}/borrow", method="POST")
    assert status == 200
    assert_contains(body, "대여중: 흐름 사용자")
    assert_contains(body, "관계 검증 도서")

    status, body, _ = request(opener, "/app?" + urllib.parse.urlencode({"q": "관계 검증"}))
    assert status == 200
    assert_contains(body, "관계 검증 도서")

    db = SessionLocal()
    try:
        loan = db.scalar(
            select(Loan)
            .where(Loan.book_id == book_id, Loan.status == "borrowed")
            .order_by(Loan.id.desc())
        )
    finally:
        db.close()
    if loan is None:
        raise AssertionError("borrowed loan was not stored")

    status, body, _ = request(opener, f"/app/loans/{loan.id}/return", method="POST")
    assert status == 200
    assert_contains(body, "반납완료")

    status, body, _ = request(opener, "/app?status=returned")
    assert status == 200
    assert_contains(body, "관계 검증 도서")
    assert_contains(body, "반납완료")

    status, body, _ = request(opener, "/app/books/999999/borrow", method="POST")
    assert status == 404
    assert_contains(body, "요청한 도서를 찾을 수 없습니다")

    status, body, _ = request(opener, "/logout", method="POST")
    assert status == 200
    assert_contains(body, "로그인")

    print(
        "PASS app flow: auth, protected access, signup hash, DB relationships, "
        "book creation, borrow/return status transition, search/filter, and error handling"
    )
finally:
    server.should_exit = True
    thread.join(timeout=5)
