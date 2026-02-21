"""
Endpoints de pagos. Datos reales desde BD.
- Tabla pagos: GET/POST/PUT/DELETE /pagos/ (listado y CRUD para /pagos/pagos).
- GET /pagos/kpis, /stats, /ultimos; POST /upload, /conciliacion/upload, /{id}/aplicar-cuotas.
"""
import calendar
import io
import logging
import re
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from sqlalchemy import and_, func, or_, select
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
    """Fecha de hoy en la zona horaria del negocio (evita que servidor UTC desfase el dÃ­a)."""
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
    conciliado: Optional[str] = Query(None, description="si=conciliados, no=no conciliados, vacío=todos"),
    sin_prestamo: Optional[str] = Query(None, description="si=solo pagos sin crédito asignado (prestamo_id NULL)"),
    db: Session = Depends(get_db),
):
    """Listado paginado desde la tabla pagos. Filtros: cedula, estado, fecha_desde, fecha_hasta, analista, conciliado, sin_prestamo."""
    try:
        q = select(Pago)
        count_q = select(func.count()).select_from(Pago)
        if sin_prestamo and sin_prestamo.strip().lower() == "si":
            q = q.where(Pago.prestamo_id.is_(None))
            count_q = count_q.where(Pago.prestamo_id.is_(None))
        if conciliado and conciliado.strip().lower() == "si":
            q = q.where(Pago.conciliado == True)
            count_q = count_q.where(Pago.conciliado == True)
        elif conciliado and conciliado.strip().lower() == "no":
            q = q.where(or_(Pago.conciliado == False, Pago.conciliado.is_(None)))
            count_q = count_q.where(or_(Pago.conciliado == False, Pago.conciliado.is_(None)))
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
        # Orden: mÃ¡s reciente primero (fecha_pago desc, luego id desc)
        q = q.order_by(Pago.fecha_registro.desc().nullslast(), Pago.id.desc()).offset((page - 1) * per_page).limit(per_page)
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
    Resumen de Ãºltimos pagos por cÃ©dula (para PagosListResumen).
    Items: cedula, pago_id, prestamo_id, estado_pago, monto_ultimo_pago, fecha_ultimo_pago,
    cuotas_atrasadas, saldo_vencido, total_prestamos.
    """
    hoy = _hoy_local()
    # Subconsulta: cÃ©dulas distintas ordenadas por pago mÃ¡s reciente (mÃ¡s actual a mÃ¡s antiguo)
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
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB (alineado con frontend)
    MAX_ROWS = 10000  # Maximo filas de datos (alineado con frontend)
    try:
        import openpyxl
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"El archivo es demasiado grande. Tamano maximo: {MAX_FILE_SIZE // (1024 * 1024)} MB.",
            )
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        if not ws:
            return {"message": "Archivo sin hojas", "registros_procesados": 0, "errores": []}
        rows = list(ws.iter_rows(min_row=2, values_only=True))
        if len(rows) > MAX_ROWS:
            raise HTTPException(
                status_code=400,
                detail=f"El archivo tiene demasiadas filas ({len(rows)}). MÃ¡ximo permitido: {MAX_ROWS}.",
            )

        def _looks_like_cedula(v: Any) -> bool:
            if v is None:
                return False
            s = str(v).strip()
            return bool(re.match(r"^[VJ]\d{7,9}$", s, re.IGNORECASE))

        def _looks_like_date(v: Any) -> bool:
            if v is None:
                return False
            if isinstance(v, (datetime, date)):
                return True
            s = str(v).strip()
            return bool(re.search(r"\d{1,4}[-\/]\d{1,2}[-\/]\d{1,4}", s))

        def _parse_fecha(v: Any) -> date:
            if isinstance(v, datetime):
                return v.date()
            if isinstance(v, date):
                return v
            if v is None:
                return date.today()
            s = str(v).strip()
            for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(s[:10], fmt).date()
                except ValueError:
                    continue
            return date.today()

        registros = 0
        filas_omitidas = 0  # cÃ©dula vacÃ­a o monto <= 0
        errores = []
        errores_detalle = []
        numeros_doc_en_lote: set[str] = set()  # NÂº documento no puede repetirse ni en archivo ni en BD
        for i, row in enumerate(rows):
            if not row or all(cell is None for cell in row):
                continue
            try:
                cedula = ""
                prestamo_id: Optional[int] = None
                fecha_val: Any = None
                monto = 0.0
                numero_doc = ""
                # Formato alternativo: Fecha, CÃ©dula, Cantidad, Documento (ej. Excel con columnas A=Fecha, B=CÃ©dula, C=Cantidad, D=Documento)
                if len(row) >= 4 and _looks_like_date(row[0]) and _looks_like_cedula(row[1]):
                    cedula = str(row[1]).strip()
                    try:
                        monto = float(row[2]) if row[2] is not None else 0.0
                    except (TypeError, ValueError):
                        monto = 0.0
                    fecha_val = row[0]
                    numero_doc = str(row[3]).strip() if row[3] is not None else ""
                else:
                    # Formato estÃ¡ndar: CÃ©dula, ID PrÃ©stamo, Fecha, Monto, NÃºmero documento
                    cedula = str(row[0]).strip() if row[0] is not None else ""
                    _val_prestamo = row[1] if len(row) > 1 else None
                    if _val_prestamo is None:
                        prestamo_id = None
                    else:
                        _s = str(_val_prestamo).strip()
                        prestamo_id = int(_s) if (_s and _s.isdigit()) else None
                    fecha_val = row[2] if len(row) > 2 else None
                    _monto_raw = row[3] if len(row) > 3 else None
                    try:
                        monto = float(_monto_raw) if _monto_raw is not None else 0.0
                    except (TypeError, ValueError):
                        monto = 0.0
                    numero_doc = str(row[4]).strip() if len(row) > 4 and row[4] is not None else ""

                if not cedula or monto <= 0:
                    filas_omitidas += 1
                    continue
                numero_doc_norm = (numero_doc or "").strip() or None
                if numero_doc_norm:
                    if numero_doc_norm in numeros_doc_en_lote:
                        datos_fila = {"cedula": cedula, "prestamo_id": prestamo_id, "fecha_pago": fecha_val, "monto_pagado": monto, "numero_documento": numero_doc or ""}
                        errores.append(f"Fila {i + 2}: NÂº documento duplicado en este archivo")
                        errores_detalle.append({"fila": i + 2, "cedula": cedula, "error": "NÂº documento duplicado en este archivo. El NÂº documento no puede repetirse.", "datos": datos_fila})
                        continue
                    if _numero_documento_ya_existe(db, numero_doc_norm):
                        datos_fila = {"cedula": cedula, "prestamo_id": prestamo_id, "fecha_pago": fecha_val, "monto_pagado": monto, "numero_documento": numero_doc or ""}
                        errores.append(f"Fila {i + 2}: Ya existe un pago con ese NÂº de documento")
                        errores_detalle.append({"fila": i + 2, "cedula": cedula, "error": "Ya existe un pago con ese NÂº de documento. El NÂº documento no puede repetirse.", "datos": datos_fila})
                        continue

                # Si la persona tiene más de un préstamo, prestamo_id es obligatorio
                if prestamo_id is None and cedula.strip():
                    count_prestamos = db.scalar(
                        select(func.count())
                        .select_from(Prestamo)
                        .join(Cliente, Prestamo.cliente_id == Cliente.id)
                        .where(Cliente.cedula == cedula.strip())
                    ) or 0
                    if count_prestamos > 1:
                        datos_fila = {"cedula": cedula, "prestamo_id": prestamo_id, "fecha_pago": fecha_val, "monto_pagado": monto, "numero_documento": numero_doc or ""}
                        errores.append(f"Fila {i + 2}: La cédula {cedula} tiene {count_prestamos} préstamos. Debe indicar el ID del préstamo.")
                        errores_detalle.append({
                            "fila": i + 2,
                            "cedula": cedula,
                            "error": f"Esta persona tiene {count_prestamos} préstamos. Debe indicar el ID del préstamo (columna 2) al que aplica este pago.",
                            "datos": datos_fila,
                        })
                        continue

                fecha_pago = _parse_fecha(fecha_val)
                p = Pago(
                    cedula_cliente=cedula,
                    prestamo_id=prestamo_id,
                    fecha_pago=datetime.combine(fecha_pago, dt_time.min),
                    monto_pagado=monto,
                    numero_documento=numero_doc_norm,
                    estado="PENDIENTE",
                    referencia_pago=(numero_doc_norm or numero_doc or "").strip() or "Carga",
                )
                db.add(p)
                registros += 1
                if numero_doc_norm:
                    numeros_doc_en_lote.add(numero_doc_norm)
            except Exception as e:
                msg = str(e)
                errores.append(f"Fila {i + 2}: {msg}")
                datos_fila = {}
                if len(row) > 0:
                    datos_fila["cedula"] = row[0]
                if len(row) > 1:
                    datos_fila["prestamo_id"] = row[1]
                if len(row) > 2:
                    datos_fila["fecha_pago"] = row[2]
                if len(row) > 3:
                    datos_fila["monto_pagado"] = row[3]
                if len(row) > 4:
                    datos_fila["numero_documento"] = row[4]
                errores_detalle.append({
                    "fila": i + 2,
                    "cedula": str(datos_fila.get("cedula", "")),
                    "error": msg,
                    "datos": datos_fila,
                })
        db.commit()
        errores_limit = 50
        errores_detalle_limit = 100
        total_errores = len(errores)
        total_errores_detalle = len(errores_detalle)
        return {
            "message": "Carga finalizada",
            "registros_procesados": registros,
            "filas_omitidas": filas_omitidas,
            "errores": errores[:errores_limit],
            "errores_detalle": errores_detalle[:errores_detalle_limit],
            "errores_total": total_errores,
            "errores_detalle_total": total_errores_detalle,
            "errores_truncados": total_errores > errores_limit or total_errores_detalle > errores_detalle_limit,
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
    Carga archivo de conciliaciÃ³n (Excel: Fecha de DepÃ³sito, NÃºmero de Documento).
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
        logger.exception("Error upload conciliaciÃ³n: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/kpis")
def get_pagos_kpis(
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    KPIs de pagos para el mes en curso:
    1. montoACobrarMes: cuÃ¡nto dinero deberÃ­a cobrarse en el mes en transcurso (cuotas con vencimiento en el mes).
    2. montoCobradoMes: cuÃ¡nto dinero se ha cobrado = pagado en el mes.
    3. morosidadMensualPorcentaje: pago vencido mensual en % (cuotas vencidas no cobradas / cartera * 100).
       Concepto: vencido = fecha_vencimiento < hoy; moroso = 90+ días de atraso.
    """
    try:
        hoy = _hoy_local()
        inicio_mes = hoy.replace(day=1)
        _, ultimo_dia = calendar.monthrange(hoy.year, hoy.month)
        fin_mes = inicio_mes.replace(day=ultimo_dia)

        # Condiciones base: solo clientes ACTIVOS
        conds_activo = [
            Cuota.prestamo_id == Prestamo.id,
            Prestamo.cliente_id == Cliente.id,
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
        ]

        # 1) Monto a cobrar en el mes en transcurso (solo clientes ACTIVOS)
        monto_a_cobrar_mes = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                and_(*conds_activo),
                Cuota.fecha_vencimiento >= inicio_mes,
                Cuota.fecha_vencimiento <= fin_mes,
            )
        ) or 0

        # 2) Monto cobrado = pagado en el mes (solo clientes ACTIVOS)
        monto_cobrado_mes = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                and_(*conds_activo),
                Cuota.fecha_pago.isnot(None),
                func.date(Cuota.fecha_pago) >= inicio_mes,
                func.date(Cuota.fecha_pago) <= hoy,
            )
        ) or 0

        # 3) Morosidad mensual % (solo clientes ACTIVOS). Solo cuotas ya vencidas (fecha_vencimiento < hoy).
        total_vencido_mes = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                and_(*conds_activo),
                Cuota.fecha_vencimiento >= inicio_mes,
                Cuota.fecha_vencimiento <= fin_mes,
                Cuota.fecha_vencimiento < hoy,
            )
        ) or 0
        no_cobrado_mes = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                and_(*conds_activo),
                Cuota.fecha_vencimiento >= inicio_mes,
                Cuota.fecha_vencimiento <= fin_mes,
                Cuota.fecha_vencimiento < hoy,
                Cuota.fecha_pago.is_(None),
            )
        ) or 0
        morosidad_porcentaje = (
            (_safe_float(no_cobrado_mes) / _safe_float(total_vencido_mes) * 100.0)
            if total_vencido_mes and _safe_float(total_vencido_mes) > 0
            else 0.0
        )
        cartera_pendiente = db.scalar(
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*conds_activo), Cuota.fecha_pago.is_(None))
        ) or 0
        # Compatibilidad: clientes en mora / al dÃ­a (solo clientes ACTIVOS)
        subq = (
            select(Prestamo.cliente_id)
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                and_(*conds_activo),
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento < hoy,
            )
            .distinct()
        )
        clientes_en_mora = db.scalar(select(func.count()).select_from(subq.subquery())) or 0
        clientes_con_prestamo = db.scalar(
            select(func.count(func.distinct(Prestamo.cliente_id)))
            .select_from(Prestamo)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Cliente.estado == "ACTIVO", Prestamo.estado == "APROBADO")
        ) or 0
        clientes_al_dia = max(0, clientes_con_prestamo - clientes_en_mora)

        return {
            "montoACobrarMes": _safe_float(monto_a_cobrar_mes),
            "montoCobradoMes": _safe_float(monto_cobrado_mes),
            "morosidadMensualPorcentaje": round(morosidad_porcentaje, 2),
            "mes": hoy.month,
            "aÃ±o": hoy.year,
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
            "aÃ±o": hoy.year,
            "saldoPorCobrar": 0.0,
            "clientesEnMora": 0,
            "clientesAlDia": 0,
        }


def _stats_conds_cuota(analista: Optional[str], concesionario: Optional[str], modelo: Optional[str]):
    """Condiciones base para filtrar cuotas por prÃ©stamo (solo clientes ACTIVOS + analista/concesionario/modelo)."""
    conds = [
        Cuota.prestamo_id == Prestamo.id,
        Prestamo.cliente_id == Cliente.id,
        Cliente.estado == "ACTIVO",
        Prestamo.estado == "APROBADO",
    ]
    if analista:
        conds.append(Prestamo.analista == analista)
    if concesionario:
        conds.append(Prestamo.concesionario == concesionario)
    if modelo:
        conds.append(Prestamo.modelo_vehiculo == modelo)
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
    EstadÃ­sticas de pagos desde BD (solo clientes ACTIVOS): total_pagos, total_pagado, pagos_por_estado,
    cuotas_pagadas, cuotas_pendientes, cuotas_atrasadas, pagos_hoy.
    """
    hoy = _hoy_local()
    use_filters = bool(analista or concesionario or modelo)

    def _q_cuotas():
        return (
            select(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*_stats_conds_cuota(analista, concesionario, modelo)))
        )

    def _count(q):
        subq = q.subquery()
        return int(db.scalar(select(func.count()).select_from(subq)) or 0)

    try:
        # Cuotas pagadas / pendientes / atrasadas (solo clientes ACTIVOS)
        cuotas_pagadas = _count(_q_cuotas().where(Cuota.fecha_pago.isnot(None)))
        cuotas_pendientes = _count(_q_cuotas().where(Cuota.fecha_pago.is_(None)))
        cuotas_atrasadas = _count(
            _q_cuotas().where(Cuota.fecha_pago.is_(None), Cuota.fecha_vencimiento < hoy)
        )
        # Total pagado (solo clientes ACTIVOS)
        q_sum = (
            select(func.coalesce(func.sum(Cuota.monto), 0))
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*_stats_conds_cuota(analista, concesionario, modelo), Cuota.fecha_pago.isnot(None))
            )
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
        q_estado = (
            select(Cuota.estado, func.count())
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(and_(*_stats_conds_cuota(analista, concesionario, modelo)))
            .group_by(Cuota.estado)
        )
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


def _numero_documento_ya_existe(
    db: Session, numero_documento: Optional[str], exclude_pago_id: Optional[int] = None
) -> bool:
    """Comprueba si ya existe un pago con ese NÂº documento (no se permite repetir)."""
    num = (numero_documento or "").strip() or None
    if not num:
        return False
    q = select(Pago.id).where(Pago.numero_documento == num)
    if exclude_pago_id is not None:
        q = q.where(Pago.id != exclude_pago_id)
    return db.scalar(q) is not None


@router.post("", response_model=dict, status_code=201)
@router.post("/", include_in_schema=False, response_model=dict, status_code=201)
def crear_pago(payload: PagoCreate, db: Session = Depends(get_db)):
    """Crea un pago en la tabla pagos. NÂº documento no puede repetirse."""
    num_doc = (payload.numero_documento or "").strip() or None
    if num_doc and _numero_documento_ya_existe(db, num_doc):
        raise HTTPException(
            status_code=409,
            detail="Ya existe un pago con ese NÂº de documento. El NÂº documento no puede repetirse.",
        )
    ref = num_doc or "N/A"
    fecha_pago_ts = datetime.combine(payload.fecha_pago, dt_time.min)
    conciliado = payload.conciliado if payload.conciliado is not None else False
    row = Pago(
        cedula_cliente=payload.cedula_cliente.strip(),
        prestamo_id=payload.prestamo_id,
        fecha_pago=fecha_pago_ts,
        monto_pagado=payload.monto_pagado,
        numero_documento=num_doc,
        institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,
        estado="PENDIENTE",
        notas=payload.notas.strip() if payload.notas else None,
        referencia_pago=ref,
        conciliado=conciliado,
        fecha_conciliacion=datetime.now(ZoneInfo(TZ_NEGOCIO)) if conciliado else None,
        verificado_concordancia="SI" if conciliado else "NO",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    # Reglas de negocio: al conciliar con préstamo, aplicar pago a cuotas
    if conciliado and row.prestamo_id and float(row.monto_pagado or 0) > 0:
        try:
            cuotas_completadas, cuotas_parciales = _aplicar_pago_a_cuotas_interno(row, db)
            if cuotas_completadas > 0 or cuotas_parciales > 0:
                row.estado = "PAGADO"
            db.commit()
            db.refresh(row)
        except Exception as e:
            logger.warning("Al crear pago conciliado, no se pudo aplicar a cuotas: %s", e)
            db.rollback()
    return _pago_to_response(row)


@router.put("/{pago_id}", response_model=dict)
def actualizar_pago(pago_id: int, payload: PagoUpdate, db: Session = Depends(get_db)):
    """Actualiza un pago en la tabla pagos. NÂº documento no puede repetirse."""
    row = db.get(Pago, pago_id)
    if not row:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "numero_documento" in data and data["numero_documento"] is not None:
        num_doc = (data["numero_documento"] or "").strip() or None
        if num_doc and _numero_documento_ya_existe(db, num_doc, exclude_pago_id=pago_id):
            raise HTTPException(
                status_code=409,
                detail="Ya existe otro pago con ese NÂº de documento. El NÂº documento no puede repetirse.",
            )
    for k, v in data.items():
        if k == "notas" and v is not None:
            setattr(row, k, v.strip() or None)
        elif k == "institucion_bancaria" and v is not None:
            setattr(row, k, v.strip() or None)
        elif k == "numero_documento" and v is not None:
            setattr(row, k, (v or "").strip() or None)
        elif k == "cedula_cliente" and v is not None:
            setattr(row, k, v.strip())
        elif k == "fecha_pago" and v is not None:
            setattr(row, k, datetime.combine(v, dt_time.min) if isinstance(v, date) and not isinstance(v, datetime) else v)
        elif k == "conciliado" and v is not None:
            row.conciliado = bool(v)
            row.fecha_conciliacion = datetime.now(ZoneInfo(TZ_NEGOCIO)) if v else None
            row.verificado_concordancia = "SI" if v else "NO"
        elif k == "verificado_concordancia" and v is not None:
            val = (v or "").strip().upper()
            row.verificado_concordancia = val if val in ("SI", "NO") else ("" if v == "" else str(v)[:10])
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


def _estado_cuota_por_cobertura(total_pagado: float, monto_cuota: float, fecha_vencimiento: date) -> str:
    """Determina estado según cobertura y fecha de vencimiento. Reglas de negocio."""
    hoy = _hoy_local()
    if total_pagado >= monto_cuota - 0.01:
        return "PAGADO"
    if total_pagado > 0:
        return "PAGO_ADELANTADO" if fecha_vencimiento > hoy else "PENDIENTE"
    return "PENDIENTE"


def _aplicar_pago_a_cuotas_interno(pago: Pago, db: Session) -> tuple[int, int]:
    """
    Aplica el monto del pago a cuotas del préstamo. Reglas de negocio.
    Retorna (cuotas_completadas, cuotas_parciales). No hace commit.
    """
    prestamo_id = pago.prestamo_id
    if not prestamo_id:
        return 0, 0
    monto_restante = float(pago.monto_pagado) if pago.monto_pagado else 0
    if monto_restante <= 0:
        return 0, 0
    fecha_pago_date = pago.fecha_pago.date() if hasattr(pago.fecha_pago, "date") and pago.fecha_pago else date.today()
    hoy = _hoy_local()
    cuotas_pendientes = (
        db.execute(
            select(Cuota)
            .where(
                Cuota.prestamo_id == prestamo_id,
                Cuota.fecha_pago.is_(None),
                or_(Cuota.total_pagado.is_(None), Cuota.total_pagado < Cuota.monto),
            )
            .order_by(Cuota.numero_cuota)
        )
    ).scalars().all()
    cuotas_completadas = 0
    cuotas_parciales = 0
    for c in cuotas_pendientes:
        monto_cuota = float(c.monto) if c.monto is not None else 0
        total_pagado_actual = float(c.total_pagado or 0)
        monto_necesario = monto_cuota - total_pagado_actual
        if monto_restante <= 0 or monto_cuota <= 0:
            break
        a_aplicar = min(monto_restante, monto_necesario)
        if a_aplicar <= 0:
            continue
        nuevo_total = total_pagado_actual + a_aplicar
        c.total_pagado = Decimal(str(round(nuevo_total, 2)))
        c.pago_id = pago.id
        fecha_venc = c.fecha_vencimiento
        if fecha_venc is not None and hasattr(fecha_venc, "date"):
            fecha_venc = fecha_venc.date()
        fecha_venc = fecha_venc or hoy
        if nuevo_total >= monto_cuota - 0.01:
            c.fecha_pago = fecha_pago_date
            c.estado = "PAGADO"
            cuotas_completadas += 1
        else:
            c.estado = _estado_cuota_por_cobertura(nuevo_total, monto_cuota, fecha_venc)
            cuotas_parciales += 1
        monto_restante -= a_aplicar
    return cuotas_completadas, cuotas_parciales


@router.post("/{pago_id}/aplicar-cuotas", response_model=dict)
def aplicar_pago_a_cuotas(pago_id: int, db: Session = Depends(get_db)):
    """
    Aplica el monto del pago a cuotas del préstamo (por orden de numero_cuota).
    Reglas de negocio: 100% cubierta → PAGADO; parcial + futuro → PAGO_ADELANTADO; parcial + vencido → PENDIENTE.
    Actualiza pago.estado a PAGADO cuando se aplica a cuotas.
    """
    pago = db.get(Pago, pago_id)
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    if not pago.prestamo_id:
        return {
            "success": False,
            "cuotas_completadas": 0,
            "cuotas_parciales": 0,
            "message": "El pago no tiene préstamo asociado.",
        }
    monto_restante = float(pago.monto_pagado) if pago.monto_pagado else 0
    if monto_restante <= 0:
        return {"success": True, "cuotas_completadas": 0, "cuotas_parciales": 0, "message": "Monto del pago es cero."}
    try:
        cuotas_completadas, cuotas_parciales = _aplicar_pago_a_cuotas_interno(pago, db)
        if cuotas_completadas > 0 or cuotas_parciales > 0:
            pago.estado = "PAGADO"
        db.commit()
        return {
            "success": True,
            "cuotas_completadas": cuotas_completadas,
            "cuotas_parciales": cuotas_parciales,
            "message": f"Se aplicó el pago: {cuotas_completadas} cuota(s) completadas, {cuotas_parciales} parcial(es).",
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error aplicar-cuotas pago_id=%s: %s", pago_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Error al aplicar el pago a cuotas: {str(e)}",
        ) from e

