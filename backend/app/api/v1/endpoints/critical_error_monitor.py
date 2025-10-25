from collections import deque
"""

import logging
import threading
from collections import defaultdict, deque
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


    def __init__(self):
        self.error_patterns = defaultdict(int)
        self.critical_errors = deque(maxlen=1000)
        self.deployment_failures = deque(maxlen=100)
        self.service_503_errors = deque(maxlen=200)
        self.lock = threading.Lock()


    def log_critical_error
    ) -> None:
        """Registrar un error crítico"""
        with self.lock:
            error_record = 

            self.critical_errors.append(error_record)
            self.error_patterns[error_type] += 1

            logger.error


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
        with self.lock:
            return 


    def get_deployment_failures(self) -> List[Dict[str, Any]]:
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
async def get_critical_errors_summary
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        summary = critical_monitor.get_error_summary()
        return 
    except Exception as e:
        raise HTTPException

@router.get("/critical-errors/deployment-failures")
async def get_deployment_failures
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        failures = critical_monitor.get_deployment_failures()
        return 
    except Exception as e:
        raise HTTPException

@router.get("/critical-errors/503-errors")
async def get_503_errors
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener errores 503"""
    try:
        errors = critical_monitor.get_503_errors()
        return 
    except Exception as e:
        logger.error(f"Error obteniendo errores 503: {e}")
        raise HTTPException

async def log_critical_error
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Registrar un error crítico"""
    try:
        critical_monitor.log_critical_error

        return 
    except Exception as e:
        logger.error(f"Error registrando error crítico: {e}")
        raise HTTPException

@router.get("/critical-errors/health")
async def critical_errors_health():
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

        return 
    except Exception as e:
        logger.error(f"Error verificando salud del sistema: {e}")
        return 

"""