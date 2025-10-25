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
            
            # Log específico para errores críticos
            logger.error(
                f"🚨 ERROR CRÍTICO: {error_type} - {error_message}",
                extra={"context": context, "timestamp": timestamp}
            )
    
    def _calculate_severity(self, error_type: str, context: Dict[str, Any]) -> str:
        """Calcular severidad del error"""
        if "503" in error_type or "deployment" in error_type.lower():
            return "CRITICAL"
        elif "import" in error_type.lower() or "syntax" in error_type.lower():
            return "HIGH"
        elif "indentation" in error_type.lower():
            return "HIGH"
        else:
            return "MEDIUM"
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Obtener resumen de errores críticos"""
        with self.lock:
            return {
                "total_critical_errors": len(self.critical_errors),
                "error_patterns": dict(self.error_patterns),
                "recent_errors": list(self.critical_errors)[-10:],  # Últimos 10 errores
                "deployment_failures": len(self.deployment_failures),
                "service_503_errors": len(self.service_503_errors)
            }
    
    def get_deployment_failures(self) -> List[Dict[str, Any]]:
        """Obtener fallos de despliegue"""
        with self.lock:
            return list(self.deployment_failures)
    
    def get_503_errors(self) -> List[Dict[str, Any]]:
        """Obtener errores 503"""
        with self.lock:
            return list(self.service_503_errors)

# Instancia global del monitor
critical_monitor = CriticalErrorMonitor()

# ============================================
# ENDPOINTS DE MONITOREO
# ============================================

@router.get("/critical-errors/summary")
async def get_critical_errors_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener resumen de errores críticos"""
    try:
        summary = critical_monitor.get_error_summary()
        return {
            "success": True,
            "data": summary,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error obteniendo resumen de errores críticos: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.get("/critical-errors/deployment-failures")
async def get_deployment_failures(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener fallos de despliegue"""
    try:
        failures = critical_monitor.get_deployment_failures()
        return {
            "success": True,
            "data": failures,
            "count": len(failures),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error obteniendo fallos de despliegue: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.get("/critical-errors/503-errors")
async def get_503_errors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener errores 503"""
    try:
        errors = critical_monitor.get_503_errors()
        return {
            "success": True,
            "data": errors,
            "count": len(errors),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error obteniendo errores 503: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.post("/critical-errors/log")
async def log_critical_error(
    error_type: str,
    error_message: str,
    context: Dict[str, Any] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Registrar un error crítico"""
    try:
        critical_monitor.log_critical_error(
            error_type=error_type,
            error_message=error_message,
            context=context or {}
        )
        
        return {
            "success": True,
            "message": "Error crítico registrado",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error registrando error crítico: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.get("/critical-errors/health")
async def critical_errors_health():
    """Verificar salud del sistema de monitoreo de errores críticos"""
    try:
        summary = critical_monitor.get_error_summary()
        
        # Determinar estado de salud
        total_errors = summary["total_critical_errors"]
        if total_errors == 0:
            health_status = "HEALTHY"
        elif total_errors < 5:
            health_status = "WARNING"
        else:
            health_status = "CRITICAL"
        
        return {
            "success": True,
            "health_status": health_status,
            "total_critical_errors": total_errors,
            "error_patterns": summary["error_patterns"],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error verificando salud del sistema: {e}")
        return {
            "success": False,
            "health_status": "ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }