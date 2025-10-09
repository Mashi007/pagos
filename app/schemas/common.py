# app/schemas/common.py
"""Schemas comunes reutilizables"""
from pydantic import BaseModel
from typing import List, Optional, Any, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')

class MessageResponse(BaseModel):
    """Respuesta simple con mensaje"""
    success: bool
    message: str
    timestamp: datetime = datetime.utcnow()

class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta paginada genérica"""
    success: bool = True
    data: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    timestamp: datetime = datetime.utcnow()
