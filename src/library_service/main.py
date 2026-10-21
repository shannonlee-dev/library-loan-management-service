"""서비스 조립과 ASGI 진입점."""

import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.middleware.sessions import SessionMiddleware

from library_service.auth.middleware import SameOriginMiddleware
from library_service.auth.security import LoginRequired
from library_service.bootstrap import initialize_database
from library_service.core.paths import STATIC_DIR
from library_service.routers import app_routes, auth_routes, oauth_routes
from library_service.services.library_service import LibraryError
from library_service.ui.errors import (
    http_error_handler,
    library_error_handler,
    login_required_handler,
    unexpected_error_handler,
    validation_error_handler,
)


def create_app() -> FastAPI:
    """기존 초기화 순서·라우터·세션 정책으로 앱을 만든다."""
    production = os.getenv("LIBRARY_ENV") == "production"
    secret = os.getenv("SESSION_SECRET_KEY", "development-only-change-me")
    if production and (
        len(secret) < 32
        or secret
        in {"development-only-change-me", "replace-with-your-own-random-secret"}
    ):
        raise RuntimeError(
            "Production requires a random SESSION_SECRET_KEY of at least 32 characters"
        )
    initialize_database()
    application = FastAPI(
        title="코드 도서관", debug=os.getenv("LIBRARY_ENV") == "development"
    )
    application.add_middleware(
        SessionMiddleware,
        secret_key=secret,
        same_site="lax",
        https_only=production,
        max_age=60 * 60 * 12,
    )
    application.add_middleware(SameOriginMiddleware)
    application.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    if application.debug:
        application.mount(
            "/_dev",
            StaticFiles(directory=str(STATIC_DIR.parent / "dev")),
            name="dev_tools",
        )
    application.include_router(auth_routes.router)
    application.include_router(app_routes.router)
    application.include_router(oauth_routes.router)
    application.add_exception_handler(LoginRequired, login_required_handler)
    application.add_exception_handler(LibraryError, library_error_handler)
    application.add_exception_handler(HTTPException, http_error_handler)
    application.exception_handler(RequestValidationError)(validation_error_handler)
    application.exception_handler(Exception)(unexpected_error_handler)

    @application.get("/healthz", include_in_schema=False)
    def health():
        return {"status": "ok"}

    return application


app = create_app()
