# backend/app/services/logging_config.py"""Configuración de Logging Estructurado para ServicesImplementa normas de monitoreo"""
# ContextVar("request_id", default=None)user_id: ContextVar[Optional[int]] = ContextVar("user_id", default=None)session_id:
# ContextVar[Optional[str]] = ContextVar("session_id", default=None)class StructuredFormatter(logging.Formatter): """"""
# "level": record.levelname, "logger": record.name, "message": record.getMessage(), "module": record.module, "function":
# record.funcName, "line": record.lineno, "thread": record.thread, "process": record.process, } # Agregar contexto de
# trazabilidad if request_id.get(): log_data["request_id"] = request_id.get() if user_id.get(): log_data["user_id"] =
# user_id.get() if session_id.get(): log_data["session_id"] = session_id.get() # Agregar excepción si existe if
# record.exc_info: log_data["exception"] = 
# log_data["error"] = error if success: logger.info( f"Service call completed: {service_name}.{method_name}", **log_data )
# else: logger.error( f"Service call failed: {service_name}.{method_name}", **log_data )def log_business_event
# metadata or {}, } logger.info(f"Business event: {event_type}", **event_data)def log_performance_metric
# value: float, unit: str = "ms", tags: Optional[Dict[str, str]] = None,): """ Log de métricas de rendimiento """ logger =
# get_service_logger("performance") metric_data = 
# {}, } logger.info(f"Performance metric: {metric_name}", **metric_data)def log_security_event
# """ logger = get_service_logger("security") security_data = """
# "threat_level": threat_level, "details": details or {}, } if severity in ["HIGH", "CRITICAL"]: logger.critical
# event: {event_type}", **security_data) else: logger.warning(f"Security event: {event_type}", **security_data)#
# "app.services.email_service", "app.services.ml_service", "app.services.notification_multicanal_service",
# "app.services.validators_service", "app.services.whatsapp_service", "app.services.amortizacion_service", ] for logger_name
# in service_loggers: logger = logging.getLogger(logger_name) logger.setLevel(logging.INFO) # Agregar handler estructurado si
# no existe if not any( isinstance(h, logging.StreamHandler) for h in logger.handlers ): handler =
# logging.StreamHandler(sys.stdout) handler.setFormatter(StructuredFormatter()) logger.addHandler(handler)# Decorador para
# * 1000 logger.error( f"Method call failed: {func.__name__}", duration_ms=duration, error=str(e), ) raise return wrapper
# return decorator

""""""