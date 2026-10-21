"""Reject cross-origin browser form submissions before session mutations."""

from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from library_service.ui.errors import error_response


class SameOriginMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            source = urlsplit(origin) if origin else None
            if request.headers.get("sec-fetch-site") == "cross-site" or (
                source
                and (source.scheme, source.netloc)
                != (request.url.scheme, request.url.netloc)
            ):
                return error_response(
                    request, 403, "다른 사이트에서 보낸 요청은 처리할 수 없습니다."
                )
        return await call_next(request)
