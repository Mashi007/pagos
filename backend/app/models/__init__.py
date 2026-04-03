from app.core.database import Base
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.ticket import Ticket
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pagos_whatsapp import PagosWhatsapp
from app.models.conversacion_cobranza import ConversacionCobranza
from app.models.pagos_informe import PagosInforme
from app.models.configuracion import Configuracion
from app.models.auditoria import Auditoria
from app.models.auditoria_cartera_revision import AuditoriaCarteraRevision
from app.models.auditoria_pago_control5_visto import AuditoriaPagoControl5Visto
from app.models.auditoria_conciliacion_manual import AuditoriaConciliacionManual
from app.models.registro_cambios import RegistroCambios
from app.models.user import User
from app.models.definicion_campo import DefinicionCampo
from app.models.conversacion_ai import ConversacionAI
from app.models.diccionario_semantico import DiccionarioSemantico
from app.models.mensaje_whatsapp import MensajeWhatsapp
from app.models.pago import Pago
from app.models.plantilla_notificacion import PlantillaNotificacion
from app.models.variable_notificacion import VariableNotificacion
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.reporte_contable_cache import ReporteContableCache
from app.models.revisar_pago import RevisarPago
from app.models.pago_con_error import PagoConError
from app.models.conciliacion_temporal import ConciliacionTemporal
from app.models.cliente_con_error import ClienteConError
from app.models.prestamo_con_error import PrestamoConError
from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem
from app.models.pago_reportado import PagoReportado, PagoReportadoHistorial
from app.models.pago_reportado_exportado import PagoReportadoExportado
from app.models.pago_pendiente_descargar import PagoPendienteDescargar
from app.models.datos_importados_conerrores import DatosImportadosConErrores
from app.models.estado_cuenta_codigo import EstadoCuentaCodigo
from app.models.cobros_publico_codigo import CobrosPublicoCodigo
from app.models.envio_notificacion import EnvioNotificacion
from app.models.envio_notificacion_adjunto import EnvioNotificacionAdjunto
from app.models.crm_campana import CampanaCrm
from app.models.crm_campana_envio import CampanaEnvioCrm
from app.models.cedula_reportar_bs import CedulaReportarBs
from app.models.tasa_cambio_diaria import TasaCambioDiaria
from app.models.analista import Analista
from app.models.finiquito import (
    FiniquitoAreaTrabajoAuditoria,
    FiniquitoCaso,
    FiniquitoEstadoHistorial,
    FiniquitoLoginCodigo,
    FiniquitoUsuarioAcceso,
)

__all__ = [
    "Base",
    "Cliente",
    "Prestamo",
    "Ticket",
    "Cuota",
    "CuotaPago",
    "Pago",
    "PagosWhatsapp",
    "PlantillaNotificacion",
    "VariableNotificacion",
    "ConversacionCobranza",
    "PagosInforme",
    "MensajeWhatsapp",
    "Configuracion",
    "Auditoria",
    "AuditoriaCarteraRevision",
    "AuditoriaPagoControl5Visto",
    "AuditoriaConciliacionManual",
    "RegistroCambios",
    "User",
    "DefinicionCampo",
    "ConversacionAI",
    "DiccionarioSemantico",
    "ModeloVehiculo",
    "ReporteContableCache",
    "RevisarPago",
    "PagoConError",
    "ClienteConError",
    "PrestamoConError",
    "ConciliacionTemporal",
    "PagoReportado",
    "PagoReportadoHistorial",
    "PagoReportadoExportado",
    "PagoPendienteDescargar",
    "DatosImportadosConErrores",
    "EstadoCuentaCodigo",
    "CobrosPublicoCodigo",
    "EnvioNotificacion",
    "EnvioNotificacionAdjunto",
    "CampanaCrm",
    "CampanaEnvioCrm",
    "CedulaReportarBs",
    "TasaCambioDiaria",
    "Analista",
    "FiniquitoAreaTrabajoAuditoria",
    "FiniquitoCaso",
    "FiniquitoEstadoHistorial",
    "FiniquitoLoginCodigo",
    "FiniquitoUsuarioAcceso",
]
