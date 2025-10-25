"""Sistema de Mediciones Estratégicas
Implementa mediciones específicas para problemas identificados
"""

import logging
import os
import threading
from collections import deque
from datetime import datetime
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User

# Import condicional de psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA DE MEDICIONES ESTRATÉGICAS
# ============================================

class StrategicMeasurements:
    """Sistema de mediciones estratégicas para diagnóstico"""
    
    def __init__(self):
        self.measurements = deque(maxlen=1000)  # Mediciones almacenadas
        self.lock = threading.Lock()
        self.measurement_intervals = {
            "cpu_usage": 30,  # Cada 30 segundos
            "memory_usage": 30,
            "disk_usage": 60,  # Cada minuto
            "network_io": 30,
            "database_connections": 60,
        }
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Recopilar métricas del sistema"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": self._get_cpu_usage(),
            "memory_usage": self._get_memory_usage(),
            "disk_usage": self._get_disk_usage(),
            "network_io": self._get_network_io(),
            "database_connections": self._get_db_connections(),
        }
        
        with self.lock:
            self.measurements.append(metrics)
        
        return metrics
    
    def _get_cpu_usage(self) -> Dict[str, Any]:
        """Obtener uso de CPU"""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil no disponible"}
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            return {
                "usage_percent": cpu_percent,
                "core_count": cpu_count,
                "frequency_mhz": cpu_freq.current if cpu_freq else None,
                "status": "ok" if cpu_percent < 80 else "warning",
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Obtener uso de memoria"""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil no disponible"}
        
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": memory.percent,
                "swap_total_gb": round(swap.total / (1024**3), 2),
                "swap_used_percent": swap.percent,
                "status": "ok" if memory.percent < 80 else "warning",
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_disk_usage(self) -> Dict[str, Any]:
        """Obtener uso de disco"""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil no disponible"}
        
        try:
            disk_usage = psutil.disk_usage('/')
            
            return {
                "total_gb": round(disk_usage.total / (1024**3), 2),
                "used_gb": round(disk_usage.used / (1024**3), 2),
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "used_percent": round((disk_usage.used / disk_usage.total) * 100, 2),
                "status": "ok" if (disk_usage.free / disk_usage.total) > 0.1 else "warning",
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_network_io(self) -> Dict[str, Any]:
        """Obtener estadísticas de red"""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil no disponible"}
        
        try:
            net_io = psutil.net_io_counters()
            
            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "status": "ok",
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _get_db_connections(self) -> Dict[str, Any]:
        """Obtener estadísticas de conexiones de BD"""
        # Simulación - en un sistema real se consultaría la BD
        return {
            "active_connections": 5,
            "max_connections": 100,
            "connection_pool_size": 20,
            "status": "ok",
        }
    
    def get_measurement_history(self, limit: int = 100) -> Dict[str, Any]:
        """Obtener historial de mediciones"""
        with self.lock:
            recent_measurements = list(self.measurements)[-limit:]
            
            return {
                "measurements": recent_measurements,
                "total_count": len(self.measurements),
                "last_update": datetime.now().isoformat(),
            }

# Instancia global del sistema de mediciones
strategic_measurements = StrategicMeasurements()

# ============================================
# ENDPOINTS DE MEDICIONES ESTRATÉGICAS
# ============================================

@router.get("/measurements/system-metrics", response_model=Dict[str, Any])
async def get_system_metrics(
    current_user: User = Depends(get_current_user),
):
    """Obtener métricas del sistema"""
    metrics = strategic_measurements.collect_system_metrics()
    return metrics

@router.get("/measurements/history", response_model=Dict[str, Any])
async def get_measurement_history(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
):
    """Obtener historial de mediciones"""
    return strategic_measurements.get_measurement_history(limit)