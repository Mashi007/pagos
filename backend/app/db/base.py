# backend/app/db/base.py
"""
Importar Base y todos los modelos para que Alembic los detecte.
Este módulo centraliza todos los modelos para las migraciones.
"""

from app.db.session import Base

# Importar todos los modelos
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.user import User
from app.models.auditoria import Auditoria
from app.models.notificacion import Notificacion
from app.models.aprobacion import Aprobacion

# Export explícito para mejor control
__all__ = [
    "Base",
    "Cliente",
    "Prestamo",
    "Pago",
    "User",
    "Auditoria",
    "Notificacion",
    "Aprobacion",
]
