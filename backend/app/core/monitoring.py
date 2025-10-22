# backend/app/core/monitoring.py
"""
Configuración de Monitoreo y Observabilidad
Integración con Sentry, Prometheus y logging estructurado
"""
import logging
from typing import Optional
from datetime import datetime

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastAPIIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from pythonjsonlogger import jsonlogger

from app.core.config import settings


def configure_sentry(app: FastAPI) -> None:
    """
    Configura Sentry para tracking de errores
    
    Args:
        app: Instancia de FastAPI
    """
    if not settings.SENTRY_DSN:
        logging.warning("SENTRY_DSN no configurado - Sentry deshabilitado")
        return
    
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        integrations=[
            FastAPIIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        # Configuración adicional
        before_send=before_send_sentry,
        send_default_pii=False,  # No enviar PII por defecto
        attach_stacktrace=True,
        max_breadcrumbs=50,
    )
    
    logging.info(f"Sentry configurado - Environment: {settings.ENVIRONMENT}")


def before_send_sentry(event, hint):
    """
    Hook para modificar eventos antes de enviar a Sentry
    Útil para filtrar información sensible
    """
    # Filtrar información sensible
    if "request" in event:
        if "headers" in event["request"]:
            # Remover headers sensibles
            sensitive_headers = ["authorization", "cookie", "x-api-key"]
            for header in sensitive_headers:
                if header in event["request"]["headers"]:
                    event["request"]["headers"][header] = "[FILTERED]"
    
    return event


def configure_prometheus(app: FastAPI) -> Optional[Instrumentator]:
    """
    Configura Prometheus para métricas
    
    Args:
        app: Instancia de FastAPI
        
    Returns:
        Instrumentator configurado o None
    """
    if not settings.PROMETHEUS_ENABLED:
        logging.warning("PROMETHEUS_ENABLED=False - Prometheus deshabilitado")
        return None
    
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/metrics"],
        env_var_name="ENABLE_METRICS",
        inprogress_name="fastapi_inprogress",
        inprogress_labels=True,
    )
    
    # Configurar métricas adicionales
    instrumentator.add(
        # Duración de requests por endpoint
        instrumentator.metrics.latency(
            buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
        )
    )
    
    instrumentator.add(
        # Tamaño de requests/responses
        instrumentator.metrics.requests()
    )
    
    # Instrumentar la app
    instrumentator.instrument(app)
    
    # Exponer endpoint /metrics
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)
    
    logging.info("Prometheus configurado - Métricas en /metrics")
    
    return instrumentator


def configure_structured_logging() -> None:
    """
    Configura logging estructurado en formato JSON
    """
    log_level = settings.LOG_LEVEL.upper()
    
    # Configurar formato JSON
    log_handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "pathname": "file",
            "lineno": "line",
        }
    )
    log_handler.setFormatter(formatter)
    
    # Configurar logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = []
    root_logger.addHandler(log_handler)
    
    # Configurar loggers específicos
    loggers_to_configure = [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "sqlalchemy.engine",
        "app",
    ]
    
    for logger_name in loggers_to_configure:
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger.handlers = []
        logger.addHandler(log_handler)
        logger.propagate = False
    
    logging.info(f"Logging estructurado configurado - Level: {log_level}")


def setup_monitoring(app: FastAPI) -> dict:
    """
    Configura todo el sistema de monitoreo
    
    Args:
        app: Instancia de FastAPI
        
    Returns:
        dict con configuración aplicada
    """
    config_applied = {
        "sentry": False,
        "prometheus": False,
        "structured_logging": False,
    }
    
    try:
        # Logging estructurado
        configure_structured_logging()
        config_applied["structured_logging"] = True
        
        # Sentry
        if settings.SENTRY_DSN:
            configure_sentry(app)
            config_applied["sentry"] = True
        
        # Prometheus
        if settings.PROMETHEUS_ENABLED:
            instrumentator = configure_prometheus(app)
            if instrumentator:
                config_applied["prometheus"] = True
        
        logging.info("Sistema de monitoreo configurado exitosamente")
        logging.info(f"Configuración aplicada: {config_applied}")
        
    except Exception as e:
        logging.error(f"Error configurando monitoreo: {str(e)}")
        # No fallar si el monitoreo falla
        pass
    
    return config_applied


# ============================================
# MÉTRICAS PERSONALIZADAS DE FINANCIAMIENTO AUTOMOTRIZ
# ============================================

def track_business_metrics(
    metric_name: str,
    value: float,
    labels: Optional[dict] = None
) -> None:
    """
    Registra métricas de negocio personalizadas para financiamiento automotriz
    
    Args:
        metric_name: Nombre de la métrica
        value: Valor de la métrica
        labels: Labels adicionales
        
    Examples:
        track_business_metrics("clientes_creados", 1, {"analista": "Juan", "concesionario": "AutoCenter"})
        track_business_metrics("pagos_procesados", monto, {"estado": "EXITOSO", "metodo": "TRANSFERENCIA"})
        track_business_metrics("mora_acumulada", dias_mora, {"cliente_id": 123})
        track_business_metrics("conciliacion_exitosa", 1, {"banco": "Popular", "registros": 50})
    """
    try:
        # Log estructurado para métricas de negocio
        logging.info(
            f"BUSINESS_METRIC: {metric_name}",
            extra={
                "metric_name": metric_name,
                "metric_value": value,
                "labels": labels or {},
                "timestamp": datetime.now().isoformat(),
                "system": "financiamiento_automotriz"
            }
        )
        
        # Si Prometheus está habilitado, registrar métrica
        if settings.PROMETHEUS_ENABLED:
            # Implementar contadores específicos del negocio
            pass
            
    except Exception as e:
        logging.error(f"Error registrando métrica de negocio: {e}")


def track_financial_operation(
    operation_type: str,
    amount: float,
    client_id: int,
    user_id: int,
    additional_data: Optional[dict] = None
) -> None:
    """
    Trackear operaciones financieras específicas
    
    Args:
        operation_type: PAGO, PRESTAMO, ANULACION, MODIFICACION
        amount: Monto de la operación
        client_id: ID del cliente
        user_id: ID del usuario que ejecuta
        additional_data: Datos adicionales
    """
    track_business_metrics(
        f"financial_operation_{operation_type.lower()}",
        amount,
        {
            "operation_type": operation_type,
            "client_id": client_id,
            "user_id": user_id,
            **(additional_data or {})
        }
    )


def track_approval_workflow(
    workflow_step: str,
    request_type: str,
    user_role: str,
    processing_time_seconds: Optional[float] = None
) -> None:
    """
    Trackear flujo de aprobaciones
    
    Args:
        workflow_step: SOLICITUD, APROBACION, RECHAZO, EJECUCION
        request_type: MODIFICAR_PAGO, ANULAR_PAGO, EDITAR_CLIENTE
        user_role: Rol del usuario
        processing_time_seconds: Tiempo de procesamiento
    """
    track_business_metrics(
        f"approval_workflow_{workflow_step.lower()}",
        processing_time_seconds or 1,
        {
            "workflow_step": workflow_step,
            "request_type": request_type,
            "user_role": user_role
        }
    )


def track_bulk_migration(
    total_records: int,
    successful: int,
    failed: int,
    warnings: int,
    migration_type: str
) -> None:
    """
    Trackear migraciones masivas
    """
    track_business_metrics("bulk_migration_total", total_records, {"type": migration_type})
    track_business_metrics("bulk_migration_successful", successful, {"type": migration_type})
    track_business_metrics("bulk_migration_failed", failed, {"type": migration_type})
    track_business_metrics("bulk_migration_warnings", warnings, {"type": migration_type})


# Context managers para tracking
class track_operation:
    """
    Context manager para trackear operaciones
    
    Example:
        with track_operation("crear_prestamo", cliente_id=123):
            # código
            pass
    """
    def __init__(self, operation_name: str, **kwargs):
        self.operation_name = operation_name
        self.context = kwargs
    
    def __enter__(self):
        logging.info(f"Iniciando operación: {self.operation_name}", extra=self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logging.error(
                f"Error en operación: {self.operation_name}",
                extra={**self.context, "error": str(exc_val)},
                exc_info=True
            )
        else:
            logging.info(f"Operación completada: {self.operation_name}", extra=self.context)


# ============================================
# ENDPOINT DE VERIFICACIÓN DE MONITOREO
# ============================================

def get_monitoring_status() -> dict:
    """
    Obtener estado actual del sistema de monitoreo
    """
    return {
        "titulo": "🔍 ESTADO DEL SISTEMA DE MONITOREO",
        "fecha_verificacion": datetime.now().isoformat(),
        
        "servicios_monitoreo": {
            "sentry": {
                "habilitado": bool(getattr(settings, 'SENTRY_DSN', None)),
                "dsn_configurado": bool(getattr(settings, 'SENTRY_DSN', None)),
                "environment": getattr(settings, 'ENVIRONMENT', 'production'),
                "traces_sample_rate": getattr(settings, 'SENTRY_TRACES_SAMPLE_RATE', 0.1),
                "descripcion": "Tracking de errores y performance"
            },
            "prometheus": {
                "habilitado": getattr(settings, 'PROMETHEUS_ENABLED', False),
                "endpoint": "/metrics",
                "descripcion": "Métricas de aplicación y negocio"
            },
            "logging_estructurado": {
                "habilitado": True,
                "formato": "JSON",
                "nivel": getattr(settings, 'LOG_LEVEL', 'INFO'),
                "descripcion": "Logs estructurados para análisis"
            }
        },
        
        "metricas_negocio_disponibles": {
            "financieras": [
                "clientes_creados",
                "pagos_procesados", 
                "prestamos_aprobados",
                "mora_acumulada",
                "conciliacion_exitosa"
            ],
            "operacionales": [
                "approval_workflow_solicitud",
                "approval_workflow_aprobacion",
                "bulk_migration_total",
                "financial_operation_pago"
            ],
            "rendimiento": [
                "http_requests_total",
                "http_request_duration_seconds",
                "database_connections"
            ]
        },
        
        "integracion_actual": {
            "main_py": "❌ No integrado",
            "endpoints": "❌ No utilizado",
            "recomendacion": "Integrar en main.py para habilitar monitoreo completo"
        },
        
        "beneficios_implementacion": [
            "🔍 Tracking automático de errores con Sentry",
            "📊 Métricas de performance con Prometheus",
            "📋 Logs estructurados para análisis",
            "⚡ Alertas automáticas de problemas",
            "📈 Métricas de negocio específicas",
            "🔧 Debugging mejorado en producción"
        ],
        
        "pasos_integracion": [
            "1. Agregar variables de entorno (SENTRY_DSN, etc.)",
            "2. Importar setup_monitoring en main.py",
            "3. Llamar setup_monitoring(app) al inicio",
            "4. Usar track_operation en endpoints críticos",
            "5. Configurar alertas en Sentry/Prometheus"
        ],
        
        "utilidad_para_financiamiento": {
            "alta": "✅ Muy útil para sistema empresarial",
            "razones": [
                "Tracking de operaciones financieras críticas",
                "Monitoreo de flujos de aprobación",
                "Alertas de errores en pagos/conciliación",
                "Métricas de rendimiento de analistaes",
                "Análisis de patrones de mora",
                "Debugging de migraciones masivas"
            ]
        }
    }
