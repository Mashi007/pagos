"""
Codigo temporal (OTP por correo) para el formulario publico de reporte de pago (rapicredit-cobros).
Flujo: cedula + correo registrado -> envio de codigo -> verificacion -> JWT de sesion corta (cobros_public).
"""
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.core.database import Base


class CobrosPublicoCodigo(Base):
    __tablename__ = "cobros_publico_codigos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cedula_normalizada = Column(String(20), nullable=False, index=True)
    email = Column(String(100), nullable=False)
    codigo = Column(String(10), nullable=False)
    expira_en = Column(DateTime(timezone=False), nullable=False)
    usado = Column(Boolean, nullable=False, default=False)
    creado_en = Column(DateTime(timezone=False), nullable=False)
