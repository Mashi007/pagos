from collections import deque
import statistics
﻿"""Dashboard de Diagnóstico en Tiempo Real
Sistema de monitoreo y auditoría para problemas de autenticación
"""

import logging
from collections import defaultdict, deque
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# Almacenamiento en memoria para auditoría
error_patterns = defaultdict(int)
request_stats = defaultdict(int)


class AuditLogger:
    """Logger especializado para auditoría de autenticación"""

    @staticmethod
    def log_request
    ):
        """Registrar request en auditoría"""
        log_entry = 
        }

        # Agregar al log
        audit_logs.append(log_entry)

        # Actualizar estadísticas
        request_stats[f"status_{response.status_code}"] += 1
        if error:
            error_patterns[error] += 1

        # Log específico para errores 401
        if response.status_code == 401:
            logger.warning
            )

    @staticmethod
    def get_recent_logs(minutes: int = 60) -> List[Dict[str, Any]]:
        """Obtener logs recientes"""
        return [
            log for log in audit_logs
        ]

    @staticmethod
    def get_error_summary() -> Dict[str, Any]:
        """Obtener resumen de errores"""
        return 
        }

# ============================================
# ENDPOINTS DEL DASHBOARD
# ============================================

@router.get("/dashboard/overview")
async def get_dashboard_overview
    db: Session = Depends(get_db),
):
    """Obtener vista general del dashboard"""
    try:
        # Obtener estadísticas de auditoría
        audit_summary = AuditLogger.get_error_summary()

        # Obtener logs recientes
        recent_logs = AuditLogger.get_recent_logs(60)

        # Calcular métricas básicas
        total_requests = len(recent_logs)
        error_requests = len([log for log in recent_logs if log["status_code"] >= 400])
        auth_requests = len([log for log in recent_logs if log["auth_header_present"]])

        overview = 
            },
            "audit_summary": audit_summary,
            "system_status": "operational",
            "database_status": "connected",
        }

        return 
        }

    except Exception as e:
        logger.error(f"Error obteniendo vista general: {e}")
        raise HTTPException
            detail=f"Error interno: {str(e)}"
        )

@router.get("/dashboard/recent-activity")
async def get_recent_activity
    db: Session = Depends(get_db),
):
    """Obtener actividad reciente"""
    try:
        recent_logs = AuditLogger.get_recent_logs(minutes)

        # Procesar logs para actividad
        activity = []
        for log in recent_logs:
            activity.append
            })

        return 
        }

    except Exception as e:
        logger.error(f"Error obteniendo actividad reciente: {e}")
        raise HTTPException
            detail=f"Error interno: {str(e)}"
        )

@router.get("/dashboard/error-analysis")
async def get_error_analysis
    db: Session = Depends(get_db),
):
    """Obtener análisis de errores"""
    try:
        audit_summary = AuditLogger.get_error_summary()

        # Analizar patrones de error
        error_analysis = 
        }

        # Generar recomendaciones basadas en patrones
        if error_patterns.get("Invalid token", 0) > 10:
            error_analysis["recommendations"].append
            )

        if error_patterns.get("Token expired", 0) > 5:
            error_analysis["recommendations"].append
            )

        if not error_analysis["recommendations"]:
            error_analysis["recommendations"].append
            )

        return 
        }

    except Exception as e:
        logger.error(f"Error analizando errores: {e}")
        raise HTTPException
            detail=f"Error interno: {str(e)}"
        )

async def log_dashboard_event
    db: Session = Depends(get_db),
):
    """Registrar evento en el dashboard"""
    try:
        # Crear respuesta simulada para el logger
        from fastapi import Response
        response = Response()
        response.status_code = event_data.get("status_code", 200)

        # Registrar evento
        AuditLogger.log_request
            user_id=event_data.get("user_id"),
            error=event_data.get("error")
        )

        return 
        }

    except Exception as e:
        logger.error(f"Error registrando evento: {e}")
        raise HTTPException
            detail=f"Error interno: {str(e)}"
        )

@router.get("/dashboard/system-health")
async def get_system_health
    db: Session = Depends(get_db),
):
    """Obtener estado de salud del sistema"""
    try:
        # Verificar conexión a BD
        db_status = "connected"
        try:
            db.execute("SELECT 1")
        except Exception:
            db_status = "disconnected"

        # Obtener métricas del sistema
        recent_logs = AuditLogger.get_recent_logs(60)
        error_rate = len([log for log in recent_logs if log["status_code"] >= 400]) / max(len(recent_logs), 1) * 100

        health_status = 
            },
            "metrics": 
            },
            "alerts": []
        }

        # Agregar alertas si es necesario
        if error_rate > 20:
            health_status["alerts"].append
            })

        if db_status == "disconnected":
            health_status["alerts"].append
            })

        return 
        }

    except Exception as e:
        logger.error(f"Error obteniendo estado de salud: {e}")
        raise HTTPException
            detail=f"Error interno: {str(e)}"
        )

"""