"""인증·세션 보호·대여와 반납의 HTTP 전체 흐름을 검증한다."""

import pytest
from sqlalchemy import select

from library_service.models import Book, Loan, User

pytestmark = pytest.mark.smoke


def test_logout_without_login_is_repeatable_and_post_only(client):
    for _ in range(2):
        response = client.post("/logout", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"].startswith("/?message=")
        assert client.get("/app", follow_redirects=False).status_code == 303
    assert client.get("/logout").status_code == 405


def test_public_pages_and_protected_access(client):
    home = client.get("/")
    assert home.status_code == 200
    assert "로그인" in home.text and "비로그인 사용자는" in home.text
    protected = client.get("/app", follow_redirects=False)
    assert protected.status_code == 303
    assert protected.headers["location"].startswith("/login")
    assert "로그인" in client.get("/app").text
    invalid = client.post("/login", data={"username": "demo", "password": "wrong"})
    assert invalid.status_code == 401
    assert "올바르지" in invalid.text


def test_signup_book_loan_return_and_logout(client, web_database):
    signup = client.post(
        "/signup",
        data={
            "username": "flowuser",
            "display_name": "흐름 사용자",
            "password": "flowpass123",
        },
    )
    assert signup.status_code == 200
    assert "흐름 사용자님 환영합니다" in signup.text
    with web_database() as db:
        user = db.scalar(select(User).where(User.username == "flowuser"))
        assert user is not None and user.password_hash != "flowpass123"

    created = client.post(
        "/app/books",
        data={
            "title": "관계 검증 도서",
            "author": "자동 테스트",
            "description": "대여 관계 출력 확인",
        },
    )
    assert created.status_code == 200
    assert "관계 검증 도서" in created.text and "대여 가능" in created.text
    with web_database() as db:
        book_id = db.scalar(select(Book.id).where(Book.title == "관계 검증 도서"))
        assert book_id is not None
    borrowed = client.post(f"/app/books/{book_id}/borrow")
    assert borrowed.status_code == 200
    assert "대여중: 흐름 사용자" in borrowed.text and "관계 검증 도서" in borrowed.text
    searched = client.get("/app", params={"q": "관계 검증"})
    assert searched.status_code == 200 and "관계 검증 도서" in searched.text
    with web_database() as db:
        loan = db.scalar(
            select(Loan).where(Loan.book_id == book_id, Loan.status == "borrowed")
        )
        assert loan is not None
        loan_id = loan.id
    returned = client.post(f"/app/loans/{loan_id}/return")
    assert returned.status_code == 200 and "반납완료" in returned.text
    filtered = client.get("/app", params={"status": "returned"})
    assert filtered.status_code == 200
    assert "관계 검증 도서" in filtered.text and "반납완료" in filtered.text
    missing = client.post("/app/books/999999/borrow")
    assert (
        missing.status_code == 404 and "요청한 도서를 찾을 수 없습니다" in missing.text
    )
    logout = client.post("/logout")
    assert logout.status_code == 200 and "로그인" in logout.text
    assert client.get("/app", follow_redirects=False).status_code == 303
