from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import Loan, User


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def get_user_with_loans(db: Session, user_id: int) -> User | None:
    statement = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.loans).selectinload(Loan.book))
    )
    return db.scalar(statement)


def create_user(db: Session, username: str, display_name: str, password_hash: str) -> User:
    user = User(username=username, display_name=display_name, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
