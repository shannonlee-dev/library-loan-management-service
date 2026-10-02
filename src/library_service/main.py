"""서비스 조립과 ASGI 진입점."""

import os

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from library_service.auth.security import LoginRequired
from library_service.bootstrap import initialize_database
from library_service.core.paths import STATIC_DIR
from library_service.routers import app_routes, auth_routes
from library_service.services.library_service import LibraryError
from library_service.ui.errors import (
    http_error_handler,
    library_error_handler,
    login_required_handler,
)


def create_app() -> FastAPI:
    """기존 초기화 순서·라우터·세션 정책으로 앱을 만든다."""
    initialize_database()
    application = FastAPI(title="코드 도서관")
    application.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SESSION_SECRET_KEY", "development-only-change-me"),
        same_site="lax",
        https_only=False,
    )
    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    application.include_router(auth_routes.router)
    application.include_router(app_routes.router)
    application.add_exception_handler(LoginRequired, login_required_handler)
    application.add_exception_handler(LibraryError, library_error_handler)
    application.add_exception_handler(HTTPException, http_error_handler)
    return application


app = create_app()
