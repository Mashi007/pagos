"""Pagos API: kpis."""
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

        n_prestamos_huella_dup = contar_prestamos_con_huella_funcional_duplicada(db)

        calidad_huella = {

            **snapshot_rechazos_huella_funcional(),

            "prestamos_con_alerta_control_huella_funcional_duplicada": n_prestamos_huella_dup,

            "codigo_control_auditoria": "pagos_huella_funcional_duplicada",

            "nota": (

                "rechazos_409_* cuenta rechazos API desde el ultimo arranque del proceso; "

                "prestamos_con_alerta_* es conteo en tiempo real en BD (misma regla que auditoria cartera)."

            ),

        }

        return {

            "montoACobrarMes": _safe_float(monto_a_cobrar_mes),

            "montoCobradoMes": _safe_float(monto_cobrado_mes),

            "morosidadMensualPorcentaje": round(morosidad_porcentaje, 2),

            "mes": mes_resp,

            "anio": anio_resp,

            "saldoPorCobrar": _safe_float(cartera_pendiente),

            "clientesEnMora": clientes_en_mora,

            "clientesAlDia": clientes_al_dia,

            "calidad_carga_pagos_huella": calidad_huella,

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

            "saldoPorCobrar": 0.0,

            "clientesEnMora": 0,

            "clientesAlDia": 0,

            "calidad_carga_pagos_huella": {

                **snapshot_rechazos_huella_funcional(),

                "prestamos_con_alerta_control_huella_funcional_duplicada": None,

                "codigo_control_auditoria": "pagos_huella_funcional_duplicada",

                "nota": "KPI principal no disponible por error; conteo BD omitido en este fallback.",

            },

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





