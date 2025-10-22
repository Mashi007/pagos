# backend/app/models/modelo_vehiculo.py
""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, relationship
from sqlalchemy import ForeignKey, Text, Numeric, JSON, Boolean, Enum
from fastapi import APIRouter, Depends, HTTPException, Query, status
Modelo SQLAlchemy para modelos de vehículos configurables
""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class ModeloVehiculo(Base):
    __tablename__ = "modelos_vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    modelo = Column(String(100), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<ModeloVehiculo(id={self.id}, modelo='{self.modelo}', activo={self.activo})>"

    def to_dict(self):
        return {
            "id": self.id,
            "modelo": self.modelo,
            "activo": self.activo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
