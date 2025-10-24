"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, relationship
from sqlalchemy import ForeignKey, Text, Numeric, JSON, Boolean, Enum
from fastapi import APIRouter, Depends, HTTPException, Query, status
 Sistema de Monitoreo en Tiempo Real Específico
Monitorea específicamente los momentos cuando ocurren fallos 401 intermitentes
"""

import threading

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA DE MONITOREO EN TIEMPO REAL ESPECÍFICO
# ============================================

class RealTimeSpecificMonitor:
    """Monitor específico para fallos 401 intermitentes"""

    def __init__(self):
        self.active_monitoring = False
        self.monitoring_sessions = {}  # Sesiones de monitoreo activas
        self.real_time_events = deque(maxlen=1000)  # Eventos en tiempo real
        self.failure_moments = deque(maxlen=100)    # Momentos específicos de fallo
        self.success_moments = deque(maxlen=100)    # Momentos específicos de éxito
        self.lock = threading.Lock()

    def start_specific_monitoring(self, session_id: str, target_endpoints: List[str] = None) -> Dict[str, Any]:
        """Iniciar monitoreo específico"""
        with self.lock:
            monitoring_session = {
                'session_id': session_id,
                'start_time': datetime.now(),
                'target_endpoints': target_endpoints or [],
                'status': 'active',
                'events_captured': 0,
                'failures_captured': 0,
                'successes_captured': 0
            }

            self.monitoring_sessions[session_id] = monitoring_session
            self.active_monitoring = True

            logger.info(f"🔍 Monitoreo específico iniciado: {session_id}")
            return monitoring_session

    def stop_specific_monitoring(self, session_id: str) -> Dict[str, Any]:
        """Detener monitoreo específico"""
        with self.lock:
            if session_id not in self.monitoring_sessions:
                return {'error': 'Sesión no encontrada'}

            session = self.monitoring_sessions[session_id]
            session['status'] = 'stopped'
            session['end_time'] = datetime.now()
            session['duration_seconds'] = (session['end_time'] - session['start_time']).total_seconds()

            # Si no hay más sesiones activas, detener monitoreo global
            active_sessions = [s for s in self.monitoring_sessions.values() if s['status'] == 'active']
            if not active_sessions:
                self.active_monitoring = False

            logger.info(f"⏹️ Monitoreo específico detenido: {session_id}")
            return session

    def capture_auth_event(self, event_type: str, event_data: Dict[str, Any]):
        """Capturar evento de autenticación en tiempo real"""
        if not self.active_monitoring:
            return

        with self.lock:
            event = {
                'event_id': f"rt_{len(self.real_time_events)}_{int(time.time())}",
                'event_type': event_type,
                'timestamp': datetime.now(),
                'data': event_data,
                'session_context': self._get_session_context()
            }

            self.real_time_events.append(event)

            # Actualizar contadores de sesiones activas
            for session in self.monitoring_sessions.values():
                if session['status'] == 'active':
                    session['events_captured'] += 1

                    if event_type in ['auth_failure', 'token_expired', 'validation_failed']:
                        session['failures_captured'] += 1
                        self.failure_moments.append(event)
                    elif event_type in ['auth_success', 'token_validated', 'user_authenticated']:
                        session['successes_captured'] += 1
                        self.success_moments.append(event)

            logger.debug(f"📡 Evento capturado: {event_type}")

    def _get_session_context(self) -> Dict[str, Any]:
        """Obtener contexto de sesiones activas"""
        active_sessions = [s for s in self.monitoring_sessions.values() if s['status'] == 'active']
        return {
            'active_sessions_count': len(active_sessions),
            'session_ids': [s['session_id'] for s in active_sessions],
            'total_events_captured': sum(s['events_captured'] for s in active_sessions)
        }

    def analyze_failure_moments(self) -> Dict[str, Any]:
        """Analizar momentos específicos de fallo"""
        with self.lock:
            if not self.failure_moments:
                return {'error': 'No hay momentos de fallo capturados'}

            analysis = {
                'timestamp': datetime.now().isoformat(),
                'total_failure_moments': len(self.failure_moments),
                'failure_patterns': self._analyze_failure_patterns(),
                'timing_analysis': self._analyze_failure_timing(),
                'context_analysis': self._analyze_failure_context(),
                'correlation_analysis': self._analyze_failure_correlations()
            }

            return analysis

    def _analyze_failure_patterns(self) -> Dict[str, Any]:
        """Analizar patrones en momentos de fallo"""
        failure_types = defaultdict(int)
        endpoints = defaultdict(int)
        error_messages = defaultdict(int)

        for moment in self.failure_moments:
            failure_types[moment['event_type']] += 1

            endpoint = moment['data'].get('endpoint', 'unknown')
            endpoints[endpoint] += 1

            error_msg = moment['data'].get('error_message', 'unknown')
            error_messages[error_msg] += 1

        return {
            'failure_type_distribution': dict(failure_types),
            'endpoint_distribution': dict(endpoints),
            'error_message_distribution': dict(error_messages)
        }

    def _analyze_failure_timing(self) -> Dict[str, Any]:
        """Analizar timing de momentos de fallo"""
        if len(self.failure_moments) < 2:
            return {'error': 'Datos insuficientes para análisis de timing'}

        timestamps = [moment['timestamp'] for moment in self.failure_moments]
        timestamps.sort()

        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds()
            intervals.append(interval)

        return {
            'failure_intervals_seconds': intervals,
            'avg_interval_seconds': sum(intervals) / len(intervals) if intervals else 0,
            'min_interval_seconds': min(intervals) if intervals else 0,
            'max_interval_seconds': max(intervals) if intervals else 0,
            'first_failure': timestamps[0].isoformat(),
            'last_failure': timestamps[-1].isoformat()
        }

    def _analyze_failure_context(self) -> Dict[str, Any]:
        """Analizar contexto de momentos de fallo"""
        contexts = []
        for moment in self.failure_moments:
            context = moment.get('session_context', {})
            contexts.append(context)

        if not contexts:
            return {'error': 'No hay contexto disponible'}

        return {
            'avg_active_sessions': sum(c.get('active_sessions_count', 0) for c in contexts) / len(contexts),
            'total_events_during_failures': sum(c.get('total_events_captured', 0) for c in contexts),
            'context_samples': contexts[-5:]  # Últimos 5 contextos
        }

    def _analyze_failure_correlations(self) -> Dict[str, Any]:
        """Analizar correlaciones entre fallos y éxitos"""
        if not self.success_moments:
            return {'error': 'No hay momentos de éxito para correlación'}

        # Buscar patrones de alternancia entre éxito y fallo
        all_moments = []

        for moment in self.failure_moments:
            all_moments.append({**moment, 'outcome': 'failure'})

        for moment in self.success_moments:
            all_moments.append({**moment, 'outcome': 'success'})

        all_moments.sort(key=lambda x: x['timestamp'])

        # Analizar transiciones
        transitions = []
        for i in range(len(all_moments) - 1):
            current = all_moments[i]['outcome']
            next_outcome = all_moments[i + 1]['outcome']
            if current != next_outcome:
                transitions.append({
                    'from': current,
                    'to': next_outcome,
                    'time_diff_seconds': (all_moments[i + 1]['timestamp'] - all_moments[i]['timestamp']).total_seconds()
                })

        return {
            'total_transitions': len(transitions),
            'failure_to_success_transitions': len([t for t in transitions if t['from'] == 'failure' and t['to'] == 'success']),
            'success_to_failure_transitions': len([t for t in transitions if t['from'] == 'success' and t['to'] == 'failure']),
            'avg_transition_time_seconds': sum(t['time_diff_seconds'] for t in transitions) / len(transitions) if transitions else 0
        }

    def get_real_time_status(self) -> Dict[str, Any]:
        """Obtener estado del monitoreo en tiempo real"""
        with self.lock:
            active_sessions = [s for s in self.monitoring_sessions.values() if s['status'] == 'active']

            return {
                'timestamp': datetime.now().isoformat(),
                'monitoring_active': self.active_monitoring,
                'active_sessions_count': len(active_sessions),
                'total_events_captured': len(self.real_time_events),
                'failure_moments_captured': len(self.failure_moments),
                'success_moments_captured': len(self.success_moments),
                'active_sessions': [
                    {
                        'session_id': s['session_id'],
                        'start_time': s['start_time'].isoformat(),
                        'events_captured': s['events_captured'],
                        'failures_captured': s['failures_captured'],
                        'successes_captured': s['successes_captured']
                    }
                    for s in active_sessions
                ]
            }

    def get_monitoring_session_details(self, session_id: str) -> Dict[str, Any]:
        """Obtener detalles de sesión de monitoreo específica"""
        with self.lock:
            if session_id not in self.monitoring_sessions:
                return {'error': 'Sesión no encontrada'}

            session = self.monitoring_sessions[session_id]

            # Filtrar eventos de esta sesión
            session_events = []
            for event in self.real_time_events:
                if session['start_time'] <= event['timestamp']:
                    if session['status'] == 'stopped' and hasattr(session, 'end_time'):
                        if event['timestamp'] <= session['end_time']:
                            session_events.append(event)
                    else:
                        session_events.append(event)

            return {
                'session': session,
                'events_captured': session_events[-20:],  # Últimos 20 eventos
                'total_events_in_session': len(session_events)
            }

# Instancia global del monitor específico
real_time_monitor = RealTimeSpecificMonitor()

# ============================================
# ENDPOINTS DE MONITOREO ESPECÍFICO
# ============================================

@router.post("/start-specific-monitoring")
async def start_specific_monitoring_endpoint(
    monitoring_request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔍 Iniciar monitoreo específico de fallos 401
    """
    try:
        session_id = monitoring_request.get('session_id', f"monitor_{int(time.time())}")
        target_endpoints = monitoring_request.get('target_endpoints', [])

        session = real_time_monitor.start_specific_monitoring(session_id, target_endpoints)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "monitoring_session": session
        }

    except Exception as e:
        logger.error(f"Error iniciando monitoreo específico: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.post("/stop-monitoring/{session_id}")
async def stop_specific_monitoring_endpoint(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    ⏹️ Detener monitoreo específico
    """
    try:
        session = real_time_monitor.stop_specific_monitoring(session_id)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "monitoring_session": session
        }

    except Exception as e:
        logger.error(f"Error deteniendo monitoreo específico: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.post("/capture-auth-event")
async def capture_auth_event_endpoint(
    event_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📡 Capturar evento de autenticación en tiempo real
    """
    try:
        event_type = event_data.get('event_type')
        event_details = event_data.get('event_details', {})

        if not event_type:
            raise HTTPException(status_code=400, detail="event_type requerido")

        real_time_monitor.capture_auth_event(event_type, event_details)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "captured",
            "message": "Evento capturado"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error capturando evento de autenticación: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

router.get("/failure-moments-analysis")
async def get_failure_moments_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
:
    """
    🔍 Análisis de momentos específicos de fallo
    """
    try:
        analysis = real_time_monitor.analyze_failure_moments()

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "analysis": analysis
        }

    except Exception as e:
        logger.error(f"Error analizando momentos de fallo: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

router.get("/real-time-status")
async def get_real_time_status_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
:
    """
    📊 Estado del monitoreo en tiempo real
    """
    try:
        status = real_time_monitor.get_real_time_status()

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "monitoring_status": status
        }

    except Exception as e:
        logger.error(f"Error obteniendo estado de monitoreo: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

router.get("/monitoring-session/{session_id}")
async def get_monitoring_session_details_endpoint(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
:
    """
    📋 Detalles de sesión de monitoreo específica
    """
    try:
        details = real_time_monitor.get_monitoring_session_details(session_id)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "session_details": details
        }

    except Exception as e:
        logger.error(f"Error obteniendo detalles de sesión: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }
