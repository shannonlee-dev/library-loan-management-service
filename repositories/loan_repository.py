from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Loan


def get_loan(db: Session, loan_id: int) -> Loan | None:
    return db.get(Loan, loan_id)


def get_active_loan_for_book(db: Session, book_id: int) -> Loan | None:
    statement = select(Loan).where(Loan.book_id == book_id, Loan.status == "borrowed")
    return db.scalar(statement)


def create_loan(db: Session, user_id: int, book_id: int) -> Loan:
    loan = Loan(user_id=user_id, book_id=book_id, status="borrowed")
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def mark_returned(db: Session, loan: Loan) -> Loan:
    loan.status = "returned"
    loan.returned_at = datetime.utcnow()
    db.commit()
    db.refresh(loan)
    return loan
