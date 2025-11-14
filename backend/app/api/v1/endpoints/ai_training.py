"""
Endpoints para entrenamiento de AI
Fine-tuning, RAG, ML Risk
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.conversacion_ai import ConversacionAI
from app.models.documento_ai import DocumentoAI
from app.models.documento_embedding import DocumentoEmbedding
from app.models.fine_tuning_job import FineTuningJob
from app.models.modelo_riesgo import ModeloRiesgo
from app.models.user import User
from app.services.ai_training_service import AITrainingService
from app.services.rag_service import RAGService

# Import condicional de MLService
try:
    from app.services.ml_service import MLService

    ML_SERVICE_AVAILABLE = True
except ImportError:
    ML_SERVICE_AVAILABLE = False
    MLService = None

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


class PrepararDatosRequest(BaseModel):
    conversacion_ids: Optional[List[int]] = None


class IniciarFineTuningRequest(BaseModel):
    archivo_id: str
    modelo_base: str = "gpt-3.5-turbo"
    epochs: Optional[int] = None
    learning_rate: Optional[float] = None


class ActivarModeloRequest(BaseModel):
    modelo_id: str


class GenerarEmbeddingsRequest(BaseModel):
    documento_ids: Optional[List[int]] = None


class BuscarDocumentosRequest(BaseModel):
    pregunta: str
    top_k: int = 3


class EntrenarModeloRiesgoRequest(BaseModel):
    algoritmo: str = "random_forest"
    test_size: float = 0.2
    random_state: int = 42


class ActivarModeloRiesgoRequest(BaseModel):
    modelo_id: int


class PredecirRiesgoRequest(BaseModel):
    edad: Optional[int] = None
    ingreso: Optional[float] = None
    deuda_total: Optional[float] = None
    ratio_deuda_ingreso: Optional[float] = None
    historial_pagos: Optional[float] = None
    dias_ultimo_prestamo: Optional[int] = None
    numero_prestamos_previos: Optional[int] = None


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
    """Obtener API key de OpenAI desde configuración"""
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

    return config.valor


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

        if len(conversaciones) < 10:
            raise HTTPException(
                status_code=400,
                detail=f"Se necesitan al menos 10 conversaciones calificadas (4+ estrellas). Actualmente hay {len(conversaciones)}.",
            )

        # Obtener API key
        openai_api_key = _obtener_openai_api_key(db)

        # Preparar datos
        service = AITrainingService(openai_api_key)
        conversaciones_data = [c.to_dict() for c in conversaciones]
        result = await service.preparar_datos_entrenamiento(conversaciones_data)

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
                    job.error = str(estado["error"])

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
            job.error = str(estado["error"])

        db.commit()
        db.refresh(job)

        return {"job": job.to_dict()}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error obteniendo estado del job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado: {str(e)}")


@router.post("/fine-tuning/activar")
async def activar_modelo_fine_tuned(
    request: ActivarModeloRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activar modelo fine-tuned"""
    try:
        # Desactivar otros modelos
        db.query(FineTuningJob).filter(FineTuningJob.modelo_entrenado == request.modelo_id).update({"status": "succeeded"})

        # Guardar modelo activo en configuración
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

        if config:
            config.valor = request.modelo_id
        else:
            config = ConfiguracionSistema(
                categoria="AI",
                clave="modelo_fine_tuned",
                valor=request.modelo_id,
                tipo_dato="string",
            )
            db.add(config)

        db.commit()

        return {
            "mensaje": "Modelo activado exitosamente",
            "modelo_activo": request.modelo_id,
        }

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
                        DocumentoAI.contenido_procesado == True,
                    )
                )
                .all()
            )
        else:
            documentos = db.query(DocumentoAI).filter(DocumentoAI.contenido_procesado == True).all()

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
# ML RIESGO ENDPOINTS
# ============================================


@router.get("/ml-riesgo/modelos")
async def listar_modelos_riesgo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar modelos de riesgo disponibles"""
    try:
        modelos = db.query(ModeloRiesgo).order_by(ModeloRiesgo.entrenado_en.desc()).all()
        return {"modelos": [m.to_dict() for m in modelos]}

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_database_error(e, "listando modelos")


@router.get("/ml-riesgo/modelo-activo")
async def obtener_modelo_riesgo_activo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener modelo de riesgo activo"""
    try:
        modelo = db.query(ModeloRiesgo).filter(ModeloRiesgo.activo == True).first()

        if not modelo:
            return {"modelo": None}

        return {"modelo": modelo.to_dict()}

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_database_error(e, "obteniendo modelo activo")


@router.post("/ml-riesgo/entrenar")
async def entrenar_modelo_riesgo(
    request: EntrenarModeloRiesgoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Entrenar modelo de riesgo"""
    try:
        # Obtener datos históricos de préstamos y pagos para entrenamiento
        from datetime import date

        from app.models.amortizacion import Cuota
        from app.models.pago import Pago
        from app.models.prestamo import Prestamo

        # Obtener préstamos aprobados con historial
        prestamos = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").all()

        if len(prestamos) < 10:
            raise HTTPException(
                status_code=400,
                detail=f"Se necesitan al menos 10 préstamos aprobados para entrenar. Actualmente hay {len(prestamos)}.",
            )

        # Preparar datos de entrenamiento
        training_data = []

        for prestamo in prestamos:
            # Calcular features
            cliente = prestamo.cliente
            if not cliente:
                continue

            # Calcular edad
            if cliente.fecha_nacimiento:
                edad = (date.today() - cliente.fecha_nacimiento).days // 365
            else:
                edad = 0

            # Obtener pagos del préstamo
            pagos = db.query(Pago).filter(Pago.prestamo_id == prestamo.id).all()
            total_pagado = sum(float(p.monto_pagado) for p in pagos if p.monto_pagado)

            # Calcular ratio deuda/ingreso (simplificado)
            ingreso_estimado = float(prestamo.total_financiamiento) * 0.3  # Estimación
            deuda_total = float(prestamo.total_financiamiento) - total_pagado
            ratio_deuda_ingreso = deuda_total / ingreso_estimado if ingreso_estimado > 0 else 0

            # Historial de pagos (porcentaje pagado)
            historial_pagos = total_pagado / float(prestamo.total_financiamiento) if prestamo.total_financiamiento > 0 else 0

            # Días desde último préstamo
            dias_ultimo_prestamo = (date.today() - prestamo.fecha_registro.date()).days if prestamo.fecha_registro else 0

            # Número de préstamos previos
            prestamos_previos = (
                db.query(Prestamo)
                .filter(
                    and_(
                        Prestamo.cliente_id == prestamo.cliente_id,
                        Prestamo.id < prestamo.id,
                    )
                )
                .count()
            )

            # Determinar target (riesgo) basado en morosidad
            cuotas = db.query(Cuota).filter(Cuota.prestamo_id == prestamo.id).all()
            cuotas_vencidas = [c for c in cuotas if c.fecha_vencimiento < date.today() and c.estado != "PAGADA"]

            if len(cuotas_vencidas) > 3:
                target = 2  # Alto riesgo
            elif len(cuotas_vencidas) > 0:
                target = 1  # Medio riesgo
            else:
                target = 0  # Bajo riesgo

            training_data.append(
                {
                    "edad": edad,
                    "ingreso": ingreso_estimado,
                    "deuda_total": deuda_total,
                    "ratio_deuda_ingreso": ratio_deuda_ingreso,
                    "historial_pagos": historial_pagos,
                    "dias_ultimo_prestamo": dias_ultimo_prestamo,
                    "numero_prestamos_previos": prestamos_previos,
                    "target": target,
                }
            )

        if len(training_data) < 10:
            raise HTTPException(
                status_code=400,
                detail=f"Se necesitan al menos 10 muestras válidas para entrenar. Se generaron {len(training_data)}.",
            )

        # Verificar que MLService esté disponible
        if not ML_SERVICE_AVAILABLE or MLService is None:
            raise HTTPException(
                status_code=503,
                detail="scikit-learn no está instalado. Instala con: pip install scikit-learn",
            )

        # Entrenar modelo
        ml_service = MLService()
        resultado = ml_service.train_risk_model(
            training_data,
            algoritmo=request.algoritmo,
            test_size=request.test_size,
            random_state=request.random_state,
        )

        if not resultado.get("success"):
            raise HTTPException(status_code=500, detail=resultado.get("error", "Error entrenando modelo"))

        # Guardar modelo en BD
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        modelo = ModeloRiesgo(
            nombre=f"Modelo Riesgo {timestamp}",
            version="1.0.0",
            algoritmo=request.algoritmo,
            accuracy=resultado["metrics"]["accuracy"],
            precision=resultado["metrics"]["precision"],
            recall=resultado["metrics"]["recall"],
            f1_score=resultado["metrics"]["f1_score"],
            roc_auc=resultado["metrics"].get("roc_auc"),
            ruta_archivo=resultado["model_path"],
            total_datos_entrenamiento=resultado["training_samples"],
            total_datos_test=resultado["test_samples"],
            test_size=request.test_size,
            random_state=request.random_state,
            features_usadas=",".join(resultado["features"]),
            activo=False,
        )

        db.add(modelo)
        db.commit()
        db.refresh(modelo)

        return {
            "job_id": str(modelo.id),
            "mensaje": "Modelo entrenado exitosamente",
            "modelo": modelo.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error entrenando modelo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error entrenando modelo: {str(e)}")


@router.get("/ml-riesgo/jobs/{job_id}")
async def obtener_estado_entrenamiento_ml(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtener estado del entrenamiento ML"""
    try:
        modelo = db.query(ModeloRiesgo).filter(ModeloRiesgo.id == int(job_id)).first()

        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")

        return {
            "status": "succeeded",  # Los modelos ML se entrenan sincrónicamente
            "modelo": modelo.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estado: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado: {str(e)}")


@router.post("/ml-riesgo/activar")
async def activar_modelo_riesgo(
    request: ActivarModeloRiesgoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activar modelo de riesgo"""
    try:
        # Desactivar otros modelos
        db.query(ModeloRiesgo).update({"activo": False})

        # Activar modelo seleccionado
        modelo = db.query(ModeloRiesgo).filter(ModeloRiesgo.id == request.modelo_id).first()

        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")

        modelo.activo = True
        modelo.activado_en = datetime.utcnow()

        # Verificar que MLService esté disponible
        if not ML_SERVICE_AVAILABLE or MLService is None:
            raise HTTPException(
                status_code=503,
                detail="scikit-learn no está instalado. Instala con: pip install scikit-learn",
            )

        # Cargar modelo en servicio ML
        ml_service = MLService()
        ml_service.load_model_from_path(modelo.ruta_archivo)

        db.commit()
        db.refresh(modelo)

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


@router.post("/ml-riesgo/predecir")
async def predecir_riesgo(
    request: PredecirRiesgoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Predecir riesgo de un cliente"""
    try:
        # Obtener modelo activo
        modelo_activo = db.query(ModeloRiesgo).filter(ModeloRiesgo.activo == True).first()

        if not modelo_activo:
            raise HTTPException(status_code=400, detail="No hay modelo activo")

        # Verificar que MLService esté disponible
        if not ML_SERVICE_AVAILABLE or MLService is None:
            raise HTTPException(
                status_code=503,
                detail="scikit-learn no está instalado. Instala con: pip install scikit-learn",
            )

        # Cargar modelo
        ml_service = MLService()
        if not ml_service.load_model_from_path(modelo_activo.ruta_archivo):
            raise HTTPException(status_code=500, detail="Error cargando modelo")

        # Preparar datos del cliente
        client_data = {
            "age": request.edad or 0,
            "income": request.ingreso or 0,
            "debt_total": request.deuda_total or 0,
            "debt_ratio": request.ratio_deuda_ingreso or 0,
            "credit_score": request.historial_pagos or 0,  # Usar historial como score
        }

        # Predecir
        prediccion = ml_service.predict_risk(client_data)

        return {
            "riesgo_level": prediccion["risk_level"],
            "confidence": prediccion["confidence"],
            "recommendation": prediccion["recommendation"],
            "features_used": prediccion["features_used"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error prediciendo riesgo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error prediciendo riesgo: {str(e)}")


# ============================================
# MÉTRICAS CONSOLIDADAS
# ============================================


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

        # Métricas de ML
        modelos_disponibles = db.query(ModeloRiesgo).count()
        modelo_activo_ml = db.query(ModeloRiesgo).filter(ModeloRiesgo.activo == True).first()
        ultimo_modelo = db.query(ModeloRiesgo).order_by(ModeloRiesgo.entrenado_en.desc()).first()

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
            "ml_riesgo": {
                "modelos_disponibles": modelos_disponibles,
                "modelo_activo": modelo_activo_ml.nombre if modelo_activo_ml else None,
                "ultimo_entrenamiento": (ultimo_modelo.entrenado_en.isoformat() if ultimo_modelo else None),
                "accuracy_promedio": (
                    float(modelo_activo_ml.accuracy) if modelo_activo_ml and modelo_activo_ml.accuracy else None
                ),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise _handle_database_error(e, "obteniendo métricas")
