"""Sistema Temporal de AnÃ¡lisis de TimingIdentifica problemas relacionados con tiempo y sincronizaciÃ³n"""
import logging
import statistics
import threading
import time
from collections 
import defaultdict, deque
from datetime 
import datetime, timedelta
from typing 
import Any, Dict
from fastapi 
import APIRouter, Depends, HTTPException
from sqlalchemy.orm 
import Session
from app.api.deps 
import get_current_user, get_db
from app.core.security 
import decode_token
from app.models.user 
import Userlogger = logging.getLogger(__name__)router = APIRouter()# ============================================# SISTEMA TEMPORAL DE ANÃLISIS DE TIMING# ============================================
class TemporalAnalysisSystem:
    """Sistema temporal para anÃ¡lisis de timing y sincronizaciÃ³n"""    
def __init__(self):
        self.timing_events = deque(maxlen=10000)  # Eventos de timing        self.clock_sync_data = deque(            maxlen=1000        )  # Datos de sincronizaciÃ³n de reloj        self.token_lifecycle_data = deque(            maxlen=5000        )  # Datos de ciclo de vida de tokens        self.timing_correlations = {}  # Correlaciones temporales        self.lock = threading.Lock()        # Iniciar monitoreo temporal en background        self._start_temporal_monitoring()    
def _start_temporal_monitoring(self):
        """Iniciar monitoreo temporal en background"""        
def monitoring_loop():
            while True:
                try:
                    self._collect_timing_data()                    self._analyze_timing_patterns()                    time.sleep(60)  # Monitorear cada minuto                except Exception as e:
                    logger.error(f"Error en monitoreo temporal:
 {e}")                    time.sleep(120)        thread = threading.Thread(target=monitoring_loop, daemon=True)        thread.start()        logger.info("â° Sistema temporal de anÃ¡lisis iniciado")    
def _collect_timing_data(self):
        """Recopilar datos de timing del sistema"""        with self.lock:
            current_time = datetime.now()            # Datos de sincronizaciÃ³n de reloj            clock_data = {                "timestamp":
 current_time,                "system_time":
 time.time(),                "datetime_now":
 current_time.isoformat(),                "timezone_offset":
 (                    current_time.utcoffset().total_seconds()                    if current_time.utcoffset()                    else 0                ),            }            self.clock_sync_data.append(clock_data)            # Verificar desviaciÃ³n de tiempo            if len(self.clock_sync_data) >= 2:
                prev_data = self.clock_sync_data[-2]                time_diff = (                    current_time - prev_data["timestamp"]                ).total_seconds()                expected_diff = 60.0  # Esperamos 60 segundos                if (                    abs(time_diff - expected_diff) > 5                ):
  # MÃ¡s de 5 segundos de desviaciÃ³n                    logger.warning(                        f"âš ï¸ DesviaciÃ³n de tiempo"                        + f"detectada:
 {time_diff \                        - expected_diff:
.2f} segundos"                    )    
def _analyze_timing_patterns(self):
        """Analizar patrones temporales"""        with self.lock:
            if len(self.timing_events) < 10:
                return            # Analizar patrones de timing en eventos recientes            recent_events = list(self.timing_events)[                -100:
            ]  # Ãšltimos 100 eventos            # Agrupar por tipo de evento            event_timings = defaultdict(list)            for event in recent_events:
                event_timings[event["event_type"]].append(event["timing_data"])            # Calcular estadÃ­sticas de timing por tipo            timing_stats = {}            for event_type, timings in event_timings.items():
                if timings:
                    timing_stats[event_type] = {                        "avg_duration_ms":
 statistics.mean(                            [t.get("duration_ms", 0) for t in timings]                        ),                        "min_duration_ms":
 min(                            [t.get("duration_ms", 0) for t in timings]                        ),                        "max_duration_ms":
 max(                            [t.get("duration_ms", 0) for t in timings]                        ),                        "std_deviation_ms":
 (                            statistics.stdev(                                [t.get("duration_ms", 0) for t in timings]                            )                            if len(timings) > 1                            else 0                        ),                    }            # Detectar anomalÃ­as temporales            self._detect_temporal_anomalies(timing_stats)    
def _detect_temporal_anomalies(self, timing_stats:
 Dict[str, Any]):
        """Detectar anomalÃ­as temporales"""        anomalies = []        for event_type, stats in timing_stats.items():
            avg_duration = stats["avg_duration_ms"]            std_deviation = stats["std_deviation_ms"]            # Detectar eventos que toman mucho tiempo            if avg_duration > 5000:
  # MÃ¡s de 5 segundos                anomalies.append(                    {                        "type":
 "slow_event",                        "event_type":
 event_type,                        "avg_duration_ms":
 avg_duration,                        "severity":
 (                            "high" if avg_duration > 10000 else "medium"                        ),                    }                )            # Detectar alta variabilidad en timing            if (                std_deviation > avg_duration * 0.5            ):
  # DesviaciÃ³n > 50% del promedio                anomalies.append(                    {                        "type":
 "high_variability",                        "event_type":
 event_type,                        "std_deviation_ms":
 std_deviation,                        "avg_duration_ms":
 avg_duration,                        "variability_ratio":
 std_deviation / avg_duration,                    }                )        if anomalies:
            logger.warning(                f"ðŸš¨ AnomalÃ­as temporales detectadas:
 {len(anomalies)}"            )            for anomaly in anomalies:
                logger.warning(                    f"   - {anomaly['type']}:
 {anomaly['event_type']}"                )    
def log_timing_event(        self,        event_type:
 str,        timing_data:
 Dict[str, Any],        context:
 Dict[str, Any] = None,    ):
        """Registrar evento de timing"""        with self.lock:
            event = {                "event_id":
 f"timing_{len(self.timing_events)}_{int(time.time \                ())}",                "event_type":
 event_type,                "timestamp":
 datetime.now(),                "timing_data":
 timing_data,                "context":
 context or {},            }            self.timing_events.append(event)            logger.debug(f"â° Evento temporal registrado:
 {event_type}")    
def analyze_token_timing(self, token:
 str) -> Dict[str, Any]:
        """Analizar timing especÃ­fico de un token"""        try:
            payload = decode_token(token)            # InformaciÃ³n temporal del token            iat_timestamp = payload.get("iat", 0)            exp_timestamp = payload.get("exp", 0)            current_time = datetime.now()            # Calcular tiempos            issued_time = (                datetime.fromtimestamp(iat_timestamp)                if iat_timestamp                else None            )            expires_time = (                datetime.fromtimestamp(exp_timestamp)                if exp_timestamp                else None            )            # AnÃ¡lisis temporal            timing_analysis = {                "token_timing":
 {                    "issued_at":
 (                        issued_time.isoformat() if issued_time else None                    ),                    "expires_at":
 (                        expires_time.isoformat() if expires_time else None                    ),                    "current_time":
 current_time.isoformat(),                    "age_seconds":
 (                        (current_time - issued_time).total_seconds()                        if issued_time                        else None                    ),                    "time_to_expiry_seconds":
 (                        (expires_time - current_time).total_seconds()                        if expires_time                        else None                    ),                    "is_expired":
 (                        expires_time < current_time if expires_time else None                    ),                },                "timing_issues":
 [],                "recommendations":
 [],            }            # Detectar problemas temporales            if issued_time and issued_time > current_time:
                timing_analysis["timing_issues"].append(                    {                        "issue":
 "token_from_future",                        "description":
 "Token emitido en el futuro",                        "severity":
 "critical",                    }                )            if expires_time and expires_time < current_time:
                timing_analysis["timing_issues"].append(                    {                        "issue":
 "token_expired",                        "description":
 "Token ya expirado",                        "severity":
 "high",                    }                )            if (                expires_time                and (expires_time - current_time).total_seconds() < 300            ):
                timing_analysis["timing_issues"].append(                    {                        "issue":
 "token_expiring_soon",                        "description":
 "Token expira en menos de 5 minutos",                        "severity":
 "medium",                    }                )            # Generar recomendaciones            if timing_analysis["timing_issues"]:
                timing_analysis["recommendations"].append(                    "ðŸ”„ Renovar token inmediatamente"                )            else:
                timing_analysis["recommendations"].append(                    "âœ… Timing del token es correcto"                )            return timing_analysis        except Exception as e:
            return {                "error":
 str(e),                "token_timing":
 None,                "timing_issues":
 [                    {                        "issue":
 "token_decode_error",                        "description":
 str(e),                        "severity":
 "critical",                    }                ],                "recommendations":
 ["ðŸ”§ Verificar formato del token"],            }    
def analyze_clock_synchronization(self) -> Dict[str, Any]:
        """Analizar sincronizaciÃ³n de reloj"""        with self.lock:
            if len(self.clock_sync_data) < 2:
                return {"error":
 "Datos de sincronizaciÃ³n insuficientes"}            recent_data = list(self.clock_sync_data)[                -10:
            ]  # Ãšltimos 10 registros            # Calcular desviaciones de tiempo            time_diffs = []            for i in range(1, len(recent_data)):
                prev_time = recent_data[i - 1]["timestamp"]                curr_time = recent_data[i]["timestamp"]                diff = (curr_time - prev_time).total_seconds()                time_diffs.append(diff)            # AnÃ¡lisis de sincronizaciÃ³n            sync_analysis = {                "clock_sync_status":
 "unknown",                "time_differences":
 time_diffs,                "avg_time_diff":
 (                    statistics.mean(time_diffs) if time_diffs else 0                ),                "time_diff_std":
 (                    statistics.stdev(time_diffs) if len(time_diffs) > 1 else 0                ),                "max_deviation":
 (                    max(time_diffs) - min(time_diffs) if time_diffs else 0                ),                "sync_issues":
 [],                "recommendations":
 [],            }            # Determinar estado de sincronizaciÃ³n            avg_diff = sync_analysis["avg_time_diff"]            if abs(avg_diff - 60.0) < 1.0:
  # Diferencia menor a 1 segundo                sync_analysis["clock_sync_status"] = "excellent"            elif abs(avg_diff - 60.0) < 5.0:
  # Diferencia menor a 5 segundos                sync_analysis["clock_sync_status"] = "good"            elif abs(avg_diff - 60.0) < 10.0:
  # Diferencia menor a 10 segundos                sync_analysis["clock_sync_status"] = "degraded"            else:
                sync_analysis["clock_sync_status"] = "poor"            # Detectar problemas de sincronizaciÃ³n            if sync_analysis["time_diff_std"] > 5.0:
                sync_analysis["sync_issues"].append(                    {                        "issue":
 "high_time_variability",                        "description":
 "Alta variabilidad en intervalos de    tiempo",                        "severity":
 "medium",                    }                )            if sync_analysis["max_deviation"] > 30.0:
                sync_analysis["sync_issues"].append(                    {                        "issue":
 "large_time_deviation",                        "description":
 "Gran desviaciÃ³n en intervalos de    tiempo",                        "severity":
 "high",                    }                )            # Generar recomendaciones            if sync_analysis["clock_sync_status"] == "poor":
                sync_analysis["recommendations"].append(                    "ðŸ”§ Sincronizar reloj del sistema"                )            elif sync_analysis["clock_sync_status"] == "degraded":
                sync_analysis["recommendations"].append(                    "âš ï¸ Monitorear sincronizaciÃ³n de reloj"                )            else:
                sync_analysis["recommendations"].append(                    "âœ… SincronizaciÃ³n de reloj correcta"                )            return sync_analysis    
def analyze_temporal_correlations(self) -> Dict[str, Any]:
        """Analizar correlaciones temporales"""        with self.lock:
            if len(self.timing_events) < 20:
                return {                    "error":
 "Datos de eventos insuficientes para anÃ¡lisis    de correlaciones"                }            recent_events = list(self.timing_events)[                -200:
            ]  # Ãšltimos 200 eventos            # Agrupar eventos por ventanas de tiempo            time_windows = defaultdict(list)            for event in recent_events:
                # Crear ventana de 5 minutos                window_key = event["timestamp"].replace(                    minute=(event["timestamp"].minute // 5) * 5,                    second=0,                    microsecond=0,                )                time_windows[window_key].append(event)            # Analizar correlaciones            correlations = {}            window_keys = sorted(time_windows.keys())            for i in range(len(window_keys) - 1):
                current_window = time_windows[window_keys[i]]                next_window = time_windows[window_keys[i + 1]]                # Contar tipos de eventos en cada ventana                current_types = defaultdict(int)                next_types = defaultdict(int)                for event in current_window:
                    current_types[event["event_type"]] += 1                for event in next_window:
                    next_types[event["event_type"]] += 1                # Buscar correlaciones                for event_type in current_types:
                    if event_type in next_types:
                        correlation_strength = min(                            current_types[event_type], next_types[event_type]                        ) / max(                            current_types[event_type], next_types[event_type]                        )                        if correlation_strength > 0.7:
  # CorrelaciÃ³n fuerte                            correlations[f"{event_type}_correlation"] = {                                "strength":
 correlation_strength,                                "current_count":
 current_types[event_type],                                "next_count":
 next_types[event_type],                            }            return {                "temporal_correlations":
 correlations,                "analysis_period":
 {                    "start_time":
 (                        window_keys[0].isoformat() if window_keys else None                    ),                    "end_time":
 (                        window_keys[-1].isoformat() if window_keys else None                    ),                    "total_windows":
 len(window_keys),                },                "correlation_summary":
 {                    "strong_correlations":
 len(                        [                            c                            for c in correlations.values()                            if c["strength"] > 0.8                        ]                    ),                    "medium_correlations":
 len(                        [                            c                            for c in correlations.values()                            if 0.6 < c["strength"] <= 0.8                        ]                    ),                    "weak_correlations":
 len(                        [                            c                            for c in correlations.values()                            if c["strength"] <= 0.6                        ]                    ),                },            }    
def get_temporal_summary(self) -> Dict[str, Any]:
        """Obtener resumen temporal general"""        with self.lock:
            current_time = datetime.now()            cutoff_time = current_time - timedelta(                hours=24            )  # Ãšltimas 24 horas            # Filtrar eventos recientes            recent_events = [                event                for event in self.timing_events                if event["timestamp"] > cutoff_time            ]            # EstadÃ­sticas temporales            if recent_events:
                durations = [                    event["timing_data"].get("duration_ms", 0)                    for event in recent_events                ]                avg_duration = statistics.mean(durations) if durations else 0                max_duration = max(durations) if durations else 0                min_duration = min(durations) if durations else 0            else:
                avg_duration = max_duration = min_duration = 0            # AnÃ¡lisis de sincronizaciÃ³n de reloj            clock_sync_analysis = self.analyze_clock_synchronization()            return {                "timestamp":
 current_time.isoformat(),                "summary":
 {                    "total_events_24h":
 len(recent_events),                    "avg_event_duration_ms":
 avg_duration,                    "max_event_duration_ms":
 max_duration,                    "min_event_duration_ms":
 min_duration,                    "clock_sync_status":
 clock_sync_analysis.get(                        "clock_sync_status", "unknown"                    ),                    "sync_issues_count":
 len(                        clock_sync_analysis.get("sync_issues", [])                    ),                },                "clock_sync_analysis":
 clock_sync_analysis,                "recent_timing_events":
 (                    recent_events[-10:
] if recent_events else []                ),            }# Instancia global del sistema temporaltemporal_system = TemporalAnalysisSystem()# ============================================# ENDPOINTS TEMPORALES# ============================================@router.post("/log-timing-event")async 
def log_timing_event_endpoint(    event_data:
 Dict[str, Any],    db:
 Session = Depends(get_db),    current_user:
 User = Depends(get_current_user),):
    """    â° Registrar evento de timing    """    try:
        event_type = event_data.get("event_type")        timing_data = event_data.get("timing_data", {})        context = event_data.get("context", {})        if not event_type:
            raise HTTPException(status_code=400, detail="event_type requerido")        temporal_system.log_timing_event(event_type, timing_data, context)        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "logged",            "message":
 "Evento temporal registrado",        }    except HTTPException:
        raise    except Exception as e:
        logger.error(f"Error registrando evento temporal:
 {e}")        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "error",            "error":
 str(e),        }@router.post("/analyze-token-timing")async 
def analyze_token_timing_endpoint(    token_data:
 Dict[str, str],    db:
 Session = Depends(get_db),    current_user:
 User = Depends(get_current_user),):
    """    ðŸ” Analizar timing especÃ­fico de un token    """    try:
        token = token_data.get("token")        if not token:
            raise HTTPException(status_code=400, detail="Token requerido")        analysis = temporal_system.analyze_token_timing(token)        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "success",            "analysis":
 analysis,        }    except HTTPException:
        raise    except Exception as e:
        logger.error(f"Error analizando timing de token:
 {e}")        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "error",            "error":
 str(e),        }@router.get("/clock-synchronization")async 
def get_clock_synchronization_analysis(    db:
 Session = Depends(get_db),    current_user:
 User = Depends(get_current_user),):
    """    ðŸ• AnÃ¡lisis de sincronizaciÃ³n de reloj    """    try:
        analysis = temporal_system.analyze_clock_synchronization()        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "success",            "analysis":
 analysis,        }    except Exception as e:
        logger.error(f"Error analizando sincronizaciÃ³n de reloj:
 {e}")        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "error",            "error":
 str(e),        }@router.get("/temporal-correlations")async 
def get_temporal_correlations_analysis(    db:
 Session = Depends(get_db),    current_user:
 User = Depends(get_current_user),):
    """    ðŸ”— AnÃ¡lisis de correlaciones temporales    """    try:
        analysis = temporal_system.analyze_temporal_correlations()        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "success",            "analysis":
 analysis,        }    except Exception as e:
        logger.error(f"Error analizando correlaciones temporales:
 {e}")        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "error",            "error":
 str(e),        }@router.get("/temporal-summary")async 
def get_temporal_summary_endpoint(    db:
 Session = Depends(get_db),    current_user:
 User = Depends(get_current_user),):
    """    ðŸ“Š Resumen temporal general    """    try:
        summary = temporal_system.get_temporal_summary()        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "success",            "summary":
 summary,        }    except Exception as e:
        logger.error(f"Error obteniendo resumen temporal:
 {e}")        return {            "timestamp":
 datetime.now().isoformat(),            "status":
 "error",            "error":
 str(e),        }





