from fastapi import Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from models import User
from repositories import user_repository


class LoginRequired(Exception):
    pass


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not isinstance(user_id, int):
        return None
    return user_repository.get_user(db, user_id)


def require_user(current_user: User | None = Depends(get_optional_user)) -> User:
    if current_user is None:
        raise LoginRequired
    return current_user
