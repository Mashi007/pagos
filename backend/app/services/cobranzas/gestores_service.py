# -*- coding: utf-8 -*-
"""
Gestores de cobranza: asignacion fija, Excel en vivo y dashboard.

- Universo inicial: prestamos APROBADO con al menos una cuota VENCIDO/MORA
  con fecha_vencimiento >= 2026-01-01 y <= hoy (Caracas).
- Reparto equilibrado por dolares vencidos+mora y cantidad de cuotas.
- Asignacion sticky: no se rebalancea ni se agregan casos nuevos tras el primer cierre.
- Si un prestamo pasa a LIQUIDADO (u otro estado distinto de APROBADO), sale de la lista
  Excel/dashboard en la siguiente actualizacion (la asignacion historica se conserva).
- Excel / montos: siempre recalculados desde BD (pagos actualizan al instante).
"""
from __future__ import annotations

import io
import logging
import re
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

import openpyxl
from openpyxl.styles import Font
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cobranza_gestor import (
    CobranzaGestorAsignacion,
    CobranzaGestorDesempenoDiario,
)
from app.models.configuracion import Configuracion
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.services.cobranzas.gestores_constantes import (
    EMAIL_GESTORES_BCC,
    EMAIL_GESTORES_TO,
    FECHA_INICIO_CARTERA_GESTORES,
    GESTOR_NOMBRES,
    GESTOR_SLUGS,
    GESTORES,
)
from app.services.cuota_estado import hoy_negocio

logger = logging.getLogger(__name__)

CLAVE_ASIGNACION_CERRADA = "cobranza_gestores_asignacion_cerrada"
ESTADOS_ATRASO = ("VENCIDO", "MORA")


def _f(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _residual(monto: Any, total_pagado: Any) -> float:
    return max(0.0, _f(monto) - _f(total_pagado))


def listar_gestores() -> List[Dict[str, str]]:
    return [{"slug": s, "nombre": n} for s, n in GESTORES]


def _asignacion_cerrada(db: Session) -> bool:
    row = db.get(Configuracion, CLAVE_ASIGNACION_CERRADA)
    if not row or not row.valor:
        return False
    return str(row.valor).strip().lower() in ("1", "true", "si", "yes")


def _marcar_asignacion_cerrada(db: Session) -> None:
    row = db.get(Configuracion, CLAVE_ASIGNACION_CERRADA)
    if row is None:
        db.add(Configuracion(clave=CLAVE_ASIGNACION_CERRADA, valor="true"))
    else:
        row.valor = "true"


def _metricas_cuotas_atraso(
    cuotas: Sequence[Cuota], *, desde: date, hasta: date
) -> Dict[str, float]:
    cant_venc = 0
    usd_venc = 0.0
    cant_mora = 0
    usd_mora = 0.0
    total_pagado = 0.0
    for c in cuotas:
        total_pagado += _f(c.total_pagado)
        fv = c.fecha_vencimiento
        if fv is None or fv < desde or fv > hasta:
            continue
        est = (c.estado or "").strip().upper()
        if est not in ESTADOS_ATRASO:
            continue
        res = _residual(c.monto, c.total_pagado)
        if est == "MORA":
            cant_mora += 1
            usd_mora += res
        else:
            cant_venc += 1
            usd_venc += res
    return {
        "cant_vencidas": float(cant_venc),
        "usd_vencidas": usd_venc,
        "cant_mora": float(cant_mora),
        "usd_mora": usd_mora,
        "total_pagado": total_pagado,
        "carga_usd": usd_venc + usd_mora,
        "carga_cuotas": float(cant_venc + cant_mora),
    }


def _cargar_universo_inicial(db: Session) -> List[Dict[str, Any]]:
    """Prestamos APROBADO con al menos una cuota VENCIDO/MORA en el rango."""
    hoy = hoy_negocio()
    desde = FECHA_INICIO_CARTERA_GESTORES
    rows = db.execute(
        select(Prestamo, Cliente)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(func.upper(func.trim(Prestamo.estado)) == "APROBADO")
        .order_by(Prestamo.id.asc())
    ).all()
    out: List[Dict[str, Any]] = []
    for prestamo, cliente in rows:
        cuotas = (
            db.execute(
                select(Cuota)
                .where(Cuota.prestamo_id == prestamo.id)
                .order_by(Cuota.numero_cuota.asc())
            )
            .scalars()
            .all()
        )
        m = _metricas_cuotas_atraso(cuotas, desde=desde, hasta=hoy)
        if m["carga_cuotas"] <= 0:
            continue
        out.append(
            {
                "prestamo_id": int(prestamo.id),
                "carga_usd": m["carga_usd"],
                "carga_cuotas": m["carga_cuotas"],
            }
        )
    return out


def asegurar_asignaciones(db: Session) -> Dict[str, Any]:
    """
    Si la asignacion no esta cerrada: reparte el universo entre los 9 gestores
    (greedy por menor carga USD) y cierra. Si ya esta cerrada: no-op.
    """
    if _asignacion_cerrada(db):
        n = db.scalar(select(func.count()).select_from(CobranzaGestorAsignacion)) or 0
        return {"cerrada": True, "asignados": int(n), "nuevos": 0}

    existentes = {
        int(r[0])
        for r in db.execute(select(CobranzaGestorAsignacion.prestamo_id)).all()
    }
    universo = _cargar_universo_inicial(db)
    candidatos = [u for u in universo if u["prestamo_id"] not in existentes]
    # Mayor carga primero → se reparte mejor.
    candidatos.sort(
        key=lambda x: (x["carga_usd"], x["carga_cuotas"], x["prestamo_id"]),
        reverse=True,
    )

    cargas: Dict[str, Dict[str, float]] = {
        s: {"usd": 0.0, "cuotas": 0.0, "n": 0.0} for s in GESTOR_SLUGS
    }
    for pid in existentes:
        # Recalcular carga de ya asignados (por si hubo crash a medias).
        pass
    if existentes:
        for asg in db.execute(select(CobranzaGestorAsignacion)).scalars().all():
            slug = asg.gestor_slug
            if slug not in cargas:
                continue
            cuotas = (
                db.execute(select(Cuota).where(Cuota.prestamo_id == asg.prestamo_id))
                .scalars()
                .all()
            )
            m = _metricas_cuotas_atraso(
                cuotas, desde=FECHA_INICIO_CARTERA_GESTORES, hasta=hoy_negocio()
            )
            cargas[slug]["usd"] += m["carga_usd"]
            cargas[slug]["cuotas"] += m["carga_cuotas"]
            cargas[slug]["n"] += 1

    nuevos = 0
    for item in candidatos:
        slug = min(
            GESTOR_SLUGS,
            key=lambda s: (cargas[s]["usd"], cargas[s]["cuotas"], cargas[s]["n"], s),
        )
        db.add(
            CobranzaGestorAsignacion(
                prestamo_id=item["prestamo_id"],
                gestor_slug=slug,
            )
        )
        cargas[slug]["usd"] += item["carga_usd"]
        cargas[slug]["cuotas"] += item["carga_cuotas"]
        cargas[slug]["n"] += 1
        nuevos += 1

    _marcar_asignacion_cerrada(db)
    db.commit()
    total = db.scalar(select(func.count()).select_from(CobranzaGestorAsignacion)) or 0
    logger.info(
        "[gestores] asignacion cerrada nuevos=%s total=%s",
        nuevos,
        total,
    )
    return {"cerrada": True, "asignados": int(total), "nuevos": nuevos}


def _fila_caso(
    prestamo: Prestamo,
    cliente: Cliente,
    cuotas: Sequence[Cuota],
    *,
    desde: date,
    hasta: date,
) -> Dict[str, Any]:
    m = _metricas_cuotas_atraso(cuotas, desde=desde, hasta=hasta)
    return {
        "prestamo_id": int(prestamo.id),
        "cedula": (cliente.cedula or prestamo.cedula or "").strip(),
        "nombres": (cliente.nombres or prestamo.nombres or "").strip(),
        "telefono": (cliente.telefono or "").strip(),
        "email": (cliente.email or "").strip(),
        "total_financiamiento": round(_f(prestamo.total_financiamiento), 2),
        "total_pagado": round(m["total_pagado"], 2),
        "cant_cuotas_vencidas": int(m["cant_vencidas"]),
        "usd_cuotas_vencidas": round(m["usd_vencidas"], 2),
        "cant_cuotas_mora": int(m["cant_mora"]),
        "usd_cuotas_mora": round(m["usd_mora"], 2),
        "total_cobranza_usd": round(m["carga_usd"], 2),
    }


def filas_gestor(db: Session, gestor_slug: str) -> List[Dict[str, Any]]:
    slug = (gestor_slug or "").strip().lower()
    if slug not in GESTOR_NOMBRES:
        raise ValueError(f"Gestor desconocido: {gestor_slug}")
    asegurar_asignaciones(db)
    return _filas_gestor_sin_asegurar(db, slug)


def _filas_gestor_sin_asegurar(db: Session, slug: str) -> List[Dict[str, Any]]:
    hoy = hoy_negocio()
    desde = FECHA_INICIO_CARTERA_GESTORES
    asigs = (
        db.execute(
            select(CobranzaGestorAsignacion)
            .where(CobranzaGestorAsignacion.gestor_slug == slug)
            .order_by(CobranzaGestorAsignacion.prestamo_id.asc())
        )
        .scalars()
        .all()
    )
    filas: List[Dict[str, Any]] = []
    for asg in asigs:
        prestamo = db.get(Prestamo, asg.prestamo_id)
        if not prestamo:
            continue
        # Al liquidarse (u otro estado no APROBADO) sale de la lista al actualizar.
        if (prestamo.estado or "").strip().upper() != "APROBADO":
            continue
        cliente = db.get(Cliente, prestamo.cliente_id)
        if not cliente:
            continue
        cuotas = (
            db.execute(
                select(Cuota)
                .where(Cuota.prestamo_id == prestamo.id)
                .order_by(Cuota.numero_cuota.asc())
            )
            .scalars()
            .all()
        )
        filas.append(_fila_caso(prestamo, cliente, cuotas, desde=desde, hasta=hoy))
    return filas


def excel_gestor_bytes(db: Session, gestor_slug: str) -> Tuple[bytes, str, str]:
    slug = (gestor_slug or "").strip().lower()
    nombre = GESTOR_NOMBRES.get(slug)
    if not nombre:
        raise ValueError(f"Gestor desconocido: {gestor_slug}")
    filas = filas_gestor(db, slug)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cartera"
    headers = [
        "Cedula",
        "Nombres",
        "Telefono",
        "Email",
        "Total financiamiento",
        "Total pagado",
        "Cantidad cuotas vencidas",
        "Dolares cuotas vencidas",
        "Cantidad cuotas mora",
        "Dolares cuotas mora",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for f in filas:
        ws.append(
            [
                f["cedula"],
                f["nombres"],
                f["telefono"],
                f["email"],
                f["total_financiamiento"],
                f["total_pagado"],
                f["cant_cuotas_vencidas"],
                f["usd_cuotas_vencidas"],
                f["cant_cuotas_mora"],
                f["usd_cuotas_mora"],
            ]
        )
    # Totales al final
    if filas:
        ws.append([])
        ws.append(
            [
                "",
                "TOTAL",
                "",
                "",
                round(sum(x["total_financiamiento"] for x in filas), 2),
                round(sum(x["total_pagado"] for x in filas), 2),
                sum(x["cant_cuotas_vencidas"] for x in filas),
                round(sum(x["usd_cuotas_vencidas"] for x in filas), 2),
                sum(x["cant_cuotas_mora"] for x in filas),
                round(sum(x["usd_cuotas_mora"] for x in filas), 2),
            ]
        )
        for cell in ws[ws.max_row]:
            cell.font = Font(bold=True)
    buf = io.BytesIO()
    wb.save(buf)
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", nombre).strip("_") or slug
    fname = f"gestor_{safe}_{hoy_negocio().isoformat()}.xlsx"
    return buf.getvalue(), fname, nombre


def totales_vivos_por_gestor(db: Session) -> List[Dict[str, Any]]:
    asegurar_asignaciones(db)
    out: List[Dict[str, Any]] = []
    for slug, nombre in GESTORES:
        filas = _filas_gestor_sin_asegurar(db, slug)
        out.append(
            {
                "slug": slug,
                "nombre": nombre,
                "cantidad_casos": len(filas),
                "total_cobranza_usd": round(
                    sum(f["total_cobranza_usd"] for f in filas), 2
                ),
                "usd_vencidas": round(sum(f["usd_cuotas_vencidas"] for f in filas), 2),
                "usd_mora": round(sum(f["usd_cuotas_mora"] for f in filas), 2),
            }
        )
    return out


def persistir_snapshot_diario(
    db: Session,
    *,
    fecha: Optional[date] = None,
    commit: bool = True,
) -> Dict[str, Any]:
    """Guarda totales vivos del dia (Caracas) para la linea de tendencia."""
    dia = fecha or hoy_negocio()
    totales = totales_vivos_por_gestor(db)
    for t in totales:
        row = db.get(
            CobranzaGestorDesempenoDiario,
            {"fecha": dia, "gestor_slug": t["slug"]},
        )
        if row is None:
            row = CobranzaGestorDesempenoDiario(
                fecha=dia,
                gestor_slug=t["slug"],
                total_cobranza_usd=t["total_cobranza_usd"],
                cantidad_casos=t["cantidad_casos"],
            )
            db.add(row)
        else:
            row.total_cobranza_usd = t["total_cobranza_usd"]
            row.cantidad_casos = t["cantidad_casos"]
    if commit:
        db.commit()
    else:
        db.flush()
    return {"fecha": dia.isoformat(), "gestores": len(totales)}


def refrescar_desempeno_tras_pago(
    db: Session, prestamo_id: Optional[int]
) -> None:
    """
    Si el prestamo esta en una lista de gestores, actualiza el snapshot de hoy
    (todos los gestores) para que los graficos bajen al instante tras el pago.
    Nunca propaga excepciones al flujo de pagos.
    """
    if prestamo_id is None:
        return
    try:
        pid = int(prestamo_id)
    except (TypeError, ValueError):
        return
    if pid <= 0:
        return
    try:
        existe = db.scalar(
            select(CobranzaGestorAsignacion.id)
            .where(CobranzaGestorAsignacion.prestamo_id == pid)
            .limit(1)
        )
        if not existe:
            return
        # No reabrir asignacion: solo refrescar totales vivos del dia.
        dia = hoy_negocio()
        for slug in GESTOR_SLUGS:
            filas = _filas_gestor_sin_asegurar(db, slug)
            total_usd = round(sum(f["total_cobranza_usd"] for f in filas), 2)
            n_casos = len(filas)
            row = db.get(
                CobranzaGestorDesempenoDiario,
                {"fecha": dia, "gestor_slug": slug},
            )
            if row is None:
                db.add(
                    CobranzaGestorDesempenoDiario(
                        fecha=dia,
                        gestor_slug=slug,
                        total_cobranza_usd=total_usd,
                        cantidad_casos=n_casos,
                    )
                )
            else:
                row.total_cobranza_usd = total_usd
                row.cantidad_casos = n_casos
        db.flush()
    except Exception:
        logger.exception(
            "[gestores] refrescar_desempeno_tras_pago prestamo_id=%s",
            prestamo_id,
        )


def dashboard_gestores(db: Session) -> Dict[str, Any]:
    asegurar_asignaciones(db)
    # Snapshot de hoy para que la tendencia no quede vacia al abrir el modulo.
    try:
        persistir_snapshot_diario(db)
    except Exception:
        db.rollback()
        logger.exception("[gestores] snapshot diario falló")

    totales = totales_vivos_por_gestor(db)
    rows = db.execute(
        select(CobranzaGestorDesempenoDiario)
        .order_by(
            CobranzaGestorDesempenoDiario.fecha.asc(),
            CobranzaGestorDesempenoDiario.gestor_slug.asc(),
        )
    ).scalars().all()

    by_fecha: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        key = r.fecha.isoformat()
        if key not in by_fecha:
            by_fecha[key] = {"fecha": key}
        by_fecha[key][r.gestor_slug] = float(r.total_cobranza_usd or 0)

    return {
        "gestores": listar_gestores(),
        "totales": totales,
        "tendencia": list(by_fecha.values()),
        "asignacion_cerrada": _asignacion_cerrada(db),
        "fecha_inicio_cartera": FECHA_INICIO_CARTERA_GESTORES.isoformat(),
        "fecha_negocio": hoy_negocio().isoformat(),
    }


def enviar_listas_gestores_email(db: Session) -> Dict[str, Any]:
    """
    Regenera las 9 listas Excel al momento (sin liquidados) y las envia.
    To: operaciones@  BCC: itmaster@
    """
    from app.core.email import send_email

    asegurar_asignaciones(db)
    persistir_snapshot_diario(db)

    # Adjuntos = listas recalculadas justo antes del envio.
    attachments: List[Tuple[str, bytes]] = []
    for slug, _nombre in GESTORES:
        data, fname, _ = excel_gestor_bytes(db, slug)
        attachments.append((fname, data))

    hoy = hoy_negocio().isoformat()
    asunto = f"Listas actualizadas {hoy}"
    cuerpo = "Eduardo: Adjunto listas actualizadas"
    ok, err = send_email(
        [EMAIL_GESTORES_TO],
        asunto,
        cuerpo,
        bcc_emails=[EMAIL_GESTORES_BCC],
        attachments=attachments,
        servicio="notificaciones",
        tipo_tab="cobranza_gestores",
        aplicar_cco_automatica=False,
    )
    if not ok:
        logger.error("[gestores] fallo email listas: %s", err)
        return {"ok": False, "error": err, "adjuntos": len(attachments)}
    logger.info(
        "[gestores] email listas enviado to=%s bcc=%s adjuntos=%s asunto=%s",
        EMAIL_GESTORES_TO,
        EMAIL_GESTORES_BCC,
        len(attachments),
        asunto,
    )
    return {
        "ok": True,
        "adjuntos": len(attachments),
        "to": EMAIL_GESTORES_TO,
        "bcc": EMAIL_GESTORES_BCC,
        "asunto": asunto,
    }
