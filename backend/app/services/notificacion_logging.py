# -*- coding: utf-8 -*-
"""
Fases e indicadores de log para el flujo de notificaciones.
Permite identificar por fase fallas o indicadores de funcionamiento (búsqueda por FASE_* en logs).
"""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Fases del flujo de envío (notificaciones_tabs)
FASE_ENVIO_INICIO = "notif_envio_inicio"
FASE_ENVIO_CONFIG = "notif_envio_config"
FASE_ENVIO_CONTEXTO_COBRANZA = "notif_envio_contexto_cobranza"
FASE_ENVIO_ADJUNTOS = "notif_envio_adjuntos"
FASE_ENVIO_EMAIL = "notif_envio_email"
FASE_ENVIO_PERSISTENCIA = "notif_envio_persistencia"
FASE_ENVIO_RESUMEN = "notif_envio_resumen"
FASE_ENVIO_FALLO = "notif_envio_fallo"

# Fases del flujo de historial por cédula
FASE_HISTORIAL_CONSULTA = "notif_historial_consulta"
FASE_HISTORIAL_EXCEL = "notif_historial_excel"
FASE_HISTORIAL_COMPROBANTE = "notif_historial_comprobante"
FASE_HISTORIAL_FALLO = "notif_historial_fallo"


def _extra(phase: str, **kwargs: Any) -> dict:
    """Extra dict para que quede en estructura (fase=..., ...) en logs JSON si se usa."""
    return {"fase": phase, **kwargs}


def log_envio_inicio(total_items: int, origen: str) -> None:
    """Indicador: inicio de envío por lote."""
    logger.info(
        "[%s] Inicio envío notificaciones: items=%s origen=%s",
        FASE_ENVIO_INICIO,
        total_items,
        origen,
        extra=_extra(FASE_ENVIO_INICIO, total_items=total_items, origen=origen),
    )


def log_envio_config(modo_pruebas: bool, email_pruebas: bool, habilitados: int) -> None:
    """Indicador: config de envío cargada."""
    logger.info(
        "[%s] Config envío: modo_pruebas=%s email_pruebas_ok=%s tipos_habilitados=%s",
        FASE_ENVIO_CONFIG,
        modo_pruebas,
        email_pruebas,
        habilitados,
        extra=_extra(FASE_ENVIO_CONFIG, modo_pruebas=modo_pruebas, habilitados=habilitados),
    )


def log_envio_contexto_cobranza(item_id: str, ok: bool, motivo: Optional[str] = None) -> None:
    """Indicador: construcción de contexto cobranza por ítem."""
    level = logging.INFO if ok else logging.WARNING
    logger.log(
        level,
        "[%s] Contexto cobranza item=%s ok=%s motivo=%s",
        FASE_ENVIO_CONTEXTO_COBRANZA,
        item_id,
        ok,
        motivo or "ok",
        extra=_extra(FASE_ENVIO_CONTEXTO_COBRANZA, item_id=item_id, ok=ok, motivo=motivo),
    )


def log_envio_adjuntos(item_id: str, cantidad: int, error: Optional[str] = None) -> None:
    """Indicador: generación de adjuntos (PDF anexo / fijos)."""
    if error:
        logger.warning(
            "[%s] Adjuntos item=%s fallo=%s",
            FASE_ENVIO_ADJUNTOS,
            item_id,
            error,
            extra=_extra(FASE_ENVIO_ADJUNTOS, item_id=item_id, cantidad=0, error=error),
        )
    else:
        logger.info(
            "[%s] Adjuntos item=%s cantidad=%s",
            FASE_ENVIO_ADJUNTOS,
            item_id,
            cantidad,
            extra=_extra(FASE_ENVIO_ADJUNTOS, item_id=item_id, cantidad=cantidad),
        )


def log_envio_email(item_id: str, email: str, exito: bool, error: Optional[str] = None) -> None:
    """Indicador: envío de email (éxito o fallo)."""
    if exito:
        logger.info(
            "[%s] Email enviado item=%s destinatario=%s",
            FASE_ENVIO_EMAIL,
            item_id,
            email,
            extra=_extra(FASE_ENVIO_EMAIL, item_id=item_id, email=email, exito=True),
        )
    else:
        logger.warning(
            "[%s] Email fallido item=%s destinatario=%s error=%s",
            FASE_ENVIO_EMAIL,
            item_id,
            email,
            error or "desconocido",
            extra=_extra(FASE_ENVIO_EMAIL, item_id=item_id, email=email, exito=False, error=error),
        )


def log_envio_persistencia(registros: int, ok: bool, error: Optional[str] = None) -> None:
    """Indicador: persistencia en BD (envios_notificacion)."""
    if ok:
        logger.info(
            "[%s] Persistencia BD: registros=%s",
            FASE_ENVIO_PERSISTENCIA,
            registros,
            extra=_extra(FASE_ENVIO_PERSISTENCIA, registros=registros, ok=True),
        )
    else:
        logger.error(
            "[%s] Persistencia BD fallida: registros=%s error=%s",
            FASE_ENVIO_PERSISTENCIA,
            registros,
            error or "desconocido",
            extra=_extra(FASE_ENVIO_PERSISTENCIA, registros=registros, ok=False, error=error),
        )


def log_envio_resumen(
    enviados: int,
    fallidos: int,
    sin_email: int,
    omitidos_config: int,
    enviados_whatsapp: int,
    fallidos_whatsapp: int,
) -> None:
    """Indicador: resumen del lote (indicadores de funcionamiento)."""
    logger.info(
        "[%s] Resumen: enviados=%s fallidos=%s sin_email=%s omitidos_config=%s whatsapp_ok=%s whatsapp_fallo=%s",
        FASE_ENVIO_RESUMEN,
        enviados,
        fallidos,
        sin_email,
        omitidos_config,
        enviados_whatsapp,
        fallidos_whatsapp,
        extra=_extra(
            FASE_ENVIO_RESUMEN,
            enviados=enviados,
            fallidos=fallidos,
            sin_email=sin_email,
            omitidos_config=omitidos_config,
            enviados_whatsapp=enviados_whatsapp,
            fallidos_whatsapp=fallidos_whatsapp,
        ),
    )


def log_envio_fallo(fase: str, detalle: str, exc: Optional[Exception] = None) -> None:
    """Falla en alguna fase del envío."""
    logger.error(
        "[%s] FALLO fase=%s detalle=%s",
        FASE_ENVIO_FALLO,
        fase,
        detalle,
        exc_info=exc is not None,
        extra=_extra(FASE_ENVIO_FALLO, fase=fase, detalle=detalle),
    )


def log_historial_consulta(cedula_norm: str, total: int, tiempo_ms: Optional[float] = None) -> None:
    """Indicador: consulta historial por cédula."""
    logger.info(
        "[%s] Consulta cedula=%s total=%s tiempo_ms=%s",
        FASE_HISTORIAL_CONSULTA,
        cedula_norm,
        total,
        tiempo_ms,
        extra=_extra(FASE_HISTORIAL_CONSULTA, cedula=cedula_norm, total=total, tiempo_ms=tiempo_ms),
    )


def log_historial_excel(cedula: str, filas: int, ok: bool, error: Optional[str] = None) -> None:
    """Indicador: descarga Excel historial."""
    if ok:
        logger.info(
            "[%s] Excel generado cedula=%s filas=%s",
            FASE_HISTORIAL_EXCEL,
            cedula,
            filas,
            extra=_extra(FASE_HISTORIAL_EXCEL, cedula=cedula, filas=filas, ok=True),
        )
    else:
        logger.warning(
            "[%s] Excel fallido cedula=%s error=%s",
            FASE_HISTORIAL_EXCEL,
            cedula,
            error or "desconocido",
            extra=_extra(FASE_HISTORIAL_EXCEL, cedula=cedula, ok=False, error=error),
        )


def log_historial_comprobante(envio_id: int, ok: bool, error: Optional[str] = None) -> None:
    """Indicador: comprobante de envío (por id)."""
    if ok:
        logger.info(
            "[%s] Comprobante generado envio_id=%s",
            FASE_HISTORIAL_COMPROBANTE,
            envio_id,
            extra=_extra(FASE_HISTORIAL_COMPROBANTE, envio_id=envio_id, ok=True),
        )
    else:
        logger.warning(
            "[%s] Comprobante fallido envio_id=%s error=%s",
            FASE_HISTORIAL_COMPROBANTE,
            envio_id,
            error or "desconocido",
            extra=_extra(FASE_HISTORIAL_COMPROBANTE, envio_id=envio_id, ok=False, error=error),
        )


def log_historial_fallo(fase: str, detalle: str, exc: Optional[Exception] = None) -> None:
    """Falla en alguna fase del historial."""
    logger.error(
        "[%s] FALLO fase=%s detalle=%s",
        FASE_HISTORIAL_FALLO,
        fase,
        detalle,
        exc_info=exc is not None,
        extra=_extra(FASE_HISTORIAL_FALLO, fase=fase, detalle=detalle),
    )
