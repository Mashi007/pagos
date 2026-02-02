"""
Models Module. Export Base y modelos para que Base.metadata conozca las tablas.
"""
from app.core.database import Base
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.ticket import Ticket
from app.models.cuota import Cuota
from app.models.pagos_whatsapp import PagosWhatsapp
from app.models.conversacion_cobranza import ConversacionCobranza
from app.models.pagos_informe import PagosInforme
from app.models.configuracion import Configuracion
from app.models.auditoria import Auditoria
from app.models.user import User
from app.models.definicion_campo import DefinicionCampo
from app.models.conversacion_ai import ConversacionAI
from app.models.diccionario_semantico import DiccionarioSemantico

__all__ = [
    "Base", "Cliente", "Prestamo", "Ticket", "Cuota", "PagosWhatsapp",
    "ConversacionCobranza", "PagosInforme",
    "Configuracion", "Auditoria", "User", "DefinicionCampo", "ConversacionAI", "DiccionarioSemantico",
]

