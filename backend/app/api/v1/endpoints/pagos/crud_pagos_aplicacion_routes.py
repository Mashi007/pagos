"""Pagos: aplicar cuotas, eliminar, conciliar batch."""
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

        # Incremental por defecto (cascada por pago). Full reset solo si diagnostico lo exige.
        pipeline = aplicar_cascada_prestamo_pipeline(
            prestamo_id,
            db,
            reconstruir_completa=False,
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

            # Preferir cascada completa; si hay otros duplicados por huella en el crédito,
            # no revertir el DELETE: realinear desde cuota_pagos restantes.
            r = None
            if n_cuota_pagos_articuladas > 0:
                r = reset_y_reaplicar_cascada_prestamo(db, prestamo_id_previo)
            else:
                r = realinear_cuotas_prestamo_desde_cuota_pagos(db, prestamo_id_previo)
                if r.get("ok") and r.get("requiere_reset_cascada"):
                    r = reset_y_reaplicar_cascada_prestamo(db, prestamo_id_previo)

            if not r or not r.get("ok"):
                codigo = (r or {}).get("codigo")
                if codigo == "huella_duplicada" or (
                    "huella funcional" in str((r or {}).get("error") or "").lower()
                ):
                    logger.warning(
                        "eliminar_pago pago_id=%s: cascada bloqueada por huella en prestamo %s; "
                        "se conserva el DELETE y se realinea desde cuota_pagos. detalle=%s",
                        pago_id,
                        prestamo_id_previo,
                        (r or {}).get("error"),
                    )
                    r2 = realinear_cuotas_prestamo_desde_cuota_pagos(db, prestamo_id_previo)
                    if not r2.get("ok"):
                        raise HTTPException(
                            status_code=500,
                            detail=(
                                r2.get("error")
                                or "No se pudo realinear cuotas tras eliminar el pago"
                            )[:400],
                        )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=(
                            (r or {}).get("error")
                            or "No se pudo alinear cuotas tras eliminar el pago"
                        )[:400],
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


