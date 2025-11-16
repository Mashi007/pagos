"""
Endpoints para el módulo de Pagos
"""

import logging
import time
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query  # type: ignore[import-untyped]
from fastapi.responses import StreamingResponse  # type: ignore[import-untyped]
from openpyxl import Workbook  # type: ignore[import-untyped]
from openpyxl.styles import Alignment, Font, PatternFill  # type: ignore[import-untyped]
from sqlalchemy import func, or_, text  # type: ignore[import-untyped]
from sqlalchemy.orm import Session  # type: ignore[import-untyped]

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_result
from app.core.config import settings
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.pago import Pago  # Tabla oficial de pagos
from app.models.pago_auditoria import PagoAuditoria
from app.models.prestamo import Prestamo
from app.models.user import User
from app.schemas.pago import PagoCreate, PagoResponse, PagoUpdate
from app.utils.filtros_dashboard import FiltrosDashboard

router = APIRouter()
logger = logging.getLogger(__name__)


def _aplicar_filtros_pagos(
    query,
    cedula: Optional[str],
    estado: Optional[str],
    fecha_desde: Optional[date],
    fecha_hasta: Optional[date],
    analista: Optional[str],
    db: Session,
):
    """Aplica filtros a la query de pagos (usa tabla pagos)"""
    if cedula:
        query = query.filter(Pago.cedula == cedula)
        logger.info(f"🔍 [listar_pagos] Filtro cédula: {cedula}")
    if estado:
        query = query.filter(Pago.estado == estado)
        logger.info(f"🔍 [listar_pagos] Filtro estado: {estado}")
    if fecha_desde:
        query = query.filter(Pago.fecha_pago >= datetime.combine(fecha_desde, datetime.min.time()))
        logger.info(f"🔍 [listar_pagos] Filtro fecha_desde: {fecha_desde}")
    if fecha_hasta:
        query = query.filter(Pago.fecha_pago <= datetime.combine(fecha_hasta, time.max))
        logger.info(f"🔍 [listar_pagos] Filtro fecha_hasta: {fecha_hasta}")
    if analista:
        query = query.join(Prestamo, Pago.prestamo_id == Prestamo.id).filter(Prestamo.usuario_proponente == analista)
        logger.info(f"🔍 [listar_pagos] Filtro analista: {analista}")
    return query


def _calcular_cuotas_atrasadas(db: Session, cedula_cliente: Optional[str], hoy: date) -> int:
    """Calcula cuotas atrasadas para un cliente (versión individual - para compatibilidad)"""
    if not cedula_cliente:
        return 0

    # OPTIMIZACIÓN: Calcular en una sola query optimizada
    cuotas_atrasadas = (
        db.query(func.count(Cuota.id))
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Prestamo.cedula == cedula_cliente,
            Prestamo.estado == "APROBADO",
            Cuota.fecha_vencimiento < hoy,
            Cuota.total_pagado < Cuota.monto_cuota,
        )
        .scalar()
        or 0
    )

    return cuotas_atrasadas


def _calcular_cuotas_atrasadas_batch(db: Session, cedulas: list[str], hoy: date) -> dict[str, int]:
    """
    OPTIMIZACIÓN: Calcula cuotas atrasadas para múltiples clientes en una sola query.
    Reduce N+1 queries a 1 query batch.

    Args:
        db: Sesión de base de datos
        cedulas: Lista de cédulas de clientes
        hoy: Fecha de referencia

    Returns:
        Dict con cédula -> número de cuotas atrasadas
    """
    if not cedulas:
        return {}

    # OPTIMIZACIÓN: Una sola query para todos los clientes
    resultados = (
        db.query(Prestamo.cedula, func.count(Cuota.id))
        .join(Cuota, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Prestamo.cedula.in_(cedulas),
            Prestamo.estado == "APROBADO",
            Cuota.fecha_vencimiento < hoy,
            Cuota.total_pagado < Cuota.monto_cuota,
        )
        .group_by(Prestamo.cedula)
        .all()
    )

    # Construir diccionario con resultados (default 0 si no hay cuotas atrasadas)
    cuotas_por_cedula = {cedula: 0 for cedula in cedulas}
    for cedula, count in resultados:
        cuotas_por_cedula[cedula] = count

    logger.debug(
        f"📊 [batch] Calculadas cuotas atrasadas para {len(cedulas)} clientes " f"({len(resultados)} con cuotas atrasadas)"
    )

    return cuotas_por_cedula


def _convertir_fecha_pago(fecha_pago: Any) -> Optional[datetime]:
    """Convierte fecha_pago a datetime si es necesario"""
    if fecha_pago is None:
        return None

    if isinstance(fecha_pago, str):
        try:
            return datetime.fromisoformat(fecha_pago.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            try:
                return datetime.strptime(fecha_pago[:19], "%Y-%m-%d %H:%M:%S")
            except (ValueError, IndexError):
                return datetime.combine(date.fromisoformat(fecha_pago[:10]), time.min)

    if isinstance(fecha_pago, date) and not isinstance(fecha_pago, datetime):
        return datetime.combine(fecha_pago, time.min)

    return fecha_pago


def _convertir_monto_pagado(monto: Any, pago_id: Any) -> Decimal:
    """Convierte monto_pagado de string a Decimal"""
    if not monto:
        return Decimal("0.00")

    try:
        monto_str = str(monto).strip()
        if monto_str and monto_str != "":
            return Decimal(monto_str)
    except (ValueError, TypeError):
        logger.warning(f"⚠️ [serializar_pago] No se pudo convertir monto_pagado '{monto}' a Decimal para pago {pago_id}")
    return Decimal("0.00")


def _obtener_cuotas_atrasadas(cedula_cliente: str, cuotas_atrasadas_cache: Optional[dict[str, int]], pago_id: Any) -> int:
    """Obtiene cuotas atrasadas del cache"""
    if cuotas_atrasadas_cache is not None:
        return cuotas_atrasadas_cache.get(cedula_cliente, 0)
    logger.warning(f"⚠️ [serializar_pago] No se proporcionó cache de cuotas atrasadas para pago {pago_id}")
    return 0


def _serializar_pago(pago, _hoy: date, cuotas_atrasadas_cache: Optional[dict[str, int]] = None):
    """
    Serializa un pago de forma segura.

    Serializa un pago de la tabla pagos.
    Maneja conversión de tipos de datos.

    OPTIMIZACIÓN: Recibe cache de cuotas_atrasadas para evitar N+1 queries.
    Si no se proporciona cache, asume 0 (no se calcula individualmente para mejor performance).
    """
    try:
        fecha_pago_dt = None
        if hasattr(pago, "fecha_pago") and pago.fecha_pago is not None:
            fecha_pago_dt = _convertir_fecha_pago(pago.fecha_pago)

        monto_pagado_decimal = Decimal("0.00")
        if hasattr(pago, "monto_pagado") and pago.monto_pagado:
            monto_pagado_decimal = _convertir_monto_pagado(pago.monto_pagado, pago.id)

        cedula_cliente = getattr(pago, "cedula", "")  # Unificado: ahora usa 'cedula' en lugar de 'cedula_cliente'
        cuotas_atrasadas = _obtener_cuotas_atrasadas(cedula_cliente, cuotas_atrasadas_cache, pago.id)

        # Obtener valores de conciliación del pago (si existen)
        conciliado = getattr(pago, "conciliado", False)
        if conciliado is None:
            conciliado = False
        fecha_conciliacion = getattr(pago, "fecha_conciliacion", None)

        pago_dict = {
            "id": pago.id,
            "cedula_cliente": cedula_cliente,
            "prestamo_id": getattr(pago, "prestamo_id", None),
            "fecha_pago": fecha_pago_dt,
            "monto_pagado": float(monto_pagado_decimal),
            "numero_documento": getattr(pago, "numero_documento", ""),
            "institucion_bancaria": getattr(pago, "institucion_bancaria", None),
            "notas": getattr(pago, "notas", None),
            "fecha_registro": getattr(pago, "fecha_registro", None),
            "estado": getattr(pago, "estado", "PAGADO"),
            "conciliado": conciliado,
            "fecha_conciliacion": fecha_conciliacion,
            "documento_nombre": getattr(pago, "documento_nombre", None),
            "documento_tipo": getattr(pago, "documento_tipo", None),
            "documento_ruta": getattr(pago, "documento_ruta", None),
            "usuario_registro": getattr(pago, "usuario_registro", "SISTEMA"),
            "activo": getattr(pago, "activo", True),
            "fecha_actualizacion": getattr(pago, "fecha_actualizacion", None),
            "verificado_concordancia": getattr(pago, "verificado_concordancia", None),
            "cuotas_atrasadas": cuotas_atrasadas,
        }

        return pago_dict
    except Exception as e:
        error_detail = str(e)
        logger.error(
            f"❌ [listar_pagos] Error serializando pago ID {getattr(pago, 'id', 'N/A')}: {error_detail}",
            exc_info=True,
        )
        cedula_cliente = getattr(pago, "cedula", None)  # Unificado: ahora usa 'cedula'
        logger.error(f"   Datos del pago: cedula={cedula_cliente}")
        logger.error(f"   fecha_pago={getattr(pago, 'fecha_pago', 'N/A')} (tipo: {type(getattr(pago, 'fecha_pago', None))})")
        logger.error(
            f"   monto_pagado={getattr(pago, 'monto_pagado', 'N/A')} (tipo: {type(getattr(pago, 'monto_pagado', None))})"
        )
        raise


@router.get("/health")
def healthcheck_pagos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verificación rápida del módulo de Pagos y conexión a BD.

    Retorna métricas mínimas que confirman conectividad a la base de datos
    y disponibilidad de datos para alimentar el dashboard.
    """
    try:
        # Verificar conexión a BD con prueba de consulta (usa tabla pagos)
        total_pagos = db.query(func.count(Pago.id)).filter(Pago.activo.is_(True)).scalar() or 0

        # Pagos del mes actual
        hoy = date.today()
        primer_dia_mes = date(hoy.year, hoy.month, 1)
        pagos_mes = (
            db.query(func.count(Pago.id))
            .filter(Pago.activo.is_(True), Pago.fecha_pago >= datetime.combine(primer_dia_mes, datetime.min.time()))
            .scalar()
            or 0
        )

        # Monto total pagado
        monto_total_query = db.query(func.sum(Pago.monto_pagado)).filter(Pago.activo.is_(True), Pago.monto_pagado.isnot(None))
        monto_total = Decimal(str(monto_total_query.scalar() or 0))

        # Pagos por estado
        pagos_por_estado = db.query(Pago.estado, func.count(Pago.id)).filter(Pago.activo.is_(True)).group_by(Pago.estado).all()
        estados_dict = {estado: count for estado, count in pagos_por_estado}

        return {
            "status": "ok",
            "database": True,
            "metrics": {
                "total_pagos": int(total_pagos),
                "pagos_mes_actual": int(pagos_mes),
                "monto_total_pagado": float(monto_total),
                "pagos_por_estado": estados_dict,
            },
            "fecha_consulta": hoy.isoformat(),
        }
    except Exception as e:
        logger.error(f"Healthcheck pagos error: {e}")
        return {
            "status": "error",
            "database": False,
            "error": str(e),
            "mensaje": "❌ Error de conexión o consulta a la base de datos",
        }


def _verificar_conexion_basica(db: Session, diagnostico: dict):
    """Verifica la conexión básica a la base de datos"""
    logger.info("🔍 [diagnostico_pagos] Verificando conexión básica...")
    try:
        db.execute(text("SELECT 1"))
        diagnostico["verificaciones"]["conexion_basica"] = {
            "status": "ok",
            "mensaje": "Conexión a BD establecida correctamente",
        }
    except Exception as e:
        diagnostico["verificaciones"]["conexion_basica"] = {"status": "error", "mensaje": f"Error de conexión: {str(e)}"}
        diagnostico["errores"].append(f"Conexión básica falló: {str(e)}")
        diagnostico["estado"] = "error"
        logger.error(f"❌ [diagnostico_pagos] Error conexión básica: {e}", exc_info=True)


def _verificar_tabla(db: Session, nombre: str, modelo, diagnostico: dict, es_warning: bool = False):
    """Verifica acceso a una tabla específica"""
    logger.info(f"🔍 [diagnostico_pagos] Verificando tabla {nombre}...")
    try:
        total = db.query(func.count(modelo.id)).scalar()
        diagnostico["verificaciones"][f"tabla_{nombre}"] = {
            "status": "ok",
            "total_registros": total,
            "mensaje": f"Tabla '{nombre}' accesible con {total} registros",
        }
    except Exception as e:
        estado = "warning" if es_warning else "error"
        diagnostico["verificaciones"][f"tabla_{nombre}"] = {
            "status": "error",
            "mensaje": f"Error accediendo tabla {nombre}: {str(e)}",
        }
        diagnostico["errores"].append(f"Tabla {nombre} inaccesible: {str(e)}")
        diagnostico["estado"] = estado
        nivel_log = logger.warning if es_warning else logger.error
        nivel_log(f"⚠️ [diagnostico_pagos] Error tabla {nombre}: {e}", exc_info=True)


def _verificar_query_compleja(db: Session, diagnostico: dict):
    """Verifica query compleja similar a listar_pagos"""
    logger.info("🔍 [diagnostico_pagos] Verificando query compleja (listar_pagos)...")
    try:
        hoy = date.today()
        # Usar tabla pagos
        query_test = db.query(Pago).filter(Pago.activo.is_(True)).order_by(Pago.id.desc()).limit(5)
        pagos_test = query_test.all()

        if not pagos_test:
            diagnostico["verificaciones"]["query_compleja"] = {
                "status": "warning",
                "mensaje": "Query compleja exitosa pero no hay pagos en BD para probar",
            }
            return

        primer_pago = pagos_test[0]
        if not primer_pago.cedula:  # Unificado: ahora usa 'cedula'
            diagnostico["verificaciones"]["query_compleja"] = {
                "status": "ok",
                "mensaje": f"Query compleja exitosa - {len(pagos_test)} pagos obtenidos, primer pago sin cédula",
            }
            return

        prestamos_ids = [
            p.id
            for p in db.query(Prestamo.id)
            .filter(
                Prestamo.cedula == primer_pago.cedula,  # Unificado: ahora usa 'cedula'
                Prestamo.estado == "APROBADO",
            )
            .all()
        ]

        if not prestamos_ids:
            diagnostico["verificaciones"]["query_compleja"] = {
                "status": "ok",
                "mensaje": f"Query compleja exitosa - {len(pagos_test)} pagos obtenidos, sin préstamos APROBADOS para prueba",
            }
            return

        cuotas_atrasadas_query = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.id.in_(prestamos_ids),
                Prestamo.estado == "APROBADO",
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
            )
        )
        cuotas_atrasadas = cuotas_atrasadas_query.scalar() or 0

        diagnostico["verificaciones"]["query_compleja"] = {
            "status": "ok",
            "mensaje": f"Query compleja exitosa - {len(pagos_test)} pagos obtenidos, cálculo de cuotas atrasadas OK",
            "ejemplo": {
                "pago_id": primer_pago.id,
                "cedula": primer_pago.cedula,  # Unificado: ahora usa 'cedula'
                "prestamos_encontrados": len(prestamos_ids),
                "cuotas_atrasadas": cuotas_atrasadas,
            },
        }

    except Exception as e:
        diagnostico["verificaciones"]["query_compleja"] = {
            "status": "error",
            "mensaje": f"Error en query compleja: {str(e)}",
        }
        diagnostico["errores"].append(f"Query compleja falló: {str(e)}")
        diagnostico["estado"] = "error"
        logger.error(f"❌ [diagnostico_pagos] Error query compleja: {e}", exc_info=True)


def _verificar_serializacion(db: Session, diagnostico: dict):
    """Verifica serialización de PagoResponse"""
    logger.info("🔍 [diagnostico_pagos] Verificando serialización...")
    try:
        # Usar tabla pagos
        query_test = db.query(Pago).filter(Pago.activo.is_(True)).order_by(Pago.fecha_registro.desc()).limit(1)
        pagos_test = query_test.all()

        if not pagos_test:
            diagnostico["verificaciones"]["serializacion"] = {
                "status": "warning",
                "mensaje": "No hay pagos para probar serialización",
            }
            return

        primer_pago = pagos_test[0]
        pago_dict = PagoResponse.model_validate(primer_pago).model_dump()
        diagnostico["verificaciones"]["serializacion"] = {
            "status": "ok",
            "mensaje": "Serialización de PagoResponse exitosa",
            "campos_serializados": len(pago_dict),
        }

    except Exception as e:
        diagnostico["verificaciones"]["serializacion"] = {
            "status": "error",
            "mensaje": f"Error en serialización: {str(e)}",
        }
        diagnostico["errores"].append(f"Serialización falló: {str(e)}")
        diagnostico["estado"] = "error"
        logger.error(f"❌ [diagnostico_pagos] Error serialización: {e}", exc_info=True)


@router.get("/diagnostico")
def diagnostico_pagos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Diagnóstico detallado del módulo de Pagos para identificar problemas de conexión.
    """
    diagnostico = {"timestamp": datetime.now().isoformat(), "verificaciones": {}, "errores": [], "estado": "ok"}

    try:
        _verificar_conexion_basica(db, diagnostico)
        _verificar_tabla(db, "pagos", Pago, diagnostico)
        _verificar_tabla(db, "prestamos", Prestamo, diagnostico, es_warning=True)
        _verificar_tabla(db, "cuotas", Cuota, diagnostico, es_warning=True)
        _verificar_query_compleja(db, diagnostico)
        _verificar_serializacion(db, diagnostico)

    except Exception as e:
        logger.error(f"❌ [diagnostico_pagos] Error general: {e}", exc_info=True)
        diagnostico["estado"] = "error"
        diagnostico["errores"].append(f"Error general: {str(e)}")

    logger.info(f"✅ [diagnostico_pagos] Diagnóstico completado - Estado: {diagnostico['estado']}")

    return diagnostico


def _contar_total_pagos_validos(db: Session, cedula: Optional[str] = None) -> int:
    """Cuenta el total de pagos válidos en tabla pagos"""
    query = db.query(func.count(Pago.id)).filter(Pago.activo.is_(True))

    if cedula:
        query = query.filter(Pago.cedula == cedula)

    return query.scalar() or 0


def _obtener_pagos_paginados(db: Session, page: int, per_page: int) -> list:
    """Obtiene pagos paginados de la tabla pagos"""
    offset = (page - 1) * per_page
    pagos = db.query(Pago).filter(Pago.activo.is_(True)).order_by(Pago.id.desc()).offset(offset).limit(per_page).all()
    return pagos


def _serializar_pagos_con_cache(pagos: list, db: Session, hoy: date) -> list:
    """Serializa una lista de pagos usando cache de cuotas atrasadas"""
    cedulas_unicas = list(set(p.cedula for p in pagos if p.cedula))  # Unificado: ahora usa 'cedula'
    cuotas_atrasadas_cache = _calcular_cuotas_atrasadas_batch(db, cedulas_unicas, hoy)

    pagos_serializados = []
    for pago in pagos:
        try:
            pago_dict = _serializar_pago(pago, hoy, cuotas_atrasadas_cache)
            if pago_dict:
                pagos_serializados.append(pago_dict)
        except Exception:
            continue
    return pagos_serializados


@router.get("/", response_model=dict)
def listar_pagos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cedula: Optional[str] = None,
    estado: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    analista: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar pagos con filtros y paginación
    """
    try:
        logger.info(f"📋 [listar_pagos] Iniciando consulta - página {page}, por página {per_page}")

        try:
            # Verificar que la tabla existe antes de consultarla
            from sqlalchemy import inspect

            inspector = inspect(db.bind)
            tablas_disponibles = inspector.get_table_names()

            if "pagos" not in tablas_disponibles:
                # Obtener nombre de BD actual para diagnóstico
                try:
                    resultado = db.execute(text("SELECT current_database()"))
                    bd_nombre = resultado.scalar()
                except Exception:
                    bd_nombre = "No se pudo determinar"

                logger.error(
                    f"❌ [listar_pagos] Tabla 'pagos' NO EXISTE en BD '{bd_nombre}'. "
                    f"Tablas disponibles: {', '.join(tablas_disponibles[:10])}"
                )
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Error: La tabla 'pagos' no existe en la base de datos '{bd_nombre}'. "
                        f"Verifique que está conectado a la base de datos 'pagos' y que las migraciones se han ejecutado."
                    ),
                )

            test_query = db.query(func.count(Pago.id)).scalar()
            logger.info(f"✅ [listar_pagos] Conexión BD OK. Total pagos en tabla pagos: {test_query}")
        except HTTPException:
            # Re-lanzar HTTPException sin modificar
            raise
        except Exception as db_error:
            logger.error(f"❌ [listar_pagos] Error de conexión BD: {db_error}", exc_info=True)

            # Verificar si es un error de tabla no encontrada
            error_str = str(db_error)
            if "does not exist" in error_str or "UndefinedTable" in error_str:
                try:
                    resultado = db.execute(text("SELECT current_database()"))
                    bd_nombre = resultado.scalar()
                except Exception:
                    bd_nombre = "No se pudo determinar"

                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Error: La tabla 'pagos' no existe en la base de datos '{bd_nombre}'. "
                        f"Verifique que está conectado a la base de datos 'pagos' y que las migraciones se han ejecutado."
                    ),
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error de conexión a la base de datos: {str(db_error)}",
                )

        total = _contar_total_pagos_validos(db, cedula)
        logger.debug(f"📊 [listar_pagos] Total pagos encontrados (sin paginación): {total}")

        pagos = _obtener_pagos_paginados(db, page, per_page)
        logger.info(f"📄 [listar_pagos] Pagos obtenidos de BD: {len(pagos)}")

        hoy = date.today()
        pagos_serializados = _serializar_pagos_con_cache(pagos, db, hoy)
        logger.info(f"✅ [listar_pagos] Serializados exitosamente: {len(pagos_serializados)} pagos")

        return {
            "pagos": pagos_serializados,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ [listar_pagos] Error general: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {error_msg}")


@router.post("/", response_model=PagoResponse)
def crear_pago(
    pago_data: PagoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Registrar un nuevo pago
    """
    try:
        # Verificar que el cliente existe
        cliente = db.query(Cliente).filter(Cliente.cedula == pago_data.cedula).first()  # Unificado: ahora usa 'cedula'
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # ✅ BUSCAR PRÉSTAMO AUTOMÁTICAMENTE si no viene en el request
        # Es obligatorio que el pago esté relacionado con un préstamo
        prestamo_id = pago_data.prestamo_id
        if not prestamo_id:
            prestamo = db.query(Prestamo).filter(Prestamo.cedula == pago_data.cedula, Prestamo.estado == "APROBADO").first()
            if prestamo:
                prestamo_id = prestamo.id
                logger.info(
                    f"✅ [crear_pago] Préstamo encontrado automáticamente para cédula {pago_data.cedula}: "
                    f"prestamo_id={prestamo_id}"
                )
            else:
                logger.warning(
                    f"⚠️ [crear_pago] No se encontró préstamo APROBADO para cédula {pago_data.cedula}. "
                    f"El pago se registrará sin prestamo_id y NO se aplicará a cuotas."
                )

        # Crear el pago
        pago_dict = pago_data.model_dump()
        pago_dict["usuario_registro"] = current_user.email
        pago_dict["fecha_registro"] = datetime.now()
        # ✅ Asignar prestamo_id (del request o encontrado automáticamente)
        if prestamo_id:
            pago_dict["prestamo_id"] = prestamo_id

        # Eliminar cualquier campo que no exista en el modelo
        # (por ejemplo, referencia_pago si la migración no se ha ejecutado)
        campos_validos = [col.key for col in Pago.__table__.columns]
        pago_dict = {k: v for k, v in pago_dict.items() if k in campos_validos}

        nuevo_pago = Pago(**pago_dict)
        db.add(nuevo_pago)
        db.commit()
        db.refresh(nuevo_pago)

        # Registrar auditoría
        registrar_auditoria_pago(
            pago_id=nuevo_pago.id,
            usuario=current_user.email,
            accion="CREATE",
            campo_modificado="pago_completo",
            valor_anterior="N/A",
            valor_nuevo=f"Pago de {pago_data.monto_pagado} registrado",
            db=db,
        )

        # ⚠️ NO APLICAR PAGO A CUOTAS AQUÍ
        # Los pagos solo se aplican a cuotas cuando están conciliados (conciliado = True o verificado_concordancia = 'SI')
        # La aplicación a cuotas se hará automáticamente cuando el pago se concilie
        logger.info(
            f"ℹ️ [crear_pago] Pago ID {nuevo_pago.id} registrado. "
            f"Se aplicará a cuotas cuando esté conciliado (conciliado=True o verificado_concordancia='SI')"
        )

        # ⚠️ NO ACTUALIZAR ESTADO DEL PAGO AQUÍ
        # El estado del pago (PARCIAL/PAGADO) solo se actualiza DESPUÉS de conciliar y aplicar a cuotas
        # Mantener el estado por defecto "REGISTRADO" o "PAGADO" según el modelo

        db.commit()
        db.refresh(nuevo_pago)

        return nuevo_pago
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en crear_pago: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.post("/{pago_id}/aplicar-cuotas", response_model=dict)
def aplicar_pago_manualmente(
    pago_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reaplicar un pago a las cuotas del préstamo asociado.
    ⚠️ IMPORTANTE: Solo se puede aplicar si el pago está conciliado (conciliado=True o verificado_concordancia='SI').
    Útil cuando un pago fue registrado pero no se aplicó correctamente a las cuotas.
    """
    try:
        pago = db.query(Pago).filter(Pago.id == pago_id).first()
        if not pago:
            raise HTTPException(status_code=404, detail="Pago no encontrado")

        if not pago.prestamo_id:
            raise HTTPException(
                status_code=400,
                detail="El pago no tiene un préstamo asociado (prestamo_id es NULL)",
            )

        # ✅ VERIFICAR QUE EL PAGO ESTÉ CONCILIADO
        if not pago.conciliado:
            verificado_ok = getattr(pago, "verificado_concordancia", None) == "SI"
            if not verificado_ok:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"El pago ID {pago_id} NO está conciliado "
                        f"(conciliado={pago.conciliado}, verificado_concordancia={getattr(pago, 'verificado_concordancia', 'N/A')}). "
                        f"El pago debe estar conciliado primero (conciliado=True o verificado_concordancia='SI') "
                        f"antes de poder aplicarse a cuotas."
                    ),
                )

        logger.info(f"🔄 [aplicar_pago_manualmente] Reaplicando pago ID {pago_id} " f"al préstamo {pago.prestamo_id}")

        # Reaplicar el pago a las cuotas (solo si está conciliado)
        cuotas_completadas = aplicar_pago_a_cuotas(pago, db, current_user)

        return {
            "success": True,
            "message": f"Pago aplicado exitosamente. {cuotas_completadas} cuota(s) completada(s)",
            "pago_id": pago_id,
            "prestamo_id": pago.prestamo_id,
            "cuotas_completadas": cuotas_completadas,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [aplicar_pago_manualmente] Error: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al aplicar pago a cuotas: {str(e)}")


@router.put("/{pago_id}", response_model=PagoResponse)
def actualizar_pago(
    pago_id: int,
    pago_data: PagoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Actualizar un pago existente
    """
    try:
        pago = db.query(Pago).filter(Pago.id == pago_id).first()
        if not pago:
            raise HTTPException(status_code=404, detail="Pago no encontrado")

        # Registrar cambios para auditoría
        update_data = pago_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(pago, field):
                old_value = getattr(pago, field)
                setattr(pago, field, value)
                registrar_auditoria_pago(
                    pago_id=pago_id,
                    usuario=current_user.email,
                    accion="UPDATE",
                    campo_modificado=field,
                    valor_anterior=str(old_value) if old_value else "N/A",
                    valor_nuevo=str(value) if value else "N/A",
                    db=db,
                )

        pago.fecha_actualizacion = datetime.now()  # type: ignore[assignment]
        db.commit()
        db.refresh(pago)

        return pago
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en actualizar_pago: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# ============================================
# NUEVO: Listado de últimos pagos por cédula
# ============================================
@router.get("/ultimos", response_model=dict)
def listar_ultimos_pagos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cedula: Optional[str] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el último pago por cédula y métricas agregadas del balance general."""
    try:
        # Subconsulta: última fecha_registro por cédula
        # Obtener últimos pagos por cédula usando fecha_registro (más reciente)
        sub_ultimos = (
            db.query(
                Pago.cedula.label("cedula"),
                func.max(Pago.fecha_registro).label("max_fecha_registro"),
            )
            .filter(Pago.cedula.isnot(None), Pago.activo.is_(True))
            .group_by(Pago.cedula)
            .subquery()
        )

        # Join para obtener el registro de pago completo de esa fecha más reciente
        pagos_ultimos_q = (
            db.query(Pago)
            .join(
                sub_ultimos,
                (Pago.cedula == sub_ultimos.c.cedula) & (Pago.fecha_registro == sub_ultimos.c.max_fecha_registro),
            )
            .filter(Pago.activo.is_(True))
        )

        # Filtros
        if cedula:
            pagos_ultimos_q = pagos_ultimos_q.filter(Pago.cedula == cedula)
        if estado:
            pagos_ultimos_q = pagos_ultimos_q.filter(Pago.estado == estado)

        # Total para paginación
        total = pagos_ultimos_q.count()

        # Paginación (ordenar por fecha_registro desc)
        offset = (page - 1) * per_page
        pagos_ultimos = pagos_ultimos_q.order_by(Pago.fecha_registro.desc()).offset(offset).limit(per_page).all()

        # Para cada cédula, calcular agregados sobre amortización (todas sus deudas)
        items = []
        from datetime import date
        from decimal import Decimal

        from app.models.amortizacion import Cuota
        from app.models.prestamo import Prestamo

        for pago in pagos_ultimos:
            # Usar cedula de la tabla pagos
            cedula_cliente = pago.cedula
            # ✅ Obtener TODOS los préstamos APROBADOS del cliente (no solo del último pago)
            prestamos_ids = [
                p.id
                for p in db.query(Prestamo.id)
                .filter(
                    Prestamo.cedula == cedula_cliente,
                    Prestamo.estado == "APROBADO",  # ✅ Solo préstamos activos
                )
                .all()
            ]

            total_prestamos = len(prestamos_ids)

            cuotas_atrasadas = 0
            saldo_vencido: Decimal = Decimal("0.00")
            if prestamos_ids:
                # ✅ IMPORTANTE: Contar TODAS las cuotas atrasadas de TODOS los préstamos activos del cliente
                # Reglas aplicadas:
                # 1. Pertenece a algún préstamo APROBADO del cliente
                # 2. fecha_vencimiento < hoy (vencida)
                # 3. total_pagado < monto_cuota (pago incompleto)
                # Esto incluye cuotas con estado ATRASADO, PARCIAL, PENDIENTE que estén vencidas e incompletas
                # NO solo las del último pago, sino TODAS las cuotas de la amortización de TODOS los préstamos
                # ✅ NO HAY VALORES HARDCODEADOS - Todo se calcula dinámicamente desde la BD
                hoy = date.today()
                cuotas_atrasadas_query = (
                    db.query(func.count(Cuota.id))
                    .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                    .filter(
                        Prestamo.id.in_(prestamos_ids),
                        Prestamo.estado == "APROBADO",  # ✅ Solo préstamos activos
                        Cuota.fecha_vencimiento < hoy,  # ✅ Vencida
                        Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Verificar que el pago NO esté completo
                    )
                )
                cuotas_atrasadas = cuotas_atrasadas_query.scalar() or 0

                # Logging detallado para verificación
                logger.info(
                    f"📊 [ultimos_pagos] Cliente {cedula_cliente}: "
                    f"{len(prestamos_ids)} préstamos APROBADOS, "
                    f"{cuotas_atrasadas} cuotas atrasadas "
                    f"(fecha_vencimiento < {hoy} AND total_pagado < monto_cuota) - "
                    f"TODAS las cuotas de TODOS los préstamos - CÁLCULO DINÁMICO DESDE BD ✅"
                )
                # Suma optimizada de saldos pendientes (capital+interes+mora) de todas las cuotas no pagadas
                # Usando func.sum para mejor performance
                saldo_result = (
                    db.query(
                        func.sum(
                            func.coalesce(Cuota.capital_pendiente, Decimal("0.00"))
                            + func.coalesce(Cuota.interes_pendiente, Decimal("0.00"))
                            + func.coalesce(Cuota.monto_mora, Decimal("0.00"))
                        )
                    )
                    .filter(
                        Cuota.prestamo_id.in_(prestamos_ids),
                        Cuota.estado != "PAGADO",
                    )
                    .scalar()
                )
                saldo_vencido = saldo_result if saldo_result else Decimal("0.00")

            # ✅ Si el pago no tiene prestamo_id, intentar obtener el primer préstamo aprobado del cliente
            prestamo_id_mostrar = pago.prestamo_id
            if not prestamo_id_mostrar and prestamos_ids:
                # Si el pago no tiene prestamo_id, usar el primer préstamo aprobado del cliente
                prestamo_id_mostrar = prestamos_ids[0]
                logger.info(
                    f"⚠️ [ultimos_pagos] Pago ID {pago.id} no tiene prestamo_id. "
                    f"Usando primer préstamo aprobado del cliente: {prestamo_id_mostrar}"
                )

            items.append(
                {
                    "cedula": cedula_cliente,
                    "pago_id": pago.id,
                    "prestamo_id": prestamo_id_mostrar,  # ✅ Usar prestamo_id del pago o del primer préstamo aprobado
                    "estado_pago": pago.estado,
                    "monto_ultimo_pago": float(pago.monto_pagado),
                    "fecha_ultimo_pago": (pago.fecha_pago.isoformat() if pago.fecha_pago else None),
                    "cuotas_atrasadas": int(cuotas_atrasadas),
                    "saldo_vencido": float(saldo_vencido),
                    "total_prestamos": int(total_prestamos),
                }
            )

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
        }
    except Exception as e:
        logger.error(f"Error en listar_ultimos_pagos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


def _calcular_proporcion_capital_interes(cuota, monto_aplicar: Decimal) -> tuple[Decimal, Decimal]:
    """Calcula la proporción de capital e interés a aplicar según lo pendiente"""
    total_pendiente = cuota.capital_pendiente + cuota.interes_pendiente
    if total_pendiente > Decimal("0.00"):
        capital = monto_aplicar * (cuota.capital_pendiente / total_pendiente)
        interes = monto_aplicar * (cuota.interes_pendiente / total_pendiente)
    else:
        capital = monto_aplicar
        interes = Decimal("0.00")
    return capital, interes


def _verificar_pagos_conciliados_cuota(db: Session, cuota_id: int, prestamo_id: int) -> bool:
    """
    Verifica si TODOS los pagos que afectan una cuota están conciliados.
    Busca en la tabla `pagos` por prestamo_id.

    ✅ ESTRATEGIA:
    - Obtener todos los pagos de la tabla `pagos` que tienen este prestamo_id
    - Verificar si cada uno está conciliado
    - Si TODOS están conciliados → True, sino → False

    Returns: True si todos los pagos están conciliados, False en caso contrario.
    """
    # Obtener todos los pagos del préstamo que podrían afectar esta cuota
    # Como los pagos se aplican desde la cuota más antigua, verificamos todos los pagos del préstamo
    pagos_prestamo = (
        db.query(Pago)
        .filter(Pago.prestamo_id == prestamo_id, Pago.numero_documento.isnot(None), Pago.numero_documento != "")
        .all()
    )

    if not pagos_prestamo:
        # No hay pagos para este préstamo, asumir que no está conciliado
        return False

    # Verificar si todos los pagos están conciliados
    for pago in pagos_prestamo:
        if not pago.conciliado:
            return False

    return True


def _actualizar_morosidad_cuota(cuota, fecha_hoy: date) -> None:
    """
    ✅ ACTUALIZA AUTOMÁTICAMENTE las columnas de morosidad:
    - dias_morosidad: Días de atraso (desde fecha_vencimiento hasta hoy o fecha_pago)
    - monto_morosidad: Monto pendiente (monto_cuota - total_pagado)

    Esta función se llama automáticamente cuando se actualiza una cuota.
    """
    from datetime import date as date_type

    # 1. Calcular dias_morosidad
    if cuota.fecha_vencimiento:
        if cuota.fecha_pago:
            # Si está pagada: calcular días entre fecha_pago y fecha_vencimiento (si fecha_pago > fecha_vencimiento)
            if cuota.fecha_pago > cuota.fecha_vencimiento:
                cuota.dias_morosidad = (cuota.fecha_pago - cuota.fecha_vencimiento).days  # type: ignore[assignment]
            else:
                # Pagada a tiempo o adelantada: 0 días de morosidad
                cuota.dias_morosidad = 0  # type: ignore[assignment]
        else:
            # Si no está pagada: calcular días desde fecha_vencimiento hasta hoy
            if cuota.fecha_vencimiento < fecha_hoy:
                cuota.dias_morosidad = (fecha_hoy - cuota.fecha_vencimiento).days  # type: ignore[assignment]
            else:
                # No vencida aún: 0 días de morosidad
                cuota.dias_morosidad = 0  # type: ignore[assignment]
    else:
        cuota.dias_morosidad = 0  # type: ignore[assignment]

    # 2. Calcular monto_morosidad (monto_cuota - total_pagado)
    monto_pendiente = cuota.monto_cuota - (cuota.total_pagado or Decimal("0.00"))
    cuota.monto_morosidad = max(Decimal("0.00"), monto_pendiente)  # type: ignore[assignment]

    logger.debug(
        f"📊 [actualizar_morosidad_cuota] Cuota #{cuota.numero_cuota} (Préstamo {cuota.prestamo_id}): "
        f"dias_morosidad={cuota.dias_morosidad}, monto_morosidad=${cuota.monto_morosidad}"
    )


def _actualizar_estado_cuota(cuota, fecha_hoy: date, db: Session = None, es_exceso: bool = False) -> bool:
    """
    Actualiza el estado de una cuota según las reglas de negocio.

    ✅ REGLAS ACTUALIZADAS CON CONCILIACIÓN:
    - PAGADO: total_pagado >= monto_cuota Y todos los pagos están conciliados
    - PENDIENTE: total_pagado >= monto_cuota PERO NO todos los pagos están conciliados
    - PENDIENTE: total_pagado > 0 pero < monto_cuota y fecha_vencimiento >= hoy
    - PARCIAL: total_pagado > 0 pero < monto_cuota y fecha_vencimiento < hoy (cuota atrasada)
    - ATRASADO: total_pagado = 0 y fecha_vencimiento < hoy
    - ADELANTADO: total_pagado > 0 pero < monto_cuota y fecha_vencimiento >= hoy (exceso de pago)

    Returns:
        bool: True si la cuota se completó completamente (pasó de incompleta a PAGADO)
    """
    estado_previo_completo = cuota.total_pagado >= cuota.monto_cuota
    estado_completado = False

    # Verificar si todos los pagos están conciliados
    todos_conciliados = False
    if db and cuota.total_pagado > Decimal("0.00"):
        todos_conciliados = _verificar_pagos_conciliados_cuota(db, cuota.id, cuota.prestamo_id)

    if cuota.total_pagado >= cuota.monto_cuota:
        # ✅ Cuota completa: PAGADO solo si está conciliado, sino PENDIENTE
        if todos_conciliados:
            cuota.estado = "PAGADO"  # type: ignore[assignment]
            if not estado_previo_completo:
                estado_completado = True
        else:
            # Pagada pero no conciliada → PENDIENTE
            cuota.estado = "PENDIENTE"  # type: ignore[assignment]
    elif cuota.total_pagado > Decimal("0.00"):
        # ✅ Pago parcial
        if cuota.fecha_vencimiento and cuota.fecha_vencimiento < fecha_hoy:
            # Cuota vencida con pago parcial → PARCIAL
            cuota.estado = "PARCIAL"  # type: ignore[assignment]
        else:
            # Cuota no vencida con pago parcial
            if es_exceso:
                cuota.estado = "ADELANTADO"  # type: ignore[assignment]
            else:
                cuota.estado = "PENDIENTE"  # type: ignore[assignment]
    else:
        # ✅ Sin pagos
        if cuota.fecha_vencimiento and cuota.fecha_vencimiento < fecha_hoy:
            cuota.estado = "ATRASADO"  # type: ignore[assignment]
        else:
            cuota.estado = "PENDIENTE"  # type: ignore[assignment]

    # ✅ ACTUALIZAR AUTOMÁTICAMENTE columnas de morosidad
    _actualizar_morosidad_cuota(cuota, fecha_hoy)

    return estado_completado


def _aplicar_monto_a_cuota(
    cuota,
    monto_aplicar: Decimal,
    fecha_pago: date,
    fecha_hoy: date,
    db: Session = None,
    es_exceso: bool = False,
) -> bool:
    """
    Aplica un monto a una cuota, actualizando todos los campos correspondientes.

    ✅ ACTUALIZADO: Calcula automáticamente mora si fecha_pago > fecha_vencimiento

    Returns:
        bool: True si la cuota se completó completamente con este pago
    """
    if monto_aplicar <= Decimal("0.00"):
        return False

    capital_aplicar, interes_aplicar = _calcular_proporcion_capital_interes(cuota, monto_aplicar)

    cuota.capital_pagado += capital_aplicar  # type: ignore[assignment]
    cuota.interes_pagado += interes_aplicar  # type: ignore[assignment]
    cuota.total_pagado += monto_aplicar  # type: ignore[assignment]
    cuota.capital_pendiente = max(Decimal("0.00"), cuota.capital_pendiente - capital_aplicar)  # type: ignore[assignment]
    cuota.interes_pendiente = max(Decimal("0.00"), cuota.interes_pendiente - interes_aplicar)  # type: ignore[assignment]

    if monto_aplicar > Decimal("0.00"):
        cuota.fecha_pago = fecha_pago  # type: ignore[assignment]

        # ✅ UNIFICAR EN FECHA DE PAGO: Si fecha_pago > fecha_vencimiento, calcular mora automáticamente
        if cuota.fecha_vencimiento and fecha_pago > cuota.fecha_vencimiento:
            # Calcular días de mora
            dias_mora = (fecha_pago - cuota.fecha_vencimiento).days

            # Obtener tasa de mora diaria (por defecto desde settings)
            tasa_mora_diaria = Decimal(str(settings.TASA_MORA_DIARIA))  # 0.067% diario (2% mensual / 30 días)

            # Calcular monto de mora sobre el saldo pendiente al momento del vencimiento
            # Usar monto_cuota como base (o saldo pendiente si se prefiere)
            saldo_base_mora = cuota.monto_cuota  # O usar: cuota.capital_pendiente + cuota.interes_pendiente

            # Fórmula: monto_mora = saldo_base * tasa_diaria * dias_mora / 100
            from decimal import ROUND_HALF_UP

            monto_mora = (saldo_base_mora * tasa_mora_diaria * Decimal(dias_mora) / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Actualizar campos de mora
            cuota.dias_mora = dias_mora
            cuota.monto_mora = monto_mora
            cuota.tasa_mora = tasa_mora_diaria

            logger.info(
                f"💰 [aplicar_monto_a_cuota] Cuota #{cuota.numero_cuota} (Préstamo {cuota.prestamo_id}): "
                f"Mora calculada: {dias_mora} días, ${monto_mora} "
                f"(fecha_pago: {fecha_pago}, fecha_vencimiento: {cuota.fecha_vencimiento})"
            )
        else:
            # Si pago a tiempo o adelantado, no hay mora
            if fecha_pago <= cuota.fecha_vencimiento:
                cuota.dias_mora = 0
                cuota.monto_mora = Decimal("0.00")
                cuota.tasa_mora = Decimal("0.00")

        # ✅ ACTUALIZAR AUTOMÁTICAMENTE columnas de morosidad después de aplicar pago
        _actualizar_morosidad_cuota(cuota, fecha_hoy)

    return _actualizar_estado_cuota(cuota, fecha_hoy, db, es_exceso)


def _aplicar_exceso_a_siguiente_cuota(
    db: Session, prestamo_id: int, saldo_restante: Decimal, fecha_pago: date, fecha_hoy: date
) -> int:
    """
    Aplica el exceso de pago a la siguiente cuota pendiente (más antigua primero).

    Returns:
        número de cuotas completadas
    """
    siguiente_cuota = (
        db.query(Cuota)
        .filter(
            Cuota.prestamo_id == prestamo_id,
            Cuota.estado != "PAGADO",
        )
        .order_by(Cuota.fecha_vencimiento, Cuota.numero_cuota)  # ✅ Más antigua primero por fecha_vencimiento
        .first()
    )

    if not siguiente_cuota:
        return 0

    monto_faltante = siguiente_cuota.monto_cuota - siguiente_cuota.total_pagado
    monto_aplicar_exceso = min(saldo_restante, monto_faltante)

    if monto_aplicar_exceso <= Decimal("0.00"):
        return 0

    estado_completado = _aplicar_monto_a_cuota(
        siguiente_cuota, monto_aplicar_exceso, fecha_pago, fecha_hoy, db, es_exceso=True
    )

    logger.debug(
        f"  💰 [aplicar_pago_a_cuotas] Cuota #{siguiente_cuota.numero_cuota} "
        f"(exceso): Aplicado ${monto_aplicar_exceso}, Estado: {siguiente_cuota.estado}"
    )

    return 1 if estado_completado else 0


def _verificar_prestamo_y_cedula(pago: Pago, db: Session) -> tuple[bool, Optional[Any]]:
    """Verifica que el préstamo existe y la cédula coincide"""
    from app.models.prestamo import Prestamo

    if not pago.prestamo_id:
        logger.warning(f"⚠️ [aplicar_pago_a_cuotas] Pago ID {pago.id} no tiene prestamo_id. No se aplicará a cuotas.")
        return False, None

    prestamo = db.query(Prestamo).filter(Prestamo.id == pago.prestamo_id).first()
    if not prestamo:
        logger.error(f"❌ [aplicar_pago_a_cuotas] Préstamo {pago.prestamo_id} no encontrado")
        return False, None

    if pago.cedula and prestamo.cedula and pago.cedula != prestamo.cedula:  # Unificado: ahora usa 'cedula'
        logger.error(
            f"❌ [aplicar_pago_a_cuotas] Cédula del pago ({pago.cedula}) "
            f"no coincide con cédula del préstamo ({prestamo.cedula}). No se aplicará el pago a las cuotas."
        )
        return False, None

    return True, prestamo


def _obtener_cuotas_pendientes(db: Session, prestamo_id: int) -> list:
    """Obtiene las cuotas pendientes del préstamo ordenadas por fecha de vencimiento"""
    cuotas = (
        db.query(Cuota)
        .filter(
            Cuota.prestamo_id == prestamo_id,
            Cuota.estado != "PAGADO",
        )
        .order_by(Cuota.fecha_vencimiento, Cuota.numero_cuota)
        .all()
    )
    return cuotas


def _aplicar_pago_a_cuotas_iterativas(
    cuotas: list, saldo_restante: Decimal, fecha_pago: date, fecha_hoy: date, db: Session
) -> tuple[int, Decimal]:
    """Aplica el pago a las cuotas iterativamente"""
    cuotas_completadas = 0

    for cuota in cuotas:
        if saldo_restante <= Decimal("0.00"):
            break

        monto_faltante = cuota.monto_cuota - cuota.total_pagado
        monto_aplicar = min(saldo_restante, monto_faltante)

        if monto_aplicar <= Decimal("0.00"):
            continue

        if _aplicar_monto_a_cuota(cuota, monto_aplicar, fecha_pago, fecha_hoy, db):
            cuotas_completadas += 1

        saldo_restante -= monto_aplicar
        logger.debug(
            f"  💰 [aplicar_pago_a_cuotas] Cuota #{cuota.numero_cuota}: "
            f"Aplicado ${monto_aplicar}, Saldo restante: ${saldo_restante}, Estado: {cuota.estado}"
        )

    return cuotas_completadas, saldo_restante


def aplicar_pago_a_cuotas(pago: Pago, db: Session, current_user: User) -> int:
    """
    Aplica un pago a las cuotas correspondientes según la regla de negocio:
    - ✅ VERIFICA que el pago esté conciliado (conciliado = True o verificado_concordancia = 'SI')
    - VERIFICA que la cédula del pago coincida con la cédula del préstamo
    - Los pagos se aplican a las cuotas más antiguas primero (por fecha_vencimiento)
    - Una cuota está "ATRASADO" hasta que esté completamente pagada (monto_cuota)
    - Solo cuando total_pagado >= monto_cuota, se marca como "PAGADO"
    - Si un pago cubre completamente una cuota y sobra, el exceso se aplica a la siguiente

    ⚠️ IMPORTANTE: Solo se aplica si el pago está conciliado.

    Returns:
        int: Número de cuotas que se completaron completamente con este pago
    """
    from datetime import date

    # ✅ VERIFICAR QUE EL PAGO ESTÉ CONCILIADO
    if not pago.conciliado:
        # Verificar también verificado_concordancia como alternativa
        verificado_ok = getattr(pago, "verificado_concordancia", None) == "SI"
        if not verificado_ok:
            logger.warning(
                f"⚠️ [aplicar_pago_a_cuotas] Pago ID {pago.id} NO está conciliado "
                f"(conciliado={pago.conciliado}, verificado_concordancia={getattr(pago, 'verificado_concordancia', 'N/A')}). "
                f"No se aplicará a cuotas. El pago debe estar conciliado primero."
            )
            return 0

    logger.info(f"✅ [aplicar_pago_a_cuotas] Pago ID {pago.id} está conciliado. Procediendo a aplicar a cuotas.")

    validacion_ok, _ = _verificar_prestamo_y_cedula(pago, db)
    if not validacion_ok:
        return 0

    logger.info(
        f"🔄 [aplicar_pago_a_cuotas] Aplicando pago ID {pago.id} "
        f"(monto: ${pago.monto_pagado}, prestamo_id: {pago.prestamo_id}, cedula: {pago.cedula})"  # Unificado: ahora usa 'cedula'
    )

    cuotas = _obtener_cuotas_pendientes(db, pago.prestamo_id)
    logger.info(f"📋 [aplicar_pago_a_cuotas] Préstamo {pago.prestamo_id}: {len(cuotas)} cuotas no pagadas encontradas")

    if len(cuotas) == 0:
        logger.warning(
            f"⚠️ [aplicar_pago_a_cuotas] Préstamo {pago.prestamo_id} " f"no tiene cuotas pendientes. No se aplicará el pago."
        )
        return 0

    fecha_hoy = date.today()
    cuotas_completadas, saldo_restante = _aplicar_pago_a_cuotas_iterativas(
        cuotas, pago.monto_pagado, pago.fecha_pago, fecha_hoy, db
    )

    if saldo_restante > Decimal("0.00"):
        logger.info(
            f"📊 [aplicar_pago_a_cuotas] Saldo restante: ${saldo_restante}. " f"Aplicando a siguiente cuota pendiente..."
        )
        cuotas_completadas += _aplicar_exceso_a_siguiente_cuota(
            db, pago.prestamo_id, saldo_restante, pago.fecha_pago, fecha_hoy
        )

    try:
        # ✅ ACTUALIZAR ESTADO DEL PAGO después de aplicar a cuotas
        # El estado solo se actualiza DESPUÉS de conciliar y aplicar a cuotas
        if cuotas_completadas > 0:
            # Si completó al menos una cuota completamente → estado "PAGADO"
            pago.estado = "PAGADO"  # type: ignore[assignment]
            logger.info(
                f"✅ [aplicar_pago_a_cuotas] Pago ID {pago.id}: Estado actualizado a 'PAGADO' "
                f"(completó {cuotas_completadas} cuota(s))"
            )
        elif pago.prestamo_id:
            # Si tiene préstamo pero no completó ninguna cuota completamente → estado "PARCIAL"
            pago.estado = "PARCIAL"  # type: ignore[assignment]
            logger.info(
                f"ℹ️ [aplicar_pago_a_cuotas] Pago ID {pago.id}: Estado actualizado a 'PARCIAL' "
                f"(no completó ninguna cuota completamente)"
            )
        # Si no tiene prestamo_id, mantener el estado por defecto

        db.commit()
        logger.info(
            f"✅ [aplicar_pago_a_cuotas] Pago ID {pago.id} aplicado exitosamente. " f"Cuotas completadas: {cuotas_completadas}"
        )
    except Exception as e:
        logger.error(f"❌ [aplicar_pago_a_cuotas] Error al guardar cambios en BD: {str(e)}", exc_info=True)
        db.rollback()
        raise

    return cuotas_completadas


def registrar_auditoria_pago(
    pago_id: int,
    usuario: str,
    accion: str,
    campo_modificado: str,
    valor_anterior: str,
    valor_nuevo: str,
    observaciones: Optional[str] = None,
    db: Session = None,
):
    """
    Registra un cambio en la auditoría de pagos
    """
    auditoria = PagoAuditoria(
        pago_id=pago_id,
        usuario=usuario,
        campo_modificado=campo_modificado,
        valor_anterior=valor_anterior,
        valor_nuevo=valor_nuevo,
        accion=accion,
        observaciones=observaciones,
        fecha_cambio=datetime.now(),
    )
    db.add(auditoria)
    db.commit()


def _calcular_kpis_pagos_interno(db: Session, mes_consulta: int, año_consulta: int) -> dict:
    """
    Función interna para calcular KPIs (cacheable)
    Optimizada para reducir número de queries y tiempo de ejecución
    """
    from datetime import date, datetime

    start_total = time.time()
    hoy = date.today()

    # Fecha inicio y fin del mes
    fecha_inicio_mes = date(año_consulta, mes_consulta, 1)
    # Calcular último día del mes
    if mes_consulta == 12:
        fecha_fin_mes = date(año_consulta + 1, 1, 1)
    else:
        fecha_fin_mes = date(año_consulta, mes_consulta + 1, 1)

    logger.debug(f"📊 [kpis_pagos] Calculando KPIs para mes {mes_consulta}/{año_consulta}")
    logger.debug(f"📅 [kpis_pagos] Rango de fechas: {fecha_inicio_mes} a {fecha_fin_mes}")

    fecha_inicio_dt = datetime.combine(fecha_inicio_mes, datetime.min.time())
    fecha_fin_dt = datetime.combine(fecha_fin_mes, datetime.min.time())

    # OPTIMIZACIÓN 1: Usar ORM para consultar tabla pagos
    start_pagos = time.time()
    monto_cobrado_mes = Decimal("0")
    monto_no_definido = Decimal("0")

    try:
        # Monto total cobrado en el mes
        monto_total_query = db.query(func.sum(Pago.monto_pagado)).filter(
            Pago.activo.is_(True),
            Pago.fecha_pago >= fecha_inicio_dt,
            Pago.fecha_pago < fecha_fin_dt,
            Pago.monto_pagado.isnot(None),
        )
        monto_cobrado_mes = Decimal(str(monto_total_query.scalar() or 0))

        # Monto no definido (sin conciliar o sin número de documento)
        monto_no_definido_query = db.query(func.sum(Pago.monto_pagado)).filter(
            Pago.activo.is_(True),
            Pago.fecha_pago >= fecha_inicio_dt,
            Pago.fecha_pago < fecha_fin_dt,
            Pago.monto_pagado.isnot(None),
            or_(
                Pago.conciliado.is_(False),
                Pago.conciliado.is_(None),
                Pago.numero_documento.is_(None),
                Pago.numero_documento == "",
                func.upper(func.trim(Pago.numero_documento)) == "NO DEFINIDO",
            ),
        )
        monto_no_definido = Decimal(str(monto_no_definido_query.scalar() or 0))
    except Exception as e:
        logger.warning(f"⚠️ [kpis_pagos] Error consultando pagos: {e}, usando valores por defecto")
        # Hacer rollback para limpiar la transacción abortada
        try:
            db.rollback()
        except Exception:
            pass  # Ignorar errores de rollback
        # Si hay error, usar valores por defecto (0)
        monto_cobrado_mes = Decimal("0")
        monto_no_definido = Decimal("0")

    tiempo_pagos = int((time.time() - start_pagos) * 1000)
    logger.debug(
        f"💰 [kpis_pagos] Monto cobrado: ${monto_cobrado_mes:,.2f}, NO DEFINIDO: ${monto_no_definido:,.2f} ({tiempo_pagos}ms)"
    )

    # OPTIMIZACIÓN 2: Saldo por cobrar (query única optimizada)
    start_saldo = time.time()
    try:
        saldo_por_cobrar_query = (
            db.query(
                func.sum(
                    func.coalesce(Cuota.capital_pendiente, Decimal("0.00"))
                    + func.coalesce(Cuota.interes_pendiente, Decimal("0.00"))
                    + func.coalesce(Cuota.monto_mora, Decimal("0.00"))
                )
            )
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.estado != "PAGADO",
                Prestamo.estado == "APROBADO",
            )
        )
        saldo_por_cobrar = saldo_por_cobrar_query.scalar() or Decimal("0.00")
    except Exception as e:
        logger.warning(f"⚠️ [kpis_pagos] Error consultando saldo por cobrar: {e}, usando valor por defecto")
        # Hacer rollback para limpiar la transacción abortada
        try:
            db.rollback()
        except Exception:
            pass  # Ignorar errores de rollback
        saldo_por_cobrar = Decimal("0.00")
    tiempo_saldo = int((time.time() - start_saldo) * 1000)
    logger.debug(f"💳 [kpis_pagos] Saldo por cobrar: ${saldo_por_cobrar:,.2f} ({tiempo_saldo}ms)")

    # OPTIMIZACIÓN 3: Combinar queries de clientes en una sola con CTE
    # Esto reduce de 2 queries a 1 y calcula ambos valores en una sola pasada
    start_clientes = time.time()
    clientes_query = db.execute(
        text(
            """
            WITH clientes_prestamos AS (
                SELECT DISTINCT p.cedula
                FROM prestamos p
                INNER JOIN cuotas c ON c.prestamo_id = p.id
                WHERE p.estado = 'APROBADO'
            ),
            clientes_en_mora AS (
                SELECT DISTINCT p.cedula
                FROM prestamos p
                INNER JOIN cuotas c ON c.prestamo_id = p.id
                WHERE p.estado = 'APROBADO'
                  AND c.fecha_vencimiento < :hoy
                  AND c.total_pagado < c.monto_cuota
            )
            SELECT
                (SELECT COUNT(*) FROM clientes_prestamos) AS total_clientes,
                (SELECT COUNT(*) FROM clientes_en_mora) AS clientes_mora
        """
        ).bindparams(hoy=hoy)
    )
    clientes_result = clientes_query.fetchone()
    if clientes_result is None:
        clientes_con_cuotas = 0
        clientes_en_mora = 0
    else:
        clientes_con_cuotas = clientes_result[0] if clientes_result[0] is not None else 0
        clientes_en_mora = clientes_result[1] if clientes_result[1] is not None else 0
    clientes_al_dia = max(0, clientes_con_cuotas - clientes_en_mora)
    tiempo_clientes = int((time.time() - start_clientes) * 1000)
    logger.debug(
        f"👥 [kpis_pagos] Clientes - Total: {clientes_con_cuotas}, En mora: {clientes_en_mora}, Al día: {clientes_al_dia} ({tiempo_clientes}ms)"
    )

    tiempo_total = int((time.time() - start_total) * 1000)
    logger.debug(
        f"⏱️ [kpis_pagos] Tiempo total: {tiempo_total}ms (pagos: {tiempo_pagos}ms, saldo: {tiempo_saldo}ms, clientes: {tiempo_clientes}ms)"
    )

    return {
        "montoCobradoMes": float(monto_cobrado_mes),
        "montoNoDefinido": float(monto_no_definido),  # ✅ Categoría "NO DEFINIDO"
        "saldoPorCobrar": float(saldo_por_cobrar),
        "clientesEnMora": clientes_en_mora,
        "clientesAlDia": clientes_al_dia,
        "mes": mes_consulta,
        "año": año_consulta,
    }


@router.get("/kpis")
def obtener_kpis_pagos(
    mes: Optional[int] = Query(None, description="Mes (1-12), default: mes actual"),
    año: Optional[int] = Query(None, description="Año, default: año actual"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    KPIs específicos para el módulo de Pagos

    Devuelve:
    - montoCobradoMes: Suma de todos los pagos del mes especificado
    - montoNoDefinido: Suma de pagos no conciliados o sin numero_documento (agrupados como "NO DEFINIDO")
    - saldoPorCobrar: Suma de capital_pendiente + interes_pendiente + monto_mora de todas las cuotas no pagadas
    - clientesEnMora: Conteo de clientes únicos con cuotas vencidas y no pagadas
    - clientesAlDia: Conteo de clientes únicos sin cuotas vencidas sin pagar

    Los KPIs son fijos por mes (mes/año especificados o mes/año actual)
    Cacheado por 5 minutos para mejorar rendimiento.
    """
    try:
        from datetime import date

        from app.core.cache import cache_backend

        # Determinar mes y año (default: mes/año actual)
        hoy = date.today()
        mes_consulta = mes if mes is not None else hoy.month
        año_consulta = año if año is not None else hoy.year

        # Validar mes
        if mes_consulta < 1 or mes_consulta > 12:
            raise HTTPException(status_code=400, detail="El mes debe estar entre 1 y 12")

        # Construir clave de caché única por mes/año
        cache_key = f"pagos_kpis:obtener_kpis_pagos:{mes_consulta}:{año_consulta}"

        # Intentar obtener del caché
        cached_result = cache_backend.get(cache_key)
        if cached_result is not None:
            logger.debug(f"✅ [kpis_pagos] Cache HIT para mes {mes_consulta}/{año_consulta}")
            return cached_result

        # Cache miss - calcular KPIs
        logger.debug(f"❌ [kpis_pagos] Cache MISS para mes {mes_consulta}/{año_consulta}, calculando...")
        try:
            result = _calcular_kpis_pagos_interno(db, mes_consulta, año_consulta)

            # Guardar en caché por 5 minutos (300 segundos)
            cache_backend.set(cache_key, result, ttl=300)
            logger.debug(f"💾 [kpis_pagos] Resultados guardados en caché para mes {mes_consulta}/{año_consulta}")

            return result
        except Exception as calc_error:
            logger.error(f"❌ [kpis_pagos] Error calculando KPIs: {calc_error}", exc_info=True)
            try:
                db.rollback()
            except Exception:
                pass
            # Retornar valores por defecto en lugar de fallar completamente
            return {
                "montoCobradoMes": 0.0,
                "montoNoDefinido": 0.0,
                "saldoPorCobrar": 0.0,
                "clientesEnMora": 0,
                "clientesAlDia": 0,
                "mes": mes_consulta,
                "año": año_consulta,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [kpis_pagos] Error obteniendo KPIs: {e}", exc_info=True)
        try:
            db.rollback()  # ✅ Rollback para restaurar transacción después de error
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error interno al obtener KPIs: {str(e)}")


@router.get("/stats")
def obtener_estadisticas_pagos(
    analista: Optional[str] = Query(None, description="Filtrar por analista"),
    concesionario: Optional[str] = Query(None, description="Filtrar por concesionario"),
    modelo: Optional[str] = Query(None, description="Filtrar por modelo"),
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estadísticas de pagos con filtros opcionales
    """
    try:
        hoy = datetime.now().date()

        # ✅ Base query para pagos - usar tabla pagos
        base_pago_query = db.query(Pago).filter(Pago.activo.is_(True))

        # Aplicar filtros de fecha directamente
        if fecha_inicio:
            base_pago_query = base_pago_query.filter(Pago.fecha_pago >= datetime.combine(fecha_inicio, datetime.min.time()))
        if fecha_fin:
            base_pago_query = base_pago_query.filter(Pago.fecha_pago <= datetime.combine(fecha_fin, datetime.max.time()))

        # Si hay filtros de analista/concesionario/modelo, necesitamos join con Prestamo
        if analista or concesionario or modelo:
            base_pago_query = base_pago_query.join(Prestamo, Pago.prestamo_id == Prestamo.id)
            base_pago_query = FiltrosDashboard.aplicar_filtros_pago(
                base_pago_query,
                analista,
                concesionario,
                modelo,
                fecha_inicio,
                fecha_fin,
            )
        else:
            # Aplicar filtros básicos sin join
            base_pago_query = FiltrosDashboard.aplicar_filtros_pago(
                base_pago_query,
                analista,
                concesionario,
                modelo,
                fecha_inicio,
                fecha_fin,
            )

        # Total de pagos
        total_pagos = base_pago_query.count()

        # Pagos por estado - necesitamos una query separada para agrupar
        pagos_por_estado_query = db.query(Pago.estado, func.count(Pago.id)).filter(Pago.activo.is_(True))
        if fecha_inicio:
            pagos_por_estado_query = pagos_por_estado_query.filter(
                Pago.fecha_pago >= datetime.combine(fecha_inicio, datetime.min.time())
            )
        if fecha_fin:
            pagos_por_estado_query = pagos_por_estado_query.filter(
                Pago.fecha_pago <= datetime.combine(fecha_fin, datetime.max.time())
            )
        if analista or concesionario or modelo:
            pagos_por_estado_query = pagos_por_estado_query.join(Prestamo, Pago.prestamo_id == Prestamo.id)
            pagos_por_estado_query = FiltrosDashboard.aplicar_filtros_pago(
                pagos_por_estado_query,
                analista,
                concesionario,
                modelo,
                fecha_inicio,
                fecha_fin,
            )
        pagos_por_estado = pagos_por_estado_query.group_by(Pago.estado).all()

        # Monto total pagado usando ORM
        total_pagado_query = db.query(func.sum(Pago.monto_pagado)).filter(Pago.activo.is_(True), Pago.monto_pagado.isnot(None))
        if fecha_inicio:
            total_pagado_query = total_pagado_query.filter(
                Pago.fecha_pago >= datetime.combine(fecha_inicio, datetime.min.time())
            )
        if fecha_fin:
            total_pagado_query = total_pagado_query.filter(Pago.fecha_pago <= datetime.combine(fecha_fin, datetime.max.time()))
        if analista or concesionario or modelo:
            total_pagado_query = total_pagado_query.join(Prestamo, Pago.prestamo_id == Prestamo.id)
            total_pagado_query = FiltrosDashboard.aplicar_filtros_pago(
                total_pagado_query,
                analista,
                concesionario,
                modelo,
                fecha_inicio,
                fecha_fin,
            )
        total_pagado = Decimal(str(total_pagado_query.scalar() or 0))

        # Pagos del día actual
        pagos_hoy_query = db.query(func.sum(Pago.monto_pagado)).filter(
            Pago.activo.is_(True), Pago.monto_pagado.isnot(None), func.date(Pago.fecha_pago) == hoy
        )
        if analista or concesionario or modelo:
            pagos_hoy_query = pagos_hoy_query.join(Prestamo, Pago.prestamo_id == Prestamo.id)
            pagos_hoy_query = FiltrosDashboard.aplicar_filtros_pago(
                pagos_hoy_query,
                analista,
                concesionario,
                modelo,
                fecha_inicio,
                fecha_fin,
            )
        pagos_hoy = Decimal(str(pagos_hoy_query.scalar() or 0))

        # ✅ Cuotas pagadas vs pendientes - usar FiltrosDashboard
        cuotas_query = db.query(Cuota).join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        cuotas_query = FiltrosDashboard.aplicar_filtros_cuota(
            cuotas_query,
            analista,
            concesionario,
            modelo,
            fecha_inicio,
            fecha_fin,
        )

        cuotas_pagadas = cuotas_query.filter(Cuota.estado == "PAGADO").count()
        cuotas_pendientes = cuotas_query.filter(Cuota.estado == "PENDIENTE").count()
        cuotas_atrasadas = cuotas_query.filter(Cuota.estado == "ATRASADO").count()

        return {
            "total_pagos": total_pagos,
            "pagos_por_estado": {estado: count for estado, count in pagos_por_estado},
            "total_pagado": float(total_pagado),
            "pagos_hoy": float(pagos_hoy),
            "cuotas_pagadas": cuotas_pagadas,
            "cuotas_pendientes": cuotas_pendientes,
            "cuotas_atrasadas": cuotas_atrasadas,
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/auditoria/{pago_id}")
def obtener_auditoria_pago(
    pago_id: int = Path(..., gt=0, description="ID del pago"),
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Registros por página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener historial de auditoría de un pago con paginación
    """
    from app.utils.pagination import calculate_pagination_params, create_paginated_response

    # Calcular paginación
    skip, limit = calculate_pagination_params(page=page, per_page=per_page, max_per_page=100)

    # Query base
    query = db.query(PagoAuditoria).filter(PagoAuditoria.pago_id == pago_id).order_by(PagoAuditoria.fecha_cambio.desc())

    # Contar total
    total = query.count()

    # Aplicar paginación
    auditorias = query.offset(skip).limit(limit).all()

    # Serializar resultados
    items = [
        {
            "id": a.id,
            "usuario": a.usuario,
            "campo_modificado": a.campo_modificado,
            "valor_anterior": a.valor_anterior,
            "valor_nuevo": a.valor_nuevo,
            "accion": a.accion,
            "observaciones": a.observaciones,
            "fecha_cambio": a.fecha_cambio.isoformat(),
        }
        for a in auditorias
    ]

    return create_paginated_response(items=items, total=total, page=page, page_size=limit)


# ============================================
# ENDPOINTS PARA PAGOS_STAGING - ELIMINADOS
# La tabla pagos_staging ya fue migrada a pagos
# ============================================

# ⚠️ NOTA: Los siguientes endpoints fueron eliminados porque pagos_staging ya no existe:
# - listar_pagos_staging
# - estadisticas_pagos_staging
# - migrar_pago_staging_a_pagos
# - verificar_conexion_pagos_staging
# Todo ahora usa la tabla 'pagos' directamente


@router.get("/exportar/errores")
def exportar_pagos_con_errores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exporta un informe Excel con pagos que tienen errores:
    - Cédulas vacías o con valor "Z999999999"
    - Fechas que no cumplen formato o tienen "31/10/2025"
    - numero_documento con "NO DEFINIDO" o "Nodefinida"

    El informe incluye las mismas columnas que la tabla pagos.
    """
    try:
        logger.debug("📊 [exportar_pagos_errores] Generando informe de pagos con errores...")

        # ✅ Consulta SQL para obtener pagos con errores de la tabla pagos
        query = text(
            """
            SELECT
                id,
                cedula,
                fecha_pago,
                monto_pagado,
                numero_documento,
                COALESCE(conciliado, FALSE) as conciliado,
                fecha_conciliacion
            FROM pagos
            WHERE activo = TRUE
              AND (
                  -- Cédulas vacías o Z999999999
                  cedula IS NULL
                  OR TRIM(cedula) = ''
                  OR UPPER(TRIM(cedula)) = 'Z999999999'
                  -- Fechas inválidas o con formato incorrecto o 31/10/2025
                  OR fecha_pago IS NULL
                  OR fecha_pago::text LIKE '%31/10/2025%'
                  OR fecha_pago::text LIKE '%2025-10-31%'
                  -- numero_documento con "NO DEFINIDO" o "Nodefinida"
                  OR numero_documento IS NULL
                  OR TRIM(UPPER(numero_documento)) = 'NO DEFINIDO'
                  OR TRIM(UPPER(numero_documento)) = 'NODEFINIDA'
                  OR TRIM(UPPER(numero_documento)) = 'NODEFINIDO'
              )
            ORDER BY id DESC
        """
        )

        resultados = db.execute(query).fetchall()

        logger.debug(f"📊 [exportar_pagos_errores] Encontrados {len(resultados)} pagos con errores")

        # ✅ Generar archivo Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Pagos con Errores"

        # Estilos
        header_fill = PatternFill(start_color="DC143C", end_color="DC143C", fill_type="solid")  # Rojo
        header_font = Font(bold=True, color="FFFFFF", size=12)

        # Encabezados (columnas de la tabla pagos)
        headers = [
            "ID",
            "Cédula",
            "Fecha Pago",
            "Monto Pagado",
            "Número Documento",
            "Conciliado",
            "Fecha Conciliación",
        ]

        # Escribir encabezados
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Escribir datos
        for row_idx, registro in enumerate(resultados, 2):
            ws.cell(row=row_idx, column=1, value=registro[0])  # id
            ws.cell(row=row_idx, column=2, value=registro[1] if registro[1] else "")  # cedula
            ws.cell(row=row_idx, column=3, value=registro[2].isoformat() if registro[2] else "")  # fecha_pago
            ws.cell(row=row_idx, column=4, value=float(registro[3]) if registro[3] else "")  # monto_pagado
            ws.cell(row=row_idx, column=5, value=registro[4] if registro[4] else "")  # numero_documento
            ws.cell(row=row_idx, column=6, value="Sí" if registro[5] else "No")  # conciliado
            ws.cell(row=row_idx, column=7, value=registro[6].isoformat() if registro[6] else "")  # fecha_conciliacion

        # Ajustar anchos de columnas
        column_widths = [12, 18, 20, 18, 25, 12, 20]
        for col, width in enumerate(column_widths, 1):
            ws.column_dimensions[chr(64 + col)].width = width

        # Agregar fila de totales
        total_row = len(resultados) + 3
        ws.cell(row=total_row, column=1, value="TOTAL:")
        ws.cell(row=total_row, column=1).font = Font(bold=True)
        ws.cell(row=total_row, column=2, value=f"{len(resultados)} registros con errores")
        ws.cell(row=total_row, column=2).font = Font(bold=True)

        # Guardar en BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        # Nombre del archivo con fecha
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pagos_con_errores_{fecha}.xlsx"

        logger.info(f"✅ [exportar_pagos_errores] Excel generado: {filename} ({len(resultados)} registros)")

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [exportar_pagos_errores] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al exportar pagos con errores: {str(e)}")
