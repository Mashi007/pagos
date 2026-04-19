"""
Recibos: correo con PDF de estado de cuenta tras pagos conciliados (tabla pagos).

Criterio de negocio (alineado a BD real):
- Conciliación y marca de pago están en ``pagos`` (``conciliado``, ``fecha_registro``, ``estado``).
- Vínculo con cuotas: ``cuotas.pago_id = pagos.id`` o fila en ``cuota_pagos`` (pagos aplicados a cuotas).
- Ventanas por **fecha_registro** en America/Caracas (naive = reloj Caracas, coherente con cuota_estado).

Franjas diarias:
- ``manana``: 01:00 <= fecha_registro < 11:01  → envío programado 11:05
- ``tarde``:  11:01 <= fecha_registro < 17:01 → envío programado 17:05
- ``noche``:  17:01 <= fecha_registro <= 23:45 del mismo día → envío programado 23:55

PDF: misma fuente que el portal (``obtener_datos_estado_cuenta_cliente`` + ``generar_pdf_estado_cuenta``).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time
from typing import Any, Dict, List, Literal, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.email import send_email
from app.core.email_config_holder import get_email_activo_servicio
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.recibos_email_envio import RecibosEmailEnvio
from app.services.cuota_estado import TZ_NEGOCIO, hoy_negocio
from app.services.documentos_cliente_centro import (
    generar_pdf_estado_cuenta,
    obtener_datos_estado_cuenta_cliente,
    obtener_recibos_cliente_estado_cuenta,
)
from app.services.notificaciones_exclusion_desistimiento import cliente_bloqueado_por_desistimiento
from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd

logger = logging.getLogger(__name__)

RecibosSlot = Literal["manana", "tarde", "noche"]


def _bounds_fecha_registro_caracas(
    fecha_dia: date, slot: RecibosSlot
) -> Tuple[datetime, datetime]:
    """Inicio y fin inclusive (naive Caracas) para filtrar ``pagos.fecha_registro``."""
    tz = ZoneInfo(TZ_NEGOCIO)
    if slot == "manana":
        start = datetime.combine(fecha_dia, time(1, 0, 0), tzinfo=tz)
        end = datetime.combine(fecha_dia, time(11, 0, 59), tzinfo=tz)
    elif slot == "tarde":
        start = datetime.combine(fecha_dia, time(11, 1, 0), tzinfo=tz)
        end = datetime.combine(fecha_dia, time(17, 0, 59), tzinfo=tz)
    else:
        start = datetime.combine(fecha_dia, time(17, 1, 0), tzinfo=tz)
        end = datetime.combine(fecha_dia, time(23, 45, 59), tzinfo=tz)
    return start.replace(tzinfo=None), end.replace(tzinfo=None)


def _pago_aplicado_a_cuota_exists():
    cuota_direct = select(1).where(Cuota.pago_id == Pago.id).exists()
    via_cp = select(1).where(CuotaPago.pago_id == Pago.id).exists()
    return or_(cuota_direct, via_cp)


def listar_pagos_recibos_ventana(
    db: Session,
    *,
    fecha_dia: date,
    slot: RecibosSlot,
) -> List[Dict[str, Any]]:
    """Pagos conciliados PAGADO en la ventana, con enlace a cuotas (pago_id o cuota_pagos)."""
    start_naive, end_naive = _bounds_fecha_registro_caracas(fecha_dia, slot)
    rows = db.execute(
        select(Pago)
        .where(
            Pago.conciliado.is_(True),
            func.upper(func.coalesce(Pago.estado, "")) == "PAGADO",
            Pago.fecha_registro >= start_naive,
            Pago.fecha_registro <= end_naive,
            Pago.cedula_cliente.isnot(None),
            func.length(func.trim(Pago.cedula_cliente)) > 0,
            _pago_aplicado_a_cuota_exists(),
        )
        .order_by(Pago.fecha_registro.asc(), Pago.id.asc())
    ).scalars().all()
    out: List[Dict[str, Any]] = []
    for pg in rows:
        ced = (getattr(pg, "cedula_cliente", None) or "").strip()
        out.append(
            {
                "pago_id": int(pg.id),
                "cedula": ced,
                "cedula_normalizada": texto_cedula_comparable_bd(ced),
                "fecha_registro": pg.fecha_registro.isoformat() if pg.fecha_registro else None,
                "monto_pagado": float(getattr(pg, "monto_pagado", 0) or 0),
            }
        )
    return out


def _cedulas_distintas_desde_pagos(rows: List[Dict[str, Any]]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for r in rows:
        k = (r.get("cedula_normalizada") or "").strip()
        if not k or k in seen:
            continue
        seen.add(k)
        ordered.append(k)
    return ordered


def _ya_enviado_recibo(db: Session, cedula_norm: str, fecha_dia: date, slot: RecibosSlot) -> bool:
    row = db.execute(
        select(RecibosEmailEnvio.id).where(
            RecibosEmailEnvio.cedula_normalizada == cedula_norm,
            RecibosEmailEnvio.fecha_dia == fecha_dia,
            RecibosEmailEnvio.slot == slot,
        ).limit(1)
    ).scalar_one_or_none()
    return row is not None


def ejecutar_recibos_envio_slot(
    db: Session,
    *,
    fecha_dia: date,
    slot: RecibosSlot,
    solo_simular: bool = False,
) -> Dict[str, Any]:
    """
    Por cada cédula distinta con pagos en ventana: genera estado de cuenta y envía a correos del cliente.
    Si ``solo_simular`` es True, no persiste ``recibos_email_envio`` ni envía SMTP.
    """
    if not solo_simular and not get_email_activo_servicio("recibos"):
        return {
            "fecha_dia": fecha_dia.isoformat(),
            "slot": slot,
            "solo_simular": solo_simular,
            "error": "email_activo_recibos_desactivado",
            "pagos_en_ventana": 0,
            "cedulas_distintas": 0,
            "enviados": 0,
            "fallidos": 0,
            "omitidos_sin_email": 0,
            "omitidos_ya_enviado": 0,
            "omitidos_desistimiento": 0,
            "omitidos_sin_datos": 0,
            "detalles": [],
        }

    pagos = listar_pagos_recibos_ventana(db, fecha_dia=fecha_dia, slot=slot)
    cedulas = _cedulas_distintas_desde_pagos(pagos)
    enviados = 0
    fallidos = 0
    omitidos_sin_email = 0
    omitidos_ya_enviado = 0
    omitidos_desistimiento = 0
    omitidos_sin_datos = 0
    detalles: List[Dict[str, Any]] = []

    for cedula_norm in cedulas:
        if not solo_simular and _ya_enviado_recibo(db, cedula_norm, fecha_dia, slot):
            omitidos_ya_enviado += 1
            detalles.append({"cedula": cedula_norm, "motivo": "ya_enviado"})
            continue

        datos = obtener_datos_estado_cuenta_cliente(db, cedula_norm)
        if not datos:
            omitidos_sin_datos += 1
            detalles.append({"cedula": cedula_norm, "motivo": "sin_datos_estado_cuenta"})
            continue

        emails = datos.get("emails")
        if not isinstance(emails, list) or not emails:
            omitidos_sin_email += 1
            detalles.append({"cedula": cedula_norm, "motivo": "sin_email"})
            continue

        email0 = (emails[0] or "").strip() if emails else ""
        if cliente_bloqueado_por_desistimiento(db, cedula=cedula_norm, email=email0):
            omitidos_desistimiento += 1
            detalles.append({"cedula": cedula_norm, "motivo": "desistimiento"})
            continue

        cedula_display = (datos.get("cedula_display") or "").strip()
        nombre = (datos.get("nombre") or "").strip()
        fecha_corte = datos.get("fecha_corte") or fecha_dia
        if isinstance(fecha_corte, datetime):
            fecha_corte_d = fecha_corte.date()
        else:
            fecha_corte_d = fecha_corte if isinstance(fecha_corte, date) else fecha_dia

        recibos = obtener_recibos_cliente_estado_cuenta(db, cedula_norm)
        pdf_bytes = generar_pdf_estado_cuenta(
            cedula=cedula_display,
            nombre=nombre,
            prestamos=datos.get("prestamos_list") or [],
            fecha_corte=fecha_corte_d,
            amortizaciones_por_prestamo=datos.get("amortizaciones_por_prestamo") or [],
            pagos_realizados=datos.get("pagos_realizados") or [],
            recibos=recibos,
            recibo_token=None,
            base_url="",
        )
        fname = f"estado_cuenta_{cedula_display.replace('-', '_')}.pdf"
        asunto = f"Estado de cuenta - {fecha_corte_d.isoformat()} (Recibos)"
        body = (
            f"Estimado(a) {nombre},\n\n"
            f"Adjuntamos su estado de cuenta actualizado a la fecha de corte {fecha_corte_d.isoformat()} "
            f"por registro de pago(s) conciliado(s) en el sistema.\n\n"
            f"Saludos,\nRapiCredit"
        )

        if solo_simular:
            detalles.append(
                {
                    "cedula": cedula_norm,
                    "motivo": "simulacion_ok",
                    "emails": emails,
                    "pagos_en_ventana": len([p for p in pagos if p.get("cedula_normalizada") == cedula_norm]),
                }
            )
            continue

        ok, err = send_email(
            [e.strip() for e in emails if e and isinstance(e, str) and "@" in e.strip()],
            asunto,
            body,
            attachments=[(fname, pdf_bytes)],
            servicio="recibos",
            tipo_tab="recibos",
            respetar_destinos_manuales=True,
        )
        if ok:
            enviados += 1
            db.add(
                RecibosEmailEnvio(
                    cedula_normalizada=cedula_norm,
                    fecha_dia=fecha_dia,
                    slot=slot,
                )
            )
            detalles.append({"cedula": cedula_norm, "motivo": "enviado", "emails": emails})
        else:
            fallidos += 1
            detalles.append({"cedula": cedula_norm, "motivo": "fallo_smtp", "error": (err or "")[:500]})

    if not solo_simular and (enviados or fallidos):
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.exception("recibos: commit tras envíos: %s", e)
            raise

    return {
        "fecha_dia": fecha_dia.isoformat(),
        "slot": slot,
        "solo_simular": solo_simular,
        "pagos_en_ventana": len(pagos),
        "cedulas_distintas": len(cedulas),
        "enviados": enviados,
        "fallidos": fallidos,
        "omitidos_sin_email": omitidos_sin_email,
        "omitidos_ya_enviado": omitidos_ya_enviado,
        "omitidos_desistimiento": omitidos_desistimiento,
        "omitidos_sin_datos": omitidos_sin_datos,
        "detalles": detalles[:200],
    }


def job_recibos_manana_1105(db: Session) -> None:
    ejecutar_recibos_envio_slot(db, fecha_dia=hoy_negocio(), slot="manana", solo_simular=False)


def job_recibos_tarde_1705(db: Session) -> None:
    ejecutar_recibos_envio_slot(db, fecha_dia=hoy_negocio(), slot="tarde", solo_simular=False)


def job_recibos_noche_2355(db: Session) -> None:
    ejecutar_recibos_envio_slot(db, fecha_dia=hoy_negocio(), slot="noche", solo_simular=False)
