# -*- coding: utf-8 -*-
"""
Correos automaticos por prestamo LIQUIDADO con PDF de estado de cuenta.

El envio NO es el mismo dia del cambio a LIQUIDADO: lo programa el job diario
`liquidado_email_deferido` segun NOTIFICACIONES_LIQUIDADO_DIAS_ENVIO (por defecto
1 y 2 dias calendario despues de prestamos.fecha_liquidado, zona Caracas).
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.email import mask_email_for_log, send_email
from app.models.envio_notificacion import EnvioNotificacion
from app.services.cuota_estado import estado_cuota_para_mostrar, hoy_negocio
from app.services.estado_cuenta_pdf import generar_pdf_estado_cuenta

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
                pdf_bytes = LiquidadoNotificacionService._generar_pdf_estado_cuenta(
                    db, cliente_id
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

            db.add(
                EnvioNotificacion(
                    tipo_tab="liquidados",
                    asunto=(asunto or "")[:500],
                    email=(email or "")[:255],
                    nombre=(nombre_cliente or "")[:255],
                    cedula=(cedula or "")[:50],
                    exito=bool(exito),
                    error_mensaje=None if exito else (error_msg or "")[:5000],
                    prestamo_id=prestamo_id,
                    correlativo=recordatorio_seq,
                )
            )
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
    def _generar_pdf_estado_cuenta(db: Session, cliente_id: int) -> Optional[bytes]:
        try:
            result_cliente = db.execute(
                text(
                    "SELECT cedula, nombres, email FROM clientes WHERE id = :cliente_id"
                ),
                {"cliente_id": cliente_id},
            ).fetchone()

            if not result_cliente:
                return None

            cedula, nombre, _email = result_cliente

            result_prestamos = db.execute(
                text(
                    """
                SELECT id, producto, total_financiamiento, estado
                FROM prestamos
                WHERE cliente_id = :cliente_id
                ORDER BY id DESC
            """
                ),
                {"cliente_id": cliente_id},
            ).fetchall()

            prestamos_data = []
            for row in result_prestamos:
                prestamos_data.append(
                    {
                        "id": row[0],
                        "producto": row[1] or "Préstamo",
                        "total_financiamiento": float(row[2] or 0),
                        "estado": row[3],
                    }
                )

            result_cuotas = db.execute(
                text(
                    """
                SELECT c.prestamo_id, c.numero_cuota, c.fecha_vencimiento,
                       COALESCE(c.monto_cuota, 0), COALESCE(c.total_pagado, 0)
                FROM cuotas c
                INNER JOIN prestamos p ON c.prestamo_id = p.id
                WHERE p.cliente_id = :cliente_id
                  AND COALESCE(c.total_pagado, 0) < COALESCE(c.monto_cuota, 0) - 0.01
                ORDER BY c.prestamo_id, c.numero_cuota
            """
                ),
                {"cliente_id": cliente_id},
            ).fetchall()

            cuotas_data = []
            total_pendiente = 0.0
            hoy_ref = hoy_negocio()
            for row in result_cuotas:
                fv = row[2]
                fv_d = fv.date() if fv and hasattr(fv, "date") else fv
                monto_c = float(row[3] or 0)
                total_p = float(row[4] or 0)
                estado_str = estado_cuota_para_mostrar(
                    total_p, monto_c, fv_d, hoy_ref
                )
                pend = max(0.0, monto_c - total_p)
                cuotas_data.append(
                    {
                        "prestamo_id": row[0],
                        "numero_cuota": row[1],
                        "fecha_vencimiento": row[2].isoformat() if row[2] else "",
                        "monto": pend,
                        "estado": estado_str,
                    }
                )
                total_pendiente += pend

            corte = hoy_negocio()
            return generar_pdf_estado_cuenta(
                cedula=cedula or "",
                nombre=nombre or "",
                prestamos=prestamos_data,
                cuotas_pendientes=cuotas_data,
                total_pendiente=total_pendiente,
                fecha_corte=corte,
            )

        except Exception as e:
            logger.error(
                "[LIQUIDADO_NOTIF] Error en _generar_pdf_estado_cuenta: %s",
                e,
                exc_info=True,
            )
            return None


notificacion_service = LiquidadoNotificacionService()
