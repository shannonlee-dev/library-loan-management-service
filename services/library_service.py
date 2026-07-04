from sqlalchemy.orm import Session

from models import Book, Loan, User
from repositories import book_repository, loan_repository, user_repository


class LibraryError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def list_dashboard(
    db: Session,
    user: User,
    query: str | None = None,
    loan_status: str | None = None,
) -> tuple[list[Book], User, list[Loan]]:
    cleaned_query = query.strip() if query else None
    books = book_repository.list_books_with_loans(db, cleaned_query)
    user_with_loans = user_repository.get_user_with_loans(db, user.id)
    if user_with_loans is None:
        raise LibraryError("사용자 정보를 찾을 수 없습니다.", 404)
    loans = list(user_with_loans.loans)
    if loan_status in {"borrowed", "returned"}:
        loans = [loan for loan in loans if loan.status == loan_status]
    return books, user_with_loans, loans


def create_book(db: Session, title: str, author: str, description: str) -> Book:
    cleaned_title = title.strip()
    cleaned_author = author.strip()
    if not cleaned_title or not cleaned_author:
        raise LibraryError("도서 제목과 저자는 필수입니다.")
    return book_repository.create_book(
        db,
        title=cleaned_title,
        author=cleaned_author,
        description=description.strip(),
    )


def borrow_book(db: Session, user: User, book_id: int) -> Loan:
    book = book_repository.get_book_with_loans(db, book_id)
    if book is None:
        raise LibraryError("요청한 도서를 찾을 수 없습니다.", 404)
    if loan_repository.get_active_loan_for_book(db, book_id):
        raise LibraryError("이미 대여 중인 도서입니다.")
    return loan_repository.create_loan(db, user_id=user.id, book_id=book_id)


def return_loan(db: Session, user: User, loan_id: int) -> Loan:
    loan = loan_repository.get_loan(db, loan_id)
    if loan is None:
        raise LibraryError("대여 기록을 찾을 수 없습니다.", 404)
    if loan.user_id != user.id:
        raise LibraryError("본인의 대여 기록만 반납할 수 있습니다.", 403)
    if loan.status != "borrowed":
        raise LibraryError("이미 반납 완료된 도서입니다.")
    return loan_repository.mark_returned(db, loan)
