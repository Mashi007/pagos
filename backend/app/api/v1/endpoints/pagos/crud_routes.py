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





@router.post("/batch", response_model=dict)

def crear_pagos_batch(

    body: PagoBatchBody,

    db: Session = Depends(get_db),

    current_user: UserResponse = Depends(get_current_user),

):

    """

    Crea varios pagos en una sola petición (máx. 500).

    Devuelve éxitos y errores por índice para reducir rondas y timeouts en "Guardar todos".

    Optimizado: precarga de préstamos y clientes en lugar de N consultas por fila.

    Mismo comprobante puede repetirse con codigo_documento distinto; duplicado = mismo valor almacenado.

    """

    try:

        usuario_registro = _usuario_registro_desde_current_user(current_user)

        pagos_list = body.pagos

        docs_compuestos = [

            compose_numero_documento_almacenado(p.numero_documento, getattr(p, "codigo_documento", None))

            for p in pagos_list

        ]

        docs_no_vacios = [d for d in docs_compuestos if d]

        existing_docs: set[str] = set()

        if docs_no_vacios:

            rows_bd = db.execute(select(Pago.numero_documento).where(Pago.numero_documento.in_(docs_no_vacios))).scalars().all()

            existing_docs = {r for r in rows_bd if r}

            rows_pe = db.execute(

                select(PagoConError.numero_documento).where(PagoConError.numero_documento.in_(docs_no_vacios))

            ).scalars().all()

            existing_docs.update({r for r in rows_pe if r})

        cedulas_payload = list(

            {

                (p.cedula_cliente or "").strip().replace("-", "").upper()

                for p in pagos_list

                if (p.cedula_cliente or "").strip()

            }

        )

        # Preload: ids de préstamos válidos (una sola consulta)

        prestamo_ids = [p.prestamo_id for p in pagos_list if p.prestamo_id]

        pc_prest = func.upper(func.replace(Prestamo.cedula, "-", ""))

        prestamos_activos_por_cedula: dict[str, list[int]] = {}

        if cedulas_payload:

            rows_act = db.execute(

                select(Prestamo.id, pc_prest)

                .where(pc_prest.in_(cedulas_payload))

                .where(Prestamo.estado.in_(("APROBADO", "DESEMBOLSADO")))

            ).all()

            for pid, ccell in rows_act:

                if pid is None:

                    continue

                ck = (str(ccell) if ccell is not None else "").strip().replace("-", "").upper()

                if ck:

                    prestamos_activos_por_cedula.setdefault(ck, []).append(int(pid))

            for _ck in prestamos_activos_por_cedula:

                prestamos_activos_por_cedula[_ck] = sorted(set(prestamos_activos_por_cedula[_ck]))

        all_pids_batch: set[int] = set(int(x) for x in prestamo_ids if x is not None)

        for _ids in prestamos_activos_por_cedula.values():

            all_pids_batch.update(_ids)

        valid_prestamo_ids: set[int] = set()

        if all_pids_batch:

            ids_rows = db.execute(select(Prestamo.id).where(Prestamo.id.in_(all_pids_batch))).scalars().all()

            valid_prestamo_ids = {int(r) for r in ids_rows if r is not None}

        prestamo_estado_por_id: dict[int, str] = {}

        if all_pids_batch:

            er_rows = db.execute(select(Prestamo.id, Prestamo.estado).where(Prestamo.id.in_(all_pids_batch))).all()

            prestamo_estado_por_id = {int(r[0]): (r[1] or "") for r in er_rows if r[0] is not None}


        # Preload: cédulas que tienen al menos un préstamo (normalizadas)

        valid_cedulas_prestamo: set[str] = set()

        if cedulas_payload:

            pc = func.upper(func.replace(Prestamo.cedula, "-", ""))

            ced_rows = db.execute(select(pc).where(pc.in_(cedulas_payload)).distinct()).scalars().all()

            valid_cedulas_prestamo = {(r or "").strip().replace("-", "").upper() for r in ced_rows if r}

        todas_cedulas_upper = list(

            {

                (p.cedula_cliente or "").strip().upper()

                for p in pagos_list

                if (p.cedula_cliente or "").strip()

            }

        )

        valid_cedulas: set[str] = set()

        if todas_cedulas_upper:

            ced_rows_c = db.execute(

                select(Cliente.cedula).where(func.upper(Cliente.cedula).in_(todas_cedulas_upper))

            ).scalars().all()

            valid_cedulas = {(r or "").strip().upper() for r in ced_rows_c if r}

        # Fase 1: validacion (sin insertar). Errores por indice; las filas validas se insertan en fase 2.

        errors_by_index: dict[int, dict] = {}

        resolved_prestamo_id_by_index: dict[int, int] = {}

        docs_added_in_batch: set[str] = set()

        for idx, payload in enumerate(pagos_list):

            num_doc = (

                docs_compuestos[idx]

                if idx < len(docs_compuestos)

                else compose_numero_documento_almacenado(

                    payload.numero_documento,

                    getattr(payload, "codigo_documento", None),

                )

            )

            if num_doc and (num_doc in existing_docs or num_doc in docs_added_in_batch):

                errors_by_index[idx] = {

                    "error": "Ya existe un pago con la misma combinación comprobante + código.",

                    "status_code": 409,

                }

                continue

            cedula_normalizada = (payload.cedula_cliente or "").strip().upper()

            ced_norm_prest = (payload.cedula_cliente or "").strip().replace("-", "").upper()

            if ced_norm_prest and ced_norm_prest not in valid_cedulas_prestamo:

                errors_by_index[idx] = {

                        "error": f"La cédula no tiene préstamo registrado: {cedula_normalizada}",

                        "status_code": 400,

                    }

                continue

            activos_ced = prestamos_activos_por_cedula.get(ced_norm_prest, [])

            effective_prestamo_id: Optional[int] = None

            raw_pid = getattr(payload, "prestamo_id", None)

            if raw_pid is not None and int(raw_pid) > 0:

                effective_prestamo_id = int(raw_pid)

            elif len(activos_ced) == 1:

                effective_prestamo_id = activos_ced[0]

            elif len(activos_ced) == 0:

                errors_by_index[idx] = {

                    "error": (

                        f"Sin credito activo (APROBADO/DESEMBOLSADO) para {cedula_normalizada}; "

                        "indique prestamo_id o asocie un credito."

                    ),

                    "status_code": 400,

                }

                continue

            else:

                errors_by_index[idx] = {

                    "error": (

                        f"La cedula {cedula_normalizada} tiene varios creditos activos; "

                        "elija prestamo_id en la columna Credito (obligatorio en lote)."

                    ),

                    "status_code": 400,

                }

                continue

            if effective_prestamo_id not in valid_prestamo_ids:

                errors_by_index[idx] = {"error": f"Credito #{effective_prestamo_id} no existe.", "status_code": 400}

                continue

            if (prestamo_estado_por_id.get(effective_prestamo_id) or "").strip().upper() == "DESISTIMIENTO":

                errors_by_index[idx] = {

                    "error": "El prestamo esta en desistimiento; no se registran pagos.",

                    "status_code": 400,

                }

                continue

            if cedula_normalizada and cedula_normalizada not in valid_cedulas:

                errors_by_index[idx] = {"error": f"No existe cliente con cedula {cedula_normalizada}", "status_code": 404}

                continue

            resolved_prestamo_id_by_index[idx] = effective_prestamo_id

            if num_doc:

                docs_added_in_batch.add(num_doc)

        if len(errors_by_index) == len(pagos_list):

            results = [
                {
                    "index": i,
                    "success": False,
                    "error": errors_by_index[i]["error"],
                    "status_code": errors_by_index[i]["status_code"],
                }
                for i in sorted(errors_by_index)
            ]

            return {"results": results, "ok_count": 0, "fail_count": len(results)}

        cedulas_lote = {
            (pagos_list[i].cedula_cliente or "").strip().upper()
            for i in range(len(pagos_list))
            if i not in errors_by_index and (pagos_list[i].cedula_cliente or "").strip()
        }

        alinear_cedulas_clientes_existentes(db, cedulas_lote)



        # Fase 2: transaccion unica. Crear pagos validos (flush), aplicar a cuotas, un commit al final.

        results: list[dict] = []

        try:

            autorizados_bs = preload_autorizados_bs(db)

            huellas_lote_batch: set[tuple[int, str, str, str]] = set()

            for idx, payload in enumerate(pagos_list):

                num_doc = (

                    docs_compuestos[idx]

                    if idx < len(docs_compuestos)

                    else compose_numero_documento_almacenado(

                        payload.numero_documento,

                        getattr(payload, "codigo_documento", None),

                    )

                )

                if idx in errors_by_index:

                    err = errors_by_index[idx]

                    results.append(

                        {

                            "index": idx,

                            "success": False,

                            "error": err["error"],

                            "status_code": err["status_code"],

                        }

                    )

                    continue

                ref = (num_doc or "N/A")[:_MAX_LEN_NUMERO_DOCUMENTO]

                fecha_pago_ts = datetime.combine(payload.fecha_pago, dt_time.min)

                _pid_res = resolved_prestamo_id_by_index.get(idx)

                if _pid_res is None:

                    raise HTTPException(status_code=500, detail=f"Lote fila {idx + 1}: falta prestamo_id resuelto (error interno).")

                conciliado = payload.conciliado if payload.conciliado is not None else True

                cedula_normalizada = (payload.cedula_cliente or "").strip().upper()

                es_valido_b, monto_val_b, err_msg_b = _validar_monto(payload.monto_pagado)

                if not es_valido_b:

                    raise HTTPException(status_code=400, detail=f"Lote fila {idx + 1}: {err_msg_b}")

                try:

                    monto_usd_b, moneda_fin_b, monto_bs_b, tasa_b, fecha_tasa_b = resolver_monto_registro_pago(

                        db,

                        cedula_normalizada=cedula_normalizada,

                        fecha_pago=payload.fecha_pago,

                        monto_pagado=Decimal(str(round(monto_val_b, 2))),

                        moneda_registro=payload.moneda_registro or "USD",

                        tasa_cambio_manual=payload.tasa_cambio_manual,

                        autorizados_bs=autorizados_bs,

                    )

                except HTTPException as e:

                    d = e.detail if isinstance(e.detail, str) else str(e.detail)

                    raise HTTPException(status_code=e.status_code, detail=f"Lote fila {idx + 1}: {d}") from e

                msg_h_batch = conflicto_huella_para_creacion(
                    db,
                    prestamo_id=_pid_res,
                    fecha_pago=payload.fecha_pago,
                    monto_pagado=monto_usd_b,
                    numero_documento=num_doc,
                    referencia_pago=ref,
                    huellas_en_mismo_lote=huellas_lote_batch,
                )
                if msg_h_batch:
                    registrar_rechazo_huella_funcional()
                    raise HTTPException(
                        status_code=409,
                        detail=f"Lote fila {idx + 1}: {msg_h_batch}",
                    )

                row = Pago(

                    cedula_cliente=cedula_normalizada,

                    prestamo_id=_pid_res,

                    fecha_pago=fecha_pago_ts,

                    monto_pagado=monto_usd_b,

                    numero_documento=num_doc,

                    institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,

                    estado="PAGADO" if conciliado else "PENDIENTE",

                    notas=payload.notas.strip() if payload.notas else None,

                    referencia_pago=ref,

                    conciliado=conciliado,

                    fecha_conciliacion=datetime.now(ZoneInfo(TZ_NEGOCIO)) if conciliado else None,

                    verificado_concordancia="SI" if conciliado else "",

                    usuario_registro=usuario_registro,

                    moneda_registro=moneda_fin_b,

                    monto_bs_original=monto_bs_b,

                    tasa_cambio_bs_usd=tasa_b,

                    fecha_tasa_referencia=fecha_tasa_b,

                    link_comprobante=(
                        payload.link_comprobante.strip()
                        if payload.link_comprobante
                        else None
                    ),

                )

                db.add(row)

                db.flush()

                db.refresh(row)

                if _debe_aplicar_cascada_pago(row):

                    cc_b, cp_b = _aplicar_pago_a_cuotas_interno(row, db)

                    row.estado = _estado_conciliacion_post_cascada(row, cc_b, cp_b)

                results.append({"index": idx, "success": True, "pago": _pago_to_response(row)})

            db.commit()

            # Persistir link_comprobante desde pagos_gmail_sync_item si el Excel no trajo URL
            try:
                ok_ids = [
                    int(r["pago"]["id"])
                    for r in results
                    if r.get("success") and r.get("pago", {}).get("id") is not None
                ]
                if ok_ids:
                    rows_lc = db.execute(select(Pago).where(Pago.id.in_(ok_ids))).scalars().all()
                    to_persist = False
                    for row_lc in rows_lc:
                        if (getattr(row_lc, "link_comprobante", None) or "").strip():
                            continue
                        out_lc = _pago_to_response(row_lc)
                        enriquecer_items_link_comprobante_desde_gmail(db, [out_lc])
                        url_lc = (out_lc.get("link_comprobante") or "").strip()
                        if url_lc:
                            row_lc.link_comprobante = url_lc
                            to_persist = True
                    if to_persist:
                        db.commit()
                        for r in results:
                            if not r.get("success"):
                                continue
                            pid = r.get("pago", {}).get("id")
                            if pid is None:
                                continue
                            row_u = db.get(Pago, int(pid))
                            if row_u:
                                r["pago"] = _pago_to_response(row_u)
            except Exception as ex_lc:
                logger.warning(
                    "Batch: no se pudo persistir link_comprobante desde Gmail sync: %s",
                    ex_lc,
                )
                db.rollback()

            results.sort(key=lambda r: r["index"])

            ok_count = sum(1 for r in results if r.get("success"))

            fail_count = len(results) - ok_count

            return {"results": results, "ok_count": ok_count, "fail_count": fail_count}

        except HTTPException:

            db.rollback()

            raise

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

    _doc_touch = False

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

            raise HTTPException(status_code=400, detail="numero_documento no puede estar vacio.")

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

        data.pop("numero_documento", None)

        data.pop("codigo_documento", None)

        row.numero_documento = new_stored

    _mark_fase("validacion_documento")

    aplicar_conciliado = False

    _put_mon_keys = ("monto_pagado", "moneda_registro", "tasa_cambio_manual", "fecha_pago")

    monetario_up = {k: data.pop(k) for k in _put_mon_keys if k in data}

    for k, v in data.items():

        if k == "notas" and v is not None:

            setattr(row, k, v.strip() or None)

        elif k == "institucion_bancaria" and v is not None:

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

            if "monto_pagado" in monetario_up:

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


@router.post("/por-prestamo/{prestamo_id:int}/aplicar-pagos-cuotas", response_model=dict)

def aplicar_pagos_pendientes_cuotas_por_prestamo(

    prestamo_id: int,

    db: Session = Depends(get_db),

):

    """

    Aplica en cascada (por fecha_pago, luego id) los pagos del préstamo que aún no tienen

    filas en cuota_pagos y cumplen criterios de elegibilidad (conciliado / verificado / PAGADO /
    PENDIENTE con prestamo asignado).

    Por cada pago, el reparto a cuotas sigue el orden numero_cuota (cascada / waterfall).

    Persiste en BD. Útil tras editar/crear pagos en revisión manual o regenerar cuotas.

    """

    p = db.get(Prestamo, prestamo_id)

    if not p:

        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    diagnostico: dict[str, Any] = {}

    try:

        from app.services.pagos_aplicacion_prestamo import aplicar_cascada_prestamo_pipeline

        pipeline = aplicar_cascada_prestamo_pipeline(
            prestamo_id,
            db,
            reconstruir_completa=True,
        )

        if not pipeline.get("ok"):

            raise HTTPException(

                status_code=400,

                detail=str(pipeline.get("error") or "No se pudo aplicar la cascada de cuotas."),

            )

        n = int(pipeline.get("pagos_con_aplicacion") or 0)

        diagnostico = dict(pipeline.get("diagnostico") or {})

        reaplicacion_completa = bool(pipeline.get("reaplicacion_completa"))

        detalle_reaplicacion = pipeline.get("detalle_reaplicacion")

        mensaje = str(pipeline.get("mensaje") or "")

        db.commit()

    except HTTPException:

        db.rollback()

        raise

    except Exception as e:

        db.rollback()

        logger.exception(

            "aplicar-pagos-cuotas por prestamo_id=%s: %s",

            prestamo_id,

            e,

        )

        raise HTTPException(

            status_code=500,

            detail=f"Error al aplicar pagos a cuotas: {str(e)}",

        ) from e

    return {

        "prestamo_id": prestamo_id,

        "pagos_con_aplicacion": n,

        "reaplicacion_completa": reaplicacion_completa,

        "detalle_reaplicacion": detalle_reaplicacion,

        "mensaje": mensaje,

        "diagnostico": diagnostico,

    }





@router.delete("/por-prestamo/{prestamo_id:int}/todos", response_model=dict)

def eliminar_todos_pagos_por_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    _current: UserResponse = Depends(require_operator_or_higher),
):

    """

    Elimina todos los pagos asociados al préstamo, limpia dependencias y reinicia totales en cuotas.

    También elimina filas en `pagos_con_errores` del mismo préstamo (y pendientes huérfanos
    de la misma cédula) para que al volver a cargar Excel no falle por «Ya existe» en comprobante+código.

    Solo préstamos en estado APROBADO (flujo «reemplazar pagos» antes de carga masiva desde Excel).

    Requiere rol operario, gerente o administrador (no «viewer»): operación masiva de escritura.

    """

    from app.services.pagos_cuotas_reaplicacion import eliminar_todos_pagos_prestamo

    try:

        r = eliminar_todos_pagos_prestamo(db, prestamo_id)

        if not r.get("ok"):

            msg = str(r.get("error") or "No se pudo eliminar")

            if "no encontrado" in msg.lower():

                raise HTTPException(status_code=404, detail=msg)

            raise HTTPException(status_code=400, detail=msg)

        db.commit()

    except HTTPException:

        db.rollback()

        raise

    except Exception as e:

        db.rollback()

        logger.exception(

            "eliminar_todos_pagos_por_prestamo prestamo_id=%s: %s",

            prestamo_id,

            e,

        )

        raise HTTPException(status_code=500, detail=str(e)[:300]) from e

    return r





@router.delete("/{pago_id:int}", status_code=204)

def eliminar_pago(pago_id: int, db: Session = Depends(get_db)):

    """Elimina un pago, limpia dependencias y, si tiene crédito, alinea cuotas vía cascada.

    Con `prestamo_id`: tras borrar el pago se ejecuta `reset_y_reaplicar_cascada_prestamo`
    (limpia `reporte_contable_cache`, recalcula `total_pagado` / estados y reaplica pagos restantes).
    Sin crédito: basta el borrado del pago (CASCADE en `cuota_pagos` si hubiera filas huérfanas).
    """

    row = db.get(Pago, pago_id)

    if not row:

        raise HTTPException(status_code=404, detail="Pago no encontrado")

    prestamo_id_previo = row.prestamo_id
    n_cuota_pagos_articuladas = int(
        db.scalar(
            text("SELECT COUNT(*) FROM cuota_pagos WHERE pago_id = :pid"),
            {"pid": pago_id},
        )
        or 0
    )

    try:
        db.execute(text("DELETE FROM auditoria_conciliacion_manual WHERE pago_id = :pid"), {"pid": pago_id})
        db.execute(text("DELETE FROM auditoria_pago_control5_visto WHERE pago_id = :pid"), {"pid": pago_id})
        db.execute(text("DELETE FROM cuota_pagos WHERE pago_id = :pid"), {"pid": pago_id})
        db.execute(text("UPDATE cuotas SET pago_id = NULL WHERE pago_id = :pid"), {"pid": pago_id})
        db.execute(text("DELETE FROM revisar_pagos WHERE pago_id = :pid"), {"pid": pago_id})

        db.delete(row)
        db.flush()

        if prestamo_id_previo:
            from app.services.pagos_cuotas_reaplicacion import (
                realinear_cuotas_prestamo_desde_cuota_pagos,
                reset_y_reaplicar_cascada_prestamo,
            )

            if n_cuota_pagos_articuladas > 0:
                r = reset_y_reaplicar_cascada_prestamo(db, prestamo_id_previo)
            else:
                r = realinear_cuotas_prestamo_desde_cuota_pagos(db, prestamo_id_previo)
                if not r.get("ok"):
                    raise HTTPException(
                        status_code=500,
                        detail=(r.get("error") or "No se pudo realinear cuotas tras eliminar el pago")[:400],
                    )
                if r.get("requiere_reset_cascada"):
                    r = reset_y_reaplicar_cascada_prestamo(db, prestamo_id_previo)
            if not r.get("ok"):
                raise HTTPException(
                    status_code=500,
                    detail=(r.get("error") or "No se pudo alinear cuotas tras eliminar el pago")[:400],
                )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import logging
        from app.services.pagos_aplicacion_prestamo import detalle_excepcion_db

        logging.getLogger(__name__).error("Error eliminando pago %s: %s", pago_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar pago {pago_id}: {detalle_excepcion_db(e, max_len=400)}",
        ) from e

    return None


@router.get("/diagnostico/pago/{pago_id}", response_model=dict)
def diagnostico_pago(pago_id: int, db: Session = Depends(get_db)):
    """Verifica si un pago existe en BD y muestra sus dependencias."""
    info: dict = {"pago_id": pago_id, "existe_en_pagos": False, "dependencias": {}}

    row = db.execute(
        text("SELECT id, prestamo_id, cedula_cliente, monto_pagado, fecha_pago, numero_documento, estado, ref_norm FROM pagos WHERE id = :pid"),
        {"pid": pago_id},
    ).first()

    if row:
        info["existe_en_pagos"] = True
        info["pago"] = {
            "id": row[0], "prestamo_id": row[1], "cedula": row[2],
            "monto": float(row[3]) if row[3] else None,
            "fecha": str(row[4]) if row[4] else None,
            "documento": row[5], "estado": row[6], "ref_norm": row[7],
        }

    cp = db.execute(text("SELECT COUNT(*) FROM cuota_pagos WHERE pago_id = :pid"), {"pid": pago_id}).scalar()
    info["dependencias"]["cuota_pagos"] = cp or 0

    acm = db.execute(text("SELECT COUNT(*) FROM auditoria_conciliacion_manual WHERE pago_id = :pid"), {"pid": pago_id}).scalar()
    info["dependencias"]["auditoria_conciliacion_manual"] = acm or 0

    cuotas_ref = db.execute(text("SELECT COUNT(*) FROM cuotas WHERE pago_id = :pid"), {"pid": pago_id}).scalar()
    info["dependencias"]["cuotas_con_pago_id"] = cuotas_ref or 0

    rp = db.execute(text("SELECT COUNT(*) FROM revisar_pagos WHERE pago_id = :pid"), {"pid": pago_id}).scalar()
    info["dependencias"]["revisar_pagos"] = rp or 0

    return info


@router.delete("/forzar-eliminar/{pago_id}", response_model=dict)
@router.post("/forzar-eliminar/{pago_id}", response_model=dict)
def forzar_eliminar_pago(
    pago_id: int,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin),
):
    """Eliminacion forzada: limpia TODAS las dependencias y borra el pago con SQL directo.

    Si el pago tenia `prestamo_id`, tras borrarlo se reaplica la cascada del credito
    (misma logica que DELETE normal: cuotas alineadas y cache contable invalidada).
    """
    import logging
    log = logging.getLogger(__name__)

    row0 = db.execute(
        text("SELECT id, prestamo_id FROM pagos WHERE id = :pid"),
        {"pid": pago_id},
    ).first()
    if not row0:
        return {"ok": False, "detail": f"Pago {pago_id} no existe en tabla pagos"}
    prestamo_id_previo = row0[1]

    try:
        r1 = db.execute(text("DELETE FROM cuota_pagos WHERE pago_id = :pid"), {"pid": pago_id})
        r2 = db.execute(text("DELETE FROM auditoria_conciliacion_manual WHERE pago_id = :pid"), {"pid": pago_id})
        r3 = db.execute(text("UPDATE cuotas SET pago_id = NULL WHERE pago_id = :pid"), {"pid": pago_id})
        r4 = db.execute(text("DELETE FROM revisar_pagos WHERE pago_id = :pid"), {"pid": pago_id})

        # Buscar cualquier otra FK que referencie pagos.id
        fk_check = db.execute(text("""
            SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
            WHERE ccu.table_name = 'pagos' AND ccu.column_name = 'id'
              AND tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name NOT IN ('cuota_pagos', 'auditoria_conciliacion_manual', 'cuotas', 'revisar_pagos')
        """)).fetchall()

        extra_cleaned = []
        for fk_row in fk_check:
            tbl, col = fk_row[0], fk_row[1]
            db.execute(text(f'DELETE FROM "{tbl}" WHERE "{col}" = :pid'), {"pid": pago_id})
            extra_cleaned.append(f"{tbl}.{col}")

        r5 = db.execute(text("DELETE FROM pagos WHERE id = :pid"), {"pid": pago_id})

        reaplicado: Optional[dict] = None
        if prestamo_id_previo:
            from app.services.pagos_cuotas_reaplicacion import reset_y_reaplicar_cascada_prestamo

            r = reset_y_reaplicar_cascada_prestamo(db, prestamo_id_previo)
            if not r.get("ok"):
                db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail=(r.get("error") or "No se pudo alinear cuotas tras forzar eliminación")[:300],
                )
            reaplicado = {
                "prestamo_id": prestamo_id_previo,
                "pagos_reaplicados": r.get("pagos_reaplicados"),
                "cache_contable_eliminadas": r.get("cache_contable_eliminadas"),
            }

        db.commit()

        log.info("Pago %s eliminado forzadamente. cuota_pagos=%s acm=%s cuotas=%s revisar=%s pagos=%s extra=%s",
                 pago_id, r1.rowcount, r2.rowcount, r3.rowcount, r4.rowcount, r5.rowcount, extra_cleaned)

        out: dict = {
            "ok": True,
            "eliminado": {
                "cuota_pagos": r1.rowcount, "auditoria_conciliacion_manual": r2.rowcount,
                "cuotas_nulled": r3.rowcount, "revisar_pagos": r4.rowcount,
                "pagos": r5.rowcount, "extra_fks": extra_cleaned,
            },
        }
        if reaplicado is not None:
            out["cascada_tras_eliminar"] = reaplicado
        return out
    except Exception as e:
        db.rollback()
        log.error("Error forzar-eliminar pago %s: %s", pago_id, e)
        raise HTTPException(
            status_code=500,
            detail="Error interno al eliminar el pago. Intente nuevamente o contacte soporte.",
        ) from e




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

    if pago_tiene_aplicaciones_cuotas(db, pago.id):
        return {
            "success": True,
            "ya_aplicado": True,
            "cuotas_completadas": 0,
            "cuotas_parciales": 0,
            "message": "El pago ya tiene aplicaciones en cuota_pagos. No se duplico la cascada.",
        }

    try:

        cuotas_completadas, cuotas_parciales = _aplicar_pago_a_cuotas_interno(pago, db)

        pago.estado = _estado_conciliacion_post_cascada(pago, cuotas_completadas, cuotas_parciales)

        db.commit()

        return {

            "success": True,

            "ya_aplicado": False,

            "cuotas_completadas": cuotas_completadas,

            "cuotas_parciales": cuotas_parciales,

            "message": f"Se aplicó el pago: {cuotas_completadas} cuota(s) completadas, {cuotas_parciales} parcial(es).",

        }

    except HTTPException:

        raise

    except ValueError as e:

        db.rollback()

        logger.warning("aplicar-cuotas integridad pago_id=%s: %s", pago_id, e)

        raise HTTPException(status_code=409, detail=str(e)) from e

    except Exception as e:

        db.rollback()

        logger.exception("Error aplicar-cuotas pago_id=%s: %s", pago_id, e)

        raise HTTPException(

            status_code=500,

            detail=f"Error al aplicar el pago a cuotas: {str(e)}",

        ) from e





class ConciliarAplicarBatchBody(BaseModel):
    """Lote de IDs de pagos a conciliar y aplicar a cuotas en una sola operación."""

    ids: list[int]

    @field_validator("ids")
    @classmethod
    def _ids_limite(cls, v: list[int]) -> list[int]:
        if len(v) > 500:
            raise ValueError("Máximo 500 pagos por lote.")
        return v


@router.post("/conciliar-aplicar-batch", response_model=dict)
def conciliar_y_aplicar_pagos_batch(
    payload: ConciliarAplicarBatchBody = Body(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    """
    Para los IDs indicados (tabla `pagos`), si están en cartera **PENDIENTE** con préstamo y monto:
    - fija `conciliado=True`, `verificado_concordancia="SI"`, `fecha_conciliacion=now`
    - abre `estado="PAGADO"` (cumple `chk_pagos_conciliado_pendiente_inconsistente`)
    - dispara la cascada `_aplicar_pago_a_cuotas_interno`

    Aislamiento por fila (try/except + rollback parcial): un fallo puntual no tumba el lote;
    devuelve resumen con `procesados`, `cuotas_aplicadas` y `errores[]` para los que no entraron.
    Saltos no son error: pagos ya conciliados, sin préstamo, monto<=0, ya aplicados a cuotas, etc.
    """
    _ = current_user  # auth, no se usa el objeto aquí
    ids = [int(i) for i in (payload.ids or []) if isinstance(i, int) and i > 0]
    if not ids:
        return {
            "procesados": 0,
            "cuotas_aplicadas": 0,
            "saltados": 0,
            "errores": [],
            "mensaje": "No hay IDs válidos en el lote.",
        }

    procesados = 0
    cuotas_aplicadas = 0
    saltados = 0
    errores: list[str] = []
    saltados_detalle: list[str] = []

    for pid in ids:
        try:
            pago = db.get(Pago, pid)
            if pago is None:
                saltados += 1
                saltados_detalle.append(f"Pago {pid}: no encontrado")
                continue

            estado_actual = (pago.estado or "").strip().upper()
            if estado_actual not in ("", "PENDIENTE"):
                saltados += 1
                saltados_detalle.append(
                    f"Pago {pid}: estado {estado_actual or '∅'} ≠ PENDIENTE; ya cerrado o no aplicable."
                )
                continue

            if not pago.prestamo_id:
                saltados += 1
                saltados_detalle.append(f"Pago {pid}: sin préstamo asociado.")
                continue

            try:
                monto = float(pago.monto_pagado or 0)
            except (TypeError, ValueError):
                monto = 0.0
            if monto <= 0:
                saltados += 1
                saltados_detalle.append(f"Pago {pid}: monto <= 0.")
                continue

            if pago_tiene_aplicaciones_cuotas(db, pago.id):
                # Ya tenía cuota_pagos: solo alineamos la marca de cartera si hace falta.
                cambios = False
                if not bool(pago.conciliado):
                    pago.conciliado = True
                    pago.fecha_conciliacion = datetime.now(ZoneInfo("America/Caracas"))
                    cambios = True
                if (pago.verificado_concordancia or "").strip().upper() != "SI":
                    pago.verificado_concordancia = "SI"
                    cambios = True
                if estado_actual == "PENDIENTE":
                    pago.estado = "PAGADO"
                    cambios = True
                if cambios:
                    db.flush()
                    procesados += 1
                else:
                    saltados += 1
                    saltados_detalle.append(
                        f"Pago {pid}: ya aplicado a cuotas y marcado en cartera."
                    )
                continue

            # Pago elegible: marcar cartera y aplicar cascada.
            pago.conciliado = True
            pago.verificado_concordancia = "SI"
            pago.fecha_conciliacion = datetime.now(ZoneInfo("America/Caracas"))
            pago.estado = "PAGADO"  # evita chk_pagos_conciliado_pendiente_inconsistente

            db.flush()

            cc, cp = _aplicar_pago_a_cuotas_interno(pago, db)
            cuotas_aplicadas += int(cc) + int(cp)
            procesados += 1
        except Exception as e_row:
            db.rollback()
            logger.error(
                "conciliar_y_aplicar_pagos_batch: fallo en pago_id=%s: %s",
                pid,
                e_row,
                exc_info=True,
            )
            errores.append(f"Pago {pid}: {e_row}")
            continue

    try:
        db.commit()
    except Exception as e_commit:
        db.rollback()
        logger.exception("conciliar_y_aplicar_pagos_batch: commit final falló: %s", e_commit)
        raise HTTPException(
            status_code=500,
            detail=f"Error al confirmar el lote: {e_commit}",
        ) from e_commit

    mensaje = (
        f"{procesados} pago(s) procesado(s); {cuotas_aplicadas} cuota(s) afectada(s); "
        f"{saltados} saltado(s); {len(errores)} con error."
    )
    respuesta: dict[str, Any] = {
        "procesados": procesados,
        "cuotas_aplicadas": cuotas_aplicadas,
        "saltados": saltados,
        "saltados_detalle": saltados_detalle,
        "errores": errores,
        "mensaje": mensaje,
    }
    return respuesta


# --- Cédulas permitidas para reportar en Bs (rapicredit-cobros / infopagos) ---
# Normalización canónica: app.services.cobros.cedula_reportar_bs_service


