# backend/app/db/base.py
"""
Importaciones centralizadas de Base y modelos para SQLAlchemy.
Este archivo facilita las importaciones y asegura que todos los modelos
estén registrados antes de crear las tablas.
"""

# Importar Base desde session
from app.db.session import Base

# Importar settings correctamente
from app.core.config import settings

# Importar todos los modelos para que SQLAlchemy los registre
from app.models.user import User
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.notificacion import Notificacion
from app.models.auditoria import Auditoria
from app.models.aprobacion import Aprobacion

# Exportar para facilitar imports
__all__ = [
    "Base",
    "settings",
    "User",
    "Cliente", 
    "Prestamo",
    "Pago",
    "Notificacion",
    "Auditoria",
    "Aprobacion"
]
