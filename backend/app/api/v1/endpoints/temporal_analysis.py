"""Sistema Temporal de Análisis de Timing
Identifica problemas relacionados con tiempo y sincronización
"""

import logging
import statistics
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.core.security import decode_token
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA TEMPORAL DE ANÁLISIS DE TIMING
# ============================================

class TemporalAnalysisSystem:
    """Sistema temporal para análisis de timing y sincronización"""
    
def __init__(self):
        self.timing_events = deque(maxlen=10000)  # Eventos de timing
        self.clock_sync_data = deque(maxlen=1000)  # Datos de sincronización de reloj
        self.token_lifecycle_data = deque(maxlen=5000)  # Datos de ciclo de vida de tokens
        self.timing_correlations = {}  # Correlaciones temporales
        self.lock = threading.Lock()
        
        # Iniciar monitoreo temporal en background
        self._start_temporal_monitoring()
    
def _start_temporal_monitoring(self):
        """Iniciar monitoreo temporal en background"""        
def monitoring_loop():
            while True:
                try:
                    self._collect_timing_data()
                    self._analyze_timing_patterns()
                    time.sleep(60)  # Monitorear cada minuto
                except Exception as e:
                    logger.error(f"Error en monitoreo temporal: {e}")
                    time.sleep(120)
        
        thread = threading.Thread(target=monitoring_loop, daemon=True)
        thread.start()
        logger.info("🕐 Sistema temporal de análisis iniciado")
    
def _collect_timing_data(self):
        """Recopilar datos de timing del sistema"""
        with self.lock:
            current_time = datetime.now()
            
            # Datos de sincronización de reloj
            clock_data = {
                "timestamp": current_time,
                "system_time": time.time(),
                "datetime_now": current_time.isoformat(),
                "timezone_offset": (
                    current_time.utcoffset().total_seconds()
                    if current_time.utcoffset()
                    else 0
                ),
            }
            self.clock_sync_data.append(clock_data)
            
            # Verificar desviación de tiempo
            if len(self.clock_sync_data) >= 2:
                prev_data = self.clock_sync_data[-2]
                time_diff = (current_time - prev_data["timestamp"]).total_seconds()
                expected_diff = 60.0  # Esperamos 60 segundos
                
                if abs(time_diff - expected_diff) > 5:  # Más de 5 segundos de desviación
                    logger.warning(
                        f"⚠️ Desviación de tiempo detectada: "
                        f"{time_diff - expected_diff:.2f} segundos"
                    )
    
def _analyze_timing_patterns(self):
        """Analizar patrones temporales"""
        with self.lock:
            if len(self.timing_events) < 10:
                return
            
            # Analizar patrones de timing en eventos recientes
            recent_events = list(self.timing_events)[-100:]  # Últimos 100 eventos
            
            # Agrupar por tipo de evento
            event_timings = defaultdict(list)
            for event in recent_events:
                event_timings[event["event_type"]].append(event["timing_data"])
            
            # Calcular estadísticas de timing por tipo
            timing_stats = {}
            for event_type, timings in event_timings.items():
                if timings:
                    timing_stats[event_type] = {
                        "avg_duration_ms": statistics.mean(
                            [t.get("duration_ms", 0) for t in timings]
                        ),
                        "min_duration_ms": min(
                            [t.get("duration_ms", 0) for t in timings]
                        ),
                        "max_duration_ms": max(
                            [t.get("duration_ms", 0) for t in timings]
                        ),
                        "std_deviation": statistics.stdev(
                            [t.get("duration_ms", 0) for t in timings]
                        ) if len(timings) > 1 else 0,
                        "count": len(timings),
                    }
            
            # Detectar anomalías temporales
            self._detect_temporal_anomalies(timing_stats)
    
    def _detect_temporal_anomalies(self, timing_stats: Dict[str, Any]):
        """Detectar anomalías temporales"""
        for event_type, stats in timing_stats.items():
            avg_duration = stats["avg_duration_ms"]
            std_deviation = stats["std_deviation"]
            
            # Si la desviación estándar es muy alta, puede indicar problemas
            if std_deviation > avg_duration * 0.5:  # Más del 50% de variación
                logger.warning(
                    f"⚠️ Alta variación temporal detectada en {event_type}: "
                    f"promedio={avg_duration:.2f}ms, desv_std={std_deviation:.2f}ms"
                )
    
    def log_timing_event(
        self, 
        event_type: str, 
        timing_data: Dict[str, Any],
        user_id: str = None
    ):
        """Registrar un evento de timing"""
        with self.lock:
            event = {
                "timestamp": datetime.now(),
                "event_type": event_type,
                "timing_data": timing_data,
                "user_id": user_id,
            }
            self.timing_events.append(event)
    
    def get_timing_analysis(self) -> Dict[str, Any]:
        """Obtener análisis de timing actual"""
        with self.lock:
            return {
                "total_events": len(self.timing_events),
                "clock_sync_samples": len(self.clock_sync_data),
                "token_lifecycle_samples": len(self.token_lifecycle_data),
                "last_update": datetime.now().isoformat(),
            }

# Instancia global del sistema temporal
temporal_analyzer = TemporalAnalysisSystem()

# ============================================
# ENDPOINTS DEL SISTEMA TEMPORAL
# ============================================

@router.post("/temporal/log-event", status_code=201)
async def log_timing_event(
    event_type: str,
    timing_data: Dict[str, Any],
    user_id: str = None,
    current_user: User = Depends(get_current_user),
):
    """Registrar un evento de timing"""
    temporal_analyzer.log_timing_event(event_type, timing_data, user_id)
    return {"message": "Evento de timing registrado"}

@router.get("/temporal/analysis", response_model=Dict[str, Any])
async def get_temporal_analysis(
    current_user: User = Depends(get_current_user),
):
    """Obtener análisis temporal actual"""
    return temporal_analyzer.get_timing_analysis()

@router.get("/temporal/clock-sync", response_model=Dict[str, Any])
async def get_clock_sync_status(
    current_user: User = Depends(get_current_user),
):
    """Obtener estado de sincronización de reloj"""
    with temporal_analyzer.lock:
        if not temporal_analyzer.clock_sync_data:
            return {"message": "No hay datos de sincronización disponibles"}
        
        latest_data = temporal_analyzer.clock_sync_data[-1]
        return {
            "latest_sync": latest_data,
            "total_samples": len(temporal_analyzer.clock_sync_data),
            "status": "synchronized",
        }