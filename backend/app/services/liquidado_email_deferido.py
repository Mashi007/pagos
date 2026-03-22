# -*- coding: utf-8 -*-
"""
Job diario: envia correos con PDF de estado de cuenta para prestamos LIQUIDADO.

Regla: para cada entero N en NOTIFICACIONES_LIQUIDADO_DIAS_ENVIO (defecto 1,2),
el dia D (Caracas) se consideran prestamos con fecha_liquidado = D - N dias
calendario. correlativo en envios_notificacion = N (1er correo, 2do correo).

Por cliente: un solo correo por oleada (mismo N y misma fecha_liquidado), usando el
prestamo de menor id como referencia; el PDF incluye todos los prestamos del cliente.

No reenvia si ya hay envio exitoso para ese prestamo_id con tipo_tab liquidados
y correlativo N.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.envio_notificacion import EnvioNotificacion
from app.models.prestamo import Prestamo
from app.services.cuota_estado import hoy_negocio
from app.services.liquidado_notificacion_service import LiquidadoNotificacionService

logger = logging.getLogger(__name__)


def _parse_dias_envio() -> List[int]:
    raw = (getattr(settings, "NOTIFICACIONES_LIQUIDADO_DIAS_ENVIO", None) or "1,2").strip()
    out: List[int] = []
    for part in raw.split(","):
        p = part.strip()
        if p.isdigit():
            n = int(p)
            if n >= 1:
                out.append(n)
    return sorted(set(out)) or [1, 2]


def _ya_enviado_exito(db: Session, prestamo_id: int, correlativo: int) -> bool:
    n = db.execute(
        select(func.count())
        .select_from(EnvioNotificacion)
        .where(
            EnvioNotificacion.prestamo_id == prestamo_id,
            EnvioNotificacion.tipo_tab == "liquidados",
            EnvioNotificacion.correlativo == correlativo,
            EnvioNotificacion.exito.is_(True),
        )
    ).scalar()
    return (n or 0) > 0


def ejecutar_emails_liquidado_diferidos(db: Session) -> dict:
    """
    Ejecutar una vez al dia (p. ej. 01:10 Caracas). Respeta modo_pruebas via send_email.
    """
    hoy = hoy_negocio()
    dias = _parse_dias_envio()
    enviados_ok = 0
    fallidos = 0
    omitidos_dup = 0
    for seq in dias:
        target = hoy - timedelta(days=seq)
        prestamos = db.execute(
            select(Prestamo).where(
                Prestamo.estado == "LIQUIDADO",
                Prestamo.fecha_liquidado == target,
            )
        ).scalars().all()

        by_client: dict[int, list[Prestamo]] = {}
        for p in prestamos:
            by_client.setdefault(p.cliente_id, []).append(p)

        for _cid, plist in by_client.items():
            rep = min(plist, key=lambda x: x.id)
            if _ya_enviado_exito(db, rep.id, seq):
                omitidos_dup += 1
                continue
            ok = LiquidadoNotificacionService.enviar_correo_liquidacion_pdf(
                db, rep.id, recordatorio_seq=seq
            )
            if ok:
                enviados_ok += 1
            else:
                fallidos += 1

    logger.info(
        "[LIQUIDADO_DEFERIDO] hoy=%s dias=%s enviados_ok=%s fallidos=%s omitidos_dup=%s",
        hoy,
        dias,
        enviados_ok,
        fallidos,
        omitidos_dup,
    )
    return {
        "fecha_job": hoy.isoformat(),
        "dias_config": dias,
        "enviados_ok": enviados_ok,
        "fallidos": fallidos,
        "omitidos_duplicado": omitidos_dup,
    }
