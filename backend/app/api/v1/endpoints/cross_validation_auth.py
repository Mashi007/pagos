from app.core.security import decode_token
from datetime import date
﻿"""Sistema de Validación Cruzada de Autenticación
Valida tokens desde múltiples perspectivas para detectar inconsistencias
"""

import hashlib
import logging
from collections import defaultdict
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request
from app.api.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================
# SISTEMA DE VALIDACIÓN CRUZADA
# ============================================


    """Validador cruzado de autenticación"""


    def __init__(self):
        self.validation_cache = {}  # Cache de validaciones
        self.validation_patterns = defaultdict(int)  # Patrones de validación


        self,
        token: str,
        request_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validación cruzada completa de un token"""
        validation_results = 
            "validations": {},
            "overall_status": "unknown",
            "confidence_score": 0.0,
            "recommendations": [],
        }

        try:
            # 1. Validación básica de JWT
            jwt_validation = self._validate_jwt_structure(token)
            validation_results["validations"]["jwt_structure"] = jwt_validation

            # 2. Validación de contenido
            content_validation = self._validate_token_content(token)
            validation_results["validations"]["token_content"] = content_validation

            # 3. Validación de contexto
            context_validation = self._validate_request_context
            )
            validation_results["validations"]["request_context"] = context_validation

            # 4. Validación de tiempo

            # 5. Validación de usuario
            user_validation = self._validate_user_consistency
            )
            validation_results["validations"]["user_consistency"] = user_validation

            # 6. Validación de seguridad
            security_validation = self._validate_security_patterns
            )
            validation_results["validations"]["security_patterns"] = security_validation

            # Calcular resultado general
            validation_results = self._calculate_overall_result
            )

            # Cachear resultado
            self.validation_cache[validation_results["token_id"]] = 
            )

            return validation_results

        except Exception as e:
            logger.error(f"Error en validación cruzada: {e}")
            validation_results["overall_status"] = "error"
            validation_results["error"] = str(e)
            return validation_results


    def _generate_token_id(self, token: str) -> str:
        """Generar ID único para el token"""
        return hashlib.sha256(token.encode()).hexdigest()[:16]


    def _validate_jwt_structure(self, token: str) -> Dict[str, Any]:
        """Validar estructura básica del JWT"""
        validation = {"status": "unknown", "details": {}, "score": 0.0}

        try:
            parts = token.split(".")
            if len(parts) != 3:
                validation["status"] = "invalid"
                validation["details"]["error"] = "Formato JWT inválido"
                return validation

            # Verificar que cada parte sea base64 válido
            for i, part in enumerate(parts):
                try:
                    import base64
                    base64.b64decode(part + "==")  # Agregar padding si es necesario
                except Exception:
                    validation["status"] = "invalid"
                    validation["details"]["error"] = f"Parte {i+1} no es base64 válido"
                    return validation

            validation["status"] = "valid"
            validation["score"] = 1.0
            validation["details"]["parts_count"] = len(parts)

        except Exception as e:
            validation["status"] = "error"
            validation["details"]["error"] = str(e)

        return validation


    def _validate_token_content(self, token: str) -> Dict[str, Any]:
        """Validar contenido del token"""
        validation = {"status": "unknown", "details": {}, "score": 0.0}

        try:
            decoded_token = decode_token(token)

            if not decoded_token:
                validation["status"] = "invalid"
                validation["details"]["error"] = "Token no válido o expirado"
                return validation

            required_fields = ["sub", "exp", "iat"]
            missing_fields = []

            for field in required_fields:
                if field not in decoded_token:
                    missing_fields.append(field)

            if missing_fields:
                validation["status"] = "invalid"
                validation["details"]["missing_fields"] = missing_fields
                return validation

            validation["status"] = "valid"
            validation["score"] = 1.0
            validation["details"]["user_id"] = decoded_token.get("sub")
            validation["details"]["expires_at"] = decoded_token.get("exp")

        except Exception as e:
            validation["status"] = "error"
            validation["details"]["error"] = str(e)

        return validation


    def _validate_request_context
    ) -> Dict[str, Any]:
        """Validar contexto de la petición"""
        validation = {"status": "unknown", "details": {}, "score": 0.0}

        try:
            decoded_token = decode_token(token)
            if not decoded_token:
                validation["status"] = "invalid"
                return validation

            # Verificar IP si está disponible
            client_ip = context.get("client_ip")
            if client_ip:
                # Aquí se podría implementar lógica de validación de IP
                validation["details"]["client_ip"] = client_ip

            # Verificar User-Agent
            user_agent = context.get("user_agent")
            if user_agent:
                validation["details"]["user_agent"] = user_agent

            validation["status"] = "valid"
            validation["score"] = 0.8  # Score moderado para contexto

        except Exception as e:
            validation["status"] = "error"
            validation["details"]["error"] = str(e)

        return validation


    def _validate_timing(self, token: str) -> Dict[str, Any]:
        """Validar timing del token"""
        validation = {"status": "unknown", "details": {}, "score": 0.0}

        try:
            decoded_token = decode_token(token)
            if not decoded_token:
                validation["status"] = "invalid"
                return validation


            # Verificar si el token ha expirado
                validation["status"] = "expired"
                return validation

            # Verificar si el token es del futuro (iat)
                validation["status"] = "invalid"
                validation["details"]["future_token"] = True
                return validation

            validation["status"] = "valid"
            validation["score"] = 1.0

        except Exception as e:
            validation["status"] = "error"
            validation["details"]["error"] = str(e)

        return validation


    def _validate_user_consistency
    ) -> Dict[str, Any]:
        """Validar consistencia del usuario"""
        validation = {"status": "unknown", "details": {}, "score": 0.0}

        try:
            decoded_token = decode_token(token)
            if not decoded_token:
                validation["status"] = "invalid"
                return validation

            user_id = decoded_token.get("sub")
            if not user_id:
                validation["status"] = "invalid"
                validation["details"]["error"] = "No se encontró user_id en el token"
                return validation

            validation["status"] = "valid"
            validation["score"] = 0.9
            validation["details"]["user_id"] = user_id

        except Exception as e:
            validation["status"] = "error"
            validation["details"]["error"] = str(e)

        return validation


    def _validate_security_patterns
    ) -> Dict[str, Any]:
        """Validar patrones de seguridad"""
        validation = {"status": "unknown", "details": {}, "score": 0.0}

        try:
            # Verificar longitud del token
            if len(token) < 100:
                validation["status"] = "suspicious"
                validation["details"]["short_token"] = True
                validation["score"] = 0.3
                return validation

            suspicious_patterns = ["admin", "test", "123456"]
            token_lower = token.lower()

            for pattern in suspicious_patterns:
                if pattern in token_lower:
                    validation["status"] = "suspicious"
                    validation["details"]["suspicious_pattern"] = pattern
                    validation["score"] = 0.5
                    return validation

            validation["status"] = "valid"
            validation["score"] = 1.0

        except Exception as e:
            validation["status"] = "error"
            validation["details"]["error"] = str(e)

        return validation


    def _calculate_overall_result
    ) -> Dict[str, Any]:
        """Calcular resultado general de la validación"""
        validations = validation_results["validations"]

        # Calcular score promedio
        scores = []
        for validation in validations.values():
            if isinstance(validation, dict) and "score" in validation:
                scores.append(validation["score"])

        if scores:
            avg_score = sum(scores) / len(scores)
            validation_results["confidence_score"] = avg_score

            # Determinar estado general
            if avg_score >= 0.9:
                validation_results["overall_status"] = "valid"
            elif avg_score >= 0.7:
                validation_results["overall_status"] = "suspicious"
            else:
                validation_results["overall_status"] = "invalid"

        # Generar recomendaciones
        recommendations = []
        for name, validation in validations.items():
            if validation.get("status") == "invalid":
                recommendations.append(f"Revisar {name}: {validation.get('details', {}).get('error', 'Error desconocido')}")

        validation_results["recommendations"] = recommendations

        return validation_results

# Instancia global del validador

# ============================================
# ENDPOINTS DE VALIDACIÓN CRUZADA
# ============================================

    request: Request,
    current_user: User = Depends(get_current_user),
):
    try:
        # Obtener token del header
        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException
            )

        token = authorization.split(" ")[1]

        # Obtener contexto de la petición
        context = 
        }

        # Realizar validación cruzada

        return 
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en validación cruzada: {e}")
        raise HTTPException
            detail=f"Error interno: {str(e)}"
        )

@router.get("/validation-history")
async def get_validation_history
    current_user: User = Depends(get_current_user),
):
    """Obtener historial de validaciones"""
    try:
        with auth_checker.lock if hasattr(auth_checker, 'lock') else None:
            history = list(auth_checker.failed_validations.values())

        return 
            }
        }
    except Exception as e:
        logger.error(f"Error obteniendo historial de validaciones: {e}")
        raise HTTPException
            detail=f"Error interno: {str(e)}"
        )

@router.get("/validation-patterns")
async def get_validation_patterns
    current_user: User = Depends(get_current_user),
):
    """Obtener patrones de validación"""
    try:
        patterns = dict(auth_checker.validation_patterns)

        return 
            }
        }
    except Exception as e:
        logger.error(f"Error obteniendo patrones de validación: {e}")
        raise HTTPException
            detail=f"Error interno: {str(e)}"
        )
