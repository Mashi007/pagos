"""
Endpoints para entrenamiento de AI
Fine-tuning, RAG
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session, joinedload, load_only

from app.api.deps import get_current_user, get_db
from app.models.cliente import Cliente
from app.models.conversacion_ai import ConversacionAI
from app.models.documento_ai import DocumentoAI
from app.models.documento_embedding import DocumentoEmbedding
from app.models.fine_tuning_job import FineTuningJob
from app.models.user import User
from app.services.ai_training_service import AITrainingService
from app.services.rag_service import RAGService


logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================
# SCHEMAS
# ============================================


class ConversacionCreate(BaseModel):
    pregunta: str
    respuesta: str
    contexto_usado: Optional[str] = None
    documentos_usados: Optional[List[int]] = None
    modelo_usado: Optional[str] = None
    tokens_usados: Optional[int] = None
    tiempo_respuesta: Optional[int] = None
    cliente_id: Optional[int] = None
    prestamo_id: Optional[int] = None
    pago_id: Optional[int] = None
    cuota_id: Optional[int] = None


class CalificarConversacionRequest(BaseModel):
    calificacion: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None


class MejorarConversacionRequest(BaseModel):
    pregunta: Optional[str] = Field(None, description="Pregunta a mejorar")
    respuesta: Optional[str] = Field(None, description="Respuesta a mejorar")


class PrepararDatosRequest(BaseModel):
    conversacion_ids: Optional[List[int]] = None
    filtrar_feedback_negativo: bool = Field(True, description="Excluir conversaciones con feedback negativo automáticamente")


class IniciarFineTuningRequest(BaseModel):
    archivo_id: str
    modelo_base: str = "gpt-4o-2024-08-06"  # Versión específica de gpt-4o requerida para fine-tuning
    epochs: Optional[int] = None
    learning_rate: Optional[float] = None


class ActivarModeloRequest(BaseModel):
    modelo_id: str


class GenerarEmbeddingsRequest(BaseModel):
    documento_ids: Optional[List[int]] = None


class BuscarDocumentosRequest(BaseModel):
    pregunta: str
    top_k: int = 3




# ============================================
# HELPER FUNCTIONS
# ============================================


def _handle_database_error(e: Exception, operation: str) -> HTTPException:
    """Manejar errores de base de datos y retornar mensajes claros"""
    error_str = str(e).lower()

    # Detectar errores de tablas no encontradas
    if "does not exist" in error_str or "no such table" in error_str or "relation" in error_str:
        logger.error(f"Tablas de AI training no encontradas. Error: {e}")
        return HTTPException(
            status_code=503,
            detail=(
                "Las tablas de entrenamiento AI no están creadas. " "Ejecuta las migraciones de Alembic: alembic upgrade head"
            ),
        )

    # Otros errores de base de datos
    if isinstance(e, (ProgrammingError, OperationalError)):
        logger.error(f"Error de base de datos en {operation}: {e}", exc_info=True)
        return HTTPException(
            status_code=500,
            detail=f"Error de base de datos en {operation}: {str(e)}",
        )

    # Error genérico
    logger.error(f"Error en {operation}: {e}", exc_info=True)
    return HTTPException(status_code=500, detail=f"Error en {operation}: {str(e)}")


def _obtener_openai_api_key(db: Session) -> str:
    """Obtener API key de OpenAI desde configuración (desencriptada)"""
    from app.core.encryption import decrypt_api_key
    from app.models.configuracion_sistema import ConfiguracionSistema

    config = (
        db.query(ConfiguracionSistema)
        .filter(
            and_(
                ConfiguracionSistema.categoria == "AI",
                ConfiguracionSistema.clave == "openai_api_key",
            )
        )
        .first()
    )

    if not config or not config.valor:
        raise HTTPException(status_code=400, detail="OpenAI API Key no configurado")

    # Desencriptar API Key si está encriptada
    return decrypt_api_key(config.valor)


# ============================================
# FINE-TUNING ENDPOINTS
# ============================================


@router.get("/conversaciones")
async def listar_conversaciones(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    con_calificacion: Optional[bool] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar conversaciones para fine-tuning"""
    try:
        query = db.query(ConversacionAI)

        if con_calificacion is not None:
            if con_calificacion:
                query = query.filter(ConversacionAI.calificacion.isnot(None))
            else:
                query = query.filter(ConversacionAI.calificacion.is_(None))

        if fecha_desde:
            query = query.filter(ConversacionAI.creado_en >= fecha_desde)

        if fecha_hasta:
            query = query.filter(ConversacionAI.creado_en <= fecha_hasta)

        total = query.count()
        conversaciones = query.order_by(ConversacionAI.creado_en.desc()).offset((page - 1) * per_page).limit(per_page).all()

        return {
            "conversaciones": [c.to_dict() for c in conversaciones],
            "total": total,
            "page": page,
            "total_pages": (total + per_page - 1) // per_page,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_database_error(e, "listando conversaciones")


@router.post("/conversaciones")
async def crear_conversacion(
    conversacion: ConversacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crear nueva conversación"""
    try:
        documentos_str = ",".join(map(str, conversacion.documentos_usados)) if conversacion.documentos_usados else None

        nueva_conversacion = ConversacionAI(
            pregunta=conversacion.pregunta,
            respuesta=conversacion.respuesta,
            contexto_usado=conversacion.contexto_usado,
            documentos_usados=documentos_str,
            modelo_usado=conversacion.modelo_usado,
            tokens_usados=conversacion.tokens_usados,
            tiempo_respuesta=conversacion.tiempo_respuesta,
            usuario_id=current_user.id,
            cliente_id=conversacion.cliente_id,
            prestamo_id=conversacion.prestamo_id,
            pago_id=conversacion.pago_id,
            cuota_id=conversacion.cuota_id,
        )

        db.add(nueva_conversacion)
        db.commit()
        db.refresh(nueva_conversacion)

        return {"conversacion": nueva_conversacion.to_dict()}

    except Exception as e:
        db.rollback()
        logger.error(f"Error creando conversación: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creando conversación: {str(e)}")


@router.put("/conversaciones/{conversacion_id}")
async def actualizar_conversacion(
    conversacion_id: int,
    conversacion: ConversacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar una conversación existente"""
    try:
        conversacion_existente = db.query(ConversacionAI).filter(ConversacionAI.id == conversacion_id).first()

        if not conversacion_existente:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")

        # Actualizar campos
        conversacion_existente.pregunta = conversacion.pregunta
        conversacion_existente.respuesta = conversacion.respuesta
        if conversacion.contexto_usado is not None:
            conversacion_existente.contexto_usado = conversacion.contexto_usado
        if conversacion.documentos_usados:
            conversacion_existente.documentos_usados = ",".join(map(str, conversacion.documentos_usados))
        if conversacion.modelo_usado is not None:
            conversacion_existente.modelo_usado = conversacion.modelo_usado

        # Si se actualiza pregunta/respuesta, resetear calificación para revisión
        # (opcional: puedes comentar estas líneas si quieres mantener la calificación)
        # conversacion_existente.calificacion = None
        # conversacion_existente.feedback = None

        db.commit()
        db.refresh(conversacion_existente)

        logger.info(f"✅ Conversación {conversacion_id} actualizada por usuario {current_user.email}")

        return {"conversacion": conversacion_existente.to_dict()}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando conversación: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error actualizando conversación: {str(e)}")


@router.get("/conversaciones/estadisticas-feedback")
async def obtener_estadisticas_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener estadísticas sobre feedback de conversaciones"""
    try:
        from sqlalchemy import case, func

        # Total de conversaciones
        total_conversaciones = db.query(ConversacionAI).count()

        # Conversaciones con calificación
        conversaciones_calificadas = db.query(ConversacionAI).filter(ConversacionAI.calificacion.isnot(None)).count()

        # Conversaciones con feedback
        conversaciones_con_feedback = (
            db.query(ConversacionAI).filter(ConversacionAI.feedback.isnot(None), ConversacionAI.feedback != "").count()
        )

        # Distribución de calificaciones
        distribucion_calificaciones = (
            db.query(ConversacionAI.calificacion, func.count(ConversacionAI.id).label("cantidad"))
            .filter(ConversacionAI.calificacion.isnot(None))
            .group_by(ConversacionAI.calificacion)
            .all()
        )

        distribucion = {str(cal): cant for cal, cant in distribucion_calificaciones}

        # Análisis de feedback (usar servicio para detectar negativo)
        # Crear instancia temporal solo para usar el método de detección
        temp_service = AITrainingService("dummy")  # No necesitamos API key para detección
        conversaciones_con_feedback_list = (
            db.query(ConversacionAI).filter(ConversacionAI.feedback.isnot(None), ConversacionAI.feedback != "").all()
        )

        feedback_positivo = 0
        feedback_negativo = 0
        feedback_neutro = 0

        for conv in conversaciones_con_feedback_list:
            if temp_service._detectar_feedback_negativo(conv.feedback):
                feedback_negativo += 1
            elif conv.calificacion and conv.calificacion >= 4:
                feedback_positivo += 1
            else:
                feedback_neutro += 1

        # Conversaciones listas para entrenamiento (4+ estrellas, sin feedback negativo)
        conversaciones_listas = (
            db.query(ConversacionAI).filter(ConversacionAI.calificacion.isnot(None), ConversacionAI.calificacion >= 4).all()
        )

        listas_sin_feedback_negativo = 0
        listas_con_feedback_negativo = 0

        for conv in conversaciones_listas:
            if conv.feedback and temp_service._detectar_feedback_negativo(conv.feedback):
                listas_con_feedback_negativo += 1
            else:
                listas_sin_feedback_negativo += 1

        return {
            "total_conversaciones": total_conversaciones,
            "conversaciones_calificadas": conversaciones_calificadas,
            "conversaciones_con_feedback": conversaciones_con_feedback,
            "distribucion_calificaciones": distribucion,
            "analisis_feedback": {
                "positivo": feedback_positivo,
                "negativo": feedback_negativo,
                "neutro": feedback_neutro,
                "total": conversaciones_con_feedback,
            },
            "conversaciones_listas_entrenamiento": {
                "total": len(conversaciones_listas),
                "sin_feedback_negativo": listas_sin_feedback_negativo,
                "con_feedback_negativo": listas_con_feedback_negativo,
                "puede_preparar": listas_sin_feedback_negativo >= 1,
            },
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")


@router.post("/conversaciones/mejorar")
async def mejorar_conversacion(
    request: MejorarConversacionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mejorar pregunta y/o respuesta usando IA para optimizar el entrenamiento"""
    try:
        if not request.pregunta and not request.respuesta:
            raise HTTPException(status_code=400, detail="Debe proporcionar al menos pregunta o respuesta")

        # Obtener API key
        openai_api_key = _obtener_openai_api_key(db)

        # Preparar datos
        service = AITrainingService(openai_api_key)
        resultado = await service.mejorar_conversacion_para_entrenamiento(
            pregunta=request.pregunta or "",
            respuesta=request.respuesta or "",
        )

        return resultado

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error mejorando conversación: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error mejorando conversación: {str(e)}")


@router.post("/conversaciones/{conversacion_id}/calificar")
async def calificar_conversacion(
    conversacion_id: int,
    request: CalificarConversacionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calificar una conversación"""
    try:
        conversacion = db.query(ConversacionAI).filter(ConversacionAI.id == conversacion_id).first()

        if not conversacion:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")

        conversacion.calificacion = request.calificacion
        conversacion.feedback = request.feedback

        db.commit()
        db.refresh(conversacion)

        return {"conversacion": conversacion.to_dict()}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error calificando conversación: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calificando conversación: {str(e)}")


@router.post("/fine-tuning/preparar")
async def preparar_datos_entrenamiento(
    request: PrepararDatosRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preparar datos para fine-tuning"""
    try:
        # Obtener conversaciones calificadas (4+ estrellas)
        query = db.query(ConversacionAI).filter(
            and_(
                ConversacionAI.calificacion.isnot(None),
                ConversacionAI.calificacion >= 4,
            )
        )

        if request.conversacion_ids:
            query = query.filter(ConversacionAI.id.in_(request.conversacion_ids))

        conversaciones = query.all()

        # OpenAI requiere mínimo 10 conversaciones para fine-tuning
        MINIMO_CONVERSACIONES = 10
        if len(conversaciones) < MINIMO_CONVERSACIONES:
            raise HTTPException(
                status_code=400,
                detail=f"Se necesita al menos {MINIMO_CONVERSACIONES} conversaciones calificadas (4+ estrellas) para entrenar un modelo. OpenAI requiere mínimo 10 ejemplos. Actualmente hay {len(conversaciones)}.",
            )

        # Obtener API key
        openai_api_key = _obtener_openai_api_key(db)

        # Preparar datos
        service = AITrainingService(openai_api_key)
        conversaciones_data = [c.to_dict() for c in conversaciones]
        result = await service.preparar_datos_entrenamiento(
            conversaciones_data, filtrar_feedback_negativo=request.filtrar_feedback_negativo
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error preparando datos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error preparando datos: {str(e)}")


@router.post("/fine-tuning/iniciar")
async def iniciar_fine_tuning(
    request: IniciarFineTuningRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Iniciar job de fine-tuning"""
    try:
        openai_api_key = _obtener_openai_api_key(db)

        service = AITrainingService(openai_api_key)
        job_data = await service.iniciar_fine_tuning(
            request.archivo_id,
            request.modelo_base,
            request.epochs,
            request.learning_rate,
        )

        # Guardar job en BD
        job = FineTuningJob(
            openai_job_id=job_data["id"],
            status=job_data.get("status", "pending"),
            modelo_base=request.modelo_base,
            archivo_entrenamiento=request.archivo_id,
            epochs=request.epochs,
            learning_rate=request.learning_rate,
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        return {"job": job.to_dict()}

    except Exception as e:
        db.rollback()
        logger.error(f"Error iniciando fine-tuning: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error iniciando fine-tuning: {str(e)}")


@router.get("/fine-tuning/jobs")
async def listar_fine_tuning_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar todos los jobs de fine-tuning"""
    try:
        jobs = db.query(FineTuningJob).order_by(FineTuningJob.creado_en.desc()).all()

        # Actualizar estado desde OpenAI
        openai_api_key = _obtener_openai_api_key(db)
        service = AITrainingService(openai_api_key)

        for job in jobs:
            try:
                estado = await service.obtener_estado_job(job.openai_job_id)
                job.status = estado.get("status", job.status)
                job.modelo_entrenado = estado.get("fine_tuned_model")
                job.progreso = (
                    estado.get("trained_tokens", 0) / estado.get("training_file_tokens", 1) * 100
                    if estado.get("training_file_tokens")
                    else None
                )

                if estado.get("status") in ["succeeded", "failed", "cancelled"]:
                    job.completado_en = datetime.utcnow()

                if estado.get("error"):
                    # Formatear error de forma legible
                    error_data = estado["error"]
                    if isinstance(error_data, dict):
                        # Si es un diccionario, extraer información clave
                        error_msg = error_data.get("message", str(error_data))
                        if error_data.get("code"):
                            error_msg = f"[{error_data.get('code')}] {error_msg}"
                        if error_data.get("param"):
                            error_msg += f" (param: {error_data.get('param')})"
                        job.error = error_msg
                    else:
                        job.error = str(error_data)
                    logger.warning(f"Job {job.openai_job_id} falló: {job.error}")

                db.commit()
            except Exception as e:
                logger.warning(f"Error actualizando estado del job {job.openai_job_id}: {e}")

        return {"jobs": [job.to_dict() for job in jobs]}

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_database_error(e, "listando jobs")


@router.get("/fine-tuning/jobs/{job_id}")
async def obtener_estado_fine_tuning(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener estado de un job de fine-tuning"""
    try:
        job = db.query(FineTuningJob).filter(FineTuningJob.openai_job_id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job no encontrado")

        # Actualizar desde OpenAI
        openai_api_key = _obtener_openai_api_key(db)
        service = AITrainingService(openai_api_key)
        estado = await service.obtener_estado_job(job_id)

        job.status = estado.get("status", job.status)
        job.modelo_entrenado = estado.get("fine_tuned_model")
        job.progreso = (
            estado.get("trained_tokens", 0) / estado.get("training_file_tokens", 1) * 100
            if estado.get("training_file_tokens")
            else None
        )

        if estado.get("status") in ["succeeded", "failed", "cancelled"]:
            job.completado_en = datetime.utcnow()

        if estado.get("error"):
            # Formatear error de forma legible
            error_data = estado["error"]
            if isinstance(error_data, dict):
                # Si es un diccionario, extraer información clave
                error_msg = error_data.get("message", str(error_data))
                if error_data.get("code"):
                    error_msg = f"[{error_data.get('code')}] {error_msg}"
                if error_data.get("param"):
                    error_msg += f" (param: {error_data.get('param')})"
                job.error = error_msg
            else:
                job.error = str(error_data)
            logger.warning(f"Job {job_id} falló: {job.error}")

        db.commit()
        db.refresh(job)

        return {"job": job.to_dict()}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error obteniendo estado del job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado: {str(e)}")


@router.post("/fine-tuning/jobs/{job_id}/cancelar")
async def cancelar_fine_tuning_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancelar un job de fine-tuning"""
    try:
        # Buscar job en BD
        job = db.query(FineTuningJob).filter(FineTuningJob.openai_job_id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job no encontrado")

        # Verificar que el job puede ser cancelado
        if job.status in ["succeeded", "failed", "cancelled"]:
            raise HTTPException(status_code=400, detail=f"No se puede cancelar un job con estado '{job.status}'")

        # Cancelar en OpenAI
        openai_api_key = _obtener_openai_api_key(db)
        service = AITrainingService(openai_api_key)
        job_data = await service.cancelar_job(job_id)

        # Actualizar estado en BD
        job.status = job_data.get("status", "cancelled")
        if job.status == "cancelled":
            job.completado_en = datetime.utcnow()

        db.commit()
        db.refresh(job)

        logger.info(f"Job {job_id} cancelado por usuario {current_user.id}")

        return {"job": job.to_dict(), "mensaje": "Job cancelado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error cancelando job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error cancelando job: {str(e)}")


@router.delete("/fine-tuning/jobs/{job_id}")
async def eliminar_fine_tuning_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar un job de fine-tuning"""
    try:
        # Buscar job en BD
        job = db.query(FineTuningJob).filter(FineTuningJob.openai_job_id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job no encontrado")

        # No permitir eliminar jobs en ejecución
        if job.status in ["pending", "running"]:
            raise HTTPException(
                status_code=400, detail=f"No se puede eliminar un job con estado '{job.status}'. Cancélalo primero."
            )

        # Eliminar de la BD
        db.delete(job)
        db.commit()

        logger.info(f"Job {job_id} eliminado por usuario {current_user.id}")

        return {"mensaje": "Job eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error eliminando job: {str(e)}")


@router.delete("/fine-tuning/jobs")
async def eliminar_todos_fine_tuning_jobs(
    solo_fallidos: bool = Query(False, description="Eliminar solo jobs fallidos"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminar todos los jobs de fine-tuning (o solo los fallidos)"""
    try:
        # Construir query
        query = db.query(FineTuningJob)

        if solo_fallidos:
            # Solo eliminar jobs fallidos o cancelados
            query = query.filter(FineTuningJob.status.in_(["failed", "cancelled"]))
        else:
            # Eliminar todos excepto los que están en ejecución
            query = query.filter(~FineTuningJob.status.in_(["pending", "running"]))

        jobs = query.all()

        if not jobs:
            return {"mensaje": "No hay jobs para eliminar", "eliminados": 0}

        # Contar jobs que se eliminarán
        total_eliminados = len(jobs)

        # Eliminar jobs
        for job in jobs:
            db.delete(job)

        db.commit()

        logger.info(f"{total_eliminados} jobs eliminados por usuario {current_user.id}")

        return {"mensaje": f"{total_eliminados} job(s) eliminado(s) exitosamente", "eliminados": total_eliminados}

    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error eliminando jobs: {str(e)}")


@router.post("/fine-tuning/activar")
async def activar_modelo_fine_tuned(
    request: ActivarModeloRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activar modelo fine-tuned"""
    try:
        # Verificar que el modelo existe y está disponible
        job = db.query(FineTuningJob).filter(FineTuningJob.modelo_entrenado == request.modelo_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Modelo fine-tuned no encontrado: {request.modelo_id}")

        if job.status != "succeeded":
            raise HTTPException(
                status_code=400,
                detail=f"El modelo no está listo para usar. Estado actual: {job.status}. Solo se pueden activar modelos con estado 'succeeded'.",
            )

        # Guardar modelo activo en configuración
        from app.models.configuracion_sistema import ConfiguracionSistema

        # Guardar en modelo_fine_tuned (para referencia)
        config_fine_tuned = (
            db.query(ConfiguracionSistema)
            .filter(
                and_(
                    ConfiguracionSistema.categoria == "AI",
                    ConfiguracionSistema.clave == "modelo_fine_tuned",
                )
            )
            .first()
        )

        if config_fine_tuned:
            config_fine_tuned.valor = request.modelo_id
        else:
            config_fine_tuned = ConfiguracionSistema(
                categoria="AI",
                clave="modelo_fine_tuned",
                valor=request.modelo_id,
                tipo_dato="string",
            )
            db.add(config_fine_tuned)

        # ✅ CRÍTICO: Actualizar también la clave "modelo" para que el servicio de chat lo use
        # Esto asegura que el modelo fine-tuned se use realmente en las llamadas a la API
        config_modelo = (
            db.query(ConfiguracionSistema)
            .filter(
                and_(
                    ConfiguracionSistema.categoria == "AI",
                    ConfiguracionSistema.clave == "modelo",
                )
            )
            .first()
        )

        if config_modelo:
            # Guardar el modelo base original si no existe
            if not config_modelo.valor or config_modelo.valor == "gpt-3.5-turbo":
                # Guardar el modelo base del job como respaldo
                config_modelo.valor = job.modelo_base or "gpt-4o-2024-08-06"
            # Actualizar a modelo fine-tuned
            modelo_anterior = config_modelo.valor
            config_modelo.valor = request.modelo_id
            logger.info(f"✅ Modelo actualizado de '{modelo_anterior}' a '{request.modelo_id}'")
        else:
            # Si no existe configuración de modelo, crear una con el fine-tuned
            config_modelo = ConfiguracionSistema(
                categoria="AI",
                clave="modelo",
                valor=request.modelo_id,
                tipo_dato="string",
            )
            db.add(config_modelo)
            logger.info(f"✅ Configuración de modelo creada con fine-tuned: {request.modelo_id}")

        db.commit()

        logger.info(f"✅ Modelo fine-tuned activado exitosamente: {request.modelo_id}")
        logger.info(f"   Modelo base original: {job.modelo_base}")
        logger.info("   El modelo se usará en todas las llamadas al Chat AI")

        return {
            "mensaje": "Modelo activado exitosamente",
            "modelo_activo": request.modelo_id,
            "modelo_base": job.modelo_base,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error activando modelo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error activando modelo: {str(e)}")


# ============================================
# RAG ENDPOINTS
# ============================================


@router.get("/rag/estado")
async def obtener_estado_embeddings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener estado de embeddings"""
    try:
        total_documentos = db.query(DocumentoAI).count()
        documentos_con_embeddings = db.query(DocumentoEmbedding.documento_id).distinct().count()
        total_embeddings = db.query(DocumentoEmbedding).count()

        ultima_actualizacion = db.query(func.max(DocumentoEmbedding.creado_en)).scalar()

        return {
            "total_documentos": total_documentos,
            "documentos_con_embeddings": documentos_con_embeddings,
            "total_embeddings": total_embeddings,
            "ultima_actualizacion": ultima_actualizacion.isoformat() if ultima_actualizacion else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_database_error(e, "obteniendo estado de embeddings")


@router.post("/rag/generar-embeddings")
async def generar_embeddings(
    request: GenerarEmbeddingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generar embeddings para documentos"""
    try:
        openai_api_key = _obtener_openai_api_key(db)
        service = RAGService(openai_api_key)

        # Obtener documentos
        if request.documento_ids:
            documentos = (
                db.query(DocumentoAI)
                .filter(
                    and_(
                        DocumentoAI.id.in_(request.documento_ids),
                        DocumentoAI.contenido_procesado.is_(True),
                    )
                )
                .all()
            )
        else:
            documentos = db.query(DocumentoAI).filter(DocumentoAI.contenido_procesado.is_(True)).all()

        documentos_procesados = 0
        total_embeddings = 0

        for documento in documentos:
            if not documento.contenido_texto:
                continue

            # Dividir en chunks
            chunks = service.dividir_texto_en_chunks(documento.contenido_texto)

            # Generar embeddings para cada chunk
            textos = [chunk for chunk in chunks if chunk.strip()]
            if not textos:
                continue

            embeddings = await service.generar_embeddings_batch(textos)

            # Eliminar embeddings existentes del documento
            db.query(DocumentoEmbedding).filter(DocumentoEmbedding.documento_id == documento.id).delete()

            # Guardar nuevos embeddings
            for idx, (texto, embedding) in enumerate(zip(textos, embeddings)):
                embedding_obj = DocumentoEmbedding(
                    documento_id=documento.id,
                    embedding=embedding,
                    chunk_index=idx,
                    texto_chunk=texto,
                    modelo_embedding=service.embedding_model,
                    dimensiones=service.embedding_dimension,
                )
                db.add(embedding_obj)
                total_embeddings += 1

            documentos_procesados += 1

        db.commit()

        return {
            "documentos_procesados": documentos_procesados,
            "total_embeddings": total_embeddings,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error generando embeddings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generando embeddings: {str(e)}")


@router.post("/rag/buscar")
async def buscar_documentos_relevantes(
    request: BuscarDocumentosRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Buscar documentos relevantes usando embeddings"""
    try:
        openai_api_key = _obtener_openai_api_key(db)
        service = RAGService(openai_api_key)

        # Generar embedding de la pregunta
        query_embedding = await service.generar_embedding(request.pregunta)

        # Obtener todos los embeddings
        embeddings_db = db.query(DocumentoEmbedding).all()

        documento_embeddings = [
            {
                "documento_id": emb.documento_id,
                "chunk_index": emb.chunk_index,
                "texto_chunk": emb.texto_chunk,
                "embedding": emb.embedding,
            }
            for emb in embeddings_db
        ]

        # Buscar documentos relevantes
        resultados = service.buscar_documentos_relevantes(query_embedding, documento_embeddings, top_k=request.top_k)

        return {
            "documentos": resultados,
            "query_embedding": query_embedding,  # Opcional, para debugging
        }

    except Exception as e:
        logger.error(f"Error buscando documentos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error buscando documentos: {str(e)}")


@router.post("/rag/documentos/{documento_id}/embeddings")
async def actualizar_embeddings_documento(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar embeddings de un documento específico"""
    try:
        documento = db.query(DocumentoAI).filter(DocumentoAI.id == documento_id).first()

        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        if not documento.contenido_procesado or not documento.contenido_texto:
            raise HTTPException(status_code=400, detail="Documento no procesado o sin contenido")

        openai_api_key = _obtener_openai_api_key(db)
        service = RAGService(openai_api_key)

        # Dividir en chunks
        chunks = service.dividir_texto_en_chunks(documento.contenido_texto)
        textos = [chunk for chunk in chunks if chunk.strip()]

        if not textos:
            return {"embeddings_generados": 0}

        # Generar embeddings
        embeddings = await service.generar_embeddings_batch(textos)

        # Eliminar embeddings existentes
        db.query(DocumentoEmbedding).filter(DocumentoEmbedding.documento_id == documento_id).delete()

        # Guardar nuevos embeddings
        for idx, (texto, embedding) in enumerate(zip(textos, embeddings)):
            embedding_obj = DocumentoEmbedding(
                documento_id=documento_id,
                embedding=embedding,
                chunk_index=idx,
                texto_chunk=texto,
                modelo_embedding=service.embedding_model,
                dimensiones=service.embedding_dimension,
            )
            db.add(embedding_obj)

        db.commit()

        return {"embeddings_generados": len(embeddings)}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando embeddings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error actualizando embeddings: {str(e)}")


# ============================================
# MÉTRICAS CONSOLIDADAS
# ============================================


@router.get("/verificar-bd")
async def verificar_conexion_bd_modelos_ml(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verificar si las tablas de modelos ML están conectadas a la base de datos"""
    try:
        from sqlalchemy import inspect, text

        inspector = inspect(db.bind)
        tablas_existentes = inspector.get_table_names()

        tablas_requeridas = {}

        resultado = {
            "conexion_bd": True,
            "tablas": {},
            "todas_existen": True,
        }

        for tabla, nombre in tablas_requeridas.items():
            existe = tabla in tablas_existentes
            resultado["tablas"][tabla] = {
                "existe": existe,
                "nombre": nombre,
                "columnas": [],
                "indices": [],
                "total_registros": 0,
            }

            if existe:
                try:
                    # Obtener información de columnas
                    columnas = inspector.get_columns(tabla)
                    resultado["tablas"][tabla]["columnas"] = [
                        {
                            "nombre": col["name"],
                            "tipo": str(col["type"]),
                            "nullable": col["nullable"],
                        }
                        for col in columnas
                    ]

                    # Obtener índices
                    indices = inspector.get_indexes(tabla)
                    resultado["tablas"][tabla]["indices"] = [
                        {
                            "nombre": idx["name"],
                            "columnas": idx["column_names"],
                            "unique": idx.get("unique", False),
                        }
                        for idx in indices
                    ]

                    # Contar registros
                    count_result = db.execute(text(f"SELECT COUNT(*) FROM {tabla}"))
                    resultado["tablas"][tabla]["total_registros"] = count_result.scalar() or 0
                except Exception as e:
                    resultado["tablas"][tabla]["error"] = str(e)
            else:
                resultado["todas_existen"] = False

        return resultado

    except Exception as e:
        logger.error(f"Error verificando conexión BD modelos ML: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error verificando conexión a base de datos: {str(e)}")


@router.get("/metricas")
async def obtener_metricas_entrenamiento(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener métricas consolidadas de todos los sistemas de entrenamiento"""
    try:
        # Métricas de conversaciones
        total_conversaciones = db.query(ConversacionAI).count()
        conversaciones_calificadas = db.query(ConversacionAI).filter(ConversacionAI.calificacion.isnot(None)).count()
        promedio_calificacion = (
            db.query(func.avg(ConversacionAI.calificacion)).filter(ConversacionAI.calificacion.isnot(None)).scalar()
        ) or 0
        conversaciones_listas = (
            db.query(ConversacionAI)
            .filter(
                and_(
                    ConversacionAI.calificacion.isnot(None),
                    ConversacionAI.calificacion >= 4,
                )
            )
            .count()
        )

        # Métricas de fine-tuning
        jobs_totales = db.query(FineTuningJob).count()
        jobs_exitosos = db.query(FineTuningJob).filter(FineTuningJob.status == "succeeded").count()
        jobs_fallidos = db.query(FineTuningJob).filter(FineTuningJob.status == "failed").count()
        ultimo_job = db.query(FineTuningJob).order_by(FineTuningJob.creado_en.desc()).first()
        modelo_activo_ft = None
        if ultimo_job and ultimo_job.status == "succeeded":
            from app.models.configuracion_sistema import ConfiguracionSistema

            config = (
                db.query(ConfiguracionSistema)
                .filter(
                    and_(
                        ConfiguracionSistema.categoria == "AI",
                        ConfiguracionSistema.clave == "modelo_fine_tuned",
                    )
                )
                .first()
            )
            modelo_activo_ft = config.valor if config else None

        # Métricas de RAG
        documentos_con_embeddings = db.query(DocumentoEmbedding.documento_id).distinct().count()
        total_embeddings = db.query(DocumentoEmbedding).count()
        ultima_actualizacion_rag = db.query(func.max(DocumentoEmbedding.creado_en)).scalar()

        return {
            "conversaciones": {
                "total": total_conversaciones,
                "con_calificacion": conversaciones_calificadas,
                "promedio_calificacion": float(promedio_calificacion),
                "listas_entrenamiento": conversaciones_listas,
            },
            "fine_tuning": {
                "jobs_totales": jobs_totales,
                "jobs_exitosos": jobs_exitosos,
                "jobs_fallidos": jobs_fallidos,
                "modelo_activo": modelo_activo_ft,
                "ultimo_entrenamiento": (ultimo_job.creado_en.isoformat() if ultimo_job else None),
            },
            "rag": {
                "documentos_con_embeddings": documentos_con_embeddings,
                "total_embeddings": total_embeddings,
                "ultima_actualizacion": (ultima_actualizacion_rag.isoformat() if ultima_actualizacion_rag else None),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_database_error(e, "obteniendo métricas")


@router.post("/recolectar-automatico")
async def recolectar_conversaciones_automatico(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recolecta automáticamente conversaciones del Chat AI que aún no han sido guardadas.
    Busca en logs o en una tabla temporal si existe.
    """
    try:
        # Por ahora, simplemente retornamos las conversaciones existentes
        # En el futuro, esto podría buscar en logs o una tabla temporal
        total_existentes = db.query(ConversacionAI).count()
        
        # Simular recolección de nuevas conversaciones (esto debería implementarse según tu arquitectura)
        # Por ejemplo, buscar conversaciones del endpoint /ai/chat que no se guardaron
        
        logger.info(f"Recolección automática: {total_existentes} conversaciones existentes")
        
        return {
            "total_recolectadas": 0,  # Por ahora retornamos 0, pero esto debería implementarse
            "total_existentes": total_existentes,
            "mensaje": "Recolección completada. Las conversaciones del Chat AI se guardan automáticamente.",
        }
    except Exception as e:
        logger.error(f"Error en recolección automática: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error en recolección automática: {str(e)}")


@router.post("/analizar-calidad")
async def analizar_calidad_datos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analiza la calidad de las conversaciones para entrenamiento.
    Retorna métricas de completitud, consistencia, relevancia y sugerencias.
    """
    try:
        conversaciones = db.query(ConversacionAI).all()
        
        if not conversaciones:
            return {
                "completitud": 0,
                "consistencia": 0,
                "relevancia": 0,
                "calidad_general": 0,
                "sugerencias": ["No hay conversaciones para analizar. Recolecta conversaciones primero."],
            }
        
        total = len(conversaciones)
        
        # Completitud: conversaciones con pregunta y respuesta completas
        completas = sum(
            1
            for c in conversaciones
            if c.pregunta and c.respuesta and len(c.pregunta.strip()) > 10 and len(c.respuesta.strip()) > 20
        )
        completitud = (completas / total) * 100 if total > 0 else 0
        
        # Consistencia: conversaciones con calificación y feedback
        con_calificacion = sum(1 for c in conversaciones if c.calificacion is not None)
        consistencia = (con_calificacion / total) * 100 if total > 0 else 0
        
        # Relevancia: conversaciones con 4+ estrellas
        relevantes = sum(1 for c in conversaciones if c.calificacion and c.calificacion >= 4)
        relevancia = (relevantes / total) * 100 if total > 0 else 0
        
        # Calidad general: promedio ponderado
        calidad_general = (completitud * 0.4 + consistencia * 0.3 + relevancia * 0.3)
        
        # Sugerencias
        sugerencias = []
        if completitud < 80:
            sugerencias.append(f"Completitud baja ({completitud:.1f}%): Asegúrate de que todas las conversaciones tengan pregunta y respuesta completas.")
        if consistencia < 50:
            sugerencias.append(f"Consistencia baja ({consistencia:.1f}%): Califica más conversaciones para mejorar la calidad del dataset.")
        if relevancia < 30:
            sugerencias.append(f"Relevancia baja ({relevancia:.1f}%): Necesitas más conversaciones con calificación alta (4-5 estrellas) para entrenar.")
        if calidad_general < 60:
            sugerencias.append("Calidad general baja: Revisa y mejora las conversaciones antes de entrenar.")
        if total < 10:
            sugerencias.append(f"Solo tienes {total} conversaciones. Se recomiendan al menos 10 para entrenar (ideal: 50+).")
        
        if not sugerencias:
            sugerencias.append("✅ La calidad de tus datos es buena. Puedes proceder con el entrenamiento.")
        
        return {
            "completitud": round(completitud, 1),
            "consistencia": round(consistencia, 1),
            "relevancia": round(relevancia, 1),
            "calidad_general": round(calidad_general, 1),
            "total_conversaciones": total,
            "conversaciones_completas": completas,
            "conversaciones_calificadas": con_calificacion,
            "conversaciones_relevantes": relevantes,
            "sugerencias": sugerencias,
        }
    except Exception as e:
        logger.error(f"Error analizando calidad: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error analizando calidad: {str(e)}")


def _validar_tabla_modelos_impago(db: Session) -> None:
    """Valida que la tabla modelos_impago_cuotas exista"""
    try:
        db.query(ModeloImpagoCuotas).limit(1).all()
    except (ProgrammingError, OperationalError) as db_error:
        error_msg = str(db_error).lower()
        if any(term in error_msg for term in ["does not exist", "no such table", "relation", "table"]):
            raise HTTPException(
                status_code=503,
                detail="La tabla 'modelos_impago_cuotas' no está creada. Ejecuta las migraciones: alembic upgrade head",
            )
        raise


def _verificar_conexion_bd(db: Session) -> None:
    """Verifica la conexión a la base de datos"""
    try:
        logger.info("🔍 Verificando conexión a la base de datos...")
        db.execute(text("SELECT 1"))
        logger.info("✅ Conexión a la base de datos verificada")
    except Exception as db_conn_error:
        logger.error(f"❌ Error de conexión a la base de datos: {db_conn_error}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Error de conexión a la base de datos: {str(db_conn_error)[:200]}",
        )


def _obtener_prestamos_aprobados_impago(db: Session) -> list:
    """
    Obtiene préstamos aprobados con manejo de errores de columnas.
    Retorna lista de préstamos.
    """
    from app.models.prestamo import Prestamo

    prestamos_query = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").filter(Prestamo.fecha_aprobacion.isnot(None))

    try:
        return prestamos_query.all()
    except Exception as e:
        error_msg = str(e).lower()
        # Hacer rollback si la transacción está abortada
        if "aborted" in error_msg or "InFailedSqlTransaction" in str(e):
            logger.warning("⚠️ [ML-IMPAGO] Transacción abortada detectada, haciendo rollback antes de reintentar")
            try:
                db.rollback()
            except Exception:
                pass

        if (
            "valor_activo" in error_msg
            or "does not exist" in error_msg
            or "aborted" in error_msg
            or "InFailedSqlTransaction" in str(e)
        ):
            logger.warning("⚠️ [ML-IMPAGO] Error en query inicial, haciendo rollback y usando query directo")
            # Asegurar rollback antes de continuar
            try:
                db.rollback()
            except Exception:
                pass

            from sqlalchemy import select

            stmt = (
                select(
                    Prestamo.id,
                    Prestamo.cliente_id,
                    Prestamo.cedula,
                    Prestamo.nombres,
                    Prestamo.total_financiamiento,
                    Prestamo.estado,
                    Prestamo.fecha_aprobacion,
                )
                .where(Prestamo.estado == "APROBADO")
                .where(Prestamo.fecha_aprobacion.isnot(None))
            )

            resultados = db.execute(stmt).all()
            prestamos = []
            for row in resultados:
                prestamo = Prestamo()
                prestamo.id = row.id
                prestamo.cliente_id = row.cliente_id
                prestamo.cedula = row.cedula
                prestamo.nombres = row.nombres
                prestamo.total_financiamiento = row.total_financiamiento
                prestamo.estado = row.estado
                prestamo.fecha_aprobacion = row.fecha_aprobacion
                prestamos.append(prestamo)
            return prestamos
        raise
    """Obtiene cuotas de un préstamo con manejo de errores"""
    from app.models.amortizacion import Cuota

    try:
        return db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id).order_by(Cuota.numero_cuota).all()
    except Exception as cuota_query_error:
        logger.warning(f"Error consultando cuotas del préstamo {prestamo_id}: {cuota_query_error}")
        return []


def _extraer_features_prestamo_impago(cuotas: list, prestamo, fecha_actual, ml_service) -> Optional[Dict]:
    """
    Extrae features de un préstamo para entrenamiento de impago.
    Retorna dict con features o None si hay error.
    """
    try:
        features = ml_service.extract_payment_features(cuotas, prestamo, fecha_actual)
        if not features or len(features) == 0:
            logger.warning(f"Features vacías para préstamo {prestamo.id}, omitiendo...")
            return None
        return features
    except Exception as e:
        logger.warning(f"Error extrayendo features del préstamo {prestamo.id}: {e}, omitiendo...", exc_info=True)
        return None


def _calcular_target_impago(cuotas: list, fecha_actual) -> Optional[int]:
    """
    Calcula el target (impago) basado en cuotas vencidas.
    Retorna 0 (pagó) o 1 (no pagó), o None si no hay cuotas vencidas.
    """
    try:
        cuotas_vencidas = [c for c in cuotas if c.fecha_vencimiento and c.fecha_vencimiento < fecha_actual]
        if not cuotas_vencidas:
            return None  # No hay cuotas vencidas aún, no podemos determinar target

        # Target: 0 = Pagó (todas las cuotas vencidas están pagadas), 1 = No pagó (hay cuotas vencidas sin pagar)
        cuotas_vencidas_sin_pagar = sum(1 for c in cuotas_vencidas if c.estado and c.estado not in ["PAGADO", "PARCIAL"])
        return 1 if cuotas_vencidas_sin_pagar > 0 else 0
    except Exception as e:
        logger.warning(f"Error determinando target: {e}, omitiendo...", exc_info=True)
        return None


def _procesar_prestamos_para_entrenamiento(prestamos: list, ml_service, fecha_actual, db: Session) -> list:
    """
    Procesa préstamos para generar datos de entrenamiento.
    Retorna lista de training_data.
    """
    from app.models.amortizacion import Cuota

    training_data = []
    prestamos_procesados = 0
    prestamos_con_cuotas = 0
    prestamos_con_features = 0

    logger.info(f"🔄 Procesando {len(prestamos)} préstamos para generar datos de entrenamiento...")

    for prestamo in prestamos:
        prestamos_procesados += 1
        try:
            # Obtener cuotas del préstamo
            cuotas = _obtener_cuotas_prestamo(prestamo.id, db)
            if not cuotas or len(cuotas) < 2:
                if prestamos_procesados % 10 == 0:
                    logger.debug(f"Préstamo {prestamo.id}: {len(cuotas) if cuotas else 0} cuotas (necesita mínimo 2)")
                continue

            prestamos_con_cuotas += 1

            # Extraer features
            features = _extraer_features_prestamo_impago(cuotas, prestamo, fecha_actual, ml_service)
            if not features:
                continue

            # Calcular target
            target = _calcular_target_impago(cuotas, fecha_actual)
            if target is None:
                continue

            # Agregar a datos de entrenamiento
            training_data.append({**features, "target": target})
            prestamos_con_features += 1

            if prestamos_con_features % 5 == 0:
                logger.info(f"✅ Generadas {prestamos_con_features} muestras de entrenamiento...")

        except Exception as e:
            logger.warning(f"Error procesando préstamo {prestamo.id}: {e}, omitiendo...", exc_info=True)
            continue

    logger.info(
        f"📊 Resumen de procesamiento:\n"
        f"   - Préstamos procesados: {prestamos_procesados}/{len(prestamos)}\n"
        f"   - Préstamos con cuotas (≥2): {prestamos_con_cuotas}\n"
        f"   - Préstamos con features válidas: {prestamos_con_features}\n"
        f"   - Muestras de entrenamiento generadas: {len(training_data)}"
    )

    return training_data


def _guardar_modelo_impago(
    resultado: Dict, request: EntrenarModeloImpagoRequest, current_user: User, db: Session
) -> ModeloImpagoCuotas:
    """Guarda el modelo entrenado en la base de datos"""
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    modelo = ModeloImpagoCuotas(
        nombre=f"Modelo Impago Cuotas {timestamp}",
        version="1.0.0",
        algoritmo=request.algoritmo,
        accuracy=resultado["metrics"]["accuracy"],
        precision=resultado["metrics"]["precision"],
        recall=resultado["metrics"]["recall"],
        f1_score=resultado["metrics"]["f1_score"],
        roc_auc=resultado["metrics"]["roc_auc"],
        ruta_archivo=resultado["model_path"],
        total_datos_entrenamiento=resultado["training_samples"],
        total_datos_test=resultado["test_samples"],
        test_size=request.test_size,
        random_state=request.random_state,
        activo=False,
        usuario_id=current_user.id,
        descripcion=f"Modelo entrenado para predecir impago de cuotas usando {request.algoritmo}",
        features_usadas=",".join(resultado["features"]),
    )

    db.add(modelo)
    db.commit()
    db.refresh(modelo)
    return modelo


def _manejar_error_entrenamiento_impago(e: Exception, db: Session) -> HTTPException:
    """Maneja errores durante el entrenamiento y retorna HTTPException apropiado"""
    db.rollback()
    error_msg = str(e)
    error_type = type(e).__name__
    import traceback

    error_traceback = traceback.format_exc()

    logger.error(
        f"❌ [ML-IMPAGO] Error entrenando modelo de impago: {error_type}: {error_msg}\n"
        f"Traceback completo:\n{error_traceback}",
        exc_info=True,
    )

    # Mensaje más descriptivo según el tipo de error
    if "scikit-learn" in error_msg.lower() or "sklearn" in error_msg.lower() or "SKLEARN" in error_msg:
        detail_msg = "Error con scikit-learn. Verifica que esté instalado correctamente."
    elif "stratify" in error_msg.lower():
        detail_msg = "Error al dividir datos. Puede ser por pocas muestras de alguna clase."
    elif "cuota" in error_msg.lower() or "fecha_vencimiento" in error_msg.lower() or "Cuota" in error_msg:
        detail_msg = "Error accediendo a datos de cuotas. Verifica la integridad de los datos."
    elif "does not exist" in error_msg.lower() or "no such table" in error_msg.lower():
        detail_msg = "La tabla de modelos de impago no está creada. Ejecuta las migraciones: alembic upgrade head"
    elif "AttributeError" in error_type or "'NoneType' object has no attribute" in error_msg:
        detail_msg = f"Error de datos: {error_msg[:200]}. Verifica que los préstamos tengan cuotas y datos válidos."
    elif "KeyError" in error_type:
        detail_msg = f"Error de estructura de datos: {error_msg[:200]}. Verifica que las features estén completas."
    elif "ValueError" in error_type:
        detail_msg = f"Error de validación: {error_msg[:200]}"
    elif "TypeError" in error_type:
        detail_msg = f"Error de tipo de dato: {error_msg[:200]}. Verifica que los datos sean numéricos."
    else:
        detail_msg = f"Error entrenando modelo ({error_type}): {error_msg[:300]}"

    return HTTPException(status_code=500, detail=detail_msg)


@router.post("/ml-impago/entrenar")
async def entrenar_modelo_impago(
    request: EntrenarModeloImpagoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Entrenar modelo de predicción de impago de cuotas
    Analiza el historial de pagos de préstamos aprobados para predecir impago futuro
    """
    # Log inmediato al inicio - esto confirma que el endpoint se está ejecutando
    logger.info("=" * 80)
    logger.info("🚀 [ML-IMPAGO] ===== INICIO DE ENTRENAMIENTO =====")
    logger.info(f"   Usuario ID: {current_user.id}")
    logger.info(f"   Usuario es admin: {current_user.is_admin}")
    logger.info(f"   Algoritmo solicitado: {request.algoritmo}")
    logger.info(f"   Test size: {request.test_size}")
    logger.info(f"   Random state: {request.random_state}")
    logger.info("=" * 80)

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden entrenar modelos ML")

    try:
        # Validaciones
        _validar_ml_impago_service_disponible()
        _validar_tabla_modelos_impago(db)
        _verificar_conexion_bd(db)

        # Verificar y limpiar transacción antes de obtener préstamos
        try:
            from sqlalchemy import text

            db.execute(text("SELECT 1"))
        except Exception as test_error:
            error_str = str(test_error)
            if "aborted" in error_str.lower() or "InFailedSqlTransaction" in error_str:
                logger.warning("⚠️ [ML-IMPAGO] Transacción abortada detectada al inicio, haciendo rollback preventivo")
                try:
                    db.rollback()
                except Exception:
                    pass

        # Obtener préstamos
        logger.info("🔍 Buscando préstamos aprobados para entrenamiento...")
        prestamos = _obtener_prestamos_aprobados_impago(db)
        logger.info(f"📊 Encontrados {len(prestamos)} préstamos aprobados")

        if not prestamos:
            raise HTTPException(status_code=400, detail="No hay préstamos aprobados para entrenar el modelo")

        # Procesar préstamos para generar datos de entrenamiento
        from datetime import date

        ml_service = MLImpagoCuotasService()
        fecha_actual = date.today()
        logger.info(f"📅 Fecha actual para cálculo de features: {fecha_actual}")

        training_data = _procesar_prestamos_para_entrenamiento(prestamos, ml_service, fecha_actual, db)

        if len(training_data) < 10:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Se necesitan al menos 10 muestras válidas para entrenar. "
                    f"Se generaron {len(training_data)} muestras. "
                    f"Posibles causas: préstamos sin cuotas suficientes, sin cuotas vencidas, o errores al extraer features."
                ),
            )

        logger.info(f"📊 Iniciando entrenamiento con {len(training_data)} muestras, algoritmo: {request.algoritmo}")

        # Entrenar modelo
        try:
            resultado = ml_service.train_impago_model(
                training_data,
                algoritmo=request.algoritmo,
                test_size=request.test_size,
                random_state=request.random_state,
            )
        except Exception as train_error:
            error_msg = str(train_error)
            error_type = type(train_error).__name__
            logger.error(f"Error durante train_impago_model: {error_type}: {error_msg}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error durante entrenamiento del modelo ({error_type}): {error_msg[:200]}",
            )

        if not resultado.get("success"):
            error_msg = resultado.get("error", "Error desconocido entrenando modelo")
            logger.error(f"train_impago_model retornó success=False: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Error entrenando modelo: {error_msg}")

        # Guardar modelo en BD
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        modelo = ModeloImpagoCuotas(
            nombre=f"Modelo Impago Cuotas {timestamp}",
            version="1.0.0",
            algoritmo=request.algoritmo,
            accuracy=resultado["metrics"]["accuracy"],
            precision=resultado["metrics"]["precision"],
            recall=resultado["metrics"]["recall"],
            f1_score=resultado["metrics"]["f1_score"],
            roc_auc=resultado["metrics"]["roc_auc"],
            ruta_archivo=resultado["model_path"],
            total_datos_entrenamiento=resultado["training_samples"],
            total_datos_test=resultado["test_samples"],
            test_size=request.test_size,
            random_state=request.random_state,
            activo=False,
            usuario_id=current_user.id,
            descripcion=f"Modelo entrenado para predecir impago de cuotas usando {request.algoritmo}",
            features_usadas=",".join(resultado["features"]),
        )

        db.add(modelo)
        db.commit()
        db.refresh(modelo)

        logger.info(f"✅ Modelo de impago entrenado: {modelo.nombre} (ID: {modelo.id})")

        return {
            "mensaje": "Modelo entrenado exitosamente",
            "modelo": modelo.to_dict(),
            "metricas": resultado["metrics"],
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        error_type = type(e).__name__
        import traceback

        error_traceback = traceback.format_exc()
        logger.error(
            f"❌ [ML-IMPAGO] Error entrenando modelo de impago: {error_type}: {error_msg}\n"
            f"Traceback completo:\n{error_traceback}",
            exc_info=True,
        )

        # Mensaje más descriptivo según el tipo de error
        if "scikit-learn" in error_msg.lower() or "sklearn" in error_msg.lower() or "SKLEARN" in error_msg:
            detail_msg = "Error con scikit-learn. Verifica que esté instalado correctamente."
        elif "stratify" in error_msg.lower():
            detail_msg = "Error al dividir datos. Puede ser por pocas muestras de alguna clase."
        elif "cuota" in error_msg.lower() or "fecha_vencimiento" in error_msg.lower() or "Cuota" in error_msg:
            detail_msg = "Error accediendo a datos de cuotas. Verifica la integridad de los datos."
        elif "aborted" in error_msg.lower() or "InFailedSqlTransaction" in error_msg:
            detail_msg = (
                "Error de transacción SQL abortada. Esto puede ocurrir si una consulta anterior falló. Intenta nuevamente."
            )
        elif "does not exist" in error_msg.lower() or "no such table" in error_msg.lower():
            detail_msg = "La tabla de modelos de impago no está creada. Ejecuta las migraciones: alembic upgrade head"
        elif "AttributeError" in error_type or "'NoneType' object has no attribute" in error_msg:
            detail_msg = f"Error de datos: {error_msg[:200]}. Verifica que los préstamos tengan cuotas y datos válidos."
        elif "KeyError" in error_type:
            detail_msg = f"Error de estructura de datos: {error_msg[:200]}. Verifica que las features estén completas."
        elif "ValueError" in error_type:
            detail_msg = f"Error de validación: {error_msg[:200]}"
        elif "TypeError" in error_type:
            detail_msg = f"Error de tipo de dato: {error_msg[:200]}. Verifica que los datos sean numéricos."
        else:
            # Incluir más información del error para debugging
            detail_msg = f"Error entrenando modelo ({error_type}): {error_msg[:300]}"

        raise HTTPException(status_code=500, detail=detail_msg)


@router.post("/ml-impago/corregir-activos")
async def corregir_modelos_activos_impago(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint para corregir si hay múltiples modelos activos.
    Desactiva todos excepto el más reciente.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden corregir modelos ML")

    try:
        # Contar modelos activos
        modelos_activos = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).all()
        total_activos = len(modelos_activos)

        if total_activos == 0:
            return {
                "mensaje": "No hay modelos activos",
                "modelos_corregidos": 0,
            }

        if total_activos == 1:
            return {
                "mensaje": "Ya hay solo un modelo activo. No se requiere corrección.",
                "modelo_activo": modelos_activos[0].to_dict(),
                "modelos_corregidos": 0,
            }

        # Hay múltiples activos, corregir
        logger.warning(f"⚠️ Detectados {total_activos} modelos activos. Corrigiendo...")

        # Encontrar el más reciente (por activado_en, o si es NULL, por entrenado_en)
        modelo_mas_reciente = max(modelos_activos, key=lambda m: m.activado_en if m.activado_en else m.entrenado_en)

        # Desactivar todos
        db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).update(
            {"activo": False}, synchronize_session=False
        )
        db.flush()

        # Activar solo el más reciente
        modelo_mas_reciente.activo = True
        if not modelo_mas_reciente.activado_en:
            modelo_mas_reciente.activado_en = datetime.now()

        db.commit()
        db.refresh(modelo_mas_reciente)

        logger.info(f"✅ Corregido: Solo el modelo {modelo_mas_reciente.id} ({modelo_mas_reciente.nombre}) está activo ahora")

        return {
            "mensaje": f"Corregido: {total_activos - 1} modelo(s) desactivado(s). Solo queda activo el más reciente.",
            "modelo_activo": modelo_mas_reciente.to_dict(),
            "modelos_desactivados": total_activos - 1,
            "modelos_corregidos": total_activos - 1,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error corrigiendo modelos activos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error corrigiendo modelos activos: {str(e)}")


@router.post("/ml-impago/activar")
async def activar_modelo_impago(
    request: ActivarModeloImpagoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activar un modelo de predicción de impago de cuotas"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden activar modelos ML")

    try:
        # Verificar que MLImpagoCuotasService esté disponible
        if not ML_IMPAGO_SERVICE_AVAILABLE or MLImpagoCuotasService is None:
            raise HTTPException(
                status_code=503,
                detail="scikit-learn no está instalado. Instala con: pip install scikit-learn",
            )

        # Desactivar todos los modelos (CORREGIDO: usar sintaxis correcta de SQLAlchemy)
        # Usar synchronize_session=False para evitar problemas con la sesión
        modelos_desactivados = (
            db.query(ModeloImpagoCuotas)
            .filter(ModeloImpagoCuotas.activo.is_(True))
            .update({"activo": False}, synchronize_session=False)
        )
        db.flush()  # Asegurar que el update se ejecute antes de activar el nuevo

        if modelos_desactivados > 0:
            logger.info(f"✅ Desactivados {modelos_desactivados} modelo(s) anterior(es)")

        # Activar el modelo solicitado
        modelo = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.id == request.modelo_id).first()

        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")

        # Intentar cargar modelo en servicio ML antes de activar (pero no fallar si no existe)
        ml_service = MLImpagoCuotasService()
        modelo_cargado = ml_service.load_model_from_path(modelo.ruta_archivo)

        if not modelo_cargado:
            logger.warning(
                f"⚠️ [ML-IMPAGO] No se pudo cargar el archivo del modelo desde {modelo.ruta_archivo}. "
                f"El modelo se activará de todas formas, pero no funcionará hasta que el archivo exista. "
                f"Esto puede ocurrir si el archivo fue eliminado o si el modelo se entrenó en otro entorno."
            )
            # No lanzar error, solo advertir - permitir activar el modelo de todas formas
            # El sistema de cobranza manejará el caso cuando intente usar el modelo

        modelo.activo = True
        modelo.activado_en = datetime.now()
        db.commit()
        db.refresh(modelo)

        # Verificar que solo este modelo esté activo (doble verificación)
        modelos_activos = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).count()
        if modelos_activos > 1:
            logger.error(f"❌ ERROR: Hay {modelos_activos} modelos activos después de activar. Esto no debería ocurrir.")
            # Corregir: desactivar todos excepto el que acabamos de activar
            db.query(ModeloImpagoCuotas).filter(
                ModeloImpagoCuotas.activo.is_(True), ModeloImpagoCuotas.id != modelo.id
            ).update({"activo": False}, synchronize_session=False)
            db.commit()
            logger.warning(f"⚠️ Corregido: Desactivados modelos adicionales. Solo queda activo el modelo {modelo.id}")

        logger.info(f"✅ Modelo de impago activado: {modelo.nombre} (ID: {modelo.id})")
        logger.info(f"   Verificación: {modelos_activos} modelo(s) activo(s) en total")

        return {
            "mensaje": "Modelo activado exitosamente",
            "modelo_activo": modelo.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error activando modelo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error activando modelo: {str(e)}")


@router.get("/ml-impago/calcular-detalle-cedula/{cedula}")
async def calcular_detalle_impago_por_cedula(
    cedula: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calcular y mostrar el detalle completo del cálculo de riesgo ML Impago para un cliente por cédula.
    Si el cliente tiene múltiples préstamos, muestra el cálculo para el préstamo activo más reciente.
    """
    try:
        from app.models.prestamo import Prestamo

        # Buscar préstamos aprobados del cliente
        prestamos = (
            db.query(Prestamo)
            .filter(Prestamo.cedula == cedula, Prestamo.estado == "APROBADO")
            .order_by(Prestamo.fecha_aprobacion.desc())
            .all()
        )

        if not prestamos:
            raise HTTPException(status_code=404, detail=f"No se encontraron préstamos aprobados para la cédula {cedula}")

        # Usar el préstamo más reciente
        prestamo = prestamos[0]

        # Llamar directamente a la función de cálculo
        return await calcular_detalle_impago(prestamo.id, db, current_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculando detalle de impago por cédula: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculando detalle: {str(e)}")


@router.get("/ml-impago/calcular-detalle/{prestamo_id}")
async def calcular_detalle_impago(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calcular y mostrar el detalle completo del cálculo de riesgo ML Impago para un préstamo.
    Incluye todas las features extraídas y cómo se calcula la probabilidad.
    """
    try:
        from datetime import date

        from app.models.amortizacion import Cuota
        from app.models.prestamo import Prestamo

        # Obtener modelo activo
        modelo_activo = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).first()

        if not modelo_activo:
            raise HTTPException(status_code=400, detail="No hay modelo activo")

        # Verificar que MLImpagoCuotasService esté disponible
        if not ML_IMPAGO_SERVICE_AVAILABLE or MLImpagoCuotasService is None:
            raise HTTPException(
                status_code=503,
                detail="scikit-learn no está instalado. Instala con: pip install scikit-learn",
            )

        # Obtener préstamo
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()

        if not prestamo:
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")

        if prestamo.estado != "APROBADO":
            raise HTTPException(status_code=400, detail="El préstamo debe estar aprobado para calcular impago")

        # Obtener cuotas del préstamo
        cuotas = db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).order_by(Cuota.numero_cuota).all()

        if not cuotas:
            raise HTTPException(status_code=400, detail="El préstamo no tiene cuotas generadas")

        # Cargar modelo
        ml_service = MLImpagoCuotasService()
        if not ml_service.load_model_from_path(modelo_activo.ruta_archivo):
            raise HTTPException(status_code=500, detail="Error cargando modelo")

        # Extraer features
        fecha_actual = date.today()
        features = ml_service.extract_payment_features(cuotas, prestamo, fecha_actual)

        # Calcular estadísticas detalladas de cuotas
        cuotas_ordenadas = sorted(cuotas, key=lambda c: c.numero_cuota)
        total_cuotas = len(cuotas_ordenadas)
        cuotas_pagadas = sum(1 for c in cuotas_ordenadas if c.estado and c.estado == "PAGADO")
        cuotas_atrasadas = sum(1 for c in cuotas_ordenadas if c.estado and c.estado == "ATRASADO")
        cuotas_parciales = sum(1 for c in cuotas_ordenadas if c.estado and c.estado == "PARCIAL")
        cuotas_pendientes = sum(1 for c in cuotas_ordenadas if c.estado and c.estado == "PENDIENTE")
        cuotas_vencidas = [c for c in cuotas_ordenadas if c.fecha_vencimiento and c.fecha_vencimiento < fecha_actual]
        cuotas_vencidas_sin_pagar = sum(1 for c in cuotas_vencidas if c.estado and c.estado not in ["PAGADO", "PARCIAL"])

        # Calcular montos
        monto_total_prestamo = float(prestamo.total_financiamiento or 0)
        monto_total_pagado = sum(float(c.total_pagado or 0) for c in cuotas_ordenadas if c.total_pagado is not None)
        monto_total_pendiente = monto_total_prestamo - monto_total_pagado

        # Predecir
        prediccion = ml_service.predict_impago(features)

        # Determinar criterio de clasificación
        probabilidad_impago = prediccion.get("probabilidad_impago", 0.0)
        criterio_clasificacion = ""
        if probabilidad_impago >= 0.7:
            criterio_clasificacion = f"probabilidad_impago >= 0.7 ({probabilidad_impago:.3f} >= 0.7) → Riesgo ALTO"
        elif probabilidad_impago >= 0.4:
            criterio_clasificacion = f"0.4 <= probabilidad_impago < 0.7 ({probabilidad_impago:.3f}) → Riesgo MEDIO"
        else:
            criterio_clasificacion = f"probabilidad_impago < 0.4 ({probabilidad_impago:.3f} < 0.4) → Riesgo BAJO"

        return {
            "prestamo_id": prestamo_id,
            "cedula": prestamo.cedula,
            "nombres": prestamo.nombres,
            "modelo_usado": {
                "id": modelo_activo.id,
                "nombre": modelo_activo.nombre,
                "algoritmo": modelo_activo.algoritmo,
                "accuracy": modelo_activo.accuracy,
            },
            "fecha_calculo": fecha_actual.isoformat(),
            "estadisticas_cuotas": {
                "total_cuotas": total_cuotas,
                "cuotas_pagadas": cuotas_pagadas,
                "cuotas_atrasadas": cuotas_atrasadas,
                "cuotas_parciales": cuotas_parciales,
                "cuotas_pendientes": cuotas_pendientes,
                "cuotas_vencidas": len(cuotas_vencidas),
                "cuotas_vencidas_sin_pagar": cuotas_vencidas_sin_pagar,
            },
            "estadisticas_financieras": {
                "monto_total_prestamo": round(monto_total_prestamo, 2),
                "monto_total_pagado": round(monto_total_pagado, 2),
                "monto_total_pendiente": round(monto_total_pendiente, 2),
                "porcentaje_pagado": round(
                    (monto_total_pagado / monto_total_prestamo * 100) if monto_total_prestamo > 0 else 0, 2
                ),
            },
            "features_extraidas": features,
            "prediccion": {
                "probabilidad_impago": round(probabilidad_impago, 4),
                "probabilidad_impago_porcentaje": round(probabilidad_impago * 100, 2),
                "probabilidad_pago": round(prediccion.get("probabilidad_pago", 0.0), 4),
                "prediccion": prediccion.get("prediccion", "Desconocido"),
                "nivel_riesgo": prediccion.get("nivel_riesgo", "Desconocido"),
                "confidence": round(prediccion.get("confidence", 0.0), 4),
                "recomendacion": prediccion.get("recomendacion", ""),
            },
            "criterio_clasificacion": criterio_clasificacion,
            "umbrales": {
                "alto": "probabilidad_impago >= 0.7 (70% o más)",
                "medio": "0.4 <= probabilidad_impago < 0.7 (40% a 69.9%)",
                "bajo": "probabilidad_impago < 0.4 (menos de 40%)",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculando detalle de impago: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculando detalle: {str(e)}")


@router.post("/ml-impago/predecir")
async def predecir_impago(
    request: PredecirImpagoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Predecir probabilidad de impago de cuotas futuras para un préstamo"""
    try:
        from datetime import date

        from app.models.amortizacion import Cuota
        from app.models.prestamo import Prestamo

        # Obtener modelo activo
        modelo_activo = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).first()

        if not modelo_activo:
            raise HTTPException(status_code=400, detail="No hay modelo activo")

        # Verificar que MLImpagoCuotasService esté disponible
        if not ML_IMPAGO_SERVICE_AVAILABLE or MLImpagoCuotasService is None:
            raise HTTPException(
                status_code=503,
                detail="scikit-learn no está instalado. Instala con: pip install scikit-learn",
            )

        # Obtener préstamo
        prestamo = db.query(Prestamo).filter(Prestamo.id == request.prestamo_id).first()

        if not prestamo:
            raise HTTPException(status_code=404, detail="Préstamo no encontrado")

        if prestamo.estado != "APROBADO":
            raise HTTPException(status_code=400, detail="El préstamo debe estar aprobado para predecir impago")

        # Obtener cuotas del préstamo
        cuotas = db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).order_by(Cuota.numero_cuota).all()

        if not cuotas:
            raise HTTPException(status_code=400, detail="El préstamo no tiene cuotas generadas")

        # Cargar modelo
        ml_service = MLImpagoCuotasService()
        if not ml_service.load_model_from_path(modelo_activo.ruta_archivo):
            raise HTTPException(status_code=500, detail="Error cargando modelo")

        # Extraer features del historial de pagos
        fecha_actual = date.today()
        features = ml_service.extract_payment_features(cuotas, prestamo, fecha_actual)

        # Predecir
        prediccion = ml_service.predict_impago(features)

        return {
            "prestamo_id": prestamo.id,
            "probabilidad_impago": prediccion["probabilidad_impago"],
            "probabilidad_pago": prediccion["probabilidad_pago"],
            "prediccion": prediccion["prediccion"],
            "nivel_riesgo": prediccion["nivel_riesgo"],
            "confidence": prediccion["confidence"],
            "recomendacion": prediccion["recomendacion"],
            "features_usadas": prediccion["features_usadas"],
            "modelo_usado": {
                "id": modelo_activo.id,
                "nombre": modelo_activo.nombre,
                "version": modelo_activo.version,
                "algoritmo": modelo_activo.algoritmo,
                "accuracy": modelo_activo.accuracy,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error prediciendo impago: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error prediciendo impago: {str(e)}")


@router.delete("/ml-impago/modelos/{modelo_id}")
async def eliminar_modelo_impago(
    modelo_id: int,
    eliminar_archivo: bool = Query(False, description="Eliminar también el archivo .pkl del modelo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Eliminar un modelo de predicción de impago.
    Solo se pueden eliminar modelos INACTIVOS. El modelo activo no se puede eliminar.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar modelos ML")

    try:
        # Buscar el modelo
        modelo = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.id == modelo_id).first()

        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")

        # Verificar que el modelo NO esté activo
        if modelo.activo:
            raise HTTPException(
                status_code=400, detail="No se puede eliminar un modelo activo. Primero desactívalo o activa otro modelo."
            )

        # Guardar información del modelo antes de eliminarlo
        nombre_modelo = modelo.nombre
        ruta_archivo = modelo.ruta_archivo

        # Eliminar el modelo de la base de datos
        db.delete(modelo)
        db.commit()

        logger.info(f"✅ Modelo eliminado: {nombre_modelo} (ID: {modelo_id}) por {current_user.email}")

        # Opcionalmente eliminar el archivo .pkl
        archivo_eliminado = False
        if eliminar_archivo and ruta_archivo:
            try:
                from pathlib import Path

                ruta = Path(ruta_archivo)

                # Buscar el archivo en diferentes ubicaciones
                archivos_a_eliminar = []
                if ruta.is_absolute():
                    if ruta.exists():
                        archivos_a_eliminar.append(ruta)
                else:
                    # Buscar en ubicaciones comunes
                    posibles_rutas = [
                        Path(ruta_archivo),
                        Path("ml_models") / ruta_archivo,
                        Path("ml_models") / Path(ruta_archivo).name,
                    ]
                    try:
                        project_root = Path(__file__).parent.parent.parent.parent
                        posibles_rutas.extend(
                            [
                                project_root / "ml_models" / ruta_archivo,
                                project_root / "ml_models" / Path(ruta_archivo).name,
                            ]
                        )
                    except Exception:
                        pass

                    for posible_ruta in posibles_rutas:
                        if posible_ruta.exists() and posible_ruta.is_file():
                            archivos_a_eliminar.append(posible_ruta)
                            break

                # Eliminar archivos encontrados
                for archivo in archivos_a_eliminar:
                    try:
                        archivo.unlink()
                        logger.info(f"✅ Archivo eliminado: {archivo.absolute()}")
                        archivo_eliminado = True
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo eliminar el archivo {archivo}: {e}")

                # También intentar eliminar el scaler si existe
                if ruta_archivo and "impago_cuotas_model_" in ruta_archivo:
                    timestamp = Path(ruta_archivo).stem.replace("impago_cuotas_model_", "")
                    scaler_path = Path("ml_models") / f"impago_cuotas_scaler_{timestamp}.pkl"
                    if scaler_path.exists():
                        try:
                            scaler_path.unlink()
                            logger.info(f"✅ Scaler eliminado: {scaler_path.absolute()}")
                        except Exception as e:
                            logger.warning(f"⚠️ No se pudo eliminar el scaler {scaler_path}: {e}")

            except Exception as e:
                logger.warning(f"⚠️ Error intentando eliminar archivo del modelo: {e}")

        return {
            "mensaje": f"Modelo '{nombre_modelo}' eliminado exitosamente",
            "modelo_id": modelo_id,
            "archivo_eliminado": archivo_eliminado if eliminar_archivo else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando modelo {modelo_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error eliminando modelo: {str(e)}")


@router.get("/ml-impago/modelos")
async def listar_modelos_impago(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar todos los modelos de predicción de impago"""
    try:
        # Intentar verificar si la tabla existe primero
        try:
            modelos = db.query(ModeloImpagoCuotas).order_by(ModeloImpagoCuotas.entrenado_en.desc()).all()
            modelo_activo = db.query(ModeloImpagoCuotas).filter(ModeloImpagoCuotas.activo.is_(True)).first()

            return {
                "modelos": [modelo.to_dict() for modelo in modelos],
                "modelo_activo": modelo_activo.to_dict() if modelo_activo else None,
                "total": len(modelos),
            }
        except (ProgrammingError, OperationalError) as db_error:
            error_msg = str(db_error).lower()
            logger.error(f"Error de base de datos listando modelos de impago: {db_error}", exc_info=True)

            # Verificar si es un error de tabla no encontrada
            if any(term in error_msg for term in ["does not exist", "no such table", "relation", "table"]):
                # Retornar respuesta vacía en lugar de error 503 para que el frontend pueda manejar
                return {
                    "modelos": [],
                    "modelo_activo": None,
                    "total": 0,
                    "error": "La tabla 'modelos_impago_cuotas' no está creada. Ejecuta las migraciones: alembic upgrade head",
                }
            raise

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error listando modelos de impago: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listando modelos: {error_msg}")
