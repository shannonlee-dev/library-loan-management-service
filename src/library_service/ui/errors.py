"""인증·도메인·HTTP 오류의 기존 화면 응답을 유지한다."""

from fastapi import Request
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse

from library_service.auth.security import LoginRequired
from library_service.services.library_service import LibraryError
from library_service.ui.templating import templates


def login_required_handler(request: Request, exc: LoginRequired):
    return RedirectResponse("/login", status_code=303)


def library_error_handler(request: Request, exc: LibraryError):
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "current_user": None,
            "status_code": exc.status_code,
            "message": exc.message,
        },
        status_code=exc.status_code,
    )


def http_error_handler(request: Request, exc: HTTPException):
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "current_user": None,
            "status_code": exc.status_code,
            "message": str(exc.detail),
        },
        status_code=exc.status_code,
    )
