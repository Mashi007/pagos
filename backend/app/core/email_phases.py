"""
Fases del flujo de email para logs y tests.
Cada fase identifica un paso concreto (config, SMTP, IMAP) y permite detectar
fallos o indicadores de funcionamiento por etapa.
"""
import logging
import time
from typing import Any, Optional

# Nombres de fases (usar en logs y tests)
FASE_CONFIG_CARGA = "email_fase_config_carga"
FASE_CONFIG_GUARDADO = "email_fase_config_guardado"
FASE_SMTP_CONFIG = "email_fase_smtp_config"
FASE_SMTP_CONEXION = "email_fase_smtp_conexion"
FASE_SMTP_ENVIO = "email_fase_smtp_envio"
FASE_MODO_PRUEBAS = "email_fase_modo_pruebas"
FASE_IMAP_CONEXION = "email_fase_imap_conexion"
FASE_IMAP_LOGIN = "email_fase_imap_login"
FASE_IMAP_LIST = "email_fase_imap_list"
FASE_IMAP_COMPLETA = "email_fase_imap_completa"

# Todas las fases (para tests que comprueben presencia en logs)
FASES_EMAIL = (
    FASE_CONFIG_CARGA,
    FASE_CONFIG_GUARDADO,
    FASE_SMTP_CONFIG,
    FASE_SMTP_CONEXION,
    FASE_SMTP_ENVIO,
    FASE_MODO_PRUEBAS,
    FASE_IMAP_CONEXION,
    FASE_IMAP_LOGIN,
    FASE_IMAP_LIST,
    FASE_IMAP_COMPLETA,
)


def log_phase(
    logger: logging.Logger,
    phase: str,
    success: bool,
    message: Optional[str] = None,
    duration_ms: Optional[float] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """
    Log estructurado por fase. Formato: [FASE] phase=... success=... [mensaje] [duration_ms=...]
    Permite a tests y monitoreo identificar en qué fase hubo fallo o éxito.
    """
    parts = [f"phase={phase}", f"success={success}"]
    if message:
        parts.append(str(message)[:500])
    if duration_ms is not None:
        parts.append(f"duration_ms={round(duration_ms, 2)}")
    msg = " | ".join(parts)
    if extra:
        for k, v in extra.items():
            if k in ("phase", "success"):
                continue
            safe_v = str(v)[:200] if v is not None else ""
            msg += f" | {k}={safe_v}"
    if success:
        logger.info("[FASE] %s", msg)
    else:
        logger.warning("[FASE] %s", msg)


def log_phase_exception(
    logger: logging.Logger,
    phase: str,
    exc: Exception,
    message: Optional[str] = None,
) -> None:
    """Log de fallo de fase con excepción (warning + phase/success=False)."""
    log_phase(
        logger,
        phase,
        success=False,
        message=message or str(exc),
        extra={"error_type": type(exc).__name__},
    )
    logger.exception("Excepcion en fase %s: %s", phase, exc)
