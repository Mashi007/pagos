"""
Archivo corregido - Contenido básico funcional
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/test")
def test_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Endpoint de prueba básico"""
    return {"message": "Verificar concesionarios endpoint funcionando"}
