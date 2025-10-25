"""Sistema de Monitoreo de Errores Críticos
Monitorea específicamente errores que causan fallos de despliegue y 503
"""

import logging
import threading
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA DE MONITOREO DE ERRORES CRÍTICOS
# ============================================

class CriticalErrorMonitor:
    """Monitor de errores críticos del sistema"""
    
def __init__(self):
        self.error_patterns = defaultdict(int)
        self.critical_errors = deque(maxlen=1000)
        self.deployment_failures = deque(maxlen=100)
        self.service_503_errors = deque(maxlen=200)
        self.lock = threading.Lock()
    
    def log_critical_error(
        self, 
        error_type: str, 
        error_message: str, 
        context: Dict[str, Any]
    ) -> None:
        """Registrar un error crítico"""
        with self.lock:
            timestamp = datetime.now()
            error_record = {
                "timestamp": timestamp,
                "error_type": error_type,
                "error_message": error_message,
                "context": context,
                "severity": self._calculate_severity(error_type, context)
            }
            
            self.critical_errors.append(error_record)
            self.error_patterns[error_type] += 1
            
            # Clasificar por tipo específico
            if "deployment" in error_type.lower():
                self.deployment_failures.append(error_record)
            elif "503" in error_message or "service_unavailable" in error_type.lower():
                self.service_503_errors.append(error_record)
            
            logger.critical(f"Error crítico detectado: {error_type} - {error_message}")
    
    def _calculate_severity(self, error_type: str, context: Dict[str, Any]) -> str:
        """Calcular severidad del error"""
        if "database" in error_type.lower():
            return "CRITICAL"
        elif "authentication" in error_type.lower():
            return "HIGH"
        elif "deployment" in error_type.lower():
            return "CRITICAL"
        elif "503" in str(context):
            return "HIGH"
        else:
            return "MEDIUM"
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Obtener resumen de errores críticos"""
        with self.lock:
            return {
                "timestamp": datetime.now().isoformat(),
                "total_critical_errors": len(self.critical_errors),
                "deployment_failures": len(self.deployment_failures),
                "service_503_errors": len(self.service_503_errors),
                "error_patterns": dict(self.error_patterns),
                "recent_errors": list(self.critical_errors)[-10:],  # Últimos 10
                "severity_distribution": self._get_severity_distribution()
            }
    
    def _get_severity_distribution(self) -> Dict[str, int]:
        """Obtener distribución por severidad"""
        distribution = defaultdict(int)
        for error in self.critical_errors:
            distribution[error["severity"]] += 1
        return dict(distribution)
    
    def clear_old_errors(self, hours: int = 24) -> int:
        """Limpiar errores antiguos"""
        with self.lock:
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            initial_count = len(self.critical_errors)
            
            # Filtrar errores recientes
            recent_errors = [
                error for error in self.critical_errors 
                if error["timestamp"].timestamp() > cutoff_time
            ]
            
            self.critical_errors.clear()
            self.critical_errors.extend(recent_errors)
            
            cleared_count = initial_count - len(self.critical_errors)
            logger.info(f"Limpiados {cleared_count} errores antiguos")
            return cleared_count

# Instancia global del monitor
critical_monitor = CriticalErrorMonitor()

# ============================================
# ENDPOINTS DE MONITOREO
# ============================================

@router.get("/critical-errors-summary")
async def get_critical_errors_summary(
    current_user: User = Depends(get_current_user),
):
    """Obtener resumen de errores críticos"""
    try:
        summary = critical_monitor.get_error_summary()
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        logger.error(f"Error obteniendo resumen de errores críticos: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.post("/log-critical-error")
async def log_critical_error(
    error_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """Registrar un error crítico"""
    try:
        error_type = error_data.get("error_type", "unknown")
        error_message = error_data.get("error_message", "")
        context = error_data.get("context", {})
        
        critical_monitor.log_critical_error(
            error_type=error_type,
            error_message=error_message,
            context=context
        )
        
        return {
            "success": True,
            "message": "Error crítico registrado exitosamente"
        }
    except Exception as e:
        logger.error(f"Error registrando error crítico: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/deployment-failures")
async def get_deployment_failures(
    current_user: User = Depends(get_current_user),
):
    """Obtener fallos de despliegue recientes"""
    try:
        with critical_monitor.lock:
            failures = list(critical_monitor.deployment_failures)
        
        return {
            "success": True,
            "data": {
                "total_failures": len(failures),
                "failures": failures[-20:]  # Últimos 20
            }
        }
    except Exception as e:
        logger.error(f"Error obteniendo fallos de despliegue: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/service-503-errors")
async def get_service_503_errors(
    current_user: User = Depends(get_current_user),
):
    """Obtener errores 503 del servicio"""
    try:
        with critical_monitor.lock:
            errors_503 = list(critical_monitor.service_503_errors)
        
        return {
            "success": True,
            "data": {
                "total_503_errors": len(errors_503),
                "errors": errors_503[-30:]  # Últimos 30
            }
        }
    except Exception as e:
        logger.error(f"Error obteniendo errores 503: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.post("/clear-old-errors")
async def clear_old_errors(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
):
    """Limpiar errores antiguos"""
    try:
        cleared_count = critical_monitor.clear_old_errors(hours)
        
        return {
            "success": True,
            "message": f"Limpiados {cleared_count} errores antiguos",
            "cleared_count": cleared_count
        }
    except Exception as e:
        logger.error(f"Error limpiando errores antiguos: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )

@router.get("/error-patterns")
async def get_error_patterns(
    current_user: User = Depends(get_current_user),
):
    """Obtener patrones de errores"""
    try:
        with critical_monitor.lock:
            patterns = dict(critical_monitor.error_patterns)
        
        # Ordenar por frecuencia
        sorted_patterns = sorted(
            patterns.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return {
            "success": True,
            "data": {
                "patterns": dict(sorted_patterns),
                "total_patterns": len(patterns)
            }
        }
    except Exception as e:
        logger.error(f"Error obteniendo patrones de errores: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )