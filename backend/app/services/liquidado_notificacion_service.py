# -*- coding: utf-8 -*-
"""
Correos automaticos por prestamo LIQUIDADO con PDF de estado de cuenta.

El envio NO es el mismo dia del cambio a LIQUIDADO: lo programa el job diario
`liquidado_email_deferido` solo si NOTIFICACIONES_LIQUIDADO_EMAIL_ENABLED=true,
segun NOTIFICACIONES_LIQUIDADO_DIAS_ENVIO (por defecto 1 y 2 dias calendario
despues de prestamos.fecha_liquidado, zona Caracas).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.email import mask_email_for_log, send_email
from app.models.envio_notificacion import EnvioNotificacion
from app.services.envio_notificacion_snapshot import persistir_snapshot_envio_notificacion
from app.services.estado_cuenta_datos import obtener_datos_estado_cuenta_prestamo
from app.services.estado_cuenta_pdf import generar_pdf_estado_cuenta
from app.services.notificaciones_exclusion_desistimiento import (
    cliente_tiene_prestamo_desistimiento,
)

logger = logging.getLogger(__name__)


class LiquidadoNotificacionService:
    """Envia correo con PDF de estado de cuenta para prestamos liquidados (envio diferido)."""

    @staticmethod
    def crear_notificacion(prestamo_id: int, capital: float, suma_pagado: float) -> bool:
        """
        Compatibilidad: envia inmediatamente correo #1 (mismo dia). Preferir el job diferido.
        """
        db = SessionLocal()
        try:
            return LiquidadoNotificacionService.enviar_correo_liquidacion_pdf(
                db,
                prestamo_id,
                recordatorio_seq=1,
                capital_override=capital,
                suma_pagado_override=suma_pagado,
            )
        finally:
            db.close()

    @staticmethod
    def enviar_correo_liquidacion_pdf(
        db: Session,
        prestamo_id: int,
        recordatorio_seq: int,
        capital_override: Optional[float] = None,
        suma_pagado_override: Optional[float] = None,
    ) -> bool:
        """
        Genera PDF de estado de cuenta del cliente y envia un correo.
        recordatorio_seq: 1 = primer envio (dia +N segun job); 2 = segundo envio; correlativo en envios_notificacion.
        """
        if not getattr(settings, "NOTIFICACIONES_LIQUIDADO_EMAIL_ENABLED", False):
            logger.info(
                "[LIQUIDADO_NOTIF] Omitido prestamo_id=%s: NOTIFICACIONES_LIQUIDADO_EMAIL_ENABLED=False",
                prestamo_id,
            )
            return False
        try:
            result = db.execute(
                text(
                    """
                SELECT
                    p.cliente_id,
                    c.email,
                    c.cedula,
                    ('#' || CAST(p.id AS TEXT)),
                    c.nombres,
                    p.total_financiamiento,
                    p.id
                FROM prestamos p
                LEFT JOIN clientes c ON p.cliente_id = c.id
                WHERE p.id = :prestamo_id
            """
                ),
                {"prestamo_id": prestamo_id},
            ).fetchone()

            if not result:
                logger.warning(
                    "[LIQUIDADO_NOTIF] Prestamo %s no encontrado para notificacion",
                    prestamo_id,
                )
                return False

            (
                cliente_id,
                email,
                cedula,
                referencia,
                nombre_cliente,
                capital_bd,
                _pid,
            ) = result

            if cliente_tiene_prestamo_desistimiento(db, cliente_id):
                logger.warning(
                    "[LIQUIDADO_NOTIF] Omitido prestamo=%s cliente=%s (regla: cliente con prestamo DESISTIMIENTO)",
                    prestamo_id,
                    cliente_id,
                )
                return False

            sum_row = db.execute(
                text(
                    """
                SELECT COALESCE(SUM(total_pagado), 0) FROM cuotas WHERE prestamo_id = :pid
            """
                ),
                {"pid": prestamo_id},
            ).fetchone()
            suma_cuotas = float(sum_row[0] or 0) if sum_row else 0.0

            if not email or "@" not in (email or ""):
                logger.warning(
                    "[LIQUIDADO_NOTIF] Cliente %s sin email valido", cliente_id
                )
                return False

            capital = (
                float(capital_override)
                if capital_override is not None
                else float(capital_bd or 0)
            )
            suma_pagado = (
                float(suma_pagado_override)
                if suma_pagado_override is not None
                else suma_cuotas
            )

            logger.info(
                "[LIQUIDADO_NOTIF] Generando PDF prestamo=%s cliente=%s rec=%s",
                prestamo_id,
                cliente_id,
                recordatorio_seq,
            )
            pdf_bytes: Optional[bytes] = None
            try:
                pdf_bytes = LiquidadoNotificacionService._generar_pdf_estado_cuenta_prestamo(
                    db, prestamo_id
                )
            except Exception as e:
                logger.error("[LIQUIDADO_NOTIF] Error generando PDF: %s", e)

            if recordatorio_seq <= 1:
                asunto = f"Préstamo {referencia} — Crédito liquidado (estado de cuenta)"
                cuerpo_texto = f"""Estimado(a) {nombre_cliente or "Cliente"},

Su préstamo ref. {referencia} por {capital:,.2f} USD quedó liquidado.

Total abonado en cuotas (referencia): {suma_pagado:,.2f}

Adjuntamos su estado de cuenta en PDF.

Gracias por su confianza en RapiCredit.

Equipo RapiCredit"""
            else:
                asunto = f"Recordatorio — Estado de cuenta (préstamo {referencia})"
                cuerpo_texto = f"""Estimado(a) {nombre_cliente or "Cliente"},

Le reenviamos el estado de cuenta en PDF correspondiente a su préstamo {referencia}, ya liquidado.

Si ya recibió el mensaje anterior, puede ignorar este correo.

Equipo RapiCredit"""

            adjuntos: Optional[List[Tuple[str, bytes]]] = None
            if pdf_bytes:
                safe_ref = (referencia or str(prestamo_id)).replace(" ", "_")[:50]
                nombre_pdf = f"estado_cuenta_{safe_ref}.pdf"
                adjuntos = [(nombre_pdf, pdf_bytes)]

            exito = False
            error_msg: Optional[str] = None
            smtp_meta: dict = {}
            try:
                logger.info(
                    "[SMTP_ENVIO] context=liquidado_notif prestamo_id=%s recordatorio=%s email_cliente_MASK=%s",
                    prestamo_id,
                    recordatorio_seq,
                    mask_email_for_log(email.strip()),
                )
                exito, error_msg = send_email(
                    [email.strip()],
                    asunto,
                    cuerpo_texto,
                    attachments=adjuntos,
                    servicio="notificaciones",
                    tipo_tab="liquidados",
                    smtp_session_metadata=smtp_meta,
                )
            except Exception as e:
                logger.error("[LIQUIDADO_NOTIF] Excepcion enviando correo: %s", e)
                exito = False
                error_msg = str(e)

            if exito:
                logger.info(
                    "[LIQUIDADO_NOTIF] Correo enviado ok prestamo=%s rec=%s",
                    prestamo_id,
                    recordatorio_seq,
                )
            else:
                logger.warning(
                    "[LIQUIDADO_NOTIF] Fallo envio prestamo=%s: %s",
                    prestamo_id,
                    error_msg,
                )

            envio = EnvioNotificacion(
                tipo_tab="liquidados",
                asunto=(asunto or "")[:500],
                email=(email or "")[:255],
                nombre=(nombre_cliente or "")[:255],
                cedula=(cedula or "")[:50],
                exito=bool(exito),
                error_mensaje=None if exito else (error_msg or "")[:5000],
                prestamo_id=prestamo_id,
                correlativo=recordatorio_seq,
                mensaje_html=None,
                mensaje_texto=cuerpo_texto,
                metadata_tecnica=smtp_meta if smtp_meta else None,
            )
            db.add(envio)
            persistir_snapshot_envio_notificacion(db, envio, adjuntos)
            db.commit()
            return bool(exito)

        except Exception as e:
            logger.error(
                "[LIQUIDADO_NOTIF] Error prestamo_id=%s: %s",
                prestamo_id,
                e,
                exc_info=True,
            )
            try:
                db.rollback()
            except Exception:
                pass
            return False

    @staticmethod
    def _generar_pdf_estado_cuenta_prestamo(db: Session, prestamo_id: int) -> Optional[bytes]:
        """
        Mismo origen de datos que GET /prestamos/{id}/estado-cuenta/pdf (obtener_datos_estado_cuenta_prestamo):
        un solo prestamo, compatibilidad sin columna fecha_liquidado, amortizacion si aplica.
        """
        try:
            datos = obtener_datos_estado_cuenta_prestamo(db, prestamo_id)
            if not datos:
                logger.warning(
                    "[LIQUIDADO_NOTIF] Sin datos estado cuenta prestamo_id=%s", prestamo_id
                )
                return None
            return generar_pdf_estado_cuenta(
                cedula=datos.get("cedula_display") or "",
                nombre=datos.get("nombre") or "",
                prestamos=datos.get("prestamos_list") or [],
                fecha_corte=datos.get("fecha_corte") or date.today(),
                amortizaciones_por_prestamo=datos.get("amortizaciones_por_prestamo") or [],
                pagos_realizados=datos.get("pagos_realizados") or [],
            )
        except Exception as e:
            logger.error(
                "[LIQUIDADO_NOTIF] Error en _generar_pdf_estado_cuenta_prestamo prestamo_id=%s: %s",
                prestamo_id,
                e,
                exc_info=True,
            )
            return None


notificacion_service = LiquidadoNotificacionService()
