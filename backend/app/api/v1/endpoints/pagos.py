"""
Endpoints de pagos. Datos reales desde BD.
- Tabla pagos: GET/POST/PUT/DELETE /pagos/ (listado y CRUD para /pagos/pagos).
- GET /pagos/kpis, /stats, /ultimos; POST /upload, /conciliacion/upload, /{id}/aplicar-cuotas.

NÂº documento / referencia de pago:
- Regla general: no se aceptan duplicados en documentos. En todo el sistema (carga masiva, crear,
  actualizar, BD) no puede existir dos pagos con el mismo NÂº documento. Misma clave canÃ³nica =
  duplicado â†’ rechazo.
- Se aceptan TODOS los formatos (BNC/, BINANCE, VE/, ZELLE/, numérico, REF, etc.). Límite 100 caracteres. Varias filas sin documento (vacío) se permiten. Única regla: no duplicados.
"""
import calendar
import io
import logging
import re
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Body
from pydantic import BaseModel, field_validator
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.documento import normalize_documento
from app.core.serializers import to_float, format_date_iso
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.pago_con_error import PagoConError
from app.models.revisar_pago import RevisarPago
from app.models.cuota_pago import CuotaPago
from app.schemas.pago import PagoCreate, PagoUpdate, PagoResponse
from app.schemas.auth import UserResponse


class MoverRevisarPagosBody(BaseModel):
    """IDs de pagos exportados a Excel para mover a tabla revisar_pagos."""
    pago_ids: list[int]


class GuardarFilaEditableBody(BaseModel):
    """Datos de una fila editable validada para guardar como Pago."""
    cedula: str
    prestamo_id: Optional[int] = None
    monto_pagado: float
    fecha_pago: str  # formato "DD-MM-YYYY"
    numero_documento: Optional[str] = None


class ValidarFilasBatchBody(BaseModel):
    """Batch de cÃ©dulas y documentos para validar contra BD."""
    cedulas: list[str] = []
    documentos: list[str] = []  # Solo los no vacÃ­os


class PagoBatchBody(BaseModel):
    """Array de pagos para crear en una sola peticiÃ³n (Guardar todos). MÃ¡ximo 500 ítems."""
    pagos: list[PagoCreate]

    @field_validator("pagos")
    @classmethod
    def pagos_limite(cls, v: list) -> list:
        if len(v) > 500:
            raise ValueError("MÃ¡ximo 500 pagos por lote. Divida en varios envíos.")
        return v



logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])

# LÃ­mite de la columna numero_documento y referencia_pago en tabla pagos (String(100))
_MAX_LEN_NUMERO_DOCUMENTO = 100
# ValidaciÃ³n de monto para NUMERIC(14, 2): mÃ¡ximo ~999,999,999,999.99 (12 dÃ­gitos antes del decimal)
_MAX_MONTO_PAGADO = 999_999_999_999.99
_MIN_MONTO_PAGADO = 0.01  # Monto mÃ­nimo vÃ¡lido (> 0)
_PRESTAMO_ID_MAX = 2_147_483_647  # INT max en BD (32-bit signed)


# Todas las funciones de normalizaciÃ³n de documento estÃ¡n centralizadas en app.core.documento
# Se usan ahora: normalize_documento() que consolidaba las 3 funciones anteriores.
# Esto evita duplicaciÃ³n y facilita mantenimiento.



def _validar_monto(monto_raw: Any) -> tuple[bool, float, str]:
    """
    Valida que el monto estÃ© dentro de los rangos permitidos para NUMERIC(14, 2).
    Retorna: (es_valido, monto_parseado, mensaje_error)
    """
    try:
        monto = float(monto_raw) if monto_raw is not None else 0.0
    except (TypeError, ValueError):
        return (False, 0.0, f"No se puede parsear el monto: {monto_raw}")
    
    # Validar rango: debe estar entre 0.01 y 999,999,999,999.99
    if monto < _MIN_MONTO_PAGADO:
        return (False, monto, f"Monto debe ser mayor a {_MIN_MONTO_PAGADO}")
    
    if monto > _MAX_MONTO_PAGADO:
        # Probablemente es una fecha convertida a nÃºmero de Excel (dÃ­as desde 1900)
        # Las fechas en Excel tÃ­picamente son nÃºmeros entre 1 y ~50000
        if monto < 100000:
            return (False, monto, f"Monto sospechosamente pequeÃ±o para ser una cantidad; parece ser una fecha o nÃºmero de secuencia: {monto}")
        return (False, monto, f"Monto excede lÃ­mite mÃ¡ximo ({_MAX_MONTO_PAGADO}): {monto}")
    
    return (True, monto, "")


def _celda_a_string_documento(val: Any) -> str:
    """
    Convierte el valor de una celda Excel a string para NÂº documento.
    Acepta cualquier tipo: str, int, float (evita notaciÃ³n cientÃ­fica para nÃºmeros largos).
    """
    if val is None:
        return ""
    if isinstance(val, float):
        if val != val:
            return ""  # NaN
        if val == int(val):
            return str(int(val))  # 740087415441562.0 -> "740087415441562" (sin 7.4e+14)
        return str(val)
    if isinstance(val, int):
        return str(val)
    return str(val).strip()


# Zona horaria del negocio para "hoy" e "inicio_mes" (Monto cobrado mes, Pagos hoy)
TZ_NEGOCIO = "America/Caracas"


def _hoy_local() -> date:
    """
    [MORA] Retorna la fecha actual en la zona horaria del negocio (America/Caracas).
    Usada para calcular dias_mora, detectar vencimientos, y acciones automÃ¡ticas.
    """
    tz = ZoneInfo(TZ_NEGOCIO)
    return datetime.now(tz).date()


def _validar_transicion_estado_cuota(estado_anterior: str, estado_nuevo: str) -> bool:
    """
    [validar_transiciones] Valida transiciones permitidas entre estados de cuota.
    
    Transiciones permitidas:
    PENDIENTE â†’ PAGADO, PAGO_ADELANTADO
    PAGO_ADELANTADO â†’ PAGADO
    PAGADO â†’ PAGADO (idempotente)
    """
    transiciones_permitidas = {
        "PENDIENTE": ["PAGADO", "PAGO_ADELANTADO", "PENDIENTE"],
        "PAGO_ADELANTADO": ["PAGADO", "PAGO_ADELANTADO"],
        "PAGADO": ["PAGADO"],  # Idempotente
    }
    return estado_nuevo in transiciones_permitidas.get(estado_anterior, [])


def _calcular_dias_mora(fecha_vencimiento: date) -> int:
    """
    [MORA] Calcula el nÃºmero de dÃ­as en mora desde la fecha de vencimiento.
    
    - Si fecha_vencimiento >= hoy â†’ 0 (no hay mora)
    - Si fecha_vencimiento < hoy â†’ (hoy - fecha_vencimiento).days (dÃ­as vencidos)
    
    Regla: Mora se acumula desde el dÃ­a siguiente a fecha_vencimiento hasta que pague 100%.
    """
    hoy = _hoy_local()
    if not fecha_vencimiento:
        return 0
    dias = (hoy - fecha_vencimiento).days
    return max(0, dias)


def _clasificar_nivel_mora(dias_mora: int, total_pagado: float, monto_cuota: float) -> str:
    """
    [MORA] Clasifica el nivel de mora segÃºn dÃ­as vencidos.
    
    Reglas:
    - Si total_pagado >= monto_cuota (100%) â†’ PAGADO (sin mora)
    - Si dias_mora == 0 y total_pagado == 0 â†’ PENDIENTE (vigente, no vencida)
    - Si 0 < dias_mora <= 90 â†’ VENCIDO (dentro de plazo de cobranza)
    - Si dias_mora > 90 â†’ MORA (severa, automatiza acciones de cobranza)
    - Si 0 < total_pagado < monto_cuota:
        - Con dias_mora <= 90 â†’ VENCIDO (pago parcial dentro de plazo)
        - Con dias_mora > 90 â†’ MORA (pago parcial ya en mora severa)
    """
    if total_pagado >= monto_cuota - 0.01:
        return "PAGADO"
    if dias_mora == 0:
        return "PENDIENTE"
    if dias_mora > 90:
        return "MORA"
    return "VENCIDO"  # 1 <= dias_mora <= 90


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
def listar_pagos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cedula: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    analista: Optional[str] = Query(None),
    conciliado: Optional[str] = Query(None, description="si=conciliados, no=no conciliados, vacÃ­o=todos"),
    sin_prestamo: Optional[str] = Query(None, description="si=solo pagos sin crÃ©dito asignado (prestamo_id NULL)"),
    db: Session = Depends(get_db),
):
    """Listado paginado desde la tabla pagos. Filtros: cedula, estado, fecha_desde, fecha_hasta, analista, conciliado, sin_prestamo."""
    try:
        q = select(Pago)
        count_q = select(func.count()).select_from(Pago)
        if sin_prestamo and sin_prestamo.strip().lower() == "si":
            q = q.where(Pago.prestamo_id.is_(None))
            count_q = count_q.where(Pago.prestamo_id.is_(None))
            # Excluir pagos ya movidos a revisar_pagos (tabla temporal de validaciÃ³n)
            revisar_subq = select(RevisarPago.pago_id)
            q = q.where(~Pago.id.in_(revisar_subq))
            count_q = count_q.where(~Pago.id.in_(revisar_subq))
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
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Carga masiva de pagos desde Excel (subir y procesar todo en el servidor).
    Formatos de columnas soportados (primera fila = cabecera; datos desde fila 2):
    - Formato D (principal): Cédula | Monto | Fecha | Nº documento
    - Formato A: Documento | Cédula | Fecha | Monto
    - Formato B: Fecha | Cédula | Monto | Documento
    - Formato C: Cédula | ID Préstamo | Fecha | Monto | Nº documento
    Recomendado: hasta 2.500 filas para evitar timeouts; máximo 10.000.
    Timeout: en producción, configurar timeout del servidor (uvicorn/gunicorn o proxy)
    suficientemente alto para archivos grandes (p. ej. 120 s) para POST /pagos/upload.
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Debe subir un archivo Excel (.xlsx o .xls)")
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB (alineado con frontend)
    MAX_ROWS = 10000  # LÃ­mite mÃ¡ximo de filas (rechazo si se supera)
    MAX_ROWS_RECOMENDADO = 2500  # Sin sobrecarga ni timeouts en servidor tÃ­pico
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
                detail=f"El archivo tiene demasiadas filas ({len(rows)}). MÃ¡ximo permitido: {MAX_ROWS}. Para evitar sobrecarga, se recomienda hasta {MAX_ROWS_RECOMENDADO} filas.",
            )
        if len(rows) > MAX_ROWS_RECOMENDADO:
            logger.warning(
                "Carga masiva con %s filas (recomendado hasta %s). Puede haber timeouts o lentitud.",
                len(rows),
                MAX_ROWS_RECOMENDADO,
            )

        def _looks_like_cedula(v: Any) -> bool:
            if v is None:
                return False
            s = str(v).strip()
            return bool(re.match(r"^[VEJZ]\d{6,11}$", s, re.IGNORECASE))

        def _looks_like_documento(v: Any) -> bool:
            """True si el valor puede ser Nº documento. REGLA: aceptar TODOS los formatos; única restricción = no duplicados."""
            if v is None or (isinstance(v, str) and not v.strip()):
                return False
            s = _celda_a_string_documento(v)
            if not s:
                return False
            if _looks_like_cedula(v):
                return False  # No confundir cédula con documento
            # Cualquier otro valor no vacío (1+ caracteres, hasta límite BD) se acepta como documento
            return len(s) <= _MAX_LEN_NUMERO_DOCUMENTO

        def _looks_like_date(v: Any) -> bool:
            if v is None:
                return False
            if isinstance(v, (datetime, date)):
                return True
            s = str(v).strip()
            return bool(re.search(r"\d{1,4}[-\/]\d{1,2}[-\/]\d{1,4}", s))

        def _extraer_documento_de_fila(row: tuple, col_documento: Optional[int]) -> str:
            """Obtiene el valor de documento: primero columna indicada; si vacÃ­o, busca en todas las celdas (fallback)."""
            if col_documento is not None and col_documento < len(row) and row[col_documento] is not None:
                s = _celda_a_string_documento(row[col_documento])
                if (s or "").strip():
                    return s
            for idx, cell in enumerate(row):
                if cell is None:
                    continue
                if _looks_like_documento(cell):
                    s = _celda_a_string_documento(cell)
                    if (s or "").strip():
                        return s
            return ""


        # Initialize error tracking
        errores: list[str] = []
        errores_detalle: list[dict] = []
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

        # --- FASE 1: Parsear todas las filas (ingresar todos los datos para validar despuÃ©s) ---
        FilasParseadas: list[dict] = []
        filas_omitidas = 0
        pagos_con_error_list: list[dict] = []  # Filas con error para guardar en pagos_con_errores
        errores: list[str] = []
        errores_detalle: list[dict] = []
        for i, row in enumerate(rows):
            if not row or all(cell is None for cell in row):
                continue
            try:
                cedula = ""
                prestamo_id: Optional[int] = None
                fecha_val: Any = None
                monto = 0.0
                numero_doc = ""
                col_doc: Optional[int] = None
                # Formato D (PRINCIPAL): CÃ©dula, Monto, Fecha, NÂº documento
                if len(row) >= 4 and _looks_like_cedula(row[0]) and row[1] is not None and _looks_like_date(row[2]):
                    cedula = str(row[0]).strip()
                    es_valido, monto, err_msg = _validar_monto(row[1])
                    if not es_valido and monto != 0.0:
                        errores.append(f'Fila {i + 2} (Formato D - Principal): {err_msg}')
                        pagos_con_error_list.append({
                            "fila_idx": i + 2,
                            "cedula": cedula,
                            "prestamo_id": prestamo_id,
                            "fecha_val": fecha_val,
                            "monto": monto,
                            "numero_doc": numero_doc,
                            "errores": [err_msg]
                        })
                        continue
                    fecha_val = row[2]
                    numero_doc = _celda_a_string_documento(row[3]) if len(row) > 3 else ""
                    col_doc = 3
                    prestamo_id = None
                # Formato A: Documento, CÃ©dula, Fecha, Monto
                elif len(row) >= 4 and _looks_like_documento(row[0]) and _looks_like_cedula(row[1]):
                    numero_doc = _celda_a_string_documento(row[0])
                    col_doc = 0
                    cedula = str(row[1]).strip()
                    fecha_val = row[2] if len(row) > 2 else None
                    es_valido, monto, err_msg = _validar_monto(row[3]) if len(row) > 3 else (True, 0.0, '')

                    if not es_valido and monto != 0.0:
                        errores.append(f'Fila {i + 2} (Formato A): {err_msg}')
                        pagos_con_error_list.append({
                            "fila_idx": i + 2,
                            "cedula": cedula,
                            "prestamo_id": None,
                            "fecha_val": row[2] if len(row) > 2 else None,
                            "monto": monto,
                            "numero_doc": numero_doc,
                            "errores": [err_msg],
                        })
                        continue
                # Formato B: Fecha, Cédula, Monto, Documento
                elif len(row) >= 4 and _looks_like_date(row[0]) and _looks_like_cedula(row[1]):
                    cedula = str(row[1]).strip()
                    es_valido, monto, err_msg = _validar_monto(row[2])

                    if not es_valido and monto != 0.0:
                        errores.append(f'Fila {i + 2} (Formato B): {err_msg}')
                        pagos_con_error_list.append({
                            "fila_idx": i + 2,
                            "cedula": cedula,
                            "prestamo_id": None,
                            "fecha_val": row[0],
                            "monto": monto,
                            "numero_doc": _celda_a_string_documento(row[3]) if len(row) > 3 else "",
                            "errores": [err_msg],
                        })
                        continue
                    fecha_val = row[0]
                    numero_doc = _celda_a_string_documento(row[3])
                    col_doc = 3
                else:
                    # Formato C (Alternativo): CÃ©dula, ID PrÃ©stamo, Fecha, Monto, NÂº documento
                    cedula = str(row[0]).strip() if row[0] is not None else ""
                    _val_prestamo = row[1] if len(row) > 1 else None
                    if _val_prestamo is None:
                        prestamo_id = None
                    else:
                        _s = str(_val_prestamo).strip()
                        try:
                            _pid = int(_s) if (_s and _s.isdigit()) else None
                        except ValueError:
                            _pid = None
                        if _pid is not None and (_pid < 1 or _pid > _PRESTAMO_ID_MAX):
                            prestamo_id = None
                        else:
                            prestamo_id = _pid
                    fecha_val = row[2] if len(row) > 2 else None
                    _monto_raw = row[3] if len(row) > 3 else None
                    es_valido, monto, err_msg = _validar_monto(_monto_raw)
                    if not es_valido and monto != 0.0:
                        errores.append(f'Fila {i + 2} (Formato C): {err_msg}')
                        pagos_con_error_list.append({
                            "fila_idx": i + 2,
                            "cedula": cedula,
                            "prestamo_id": prestamo_id,
                            "fecha_val": fecha_val,
                            "monto": monto,
                            "numero_doc": _celda_a_string_documento(row[4]) if len(row) > 4 else "",
                            "errores": [err_msg],
                        })
                        continue
                    numero_doc = _celda_a_string_documento(row[4]) if len(row) > 4 else ""
                    col_doc = 4 if len(row) > 4 else None

                # Fallback: si documento vacÃ­o, buscar en cualquier celda de la fila
                if not (numero_doc or "").strip():
                    numero_doc = _extraer_documento_de_fila(row, col_doc)

                if not cedula or monto <= 0:
                    filas_omitidas += 1
                    # Guardar en lista de errores para despues guardar en BD
                    pagos_con_error_list.append({
                        "fila_idx": i + 2,
                        "cedula": cedula or "",
                        "prestamo_id": prestamo_id,
                        "fecha_val": fecha_val,
                        "monto": monto,
                        "numero_doc": numero_doc,
                        "errores": ["Cedula vacia o monto <= 0"]
                    })
                    continue

                FilasParseadas.append({
                    "fila_idx": i + 2,
                    "cedula": cedula,
                    "prestamo_id": prestamo_id,
                    "fecha_val": fecha_val,
                    "monto": monto,
                    "numero_doc_raw": (numero_doc or "").strip(),
                })
            except Exception as e:
                errores.append(f"Fila {i + 2}: {e}")
                errores_detalle.append({"fila": i + 2, "cedula": "", "error": str(e), "datos": {}})

        # --- FASE 2: Validar documentos (Ãºnica regla: no duplicados) e insertar ---
        numeros_doc_en_lote: set[str] = set()
        documentos_ya_en_bd: set[str] = set()
        # Precarga en lote: documentos del archivo que ya existen en BD (evita N consultas)
        docs_en_archivo: set[str] = set()
        for item in FilasParseadas:
            numero_doc = (item.get("numero_doc_raw") or "").strip()
            if not numero_doc or numero_doc.upper() in ("NAN", "NONE", "UNDEFINED", "NA", "N/A"):
                continue
            numero_doc_norm = normalize_documento(numero_doc)
            if numero_doc_norm:
                docs_en_archivo.add(numero_doc_norm)
        if docs_en_archivo:
            chunk_size = 1000
            docs_list = list(docs_en_archivo)
            for ichunk in range(0, len(docs_list), chunk_size):
                chunk = docs_list[ichunk : ichunk + chunk_size]
                existentes = db.execute(select(Pago.numero_documento).where(Pago.numero_documento.in_(chunk))).scalars().all()
                documentos_ya_en_bd.update(str(d) for d in existentes if d)

        registros = 0
        pagos_con_prestamo: list[Pago] = []
        for item in FilasParseadas:
            i = item["fila_idx"]
            cedula = item["cedula"]
            prestamo_id = item["prestamo_id"]
            fecha_val = item["fecha_val"]
            monto = item["monto"]
            numero_doc = item["numero_doc_raw"]

            numero_doc_norm = normalize_documento(numero_doc)
            key_doc = (numero_doc_norm or "").strip()

            # ValidaciÃ³n post-documentos: duplicado en archivo
            if key_doc and key_doc in numeros_doc_en_lote:
                datos_fila = {"cedula": cedula, "prestamo_id": prestamo_id, "fecha_pago": fecha_val, "monto_pagado": monto, "numero_documento": numero_doc or ""}
                errores.append(f"Fila {i}: NÂº documento duplicado en este archivo")
                errores_detalle.append({"fila": i, "cedula": cedula, "error": "NÂº documento duplicado en este archivo. Regla general: no se aceptan duplicados en documentos.", "datos": datos_fila})
                continue

            # ValidaciÃ³n post-documentos: duplicado en BD (documentos_ya_en_bd precargado en lote)
            if key_doc:
                if key_doc in documentos_ya_en_bd:
                    datos_fila = {"cedula": cedula, "prestamo_id": prestamo_id, "fecha_pago": fecha_val, "monto_pagado": monto, "numero_documento": numero_doc or ""}
                    errores.append(f"Fila {i}: Ya existe un pago con ese NÂº de documento")
                    errores_detalle.append({"fila": i, "cedula": cedula, "error": "Ya existe un pago con ese NÂº de documento. Regla general: no se aceptan duplicados en documentos.", "datos": datos_fila})
                    continue
                numeros_doc_en_lote.add(key_doc)

            # PrÃ©stamo obligatorio si la cÃ©dula tiene mÃ¡s de un prÃ©stamo
            if prestamo_id is None and cedula.strip():
                count_prestamos = db.scalar(
                    select(func.count())
                    .select_from(Prestamo)
                    .join(Cliente, Prestamo.cliente_id == Cliente.id)
                    .where(Cliente.cedula == cedula.strip())
                ) or 0
                if count_prestamos > 1:
                    datos_fila = {"cedula": cedula, "prestamo_id": prestamo_id, "fecha_pago": fecha_val, "monto_pagado": monto, "numero_documento": numero_doc or ""}
                    errores.append(f"Fila {i}: La cÃ©dula {cedula} tiene {count_prestamos} prÃ©stamos. Debe indicar el ID del prÃ©stamo.")
                    errores_detalle.append({"fila": i, "cedula": cedula, "error": f"Esta persona tiene {count_prestamos} prÃ©stamos. Debe indicar el ID del prÃ©stamo.", "datos": datos_fila})
                    continue

            try:
                fecha_pago = _parse_fecha(fecha_val)
                ref_pago = ((numero_doc_norm or (numero_doc or "").strip()) or "Carga")[:_MAX_LEN_NUMERO_DOCUMENTO]
                usuario_email = current_user.email if current_user else "sistema@rapicredit.com"
                p = Pago(
                    cedula_cliente=cedula.strip().upper() if cedula else "",  # Normalize to uppercase
                    prestamo_id=prestamo_id,
                    fecha_pago=datetime.combine(fecha_pago, dt_time.min),
                    monto_pagado=monto,
                    numero_documento=numero_doc_norm,
                    estado="PENDIENTE",
                    referencia_pago=ref_pago,
                    usuario_registro=usuario_email,  # [MEJORADO] Usuario real desde JWT
                )
                db.add(p)
                registros += 1
                if prestamo_id and monto > 0:
                    pagos_con_prestamo.append(p)
            except Exception as e:
                errores.append(f"Fila {i}: {e}")
                datos_fila = {"cedula": cedula, "prestamo_id": prestamo_id, "fecha_pago": fecha_val, "monto_pagado": monto, "numero_documento": numero_doc or ""}
                errores_detalle.append({"fila": i, "cedula": cedula, "error": str(e), "datos": datos_fila})
        db.flush()  # Asigna IDs a los pagos insertados
        # --- GUARDAR PAGOS CON ERRORES EN BD ---
        for pce_data in pagos_con_error_list:
            try:
                pce = PagoConError(
                    cedula_cliente=pce_data["cedula"].strip().upper() if pce_data["cedula"] else "",  # Normalize
                    prestamo_id=pce_data["prestamo_id"],
                    fecha_pago=datetime.combine(_parse_fecha(pce_data["fecha_val"]), dt_time.min) if pce_data["fecha_val"] else datetime.now(),
                    monto_pagado=pce_data["monto"],
                    numero_documento=pce_data["numero_doc"],
                    estado="PENDIENTE",
                    errores_descripcion=pce_data["errores"],
                    observaciones="validacion",
                    fila_origen=pce_data["fila_idx"]
                )
                db.add(pce)
            except Exception as e:
                logger.warning(f"No se pudo guardar error de fila {pce_data['fila_idx']}: {e}")
        # Reglas de negocio: aplicar pagos con prestamo_id a cuotas
        cuotas_aplicadas = 0
        pagos_articulados = 0  # Track how many payments were successfully articulated
        for p in pagos_con_prestamo:
            try:
                cc, cp = _aplicar_pago_a_cuotas_interno(p, db)
                if cc > 0 or cp > 0:
                    p.estado = "PAGADO"
                    cuotas_aplicadas += cc + cp
                    pagos_articulados += 1
                    logger.info(f"Pago {p.id}: articulado a {cc + cp} cuota(s)")
                else:
                    logger.warning(f"Pago {p.id} (monto={p.monto_pagado}) no se pudo aplicar a cuotas")
            except Exception as e:
                logger.warning("Carga masiva: no se pudo aplicar pago id=%s a cuotas: %s", getattr(p, "id", "?"), e)
        db.commit()
        errores_limit = 50
        errores_detalle_limit = 100
        total_errores = len(errores)
        total_errores_detalle = len(errores_detalle)
        return {
            "message": "Carga finalizada",
            "registros_procesados": registros,
            "registros_con_error": len(pagos_con_error_list),
            "cuotas_aplicadas": cuotas_aplicadas,
            "pagos_articulados": pagos_articulados,  # [NUEVA] NÃºmero de pagos que se articularon a cuotas
            "filas_omitidas": filas_omitidas,
            "pagos_con_errores": [
                {
                    "id": pce.id,
                    "fila_origen": pce.fila_origen,
                    "cedula": pce.cedula_cliente,
                    "monto": float(pce.monto_pagado) if pce.monto_pagado else 0,
                    "errores": pce.errores_descripcion or [],
                    "accion": "revisar"
                }
                for pce in (db.query(PagoConError).filter(PagoConError.fila_origen.in_([p['fila_idx'] for p in pagos_con_error_list])).all() if pagos_con_error_list else [])
            ],
            "errores": errores[:errores_limit],
            "errores_detalle": errores_detalle[:errores_detalle_limit],
            "errores_total": total_errores,
            "errores_detalle_total": total_errores_detalle,
            "errores_truncados": total_errores > errores_limit or total_errores_detalle > errores_detalle_limit,
            "max_filas_recomendado": MAX_ROWS_RECOMENDADO,
            "max_filas_permitido": MAX_ROWS,
        }
    except Exception as e:
        db.rollback()
        logger.exception("Error upload Excel pagos: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/validar-filas-batch", response_model=dict)
def validar_filas_batch(
    body: ValidarFilasBatchBody = Body(...),
    db: Session = Depends(get_db),
):
    """
    Valida en lote:
    - CÃ©dulas: deben existir en tabla clientes
    - Documentos: se verifica en tabla CUOTAS (si existe â†’ confirmado/vÃ¡lido)
                  Si NO existe en CUOTAS pero SÃ en PAGOS â†’ duplicado sin aplicar
    Retorna cÃ©dulas vÃ¡lidas y documentos con estado de confirmaciÃ³n.
    """
    from app.models.cuota import Cuota
    
    # Normalizar cÃ©dulas (sin guiÃ³n, uppercase)
    cedulas_norm = list({
        c.strip().replace("-", "").upper()
        for c in (body.cedulas or [])
        if c and c.strip()
    })

    # CÃ©dulas que existen en tabla clientes
    cedulas_existentes: set[str] = set()
    if cedulas_norm:
        rows = db.execute(
            select(Cliente.cedula).where(Cliente.cedula.in_(cedulas_norm))
        ).all()
        cedulas_existentes = {r[0].strip().replace("-", "").upper() for r in rows}

    # Documentos: verificar contra CUOTAS (si existe â†’ confirmado) y PAGOS (si existe sin cuota â†’ duplicado)
    documentos_confirmados: list[dict] = []  # Documentos encontrados en CUOTAS (pago ya aplicado)
    documentos_duplicados: list[dict] = []   # Documentos en PAGOS pero NO aplicados a CUOTA
    
    docs_norm = [
        normalize_documento(d)
        for d in (body.documentos or [])
        if d and d.strip()
    ]
    docs_norm_limpios = [d for d in docs_norm if d]
    
    if docs_norm_limpios:
        # Buscar documentos que YA EXISTEN en tabla PAGOS (sin importar si estÃ¡n en CUOTAS)
        # Si existe en PAGOS = DUPLICADO (rechazar)
        rows_pagos = db.execute(
            select(Pago.numero_documento, Pago.id, Pago.cedula_cliente, 
                   Pago.fecha_pago, Pago.monto_pagado)
            .where(Pago.numero_documento.in_(docs_norm_limpios))
        ).all()
        
        for row in rows_pagos:
            documentos_duplicados.append({
                "numero_documento": row[0],
                "pago_id": row[1],
                "cedula": row[2],
                "fecha_pago": row[3].isoformat() if row[3] else None,
                "monto_pagado": float(row[4]) if row[4] else 0,
                "estado": "duplicado",
            })

    return {
        "cedulas_existentes": list(cedulas_existentes),
        "documentos_duplicados": documentos_duplicados,  # Documentos que YA existen en tabla PAGOS
    }


@router.post("/guardar-fila-editable", response_model=dict)
def guardar_fila_editable(
    body: GuardarFilaEditableBody = Body(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Guarda una fila editable validada (desde Preview).
    Si cumple validadores, inserta en pagos, aplica cuotas y retorna Ã©xito.
    Auto-marca como conciliado ('SI') para aplicar reglas de negocio inmediatamente.
    """
    try:
        cedula = (body.cedula or "").strip()
        monto = body.monto_pagado
        numero_doc = (body.numero_documento or "").strip() if body.numero_documento else None
        prestamo_id = body.prestamo_id
        usuario_email = current_user.email if current_user else "sistema@rapicredit.com"

        # Validaciones post-guardado
        if not cedula:
            raise HTTPException(status_code=400, detail="CÃ©dula requerida")
        if not _looks_like_cedula_inline(cedula):
            raise HTTPException(status_code=400, detail="CÃ©dula invÃ¡lida (debe ser V/E/J/Z + 6-11 dÃ­gitos)")
        if monto <= 0:
            raise HTTPException(status_code=400, detail="Monto debe ser > 0")
        if monto > _MAX_MONTO_PAGADO:
            raise HTTPException(status_code=400, detail=f"Monto excede lÃ­mite mÃ¡ximo: {_MAX_MONTO_PAGADO}")

        # Parsear fecha
        try:
            fecha_pago = datetime.strptime(body.fecha_pago[:10], "%d-%m-%Y").date()
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail="Fecha invÃ¡lida (formato: DD-MM-YYYY)")

        # Normalizar documento
        numero_doc_norm = normalize_documento(numero_doc)

        # Validar duplicado en BD (documento)
        if numero_doc_norm:
            pago_existente = db.execute(
                select(Pago).where(Pago.numero_documento == numero_doc_norm).limit(1)
            ).first()
            if pago_existente:
                raise HTTPException(
                    status_code=409,
                    detail=f"Ya existe un pago con este documento: {numero_doc_norm}"
                )

        # Si prestamo_id es None, buscar automÃ¡ticamente
        if prestamo_id is None:
            cliente_row = db.execute(
                select(Prestamo.id)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(Cliente.cedula == cedula)
                .limit(1)
            ).first()
            if cliente_row:
                prestamo_id = cliente_row[0]

        # Crear pago
        # [A2] Marcar conciliado=True y verificado_concordancia="SI" desde el momento de la creaciÃ³n,
        # ya que guardar-fila-editable implica que el pago fue revisado y validado manualmente.
        ref_pago = (numero_doc_norm or (numero_doc or "Carga"))[:_MAX_LEN_NUMERO_DOCUMENTO]
        ahora_conciliacion = datetime.now(ZoneInfo(TZ_NEGOCIO))
        pago = Pago(
            cedula_cliente=cedula.strip().upper() if cedula else "",  # Normalize to uppercase
            prestamo_id=prestamo_id,
            fecha_pago=datetime.combine(fecha_pago, dt_time.min),
            monto_pagado=Decimal(str(round(monto, 2))),
            numero_documento=numero_doc_norm,
            estado="PAGADO",
            referencia_pago=ref_pago,
            conciliado=True,  # [B2] Usar solo conciliado
            fecha_conciliacion=ahora_conciliacion,
            verificado_concordancia="SI",  # Legacy: sync con conciliado
            usuario_registro=usuario_email,  # [MEJORADO] Usuario real desde JWT
        )
        db.add(pago)
        db.flush()

        # Aplicar a cuotas si prestamo_id existe
        cuotas_completadas = 0
        cuotas_parciales = 0
        if pago.prestamo_id and monto > 0:
            cuotas_completadas, cuotas_parciales = _aplicar_pago_a_cuotas_interno(pago, db)

        db.commit()

        return {
            "success": True,
            "pago_id": pago.id,
            "message": "Fila guardada exitosamente",
            "cuotas_completadas": cuotas_completadas,
            "cuotas_parciales": cuotas_parciales,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error guardar-fila-editable: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


def _looks_like_cedula_inline(cedula: str) -> bool:
    """Validar cÃ©dula inline (helper)."""
    return bool(re.match(r"^[VEJZ]\d{6,11}$", cedula.strip(), re.IGNORECASE))


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
        pagos_para_aplicar: list[Pago] = []
        for i, row in enumerate(rows):
            if not row or (row[0] is None and row[1] is None):
                continue
            try:
                numero_doc_raw = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
                if not numero_doc_raw:
                    continue
                # Misma clave canÃ³nica que carga/crear: cualquier formato reconocido, bÃºsqueda por valor normalizado
                numero_doc = normalize_documento(numero_doc_raw)
                pago_row = db.execute(
                    select(Pago).where(Pago.numero_documento == numero_doc).limit(1)
                ).first()
                if not pago_row:
                    documentos_no_encontrados.append(numero_doc_raw)
                    continue
                pago = pago_row[0]
                pago.conciliado = True
                pago.fecha_conciliacion = ahora
                pagos_conciliados += 1
                if pago.prestamo_id and float(pago.monto_pagado or 0) > 0:
                    pagos_para_aplicar.append(pago)
            except Exception as e:
                errores_detalle.append(f"Fila {i + 2}: {e}")
        cuotas_aplicadas = 0
        for pago in pagos_para_aplicar:
            try:
                cc, cp = _aplicar_pago_a_cuotas_interno(pago, db)
                if cc > 0 or cp > 0:
                    pago.estado = "PAGADO"
                    cuotas_aplicadas += cc + cp
            except Exception as e:
                logger.warning("Conciliacion: no se pudo aplicar pago id=%s a cuotas: %s", pago.id, e)
        db.commit()
        return {
            "pagos_conciliados": pagos_conciliados,
            "cuotas_aplicadas": cuotas_aplicadas,
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
    mes: Optional[int] = Query(None, ge=1, le=12),
    anio: Optional[int] = Query(None, ge=2000, le=2100),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    KPIs de pagos para un mes:
    1. montoACobrarMes: cuÃ¡nto dinero deberÃ­a cobrarse en el mes (cuotas con vencimiento en el mes).
    2. montoCobradoMes: cuÃ¡nto dinero se ha cobrado = pagado en el mes.
    3. morosidadMensualPorcentaje: pago vencido mensual en % (cuotas vencidas no cobradas / cartera * 100).
    ParÃ¡metros: mes (1-12) y anio (2000-2100). Si no se envÃ­an, se usa el mes actual.
    """
    try:
        hoy = _hoy_local()
        if mes is not None and anio is not None:
            inicio_mes = hoy.replace(year=anio, month=mes, day=1)
            _, ultimo_dia = calendar.monthrange(anio, mes)
            fin_mes = inicio_mes.replace(day=ultimo_dia)
        elif fecha_inicio and fecha_fin:
            try:
                inicio_mes = datetime.strptime(fecha_inicio[:10], "%Y-%m-%d").date()
                fin_mes = datetime.strptime(fecha_fin[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                inicio_mes = hoy.replace(day=1)
                _, ultimo_dia = calendar.monthrange(hoy.year, hoy.month)
                fin_mes = inicio_mes.replace(day=ultimo_dia)
        else:
            inicio_mes = hoy.replace(day=1)
            _, ultimo_dia = calendar.monthrange(hoy.year, hoy.month)
            fin_mes = inicio_mes.replace(day=ultimo_dia)
        # Fecha de referencia: para meses pasados = fin_mes; para mes actual = hoy
        fecha_referencia = min(fin_mes, hoy)

        # Condiciones base: solo clientes ACTIVOS
        conds_activo = [
            Cuota.prestamo_id == Prestamo.id,
            Prestamo.cliente_id == Cliente.id,
            Cliente.estado == "ACTIVO",
            Prestamo.estado == "APROBADO",
        ]
        base_where = and_(*conds_activo)

        # Una sola consulta con agregaciÃ³n condicional para los 5 montos (menos round-trips a BD)
        aggr = select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Cuota.fecha_vencimiento >= inicio_mes,
                                Cuota.fecha_vencimiento <= fin_mes,
                            ),
                            Cuota.monto,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("monto_a_cobrar_mes"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Cuota.fecha_pago.isnot(None),
                                Cuota.fecha_pago >= inicio_mes,
                                Cuota.fecha_pago <= fecha_referencia,
                            ),
                            Cuota.monto,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("monto_cobrado_mes"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Cuota.fecha_vencimiento >= inicio_mes,
                                Cuota.fecha_vencimiento <= fin_mes,
                                Cuota.fecha_vencimiento < fecha_referencia,
                            ),
                            Cuota.monto,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("total_vencido_mes"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Cuota.fecha_vencimiento >= inicio_mes,
                                Cuota.fecha_vencimiento <= fin_mes,
                                Cuota.fecha_vencimiento < fecha_referencia,
                                Cuota.fecha_pago.is_(None),
                            ),
                            Cuota.monto,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("no_cobrado_mes"),
            func.coalesce(
                func.sum(case((Cuota.fecha_pago.is_(None), Cuota.monto), else_=0)),
                0,
            ).label("cartera_pendiente"),
        ).select_from(Cuota).join(Prestamo, Cuota.prestamo_id == Prestamo.id).join(
            Cliente, Prestamo.cliente_id == Cliente.id
        ).where(base_where)

        row = db.execute(aggr).one()
        monto_a_cobrar_mes = row.monto_a_cobrar_mes or 0
        monto_cobrado_mes = row.monto_cobrado_mes or 0
        total_vencido_mes = row.total_vencido_mes or 0
        no_cobrado_mes = row.no_cobrado_mes or 0
        cartera_pendiente = row.cartera_pendiente or 0

        morosidad_porcentaje = (
            (_safe_float(no_cobrado_mes) / _safe_float(total_vencido_mes) * 100.0)
            if total_vencido_mes and _safe_float(total_vencido_mes) > 0
            else 0.0
        )

        # Conteos: clientes en mora y clientes con prÃ©stamo (2 consultas ligeras)
        subq = (
            select(Prestamo.cliente_id)
            .select_from(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(
                and_(*conds_activo),
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento < fecha_referencia,
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

        mes_resp = mes if mes is not None else inicio_mes.month
        anio_resp = anio if anio is not None else inicio_mes.year
        return {
            "montoACobrarMes": _safe_float(monto_a_cobrar_mes),
            "montoCobradoMes": _safe_float(monto_cobrado_mes),
            "morosidadMensualPorcentaje": round(morosidad_porcentaje, 2),
            "mes": mes_resp,
            "anio": anio_resp,
            "anio": anio_resp,
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
            "mes": mes if mes is not None else hoy.month,
            "anio": anio if anio is not None else hoy.year,
            "anio": anio if anio is not None else hoy.year,
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


@router.post("/revisar-pagos/mover", response_model=dict)
def mover_a_revisar_pagos(payload: MoverRevisarPagosBody = Body(...), db: Session = Depends(get_db)):
    """
    Mueve los pagos exportados a la tabla revisar_pagos (temporal de validaciÃ³n).
    Tras descargar Excel y guardar en PC, estos pagos dejan de mostrarse en Revisar Pagos.
    No interfiere con procesos ni reglas de negocio.
    """
    if not payload.pago_ids:
        return {"movidos": 0, "mensaje": "No hay pagos para mover"}
    insertados = 0
    for pid in payload.pago_ids:
        if not isinstance(pid, int) or pid <= 0:
            continue
        existing = db.scalar(select(RevisarPago.id).where(RevisarPago.pago_id == pid))
        if existing:
            continue
        db.add(RevisarPago(pago_id=pid))
        insertados += 1
    db.commit()
    return {"movidos": insertados, "mensaje": f"{insertados} pagos movidos a revisar_pagos"}


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
    """Regla general: no duplicados en documentos. Comprueba si ya existe un pago con ese NÂº documento."""
    num = normalize_documento(numero_documento)
    if not num:
        return False
    q = select(Pago.id).where(Pago.numero_documento == num)
    if exclude_pago_id is not None:
        q = q.where(Pago.id != exclude_pago_id)
    return db.scalar(q) is not None


@router.post("/batch", response_model=dict)
def crear_pagos_batch(
    body: PagoBatchBody,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Crea varios pagos en una sola peticiÃ³n (mÃ¡x. 500).
    Devuelve Ã©xitos y errores por Ã­ndice para reducir rondas y timeouts en "Guardar todos".
    """
    usuario_email = current_user.email if current_user else "sistema@rapicredit.com"
    results: list[dict] = []
    ok_count = 0
    fail_count = 0
    for idx, payload in enumerate(body.pagos):
        try:
            num_doc = normalize_documento(payload.numero_documento)
            if num_doc and _numero_documento_ya_existe(db, num_doc):
                results.append({"index": idx, "success": False, "error": "Ya existe un pago con ese NÂº de documento.", "status_code": 409})
                fail_count += 1
                continue
            ref = (num_doc or "N/A")[:_MAX_LEN_NUMERO_DOCUMENTO]
            fecha_pago_ts = datetime.combine(payload.fecha_pago, dt_time.min)
            conciliado = payload.conciliado if payload.conciliado is not None else False
            cedula_normalizada = payload.cedula_cliente.strip().upper() if payload.cedula_cliente else ""
            if payload.prestamo_id:
                prestamo = db.execute(select(Prestamo).where(Prestamo.id == payload.prestamo_id)).scalars().first()
                if not prestamo:
                    results.append({"index": idx, "success": False, "error": f"CrÃ©dito #{payload.prestamo_id} no existe.", "status_code": 400})
                    fail_count += 1
                    continue
            if cedula_normalizada and payload.prestamo_id:
                cliente = db.execute(select(Cliente).where(Cliente.cedula == cedula_normalizada)).scalars().first()
                if not cliente:
                    results.append({"index": idx, "success": False, "error": f"No existe cliente con cÃ©dula {cedula_normalizada}", "status_code": 404})
                    fail_count += 1
                    continue
            row = Pago(
                cedula_cliente=cedula_normalizada,
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
                verificado_concordancia="SI" if conciliado else "",
                usuario_registro=usuario_email,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            if row.prestamo_id and float(row.monto_pagado or 0) > 0:
                try:
                    _aplicar_pago_a_cuotas_interno(row, db)
                    row.estado = "PAGADO"
                    db.commit()
                    db.refresh(row)
                except Exception as e:
                    logger.warning("Batch: no se pudo aplicar a cuotas (Ã­ndice %s): %s", idx, e)
                    db.rollback()
            results.append({"index": idx, "success": True, "pago": _pago_to_response(row)})
            ok_count += 1
        except IntegrityError as e:
            db.rollback()
            if getattr(getattr(e, "orig", None), "pgcode", None) == "23505":
                results.append({"index": idx, "success": False, "error": "NÂº de documento duplicado.", "status_code": 409})
            else:
                results.append({"index": idx, "success": False, "error": str(e), "status_code": 500})
            fail_count += 1
        except Exception as e:
            db.rollback()
            logger.exception("Batch Ã­ndice %s: %s", idx, e)
            results.append({"index": idx, "success": False, "error": str(e), "status_code": 500})
            fail_count += 1
    return {"results": results, "ok_count": ok_count, "fail_count": fail_count}


@router.post("", response_model=dict, status_code=201)
def crear_pago(payload: PagoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):
    """Crea un pago. Documento acepta cualquier formato. Regla general: no duplicados (409 si ya existe)."""
    num_doc = normalize_documento(payload.numero_documento)
    if num_doc and _numero_documento_ya_existe(db, num_doc):
        raise HTTPException(
            status_code=409,
            detail="Ya existe un pago con ese NÂº de documento. Regla general: no se aceptan duplicados en documentos.",
        )
    ref = (num_doc or "N/A")[:_MAX_LEN_NUMERO_DOCUMENTO]
    fecha_pago_ts = datetime.combine(payload.fecha_pago, dt_time.min)
    conciliado = payload.conciliado if payload.conciliado is not None else False  # [B2] Default False
    usuario_email = current_user.email if current_user else "sistema@rapicredit.com"
    
    # Normalizar cÃ©dula: uppercase para evitar FK mismatch
    cedula_normalizada = payload.cedula_cliente.strip().upper() if payload.cedula_cliente else ""
    
    # Validar que el crédito (prestamo_id) existe en prestamos (evita IntegrityError FK)
    if payload.prestamo_id:
        prestamo = db.execute(select(Prestamo).where(Prestamo.id == payload.prestamo_id)).scalars().first()
        if not prestamo:
            raise HTTPException(
                status_code=400,
                detail=f"El crédito #{payload.prestamo_id} no existe. Elija un crédito de la lista (no use el número de documento como crédito).",
            )
    # Validar que cedula existe en clientes si se proporciona y hay prestamo_id
    if cedula_normalizada and payload.prestamo_id:
        cliente = db.execute(
            select(Cliente).where(Cliente.cedula == cedula_normalizada)
        ).scalars().first()
        if not cliente:
            raise HTTPException(
                status_code=404,
                detail=f"No existe cliente con cedula {cedula_normalizada}"
            )
    
    try:
        row = Pago(
            cedula_cliente=cedula_normalizada,
            prestamo_id=payload.prestamo_id,
            fecha_pago=fecha_pago_ts,
            monto_pagado=payload.monto_pagado,
            numero_documento=num_doc,
            institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,
            estado="PENDIENTE",
            notas=payload.notas.strip() if payload.notas else None,
            referencia_pago=ref,
            conciliado=conciliado,  # [B2] Usar solo conciliado, no verificado_concordancia
            fecha_conciliacion=datetime.now(ZoneInfo(TZ_NEGOCIO)) if conciliado else None,
            verificado_concordancia="SI" if conciliado else "",  # Legacy: sync con conciliado
            usuario_registro=usuario_email,  # [MEJORADO] Usuario real desde JWT
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        # [C3] Aplicar FIFO a cuotas siempre que el pago tenga prestamo_id
        if row.prestamo_id and float(row.monto_pagado or 0) > 0:
            try:
                _aplicar_pago_a_cuotas_interno(row, db)
                row.estado = "PAGADO"
                db.commit()
                db.refresh(row)
            except Exception as e:
                logger.warning("Al crear pago, no se pudo aplicar a cuotas (FIFO): %s", e)
                db.rollback()
        return _pago_to_response(row)
    except HTTPException:
        raise
    except IntegrityError as e:
        db.rollback()
        # Unique violation (p. ej. numero_documento duplicado) → 409
        if getattr(getattr(e, "orig", None), "pgcode", None) == "23505":
            raise HTTPException(
                status_code=409,
                detail="Ya existe un pago con ese Nº de documento. El documento debe ser único; no se permiten repetidos.",
            )
        raise HTTPException(status_code=500, detail="Error de integridad en la base de datos.")
    except Exception as e:
        logger.exception("Error en POST /pagos (crear_pago): %s", e)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error al crear el pago. Revise los datos (cédula, crédito, monto, fecha, Nº documento) o contacte soporte.",
        )


@router.put("/{pago_id}", response_model=dict)
def actualizar_pago(pago_id: int, payload: PagoUpdate, db: Session = Depends(get_db)):
    """Actualiza un pago en la tabla pagos. NÂº documento no puede repetirse."""
    row = db.get(Pago, pago_id)
    if not row:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "numero_documento" in data and data["numero_documento"] is not None:
        num_doc = normalize_documento(data["numero_documento"])
        if num_doc and _numero_documento_ya_existe(db, num_doc, exclude_pago_id=pago_id):
            raise HTTPException(
                status_code=409,
                detail="Ya existe otro pago con ese NÂº de documento. Regla general: no se aceptan duplicados en documentos.",
            )
    aplicar_conciliado = False
    for k, v in data.items():
        if k == "notas" and v is not None:
            setattr(row, k, v.strip() or None)
        elif k == "institucion_bancaria" and v is not None:
            setattr(row, k, v.strip() or None)
        elif k == "numero_documento" and v is not None:
            setattr(row, k, normalize_documento(v))
        elif k == "cedula_cliente" and v is not None:
            setattr(row, k, v.strip())
        elif k == "fecha_pago" and v is not None:
            setattr(row, k, datetime.combine(v, dt_time.min) if isinstance(v, date) and not isinstance(v, datetime) else v)
        elif k == "conciliado" and v is not None:
            row.conciliado = bool(v)
            row.fecha_conciliacion = datetime.now(ZoneInfo(TZ_NEGOCIO)) if v else None
            row.verificado_concordancia = "SI" if v else "NO"
            aplicar_conciliado = bool(v)
        elif k == "verificado_concordancia" and v is not None:
            val = (v or "").strip().upper()
            row.verificado_concordancia = val if val in ("SI", "NO") else ("" if v == "" else str(v)[:10])
        else:
            setattr(row, k, v)
    try:
        db.commit()
        db.refresh(row)
    except IntegrityError as e:
        db.rollback()
        if getattr(getattr(e, "orig", None), "pgcode", None) == "23505":
            raise HTTPException(
                status_code=409,
                detail="Ya existe otro pago con ese Nº de documento. El documento debe ser único; no se permiten repetidos.",
            )
        raise HTTPException(status_code=500, detail="Error de integridad en la base de datos.")
    if aplicar_conciliado and row.prestamo_id and float(row.monto_pagado or 0) > 0:
        try:
            cuotas_completadas, cuotas_parciales = _aplicar_pago_a_cuotas_interno(row, db)
            # PAGADO si se abonÃ³ a alguna cuota o si no habÃ­a cuotas pendientes (pago procesado para el prÃ©stamo)
            row.estado = "PAGADO"
            db.commit()
            db.refresh(row)
        except Exception as e:
            logger.warning("Al actualizar pago conciliado, no se pudo aplicar a cuotas: %s", e)
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
    """
    [MORA] Determina estado segÃºn cobertura y fecha de vencimiento.
    Usa la nueva clasificaciÃ³n: PENDIENTE | VENCIDO (1-90d) | MORA (>90d) | PAGO_ADELANTADO
    """
    dias_mora = _calcular_dias_mora(fecha_vencimiento)
    return _clasificar_nivel_mora(dias_mora, total_pagado, monto_cuota)
    # Nota: Si total_pagado > 0 pero < monto_cuota:
    #   - _clasificar_nivel_mora devuelve VENCIDO o MORA segÃºn dÃ­as
    # Si total_pagado == 0:
    #   - devuelve PENDIENTE si dias_mora == 0, sino VENCIDO/MORA


def _aplicar_pago_a_cuotas_interno(pago: Pago, db: Session) -> tuple[int, int]:
    """
    Aplica el monto del pago a cuotas del prÃ©stamo. Reglas de negocio.
    Crea registros en cuota_pagos para historial completo (no solo sobrescribe pago_id).
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
    orden_aplicacion = 0  # Para rastrear secuencia FIFO en cuota_pagos
    
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
        
        # NUEVO: Registrar en cuota_pagos para historial completo
        es_pago_completo = nuevo_total >= monto_cuota - 0.01
        cuota_pago = CuotaPago(
            cuota_id=c.id,
            pago_id=pago.id,
            monto_aplicado=Decimal(str(round(a_aplicar, 2))),
            fecha_aplicacion=datetime.now(),
            orden_aplicacion=orden_aplicacion,
            es_pago_completo=es_pago_completo,
        )
        db.add(cuota_pago)
        orden_aplicacion += 1
        
        fecha_venc = c.fecha_vencimiento
        if fecha_venc is not None and hasattr(fecha_venc, "date"):
            fecha_venc = fecha_venc.date()
        fecha_venc = fecha_venc or hoy
        if nuevo_total >= monto_cuota - 0.01:
            c.fecha_pago = fecha_pago_date
            estado_nuevo = "PAGADO"
            if not _validar_transicion_estado_cuota(c.estado, estado_nuevo):  # [validar_transiciones]
                logger.warning(f"TransiciÃ³n de estado invÃ¡lida en cuota {c.id}: {c.estado} â†’ {estado_nuevo}")
                c.estado = estado_nuevo  # Forzar transiciÃ³n igualmente (log informativo)
            else:
                c.estado = estado_nuevo
            c.dias_mora = 0  # [M5] Sin mora si estÃ¡ pagada
            cuotas_completadas += 1
        else:
            estado_nuevo = _estado_cuota_por_cobertura(nuevo_total, monto_cuota, fecha_venc)
            if not _validar_transicion_estado_cuota(c.estado, estado_nuevo):  # [validar_transiciones]
                logger.warning(f"TransiciÃ³n de estado invÃ¡lida en cuota {c.id}: {c.estado} â†’ {estado_nuevo}")
            c.estado = estado_nuevo
            c.dias_mora = _calcular_dias_mora(fecha_venc)  # [M5] Calcular mora
            cuotas_parciales += 1
        monto_restante -= a_aplicar
    return cuotas_completadas, cuotas_parciales


@router.post("/{pago_id}/aplicar-cuotas", response_model=dict)
def aplicar_pago_a_cuotas(pago_id: int, db: Session = Depends(get_db)):
    """
    Aplica el monto del pago a cuotas del prÃ©stamo (por orden de numero_cuota).
    Reglas de negocio: 100% cubierta â†’ PAGADO; parcial + futuro â†’ PAGO_ADELANTADO; parcial + vencido â†’ PENDIENTE.
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
            "message": "El pago no tiene prÃ©stamo asociado.",
        }
    monto_restante = float(pago.monto_pagado) if pago.monto_pagado else 0
    if monto_restante <= 0:
        return {"success": True, "cuotas_completadas": 0, "cuotas_parciales": 0, "message": "Monto del pago es cero."}
    try:
        cuotas_completadas, cuotas_parciales = _aplicar_pago_a_cuotas_interno(pago, db)
        # PAGADO siempre que se procese para el prÃ©stamo (haya o no cuotas pendientes)
        pago.estado = "PAGADO"
        db.commit()
        return {
            "success": True,
            "cuotas_completadas": cuotas_completadas,
            "cuotas_parciales": cuotas_parciales,
            "message": f"Se aplicÃ³ el pago: {cuotas_completadas} cuota(s) completadas, {cuotas_parciales} parcial(es).",
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




