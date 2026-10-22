"""저장소 조합과 서비스 실패가 부분 저장을 남기지 않는지 검증한다."""

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from library_service import bootstrap
from library_service.core.database import Base
from library_service.models import Book, Loan, User
from library_service.models.entities import OAuthIdentity
from library_service.repositories import (
    book_repository,
    loan_repository,
    user_repository,
)
from library_service.services import auth_service, library_service, oauth_service


@pytest.fixture
def sessions(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'transactions.db'}")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    engine.dispose()


def test_repository_writes_can_be_rolled_back_as_one_work_unit(sessions):
    with sessions() as db:
        user = user_repository.create_user(db, "reader", "독자", "!")
        book = book_repository.create_book(db, "도서", "저자", "")
        loan = loan_repository.create_loan(db, user.id, book.id)
        loan_repository.mark_returned(db, loan)
        assert loan.id is not None and loan.status == "returned"
        db.rollback()
    with sessions() as observer:
        for model in (User, Book, Loan):
            assert list(observer.scalars(select(model))) == []


@pytest.mark.parametrize("operation", ["signup", "book", "borrow", "return", "oauth"])
def test_service_commit_failure_rolls_back_and_session_is_reusable(sessions, operation):
    with sessions() as db:
        user, _ = auth_service.register_user(
            db, "reader", "독자", "password123", "password123"
        )
        book = library_service.create_book(db, "기존 도서", "저자", "")
        loan = (
            library_service.borrow_book(db, user, book.id)
            if operation == "return"
            else None
        )
        user_id, book_id = user.id, book.id
        loan_id = loan.id if loan else None

        def fail_commit(session):
            # Exercise a failure after SQL has been sent, before committing it.
            session.flush()
            raise RuntimeError("simulated commit failure")

        event.listen(db, "before_commit", fail_commit)
        try:
            with pytest.raises(RuntimeError, match="simulated commit failure"):
                if operation == "signup":
                    auth_service.register_user(
                        db, "newreader", "신규", "password123", "password123"
                    )
                elif operation == "book":
                    library_service.create_book(db, "신규 도서", "저자", "")
                elif operation == "borrow":
                    library_service.borrow_book(db, user, book_id)
                elif operation == "return":
                    library_service.return_loan(db, user, loan_id)
                else:
                    oauth_service.get_or_create_user_id(
                        db, {"id": 123, "login": "reader"}
                    )
        finally:
            event.remove(db, "before_commit", fail_commit)

        assert not db.in_transaction()
        # A later successful operation must not accidentally persist failed work.
        library_service.create_book(db, "재시도 도서", "저자", "")
    with sessions() as observer:
        assert [u.id for u in observer.scalars(select(User))] == [user_id]
        assert set(observer.scalars(select(Book.title))) == {"기존 도서", "재시도 도서"}
        assert list(observer.scalars(select(OAuthIdentity))) == []
        loans = list(observer.scalars(select(Loan)))
        if operation == "return":
            assert len(loans) == 1 and loans[0].id == loan_id
            assert loans[0].status == "borrowed" and loans[0].returned_at is None
        else:
            assert loans == []


def test_bootstrap_failure_does_not_leave_partial_seed(sessions, monkeypatch):
    monkeypatch.setenv("LIBRARY_ENV", "development")
    monkeypatch.setattr(bootstrap, "SessionLocal", sessions)
    with sessions() as db:
        monkeypatch.setattr(bootstrap, "engine", db.get_bind())
    original = book_repository.create_book

    def fail_second_book(db, title, author, description):
        book = original(db, title, author, description)
        if title == "SQLAlchemy 관계 지도":
            raise RuntimeError("second seed failed")
        return book

    monkeypatch.setattr(book_repository, "create_book", fail_second_book)
    with pytest.raises(RuntimeError, match="second seed failed"):
        bootstrap.initialize_database()
    with sessions() as observer:
        assert list(observer.scalars(select(User))) == []
        assert list(observer.scalars(select(Book))) == []
    monkeypatch.setattr(book_repository, "create_book", original)
    bootstrap.initialize_database()
    bootstrap.initialize_database()
    with sessions() as observer:
        assert len(list(observer.scalars(select(User)))) == 1
        assert len(list(observer.scalars(select(Book)))) == 2
