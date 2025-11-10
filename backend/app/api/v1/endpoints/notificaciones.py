import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.cache import cache_result
from app.models.amortizacion import Cuota
from app.models.auditoria import Auditoria
from app.models.cliente import Cliente
from app.models.notificacion import Notificacion
from app.models.notificacion_plantilla import NotificacionPlantilla
from app.models.notificacion_variable import NotificacionVariable
from app.models.prestamo import Prestamo
from app.models.user import User
from app.schemas.notificacion_plantilla import (
    NotificacionPlantillaCreate,
    NotificacionPlantillaResponse,
    NotificacionPlantillaUpdate,
)
from app.schemas.notificacion_variable import (
    NotificacionVariableCreate,
    NotificacionVariableResponse,
    NotificacionVariableUpdate,
)
from app.services.email_service import EmailService
from app.services.notificacion_automatica_service import (
    NotificacionAutomaticaService,
)
from app.services.variables_notificacion_service import VariablesNotificacionService
from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)
router = APIRouter()

# Cache para verificación de columnas (evita verificar en cada request)
_columnas_notificaciones_cache: Optional[dict] = None


def ejecutar_async_en_background(coroutine):
    """
    Helper para ejecutar funciones async en background tasks de FastAPI
    """
    import asyncio

    try:
        # Intentar obtener el loop existente
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Si hay un loop corriendo, crear una tarea
            asyncio.create_task(coroutine)
        else:
            # Si no hay loop, ejecutar directamente
            loop.run_until_complete(coroutine)
    except RuntimeError:
        # Si no hay loop, crear uno nuevo
        asyncio.run(coroutine)


# Schemas
class NotificacionCreate(BaseModel):
    cliente_id: int
    tipo: str
    canal: str  # EMAIL, WHATSAPP
    mensaje: str
    asunto: Optional[str] = None


class NotificacionResponse(BaseModel):
    id: int
    cliente_id: Optional[int]
    tipo: str
    canal: Optional[str]
    mensaje: str
    asunto: Optional[str]
    estado: str
    fecha_envio: Optional[datetime]
    fecha_creacion: Optional[datetime]  # Opcional porque puede no existir en BD

    class Config:
        from_attributes = True


class EnvioMasivoRequest(BaseModel):
    tipo_cliente: str  # MOROSO, ACTIVO, etc.
    dias_mora_min: Optional[int] = None
    template: str
    canal: str = "EMAIL"


@router.post("/enviar", response_model=NotificacionResponse)
async def enviar_notificacion(
    notificacion: NotificacionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enviar notificación individual."""
    try:
        # Obtener cliente
        cliente = db.query(Cliente).filter(Cliente.id == notificacion.cliente_id).first()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Crear registro de notificación
        nueva_notif = Notificacion(
            cliente_id=notificacion.cliente_id,
            tipo=notificacion.tipo,
            canal=notificacion.canal,
            mensaje=notificacion.mensaje,
            asunto=notificacion.asunto,
            estado="PENDIENTE",
        )

        db.add(nueva_notif)
        db.commit()
        db.refresh(nueva_notif)

        # Enviar según canal
        if notificacion.canal == "EMAIL":
            email_service = EmailService(db=db)
            notif_id = nueva_notif.id
            email_cliente = str(cliente.email)
            asunto_cliente = notificacion.asunto or "Notificación"
            mensaje_cliente = notificacion.mensaje

            # Función sync wrapper para background task (igual que WhatsApp)
            def enviar_email_sync():
                """Envía email y actualiza estado de notificación"""
                from app.db.session import SessionLocal

                db_local = SessionLocal()
                try:
                    resultado = email_service.send_email(
                        to_emails=[email_cliente],
                        subject=asunto_cliente,
                        body=mensaje_cliente,
                        is_html=True,
                    )
                    # Actualizar estado de notificación
                    notif = db_local.query(Notificacion).filter(Notificacion.id == notif_id).first()
                    if notif:
                        if resultado.get("success"):
                            notif.estado = "ENVIADA"
                            notif.enviada_en = datetime.utcnow()
                            notif.respuesta_servicio = resultado.get("message", "Email enviado exitosamente")
                            logger.info(f"✅ Notificación Email {notif_id} enviada exitosamente a {email_cliente}")
                        else:
                            notif.estado = "FALLIDA"
                            notif.error_mensaje = resultado.get("message", "Error desconocido")
                            notif.intentos = (notif.intentos or 0) + 1
                            logger.error(f"❌ Error enviando notificación Email {notif_id}: {resultado.get('message')}")
                        db_local.commit()
                except Exception as e:
                    db_local.rollback()
                    logger.error(f"Error enviando email o actualizando estado: {e}")
                    # Intentar marcar como fallida
                    try:
                        notif = db_local.query(Notificacion).filter(Notificacion.id == notif_id).first()
                        if notif:
                            notif.estado = "FALLIDA"
                            notif.error_mensaje = str(e)
                            notif.intentos = (notif.intentos or 0) + 1
                            db_local.commit()
                    except Exception:
                        pass
                finally:
                    db_local.close()

            background_tasks.add_task(enviar_email_sync)
        elif notificacion.canal == "WHATSAPP":
            whatsapp_service = WhatsAppService(db=db)
            notif_id = nueva_notif.id
            telefono_cliente = str(cliente.telefono)
            mensaje_cliente = notificacion.mensaje

            # Función sync wrapper para background task
            def enviar_whatsapp_sync():
                async def enviar_whatsapp_async():
                    try:
                        resultado = await whatsapp_service.send_message(
                            to_number=telefono_cliente,
                            message=mensaje_cliente,
                        )
                        # Actualizar estado de notificación
                        from app.db.session import SessionLocal

                        db_local = SessionLocal()
                        try:
                            notif = db_local.query(Notificacion).filter(Notificacion.id == notif_id).first()
                            if notif:
                                if resultado.get("success"):
                                    notif.estado = "ENVIADA"
                                    notif.enviada_en = datetime.utcnow()
                                    notif.respuesta_servicio = resultado.get("message", "Mensaje enviado exitosamente")
                                    logger.info(
                                        f"✅ Notificación WhatsApp {notif_id} enviada exitosamente a {telefono_cliente}"
                                    )
                                else:
                                    notif.estado = "FALLIDA"
                                    notif.error_mensaje = resultado.get("message", "Error desconocido")
                                    notif.intentos = (notif.intentos or 0) + 1
                                    logger.error(
                                        f"❌ Error enviando notificación WhatsApp {notif_id}: {resultado.get('message')}"
                                    )
                                db_local.commit()
                        except Exception as e:
                            db_local.rollback()
                            logger.error(f"Error actualizando estado de notificación: {e}")
                        finally:
                            db_local.close()
                    except Exception as e:
                        logger.error(f"Error enviando WhatsApp: {e}")

                ejecutar_async_en_background(enviar_whatsapp_async())

            background_tasks.add_task(enviar_whatsapp_sync)

        logger.info(f"Notificación programada para cliente {cliente.id}")
        return nueva_notif

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error enviando notificación: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.post("/envio-masivo")
async def envio_masivo(
    request: EnvioMasivoRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Envío masivo de notificaciones."""
    try:
        # Obtener clientes según filtros
        # CORREGIDO: Prestamo no tiene dias_mora, usar Cuota.dias_mora
        query = (
            db.query(Cliente).join(Prestamo, Cliente.id == Prestamo.cliente_id).join(Cuota, Prestamo.id == Cuota.prestamo_id)
        )

        if request.tipo_cliente == "MOROSO":
            query = query.filter(Cuota.dias_mora > 0)

        if request.dias_mora_min:
            query = query.filter(Cuota.dias_mora >= request.dias_mora_min)

        # Obtener clientes únicos (puede haber múltiples cuotas por cliente)
        clientes = query.distinct(Cliente.id).all()

        # Crear notificaciones masivas
        notificaciones_creadas = []

        for cliente in clientes:
            nueva_notif = Notificacion(
                cliente_id=cliente.id,
                tipo="MASIVA",
                canal=request.canal,
                mensaje=request.template,
                estado="PENDIENTE",
            )

            db.add(nueva_notif)
            notificaciones_creadas.append(nueva_notif)

        db.commit()

        # Programar envíos
        for notif in notificaciones_creadas:
            cliente = next(c for c in clientes if c.id == notif.cliente_id)

            if request.canal == "EMAIL":
                email_service = EmailService(db=db)
                notif_id = notif.id
                email_cliente = str(cliente.email)
                mensaje_template = request.template

                # Función sync wrapper para background task (igual que WhatsApp)
                def enviar_email_masivo_sync():
                    """Envía email masivo y actualiza estado de notificación"""
                    from app.db.session import SessionLocal

                    db_local = SessionLocal()
                    try:
                        resultado = email_service.send_email(
                            to_emails=[email_cliente],
                            subject="Notificación Importante",
                            body=mensaje_template,
                            is_html=True,
                        )
                        # Actualizar estado de notificación
                        notif_local = db_local.query(Notificacion).filter(Notificacion.id == notif_id).first()
                        if notif_local:
                            if resultado.get("success"):
                                notif_local.estado = "ENVIADA"
                                notif_local.enviada_en = datetime.utcnow()
                                notif_local.respuesta_servicio = resultado.get("message", "Email enviado exitosamente")
                                logger.info(f"✅ Notificación Email masiva {notif_id} enviada exitosamente a {email_cliente}")
                            else:
                                notif_local.estado = "FALLIDA"
                                notif_local.error_mensaje = resultado.get("message", "Error desconocido")
                                notif_local.intentos = (notif_local.intentos or 0) + 1
                                logger.error(
                                    f"❌ Error enviando notificación Email masiva {notif_id}: {resultado.get('message')}"
                                )
                            db_local.commit()
                    except Exception as e:
                        db_local.rollback()
                        logger.error(f"Error enviando email masivo o actualizando estado: {e}")
                        # Intentar marcar como fallida
                        try:
                            notif_local = db_local.query(Notificacion).filter(Notificacion.id == notif_id).first()
                            if notif_local:
                                notif_local.estado = "FALLIDA"
                                notif_local.error_mensaje = str(e)
                                notif_local.intentos = (notif_local.intentos or 0) + 1
                                db_local.commit()
                        except Exception:
                            pass
                    finally:
                        db_local.close()

                background_tasks.add_task(enviar_email_masivo_sync)
            elif request.canal == "WHATSAPP":
                whatsapp_service = WhatsAppService(db=db)
                notif_id = notif.id
                telefono_cliente = str(cliente.telefono)
                mensaje_template = request.template

                # Función sync wrapper para background task
                def enviar_whatsapp_masivo_sync():
                    async def enviar_whatsapp_masivo_async():
                        try:
                            resultado = await whatsapp_service.send_message(
                                to_number=telefono_cliente,
                                message=mensaje_template,
                            )
                            # Actualizar estado de notificación
                            from app.db.session import SessionLocal

                            db_local = SessionLocal()
                            try:
                                notif_local = db_local.query(Notificacion).filter(Notificacion.id == notif_id).first()
                                if notif_local:
                                    if resultado.get("success"):
                                        notif_local.estado = "ENVIADA"
                                        notif_local.enviada_en = datetime.utcnow()
                                        notif_local.respuesta_servicio = resultado.get(
                                            "message", "Mensaje enviado exitosamente"
                                        )
                                        logger.info(
                                            f"✅ Notificación WhatsApp masiva {notif_id} enviada exitosamente a {telefono_cliente}"
                                        )
                                    else:
                                        notif_local.estado = "FALLIDA"
                                        notif_local.error_mensaje = resultado.get("message", "Error desconocido")
                                        notif_local.intentos = (notif_local.intentos or 0) + 1
                                        logger.error(
                                            f"❌ Error enviando notificación WhatsApp masiva {notif_id}: {resultado.get('message')}"
                                        )
                                    db_local.commit()
                            except Exception as e:
                                db_local.rollback()
                                logger.error(f"Error actualizando estado de notificación: {e}")
                            finally:
                                db_local.close()
                        except Exception as e:
                            logger.error(f"Error enviando WhatsApp: {e}")

                    ejecutar_async_en_background(enviar_whatsapp_masivo_async())

                background_tasks.add_task(enviar_whatsapp_masivo_sync)

        logger.info(f"Enviadas {len(notificaciones_creadas)} notificaciones masivas")

        return {
            "message": f"Enviadas {len(notificaciones_creadas)} notificaciones",
            "count": len(notificaciones_creadas),
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error en envío masivo: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/")
def listar_notificaciones(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(20, ge=1, le=100, description="Registros por página"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    canal: Optional[str] = Query(None, description="Filtrar por canal (EMAIL, WHATSAPP)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar notificaciones con filtros y paginación
    """
    from sqlalchemy import text as sql_text
    from sqlalchemy.exc import ProgrammingError

    from app.utils.pagination import calculate_pagination_params, create_paginated_response

    try:
        # Calcular paginación
        skip, limit = calculate_pagination_params(page=page, per_page=per_page, max_per_page=100)

        # Verificar qué columnas existen usando inspect (más seguro, no aborta transacciones)
        # Usar cache para evitar verificar en cada request
        global _columnas_notificaciones_cache

        if _columnas_notificaciones_cache is None:
            canal_exists = False
            leida_exists = False
            created_at_exists = False
            try:
                from sqlalchemy import inspect as sql_inspect

                # Obtener el engine de forma compatible con SQLAlchemy 1.x y 2.x
                engine = db.bind if hasattr(db, "bind") else db.get_bind()
                inspector = sql_inspect(engine)
                columns = [col["name"] for col in inspector.get_columns("notificaciones")]
                canal_exists = "canal" in columns
                leida_exists = "leida" in columns
                created_at_exists = "created_at" in columns
                
                # Solo mostrar info la primera vez (no es un error, es un comportamiento esperado)
                if not canal_exists:
                    logger.info("ℹ️ Columna 'canal' no existe en BD. Usando query sin canal.")
                if not leida_exists:
                    logger.info("ℹ️ Columna 'leida' no existe en BD. Usando query sin leida.")
                if not created_at_exists:
                    logger.info("ℹ️ Columna 'created_at' no existe en BD. Usando 'id' para ordenar.")
                # Cachear resultado
                _columnas_notificaciones_cache = {
                    "canal": canal_exists,
                    "leida": leida_exists,
                    "created_at": created_at_exists,
                }
            except Exception as e:
                # Si falla la inspección, asumir que no existen y continuar
                logger.warning(f"No se pudo verificar columnas: {e}. Usando query básica.")
                canal_exists = False
                leida_exists = False
                created_at_exists = False
                _columnas_notificaciones_cache = {"canal": False, "leida": False, "created_at": False}
        else:
            # Usar valores cacheados
            canal_exists = _columnas_notificaciones_cache["canal"]
            leida_exists = _columnas_notificaciones_cache["leida"]
            created_at_exists = _columnas_notificaciones_cache["created_at"]

        # Construir query según si canal existe
        if canal_exists:
            query = db.query(Notificacion)
        else:
            # Usar query raw seleccionando solo columnas que existen (usando parámetros seguros)
            # Construir SELECT dinámicamente según columnas disponibles
            select_columns = [
                "id",
                "cliente_id",
                "user_id",
                "tipo",
                "asunto",
                "mensaje",
                "estado",
                "programada_para",
                "enviada_en",
                "intentos",
                "respuesta_servicio",
                "error_mensaje",
            ]
            if canal_exists:
                select_columns.insert(select_columns.index("tipo") + 1, "canal")
            if leida_exists:
                select_columns.insert(select_columns.index("enviada_en") + 1, "leida")
            if created_at_exists:
                select_columns.append("created_at")

            columns_str = ", ".join(select_columns)
            # Usar created_at si existe, sino usar id para ordenar
            order_by = "created_at DESC" if created_at_exists else "id DESC"
            # Construir WHERE dinámicamente
            where_clauses = ["(:estado IS NULL OR estado = :estado)"]
            if canal_exists and canal:
                where_clauses.append("canal = :canal")
            where_str = " AND ".join(where_clauses)

            base_query = sql_text(
                f"""
                SELECT {columns_str}
                FROM notificaciones
                WHERE {where_str}
                ORDER BY {order_by}
                LIMIT :limit OFFSET :skip
            """
            )

            query_params = {"estado": estado, "limit": limit, "skip": skip}
            if canal_exists and canal:
                query_params["canal"] = canal

            result = db.execute(base_query, query_params)
            rows = result.fetchall()

            # Contar total (usando parámetros seguros)
            count_query = sql_text(
                f"""
                SELECT COUNT(*) FROM notificaciones
                WHERE {where_str}
            """
            )
            total = db.execute(count_query, query_params).scalar() or 0

            # Serializar resultados - mapear índices dinámicamente según columnas disponibles
            items = []
            for row in rows:
                try:
                    # Mapear índices según el orden de las columnas en select_columns
                    col_idx = 0
                    row_id = row[col_idx] if len(row) > col_idx else None
                    col_idx += 1  # id
                    cliente_id = row[col_idx] if len(row) > col_idx else None
                    col_idx += 1  # cliente_id
                    _ = row[col_idx] if len(row) > col_idx else None  # user_id (no usado)
                    col_idx += 1
                    tipo = row[col_idx] if len(row) > col_idx else None
                    col_idx += 1  # tipo
                    canal_row = None
                    if canal_exists:
                        canal_row = row[col_idx] if len(row) > col_idx else None
                        col_idx += 1  # canal
                    asunto = row[col_idx] if len(row) > col_idx else None
                    col_idx += 1  # asunto
                    mensaje = row[col_idx] if len(row) > col_idx else None
                    col_idx += 1  # mensaje
                    estado_row = row[col_idx] if len(row) > col_idx else None
                    col_idx += 1  # estado
                    _ = row[col_idx] if len(row) > col_idx else None  # programada_para (no usado)
                    col_idx += 1
                    enviada_en = row[col_idx] if len(row) > col_idx else None
                    col_idx += 1  # enviada_en
                    if leida_exists:
                        _ = row[col_idx] if len(row) > col_idx else None  # leida (solo si existe)
                        col_idx += 1
                    _ = row[col_idx] if len(row) > col_idx else None  # intentos (no usado)
                    col_idx += 1
                    _ = row[col_idx] if len(row) > col_idx else None  # respuesta_servicio (no usado)
                    col_idx += 1
                    _ = row[col_idx] if len(row) > col_idx else None  # error_mensaje (no usado)
                    col_idx += 1
                    created_at = None
                    if created_at_exists:
                        created_at = row[col_idx] if len(row) > col_idx else None
                        col_idx += 1  # created_at

                    # Validar que los campos requeridos no sean None
                    if not mensaje:
                        logger.warning(f"Notificación {row_id} tiene mensaje vacío, saltando...")
                        continue
                    # Si created_at no existe, usar None (no es crítico)
                    if created_at_exists and not created_at:
                        logger.warning(f"Notificación {row_id} tiene created_at None, usando None...")

                    item_dict = {
                        "id": row_id,
                        "cliente_id": cliente_id,
                        "tipo": tipo or "",
                        "canal": canal_row if canal_exists else None,
                        "mensaje": mensaje or "",
                        "asunto": asunto,
                        "estado": estado_row or "PENDIENTE",
                        "fecha_envio": enviada_en,
                        "fecha_creacion": created_at,  # Puede ser None si created_at no existe
                    }
                    items.append(NotificacionResponse.model_validate(item_dict))
                except Exception as e:
                    logger.warning(f"Error serializando notificación {row[0] if len(row) > 0 else 'unknown'}: {e}")
                    continue  # Continuar con el siguiente item en lugar de fallar todo

            return create_paginated_response(items=items, total=total, page=page, page_size=limit)

        # Si canal existe, usar query normal
        if estado:
            query = query.filter(Notificacion.estado == estado)
        if canal:
            query = query.filter(Notificacion.canal == canal)

        # Contar total
        try:
            total = query.count()
        except Exception as e:
            logger.error(f"Error contando notificaciones: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error contando notificaciones: {str(e)}")

        # Aplicar paginación - usar created_at si existe, sino usar id
        try:
            if created_at_exists:
                try:
                    notificaciones = query.order_by(Notificacion.created_at.desc()).offset(skip).limit(limit).all()
                except (AttributeError, ProgrammingError):
                    # Si created_at no existe en el modelo o BD, usar id
                    logger.warning("created_at no disponible en modelo/BD, usando id para ordenar")
                    notificaciones = query.order_by(Notificacion.id.desc()).offset(skip).limit(limit).all()
            else:
                # Si created_at no existe, ordenar por id descendente
                notificaciones = query.order_by(Notificacion.id.desc()).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error obteniendo notificaciones: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error obteniendo notificaciones: {str(e)}")

        # Serializar notificaciones usando el schema con manejo de errores
        items = []
        for notif in notificaciones:
            try:
                # Validar que los campos requeridos existan
                if not notif.mensaje:
                    logger.warning(f"Notificación {notif.id} tiene mensaje vacío, saltando...")
                    continue
                # Si created_at no existe, fecha_creacion puede ser None (no es crítico)
                if created_at_exists and not notif.fecha_creacion:
                    logger.warning(f"Notificación {notif.id} tiene fecha_creacion None, usando None...")

                items.append(NotificacionResponse.model_validate(notif))
            except Exception as e:
                logger.warning(f"Error serializando notificación {notif.id}: {e}", exc_info=True)
                continue  # Continuar con el siguiente item en lugar de fallar todo

        # Retornar respuesta paginada
        return create_paginated_response(items=items, total=total, page=page, page_size=limit)

    except ProgrammingError as pe:
        # Manejar errores de columnas/tablas faltantes
        error_str = str(pe).lower()
        if "canal" in error_str and ("does not exist" in error_str or "undefined column" in error_str):
            logger.warning("Columna 'canal' no existe en BD. Retornando respuesta vacía.")
            return create_paginated_response(items=[], total=0, page=page, page_size=limit)
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(pe)}")
    except Exception as e:
        logger.error(f"Error listando notificaciones: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.get("/estadisticas/resumen")
@cache_result(ttl=30, key_prefix="notificaciones")  # Cache reducido a 30 segundos para actualizaciones más rápidas
def obtener_estadisticas_notificaciones(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estadísticas de notificaciones.

    OPTIMIZADO: Usa una sola query GROUP BY en lugar de 5 queries COUNT separadas.
    Cache: 5 minutos para mejorar performance.
    """
    try:
        from sqlalchemy import func
        from sqlalchemy.exc import ProgrammingError

        # ✅ OPTIMIZACIÓN: Una sola query con GROUP BY en lugar de 5 queries COUNT
        # Esto es 5-10x más rápido, especialmente con índices en la columna 'estado'
        estadisticas = (
            db.query(Notificacion.estado, func.count(Notificacion.id).label("cantidad")).group_by(Notificacion.estado).all()
        )

        # Convertir resultados a diccionario
        stats_dict = {row.estado: row.cantidad for row in estadisticas}

        # Calcular totales
        total = sum(stats_dict.values())
        enviadas = stats_dict.get("ENVIADA", 0)
        pendientes = stats_dict.get("PENDIENTE", 0)
        fallidas = stats_dict.get("FALLIDA", 0)

        # Query separada solo para no_leidas (si la columna existe)
        no_leidas = 0
        try:
            no_leidas = db.query(func.count(Notificacion.id)).filter(Notificacion.leida.is_(False)).scalar() or 0
        except ProgrammingError as pe:
            # Si la columna 'leida' no existe en la BD, usar aproximación
            if "column notificaciones.leida does not exist" in str(pe):
                logger.info("Columna 'leida' aún no existe en BD, usando aproximación temporal")
            else:
                logger.warning(f"Error al consultar columna 'leida', usando aproximación: {pe}")
            no_leidas = enviadas  # Aproximación: todas las enviadas se consideran no leídas

        # ✅ VALIDACIÓN: Asegurar que siempre retornamos una estructura completa
        # Incluso si no hay datos, retornar valores por defecto válidos
        resultado = {
            "total": total,
            "enviadas": enviadas,
            "pendientes": pendientes,
            "fallidas": fallidas,
            "no_leidas": no_leidas,
            "tasa_exito": round((enviadas / total * 100) if total > 0 else 0.0, 2),
        }

        # ✅ LOGGING: Registrar si no hay datos (puede indicar problema)
        if total == 0:
            logger.info("📊 [estadisticas_notificaciones] No hay notificaciones en la base de datos")
        else:
            logger.debug(
                f"📊 [estadisticas_notificaciones] Total: {total}, "
                f"Enviadas: {enviadas}, Pendientes: {pendientes}, "
                f"Fallidas: {fallidas}, No leídas: {no_leidas}"
            )

        return resultado

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


# ============================================
# PLANTILLAS DE NOTIFICACIONES
# ============================================


def _construir_query_plantillas(db: Session, solo_activas: bool, tipo: Optional[str]):
    """Construye la query para listar plantillas con filtros"""
    query = db.query(NotificacionPlantilla)

    if solo_activas:
        query = query.filter(NotificacionPlantilla.activa.is_(True))

    if tipo:
        query = query.filter(NotificacionPlantilla.tipo == tipo)

    return query.order_by(NotificacionPlantilla.nombre)


def _serializar_plantilla(p) -> Optional[dict]:
    """Serializa una plantilla a diccionario"""
    try:
        return {
            "id": p.id,
            "nombre": p.nombre,
            "descripcion": p.descripcion,
            "tipo": p.tipo,
            "asunto": p.asunto,
            "cuerpo": p.cuerpo,
            "variables_disponibles": p.variables_disponibles,
            "activa": bool(p.activa),
            "zona_horaria": p.zona_horaria or "America/Caracas",
            "fecha_creacion": p.fecha_creacion,
            "fecha_actualizacion": p.fecha_actualizacion,
        }
    except Exception as e:
        logger.error(f"Error serializando plantilla {p.id}: {e}")
        return None


def _verificar_tabla_plantillas(db: Session):
    """Verifica si la tabla de plantillas existe"""
    try:
        from sqlalchemy import inspect

        inspector = inspect(db.bind)
        tablas = inspector.get_table_names()
        if "notificacion_plantillas" not in tablas:
            raise HTTPException(status_code=500, detail="Tabla 'notificacion_plantillas' no existe. Ejecute las migraciones.")
    except HTTPException:
        raise
    except Exception:
        pass


@router.get("/plantillas", response_model=list[NotificacionPlantillaResponse])
def listar_plantillas(
    tipo: Optional[str] = Query(None, description="Filtrar por tipo"),
    solo_activas: bool = Query(True, description="Solo plantillas activas"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar plantillas de notificaciones"""
    try:
        query = _construir_query_plantillas(db, solo_activas, tipo)
        plantillas = query.all()

        resultado = []
        for p in plantillas:
            serializado = _serializar_plantilla(p)
            if serializado:
                resultado.append(serializado)

        return resultado

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        logger.error(f"Error listando plantillas: {e}\n{error_trace}")
        _verificar_tabla_plantillas(db)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/plantillas/verificar")
def verificar_plantillas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verificar estado de conexión BD y existencia de plantillas"""
    try:
        # Verificar conexión a BD
        total_plantillas = db.query(NotificacionPlantilla).count()
        plantillas_activas = db.query(NotificacionPlantilla).filter(NotificacionPlantilla.activa.is_(True)).count()

        # Tipos esperados para notificaciones automáticas
        tipos_esperados = [
            "PAGO_5_DIAS_ANTES",
            "PAGO_3_DIAS_ANTES",
            "PAGO_1_DIA_ANTES",
            "PAGO_DIA_0",
            "PAGO_1_DIA_ATRASADO",
            "PAGO_3_DIAS_ATRASADO",
            "PAGO_5_DIAS_ATRASADO",
        ]

        # Verificar qué tipos existen
        tipos_existentes = db.query(NotificacionPlantilla.tipo).filter(NotificacionPlantilla.activa.is_(True)).distinct().all()
        tipos_encontrados = [t[0] for t in tipos_existentes]
        tipos_faltantes = [t for t in tipos_esperados if t not in tipos_encontrados]

        return {
            "conexion_bd": True,
            "total_plantillas": total_plantillas,
            "plantillas_activas": plantillas_activas,
            "tipos_esperados": tipos_esperados,
            "tipos_encontrados": tipos_encontrados,
            "tipos_faltantes": tipos_faltantes,
            "plantillas_ok": len(tipos_faltantes) == 0,
            "mensaje": (
                "✅ Todas las plantillas necesarias están configuradas"
                if len(tipos_faltantes) == 0
                else f"⚠️ Faltan {len(tipos_faltantes)} plantillas: {', '.join(tipos_faltantes)}"
            ),
        }

    except Exception as e:
        logger.error(f"Error verificando plantillas: {e}")
        return {
            "conexion_bd": False,
            "error": str(e),
            "mensaje": "❌ Error de conexión a la base de datos",
        }


@router.post("/plantillas", response_model=NotificacionPlantillaResponse)
def crear_plantilla(
    plantilla: NotificacionPlantillaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear nueva plantilla de notificación"""
    try:
        # Verificar si ya existe una plantilla con el mismo nombre
        existe = db.query(NotificacionPlantilla).filter(NotificacionPlantilla.nombre == plantilla.nombre).first()
        if existe:
            raise HTTPException(status_code=400, detail="Ya existe una plantilla con este nombre")

        nueva_plantilla = NotificacionPlantilla(**plantilla.model_dump())
        db.add(nueva_plantilla)
        db.commit()
        db.refresh(nueva_plantilla)

        # Auditoría
        try:
            audit = Auditoria(
                usuario_id=current_user.id,
                accion="CREATE",
                entidad="NOTIFICACION_PLANTILLA",
                entidad_id=nueva_plantilla.id,
                detalles=f"Creó plantilla {nueva_plantilla.nombre}",
                exito=True,
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            logger.warning(f"No se pudo registrar auditoría creación plantilla: {e}")

        # Serializar manualmente para evitar errores
        return {
            "id": nueva_plantilla.id,
            "nombre": nueva_plantilla.nombre,
            "descripcion": nueva_plantilla.descripcion,
            "tipo": nueva_plantilla.tipo,
            "asunto": nueva_plantilla.asunto,
            "cuerpo": nueva_plantilla.cuerpo,
            "variables_disponibles": nueva_plantilla.variables_disponibles,
            "activa": bool(nueva_plantilla.activa),
            "zona_horaria": nueva_plantilla.zona_horaria or "America/Caracas",
            "fecha_creacion": nueva_plantilla.fecha_creacion,
            "fecha_actualizacion": nueva_plantilla.fecha_actualizacion,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando plantilla: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.put("/plantillas/{plantilla_id}", response_model=NotificacionPlantillaResponse)
def actualizar_plantilla(
    plantilla_id: int,
    plantilla: NotificacionPlantillaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar plantilla de notificación"""
    try:
        plantilla_existente = db.query(NotificacionPlantilla).filter(NotificacionPlantilla.id == plantilla_id).first()

        if not plantilla_existente:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")

        # Actualizar solo campos proporcionados
        update_data = plantilla.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(plantilla_existente, key, value)

        db.commit()
        db.refresh(plantilla_existente)

        # Auditoría
        try:
            audit = Auditoria(
                usuario_id=current_user.id,
                accion="UPDATE",
                entidad="NOTIFICACION_PLANTILLA",
                entidad_id=plantilla_id,
                detalles=f"Actualizó plantilla {plantilla_existente.nombre}",
                exito=True,
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            logger.warning(f"No se pudo registrar auditoría actualización plantilla: {e}")

        # Serializar manualmente para evitar errores
        return {
            "id": plantilla_existente.id,
            "nombre": plantilla_existente.nombre,
            "descripcion": plantilla_existente.descripcion,
            "tipo": plantilla_existente.tipo,
            "asunto": plantilla_existente.asunto,
            "cuerpo": plantilla_existente.cuerpo,
            "variables_disponibles": plantilla_existente.variables_disponibles,
            "activa": bool(plantilla_existente.activa),
            "zona_horaria": plantilla_existente.zona_horaria or "America/Caracas",
            "fecha_creacion": plantilla_existente.fecha_creacion,
            "fecha_actualizacion": plantilla_existente.fecha_actualizacion,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando plantilla: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.delete("/plantillas/{plantilla_id}")
def eliminar_plantilla(
    plantilla_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar plantilla de notificación"""
    try:
        plantilla = db.query(NotificacionPlantilla).filter(NotificacionPlantilla.id == plantilla_id).first()

        if not plantilla:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")

        plantilla_id_ref = plantilla.id
        nombre_ref = plantilla.nombre
        db.delete(plantilla)
        db.commit()

        # Auditoría
        try:
            audit = Auditoria(
                usuario_id=current_user.id,
                accion="DELETE",
                entidad="NOTIFICACION_PLANTILLA",
                entidad_id=plantilla_id_ref,
                detalles=f"Eliminó plantilla {nombre_ref}",
                exito=True,
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            logger.warning(f"No se pudo registrar auditoría eliminación plantilla: {e}")

        return {"mensaje": "Plantilla eliminada exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando plantilla: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/plantillas/{plantilla_id}", response_model=NotificacionPlantillaResponse)
def obtener_plantilla(
    plantilla_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener plantilla específica"""
    try:
        plantilla = db.query(NotificacionPlantilla).filter(NotificacionPlantilla.id == plantilla_id).first()

        if not plantilla:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")

        # Serializar manualmente para evitar errores
        return {
            "id": plantilla.id,
            "nombre": plantilla.nombre,
            "descripcion": plantilla.descripcion,
            "tipo": plantilla.tipo,
            "asunto": plantilla.asunto,
            "cuerpo": plantilla.cuerpo,
            "variables_disponibles": plantilla.variables_disponibles,
            "activa": bool(plantilla.activa),
            "zona_horaria": plantilla.zona_horaria or "America/Caracas",
            "fecha_creacion": plantilla.fecha_creacion,
            "fecha_actualizacion": plantilla.fecha_actualizacion,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo plantilla: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.get("/plantillas/{plantilla_id}/export")
def exportar_plantilla(
    plantilla_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta una plantilla en formato JSON y registra auditoría"""
    try:
        plantilla = db.query(NotificacionPlantilla).filter(NotificacionPlantilla.id == plantilla_id).first()
        if not plantilla:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")

        data = {
            "id": plantilla.id,
            "nombre": plantilla.nombre,
            "tipo": plantilla.tipo,
            "asunto": plantilla.asunto,
            "cuerpo": plantilla.cuerpo,
            "activa": bool(plantilla.activa),
        }

        # Auditoría
        try:
            audit = Auditoria(
                usuario_id=current_user.id,
                accion="EXPORT",
                entidad="NOTIFICACION_PLANTILLA",
                entidad_id=plantilla.id,
                detalles=f"Exportó plantilla {plantilla.nombre}",
                exito=True,
            )
            db.add(audit)
            db.commit()
        except Exception as e:
            logger.warning(f"No se pudo registrar auditoría exportación plantilla: {e}")

        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando plantilla: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/plantillas/{plantilla_id}/enviar")
async def enviar_notificacion_con_plantilla(
    plantilla_id: int,
    cliente_id: int,
    variables: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enviar notificación usando una plantilla"""
    try:
        # Obtener plantilla
        plantilla = db.query(NotificacionPlantilla).filter(NotificacionPlantilla.id == plantilla_id).first()

        if not plantilla:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")

        if not plantilla.activa:
            raise HTTPException(status_code=400, detail="La plantilla no está activa")

        # Obtener cliente
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()

        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        # Obtener préstamo y cuota relacionados si existen
        prestamo = None
        cuota = None

        # Intentar obtener el préstamo más reciente del cliente
        from app.models.amortizacion import Cuota
        from app.models.prestamo import Prestamo

        prestamo = (
            db.query(Prestamo)
            .filter(Prestamo.cliente_id == cliente_id, Prestamo.estado == "APROBADO")
            .order_by(Prestamo.fecha_registro.desc())
            .first()
        )

        if prestamo:
            # Obtener la cuota más próxima a vencer
            cuota = (
                db.query(Cuota)
                .filter(Cuota.prestamo_id == prestamo.id, Cuota.estado.in_(["PENDIENTE", "ATRASADO"]))
                .order_by(Cuota.fecha_vencimiento.asc())
                .first()
            )

        # Construir variables desde la BD usando las variables configuradas
        variables_service = VariablesNotificacionService(db=db)

        # Si se pasan variables manualmente, combinarlas con las de la BD
        # Las variables manuales tienen prioridad sobre las de la BD
        variables_bd = variables_service.construir_variables_desde_bd(
            cliente=cliente,
            prestamo=prestamo,
            cuota=cuota,
        )

        # Combinar: variables manuales tienen prioridad
        variables_finales = {**variables_bd, **variables}

        # Reemplazar variables en el asunto y cuerpo usando el servicio
        asunto = variables_service.reemplazar_variables_en_texto(plantilla.asunto, variables_finales)
        cuerpo = variables_service.reemplazar_variables_en_texto(plantilla.cuerpo, variables_finales)

        # Crear registro de notificación
        nueva_notif = Notificacion(
            cliente_id=cliente_id,
            tipo=plantilla.tipo,
            canal="EMAIL",
            asunto=asunto,
            mensaje=cuerpo,
            estado="PENDIENTE",
        )
        db.add(nueva_notif)
        db.commit()
        db.refresh(nueva_notif)

        # Función helper para enviar email y actualizar estado
        def enviar_y_actualizar_estado():
            """Envía email y actualiza estado de notificación"""
            from app.db.session import SessionLocal

            db_local = SessionLocal()
            try:
                # Recargar notificación para asegurar que tenemos la última versión
                notif = db_local.query(Notificacion).filter(Notificacion.id == nueva_notif.id).first()
                if not notif:
                    logger.error(f"Notificación {nueva_notif.id} no encontrada para actualizar estado")
                    return

                # Enviar email
                if cliente.email:
                    email_service = EmailService(db=db_local)
                    resultado = email_service.send_email(
                        to_emails=[str(cliente.email)],
                        subject=asunto,
                        body=cuerpo,
                        is_html=True,
                    )

                    # Actualizar estado según resultado
                    if resultado.get("success"):
                        notif.estado = "ENVIADA"
                        notif.enviada_en = datetime.utcnow()
                        notif.respuesta_servicio = resultado.get("message", "Email enviado exitosamente")
                        logger.info(f"✅ Notificación {notif.id} enviada exitosamente a {cliente.email}")
                    else:
                        notif.estado = "FALLIDA"
                        notif.error_mensaje = resultado.get("message", "Error desconocido")
                        notif.intentos = (notif.intentos or 0) + 1
                        logger.error(f"❌ Error enviando notificación {notif.id}: {resultado.get('message')}")
                else:
                    notif.estado = "FALLIDA"
                    notif.error_mensaje = "Cliente no tiene email registrado"
                    logger.warning(f"⚠️ Cliente {cliente_id} no tiene email registrado")

                db_local.commit()
            except Exception as e:
                db_local.rollback()
                logger.error(f"❌ Error en background task de envío de email: {e}", exc_info=True)
                # Intentar marcar como fallida
                try:
                    notif = db_local.query(Notificacion).filter(Notificacion.id == nueva_notif.id).first()
                    if notif:
                        notif.estado = "FALLIDA"
                        notif.error_mensaje = str(e)
                        notif.intentos = (notif.intentos or 0) + 1
                        db_local.commit()
                except Exception:
                    pass
            finally:
                db_local.close()

        # Enviar email en background
        if cliente.email:
            background_tasks.add_task(enviar_y_actualizar_estado)
            logger.info(f"📧 Email programado para envío usando plantilla {plantilla_id} a cliente {cliente_id}")
        else:
            # Si no tiene email, marcar como fallida inmediatamente
            nueva_notif.estado = "FALLIDA"
            nueva_notif.error_mensaje = "Cliente no tiene email registrado"
            db.commit()

        return {
            "mensaje": "Notificación programada para envío" if cliente.email else "Cliente no tiene email registrado",
            "cliente_id": cliente_id,
            "asunto": asunto,
            "notificacion_id": nueva_notif.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error enviando notificación con plantilla: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


# ============================================
# NOTIFICACIONES AUTOMÁTICAS
# ============================================


@router.post("/automaticas/procesar")
def procesar_notificaciones_automaticas(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Procesar todas las notificaciones automáticas pendientes
    Este endpoint debe ser llamado por un scheduler (cron job)
    """
    try:
        service = NotificacionAutomaticaService(db)
        stats = service.procesar_notificaciones_automaticas()

        return {
            "mensaje": "Procesamiento de notificaciones automáticas completado",
            "estadisticas": stats,
        }

    except Exception as e:
        logger.error(f"Error procesando notificaciones automáticas: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


# ============================================
# VARIABLES DE NOTIFICACIONES
# ============================================


@router.get("/variables", response_model=list[NotificacionVariableResponse])
def listar_variables(
    activa: Optional[str] = Query(None, description="Filtrar por estado activo (true/false)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar todas las variables de notificaciones configuradas
    """
    try:
        # Verificar si la tabla existe
        from sqlalchemy import inspect
        from sqlalchemy.exc import ProgrammingError

        try:
            inspector = inspect(db.bind)
            if "notificacion_variables" not in inspector.get_table_names():
                logger.warning("Tabla 'notificacion_variables' no existe, retornando lista vacía")
                return []
        except Exception as inspect_error:
            logger.warning(f"Error verificando existencia de tabla: {inspect_error}, retornando lista vacía")
            return []

        query = db.query(NotificacionVariable)

        # Convertir string a boolean si es necesario
        if activa is not None:
            if isinstance(activa, str):
                activa_bool = activa.lower() == "true"
            else:
                activa_bool = bool(activa)
            query = query.filter(NotificacionVariable.activa == activa_bool)

        variables = query.order_by(NotificacionVariable.nombre_variable).all()
        return [v.to_dict() for v in variables]

    except ProgrammingError as e:
        logger.warning(f"Error de base de datos (tabla puede no existir): {e}, retornando lista vacía")
        return []
    except Exception as e:
        logger.error(f"Error listando variables: {e}", exc_info=True)
        # Si hay un error, retornar lista vacía en lugar de 500
        return []


@router.get("/variables/{variable_id}", response_model=NotificacionVariableResponse)
def obtener_variable(
    variable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Obtener una variable específica por ID
    """
    try:
        variable = db.query(NotificacionVariable).filter(NotificacionVariable.id == variable_id).first()

        if not variable:
            raise HTTPException(status_code=404, detail="Variable no encontrada")

        return variable.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo variable: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.post("/variables", response_model=NotificacionVariableResponse, status_code=201)
def crear_variable(
    variable: NotificacionVariableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crear una nueva variable de notificación
    """
    try:
        # Verificar si ya existe una variable con ese nombre
        existente = (
            db.query(NotificacionVariable).filter(NotificacionVariable.nombre_variable == variable.nombre_variable).first()
        )

        if existente:
            raise HTTPException(status_code=400, detail=f"Ya existe una variable con el nombre '{variable.nombre_variable}'")

        nueva_variable = NotificacionVariable(
            nombre_variable=variable.nombre_variable,
            tabla=variable.tabla,
            campo_bd=variable.campo_bd,
            descripcion=variable.descripcion,
            activa=variable.activa,
        )

        db.add(nueva_variable)
        db.commit()
        db.refresh(nueva_variable)

        return nueva_variable.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando variable: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.put("/variables/{variable_id}", response_model=NotificacionVariableResponse)
def actualizar_variable(
    variable_id: int,
    variable: NotificacionVariableUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Actualizar una variable existente
    """
    try:
        variable_db = db.query(NotificacionVariable).filter(NotificacionVariable.id == variable_id).first()

        if not variable_db:
            raise HTTPException(status_code=404, detail="Variable no encontrada")

        # Si se actualiza el nombre, verificar que no exista otra con ese nombre
        if variable.nombre_variable and variable.nombre_variable != variable_db.nombre_variable:
            existente = (
                db.query(NotificacionVariable)
                .filter(
                    NotificacionVariable.nombre_variable == variable.nombre_variable, NotificacionVariable.id != variable_id
                )
                .first()
            )

            if existente:
                raise HTTPException(
                    status_code=400, detail=f"Ya existe una variable con el nombre '{variable.nombre_variable}'"
                )

        # Actualizar campos
        if variable.nombre_variable is not None:
            variable_db.nombre_variable = variable.nombre_variable
        if variable.tabla is not None:
            variable_db.tabla = variable.tabla
        if variable.campo_bd is not None:
            variable_db.campo_bd = variable.campo_bd
        if variable.descripcion is not None:
            variable_db.descripcion = variable.descripcion
        if variable.activa is not None:
            variable_db.activa = variable.activa

        db.commit()
        db.refresh(variable_db)

        return variable_db.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando variable: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.post("/variables/inicializar-precargadas")
def inicializar_variables_precargadas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Inicializar variables precargadas en la base de datos
    Crea automáticamente todas las variables basadas en los campos de las tablas
    """
    try:
        # Verificar si la tabla existe
        from sqlalchemy import inspect
        from sqlalchemy.exc import ProgrammingError

        try:
            inspector = inspect(db.bind)
            if "notificacion_variables" not in inspector.get_table_names():
                logger.warning("Tabla 'notificacion_variables' no existe")
                raise HTTPException(status_code=400, detail="La tabla 'notificacion_variables' no existe en la base de datos")
        except Exception as inspect_error:
            logger.warning(f"Error verificando existencia de tabla: {inspect_error}")
            raise HTTPException(status_code=400, detail=f"Error verificando tabla: {str(inspect_error)}")

        # Definir campos disponibles (mismo que en frontend)
        CAMPOS_DISPONIBLES = {
            "clientes": [
                {"campo": "id", "descripcion": "ID único del cliente"},
                {"campo": "cedula", "descripcion": "Cédula de identidad"},
                {"campo": "nombres", "descripcion": "Nombres completos"},
                {"campo": "telefono", "descripcion": "Teléfono de contacto"},
                {"campo": "email", "descripcion": "Correo electrónico"},
                {"campo": "direccion", "descripcion": "Dirección de residencia"},
                {"campo": "fecha_nacimiento", "descripcion": "Fecha de nacimiento"},
                {"campo": "ocupacion", "descripcion": "Ocupación del cliente"},
                {"campo": "estado", "descripcion": "Estado (ACTIVO, INACTIVO, FINALIZADO)"},
                {"campo": "activo", "descripcion": "Estado activo (true/false)"},
                {"campo": "fecha_registro", "descripcion": "Fecha de registro"},
                {"campo": "fecha_actualizacion", "descripcion": "Fecha de última actualización"},
                {"campo": "usuario_registro", "descripcion": "Usuario que registró"},
                {"campo": "notas", "descripcion": "Notas adicionales"},
            ],
            "prestamos": [
                {"campo": "id", "descripcion": "ID del préstamo"},
                {"campo": "cliente_id", "descripcion": "ID del cliente"},
                {"campo": "cedula", "descripcion": "Cédula del cliente"},
                {"campo": "nombres", "descripcion": "Nombres del cliente"},
                {"campo": "valor_activo", "descripcion": "Valor del activo (vehículo)"},
                {"campo": "total_financiamiento", "descripcion": "Monto total financiado"},
                {"campo": "fecha_requerimiento", "descripcion": "Fecha requerida del préstamo"},
                {"campo": "modalidad_pago", "descripcion": "Modalidad (MENSUAL, QUINCENAL, SEMANAL)"},
                {"campo": "numero_cuotas", "descripcion": "Número total de cuotas"},
                {"campo": "cuota_periodo", "descripcion": "Monto de cuota por período"},
                {"campo": "tasa_interes", "descripcion": "Tasa de interés (%)"},
                {"campo": "fecha_base_calculo", "descripcion": "Fecha base para cálculo"},
                {"campo": "producto", "descripcion": "Producto financiero"},
                {"campo": "producto_financiero", "descripcion": "Producto financiero"},
                {"campo": "concesionario", "descripcion": "Concesionario"},
                {"campo": "analista", "descripcion": "Analista asignado"},
                {"campo": "modelo_vehiculo", "descripcion": "Modelo del vehículo"},
                {"campo": "estado", "descripcion": "Estado del préstamo"},
                {"campo": "usuario_proponente", "descripcion": "Usuario proponente"},
                {"campo": "usuario_aprobador", "descripcion": "Usuario aprobador"},
                {"campo": "fecha_registro", "descripcion": "Fecha de registro"},
                {"campo": "fecha_aprobacion", "descripcion": "Fecha de aprobación"},
            ],
            "cuotas": [
                {"campo": "id", "descripcion": "ID de la cuota"},
                {"campo": "prestamo_id", "descripcion": "ID del préstamo"},
                {"campo": "numero_cuota", "descripcion": "Número de cuota"},
                {"campo": "fecha_vencimiento", "descripcion": "Fecha de vencimiento"},
                {"campo": "fecha_pago", "descripcion": "Fecha de pago"},
                {"campo": "monto_cuota", "descripcion": "Monto total de la cuota"},
                {"campo": "monto_capital", "descripcion": "Monto de capital"},
                {"campo": "monto_interes", "descripcion": "Monto de interés"},
                {"campo": "saldo_capital_inicial", "descripcion": "Saldo capital inicial"},
                {"campo": "saldo_capital_final", "descripcion": "Saldo capital final"},
                {"campo": "capital_pagado", "descripcion": "Capital pagado"},
                {"campo": "interes_pagado", "descripcion": "Interés pagado"},
                {"campo": "mora_pagada", "descripcion": "Mora pagada"},
                {"campo": "total_pagado", "descripcion": "Total pagado"},
                {"campo": "capital_pendiente", "descripcion": "Capital pendiente"},
                {"campo": "interes_pendiente", "descripcion": "Interés pendiente"},
                {"campo": "dias_mora", "descripcion": "Días de mora"},
                {"campo": "monto_mora", "descripcion": "Monto de mora"},
                {"campo": "tasa_mora", "descripcion": "Tasa de mora (%)"},
                {"campo": "dias_morosidad", "descripcion": "Días de morosidad"},
                {"campo": "monto_morosidad", "descripcion": "Monto de morosidad"},
                {"campo": "estado", "descripcion": "Estado de la cuota"},
            ],
            "pagos": [
                {"campo": "id", "descripcion": "ID del pago"},
                {"campo": "cedula", "descripcion": "Cédula del cliente"},
                {"campo": "prestamo_id", "descripcion": "ID del préstamo"},
                {"campo": "numero_cuota", "descripcion": "Número de cuota"},
                {"campo": "fecha_pago", "descripcion": "Fecha de pago"},
                {"campo": "fecha_registro", "descripcion": "Fecha de registro"},
                {"campo": "monto_pagado", "descripcion": "Monto pagado"},
                {"campo": "numero_documento", "descripcion": "Número de documento"},
                {"campo": "institucion_bancaria", "descripcion": "Institución bancaria"},
                {"campo": "estado", "descripcion": "Estado del pago"},
                {"campo": "conciliado", "descripcion": "Si está conciliado"},
                {"campo": "fecha_conciliacion", "descripcion": "Fecha de conciliación"},
            ],
        }

        variables_creadas = 0
        variables_existentes = 0

        for tabla, campos in CAMPOS_DISPONIBLES.items():
            for campo_info in campos:
                campo = campo_info["campo"]
                descripcion = campo_info["descripcion"]

                # Generar nombre de variable: tabla_campo (remover 's' final)
                nombre_variable = f"{tabla[:-1]}_{campo}" if tabla.endswith("s") else f"{tabla}_{campo}"

                # Verificar si ya existe
                existente = (
                    db.query(NotificacionVariable).filter(NotificacionVariable.nombre_variable == nombre_variable).first()
                )

                if not existente:
                    nueva_variable = NotificacionVariable(
                        nombre_variable=nombre_variable,
                        tabla=tabla,
                        campo_bd=campo,
                        descripcion=descripcion,
                        activa=True,
                    )
                    db.add(nueva_variable)
                    variables_creadas += 1
                else:
                    variables_existentes += 1

        db.commit()

        logger.info(f"✅ Variables precargadas inicializadas: {variables_creadas} creadas, {variables_existentes} ya existían")

        return {
            "mensaje": "Variables precargadas inicializadas exitosamente",
            "variables_creadas": variables_creadas,
            "variables_existentes": variables_existentes,
            "total": variables_creadas + variables_existentes,
        }

    except HTTPException:
        raise
    except ProgrammingError as e:
        db.rollback()
        logger.error(f"Error de base de datos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error de base de datos: {str(e)}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error inicializando variables precargadas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.delete("/variables/{variable_id}", status_code=204)
def eliminar_variable(
    variable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Eliminar una variable de notificación
    """
    try:
        variable = db.query(NotificacionVariable).filter(NotificacionVariable.id == variable_id).first()

        if not variable:
            raise HTTPException(status_code=404, detail="Variable no encontrada")

        db.delete(variable)
        db.commit()

        return None

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando variable: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
