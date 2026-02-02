"""
Endpoints de entrenamiento AI.
GET /metricas: métricas de conversaciones, fine-tuning, RAG y ML riesgo.
Estructura esperada por el frontend (MetricasEntrenamiento); datos desde BD cuando existan tablas.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(get_current_user)])


def _metricas_stub() -> dict[str, Any]:
    """Estructura por defecto cuando no hay datos de conversaciones/fine-tuning en BD."""
    return {
        "conversaciones": {
            "total": 0,
            "con_calificacion": 0,
            "promedio_calificacion": 0.0,
            "listas_entrenamiento": 0,
        },
        "fine_tuning": {
            "jobs_totales": 0,
            "jobs_exitosos": 0,
            "jobs_fallidos": 0,
        },
        "rag": {
            "documentos_con_embeddings": 0,
            "total_embeddings": 0,
        },
        "ml_riesgo": {
            "modelos_disponibles": 0,
        },
    }


@router.get("/metricas")
def get_metricas(db: Session = Depends(get_db)):
    """
    Métricas de entrenamiento AI (conversaciones, fine-tuning, RAG, ML riesgo).
    Devuelve estructura esperada por el frontend; por ahora stub con ceros.
    """
    # TODO: consultar BD cuando existan tablas conversaciones_ai, jobs fine-tuning, embeddings, modelos
    return _metricas_stub()
