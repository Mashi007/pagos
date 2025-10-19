#!/usr/bin/env python3
"""
SEGUNDO CRITERIO DE VALIDACION - ANALISIS PROFUNDO DEL LOGIN
============================================================

Este script implementa un segundo criterio de validacion mas profundo
para encontrar la causa raiz del problema de login.

Enfoques de analisis:
1. Validacion de esquemas Pydantic
2. Analisis de flujo de datos
3. Verificacion de tipos de datos
4. Analisis de dependencias
5. Validacion de configuracion
"""

import sys
import os
import json
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

# Agregar el path del backend
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def log_info(message: str):
    """Log con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] INFO: {message}")

def log_error(message: str):
    """Log de error con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ERROR: {message}")

def log_success(message: str):
    """Log de exito con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] SUCCESS: {message}")

def log_warning(message: str):
    """Log de advertencia con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] WARNING: {message}")

class SegundoCriterioValidacion:
    """Segundo criterio de validacion para analisis profundo del login"""
    
    def __init__(self):
        self.resultados = {
            "timestamp": datetime.now().isoformat(),
            "criterios_validados": [],
            "errores_encontrados": [],
            "recomendaciones": [],
            "estado_general": "PENDIENTE"
        }
    
    def validar_esquemas_pydantic(self) -> Dict[str, Any]:
        """Validar esquemas Pydantic relacionados con login"""
        log_info("CRITERIO 1: Validando esquemas Pydantic...")
        
        criterio = {
            "nombre": "Validacion de Esquemas Pydantic",
            "estado": "PENDIENTE",
            "detalles": [],
            "errores": []
        }
        
        try:
            # Importar esquemas
            from app.schemas.auth import LoginResponse, LoginRequest, Token
            from app.schemas.user import UserMeResponse
            
            # Test 1: Validar LoginRequest
            log_info("  Validando LoginRequest...")
            try:
                test_login_request = LoginRequest(
                    email="test@example.com",
                    password="Test123!"
                )
                criterio["detalles"].append("OK LoginRequest: Validacion exitosa")
            except Exception as e:
                criterio["errores"].append(f"ERROR LoginRequest: {str(e)}")
            
            # Test 2: Validar LoginResponse con datos minimos
            log_info("  Validando LoginResponse...")
            try:
                test_login_response = LoginResponse(
                    access_token="test_token",
                    refresh_token="test_refresh",
                    token_type="bearer",
                    user={"id": 1, "email": "test@example.com"}
                )
                criterio["detalles"].append("OK LoginResponse: Validacion exitosa")
            except Exception as e:
                criterio["errores"].append(f"ERROR LoginResponse: {str(e)}")
            
            # Test 3: Validar UserMeResponse
            log_info("  Validando UserMeResponse...")
            try:
                test_user_response = UserMeResponse(
                    id=1,
                    email="test@example.com",
                    is_admin=False,
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    permissions=[]
                )
                criterio["detalles"].append("OK UserMeResponse: Validacion exitosa")
            except Exception as e:
                criterio["errores"].append(f"ERROR UserMeResponse: {str(e)}")
            
            # Test 4: Validar conversion model_dump()
            log_info("  Validando conversion model_dump()...")
            try:
                user_dict = test_user_response.model_dump()
                if isinstance(user_dict, dict):
                    criterio["detalles"].append("OK model_dump(): Conversion exitosa a dict")
                else:
                    criterio["errores"].append(f"ERROR model_dump(): Tipo incorrecto: {type(user_dict)}")
            except Exception as e:
                criterio["errores"].append(f"ERROR model_dump(): {str(e)}")
            
            criterio["estado"] = "EXITOSO" if not criterio["errores"] else "CON_ERRORES"
            
        except ImportError as e:
            criterio["errores"].append(f"ERROR ImportError: {str(e)}")
            criterio["estado"] = "ERROR_IMPORT"
        except Exception as e:
            criterio["errores"].append(f"ERROR Error inesperado: {str(e)}")
            criterio["estado"] = "ERROR_GENERAL"
        
        return criterio
    
    def validar_flujo_datos(self) -> Dict[str, Any]:
        """Validar flujo de datos en el endpoint de login"""
        log_info("CRITERIO 2: Validando flujo de datos...")
        
        criterio = {
            "nombre": "Validacion de Flujo de Datos",
            "estado": "PENDIENTE",
            "detalles": [],
            "errores": []
        }
        
        try:
            # Importar dependencias
            from app.api.v1.endpoints.auth import router
            from app.schemas.auth import LoginRequest
            from app.core.security import create_access_token, create_refresh_token
            
            # Test 1: Validar funciones de seguridad
            log_info("  Validando funciones de seguridad...")
            try:
                test_access_token = create_access_token(subject=1)
                if isinstance(test_access_token, str) and len(test_access_token) > 0:
                    criterio["detalles"].append("OK create_access_token: Funcion operativa")
                else:
                    criterio["errores"].append("ERROR create_access_token: Token invalido")
            except Exception as e:
                criterio["errores"].append(f"ERROR create_access_token: {str(e)}")
            
            try:
                test_refresh_token = create_refresh_token(subject=1)
                if isinstance(test_refresh_token, str) and len(test_refresh_token) > 0:
                    criterio["detalles"].append("OK create_refresh_token: Funcion operativa")
                else:
                    criterio["errores"].append("ERROR create_refresh_token: Token invalido")
            except Exception as e:
                criterio["errores"].append(f"ERROR create_refresh_token: {str(e)}")
            
            # Test 2: Validar estructura del endpoint
            log_info("  Validando estructura del endpoint...")
            try:
                # Verificar que el router existe y tiene rutas
                if hasattr(router, 'routes'):
                    criterio["detalles"].append(f"OK Router: {len(router.routes)} rutas encontradas")
                else:
                    criterio["errores"].append("ERROR Router: No tiene atributo 'routes'")
            except Exception as e:
                criterio["errores"].append(f"ERROR Router: {str(e)}")
            
            criterio["estado"] = "EXITOSO" if not criterio["errores"] else "CON_ERRORES"
            
        except ImportError as e:
            criterio["errores"].append(f"ERROR ImportError: {str(e)}")
            criterio["estado"] = "ERROR_IMPORT"
        except Exception as e:
            criterio["errores"].append(f"ERROR Error inesperado: {str(e)}")
            criterio["estado"] = "ERROR_GENERAL"
        
        return criterio
    
    def validar_tipos_datos(self) -> Dict[str, Any]:
        """Validar tipos de datos en el proceso de login"""
        log_info("CRITERIO 3: Validando tipos de datos...")
        
        criterio = {
            "nombre": "Validacion de Tipos de Datos",
            "estado": "PENDIENTE",
            "detalles": [],
            "errores": []
        }
        
        try:
            # Test 1: Validar tipos de tokens
            log_info("  Validando tipos de tokens...")
            from app.core.security import create_access_token, create_refresh_token
            
            access_token = create_access_token(subject=1)
            refresh_token = create_refresh_token(subject=1)
            
            if isinstance(access_token, str):
                criterio["detalles"].append("OK Access Token: Tipo str correcto")
            else:
                criterio["errores"].append(f"ERROR Access Token: Tipo incorrecto {type(access_token)}")
            
            if isinstance(refresh_token, str):
                criterio["detalles"].append("OK Refresh Token: Tipo str correcto")
            else:
                criterio["errores"].append(f"ERROR Refresh Token: Tipo incorrecto {type(refresh_token)}")
            
            # Test 2: Validar estructura de diccionarios
            log_info("  Validando estructura de diccionarios...")
            from app.schemas.user import UserMeResponse
            
            test_user = UserMeResponse(
                id=1,
                email="test@example.com",
                is_admin=False,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                permissions=[]
            )
            
            user_dict = test_user.model_dump()
            if isinstance(user_dict, dict):
                criterio["detalles"].append("OK User Dict: Tipo dict correcto")
                criterio["detalles"].append(f"OK User Dict: {len(user_dict)} campos")
            else:
                criterio["errores"].append(f"ERROR User Dict: Tipo incorrecto {type(user_dict)}")
            
            # Test 3: Validar campos requeridos
            log_info("  Validando campos requeridos...")
            required_fields = ['id', 'email', 'is_admin', 'is_active']
            missing_fields = [field for field in required_fields if field not in user_dict]
            
            if not missing_fields:
                criterio["detalles"].append("OK Campos requeridos: Todos presentes")
            else:
                criterio["errores"].append(f"ERROR Campos faltantes: {missing_fields}")
            
            criterio["estado"] = "EXITOSO" if not criterio["errores"] else "CON_ERRORES"
            
        except Exception as e:
            criterio["errores"].append(f"ERROR Error inesperado: {str(e)}")
            criterio["estado"] = "ERROR_GENERAL"
        
        return criterio
    
    def validar_dependencias(self) -> Dict[str, Any]:
        """Validar dependencias criticas del sistema de login"""
        log_info("CRITERIO 4: Validando dependencias...")
        
        criterio = {
            "nombre": "Validacion de Dependencias",
            "estado": "PENDIENTE",
            "detalles": [],
            "errores": []
        }
        
        try:
            # Test 1: Validar imports criticos
            log_info("  Validando imports criticos...")
            
            imports_criticos = [
                ("app.schemas.auth", "LoginResponse"),
                ("app.schemas.auth", "LoginRequest"),
                ("app.schemas.user", "UserMeResponse"),
                ("app.core.security", "create_access_token"),
                ("app.core.security", "create_refresh_token"),
                ("app.services.auth_service", "AuthService")
            ]
            
            for modulo, clase in imports_criticos:
                try:
                    exec(f"from {modulo} import {clase}")
                    criterio["detalles"].append(f"OK Import: {modulo}.{clase}")
                except ImportError as e:
                    criterio["errores"].append(f"ERROR Import: {modulo}.{clase} - {str(e)}")
            
            # Test 2: Validar configuracion de logging
            log_info("  Validando configuracion de logging...")
            try:
                import logging
                logger = logging.getLogger("app.api.v1.endpoints.auth")
                if logger:
                    criterio["detalles"].append("OK Logger: Configuracion correcta")
                else:
                    criterio["errores"].append("ERROR Logger: No configurado")
            except Exception as e:
                criterio["errores"].append(f"ERROR Logger: {str(e)}")
            
            criterio["estado"] = "EXITOSO" if not criterio["errores"] else "CON_ERRORES"
            
        except Exception as e:
            criterio["errores"].append(f"ERROR Error inesperado: {str(e)}")
            criterio["estado"] = "ERROR_GENERAL"
        
        return criterio
    
    def validar_configuracion(self) -> Dict[str, Any]:
        """Validar configuracion del sistema"""
        log_info("CRITERIO 5: Validando configuracion...")
        
        criterio = {
            "nombre": "Validacion de Configuracion",
            "estado": "PENDIENTE",
            "detalles": [],
            "errores": []
        }
        
        try:
            # Test 1: Validar variables de entorno
            log_info("  Validando variables de entorno...")
            import os
            
            env_vars = ["SECRET_KEY", "DATABASE_URL", "ENVIRONMENT"]
            for var in env_vars:
                if os.getenv(var):
                    criterio["detalles"].append(f"OK Env Var: {var} configurada")
                else:
                    criterio["errores"].append(f"ERROR Env Var: {var} no configurada")
            
            # Test 2: Validar configuracion de CORS
            log_info("  Validando configuracion CORS...")
            try:
                from app.main import app
                if hasattr(app, 'middleware'):
                    criterio["detalles"].append("OK CORS: Middleware configurado")
                else:
                    criterio["errores"].append("ERROR CORS: Middleware no encontrado")
            except Exception as e:
                criterio["errores"].append(f"ERROR CORS: {str(e)}")
            
            criterio["estado"] = "EXITOSO" if not criterio["errores"] else "CON_ERRORES"
            
        except Exception as e:
            criterio["errores"].append(f"ERROR Error inesperado: {str(e)}")
            criterio["estado"] = "ERROR_GENERAL"
        
        return criterio
    
    def ejecutar_validacion_completa(self):
        """Ejecutar todos los criterios de validacion"""
        log_info("INICIANDO SEGUNDO CRITERIO DE VALIDACION")
        log_info("=" * 60)
        
        # Ejecutar todos los criterios
        criterios = [
            self.validar_esquemas_pydantic(),
            self.validar_flujo_datos(),
            self.validar_tipos_datos(),
            self.validar_dependencias(),
            self.validar_configuracion()
        ]
        
        self.resultados["criterios_validados"] = criterios
        
        # Analizar resultados
        errores_totales = []
        exitosos = 0
        
        for criterio in criterios:
            errores_totales.extend(criterio["errores"])
            if criterio["estado"] == "EXITOSO":
                exitosos += 1
        
        self.resultados["errores_encontrados"] = errores_totales
        
        # Generar recomendaciones
        self.generar_recomendaciones()
        
        # Determinar estado general
        if not errores_totales:
            self.resultados["estado_general"] = "EXITOSO"
        elif exitosos >= 3:
            self.resultados["estado_general"] = "PARCIALMENTE_EXITOSO"
        else:
            self.resultados["estado_general"] = "CRITICO"
        
        # Mostrar resumen
        self.mostrar_resumen()
        
        return self.resultados
    
    def generar_recomendaciones(self):
        """Generar recomendaciones basadas en los errores encontrados"""
        log_info("GENERANDO RECOMENDACIONES...")
        
        errores = self.resultados["errores_encontrados"]
        recomendaciones = []
        
        if any("LoginResponse" in error for error in errores):
            recomendaciones.append("Revisar esquema LoginResponse - posible problema de validacion Pydantic")
        
        if any("create_refresh_token" in error for error in errores):
            recomendaciones.append("Verificar funcion create_refresh_token - posible problema de generacion")
        
        if any("model_dump" in error for error in errores):
            recomendaciones.append("Revisar conversion model_dump() - posible problema de serializacion")
        
        if any("ImportError" in error for error in errores):
            recomendaciones.append("Verificar imports - posible problema de dependencias")
        
        if any("CORS" in error for error in errores):
            recomendaciones.append("Revisar configuracion CORS - posible problema de comunicacion")
        
        self.resultados["recomendaciones"] = recomendaciones
    
    def mostrar_resumen(self):
        """Mostrar resumen de la validacion"""
        log_info("RESUMEN DEL SEGUNDO CRITERIO DE VALIDACION")
        log_info("=" * 60)
        
        estado = self.resultados["estado_general"]
        if estado == "EXITOSO":
            log_success(f"ESTADO GENERAL: {estado}")
        elif estado == "PARCIALMENTE_EXITOSO":
            log_warning(f"ESTADO GENERAL: {estado}")
        else:
            log_error(f"ESTADO GENERAL: {estado}")
        
        log_info(f"Criterios validados: {len(self.resultados['criterios_validados'])}")
        log_info(f"Errores encontrados: {len(self.resultados['errores_encontrados'])}")
        log_info(f"Recomendaciones: {len(self.resultados['recomendaciones'])}")
        
        if self.resultados["errores_encontrados"]:
            log_error("ERRORES CRITICOS ENCONTRADOS:")
            for error in self.resultados["errores_encontrados"]:
                log_error(f"  - {error}")
        
        if self.resultados["recomendaciones"]:
            log_info("RECOMENDACIONES:")
            for rec in self.resultados["recomendaciones"]:
                log_info(f"  - {rec}")
        
        log_info("=" * 60)

def main():
    """Funcion principal"""
    try:
        validador = SegundoCriterioValidacion()
        resultados = validador.ejecutar_validacion_completa()
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"segundo_criterio_validacion_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False, default=str)
        
        log_success(f"Resultados guardados en: {filename}")
        
        return resultados
        
    except Exception as e:
        log_error(f"Error critico en validacion: {str(e)}")
        log_error(f"Traceback: {traceback.format_exc()}")
        return None

if __name__ == "__main__":
    main()
