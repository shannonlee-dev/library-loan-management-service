import hashlib
import hmac
import os

from sqlalchemy.orm import Session

from models import User
from repositories import user_repository


PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        bytes.fromhex(salt_hex),
        int(iterations),
    )
    return hmac.compare_digest(candidate.hex(), digest_hex)


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
    if len(cleaned_username) < 3:
        errors["username"] = "아이디는 3자 이상 입력하세요."
    elif user_repository.get_user_by_username(db, cleaned_username):
        errors["username"] = "이미 사용 중인 아이디입니다."
    if not cleaned_display_name:
        errors["display_name"] = "표시 이름을 입력하세요."
    if len(password) < 8:
        errors["password"] = "비밀번호는 8자 이상 입력하세요."
    if errors:
        return None, errors
    user = user_repository.create_user(
        db,
        username=cleaned_username,
        display_name=cleaned_display_name,
        password_hash=hash_password(password),
    )
    return user, {}
