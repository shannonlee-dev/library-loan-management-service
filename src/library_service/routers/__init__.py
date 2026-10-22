"""HTTP 라우터 등록을 한곳에서 관리한다."""

from fastapi import APIRouter

from library_service.routers import app_routes, auth_routes, oauth_routes, public_routes

router = APIRouter()
router.include_router(public_routes.router)
router.include_router(auth_routes.router)
router.include_router(app_routes.router)
router.include_router(oauth_routes.router)

__all__ = ["router"]
