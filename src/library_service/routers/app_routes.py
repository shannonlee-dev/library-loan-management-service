"""로그인 후 사용하는 /app 라우터 조립."""

from fastapi import APIRouter

from library_service.routers import book_routes, dashboard_routes, loan_routes

router = APIRouter()
router.include_router(dashboard_routes.router, prefix="/app")
router.include_router(book_routes.router, prefix="/app")
router.include_router(loan_routes.router, prefix="/app")
