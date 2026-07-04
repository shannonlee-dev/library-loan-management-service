import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from auth.security import LoginRequired
from database import Base, SessionLocal, engine
from models import Book
from repositories import book_repository, user_repository
from routers import app_routes, auth_routes
from services import auth_service
from services.library_service import LibraryError


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if user_repository.get_user_by_username(db, "demo") is None:
            user_repository.create_user(
                db,
                username="demo",
                display_name="데모 사용자",
                password_hash=auth_service.hash_password("demo1234"),
            )
        if db.query(Book).count() == 0:
            book_repository.create_book(
                db,
                title="FastAPI 실전 안내서",
                author="코드 도서관",
                description="인증과 SSR 흐름을 연습하기 위한 샘플 도서",
            )
            book_repository.create_book(
                db,
                title="SQLAlchemy 관계 지도",
                author="데이터 연구회",
                description="ORM 연관관계를 살펴보기 위한 샘플 도서",
            )
    finally:
        db.close()


initialize_database()

app = FastAPI(title="코드 도서관")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "development-only-change-me"),
    same_site="lax",
    https_only=False,
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(auth_routes.router)
app.include_router(app_routes.router)


@app.exception_handler(LoginRequired)
def login_required_handler(request: Request, exc: LoginRequired):
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(LibraryError)
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


@app.exception_handler(HTTPException)
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
