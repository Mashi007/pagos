"""
Endpoints de entrenamiento AI.
Conversaciones (CRUD, calificar, estadísticas, recolectar, analizar), fine-tuning (stubs), RAG (stubs).
Métricas desde BD cuando exista tabla conversaciones_ai.
"""
import json
import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.conversacion_ai import ConversacionAI

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


def _parse_json_array(s: Optional[str]):
    if not s or not s.strip():
        return []
    try:
        out = json.loads(s)
        return out if isinstance(out, list) else []
    except Exception:
        return []


def _conv_to_dict(row: ConversacionAI) -> dict:
    return {
        "id": row.id,
        "pregunta": row.pregunta or "",
        "respuesta": row.respuesta or "",
        "contexto_usado": row.contexto_usado,
        "documentos_usados": _parse_json_array(row.documentos_usados),
        "modelo_usado": row.modelo_usado,
        "tokens_usados": row.tokens_usados,
        "tiempo_respuesta": row.tiempo_respuesta,
        "calificacion": row.calificacion,
        "feedback": row.feedback,
        "usuario_id": row.usuario_id,
        "creado_en": row.creado_en.isoformat() if row.creado_en else "",
    }


# ============== MÉTRICAS ==============

def _metricas_from_db(db: Session) -> dict[str, Any]:
    """Métricas desde tabla conversaciones_ai si existe."""
    try:
        total = db.query(func.count(ConversacionAI.id)).scalar() or 0
        con_cal = db.query(func.count(ConversacionAI.id)).filter(ConversacionAI.calificacion.isnot(None)).scalar() or 0
        avg = db.query(func.avg(ConversacionAI.calificacion)).filter(ConversacionAI.calificacion.isnot(None)).scalar()
        listas = db.query(func.count(ConversacionAI.id)).filter(ConversacionAI.calificacion >= 4).scalar() or 0
        return {
            "conversaciones": {
                "total": total,
                "con_calificacion": con_cal,
                "promedio_calificacion": round(float(avg or 0), 2),
                "listas_entrenamiento": listas,
            },
            "fine_tuning": {"jobs_totales": 0, "jobs_exitosos": 0, "jobs_fallidos": 0},
            "rag": {"documentos_con_embeddings": 0, "total_embeddings": 0},
            "ml_riesgo": {"modelos_disponibles": 0},
        }
    except Exception as e:
        logger.warning("Métricas desde BD: %s", e)
    return {
        "conversaciones": {"total": 0, "con_calificacion": 0, "promedio_calificacion": 0.0, "listas_entrenamiento": 0},
        "fine_tuning": {"jobs_totales": 0, "jobs_exitosos": 0, "jobs_fallidos": 0},
        "rag": {"documentos_con_embeddings": 0, "total_embeddings": 0},
        "ml_riesgo": {"modelos_disponibles": 0},
    }


@router.get("/metricas")
def get_metricas(db: Session = Depends(get_db)):
    """Métricas de entrenamiento AI desde BD (conversaciones_ai) o stub."""
    return _metricas_from_db(db)


# ============== CONVERSACIONES ==============

@router.get("/conversaciones")
def get_conversaciones(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    con_calificacion: Optional[bool] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
):
    """Lista conversaciones paginadas. Filtros: con_calificacion, fecha_desde, fecha_hasta."""
    q = db.query(ConversacionAI)
    if con_calificacion is not None:
        if con_calificacion:
            q = q.filter(ConversacionAI.calificacion.isnot(None))
        else:
            q = q.filter(ConversacionAI.calificacion.is_(None))
    if fecha_desde:
        q = q.filter(ConversacionAI.creado_en >= fecha_desde)
    if fecha_hasta:
        q = q.filter(ConversacionAI.creado_en <= fecha_hasta)
    total = q.count()
    offset = (page - 1) * per_page
    rows = q.order_by(ConversacionAI.creado_en.desc()).offset(offset).limit(per_page).all()
    total_pages = (total + per_page - 1) // per_page if total else 1
    return {
        "conversaciones": [_conv_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "total_pages": total_pages,
    }


class ConversacionCreate(BaseModel):
    pregunta: str
    respuesta: str
    contexto_usado: Optional[str] = None
    documentos_usados: Optional[list[int]] = None
    modelo_usado: Optional[str] = None
    tokens_usados: Optional[int] = None
    tiempo_respuesta: Optional[int] = None


@router.post("/conversaciones")
def post_conversaciones(payload: ConversacionCreate = Body(...), db: Session = Depends(get_db)):
    """Crea una conversación para entrenamiento."""
    doc_usados = json.dumps(payload.documentos_usados) if payload.documentos_usados else None
    row = ConversacionAI(
        pregunta=payload.pregunta.strip(),
        respuesta=payload.respuesta.strip(),
        contexto_usado=payload.contexto_usado or None,
        documentos_usados=doc_usados,
        modelo_usado=payload.modelo_usado,
        tokens_usados=payload.tokens_usados,
        tiempo_respuesta=payload.tiempo_respuesta,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"conversacion": _conv_to_dict(row)}


class CalificarBody(BaseModel):
    calificacion: int
    feedback: Optional[str] = None


@router.post("/conversaciones/{conversacion_id}/calificar")
def post_conversaciones_calificar(
    conversacion_id: int,
    payload: CalificarBody = Body(...),
    db: Session = Depends(get_db),
):
    """Califica una conversación (1-5) y opcionalmente feedback."""
    row = db.get(ConversacionAI, conversacion_id)
    if not row:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    if not (1 <= payload.calificacion <= 5):
        raise HTTPException(status_code=400, detail="Calificación debe ser 1-5")
    row.calificacion = payload.calificacion
    row.feedback = payload.feedback or None
    db.commit()
    db.refresh(row)
    return {"conversacion": _conv_to_dict(row)}


class ConversacionUpdate(BaseModel):
    pregunta: Optional[str] = None
    respuesta: Optional[str] = None
    contexto_usado: Optional[str] = None
    documentos_usados: Optional[list[int]] = None
    modelo_usado: Optional[str] = None


@router.put("/conversaciones/{conversacion_id}")
def put_conversaciones(
    conversacion_id: int,
    payload: ConversacionUpdate = Body(...),
    db: Session = Depends(get_db),
):
    """Actualiza una conversación."""
    row = db.get(ConversacionAI, conversacion_id)
    if not row:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    data = payload.model_dump(exclude_unset=True)
    if "documentos_usados" in data and data["documentos_usados"] is not None:
        data["documentos_usados"] = json.dumps(data["documentos_usados"])
    for k, v in data.items():
        if hasattr(row, k):
            setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return {"conversacion": _conv_to_dict(row)}


@router.get("/conversaciones/estadisticas-feedback")
def get_estadisticas_feedback(db: Session = Depends(get_db)):
    """Estadísticas de feedback para el dashboard de fine-tuning."""
    total = db.query(func.count(ConversacionAI.id)).scalar() or 0
    calificadas = db.query(func.count(ConversacionAI.id)).filter(ConversacionAI.calificacion.isnot(None)).scalar() or 0
    con_feedback = db.query(func.count(ConversacionAI.id)).filter(ConversacionAI.feedback.isnot(None), ConversacionAI.feedback != "").scalar() or 0
    listas = db.query(func.count(ConversacionAI.id)).filter(ConversacionAI.calificacion >= 4).scalar() or 0
    # Distribución calificaciones
    dist = {}
    for i in range(1, 6):
        c = db.query(func.count(ConversacionAI.id)).filter(ConversacionAI.calificacion == i).scalar() or 0
        dist[str(i)] = c
    # Feedback negativo: heuristic simple (palabras típicas)
    neg_words = ["mal", "incorrecto", "error", "no sirve", "malo", "pésimo", "incorrecta"]
    con_neg = 0
    for r in db.query(ConversacionAI).filter(ConversacionAI.feedback.isnot(None), ConversacionAI.feedback != "").all():
        fb = (r.feedback or "").lower()
        if any(w in fb for w in neg_words):
            con_neg += 1
    sin_neg = max(0, listas - con_neg)
    return {
        "total_conversaciones": total,
        "conversaciones_calificadas": calificadas,
        "conversaciones_con_feedback": con_feedback,
        "distribucion_calificaciones": dist,
        "analisis_feedback": {"positivo": max(0, con_feedback - con_neg), "negativo": con_neg, "neutro": 0, "total": con_feedback},
        "conversaciones_listas_entrenamiento": {
            "total": listas,
            "sin_feedback_negativo": sin_neg,
            "con_feedback_negativo": con_neg,
            "puede_preparar": listas >= 10,
        },
    }


class RecolectarBody(BaseModel):
    pass


@router.post("/recolectar-automatico")
def post_recolectar_automatico(db: Session = Depends(get_db)):
    """Recolecta conversaciones desde chat/calificaciones hacia conversaciones_ai (stub: 0 nuevas)."""
    # TODO: leer desde configuracion chat_ai_calificaciones y crear filas en conversaciones_ai si no existen
    return {"total_recolectadas": 0}


class AnalizarCalidadBody(BaseModel):
    pass


@router.post("/analizar-calidad")
def post_analizar_calidad(db: Session = Depends(get_db)):
    """Analiza calidad de conversaciones (stub)."""
    return {"mensaje": "Análisis de calidad no implementado aún", "resumen": {}}


class MejorarBody(BaseModel):
    pregunta: Optional[str] = None
    respuesta: Optional[str] = None


@router.post("/conversaciones/mejorar")
def post_conversaciones_mejorar(payload: MejorarBody = Body(...)):
    """Mejora pregunta/respuesta con IA (stub: devuelve mismo texto)."""
    return {
        "pregunta_mejorada": payload.pregunta or "",
        "respuesta_mejorada": payload.respuesta or "",
        "mejoras_aplicadas": [],
    }


# ============== FINE-TUNING (stubs) ==============

@router.get("/fine-tuning/jobs")
def get_fine_tuning_jobs():
    """Lista jobs de fine-tuning (stub: vacío)."""
    return {"jobs": []}


@router.get("/fine-tuning/jobs/{job_id}")
def get_fine_tuning_job(job_id: str):
    """Estado de un job (stub: 404)."""
    raise HTTPException(status_code=404, detail="Job no encontrado")


class PrepararBody(BaseModel):
    conversacion_ids: Optional[list[int]] = None
    filtrar_feedback_negativo: bool = True


@router.post("/fine-tuning/preparar")
def post_fine_tuning_preparar(payload: PrepararBody = Body(...), db: Session = Depends(get_db)):
    """Prepara datos para fine-tuning: genera archivo_id y cuenta conversaciones."""
    ids = payload.conversacion_ids or []
    if not ids:
        # Todas las calificadas 4+
        rows = db.query(ConversacionAI).filter(ConversacionAI.calificacion >= 4).all()
        ids = [r.id for r in rows]
    if payload.filtrar_feedback_negativo:
        neg_words = ["mal", "incorrecto", "error", "no sirve", "malo", "pésimo"]
        excluidos = []
        restantes = []
        for r in db.query(ConversacionAI).filter(ConversacionAI.id.in_(ids)).all():
            fb = (r.feedback or "").lower()
            if any(w in fb for w in neg_words):
                excluidos.append({"id": r.id, "razon": "feedback negativo", "feedback": r.feedback or ""})
            else:
                restantes.append(r.id)
        ids = restantes
    else:
        excluidos = []
    archivo_id = f"file-{uuid.uuid4().hex[:12]}"
    return {
        "archivo_id": archivo_id,
        "total_conversaciones": len(ids),
        "conversaciones_originales": len(ids) + len(excluidos) if excluidos else None,
        "conversaciones_excluidas": len(excluidos) if excluidos else 0,
        "detalles_exclusion": excluidos if excluidos else None,
    }


class IniciarBody(BaseModel):
    archivo_id: str
    modelo_base: Optional[str] = None
    epochs: Optional[int] = None
    learning_rate: Optional[float] = None


@router.post("/fine-tuning/iniciar")
def post_fine_tuning_iniciar(payload: IniciarBody = Body(...)):
    """Inicia fine-tuning (stub: devuelve job pendiente)."""
    job_id = f"ft-{uuid.uuid4().hex[:12]}"
    return {
        "job": {
            "id": job_id,
            "status": "pending",
            "modelo_base": payload.modelo_base or "gpt-4o-2024-08-06",
            "modelo_entrenado": None,
            "archivo_entrenamiento": payload.archivo_id,
            "progreso": 0,
            "error": None,
            "creado_en": "",
            "completado_en": None,
        }
    }


@router.post("/fine-tuning/activar")
def post_fine_tuning_activar(payload: dict = Body(...)):
    """Activa modelo fine-tuned (stub)."""
    modelo_id = payload.get("modelo_id") or ""
    return {"mensaje": "Activación no implementada aún", "modelo_activo": modelo_id}


@router.post("/fine-tuning/jobs/{job_id}/cancelar")
def post_fine_tuning_jobs_cancelar(job_id: str):
    """Cancela job (stub)."""
    raise HTTPException(status_code=404, detail="Job no encontrado")


@router.delete("/fine-tuning/jobs/{job_id}")
def delete_fine_tuning_jobs_id(job_id: str):
    """Elimina job (stub)."""
    return {"mensaje": "Eliminado"}


@router.delete("/fine-tuning/jobs")
def delete_fine_tuning_jobs(solo_fallidos: bool = Query(False)):
    """Elimina todos los jobs o solo fallidos (stub)."""
    return {"mensaje": "Eliminados", "eliminados": 0}


# ============== RAG (stubs) ==============

@router.get("/rag/estado")
def get_rag_estado():
    """Estado de embeddings RAG (stub)."""
    return {
        "total_documentos": 0,
        "documentos_con_embeddings": 0,
        "total_embeddings": 0,
        "ultima_actualizacion": None,
    }


@router.post("/rag/generar-embeddings")
def post_rag_generar_embeddings(payload: dict = Body(...)):
    """Genera embeddings (stub)."""
    return {"documentos_procesados": 0, "total_embeddings": 0}


@router.post("/rag/buscar")
def post_rag_buscar(payload: dict = Body(...)):
    """Busca documentos por similitud (stub)."""
    return {"documentos": [], "query_embedding": None}


@router.post("/rag/documentos/{documento_id}/embeddings")
def post_rag_documentos_embeddings(documento_id: int):
    """Actualiza embeddings de un documento (stub)."""
    return {"embeddings_generados": 0}
