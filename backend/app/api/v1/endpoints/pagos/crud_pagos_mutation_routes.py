"""Pagos: obtener, crear, actualizar."""
"""Pagos API: crud."""
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

@router.get("/{pago_id:int}", response_model=dict)

def obtener_pago(pago_id: int, db: Session = Depends(get_db)):

    """Obtiene un pago por ID desde la tabla pagos."""

    row = db.get(Pago, pago_id)

    if not row:

        raise HTTPException(status_code=404, detail="Pago no encontrado")

    return _pago_response_enriquecido(db, row)





@router.post("", response_model=dict, status_code=201)

def crear_pago(payload: PagoCreate, db: Session = Depends(get_db), current_user: UserResponse = Depends(get_current_user)):

    """Crea un pago. Clave única = comprobante + código opcional; 409 si ya existe o por huella funcional."""

    if payload.prestamo_id is None:

        raise HTTPException(status_code=400, detail="prestamo_id es obligatorio para crear pagos.")

    num_stored = compose_numero_documento_almacenado(
        payload.numero_documento,
        payload.codigo_documento,
    )

    if not num_stored:

        raise HTTPException(status_code=400, detail="numero_documento es obligatorio para crear pagos.")

    if numero_documento_ya_registrado(db, num_stored):

        raise HTTPException(

            status_code=409,

            detail=(

                "Conflicto numero_documento: ya existe un pago con la misma combinación "

                "comprobante + código (incluye misma referencia con distinto uso de mayúsculas). "

                "Use un código distinto en el campo «Código» o verifique duplicados."

            ),

        )

    ref = (num_stored or "N/A")[:_MAX_LEN_NUMERO_DOCUMENTO]

    ref_norm = _normalizar_ref_fingerprint(num_stored or ref)

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
        if prestamo and (prestamo.estado or "").strip().upper() == "DESISTIMIENTO":

            raise HTTPException(

                status_code=400,

                detail="El prestamo esta en desistimiento; no se registran pagos.",

            )


    try:
        cedula_fk_crear = asegurar_cedula_pago_para_fk(
            db,
            cedula_raw=cedula_normalizada or None,
            prestamo_id=payload.prestamo_id,
        )
    except CedulaPagoFkError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    cedula_normalizada = (cedula_fk_crear or "").strip().upper()

    # Validar monto (mismo criterio que carga Excel y guardar-fila-editable)

    monto_raw = payload.monto_pagado

    es_valido, monto_val, err_msg = _validar_monto(monto_raw)

    if not es_valido:

        raise HTTPException(status_code=400, detail=err_msg)



    try:

        monto_usd, moneda_fin, monto_bs_o, tasa_o, fecha_tasa_o = resolver_monto_registro_pago(

            db,

            cedula_normalizada=cedula_normalizada,

            fecha_pago=payload.fecha_pago,

            monto_pagado=Decimal(str(round(monto_val, 2))),

            moneda_registro=payload.moneda_registro or "USD",

            tasa_cambio_manual=payload.tasa_cambio_manual,

        )

        msg_huella = conflicto_huella_para_creacion(
            db,
            prestamo_id=payload.prestamo_id,
            fecha_pago=payload.fecha_pago,
            monto_pagado=monto_usd,
            numero_documento=num_stored,
            referencia_pago=ref,
        )
        if msg_huella:
            registrar_rechazo_huella_funcional()
            raise HTTPException(status_code=409, detail=msg_huella)

        row = Pago(

            cedula_cliente=cedula_fk_crear,

            prestamo_id=payload.prestamo_id,

            fecha_pago=fecha_pago_ts,

            monto_pagado=monto_usd,

            numero_documento=num_stored,

            institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,

            estado="PAGADO" if conciliado else "PENDIENTE",

            notas=payload.notas.strip() if payload.notas else None,

            referencia_pago=ref,

            ref_norm=ref_norm,

            conciliado=conciliado,  # [B2] Usar solo conciliado, no verificado_concordancia

            fecha_conciliacion=datetime.now(ZoneInfo(TZ_NEGOCIO)) if conciliado else None,

            verificado_concordancia="SI" if conciliado else "",  # Legacy: sync con conciliado

            usuario_registro=usuario_registro,  # [MEJORADO] Usuario real desde JWT

            moneda_registro=moneda_fin,

            monto_bs_original=monto_bs_o,

            tasa_cambio_bs_usd=tasa_o,

            fecha_tasa_referencia=fecha_tasa_o,

            link_comprobante=(payload.link_comprobante.strip() if payload.link_comprobante else None),

        )

        db.add(row)

        db.flush()

        db.refresh(row)

        # [C3] Aplicar cascada a cuotas en la misma transacción para que préstamos y estado de cuenta se actualicen

        if _debe_aplicar_cascada_pago(row):

            cc_n, cp_n = _aplicar_pago_a_cuotas_interno(row, db)

            row.estado = _estado_conciliacion_post_cascada(row, cc_n, cp_n)

        db.commit()

        db.refresh(row)

        return _pago_response_enriquecido(db, row)

    except HTTPException:

        raise

    except IntegrityError as e:

        db.rollback()

        # Unique violation (p. ej. numero_documento duplicado) ? 409

        if getattr(getattr(e, "orig", None), "pgcode", None) == "23505":

            constraint = getattr(getattr(getattr(e, "orig", None), "diag", None), "constraint_name", "") or ""

            if "ux_pagos_fingerprint_activos" in constraint:

                registrar_rechazo_huella_funcional()

                raise HTTPException(

                    status_code=409,

                    detail=HTTP_409_DETAIL_HUELLA_FUNCIONAL,

                )

            raise HTTPException(

                status_code=409,

                detail=(

                    "Violación de unicidad en base de datos (restricción distinta a la huella funcional). "

                    "Si el mensaje menciona numero_documento, ejecute en BD: "

                    "ALTER TABLE public.pagos DROP CONSTRAINT IF EXISTS uq_pagos_numero_documento;"

                ),

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

def actualizar_pago(
    pago_id: int,
    payload: PagoUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):

    """Actualiza un pago en la tabla pagos. Mismo texto de documento puede existir en otros pagos.

    Si el pago ya estaba articulado a cuotas (cuota_pagos) y cambian monto, fecha de pago o préstamo,
    se ejecuta la misma reconstrucción en cascada que POST .../prestamos/{id}/reaplicar-cascada-aplicacion
    sobre el o los préstamos afectados para que la amortización y servicios alineados vuelvan a cuadrar.
    """

    t0_put = time.perf_counter()
    _fase_prev = [t0_put]
    _fases_ms: dict[str, float] = {}

    def _mark_fase(nombre: str) -> None:
        now = time.perf_counter()
        _fases_ms[nombre] = round((now - _fase_prev[0]) * 1000.0, 2)
        _fase_prev[0] = now

    row = db.get(Pago, pago_id)

    if not row:

        raise HTTPException(status_code=404, detail="Pago no encontrado")

    had_cuota_pagos_antes = pago_tiene_aplicaciones_cuotas(db, pago_id)

    old_prestamo_id = row.prestamo_id

    old_monto_pagado = row.monto_pagado

    old_fecha_pago = row.fecha_pago

    data = payload.model_dump(exclude_unset=True)

    reescaneo_ocr = bool(data.pop("reescaneo_ocr", False))
    limpiar_numero_documento_ocr = bool(data.pop("limpiar_numero_documento_ocr", False))
    limpiar_fecha_pago_ocr = bool(data.pop("limpiar_fecha_pago_ocr", False))
    limpiar_monto_pago_ocr = bool(data.pop("limpiar_monto_pago_ocr", False))

    # fecha_pago y monto_pagado son NOT NULL en BD: no poner NULL ni 0 al limpiar OCR.
    if limpiar_monto_pago_ocr and reescaneo_ocr:
        row.monto_bs_original = None
        row.moneda_registro = "USD"
        row.tasa_cambio_bs_usd = None
        row.fecha_tasa_referencia = None

    def _referencia_pago_sintetica_ocr(valor: Optional[str]) -> bool:
        t = (valor or "").strip().upper()
        if not t:
            return False
        if t.startswith("ABONOS-DRIVE-"):
            return True
        if re.search(r"-\d{8}-\d{6}-DCME-", t, re.I):
            return True
        return False

    _doc_touch = False

    if limpiar_numero_documento_ocr and reescaneo_ocr:
        row.numero_documento = None
        if _referencia_pago_sintetica_ocr(row.referencia_pago):
            row.referencia_pago = ""

    if "numero_documento" in data:

        _doc_touch = True

    if "codigo_documento" in data:

        _doc_touch = True

    if _doc_touch:

        b0, c0 = split_numero_documento_almacenado(row.numero_documento)

        nb = (

            normalize_documento(data["numero_documento"])

            if "numero_documento" in data and data["numero_documento"] is not None

            else b0

        )

        if not nb:

            if reescaneo_ocr:
                row.numero_documento = None
            else:
                raise HTTPException(status_code=400, detail="numero_documento no puede estar vacio.")

        elif nb:

            if "codigo_documento" in data:

                nc = normalize_codigo_documento(data["codigo_documento"])

            else:

                nc = normalize_codigo_documento(c0) if c0 else None

            new_stored = compose_numero_documento_almacenado(nb, nc)

            codigo_anterior = normalize_codigo_documento(c0) if c0 else None

            codigo_cambio = (nc or "") != (codigo_anterior or "")

            if codigo_cambio and (
                bool(row.conciliado)
                or str(row.estado or "").upper() in ("PAGADO", "PAGO_ADELANTADO")
            ):
                if canonical_rol(getattr(current_user, "rol", None)) != "admin":
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "No se permite cambiar código en pagos conciliados o pagados. "
                            "Solo administración puede hacerlo."
                        ),
                    )

            if new_stored and numero_documento_ya_registrado(db, new_stored, exclude_pago_id=pago_id):

                raise HTTPException(

                    status_code=409,

                    detail="Ya existe otro pago con la misma combinación comprobante + código.",

                )

            row.numero_documento = new_stored
            if reescaneo_ocr:
                ref_prev = (row.referencia_pago or "").strip()
                if (
                    not ref_prev
                    or _referencia_pago_sintetica_ocr(ref_prev)
                    or ref_prev == (b0 or "").strip()
                ):
                    row.referencia_pago = (new_stored or "")[:100]

        data.pop("numero_documento", None)

        data.pop("codigo_documento", None)

    _mark_fase("validacion_documento")

    aplicar_conciliado = False

    _put_mon_keys = (
        "monto_pagado",
        "moneda_registro",
        "monto_bs_original",
        "tasa_cambio_manual",
        "fecha_pago",
    )

    monetario_up = {k: data.pop(k) for k in _put_mon_keys if k in data}

    for k, v in data.items():

        if k == "notas" and v is not None:

            setattr(row, k, v.strip() or None)

        elif k == "institucion_bancaria":
            if reescaneo_ocr:
                setattr(row, k, (str(v).strip() or None) if v is not None else None)
            elif v is not None:
                setattr(row, k, v.strip() or None)

        elif k == "cedula_cliente" and v is not None:

            setattr(row, k, v.strip())

        elif k == "conciliado" and v is not None:

            aplicar_conciliado = bool(v)

            if aplicar_conciliado:
                from app.services.pago_autoconciliacion import marcar_pago_autoconciliado

                marcar_pago_autoconciliado(row)
            else:
                row.conciliado = False
                row.fecha_conciliacion = None
                row.verificado_concordancia = "NO"
                _alinear_estado_si_toggle_conciliado_actualizar_pago(row, False)

        elif k == "verificado_concordancia" and v is not None:

            val = (v or "").strip().upper()

            row.verificado_concordancia = val if val in ("SI", "NO") else ("" if v == "" else str(v)[:10])

        else:

            setattr(row, k, v)

    _mark_fase("campos_basicos")

    if monetario_up:

        def _fp_row_a_date(fp):

            if fp is None:

                return None

            return fp.date() if hasattr(fp, "date") and callable(getattr(fp, "date", None)) else fp

        try:

            moneda_prev = normalizar_moneda_registro(row.moneda_registro or "USD")

        except HTTPException:

            moneda_prev = "USD"

        if "moneda_registro" in monetario_up:

            moneda_target = normalizar_moneda_registro(monetario_up["moneda_registro"])

        else:

            moneda_target = moneda_prev

        if moneda_target == "BS":

            fecha_eff = monetario_up.get("fecha_pago")

            if fecha_eff is None:

                fecha_eff = _fp_row_a_date(row.fecha_pago)

            if fecha_eff is None:

                raise HTTPException(

                    status_code=400,

                    detail="fecha_pago es requerida para pagos en bolivares.",

                )

            if "monto_bs_original" in monetario_up and monetario_up["monto_bs_original"] is not None:

                es_valido, monto_val, err_msg = _validar_monto(monetario_up["monto_bs_original"])

                if not es_valido:

                    raise HTTPException(status_code=400, detail=err_msg)

                monto_bs_input = Decimal(str(round(monto_val, 2)))

            elif "monto_pagado" in monetario_up:

                es_valido, monto_val, err_msg = _validar_monto(monetario_up["monto_pagado"])

                if not es_valido:

                    raise HTTPException(status_code=400, detail=err_msg)

                monto_bs_input = Decimal(str(round(monto_val, 2)))

            else:

                if row.monto_bs_original is not None:

                    monto_bs_input = Decimal(str(round(float(row.monto_bs_original), 2)))

                else:

                    raise HTTPException(

                        status_code=400,

                        detail="Indique el monto en bolivares; no hay monto Bs previo en este pago.",

                    )

            cedula_norm = (row.cedula_cliente or "").strip().upper()

            if cedula_norm:

                alinear_cedulas_clientes_existentes(db, [cedula_norm])

            tasa_manual_put = monetario_up.get("tasa_cambio_manual")

            monto_usd, moneda_fin, monto_bs_o, tasa_o, fecha_tasa_o = resolver_monto_registro_pago(

                db,

                cedula_normalizada=cedula_norm,

                fecha_pago=fecha_eff,

                monto_pagado=monto_bs_input,

                moneda_registro="BS",

                tasa_cambio_manual=tasa_manual_put,

            )

            row.monto_pagado = monto_usd

            row.moneda_registro = moneda_fin

            row.monto_bs_original = monto_bs_o

            row.tasa_cambio_bs_usd = tasa_o

            row.fecha_tasa_referencia = fecha_tasa_o

            if "fecha_pago" in monetario_up:

                fpv = monetario_up["fecha_pago"]

                row.fecha_pago = (

                    datetime.combine(fpv, dt_time.min)

                    if isinstance(fpv, date) and not isinstance(fpv, datetime)

                    else fpv

                )

        else:

            if "fecha_pago" in monetario_up:

                fpv = monetario_up["fecha_pago"]

                row.fecha_pago = (

                    datetime.combine(fpv, dt_time.min)

                    if isinstance(fpv, date) and not isinstance(fpv, datetime)

                    else fpv

                )

            if "monto_pagado" in monetario_up:

                es_valido, monto_val, err_msg = _validar_monto(monetario_up["monto_pagado"])

                if not es_valido:

                    raise HTTPException(status_code=400, detail=err_msg)

                row.monto_pagado = Decimal(str(round(monto_val, 2)))

            row.moneda_registro = "USD"

            row.monto_bs_original = None

            row.tasa_cambio_bs_usd = None

            row.fecha_tasa_referencia = None

    _mark_fase("normalizacion_monetaria")

    fp_row = row.fecha_pago

    if isinstance(fp_row, datetime):

        fecha_huella_up = fp_row.date()

    elif isinstance(fp_row, date):

        fecha_huella_up = fp_row

    else:

        fecha_huella_up = None

    rn_up = ref_norm_desde_campos(row.numero_documento, row.referencia_pago).strip()

    if row.prestamo_id and fecha_huella_up is not None and rn_up:

        cid_up = primer_id_conflicto_huella_funcional(
            db,
            prestamo_id=int(row.prestamo_id),
            fecha_pago=fecha_huella_up,
            monto_pagado=row.monto_pagado,
            ref_norm=rn_up,
            exclude_pago_id=pago_id,
        )
        if cid_up is not None:
            db.rollback()

            registrar_rechazo_huella_funcional()

            raise HTTPException(status_code=409, detail=mensaje_409_huella_funcional_con_id(cid_up))

    _mark_fase("huella_funcional")

    try:
        row.cedula_cliente = asegurar_cedula_pago_para_fk(
            db,
            cedula_raw=row.cedula_cliente,
            prestamo_id=row.prestamo_id,
        )
    except CedulaPagoFkError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e

    _mark_fase("cedula_fk")

    try:

        db.commit()

        db.refresh(row)
        _mark_fase("commit_base")

    except IntegrityError as e:

        db.rollback()

        pgcode, cname = _integridad_error_pgcode_y_constraint(e)

        if pgcode == "23505":

            if "ux_pagos_fingerprint_activos" in cname:

                registrar_rechazo_huella_funcional()

                raise HTTPException(status_code=409, detail=HTTP_409_DETAIL_HUELLA_FUNCIONAL)

            raise HTTPException(

                status_code=409,

                detail=(

                    "Violación de unicidad en base de datos. Si aplica a numero_documento, "

                    "ejecute: ALTER TABLE public.pagos DROP CONSTRAINT IF EXISTS uq_pagos_numero_documento;"

                ),

            )

        if pgcode == "23514":

            logger.warning(
                "actualizar_pago pago_id=%s: violacion CHECK (23514) constraint=%s detail=%s",
                pago_id,
                cname,
                str(e)[:400],
            )

            raise HTTPException(
                status_code=400,
                detail=(
                    "La base de datos rechazó la combinación estado/conciliación del pago "
                    f"(restricción: {cname or 'CHECK'}). "
                    "Pruebe de nuevo tras recargar; si quitó validación cartera, el estado debe pasar a Pendiente."
                ),
            )

        if pgcode == "23503" and "fk_pagos_cedula" in (cname or ""):

            raise HTTPException(
                status_code=400,
                detail=(
                    "La cédula del pago no coincide con ningún cliente en el sistema "
                    f"(restricción {cname}). "
                    "Recargue la página, verifique el crédito asociado o corrija el documento del cliente en CRM."
                ),
            )

        logger.warning(
            "actualizar_pago pago_id=%s IntegrityError pgcode=%s constraint=%s msg=%s",
            pago_id,
            pgcode,
            cname,
            str(e)[:500],
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "La base de datos rechazó la actualización del pago "
                f"(código SQL {pgcode or 'desconocido'}, restricción {cname or 'N/A'}). "
                "Revise estado, conciliación y documento; copie este mensaje si contacta soporte."
            ),
        )

    def _fecha_pago_a_date(fp):

        if fp is None:

            return None

        return fp.date() if hasattr(fp, "date") and callable(getattr(fp, "date", None)) else fp

    new_fd = _fecha_pago_a_date(row.fecha_pago)

    old_fd = _fecha_pago_a_date(old_fecha_pago)

    monto_changed = had_cuota_pagos_antes and abs(float(old_monto_pagado or 0) - float(row.monto_pagado or 0)) >= 0.01

    fecha_changed = had_cuota_pagos_antes and (old_fd != new_fd)

    prestamo_changed = had_cuota_pagos_antes and (old_prestamo_id != row.prestamo_id)

    articulacion_afectada = monto_changed or fecha_changed or prestamo_changed

    if articulacion_afectada:

        from app.services.pagos_cuotas_reaplicacion import reset_y_reaplicar_cascada_prestamo

        try:

            from app.services.pagos_aplicacion_prestamo import (
                _restaurar_autoconciliacion_pagos_prestamo,
            )

            for pid in sorted({p for p in (old_prestamo_id, row.prestamo_id) if p}):

                par_dup = primer_par_huella_duplicada_prestamo(db, int(pid))
                if par_dup is not None:
                    registrar_rechazo_huella_funcional()
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"{mensaje_409_huella_funcional_con_id(par_dup[0])} "
                            f"Duplicado con pagos.id={par_dup[1]}."
                        ),
                    )

                r = reset_y_reaplicar_cascada_prestamo(db, pid)

                if not r.get("ok"):
                    err_sync = str(r.get("error") or "error desconocido")
                    if r.get("codigo") == "huella_duplicada" or "huella funcional" in err_sync.lower():
                        registrar_rechazo_huella_funcional()
                        raise HTTPException(status_code=409, detail=err_sync)
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"No se pudo sincronizar la tabla de amortización del préstamo {pid}: "
                            f"{err_sync}."
                        ),
                    )

                _restaurar_autoconciliacion_pagos_prestamo(int(pid), db)

            if bool(row.conciliado) and row.prestamo_id and float(row.monto_pagado or 0) > 0:
                from app.services.pago_autoconciliacion import marcar_pago_autoconciliado

                marcar_pago_autoconciliado(row)

            db.commit()

            db.refresh(row)
            _mark_fase("reaplicacion_cascada")

        except HTTPException:

            db.rollback()

            raise

        except Exception as e:

            logger.exception(

                "actualizar_pago pago_id=%s: fallo reaplicar cascada tras cambio de articulacion",

                pago_id,

            )

            db.rollback()

            raise HTTPException(

                status_code=500,

                detail=f"Error al recalcular cuotas tras editar el pago: {str(e)[:280]}",

            ) from e

        _mark_fase("response_enriquecido")
        out = _pago_response_enriquecido(db, row)
        total_ms = round((time.perf_counter() - t0_put) * 1000.0, 2)
        logger.info(
            "[PAGOS_PUT_TIMING] pago_id=%s total_ms=%s fases_ms=%s had_cuota_pagos=%s articulacion_afectada=%s",
            pago_id,
            total_ms,
            _fases_ms,
            had_cuota_pagos_antes,
            articulacion_afectada,
        )
        return out

    # Regla: si el pago cumple validadores (prestamo_id + monto), aplicar automáticamente a cuotas en cualquier canal

    if row.prestamo_id and float(row.monto_pagado or 0) > 0:

        try:

            cuotas_completadas, cuotas_parciales = _aplicar_pago_a_cuotas_interno(row, db)

            # Misma regla que crear_pago: alinear estado y conciliado si no hubo abono en cuotas.
            row.estado = _estado_conciliacion_post_cascada(row, cuotas_completadas, cuotas_parciales)

            if bool(row.conciliado) and row.prestamo_id and float(row.monto_pagado or 0) > 0:
                from app.services.pago_autoconciliacion import marcar_pago_autoconciliado

                marcar_pago_autoconciliado(row)

            db.commit()

            db.refresh(row)
            _mark_fase("aplicar_cuotas_post_put")

        except IntegrityError as e:

            try:
                db.rollback()
            except Exception:
                logger.exception("Rollback tras IntegrityError cascada (actualizar_pago pago_id=%s)", pago_id)

            pg2, cn2 = _integridad_error_pgcode_y_constraint(e)

            logger.warning(
                "actualizar_pago pago_id=%s commit post-cascada IntegrityError pgcode=%s cname=%s %s",
                pago_id,
                pg2,
                cn2,
                str(e)[:400],
            )

            raise HTTPException(
                status_code=400,
                detail=(
                    "Integridad al guardar tras aplicar cuotas al pago "
                    f"(código {pg2 or '?'}, restricción {cn2 or 'N/A'}). "
                    "Revise montos y cuotas; use «Aplicar pagos a cuotas» por préstamo si corresponde."
                ),
            ) from e

        except Exception as e:

            logger.warning(
                "Al actualizar pago, no se pudo aplicar a cuotas: %s",
                e,
                exc_info=True,
            )
            try:
                db.rollback()
            except Exception:
                logger.exception("Rollback tras fallo aplicacion cuotas (actualizar_pago pago_id=%s)", pago_id)
            else:
                try:
                    db.refresh(row)
                except Exception:
                    logger.warning(
                        "No se pudo refrescar pago id=%s tras rollback de cascada; se responde con estado en memoria.",
                        pago_id,
                    )

    _mark_fase("response_enriquecido")
    out = _pago_response_enriquecido(db, row)
    total_ms = round((time.perf_counter() - t0_put) * 1000.0, 2)
    logger.info(
        "[PAGOS_PUT_TIMING] pago_id=%s total_ms=%s fases_ms=%s had_cuota_pagos=%s articulacion_afectada=%s",
        pago_id,
        total_ms,
        _fases_ms,
        had_cuota_pagos_antes,
        articulacion_afectada,
    )
    return out


