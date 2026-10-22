"""대시보드와 도서 대여 HTTP 요청·응답."""

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from library_service.auth.security import require_user
from library_service.core.database import get_db
from library_service.models import User
from library_service.services import library_service
from library_service.ui.templating import templates

router = APIRouter(prefix="/app")


@router.get("")
def dashboard(
    request: Request,
    q: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    availability: str | None = Query(None),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    books, user, loans = library_service.list_dashboard(
        db, current_user, q, status, availability
    )
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "current_user": user,
            "books": books,
            "loans": loans,
            "q": q or "",
            "availability": availability or "",
            "status": status or "",
            "message": request.query_params.get("message"),
        },
    )


@router.post("/books")
def create_book(
    title: str = Form(""),
    author: str = Form(""),
    description: str = Form(""),
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    library_service.create_book(db, title, author, description)
    return RedirectResponse("/app?message=새+도서를+등록했습니다.", status_code=303)


@router.post("/books/{book_id}/borrow")
def borrow_book(
    book_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    library_service.borrow_book(db, current_user, book_id)
    return RedirectResponse("/app?message=도서를+대여했습니다.", status_code=303)


@router.post("/loans/{loan_id}/return")
def return_loan(
    loan_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    library_service.return_loan(db, current_user, loan_id)
    return RedirectResponse("/app?message=반납이+완료되었습니다.", status_code=303)
