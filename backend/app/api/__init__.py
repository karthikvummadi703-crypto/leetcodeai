"""
API route registration.

All routers are collected here and attached under the /api prefix
inside the application factory.
"""

from fastapi import APIRouter

from app.api.chat import router as chat_router
from app.api.user import router as user_router
from app.api.health import router as health_router

api_router = APIRouter(prefix="/api")

api_router.include_router(chat_router)
api_router.include_router(user_router)
api_router.include_router(health_router)
