"""기존 테이블과 데모 데이터를 준비한다."""

from library_service.core.database import Base, SessionLocal, engine
from library_service.models import Book
from library_service.repositories import book_repository, user_repository
from library_service.services import auth_service


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if user_repository.get_user_by_username(db, "demo") is None:
            user_repository.create_user(
                db,
                username="demo",
                display_name="데모 사용자",
                password_hash=auth_service.hash_password("demo1234"),
            )
        if db.query(Book).count() == 0:
            book_repository.create_book(
                db,
                title="FastAPI 실전 안내서",
                author="코드 도서관",
                description="인증과 SSR 흐름을 연습하기 위한 샘플 도서",
            )
            book_repository.create_book(
                db,
                title="SQLAlchemy 관계 지도",
                author="데이터 연구회",
                description="ORM 연관관계를 살펴보기 위한 샘플 도서",
            )
    finally:
        db.close()
