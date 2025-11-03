"""
Endpoints para el módulo de Pagos
"""

import logging
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query  # type: ignore[import-untyped]
from sqlalchemy import func, or_, text  # type: ignore[import-untyped]
from sqlalchemy.orm import Session  # type: ignore[import-untyped]

from app.api.deps import get_current_user, get_db
from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.pago import Pago  # Mantener para operaciones que necesiten tabla pagos (crear, actualizar)
from app.models.pago_auditoria import PagoAuditoria
from app.models.pago_staging import PagoStaging  # Usar para consultas principales (listar, stats, kpis)
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
    """Aplica filtros a la query de pagos (usa PagoStaging)"""
    if cedula:
        # PagoStaging puede tener cedula_cliente o cedula
        query = query.filter(or_(PagoStaging.cedula_cliente == cedula, PagoStaging.cedula == cedula))
        logger.info(f"🔍 [listar_pagos] Filtro cédula: {cedula}")
    if estado:
        query = query.filter(PagoStaging.estado == estado)
        logger.info(f"🔍 [listar_pagos] Filtro estado: {estado}")
    if fecha_desde:
        query = query.filter(PagoStaging.fecha_pago >= fecha_desde)
        logger.info(f"🔍 [listar_pagos] Filtro fecha_desde: {fecha_desde}")
    if fecha_hasta:
        query = query.filter(PagoStaging.fecha_pago <= fecha_hasta)
        logger.info(f"🔍 [listar_pagos] Filtro fecha_hasta: {fecha_hasta}")
    if analista:
        query = query.join(Prestamo, PagoStaging.prestamo_id == Prestamo.id).filter(Prestamo.usuario_proponente == analista)
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


def _serializar_pago(pago, hoy: date, cuotas_atrasadas_cache: Optional[dict[str, int]] = None):
    """
    Serializa un pago de forma segura.

    OPTIMIZACIÓN: Recibe cache de cuotas_atrasadas para evitar N+1 queries.
    Si no se proporciona cache, asume 0 (no se calcula individualmente para mejor performance).
    """
    try:
        # Convertir fecha_pago si es DATE a datetime si es necesario
        if hasattr(pago, "fecha_pago") and pago.fecha_pago is not None:
            if isinstance(pago.fecha_pago, date) and not isinstance(pago.fecha_pago, datetime):
                pago.fecha_pago = datetime.combine(pago.fecha_pago, time.min)

        # Validar con el schema
        pago_dict = PagoResponse.model_validate(pago).model_dump()

        # Obtener cuotas atrasadas del cache (siempre debe proporcionarse)
        # PagoStaging puede tener cedula_cliente o cedula
        cedula_cliente = pago.cedula_cliente or pago.cedula
        if cuotas_atrasadas_cache is not None:
            cuotas_atrasadas = cuotas_atrasadas_cache.get(cedula_cliente, 0)
        else:
            # Fallback: 0 si no hay cache (para evitar N+1, el cache debe calcularse antes)
            cuotas_atrasadas = 0
            logger.warning(f"⚠️ [serializar_pago] No se proporcionó cache de cuotas atrasadas para pago {pago.id}")

        pago_dict["cuotas_atrasadas"] = cuotas_atrasadas
        return pago_dict
    except Exception as e:
        error_detail = str(e)
        logger.error(
            f"❌ [listar_pagos] Error serializando pago ID {pago.id}: {error_detail}",
            exc_info=True,
        )
        cedula_cliente = getattr(pago, "cedula_cliente", None) or getattr(pago, "cedula", None)
        logger.error(f"   Datos del pago: cedula={cedula_cliente}")
        logger.error(f"   fecha_pago={pago.fecha_pago} (tipo: {type(pago.fecha_pago)})")
        logger.error(
            f"   fecha_registro={getattr(pago, 'fecha_registro', 'N/A')} (tipo: {type(getattr(pago, 'fecha_registro', None))})"
        )
        logger.error(
            f"   fecha_actualizacion={getattr(pago, 'fecha_actualizacion', 'N/A')} (tipo: {type(getattr(pago, 'fecha_actualizacion', None))})"
        )
        logger.error(
            f"   fecha_conciliacion={getattr(pago, 'fecha_conciliacion', 'N/A')} (tipo: {type(getattr(pago, 'fecha_conciliacion', None))})"
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
        # Verificar conexión a BD con prueba de consulta (usa PagoStaging)
        total_pagos = db.query(func.count(PagoStaging.id)).scalar() or 0

        # Pagos del mes actual
        hoy = date.today()
        primer_dia_mes = date(hoy.year, hoy.month, 1)
        pagos_mes = db.query(func.count(PagoStaging.id)).filter(PagoStaging.fecha_pago >= primer_dia_mes).scalar() or 0

        # Monto total pagado
        monto_total = db.query(func.sum(PagoStaging.monto_pagado)).scalar() or Decimal("0")

        # Pagos por estado
        pagos_por_estado = db.query(PagoStaging.estado, func.count(PagoStaging.id)).group_by(PagoStaging.estado).all()
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
        # Usar PagoStaging donde están los datos reales
        query_test = db.query(PagoStaging).order_by(PagoStaging.fecha_registro.desc()).limit(5)
        pagos_test = query_test.all()

        if not pagos_test:
            diagnostico["verificaciones"]["query_compleja"] = {
                "status": "warning",
                "mensaje": "Query compleja exitosa pero no hay pagos en BD para probar",
            }
            return

        primer_pago = pagos_test[0]
        if not primer_pago.cedula_cliente:
            diagnostico["verificaciones"]["query_compleja"] = {
                "status": "ok",
                "mensaje": f"Query compleja exitosa - {len(pagos_test)} pagos obtenidos, primer pago sin cédula",
            }
            return

        prestamos_ids = [
            p.id
            for p in db.query(Prestamo.id)
            .filter(
                Prestamo.cedula == primer_pago.cedula_cliente,
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
                "cedula": primer_pago.cedula_cliente,
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
        # Usar PagoStaging donde están los datos reales
        query_test = db.query(PagoStaging).order_by(PagoStaging.fecha_registro.desc()).limit(1)
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

        # Verificar conexión a BD
        try:
            test_query = db.query(func.count(PagoStaging.id)).scalar()
            logger.info(f"✅ [listar_pagos] Conexión BD OK. Total pagos en pagos_staging: {test_query}")
        except Exception as db_error:
            logger.error(f"❌ [listar_pagos] Error de conexión BD: {db_error}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error de conexión a la base de datos: {str(db_error)}",
            )

        query = db.query(PagoStaging)

        # Aplicar filtros
        query = _aplicar_filtros_pagos(query, cedula, estado, fecha_desde, fecha_hasta, analista, db)

        # Contar total antes de aplicar paginación
        total = query.count()
        logger.info(f"📊 [listar_pagos] Total pagos encontrados (sin paginación): {total}")

        # Ordenar por fecha de registro descendente (más actual primero)
        if hasattr(PagoStaging, "fecha_registro"):
            query = query.order_by(PagoStaging.fecha_registro.desc(), PagoStaging.id.desc())
        else:
            query = query.order_by(PagoStaging.id.desc())

        # Paginación
        offset = (page - 1) * per_page
        pagos = query.offset(offset).limit(per_page).all()
        logger.info(f"📄 [listar_pagos] Pagos obtenidos de BD: {len(pagos)}")

        # OPTIMIZACIÓN: Calcular todas las cuotas atrasadas de una vez (batch)
        hoy = date.today()
        # PagoStaging puede tener cedula_cliente o cedula
        cedulas_unicas = list(set((p.cedula_cliente or p.cedula) for p in pagos if (p.cedula_cliente or p.cedula)))
        cuotas_atrasadas_cache = _calcular_cuotas_atrasadas_batch(db, cedulas_unicas, hoy)

        logger.debug(f"✅ [listar_pagos] Cache de cuotas atrasadas calculado para {len(cedulas_unicas)} clientes únicos")

        # Serializar pagos usando el cache
        pagos_serializados = []
        errores_serializacion = 0

        for pago in pagos:
            try:
                pago_dict = _serializar_pago(pago, hoy, cuotas_atrasadas_cache)
                pagos_serializados.append(pago_dict)
            except Exception:
                errores_serializacion += 1
                continue

        if errores_serializacion > 0:
            logger.warning(f"⚠️ [listar_pagos] {errores_serializacion} de {len(pagos)} pagos fallaron en serialización")

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
        cliente = db.query(Cliente).filter(Cliente.cedula == pago_data.cedula_cliente).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Crear el pago
        pago_dict = pago_data.model_dump()
        pago_dict["usuario_registro"] = current_user.email
        pago_dict["fecha_registro"] = datetime.now()

        # Eliminar cualquier campo que no exista en el modelo (por ejemplo, referencia_pago si la migración no se ha ejecutado)
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

        # Aplicar pago a cuotas
        try:
            cuotas_completadas = aplicar_pago_a_cuotas(nuevo_pago, db, current_user)
            logger.info(f"✅ [crear_pago] Pago ID {nuevo_pago.id}: " f"{cuotas_completadas} cuota(s) completada(s)")
        except Exception as e:
            logger.error(
                f"❌ [crear_pago] Error aplicando pago a cuotas: {str(e)}",
                exc_info=True,
            )
            # No fallar el registro del pago si falla la aplicación a cuotas
            # El pago se registra pero las cuotas no se actualizan
            cuotas_completadas = 0

        # Actualizar estado del pago según regla de negocio:
        # - Si el pago no tiene préstamo asociado, mantener estado por defecto "PAGADO"
        # - Si tiene préstamo pero no completó ninguna cuota completamente → estado "PARCIAL" (abono parcial)
        # - Si completó al menos una cuota completamente → estado "PAGADO"
        if nuevo_pago.prestamo_id and cuotas_completadas == 0:
            nuevo_pago.estado = "PARCIAL"
        elif nuevo_pago.prestamo_id and cuotas_completadas > 0:
            nuevo_pago.estado = "PAGADO"
        # Si no tiene prestamo_id, mantener el estado por defecto "PAGADO"

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

        logger.info(f"🔄 [aplicar_pago_manualmente] Reaplicando pago ID {pago_id} " f"al préstamo {pago.prestamo_id}")

        # Reaplicar el pago a las cuotas
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

        pago.fecha_actualizacion = datetime.now()
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
        # Usar PagoStaging donde están los datos reales
        sub_ultimos = (
            db.query(
                func.coalesce(PagoStaging.cedula_cliente, PagoStaging.cedula).label("cedula"),
                func.max(PagoStaging.fecha_registro).label("max_fecha"),
            )
            .filter(or_(PagoStaging.cedula_cliente.isnot(None), PagoStaging.cedula.isnot(None)))
            .group_by(func.coalesce(PagoStaging.cedula_cliente, PagoStaging.cedula))
            .subquery()
        )

        # Join para obtener el registro de pago completo de esa última fecha
        # Usar PagoStaging donde están los datos reales
        pagos_ultimos_q = db.query(PagoStaging).join(
            sub_ultimos,
            (or_(PagoStaging.cedula_cliente == sub_ultimos.c.cedula, PagoStaging.cedula == sub_ultimos.c.cedula))
            & (PagoStaging.fecha_registro == sub_ultimos.c.max_fecha),
        )

        # Filtros
        if cedula:
            pagos_ultimos_q = pagos_ultimos_q.filter(or_(PagoStaging.cedula_cliente == cedula, PagoStaging.cedula == cedula))
        if estado:
            pagos_ultimos_q = pagos_ultimos_q.filter(PagoStaging.estado == estado)

        # Total para paginación
        total = pagos_ultimos_q.count()

        # Paginación (ordenar por fecha_registro desc)
        offset = (page - 1) * per_page
        if hasattr(PagoStaging, "fecha_registro"):
            pagos_ultimos = pagos_ultimos_q.order_by(PagoStaging.fecha_registro.desc()).offset(offset).limit(per_page).all()
        else:
            pagos_ultimos = pagos_ultimos_q.order_by(PagoStaging.id.desc()).offset(offset).limit(per_page).all()

        # Para cada cédula, calcular agregados sobre amortización (todas sus deudas)
        items = []
        from datetime import date
        from decimal import Decimal

        from app.models.amortizacion import Cuota
        from app.models.prestamo import Prestamo

        for pago in pagos_ultimos:
            # PagoStaging puede tener cedula_cliente o cedula
            cedula_cliente = pago.cedula_cliente or pago.cedula
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


def _actualizar_estado_cuota(cuota, fecha_hoy: date, es_exceso: bool = False) -> bool:
    """
    Actualiza el estado de una cuota según las reglas de negocio.
    Returns:
        bool: True si la cuota se completó completamente (pasó de incompleta a PAGADO)
    """
    estado_previo_completo = cuota.total_pagado >= cuota.monto_cuota
    estado_completado = False

    if cuota.total_pagado >= cuota.monto_cuota:
        cuota.estado = "PAGADO"
        if not estado_previo_completo:
            estado_completado = True
    elif cuota.total_pagado > Decimal("0.00"):
        if cuota.fecha_vencimiento and cuota.fecha_vencimiento < fecha_hoy:
            cuota.estado = "ATRASADO"
        else:
            cuota.estado = "ADELANTADO" if es_exceso else "PENDIENTE"
    else:
        if cuota.fecha_vencimiento and cuota.fecha_vencimiento < fecha_hoy:
            cuota.estado = "ATRASADO"
        else:
            cuota.estado = "PENDIENTE"

    return estado_completado


def _aplicar_monto_a_cuota(cuota, monto_aplicar: Decimal, fecha_pago: date, fecha_hoy: date, es_exceso: bool = False) -> bool:
    """
    Aplica un monto a una cuota, actualizando todos los campos correspondientes.
    Returns:
        bool: True si la cuota se completó completamente con este pago
    """
    if monto_aplicar <= Decimal("0.00"):
        return False

    capital_aplicar, interes_aplicar = _calcular_proporcion_capital_interes(cuota, monto_aplicar)

    cuota.capital_pagado += capital_aplicar
    cuota.interes_pagado += interes_aplicar
    cuota.total_pagado += monto_aplicar
    cuota.capital_pendiente = max(Decimal("0.00"), cuota.capital_pendiente - capital_aplicar)
    cuota.interes_pendiente = max(Decimal("0.00"), cuota.interes_pendiente - interes_aplicar)

    if monto_aplicar > Decimal("0.00"):
        cuota.fecha_pago = fecha_pago

    return _actualizar_estado_cuota(cuota, fecha_hoy, es_exceso)


def _aplicar_exceso_a_siguiente_cuota(
    db: Session, prestamo_id: int, saldo_restante: Decimal, fecha_pago: date, fecha_hoy: date
) -> int:
    """Aplica el exceso de pago a la siguiente cuota pendiente (más antigua primero). Returns: número de cuotas completadas"""
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

    estado_completado = _aplicar_monto_a_cuota(siguiente_cuota, monto_aplicar_exceso, fecha_pago, fecha_hoy, es_exceso=True)

    logger.debug(
        f"  💰 [aplicar_pago_a_cuotas] Cuota #{siguiente_cuota.numero_cuota} "
        f"(exceso): Aplicado ${monto_aplicar_exceso}, Estado: {siguiente_cuota.estado}"
    )

    return 1 if estado_completado else 0


def aplicar_pago_a_cuotas(pago: Pago, db: Session, current_user: User) -> int:
    """
    Aplica un pago a las cuotas correspondientes según la regla de negocio:
    - VERIFICA que la cédula del pago coincida con la cédula del préstamo
    - Los pagos se aplican a las cuotas más antiguas primero (por fecha_vencimiento)
    - Una cuota está "ATRASADO" hasta que esté completamente pagada (monto_cuota)
    - Solo cuando total_pagado >= monto_cuota, se marca como "PAGADO"
    - Si un pago cubre completamente una cuota y sobra, el exceso se aplica a la siguiente

    Returns:
        int: Número de cuotas que se completaron completamente con este pago
    """
    if not pago.prestamo_id:
        logger.warning(f"⚠️ [aplicar_pago_a_cuotas] Pago ID {pago.id} no tiene prestamo_id. " f"No se aplicará a cuotas.")
        return 0

    from datetime import date

    from app.models.prestamo import Prestamo

    # ✅ VERIFICACIÓN DE CÉDULA: Verificar que la cédula del pago coincida con la del préstamo
    prestamo = db.query(Prestamo).filter(Prestamo.id == pago.prestamo_id).first()
    if not prestamo:
        logger.error(f"❌ [aplicar_pago_a_cuotas] Préstamo {pago.prestamo_id} no encontrado")
        return 0

    if pago.cedula_cliente and prestamo.cedula and pago.cedula_cliente != prestamo.cedula:
        logger.error(
            f"❌ [aplicar_pago_a_cuotas] Cédula del pago ({pago.cedula_cliente}) "
            f"no coincide con cédula del préstamo ({prestamo.cedula}). "
            f"No se aplicará el pago a las cuotas."
        )
        return 0

    logger.info(
        f"🔄 [aplicar_pago_a_cuotas] Aplicando pago ID {pago.id} "
        f"(monto: ${pago.monto_pagado}, prestamo_id: {pago.prestamo_id}, cedula: {pago.cedula_cliente})"
    )

    # ✅ ORDENAMIENTO: Ordenar por fecha_vencimiento (más antigua primero), luego por numero_cuota
    # Esto asegura que se cubran primero las cuotas más antiguas según su fecha de vencimiento
    cuotas = (
        db.query(Cuota)
        .filter(
            Cuota.prestamo_id == pago.prestamo_id,
            Cuota.estado != "PAGADO",
        )
        .order_by(Cuota.fecha_vencimiento, Cuota.numero_cuota)  # ✅ Más antigua primero por fecha_vencimiento
        .all()
    )

    logger.info(f"📋 [aplicar_pago_a_cuotas] Préstamo {pago.prestamo_id}: " f"{len(cuotas)} cuotas no pagadas encontradas")

    if len(cuotas) == 0:
        logger.warning(
            f"⚠️ [aplicar_pago_a_cuotas] Préstamo {pago.prestamo_id} no tiene cuotas pendientes. " f"No se aplicará el pago."
        )
        return 0

    saldo_restante = pago.monto_pagado
    cuotas_completadas = 0
    fecha_hoy = date.today()

    for cuota in cuotas:
        if saldo_restante <= Decimal("0.00"):
            break

        monto_faltante = cuota.monto_cuota - cuota.total_pagado
        monto_aplicar = min(saldo_restante, monto_faltante)

        if monto_aplicar <= Decimal("0.00"):
            continue

        if _aplicar_monto_a_cuota(cuota, monto_aplicar, pago.fecha_pago, fecha_hoy):
            cuotas_completadas += 1

        saldo_restante -= monto_aplicar
        logger.debug(
            f"  💰 [aplicar_pago_a_cuotas] Cuota #{cuota.numero_cuota}: "
            f"Aplicado ${monto_aplicar}, Saldo restante: ${saldo_restante}, "
            f"Estado: {cuota.estado}"
        )

    if saldo_restante > Decimal("0.00"):
        logger.info(
            f"📊 [aplicar_pago_a_cuotas] Saldo restante: ${saldo_restante}. " f"Aplicando a siguiente cuota pendiente..."
        )
        cuotas_completadas += _aplicar_exceso_a_siguiente_cuota(
            db, pago.prestamo_id, saldo_restante, pago.fecha_pago, fecha_hoy
        )

    try:
        db.commit()
        logger.info(
            f"✅ [aplicar_pago_a_cuotas] Pago ID {pago.id} aplicado exitosamente. " f"Cuotas completadas: {cuotas_completadas}"
        )
    except Exception as e:
        logger.error(
            f"❌ [aplicar_pago_a_cuotas] Error al guardar cambios en BD: {str(e)}",
            exc_info=True,
        )
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
    - saldoPorCobrar: Suma de capital_pendiente + interes_pendiente + monto_mora de todas las cuotas no pagadas
    - clientesEnMora: Conteo de clientes únicos con cuotas vencidas y no pagadas
    - clientesAlDia: Conteo de clientes únicos sin cuotas vencidas sin pagar

    Los KPIs son fijos por mes (mes/año especificados o mes/año actual)
    """
    try:
        from datetime import date, datetime

        # Determinar mes y año (default: mes/año actual)
        hoy = date.today()
        mes_consulta = mes if mes is not None else hoy.month
        año_consulta = año if año is not None else hoy.year

        # Validar mes
        if mes_consulta < 1 or mes_consulta > 12:
            raise HTTPException(status_code=400, detail="El mes debe estar entre 1 y 12")

        # Fecha inicio y fin del mes
        fecha_inicio_mes = date(año_consulta, mes_consulta, 1)
        # Calcular último día del mes
        if mes_consulta == 12:
            fecha_fin_mes = date(año_consulta + 1, 1, 1)
        else:
            fecha_fin_mes = date(año_consulta, mes_consulta + 1, 1)

        logger.info(f"📊 [kpis_pagos] Calculando KPIs para mes {mes_consulta}/{año_consulta}")
        logger.info(f"📅 [kpis_pagos] Rango de fechas: {fecha_inicio_mes} a {fecha_fin_mes}")

        # 1. MONTO COBRADO EN EL MES
        # Suma de todos los pagos del mes especificado (DATOS REALES DESDE BD - SIN VALORES HARDCODEADOS)
        logger.info(
            f"🔍 [kpis_pagos] Consultando pagos del {mes_consulta}/{año_consulta} "
            f"(desde {fecha_inicio_mes} hasta {fecha_fin_mes})"
        )

        # Usar PagoStaging (donde están los datos reales)
        monto_cobrado_mes_query = db.query(func.sum(PagoStaging.monto_pagado)).filter(
            PagoStaging.fecha_pago >= datetime.combine(fecha_inicio_mes, datetime.min.time()),
            PagoStaging.fecha_pago < datetime.combine(fecha_fin_mes, datetime.min.time()),
        )
        monto_cobrado_mes = monto_cobrado_mes_query.scalar() or Decimal("0.00")

        # Log detallado para verificación
        total_pagos_mes = (
            db.query(func.count(PagoStaging.id))
            .filter(
                PagoStaging.fecha_pago >= datetime.combine(fecha_inicio_mes, datetime.min.time()),
                PagoStaging.fecha_pago < datetime.combine(fecha_fin_mes, datetime.min.time()),
            )
            .scalar()
            or 0
        )

        # ✅ DIAGNÓSTICO: Verificar algunos pagos reales del mes
        pagos_ejemplo_mes = (
            db.query(
                PagoStaging.id,
                PagoStaging.monto_pagado,
                PagoStaging.fecha_pago,
                PagoStaging.cedula_cliente,
                PagoStaging.cedula,
            )
            .filter(
                PagoStaging.fecha_pago >= datetime.combine(fecha_inicio_mes, datetime.min.time()),
                PagoStaging.fecha_pago < datetime.combine(fecha_fin_mes, datetime.min.time()),
            )
            .limit(5)
            .all()
        )

        logger.info(
            f"💰 [kpis_pagos] Monto cobrado en el mes: ${monto_cobrado_mes:,.2f} "
            f"(de {total_pagos_mes} pagos - DATOS REALES DESDE BD)"
        )

        if pagos_ejemplo_mes:
            ejemplos_pagos = "; ".join(
                [f"Pago ID {p.id}: ${float(p.monto_pagado):,.2f} ({p.fecha_pago.date()})" for p in pagos_ejemplo_mes[:3]]
            )
            logger.info(f"📋 [kpis_pagos] Ejemplos de pagos del mes: {ejemplos_pagos}")
        else:
            logger.info(f"⚠️ [kpis_pagos] No se encontraron pagos en el mes {mes_consulta}/{año_consulta}")

        # 2. SALDO POR COBRAR
        # Suma de capital_pendiente + interes_pendiente + monto_mora de todas las cuotas no pagadas (DATOS REALES DESDE BD - SIN VALORES HARDCODEADOS)
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

        # Log detallado para verificación
        total_cuotas_pendientes = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.estado != "PAGADO",
                Prestamo.estado == "APROBADO",
            )
            .scalar()
            or 0
        )

        # ✅ DIAGNÓSTICO: Verificar algunas cuotas pendientes reales
        cuotas_pendientes_ejemplo = (
            db.query(
                Cuota.id,
                Cuota.prestamo_id,
                Cuota.capital_pendiente,
                Cuota.interes_pendiente,
                Cuota.monto_mora,
                Cuota.estado,
            )
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.estado != "PAGADO",
                Prestamo.estado == "APROBADO",
            )
            .limit(5)
            .all()
        )

        logger.info(
            f"💳 [kpis_pagos] Saldo por cobrar: ${saldo_por_cobrar:,.2f} "
            f"(de {total_cuotas_pendientes} cuotas pendientes - DATOS REALES DESDE BD)"
        )

        if cuotas_pendientes_ejemplo:
            ejemplos_cuotas = "; ".join(
                [
                    f"Cuota ID {c.id} (Préstamo {c.prestamo_id}): "
                    f"${float(c.capital_pendiente + c.interes_pendiente + (c.monto_mora or 0)):,.2f} ({c.estado})"
                    for c in cuotas_pendientes_ejemplo[:3]
                ]
            )
            logger.info(f"📋 [kpis_pagos] Ejemplos de cuotas pendientes: {ejemplos_cuotas}")

        # 3. CLIENTES EN MORA
        # Clientes únicos con cuotas vencidas Y con pago incompleto (total_pagado < monto_cuota) (DATOS REALES DESDE BD)
        # Esto asegura que pagos parciales cuenten como mora si están vencidos

        # ✅ DIAGNÓSTICO: Verificar datos en BD antes del cálculo
        total_prestamos_aprobados = db.query(func.count(Prestamo.id)).filter(Prestamo.estado == "APROBADO").scalar() or 0
        total_cuotas = db.query(func.count(Cuota.id)).scalar() or 0
        cuotas_vencidas = db.query(func.count(Cuota.id)).filter(Cuota.fecha_vencimiento < hoy).scalar() or 0
        cuotas_pendientes = db.query(func.count(Cuota.id)).filter(Cuota.estado != "PAGADO").scalar() or 0

        # ✅ DIAGNÓSTICO ADICIONAL: Contar clientes únicos con préstamos aprobados
        clientes_unicos_aprobados = (
            db.query(func.count(func.distinct(Prestamo.cedula))).filter(Prestamo.estado == "APROBADO").scalar() or 0
        )

        # ✅ DIAGNÓSTICO ADICIONAL: Contar préstamos aprobados CON cuotas generadas
        prestamos_con_cuotas = (
            db.query(func.count(func.distinct(Prestamo.id)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar()
            or 0
        )

        # ✅ DIAGNÓSTICO ADICIONAL: Contar cuotas de préstamos aprobados
        cuotas_prestamos_aprobados = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar()
            or 0
        )

        logger.info(
            f"🔍 [kpis_pagos] DIAGNÓSTICO PRE-CÁLCULO: "
            f"Préstamos aprobados={total_prestamos_aprobados}, "
            f"Préstamos aprobados CON cuotas={prestamos_con_cuotas}, "
            f"Clientes únicos aprobados={clientes_unicos_aprobados}, "
            f"Total cuotas={total_cuotas}, "
            f"Cuotas de préstamos aprobados={cuotas_prestamos_aprobados}, "
            f"Cuotas vencidas={cuotas_vencidas}, "
            f"Cuotas pendientes={cuotas_pendientes}, "
            f"Fecha hoy={hoy}"
        )

        clientes_en_mora_query = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
                Prestamo.estado == "APROBADO",
            )
        )
        clientes_en_mora = clientes_en_mora_query.scalar() or 0

        # Log detallado para verificación
        cuotas_en_mora_count = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
                Prestamo.estado == "APROBADO",
            )
            .scalar()
            or 0
        )

        # ✅ DIAGNÓSTICO ADICIONAL: Verificar si hay clientes con préstamos pero sin cuotas
        clientes_sin_cuotas = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .filter(
                Prestamo.estado == "APROBADO",
                ~Prestamo.id.in_(db.query(Cuota.prestamo_id).distinct()),
            )
            .scalar()
            or 0
        )

        # ✅ DIAGNÓSTICO ADICIONAL: Detalles de cuotas en mora
        # Obtener algunos ejemplos de cuotas en mora para verificación
        cuotas_mora_ejemplo = (
            db.query(
                Cuota.id,
                Cuota.prestamo_id,
                Cuota.fecha_vencimiento,
                Cuota.total_pagado,
                Cuota.monto_cuota,
            )
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
                Prestamo.estado == "APROBADO",
            )
            .limit(5)
            .all()
        )

        ejemplos_info = []
        for c in cuotas_mora_ejemplo:
            ejemplos_info.append(
                f"Cuota ID {c.id} (Préstamo {c.prestamo_id}): "
                f"Vencida {c.fecha_vencimiento}, "
                f"Pagado ${float(c.total_pagado):.2f} de ${float(c.monto_cuota):.2f}"
            )

        logger.info(
            f"⚠️ [kpis_pagos] Clientes en mora: {clientes_en_mora} "
            f"(con {cuotas_en_mora_count} cuotas vencidas e incompletas), "
            f"Clientes aprobados sin cuotas={clientes_sin_cuotas}"
        )

        if ejemplos_info:
            logger.info(
                f"📋 [kpis_pagos] Ejemplos de cuotas en mora ({min(len(ejemplos_info), 3)}): " + "; ".join(ejemplos_info[:3])
            )
        else:
            logger.info(
                "✅ [kpis_pagos] No hay cuotas en mora detectadas (todas las cuotas están pagadas o no están vencidas)"
            )
        # 4. CLIENTES AL DÍA
        # Clientes únicos que tienen préstamos aprobados pero NO tienen cuotas vencidas sin pagar
        # Es decir: clientes con préstamos aprobados que no están en la lista de clientes en mora
        # O clientes que tienen todas sus cuotas vencidas pagadas o no tienen cuotas vencidas

        # Primero obtener todos los clientes con préstamos aprobados
        todos_clientes_aprobados = (
            db.query(func.count(func.distinct(Prestamo.cedula))).filter(Prestamo.estado == "APROBADO").scalar() or 0
        )

        # ✅ CÁLCULO MEJORADO: Clientes al día deben tener préstamos aprobados CON cuotas generadas
        # No contar clientes que tienen préstamos pero aún no tienen tabla de amortización
        clientes_con_cuotas = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(Prestamo.estado == "APROBADO")
            .scalar()
            or 0
        )

        # Clientes al día = clientes con préstamos aprobados Y cuotas - clientes en mora
        # (Un cliente al día es uno que tiene préstamos aprobados con cuotas pero no está en mora)
        clientes_al_dia = max(0, clientes_con_cuotas - clientes_en_mora)

        logger.info(
            f"✅ [kpis_pagos] Clientes al día: {clientes_al_dia} "
            f"(de {clientes_con_cuotas} clientes con cuotas, "
            f"{todos_clientes_aprobados} totales aprobados, "
            f"{clientes_en_mora} en mora)"
        )

        # ✅ LOG FINAL CONFIRMANDO QUE SON DATOS REALES
        logger.info(
            f"✅ [kpis_pagos] ===== KPIs CALCULADOS CON DATOS REALES DE BD ===== "
            f"Monto Cobrado=${float(monto_cobrado_mes):,.2f}, "
            f"Saldo por Cobrar=${float(saldo_por_cobrar):,.2f}, "
            f"Clientes en Mora={clientes_en_mora}, "
            f"Clientes al Día={clientes_al_dia} "
            f"(Mes: {mes_consulta}/{año_consulta})"
        )

        return {
            "montoCobradoMes": float(monto_cobrado_mes),
            "saldoPorCobrar": float(saldo_por_cobrar),
            "clientesEnMora": clientes_en_mora,
            "clientesAlDia": clientes_al_dia,
            "mes": mes_consulta,
            "año": año_consulta,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [kpis_pagos] Error obteniendo KPIs: {e}", exc_info=True)
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

        # ✅ Base query para pagos - usar FiltrosDashboard (usa PagoStaging donde están los datos)
        base_pago_query = db.query(PagoStaging)
        if analista or concesionario or modelo:
            base_pago_query = base_pago_query.join(Prestamo, PagoStaging.prestamo_id == Prestamo.id)
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

        # Pagos por estado (requiere subquery si hay filtros)
        pagos_por_estado_query = base_pago_query.subquery()
        if analista or concesionario or modelo:
            pagos_por_estado = (
                db.query(
                    pagos_por_estado_query.c.estado,
                    func.count(pagos_por_estado_query.c.id),
                )
                .group_by(pagos_por_estado_query.c.estado)
                .all()
            )
        else:
            pagos_por_estado = db.query(PagoStaging.estado, func.count(PagoStaging.id)).group_by(PagoStaging.estado).all()

        # Monto total pagado
        total_pagado = base_pago_query.with_entities(func.sum(PagoStaging.monto_pagado)).scalar() or Decimal("0.00")

        # Pagos del día actual
        pagos_hoy_query = base_pago_query.filter(func.date(PagoStaging.fecha_pago) == hoy)
        pagos_hoy = pagos_hoy_query.with_entities(func.sum(PagoStaging.monto_pagado)).scalar() or Decimal("0.00")

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
# ENDPOINTS PARA PAGOS_STAGING
# ============================================


@router.get("/staging")
def listar_pagos_staging(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    cedula: Optional[str] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar pagos de la tabla pagos_staging con filtros y paginación
    """
    try:
        logger.info(f"📋 [listar_pagos_staging] Consultando pagos_staging - página {page}, por página {per_page}")

        # Verificar si la tabla existe
        try:
            test_query = db.query(func.count(PagoStaging.id)).scalar()
            logger.info(f"✅ [listar_pagos_staging] Conexión a pagos_staging OK. Total registros: {test_query}")
        except Exception as db_error:
            logger.error(f"❌ [listar_pagos_staging] Error de conexión a pagos_staging: {db_error}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error de conexión a pagos_staging: {str(db_error)}",
            )

        query = db.query(PagoStaging)

        # Aplicar filtros
        if cedula:
            query = query.filter(or_(PagoStaging.cedula_cliente == cedula, PagoStaging.cedula == cedula))
            logger.info(f"🔍 [listar_pagos_staging] Filtro cédula: {cedula}")
        if estado:
            query = query.filter(PagoStaging.estado == estado)
            logger.info(f"🔍 [listar_pagos_staging] Filtro estado: {estado}")

        # Contar total antes de aplicar paginación
        total = query.count()
        logger.info(f"📊 [listar_pagos_staging] Total registros encontrados (sin paginación): {total}")

        # Ordenar por fecha de registro descendente (más actual primero)
        if hasattr(PagoStaging, "fecha_registro"):
            query = query.order_by(PagoStaging.fecha_registro.desc(), PagoStaging.id.desc())
        else:
            query = query.order_by(PagoStaging.id.desc())

        # Paginación
        from app.utils.pagination import calculate_pagination_params, create_paginated_response

        skip, limit = calculate_pagination_params(page=page, per_page=per_page, max_per_page=100)
        pagos_staging = query.offset(skip).limit(limit).all()
        logger.info(f"📄 [listar_pagos_staging] Registros obtenidos: {len(pagos_staging)}")

        # Serializar resultados
        items = [
            {
                "id": p.id,
                "cedula_cliente": p.cedula_cliente or p.cedula,
                "cedula": p.cedula,
                "prestamo_id": p.prestamo_id,
                "numero_cuota": p.numero_cuota,
                "fecha_pago": p.fecha_pago.isoformat() if p.fecha_pago else None,
                "fecha_registro": p.fecha_registro.isoformat() if p.fecha_registro else None,
                "monto_pagado": float(p.monto_pagado) if p.monto_pagado else None,
                "numero_documento": p.numero_documento,
                "institucion_bancaria": p.institucion_bancaria,
                "estado": p.estado,
                "conciliado": p.conciliado,
                "notas": p.notas,
            }
            for p in pagos_staging
        ]

        return create_paginated_response(items=items, total=total, page=page, page_size=limit)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [listar_pagos_staging] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al listar pagos_staging: {str(e)}")


@router.get("/staging/estadisticas")
def estadisticas_pagos_staging(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estadísticas de la tabla pagos_staging
    """
    try:
        logger.info("📊 [estadisticas_pagos_staging] Obteniendo estadísticas de pagos_staging")

        # Verificar si la tabla existe
        try:
            total_registros = db.query(func.count(PagoStaging.id)).scalar() or 0
        except Exception as db_error:
            logger.error(f"❌ [estadisticas_pagos_staging] Error de conexión: {db_error}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error de conexión a pagos_staging: {str(db_error)}",
            )

        if total_registros == 0:
            return {
                "total_registros": 0,
                "con_datos_completos": 0,
                "con_cedula": 0,
                "con_fecha_pago": 0,
                "con_monto": 0,
                "sin_prestamo_id": 0,
                "por_estado": {},
            }

        # Estadísticas detalladas
        con_cedula = (
            db.query(func.count(PagoStaging.id))
            .filter(or_(PagoStaging.cedula_cliente.isnot(None), PagoStaging.cedula.isnot(None)))
            .scalar()
            or 0
        )

        con_fecha_pago = db.query(func.count(PagoStaging.id)).filter(PagoStaging.fecha_pago.isnot(None)).scalar() or 0

        con_monto = (
            db.query(func.count(PagoStaging.id))
            .filter(PagoStaging.monto_pagado.isnot(None), PagoStaging.monto_pagado > 0)
            .scalar()
            or 0
        )

        sin_prestamo_id = db.query(func.count(PagoStaging.id)).filter(PagoStaging.prestamo_id.is_(None)).scalar() or 0

        con_datos_completos = (
            db.query(func.count(PagoStaging.id))
            .filter(
                or_(PagoStaging.cedula_cliente.isnot(None), PagoStaging.cedula.isnot(None)),
                PagoStaging.fecha_pago.isnot(None),
                PagoStaging.monto_pagado.isnot(None),
                PagoStaging.monto_pagado > 0,
            )
            .scalar()
            or 0
        )

        # Por estado
        query_estado = (
            db.query(PagoStaging.estado, func.count(PagoStaging.id).label("cantidad")).group_by(PagoStaging.estado).all()
        )

        por_estado = {estado or "SIN_ESTADO": cantidad for estado, cantidad in query_estado}

        estadisticas = {
            "total_registros": total_registros,
            "con_datos_completos": con_datos_completos,
            "con_cedula": con_cedula,
            "con_fecha_pago": con_fecha_pago,
            "con_monto": con_monto,
            "sin_prestamo_id": sin_prestamo_id,
            "por_estado": por_estado,
        }

        logger.info(f"✅ [estadisticas_pagos_staging] Estadísticas obtenidas: {estadisticas}")
        return estadisticas

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [estadisticas_pagos_staging] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}")


@router.post("/staging/migrar/{pago_staging_id}")
def migrar_pago_staging_a_pagos(
    pago_staging_id: int = Path(..., description="ID del pago en staging a migrar"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Migra un pago de pagos_staging a la tabla pagos
    """
    try:
        logger.info(f"🔄 [migrar_pago_staging] Iniciando migración de pago_staging_id={pago_staging_id}")

        # Buscar el pago en staging
        pago_staging = db.query(PagoStaging).filter(PagoStaging.id == pago_staging_id).first()

        if not pago_staging:
            raise HTTPException(status_code=404, detail=f"Pago staging con ID {pago_staging_id} no encontrado")

        # Validar que tenga datos mínimos
        cedula_final = pago_staging.cedula_cliente or pago_staging.cedula
        if not cedula_final:
            raise HTTPException(status_code=400, detail="El pago staging no tiene cédula de cliente (cedula_cliente o cedula)")
        if not pago_staging.fecha_pago:
            raise HTTPException(status_code=400, detail="El pago staging no tiene fecha_pago")
        if not pago_staging.monto_pagado or pago_staging.monto_pagado <= 0:
            raise HTTPException(status_code=400, detail="El pago staging no tiene monto_pagado válido")
        if not pago_staging.numero_documento:
            raise HTTPException(status_code=400, detail="El pago staging no tiene numero_documento")

        # Crear el pago en la tabla principal
        nuevo_pago = Pago(
            cedula_cliente=cedula_final,
            prestamo_id=pago_staging.prestamo_id,
            numero_cuota=pago_staging.numero_cuota,
            fecha_pago=pago_staging.fecha_pago,
            fecha_registro=pago_staging.fecha_registro or datetime.now(),
            monto_pagado=pago_staging.monto_pagado,
            numero_documento=pago_staging.numero_documento,
            institucion_bancaria=pago_staging.institucion_bancaria,
            documento_nombre=pago_staging.documento_nombre,
            documento_tipo=pago_staging.documento_tipo,
            documento_tamaño=pago_staging.documento_tamaño,
            documento_ruta=pago_staging.documento_ruta,
            conciliado=pago_staging.conciliado or False,
            fecha_conciliacion=pago_staging.fecha_conciliacion,
            estado=pago_staging.estado or "PAGADO",
            activo=True,
            notas=pago_staging.notas,
            usuario_registro=current_user.email,
            verificado_concordancia=pago_staging.verificado_concordancia or "NO",
        )

        db.add(nuevo_pago)
        db.flush()  # Para obtener el ID

        logger.info(f"✅ [migrar_pago_staging] Pago creado en tabla principal con ID={nuevo_pago.id}")

        # Si tiene prestamo_id, intentar aplicar a cuotas
        if nuevo_pago.prestamo_id:
            try:
                # Llamar directamente a la función (está definida en este mismo archivo)
                aplicar_pago_a_cuotas(nuevo_pago, db, current_user)
                logger.info(f"✅ [migrar_pago_staging] Pago aplicado a cuotas del préstamo {nuevo_pago.prestamo_id}")
            except Exception as e:
                logger.warning(f"⚠️ [migrar_pago_staging] No se pudo aplicar pago a cuotas: {e}")

        # Eliminar de staging (opcional, comentar si se quiere mantener)
        # db.delete(pago_staging)
        # logger.info(f"🗑️ [migrar_pago_staging] Pago eliminado de staging")

        db.commit()

        return {
            "mensaje": "Pago migrado exitosamente",
            "pago_staging_id": pago_staging_id,
            "pago_id": nuevo_pago.id,
            "prestamo_id": nuevo_pago.prestamo_id,
            "monto": float(nuevo_pago.monto_pagado),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ [migrar_pago_staging] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al migrar pago: {str(e)}")


@router.get("/verificar-pagos-staging")
def verificar_conexion_pagos_staging(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint de diagnóstico para verificar la conexión y estado de pagos_staging
    """
    diagnostico = {
        "timestamp": datetime.now().isoformat(),
        "estado": "ok",
        "verificaciones": {},
        "errores": [],
        "datos": {},
    }

    try:
        # 1. Verificar que el modelo existe
        logger.info("🔍 [verificar_pagos_staging] Verificando modelo PagoStaging...")
        try:
            diagnostico["verificaciones"]["modelo_existe"] = {
                "status": "ok",
                "mensaje": "Modelo PagoStaging importado correctamente",
                "tablename": PagoStaging.__tablename__,
            }
        except Exception as e:
            diagnostico["verificaciones"]["modelo_existe"] = {
                "status": "error",
                "mensaje": f"Error al acceder al modelo: {str(e)}",
            }
            diagnostico["errores"].append(f"Modelo: {str(e)}")
            diagnostico["estado"] = "error"
            logger.error(f"❌ [verificar_pagos_staging] Error en modelo: {e}", exc_info=True)

        # 2. Verificar conexión básica a la tabla
        logger.info("🔍 [verificar_pagos_staging] Verificando conexión a tabla pagos_staging...")
        try:
            test_count = db.query(func.count(PagoStaging.id)).scalar()
            diagnostico["verificaciones"]["conexion_tabla"] = {
                "status": "ok",
                "mensaje": "Conexión a tabla pagos_staging exitosa",
                "total_registros": test_count or 0,
            }
            diagnostico["datos"]["total_registros"] = test_count or 0
        except Exception as e:
            diagnostico["verificaciones"]["conexion_tabla"] = {
                "status": "error",
                "mensaje": f"Error de conexión a tabla: {str(e)}",
            }
            diagnostico["errores"].append(f"Conexión tabla: {str(e)}")
            diagnostico["estado"] = "error"
            logger.error(f"❌ [verificar_pagos_staging] Error conexión tabla: {e}", exc_info=True)

        # 3. Verificar estructura de columnas
        logger.info("🔍 [verificar_pagos_staging] Verificando estructura de columnas...")
        try:
            # Intentar consultar diferentes columnas
            muestra = (
                db.query(
                    PagoStaging.id,
                    PagoStaging.cedula_cliente,
                    PagoStaging.cedula,
                    PagoStaging.prestamo_id,
                    PagoStaging.fecha_pago,
                    PagoStaging.monto_pagado,
                    PagoStaging.numero_documento,
                    PagoStaging.estado,
                    PagoStaging.conciliado,
                )
                .limit(1)
                .first()
            )

            columnas_verificadas = []
            if muestra:
                columnas_verificadas = [
                    "id",
                    "cedula_cliente",
                    "cedula",
                    "prestamo_id",
                    "fecha_pago",
                    "monto_pagado",
                    "numero_documento",
                    "estado",
                    "conciliado",
                ]

            diagnostico["verificaciones"]["estructura_columnas"] = {
                "status": "ok",
                "mensaje": "Estructura de columnas verificada",
                "columnas_verificadas": columnas_verificadas,
                "tiene_datos": muestra is not None,
            }
            diagnostico["datos"]["tiene_datos"] = muestra is not None
        except Exception as e:
            diagnostico["verificaciones"]["estructura_columnas"] = {
                "status": "error",
                "mensaje": f"Error verificando columnas: {str(e)}",
            }
            diagnostico["errores"].append(f"Estructura columnas: {str(e)}")
            diagnostico["estado"] = "error"
            logger.error(f"❌ [verificar_pagos_staging] Error estructura: {e}", exc_info=True)

        # 4. Consulta completa de ejemplo
        logger.info("🔍 [verificar_pagos_staging] Ejecutando consulta de ejemplo...")
        try:
            query_ejemplo = db.query(PagoStaging).limit(5).all()
            diagnostico["verificaciones"]["consulta_ejemplo"] = {
                "status": "ok",
                "mensaje": "Consulta de ejemplo ejecutada correctamente",
                "registros_obtenidos": len(query_ejemplo),
            }
            diagnostico["datos"]["muestra_registros"] = len(query_ejemplo)

            # Datos de muestra si existen
            if query_ejemplo:
                muestra_datos = []
                for p in query_ejemplo[:3]:
                    muestra_datos.append(
                        {
                            "id": p.id,
                            "cedula": p.cedula_cliente or p.cedula,
                            "monto": float(p.monto_pagado) if p.monto_pagado else None,
                            "fecha_pago": p.fecha_pago.isoformat() if p.fecha_pago else None,
                            "estado": p.estado,
                        }
                    )
                diagnostico["datos"]["muestra"] = muestra_datos
        except Exception as e:
            diagnostico["verificaciones"]["consulta_ejemplo"] = {
                "status": "error",
                "mensaje": f"Error en consulta ejemplo: {str(e)}",
            }
            diagnostico["errores"].append(f"Consulta ejemplo: {str(e)}")
            diagnostico["estado"] = "error"
            logger.error(f"❌ [verificar_pagos_staging] Error consulta: {e}", exc_info=True)

        # 5. Estadísticas rápidas
        logger.info("🔍 [verificar_pagos_staging] Calculando estadísticas...")
        try:
            total = db.query(func.count(PagoStaging.id)).scalar() or 0
            con_cedula = (
                db.query(func.count(PagoStaging.id))
                .filter(or_(PagoStaging.cedula_cliente.isnot(None), PagoStaging.cedula.isnot(None)))
                .scalar()
                or 0
            )
            con_fecha = db.query(func.count(PagoStaging.id)).filter(PagoStaging.fecha_pago.isnot(None)).scalar() or 0
            con_monto = (
                db.query(func.count(PagoStaging.id))
                .filter(PagoStaging.monto_pagado.isnot(None), PagoStaging.monto_pagado > 0)
                .scalar()
                or 0
            )

            diagnostico["datos"]["estadisticas"] = {
                "total": total,
                "con_cedula": con_cedula,
                "con_fecha_pago": con_fecha,
                "con_monto": con_monto,
                "completos": min(con_cedula, con_fecha, con_monto),
            }
            diagnostico["verificaciones"]["estadisticas"] = {
                "status": "ok",
                "mensaje": "Estadísticas calculadas correctamente",
            }
        except Exception as e:
            diagnostico["verificaciones"]["estadisticas"] = {
                "status": "error",
                "mensaje": f"Error calculando estadísticas: {str(e)}",
            }
            diagnostico["errores"].append(f"Estadísticas: {str(e)}")
            logger.warning(f"⚠️ [verificar_pagos_staging] Error estadísticas: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"❌ [verificar_pagos_staging] Error general: {e}", exc_info=True)
        diagnostico["estado"] = "error"
        diagnostico["errores"].append(f"Error general: {str(e)}")

    logger.info(f"✅ [verificar_pagos_staging] Diagnóstico completado - Estado: {diagnostico['estado']}")
    return diagnostico
