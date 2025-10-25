# backend/app/models/__init__.py
"""
Modelos de la base de datos del sistema de Préstamos y Cobranza.
"""
from app.db.session import Base
from app.models.amortizacion import Cuota
from app.models.analista import Analista
from app.models.aprobacion import Aprobacion
from app.models.auditoria import Auditoria
from app.models.cliente import Cliente
from app.models.concesionario import Concesionario
from app.models.configuracion_sistema import ConfiguracionSistema
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.notificacion import Notificacion
from app.models.pago import Pago
from app.models.prestamo import Prestamo
# Importar modelos
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Cliente",
    "Prestamo",
    "Pago",
    "Cuota",
    "Aprobacion",
    "ConfiguracionSistema",
    "Auditoria",
    "Notificacion",
    "Concesionario",
    "Analista",
    "ModeloVehiculo",
]
