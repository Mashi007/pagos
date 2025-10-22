"""
🔄 Sistema de Validación Cruzada de Autenticación
Valida tokens desde múltiples perspectivas para detectar inconsistencias
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
import logging
import hashlib
import hmac
from collections import defaultdict

from app.db.session import get_db
from app.models.user import User
from app.core.config import settings
from app.core.security import decode_token, create_access_token, verify_password
from app.api.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA DE VALIDACIÓN CRUZADA
# ============================================

class CrossValidationAuthChecker:
    """Validador cruzado de autenticación"""

    def __init__(self):
        self.validation_cache = {}  # Cache de validaciones
        self.failed_validations = defaultdict(list)  # Historial de fallos
        self.validation_patterns = defaultdict(int)  # Patrones de validación

    def cross_validate_token(self, token: str, request_context: Dict[str, Any]) -> Dict[str, Any]:
        """Validación cruzada completa de un token"""
        validation_results = {
            'timestamp': datetime.now().isoformat(),
            'token_id': self._generate_token_id(token),
            'validations': {},
            'overall_status': 'unknown',
            'confidence_score': 0.0,
            'recommendations': []
        }

        try:
            # 1. Validación básica de JWT
            jwt_validation = self._validate_jwt_structure(token)
            validation_results['validations']['jwt_structure'] = jwt_validation

            # 2. Validación de contenido
            content_validation = self._validate_token_content(token)
            validation_results['validations']['token_content'] = content_validation

            # 3. Validación de contexto
            context_validation = self._validate_request_context(token, request_context)
            validation_results['validations']['request_context'] = context_validation

            # 4. Validación de tiempo
            time_validation = self._validate_timing(token)
            validation_results['validations']['timing'] = time_validation

            # 5. Validación de usuario
            user_validation = self._validate_user_consistency(token, request_context)
            validation_results['validations']['user_consistency'] = user_validation

            # 6. Validación de seguridad
            security_validation = self._validate_security_patterns(token, request_context)
            validation_results['validations']['security_patterns'] = security_validation

            # Calcular resultado general
            validation_results = self._calculate_overall_result(validation_results)

            # Cachear resultado
            self.validation_cache[validation_results['token_id']] = validation_results

            return validation_results

        except Exception as e:
            logger.error(f"Error en validación cruzada: {e}")
            validation_results['overall_status'] = 'error'
            validation_results['error'] = str(e)
            return validation_results

    def _generate_token_id(self, token: str) -> str:
        """Generar ID único para el token"""
        return hashlib.sha256(token.encode()).hexdigest()[:16]

    def _validate_jwt_structure(self, token: str) -> Dict[str, Any]:
        """Validar estructura básica del JWT"""
        validation = {
            'status': 'unknown',
            'details': {},
            'score': 0.0
        }

        try:
            # Verificar formato básico (3 partes separadas por puntos)
            parts = token.split('.')
            if len(parts) != 3:
                validation['status'] = 'invalid'
                validation['details']['error'] = 'Formato JWT inválido'
                return validation

            # Verificar que cada parte sea base64 válido
            for i, part in enumerate(parts):
                try:
                    import base64
                    base64.urlsafe_b64decode(part + '==')  # Padding para base64
                except Exception:
                    validation['status'] = 'invalid'
                    validation['details']['error'] = f'Parte {i+1} no es base64 válido'
                    return validation

            # Intentar decodificar el payload
            try:
                payload = decode_token(token)
                validation['status'] = 'valid'
                validation['details']['payload_keys'] = list(payload.keys())
                validation['score'] = 1.0
            except Exception as e:
                validation['status'] = 'invalid'
                validation['details']['error'] = str(e)
                validation['score'] = 0.0

            return validation

        except Exception as e:
            validation['status'] = 'error'
            validation['details']['error'] = str(e)
            return validation

    def _validate_token_content(self, token: str) -> Dict[str, Any]:
        """Validar contenido del token"""
        validation = {
            'status': 'unknown',
            'details': {},
            'score': 0.0
        }

        try:
            payload = decode_token(token)

            # Verificar campos requeridos
            required_fields = ['sub', 'exp', 'type']
            missing_fields = [field for field in required_fields if field not in payload]

            if missing_fields:
                validation['status'] = 'invalid'
                validation['details']['missing_fields'] = missing_fields
                validation['score'] = 0.0
                return validation

            # Verificar tipo de token
            if payload.get('type') != 'access':
                validation['status'] = 'invalid'
                validation['details']['error'] = f'Tipo de token incorrecto: {payload.get("type")}'
                validation['score'] = 0.0
                return validation

            # Verificar formato de user_id
            user_id = payload.get('sub')
            if not user_id or not str(user_id).isdigit():
                validation['status'] = 'invalid'
                validation['details']['error'] = 'User ID inválido'
                validation['score'] = 0.0
                return validation

            # Verificar tiempo de expiración
            exp_time = datetime.fromtimestamp(payload.get('exp', 0))
            current_time = datetime.now()

            if exp_time < current_time:
                validation['status'] = 'expired'
                validation['details']['expired_at'] = exp_time.isoformat()
                validation['score'] = 0.0
            else:
                time_to_expiry = (exp_time - current_time).total_seconds()
                validation['status'] = 'valid'
                validation['details']['expires_at'] = exp_time.isoformat()
                validation['details']['time_to_expiry_minutes'] = int(time_to_expiry / 60)
                validation['score'] = 1.0

            return validation

        except Exception as e:
            validation['status'] = 'error'
            validation['details']['error'] = str(e)
            return validation

    def _validate_request_context(self, token: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validar contexto de la request"""
        validation = {
            'status': 'unknown',
            'details': {},
            'score': 0.0
        }

        try:
            payload = decode_token(token)
            user_id = payload.get('sub')

            # Verificar que el endpoint sea apropiado para el usuario
            endpoint = context.get('endpoint', '')
            method = context.get('method', '')

            # Reglas de validación de contexto
            context_rules = {
                'admin_endpoints': ['/api/v1/usuarios', '/api/v1/configuracion'],
                'user_endpoints': ['/api/v1/clientes', '/api/v1/prestamos'],
                'public_endpoints': ['/api/v1/auth/login', '/api/v1/auth/refresh']
            }

            # Verificar si el endpoint requiere admin
            is_admin_endpoint = any(admin_ep in endpoint for admin_ep in context_rules['admin_endpoints'])
            is_user_endpoint = any(user_ep in endpoint for user_ep in context_rules['user_endpoints'])
            is_public_endpoint = any(pub_ep in endpoint for pub_ep in context_rules['public_endpoints'])

            if is_admin_endpoint:
                # Verificar si el token tiene claims de admin
                is_admin = payload.get('is_admin', False)
                if not is_admin:
                    validation['status'] = 'insufficient_privileges'
                    validation['details']['error'] = 'Endpoint requiere privilegios de admin'
                    validation['score'] = 0.0
                    return validation

            # Verificar IP y User-Agent (básico)
            client_ip = context.get('client_ip', '')
            user_agent = context.get('user_agent', '')

            validation['status'] = 'valid'
            validation['details']['endpoint_type'] = 'admin' if is_admin_endpoint else 'user' if is_user_endpoint else 'public'
            validation['details']['client_ip'] = client_ip
            validation['score'] = 1.0

            return validation

        except Exception as e:
            validation['status'] = 'error'
            validation['details']['error'] = str(e)
            return validation

    def _validate_timing(self, token: str) -> Dict[str, Any]:
        """Validar aspectos temporales del token"""
        validation = {
            'status': 'unknown',
            'details': {},
            'score': 0.0
        }

        try:
            payload = decode_token(token)

            # Verificar tiempo de emisión
            iat = payload.get('iat', 0)
            if iat:
                issued_time = datetime.fromtimestamp(iat)
                current_time = datetime.now()

                # El token no puede ser del futuro
                if issued_time > current_time:
                    validation['status'] = 'invalid'
                    validation['details']['error'] = 'Token emitido en el futuro'
                    validation['score'] = 0.0
                    return validation

                # El token no puede ser muy antiguo (más de 24 horas)
                age_hours = (current_time - issued_time).total_seconds() / 3600
                if age_hours > 24:
                    validation['status'] = 'suspicious'
                    validation['details']['warning'] = f'Token muy antiguo: {age_hours:.1f} horas'
                    validation['score'] = 0.5
                else:
                    validation['status'] = 'valid'
                    validation['details']['age_hours'] = age_hours
                    validation['score'] = 1.0
            else:
                validation['status'] = 'valid'
                validation['score'] = 0.8  # Sin iat, pero no es crítico

            return validation

        except Exception as e:
            validation['status'] = 'error'
            validation['details']['error'] = str(e)
            return validation

    def _validate_user_consistency(self, token: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validar consistencia del usuario"""
        validation = {
            'status': 'unknown',
            'details': {},
            'score': 0.0
        }

        try:
            payload = decode_token(token)
            user_id = payload.get('sub')

            # Verificar que el user_id sea consistente
            if not user_id:
                validation['status'] = 'invalid'
                validation['details']['error'] = 'User ID faltante'
                validation['score'] = 0.0
                return validation

            # Verificar formato del email si está presente
            email = payload.get('email', '')
            if email and '@' not in email:
                validation['status'] = 'invalid'
                validation['details']['error'] = 'Email inválido en token'
                validation['score'] = 0.0
                return validation

            validation['status'] = 'valid'
            validation['details']['user_id'] = user_id
            validation['details']['email'] = email
            validation['score'] = 1.0

            return validation

        except Exception as e:
            validation['status'] = 'error'
            validation['details']['error'] = str(e)
            return validation

    def _validate_security_patterns(self, token: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validar patrones de seguridad"""
        validation = {
            'status': 'unknown',
            'details': {},
            'score': 0.0
        }

        try:
            payload = decode_token(token)

            # Verificar que no sea un token de prueba/test
            if 'test' in str(payload.get('sub', '')).lower():
                validation['status'] = 'suspicious'
                validation['details']['warning'] = 'Token de prueba detectado'
                validation['score'] = 0.3
                return validation

            # Verificar patrones sospechosos en el token
            token_str = str(token)
            suspicious_patterns = ['admin', 'root', 'test', 'demo']

            for pattern in suspicious_patterns:
                if pattern in token_str.lower():
                    validation['status'] = 'suspicious'
                    validation['details']['warning'] = f'Patrón sospechoso detectado: {pattern}'
                    validation['score'] = 0.5
                    return validation

            validation['status'] = 'valid'
            validation['score'] = 1.0

            return validation

        except Exception as e:
            validation['status'] = 'error'
            validation['details']['error'] = str(e)
            return validation

    def _calculate_overall_result(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calcular resultado general de la validación"""
        validations = validation_results['validations']

        # Calcular score promedio
        scores = [v.get('score', 0.0) for v in validations.values()]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Determinar estado general
        failed_validations = [k for k, v in validations.items() if v.get('status') in ['invalid', 'error']]
        suspicious_validations = [k for k, v in validations.items() if v.get('status') == 'suspicious']

        if failed_validations:
            overall_status = 'failed'
        elif suspicious_validations:
            overall_status = 'suspicious'
        elif avg_score >= 0.8:
            overall_status = 'valid'
        else:
            overall_status = 'warning'

        # Generar recomendaciones
        recommendations = []
        if 'jwt_structure' in failed_validations:
            recommendations.append('Token JWT malformado - regenerar token')
        if 'token_content' in failed_validations:
            recommendations.append('Contenido del token inválido - verificar configuración')
        if 'timing' in failed_validations:
            recommendations.append('Problema temporal - verificar sincronización de reloj')
        if 'user_consistency' in failed_validations:
            recommendations.append('Inconsistencia de usuario - verificar datos')
        if 'security_patterns' in suspicious_validations:
            recommendations.append('Patrones sospechosos - revisar seguridad')

        if not recommendations:
            recommendations.append('Token válido - no se requieren acciones')

        validation_results['overall_status'] = overall_status
        validation_results['confidence_score'] = avg_score
        validation_results['recommendations'] = recommendations

        return validation_results

# Instancia global del validador
cross_validator = CrossValidationAuthChecker()

# ============================================
# ENDPOINTS DE VALIDACIÓN CRUZADA
# ============================================

@router.post("/cross-validate")
async def cross_validate_token_endpoint(
    request: Request,
    token_data: Dict[str, str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    🔄 Validación cruzada completa de un token
    """
    try:
        token = token_data.get('token')
        if not token:
            raise HTTPException(status_code=400, detail="Token requerido")

        # Construir contexto de la request
        request_context = {
            'endpoint': str(request.url.path),
            'method': request.method,
            'client_ip': request.client.host,
            'user_agent': request.headers.get('user-agent', ''),
            'timestamp': datetime.now().isoformat()
        }

        # Realizar validación cruzada
        validation_result = cross_validator.cross_validate_token(token, request_context)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "validation": validation_result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en validación cruzada: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.get("/validation-history")
async def get_validation_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 Historial de validaciones cruzadas
    """
    try:
        # Obtener estadísticas de validación
        total_validations = len(cross_validator.validation_cache)
        failed_validations = len(cross_validator.failed_validations)

        # Patrones más comunes
        common_patterns = dict(cross_validator.validation_patterns)
        sorted_patterns = sorted(common_patterns.items(), key=lambda x: x[1], reverse=True)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "statistics": {
                "total_validations": total_validations,
                "failed_validations": failed_validations,
                "success_rate": ((total_validations - failed_validations) / total_validations * 100) if total_validations > 0 else 100,
                "common_patterns": sorted_patterns[:10]
            },
            "recent_validations": list(cross_validator.validation_cache.values())[-10:]  # Últimas 10
        }

    except Exception as e:
        logger.error(f"Error obteniendo historial de validación: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }

@router.post("/validate-user-token")
async def validate_user_token_comprehensive(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    👤 Validación cruzada completa para un usuario específico
    """
    try:
        # Verificar que el usuario existe
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Generar token de prueba para validación
        test_token = create_access_token(
            subject=str(user.id),
            additional_claims={
                'type': 'access',
                'email': user.email,
                'is_admin': user.is_admin
            }
        )

        # Contexto de prueba
        test_context = {
            'endpoint': '/api/v1/test',
            'method': 'GET',
            'client_ip': '127.0.0.1',
            'user_agent': 'Test Agent',
            'timestamp': datetime.now().isoformat()
        }

        # Realizar validación cruzada
        validation_result = cross_validator.cross_validate_token(test_token, test_context)

        return {
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "user": {
                "id": user.id,
                "email": user.email,
                "is_active": user.is_admin
            },
            "validation": validation_result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validando token del usuario: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }
