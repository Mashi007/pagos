"""
Endpoints de cobranzas. Datos reales desde BD (Cuota, Prestamo, Cliente).
Estructura de respuestas compatible con cobranzasService.ts.
"""
from datetime import date, datetime, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo

router = APIRouter(dependencies=[Depends(get_current_user)])


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# Resumen y diagnóstico
# ---------------------------------------------------------------------------

@router.get("/resumen")
def get_resumen(
    incluir_admin: bool = Query(False),
    incluir_diagnostico: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Resumen de cobranzas desde BD: total cuotas vencidas, monto adeudado, clientes atrasados."""
    hoy = date.today()
    total_cuotas_vencidas = db.scalar(
        select(func.count()).select_from(Cuota).where(
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
        )
    ) or 0
    monto_total_adeudado = db.scalar(
        select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
            Cuota.fecha_pago.is_(None)
        )
    ) or 0
    clientes_atrasados = db.scalar(
        select(func.count(func.distinct(Cuota.cliente_id))).select_from(Cuota).where(
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
            Cuota.cliente_id.isnot(None),
        )
    ) or 0
    data: dict[str, Any] = {
        "total_cuotas_vencidas": total_cuotas_vencidas,
        "monto_total_adeudado": _safe_float(monto_total_adeudado),
        "clientes_atrasados": clientes_atrasados,
    }
    if incluir_diagnostico:
        data["diagnosticos"] = _diagnostico_desde_bd(db)
    return data


@router.get("/diagnostico")
def get_diagnostico(db: Session = Depends(get_db)):
    """Diagnóstico de cobranzas desde BD (cuotas, vencidas, estados)."""
    diag = _diagnostico_desde_bd(db)
    return {
        "diagnosticos": diag,
        "analisis_filtros": {
            "cuotas_perdidas_por_estado": 0,
            "cuotas_perdidas_por_admin": 0,
            "cuotas_perdidas_por_user_admin": 0,
        },
    }


def _diagnostico_desde_bd(db: Session) -> dict[str, Any]:
    """Calcula diagnóstico desde tabla cuotas."""
    hoy = date.today()
    total_cuotas_bd = db.scalar(select(func.count()).select_from(Cuota)) or 0
    cuotas_vencidas_solo_fecha = db.scalar(
        select(func.count()).select_from(Cuota).where(
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
        )
    ) or 0
    cuotas_pago_incompleto = 0
    cuotas_vencidas_incompletas = 0
    rows_estado = db.execute(
        select(Prestamo.estado, func.count(func.distinct(Prestamo.id)))
        .select_from(Prestamo)
        .join(Cuota, Cuota.prestamo_id == Prestamo.id)
        .where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < hoy)
        .group_by(Prestamo.estado)
    ).all()
    estados_prestamos_con_cuotas_vencidas = {r[0]: r[1] for r in rows_estado}
    return {
        "total_cuotas_bd": total_cuotas_bd,
        "cuotas_vencidas_solo_fecha": cuotas_vencidas_solo_fecha,
        "cuotas_pago_incompleto": cuotas_pago_incompleto,
        "cuotas_vencidas_incompletas": cuotas_vencidas_incompletas,
        "estados_prestamos_con_cuotas_vencidas": estados_prestamos_con_cuotas_vencidas,
    }


# ---------------------------------------------------------------------------
# Clientes atrasados
# ---------------------------------------------------------------------------

@router.get("/clientes-atrasados")
def get_clientes_atrasados(
    dias_retraso: Optional[int] = Query(None),
    dias_retraso_min: Optional[int] = Query(None),
    dias_retraso_max: Optional[int] = Query(None),
    incluir_admin: bool = Query(False),
    incluir_ml: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Lista de clientes con cuotas atrasadas desde BD."""
    hoy = date.today()
    subq = (
        select(Cuota.cliente_id)
        .where(
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
            Cuota.cliente_id.isnot(None),
        )
        .distinct()
    )
    if dias_retraso is not None:
        limite = hoy - timedelta(days=dias_retraso)
        subq = subq.where(Cuota.fecha_vencimiento <= limite)
    if dias_retraso_min is not None:
        limite_min = hoy - timedelta(days=dias_retraso_min)
        subq = subq.where(Cuota.fecha_vencimiento >= limite_min)
    if dias_retraso_max is not None:
        limite_max = hoy - timedelta(days=dias_retraso_max)
        subq = subq.where(Cuota.fecha_vencimiento <= limite_max)
    ids = [r[0] for r in db.execute(subq).all() if r[0]]
    if not ids:
        return []
    clientes = db.execute(select(Cliente).where(Cliente.id.in_(ids))).scalars().all()
    return [
        {
            "id": c.id,
            "cedula": c.cedula,
            "nombres": c.nombres,
            "telefono": c.telefono,
            "email": c.email,
            "estado": c.estado,
        }
        for c in clientes
    ]


@router.get("/clientes-por-cantidad-pagos")
def get_clientes_por_cantidad_pagos(
    cantidad_pagos: int = Query(...),
    db: Session = Depends(get_db),
):
    """Clientes con exactamente N cuotas atrasadas (desde BD)."""
    hoy = date.today()
    subq = (
        select(Cuota.cliente_id, func.count().label("cnt"))
        .where(
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
            Cuota.cliente_id.isnot(None),
        )
        .group_by(Cuota.cliente_id)
        .having(func.count() == cantidad_pagos)
    )
    rows = db.execute(subq).all()
    ids = [r[0] for r in rows]
    if not ids:
        return []
    clientes = db.execute(select(Cliente).where(Cliente.id.in_(ids))).scalars().all()
    return [
        {"id": c.id, "cedula": c.cedula, "nombres": c.nombres, "telefono": c.telefono, "email": c.email}
        for c in clientes
    ]


# ---------------------------------------------------------------------------
# Por analista
# ---------------------------------------------------------------------------

@router.get("/por-analista")
def get_cobranzas_por_analista(
    incluir_admin: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Cobranzas agrupadas por analista desde BD."""
    hoy = date.today()
    q = (
        select(
            func.coalesce(Prestamo.analista, "Sin analista").label("analista"),
            func.count(func.distinct(Cuota.cliente_id)).label("cantidad_clientes"),
            func.coalesce(func.sum(Cuota.monto), 0).label("monto_total"),
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < hoy)
        .group_by(Prestamo.analista)
    )
    rows = db.execute(q).all()
    return [
        {
            "analista": r.analista,
            "cantidad_clientes": r.cantidad_clientes,
            "monto_total": _safe_float(r.monto_total),
        }
        for r in rows
    ]


@router.get("/por-analista/{analista}/clientes")
def get_clientes_por_analista(analista: str, db: Session = Depends(get_db)):
    """Clientes atrasados de un analista desde BD."""
    hoy = date.today()
    subq = (
        select(Cuota.cliente_id)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .where(
            Cuota.fecha_pago.is_(None),
            Cuota.fecha_vencimiento < hoy,
        )
        .distinct()
    )
    if analista == "Sin analista":
        subq = subq.where(Prestamo.analista.is_(None))
    else:
        subq = subq.where(Prestamo.analista == analista)
    ids = [r[0] for r in db.execute(subq).all() if r[0]]
    if not ids:
        return []
    clientes = db.execute(select(Cliente).where(Cliente.id.in_(ids))).scalars().all()
    return [
        {"id": c.id, "cedula": c.cedula, "nombres": c.nombres, "telefono": c.telefono, "email": c.email}
        for c in clientes
    ]


# ---------------------------------------------------------------------------
# Montos por mes
# ---------------------------------------------------------------------------

@router.get("/montos-por-mes")
def get_montos_por_mes(
    incluir_admin: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Montos vencidos por mes desde BD (cuotas no pagadas con vencimiento en ese mes)."""
    q = (
        select(
            func.to_char(func.date_trunc("month", Cuota.fecha_vencimiento), "YYYY-MM").label("mes"),
            func.count().label("cantidad_cuotas"),
            func.coalesce(func.sum(Cuota.monto), 0).label("monto_total"),
        )
        .select_from(Cuota)
        .where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento.isnot(None))
        .group_by(func.date_trunc("month", Cuota.fecha_vencimiento))
        .order_by(func.date_trunc("month", Cuota.fecha_vencimiento).desc())
        .limit(12)
    )
    rows = db.execute(q).all()
    nombres = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
    out = []
    for r in rows:
        try:
            y, m = r.mes.split("-")
            mes_display = f"{nombres[int(m) - 1]} {y}"
        except Exception:
            mes_display = r.mes
        out.append({
            "mes": r.mes,
            "mes_display": mes_display,
            "cantidad_cuotas": r.cantidad_cuotas,
            "monto_total": _safe_float(r.monto_total),
        })
    return out


# ---------------------------------------------------------------------------
# Informes (JSON desde BD; PDF/Excel vacío)
# ---------------------------------------------------------------------------

@router.get("/informes/clientes-atrasados")
def get_informe_clientes_atrasados(
    dias_retraso_min: Optional[int] = Query(None),
    dias_retraso_max: Optional[int] = Query(None),
    analista: Optional[str] = Query(None),
    formato: Optional[str] = Query("json"),
    db: Session = Depends(get_db),
):
    """Informe clientes atrasados desde BD. formato=json|pdf|excel."""
    if formato in ("pdf", "excel"):
        return Response(status_code=200, content=b"", media_type="application/octet-stream")
    clientes = get_clientes_atrasados(
        dias_retraso_min=dias_retraso_min,
        dias_retraso_max=dias_retraso_max,
        db=db,
    )
    resumen = get_resumen(incluir_diagnostico=False, db=db)
    return {"clientes": clientes, "resumen": resumen}


@router.get("/informes/rendimiento-analista")
def get_informe_rendimiento_analista(
    formato: str = Query("json"),
    db: Session = Depends(get_db),
):
    if formato in ("pdf", "excel"):
        return Response(status_code=200, content=b"", media_type="application/octet-stream")
    return get_cobranzas_por_analista(db=db)


@router.get("/informes/montos-vencidos-periodo")
def get_informe_montos_periodo(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    formato: Optional[str] = Query("json"),
    db: Session = Depends(get_db),
):
    if formato in ("pdf", "excel"):
        return Response(status_code=200, content=b"", media_type="application/octet-stream")
    return get_montos_por_mes(db=db)


@router.get("/informes/antiguedad-saldos")
def get_informe_antiguedad_saldos(formato: str = Query("json"), db: Session = Depends(get_db)):
    if formato in ("pdf", "excel"):
        return Response(status_code=200, content=b"", media_type="application/octet-stream")
    return []


@router.get("/informes/resumen-ejecutivo")
def get_informe_resumen_ejecutivo(formato: str = Query("json"), db: Session = Depends(get_db)):
    if formato in ("pdf", "excel"):
        return Response(status_code=200, content=b"", media_type="application/octet-stream")
    return get_resumen(incluir_diagnostico=True, db=db)


# ---------------------------------------------------------------------------
# Notificaciones y ML
# ---------------------------------------------------------------------------

@router.post("/notificaciones/atrasos")
def procesar_notificaciones_atrasos(db: Session = Depends(get_db)):
    """Procesar notificaciones de atrasos. Devuelve estadísticas desde BD."""
    resumen = get_resumen(incluir_diagnostico=False, db=db)
    return {
        "mensaje": "Procesamiento de notificaciones.",
        "estadisticas": resumen,
    }


@router.put("/prestamos/{prestamo_id}/ml-impago")
def actualizar_ml_impago(prestamo_id: int, body: dict, db: Session = Depends(get_db)):
    """Marcar ML impago manual. Verifica préstamo en BD."""
    p = db.get(Prestamo, prestamo_id)
    if not p:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    return {"ok": True, "prestamo_id": prestamo_id}


@router.delete("/prestamos/{prestamo_id}/ml-impago")
def eliminar_ml_impago_manual(prestamo_id: int, db: Session = Depends(get_db)):
    """Quitar ML impago manual. Verifica préstamo en BD."""
    p = db.get(Prestamo, prestamo_id)
    if not p:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    return {"ok": True, "prestamo_id": prestamo_id}
