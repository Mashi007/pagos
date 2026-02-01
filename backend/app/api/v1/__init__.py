"""
API v1
"""
from fastapi import APIRouter
from app.api.v1.endpoints import whatsapp

api_router = APIRouter()

# Incluir routers de endpoints
api_router.include_router(
    whatsapp.router,
    prefix="/whatsapp",
    tags=["whatsapp"]
)
