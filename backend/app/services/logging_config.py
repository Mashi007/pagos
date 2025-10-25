# backend/app/services/logging_config.py"""Configuración de Logging Estructurado para ServicesImplementa normas de monitoreo
# ContextVar("request_id", default=None)user_id: ContextVar[Optional[int]] = ContextVar("user_id", default=None)session_id:
# ContextVar[Optional[str]] = ContextVar("session_id", default=None)class StructuredFormatter(logging.Formatter): """
# "level": record.levelname, "logger": record.name, "message": record.getMessage(), "module": record.module, "function":
# record.funcName, "line": record.lineno, "thread": record.thread, "process": record.process, } # Agregar contexto de
# trazabilidad if request_id.get(): log_data["request_id"] = request_id.get() if user_id.get(): log_data["user_id"] =
# user_id.get() if session_id.get(): log_data["session_id"] = session_id.get() # Agregar excepción si existe if
# record.exc_info: log_data["exception"] = { "type": ( record.exc_info[0].__name__ if record.exc_info[0] else None ),
# "message": ( str(record.exc_info[1]) if record.exc_info[1] else None ), "traceback": self.formatException(record.exc_info),
# con trazabilidad """ def __init__(self, name: str): self.logger = logging.getLogger(name)
# self.logger.setLevel(logging.INFO) # Configurar handler si no existe if not self.logger.handlers: handler =
# logging.StreamHandler(sys.stdout) handler.setFormatter(StructuredFormatter()) self.logger.addHandler(handler) def
# _log_with_context( self, level: int, message: str, extra_data: Optional[Dict[str, Any]] = None, **kwargs, ): """ Log con
# key, value in kwargs.items(): setattr(record, key, value) self.logger.handle(record) def info(self, message: str,
# **kwargs): """Log de información""" self._log_with_context(logging.INFO, message, **kwargs) def warning(self, message: str,
# **kwargs): """Log de advertencia""" self._log_with_context(logging.WARNING, message, **kwargs) def error(self, message:
# str, **kwargs): """Log de error""" self._log_with_context(logging.ERROR, message, **kwargs) def debug(self, message: str,
# **kwargs): """Log de debug""" self._log_with_context(logging.DEBUG, message, **kwargs) def critical(self, message: str,
# **kwargs): """Log crítico""" self._log_with_context(logging.CRITICAL, message, **kwargs)def get_service_logger(name: str)
# -> ServiceLogger: """ Obtener logger especializado para servicio """ return ServiceLogger(name)def set_request_context(
# request_id_val: Optional[str] = None, user_id_val: Optional[int] = None, session_id_val: Optional[str] = None,): """
# Establecer contexto de trazabilidad para el request actual """ if request_id_val: request_id.set(request_id_val) if
# user_id_val: user_id.set(user_id_val) if session_id_val: session_id.set(session_id_val)def generate_request_id() -> str:
# """ Generar ID único para request """ return str(uuid.uuid4())def log_service_call( service_name: str, method_name: str,
# params: Optional[Dict[str, Any]] = None, duration_ms: Optional[float] = None, success: bool = True, error: Optional[str] =
# = { "service": service_name, "method": method_name, "success": success, "duration_ms": duration_ms, } if params: # Filtrar
# "key"]: safe_params[key] = "***REDACTED***" else: safe_params[key] = value log_data["params"] = safe_params if error:
# log_data["error"] = error if success: logger.info( f"Service call completed: {service_name}.{method_name}", **log_data )
# else: logger.error( f"Service call failed: {service_name}.{method_name}", **log_data )def log_business_event( event_type:
# str, entity_type: str, entity_id: Optional[str] = None, user_action: Optional[str] = None, metadata: Optional[Dict[str,
# = { "event_type": event_type, "entity_type": entity_type, "entity_id": entity_id, "user_action": user_action, "metadata":
# metadata or {}, } logger.info(f"Business event: {event_type}", **event_data)def log_performance_metric( metric_name: str,
# value: float, unit: str = "ms", tags: Optional[Dict[str, str]] = None,): """ Log de métricas de rendimiento """ logger =
# get_service_logger("performance") metric_data = { "metric_name": metric_name, "value": value, "unit": unit, "tags": tags or
# {}, } logger.info(f"Performance metric: {metric_name}", **metric_data)def log_security_event( event_type: str, severity:
# """ logger = get_service_logger("security") security_data = { "event_type": event_type, "severity": severity,
# "threat_level": threat_level, "details": details or {}, } if severity in ["HIGH", "CRITICAL"]: logger.critical(f"Security
# event: {event_type}", **security_data) else: logger.warning(f"Security event: {event_type}", **security_data)#
# "app.services.email_service", "app.services.ml_service", "app.services.notification_multicanal_service",
# "app.services.validators_service", "app.services.whatsapp_service", "app.services.amortizacion_service", ] for logger_name
# in service_loggers: logger = logging.getLogger(logger_name) logger.setLevel(logging.INFO) # Agregar handler estructurado si
# no existe if not any( isinstance(h, logging.StreamHandler) for h in logger.handlers ): handler =
# logging.StreamHandler(sys.stdout) handler.setFormatter(StructuredFormatter()) logger.addHandler(handler)# Decorador para
# * 1000 logger.error( f"Method call failed: {func.__name__}", duration_ms=duration, error=str(e), ) raise return wrapper
# return decorator
