# backend/app/core/monitoring.py"""Configuración de Monitoreo y ObservabilidadIntegración con Sentry, Prometheus y logging
# FastAPIfrom prometheus_fastapi_instrumentator import Instrumentatorfrom pythonjsonlogger import jsonloggerfrom
# sentry_sdk.integrations.fastapi import FastAPIIntegrationfrom sentry_sdk.integrations.sqlalchemy import
# SqlalchemyIntegrationfrom app.core.config import settingsdef configure_sentry(app: FastAPI) -> None: """ Configura Sentry
# para tracking de errores Args: app: Instancia de FastAPI """ if not settings.SENTRY_DSN: logging.warning("SENTRY_DSN no
# configurado - Sentry deshabilitado") return sentry_sdk.init( dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT,
# release=settings.APP_VERSION, traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
# profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE, integrations=[ FastAPIIntegration(transaction_style="endpoint"),
# SqlalchemyIntegration(), ], # Configuración adicional before_send=before_send_sentry, send_default_pii=False, # No enviar
# PII por defecto attach_stacktrace=True, max_breadcrumbs=50, ) logging.info("Sentry configurado - Environment:
# para filtrar información sensible """ # Filtrar información sensible if "request" in event: if "headers" in
# event["request"]: # Remover headers sensibles sensitive_headers = ["authorization", "cookie", "x-api-key"] for header in
# sensitive_headers: if header in event["request"]["headers"]: event["request"]["headers"][header] = "[FILTERED]" return
# eventdef configure_prometheus(app: FastAPI) -> Optional[Instrumentator]: """ Configura Prometheus para métricas Args: app:
# Instancia de FastAPI Returns: Instrumentator configurado o None """ if not settings.PROMETHEUS_ENABLED:
# logging.warning("PROMETHEUS_ENABLED=False - Prometheus deshabilitado") return None instrumentator = Instrumentator(
# should_group_status_codes=True, should_ignore_untemplated=True, should_respect_env_var=True,
# should_instrument_requests_inprogress=True, excluded_handlers=["/health", "/metrics"], env_var_name="ENABLE_METRICS",
# inprogress_name="fastapi_inprogress", inprogress_labels=True, ) # Configurar métricas adicionales instrumentator.add( #
# Duración de requests por endpoint instrumentator.metrics.latency( buckets=( 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75,
# 1.0, 2.5, 5.0, 7.5, 10.0, ) ) ) instrumentator.add( # Tamaño de requests/responses instrumentator.metrics.requests() ) #
# endpoint="/metrics", include_in_schema=False) logging.info("Prometheus configurado - Métricas en /metrics") return
# instrumentatordef configure_structured_logging() -> None: """ Configura logging estructurado en formato JSON """ log_level
# = settings.LOG_LEVEL.upper() # Configurar formato JSON log_handler = logging.StreamHandler() formatter =
# log_handler.setFormatter(formatter) # Configurar logger raíz root_logger = logging.getLogger()
# root_logger.setLevel(log_level) root_logger.handlers = [] root_logger.addHandler(log_handler) # Configurar loggers
# logger_name in loggers_to_configure: logger = logging.getLogger(logger_name) logger.setLevel(log_level) logger.handlers =
# [] logger.addHandler(log_handler) logger.propagate = False logging.info("Logging estructurado configurado - Level:
# {log_level}")def setup_monitoring(app: FastAPI) -> dict: """ Configura todo el sistema de monitoreo Args: app: Instancia de
# FastAPI Returns: dict con configuración aplicada """ config_applied = { "sentry": False, "prometheus": False,
# "structured_logging": False, } try: # Logging estructurado configure_structured_logging()
# config_applied["structured_logging"] = True # Sentry if settings.SENTRY_DSN: configure_sentry(app) config_applied["sentry"]
# = True # Prometheus if settings.PROMETHEUS_ENABLED: instrumentator = configure_prometheus(app) if instrumentator:
# logging.info(f"Configuración aplicada: {config_applied}") except Exception as e: logging.error(f"Error configurando
# monitoreo: {str(e)}") # No fallar si el monitoreo falla return config_applied#
# ============================================# MÉTRICAS PERSONALIZADAS DE FINANCIAMIENTO AUTOMOTRIZ#
# ============================================def track_business_metrics( metric_name: str, value: float, labels:
# Optional[dict] = None) -> None: """ Registra métricas de negocio personalizadas para financiamiento automotriz Args:
# metric_name: Nombre de la métrica value: Valor de la métrica labels: Labels adicionales Examples:
# f"BUSINESS_METRIC: {metric_name}", extra={ "metric_name": metric_name, "metric_value": value, "labels": labels or {},
# e: logging.error(f"Error registrando métrica de negocio: {e}")def track_financial_operation( operation_type: str, amount:
# float, client_id: int, user_id: int, additional_data: Optional[dict] = None,) -> None: """ Trackear operaciones financieras
# específicas Args: operation_type: PAGO, PRESTAMO, ANULACION, MODIFICACION amount: Monto de la operación client_id: ID del
# f"financial_operation_{operation_type.lower()}", amount, { "operation_type": operation_type, "client_id": client_id,
# "user_id": user_id, **(additional_data or {}), }, )def track_approval_workflow( workflow_step: str, request_type: str,
# workflow_step: SOLICITUD, APROBACION, RECHAZO, EJECUCION request_type: MODIFICAR_PAGO, ANULAR_PAGO, EDITAR_CLIENTE
# "request_type": request_type, "user_role": user_role, }, )def track_bulk_migration( total_records: int, successful: int,
# failed: int, warnings: int, migration_type: str,) -> None: """ Trackear migraciones masivas """ track_business_metrics(
# "bulk_migration_total", total_records, {"type": migration_type} ) track_business_metrics( "bulk_migration_successful",
# successful, {"type": migration_type} ) track_business_metrics( "bulk_migration_failed", failed, {"type": migration_type} )
# track_business_metrics( "bulk_migration_warnings", warnings, {"type": migration_type} )# Context managers para
# trackingclass track_operation: """ Context manager para trackear operaciones Example: with
# track_operation("crear_prestamo", cliente_id=123): # código pass """ def __init__(self, operation_name: str, **kwargs):
# self.operation_name = operation_name self.context = kwargs def __enter__(self): logging.info( "Iniciando operación:
# {self.operation_name}", extra=self.context ) return self def __exit__(self, exc_type, exc_val, exc_tb): if exc_type:
# logging.error( f"Error en operación: {self.operation_name}", extra={**self.context, "error": str(exc_val)}, exc_info=True,
# ) else: logging.info( f"Operación completada: {self.operation_name}", extra=self.context, )#
# ============================================# ENDPOINT DE VERIFICACIÓN DE MONITOREO#
# ============================================def get_monitoring_status() -> dict: """ Obtener estado actual del sistema de
# bool(getattr(settings, "SENTRY_DSN", None)), "environment": getattr(settings, "ENVIRONMENT", "production"),
# "traces_sample_rate": getattr( settings, "SENTRY_TRACES_SAMPLE_RATE", 0.1 ), "descripcion": "Tracking de errores y
# performance", }, "prometheus": { "habilitado": getattr(settings, "PROMETHEUS_ENABLED", False), "endpoint": "/metrics",
# "descripcion": "Métricas de aplicación y negocio", }, "logging_estructurado": { "habilitado": True, "formato": "JSON",
# "approval_workflow_aprobacion", "bulk_migration_total", "financial_operation_pago", ], "rendimiento": [
# "http_requests_total", "http_request_duration_seconds", "database_connections", ], }, "integracion_actual": { "main_py": "❌
# No integrado", "endpoints": "❌ No utilizado", "recomendacion": "Integrar en main.py para habilitar monitoreo completo", },
# Importar setup_monitoring en main.py", "3. Llamar setup_monitoring(app) al inicio", "4. Usar track_operation en endpoints
# "Debugging de migraciones masivas", ], }, }
