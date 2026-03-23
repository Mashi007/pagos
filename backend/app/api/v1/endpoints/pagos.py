"""

Endpoints de pagos. Datos reales desde BD.

- Tabla pagos: GET/POST/PUT/DELETE /pagos/ (listado y CRUD para /pagos/pagos).

- GET /pagos/kpis, /stats, /ultimos; POST /upload, /conciliacion/upload, /{id}/aplicar-cuotas.



Nº documento / referencia de pago:

- Regla general: no se aceptan duplicados en documentos. En todo el sistema (carga masiva, crear,

  actualizar, BD) no puede existir dos pagos con el mismo Nº documento. Misma clave canónica =

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

from fastapi.responses import StreamingResponse

from pydantic import BaseModel, field_validator

from sqlalchemy import and_, case, delete, exists, func, or_, select

from sqlalchemy.orm import Session

from sqlalchemy.exc import IntegrityError, OperationalError



from app.core.database import get_db

from app.core.deps import get_current_user

from app.core.documento import normalize_documento
from app.utils.cedula_almacenamiento import alinear_cedulas_clientes_existentes, normalizar_cedula_almacenamiento
from app.services.pago_numero_documento import numero_documento_ya_registrado

from app.core.serializers import to_float, format_date_iso

from app.models.cliente import Cliente

from app.models.cuota import Cuota

from app.models.prestamo import Prestamo

from app.models.pago import Pago

from app.models.pago_con_error import PagoConError

from app.models.revisar_pago import RevisarPago

from app.models.cuota_pago import CuotaPago

from app.models.pago_reportado import PagoReportado

from app.models.datos_importados_conerrores import DatosImportadosConErrores

from app.models.cedula_reportar_bs import CedulaReportarBs

from app.schemas.pago import PagoCreate, PagoUpdate, PagoResponse

from app.schemas.auth import UserResponse

from app.services.cuota_estado import (
    clasificar_estado_cuota,
    dias_retraso_desde_vencimiento,
    hoy_negocio,
)
from app.services.prestamo_db_compat import prestamos_tiene_columna_fecha_liquidado


from app.services.tasa_cambio_service import (

    convertir_bs_a_usd,

    obtener_tasa_por_fecha,

)

from app.services.cobros.cedula_reportar_bs_service import (

    normalize_cedula_para_almacenar_lista_bs,

    load_autorizados_bs_claves,

    cedula_coincide_autorizados_bs,

)



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

    """Batch: cédulas contra tabla préstamos; documentos contra pagos y pagos_con_errores (unicidad global)."""

    cedulas: list[str] = []

    documentos: list[str] = []  # Solo los no vacíos





class PagoBatchBody(BaseModel):

    """Array de pagos para crear en una sola petición (Guardar todos). Máximo 500 ítems."""

    pagos: list[PagoCreate]



    @field_validator("pagos")

    @classmethod

    def pagos_limite(cls, v: list) -> list:

        if len(v) > 500:

            raise ValueError("Máximo 500 pagos por lote. Divida en varios envíos.")

        return v







logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])



# Límite de la columna numero_documento y referencia_pago en tabla pagos (String(100))

_MAX_LEN_NUMERO_DOCUMENTO = 100

# Validación de monto para NUMERIC(14, 2): máximo ~999,999,999,999.99 (12 dígitos antes del decimal)

_MAX_MONTO_PAGADO = 999_999_999_999.99

_MIN_MONTO_PAGADO = 0.01  # Monto mínimo válido (> 0)

_PRESTAMO_ID_MAX = 2_147_483_647  # INT max en BD (32-bit signed)







# Marca de sistema para auditoría cuando JWT no trae email (evita usuario_registro vacío en BD).

_USUARIO_REGISTRO_FALLBACK = "import-masivo@sistema.rapicredit.com"





def _usuario_registro_desde_current_user(current_user: Optional[Any]) -> str:

    """

    Email del usuario o identificador estable para auditoría.

    No devuelve cadena vacía (los lotes MER/BNC quedan trazables).

    """

    if current_user is None:

        return _USUARIO_REGISTRO_FALLBACK

    email = getattr(current_user, "email", None)

    if email is None and isinstance(current_user, dict):

        email = current_user.get("email")

    if isinstance(email, str) and email.strip():

        return email.strip()[:255]

    uid = getattr(current_user, "id", None)

    if uid is None and isinstance(current_user, dict):

        uid = current_user.get("id")

    if uid is not None:

        return f"user_id:{uid}@{_USUARIO_REGISTRO_FALLBACK}"[:255]

    return _USUARIO_REGISTRO_FALLBACK





# Todas las funciones de normalización de documento están centralizadas en app.core.documento

# Se usan ahora: normalize_documento() que consolidaba las 3 funciones anteriores.

# Esto evita duplicación y facilita mantenimiento.







def _validar_monto(monto_raw: Any) -> tuple[bool, float, str]:

    """

    Valida que el monto esté dentro de los rangos permitidos para NUMERIC(14, 2).

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

        # Probablemente es una fecha convertida a número de Excel (días desde 1900)

        # Las fechas en Excel típicamente son números entre 1 y ~50000

        if monto < 100000:

            return (False, monto, f"Monto sospechosamente pequeño para ser una cantidad; parece ser una fecha o número de secuencia: {monto}")

        return (False, monto, f"Monto excede límite máximo ({_MAX_MONTO_PAGADO}): {monto}")

    

    return (True, monto, "")





def _celda_a_string_documento(val: Any) -> str:

    """

    Convierte el valor de una celda Excel a string para Nº documento.

    Acepta cualquier tipo: str, int, float (evita notación científica para números largos).

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

    Usada para calcular dias_mora, detectar vencimientos, y acciones automáticas.

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

        "PENDIENTE": [
            "PAGADO",
            "PAGO_ADELANTADO",
            "VENCIDO",
            "MORA",
            "PENDIENTE",
            "PARCIAL",
        ],

        "PARCIAL": [
            "PAGADO",
            "PAGO_ADELANTADO",
            "VENCIDO",
            "MORA",
            "PARCIAL",
            "PENDIENTE",
        ],

        "VENCIDO": ["PAGADO", "PAGO_ADELANTADO", "VENCIDO", "MORA", "PARCIAL"],

        "MORA": ["PAGADO", "PAGO_ADELANTADO", "VENCIDO", "MORA", "PARCIAL"],

        "PAGO_ADELANTADO": ["PAGADO", "PAGO_ADELANTADO"],

        "PAGADO": ["PAGADO"],

    }

    return estado_nuevo in transiciones_permitidas.get(estado_anterior, [])





def _calcular_dias_mora(fecha_vencimiento: date) -> int:

    """

    Dias calendario desde fecha_vencimiento hasta hoy (America/Caracas), no negativos.

    """

    return dias_retraso_desde_vencimiento(fecha_vencimiento, _hoy_local())





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

        "moneda_registro": getattr(row, "moneda_registro", None),

        "monto_bs_original": float(row.monto_bs_original) if getattr(row, "monto_bs_original", None) is not None else None,

        "tasa_cambio_bs_usd": float(row.tasa_cambio_bs_usd) if getattr(row, "tasa_cambio_bs_usd", None) is not None else None,

        "fecha_tasa_referencia": row.fecha_tasa_referencia.isoformat() if getattr(row, "fecha_tasa_referencia", None) else None,

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

            # Excluir pagos ya movidos a revisar_pagos (tabla temporal de validación)

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

        # Orden: más reciente primero (fecha_pago desc, luego id desc)

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

    MAX_ROWS = 10000  # Límite máximo de filas (rechazo si se supera)

    MAX_ROWS_RECOMENDADO = 2500  # Sin sobrecarga ni timeouts en servidor típico

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

                detail=f"El archivo tiene demasiadas filas ({len(rows)}). Máximo permitido: {MAX_ROWS}. Para evitar sobrecarga, se recomienda hasta {MAX_ROWS_RECOMENDADO} filas.",

            )

        if len(rows) > MAX_ROWS_RECOMENDADO:

            logger.warning(

                "Carga masiva con %s filas (recomendado hasta %s). Puede haber timeouts o lentitud.",

                len(rows),

                MAX_ROWS_RECOMENDADO,

            )



        def _looks_like_cedula(v: Any) -> bool:

            """Cédula válida: solo V, E o J + 6-11 dígitos (no se admite Z)."""

            if v is None:

                return False

            s = str(v).strip()

            return bool(re.match(r"^[VEJ]\d{6,11}$", s, re.IGNORECASE))



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

            """Obtiene el valor de documento: primero columna indicada; si vacío, busca en todas las celdas (fallback)."""

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



        # --- FASE 1: Parsear todas las filas (ingresar todos los datos para validar después) ---

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

                # Formato D (PRINCIPAL): Cédula, Monto, Fecha, Nº documento

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

                # Formato A: Documento, Cédula, Fecha, Monto

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

                    # Fila con datos pero no matchea D, A ni B. Si primera columna no es cédula ? formato no reconocido.

                    row_has_content = any(cell is not None and str(cell).strip() for cell in row)

                    first_cell = str(row[0]).strip() if row[0] is not None else ""

                    if row_has_content and first_cell and not _looks_like_cedula(row[0]):

                        err_formato = "Formato de fila no reconocido. Use Cédula | Monto | Fecha | Documento (o los formatos soportados)."

                        errores.append(f"Fila {i + 2}: {err_formato}")

                        pagos_con_error_list.append({

                            "fila_idx": i + 2,

                            "cedula": first_cell[:100] or "",

                            "prestamo_id": None,

                            "fecha_val": row[2] if len(row) > 2 else None,

                            "monto": 0.0,

                            "numero_doc": _celda_a_string_documento(row[4]) if len(row) > 4 else "",

                            "errores": [err_formato],

                        })

                        continue

                    # Formato C (Alternativo): Cédula, ID Préstamo, Fecha, Monto, Nº documento

                    cedula = first_cell or (str(row[0]).strip() if row[0] is not None else "")

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



                # Fallback: si documento vacío, buscar en cualquier celda de la fila

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



        # --- FASE 2: Validar documentos (única regla: no duplicados) e insertar ---

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



            # Validación post-documentos: duplicado en archivo ? enviar a pagos_con_errores

            if key_doc and key_doc in numeros_doc_en_lote:

                err_msg = "Nº documento duplicado en este archivo. Regla general: no se aceptan duplicados en documentos."

                errores.append(f"Fila {i}: Nº documento duplicado en este archivo")

                errores_detalle.append({"fila": i, "cedula": cedula, "error": err_msg, "datos": {"cedula": cedula, "prestamo_id": prestamo_id, "fecha_pago": fecha_val, "monto_pagado": monto, "numero_documento": numero_doc or ""}})

                pagos_con_error_list.append({

                    "fila_idx": i,

                    "cedula": cedula or "",

                    "prestamo_id": prestamo_id,

                    "fecha_val": fecha_val,

                    "monto": monto,

                    "numero_doc": numero_doc or "",

                    "errores": [err_msg],

                })

                continue



            # Validación post-documentos: duplicado en BD ? enviar a pagos_con_errores

            if key_doc:

                if key_doc in documentos_ya_en_bd:

                    err_msg = "Ya existe un pago con ese Nº de documento. Regla general: no se aceptan duplicados en documentos."

                    errores.append(f"Fila {i}: Ya existe un pago con ese Nº de documento")

                    errores_detalle.append({"fila": i, "cedula": cedula, "error": err_msg, "datos": {"cedula": cedula, "prestamo_id": prestamo_id, "fecha_pago": fecha_val, "monto_pagado": monto, "numero_documento": numero_doc or ""}})

                    pagos_con_error_list.append({

                        "fila_idx": i,

                        "cedula": cedula or "",

                        "prestamo_id": prestamo_id,

                        "fecha_val": fecha_val,

                        "monto": monto,

                        "numero_doc": numero_doc or "",

                        "errores": [err_msg],

                    })

                    continue

                numeros_doc_en_lote.add(key_doc)



            # Identificación automática de préstamo: si la cédula tiene exactamente 1 crédito activo, asignarlo

            if prestamo_id is None and cedula.strip():

                cedula_norm = cedula.strip().upper()

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

                count_prestamos = len(prestamos_activos)

                if count_prestamos > 1:

                    err_msg = f"Esta persona tiene {count_prestamos} préstamos. Debe indicar el ID del préstamo."

                    errores.append(f"Fila {i}: La cédula {cedula} tiene {count_prestamos} préstamos. Debe indicar el ID del préstamo.")

                    errores_detalle.append({"fila": i, "cedula": cedula, "error": err_msg, "datos": {"cedula": cedula, "prestamo_id": prestamo_id, "fecha_pago": fecha_val, "monto_pagado": monto, "numero_documento": numero_doc or ""}})

                    pagos_con_error_list.append({

                        "fila_idx": i,

                        "cedula": cedula or "",

                        "prestamo_id": prestamo_id,

                        "fecha_val": fecha_val,

                        "monto": monto,

                        "numero_doc": numero_doc or "",

                        "errores": [err_msg],

                    })

                    continue

                if count_prestamos == 1:

                    prestamo_id = prestamos_activos[0][0]



            try:

                fecha_pago = _parse_fecha(fecha_val)

                ref_pago = ((numero_doc_norm or (numero_doc or "").strip()) or "Carga")[:_MAX_LEN_NUMERO_DOCUMENTO]

                usuario_registro = _usuario_registro_desde_current_user(current_user)

                # Autoconciliar: pagos creados por carga Excel se marcan conciliados (aplicados a cuotas después)

                ahora_up = datetime.now(ZoneInfo(TZ_NEGOCIO))

                p = Pago(

                    cedula_cliente=cedula.strip().upper() if cedula else "",

                    prestamo_id=prestamo_id,

                    fecha_pago=datetime.combine(fecha_pago, dt_time.min),

                    monto_pagado=monto,

                    numero_documento=numero_doc_norm,

                    estado="PENDIENTE",

                    referencia_pago=ref_pago,

                    usuario_registro=usuario_registro,  # [MEJORADO] Usuario real desde JWT

                    conciliado=True,

                    fecha_conciliacion=ahora_up,

                    verificado_concordancia="SI",

                )

                db.add(p)

                registros += 1

                if prestamo_id and monto > 0:

                    pagos_con_prestamo.append(p)

            except Exception as e:

                err_msg = str(e)

                errores.append(f"Fila {i}: {e}")

                errores_detalle.append({"fila": i, "cedula": cedula, "error": err_msg, "datos": {"cedula": cedula, "prestamo_id": prestamo_id, "fecha_pago": fecha_val, "monto_pagado": monto, "numero_documento": numero_doc or ""}})

                pagos_con_error_list.append({

                    "fila_idx": i,

                    "cedula": cedula or "",

                    "prestamo_id": prestamo_id,

                    "fecha_val": fecha_val,

                    "monto": monto,

                    "numero_doc": numero_doc or "",

                    "errores": [err_msg],

                })

        db.flush()  # Asigna IDs a los pagos insertados

        # --- GUARDAR PAGOS CON ERRORES EN BD ---

        for pce_data in pagos_con_error_list:

            try:

                pce = PagoConError(

                    cedula_cliente=pce_data["cedula"].strip().upper() if pce_data["cedula"] else "",  # Normalize

                    prestamo_id=pce_data["prestamo_id"],

                    fecha_pago=datetime.combine(_parse_fecha(pce_data["fecha_val"]), dt_time.min) if pce_data["fecha_val"] else datetime.now(),

                    monto_pagado=pce_data["monto"],

                    numero_documento=normalize_documento(pce_data.get("numero_doc")),

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

            "pagos_articulados": pagos_articulados,  # [NUEVA] Número de pagos que se articularon a cuotas

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





def importar_un_pago_reportado_a_pagos(

    db: Session,

    pr: PagoReportado,

    *,

    usuario_email: str,

    documentos_ya_en_bd: set[str],

    docs_en_lote: set[str],

    registrar_error_en_tabla: bool = True,

) -> dict:

    """

    Crea un Pago desde un PagoReportado con las mismas validaciones que importar-desde-cobros.

    No hace commit ni aplica a cuotas (el lote o el caller aplican después).

    Retorna {"ok": True, "pago": Pago} o {"ok": False, "error": str, "referencia": ..., "pce_id": int|None}.

    """

    ref_display = (pr.referencia_interna or "").strip()[:100] or None



    def _err(msg: str) -> dict:

        return {"ok": False, "error": msg, "referencia": pr.referencia_interna, "pce_id": None}



    def _err_con_pce(msg: str, **pce_kw) -> dict:

        if not registrar_error_en_tabla:

            return _err(msg)

        ref = (pr.referencia_interna or "").strip()[:100] or "N/A"

        pce = DatosImportadosConErrores(

            cedula_cliente=pce_kw.get("cedula_cliente", ""),

            prestamo_id=pce_kw.get("prestamo_id"),

            fecha_pago=datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now(),

            monto_pagado=float(pr.monto or 0),

            numero_documento=(pr.referencia_interna or "")[:100],

            estado="PENDIENTE",

            referencia_pago=ref,

            errores_descripcion=[msg],

            observaciones=ORIGEN_COBROS_REPORTADOS,

            referencia_interna=(pr.referencia_interna or "")[:100] or None,

            fila_origen=pr.id,

        )

        db.add(pce)

        db.flush()

        return {"ok": False, "error": msg, "referencia": pr.referencia_interna, "pce_id": pce.id}



    cedula_raw = f"{pr.tipo_cedula or ''}{pr.numero_cedula or ''}".replace("-", "").strip().upper()

    if not cedula_raw:

        return _err_con_pce("Cédula vacía", cedula_cliente="")



    if not _looks_like_cedula_inline(cedula_raw):

        return _err_con_pce(

            "Cédula inválida. Formato: V, E o J + 6-11 dígitos (igual que Pagos desde Excel).",

            cedula_cliente=cedula_raw,

        )



    numero_doc_raw = (pr.referencia_interna or "").strip()[:100]

    numero_doc_norm = normalize_documento(numero_doc_raw)

    if numero_doc_norm and numero_doc_norm in documentos_ya_en_bd:

        return _err_con_pce("Ya existe un pago con ese Nº documento (duplicado en BD)", cedula_cliente=cedula_raw)

    if numero_doc_norm and numero_doc_norm in docs_en_lote:

        return _err_con_pce("Nº documento duplicado en este lote", cedula_cliente=cedula_raw)



    cliente = db.execute(

        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_raw)

    ).scalars().first()

    if not cliente:

        return _err_con_pce("Cédula no encontrada en clientes", cedula_cliente=cedula_raw)



    prestamos = db.execute(

        select(Prestamo)

        .where(Prestamo.cliente_id == cliente.id, Prestamo.estado == "APROBADO")

        .order_by(Prestamo.id)

    ).scalars().all()

    prestamos = [p for p in prestamos if p is not None]

    if len(prestamos) == 0:

        return _err_con_pce("Sin crédito activo (APROBADO)", cedula_cliente=cedula_raw)

    if len(prestamos) > 1:

        return _err_con_pce(

            f"Cédula con {len(prestamos)} préstamos; indique ID del crédito",

            cedula_cliente=cedula_raw,

        )



    prestamo_id = prestamos[0].id

    moneda_pr = (getattr(pr, "moneda", None) or "USD").strip().upper()

    if moneda_pr == "USDT":

        moneda_pr = "USD"

    monto = float(pr.monto or 0)

    monto_bs_original = None

    tasa_aplicada = None

    fecha_tasa_ref = None

    if moneda_pr == "BS":

        if not pr.fecha_pago:

            return _err_con_pce(

                "Fecha de pago requerida para convertir bolivares a USD",

                cedula_cliente=cedula_raw,

                prestamo_id=prestamo_id,

            )

        tasa_obj = obtener_tasa_por_fecha(db, pr.fecha_pago)

        if tasa_obj is None:

            return _err_con_pce(

                "No hay tasa de cambio registrada para la fecha de pago "

                f"{pr.fecha_pago.isoformat()}; no se puede importar en bolivares",

                cedula_cliente=cedula_raw,

                prestamo_id=prestamo_id,

            )

        tasa_aplicada = float(tasa_obj.tasa_oficial)

        monto_bs_original = monto

        try:

            monto = convertir_bs_a_usd(monto_bs_original, tasa_aplicada)

        except ValueError as e:

            return _err_con_pce(str(e), cedula_cliente=cedula_raw, prestamo_id=prestamo_id)

        fecha_tasa_ref = pr.fecha_pago

    elif moneda_pr != "USD":

        return _err_con_pce(

            f"Moneda no soportada en importacion: {moneda_pr}",

            cedula_cliente=cedula_raw,

            prestamo_id=prestamo_id,

        )

    if monto < _MIN_MONTO_PAGADO:

        return _err_con_pce(

            f"Monto debe ser mayor a {_MIN_MONTO_PAGADO}",

            cedula_cliente=cedula_raw,

            prestamo_id=prestamo_id,

        )



    ref_pago = (numero_doc_norm or numero_doc_raw or "Cobros")[:_MAX_LEN_NUMERO_DOCUMENTO]

    ahora_imp = datetime.now(ZoneInfo(TZ_NEGOCIO))

    p = Pago(

        cedula_cliente=cedula_raw,

        prestamo_id=prestamo_id,

        fecha_pago=datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now(),

        monto_pagado=Decimal(str(round(monto, 2))),

        numero_documento=numero_doc_norm,

        estado="PENDIENTE",

        referencia_pago=ref_pago,

        usuario_registro=usuario_email,

        conciliado=True,

        fecha_conciliacion=ahora_imp,

        verificado_concordancia="SI",

        moneda_registro=moneda_pr,

        monto_bs_original=Decimal(str(round(monto_bs_original, 2))) if monto_bs_original is not None else None,

        tasa_cambio_bs_usd=Decimal(str(tasa_aplicada)) if tasa_aplicada is not None else None,

        fecha_tasa_referencia=fecha_tasa_ref,

    )

    db.add(p)

    db.flush()

    if numero_doc_norm:

        docs_en_lote.add(numero_doc_norm)

        documentos_ya_en_bd.add(numero_doc_norm)

    return {"ok": True, "pago": p, "referencia": ref_display, "pce_id": None}







ORIGEN_COBROS_REPORTADOS = "Cobros (reportados aprobados)"





@router.post("/importar-desde-cobros", response_model=dict)

def importar_reportados_aprobados_a_pagos(

    db: Session = Depends(get_db),

    current_user: UserResponse = Depends(get_current_user),

):

    """

    Pasa los pagos reportados (módulo Cobros) con estado aprobado a la tabla pagos.

    Mismas reglas que carga masiva: documento único, cédula con 1 crédito activo (APROBADO).

    Los que no cumplen se guardan en datos_importados_conerrores; descargar Excel desde el frontend.

    Los pagos válidos se aplican a cuotas del préstamo (asignación en cascada) en el mismo request.

    """

    rows = db.execute(

        select(PagoReportado).where(PagoReportado.estado == "aprobado").order_by(PagoReportado.id)

    ).scalars().all()

    reportados = [r for r in rows if r is not None]

    if not reportados:

        return {

            "registros_procesados": 0,

            "registros_con_error": 0,

            "errores_detalle": [],

            "ids_pagos_con_errores": [],

            "total_datos_revisar": 0,

            "mensaje": "No hay pagos reportados aprobados para importar.",

            "cuotas_aplicadas": 0,

            "operaciones_cuota_total": 0,

            "pagos_con_aplicacion_a_cuotas": 0,

            "pagos_sin_aplicacion_cuotas": [],

            "pagos_sin_aplicacion_cuotas_total": 0,

            "pagos_sin_aplicacion_cuotas_truncados": False,

        }



    usuario_registro = _usuario_registro_desde_current_user(current_user)

    documentos_ya_en_bd: set[str] = set()

    docs_reportados = [normalize_documento(pr.referencia_interna) for pr in reportados if (pr.referencia_interna or "").strip()]

    if docs_reportados:

        existentes = db.execute(select(Pago.numero_documento).where(Pago.numero_documento.in_(docs_reportados))).scalars().all()

        documentos_ya_en_bd = {str(d) for d in existentes if d}



    registros_procesados = 0

    ids_pagos_con_errores: list[int] = []

    errores_detalle: list[dict] = []

    docs_en_lote: set[str] = set()

    pagos_creados: list[Pago] = []



    for pr in reportados:

        res = importar_un_pago_reportado_a_pagos(

            db,

            pr,

            usuario_email=usuario_registro,

            documentos_ya_en_bd=documentos_ya_en_bd,

            docs_en_lote=docs_en_lote,

            registrar_error_en_tabla=True,

        )

        if res.get("ok"):

            registros_procesados += 1

            pagos_creados.append(res["pago"])

            continue

        pce_id = res.get("pce_id")

        if pce_id is not None:

            ids_pagos_con_errores.append(pce_id)

        errores_detalle.append(

            {"referencia": res.get("referencia"), "error": res.get("error", "Error")}

        )





    operaciones_cuota_total = 0

    pagos_con_aplicacion_a_cuotas = 0

    pagos_sin_aplicacion_cuotas: list[dict] = []

    for p in pagos_creados:

        pid = getattr(p, "id", None)

        ced = (getattr(p, "cedula_cliente", None) or "") or ""

        pr_id = getattr(p, "prestamo_id", None)

        try:

            cc, cp = _aplicar_pago_a_cuotas_interno(p, db)

            p.estado = _estado_pago_tras_aplicar_cascada(cc, cp)

            if cc > 0 or cp > 0:

                operaciones_cuota_total += cc + cp

                pagos_con_aplicacion_a_cuotas += 1

            elif pr_id and float(p.monto_pagado or 0) > 0:

                pagos_sin_aplicacion_cuotas.append(

                    {

                        "pago_id": pid,

                        "cedula_cliente": ced,

                        "prestamo_id": pr_id,

                        "motivo": "sin_cuotas_afectadas",

                        "detalle": "Ninguna cuota recibió monto; revise cuotas pendientes o use Aplicar a cuotas.",

                    }

                )

        except Exception as e:

            logger.warning(

                "Importar Cobros: no se pudo aplicar pago id=%s a cuotas: %s",

                getattr(p, "id", "?"),

                e,

            )

            pagos_sin_aplicacion_cuotas.append(

                {

                    "pago_id": pid,

                    "cedula_cliente": ced,

                    "prestamo_id": pr_id,

                    "motivo": "error",

                    "detalle": str(e),

                }

            )

    db.commit()

    total_datos_revisar = db.execute(select(func.count()).select_from(DatosImportadosConErrores)).scalar() or 0

    n_sin_aplicacion = len(pagos_sin_aplicacion_cuotas)

    _limite_sin_aplicacion = 50

    mensaje_base = (

        f"Importados {registros_procesados} pagos desde Cobros; "

        f"{len(ids_pagos_con_errores)} con error (revisar: descargar Excel)."

    )

    if n_sin_aplicacion > 0:

        mensaje_base += (

            f" Atención: {n_sin_aplicacion} pago(s) creado(s) pero sin aplicar a cuotas "

            "(error o sin cuotas pendientes según reglas); use Aplicar a cuotas o revise el préstamo."

        )

    return {

        "registros_procesados": registros_procesados,

        "registros_con_error": len(ids_pagos_con_errores),

        "errores_detalle": errores_detalle[:100],

        "ids_pagos_con_errores": ids_pagos_con_errores,

        "cuotas_aplicadas": operaciones_cuota_total,

        "operaciones_cuota_total": operaciones_cuota_total,

        "pagos_con_aplicacion_a_cuotas": pagos_con_aplicacion_a_cuotas,

        "pagos_sin_aplicacion_cuotas": pagos_sin_aplicacion_cuotas[:_limite_sin_aplicacion],

        "pagos_sin_aplicacion_cuotas_total": n_sin_aplicacion,

        "pagos_sin_aplicacion_cuotas_truncados": n_sin_aplicacion > _limite_sin_aplicacion,

        "total_datos_revisar": total_datos_revisar,

        "mensaje": mensaje_base,

    }





@router.get("/importar-desde-cobros/datos-revisar", response_model=dict)

def get_datos_revisar_importados(

    db: Session = Depends(get_db),

    current_user: UserResponse = Depends(get_current_user),

):

    """Devuelve si hay datos que revisar (tabla datos_importados_conerrores) y el total. Para mostrar dialogo tras importar."""

    total = db.execute(select(func.count()).select_from(DatosImportadosConErrores)).scalar() or 0

    return {"tiene_datos": total > 0, "total": total}





@router.get("/importar-desde-cobros/descargar-excel-errores")

def descargar_excel_errores_importados(

    db: Session = Depends(get_db),

    current_user: UserResponse = Depends(get_current_user),

):

    """Genera Excel con registros de datos_importados_conerrores (mismas columnas que Revisar Pagos). Tras generar, vacia la tabla."""

    rows = db.execute(

        select(DatosImportadosConErrores).order_by(DatosImportadosConErrores.id)

    ).scalars().all()

    rows = [r for r in rows if r is not None]

    import openpyxl

    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()

    ws = wb.active

    ws.title = "Datos con errores"

    headers = [

        "id", "cedula_cliente", "prestamo_id", "fecha_pago", "monto_pagado", "numero_documento",

        "estado", "referencia_pago", "errores_descripcion", "observaciones", "fila_origen", "referencia_interna", "created_at"

    ]

    for col, h in enumerate(headers, 1):

        ws.cell(row=1, column=col, value=h)

    for row_idx, r in enumerate(rows, 2):

        fp = r.fecha_pago

        fecha_str = fp.strftime("%Y-%m-%d") if fp else ""

        err_str = "; ".join(r.errores_descripcion) if isinstance(r.errores_descripcion, list) else str(r.errores_descripcion or "")

        created_str = r.created_at.strftime("%Y-%m-%d %H:%M") if getattr(r, "created_at", None) else ""

        ws.cell(row=row_idx, column=1, value=r.id)

        ws.cell(row=row_idx, column=2, value=r.cedula_cliente or "")

        ws.cell(row=row_idx, column=3, value=r.prestamo_id)

        ws.cell(row=row_idx, column=4, value=fecha_str)

        ws.cell(row=row_idx, column=5, value=float(r.monto_pagado) if r.monto_pagado is not None else 0)

        ws.cell(row=row_idx, column=6, value=r.numero_documento or "")

        ws.cell(row=row_idx, column=7, value=r.estado or "")

        ws.cell(row=row_idx, column=8, value=r.referencia_pago or "")

        ws.cell(row=row_idx, column=9, value=err_str)

        ws.cell(row=row_idx, column=10, value=r.observaciones or "")

        ws.cell(row=row_idx, column=11, value=r.fila_origen)

        ws.cell(row=row_idx, column=12, value=getattr(r, "referencia_interna", None) or "")

        ws.cell(row=row_idx, column=13, value=created_str)

    buf = io.BytesIO()

    wb.save(buf)

    buf.seek(0)

    db.execute(delete(DatosImportadosConErrores))

    db.commit()

    filename = f"datos_importados_con_errores_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

    return StreamingResponse(

        buf,

        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

        headers={"Content-Disposition": f"attachment; filename={filename}"},

    )





@router.get("/export/excel/pagos-sin-aplicar-cuotas")

def export_excel_pagos_sin_aplicar_cuotas(

    cohorte: str = Query(

        "todos",

        description="todos (default): sin ninguna fila en cuota_pagos (no aplicados a cuotas). "

        "cascada (alias: fifo): ademas monto>0, prestamo_id, no ANULADO_IMPORT (cola del job). "

        "sin_cupo: como cascada (alias fifo) y sin cupo aplicable en cuotas PENDIENTE/MORA/PARCIAL.",

    ),

    db: Session = Depends(get_db),

    current_user: UserResponse = Depends(get_current_user),

):

    """

    Descarga Excel con pagos que no tienen aplicacion a cuotas (sin filas en cuota_pagos).

    Por defecto cohorte=todos incluye todos esos pagos. Requiere autenticacion. Maximo 200000 filas.

    """

    c = (cohorte or "todos").strip().lower()

    if c == "cascada":

        c = "fifo"

    if c not in ("todos", "fifo", "sin_cupo"):

        raise HTTPException(status_code=400, detail="cohorte debe ser todos, cascada (alias: fifo), o sin_cupo")



    import openpyxl



    tiene_cuota_pago = exists(select(CuotaPago.id).where(CuotaPago.pago_id == Pago.id))

    if c == "todos":

        cond_final = ~tiene_cuota_pago

    else:

        cond_base = and_(

            ~tiene_cuota_pago,

            func.coalesce(Pago.monto_pagado, 0) > 0,

            func.upper(func.coalesce(Pago.estado, "")) != "ANULADO_IMPORT",

            Pago.prestamo_id.isnot(None),

        )

        if c == "sin_cupo":

            aplicado_en_cuota = (

                select(func.coalesce(func.sum(CuotaPago.monto_aplicado), 0))

                .where(CuotaPago.cuota_id == Cuota.id)

                .correlate(Cuota)

                .scalar_subquery()

            )

            hay_cupo_aplicable = exists(

                select(1)

                .select_from(Cuota)

                .where(

                    and_(

                        Cuota.prestamo_id == Pago.prestamo_id,

                        Cuota.estado.in_(["PENDIENTE", "VENCIDO", "MORA", "PARCIAL"]),

                        (func.coalesce(Cuota.monto, 0) - aplicado_en_cuota) > 0.01,

                    )

                )

            )

            cond_final = and_(cond_base, ~hay_cupo_aplicable)

        else:

            cond_final = cond_base



    rows = (

        db.execute(

            select(Pago)

            .where(cond_final)

            .order_by(Pago.fecha_registro.asc(), Pago.id.asc())

            .limit(200000)

        )

        .scalars()

        .all()

    )

    rows = [r for r in rows if r is not None]



    wb = openpyxl.Workbook()

    ws = wb.active

    ws.title = "Pagos sin aplicar"

    headers = [

        "pago_id",

        "fecha_registro",

        "fecha_pago",

        "prestamo_id",

        "cedula",

        "monto_pagado",

        "estado",

        "referencia_pago",

        "numero_documento",

        "conciliado",

        "usuario_registro",

        "cohorte_filtro",

    ]

    for col, h in enumerate(headers, 1):

        ws.cell(row=1, column=col, value=h)

    for row_idx, p in enumerate(rows, 2):

        fr = p.fecha_registro

        fp = p.fecha_pago

        ws.cell(row=row_idx, column=1, value=p.id)

        ws.cell(row=row_idx, column=2, value=fr.strftime("%Y-%m-%d %H:%M:%S") if fr else "")

        ws.cell(row=row_idx, column=3, value=fp.strftime("%Y-%m-%d %H:%M:%S") if fp else "")

        ws.cell(row=row_idx, column=4, value=p.prestamo_id)

        ws.cell(row=row_idx, column=5, value=(p.cedula_cliente or ""))

        ws.cell(row=row_idx, column=6, value=float(p.monto_pagado) if p.monto_pagado is not None else 0)

        ws.cell(row=row_idx, column=7, value=p.estado or "")

        ws.cell(row=row_idx, column=8, value=p.referencia_pago or "")

        ws.cell(row=row_idx, column=9, value=p.numero_documento or "")

        ws.cell(row=row_idx, column=10, value=bool(p.conciliado) if p.conciliado is not None else False)

        ws.cell(row=row_idx, column=11, value=p.usuario_registro or "")

        ws.cell(row=row_idx, column=12, value=c)



    buf = io.BytesIO()

    wb.save(buf)

    buf.seek(0)

    fname = f"pagos_sin_aplicar_cuotas_{c}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

    return StreamingResponse(

        buf,

        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",

        headers={"Content-Disposition": f"attachment; filename={fname}"},

    )





@router.post("/validar-filas-batch", response_model=dict)

def validar_filas_batch(

    body: ValidarFilasBatchBody = Body(...),

    db: Session = Depends(get_db),

):

    """

    Valida en lote (carga masiva / preview):

    - Cédulas: deben existir en tabla préstamos (al menos un crédito con esa cédula normalizada).

    - Nº documento: clave canónica única global; ya usada en `pagos` o en `pagos_con_errores` → duplicado.

      (Un solo registro por documento; las cuotas referencian ese pago vía pago_id.)

    """

    cedulas_norm = list(

        {

            c.strip().replace("-", "").upper()

            for c in (body.cedulas or [])

            if c and c.strip()

        }

    )

    cedulas_existentes: set[str] = set()

    if cedulas_norm:

        pc = func.upper(func.replace(Prestamo.cedula, "-", ""))

        rows = db.execute(select(pc).where(pc.in_(cedulas_norm)).distinct()).all()

        cedulas_existentes = {r[0] for r in rows if r and r[0]}

    documentos_duplicados: list[dict] = []

    docs_norm = [

        normalize_documento(d)

        for d in (body.documentos or [])

        if d and d.strip()

    ]

    docs_norm_limpios = [d for d in docs_norm if d]

    if docs_norm_limpios:

        rows_pagos = db.execute(

            select(

                Pago.numero_documento,

                Pago.id,

                Pago.cedula_cliente,

                Pago.fecha_pago,

                Pago.monto_pagado,

            ).where(Pago.numero_documento.in_(docs_norm_limpios))

        ).all()

        for row in rows_pagos:

            documentos_duplicados.append(

                {

                    "numero_documento": row[0],

                    "pago_id": row[1],

                    "cedula": row[2],

                    "fecha_pago": row[3].isoformat() if row[3] else None,

                    "monto_pagado": float(row[4]) if row[4] else 0,

                    "estado": "duplicado",

                    "origen": "pagos",

                }

            )

        rows_pce = db.execute(

            select(

                PagoConError.numero_documento,

                PagoConError.id,

                PagoConError.cedula_cliente,

                PagoConError.fecha_pago,

                PagoConError.monto_pagado,

            ).where(PagoConError.numero_documento.in_(docs_norm_limpios))

        ).all()

        for row in rows_pce:

            documentos_duplicados.append(

                {

                    "numero_documento": row[0],

                    "pago_con_error_id": row[1],

                    "cedula": row[2],

                    "fecha_pago": row[3].isoformat() if row[3] else None,

                    "monto_pagado": float(row[4]) if row[4] else 0,

                    "estado": "duplicado",

                    "origen": "pagos_con_errores",

                }

            )

    return {

        "cedulas_existentes": list(cedulas_existentes),

        "documentos_duplicados": documentos_duplicados,

    }





@router.post("/guardar-fila-editable", response_model=dict)

def guardar_fila_editable(

    body: GuardarFilaEditableBody = Body(...),

    db: Session = Depends(get_db),

    current_user: UserResponse = Depends(get_current_user),

):

    """

    Guarda una fila editable validada (desde Preview).

    Si cumple validadores, inserta en pagos, aplica cuotas y retorna éxito.

    Auto-marca como conciliado ('SI') para aplicar reglas de negocio inmediatamente.

    """

    try:

        cedula = (body.cedula or "").strip()

        monto = body.monto_pagado

        numero_doc = (body.numero_documento or "").strip() if body.numero_documento else None

        prestamo_id = body.prestamo_id

        usuario_registro = _usuario_registro_desde_current_user(current_user)



        # Validaciones post-guardado

        if not cedula:

            raise HTTPException(status_code=400, detail="Cédula requerida")

        if not _looks_like_cedula_inline(cedula):

            raise HTTPException(status_code=400, detail="Cédula inválida (debe ser V/E/J/Z + 6-11 dígitos)")


        cedula_norm_in = normalizar_cedula_almacenamiento(cedula)
        if not cedula_norm_in:
            raise HTTPException(status_code=400, detail="Cédula requerida")
        cli_por_cedula = db.execute(
            select(Cliente.id).where(Cliente.cedula == cedula_norm_in).limit(1)
        ).first()
        if not cli_por_cedula:
            raise HTTPException(
                status_code=400,
                detail="La cédula no está registrada en clientes. No se puede guardar el pago.",
            )

        if monto <= 0:

            raise HTTPException(status_code=400, detail="Monto debe ser > 0")

        if monto > _MAX_MONTO_PAGADO:

            raise HTTPException(status_code=400, detail=f"Monto excede límite máximo: {_MAX_MONTO_PAGADO}")



        # Parsear fecha

        try:

            fecha_pago = datetime.strptime(body.fecha_pago[:10], "%d-%m-%Y").date()

        except (ValueError, IndexError):

            raise HTTPException(status_code=400, detail="Fecha inválida (formato: DD-MM-YYYY)")



        # Normalizar documento

        numero_doc_norm = normalize_documento(numero_doc)



        # Validar duplicado global (pagos + pagos_con_errores)

        if numero_doc_norm and numero_documento_ya_registrado(db, numero_doc_norm):

            raise HTTPException(

                status_code=409,

                detail=f"Ya existe un registro con este documento: {numero_doc_norm}",

            )



        # Si prestamo_id es None, buscar por cédula en préstamos (normalizada)

        if prestamo_id is None:

            ced_norm = (

                cedula.strip().replace("-", "").upper()

                if cedula

                else ""

            )

            if ced_norm:

                pc = func.upper(func.replace(Prestamo.cedula, "-", ""))

                prest_row = db.execute(

                    select(Prestamo.id)

                    .where(pc == ced_norm)

                    .order_by(Prestamo.id.desc())

                    .limit(1)

                ).first()

                if prest_row:

                    prestamo_id = prest_row[0]



        if prestamo_id is None:

            raise HTTPException(

                status_code=400,

                detail="La cédula no tiene préstamo asociado; registre el crédito antes de cargar el pago.",

            )



        # Cedula en pagos debe existir en clientes (FK fk_pagos_cedula): usar la del cliente del prestamo.
        prest = db.get(Prestamo, prestamo_id)
        if not prest:
            raise HTTPException(status_code=404, detail="Prestamo no encontrado")
        cli = db.get(Cliente, prest.cliente_id)
        if not cli:
            raise HTTPException(
                status_code=400,
                detail="El prestamo no tiene cliente asociado en BD; no se puede registrar el pago.",
            )
        cedula_fk = normalizar_cedula_almacenamiento(cli.cedula) or normalizar_cedula_almacenamiento(
            prest.cedula
        )
        if not cedula_fk:
            raise HTTPException(status_code=400, detail="Cedula del cliente no disponible en BD.")
        cedula_input = normalizar_cedula_almacenamiento(cedula.strip())
        if cedula_input and cedula_input != cedula_fk:
            raise HTTPException(
                status_code=400,
                detail=f"La cedula no coincide con la del cliente del prestamo (en BD: {cedula_fk}).",
            )



        # Crear pago

        # [A2] Marcar conciliado=True y verificado_concordancia="SI" desde el momento de la creación,

        # ya que guardar-fila-editable implica que el pago fue revisado y validado manualmente.

        ref_pago = (numero_doc_norm or (numero_doc or "Carga"))[:_MAX_LEN_NUMERO_DOCUMENTO]

        ahora_conciliacion = datetime.now(ZoneInfo(TZ_NEGOCIO))

        pago = Pago(

            cedula_cliente=cedula_fk,

            prestamo_id=prestamo_id,

            fecha_pago=datetime.combine(fecha_pago, dt_time.min),

            monto_pagado=Decimal(str(round(monto, 2))),

            numero_documento=numero_doc_norm,

            estado="PENDIENTE",

            referencia_pago=ref_pago,

            conciliado=True,  # [B2] Usar solo conciliado

            fecha_conciliacion=ahora_conciliacion,

            verificado_concordancia="SI",  # Legacy: sync con conciliado

            usuario_registro=usuario_registro,

        )

        db.add(pago)

        db.flush()



        # Aplicar a cuotas si prestamo_id existe

        cuotas_completadas = 0

        cuotas_parciales = 0

        if pago.prestamo_id and monto > 0:

            cuotas_completadas, cuotas_parciales = _aplicar_pago_a_cuotas_interno(pago, db)

        pago.estado = _estado_pago_tras_aplicar_cascada(cuotas_completadas, cuotas_parciales)



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

    """Validar cédula inline: solo V, E o J + 6-11 dígitos (no se admite Z)."""

    return bool(re.match(r"^[VEJ]\d{6,11}$", cedula.strip(), re.IGNORECASE))





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

        pagos_para_aplicar: list[Pago] = []

        for i, row in enumerate(rows):

            if not row or (row[0] is None and row[1] is None):

                continue

            try:

                numero_doc_raw = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""

                if not numero_doc_raw:

                    continue

                # Misma clave canónica que carga/crear: cualquier formato reconocido, búsqueda por valor normalizado

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

        logger.exception("Error upload conciliación: %s", e)

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

    1. montoACobrarMes: cuánto dinero debería cobrarse en el mes (cuotas con vencimiento en el mes).

    2. montoCobradoMes: cuánto dinero se ha cobrado = pagado en el mes.

    3. morosidadMensualPorcentaje: pago vencido mensual en % (cuotas vencidas no cobradas / cartera * 100).

    Parámetros: mes (1-12) y anio (2000-2100). Si no se envían, se usa el mes actual.

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



        # Una sola consulta con agregación condicional para los 5 montos (menos round-trips a BD)

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



        # Conteos: clientes en mora y clientes con préstamo (2 consultas ligeras)

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

    """Condiciones base para filtrar cuotas por préstamo (solo clientes ACTIVOS + analista/concesionario/modelo)."""

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

    Estadísticas de pagos desde BD (solo clientes ACTIVOS): total_pagos, total_pagado, pagos_por_estado,

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

    Mueve los pagos exportados a la tabla revisar_pagos (temporal de validación).

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





@router.get("/{pago_id:int}", response_model=dict)

def obtener_pago(pago_id: int, db: Session = Depends(get_db)):

    """Obtiene un pago por ID desde la tabla pagos."""

    row = db.get(Pago, pago_id)

    if not row:

        raise HTTPException(status_code=404, detail="Pago no encontrado")

    return _pago_to_response(row)





@router.post("/batch", response_model=dict)

def crear_pagos_batch(

    body: PagoBatchBody,

    db: Session = Depends(get_db),

    current_user: UserResponse = Depends(get_current_user),

):

    """

    Crea varios pagos en una sola petición (máx. 500).

    Devuelve éxitos y errores por índice para reducir rondas y timeouts en "Guardar todos".

    Optimizado: una sola consulta para docs existentes, préstamos y clientes en lugar de N por fila.

    """

    try:

        usuario_registro = _usuario_registro_desde_current_user(current_user)

        pagos_list = body.pagos

        # Preload: documentos ya existentes en BD (una sola consulta)

        docs_en_payload = [normalize_documento(p.numero_documento) for p in pagos_list]

        docs_no_vacios = [d for d in docs_en_payload if d]

        existing_docs: set[str] = set()

        if docs_no_vacios:

            rows = db.execute(select(Pago.numero_documento).where(Pago.numero_documento.in_(docs_no_vacios))).scalars().all()

            existing_docs = {r for r in rows if r}

            rows_pe = db.execute(

                select(PagoConError.numero_documento).where(

                    PagoConError.numero_documento.in_(docs_no_vacios)

                )

            ).scalars().all()

            existing_docs.update({r for r in rows_pe if r})

        # Preload: ids de préstamos válidos (una sola consulta)

        prestamo_ids = [p.prestamo_id for p in pagos_list if p.prestamo_id]

        valid_prestamo_ids: set[int] = set()

        if prestamo_ids:

            ids_rows = db.execute(select(Prestamo.id).where(Prestamo.id.in_(prestamo_ids))).scalars().all()

            valid_prestamo_ids = {r for r in ids_rows if r is not None}

        # Preload: cédulas que tienen al menos un préstamo (normalizadas)

        cedulas_payload = list(

            {

                (p.cedula_cliente or "").strip().replace("-", "").upper()

                for p in pagos_list

                if (p.cedula_cliente or "").strip()

            }

        )

        valid_cedulas_prestamo: set[str] = set()

        if cedulas_payload:

            pc = func.upper(func.replace(Prestamo.cedula, "-", ""))

            ced_rows = db.execute(select(pc).where(pc.in_(cedulas_payload)).distinct()).scalars().all()

            valid_cedulas_prestamo = {(r or "").strip().replace("-", "").upper() for r in ced_rows if r}

        # Compat: cliente existe cuando el payload trae prestamo_id explícito

        cedulas_con_prestamo = list(

            {

                (p.cedula_cliente or "").strip().upper()

                for p in pagos_list

                if (p.cedula_cliente or "").strip() and p.prestamo_id

            }

        )

        valid_cedulas: set[str] = set()

        if cedulas_con_prestamo:

            ced_rows_c = db.execute(

                select(Cliente.cedula).where(func.upper(Cliente.cedula).in_(cedulas_con_prestamo))

            ).scalars().all()

            valid_cedulas = {(r or "").strip().upper() for r in ced_rows_c if r}

        # Fase 1: validacion (sin insertar). Si hay errores, devolver sin commit.

        validation_errors: list[dict] = []

        docs_added_in_batch: set[str] = set()

        for idx, payload in enumerate(pagos_list):

            num_doc = docs_en_payload[idx] if idx < len(docs_en_payload) else normalize_documento(payload.numero_documento)

            if num_doc and (num_doc in existing_docs or num_doc in docs_added_in_batch):

                validation_errors.append({"index": idx, "error": "Ya existe un pago con ese numero de documento.", "status_code": 409})

                continue

            ref = (num_doc or "N/A")[:_MAX_LEN_NUMERO_DOCUMENTO]

            cedula_normalizada = (payload.cedula_cliente or "").strip().upper()

            ced_norm_prest = (payload.cedula_cliente or "").strip().replace("-", "").upper()

            if ced_norm_prest and ced_norm_prest not in valid_cedulas_prestamo:

                validation_errors.append(

                    {

                        "index": idx,

                        "error": f"La cédula no tiene préstamo registrado: {cedula_normalizada}",

                        "status_code": 400,

                    }

                )

                continue

            if payload.prestamo_id and payload.prestamo_id not in valid_prestamo_ids:

                validation_errors.append({"index": idx, "error": f"Credito #{payload.prestamo_id} no existe.", "status_code": 400})

                continue

            if cedula_normalizada and payload.prestamo_id and cedula_normalizada not in valid_cedulas:

                validation_errors.append({"index": idx, "error": f"No existe cliente con cedula {cedula_normalizada}", "status_code": 404})

                continue

            if num_doc:

                docs_added_in_batch.add(num_doc)

        if validation_errors:

            return {"results": [{"index": e["index"], "success": False, "error": e["error"], "status_code": e["status_code"]} for e in validation_errors], "ok_count": 0, "fail_count": len(validation_errors)}



        cedulas_lote = {

            (p.cedula_cliente or "").strip().upper()

            for p in pagos_list

            if (p.cedula_cliente or "").strip()

        }

        alinear_cedulas_clientes_existentes(db, cedulas_lote)



        # Fase 2: transaccion unica. Crear todos los pagos (flush), aplicar a cuotas, un commit al final.

        results: list[dict] = []

        try:

            for idx, payload in enumerate(pagos_list):

                num_doc = docs_en_payload[idx] if idx < len(docs_en_payload) else normalize_documento(payload.numero_documento)

                ref = (num_doc or "N/A")[:_MAX_LEN_NUMERO_DOCUMENTO]

                fecha_pago_ts = datetime.combine(payload.fecha_pago, dt_time.min)

                conciliado = payload.conciliado if payload.conciliado is not None else (True if payload.prestamo_id else False)

                cedula_normalizada = (payload.cedula_cliente or "").strip().upper()

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

                    usuario_registro=usuario_registro,

                )

                db.add(row)

                db.flush()

                db.refresh(row)

                if row.prestamo_id and float(row.monto_pagado or 0) > 0:

                    cc_b, cp_b = _aplicar_pago_a_cuotas_interno(row, db)

                    row.estado = _estado_pago_tras_aplicar_cascada(cc_b, cp_b)

                results.append({"index": idx, "success": True, "pago": _pago_to_response(row)})

            db.commit()

            return {"results": results, "ok_count": len(results), "fail_count": 0}

        except Exception as e:

            db.rollback()

            logger.exception("Batch: error en transaccion unica: %s", e)

            raise HTTPException(status_code=500, detail=f"Error al guardar el lote. Ningun pago fue creado. Detalle: {str(e)}")

    except HTTPException:

        raise

    except OperationalError:

        raise HTTPException(

            status_code=503,

            detail="Servicio no disponible. Reintente en unos segundos.",

        )

    except Exception as e:

        logger.exception("Batch: error inesperado: %s", e)

        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}") from e







@router.post("", response_model=dict, status_code=201)

def crear_pago(payload: PagoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):

    """Crea un pago. Documento acepta cualquier formato. Regla general: no duplicados (409 si ya existe)."""

    num_doc = normalize_documento(payload.numero_documento)

    if num_doc and numero_documento_ya_registrado(db, num_doc):

        raise HTTPException(

            status_code=409,

            detail="Ya existe un pago con ese Nº de documento. Regla general: no se aceptan duplicados en documentos.",

        )

    ref = (num_doc or "N/A")[:_MAX_LEN_NUMERO_DOCUMENTO]

    fecha_pago_ts = datetime.combine(payload.fecha_pago, dt_time.min)

    # Autoconciliar cuando se asigna a un préstamo y no se indica explícitamente conciliado

    conciliado = payload.conciliado if payload.conciliado is not None else (True if payload.prestamo_id else False)

    usuario_registro = _usuario_registro_desde_current_user(current_user)

    

    # Normalizar cédula: uppercase para evitar FK mismatch

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

            select(Cliente).where(func.upper(Cliente.cedula) == cedula_normalizada)

        ).scalars().first()

        if not cliente:

            raise HTTPException(

                status_code=404,

                detail=f"No existe cliente con cedula {cedula_normalizada}"

            )



    # Validar monto (mismo criterio que carga Excel y guardar-fila-editable)

    monto_raw = payload.monto_pagado

    es_valido, monto_val, err_msg = _validar_monto(monto_raw)

    if not es_valido:

        raise HTTPException(status_code=400, detail=err_msg)



    if cedula_normalizada:

        alinear_cedulas_clientes_existentes(db, [cedula_normalizada])



    try:

        row = Pago(

            cedula_cliente=cedula_normalizada,

            prestamo_id=payload.prestamo_id,

            fecha_pago=fecha_pago_ts,

            monto_pagado=Decimal(str(round(monto_val, 2))),

            numero_documento=num_doc,

            institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,

            estado="PENDIENTE",

            notas=payload.notas.strip() if payload.notas else None,

            referencia_pago=ref,

            conciliado=conciliado,  # [B2] Usar solo conciliado, no verificado_concordancia

            fecha_conciliacion=datetime.now(ZoneInfo(TZ_NEGOCIO)) if conciliado else None,

            verificado_concordancia="SI" if conciliado else "",  # Legacy: sync con conciliado

            usuario_registro=usuario_registro,  # [MEJORADO] Usuario real desde JWT

        )

        db.add(row)

        db.flush()

        db.refresh(row)

        # [C3] Aplicar cascada a cuotas en la misma transacción para que préstamos y estado de cuenta se actualicen

        if row.prestamo_id and float(row.monto_pagado or 0) > 0:

            cc_n, cp_n = _aplicar_pago_a_cuotas_interno(row, db)

            row.estado = _estado_pago_tras_aplicar_cascada(cc_n, cp_n)

        db.commit()

        db.refresh(row)

        return _pago_to_response(row)

    except HTTPException:

        raise

    except IntegrityError as e:

        db.rollback()

        # Unique violation (p. ej. numero_documento duplicado) ? 409

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





@router.put("/{pago_id:int}", response_model=dict)

def actualizar_pago(pago_id: int, payload: PagoUpdate, db: Session = Depends(get_db)):

    """Actualiza un pago en la tabla pagos. Nº documento no puede repetirse."""

    row = db.get(Pago, pago_id)

    if not row:

        raise HTTPException(status_code=404, detail="Pago no encontrado")

    data = payload.model_dump(exclude_unset=True)

    if "numero_documento" in data and data["numero_documento"] is not None:

        num_doc = normalize_documento(data["numero_documento"])

        if num_doc and numero_documento_ya_registrado(db, num_doc, exclude_pago_id=pago_id):

            raise HTTPException(

                status_code=409,

                detail="Ya existe otro pago con ese Nº de documento. Regla general: no se aceptan duplicados en documentos.",

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

        elif k == "monto_pagado" and v is not None:

            es_valido, monto_val, err_msg = _validar_monto(v)

            if not es_valido:

                raise HTTPException(status_code=400, detail=err_msg)

            setattr(row, k, Decimal(str(round(monto_val, 2))))

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

    # Regla: si el pago cumple validadores (prestamo_id + monto), aplicar automáticamente a cuotas en cualquier canal

    if row.prestamo_id and float(row.monto_pagado or 0) > 0:

        try:

            cuotas_completadas, cuotas_parciales = _aplicar_pago_a_cuotas_interno(row, db)

            row.estado = _estado_pago_tras_aplicar_cascada(cuotas_completadas, cuotas_parciales)

            db.commit()

            db.refresh(row)

        except Exception as e:

            logger.warning("Al actualizar pago, no se pudo aplicar a cuotas: %s", e)

    return _pago_to_response(row)





@router.delete("/{pago_id:int}", status_code=204)

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

    Delega en app.services.cuota_estado (Caracas; VENCIDO dias 1-91; MORA desde dia 92).

    """

    return clasificar_estado_cuota(total_pagado, monto_cuota, fecha_vencimiento, _hoy_local())





def _marcar_prestamo_liquidado_si_corresponde(prestamo_id: int, db: Session) -> None:

    """Si todas las cuotas del prestamo estan pagadas, actualiza prestamo.estado a LIQUIDADO. No hace commit."""

    cuotas = db.execute(select(Cuota).where(Cuota.prestamo_id == prestamo_id)).scalars().all()

    if not cuotas:

        return

    pendientes = sum(1 for c in cuotas if (c.total_pagado or 0) < (float(c.monto) if c.monto else 0) - 0.01)

    if pendientes == 0:

        prestamo = db.execute(select(Prestamo).where(Prestamo.id == prestamo_id)).scalars().first()

        if prestamo and (prestamo.estado or "").upper() == "APROBADO":

            prestamo.estado = "LIQUIDADO"

            if prestamos_tiene_columna_fecha_liquidado(db):
                prestamo.fecha_liquidado = hoy_negocio()

            logger.info("Prestamo id=%s marcado como LIQUIDADO (todas las cuotas pagadas).", prestamo_id)





def _estado_pago_tras_aplicar_cascada(cuotas_completadas: int, cuotas_parciales: int) -> str:

    """

    Estado del pago según articulación real a cuotas.

    Solo PAGADO si hubo aplicación (al menos un registro en cuota_pagos).

    Evita marcar PAGADO sin cuota_pagos (inconsistencia y bloqueo del job en cascada).

    """

    if cuotas_completadas > 0 or cuotas_parciales > 0:

        return "PAGADO"

    return "PENDIENTE"





def _aplicar_pago_a_cuotas_interno(pago: Pago, db: Session) -> tuple[int, int]:

    """

    Aplica el monto del pago a cuotas del préstamo. Reglas de negocio.

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
                # Solo saldo pendiente: no exigir fecha_pago NULL. Si hay fecha_pago pero total_pagado < monto
                # (carga manual, migración o bug), excluir la cuota bloqueaba la cascada y los pagos quedaban sin aplicar.
                or_(Cuota.total_pagado.is_(None), Cuota.total_pagado < Cuota.monto - 0.01),
            )
            .order_by(Cuota.numero_cuota.asc())  # Cascada: primero las cuotas más antiguas (numero_cuota menor), luego las siguientes

        )

    ).scalars().all()

    cuotas_completadas = 0

    cuotas_parciales = 0

    orden_aplicacion = 0  # Secuencia de aplicación (de atrás hacia delante) en cuota_pagos

    

    for c in cuotas_pendientes:

        monto_cuota = float(c.monto) if c.monto is not None else 0

        total_pagado_actual = float(c.total_pagado or 0)

        monto_necesario = monto_cuota - total_pagado_actual

        if monto_restante <= 0 or monto_cuota <= 0:

            break

        dup = db.scalar(
            select(func.count())
            .select_from(CuotaPago)
            .where(CuotaPago.cuota_id == c.id, CuotaPago.pago_id == pago.id)
        )
        if dup and int(dup) > 0:
            logger.warning(
                "Aplicacion en cascada detenida: ya existe cuota_pagos para cuota_id=%s pago_id=%s. "
                "Use POST /prestamos/{id}/reaplicar-cascada-aplicacion (o .../reaplicar-fifo-aplicacion) para reconstruir.",
                c.id,
                pago.id,
            )
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

            if isinstance(fecha_venc, date) and fecha_venc > hoy:

                estado_nuevo = "PAGO_ADELANTADO"

            else:

                estado_nuevo = "PAGADO"

            if not _validar_transicion_estado_cuota(c.estado, estado_nuevo):  # [validar_transiciones]

                logger.warning(f"Transición de estado inválida en cuota {c.id}: {c.estado} â†’ {estado_nuevo}")

                c.estado = estado_nuevo  # Forzar transición igualmente (log informativo)

            else:

                c.estado = estado_nuevo

            c.dias_mora = 0  # [M5] Sin mora si está pagada

            cuotas_completadas += 1

        else:
            # Cuota aún abierta: limpiar fecha_pago residual para no bloquear futuras aplicaciones en cascada.
            c.fecha_pago = None

            estado_nuevo = _estado_cuota_por_cobertura(nuevo_total, monto_cuota, fecha_venc)

            if not _validar_transicion_estado_cuota(c.estado, estado_nuevo):  # [validar_transiciones]

                logger.warning(f"Transición de estado inválida en cuota {c.id}: {c.estado} â†’ {estado_nuevo}")

            c.estado = estado_nuevo

            c.dias_mora = _calcular_dias_mora(fecha_venc)  # [M5] Calcular mora

            cuotas_parciales += 1

        monto_restante -= a_aplicar

    _marcar_prestamo_liquidado_si_corresponde(prestamo_id, db)

    # Advertencia si no se aplicó nada pero el préstamo sí tiene cuotas (p. ej. cuotas creadas después del pago)

    if cuotas_completadas == 0 and cuotas_parciales == 0:

        num_cuotas = db.scalar(

            select(func.count()).select_from(Cuota).where(Cuota.prestamo_id == prestamo_id)

        ) or 0

        if num_cuotas > 0:

            logger.warning(

                "Pago id=%s (prestamo_id=%s): no se aplicó a ninguna cuota; el préstamo tiene %s cuotas. "

                "Puede deberse a que las cuotas se generaron después del pago; use aplicar-cuotas o generar cuotas (aplica pendientes automático).",

                pago.id, prestamo_id, num_cuotas,

            )

    return cuotas_completadas, cuotas_parciales





def aplicar_pagos_pendientes_prestamo(prestamo_id: int, db: Session) -> int:

    """

    Aplica a cuotas los pagos conciliados del préstamo que aún no tienen enlaces en cuota_pagos

    (p. ej. el pago se creó/concilió antes de que existieran las cuotas). No hace commit.

    Retorna el número de pagos a los que se les aplicó algo.

    """

    subq = select(CuotaPago.pago_id).where(CuotaPago.pago_id.isnot(None)).distinct()

    # Mismo criterio que get_cuotas_prestamo: conciliado O verificado_concordancia SI.

    rows = db.execute(
        select(Pago)
        .where(
            Pago.prestamo_id == prestamo_id,
            or_(
                Pago.conciliado.is_(True),
                func.coalesce(func.upper(func.trim(Pago.verificado_concordancia)), "") == "SI",
            ),
            Pago.monto_pagado > 0,
            ~Pago.id.in_(subq),
        )
        .order_by(Pago.fecha_pago.asc().nulls_last(), Pago.id.asc())
    ).scalars().all()

    n = 0

    for pago in rows:

        try:

            cc, cp = _aplicar_pago_a_cuotas_interno(pago, db)

            if cc > 0 or cp > 0:

                pago.estado = "PAGADO"

                n += 1

        except Exception as e:

            logger.warning(

                "aplicar_pagos_pendientes_prestamo prestamo_id=%s pago id=%s: %s",

                prestamo_id, pago.id, e,

            )

    return n





@router.post("/{pago_id:int}/aplicar-cuotas", response_model=dict)

def aplicar_pago_a_cuotas(pago_id: int, db: Session = Depends(get_db)):

    """

    Aplica el monto del pago a cuotas del prestamo (orden numero_cuota).

    pago.estado = PAGADO solo si hubo articulacion (cc o cp > 0); si no hubo cupo, PENDIENTE.

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

        pago.estado = _estado_pago_tras_aplicar_cascada(cuotas_completadas, cuotas_parciales)

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





# --- Cédulas permitidas para reportar en Bs (rapicredit-cobros / infopagos) ---
# Normalización canónica: app.services.cobros.cedula_reportar_bs_service


@router.get("/cedulas-reportar-bs", response_model=dict)

def get_cedulas_reportar_bs(db: Session = Depends(get_db)):

    """Devuelve el total de cédulas en la lista (quienes pueden reportar en Bs en cobros/infopagos)."""

    total = db.query(func.count(CedulaReportarBs.cedula)).scalar() or 0

    return {"total": total}





class AgregarCedulaReportarBsBody(BaseModel):

    cedula: str





@router.post("/cedulas-reportar-bs/agregar", response_model=dict)

def agregar_cedula_reportar_bs(

    payload: AgregarCedulaReportarBsBody,

    db: Session = Depends(get_db),

):

    """

    Agrega una cédula a la lista de quienes pueden reportar en Bs (nuevo cliente que paga en bolívares).

    Si ya existe, no duplica. La cédula se normaliza (V/E/J/G + dígitos).

    """

    cedula_norm = normalize_cedula_para_almacenar_lista_bs(payload.cedula)

    if not cedula_norm:

        raise HTTPException(

            status_code=400,

            detail="Cédula inválida. Use letra V, E, J o G seguida de 6 a 11 dígitos (ej: V12345678).",

        )

    claves_actuales = load_autorizados_bs_claves(db)

    if cedula_coincide_autorizados_bs(cedula_norm, claves_actuales):

        total = db.query(func.count(CedulaReportarBs.cedula)).scalar() or 0

        return {

            "agregada": False,

            "cedula": cedula_norm,

            "total": total,

            "mensaje": f"La cédula {cedula_norm} ya estaba en la lista.",

        }

    try:

        db.add(CedulaReportarBs(cedula=cedula_norm))

        db.commit()

        total = db.query(func.count(CedulaReportarBs.cedula)).scalar() or 0

        return {

            "agregada": True,

            "cedula": cedula_norm,

            "total": total,

            "mensaje": f"Cédula {cedula_norm} agregada. Ya puede reportar pagos en Bs en Cobros e Infopagos.",

        }

    except Exception as e:

        db.rollback()

        logger.exception("Error agregando cedula_reportar_bs: %s", e)

        raise HTTPException(status_code=500, detail="Error al agregar la cédula.") from e





@router.post("/cedulas-reportar-bs/upload", response_model=dict)

def upload_cedulas_reportar_bs(

    file: UploadFile = File(...),

    db: Session = Depends(get_db),

):

    """

    Carga un Excel con columna 'cedula'. Reemplaza la lista de cédulas que pueden reportar en Bs.

    Afecta a rapicredit-cobros e infopagos: solo esas cédulas verán habilitada la opción Bs.

    """

    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):

        raise HTTPException(status_code=400, detail="Debe subir un archivo Excel (.xlsx o .xls)")

    try:

        import openpyxl

    except ImportError:

        raise HTTPException(status_code=500, detail="Excel library not available")

    content = file.file.read()

    if len(content) < 50:

        raise HTTPException(status_code=400, detail="El archivo está vacío o no es un Excel válido.")

    try:

        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)

    except Exception as e:

        raise HTTPException(status_code=400, detail=f"No se pudo leer el Excel: {str(e)}") from e

    ws = wb.active

    if not ws:

        raise HTTPException(status_code=400, detail="El Excel no tiene hojas.")

    # Buscar columna "cedula" (primera fila)

    header = [ (c and str(c).strip().lower() if c is not None else "") for c in next(ws.iter_rows(min_row=1, max_row=1, values_only=True), []) ]

    col_cedula = None

    for i, h in enumerate(header):

        if h == "cedula":

            col_cedula = i

            break

    if col_cedula is None:

        raise HTTPException(status_code=400, detail="El Excel debe tener una columna llamada 'cedula'.")

    cedulas_unicas: set[str] = set()

    for row in ws.iter_rows(min_row=2, values_only=True):

        if not row or len(row) <= col_cedula:

            continue

        val = row[col_cedula]

        cedula_norm = normalize_cedula_para_almacenar_lista_bs(str(val).strip() if val is not None else "")

        if cedula_norm:

            cedulas_unicas.add(cedula_norm)

    wb.close()

    # Reemplazar tabla

    try:

        db.query(CedulaReportarBs).delete()

        for c in cedulas_unicas:

            db.add(CedulaReportarBs(cedula=c))

        db.commit()

    except Exception as e:

        db.rollback()

        logger.exception("Error guardando cedulas_reportar_bs: %s", e)

        raise HTTPException(status_code=500, detail="Error al guardar la lista de cédulas.") from e

    return {

        "total": len(cedulas_unicas),

        "mensaje": f"Se cargaron {len(cedulas_unicas)} cédula(s). Solo ellas pueden reportar pagos en Bs en RapiCredit Cobros e Infopagos.",

    }

# Compat: nombre historico
_estado_pago_tras_aplicar_fifo = _estado_pago_tras_aplicar_cascada
