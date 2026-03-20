# -*- coding: utf-8 -*-
"""Esquema común de respuesta JSON (status, message, data)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ResponseSchema(BaseModel):
    """Envelope estándar usado por endpoints de conciliación y similares."""

    status: str = Field(..., description="success | error")
    message: str = Field(..., description="Mensaje legible")
    data: Optional[Any] = Field(default=None, description="Cuerpo de datos")
