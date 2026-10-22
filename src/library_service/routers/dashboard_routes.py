from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from library_service.auth.security import require_user
from library_service.core.database import get_db
from library_service.models import User
from library_service.services import library_service
from library_service.ui.templating import templates

router = APIRouter()


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
            "loans": sorted(loans, key=lambda loan: loan.id, reverse=True),
            "q": q or "",
            "availability": availability or "",
            "status": status or "",
            "message": request.query_params.get("message"),
        },
    )
