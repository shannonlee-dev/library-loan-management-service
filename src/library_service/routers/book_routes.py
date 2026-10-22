from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from library_service.auth.security import require_user
from library_service.core.database import get_db
from library_service.models import User
from library_service.services import library_service

router = APIRouter(prefix="/books")


@router.post("")
def create_book(
    title: str = Form(""),
    author: str = Form(""),
    description: str = Form(""),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    library_service.create_book(db, title, author, description)
    return RedirectResponse("/app?message=새+도서를+등록했습니다.", status_code=303)


@router.post("/{book_id}/borrow")
def borrow_book(
    book_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    library_service.borrow_book(db, current_user, book_id)
    return RedirectResponse("/app?message=도서를+대여했습니다.", status_code=303)
