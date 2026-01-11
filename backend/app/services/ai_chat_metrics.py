"""
Sistema de métricas para Chat AI
Almacena métricas de uso y rendimiento del endpoint de Chat AI
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AIChatMetrics:
    """Sistema de métricas para Chat AI"""

    # Métricas en memoria (para producción, considerar usar Redis o BD)
    _metrics_store: List[Dict[str, Any]] = []
    _max_metrics = 1000  # Mantener últimas 1000 métricas

    @classmethod
    def record_metric(
        cls,
        usuario_id: int,
        usuario_email: str,
        pregunta_length: int,
        tiempo_total: float,
        tiempo_respuesta_openai: float,
        tokens_usados: int,
        modelo_usado: str,
        exito: bool,
        error: Optional[str] = None,
    ) -> None:
        """
        Registra una métrica de uso del Chat AI

        Args:
            usuario_id: ID del usuario
            usuario_email: Email del usuario
            pregunta_length: Longitud de la pregunta
            tiempo_total: Tiempo total de procesamiento (segundos)
            tiempo_respuesta_openai: Tiempo de respuesta de OpenAI (segundos)
            tokens_usados: Tokens usados en la respuesta
            modelo_usado: Modelo de AI usado
            exito: Si la operación fue exitosa
            error: Mensaje de error si hubo fallo
        """
        metric = {
            "timestamp": datetime.now().isoformat(),
            "usuario_id": usuario_id,
            "usuario_email": usuario_email,
            "pregunta_length": pregunta_length,
            "tiempo_total": tiempo_total,
            "tiempo_respuesta_openai": tiempo_respuesta_openai,
            "tokens_usados": tokens_usados,
            "modelo_usado": modelo_usado,
            "exito": exito,
            "error": error,
        }

        cls._metrics_store.append(metric)

        # Limitar tamaño del almacén
        if len(cls._metrics_store) > cls._max_metrics:
            cls._metrics_store.pop(0)

        logger.debug(f"📊 Métrica registrada: {usuario_email} - {tiempo_total:.2f}s - {tokens_usados} tokens")

    @classmethod
    def get_stats(cls, horas: int = 24) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso del Chat AI

        Args:
            horas: Número de horas hacia atrás para calcular estadísticas

        Returns:
            Diccionario con estadísticas
        """
        cutoff_time = datetime.now() - timedelta(hours=horas)
        cutoff_iso = cutoff_time.isoformat()

        # Filtrar métricas del período
        recent_metrics = [m for m in cls._metrics_store if m["timestamp"] >= cutoff_iso]

        if not recent_metrics:
            return {
                "periodo_horas": horas,
                "total_requests": 0,
                "requests_exitosos": 0,
                "requests_fallidos": 0,
                "tiempo_promedio": 0,
                "tokens_promedio": 0,
                "usuarios_unicos": 0,
            }

        total_requests = len(recent_metrics)
        requests_exitosos = sum(1 for m in recent_metrics if m["exito"])
        requests_fallidos = total_requests - requests_exitosos

        tiempos = [m["tiempo_total"] for m in recent_metrics]
        tokens = [m["tokens_usados"] for m in recent_metrics if m["tokens_usados"] > 0]
        usuarios_unicos = len(set(m["usuario_email"] for m in recent_metrics))

        return {
            "periodo_horas": horas,
            "total_requests": total_requests,
            "requests_exitosos": requests_exitosos,
            "requests_fallidos": requests_fallidos,
            "tasa_exito": round(requests_exitosos / total_requests * 100, 2) if total_requests > 0 else 0,
            "tiempo_promedio": round(sum(tiempos) / len(tiempos), 2) if tiempos else 0,
            "tiempo_minimo": round(min(tiempos), 2) if tiempos else 0,
            "tiempo_maximo": round(max(tiempos), 2) if tiempos else 0,
            "tokens_promedio": round(sum(tokens) / len(tokens), 2) if tokens else 0,
            "tokens_total": sum(tokens),
            "usuarios_unicos": usuarios_unicos,
            "modelos_usados": {
                modelo: sum(1 for m in recent_metrics if m["modelo_usado"] == modelo)
                for modelo in set(m["modelo_usado"] for m in recent_metrics)
            },
        }

    @classmethod
    def get_user_stats(cls, usuario_email: str, horas: int = 24) -> Dict[str, Any]:
        """
        Obtiene estadísticas de uso para un usuario específico

        Args:
            usuario_email: Email del usuario
            horas: Número de horas hacia atrás

        Returns:
            Diccionario con estadísticas del usuario
        """
        cutoff_time = datetime.now() - timedelta(hours=horas)
        cutoff_iso = cutoff_time.isoformat()

        user_metrics = [m for m in cls._metrics_store if m["usuario_email"] == usuario_email and m["timestamp"] >= cutoff_iso]

        if not user_metrics:
            return {
                "usuario_email": usuario_email,
                "periodo_horas": horas,
                "total_requests": 0,
                "requests_exitosos": 0,
                "requests_fallidos": 0,
                "tiempo_promedio": 0,
                "tokens_total": 0,
            }

        total_requests = len(user_metrics)
        requests_exitosos = sum(1 for m in user_metrics if m["exito"])
        requests_fallidos = total_requests - requests_exitosos

        tiempos = [m["tiempo_total"] for m in user_metrics]
        tokens = [m["tokens_usados"] for m in user_metrics if m["tokens_usados"] > 0]

        return {
            "usuario_email": usuario_email,
            "periodo_horas": horas,
            "total_requests": total_requests,
            "requests_exitosos": requests_exitosos,
            "requests_fallidos": requests_fallidos,
            "tasa_exito": round(requests_exitosos / total_requests * 100, 2) if total_requests > 0 else 0,
            "tiempo_promedio": round(sum(tiempos) / len(tiempos), 2) if tiempos else 0,
            "tiempo_minimo": round(min(tiempos), 2) if tiempos else 0,
            "tiempo_maximo": round(max(tiempos), 2) if tiempos else 0,
            "tokens_total": sum(tokens),
            "tokens_promedio": round(sum(tokens) / len(tokens), 2) if tokens else 0,
        }

    @classmethod
    def clear_metrics(cls) -> None:
        """Limpia todas las métricas almacenadas"""
        cls._metrics_store.clear()
        logger.info("📊 Métricas de Chat AI limpiadas")
