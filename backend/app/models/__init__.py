# backend/app/models/__init__.py
"""
Modelos de la base de datos del sistema de Préstamos y Cobranza.
IMPORTANTE: Importar todos los modelos aquí para que:
1. Alembic los detecte al generar migraciones
2. SQLAlchemy los registre en metadata
3. init_db.py pueda crear todas las tablas
"""

# Importar TODOS los modelos existentes
from app.models.user import User
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.amortizacion import Cuota
from app.models.aprobacion import Aprobacion
from app.models.auditoria import Auditoria
from app.models.notificacion import Notificacion

# Exportar todos para fácil importación
__all__ = [
    "User",
    "Cliente",
    "Prestamo",
    "Pago",
    "Cuota",
    "Aprobacion",
    "Auditoria",
    "Notificacion",
]
