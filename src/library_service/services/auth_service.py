import hashlib
import hmac
import re

import bcrypt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from library_service.models import User
from library_service.repositories import user_repository

PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        if encoded.startswith(("$2b$", "$2a$", "$2y$")):
            return bcrypt.checkpw(password.encode(), encoded.encode())
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, TypeError, OverflowError):
        return False


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = user_repository.get_user_by_username(db, username.strip())
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def register_user(
    db: Session,
    username: str,
    display_name: str,
    password: str,
) -> tuple[User | None, dict[str, str]]:
    errors: dict[str, str] = {}
    cleaned_username = username.strip()
    cleaned_display_name = display_name.strip()
    if not re.fullmatch(r"[a-zA-Z0-9_-]{3,50}", cleaned_username):
        errors["username"] = "아이디는 영문, 숫자, 밑줄, 하이픈으로 3~50자 입력하세요."
    elif user_repository.get_user_by_username(db, cleaned_username):
        errors["username"] = "이미 사용 중인 아이디입니다."
    if not 1 <= len(cleaned_display_name) <= 80:
        errors["display_name"] = "표시 이름을 1~80자로 입력하세요."
    if len(password) < 8 or len(password.encode()) > 72:
        errors["password"] = (
            "비밀번호는 8자 이상, UTF-8 기준 72바이트 이내로 입력하세요."
        )
    if errors:
        return None, errors
    try:
        user = user_repository.create_user(
            db,
            username=cleaned_username,
            display_name=cleaned_display_name,
            password_hash=hash_password(password),
        )
    except IntegrityError:
        db.rollback()
        return None, {"username": "이미 사용 중인 아이디입니다."}
    return user, {}
