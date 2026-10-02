"""대여 중복·소유권·반납 상태와 회원 데이터 계약을 검증한다."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from library_service.core.database import Base
from library_service.services import auth_service, library_service


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_registration_hash_and_duplicate_username(db):
    user, errors = auth_service.register_user(db, " reader ", "독자", "password123")
    assert errors == {} and user.username == "reader"
    assert user.password_hash != "password123"
    assert auth_service.authenticate(db, " reader ", "password123").id == user.id
    assert auth_service.authenticate(db, "reader", "wrong") is None
    duplicate, errors = auth_service.register_user(db, "reader", "독자", "password123")
    assert duplicate is None and "username" in errors


def test_loan_ownership_and_transitions(db):
    first, _ = auth_service.register_user(db, "first", "첫 사용자", "password123")
    second, _ = auth_service.register_user(db, "second", "다른 사용자", "password123")
    book = library_service.create_book(db, "도서", "저자", "설명")
    loan = library_service.borrow_book(db, first, book.id)
    with pytest.raises(library_service.LibraryError) as duplicate:
        library_service.borrow_book(db, second, book.id)
    assert duplicate.value.status_code == 400
    with pytest.raises(library_service.LibraryError) as forbidden:
        library_service.return_loan(db, second, loan.id)
    assert forbidden.value.status_code == 403
    assert library_service.return_loan(db, first, loan.id).status == "returned"
    with pytest.raises(library_service.LibraryError):
        library_service.return_loan(db, first, loan.id)
    assert library_service.borrow_book(db, second, book.id).status == "borrowed"
