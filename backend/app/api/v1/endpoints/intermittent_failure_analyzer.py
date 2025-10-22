"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session, relationship
from sqlalchemy import ForeignKey, Text, Numeric, JSON, Boolean, Enum
from fastapi import APIRouter, Depends, HTTPException, Query, status
 Sistema de Análisis de Fallos Intermitentes
Identifica patrones específicos que causan fallos 401 intermitentes
"""

import threading

 create_access_token

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA DE ANÁLISIS DE FALLOS INTERMITENTES
# ============================================

class IntermittentFailureAnalyzer:
    """Analizador de fallos intermitentes específicos"""

    def __init__(self):
        self.successful_requests = deque(maxlen=1000)  # Requests exitosos
        self.failed_requests = deque(maxlen=1000)      # Requests fallidos
        self.intermittent_patterns = {}               # Patrones intermitentes
        self.lock = threading.Lock()

    def log_successful_request(self, request_data: Dict[str, Any]):
        """Registrar request exitoso"""
        with self.lock:
            request = {
                'timestamp': datetime.now(),
                'endpoint': request_data.get('endpoint'),
                'method': request_data.get('method'),
                'user_id': request_data.get('user_id'),
                'token_length': request_data.get('token_length'),
                'response_time_ms': request_data.get('response_time_ms'),
                'client_ip': request_data.get('client_ip'),
                'user_agent': request_data.get('user_agent'),
                'success': True
            }
            self.successful_requests.append(request)

            logger.debug(f"✅ Request exitoso registrado: {request['endpoint']}")

    def log_failed_request(self, request_data: Dict[str, Any]):
        """Registrar request fallido"""
        with self.lock:
            request = {
                'timestamp': datetime.now(),
                'endpoint': request_data.get('endpoint'),
                'method': request_data.get('method'),
                'user_id': request_data.get('user_id'),
                'token_length': request_data.get('token_length'),
                'error_type': request_data.get('error_type'),
                'error_message': request_data.get('error_message'),
                'client_ip': request_data.get('client_ip'),
                'user_agent': request_data.get('user_agent'),
                'success': False
            }
            self.failed_requests.append(request)

            logger.warning(f"❌ Request fallido registrado: {request['endpoint']} - {request['error_type']}")

    def analyze_intermittent_patterns(self) -> Dict[str, Any]:
        """Analizar patrones de fallos intermitentes"""
        with self.lock:
            if not self.successful_requests or not self.failed_requests:
                return {'error': 'Datos insuficientes para análisis'}

            analysis = {
                'timestamp': datetime.now().isoformat(),
                'summary': self._analyze_request_summary(),
                'intermittent_patterns': self._identify_intermittent_patterns(),
                'specific_failure_triggers': self._identify_failure_triggers(),
                'timing_analysis': self._analyze_timing_patterns(),
                'recommendations': []
            }

            return analysis

    def _analyze_request_summary(self) -> Dict[str, Any]:
        """Analizar resumen de requests"""
        successful_count = len(self.successful_requests)
        failed_count = len(self.failed_requests)
        total_count = successful_count + failed_count

        # Análisis por endpoint
        successful_endpoints = defaultdict(int)
        failed_endpoints = defaultdict(int)

        for req in self.successful_requests:
            successful_endpoints[req['endpoint']] += 1

        for req in self.failed_requests:
            failed_endpoints[req['endpoint']] += 1

        return {
            'total_requests': total_count,
            'successful_requests': successful_count,
            'failed_requests': failed_count,
            'success_rate': (successful_count / total_count * 100) if total_count > 0 else 0,
            'successful_endpoints': dict(successful_endpoints),
            'failed_endpoints': dict(failed_endpoints)
        }

    def _identify_intermittent_patterns(self) -> Dict[str, Any]:
        """Identificar patrones intermitentes específicos"""
        patterns = {
            'endpoint_intermittency': {},
            'user_specific_patterns': {},
            'timing_patterns': {},
            'token_patterns': {}
        }

        # Patrones por endpoint
        all_endpoints = set()
        for req in self.successful_requests:
            all_endpoints.add(req['endpoint'])
        for req in self.failed_requests:
            all_endpoints.add(req['endpoint'])

        for endpoint in all_endpoints:
            successful_for_endpoint = [req for req in self.successful_requests if req['endpoint'] == endpoint]
            failed_for_endpoint = [req for req in self.failed_requests if req['endpoint'] == endpoint]

            if successful_for_endpoint and failed_for_endpoint:
                patterns['endpoint_intermittency'][endpoint] = {
                    'successful_count': len(successful_for_endpoint),
                    'failed_count': len(failed_for_endpoint),
                    'intermittency_score': len(failed_for_endpoint) / (len(successful_for_endpoint) + len(failed_for_endpoint))
                }

        # Patrones por usuario
        all_users = set()
        for req in self.successful_requests:
            if req.get('user_id'):
                all_users.add(req['user_id'])
        for req in self.failed_requests:
            if req.get('user_id'):
                all_users.add(req['user_id'])

        for user_id in all_users:
            successful_for_user = [req for req in self.successful_requests if req.get('user_id') == user_id]
            failed_for_user = [req for req in self.failed_requests if req.get('user_id') == user_id]

            if successful_for_user and failed_for_user:
                patterns['user_specific_patterns'][str(user_id)] = {
                    'successful_count': len(successful_for_user),
                    'failed_count': len(failed_for_user),
                    'failure_rate': len(failed_for_user) / (len(successful_for_user) + len(failed_for_user)) * 100
                }

        return patterns

    def _identify_failure_triggers(self) -> Dict[str, Any]:
        """Identificar triggers específicos de fallo"""
        triggers = {
            'token_length_patterns': {},
            'timing_triggers': {},
            'client_patterns': {},
            'error_type_patterns': {}
        }

        # Patrones de longitud de token
        successful_token_lengths = [req.get('token_length', 0) for req in self.successful_requests if req.get('token_length')]
        failed_token_lengths = [req.get('token_length', 0) for req in self.failed_requests if req.get('token_length')]

        if successful_token_lengths and failed_token_lengths:
            triggers['token_length_patterns'] = {
                'successful_avg_length': statistics.mean(successful_token_lengths),
                'failed_avg_length': statistics.mean(failed_token_lengths),
                'length_difference': statistics.mean(successful_token_lengths) - statistics.mean(failed_token_lengths)
            }

        # Patrones de timing
        successful_times = [req.get('response_time_ms', 0) for req in self.successful_requests if req.get('response_time_ms')]
        failed_times = [req.get('response_time_ms', 0) for req in self.failed_requests if req.get('response_time_ms')]

        if successful_times and failed_times:
            triggers['timing_triggers'] = {
                'successful_avg_time': statistics.mean(successful_times),
                'failed_avg_time': statistics.mean(failed_times),
                'time_difference': statistics.mean(successful_times) - statistics.mean(failed_times)
            }

        # Patrones de cliente
        successful_ips = [req.get('client_ip') for req in self.successful_requests if req.get('client_ip')]
        failed_ips = [req.get('client_ip') for req in self.failed_requests if req.get('client_ip')]

        successful_ip_counts = defaultdict(int)
        failed_ip_counts = defaultdict(int)

        for ip in successful_ips:
            successful_ip_counts[ip] += 1
        for ip in failed_ips:
            failed_ip_counts[ip] += 1

        triggers['client_patterns'] = {
            'successful_ip_distribution': dict(successful_ip_counts),
            'failed_ip_distribution': dict(failed_ip_counts)
        }

        # Patrones de tipo de error
        error_types = defaultdict(int)
        for req in self.failed_requests:
            error_type = req.get('error_type', 'unknown')
            error_types[error_type] += 1

        triggers['error_type_patterns'] = dict(error_types)

        return triggers

    def _analyze_timing_patterns(self) -> Dict[str, Any]:
        """Analizar patrones de timing específicos"""
        # Combinar todos los requests y ordenar por tiempo
        all_requests = []

        for req in self.successful_requests:
            all_requests.append({**req, 'success': True})

        for req in self.failed_requests:
            all_requests.append({**req, 'success': False})

        all_requests.sort(key=lambda x: x['timestamp'])

        # Buscar secuencias de fallos
        failure_sequences = []
        current_sequence = []

        for req in all_requests:
            if not req['success']:
                current_sequence.append(req)
            else:
                if current_sequence:
                    failure_sequences.append(current_sequence.copy())
                    current_sequence = []

        if current_sequence:
            failure_sequences.append(current_sequence)

        # Analizar patrones temporales
        timing_analysis = {
            'total_requests_analyzed': len(all_requests),
            'failure_sequences_count': len(failure_sequences),
            'longest_failure_sequence': max([len(seq) for seq in failure_sequences]) if failure_sequences else 0,
            'average_sequence_length': statistics.mean([len(seq) for seq in failure_sequences]) if failure_sequences else 0
        }

        # Buscar patrones de recuperación
        recovery_patterns = []
        for i in range(len(all_requests) - 1):
            if not all_requests[i]['success'] and all_requests[i + 1]['success']:
                recovery_time = (all_requests[i + 1]['timestamp'] - all_requests[i]['timestamp']).total_seconds()
                recovery_patterns.append(recovery_time)

        if recovery_patterns:
            timing_analysis['recovery_patterns'] = {
                'avg_recovery_time_seconds': statistics.mean(recovery_patterns),
                'min_recovery_time_seconds': min(recovery_patterns),
                'max_recovery_time_seconds': max(recovery_patterns)
            }

        return timing_analysis

    def get_intermittent_summary(self) -> Dict[str, Any]:
        """Obtener resumen de análisis intermitente"""
        with self.lock:
            current_time = datetime.now()
            cutoff_time = current_time - timedelta(hours=1)  # Última hora

            # Filtrar requests recientes
            recent_successful = [req for req in self.successful_requests if req['timestamp'] > cutoff_time]
            recent_failed = [req for req in self.failed_requests if req['timestamp'] > cutoff_time]

            return {
                'timestamp': current_time.isoformat(),
                'summary': {
                    'recent_successful_requests': len(recent_successful),
                    'recent_failed_requests': len(recent_failed),
                    'total_successful_requests': len(self.successful_requests),
                    'total_failed_requests': len(self.failed_requests),
                    'intermittency_detected': len(recent_successful) > 0 and len(recent_failed) > 0
                },
                'recent_patterns': self._analyze_recent_patterns(recent_successful, recent_failed)
            }

    def _analyze_recent_patterns(self, recent_successful: List[Dict], recent_failed: List[Dict]) -> Dict[str, Any]:
        """Analizar patrones recientes"""
        if not recent_successful or not recent_failed:
            return {'status': 'insufficient_data'}

        # Identificar endpoints con comportamiento intermitente
        intermittent_endpoints = []

        successful_endpoints = set(req['endpoint'] for req in recent_successful)
        failed_endpoints = set(req['endpoint'] for req in recent_failed)

        common_endpoints = successful_endpoints & failed_endpoints

        for endpoint in common_endpoints:
            successful_count = len([req for req in recent_successful if req['endpoint'] == endpoint])
            failed_count = len([req for req in recent_failed if req['endpoint'] == endpoint])

            intermittent_endpoints.append({
                'endpoint': endpoint,
                'successful_count': successful_count,
                'failed_count': failed_count,
                'intermittency_ratio': failed_count / (successful_count + failed_count)
            })

        return {
            'intermittent_endpoints': intermittent_endpoints,
            'common_endpoints_count': len(common_endpoints),
            'total_endpoints_with_failures': len(failed_endpoints)
        }

# Instancia global del analizador intermitente
intermittent_analyzer = IntermittentFailureAnalyzer()

# ============================================
# ENDPOINTS DE ANÁLISIS INTERMITENTE
# ============================================

router.post("/log-successful-request")
async def log_successful_request_endpoint(
    request_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
:
    """
    ✅ Registrar request exitoso para análisis intermitente
    """
    try:
        intermittent_analyzer.log_successful_request(request_data)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "logged",
            "message": "Request exitoso registrado"
        }

    except Exception as e:
        logger.error(f"Error registrando request exitoso: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

router.post("/log-failed-request")
async def log_failed_request_endpoint(
    request_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
:
    """
    ❌ Registrar request fallido para análisis intermitente
    """
    try:
        intermittent_analyzer.log_failed_request(request_data)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "logged",
            "message": "Request fallido registrado"
        }

    except Exception as e:
        logger.error(f"Error registrando request fallido: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

router.get("/intermittent-patterns")
async def get_intermittent_patterns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
:
    """
    🔄 Análisis de patrones intermitentes
    """
    try:
        analysis = intermittent_analyzer.analyze_intermittent_patterns()

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "analysis": analysis
        }

    except Exception as e:
        logger.error(f"Error analizando patrones intermitentes: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

router.get("/intermittent-summary")
async def get_intermittent_summary_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
:
    """
    📊 Resumen de análisis intermitente
    """
    try:
        summary = intermittent_analyzer.get_intermittent_summary()

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error obteniendo resumen intermitente: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }
