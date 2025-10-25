""""""
Archivo corregido - Contenido básico funcional
""""""

import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
    """Health check básico"""
    try:
        return {
            "status": "healthy",
            "message": "Endpoint funcionando correctamente"
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
