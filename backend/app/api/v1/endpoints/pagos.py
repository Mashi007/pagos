"""
Endpoints de pagos. Datos reales desde BD.
- Tabla pagos: GET/POST/PUT/DELETE /pagos/ (listado y CRUD para /pagos/pagos).
- GET /pagos/kpis, /stats, /ultimos, /exportar/errores; POST /upload, /conciliacion/upload, /{id}/aplicar-cuotas.
"""
import calendar
import io
import logging
from datetime import date, datetime, time as dt_time
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from fastapi.responses import Response
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
        # Orden: más reciente primero (fecha_pago desc, luego id desc)
        q = q.order_by(Pago.fecha_pago.desc(), Pago.id.desc()).offset((page - 1) * per_page).limit(per_page)
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


@router.get("/ultimos", response_model=dict)
def get_ultimos_pagos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cedula: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Resumen de últimos pagos por cédula (para PagosListResumen).
    Items: cedula, pago_id, prestamo_id, estado_pago, monto_ultimo_pago, fecha_ultimo_pago,
    cuotas_atrasadas, saldo_vencido, total_prestamos.
    """
    hoy = _hoy_local()
    # Subconsulta: cédulas distintas ordenadas por pago más reciente (más actual a más antiguo)
    subq = (
        select(
            Pago.cedula_cliente,
            func.max(Pago.fecha_pago).label("max_fecha"),
            func.max(Pago.id).label("max_id"),
        )
        .where(
            Pago.cedula_cliente.isnot(None),
            Pago.cedula_cliente != "",
        )
        .group_by(Pago.cedula_cliente)
    )
    if cedula and cedula.strip():
        subq = subq.where(Pago.cedula_cliente.ilike(f"%{cedula.strip()}%"))
    subq = subq.subquery()
    total_cedulas = db.scalar(select(func.count()).select_from(subq)) or 0
    total_pages = (total_cedulas + per_page - 1) // per_page if total_cedulas else 0
    q_cedulas = (
        select(subq.c.cedula_cliente)
        .order_by(subq.c.max_fecha.desc(), subq.c.max_id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    cedulas_page = db.execute(q_cedulas).scalars().all()
    cedulas_list = [c[0] for c in cedulas_page if c[0]]
    items = []
    for ced in cedulas_list:
        row_ultimo = db.execute(
            select(Pago)
            .where(Pago.cedula_cliente == ced)
            .order_by(Pago.id.desc())
            .limit(1)
        ).first()
        ultimo = row_ultimo[0] if row_ultimo else None
        if not ultimo:
            continue
        if estado and estado.strip() and (ultimo.estado or "").upper() != estado.strip().upper():
            continue
        prestamo_id = ultimo.prestamo_id
        # Cuotas atrasadas y saldo vencido para este cliente (por prestamos con esa cedula)
        prestamos_cliente = db.execute(
            select(Prestamo.id).select_from(Prestamo).join(Cliente, Prestamo.cliente_id == Cliente.id).where(Cliente.cedula == ced)
        ).scalars().all()
        prestamo_ids = [p[0] for p in prestamos_cliente]
        cuotas_atrasadas = 0
        saldo_vencido = 0.0
        if prestamo_ids:
            q_mora = (
                select(func.count(), func.coalesce(func.sum(Cuota.monto), 0))
                .select_from(Cuota)
                .where(
                    Cuota.prestamo_id.in_(prestamo_ids),
                    Cuota.fecha_pago.is_(None),
                    Cuota.fecha_vencimiento < hoy,
                )
            )
            row_mora = db.execute(q_mora).first()
            if row_mora:
                cuotas_atrasadas = int(row_mora[0] or 0)
                saldo_vencido = _safe_float(row_mora[1])
        total_prestamos = len(prestamo_ids)
        items.append({
            "cedula": ced,
            "pago_id": ultimo.id,
            "prestamo_id": prestamo_id,
            "estado_pago": ultimo.estado or "PENDIENTE",
            "monto_ultimo_pago": _safe_float(ultimo.monto_pagado),
            "fecha_ultimo_pago": ultimo.fecha_pago.date().isoformat() if hasattr(ultimo.fecha_pago, "date") and ultimo.fecha_pago else (ultimo.fecha_pago.isoformat()[:10] if ultimo.fecha_pago else None),
            "cuotas_atrasadas": cuotas_atrasadas,
            "saldo_vencido": saldo_vencido,
            "total_prestamos": total_prestamos,
        })
    return {
        "items": items,
        "total": total_cedulas,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


@router.post("/upload", response_model=dict)
async def upload_excel_pagos(
    file: UploadFile = File(..., alias="file"),
    db: Session = Depends(get_db),
):
    """
    Carga masiva de pagos desde Excel.
    Formato esperado: columnas compatibles con Pago (cedula, prestamo_id, fecha_pago, monto_pagado, numero_documento, etc.).
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Debe subir un archivo Excel (.xlsx o .xls)")
    try:
        import openpyxl
        content = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        if not ws:
            return {"message": "Archivo sin hojas", "registros_procesados": 0, "errores": []}
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        registros = 0
        errores = []
        for i, row in enumerate(rows):
            if not row or all(cell is None for cell in row):
                continue
            try:
                cedula = str(row[0]).strip() if row[0] is not None else ""
                prestamo_id = int(row[1]) if row[1] is not None else None
                fecha_val = row[2]
                monto = float(row[3]) if row[3] is not None else 0
                numero_doc = str(row[4]).strip() if len(row) > 4 and row[4] is not None else ""
                if not cedula or monto <= 0:
                    continue
                if isinstance(fecha_val, datetime):
                    fecha_pago = fecha_val.date()
                elif isinstance(fecha_val, date):
                    fecha_pago = fecha_val
                else:
                    fecha_pago = date.today()
                p = Pago(
                    cedula_cliente=cedula,
                    prestamo_id=prestamo_id,
                    fecha_pago=datetime.combine(fecha_pago, dt_time.min),
                    monto_pagado=monto,
                    numero_documento=numero_doc or None,
                    estado="PENDIENTE",
                    referencia_pago=numero_doc or "Carga",
                )
                db.add(p)
                registros += 1
            except Exception as e:
                errores.append(f"Fila {i + 2}: {e}")
        db.commit()
        return {
            "message": "Carga finalizada",
            "registros_procesados": registros,
            "errores": errores[:50],
        }
    except Exception as e:
        db.rollback()
        logger.exception("Error upload Excel pagos: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/conciliacion/upload", response_model=dict)
async def upload_conciliacion(
    file: UploadFile = File(..., alias="file"),
    db: Session = Depends(get_db),
):
    """
    Carga archivo de conciliación (Excel: Fecha de Depósito, Número de Documento).
    Marca pagos encontrados por numero_documento como conciliados.
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Debe subir un archivo Excel (.xlsx o .xls)")
    try:
        import openpyxl
        content = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        if not ws:
            return {
                "pagos_conciliados": 0,
                "pagos_no_encontrados": 0,
                "documentos_no_encontrados": [],
                "errores": 0,
                "errores_detalle": ["Archivo sin datos"],
            }
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        ahora = datetime.now(ZoneInfo(TZ_NEGOCIO))
        pagos_conciliados = 0
        documentos_no_encontrados = []
        errores_detalle = []
        for i, row in enumerate(rows):
            if not row or (row[0] is None and row[1] is None):
                continue
            try:
                numero_doc = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
                if not numero_doc:
                    continue
                pago_row = db.execute(
                    select(Pago).where(Pago.numero_documento == numero_doc).limit(1)
                ).first()
                if not pago_row:
                    documentos_no_encontrados.append(numero_doc)
                    continue
                pago = pago_row[0]
                pago.conciliado = True
                pago.fecha_conciliacion = ahora
                pagos_conciliados += 1
            except Exception as e:
                errores_detalle.append(f"Fila {i + 2}: {e}")
        db.commit()
        return {
            "pagos_conciliados": pagos_conciliados,
            "pagos_no_encontrados": len(documentos_no_encontrados),
            "documentos_no_encontrados": documentos_no_encontrados[:100],
            "errores": len(errores_detalle),
            "errores_detalle": errores_detalle[:50],
        }
    except Exception as e:
        db.rollback()
        logger.exception("Error upload conciliación: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/exportar/errores")
def exportar_pagos_errores(db: Session = Depends(get_db)):
    """Exporta Excel de pagos con errores (no conciliados o estado pendiente/revisar)."""
    try:
        import openpyxl
        q = select(Pago).where(
            (Pago.conciliado.is_(False)) | (Pago.conciliado.is_(None)) | (Pago.estado.in_(["PENDIENTE", "ATRASADO", "REVISAR"]))
        ).order_by(Pago.id.desc())
        rows = db.execute(q).scalars().all()
        pagos_list = [r[0] for r in rows]
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Pagos con errores"
        ws.append(["ID", "Cédula", "Préstamo ID", "Fecha pago", "Monto", "Nº documento", "Estado", "Conciliado", "Notas"])
        for p in pagos_list:
            fp = p.fecha_pago
            fecha_str = fp.date().isoformat() if hasattr(fp, "date") and fp else (fp.isoformat()[:10] if fp else "")
            ws.append([
                p.id,
                p.cedula_cliente or "",
                p.prestamo_id or "",
                fecha_str,
                float(p.monto_pagado) if p.monto_pagado is not None else 0,
                p.numero_documento or "",
                p.estado or "",
                "Sí" if p.conciliado else "No",
                (p.notas or "")[:200],
            ])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=pagos_con_errores.xlsx"},
        )
    except Exception as e:
        logger.exception("Error exportar pagos errores: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/kpis")
def get_pagos_kpis(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    KPIs de pagos para el mes en curso:
    1. montoACobrarMes: cuánto dinero debería cobrarse en el mes en transcurso (cuotas con vencimiento en el mes).
    2. montoCobradoMes: cuánto dinero se ha cobrado = pagado en el mes.
    3. morosidadMensualPorcentaje: morosidad mensual en % (saldo vencido no cobrado / cartera pendiente * 100).
    """
    try:
        hoy = _hoy_local()
        inicio_mes = hoy.replace(day=1)
        _, ultimo_dia = calendar.monthrange(hoy.year, hoy.month)
        fin_mes = inicio_mes.replace(day=ultimo_dia)

        # 1) Monto a cobrar en el mes en transcurso: suma de cuotas con fecha_vencimiento en este mes
        monto_a_cobrar_mes = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
                Cuota.fecha_vencimiento >= inicio_mes,
                Cuota.fecha_vencimiento <= fin_mes,
            )
        ) or 0

        # 2) Monto cobrado = pagado en el mes: suma de cuotas pagadas con fecha_pago en el mes
        monto_cobrado_mes = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
                Cuota.fecha_pago.isnot(None),
                func.date(Cuota.fecha_pago) >= inicio_mes,
                func.date(Cuota.fecha_pago) <= hoy,
            )
        ) or 0

        # 3) Morosidad mensual %: saldo vencido (no cobrado) / cartera pendiente * 100
        saldo_vencido = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento < hoy,
            )
        ) or 0
        cartera_pendiente = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0)).select_from(Cuota).where(
                Cuota.fecha_pago.is_(None)
            )
        ) or 0
        morosidad_porcentaje = (
            (_safe_float(saldo_vencido) / _safe_float(cartera_pendiente) * 100.0)
            if cartera_pendiente and _safe_float(cartera_pendiente) > 0
            else 0.0
        )
        # Compatibilidad: clientes en mora / al día y saldo por cobrar (otros módulos)
        subq = (
            select(Cuota.cliente_id)
            .where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < hoy)
            .distinct()
        )
        clientes_en_mora = db.scalar(select(func.count()).select_from(subq.subquery())) or 0
        clientes_con_prestamo = db.scalar(select(func.count(func.distinct(Prestamo.cliente_id))).select_from(Prestamo)) or 0
        clientes_al_dia = max(0, clientes_con_prestamo - clientes_en_mora)

        return {
            "montoACobrarMes": _safe_float(monto_a_cobrar_mes),
            "montoCobradoMes": _safe_float(monto_cobrado_mes),
            "morosidadMensualPorcentaje": round(morosidad_porcentaje, 2),
            "mes": hoy.month,
            "año": hoy.year,
            "saldoPorCobrar": _safe_float(cartera_pendiente),
            "clientesEnMora": clientes_en_mora,
            "clientesAlDia": clientes_al_dia,
        }
    except Exception as e:
        logger.exception("Error en GET /pagos/kpis: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        hoy = _hoy_local()
        return {
            "montoACobrarMes": 0.0,
            "montoCobradoMes": 0.0,
            "morosidadMensualPorcentaje": 0.0,
            "mes": hoy.month,
            "año": hoy.year,
            "saldoPorCobrar": 0.0,
            "clientesEnMora": 0,
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


@router.post("/{pago_id}/aplicar-cuotas", response_model=dict)
def aplicar_pago_a_cuotas(pago_id: int, db: Session = Depends(get_db)):
    """
    Aplica el monto del pago a cuotas pendientes del préstamo (por orden de número de cuota).
    Marca cuotas con fecha_pago y estado PAGADO hasta agotar el monto.
    """
    pago = db.get(Pago, pago_id)
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    prestamo_id = pago.prestamo_id
    if not prestamo_id:
        return {
            "success": False,
            "cuotas_completadas": 0,
            "message": "El pago no tiene préstamo asociado.",
        }
    monto_restante = float(pago.monto_pagado) if pago.monto_pagado else 0
    if monto_restante <= 0:
        return {"success": True, "cuotas_completadas": 0, "message": "Monto del pago es cero."}
    fecha_pago_date = pago.fecha_pago.date() if hasattr(pago.fecha_pago, "date") and pago.fecha_pago else date.today()
    cuotas_pendientes = (
        db.execute(
            select(Cuota)
            .where(Cuota.prestamo_id == prestamo_id, Cuota.fecha_pago.is_(None))
            .order_by(Cuota.numero_cuota)
        )
    ).scalars().all()
    cuotas_completadas = 0
    for row in cuotas_pendientes:
        c = row[0]
        monto_cuota = float(c.monto) if c.monto is not None else 0
        if monto_restante <= 0 or monto_cuota <= 0:
            break
        c.fecha_pago = fecha_pago_date
        c.estado = "PAGADO"
        cuotas_completadas += 1
        monto_restante -= monto_cuota
    db.commit()
    return {
        "success": True,
        "cuotas_completadas": cuotas_completadas,
        "message": f"Se aplicó el pago a {cuotas_completadas} cuota(s).",
    }
