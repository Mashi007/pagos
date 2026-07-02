"""Pagos API: listado."""
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
    _enriquecer_items_duplicado_serial_cartera,
    _enriquecer_items_tiene_aplicacion_cuotas,
    _enriquecer_pagos_pago_reportado_id,
    _pago_response_enriquecido,
    _pago_to_response,
)









logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("", response_model=dict)

def listar_pagos(

    page: int = Query(1, ge=1),

    per_page: int = Query(20, ge=1, le=100),

    cedula: Optional[str] = Query(None),

    estado: Optional[str] = Query(None),
    tipo_revision: Optional[str] = Query(
        None,
        description="Filtro especial de auditoría. Soporta: rebasa_total (suma de pagos del préstamo > total_financiamiento).",
    ),

    fecha_desde: Optional[str] = Query(None),

    fecha_hasta: Optional[str] = Query(None),

    analista: Optional[str] = Query(None),

    conciliado: Optional[str] = Query(None, description="si=conciliados, no=no conciliados, vacío=todos"),

    sin_prestamo: Optional[str] = Query(None, description="si=solo pagos sin crédito asignado (prestamo_id NULL)"),

    prestamo_cartera: str = Query(
        "activa",
        description="activa=solo pagos sin crédito o con préstamo APROBADO (oculta LIQUIDADO y otros). todos=sin filtrar por estado del préstamo.",
    ),

    resumen_prestamo_id: Optional[int] = Query(
        None,
        ge=1,
        description=(
            "Si se indica, la respuesta incluye resumen_prestamo: agregados de la tabla pagos "
            "para ese prestamo_id (cantidad, suma de montos, pendiente vs PAGADO). Opcionalmente "
            "cruzado con filtro cédula si viene en la misma petición. No altera el listado paginado."
        ),
    ),
    prestamo_id: Optional[int] = Query(
        None,
        ge=1,
        description="Si se indica, filtra el listado principal por este prestamo_id exacto.",
    ),

    db: Session = Depends(get_db),

):

    """Listado paginado desde la tabla pagos. Filtros: cedula, estado, fecha_desde, fecha_hasta, analista, conciliado, sin_prestamo, prestamo_cartera, prestamo_id."""

    try:

        # Invocación directa (p. ej. finiquito): defaults sin resolver siguen siendo Query().

        def _solo_str_lp(v: Any) -> Optional[str]:

            return v if isinstance(v, str) else None

        page = page if isinstance(page, int) else 1

        per_page = per_page if isinstance(per_page, int) else 20

        cedula = _solo_str_lp(cedula)

        estado = _solo_str_lp(estado)
        tipo_revision = _solo_str_lp(tipo_revision)

        fecha_desde = _solo_str_lp(fecha_desde)

        fecha_hasta = _solo_str_lp(fecha_hasta)

        analista = _solo_str_lp(analista)

        conciliado = _solo_str_lp(conciliado)

        sin_prestamo = _solo_str_lp(sin_prestamo)

        prestamo_cartera = _solo_str_lp(prestamo_cartera) or "activa"

        q = select(Pago)

        count_q = select(func.count()).select_from(Pago)

        sum_q = select(func.coalesce(func.sum(Pago.monto_pagado), 0)).select_from(Pago)

        _pc = (prestamo_cartera or "activa").strip().lower()

        _solo_prestamos_aprobados = _pc not in ("todos", "all", "t")
        if prestamo_id is not None:
            # Filtro puntual por credito: no aplicar recorte de cartera activa para no ocultar LIQUIDADO.
            _solo_prestamos_aprobados = False

        def _estado_prestamo_aprobado_sql():
            return func.upper(
                func.trim(func.coalesce(Prestamo.estado, ""))
            ) == "APROBADO"

        if sin_prestamo and sin_prestamo.strip().lower() == "si":

            q = q.where(Pago.prestamo_id.is_(None))

            count_q = count_q.where(Pago.prestamo_id.is_(None))

            sum_q = sum_q.where(Pago.prestamo_id.is_(None))

            # Excluir pagos ya movidos a revisar_pagos (tabla temporal de validación)

            revisar_subq = select(RevisarPago.pago_id)

            q = q.where(~Pago.id.in_(revisar_subq))

            count_q = count_q.where(~Pago.id.in_(revisar_subq))

            sum_q = sum_q.where(~Pago.id.in_(revisar_subq))

        if conciliado and conciliado.strip().lower() == "si":

            q = q.where(Pago.conciliado == True)

            count_q = count_q.where(Pago.conciliado == True)

            sum_q = sum_q.where(Pago.conciliado == True)

        elif conciliado and conciliado.strip().lower() == "no":

            q = q.where(or_(Pago.conciliado == False, Pago.conciliado.is_(None)))

            count_q = count_q.where(or_(Pago.conciliado == False, Pago.conciliado.is_(None)))

            sum_q = sum_q.where(or_(Pago.conciliado == False, Pago.conciliado.is_(None)))

        if prestamo_id is not None:

            pid = int(prestamo_id)

            q = q.where(Pago.prestamo_id == pid)

            count_q = count_q.where(Pago.prestamo_id == pid)

            sum_q = sum_q.where(Pago.prestamo_id == pid)

        if cedula and cedula.strip():

            q = q.where(Pago.cedula_cliente.ilike(f"%{cedula.strip()}%"))

            count_q = count_q.where(Pago.cedula_cliente.ilike(f"%{cedula.strip()}%"))

            sum_q = sum_q.where(Pago.cedula_cliente.ilike(f"%{cedula.strip()}%"))

        if estado and estado.strip():

            q = q.where(Pago.estado == estado.strip().upper())

            count_q = count_q.where(Pago.estado == estado.strip().upper())

            sum_q = sum_q.where(Pago.estado == estado.strip().upper())

        if tipo_revision and tipo_revision.strip().lower() in (
            "rebasa_total",
            "sobrepagado",
            "exceso_total",
        ):
            p2 = aliased(Pago)
            total_pagos_prestamo = (
                select(func.coalesce(func.sum(p2.monto_pagado), 0))
                .where(p2.prestamo_id == Pago.prestamo_id)
                .correlate(Pago)
                .scalar_subquery()
            )
            rebasa_total_cond = and_(
                Pago.prestamo_id.is_not(None),
                exists(
                    select(1).where(
                        Prestamo.id == Pago.prestamo_id,
                        total_pagos_prestamo
                        > func.coalesce(Prestamo.total_financiamiento, 0),
                    )
                ),
            )
            q = q.where(rebasa_total_cond)
            count_q = count_q.where(rebasa_total_cond)
            sum_q = sum_q.where(rebasa_total_cond)

        if fecha_desde:

            try:

                fd = date.fromisoformat(fecha_desde)

                q = q.where(Pago.fecha_pago >= datetime.combine(fd, dt_time.min))

                count_q = count_q.where(Pago.fecha_pago >= datetime.combine(fd, dt_time.min))

                sum_q = sum_q.where(Pago.fecha_pago >= datetime.combine(fd, dt_time.min))

            except ValueError:

                pass

        if fecha_hasta:

            try:

                fh = date.fromisoformat(fecha_hasta)

                q = q.where(Pago.fecha_pago <= datetime.combine(fh, dt_time.max))

                count_q = count_q.where(Pago.fecha_pago <= datetime.combine(fh, dt_time.max))

                sum_q = sum_q.where(Pago.fecha_pago <= datetime.combine(fh, dt_time.max))

            except ValueError:

                pass

        if analista and analista.strip():

            q = q.join(Prestamo, Pago.prestamo_id == Prestamo.id).where(Prestamo.analista == analista.strip())

            count_q = count_q.join(Prestamo, Pago.prestamo_id == Prestamo.id).where(Prestamo.analista == analista.strip())

            sum_q = sum_q.join(Prestamo, Pago.prestamo_id == Prestamo.id).where(Prestamo.analista == analista.strip())

            if _solo_prestamos_aprobados:

                q = q.where(_estado_prestamo_aprobado_sql())

                count_q = count_q.where(_estado_prestamo_aprobado_sql())

                sum_q = sum_q.where(_estado_prestamo_aprobado_sql())

        elif _solo_prestamos_aprobados:

            q = q.outerjoin(Prestamo, Pago.prestamo_id == Prestamo.id).where(

                or_(Pago.prestamo_id.is_(None), _estado_prestamo_aprobado_sql()),

            )

            count_q = count_q.outerjoin(Prestamo, Pago.prestamo_id == Prestamo.id).where(

                or_(Pago.prestamo_id.is_(None), _estado_prestamo_aprobado_sql()),

            )

            sum_q = sum_q.outerjoin(Prestamo, Pago.prestamo_id == Prestamo.id).where(

                or_(Pago.prestamo_id.is_(None), _estado_prestamo_aprobado_sql()),

            )

        total = db.scalar(count_q) or 0

        # Orden: más reciente primero (fecha_pago desc, luego id desc)

        q = q.order_by(Pago.fecha_pago.desc().nullslast(), Pago.id.desc()).offset((page - 1) * per_page).limit(per_page)

        rows = db.execute(q).scalars().all()

        items = [_pago_to_response(r) for r in rows]

        # Exceso por préstamo: suma(pagos.monto_pagado) - total_financiamiento.
        # Se adjunta por fila para auditoría rápida en UI (Revision global).
        prestamo_ids_page = sorted(
            {
                int(r.prestamo_id)
                for r in rows
                if getattr(r, "prestamo_id", None) is not None
            }
        )
        exceso_por_prestamo: dict[int, float] = {}
        if prestamo_ids_page:
            exceso_rows = db.execute(
                select(
                    Pago.prestamo_id,
                    (
                        func.coalesce(func.sum(Pago.monto_pagado), 0)
                        - func.coalesce(Prestamo.total_financiamiento, 0)
                    ).label("exceso"),
                )
                .join(Prestamo, Prestamo.id == Pago.prestamo_id)
                .where(Pago.prestamo_id.in_(prestamo_ids_page))
                .group_by(Pago.prestamo_id, Prestamo.total_financiamiento)
            ).all()
            for pr_id, exceso in exceso_rows:
                if pr_id is None:
                    continue
                val = float(exceso or 0)
                if val > 0:
                    exceso_por_prestamo[int(pr_id)] = val
        for it in items:
            pid = it.get("prestamo_id")
            if isinstance(pid, int) and pid in exceso_por_prestamo:
                it["exceso_sobre_total_usd"] = round(exceso_por_prestamo[pid], 2)
            else:
                it["exceso_sobre_total_usd"] = None

        _enriquecer_items_tiene_aplicacion_cuotas(db, items)

        _enriquecer_pagos_pago_reportado_id(db, items)

        _enriquecer_items_duplicado_clave_misma_pagina(rows, items)

        _enriquecer_items_duplicado_serial_cartera(db, rows, items)

        enriquecer_items_link_comprobante_desde_gmail(db, items)

        enriquecer_items_link_comprobante_desde_pago_reportado(db, items)

        total_pages = (total + per_page - 1) // per_page if total else 0

        out: dict = {

            "pagos": items,

            "total": total,

            "page": page,

            "per_page": per_page,

            "total_pages": total_pages,

        }

        # Solo con filtro cédula: total de monto_pagado de todos los pagos que coinciden (no solo la página).
        if cedula and cedula.strip():

            raw_sum = db.scalar(sum_q)

            out["sum_monto_pagado_cedula"] = float(raw_sum or 0)

        # Resumen por crédito (sin filtrar el listado principal): auditoría revisión manual / coherencia con cuotas.
        if resumen_prestamo_id is not None and isinstance(resumen_prestamo_id, int) and resumen_prestamo_id > 0:

            pid = int(resumen_prestamo_id)

            rp_conds = [Pago.prestamo_id == pid]

            if cedula and cedula.strip():

                rp_conds.append(Pago.cedula_cliente.ilike(f"%{cedula.strip()}%"))

            rp_where = and_(*rp_conds)

            from app.services.pagos_sql_where import _where_pago_excluido_operacion

            n_all = db.scalar(select(func.count()).select_from(Pago).where(rp_where)) or 0

            s_all = db.scalar(

                select(func.coalesce(func.sum(Pago.monto_pagado), 0)).select_from(Pago).where(rp_where)

            ) or 0

            oper_where = and_(rp_where, not_(_where_pago_excluido_operacion()))

            n_oper = db.scalar(select(func.count()).select_from(Pago).where(oper_where)) or 0

            s_oper = db.scalar(

                select(func.coalesce(func.sum(Pago.monto_pagado), 0)).select_from(Pago).where(oper_where)

            ) or 0

            pend_where = and_(rp_where, Pago.estado == "PENDIENTE")

            n_pend = db.scalar(select(func.count()).select_from(Pago).where(pend_where)) or 0

            s_pend = db.scalar(

                select(func.coalesce(func.sum(Pago.monto_pagado), 0)).select_from(Pago).where(pend_where)

            ) or 0

            pag_where = and_(rp_where, Pago.estado == "PAGADO")

            n_pag = db.scalar(select(func.count()).select_from(Pago).where(pag_where)) or 0

            s_pag = db.scalar(

                select(func.coalesce(func.sum(Pago.monto_pagado), 0)).select_from(Pago).where(pag_where)

            ) or 0

            out["resumen_prestamo"] = {

                "prestamo_id": pid,

                "cantidad": int(n_all),

                "cantidad_operativos": int(n_oper),

                "cantidad_no_operativos": int(n_all) - int(n_oper),

                "suma_monto_pagado": float(s_oper or 0),

                "suma_monto_total_bd": float(s_all or 0),

                "cantidad_pendiente": int(n_pend),

                "suma_monto_pendiente": float(s_pend or 0),

                "cantidad_pagado": int(n_pag),

                "suma_monto_estado_pagado": float(s_pag or 0),

            }

        return out

    except Exception as e:

        logger.exception("Error en GET /pagos: %s", e)

        db.rollback()

        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sin-prestamo/sugerir", response_model=dict)
def sugerir_prestamos_sin_asignar(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Retorna pagos sin prestamo_id y sugiere asignación automática si el cliente tiene exactamente 1 crédito activo.
    
    Respuesta incluye:
    - pago_id: ID del pago
    - cedula_cliente: Cédula del cliente
    - prestamo_sugerido: ID del crédito (si hay exactamente 1) o None
    - num_creditos_activos: Cantidad de créditos activos del cliente
    - acciones_necesarias: "auto" si puede auto-asignarse, "manual" si requiere intervención
    """
    try:
        # Contar pagos sin prestamo_id
        count_q = select(func.count()).select_from(Pago).where(Pago.prestamo_id.is_(None))
        total = db.scalar(count_q) or 0
        
        # Obtener pagos sin prestamo_id
        q = select(Pago).where(Pago.prestamo_id.is_(None)).order_by(Pago.id.desc()).offset((page - 1) * per_page).limit(per_page)
        pagos_sin_prestamo = db.execute(q).scalars().all()
        
        sugerencias = []
        
        for pago in pagos_sin_prestamo:
            cedula_norm = pago.cedula_cliente.strip().upper() if pago.cedula_cliente else ""
            
            prestamos_activos = []
            prestamo_sugerido = None
            num_creditos = 0
            acciones = "manual"
            
            if cedula_norm:
                # Buscar créditos activos para esta cédula
                prestamos_activos = db.execute(
                    select(Prestamo.id)
                    .select_from(Prestamo)
                    .join(Cliente, Prestamo.cliente_id == Cliente.id)
                    .where(
                        Cliente.cedula == cedula_norm,
                        Prestamo.estado == "APROBADO",
                    )
                    .order_by(Prestamo.id)
                ).scalars().all()
                
                num_creditos = len(prestamos_activos)
                
                # Si exactamente 1 crédito activo → sugerencia automática
                if num_creditos == 1:
                    prestamo_sugerido = prestamos_activos[0]
                    acciones = "auto"
            
            sugerencias.append({
                "pago_id": pago.id,
                "cedula_cliente": pago.cedula_cliente,
                "fecha_pago": pago.fecha_pago.isoformat() if pago.fecha_pago else None,
                "monto_pagado": float(pago.monto_pagado) if pago.monto_pagado else 0,
                "numero_documento": pago.numero_documento,
                "prestamo_sugerido": prestamo_sugerido,
                "num_creditos_activos": num_creditos,
                "acciones_necesarias": acciones,
            })
        
        total_pages = (total + per_page - 1) // per_page if total else 0
        
        return {
            "sugerencias": sugerencias,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "resumen": {
                "total_pagos_sin_prestamo": total,
                "can_auto_asignar": sum(1 for s in sugerencias if s["acciones_necesarias"] == "auto"),
                "requieren_manual": sum(1 for s in sugerencias if s["acciones_necesarias"] == "manual"),
            }
        }
    
    except Exception as e:
        logger.exception("Error en GET /pagos/sin-prestamo/sugerir: %s", e)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/sin-prestamo/asignar-automatico", response_model=dict)
def asignar_automaticamente_prestamos(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Auto-asigna prestamo_id a pagos que:
    1. Tienen prestamo_id = NULL
    2. El cliente tiene EXACTAMENTE 1 crédito activo (APROBADO)
    
    Retorna cantidad de pagos actualizados y detalles.
    """
    try:
        # Obtener todos los pagos sin prestamo_id
        pagos_sin_prestamo = db.execute(
            select(Pago).where(Pago.prestamo_id.is_(None))
        ).scalars().all()
        
        asignados = []
        no_asignables = []
        
        for pago in pagos_sin_prestamo:
            cedula_norm = pago.cedula_cliente.strip().upper() if pago.cedula_cliente else ""
            
            if not cedula_norm:
                no_asignables.append({
                    "pago_id": pago.id,
                    "razon": "Cédula vacía"
                })
                continue
            
            # Buscar créditos activos
            prestamos_activos = db.execute(
                select(Prestamo.id)
                .select_from(Prestamo)
                .join(Cliente, Prestamo.cliente_id == Cliente.id)
                .where(
                    Cliente.cedula == cedula_norm,
                    Prestamo.estado == "APROBADO",
                )
                .order_by(Prestamo.id)
            ).scalars().all()
            
            if len(prestamos_activos) == 1:
                # Auto-asignar
                pago.prestamo_id = prestamos_activos[0]
                db.add(pago)
                asignados.append({
                    "pago_id": pago.id,
                    "cedula_cliente": pago.cedula_cliente,
                    "prestamo_id_asignado": prestamos_activos[0],
                })
            else:
                no_asignables.append({
                    "pago_id": pago.id,
                    "cedula_cliente": pago.cedula_cliente,
                    "razon": f"Cliente tiene {len(prestamos_activos)} créditos activos (requiere intervención manual)" if len(prestamos_activos) > 1 else "Cliente sin créditos activos"
                })
        
        # Commit
        db.commit()
        
        logger.info(
            "Auto-asignación de prestamos: %d asignados, %d no asignables",
            len(asignados),
            len(no_asignables)
        )
        
        return {
            "asignados": len(asignados),
            "no_asignables": len(no_asignables),
            "detalles_asignados": asignados[:50],  # Limitar a 50 para la respuesta
            "detalles_no_asignables": no_asignables[:50],
            "mensaje": f"Se asignaron {len(asignados)} pagos automáticamente. {len(no_asignables)} requieren intervención manual.",
        }
    
    except Exception as e:
        logger.exception("Error en POST /pagos/sin-prestamo/asignar-automatico: %s", e)
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

    # Cédulas únicas ordenadas por su pago más reciente. El listado previo hacía un
    # N+1 severo: 1 query para la página y luego 3 queries por cada cédula.
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

    cedulas_list = list(
        db.execute(
            select(subq.c.cedula_cliente)
            .order_by(subq.c.max_fecha.desc(), subq.c.max_id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).scalars().all()
    )
    if not cedulas_list:
        return {
            "items": [],
            "total": total_cedulas,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    # Último pago por cédula de la página en una sola consulta.
    ultimos_subq = (
        select(
            Pago.id.label("pago_id"),
            Pago.cedula_cliente.label("cedula_cliente"),
            func.row_number()
            .over(
                partition_by=Pago.cedula_cliente,
                order_by=(Pago.id.desc(),),
            )
            .label("rn"),
        )
        .where(Pago.cedula_cliente.in_(cedulas_list))
        .subquery()
    )
    ultimos_rows = db.execute(
        select(Pago)
        .join(ultimos_subq, ultimos_subq.c.pago_id == Pago.id)
        .where(ultimos_subq.c.rn == 1)
    ).scalars().all()
    ultimo_por_cedula = {
        str(p.cedula_cliente): p
        for p in ultimos_rows
        if getattr(p, "cedula_cliente", None)
    }

    # Todos los préstamos asociados a las cédulas de la página.
    prestamo_rows = db.execute(
        select(Cliente.cedula, Prestamo.id)
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Cliente.cedula.in_(cedulas_list))
        .order_by(Cliente.cedula, Prestamo.id)
    ).all()
    prestamo_ids_por_cedula: dict[str, list[int]] = {}
    all_prestamo_ids: list[int] = []
    for cedula_row, prestamo_id_row in prestamo_rows:
        if cedula_row is None or prestamo_id_row is None:
            continue
        key = str(cedula_row)
        prestamo_ids_por_cedula.setdefault(key, []).append(int(prestamo_id_row))
        all_prestamo_ids.append(int(prestamo_id_row))

    # Mora agregada por préstamo para todas las cédulas de la página.
    mora_por_prestamo: dict[int, tuple[int, float]] = {}
    if all_prestamo_ids:
        mora_rows = db.execute(
            select(
                Cuota.prestamo_id,
                func.count().label("cuotas_atrasadas"),
                func.coalesce(func.sum(Cuota.monto), 0).label("saldo_vencido"),
            )
            .select_from(Cuota)
            .where(
                Cuota.prestamo_id.in_(all_prestamo_ids),
                Cuota.fecha_pago.is_(None),
                Cuota.fecha_vencimiento < hoy,
            )
            .group_by(Cuota.prestamo_id)
        ).all()
        mora_por_prestamo = {
            int(prestamo_id_row): (
                int(cuotas_atrasadas or 0),
                _safe_float(saldo_vencido),
            )
            for prestamo_id_row, cuotas_atrasadas, saldo_vencido in mora_rows
            if prestamo_id_row is not None
        }

    estado_filtrado = (estado or "").strip().upper()
    items = []
    for ced in cedulas_list:
        ultimo = ultimo_por_cedula.get(str(ced))
        if not ultimo:
            continue
        if estado_filtrado and (ultimo.estado or "").upper() != estado_filtrado:
            continue

        prestamo_ids = prestamo_ids_por_cedula.get(str(ced), [])
        cuotas_atrasadas = 0
        saldo_vencido = 0.0
        for prestamo_id in prestamo_ids:
            mora = mora_por_prestamo.get(prestamo_id)
            if not mora:
                continue
            cuotas_atrasadas += int(mora[0] or 0)
            saldo_vencido += float(mora[1] or 0)

        items.append(
            {
                "cedula": ced,
                "pago_id": ultimo.id,
                "prestamo_id": ultimo.prestamo_id,
                "estado_pago": ultimo.estado or "PENDIENTE",
                "monto_ultimo_pago": _safe_float(ultimo.monto_pagado),
                "fecha_ultimo_pago": (
                    ultimo.fecha_pago.date().isoformat()
                    if hasattr(ultimo.fecha_pago, "date") and ultimo.fecha_pago
                    else (
                        ultimo.fecha_pago.isoformat()[:10]
                        if ultimo.fecha_pago
                        else None
                    )
                ),
                "cuotas_atrasadas": cuotas_atrasadas,
                "saldo_vencido": round(saldo_vencido, 2),
                "total_prestamos": len(prestamo_ids),
            }
        )

    return {
        "items": items,
        "total": total_cedulas,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }





@router.get("/conflicto-documento-cartera", response_model=dict)


def get_conflicto_documento_cartera(
    numero_documento: str = Query(..., min_length=1),

    exclude_pago_id: Optional[int] = Query(None),

    exclude_pago_con_error_id: Optional[int] = Query(None),

    prestamo_id: Optional[int] = Query(None),

    fecha_pago: Optional[str] = Query(
        None, description="YYYY-MM-DD; con prestamo y monto activa chequeo de huella funcional"
    ),

    monto_pagado: Optional[float] = Query(None),

    referencia_pago: Optional[str] = Query(None),

    cedula_cliente: Optional[str] = Query(
        None,
        description="Cédula del formulario; con préstamo permite adoptar pago huérfano en cartera",
    ),

    db: Session = Depends(get_db),

    current_user: UserResponse = Depends(get_current_user),

):

    """

    Conflicto de serial en cartera: mismo Nº documento (pagos o pagos_con_errores) y,
    si se envían prestamo_id + fecha_pago + monto_pagado, huella funcional en `pagos`.

    """

    from app.services.pago_huella_funcional import conflicto_serial_para_formulario

    fecha_date = None
    if fecha_pago and fecha_pago.strip():
        try:
            fecha_date = date.fromisoformat(fecha_pago.strip()[:10])
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="fecha_pago debe ser YYYY-MM-DD.",
            ) from None

    return conflicto_serial_para_formulario(
        db,
        numero_documento=numero_documento,
        prestamo_id=prestamo_id,
        cedula_cliente=cedula_cliente,
        fecha_pago=fecha_date,
        monto_pagado=monto_pagado,
        referencia_pago=referencia_pago,
        exclude_pago_id=exclude_pago_id,
        exclude_pago_con_error_id=exclude_pago_con_error_id,
    )





