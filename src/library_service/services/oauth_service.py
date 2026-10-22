"""GitHub 인증 제공자 통신과 외부 계정 조회·생성."""

import base64
import hashlib
import os
import secrets
import time
from urllib.parse import urlencode

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from library_service.models import User
from library_service.models.entities import OAuthIdentity
from library_service.services.library_service import LibraryError


def settings() -> tuple[str, str, str]:
    values = tuple(
        os.getenv(key, "")
        for key in ("GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "GITHUB_REDIRECT_URI")
    )
    if not all(values):
        raise LibraryError(
            "GitHub 로그인이 아직 설정되지 않았습니다. 일반 로그인을 이용해 주세요.",
            503,
        )
    return values


async def github_profile(code: str, verifier: str) -> dict:
    client_id, client_secret, redirect_uri = settings()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                    "code_verifier": verifier,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            token = response.json().get("access_token")
            if not isinstance(token, str) or not token:
                raise ValueError("missing token")
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            profile = response.json()
            if not isinstance(profile.get("id"), int) or not profile.get("login"):
                raise ValueError("invalid identity")
            return profile
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        raise LibraryError(
            "GitHub 인증을 완료하지 못했습니다. 잠시 후 다시 로그인해 주세요.", 502
        ) from exc


def get_or_create_user_id(db: Session, profile: dict) -> int:
    identity_key = ("github", str(profile["id"]))
    identity = db.get(OAuthIdentity, identity_key)
    if identity is None:
        # Never link accounts by public login or email; only a verified provider ID.
        user = User(
            username="github:" + secrets.token_hex(16),
            display_name=str(profile.get("name") or profile["login"])[:80],
            password_hash="!",
        )
        identity = OAuthIdentity(provider="github", subject=identity_key[1], user=user)
        db.add(identity)
        try:
            db.flush()
            user_id = identity.user_id
            db.commit()
        except IntegrityError:
            db.rollback()
            identity = db.get(OAuthIdentity, identity_key)
            if identity is None:
                raise LibraryError(
                    "계정을 생성하지 못했습니다. 다시 시도해 주세요.", 409
                )
        except Exception:
            db.rollback()
            raise
        else:
            return user_id
    return identity.user_id


def begin_login() -> tuple[str, dict]:
    """인증 URL과 세션에 보관할 일회성 검증 정보를 생성한다."""
    client_id, _, redirect_uri = settings()
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)
    pending = {"state": state, "verifier": verifier, "at": time.time()}
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    authorization_url = "https://github.com/login/oauth/authorize?" + urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return authorization_url, pending


async def complete_login(
    db: Session,
    pending: dict | None,
    state: str,
    code: str | None,
    error: str | None,
) -> int:
    """콜백을 검증하고 인증된 외부 계정의 사용자 ID를 반환한다."""
    if (
        not pending
        or not secrets.compare_digest(state, pending["state"])
        or time.time() - pending["at"] > 600
    ):
        raise LibraryError(
            "로그인 요청이 만료되었거나 유효하지 않습니다. 다시 시작해 주세요.", 400
        )
    if error or not code:
        raise LibraryError(
            "GitHub 로그인이 취소되었습니다. 다시 시도할 수 있습니다.", 400
        )
    profile = await github_profile(code, pending["verifier"])
    return get_or_create_user_id(db, profile)
