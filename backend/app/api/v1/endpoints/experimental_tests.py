"""
🧪 Sistema Experimental de Tests Controlados
Reproduce el problema en condiciones controladas para identificar causa raíz
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
import logging
import uuid
import asyncio
import time
from collections import defaultdict, deque
import threading

from app.db.session import get_db
from app.models.user import User
from app.core.config import settings
from app.core.security import decode_token, create_access_token, verify_password
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA EXPERIMENTAL DE TESTS
# ============================================

class ExperimentalTestSystem:
    """Sistema experimental para reproducir problemas de autenticación"""
    
    def __init__(self):
        self.test_scenarios = {}  # Escenarios de prueba
        self.test_results = deque(maxlen=1000)  # Resultados de pruebas
        self.control_groups = {}  # Grupos de control
        self.lock = threading.Lock()
        
    def create_test_scenario(self, scenario_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Crear escenario de prueba experimental"""
        with self.lock:
            scenario = {
                'scenario_id': str(uuid.uuid4()),
                'scenario_name': scenario_name,
                'parameters': parameters,
                'created_at': datetime.now(),
                'status': 'created',
                'test_cases': [],
                'results': []
            }
            
            self.test_scenarios[scenario['scenario_id']] = scenario
            
            logger.info(f"🧪 Escenario experimental creado: {scenario_name}")
            return scenario
    
    def add_test_case(self, scenario_id: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Agregar caso de prueba a un escenario"""
        with self.lock:
            if scenario_id not in self.test_scenarios:
                raise ValueError("Escenario no encontrado")
            
            test_case_id = str(uuid.uuid4())
            test_case_data = {
                'test_case_id': test_case_id,
                'test_name': test_case.get('test_name', 'Unnamed Test'),
                'test_type': test_case.get('test_type', 'unknown'),
                'parameters': test_case.get('parameters', {}),
                'expected_result': test_case.get('expected_result'),
                'created_at': datetime.now()
            }
            
            self.test_scenarios[scenario_id]['test_cases'].append(test_case_data)
            
            return test_case_data
    
    async def execute_test_scenario(self, scenario_id: str, db: Session) -> Dict[str, Any]:
        """Ejecutar escenario de prueba completo"""
        with self.lock:
            if scenario_id not in self.test_scenarios:
                raise ValueError("Escenario no encontrado")
            
            scenario = self.test_scenarios[scenario_id]
            scenario['status'] = 'running'
            scenario['started_at'] = datetime.now()
            
            logger.info(f"🧪 Ejecutando escenario: {scenario['scenario_name']}")
            
            # Ejecutar cada caso de prueba
            test_results = []
            for test_case in scenario['test_cases']:
                try:
                    result = await self._execute_test_case(test_case, db)
                    test_results.append(result)
                except Exception as e:
                    error_result = {
                        'test_case_id': test_case['test_case_id'],
                        'test_name': test_case['test_name'],
                        'status': 'error',
                        'error': str(e),
                        'executed_at': datetime.now()
                    }
                    test_results.append(error_result)
            
            # Finalizar escenario
            scenario['status'] = 'completed'
            scenario['completed_at'] = datetime.now()
            scenario['results'] = test_results
            
            # Análisis de resultados
            analysis = self._analyze_scenario_results(scenario)
            scenario['analysis'] = analysis
            
            logger.info(f"✅ Escenario completado: {scenario['scenario_name']}")
            return scenario
    
    async def _execute_test_case(self, test_case: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """Ejecutar caso de prueba individual"""
        test_type = test_case['test_type']
        parameters = test_case['parameters']
        
        result = {
            'test_case_id': test_case['test_case_id'],
            'test_name': test_case['test_name'],
            'test_type': test_type,
            'executed_at': datetime.now(),
            'status': 'unknown',
            'data': {},
            'metrics': {}
        }
        
        try:
            if test_type == 'token_validation':
                result = await self._test_token_validation(parameters, result)
            
            elif test_type == 'user_authentication':
                result = await self._test_user_authentication(parameters, db, result)
            
            elif test_type == 'token_expiration':
                result = await self._test_token_expiration(parameters, result)
            
            elif test_type == 'permission_check':
                result = await self._test_permission_check(parameters, db, result)
            
            elif test_type == 'database_connection':
                result = await self._test_database_connection(db, result)
            
            elif test_type == 'jwt_configuration':
                result = await self._test_jwt_configuration(parameters, result)
            
            else:
                result['status'] = 'error'
                result['error'] = f"Tipo de prueba no soportado: {test_type}"
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    async def _test_token_validation(self, parameters: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Test de validación de tokens"""
        token = parameters.get('token')
        expected_valid = parameters.get('expected_valid', True)
        
        start_time = time.time()
        
        try:
            if token:
                payload = decode_token(token)
                is_valid = True
                validation_data = {
                    'payload': payload,
                    'user_id': payload.get('sub'),
                    'exp': payload.get('exp'),
                    'type': payload.get('type')
                }
            else:
                is_valid = False
                validation_data = {'error': 'No token provided'}
        except Exception as e:
            is_valid = False
            validation_data = {'error': str(e)}
        
        end_time = time.time()
        
        result['status'] = 'success' if is_valid == expected_valid else 'failed'
        result['data'] = validation_data
        result['metrics'] = {
            'validation_time_ms': (end_time - start_time) * 1000,
            'token_length': len(token) if token else 0,
            'is_valid': is_valid,
            'expected_valid': expected_valid
        }
        
        return result
    
    async def _test_user_authentication(self, parameters: Dict[str, Any], db: Session, result: Dict[str, Any]) -> Dict[str, Any]:
        """Test de autenticación de usuario"""
        user_id = parameters.get('user_id')
        email = parameters.get('email')
        
        start_time = time.time()
        
        try:
            # Buscar usuario
            if user_id:
                user = db.query(User).filter(User.id == int(user_id)).first()
            elif email:
                user = db.query(User).filter(User.email == email).first()
            else:
                user = None
            
            auth_data = {
                'user_found': user is not None,
                'user_active': user.is_active if user else False,
                'user_admin': user.is_admin if user else False,
                'user_email': user.email if user else None
            }
            
            is_valid = user is not None and user.is_active
            
        except Exception as e:
            auth_data = {'error': str(e)}
            is_valid = False
        
        end_time = time.time()
        
        result['status'] = 'success' if is_valid else 'failed'
        result['data'] = auth_data
        result['metrics'] = {
            'lookup_time_ms': (end_time - start_time) * 1000,
            'is_valid': is_valid
        }
        
        return result
    
    async def _test_token_expiration(self, parameters: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Test de expiración de tokens"""
        token = parameters.get('token')
        expected_expired = parameters.get('expected_expired', False)
        
        start_time = time.time()
        
        try:
            if token:
                payload = decode_token(token)
                exp_timestamp = payload.get('exp', 0)
                exp_time = datetime.fromtimestamp(exp_timestamp)
                current_time = datetime.now()
                
                is_expired = exp_time < current_time
                time_to_expiry = (exp_time - current_time).total_seconds()
                
                expiration_data = {
                    'exp_timestamp': exp_timestamp,
                    'exp_time': exp_time.isoformat(),
                    'current_time': current_time.isoformat(),
                    'is_expired': is_expired,
                    'time_to_expiry_seconds': time_to_expiry
                }
            else:
                is_expired = True
                expiration_data = {'error': 'No token provided'}
        
        except Exception as e:
            is_expired = True
            expiration_data = {'error': str(e)}
        
        end_time = time.time()
        
        result['status'] = 'success' if is_expired == expected_expired else 'failed'
        result['data'] = expiration_data
        result['metrics'] = {
            'check_time_ms': (end_time - start_time) * 1000,
            'is_expired': is_expired,
            'expected_expired': expected_expired
        }
        
        return result
    
    async def _test_permission_check(self, parameters: Dict[str, Any], db: Session, result: Dict[str, Any]) -> Dict[str, Any]:
        """Test de verificación de permisos"""
        user_id = parameters.get('user_id')
        required_admin = parameters.get('required_admin', False)
        
        start_time = time.time()
        
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()
            
            if user:
                has_permission = user.is_admin if required_admin else user.is_active
                permission_data = {
                    'user_found': True,
                    'user_active': user.is_active,
                    'user_admin': user.is_admin,
                    'required_admin': required_admin,
                    'has_permission': has_permission
                }
            else:
                has_permission = False
                permission_data = {
                    'user_found': False,
                    'has_permission': False
                }
        
        except Exception as e:
            has_permission = False
            permission_data = {'error': str(e)}
        
        end_time = time.time()
        
        result['status'] = 'success' if has_permission else 'failed'
        result['data'] = permission_data
        result['metrics'] = {
            'check_time_ms': (end_time - start_time) * 1000,
            'has_permission': has_permission
        }
        
        return result
    
    async def _test_database_connection(self, db: Session, result: Dict[str, Any]) -> Dict[str, Any]:
        """Test de conexión a base de datos"""
        start_time = time.time()
        
        try:
            # Test básico de conexión
            user_count = db.query(User).count()
            
            # Test de query específica
            admin_users = db.query(User).filter(User.is_admin == True).count()
            
            db_data = {
                'connection_successful': True,
                'total_users': user_count,
                'admin_users': admin_users,
                'query_time_ms': (time.time() - start_time) * 1000
            }
            
            is_successful = True
        
        except Exception as e:
            db_data = {
                'connection_successful': False,
                'error': str(e)
            }
            is_successful = False
        
        end_time = time.time()
        
        result['status'] = 'success' if is_successful else 'failed'
        result['data'] = db_data
        result['metrics'] = {
            'total_time_ms': (end_time - start_time) * 1000,
            'is_successful': is_successful
        }
        
        return result
    
    async def _test_jwt_configuration(self, parameters: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """Test de configuración JWT"""
        test_user_id = parameters.get('test_user_id', '1')
        
        start_time = time.time()
        
        try:
            # Test de creación de token
            test_token = create_access_token(
                subject=test_user_id,
                additional_claims={'type': 'access', 'test': True}
            )
            
            # Test de decodificación
            payload = decode_token(test_token)
            
            config_data = {
                'token_creation_successful': True,
                'token_decoding_successful': True,
                'token_length': len(test_token),
                'payload_keys': list(payload.keys()),
                'secret_key_length': len(settings.SECRET_KEY) if settings.SECRET_KEY else 0,
                'algorithm': 'HS256'
            }
            
            is_successful = True
        
        except Exception as e:
            config_data = {
                'token_creation_successful': False,
                'token_decoding_successful': False,
                'error': str(e)
            }
            is_successful = False
        
        end_time = time.time()
        
        result['status'] = 'success' if is_successful else 'failed'
        result['data'] = config_data
        result['metrics'] = {
            'total_time_ms': (end_time - start_time) * 1000,
            'is_successful': is_successful
        }
        
        return result
    
    def _analyze_scenario_results(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Analizar resultados del escenario"""
        results = scenario['results']
        
        if not results:
            return {'error': 'No hay resultados para analizar'}
        
        # Estadísticas básicas
        total_tests = len(results)
        successful_tests = len([r for r in results if r['status'] == 'success'])
        failed_tests = len([r for r in results if r['status'] == 'failed'])
        error_tests = len([r for r in results if r['status'] == 'error'])
        
        # Análisis por tipo de prueba
        test_type_analysis = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0, 'error': 0})
        
        for result in results:
            test_type = result['test_type']
            test_type_analysis[test_type]['total'] += 1
            test_type_analysis[test_type][result['status']] += 1
        
        # Identificar patrones problemáticos
        problematic_patterns = []
        
        for test_type, stats in test_type_analysis.items():
            if stats['failed'] > stats['success']:
                problematic_patterns.append(f"{test_type}: Más fallos que éxitos")
            
            if stats['error'] > 0:
                problematic_patterns.append(f"{test_type}: Errores de ejecución")
        
        # Recomendaciones basadas en resultados
        recommendations = []
        
        if failed_tests > successful_tests:
            recommendations.append("🔴 Más pruebas fallaron que exitosas - problema sistemático")
        
        if error_tests > 0:
            recommendations.append("🟡 Hay errores de ejecución - revisar configuración")
        
        if not problematic_patterns:
            recommendations.append("✅ Todos los patrones de prueba son normales")
        
        return {
            'summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'error_tests': error_tests,
                'success_rate': (successful_tests / total_tests * 100) if total_tests > 0 else 0
            },
            'test_type_analysis': dict(test_type_analysis),
            'problematic_patterns': problematic_patterns,
            'recommendations': recommendations
        }
    
    def get_experimental_summary(self) -> Dict[str, Any]:
        """Obtener resumen experimental general"""
        with self.lock:
            current_time = datetime.now()
            
            # Estadísticas de escenarios
            total_scenarios = len(self.test_scenarios)
            completed_scenarios = len([s for s in self.test_scenarios.values() if s['status'] == 'completed'])
            running_scenarios = len([s for s in self.test_scenarios.values() if s['status'] == 'running'])
            
            # Análisis de resultados
            all_results = []
            for scenario in self.test_scenarios.values():
                all_results.extend(scenario.get('results', []))
            
            if all_results:
                total_tests = len(all_results)
                successful_tests = len([r for r in all_results if r['status'] == 'success'])
                overall_success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
            else:
                total_tests = 0
                successful_tests = 0
                overall_success_rate = 0
            
            return {
                'timestamp': current_time.isoformat(),
                'summary': {
                    'total_scenarios': total_scenarios,
                    'completed_scenarios': completed_scenarios,
                    'running_scenarios': running_scenarios,
                    'total_tests': total_tests,
                    'successful_tests': successful_tests,
                    'overall_success_rate': overall_success_rate
                },
                'recent_scenarios': list(self.test_scenarios.values())[-5:] if self.test_scenarios else []
            }

# Instancia global del sistema experimental
experimental_system = ExperimentalTestSystem()

# ============================================
# ENDPOINTS EXPERIMENTALES
# ============================================

@router.post("/create-scenario")
async def create_test_scenario(
    scenario_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🧪 Crear escenario de prueba experimental
    """
    try:
        scenario_name = scenario_data.get('scenario_name')
        parameters = scenario_data.get('parameters', {})
        
        if not scenario_name:
            raise HTTPException(status_code=400, detail="scenario_name requerido")
        
        scenario = experimental_system.create_test_scenario(scenario_name, parameters)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "scenario": scenario
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando escenario experimental: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.post("/add-test-case/{scenario_id}")
async def add_test_case_endpoint(
    scenario_id: str,
    test_case_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📝 Agregar caso de prueba a escenario
    """
    try:
        test_case = experimental_system.add_test_case(scenario_id, test_case_data)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "test_case": test_case
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error agregando caso de prueba: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.post("/execute-scenario/{scenario_id}")
async def execute_test_scenario_endpoint(
    scenario_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🚀 Ejecutar escenario de prueba completo
    """
    try:
        scenario = await experimental_system.execute_test_scenario(scenario_id, db)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "scenario": scenario
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error ejecutando escenario experimental: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.get("/experimental-summary")
async def get_experimental_summary_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 Resumen experimental general
    """
    try:
        summary = experimental_system.get_experimental_summary()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo resumen experimental: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.get("/scenario/{scenario_id}")
async def get_scenario_details(
    scenario_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📋 Obtener detalles de escenario específico
    """
    try:
        with experimental_system.lock:
            if scenario_id not in experimental_system.test_scenarios:
                raise HTTPException(status_code=404, detail="Escenario no encontrado")
            
            scenario = experimental_system.test_scenarios[scenario_id]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "scenario": scenario
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo detalles del escenario: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }
