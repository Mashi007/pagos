"""
Endpoints para el módulo de Cobranzas
"""

import logging
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query  # type: ignore[import-untyped]
from fastapi.responses import StreamingResponse  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, field_validator  # type: ignore[import-untyped]
from openpyxl import Workbook  # type: ignore[import-untyped]
from openpyxl.styles import Alignment, Font, PatternFill  # type: ignore[import-untyped]
from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import getSampleStyleSheet  # type: ignore[import-untyped]
from reportlab.lib.units import inch  # type: ignore[import-untyped]
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # type: ignore[import-untyped]
from sqlalchemy import case, func, or_  # type: ignore[import-untyped]
from sqlalchemy.orm import Session  # type: ignore[import-untyped]

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_result
from app.models.amortizacion import Cuota
from app.models.auditoria import Auditoria
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.user import User
from app.services.notificacion_automatica_service import NotificacionAutomaticaService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
def healthcheck_cobranzas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Verificación rápida del módulo de Cobranzas y conexión a BD para Dashboard.

    Retorna métricas mínimas que confirman conectividad a la base de datos
    y disponibilidad de datos para alimentar el dashboard.
    """
    try:
        hoy = date.today()

        # Prueba simple de consulta (usa dependencias y pool configurado)
        total_cuotas = db.query(func.count(Cuota.id)).scalar() or 0

        # Métricas clave de cobranzas para dashboard
        # ✅ CRITERIO CORRECTO: fecha_vencimiento < hoy AND total_pagado < monto_cuota
        cuotas_vencidas = (
            db.query(func.count(Cuota.id))
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            )
            .scalar()
            or 0
        )

        monto_vencido = (
            db.query(func.sum(Cuota.monto_cuota))
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            )
            .scalar()
            or 0.0
        )

        return {
            "status": "ok",
            "database": True,
            "metrics": {
                "total_cuotas": int(total_cuotas),
                "cuotas_vencidas": int(cuotas_vencidas),
                "monto_vencido": float(monto_vencido),
            },
            "fecha_corte": hoy.isoformat(),
        }
    except Exception as e:
        logger.error(f"Healthcheck cobranzas error: {e}")
        raise HTTPException(status_code=500, detail="Error de conexión o consulta a la base de datos")


@router.get("/diagnostico")
def diagnostico_cobranzas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint de diagnóstico para identificar por qué no hay datos en cobranzas.
    Muestra información detallada sobre filtros y datos excluidos.
    """
    try:
        hoy = date.today()
        from app.core.config import settings

        diagnostico = {
            "fecha_corte": hoy.isoformat(),
            "criterios_aplicados": {
                "cuota_vencida": "fecha_vencimiento < hoy",
                "pago_incompleto": "total_pagado < monto_cuota",
                "estado_prestamo": ["APROBADO", "ACTIVO"],
                "excluir_admin": True,
                "admin_email": settings.ADMIN_EMAIL,
            },
            "diagnosticos": {},
        }

        # 1. Total de cuotas en la BD
        total_cuotas = db.query(func.count(Cuota.id)).scalar() or 0
        diagnostico["diagnosticos"]["total_cuotas_bd"] = total_cuotas

        # 2. Cuotas vencidas (sin filtros)
        cuotas_vencidas = db.query(func.count(Cuota.id)).filter(Cuota.fecha_vencimiento < hoy).scalar() or 0
        diagnostico["diagnosticos"]["cuotas_vencidas_solo_fecha"] = cuotas_vencidas

        # 3. Cuotas con pago incompleto (sin filtro de fecha)
        cuotas_pago_incompleto = db.query(func.count(Cuota.id)).filter(Cuota.total_pagado < Cuota.monto_cuota).scalar() or 0
        diagnostico["diagnosticos"]["cuotas_pago_incompleto"] = cuotas_pago_incompleto

        # 4. Cuotas vencidas Y pago incompleto (criterio base)
        cuotas_vencidas_incompletas = (
            db.query(func.count(Cuota.id))
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
            )
            .scalar()
            or 0
        )
        diagnostico["diagnosticos"]["cuotas_vencidas_incompletas"] = cuotas_vencidas_incompletas

        # 5. Estados de préstamos con cuotas vencidas
        estados_prestamos = (
            db.query(Prestamo.estado, func.count(func.distinct(Prestamo.id)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
            )
            .group_by(Prestamo.estado)
            .all()
        )
        diagnostico["diagnosticos"]["estados_prestamos_con_cuotas_vencidas"] = {
            estado: cantidad for estado, cantidad in estados_prestamos
        }

        # 6. Cuotas vencidas de préstamos APROBADO/ACTIVO
        cuotas_aprobado_activo = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado.in_(["APROBADO", "ACTIVO"]),
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
            )
            .scalar()
            or 0
        )
        diagnostico["diagnosticos"]["cuotas_aprobado_activo"] = cuotas_aprobado_activo

        # 7. Cuotas vencidas excluyendo admin
        cuotas_sin_admin = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
                Prestamo.usuario_proponente != settings.ADMIN_EMAIL,
            )
            .scalar()
            or 0
        )
        diagnostico["diagnosticos"]["cuotas_sin_admin"] = cuotas_sin_admin

        # 8. Cuotas vencidas con TODOS los filtros aplicados
        cuotas_final = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cedula == Cliente.cedula)
            .outerjoin(User, User.email == Prestamo.usuario_proponente)
            .filter(
                Prestamo.estado.in_(["APROBADO", "ACTIVO"]),
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
                Prestamo.usuario_proponente != settings.ADMIN_EMAIL,
                or_(User.is_admin.is_(False), User.is_admin.is_(None)),
            )
            .scalar()
            or 0
        )
        diagnostico["diagnosticos"]["cuotas_con_todos_filtros"] = cuotas_final

        # 9. Análisis de qué filtro está excluyendo más datos
        diagnostico["analisis_filtros"] = {
            "cuotas_perdidas_por_estado": cuotas_vencidas_incompletas - cuotas_aprobado_activo,
            "cuotas_perdidas_por_admin": cuotas_aprobado_activo - cuotas_sin_admin,
            "cuotas_perdidas_por_user_admin": cuotas_sin_admin - cuotas_final,
        }

        # 10. Ejemplo de cuotas vencidas (primeras 5)
        ejemplo_cuotas = (
            db.query(
                Cuota.id,
                Cuota.prestamo_id,
                Cuota.fecha_vencimiento,
                Cuota.monto_cuota,
                Cuota.total_pagado,
                Prestamo.estado,
                Prestamo.usuario_proponente,
            )
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
            )
            .limit(5)
            .all()
        )
        diagnostico["ejemplos_cuotas_vencidas"] = [
            {
                "cuota_id": c.id,
                "prestamo_id": c.prestamo_id,
                "fecha_vencimiento": c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else None,
                "monto_cuota": float(c.monto_cuota),
                "total_pagado": float(c.total_pagado),
                "estado_prestamo": c.estado,
                "usuario_proponente": c.usuario_proponente,
                "es_admin": c.usuario_proponente == settings.ADMIN_EMAIL,
            }
            for c in ejemplo_cuotas
        ]

        logger.info(f"🔍 [diagnostico_cobranzas] Diagnóstico completo: {diagnostico}")

        return diagnostico

    except Exception as e:
        logger.error(f"Error en diagnóstico de cobranzas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/clientes-atrasados")
@cache_result(ttl=300, key_prefix="cobranzas")  # Cache por 5 minutos
def obtener_clientes_atrasados(
    dias_retraso: Optional[int] = Query(None, description="Días de retraso para filtrar"),
    incluir_admin: bool = Query(False, description="Incluir datos del administrador para diagnóstico"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener clientes atrasados filtrados por días de retraso
    Excluye admin por defecto, pero puede incluirse con incluir_admin=true para diagnóstico
    Si no hay otros analistas en el sistema, incluye automáticamente al admin

    Args:
        dias_retraso: Filtrar por días específicos de retraso (1, 3, 5, etc.)
                     Si es None, devuelve todos los clientes atrasados
        incluir_admin: Si es True, incluye datos del administrador
    """
    start_time = time.time()

    try:
        # Calcular fecha límite según días de retraso
        hoy = date.today()

        # Cuotas vencidas (fecha_vencimiento < hoy y total_pagado < monto_cuota)
        # Excluir admin del listado
        from app.core.config import settings

        # Verificar si hay otros usuarios no-admin en el sistema
        otros_analistas = (
            db.query(func.count(User.id))
            .filter(User.is_active.is_(True), or_(User.is_admin.is_(False), User.is_admin.is_(None)))
            .scalar()
            or 0
        )

        # Si no hay otros analistas, incluir admin automáticamente
        if otros_analistas == 0:
            logger.info("🔍 [clientes_atrasados] No hay otros analistas, incluyendo admin automáticamente")
            incluir_admin = True

        # Optimización: Usar subquery para filtrar cuotas vencidas primero
        # Esto reduce el tamaño del dataset antes de hacer los JOINs
        # ✅ CRITERIO CORRECTO: Cuota vencida = fecha_vencimiento < hoy AND total_pagado < monto_cuota
        # Esto asegura consistencia con el módulo de pagos y otros módulos
        cuotas_filtros = [
            Cuota.fecha_vencimiento < hoy,
            Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto (incluye total_pagado = 0)
        ]

        # Si se especifica días de retraso, agregar filtro adicional
        if dias_retraso:
            fecha_limite = hoy - timedelta(days=dias_retraso)
            cuotas_filtros.append(Cuota.fecha_vencimiento <= fecha_limite)

        cuotas_vencidas_subq = (
            db.query(
                Cuota.prestamo_id,
                func.count(Cuota.id).label("cuotas_vencidas"),
                func.sum(Cuota.monto_cuota).label("total_adeudado"),
                func.min(Cuota.fecha_vencimiento).label("fecha_primera_vencida"),
            )
            .filter(*cuotas_filtros)
            .group_by(Cuota.prestamo_id)
            .subquery()
        )

        # Query principal con JOINs optimizados
        query_filters = [
            Prestamo.estado.in_(["APROBADO", "ACTIVO"]),  # Préstamos aprobados o activos
        ]

        # Aplicar filtro de admin solo si incluir_admin=False
        if not incluir_admin:
            query_filters.extend(
                [
                    Prestamo.usuario_proponente != settings.ADMIN_EMAIL,  # Excluir admin
                ]
            )

        query = (
            db.query(
                Cliente.cedula,
                Cliente.nombres,
                func.coalesce(Prestamo.analista, Prestamo.usuario_proponente).label("analista"),
                Prestamo.id.label("prestamo_id"),
                cuotas_vencidas_subq.c.cuotas_vencidas,
                cuotas_vencidas_subq.c.total_adeudado,
                cuotas_vencidas_subq.c.fecha_primera_vencida,
            )
            .join(Prestamo, Prestamo.cedula == Cliente.cedula)
            .join(cuotas_vencidas_subq, cuotas_vencidas_subq.c.prestamo_id == Prestamo.id)
            .outerjoin(User, User.email == Prestamo.usuario_proponente)
            .filter(*query_filters)
        )

        # Aplicar filtro de User.is_admin solo si incluir_admin=False
        if not incluir_admin:
            query = query.filter(or_(User.is_admin.is_(False), User.is_admin.is_(None)))  # Excluir admins

        resultados = query.all()

        query_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"📋 [clientes_atrasados] Encontrados {len(resultados)} clientes atrasados "
            f"(filtro días_retraso={dias_retraso}, query_time={query_time_ms}ms)"
        )

        # Convertir a diccionarios y agregar predicción ML Impago
        clientes_atrasados = []

        # Cargar modelo ML Impago una sola vez si está disponible
        ml_service = None
        modelo_cargado = False
        try:
            from app.models.modelo_impago_cuotas import ModeloImpagoCuotas

            modelo_activo = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).first()
            if modelo_activo:
                logger.info(f"🔍 [ML] Modelo ML Impago activo encontrado: {modelo_activo.nombre} (ID: {modelo_activo.id})")
                logger.info(f"   [ML] Ruta del modelo: {modelo_activo.ruta_archivo}")
                try:
                    from app.services.ml_impago_cuotas_service import ML_IMPAGO_SERVICE_AVAILABLE, MLImpagoCuotasService

                    if not ML_IMPAGO_SERVICE_AVAILABLE:
                        logger.warning("⚠️ [ML] ML_IMPAGO_SERVICE_AVAILABLE es False - scikit-learn no está disponible")
                    elif not MLImpagoCuotasService:
                        logger.warning("⚠️ [ML] MLImpagoCuotasService no está disponible")
                    else:
                        logger.info("✅ [ML] Servicio ML Impago disponible, intentando cargar modelo...")
                        ml_service = MLImpagoCuotasService()
                        if not ml_service.load_model_from_path(modelo_activo.ruta_archivo):
                            logger.error(f"❌ [ML] No se pudo cargar el modelo ML desde {modelo_activo.ruta_archivo}")
                            logger.error("   [ML] Verificar que el archivo existe y es accesible")
                            ml_service = None
                        else:
                            # Verificar que el modelo realmente se cargó
                            if "impago_cuotas_model" in ml_service.models:
                                logger.info(f"✅ [ML] Modelo ML Impago cargado correctamente: {modelo_activo.nombre}")
                                logger.info(f"   [ML] Modelo en memoria: {type(ml_service.models['impago_cuotas_model']).__name__}")
                                modelo_cargado = True
                            else:
                                logger.error("❌ [ML] Modelo no se cargó en memoria después de load_model_from_path")
                                ml_service = None
                except ImportError as e:
                    logger.error(f"❌ [ML] Error importando servicio ML Impago: {e}", exc_info=True)
            else:
                logger.warning("⚠️ [ML] No hay modelo ML Impago activo en la base de datos")
                logger.info("   [ML] Para activar un modelo, ve a la sección de entrenamiento de modelos ML")
        except Exception as e:
            logger.error(f"❌ [ML] Error cargando modelo ML Impago: {e}", exc_info=True)

        # Optimización: Cargar todos los préstamos de una vez
        prestamo_ids = [row.prestamo_id for row in resultados]
        prestamos_dict = {}
        if prestamo_ids:
            prestamos = db.query(Prestamo).filter(Prestamo.id.in_(prestamo_ids)).all()
            prestamos_dict = {p.id: p for p in prestamos}
            logger.info(f"📦 Cargados {len(prestamos_dict)} préstamos para procesamiento ML")

        # Optimización: Cargar todas las cuotas de una vez (solo para préstamos que necesitan ML)
        cuotas_dict = {}
        if ml_service and prestamo_ids:
            # Solo cargar cuotas para préstamos que no tienen valores manuales
            prestamos_sin_manual = [
                p_id for p_id, p in prestamos_dict.items()
                if p and p.estado == "APROBADO" and not (p.ml_impago_nivel_riesgo_manual and p.ml_impago_probabilidad_manual is not None)
            ]
            if prestamos_sin_manual:
                cuotas = db.query(Cuota).filter(Cuota.prestamo_id.in_(prestamos_sin_manual)).order_by(Cuota.prestamo_id, Cuota.numero_cuota).all()
                # Agrupar cuotas por préstamo_id
                for cuota in cuotas:
                    if cuota.prestamo_id not in cuotas_dict:
                        cuotas_dict[cuota.prestamo_id] = []
                    cuotas_dict[cuota.prestamo_id].append(cuota)
                logger.info(f"📦 Cargadas cuotas para {len(cuotas_dict)} préstamos")

        fecha_actual = date.today()
        ml_start_time = time.time()
        ml_processed = 0
        ml_manual = 0
        ml_calculated = 0
        ml_errors = 0
        
        for row in resultados:
            cliente_data = {
                "cedula": row.cedula,
                "nombres": row.nombres,
                "analista": row.analista,
                "prestamo_id": row.prestamo_id,
                "cuotas_vencidas": row.cuotas_vencidas,
                "total_adeudado": (float(row.total_adeudado) if row.total_adeudado else 0.0),
                "fecha_primera_vencida": (row.fecha_primera_vencida.isoformat() if row.fecha_primera_vencida else None),
            }

            # Agregar predicción ML Impago si está disponible
            # Priorizar valores manuales sobre calculados
            try:
                prestamo = prestamos_dict.get(row.prestamo_id)
                if prestamo and prestamo.estado == "APROBADO":
                    # Verificar si hay valores manuales
                    if prestamo.ml_impago_nivel_riesgo_manual and prestamo.ml_impago_probabilidad_manual is not None:
                        # Usar valores manuales
                        cliente_data["ml_impago"] = {
                            "probabilidad_impago": float(prestamo.ml_impago_probabilidad_manual),
                            "nivel_riesgo": prestamo.ml_impago_nivel_riesgo_manual,
                            "prediccion": "Manual",
                            "es_manual": True,
                        }
                        ml_manual += 1
                        ml_processed += 1
                    elif ml_service and modelo_cargado:
                        # Calcular con ML si no hay valores manuales
                        cuotas = cuotas_dict.get(prestamo.id, [])
                        if cuotas:
                            try:
                                features = ml_service.extract_payment_features(cuotas, prestamo, fecha_actual)
                                prediccion = ml_service.predict_impago(features)
                                
                                # Debug: Log primera predicción para verificar que funciona
                                if ml_calculated == 0:
                                    logger.info(f"🔍 [ML] Primera predicción exitosa - Préstamo {row.prestamo_id}: {prediccion.get('nivel_riesgo', 'N/A')}")

                                # Verificar si la predicción fue exitosa
                                if prediccion.get("prediccion") == "Error" or prediccion.get("prediccion") == "Desconocido":
                                    logger.debug(f"Predicción ML falló para préstamo {row.prestamo_id}: {prediccion.get('recomendacion', 'Error desconocido')}")
                                    cliente_data["ml_impago"] = None
                                else:
                                    cliente_data["ml_impago"] = {
                                        "probabilidad_impago": round(prediccion.get("probabilidad_impago", 0.0), 3),
                                        "nivel_riesgo": prediccion.get("nivel_riesgo", "Desconocido"),
                                        "prediccion": prediccion.get("prediccion", "Desconocido"),
                                        "es_manual": False,
                                    }
                                    ml_calculated += 1
                                    ml_processed += 1
                            except Exception as e:
                                logger.debug(f"Error calculando predicción ML para préstamo {row.prestamo_id}: {e}")
                                cliente_data["ml_impago"] = None
                                ml_errors += 1
                                ml_processed += 1
                        else:
                            cliente_data["ml_impago"] = None
                    else:
                        cliente_data["ml_impago"] = None
                else:
                    cliente_data["ml_impago"] = None
            except Exception as e:
                logger.debug(f"Error obteniendo predicción ML para préstamo {row.prestamo_id}: {e}")
                cliente_data["ml_impago"] = None

            clientes_atrasados.append(cliente_data)

        ml_time_ms = int((time.time() - ml_start_time) * 1000)
        total_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"✅ [clientes_atrasados] Procesamiento completado: "
            f"{len(clientes_atrasados)} clientes, "
            f"ML procesados: {ml_processed} (manuales: {ml_manual}, calculados: {ml_calculated}, errores: {ml_errors}), "
            f"tiempo_total={total_time_ms}ms, tiempo_ml={ml_time_ms}ms"
        )

        return clientes_atrasados

    except Exception as e:
        logger.error(f"Error obteniendo clientes atrasados: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/clientes-por-cantidad-pagos")
def obtener_clientes_por_cantidad_pagos_atrasados(
    cantidad_pagos: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener clientes que tienen exactamente N cantidad de pagos atrasados
    """
    try:
        hoy = date.today()

        query = (
            db.query(
                Cliente.cedula,
                Cliente.nombres,
                func.coalesce(Prestamo.analista, Prestamo.usuario_proponente).label("analista"),
                Prestamo.id.label("prestamo_id"),
                func.sum(Cuota.monto_cuota).label("total_adeudado"),
            )
            .join(Prestamo, Prestamo.cedula == Cliente.cedula)
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            )
            .group_by(
                Cliente.cedula,
                Cliente.nombres,
                Prestamo.analista,
                Prestamo.usuario_proponente,
                Prestamo.id,
            )
            .having(func.count(Cuota.id) == cantidad_pagos)
        )

        resultados = query.all()

        # Cargar modelo ML Impago una sola vez si está disponible
        ml_service = None
        try:
            from app.models.modelo_impago_cuotas import ModeloImpagoCuotas

            modelo_activo = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).first()
            if modelo_activo:
                try:
                    from app.services.ml_impago_cuotas_service import ML_IMPAGO_SERVICE_AVAILABLE, MLImpagoCuotasService

                    if ML_IMPAGO_SERVICE_AVAILABLE and MLImpagoCuotasService:
                        ml_service = MLImpagoCuotasService()
                        if not ml_service.load_model_from_path(modelo_activo.ruta_archivo):
                            logger.warning(f"No se pudo cargar el modelo ML desde {modelo_activo.ruta_archivo}")
                            ml_service = None
                        else:
                            logger.info(f"Modelo ML Impago cargado correctamente: {modelo_activo.nombre}")
                    else:
                        logger.debug("ML_IMPAGO_SERVICE_AVAILABLE es False o MLImpagoCuotasService no está disponible")
                except ImportError as e:
                    logger.warning(f"Error importando servicio ML Impago: {e}")
            else:
                logger.debug("No hay modelo ML Impago activo en la base de datos")
        except Exception as e:
            logger.warning(f"Error cargando modelo ML Impago: {e}", exc_info=True)

        clientes = []
        for row in resultados:
            cliente_data = {
                "cedula": row.cedula,
                "nombres": row.nombres,
                "analista": row.analista,
                "prestamo_id": row.prestamo_id,
                "total_adeudado": (float(row.total_adeudado) if row.total_adeudado else 0.0),
            }

            # Agregar predicción ML Impago si está disponible
            # Priorizar valores manuales sobre calculados
            try:
                prestamo = db.query(Prestamo).filter(Prestamo.id == row.prestamo_id).first()
                if prestamo and prestamo.estado == "APROBADO":
                    # Verificar si hay valores manuales
                    if prestamo.ml_impago_nivel_riesgo_manual and prestamo.ml_impago_probabilidad_manual is not None:
                        # Usar valores manuales
                        cliente_data["ml_impago"] = {
                            "probabilidad_impago": float(prestamo.ml_impago_probabilidad_manual),
                            "nivel_riesgo": prestamo.ml_impago_nivel_riesgo_manual,
                            "prediccion": "Manual",
                            "es_manual": True,
                        }
                    elif ml_service:
                        # Calcular con ML si no hay valores manuales
                        cuotas = db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).order_by(Cuota.numero_cuota).all()
                        if cuotas:
                            try:
                                fecha_actual = date.today()
                                features = ml_service.extract_payment_features(cuotas, prestamo, fecha_actual)
                                prediccion = ml_service.predict_impago(features)

                                # Verificar si la predicción fue exitosa
                                if prediccion.get("prediccion") == "Error" or prediccion.get("prediccion") == "Desconocido":
                                    logger.warning(f"Predicción ML falló para préstamo {row.prestamo_id}: {prediccion.get('recomendacion', 'Error desconocido')}")
                                    cliente_data["ml_impago"] = None
                                else:
                                    cliente_data["ml_impago"] = {
                                        "probabilidad_impago": round(prediccion.get("probabilidad_impago", 0.0), 3),
                                        "nivel_riesgo": prediccion.get("nivel_riesgo", "Desconocido"),
                                        "prediccion": prediccion.get("prediccion", "Desconocido"),
                                        "es_manual": False,
                                    }
                            except Exception as e:
                                logger.warning(f"Error calculando predicción ML para préstamo {row.prestamo_id}: {e}", exc_info=True)
                                cliente_data["ml_impago"] = None
                        else:
                            logger.debug(f"No hay cuotas para préstamo {row.prestamo_id}, no se puede calcular ML Impago")
                            cliente_data["ml_impago"] = None
                    else:
                        logger.debug(f"Servicio ML no disponible para préstamo {row.prestamo_id}")
                        cliente_data["ml_impago"] = None
            except Exception as e:
                logger.warning(f"Error obteniendo predicción ML para préstamo {row.prestamo_id}: {e}", exc_info=True)
                cliente_data["ml_impago"] = None

            clientes.append(cliente_data)

        return clientes

    except Exception as e:
        logger.error(f"Error obteniendo clientes por cantidad de pagos: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/por-analista")
def obtener_cobranzas_por_analista(
    incluir_admin: bool = Query(False, description="Incluir datos del administrador para diagnóstico"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estadísticas de cobranza por analista
    - Cantidad de clientes atrasados
    - Monto total sin cobrar
    Excluye admin por defecto, pero puede incluirse con incluir_admin=true para diagnóstico
    Si no hay otros analistas en el sistema, incluye automáticamente al admin
    """
    try:
        hoy = date.today()

        # Excluir admin del listado de analistas
        from app.core.config import settings

        # Verificar si hay otros usuarios no-admin en el sistema
        otros_analistas = (
            db.query(func.count(User.id))
            .filter(User.is_active.is_(True), or_(User.is_admin.is_(False), User.is_admin.is_(None)))
            .scalar()
            or 0
        )

        # Si no hay otros analistas, incluir admin automáticamente
        if otros_analistas == 0:
            logger.info("🔍 [por_analista] No hay otros analistas, incluyendo admin automáticamente")
            incluir_admin = True

        query_filters = [
            Prestamo.estado.in_(["APROBADO", "ACTIVO"]),  # Préstamos aprobados o activos
            Cuota.fecha_vencimiento < hoy,
            Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            Prestamo.usuario_proponente.isnot(None),
        ]

        # Aplicar filtro de admin solo si incluir_admin=False
        if not incluir_admin:
            query_filters.extend(
                [
                    Prestamo.usuario_proponente != settings.ADMIN_EMAIL,  # Excluir admin
                ]
            )

        query = (
            db.query(
                func.coalesce(Prestamo.analista, Prestamo.usuario_proponente).label("nombre_analista"),
                func.count(func.distinct(Cliente.cedula)).label("cantidad_clientes"),
                func.sum(Cuota.monto_cuota).label("monto_total"),
            )
            .join(Cliente, Cliente.cedula == Prestamo.cedula)
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .outerjoin(User, User.email == Prestamo.usuario_proponente)
            .filter(*query_filters)
        )

        # Aplicar filtro de User.is_admin solo si incluir_admin=False
        if not incluir_admin:
            query = query.filter(or_(User.is_admin.is_(False), User.is_admin.is_(None)))  # Excluir admins

        query = query.group_by(Prestamo.analista, Prestamo.usuario_proponente).having(
            func.count(func.distinct(Cliente.cedula)) > 0
        )

        resultados = query.all()

        analistas = []
        for row in resultados:
            analistas.append(
                {
                    "nombre": row.nombre_analista,
                    "cantidad_clientes": row.cantidad_clientes,
                    "monto_total": float(row.monto_total) if row.monto_total else 0.0,
                }
            )

        return analistas

    except Exception as e:
        logger.error(f"Error obteniendo cobranzas por analista: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/por-analista/{analista}/clientes")
def obtener_clientes_por_analista(
    analista: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener detalle de clientes atrasados para un analista específico
    Busca tanto por nombre (analista) como por email (usuario_proponente)
    """
    try:
        hoy = date.today()

        query = (
            db.query(
                Cliente.cedula,
                Cliente.nombres,
                Cliente.telefono,
                func.coalesce(Prestamo.analista, Prestamo.usuario_proponente).label("analista"),
                Prestamo.id.label("prestamo_id"),
                func.count(Cuota.id).label("cuotas_vencidas"),
                func.sum(Cuota.monto_cuota).label("total_adeudado"),
                func.min(Cuota.fecha_vencimiento).label("fecha_primera_vencida"),
            )
            .join(Prestamo, Prestamo.cedula == Cliente.cedula)
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado.in_(["APROBADO", "ACTIVO"]),  # Préstamos aprobados o activos
                or_(Prestamo.analista == analista, Prestamo.usuario_proponente == analista),
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            )
            .group_by(
                Cliente.cedula, Cliente.nombres, Cliente.telefono, Prestamo.analista, Prestamo.usuario_proponente, Prestamo.id
            )
        )

        resultados = query.all()

        # Cargar modelo ML Impago una sola vez si está disponible
        ml_service = None
        try:
            from app.models.modelo_impago_cuotas import ModeloImpagoCuotas

            modelo_activo = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).first()
            if modelo_activo:
                try:
                    from app.services.ml_impago_cuotas_service import ML_IMPAGO_SERVICE_AVAILABLE, MLImpagoCuotasService

                    if ML_IMPAGO_SERVICE_AVAILABLE and MLImpagoCuotasService:
                        ml_service = MLImpagoCuotasService()
                        if not ml_service.load_model_from_path(modelo_activo.ruta_archivo):
                            logger.warning(f"No se pudo cargar el modelo ML desde {modelo_activo.ruta_archivo}")
                            ml_service = None
                        else:
                            logger.info(f"Modelo ML Impago cargado correctamente: {modelo_activo.nombre}")
                    else:
                        logger.debug("ML_IMPAGO_SERVICE_AVAILABLE es False o MLImpagoCuotasService no está disponible")
                except ImportError as e:
                    logger.warning(f"Error importando servicio ML Impago: {e}")
            else:
                logger.debug("No hay modelo ML Impago activo en la base de datos")
        except Exception as e:
            logger.warning(f"Error cargando modelo ML Impago: {e}", exc_info=True)

        clientes = []
        for row in resultados:
            cliente_data = {
                "cedula": row.cedula,
                "nombres": row.nombres,
                "telefono": row.telefono,
                "analista": row.analista,
                "prestamo_id": row.prestamo_id,
                "cuotas_vencidas": row.cuotas_vencidas,
                "total_adeudado": (float(row.total_adeudado) if row.total_adeudado else 0.0),
                "fecha_primera_vencida": (row.fecha_primera_vencida.isoformat() if row.fecha_primera_vencida else None),
            }

            # Agregar predicción ML Impago si está disponible
            # Priorizar valores manuales sobre calculados
            try:
                prestamo = db.query(Prestamo).filter(Prestamo.id == row.prestamo_id).first()
                if prestamo and prestamo.estado == "APROBADO":
                    # Verificar si hay valores manuales
                    if prestamo.ml_impago_nivel_riesgo_manual and prestamo.ml_impago_probabilidad_manual is not None:
                        # Usar valores manuales
                        cliente_data["ml_impago"] = {
                            "probabilidad_impago": float(prestamo.ml_impago_probabilidad_manual),
                            "nivel_riesgo": prestamo.ml_impago_nivel_riesgo_manual,
                            "prediccion": "Manual",
                            "es_manual": True,
                        }
                    elif ml_service:
                        # Calcular con ML si no hay valores manuales
                        cuotas = db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).order_by(Cuota.numero_cuota).all()
                        if cuotas:
                            try:
                                fecha_actual = date.today()
                                features = ml_service.extract_payment_features(cuotas, prestamo, fecha_actual)
                                prediccion = ml_service.predict_impago(features)

                                # Verificar si la predicción fue exitosa
                                if prediccion.get("prediccion") == "Error" or prediccion.get("prediccion") == "Desconocido":
                                    logger.warning(f"Predicción ML falló para préstamo {row.prestamo_id}: {prediccion.get('recomendacion', 'Error desconocido')}")
                                    cliente_data["ml_impago"] = None
                                else:
                                    cliente_data["ml_impago"] = {
                                        "probabilidad_impago": round(prediccion.get("probabilidad_impago", 0.0), 3),
                                        "nivel_riesgo": prediccion.get("nivel_riesgo", "Desconocido"),
                                        "prediccion": prediccion.get("prediccion", "Desconocido"),
                                        "es_manual": False,
                                    }
                            except Exception as e:
                                logger.warning(f"Error calculando predicción ML para préstamo {row.prestamo_id}: {e}", exc_info=True)
                                cliente_data["ml_impago"] = None
                        else:
                            logger.debug(f"No hay cuotas para préstamo {row.prestamo_id}, no se puede calcular ML Impago")
                            cliente_data["ml_impago"] = None
                    else:
                        logger.debug(f"Servicio ML no disponible para préstamo {row.prestamo_id}")
                        cliente_data["ml_impago"] = None
            except Exception as e:
                logger.warning(f"Error obteniendo predicción ML para préstamo {row.prestamo_id}: {e}", exc_info=True)
                cliente_data["ml_impago"] = None

            clientes.append(cliente_data)

        return clientes

    except Exception as e:
        logger.error(f"Error obteniendo clientes del analista {analista}: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/montos-por-mes")
def obtener_montos_vencidos_por_mes(
    incluir_admin: bool = Query(False, description="Incluir datos del administrador para diagnóstico"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener montos vencidos agrupados por mes de vencimiento
    Solo incluye cuotas vencidas con los mismos filtros que el resumen
    Excluye admin por defecto, pero puede incluirse con incluir_admin=true para diagnóstico
    Si no hay otros analistas en el sistema, incluye automáticamente al admin
    """
    try:
        hoy = date.today()
        from app.core.config import settings

        # Verificar si hay otros usuarios no-admin en el sistema
        otros_analistas = (
            db.query(func.count(User.id))
            .filter(User.is_active.is_(True), or_(User.is_admin.is_(False), User.is_admin.is_(None)))
            .scalar()
            or 0
        )

        # Si no hay otros analistas, incluir admin automáticamente
        if otros_analistas == 0:
            logger.info("🔍 [montos_por_mes] No hay otros analistas, incluyendo admin automáticamente")
            incluir_admin = True

        query_filters = [
            Prestamo.estado.in_(["APROBADO", "ACTIVO"]),  # Préstamos aprobados o activos
            Cuota.fecha_vencimiento < hoy,
            Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
        ]

        # Aplicar filtro de admin solo si incluir_admin=False
        if not incluir_admin:
            query_filters.append(Prestamo.usuario_proponente != settings.ADMIN_EMAIL)  # Excluir admin

        query = (
            db.query(
                func.date_trunc("month", Cuota.fecha_vencimiento).label("mes"),
                func.count(Cuota.id).label("cantidad_cuotas"),
                func.sum(Cuota.monto_cuota).label("monto_total"),
            )
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cedula == Cliente.cedula)
            .outerjoin(User, User.email == Prestamo.usuario_proponente)
            .filter(*query_filters)
        )

        # Aplicar filtro de User.is_admin solo si incluir_admin=False
        if not incluir_admin:
            query = query.filter(or_(User.is_admin.is_(False), User.is_admin.is_(None)))  # Excluir admins

        query = query.group_by(func.date_trunc("month", Cuota.fecha_vencimiento)).order_by(
            func.date_trunc("month", Cuota.fecha_vencimiento)
        )

        resultados = query.all()

        montos_por_mes = []
        for row in resultados:
            montos_por_mes.append(
                {
                    "mes": row.mes.strftime("%Y-%m") if row.mes else None,
                    "mes_display": row.mes.strftime("%B %Y") if row.mes else None,
                    "cantidad_cuotas": row.cantidad_cuotas,
                    "monto_total": float(row.monto_total) if row.monto_total else 0.0,
                }
            )

        return montos_por_mes

    except Exception as e:
        logger.error(f"Error obteniendo montos por mes: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/resumen")
def obtener_resumen_cobranzas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    incluir_diagnostico: bool = Query(False, description="Incluir información de diagnóstico"),
    incluir_admin: bool = Query(False, description="Incluir datos del administrador para diagnóstico"),
):
    """
    Obtener resumen general de cobranzas
    Excluye admin por defecto, pero puede incluirse con incluir_admin=true para diagnóstico
    Si no hay otros analistas en el sistema, incluye automáticamente al admin
    Solo cuenta préstamos aprobados o activos
    """
    try:
        hoy = date.today()
        from app.core.config import settings

        # Verificar si hay otros usuarios no-admin en el sistema
        # Si no hay, incluir automáticamente al admin
        otros_analistas = (
            db.query(func.count(User.id))
            .filter(User.is_active.is_(True), or_(User.is_admin.is_(False), User.is_admin.is_(None)))
            .scalar()
            or 0
        )

        # Si no hay otros analistas, incluir admin automáticamente
        if otros_analistas == 0:
            logger.info("🔍 [resumen_cobranzas] No hay otros analistas en el sistema, incluyendo admin automáticamente")
            incluir_admin = True

        # DIAGNÓSTICO: Verificar estados de préstamos con cuotas vencidas
        estados_prestamos = (
            db.query(Prestamo.estado, func.count(Prestamo.id))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            )
            .group_by(Prestamo.estado)
            .all()
        )
        logger.info(f"🔍 [resumen_cobranzas] Estados de préstamos con cuotas vencidas: {dict(estados_prestamos)}")

        # Total de cuotas vencidas SIN filtro de estado (para diagnóstico)
        # ✅ Usar criterio correcto: total_pagado < monto_cuota
        total_cuotas_sin_filtro = (
            db.query(func.count(Cuota.id))
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            )
            .scalar()
            or 0
        )
        logger.info(f"🔍 [resumen_cobranzas] Total cuotas vencidas SIN filtro estado: {total_cuotas_sin_filtro}")

        # DIAGNÓSTICO ADICIONAL: Cuotas vencidas por estado de préstamo
        cuotas_por_estado = {}
        for estado_row in estados_prestamos:
            estado_nombre = estado_row[0]
            cantidad = estado_row[1]
            cuotas_por_estado[estado_nombre] = cantidad
            logger.info(f"🔍 [resumen_cobranzas] Estado '{estado_nombre}': {cantidad} préstamos con cuotas vencidas")

        # DIAGNÓSTICO: Verificar cuotas vencidas del admin
        total_del_admin = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
                Prestamo.usuario_proponente == settings.ADMIN_EMAIL,
            )
            .scalar()
            or 0
        )
        logger.info(f"🔍 [resumen_cobranzas] Total cuotas vencidas DEL admin: {total_del_admin}")

        # DIAGNÓSTICO: Verificar cuotas vencidas excluyendo admin
        total_sin_admin = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
                Prestamo.usuario_proponente != settings.ADMIN_EMAIL,
            )
            .scalar()
            or 0
        )
        logger.info(f"🔍 [resumen_cobranzas] Total cuotas vencidas SIN admin: {total_sin_admin}")

        # DIAGNÓSTICO: Verificar usuarios únicos con cuotas vencidas
        usuarios_con_cuotas_vencidas = (
            db.query(
                Prestamo.usuario_proponente,
                func.count(func.distinct(Prestamo.id)).label("prestamos"),
                func.count(Cuota.id).label("cuotas"),
            )
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado.in_(["APROBADO", "ACTIVO"]),
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
            )
            .group_by(Prestamo.usuario_proponente)
            .order_by(func.count(Cuota.id).desc())
            .limit(10)
            .all()
        )
        logger.info(
            f"🔍 [resumen_cobranzas] Top 10 usuarios con cuotas vencidas: {[(u[0], u[1], u[2]) for u in usuarios_con_cuotas_vencidas]}"
        )

        # DIAGNÓSTICO: Verificar cuotas vencidas con filtro de estado APROBADO/ACTIVO
        total_aprobado_activo = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado.in_(["APROBADO", "ACTIVO"]),
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,
            )
            .scalar()
            or 0
        )
        logger.info(f"🔍 [resumen_cobranzas] Total cuotas vencidas APROBADO/ACTIVO: {total_aprobado_activo}")

        # Base query con joins necesarios y filtros
        # Incluir préstamos APROBADO y ACTIVO (ambos son válidos para cobranzas)
        base_filters = [
            Prestamo.estado.in_(["APROBADO", "ACTIVO"]),  # Préstamos aprobados o activos
            Cuota.fecha_vencimiento < hoy,
            Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
        ]

        # Aplicar filtro de admin solo si incluir_admin=False
        if not incluir_admin:
            base_filters.extend(
                [
                    Prestamo.usuario_proponente != settings.ADMIN_EMAIL,  # Excluir admin
                ]
            )
        base_query = (
            db.query(Cuota)
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cedula == Cliente.cedula)
            .outerjoin(User, User.email == Prestamo.usuario_proponente)
            .filter(*base_filters)
        )

        # Aplicar filtro de User.is_admin solo si incluir_admin=False
        if not incluir_admin:
            base_query = base_query.filter(or_(User.is_admin.is_(False), User.is_admin.is_(None)))  # Excluir admins

        # Total de cuotas vencidas
        total_cuotas_vencidas = base_query.count()

        # Monto total adeudado
        monto_filters = [
            Prestamo.estado.in_(["APROBADO", "ACTIVO"]),
            Cuota.fecha_vencimiento < hoy,
            Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
        ]

        if not incluir_admin:
            monto_filters.append(Prestamo.usuario_proponente != settings.ADMIN_EMAIL)

        monto_query = (
            db.query(func.sum(Cuota.monto_cuota))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .outerjoin(User, User.email == Prestamo.usuario_proponente)
            .filter(*monto_filters)
        )

        if not incluir_admin:
            monto_query = monto_query.filter(or_(User.is_admin.is_(False), User.is_admin.is_(None)))
        monto_total_adeudado = monto_query.scalar() or Decimal("0.0")

        # Cantidad de clientes únicos atrasados
        clientes_filters = [
            Prestamo.estado.in_(["APROBADO", "ACTIVO"]),  # Incluir ambos estados
            Cuota.fecha_vencimiento < hoy,
            Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
        ]

        if not incluir_admin:
            clientes_filters.extend(
                [
                    Prestamo.usuario_proponente != settings.ADMIN_EMAIL,
                ]
            )

        clientes_query = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .outerjoin(User, User.email == Prestamo.usuario_proponente)
            .filter(*clientes_filters)
        )

        if not incluir_admin:
            clientes_query = clientes_query.filter(or_(User.is_admin.is_(False), User.is_admin.is_(None)))

        clientes_unicos = clientes_query.scalar() or 0

        logger.info(
            f"📊 [resumen_cobranzas] Total: {total_cuotas_vencidas} cuotas vencidas, "
            f"${float(monto_total_adeudado):,.2f} adeudado, {clientes_unicos} clientes atrasados"
        )

        resultado = {
            "total_cuotas_vencidas": total_cuotas_vencidas,
            "monto_total_adeudado": float(monto_total_adeudado),
            "clientes_atrasados": clientes_unicos,
        }

        # Agregar diagnóstico si se solicita
        if incluir_diagnostico:
            resultado["diagnostico"] = {
                "fecha_corte": hoy.isoformat(),
                "total_cuotas_vencidas_sin_filtros": total_cuotas_sin_filtro,
                "total_cuotas_vencidas_sin_admin": total_sin_admin,
                "total_cuotas_vencidas_aprobado_activo": total_aprobado_activo,
                "estados_prestamos_con_cuotas_vencidas": dict(estados_prestamos),
                "admin_email_excluido": settings.ADMIN_EMAIL,
                "filtros_aplicados": {
                    "estado_prestamo": ["APROBADO", "ACTIVO"],
                    "excluir_admin": True,
                    "criterio_cuota_vencida": "fecha_vencimiento < hoy AND total_pagado < monto_cuota",
                },
            }

        return resultado

    except Exception as e:
        logger.error(f"Error obteniendo resumen de cobranzas: {e}", exc_info=True)
        try:
            db.rollback()  # Rollback para restaurar transacción después de error
        except Exception:
            pass  # Si rollback falla, ignorar
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ==
# ACTUALIZACIÓN ML IMPAGO
# ==


class MLImpagoUpdate(BaseModel):
    """Schema para actualizar valores manuales de ML Impago"""
    nivel_riesgo: str = Field(..., description="Nivel de riesgo: Alto, Medio, Bajo")
    probabilidad_impago: float = Field(..., ge=0.0, le=1.0, description="Probabilidad de impago (0.0 a 1.0)")

    @field_validator("nivel_riesgo")
    @classmethod
    def validate_nivel_riesgo(cls, v: str) -> str:
        v_capitalized = v.capitalize()
        if v_capitalized not in ["Alto", "Medio", "Bajo"]:
            raise ValueError("Nivel de riesgo debe ser: Alto, Medio o Bajo")
        return v_capitalized


@router.put("/prestamos/{prestamo_id}/ml-impago")
def actualizar_ml_impago(
    prestamo_id: int,
    ml_impago_data: MLImpagoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Actualizar valores manuales de ML Impago para un préstamo.
    Estos valores tendrán prioridad sobre los calculados por el modelo ML.
    """
    try:
        # Buscar préstamo
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")

        # Validar nivel de riesgo
        nivel_riesgo = ml_impago_data.nivel_riesgo.capitalize()
        if nivel_riesgo not in ["Alto", "Medio", "Bajo"]:
            raise HTTPException(status_code=400, detail="Nivel de riesgo debe ser: Alto, Medio o Bajo")

        # Actualizar valores manuales
        prestamo.ml_impago_nivel_riesgo_manual = nivel_riesgo
        prestamo.ml_impago_probabilidad_manual = Decimal(str(ml_impago_data.probabilidad_impago))

        # Guardar cambios
        db.commit()
        db.refresh(prestamo)

        logger.info(f"ML Impago actualizado manualmente para préstamo {prestamo_id} por {current_user.email}")

        return {
            "mensaje": "ML Impago actualizado correctamente",
            "prestamo_id": prestamo_id,
            "ml_impago": {
                "nivel_riesgo": prestamo.ml_impago_nivel_riesgo_manual,
                "probabilidad_impago": float(prestamo.ml_impago_probabilidad_manual),
                "es_manual": True,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando ML Impago para préstamo {prestamo_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.delete("/prestamos/{prestamo_id}/ml-impago")
def eliminar_ml_impago_manual(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Eliminar valores manuales de ML Impago para un préstamo.
    Después de eliminar, se usarán los valores calculados por el modelo ML.
    """
    try:
        # Buscar préstamo
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")

        # Eliminar valores manuales
        prestamo.ml_impago_nivel_riesgo_manual = None
        prestamo.ml_impago_probabilidad_manual = None

        # Guardar cambios
        db.commit()
        db.refresh(prestamo)

        logger.info(f"ML Impago manual eliminado para préstamo {prestamo_id} por {current_user.email}")

        return {
            "mensaje": "Valores manuales de ML Impago eliminados. Se usarán valores calculados por ML.",
            "prestamo_id": prestamo_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando ML Impago manual para préstamo {prestamo_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ==
# NOTIFICACIONES DE ATRASO (VINCULACIÓN COBRANZAS)
# ==


@router.post("/notificaciones/atrasos")
def disparar_notificaciones_atrasos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dispara el proceso automático de notificaciones de atrasos
    desde el módulo de Cobranzas.

    Equivale a POST /api/v1/notificaciones/automaticas/procesar pero
    queda vinculado funcionalmente a Cobranzas para facilitar su uso
    desde esta área.
    """
    try:
        service = NotificacionAutomaticaService(db)
        stats = service.procesar_notificaciones_automaticas()

        return {
            "mensaje": "Notificaciones de atrasos procesadas",
            "estadisticas": stats,
        }
    except Exception as e:
        logger.error(f"Error disparando notificaciones de atrasos: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ==
# INFORME 1: Clientes Atrasados Completo
# ==


def _construir_query_clientes_atrasados(db: Session, hoy: date, analista: Optional[str]):
    """Construye la query base para clientes atrasados"""
    from app.core.config import settings

    query = (
        db.query(
            Cliente.cedula,
            Cliente.nombres,
            Cliente.telefono,
            func.coalesce(Prestamo.analista, Prestamo.usuario_proponente).label("analista"),
            Prestamo.id.label("prestamo_id"),
            Prestamo.total_financiamiento,
            func.count(Cuota.id).label("cuotas_vencidas"),
            func.sum(Cuota.monto_cuota).label("total_adeudado"),
            func.min(Cuota.fecha_vencimiento).label("fecha_primera_vencida"),
            func.max(Cuota.fecha_vencimiento).label("fecha_ultima_vencida"),
            func.sum(
                case(
                    (
                        Cuota.fecha_vencimiento < hoy - timedelta(days=30),
                        Cuota.monto_cuota,
                    ),
                    else_=0,
                )
            ).label("monto_mas_30_dias"),
        )
        .join(Prestamo, Prestamo.cedula == Cliente.cedula)
        .join(Cuota, Cuota.prestamo_id == Prestamo.id)
        .outerjoin(User, User.email == Prestamo.usuario_proponente)
        .filter(
            Prestamo.estado == "APROBADO",  # Solo préstamos aprobados
            Cuota.fecha_vencimiento < hoy,
            Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            Prestamo.usuario_proponente != settings.ADMIN_EMAIL,
            or_(User.is_admin.is_(False), User.is_admin.is_(None)),
        )
    )

    if analista:
        # Buscar tanto en analista (nombre) como en usuario_proponente (email)
        query = query.filter(or_(Prestamo.analista == analista, Prestamo.usuario_proponente == analista))

    return query.group_by(
        Cliente.cedula,
        Cliente.nombres,
        Cliente.telefono,
        Prestamo.analista,
        Prestamo.usuario_proponente,
        Prestamo.id,
        Prestamo.total_financiamiento,
    )


def _filtrar_por_dias_retraso(
    resultados, hoy: date, dias_retraso_min: Optional[int], dias_retraso_max: Optional[int]
) -> List[Dict]:
    """Filtra resultados por días de retraso y serializa los datos"""
    datos_filtrados = []
    for row in resultados:
        if not row.fecha_primera_vencida:
            continue

        dias_retraso = (hoy - row.fecha_primera_vencida).days
        if dias_retraso_min and dias_retraso < dias_retraso_min:
            continue
        if dias_retraso_max and dias_retraso > dias_retraso_max:
            continue

        datos_filtrados.append(
            {
                "cedula": row.cedula,
                "nombres": row.nombres,
                "telefono": row.telefono or "N/A",
                "analista": row.analista or "N/A",
                "prestamo_id": row.prestamo_id,
                "total_financiamiento": float(row.total_financiamiento),
                "cuotas_vencidas": row.cuotas_vencidas,
                "total_adeudado": (float(row.total_adeudado) if row.total_adeudado else 0.0),
                "fecha_primera_vencida": (row.fecha_primera_vencida.isoformat() if row.fecha_primera_vencida else None),
                "fecha_ultima_vencida": (row.fecha_ultima_vencida.isoformat() if row.fecha_ultima_vencida else None),
                "dias_retraso": dias_retraso,
                "monto_mas_30_dias": (float(row.monto_mas_30_dias) if row.monto_mas_30_dias else 0.0),
            }
        )

    return datos_filtrados


def _generar_respuesta_formato(datos_filtrados: List[Dict], formato: str):
    """Genera la respuesta según el formato solicitado"""
    if formato.lower() == "json":
        return {
            "titulo": "Informe de Clientes Atrasados",
            "fecha_generacion": datetime.now().isoformat(),
            "total_registros": len(datos_filtrados),
            "total_adeudado": sum(d.get("total_adeudado", 0) for d in datos_filtrados),
            "datos": datos_filtrados,
        }
    elif formato.lower() == "excel":
        return _generar_excel_clientes_atrasados(datos_filtrados)
    elif formato.lower() == "pdf":
        return _generar_pdf_clientes_atrasados(datos_filtrados)
    else:
        raise HTTPException(status_code=400, detail="Formato no válido. Use: json, excel o pdf")


@router.get("/informes/clientes-atrasados")
def informe_clientes_atrasados(
    dias_retraso_min: Optional[int] = Query(None, description="Días mínimos de retraso"),
    dias_retraso_max: Optional[int] = Query(None, description="Días máximos de retraso"),
    analista: Optional[str] = Query(None, description="Filtrar por analista"),
    formato: str = Query("json", description="Formato: json, pdf, excel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Informe completo de clientes atrasados con opciones de filtrado"""
    try:
        hoy = date.today()

        query = _construir_query_clientes_atrasados(db, hoy, analista)
        resultados = query.all()

        datos_filtrados = _filtrar_por_dias_retraso(resultados, hoy, dias_retraso_min, dias_retraso_max)

        # Agregar predicción ML Impago a cada cliente si está disponible
        ml_service = None
        try:
            from app.models.modelo_impago_cuotas import ModeloImpagoCuotas

            modelo_activo = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).first()
            if modelo_activo:
                try:
                    from datetime import date

                    from app.models.amortizacion import Cuota
                    from app.models.prestamo import Prestamo
                    from app.services.ml_impago_cuotas_service import ML_IMPAGO_SERVICE_AVAILABLE, MLImpagoCuotasService

                    if ML_IMPAGO_SERVICE_AVAILABLE and MLImpagoCuotasService:
                        ml_service = MLImpagoCuotasService()
                        if not ml_service.load_model_from_path(modelo_activo.ruta_archivo):
                            ml_service = None

                        if ml_service:
                            for cliente_data in datos_filtrados:
                                try:
                                    prestamo = db.query(Prestamo).filter(Prestamo.id == cliente_data["prestamo_id"]).first()
                                    if prestamo and prestamo.estado == "APROBADO":
                                        cuotas = (
                                            db.query(Cuota)
                                            .filter(Cuota.prestamo_id == prestamo.id)
                                            .order_by(Cuota.numero_cuota)
                                            .all()
                                        )
                                        if cuotas:
                                            fecha_actual = date.today()
                                            features = ml_service.extract_payment_features(cuotas, prestamo, fecha_actual)
                                            prediccion = ml_service.predict_impago(features)

                                            cliente_data["ml_impago"] = {
                                                "probabilidad_impago": round(prediccion.get("probabilidad_impago", 0.0), 3),
                                                "nivel_riesgo": prediccion.get("nivel_riesgo", "Desconocido"),
                                                "prediccion": prediccion.get("prediccion", "Desconocido"),
                                            }
                                except Exception as e:
                                    logger.warning(
                                        f"Error obteniendo predicción ML para préstamo {cliente_data.get('prestamo_id')}: {e}"
                                    )
                                    cliente_data["ml_impago"] = None
                except ImportError:
                    pass
        except Exception:
            pass

        return _generar_respuesta_formato(datos_filtrados, formato)

    except Exception as e:
        logger.error(f"Error generando informe clientes atrasados: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ==
# INFORME 2: Rendimiento por Analista
# ==


@router.get("/informes/rendimiento-analista")
def informe_rendimiento_analista(
    formato: str = Query("json", description="Formato: json, pdf, excel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Informe detallado de rendimiento de cobranzas por analista"""
    try:
        hoy = date.today()

        # Estadísticas por analista - Excluir admin
        from app.core.config import settings

        query = (
            db.query(
                func.coalesce(Prestamo.analista, Prestamo.usuario_proponente).label("analista"),
                func.count(func.distinct(Cliente.cedula)).label("total_clientes"),
                func.count(func.distinct(Prestamo.id)).label("total_prestamos"),
                func.sum(Cuota.monto_cuota).label("monto_total_adeudado"),
                func.count(Cuota.id).label("total_cuotas_vencidas"),
                func.avg(
                    case(
                        (
                            Cuota.fecha_vencimiento < hoy,
                            func.extract("day", hoy - Cuota.fecha_vencimiento),
                        ),
                        else_=0,
                    )
                ).label("promedio_dias_retraso"),
            )
            .join(Cliente, Cliente.cedula == Prestamo.cedula)
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .outerjoin(User, User.email == Prestamo.usuario_proponente)
            .filter(
                Prestamo.estado.in_(["APROBADO", "ACTIVO"]),  # Préstamos aprobados o activos
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
                Prestamo.usuario_proponente.isnot(None),
                Prestamo.usuario_proponente != settings.ADMIN_EMAIL,  # Excluir admin
                or_(User.is_admin.is_(False), User.is_admin.is_(None)),  # Excluir admins
            )
            .group_by(Prestamo.analista, Prestamo.usuario_proponente)
        )

        resultados = query.all()

        datos_analistas = []
        for row in resultados:
            datos_analistas.append(
                {
                    "analista": row.analista or "Sin analista",
                    "total_clientes": row.total_clientes or 0,
                    "total_prestamos": row.total_prestamos or 0,
                    "monto_total_adeudado": (float(row.monto_total_adeudado) if row.monto_total_adeudado else 0.0),
                    "total_cuotas_vencidas": row.total_cuotas_vencidas or 0,
                    "promedio_dias_retraso": (float(row.promedio_dias_retraso) if row.promedio_dias_retraso else 0.0),
                }
            )

        # Si no hay datos, retornar estructura vacía pero válida
        if not datos_analistas:
            logger.warning("[informe_rendimiento_analista] No se encontraron datos de analistas")
            if formato.lower() == "json":
                return {
                    "titulo": "Informe de Rendimiento por Analista",
                    "fecha_generacion": datetime.now().isoformat(),
                    "total_analistas": 0,
                    "datos": [],
                    "mensaje": "No se encontraron datos de analistas con cuotas vencidas",
                }
            elif formato.lower() == "excel":
                return _generar_excel_rendimiento_analista([])
            elif formato.lower() == "pdf":
                return _generar_pdf_rendimiento_analista([])
            else:
                raise HTTPException(status_code=400, detail="Formato no válido")

        if formato.lower() == "json":
            return {
                "titulo": "Informe de Rendimiento por Analista",
                "fecha_generacion": datetime.now().isoformat(),
                "total_analistas": len(datos_analistas),
                "datos": datos_analistas,
            }
        elif formato.lower() == "excel":
            return _generar_excel_rendimiento_analista(datos_analistas)
        elif formato.lower() == "pdf":
            return _generar_pdf_rendimiento_analista(datos_analistas)
        else:
            raise HTTPException(status_code=400, detail="Formato no válido")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando informe rendimiento analista: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ==
# INFORME 3: Montos Vencidos por Período
# ==


@router.get("/informes/montos-vencidos-periodo")
def informe_montos_vencidos_periodo(
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin"),
    formato: str = Query("json", description="Formato: json, pdf, excel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Informe de montos vencidos agrupados por período"""
    try:
        hoy = date.today()

        query = (
            db.query(
                func.date_trunc("month", Cuota.fecha_vencimiento).label("mes"),
                func.count(Cuota.id).label("cantidad_cuotas"),
                func.sum(Cuota.monto_cuota).label("monto_total"),
                func.count(func.distinct(Cliente.cedula)).label("clientes_unicos"),
            )
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cedula == Cliente.cedula)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            )
        )

        if fecha_inicio:
            query = query.filter(Cuota.fecha_vencimiento >= fecha_inicio)
        if fecha_fin:
            query = query.filter(Cuota.fecha_vencimiento <= fecha_fin)

        query = query.group_by(func.date_trunc("month", Cuota.fecha_vencimiento))
        query = query.order_by(func.date_trunc("month", Cuota.fecha_vencimiento))

        resultados = query.all()

        datos_periodo = []
        for row in resultados:
            datos_periodo.append(
                {
                    "mes": row.mes.strftime("%Y-%m") if row.mes else None,
                    "mes_display": row.mes.strftime("%B %Y") if row.mes else None,
                    "cantidad_cuotas": row.cantidad_cuotas,
                    "monto_total": float(row.monto_total) if row.monto_total else 0.0,
                    "clientes_unicos": row.clientes_unicos,
                }
            )

        if formato.lower() == "json":
            return {
                "titulo": "Informe de Montos Vencidos por Período",
                "fecha_generacion": datetime.now().isoformat(),
                "fecha_inicio": fecha_inicio.isoformat() if fecha_inicio else None,
                "fecha_fin": fecha_fin.isoformat() if fecha_fin else None,
                "total_meses": len(datos_periodo),
                "monto_total_acumulado": sum(d.get("monto_total", 0) for d in datos_periodo),
                "datos": datos_periodo,
            }
        elif formato.lower() == "excel":
            return _generar_excel_montos_periodo(datos_periodo)
        elif formato.lower() == "pdf":
            return _generar_pdf_montos_periodo(datos_periodo)
        else:
            raise HTTPException(status_code=400, detail="Formato no válido")

    except Exception as e:
        logger.error(f"Error generando informe montos período: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ==
# INFORME 4: Antigüedad de Saldos
# ==


def _determinar_categoria_dias(dias_diferencia: int) -> Optional[str]:
    """Determina la categoría según los días de diferencia"""
    if dias_diferencia == -3:
        return "3 días antes de vencimiento"
    elif dias_diferencia == -1:
        return "1 día antes de vencimiento"
    elif dias_diferencia == 0:
        return "Día de pago"
    elif 0 < dias_diferencia <= 3:
        return "3 días atrasado"
    elif 3 < dias_diferencia <= 30:
        return "1 mes atrasado"
    elif 30 < dias_diferencia <= 60:
        return "2 meses atrasado"
    elif dias_diferencia > 60:
        return "3 o más meses atrasado"
    return None  # Más de 3 días antes, no incluirlo


def _obtener_cuotas_categoria_dias(db: Session, analista: Optional[str], hoy: date):
    """Obtiene las cuotas para el informe por categoría de días"""
    from app.core.config import settings

    fecha_limite_inicio = hoy - timedelta(days=3)

    cuotas_query = (
        db.query(
            Cliente.cedula,
            Cliente.nombres,
            func.coalesce(Prestamo.analista, Prestamo.usuario_proponente).label("analista"),
            Cuota.id.label("cuota_id"),
            Cuota.numero_cuota,
            Cuota.fecha_vencimiento,
            Cuota.monto_cuota,
            Cuota.estado,
        )
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cedula == Cliente.cedula)
        .outerjoin(User, User.email == Prestamo.usuario_proponente)
        .filter(
            Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto (incluye cuotas no vencidas para categorización)
            Prestamo.usuario_proponente != settings.ADMIN_EMAIL,
            or_(User.is_admin.is_(False), User.is_admin.is_(None)),
            Cuota.fecha_vencimiento >= fecha_limite_inicio,
        )
    )

    if analista:
        # Buscar tanto en analista (nombre) como en usuario_proponente (email)
        cuotas_query = cuotas_query.filter(or_(Prestamo.analista == analista, Prestamo.usuario_proponente == analista))

    return cuotas_query.all()


def _categorizar_resultados(resultados_raw, hoy: date) -> List[Dict]:
    """Categoriza los resultados según días de diferencia"""
    resultados = []
    for row in resultados_raw:
        if not row.fecha_vencimiento:
            continue

        dias_diferencia = (row.fecha_vencimiento - hoy).days
        categoria = _determinar_categoria_dias(dias_diferencia)

        if not categoria:
            continue

        resultados.append(
            {
                "categoria_dias": categoria,
                "cedula": row.cedula,
                "nombres": row.nombres,
                "analista": row.analista or "Sin analista",
                "cuota_id": row.cuota_id,
                "numero_cuota": row.numero_cuota,
                "fecha_vencimiento": row.fecha_vencimiento,
                "monto_cuota": row.monto_cuota,
                "estado": row.estado,
                "dias_diferencia": dias_diferencia,
            }
        )
    return resultados


def _agrupar_por_categoria(resultados: List[Dict]) -> Dict:
    """Agrupa resultados por categoría"""
    datos_por_categoria = {}
    for row in resultados:
        categoria = row["categoria_dias"]
        if categoria not in datos_por_categoria:
            datos_por_categoria[categoria] = {
                "categoria": categoria,
                "cantidad_cuotas": 0,
                "monto_total": 0.0,
                "clientes_unicos": set(),
                "cuotas": [],
            }

        datos_por_categoria[categoria]["cantidad_cuotas"] += 1
        datos_por_categoria[categoria]["monto_total"] += float(row["monto_cuota"] or 0)
        datos_por_categoria[categoria]["clientes_unicos"].add(row["cedula"])
        datos_por_categoria[categoria]["cuotas"].append(
            {
                "cedula": row["cedula"],
                "nombres": row["nombres"],
                "analista": row["analista"],
                "numero_cuota": row["numero_cuota"],
                "fecha_vencimiento": (row["fecha_vencimiento"].isoformat() if row["fecha_vencimiento"] else None),
                "monto": float(row["monto_cuota"] or 0),
                "estado": row["estado"],
                "dias_diferencia": int(row["dias_diferencia"]),
            }
        )
    return datos_por_categoria


def _agrupar_por_analista(resultados: List[Dict]) -> Dict:
    """Agrupa resultados por analista"""
    datos_por_analista = {}
    for row in resultados:
        categoria = row["categoria_dias"]
        analista_nombre = row["analista"]

        if analista_nombre not in datos_por_analista:
            datos_por_analista[analista_nombre] = {"analista": analista_nombre, "categorias": {}}

        if categoria not in datos_por_analista[analista_nombre]["categorias"]:
            datos_por_analista[analista_nombre]["categorias"][categoria] = {
                "cantidad_cuotas": 0,
                "monto_total": 0.0,
            }

        datos_por_analista[analista_nombre]["categorias"][categoria]["cantidad_cuotas"] += 1
        datos_por_analista[analista_nombre]["categorias"][categoria]["monto_total"] += float(row["monto_cuota"] or 0)

    return datos_por_analista


def _preparar_datos_categoria_final(datos_por_categoria: Dict) -> List[Dict]:
    """Prepara y ordena datos finales por categoría"""
    orden_categorias = {
        "3 días antes de vencimiento": 1,
        "1 día antes de vencimiento": 2,
        "Día de pago": 3,
        "3 días atrasado": 4,
        "1 mes atrasado": 5,
        "2 meses atrasado": 6,
        "3 o más meses atrasado": 7,
    }

    datos_categoria_final = []
    for cat, datos in datos_por_categoria.items():
        datos_categoria_final.append(
            {
                "categoria": cat,
                "cantidad_cuotas": datos["cantidad_cuotas"],
                "monto_total": round(datos["monto_total"], 2),
                "clientes_unicos": len(datos["clientes_unicos"]),
                "orden": orden_categorias.get(cat, 99),
            }
        )

    datos_categoria_final.sort(key=lambda x: x["orden"])
    return datos_categoria_final


def _preparar_datos_analista_final(datos_por_analista: Dict) -> List[Dict]:
    """Prepara y ordena datos finales por analista"""
    orden_categorias = {
        "3 días antes de vencimiento": 1,
        "1 día antes de vencimiento": 2,
        "Día de pago": 3,
        "3 días atrasado": 4,
        "1 mes atrasado": 5,
        "2 meses atrasado": 6,
        "3 o más meses atrasado": 7,
    }

    datos_analista_final = []
    for analista_nombre, datos in datos_por_analista.items():
        total_cuotas = sum(c["cantidad_cuotas"] for c in datos["categorias"].values())
        total_monto = sum(c["monto_total"] for c in datos["categorias"].values())

        categorias_ordenadas = []
        for cat in orden_categorias.keys():
            if cat in datos["categorias"]:
                categorias_ordenadas.append(
                    {
                        "categoria": cat,
                        "cantidad_cuotas": datos["categorias"][cat]["cantidad_cuotas"],
                        "monto_total": round(datos["categorias"][cat]["monto_total"], 2),
                    }
                )

        datos_analista_final.append(
            {
                "analista": analista_nombre,
                "total_cuotas": total_cuotas,
                "total_monto": round(total_monto, 2),
                "categorias": categorias_ordenadas,
            }
        )

    datos_analista_final.sort(key=lambda x: x["total_monto"], reverse=True)
    return datos_analista_final


@router.get("/informes/por-categoria-dias")
def informe_por_categoria_dias(
    analista: Optional[str] = Query(None, description="Filtrar por analista"),
    formato: str = Query("json", description="Formato: json, pdf, excel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Informe por categorías de días de vencimiento:
    - 3 días antes de vencimiento
    - 1 día antes
    - Día de pago (día 0)
    - 3 días atrasado
    - 1 mes atrasado (30 días)
    - 2 meses atrasado (60 días)
    - 3 o más meses atrasado (90+ días)
    """
    try:
        hoy = date.today()

        resultados_raw = _obtener_cuotas_categoria_dias(db, analista, hoy)
        resultados = _categorizar_resultados(resultados_raw, hoy)

        datos_por_categoria = _agrupar_por_categoria(resultados)
        datos_por_analista = _agrupar_por_analista(resultados)

        datos_categoria_final = _preparar_datos_categoria_final(datos_por_categoria)
        datos_analista_final = _preparar_datos_analista_final(datos_por_analista)

        if formato.lower() == "json":
            return {
                "titulo": "Informe por Categorías de Días y Analista",
                "fecha_generacion": datetime.now().isoformat(),
                "fecha_corte": hoy.isoformat(),
                "por_categoria": datos_categoria_final,
                "por_analista": datos_analista_final,
                "resumen": {
                    "total_cuotas": sum(c["cantidad_cuotas"] for c in datos_categoria_final),
                    "total_monto": round(sum(c["monto_total"] for c in datos_categoria_final), 2),
                    "total_categorias": len(datos_categoria_final),
                    "total_analistas": len(datos_analista_final),
                },
            }
        elif formato.lower() == "excel":
            return _generar_excel_categoria_dias(datos_categoria_final, datos_analista_final)
        elif formato.lower() == "pdf":
            return _generar_pdf_categoria_dias(datos_categoria_final, datos_analista_final)
        else:
            raise HTTPException(status_code=400, detail="Formato no válido")

    except Exception as e:
        logger.error(f"Error generando informe por categoría días: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/informes/antiguedad-saldos")
def informe_antiguedad_saldos(
    formato: str = Query("json", description="Formato: json, pdf, excel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Informe de distribución de mora por rangos de antigüedad (legacy - usar /por-categoria-dias)"""
    try:
        hoy = date.today()

        # Agrupar por rangos de antigüedad
        query = (
            db.query(
                case(
                    (
                        (func.extract("day", hoy - Cuota.fecha_vencimiento) <= 30),
                        "0-30 días",
                    ),
                    (
                        (func.extract("day", hoy - Cuota.fecha_vencimiento) <= 60),
                        "31-60 días",
                    ),
                    (
                        (func.extract("day", hoy - Cuota.fecha_vencimiento) <= 90),
                        "61-90 días",
                    ),
                    (
                        (func.extract("day", hoy - Cuota.fecha_vencimiento) <= 180),
                        "91-180 días",
                    ),
                    else_="Más de 180 días",
                ).label("rango_antiguedad"),
                func.count(Cuota.id).label("cantidad_cuotas"),
                func.sum(Cuota.monto_cuota).label("monto_total"),
                func.count(func.distinct(Cliente.cedula)).label("clientes_unicos"),
            )
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .join(Cliente, Prestamo.cedula == Cliente.cedula)
            .filter(
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            )
            .group_by("rango_antiguedad")
        )

        resultados = query.all()

        datos_antiguedad = []
        for row in resultados:
            datos_antiguedad.append(
                {
                    "rango_antiguedad": row.rango_antiguedad,
                    "cantidad_cuotas": row.cantidad_cuotas,
                    "monto_total": float(row.monto_total) if row.monto_total else 0.0,
                    "clientes_unicos": row.clientes_unicos,
                }
            )

        # Ordenar por antigüedad
        orden_rangos = {
            "0-30 días": 1,
            "31-60 días": 2,
            "61-90 días": 3,
            "91-180 días": 4,
            "Más de 180 días": 5,
        }
        datos_antiguedad.sort(key=lambda x: orden_rangos.get(x["rango_antiguedad"], 999))

        if formato.lower() == "json":
            total_monto = sum(d.get("monto_total", 0) for d in datos_antiguedad)
            return {
                "titulo": "Informe de Antigüedad de Saldos",
                "fecha_generacion": datetime.now().isoformat(),
                "total_rangos": len(datos_antiguedad),
                "monto_total": total_monto,
                "datos": datos_antiguedad,
            }
        elif formato.lower() == "excel":
            return _generar_excel_antiguedad_saldos(datos_antiguedad)
        elif formato.lower() == "pdf":
            return _generar_pdf_antiguedad_saldos(datos_antiguedad)
        else:
            raise HTTPException(status_code=400, detail="Formato no válido")

    except Exception as e:
        logger.error(f"Error generando informe antigüedad saldos: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ==
# INFORME 5: Resumen Ejecutivo
# ==


@router.get("/informes/resumen-ejecutivo")
def informe_resumen_ejecutivo(
    formato: str = Query("json", description="Formato: json, pdf, excel"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Informe ejecutivo consolidado de cobranzas"""
    try:
        hoy = date.today()

        # Resumen general - Solo préstamos aprobados o activos
        total_cuotas_vencidas = (
            db.query(func.count(Cuota.id))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado.in_(["APROBADO", "ACTIVO"]),
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            )
            .scalar()
            or 0
        )

        monto_total_adeudado = (
            db.query(func.sum(Cuota.monto_cuota))
            .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado.in_(["APROBADO", "ACTIVO"]),
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            )
            .scalar()
            or 0.0
        )

        clientes_atrasados = (
            db.query(func.count(func.distinct(Prestamo.cedula)))
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado.in_(["APROBADO", "ACTIVO"]),
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            )
            .scalar()
            or 0
        )

        # Top 5 analistas con más mora - Excluir admin
        from app.core.config import settings

        top_analistas = (
            db.query(
                func.coalesce(Prestamo.analista, Prestamo.usuario_proponente).label("analista"),
                func.sum(Cuota.monto_cuota).label("monto_total"),
            )
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .outerjoin(User, User.email == Prestamo.usuario_proponente)
            .filter(
                Prestamo.estado.in_(["APROBADO", "ACTIVO"]),  # Préstamos aprobados o activos
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
                Prestamo.usuario_proponente.isnot(None),
                Prestamo.usuario_proponente != settings.ADMIN_EMAIL,  # Excluir admin
                or_(User.is_admin.is_(False), User.is_admin.is_(None)),  # Excluir admins
            )
            .group_by(Prestamo.analista, Prestamo.usuario_proponente)
            .order_by(func.sum(Cuota.monto_cuota).desc())
            .limit(5)
            .all()
        )

        # Top 5 clientes con más deuda
        top_clientes = (
            db.query(
                Cliente.cedula,
                Cliente.nombres,
                func.sum(Cuota.monto_cuota).label("total_adeudado"),
                func.count(Cuota.id).label("cuotas_vencidas"),
            )
            .join(Prestamo, Prestamo.cedula == Cliente.cedula)
            .join(Cuota, Cuota.prestamo_id == Prestamo.id)
            .filter(
                Prestamo.estado.in_(["APROBADO", "ACTIVO"]),  # Préstamos aprobados o activos
                Cuota.fecha_vencimiento < hoy,
                Cuota.total_pagado < Cuota.monto_cuota,  # ✅ Pago incompleto
            )
            .group_by(Cliente.cedula, Cliente.nombres)
            .order_by(func.sum(Cuota.monto_cuota).desc())
            .limit(5)
            .all()
        )

        datos_resumen = {
            "fecha_generacion": datetime.now().isoformat(),
            "fecha_corte": hoy.isoformat(),
            "resumen_general": {
                "total_cuotas_vencidas": total_cuotas_vencidas,
                "monto_total_adeudado": float(monto_total_adeudado),
                "clientes_atrasados": clientes_atrasados,
                "promedio_deuda_cliente": (
                    float(monto_total_adeudado / clientes_atrasados) if clientes_atrasados > 0 else 0.0
                ),
            },
            "top_analistas": [
                {
                    "analista": row.analista,
                    "monto_total": float(row.monto_total) if row.monto_total else 0.0,
                }
                for row in top_analistas
            ],
            "top_clientes": [
                {
                    "cedula": row.cedula,
                    "nombres": row.nombres,
                    "total_adeudado": (float(row.total_adeudado) if row.total_adeudado else 0.0),
                    "cuotas_vencidas": row.cuotas_vencidas,
                }
                for row in top_clientes
            ],
        }

        if formato.lower() == "json":
            return datos_resumen
        elif formato.lower() == "excel":
            respuesta = _generar_excel_resumen_ejecutivo(datos_resumen)
            # Auditoría de exportación
            try:
                audit = Auditoria(
                    usuario_id=current_user.id,
                    accion="EXPORT",
                    entidad="COBRANZAS",
                    entidad_id=None,
                    detalles="Exportó Resumen Ejecutivo en Excel",
                    exito=True,
                )
                db.add(audit)
                db.commit()
            except Exception as e:
                logger.warning(f"No se pudo registrar auditoría exportación cobranzas (Excel): {e}")
            return respuesta
        elif formato.lower() == "pdf":
            respuesta = _generar_pdf_resumen_ejecutivo(datos_resumen)
            # Auditoría de exportación
            try:
                audit = Auditoria(
                    usuario_id=current_user.id,
                    accion="EXPORT",
                    entidad="COBRANZAS",
                    entidad_id=None,
                    detalles="Exportó Resumen Ejecutivo en PDF",
                    exito=True,
                )
                db.add(audit)
                db.commit()
            except Exception as e:
                logger.warning(f"No se pudo registrar auditoría exportación cobranzas (PDF): {e}")
            return respuesta
        else:
            raise HTTPException(status_code=400, detail="Formato no válido")

    except Exception as e:
        logger.error(f"Error generando informe resumen ejecutivo: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


# ==
# FUNCIONES AUXILIARES PARA GENERACIÓN EXCEL
# ==


def _generar_excel_clientes_atrasados(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo Excel para informe de clientes atrasados"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Clientes Atrasados"

    # Estilos
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)

    # Encabezados
    headers = [
        "Cédula",
        "Nombres",
        "Teléfono",
        "Analista",
        "Préstamo ID",
        "Total Financiamiento",
        "Cuotas Vencidas",
        "Riesgo ML Impago",
        "Prob. Impago %",
        "Total Adeudado",
        "Fecha Primera Vencida",
        "Días Retraso",
        "Monto >30 días",
    ]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Datos
    for row_idx, registro in enumerate(datos, 2):
        ws.cell(row=row_idx, column=1, value=registro.get("cedula"))
        ws.cell(row=row_idx, column=2, value=registro.get("nombres"))
        ws.cell(row=row_idx, column=3, value=registro.get("telefono"))
        ws.cell(row=row_idx, column=4, value=registro.get("analista"))
        ws.cell(row=row_idx, column=5, value=registro.get("prestamo_id"))
        ws.cell(row=row_idx, column=6, value=registro.get("total_financiamiento"))
        ws.cell(row=row_idx, column=7, value=registro.get("cuotas_vencidas"))
        # ML Impago
        ml_impago = registro.get("ml_impago")
        if ml_impago:
            ws.cell(row=row_idx, column=8, value=ml_impago.get("nivel_riesgo", "N/A"))
            ws.cell(row=row_idx, column=9, value=round(ml_impago.get("probabilidad_impago", 0.0) * 100, 1))
        else:
            ws.cell(row=row_idx, column=8, value="N/A")
            ws.cell(row=row_idx, column=9, value="N/A")
        ws.cell(row=row_idx, column=10, value=registro.get("total_adeudado"))
        ws.cell(row=row_idx, column=11, value=registro.get("fecha_primera_vencida"))
        ws.cell(row=row_idx, column=12, value=registro.get("dias_retraso"))
        ws.cell(row=row_idx, column=13, value=registro.get("monto_mas_30_dias"))

    # Ajustar anchos
    ws.column_dimensions["A"].width = 15
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 15
    ws.column_dimensions["D"].width = 25
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 18
    ws.column_dimensions["G"].width = 15
    ws.column_dimensions["H"].width = 15  # Riesgo ML Impago
    ws.column_dimensions["I"].width = 15  # Prob. Impago %
    ws.column_dimensions["J"].width = 15  # Total Adeudado
    ws.column_dimensions["K"].width = 18  # Fecha Primera Vencida
    ws.column_dimensions["L"].width = 12  # Días Retraso
    ws.column_dimensions["M"].width = 15  # Monto >30 días

    # Totales
    total_row = len(datos) + 3
    ws.cell(row=total_row, column=7, value="TOTAL:")
    ws.cell(row=total_row, column=7).font = Font(bold=True)
    ws.cell(row=total_row, column=10, value=sum(d.get("total_adeudado", 0) for d in datos))
    ws.cell(row=total_row, column=10).font = Font(bold=True)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=informe_clientes_atrasados_{fecha}.xlsx"},
    )


def _generar_excel_rendimiento_analista(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo Excel para informe de rendimiento por analista"""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Rendimiento Analista"

        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)

        headers = [
            "Analista",
            "Total Clientes",
            "Total Préstamos",
            "Monto Total Adeudado",
            "Cuotas Vencidas",
            "Promedio Días Retraso",
        ]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        if datos and len(datos) > 0:
            for row_idx, registro in enumerate(datos, 2):
                ws.cell(row=row_idx, column=1, value=str(registro.get("analista", "Sin analista")))
                ws.cell(row=row_idx, column=2, value=registro.get("total_clientes", 0))
                ws.cell(row=row_idx, column=3, value=registro.get("total_prestamos", 0))
                ws.cell(row=row_idx, column=4, value=registro.get("monto_total_adeudado", 0))
                ws.cell(row=row_idx, column=5, value=registro.get("total_cuotas_vencidas", 0))
                ws.cell(
                    row=row_idx,
                    column=6,
                    value=round(registro.get("promedio_dias_retraso", 0), 2),
                )
        else:
            # Mensaje cuando no hay datos
            ws.cell(row=2, column=1, value="No se encontraron datos de analistas con cuotas vencidas")

        for col in range(1, 7):
            ws.column_dimensions[chr(64 + col)].width = 20

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        fecha = datetime.now().strftime("%Y%m%d")
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=informe_rendimiento_analista_{fecha}.xlsx"},
        )
    except Exception as e:
        logger.error(f"Error generando Excel rendimiento analista: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generando Excel: {str(e)}")


def _generar_excel_montos_periodo(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo Excel para informe de montos por período"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Montos por Período"

    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)

    headers = ["Mes", "Cantidad Cuotas", "Monto Total", "Clientes Únicos"]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for row_idx, registro in enumerate(datos, 2):
        ws.cell(
            row=row_idx,
            column=1,
            value=registro.get("mes_display") or registro.get("mes"),
        )
        ws.cell(row=row_idx, column=2, value=registro.get("cantidad_cuotas"))
        ws.cell(row=row_idx, column=3, value=registro.get("monto_total"))
        ws.cell(row=row_idx, column=4, value=registro.get("clientes_unicos"))

    for col in range(1, 5):
        ws.column_dimensions[chr(64 + col)].width = 20

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=informe_montos_periodo_{fecha}.xlsx"},
    )


def _generar_excel_antiguedad_saldos(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo Excel para informe de antigüedad de saldos"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Antigüedad Saldos"

    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)

    headers = ["Rango Antigüedad", "Cantidad Cuotas", "Monto Total", "Clientes Únicos"]

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for row_idx, registro in enumerate(datos, 2):
        ws.cell(row=row_idx, column=1, value=registro.get("rango_antiguedad"))
        ws.cell(row=row_idx, column=2, value=registro.get("cantidad_cuotas"))
        ws.cell(row=row_idx, column=3, value=registro.get("monto_total"))
        ws.cell(row=row_idx, column=4, value=registro.get("clientes_unicos"))

    for col in range(1, 5):
        ws.column_dimensions[chr(64 + col)].width = 20

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=informe_antiguedad_saldos_{fecha}.xlsx"},
    )


def _generar_excel_resumen_ejecutivo(datos: Dict) -> StreamingResponse:
    """Genera archivo Excel para informe resumen ejecutivo"""
    wb = Workbook()

    # Hoja 1: Resumen General
    ws1 = wb.active
    ws1.title = "Resumen General"

    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=14)

    ws1["A1"] = "RESUMEN EJECUTIVO DE COBRANZAS"
    ws1["A1"].font = header_font
    ws1["A1"].fill = header_fill

    resumen = datos.get("resumen_general", {})
    row = 3
    ws1.cell(row=row, column=1, value="Total Cuotas Vencidas:").font = Font(bold=True)
    ws1.cell(row=row, column=2, value=resumen.get("total_cuotas_vencidas", 0))
    row += 1
    ws1.cell(row=row, column=1, value="Monto Total Adeudado:").font = Font(bold=True)
    ws1.cell(row=row, column=2, value=resumen.get("monto_total_adeudado", 0))
    row += 1
    ws1.cell(row=row, column=1, value="Clientes Atrasados:").font = Font(bold=True)
    ws1.cell(row=row, column=2, value=resumen.get("clientes_atrasados", 0))
    row += 1
    ws1.cell(row=row, column=1, value="Promedio Deuda por Cliente:").font = Font(bold=True)
    ws1.cell(row=row, column=2, value=resumen.get("promedio_deuda_cliente", 0))

    # Hoja 2: Top Analistas
    ws2 = wb.create_sheet("Top Analistas")
    headers = ["Analista", "Monto Total Adeudado"]
    for col, header in enumerate(headers, 1):
        cell = ws2.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = Font(bold=True, color="FFFFFF")

    for row_idx, analista in enumerate(datos.get("top_analistas", []), 2):
        ws2.cell(row=row_idx, column=1, value=analista.get("analista"))
        ws2.cell(row=row_idx, column=2, value=analista.get("monto_total"))

    # Hoja 3: Top Clientes
    ws3 = wb.create_sheet("Top Clientes")
    headers = ["Cédula", "Nombres", "Total Adeudado", "Cuotas Vencidas"]
    for col, header in enumerate(headers, 1):
        cell = ws3.cell(row=1, column=col)
        cell.value = header
        cell.fill = header_fill
        cell.font = Font(bold=True, color="FFFFFF")

    for row_idx, cliente in enumerate(datos.get("top_clientes", []), 2):
        ws3.cell(row=row_idx, column=1, value=cliente.get("cedula"))
        ws3.cell(row=row_idx, column=2, value=cliente.get("nombres"))
        ws3.cell(row=row_idx, column=3, value=cliente.get("total_adeudado"))
        ws3.cell(row=row_idx, column=4, value=cliente.get("cuotas_vencidas"))

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=informe_resumen_ejecutivo_{fecha}.xlsx"},
    )


# ==
# FUNCIONES AUXILIARES PARA GENERACIÓN PDF
# ==


def _generar_pdf_clientes_atrasados(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo PDF para informe de clientes atrasados"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1 * inch)
    story = []
    styles = getSampleStyleSheet()

    # Título
    title = Paragraph("Informe de Clientes Atrasados", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))

    # Fecha de generación
    fecha_gen = Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"])
    story.append(fecha_gen)
    story.append(Spacer(1, 0.3 * inch))

    # Tabla de datos
    if datos:
        table_data = [["Cédula", "Nombres", "Analista", "Cuotas", "Riesgo ML", "Prob. %", "Adeudado", "Días Retraso"]]
        for registro in datos[:100]:  # Limitar a 100 registros por página
            ml_impago = registro.get("ml_impago")
            riesgo_ml = "N/A"
            prob_ml = "N/A"
            if ml_impago:
                riesgo_ml = ml_impago.get("nivel_riesgo", "N/A")
                prob_ml = f"{ml_impago.get('probabilidad_impago', 0.0) * 100:.1f}%"
            table_data.append(
                [
                    registro.get("cedula", ""),
                    registro.get("nombres", "")[:30],
                    (registro.get("analista", "") or "N/A")[:20],
                    str(registro.get("cuotas_vencidas", 0)),
                    riesgo_ml,
                    prob_ml,
                    f"${registro.get('total_adeudado', 0):,.2f}",
                    str(registro.get("dias_retraso", 0)),
                ]
            )

        table = Table(table_data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(table)

        # Total
        story.append(Spacer(1, 0.2 * inch))
        total_adeudado = sum(d.get("total_adeudado", 0) for d in datos)
        total = Paragraph(f"<b>Total Adeudado: ${total_adeudado:,.2f}</b>", styles["Normal"])
        story.append(total)

    doc.build(story)
    buffer.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=informe_clientes_atrasados_{fecha}.pdf"},
    )


def _generar_pdf_rendimiento_analista(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo PDF para informe de rendimiento por analista"""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()

        title = Paragraph("Informe de Rendimiento por Analista", styles["Title"])
        story.append(title)
        story.append(Spacer(1, 0.2 * inch))

        # Fecha de generación
        fecha_gen = Paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"])
        story.append(fecha_gen)
        story.append(Spacer(1, 0.3 * inch))

        if datos and len(datos) > 0:
            table_data = [["Analista", "Clientes", "Préstamos", "Monto Adeudado", "Promedio Días"]]
            for registro in datos:
                table_data.append(
                    [
                        str(registro.get("analista", "Sin analista"))[:30],
                        str(registro.get("total_clientes", 0)),
                        str(registro.get("total_prestamos", 0)),
                        f"${registro.get('monto_total_adeudado', 0):,.2f}",
                        f"{registro.get('promedio_dias_retraso', 0):.1f}",
                    ]
                )

            table = Table(table_data)
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            story.append(table)
        else:
            # Mensaje cuando no hay datos
            mensaje = Paragraph(
                "<i>No se encontraron datos de analistas con cuotas vencidas para el período seleccionado.</i>",
                styles["Normal"],
            )
            story.append(mensaje)

        doc.build(story)
        buffer.seek(0)

        fecha = datetime.now().strftime("%Y%m%d")
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=informe_rendimiento_analista_{fecha}.pdf"},
        )
    except Exception as e:
        logger.error(f"Error generando PDF rendimiento analista: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


def _generar_pdf_montos_periodo(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo PDF para informe de montos por período"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    title = Paragraph("Informe de Montos Vencidos por Período", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))

    if datos:
        table_data = [["Mes", "Cuotas", "Monto Total", "Clientes"]]
        for registro in datos:
            table_data.append(
                [
                    registro.get("mes_display", ""),
                    str(registro.get("cantidad_cuotas", 0)),
                    f"${registro.get('monto_total', 0):,.2f}",
                    str(registro.get("clientes_unicos", 0)),
                ]
            )

        table = Table(table_data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    buffer.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=informe_montos_periodo_{fecha}.pdf"},
    )


def _generar_pdf_antiguedad_saldos(datos: List[Dict]) -> StreamingResponse:
    """Genera archivo PDF para informe de antigüedad de saldos"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    title = Paragraph("Informe de Antigüedad de Saldos", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))

    if datos:
        table_data = [["Rango Antigüedad", "Cuotas", "Monto Total", "Clientes"]]
        for registro in datos:
            table_data.append(
                [
                    registro.get("rango_antiguedad", ""),
                    str(registro.get("cantidad_cuotas", 0)),
                    f"${registro.get('monto_total', 0):,.2f}",
                    str(registro.get("clientes_unicos", 0)),
                ]
            )

        table = Table(table_data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    buffer.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=informe_antiguedad_saldos_{fecha}.pdf"},
    )


def _generar_excel_categoria_dias(datos_categoria: List[Dict], datos_analista: List[Dict]) -> StreamingResponse:
    """Genera archivo Excel para informe por categoría de días"""
    buffer = BytesIO()
    wb = Workbook()
    wb.remove(wb.active)

    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Hoja 1: Por Categoría
    ws1 = wb.create_sheet("Por Categoría")
    headers1 = ["Categoría", "Cantidad Cuotas", "Monto Total", "Clientes Únicos"]
    ws1.append(headers1)

    # Estilo de encabezados
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    for col in range(1, len(headers1) + 1):
        cell = ws1.cell(row=1, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for registro in datos_categoria:
        ws1.append(
            [
                registro.get("categoria", ""),
                registro.get("cantidad_cuotas", 0),
                registro.get("monto_total", 0.0),
                registro.get("clientes_unicos", 0),
            ]
        )

    # Hoja 2: Por Analista
    ws2 = wb.create_sheet("Por Analista")
    ws2.append(["Analista", "Total Cuotas", "Total Monto"])

    # Encabezados de categorías (debe coincidir con los nombres del endpoint)
    categorias_headers_map = {
        "3 días antes de vencimiento": "3 días antes",
        "1 día antes de vencimiento": "1 día antes",
        "Día de pago": "Día de pago",
        "3 días atrasado": "3 días atrasado",
        "1 mes atrasado": "1 mes atrasado",
        "2 meses atrasado": "2 meses atrasado",
        "3 o más meses atrasado": "3+ meses atrasado",
    }

    categorias_headers = list(categorias_headers_map.values())
    header_row = ["Analista", "Total Cuotas", "Total Monto"] + categorias_headers
    ws2.append(header_row)

    for col in range(1, len(header_row) + 1):
        cell = ws2.cell(row=2, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for analista_data in datos_analista:
        row_data = [
            analista_data.get("analista", ""),
            analista_data.get("total_cuotas", 0),
            analista_data.get("total_monto", 0.0),
        ]

        # Crear diccionario de categorías por nombre completo
        categorias_dict = {c.get("categoria", ""): c for c in analista_data.get("categorias", [])}

        # Mapear nombres completos a headers cortos
        for cat_completa, cat_corta in categorias_headers_map.items():
            if cat_completa in categorias_dict:
                row_data.append(categorias_dict[cat_completa].get("cantidad_cuotas", 0))
            else:
                row_data.append(0)

        ws2.append(row_data)

    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=informe_categoria_dias_{fecha}.xlsx"},
    )


def _generar_pdf_categoria_dias(datos_categoria: List[Dict], datos_analista: List[Dict]) -> StreamingResponse:
    """Genera archivo PDF para informe por categoría de días"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    title = Paragraph("Informe por Categorías de Días y Analista", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(f"<b>Fecha de generación:</b> {fecha}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    # Sección 1: Por Categoría
    story.append(Paragraph("<b>Por Categoría de Días</b>", styles["Heading2"]))
    story.append(Spacer(1, 0.2 * inch))

    table_data = [["Categoría", "Cuotas", "Monto Total", "Clientes"]]
    for registro in datos_categoria:
        table_data.append(
            [
                registro.get("categoria", ""),
                str(registro.get("cantidad_cuotas", 0)),
                f"${registro.get('monto_total', 0):,.2f}",
                str(registro.get("clientes_unicos", 0)),
            ]
        )

    table = Table(table_data)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.4 * inch))

    # Sección 2: Por Analista
    story.append(Paragraph("<b>Por Analista</b>", styles["Heading2"]))
    story.append(Spacer(1, 0.2 * inch))

    for analista_data in datos_analista:
        analista_nombre = analista_data.get("analista", "Sin analista")
        total_cuotas = analista_data.get("total_cuotas", 0)
        total_monto = analista_data.get("total_monto", 0.0)

        story.append(
            Paragraph(
                f"<b>{analista_nombre}</b> - Total: {total_cuotas} cuotas, ${total_monto:,.2f}",
                styles["Normal"],
            )
        )

        categorias_data = analista_data.get("categorias", [])
        if categorias_data:
            cat_table_data = [["Categoría", "Cuotas", "Monto"]]
            for cat in categorias_data:
                cat_table_data.append(
                    [
                        cat.get("categoria", ""),
                        str(cat.get("cantidad_cuotas", 0)),
                        f"${cat.get('monto_total', 0):,.2f}",
                    ]
                )

            cat_table = Table(cat_table_data, colWidths=[3 * inch, 1.5 * inch, 1.5 * inch])
            cat_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ]
                )
            )
            story.append(cat_table)

        story.append(Spacer(1, 0.2 * inch))

    doc.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=informe_categoria_dias_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        },
    )


def _generar_pdf_resumen_ejecutivo(datos: Dict) -> StreamingResponse:
    """Genera archivo PDF para informe resumen ejecutivo"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    title = Paragraph("Informe Ejecutivo de Cobranzas", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 0.2 * inch))

    resumen = datos.get("resumen_general", {})

    # Resumen General
    story.append(Paragraph("<b>Resumen General</b>", styles["Heading2"]))
    resumen_data = [
        ["Indicador", "Valor"],
        ["Total Cuotas Vencidas", str(resumen.get("total_cuotas_vencidas", 0))],
        ["Monto Total Adeudado", f"${resumen.get('monto_total_adeudado', 0):,.2f}"],
        ["Clientes Atrasados", str(resumen.get("clientes_atrasados", 0))],
        [
            "Promedio Deuda por Cliente",
            f"${resumen.get('promedio_deuda_cliente', 0):,.2f}",
        ],
    ]

    resumen_table = Table(resumen_data)
    resumen_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(resumen_table)
    story.append(Spacer(1, 0.3 * inch))

    # Top Analistas
    if datos.get("top_analistas"):
        story.append(Paragraph("<b>Top 5 Analistas</b>", styles["Heading2"]))
        analistas_data = [["Analista", "Monto Total"]]
        for analista in datos.get("top_analistas", []):
            analistas_data.append(
                [
                    analista.get("analista", ""),
                    f"${analista.get('monto_total', 0):,.2f}",
                ]
            )

        analistas_table = Table(analistas_data)
        analistas_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        story.append(analistas_table)

    doc.build(story)
    buffer.seek(0)

    fecha = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=informe_resumen_ejecutivo_{fecha}.pdf"},
    )
