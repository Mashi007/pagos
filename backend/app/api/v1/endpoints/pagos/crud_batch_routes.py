"""Pagos: batch y mover a revisar."""
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







