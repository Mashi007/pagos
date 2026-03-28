# -*- coding: utf-8 -*-
"""
Datos de estado de cuenta desde la base de datos (fuente unica para PDF, API JSON y consumidores).

Ver backend/docs/ESTADO_CUENTA_FUENTE_UNICA.md.
"""
from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.models.pago import Pago
from app.models.pago_reportado import PagoReportado
from app.models.prestamo import Prestamo
from app.services.cuota_estado import etiqueta_estado_cuota, estado_cuota_para_mostrar, hoy_negocio
from app.services.pagos_cuotas_sincronizacion import sincronizar_pagos_pendientes_a_prestamos

logger = logging.getLogger(__name__)

# Prestamos cuyo PDF/API incluyen la tabla completa de amortizacion (todas las cuotas).
ESTADOS_PRESTAMO_TABLA_AMORTIZACION = frozenset({"APROBADO", "LIQUIDADO"})


def prestamo_muestra_tabla_amortizacion(estado_prestamo: str) -> bool:
    return (estado_prestamo or "").strip().upper() in ESTADOS_PRESTAMO_TABLA_AMORTIZACION


def obtener_recibos_cliente_estado_cuenta(db: Session, cedula_lookup: str) -> List[dict]:
    """Pagos reportados del cliente (cedula sin guion) con recibo PDF, para enlaces en estado de cuenta."""
    cedula_concat = func.concat(PagoReportado.tipo_cedula, PagoReportado.numero_cedula)
    rows = db.execute(
        select(PagoReportado)
        .where(
            and_(
                cedula_concat == cedula_lookup,
                PagoReportado.recibo_pdf.isnot(None),
            )
        )
        .order_by(PagoReportado.fecha_pago.desc())
    ).scalars().all()
    out = []
    for row in rows:
        pr = row[0] if hasattr(row, "__getitem__") else row
        fp = getattr(pr, "fecha_pago", None)
        fecha_str = fp.isoformat() if fp else ""
        out.append(
            {
                "id": pr.id,
                "referencia_interna": getattr(pr, "referencia_interna", "") or "",
                "fecha_pago": fecha_str,
                "monto": float(getattr(pr, "monto", 0) or 0),
                "moneda": getattr(pr, "moneda", "BS") or "BS",
                "aplicado_a_cuotas": False,
            }
        )
    if out:
        num_docs = ["COB-" + (r["referencia_interna"] or "")[:90] for r in out]
        pagos_aplicados = set(
            row[0]
            for row in db.execute(
                select(Pago.numero_documento).where(
                    Pago.numero_documento.in_(num_docs),
                    Pago.estado == "PAGADO",
                )
            ).all()
        )
        for r in out:
            r["aplicado_a_cuotas"] = ("COB-" + (r["referencia_interna"] or "")) in pagos_aplicados
    return out

def _fmt_fecha_hora_pago_estado_cuenta(dt) -> str:
    if dt is None:
        return "-"
    try:
        if hasattr(dt, "strftime"):
            return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass
    return str(dt)


def _prestamo_cuota_recibo_desde_pago(db: Session, pago_id: int):
    row = db.execute(
        select(Cuota.prestamo_id, Cuota.id)
        .where(Cuota.pago_id == pago_id)
        .order_by(Cuota.numero_cuota.asc())
        .limit(1)
    ).first()
    if row:
        return int(row[0]), int(row[1])
    row = db.execute(
        select(Cuota.prestamo_id, Cuota.id)
        .join(CuotaPago, CuotaPago.cuota_id == Cuota.id)
        .where(CuotaPago.pago_id == pago_id)
        .order_by(Cuota.numero_cuota.asc())
        .limit(1)
    ).first()
    if row:
        return int(row[0]), int(row[1])



def desglose_aplicacion_cuotas_por_pago(db: Session, pago_id: int) -> List[dict]:
    """CuotaPago por pago: monto aplicado a cada cuota vs monto de cuota (pago total puede ser mayor)."""
    rows = db.execute(
        select(Cuota, CuotaPago.monto_aplicado)
        .join(CuotaPago, CuotaPago.cuota_id == Cuota.id)
        .where(CuotaPago.pago_id == pago_id)
        .order_by(Cuota.numero_cuota.asc())
    ).all()
    out: List[dict] = []
    for row in rows:
        c = row[0]
        apl_raw = row[1]
        m_cuota = float(getattr(c, "monto", 0) or 0)
        apl = float(apl_raw or 0)
        pct_n = (apl / m_cuota * 100.0) if m_cuota > 0.0001 else 0.0
        if abs(pct_n - round(pct_n)) < 0.051:
            pct_str = f"{int(round(pct_n))}%"
        else:
            pct_str = f"{pct_n:.1f}%".replace(".", ",")
        out.append(
            {
                "numero_cuota": int(getattr(c, "numero_cuota", 0) or 0),
                "monto_cuota": m_cuota,
                "monto_aplicado": apl,
                "porcentaje_cuota": pct_str,
            }
        )
    return out



def listar_pagos_realizados_estado_cuenta(db: Session, prestamo_ids: List[int]) -> List[dict]:
    """Pagos PAGADO en tabla pagos; subtotal_usd = monto_pagado (USD cartera)."""
    if not prestamo_ids:
        return []
    ids = sorted({int(x) for x in prestamo_ids if x is not None})
    if not ids:
        return []
    rows = db.execute(
        select(Pago)
        .where(
            Pago.prestamo_id.in_(ids),
            func.upper(func.coalesce(Pago.estado, "")) == "PAGADO",
        )
        .order_by(Pago.fecha_pago.desc(), Pago.id.desc())
    ).scalars().all()
    resultado: List[dict] = []
    for raw in rows:
        pg = raw[0] if hasattr(raw, "__getitem__") else raw
        pago_id = int(getattr(pg, "id", 0) or 0)
        prestamo_id = getattr(pg, "prestamo_id", None)
        banco = (getattr(pg, "institucion_bancaria", None) or "").strip() or "no disponible"
        fp = getattr(pg, "fecha_pago", None)
        fr = getattr(pg, "fecha_registro", None)
        moneda_raw = (getattr(pg, "moneda_registro", None) or "").strip().upper()
        es_bs = moneda_raw in ("BS", "BOLIVAR", "BOLIVARES")
        monto_usd = float(getattr(pg, "monto_pagado", 0) or 0)
        monto_bs_val = getattr(pg, "monto_bs_original", None)
        monto_bs_f = float(monto_bs_val) if monto_bs_val is not None else None
        tasa_val = getattr(pg, "tasa_cambio_bs_usd", None)
        tasa_f = float(tasa_val) if tasa_val is not None else None
        if es_bs:
            if monto_bs_f is not None:
                monto_display = f"{monto_bs_f:,.2f} Bs"
            else:
                monto_display = "Bs (monto no disponible en BD)"
            tasa_display = f"{tasa_f:,.6f}" if tasa_f is not None else "-"
        else:
            monto_display = f"{monto_usd:,.2f} USD"
            tasa_display = "-"
        rec = _prestamo_cuota_recibo_desde_pago(db, pago_id)
        if rec:
            rp, rc = rec
        else:
            rp = int(prestamo_id) if prestamo_id is not None else None
            rc = None
        doc = (getattr(pg, "numero_documento", None) or "").strip()
        refp = (getattr(pg, "referencia_pago", None) or "").strip()
        referencia_tabla = (doc or refp or f"Pago #{pago_id}")[:32]
        cedula_comprobante = (getattr(pg, "cedula_cliente", None) or "").strip() or "-"
        aplicacion_cuotas = desglose_aplicacion_cuotas_por_pago(db, pago_id)
        resultado.append(
            {
                "pago_id": pago_id,
                "prestamo_id": int(prestamo_id) if prestamo_id is not None else None,
                "banco": banco,
                "fecha_pago_display": _fmt_fecha_hora_pago_estado_cuenta(fp),
                "fecha_registro_display": _fmt_fecha_hora_pago_estado_cuenta(fr),
                "monto_display": monto_display,
                "tasa_display": tasa_display,
                "subtotal_usd": monto_usd,
                "es_bs": es_bs,
                "recibo_prestamo_id": rp,
                "recibo_cuota_id": rc,
                "referencia_tabla": referencia_tabla,
                "numero_documento": doc or None,
                "referencia_pago": refp or None,
                "cedula_comprobante": cedula_comprobante,
                "aplicacion_cuotas": aplicacion_cuotas,
            }
        )
    return resultado



def _cargar_prestamo_para_estado_cuenta(db, prestamo_id: int):
    """
    Carga el prestamo para armar el PDF. Si en BD no existe la columna fecha_liquidado (migracion 023),
    evita db.get(Prestamo) porque el mapper haria SELECT de esa columna y PostgreSQL fallaria.
    """
    from types import SimpleNamespace

    from sqlalchemy import select

    from app.models.prestamo import Prestamo

    from app.services.prestamo_db_compat import prestamos_tiene_columna_fecha_liquidado

    if prestamos_tiene_columna_fecha_liquidado(db):
        return db.get(Prestamo, prestamo_id)
    t = Prestamo.__table__
    cols = tuple(c for c in t.c if c.name != "fecha_liquidado")
    rowm = db.execute(select(*cols).where(t.c.id == prestamo_id)).mappings().first()
    if not rowm:
        return None
    return SimpleNamespace(**dict(rowm))


def obtener_datos_estado_cuenta_prestamo(db, prestamo_id: int, sincronizar: bool = True):

    """

    Obtiene datos formateados para PDF/JSON de estado de cuenta de UN prestamo.

    Consumidores: GET /prestamos/{id}/estado-cuenta, GET /prestamos/{id}/estado-cuenta/pdf,
    obtener_datos_estado_cuenta_cliente, liquidado_notificacion_service.

    Tabla de amortizacion completa si el prestamo esta en ESTADOS_PRESTAMO_TABLA_AMORTIZACION.

    Si sincronizar es False, el llamador debe haber llamado ya sincronizar_pagos_pendientes_a_prestamos.

    """

    from sqlalchemy import select

    from app.models.cliente import Cliente

    from app.models.cuota import Cuota

    from app.services.cuota_estado import estado_cuota_para_mostrar, hoy_negocio

    from app.services.pagos_cuotas_sincronizacion import sincronizar_pagos_pendientes_a_prestamos

    

    prestamo = _cargar_prestamo_para_estado_cuenta(db, prestamo_id)

    if not prestamo:

        return None

    

    cliente = db.get(Cliente, prestamo.cliente_id)

    if not cliente:

        return None

    

    cedula_display = (getattr(cliente, "cedula", None) or "").strip()

    nombre = (getattr(cliente, "nombres", None) or "").strip()

    email = (getattr(cliente, "email", None) or "").strip()

    

    if sincronizar:

        try:

            sincronizar_pagos_pendientes_a_prestamos(db, [prestamo_id])

        except Exception as sync_exc:

            logger.warning(

                "obtener_datos_estado_cuenta_prestamo: sincronizar_pagos_pendientes_a_prestamos prestamo_id=%s: %s",

                prestamo_id,

                sync_exc,

            )

    

    prestamos_list = [{

        "id": prestamo.id,

        "producto": getattr(prestamo, "producto", None) or "",

        "total_financiamiento": float(getattr(prestamo, "total_financiamiento", 0) or 0),

        "estado": getattr(prestamo, "estado", None) or "",

    }]

    

    cuotas_pendientes = []

    total_pendiente = 0.0

    fecha_corte_dt = hoy_negocio()

    

    cuotas_rows = db.execute(

        select(Cuota)

        .where(Cuota.prestamo_id == prestamo_id)

        .order_by(Cuota.numero_cuota)

    ).scalars().all()

    

    for cuota in cuotas_rows:

        monto_cuota = float(getattr(cuota, "monto", 0) or 0)

        total_pagado = float(getattr(cuota, "total_pagado", 0) or 0)

        monto_pendiente = max(0.0, monto_cuota - total_pagado)

        

        if monto_pendiente <= 0:

            continue

        

        total_pendiente += monto_pendiente

        fv = getattr(cuota, "fecha_vencimiento", None)

        fv_date = fv.date() if fv and hasattr(fv, "date") else fv

        estado_mostrar = estado_cuota_para_mostrar(total_pagado, monto_cuota, fv_date, fecha_corte_dt)

        

        cuotas_pendientes.append({

            "prestamo_id": prestamo_id,

            "numero_cuota": getattr(cuota, "numero_cuota", ""),

            "fecha_vencimiento": fv.isoformat() if fv else "",

            "monto": monto_pendiente,

            "estado": estado_mostrar,

            "estado_etiqueta": etiqueta_estado_cuota(estado_mostrar),

        })

    

    amortizaciones_por_prestamo = []

    estado = (getattr(prestamo, "estado", "") or "").strip().upper()

    

    if prestamo_muestra_tabla_amortizacion(estado):

        cuotas_amortizacion = db.execute(

            select(Cuota)

            .where(Cuota.prestamo_id == prestamo_id)

            .order_by(Cuota.numero_cuota)

        ).scalars().all()

        

        if cuotas_amortizacion:

            cuotas_data = []

            for c in cuotas_amortizacion:

                total_pagado_c = float(getattr(c, "total_pagado", 0) or 0)

                monto_c = float(getattr(c, "monto", 0) or 0)

                pago_conciliado = getattr(c, "pago_conciliado", False)

                

                fv_c = getattr(c, "fecha_vencimiento", None)

                fv_date_c = fv_c.date() if fv_c and hasattr(fv_c, "date") else fv_c

                estado_cuota = estado_cuota_para_mostrar(total_pagado_c, monto_c, fv_date_c, fecha_corte_dt)

                

                pago_conc_display = "Si" if pago_conciliado else "-"

                

                cuotas_data.append({

                    "id": c.id,

                    "numero_cuota": getattr(c, "numero_cuota", ""),

                    "fecha_vencimiento": fv_c.strftime("%d/%m/%Y") if fv_c else "",

                    "monto_capital": float(getattr(c, "monto_capital", 0) or 0),

                    "monto_interes": float(getattr(c, "monto_interes", 0) or 0),

                    "monto_cuota": monto_c,

                    "saldo_capital_final": float(getattr(c, "saldo_capital_final", 0) or 0),

                    "pago_conciliado_display": pago_conc_display,

                    "estado": estado_cuota,

                    "estado_etiqueta": etiqueta_estado_cuota(estado_cuota),

                })

            

            amortizaciones_por_prestamo.append({

                "prestamo_id": prestamo_id,

                "producto": getattr(prestamo, "producto", None) or "Prestamo",

                "cuotas": cuotas_data,

            })

    

    return {

        "cedula_display": cedula_display,

        "nombre": nombre,

        "email": email,

        "prestamos_list": prestamos_list,

        "cuotas_pendientes": cuotas_pendientes,

        "total_pendiente": total_pendiente,

        "fecha_corte": fecha_corte_dt,

        "amortizaciones_por_prestamo": amortizaciones_por_prestamo,
        "pagos_realizados": listar_pagos_realizados_estado_cuenta(db, [prestamo_id]),

    }

def obtener_datos_estado_cuenta_cliente(db, cedula_lookup: str):
    """
    Arma el mismo dict que consume generar_pdf_estado_cuenta para todos los prestamos
    del cliente (cedula normalizada sin guiones). Reutiliza obtener_datos_estado_cuenta_prestamo
    por cada prestamo para que cuotas pendientes, totales y amortizacion coincidan con
    GET /prestamos/{id}/estado-cuenta, GET /prestamos/{id}/estado-cuenta/pdf y notificaciones liquidado.
    """
    from sqlalchemy import func, select

    from app.models.cliente import Cliente
    from app.models.prestamo import Prestamo
    from app.services.cuota_estado import hoy_negocio
    from app.services.pagos_cuotas_sincronizacion import sincronizar_pagos_pendientes_a_prestamos

    cedula_lookup = (cedula_lookup or "").strip()
    if not cedula_lookup:
        return None

    cliente_row = db.execute(
        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_lookup)
    ).scalars().first()

    if not cliente_row:
        return None

    cliente = cliente_row[0] if hasattr(cliente_row, "__getitem__") else cliente_row
    cliente_id = getattr(cliente, "id", None)
    if not cliente_id:
        return None

    nombre = (getattr(cliente, "nombres", None) or "").strip()
    email = (getattr(cliente, "email", None) or "").strip()
    cedula_display = (getattr(cliente, "cedula", None) or "").strip()

    prestamos_rows = db.execute(
        select(Prestamo).where(Prestamo.cliente_id == cliente_id)
    ).scalars().all()

    prestamo_ids = []
    for row in prestamos_rows:
        p = row[0] if hasattr(row, "__getitem__") else row
        prestamo_ids.append(p.id)

    if prestamo_ids:
        try:
            sincronizar_pagos_pendientes_a_prestamos(db, prestamo_ids)
        except Exception as sync_exc:
            logger.warning(
                "obtener_datos_estado_cuenta_cliente: sincronizar_pagos_pendientes_a_prestamos "
                "cliente_id=%s: %s",
                cliente_id,
                sync_exc,
            )

    merged = {
        "cedula_display": cedula_display,
        "nombre": nombre,
        "email": email,
        "prestamos_list": [],
        "cuotas_pendientes": [],
        "total_pendiente": 0.0,
        "fecha_corte": hoy_negocio(),
        "amortizaciones_por_prestamo": [],
        "pagos_realizados": [],
    }

    for pid in prestamo_ids:
        part = obtener_datos_estado_cuenta_prestamo(db, pid, sincronizar=False)
        if not part:
            continue
        merged["fecha_corte"] = part["fecha_corte"]
        merged["prestamos_list"].extend(part["prestamos_list"])
        merged["cuotas_pendientes"].extend(part["cuotas_pendientes"])
        merged["total_pendiente"] += float(part["total_pendiente"] or 0)
        merged["amortizaciones_por_prestamo"].extend(part["amortizaciones_por_prestamo"])

    merged["pagos_realizados"] = listar_pagos_realizados_estado_cuenta(db, prestamo_ids)

    return merged


def serializar_estado_cuenta_payload_json(datos: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convierte el dict de obtener_datos_estado_cuenta_* a JSON (fecha_corte como ISO)."""
    if not datos:
        return None
    payload = copy.deepcopy(datos)
    fc = payload.get("fecha_corte")
    if hasattr(fc, "isoformat"):
        payload["fecha_corte"] = fc.isoformat()
    return payload

