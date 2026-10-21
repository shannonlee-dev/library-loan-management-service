"""Consistent browser and JSON errors without exposing internal details."""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException

from library_service.auth.security import LoginRequired
from library_service.services.library_service import LibraryError
from library_service.ui.templating import templates

logger = logging.getLogger(__name__)


def error_response(request: Request, status: int, message: str):
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            {"error": {"status": status, "message": message}}, status_code=status
        )
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "current_user": None,
            "status_code": status,
            "message": message,
        },
        status_code=status,
    )


def login_required_handler(request: Request, exc: LoginRequired):
    if "application/json" in request.headers.get("accept", ""):
        return error_response(request, 401, "로그인이 필요합니다.")
    return RedirectResponse("/login", status_code=303)


def library_error_handler(request: Request, exc: LibraryError):
    return error_response(request, exc.status_code, exc.message)


def http_error_handler(request: Request, exc: HTTPException):
    message = {
        404: "요청한 페이지를 찾을 수 없습니다.",
        405: "지원하지 않는 요청 방식입니다.",
    }.get(exc.status_code, str(exc.detail))
    response = error_response(request, exc.status_code, message)
    if exc.headers:
        response.headers.update(exc.headers)
    return response


def validation_error_handler(request: Request, exc: RequestValidationError):
    return error_response(
        request, 422, "입력 형식이 올바르지 않습니다. 입력값을 확인해 주세요."
    )


def unexpected_error_handler(request: Request, exc: Exception):
    logger.error("Unhandled application error", exc_info=exc)
    return error_response(
        request, 500, "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
    )
