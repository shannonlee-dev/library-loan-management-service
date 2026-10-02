from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from library_service.auth.security import get_optional_user
from library_service.core.database import get_db
from library_service.models import User
from library_service.services import auth_service
from library_service.ui.templating import templates

router = APIRouter()


@router.get("/")
def home(request: Request, current_user: User | None = Depends(get_optional_user)):
    return templates.TemplateResponse(
        request,
        "home.html",
        {"current_user": current_user},
    )


@router.get("/login")
def login_form(
    request: Request, current_user: User | None = Depends(get_optional_user)
):
    if current_user:
        return RedirectResponse("/app", status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"current_user": None, "error": None},
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    user = auth_service.authenticate(db, username, password)
    if user is None:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "current_user": None,
                "error": "아이디 또는 비밀번호가 올바르지 않습니다.",
                "username": username,
            },
            status_code=401,
        )
    request.session["user_id"] = user.id
    return RedirectResponse("/app?message=로그인에+성공했습니다.", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/?message=로그아웃되었습니다.", status_code=303)


@router.get("/signup")
def signup_form(
    request: Request, current_user: User | None = Depends(get_optional_user)
):
    if current_user:
        return RedirectResponse("/app", status_code=303)
    return templates.TemplateResponse(
        request,
        "signup.html",
        {"current_user": None, "errors": {}, "form": {}},
    )


@router.post("/signup")
def signup(
    request: Request,
    username: str = Form(""),
    display_name: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    user, errors = auth_service.register_user(db, username, display_name, password)
    if errors:
        return templates.TemplateResponse(
            request,
            "signup.html",
            {
                "current_user": None,
                "errors": errors,
                "form": {"username": username, "display_name": display_name},
            },
            status_code=400,
        )
    request.session["user_id"] = user.id
    return RedirectResponse("/app?message=회원가입에+성공했습니다.", status_code=303)
