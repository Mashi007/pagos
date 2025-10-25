"""Sistema de Monitoreo en Tiempo Real Específico
Monitorea específicamente los momentos cuando ocurren fallos 401 intermitentes
"""

import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA DE MONITOREO EN TIEMPO REAL ESPECÍFICO
# ============================================

class RealTimeSpecificMonitor:
    """Monitor específico para fallos 401 intermitentes"""
    
    def __init__(self):
        self.realtime_events = deque(maxlen=5000)  # Eventos en tiempo real
        self.failure_patterns = defaultdict(list)  # Patrones de fallo
        self.success_patterns = defaultdict(list)  # Patrones de éxito
        self.correlation_matrix = {}  # Matriz de correlación
        self.lock = threading.Lock()
        
        # Iniciar monitoreo en tiempo real
        self._start_realtime_monitoring()
    
    def _start_realtime_monitoring(self):
        """Iniciar monitoreo en tiempo real"""
        def monitoring_loop():
            while True:
                try:
                    self._analyze_realtime_patterns()
                    self._detect_intermittent_failures()
                    time.sleep(30)  # Monitorear cada 30 segundos
                except Exception as e:
                    logger.error(f"Error en monitoreo tiempo real: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=monitoring_loop, daemon=True)
        thread.start()
        logger.info("🔍 Monitor tiempo real específico iniciado")
    
    def _analyze_realtime_patterns(self):
        """Analizar patrones en tiempo real"""
        with self.lock:
            if len(self.realtime_events) < 10:
                return
            
            # Analizar eventos recientes (últimos 5 minutos)
            cutoff_time = datetime.now() - timedelta(minutes=5)
            recent_events = [
                event for event in self.realtime_events
                if event["timestamp"] >= cutoff_time
            ]
            
            # Separar eventos exitosos y fallidos
            successful_events = [e for e in recent_events if e["status"] == "success"]
            failed_events = [e for e in recent_events if e["status"] == "failure"]
            
            # Analizar patrones
            self._analyze_success_patterns(successful_events)
            self._analyze_failure_patterns(failed_events)
    
    def _analyze_success_patterns(self, events: List[Dict[str, Any]]):
        """Analizar patrones de eventos exitosos"""
        if not events:
            return
        
        # Agrupar por características comunes
        patterns = defaultdict(int)
        for event in events:
            pattern_key = f"{event['endpoint']}_{event['method']}_{event['user_type']}"
            patterns[pattern_key] += 1
        
        # Actualizar patrones de éxito
        for pattern, count in patterns.items():
            self.success_patterns[pattern].append({
                "timestamp": datetime.now(),
                "count": count,
                "events": events[:count]
            })
    
    def _analyze_failure_patterns(self, events: List[Dict[str, Any]]):
        """Analizar patrones de eventos fallidos"""
        if not events:
            return
        
        # Agrupar por características comunes
        patterns = defaultdict(int)
        for event in events:
            pattern_key = f"{event['endpoint']}_{event['method']}_{event['error_type']}"
            patterns[pattern_key] += 1
        
        # Actualizar patrones de fallo
        for pattern, count in patterns.items():
            self.failure_patterns[pattern].append({
                "timestamp": datetime.now(),
                "count": count,
                "events": events[:count]
            })
    
    def _detect_intermittent_failures(self):
        """Detectar fallos intermitentes específicos"""
        with self.lock:
            # Buscar patrones que alternan entre éxito y fallo
            for pattern_key in self.failure_patterns:
                if pattern_key in self.success_patterns:
                    failure_count = len(self.failure_patterns[pattern_key])
                    success_count = len(self.success_patterns[pattern_key])
                    
                    # Si hay tanto éxitos como fallos, es intermitente
                    if failure_count > 0 and success_count > 0:
                        logger.warning(
                            f"⚠️ Patrón intermitente detectado: {pattern_key} "
                            f"(Éxitos: {success_count}, Fallos: {failure_count})"
                        )
    
    def log_realtime_event(
        self,
        endpoint: str,
        method: str,
        status: str,
        user_type: str = None,
        error_type: str = None,
        details: Dict[str, Any] = None
    ):
        """Registrar un evento en tiempo real"""
        with self.lock:
            event = {
                "timestamp": datetime.now(),
                "endpoint": endpoint,
                "method": method,
                "status": status,
                "user_type": user_type,
                "error_type": error_type,
                "details": details or {},
            }
            self.realtime_events.append(event)
    
    def get_realtime_analysis(self) -> Dict[str, Any]:
        """Obtener análisis en tiempo real"""
        with self.lock:
            return {
                "total_events": len(self.realtime_events),
                "failure_patterns_count": len(self.failure_patterns),
                "success_patterns_count": len(self.success_patterns),
                "last_update": datetime.now().isoformat(),
            }

# Instancia global del monitor tiempo real
realtime_monitor = RealTimeSpecificMonitor()

# ============================================
# ENDPOINTS DEL MONITOR TIEMPO REAL
# ============================================

@router.post("/realtime/log-event", status_code=201)
async def log_realtime_event(
    endpoint: str,
    method: str,
    status: str,
    user_type: str = None,
    error_type: str = None,
    details: Dict[str, Any] = None,
    current_user: User = Depends(get_current_user),
):
    """Registrar un evento en tiempo real"""
    realtime_monitor.log_realtime_event(
        endpoint, method, status, user_type, error_type, details
    )
    return {"message": "Evento tiempo real registrado"}

@router.get("/realtime/analysis", response_model=Dict[str, Any])
async def get_realtime_analysis(
    current_user: User = Depends(get_current_user),
):
    """Obtener análisis en tiempo real"""
    return realtime_monitor.get_realtime_analysis()

@router.get("/realtime/patterns", response_model=Dict[str, Any])
async def get_realtime_patterns(
    current_user: User = Depends(get_current_user),
):
    """Obtener patrones detectados en tiempo real"""
    with realtime_monitor.lock:
        return {
            "failure_patterns": dict(realtime_monitor.failure_patterns),
            "success_patterns": dict(realtime_monitor.success_patterns),
            "last_update": datetime.now().isoformat(),
        }