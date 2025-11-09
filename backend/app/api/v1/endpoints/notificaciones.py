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
from app.models.prestamo import Prestamo
from app.models.user import User
from app.schemas.notificacion_plantilla import (
    NotificacionPlantillaCreate,
    NotificacionPlantillaResponse,
    NotificacionPlantillaUpdate,
)
from app.services.email_service import EmailService
from app.services.notificacion_automatica_service import (
    NotificacionAutomaticaService,
)
from app.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)
router = APIRouter()


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
    fecha_creacion: datetime

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
            background_tasks.add_task(
                email_service.send_email,
                to_emails=[str(cliente.email)],
                subject=notificacion.asunto or "Notificación",
                body=notificacion.mensaje,
            )
        elif notificacion.canal == "WHATSAPP":
            whatsapp_service = WhatsAppService()
            background_tasks.add_task(
                whatsapp_service.send_message,
                to_number=str(cliente.telefono),
                message=notificacion.mensaje,
            )

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
                background_tasks.add_task(
                    email_service.send_email,
                    to_emails=[str(cliente.email)],
                    subject="Notificación Importante",
                    body=request.template,
                )
            elif request.canal == "WHATSAPP":
                whatsapp_service = WhatsAppService()
                background_tasks.add_task(
                    whatsapp_service.send_message,
                    to_number=str(cliente.telefono),
                    message=request.template,
                )

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Listar notificaciones con filtros y paginación
    """
    from sqlalchemy import text
    from sqlalchemy.exc import ProgrammingError

    from app.utils.pagination import calculate_pagination_params, create_paginated_response

    try:
        # Calcular paginación
        skip, limit = calculate_pagination_params(page=page, per_page=per_page, max_per_page=100)

        # Query base - usar query raw para evitar problemas con columnas faltantes
        from sqlalchemy import text

        # Verificar si la columna canal existe
        try:
            # Intentar hacer una query simple para verificar si la columna existe
            db.execute(text("SELECT canal FROM notificaciones LIMIT 1"))
            canal_exists = True
        except ProgrammingError:
            canal_exists = False
            logger.warning("Columna 'canal' no existe en BD. Usando query sin canal.")

        # Construir query según si canal existe
        if canal_exists:
            query = db.query(Notificacion)
        else:
            # Usar query raw seleccionando solo columnas que existen (usando parámetros seguros)
            base_query = text(
                """
                SELECT id, cliente_id, user_id, tipo, asunto, mensaje, estado, 
                       programada_para, enviada_en, leida, intentos, 
                       respuesta_servicio, error_mensaje, created_at
                FROM notificaciones
                WHERE (:estado IS NULL OR estado = :estado)
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
            """
            )

            result = db.execute(base_query, {"estado": estado, "limit": limit, "skip": skip})
            rows = result.fetchall()

            # Contar total (usando parámetros seguros)
            count_query = text(
                """
                SELECT COUNT(*) FROM notificaciones
                WHERE (:estado IS NULL OR estado = :estado)
            """
            )
            total = db.execute(count_query, {"estado": estado}).scalar() or 0

            # Serializar resultados
            items = []
            for row in rows:
                item_dict = {
                    "id": row[0],
                    "cliente_id": row[1],
                    "tipo": row[3],
                    "canal": None,  # No existe en BD
                    "mensaje": row[5],
                    "asunto": row[4],
                    "estado": row[6],
                    "fecha_envio": row[8],  # enviada_en
                    "fecha_creacion": row[13],  # created_at
                }
                items.append(NotificacionResponse.model_validate(item_dict))

            return create_paginated_response(items=items, total=total, page=page, page_size=limit)

        # Si canal existe, usar query normal
        if estado:
            query = query.filter(Notificacion.estado == estado)

        # Contar total
        total = query.count()

        # Aplicar paginación
        notificaciones = query.order_by(Notificacion.created_at.desc()).offset(skip).limit(limit).all()

        # Serializar notificaciones usando el schema
        items = [NotificacionResponse.model_validate(notif) for notif in notificaciones]

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
@cache_result(ttl=300, key_prefix="notificaciones")
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

        return {
            "total": total,
            "enviadas": enviadas,
            "pendientes": pendientes,
            "fallidas": fallidas,
            "no_leidas": no_leidas,
            "tasa_exito": (enviadas / total * 100) if total > 0 else 0,
        }

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

        # Reemplazar variables en el asunto y cuerpo
        asunto = plantilla.asunto
        cuerpo = plantilla.cuerpo

        for key, value in variables.items():
            asunto = asunto.replace(f"{{{{{key}}}}}", str(value))
            cuerpo = cuerpo.replace(f"{{{{{key}}}}}", str(value))

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

        # Enviar email en background
        if cliente.email:
            email_service = EmailService(db=db)
            background_tasks.add_task(
                email_service.send_email,
                to_emails=[str(cliente.email)],
                subject=asunto,
                body=cuerpo,
                is_html=True,
            )

        logger.info(f"Notificación enviada usando plantilla {plantilla_id}")

        return {
            "mensaje": "Notificación enviada",
            "cliente_id": cliente_id,
            "asunto": asunto,
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
