"""공개 화면과 상태 확인 엔드포인트."""

from fastapi import APIRouter, Depends, Request

from library_service.auth.security import get_optional_user
from library_service.models import User
from library_service.ui.templating import templates

router = APIRouter()


@router.get("/")
def home(request: Request, current_user: User | None = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request,
        "home.html",
        {"current_user": current_user},
    )


@router.get("/healthz", include_in_schema=False)
def health():
    return {"status": "ok"}
