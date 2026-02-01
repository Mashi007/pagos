"""
API v1
"""
from fastapi import APIRouter
from app.api.v1.endpoints import whatsapp, auth

api_router = APIRouter()

# Autenticación (login, refresh, me)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["auth"],
)

# WhatsApp
api_router.include_router(
    whatsapp.router,
    prefix="/whatsapp",
    tags=["whatsapp"],
)
