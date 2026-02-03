"""
Endpoints de pagos. Datos reales desde BD.
- Tabla pagos: GET/POST/PUT/DELETE /pagos/ (listado y CRUD para /pagos/pagos).
- GET /pagos/kpis y GET /pagos/stats desde Cuota/Prestamo; zona horaria America/Caracas.
"""
import logging
from datetime import date, datetime, time as dt_time
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.schemas.pago import PagoCreate, PagoUpdate, PagoResponse

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])

# Zona horaria del negocio para "hoy" e "inicio_mes" (Monto cobrado mes, Pagos hoy)
TZ_NEGOCIO = "America/Caracas"


def _hoy_local() -> date:
    """Fecha de hoy en la zona horaria del negocio (evita que servidor UTC desfase el día)."""
    return datetime.now(ZoneInfo(TZ_NEGOCIO)).date()


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _pago_to_response(row: Pago, cuotas_atrasadas: Optional[int] = None) -> dict:
    """Convierte fila Pago a dict para el frontend (campos en snake_case; fechas ISO)."""
    fp = row.fecha_pago
    fecha_pago_str = fp.date().isoformat() if hasattr(fp, "date") and fp else (fp.isoformat() if fp else "")
    return {
        "id": row.id,
        "cedula_cliente": row.cedula_cliente or "",
        "prestamo_id": row.prestamo_id,
        "fecha_pago": fecha_pago_str,
        "monto_pagado": float(row.monto_pagado) if row.monto_pagado is not None else 0,
        "numero_documento": row.numero_documento or "",
        "institucion_bancaria": row.institucion_bancaria,
        "estado": row.estado or "PENDIENTE",
        "fecha_registro": row.fecha_registro.isoformat() if row.fecha_registro else None,
        "fecha_conciliacion": row.fecha_conciliacion.isoformat() if row.fecha_conciliacion else None,
        "conciliado": bool(row.conciliado),
        "verificado_concordancia": getattr(row, "verificado_concordancia", None) or None,
        "usuario_registro": row.usuario_registro or "",
        "notas": row.notas,
        "documento_nombre": getattr(row, "documento_nombre", None),
        "documento_tipo": getattr(row, "documento_tipo", None),
        "documento_ruta": getattr(row, "documento_ruta", None),
        "cuotas_atrasadas": cuotas_atrasadas,
    }


@router.get("", response_model=dict)
@router.get("/", include_in_schema=False, response_model=dict)
def listar_pagos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cedula: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Listado paginado desde la tabla pagos. Filtros: cedula, estado, fecha_desde, fecha_hasta, analista (vía prestamo)."""
    try:
        q = select(Pago)
        count_q = select(func.count()).select_from(Pago)
        if cedula and cedula.strip():
            q = q.where(Pago.cedula_cliente.ilike(f"%{cedula.strip()}%"))
            count_q = count_q.where(Pago.cedula_cliente.ilike(f"%{cedula.strip()}%"))
        if estado and estado.strip():
            q = q.where(Pago.estado == estado.strip().upper())
            count_q = count_q.where(Pago.estado == estado.strip().upper())
        if fecha_desde:
            try:
                fd = date.fromisoformat(fecha_desde)
                q = q.where(Pago.fecha_pago >= datetime.combine(fd, dt_time.min))
                count_q = count_q.where(Pago.fecha_pago >= datetime.combine(fd, dt_time.min))
            except ValueError:
                pass
        if fecha_hasta:
            try:
                fh = date.fromisoformat(fecha_hasta)
                q = q.where(Pago.fecha_pago <= datetime.combine(fh, dt_time.max))
                count_q = count_q.where(Pago.fecha_pago <= datetime.combine(fh, dt_time.max))
            except ValueError:
                pass
        if analista and analista.strip():
            q = q.join(Prestamo, Pago.prestamo_id == Prestamo.id).where(Prestamo.analista == analista.strip())
            count_q = count_q.join(Prestamo, Pago.prestamo_id == Prestamo.id).where(Prestamo.analista == analista.strip())
        total = db.scalar(count_q) or 0
        q = q.order_by(Pago.id.desc()).offset((page - 1) * per_page).limit(per_page)
        rows = db.execute(q).scalars().all()
        items = [_pago_to_response(r) for r in rows]
        total_pages = (total + per_page - 1) // per_page if total else 0
        return {
            "pagos": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }
    except Exception as e:
        logger.exception("Error en GET /pagos: %s", e)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{pago_id}", response_model=dict)
def obtener_pago(pago_id: int, db: Session = Depends(get_db)):
    """Obtiene un pago por ID desde la tabla pagos."""
    row = db.get(Pago, pago_id)
    if not row:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return _pago_to_response(row)


@router.post("", response_model=dict, status_code=201)
@router.post("/", include_in_schema=False, response_model=dict, status_code=201)
def crear_pago(payload: PagoCreate, db: Session = Depends(get_db)):
    """Crea un pago en la tabla pagos."""
    ref = (payload.numero_documento or "").strip() or "N/A"
    fecha_pago_ts = datetime.combine(payload.fecha_pago, dt_time.min)
    row = Pago(
        cedula_cliente=payload.cedula_cliente.strip(),
        prestamo_id=payload.prestamo_id,
        fecha_pago=fecha_pago_ts,
        monto_pagado=payload.monto_pagado,
        numero_documento=(payload.numero_documento or "").strip() or None,
        institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,
        estado="PENDIENTE",
        notas=payload.notas.strip() if payload.notas else None,
        referencia_pago=ref,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _pago_to_response(row)


@router.put("/{pago_id}", response_model=dict)
def actualizar_pago(pago_id: int, payload: PagoUpdate, db: Session = Depends(get_db)):
    """Actualiza un pago en la tabla pagos."""
    row = db.get(Pago, pago_id)
    if not row:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "notas" and v is not None:
            setattr(row, k, v.strip() or None)
        elif k == "institucion_bancaria" and v is not None:
            setattr(row, k, v.strip() or None)
        elif k == "numero_documento" and v is not None:
            setattr(row, k, v.strip())
        elif k == "cedula_cliente" and v is not None:
            setattr(row, k, v.strip())
        elif k == "fecha_pago" and v is not None:
            setattr(row, k, datetime.combine(v, dt_time.min) if isinstance(v, date) and not isinstance(v, datetime) else v)
        else:
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _pago_to_response(row)


@router.delete("/{pago_id}", status_code=204)
def eliminar_pago(pago_id: int, db: Session = Depends(get_db)):
    """Elimina un pago de la tabla pagos."""
    row = db.get(Pago, pago_id)
    if not row:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    db.delete(row)
    db.commit()
    return None


@router.get("/kpis")
def get_pagos_kpis(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    KPIs de pagos desde BD: cuotas_pendientes, clientes_en_mora,
    montoCobradoMes, saldoPorCobrar, clientesAlDia.
    """
    try:
        hoy = _hoy_local()
        cuotas_pendientes = db.scalar(
            select(func.count()).select_from(Cuota).where(Cuota.fecha_pago.is_(None))
        ) or 0
        subq = (
            select(Cuota.cliente_id)
            .where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < hoy)
            .distinct()
        )
        clientes_en_mora = db.scalar(select(func.count()).select_from(subq.subquery())) or 0
        inicio_mes = hoy.replace(day=1)
        monto_cobrado_mes = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
                Cuota.fecha_pago.isnot(None),
                func.date(Cuota.fecha_pago) >= inicio_mes,
                func.date(Cuota.fecha_pago) <= hoy,
            )
        ) or 0
        saldo_por_cobrar = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
                Cuota.fecha_pago.is_(None)
            )
        ) or 0
        clientes_con_prestamo = db.scalar(select(func.count(func.distinct(Prestamo.cliente_id))).select_from(Prestamo)) or 0
        clientes_al_dia = max(0, clientes_con_prestamo - clientes_en_mora)
        return {
            "cuotas_pendientes": cuotas_pendientes,
            "clientes_en_mora": clientes_en_mora,
            "montoCobradoMes": _safe_float(monto_cobrado_mes),
            "saldoPorCobrar": _safe_float(saldo_por_cobrar),
            "clientesAlDia": clientes_al_dia,
        }
    except Exception as e:
        logger.exception("Error en GET /pagos/kpis: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "cuotas_pendientes": 0,
            "clientes_en_mora": 0,
            "montoCobradoMes": 0.0,
            "saldoPorCobrar": 0.0,
            "clientesAlDia": 0,
        }


def _stats_conds_cuota(analista: Optional[str], concesionario: Optional[str], modelo: Optional[str]):
    """Condiciones base para filtrar cuotas por préstamo (analista/concesionario/modelo)."""
    conds = []
    if analista:
        conds.append(Prestamo.analista == analista)
    if concesionario:
        conds.append(Prestamo.concesionario == concesionario)
    if modelo:
        conds.append(Prestamo.modelo == modelo)
    return conds


@router.get("/stats")
def get_pagos_stats(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Estadísticas de pagos desde BD: total_pagos, total_pagado, pagos_por_estado,
    cuotas_pagadas, cuotas_pendientes, cuotas_atrasadas, pagos_hoy.
    """
    hoy = _hoy_local()
    use_filters = bool(analista or concesionario or modelo)

    def _q_cuotas():
        if use_filters:
            return select(Cuota).join(Prestamo, Cuota.prestamo_id == Prestamo.id).where(
                and_(*_stats_conds_cuota(analista, concesionario, modelo))
            )
        return select(Cuota)

    def _count(q):
        subq = q.subquery()
        return int(db.scalar(select(func.count()).select_from(subq)) or 0)

    try:
        # Cuotas pagadas / pendientes / atrasadas
        cuotas_pagadas = _count(_q_cuotas().where(Cuota.fecha_pago.isnot(None)))
        cuotas_pendientes = _count(_q_cuotas().where(Cuota.fecha_pago.is_(None)))
        cuotas_atrasadas = _count(
            _q_cuotas().where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < hoy)
        )
        # Total pagado: suma directa sobre Cuota (evita errores con subquery.c.monto)
        q_sum = select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
            Cuota.fecha_pago.isnot(None)
        )
        if use_filters:
            q_sum = q_sum.join(Prestamo, Cuota.prestamo_id == Prestamo.id).where(
                and_(*_stats_conds_cuota(analista, concesionario, modelo))
            )
        total_pagado = db.scalar(q_sum) or 0
        # Pagos hoy
        pagos_hoy = _count(
            _q_cuotas().where(
                Cuota.fecha_pago.isnot(None),
                func.date(Cuota.fecha_pago) == hoy,
            )
        )
        # Pagos por estado
        q_estado = select(Cuota.estado, func.count()).select_from(Cuota)
        if use_filters:
            q_estado = q_estado.join(Prestamo, Cuota.prestamo_id == Prestamo.id).where(
                and_(*_stats_conds_cuota(analista, concesionario, modelo))
            )
        q_estado = q_estado.group_by(Cuota.estado)
        rows_estado = db.execute(q_estado).all()
        pagos_por_estado = [{"estado": str(r[0]) if r[0] is not None else "N/A", "count": int(r[1])} for r in rows_estado]
        total_pagos = cuotas_pagadas + cuotas_pendientes
        return {
            "total_pagos": total_pagos,
            "total_pagado": _safe_float(total_pagado),
            "pagos_por_estado": pagos_por_estado,
            "cuotas_pagadas": cuotas_pagadas,
            "cuotas_pendientes": cuotas_pendientes,
            "cuotas_atrasadas": cuotas_atrasadas,
            "pagos_hoy": pagos_hoy,
        }
    except Exception as e:
        logger.exception("Error en GET /pagos/stats: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return {
            "total_pagos": 0,
            "total_pagado": 0.0,
            "pagos_por_estado": [],
            "cuotas_pagadas": 0,
            "cuotas_pendientes": 0,
            "cuotas_atrasadas": 0,
            "pagos_hoy": 0,
        }
