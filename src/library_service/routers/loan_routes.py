from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from library_service.auth.security import require_user
from library_service.core.database import get_db
from library_service.models import User
from library_service.services import library_service

router = APIRouter(prefix="/loans")


@router.post("/{loan_id}/return")
def return_loan(
    loan_id: int,
    current_user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    library_service.return_loan(db, current_user, loan_id)
    return RedirectResponse("/app?message=반납이+완료되었습니다.", status_code=303)
