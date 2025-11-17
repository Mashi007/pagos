# backend/app/models/__init__.py

from app.db.session import Base
from app.models.ai_prompt_variable import AIPromptVariable
from app.models.amortizacion import Cuota
from app.models.analista import Analista
from app.models.aprobacion import Aprobacion
from app.models.auditoria import Auditoria
from app.models.cliente import Cliente
from app.models.concesionario import Concesionario
from app.models.configuracion_sistema import ConfiguracionSistema
from app.models.conversacion_ai import ConversacionAI
from app.models.conversacion_whatsapp import ConversacionWhatsApp
from app.models.documento_ai import DocumentoAI
from app.models.ticket import Ticket
from app.models.documento_embedding import DocumentoEmbedding
from app.models.fine_tuning_job import FineTuningJob
from app.models.modelo_impago_cuotas import ModeloImpagoCuotas
from app.models.modelo_riesgo import ModeloRiesgo
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.notificacion import Notificacion
from app.models.notificacion_plantilla import NotificacionPlantilla
from app.models.pago import Pago
from app.models.pago_auditoria import PagoAuditoria
from app.models.prestamo import Prestamo
from app.models.prestamo_auditoria import PrestamoAuditoria
from app.models.prestamo_evaluacion import PrestamoEvaluacion
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Cliente",
    "Prestamo",
    "PrestamoAuditoria",
    "PrestamoEvaluacion",
    "Pago",
    "PagoAuditoria",
    "Cuota",
    "Aprobacion",
    "ConfiguracionSistema",
    "DocumentoAI",
    "DocumentoEmbedding",
    "FineTuningJob",
    "ModeloRiesgo",
    "ModeloImpagoCuotas",
    "AIPromptVariable",
    "ConversacionAI",
    "ConversacionWhatsApp",
    "Ticket",
    "Auditoria",
    "Notificacion",
    "NotificacionPlantilla",
    "Concesionario",
    "Analista",
    "ModeloVehiculo",
]
