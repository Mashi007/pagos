"""Pagos API: upload_excel."""
"""

Endpoints de pagos. Datos reales desde BD.

- Tabla pagos: GET/POST/PUT/DELETE /pagos/ (listado y CRUD para /pagos/pagos).

- GET /pagos/kpis, /stats, /ultimos; POST /upload, /conciliacion/upload, /{id}/aplicar-cuotas.



Nº documento / referencia de pago:

- Regla de cartera: **no puede repetirse** el valor almacenado en `pagos.numero_documento` (único en `pagos` y
  `pagos_con_errores`, salvo edición del mismo `pago_id`).

- **Única forma permitida** de reutilizar el mismo texto de comprobante del banco: desambiguar con **código**
  (`codigo_documento`). En BD se compone `base + §CD: + código` (`compose_numero_documento_almacenado`,
  máx. 100 caracteres). En revisión manual en préstamos, el token **A#### / P####** lo asigna **Visto** (sufijo
  operativo; mismo criterio que carga masiva).

- Formatos de comprobante: BNC/, BINANCE, VE/, etc. Carga masiva: columna opcional a la derecha del Nº = código.

- Además, huella funcional (prestamo + fecha + monto + ref_norm) evita duplicar el mismo pago operativo (409),
  vía `ux_pagos_fingerprint_activos`.

"""

import calendar

import io

import logging

import re

import time

import uuid

from datetime import date, datetime, time as dt_time

from decimal import Decimal

from typing import Any, Optional

from zoneinfo import ZoneInfo



from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Body, Request

from fastapi.responses import StreamingResponse, Response

from pydantic import BaseModel, field_validator

from sqlalchemy import and_, case, delete, desc, exists, func, inspect, not_, or_, select, text

from sqlalchemy.orm import Session, aliased

from sqlalchemy.exc import IntegrityError, OperationalError



from app.core.database import get_db

from app.core.config import settings

from app.core.deps import (
    ComprobanteImagenReader,
    get_comprobante_imagen_reader,
    get_current_user,
    require_admin,
    require_operator_or_higher,
)
from app.core.rol_normalization import canonical_rol

from app.core.documento import (
    compose_numero_documento_almacenado,
    normalize_codigo_documento,
    normalize_documento,
    split_numero_documento_almacenado,
)
from app.utils.cedula_almacenamiento import (
    CedulaPagoFkError,
    asegurar_cedula_pago_para_fk,
    alinear_cedulas_clientes_existentes,
    normalizar_cedula_almacenamiento,
)
from app.services.pago_numero_documento import (
    numero_documento_ya_registrado,
    primer_pago_cartera_por_documento,
)

from app.core.serializers import to_float, format_date_iso

from app.models.cliente import Cliente

from app.models.cuota import Cuota

from app.models.prestamo import Prestamo

from app.models.pago import Pago

from app.models.pago_comprobante_imagen import PagoComprobanteImagen

from app.models.pago_con_error import PagoConError

from app.models.revisar_pago import RevisarPago

from app.models.cuota_pago import CuotaPago

from app.models.pago_reportado import PagoReportado

from app.models.datos_importados_conerrores import DatosImportadosConErrores

from app.models.cedula_reportar_bs import CedulaReportarBs

from app.schemas.pago import (
    PagoCreate,
    PagoUpdate,
    PagoResponse,
    normalizar_link_comprobante,
)

from app.schemas.auth import UserResponse

from app.services.cobros.pago_reportado_documento import (
    claves_documento_pago_desde_campos,
    claves_documento_pago_para_reportado,
    claves_documento_para_lote_reportados,
    documento_numero_desde_pago_reportado,
    pago_reportado_colisiona_tabla_pagos,
)
from app.services.pagos.comprobante_link_desde_gmail import (
    enriquecer_items_link_comprobante_desde_gmail,
    enriquecer_items_link_comprobante_desde_pago_reportado,
)
from app.services.pagos.comprobante_imagen_finiquito_access import (
    comprobante_imagen_accesible_finiquito_portal,
)
from app.services.cuota_pago_integridad import (
    pago_tiene_aplicaciones_cuotas,
    validar_suma_aplicada_vs_monto_pago,
)
from app.services.pagos_cuotas_reaplicacion import (
    prestamo_requiere_correccion_cascada,
    reset_y_reaplicar_cascada_prestamo,
)
from app.services.pagos_cascada_aplicacion import (
    _aplicar_pago_a_cuotas_interno,
    _marcar_prestamo_liquidado_si_corresponde,
)
from app.services.pagos_aplicacion_prestamo import (
    aplicar_pagos_pendientes_prestamo,
    aplicar_pagos_pendientes_prestamo_con_diagnostico,
)
from app.services.pagos_cascada_mensajes import _mensaje_sin_aplicacion_cascada


from app.services.tasa_cambio_service import (
    convertir_bs_a_usd,
    normalizar_fuente_tasa,
    obtener_tasa_por_fecha,
    valor_tasa_para_fuente,
)

from app.services.pago_registro_moneda import (
    normalizar_moneda_registro,
    resolver_monto_registro_pago,
    preload_autorizados_bs,
)
from app.services.pago_huella_funcional import (
    conflicto_huella_para_creacion,
    contar_prestamos_con_huella_funcional_duplicada,
    HTTP_409_DETAIL_HUELLA_FUNCIONAL,
    mensaje_409_huella_funcional_con_id,
    primer_id_conflicto_huella_funcional,
    primer_par_huella_duplicada_prestamo,
    ref_norm_desde_campos,
)
from app.services.pago_huella_metricas import (
    registrar_rechazo_huella_funcional,
    snapshot_rechazos_huella_funcional,
)

from app.services.cobros.cedula_reportar_bs_service import (

    normalize_cedula_para_almacenar_lista_bs,

    normalize_cedula_lookup_key,

    load_autorizados_bs_claves,

    cedula_coincide_autorizados_bs,

    cedula_autorizada_para_bs,

    obtener_fuente_tasa_lista_bs,

    fuente_tasa_bs_efectiva_para_cedula,

)

from app.services.tasa_cambio_service import normalizar_fuente_tasa

from .payload_models import (
    AgregarCedulaReportarBsBody,
    ConsultarCedulasReportarBsBatchBody,
    GuardarFilaEditableBody,
    MoverRevisarPagosBody,
    PagoBatchBody,
    ValidarFilasBatchBody,
)
from app.services.cobros.cobros_publico_reporte_service import (
    mime_efectivo_comprobante_web,
    mime_efectivo_con_firma_archivo,
    preparar_adjunto_comprobante_para_vision,
    validate_file_magic,
)

from .comprobante_imagen_helpers import (
    _COMPROBANTE_IMG_CT,
    _MAX_COMPROBANTE_IMAGEN_BYTES,
    _normalizar_id_comprobante_imagen,
    _public_base_url_para_comprobante,
)
from app.services.pagos_gmail.comprobante_bd import url_comprobante_imagen_absoluta

from .constants import (
    TZ_NEGOCIO,
    _MAX_LEN_NUMERO_DOCUMENTO,
    _MAX_MONTO_PAGADO,
    _MIN_MONTO_PAGADO,
    _PRESTAMO_ID_MAX,
)
from .cascada_estado import _estado_pago_tras_aplicar_cascada
from .sql_where_pagos import (
    _where_pago_elegible_reaplicacion_cascada,
    _where_pago_excluido_operacion,
)
from .pago_integridad_db import _integridad_error_pgcode_y_constraint
from .pago_normalizacion import (
    _celda_a_string_documento,
    _normalizar_ref_fingerprint,
    _safe_float,
    _validar_monto,
)
from .pago_zona_horaria import _calcular_dias_mora, _hoy_local
from .pago_usuario_registro import _usuario_registro_desde_current_user
from .pago_conciliacion_estado import (
    _alinear_estado_si_toggle_conciliado_actualizar_pago,
    _estado_conciliacion_post_cascada,
)
from .pago_cascada_reglas import _debe_aplicar_cascada_pago
from .pago_serializacion_respuesta import (
    _enriquecer_items_duplicado_clave_misma_pagina,
    _enriquecer_items_tiene_aplicacion_cuotas,
    _enriquecer_pagos_pago_reportado_id,
    _pago_response_enriquecido,
    _pago_to_response,
)









logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.post("/upload", response_model=dict)

async def upload_excel_pagos(

    file: UploadFile = File(..., alias="file"),

    db: Session = Depends(get_db),

    current_user: UserResponse = Depends(get_current_user),

):

    """

    Carga masiva de pagos desde Excel (subir y procesar todo en el servidor).

    Formatos de columnas soportados (primera fila = cabecera; datos desde fila 2):

    - Formato D (principal): Cédula | Monto | Fecha | Nº documento [| Código opcional]

    - Formato E: Banco | Cédula | Fecha | Monto | Nº documento [| Código opcional]

    - Formato A: Documento | Cédula | Fecha | Monto [| Código opcional]

    - Formato B: Fecha | Cédula | Monto | Documento [| Código opcional]

    - Formato C: Cédula | ID Préstamo | Fecha | Monto | Nº documento [| Código opcional]

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



        def _celda_parece_banco_excel(v: Any) -> bool:

            """Primera columna tipo nombre de banco (p. ej. BINANCE, BNC), no cédula ni fecha ni referencia larga."""

            if v is None:

                return False

            s = str(v).strip()

            if not s or len(s) > 80:

                return False

            if _looks_like_date(v):

                return False

            if _looks_like_cedula(v):

                return False

            if re.search(r"\d{10,}", s):

                return False

            if len(s) > 28 and re.search(r"\d{4,}", s):

                return False

            return True



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

                codigo_doc_raw = ""

                institucion_bancaria: Optional[str] = None

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

                    if len(row) > 4 and row[4] is not None:

                        codigo_doc_raw = str(row[4]).strip()

                # Formato E: Banco, Cédula, Fecha, Monto [, Nº documento]

                elif (
                    len(row) >= 4
                    and _celda_parece_banco_excel(row[0])
                    and _looks_like_cedula(row[1])
                    and _looks_like_date(row[2])
                ):

                    _banco_raw = str(row[0]).strip()[:255]

                    institucion_bancaria = _banco_raw or None

                    cedula = str(row[1]).strip()

                    fecha_val = row[2]

                    es_valido, monto, err_msg = _validar_monto(row[3])



                    if not es_valido and monto != 0.0:

                        errores.append(f'Fila {i + 2} (Formato E - Banco): {err_msg}')

                        pagos_con_error_list.append({

                            "fila_idx": i + 2,

                            "cedula": cedula,

                            "prestamo_id": None,

                            "fecha_val": fecha_val,

                            "monto": monto,

                            "numero_doc": "",

                            "errores": [err_msg],

                            "institucion_bancaria": institucion_bancaria,

                        })

                        continue

                    numero_doc = _celda_a_string_documento(row[4]) if len(row) > 4 else ""

                    col_doc = 4 if len(row) > 4 else None

                    prestamo_id = None

                    if len(row) > 5 and row[5] is not None:

                        codigo_doc_raw = str(row[5]).strip()

                # Formato A: Documento, Cédula, Fecha, Monto

                elif len(row) >= 4 and _looks_like_documento(row[0]) and _looks_like_cedula(row[1]):

                    numero_doc = _celda_a_string_documento(row[0])

                    col_doc = 0

                    if len(row) > 4 and row[4] is not None:

                        codigo_doc_raw = str(row[4]).strip()

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

                    if len(row) > 4 and row[4] is not None:

                        codigo_doc_raw = str(row[4]).strip()

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

                    if len(row) > 5 and row[5] is not None:

                        codigo_doc_raw = str(row[5]).strip()

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

                    "codigo_doc_raw": (codigo_doc_raw or "").strip(),

                    "institucion_bancaria": institucion_bancaria,

                })

            except Exception as e:

                errores.append(f"Fila {i + 2}: {e}")

                errores_detalle.append({"fila": i + 2, "cedula": "", "error": str(e), "datos": {}})



        # --- FASE 2: Insertar (documento+código único en BD; huella funcional por fila y lote) ---

        compuestos_archivo: set[str] = set()

        for _it in FilasParseadas:

            _c = compose_numero_documento_almacenado(

                _it.get("numero_doc_raw"),

                _it.get("codigo_doc_raw"),

            )

            if _c:

                compuestos_archivo.add(_c)

        documentos_ya_en_bd_excel: set[str] = set()

        if compuestos_archivo:

            _lista_c = list(compuestos_archivo)

            _chunk = 1000

            for _i0 in range(0, len(_lista_c), _chunk):

                _ch = _lista_c[_i0 : _i0 + _chunk]

                _ex = db.execute(select(Pago.numero_documento).where(Pago.numero_documento.in_(_ch))).scalars().all()

                documentos_ya_en_bd_excel.update(str(d) for d in _ex if d)

                _ex_pe = db.execute(
                    select(PagoConError.numero_documento).where(
                        PagoConError.numero_documento.in_(_ch)
                    )
                ).scalars().all()

                documentos_ya_en_bd_excel.update(str(d) for d in _ex_pe if d)

        numeros_doc_en_lote_excel: set[str] = set()

        registros = 0

        pagos_con_prestamo: list[Pago] = []

        huellas_lote_excel: set[tuple[int, str, str, str]] = set()

        for item in FilasParseadas:

            i = item["fila_idx"]

            cedula = item["cedula"]

            prestamo_id = item["prestamo_id"]

            fecha_val = item["fecha_val"]

            monto = item["monto"]

            numero_doc = item["numero_doc_raw"]

            ib_carga = item.get("institucion_bancaria")

            if isinstance(ib_carga, str):

                ib_carga = ib_carga.strip()[:255] or None

            else:

                ib_carga = None



            numero_doc_norm = compose_numero_documento_almacenado(

                numero_doc,

                item.get("codigo_doc_raw"),

            )

            if numero_doc_norm and numero_doc_norm in numeros_doc_en_lote_excel:

                err_msg = (

                    "Misma combinación comprobante + código repetida en este archivo. "

                    "Use códigos distintos o una sola fila por clave."

                )

                errores.append(f"Fila {i}: {err_msg}")

                errores_detalle.append(

                    {

                        "fila": i,

                        "cedula": cedula,

                        "error": err_msg,

                        "datos": {

                            "cedula": cedula,

                            "prestamo_id": prestamo_id,

                            "fecha_pago": fecha_val,

                            "monto_pagado": monto,

                            "numero_documento": numero_doc or "",

                        },

                    }

                )

                pagos_con_error_list.append(

                    {

                        "fila_idx": i,

                        "cedula": cedula or "",

                        "prestamo_id": prestamo_id,

                        "fecha_val": fecha_val,

                        "monto": monto,

                        "numero_doc": numero_doc or "",

                        "errores": [err_msg],

                    }

                )

                continue

            if numero_doc_norm and numero_doc_norm in documentos_ya_en_bd_excel:

                err_msg = "Ya existe un pago con la misma combinación comprobante + código."

                errores.append(f"Fila {i}: {err_msg}")

                errores_detalle.append(

                    {

                        "fila": i,

                        "cedula": cedula,

                        "error": err_msg,

                        "datos": {

                            "cedula": cedula,

                            "prestamo_id": prestamo_id,

                            "fecha_pago": fecha_val,

                            "monto_pagado": monto,

                            "numero_documento": numero_doc or "",

                        },

                    }

                )

                pagos_con_error_list.append(

                    {

                        "fila_idx": i,

                        "cedula": cedula or "",

                        "prestamo_id": prestamo_id,

                        "fecha_val": fecha_val,

                        "monto": monto,

                        "numero_doc": numero_doc or "",

                        "errores": [err_msg],

                    }

                )

                continue

            if numero_doc_norm:

                numeros_doc_en_lote_excel.add(numero_doc_norm)

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

                if prestamo_id:
                    msg_h_excel = conflicto_huella_para_creacion(
                        db,
                        prestamo_id=prestamo_id,
                        fecha_pago=fecha_pago,
                        monto_pagado=monto,
                        numero_documento=numero_doc_norm,
                        referencia_pago=ref_pago,
                        huellas_en_mismo_lote=huellas_lote_excel,
                    )
                    if msg_h_excel:
                        registrar_rechazo_huella_funcional()
                        err_msg = msg_h_excel
                        errores.append(f"Fila {i}: {err_msg}")
                        errores_detalle.append(
                            {
                                "fila": i,
                                "cedula": cedula,
                                "error": err_msg,
                                "datos": {
                                    "cedula": cedula,
                                    "prestamo_id": prestamo_id,
                                    "fecha_pago": fecha_val,
                                    "monto_pagado": monto,
                                    "numero_documento": numero_doc or "",
                                },
                            }
                        )
                        pagos_con_error_list.append(
                            {
                                "fila_idx": i,
                                "cedula": cedula or "",
                                "prestamo_id": prestamo_id,
                                "fecha_val": fecha_val,
                                "monto": monto,
                                "numero_doc": numero_doc or "",
                                "errores": [err_msg],
                            }
                        )
                        continue

                # Autoconciliar: pagos creados por carga Excel se marcan conciliados (aplicados a cuotas después)

                ahora_up = datetime.now(ZoneInfo(TZ_NEGOCIO))

                p = Pago(

                    cedula_cliente=cedula.strip().upper() if cedula else "",

                    prestamo_id=prestamo_id,

                    fecha_pago=datetime.combine(fecha_pago, dt_time.min),

                    monto_pagado=monto,

                    numero_documento=numero_doc_norm,

                    institucion_bancaria=ib_carga,

                    estado="PAGADO",

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

                    institucion_bancaria=(

                        None

                        if pce_data.get("institucion_bancaria") in (None, "")

                        else str(pce_data.get("institucion_bancaria")).strip()[:255] or None

                    ),

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

    huellas_funcional_lote: Optional[set[tuple[int, str, str, str]]] = None,

) -> dict:

    """

    Crea un Pago desde un PagoReportado con las mismas validaciones que importar-desde-cobros.

    El Nº documento del pago toma `numero_operacion` del reporte cuando viene informado;
    si no, `referencia_interna` (RPC-…), para alinear duplicados con el comprobante real.

    No hace commit ni aplica a cuotas (el lote o el caller aplican después).

    Retorna {"ok": True, "pago": Pago} o {"ok": False, "error": str, "referencia": ..., "pce_id": int|None}.

    """

    ref_display = (pr.referencia_interna or "").strip()[:100] or None

    conciliado_reportado = True



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

            numero_documento=(documento_numero_desde_pago_reportado(pr)[0] or pr.referencia_interna or "")[:100],

            estado="PAGADO" if conciliado_reportado else "PENDIENTE",

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



    numero_doc_raw, numero_doc_norm = documento_numero_desde_pago_reportado(pr)

    claves_pr = claves_documento_pago_para_reportado(pr)

    if claves_pr:

        if pago_reportado_colisiona_tabla_pagos(db, pr):

            return _err_con_pce(

                "Ya existe un pago con este comprobante en la tabla pagos",

                cedula_cliente=cedula_raw,

            )

        if any(k in documentos_ya_en_bd for k in claves_pr):

            return _err_con_pce(

                "Ya existe un pago enlazado a este comprobante o referencia (duplicado en BD)",

                cedula_cliente=cedula_raw,

            )

        if any(k in docs_en_lote for k in claves_pr):

            return _err_con_pce(

                "Duplicado en este lote: mismo comprobante o referencia que otra fila",

                cedula_cliente=cedula_raw,

            )



    cliente = db.execute(

        select(Cliente).where(func.replace(Cliente.cedula, "-", "") == cedula_raw)

    ).scalars().first()

    if not cliente:

        return _err_con_pce("Cédula no encontrada en clientes", cedula_cliente=cedula_raw)



    from app.services.cobros.cobros_publico_reporte_service import (
        error_si_no_puede_reportar_en_web,
        prestamos_aprobados_del_cliente,
    )

    prestamo_ids = prestamos_aprobados_del_cliente(db, cliente.id)
    err_pres = error_si_no_puede_reportar_en_web(prestamo_ids)
    if err_pres:
        return _err_con_pce(err_pres, cedula_cliente=cedula_raw)

    prestamo_sel = db.get(Prestamo, int(prestamo_ids[0]))
    if prestamo_sel is None:
        return _err_con_pce("Crédito operativo no encontrado", cedula_cliente=cedula_raw)

    prestamo_id = prestamo_sel.id
    cedula_prestamo = (
        (getattr(prestamo_sel, "cedula", "") or "")
        .replace("-", "")
        .strip()
        .upper()
    )
    if cedula_prestamo and cedula_prestamo != cedula_raw:
        return _err_con_pce(
            "La cédula del reporte no coincide con la cédula del préstamo objetivo.",
            cedula_cliente=cedula_raw,
            prestamo_id=prestamo_id,
        )

    if getattr(prestamo_sel, "cliente_id", None) != getattr(cliente, "id", None):
        return _err_con_pce(
            "El préstamo objetivo no pertenece al cliente de la cédula reportada.",
            cedula_cliente=cedula_raw,
            prestamo_id=prestamo_id,
        )

    moneda_pr = (getattr(pr, "moneda", None) or "USD").strip().upper()

    if moneda_pr == "USDT":

        moneda_pr = "USD"

    monto = float(pr.monto or 0)

    monto_bs_original = None

    tasa_aplicada = None

    fecha_tasa_ref = None

    if moneda_pr == "BS":

        if not cedula_autorizada_para_bs(db, cedula_raw):

            return _err_con_pce(

                "Cedula no autorizada para pagos en bolivares",

                cedula_cliente=cedula_raw,

                prestamo_id=prestamo_id,

            )

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

        fuente = fuente_tasa_bs_efectiva_para_cedula(
            db,
            cedula_raw.replace("-", "").replace(" ", ""),
            fuente_almacenada=getattr(pr, "fuente_tasa_cambio", None),
        )
        if not fuente:
            return _err_con_pce(
                "No hay tasa de cambio configurada para esta cédula en bolívares",
                cedula_cliente=cedula_raw,
                prestamo_id=prestamo_id,
            )
        tasa_res = valor_tasa_para_fuente(tasa_obj, fuente)
        if tasa_res is None or float(tasa_res) <= 0:
            return _err_con_pce(
                f"No hay tasa {fuente.upper()} para la fecha de pago {pr.fecha_pago.isoformat()}; "
                "no se puede importar en bolívares",
                cedula_cliente=cedula_raw,
                prestamo_id=prestamo_id,
            )
        tasa_aplicada = float(tasa_res)

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

    fecha_huella_cobros = (
        pr.fecha_pago
        if pr.fecha_pago is not None
        else datetime.now(ZoneInfo(TZ_NEGOCIO)).date()
    )

    monto_dec_cobros = Decimal(str(round(monto, 2)))

    msg_h_cobros = conflicto_huella_para_creacion(
        db,
        prestamo_id=prestamo_id,
        fecha_pago=fecha_huella_cobros,
        monto_pagado=monto_dec_cobros,
        numero_documento=numero_doc_norm,
        referencia_pago=ref_pago,
        huellas_en_mismo_lote=huellas_funcional_lote,
    )

    if msg_h_cobros:
        registrar_rechazo_huella_funcional()
        return _err_con_pce(msg_h_cobros, cedula_cliente=cedula_raw, prestamo_id=prestamo_id)

    rpc_tr = (pr.referencia_interna or "").strip()[:100]
    notas_pago = None
    if rpc_tr and numero_doc_raw and rpc_tr != numero_doc_raw:
        notas_pago = f"Ref. interna reporte: {rpc_tr}"

    img_id = (getattr(pr, "comprobante_imagen_id", None) or "").strip()
    link_comp = url_comprobante_imagen_absoluta(img_id) if img_id else None
    doc_nom = ((pr.comprobante_nombre or "").strip()[:255] or None) if img_id else None

    p = Pago(

        cedula_cliente=cedula_raw,

        prestamo_id=prestamo_id,

        fecha_pago=datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now(),

        monto_pagado=monto_dec_cobros,

        numero_documento=numero_doc_norm,

        # Evita violar chk_pagos_conciliado_pendiente_inconsistente
        estado="PAGADO",

        referencia_pago=ref_pago,

        notas=notas_pago,

        usuario_registro=usuario_email,

        conciliado=True,

        fecha_conciliacion=ahora_imp,

        verificado_concordancia="SI",

        moneda_registro=moneda_pr,

        monto_bs_original=Decimal(str(round(monto_bs_original, 2))) if monto_bs_original is not None else None,

        tasa_cambio_bs_usd=Decimal(str(tasa_aplicada)) if tasa_aplicada is not None else None,

        fecha_tasa_referencia=fecha_tasa_ref,

        link_comprobante=link_comp,

        documento_nombre=doc_nom,

    )

    db.add(p)

    db.flush()

    for _k in claves_pr:

        if _k:

            docs_en_lote.add(_k)

            documentos_ya_en_bd.add(_k)

    return {"ok": True, "pago": p, "referencia": ref_display, "pce_id": None}







ORIGEN_COBROS_REPORTADOS = "Cobros (reportados aprobados)"





