from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from models import Book, Loan


def list_books_with_loans(db: Session, query: str | None = None) -> list[Book]:
    statement = select(Book).options(
        selectinload(Book.loans).selectinload(Loan.user),
    )
    if query:
        pattern = f"%{query}%"
        statement = statement.where(
            or_(
                Book.title.like(pattern),
                Book.author.like(pattern),
                Book.description.like(pattern),
            )
        )
    return list(db.scalars(statement.order_by(Book.id.desc())).unique())


def get_book_with_loans(db: Session, book_id: int) -> Book | None:
    statement = (
        select(Book)
        .where(Book.id == book_id)
        .options(selectinload(Book.loans).selectinload(Loan.user))
    )
    return db.scalar(statement)


def create_book(db: Session, title: str, author: str, description: str) -> Book:
    book = Book(title=title, author=author, description=description)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book
