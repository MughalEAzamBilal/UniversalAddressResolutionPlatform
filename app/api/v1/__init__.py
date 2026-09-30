from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.addresses import router as address_router
from app.api.v1.resolve import router as resolve_router
from app.api.v1.admin import router as admin_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(address_router)
api_v1_router.include_router(resolve_router)
api_v1_router.include_router(admin_router)
