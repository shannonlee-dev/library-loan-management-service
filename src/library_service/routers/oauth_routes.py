"""GitHub Authorization Code flow with state, expiration and PKCE."""

import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from library_service.core.database import get_db
from library_service.services import oauth_service
from library_service.services.library_service import LibraryError

router = APIRouter(prefix="/auth/github")


@router.get("")
def github_login(request: Request):
    client_id, _, redirect_uri = oauth_service.settings()
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)
    request.session["oauth"] = {"state": state, "verifier": verifier, "at": time.time()}
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return RedirectResponse(
        "https://github.com/login/oauth/authorize?"
        + urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "state": state,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        ),
        status_code=303,
    )


@router.get("/callback")
async def github_callback(request: Request, db: Session = Depends(get_db)):
    pending = request.session.pop("oauth", None)
    state = request.query_params.get("state", "")
    if (
        not pending
        or not secrets.compare_digest(state, pending["state"])
        or time.time() - pending["at"] > 600
    ):
        raise LibraryError(
            "로그인 요청이 만료되었거나 유효하지 않습니다. 다시 시작해 주세요.", 400
        )
    code = request.query_params.get("code")
    if request.query_params.get("error") or not code:
        raise LibraryError(
            "GitHub 로그인이 취소되었습니다. 다시 시도할 수 있습니다.", 400
        )
    profile = await oauth_service.github_profile(code, pending["verifier"])
    user_id = oauth_service.get_or_create_user_id(db, profile)
    request.session.clear()
    request.session["user_id"] = user_id
    return RedirectResponse("/app", status_code=303)
