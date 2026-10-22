from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from library_service.models import Book, Loan


def list_books_with_loans(
    db: Session, query: str | None = None, availability: str | None = None
) -> list[Book]:
    statement = select(Book).options(
        selectinload(Book.loans).selectinload(Loan.user),
    )
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        statement = statement.where(
            or_(
                Book.title.ilike(pattern, escape="\\"),
                Book.author.ilike(pattern, escape="\\"),
                Book.description.ilike(pattern, escape="\\"),
            )
        )
    active = Book.loans.any(Loan.status == "borrowed")
    if availability == "available":
        statement = statement.where(~active)
    elif availability == "borrowed":
        statement = statement.where(active)
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
    db.flush()
    return book
