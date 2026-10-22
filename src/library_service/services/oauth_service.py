"""GitHub 인증 제공자 통신과 외부 계정 조회·생성."""

import os
import secrets

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
            db.commit()
        except IntegrityError:
            db.rollback()
            identity = db.get(OAuthIdentity, identity_key)
            if identity is None:
                raise LibraryError(
                    "계정을 생성하지 못했습니다. 다시 시도해 주세요.", 409
                )
    return identity.user_id
