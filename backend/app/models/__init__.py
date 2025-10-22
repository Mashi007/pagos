# backend/app/models/__init__.py
""
Modelos de la base de datos del sistema de Préstamos y Cobranza.
""
from app.db.session import Base

# Importar modelos

from app.models.amortizacion import Cuota

from app.models.configuracion_sistema import ConfiguracionSistema

from app.models.concesionario import Concesionario
from app.models.analista import Analista
from app.models.modelo_vehiculo import ModeloVehiculo

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

