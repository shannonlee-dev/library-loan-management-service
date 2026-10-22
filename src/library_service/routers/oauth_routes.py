"""GitHub 로그인 요청·세션·리다이렉트 처리."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from library_service.core.database import get_db
from library_service.services import oauth_service

router = APIRouter(prefix="/auth/github")


@router.get("")
def github_login(request: Request):
    authorization_url, pending = oauth_service.begin_login()
    request.session["oauth"] = pending
    return RedirectResponse(authorization_url, status_code=303)


@router.get("/callback")
async def github_callback(request: Request, db: Session = Depends(get_db)):
    # Consume once even when callback validation fails.
    pending = request.session.pop("oauth", None)
    user_id = await oauth_service.complete_login(
        db,
        pending,
        request.query_params.get("state", ""),
        request.query_params.get("code"),
        request.query_params.get("error"),
    )
    request.session.clear()
    request.session["user_id"] = user_id
    return RedirectResponse("/app", status_code=303)
