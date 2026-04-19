# -*- coding: utf-8 -*-
"""
Alta en `pagos` + aplicación en cascada a cuotas para comprobantes Gmail plantilla **A/B/C/D**
(Mercantil / BNC / BINANCE / BNV), cuando:

- el serial **no** está duplicado en `pagos` / `pagos_con_errores` (lo comprueba el caller), y
- el cliente tiene **exactamente un** préstamo `APROBADO` (misma regla que carga masiva Excel).

Conciliación: `conciliado=True`, `verificado_concordancia=SI`, `fecha_conciliacion` al crear
(ajuste posterior si no hubo aplicación a cuotas: ver `_estado_conciliacion_post_cascada` en `pagos.py`).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.documento import compose_numero_documento_almacenado
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.services.pago_numero_documento import numero_documento_ya_registrado
from app.services.pago_registro_moneda import resolver_monto_registro_pago
from app.services.pagos_gmail.helpers import format_monto_excel_pagos_gmail, normalizar_fecha_pago
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento

logger = logging.getLogger(__name__)

USUARIO_REGISTRO_GMAIL_ABCD = "pagos-gmail-plantilla-abcd@sistema.rapicredit.com"


def _fecha_pago_date_desde_gmail(fecha_str: str) -> Optional[date]:
    raw = (fecha_str or "").strip()
    if not raw:
        return None
    norm = normalizar_fecha_pago(raw)
    for cand in (norm, raw):
        if not cand:
            continue
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(cand[:10], fmt).date()
            except ValueError:
                continue
    return None


def _monto_decimal_desde_gmail(monto_str: str, monto_min: float, monto_max: float) -> Optional[Decimal]:
    s = format_monto_excel_pagos_gmail(monto_str)
    if not s:
        return None
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    if v < monto_min or v > monto_max:
        return None
    return Decimal(str(round(v, 2)))


def crear_pago_conciliado_y_aplicar_cuotas_gmail_plantilla_abcd(
    db: Session,
    *,
    cedula_columna: str,
    fecha_pago_str: str,
    monto_str: str,
    numero_referencia: str,
    institucion_bancaria: Optional[str],
    link_comprobante: Optional[str],
    fmt: str,
    filename: Optional[str] = None,
) -> dict[str, Any]:
    """
    Crea `Pago`, aplica cascada y hace `commit` en BD si todo OK.
    En error de negocio / validación: `rollback` y devuelve ``ok: False`` (sin excepción).
    """
    from zoneinfo import ZoneInfo

    from app.api.v1.endpoints import pagos as pagos_ep

    def _fail(motivo: str, detalle: str = "") -> dict[str, Any]:
        try:
            db.rollback()
        except Exception:
            pass
        out: dict[str, Any] = {"ok": False, "motivo": motivo}
        if detalle:
            out["detalle"] = detalle
        return out

    fmt_u = (fmt or "").strip().upper()
    if fmt_u not in ("A", "B", "C", "D"):
        return _fail("no_abcd", fmt_u)

    cedula_raw = (cedula_columna or "").strip()
    if not cedula_raw:
        return _fail("cedula_vacia")

    fecha_pago = _fecha_pago_date_desde_gmail(fecha_pago_str)
    if fecha_pago is None:
        return _fail("fecha_invalida", (fecha_pago_str or "")[:80])

    monto_dec_in = _monto_decimal_desde_gmail(
        monto_str,
        float(pagos_ep._MIN_MONTO_PAGADO),
        float(pagos_ep._MAX_MONTO_PAGADO),
    )
    if monto_dec_in is None:
        return _fail("monto_invalido", (monto_str or "")[:80])

    ref_raw = (numero_referencia or "").strip()
    numero_doc_norm = compose_numero_documento_almacenado(ref_raw, None)
    if not numero_doc_norm:
        return _fail("documento_vacio")

    if numero_documento_ya_registrado(db, numero_doc_norm):
        return _fail("duplicado_documento")

    cedula_norm = cedula_raw.upper()
    prestamos_activos = (
        db.execute(
            select(Prestamo.id)
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                Cliente.cedula == cedula_norm,
                Prestamo.estado == "APROBADO",
            )
            .order_by(Prestamo.id)
        )
    ).scalars().all()

    n_prest = len(prestamos_activos)
    if n_prest == 0:
        return _fail("sin_prestamo_aprobado")
    if n_prest > 1:
        return _fail("varios_prestamos", str(n_prest))

    prestamo_id = int(prestamos_activos[0])
    prest = db.get(Prestamo, prestamo_id)
    if not prest:
        return _fail("prestamo_no_encontrado")
    cli = db.get(Cliente, prest.cliente_id)
    if not cli:
        return _fail("cliente_prestamo")

    ced_norm_cli = normalizar_cedula_almacenamiento(cli.cedula)
    if ced_norm_cli and ced_norm_cli != (cli.cedula or ""):
        cli.cedula = ced_norm_cli
        db.flush()
    cedula_fk = normalizar_cedula_almacenamiento(cli.cedula) or normalizar_cedula_almacenamiento(
        prest.cedula
    )
    if not cedula_fk:
        return _fail("cedula_cliente_bd")

    cedula_input = normalizar_cedula_almacenamiento(cedula_raw)
    cn_body = (cedula_input or "").replace("-", "").upper()
    cn_fk = (cedula_fk or "").replace("-", "").upper()
    if cedula_input and cn_body != cn_fk:
        return _fail("cedula_no_coincide_cliente", cedula_fk)

    ref_pago = (numero_doc_norm or ref_raw or "Gmail")[: int(pagos_ep._MAX_LEN_NUMERO_DOCUMENTO)]

    try:
        monto_usd_g, moneda_fin_g, monto_bs_g, tasa_g, fecha_tasa_g = resolver_monto_registro_pago(
            db,
            cedula_normalizada=(cedula_fk or "").strip().upper(),
            fecha_pago=fecha_pago,
            monto_pagado=monto_dec_in,
            moneda_registro="USD",
            tasa_cambio_manual=None,
        )
    except Exception as e:
        logger.warning("[PAGOS_GMAIL] [ABCD_PAGO] resolver_monto: %s", e)
        return _fail("resolver_monto", str(e)[:500])

    msg_h = pagos_ep.conflicto_huella_para_creacion(
        db,
        prestamo_id=prestamo_id,
        fecha_pago=fecha_pago,
        monto_pagado=monto_usd_g,
        numero_documento=numero_doc_norm,
        referencia_pago=ref_pago,
    )
    if msg_h:
        pagos_ep.registrar_rechazo_huella_funcional()
        return _fail("huella_funcional", msg_h[:500])

    ib = (institucion_bancaria or "").strip()[:255] or None
    link_c = (link_comprobante or "").strip() or None
    if link_c and len(link_c) > 4000:
        link_c = link_c[:4000]

    ahora = datetime.now(ZoneInfo(pagos_ep.TZ_NEGOCIO))
    notas = f"Gmail plantilla {fmt_u}"
    if filename:
        notas = f"{notas} | {filename}"[:900]

    pago = Pago(
        cedula_cliente=cedula_fk,
        prestamo_id=prestamo_id,
        fecha_pago=datetime.combine(fecha_pago, dt_time.min),
        monto_pagado=monto_usd_g,
        numero_documento=numero_doc_norm,
        institucion_bancaria=ib,
        estado="PAGADO",
        referencia_pago=ref_pago,
        conciliado=True,
        fecha_conciliacion=ahora,
        verificado_concordancia="SI",
        usuario_registro=USUARIO_REGISTRO_GMAIL_ABCD,
        moneda_registro=moneda_fin_g,
        monto_bs_original=monto_bs_g,
        tasa_cambio_bs_usd=tasa_g,
        fecha_tasa_referencia=fecha_tasa_g,
        link_comprobante=link_c,
        notas=notas,
    )
    db.add(pago)
    try:
        db.flush()
    except IntegrityError as e:
        logger.warning("[PAGOS_GMAIL] [ABCD_PAGO] integridad al insertar: %s", e)
        return _fail("integridad", str(e)[:400])

    cc, cp = 0, 0
    if pago.prestamo_id and float(pago.monto_pagado or 0) > 0:
        try:
            cc, cp = pagos_ep._aplicar_pago_a_cuotas_interno(pago, db)
        except Exception as e:
            logger.warning("[PAGOS_GMAIL] [ABCD_PAGO] aplicar cuotas: %s", e)
            db.rollback()
            return _fail("aplicar_cuotas", str(e)[:500])

    pagos_ep._estado_conciliacion_post_cascada(pago, cc, cp)

    try:
        db.commit()
    except Exception as e:
        logger.warning("[PAGOS_GMAIL] [ABCD_PAGO] commit: %s", e)
        db.rollback()
        return _fail("commit", str(e)[:400])

    logger.info(
        "[PAGOS_GMAIL] [ABCD_PAGO] pago_id=%s prestamo_id=%s fmt=%s cc=%s cp=%s conciliado=%s estado=%s",
        pago.id,
        prestamo_id,
        fmt_u,
        cc,
        cp,
        bool(pago.conciliado),
        (pago.estado or "")[:32],
    )
    return {
        "ok": True,
        "pago_id": pago.id,
        "prestamo_id": prestamo_id,
        "cuotas_completadas": cc,
        "cuotas_parciales": cp,
        "conciliado": bool(pago.conciliado),
        "estado": pago.estado,
    }
