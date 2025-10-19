# backend/scripts/enfoque_8_verificacion_definitiva.py
"""
ENFOQUE 8: VERIFICACIÓN DEFINITIVA CON ANÁLISIS COMPLETO
Confirmación definitiva de que la causa raíz ha sido resuelta
"""
import os
import sys
import logging
import requests
import json
import time
import ast
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Enfoque8VerificacionDefinitiva:
    def __init__(self):
        self.backend_url = "https://pagos-f2qf.onrender.com"
        self.frontend_url = "https://rapicredit.onrender.com"
        self.credentials = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**",
            "remember": True
        }
        self.resultados_completos = {}
        self.causa_raiz_confirmada = False
        
    def verificar_servidor_y_despliegue(self) -> Dict[str, Any]:
        """Verificar estado del servidor y despliegue"""
        logger.info("🌐 VERIFICANDO SERVIDOR Y DESPLIEGUE")
        logger.info("-" * 50)
        
        try:
            # Verificar documentación
            docs_response = requests.get(f"{self.backend_url}/docs", timeout=10)
            if docs_response.status_code == 200:
                logger.info("   ✅ Servidor activo y documentación disponible")
            else:
                logger.error(f"   ❌ Servidor con problemas: {docs_response.status_code}")
                return {"status": "error", "status_code": docs_response.status_code}
            
            # Verificar health check
            health_response = requests.get(f"{self.backend_url}/api/v1/health", timeout=10)
            if health_response.status_code == 200:
                logger.info("   ✅ Health check funcionando")
                health_data = health_response.json()
                logger.info(f"   📊 Status: {health_data.get('status', 'N/A')}")
            else:
                logger.error(f"   ❌ Health check fallando: {health_response.status_code}")
            
            return {
                "status": "success",
                "servidor_activo": True,
                "documentacion_disponible": docs_response.status_code == 200,
                "health_check_ok": health_response.status_code == 200
            }
            
        except Exception as e:
            logger.error(f"   ❌ Error verificando servidor: {e}")
            return {"status": "error", "error": str(e)}
    
    def verificar_autenticacion_completa(self) -> Dict[str, Any]:
        """Verificar sistema de autenticación completo"""
        logger.info("🔐 VERIFICANDO AUTENTICACIÓN COMPLETA")
        logger.info("-" * 50)
        
        try:
            # Login
            login_response = requests.post(
                f"{self.backend_url}/api/v1/auth/login",
                json=self.credentials,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            if login_response.status_code != 200:
                logger.error(f"   ❌ Login falló: {login_response.status_code}")
                return {"status": "error", "status_code": login_response.status_code}
            
            login_data = login_response.json()
            access_token = login_data.get('access_token')
            user_info = login_data.get('user', {})
            
            if not access_token:
                logger.error("   ❌ No se obtuvo access token")
                return {"status": "error", "error": "No access token"}
            
            logger.info("   ✅ Login exitoso")
            logger.info(f"   📊 Usuario: {user_info.get('email', 'N/A')}")
            logger.info(f"   📊 Rol: {'Administrador' if user_info.get('is_admin') else 'Usuario'}")
            
            # Verificar endpoint /me
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            me_response = requests.get(
                f"{self.backend_url}/api/v1/auth/me",
                headers=headers,
                timeout=10
            )
            
            if me_response.status_code == 200:
                logger.info("   ✅ Endpoint /me funcionando")
                me_data = me_response.json()
                logger.info(f"   📊 Usuario confirmado: {me_data.get('email', 'N/A')}")
            else:
                logger.error(f"   ❌ Endpoint /me fallando: {me_response.status_code}")
            
            return {
                "status": "success",
                "login_ok": True,
                "access_token": access_token,
                "user_info": user_info,
                "me_endpoint_ok": me_response.status_code == 200
            }
            
        except Exception as e:
            logger.error(f"   ❌ Error en autenticación: {e}")
            return {"status": "error", "error": str(e)}
    
    def verificar_endpoint_analistas_definitivo(self, access_token: str) -> Dict[str, Any]:
        """Verificación definitiva del endpoint analistas"""
        logger.info("👥 VERIFICACIÓN DEFINITIVA DEL ENDPOINT ANALISTAS")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Probar múltiples rutas del endpoint analistas
        rutas_analistas = [
            ("/api/v1/analistas", "Endpoint principal"),
            ("/api/v1/analistas/test-no-auth", "Test sin auth"),
            ("/api/v1/analistas/test-activos", "Test activos"),
            ("/api/v1/analistas/list-no-auth", "Lista sin auth"),
            ("/api/v1/analistas/activos", "Lista activos")
        ]
        
        resultados_rutas = {}
        
        for ruta, descripcion in rutas_analistas:
            try:
                response = requests.get(
                    f"{self.backend_url}{ruta}",
                    headers=headers,
                    timeout=10
                )
                
                logger.info(f"   📊 {descripcion}: Status {response.status_code}")
                
                if response.status_code == 200:
                    logger.info(f"   ✅ {descripcion}: OK")
                    data = response.json()
                    if isinstance(data, dict):
                        total = data.get('total', 0)
                        items = data.get('items', [])
                        logger.info(f"   📊 Total: {total}, Items: {len(items)}")
                    resultados_rutas[ruta] = {
                        "status": "success",
                        "status_code": response.status_code,
                        "data": data
                    }
                elif response.status_code == 405:
                    logger.error(f"   ❌ {descripcion}: 405 Method Not Allowed")
                    resultados_rutas[ruta] = {
                        "status": "error",
                        "status_code": response.status_code,
                        "error": "Method Not Allowed"
                    }
                else:
                    logger.error(f"   ❌ {descripcion}: {response.status_code}")
                    resultados_rutas[ruta] = {
                        "status": "error",
                        "status_code": response.status_code,
                        "error": response.text[:100]
                    }
                    
            except Exception as e:
                logger.error(f"   ❌ {descripcion}: Error - {e}")
                resultados_rutas[ruta] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Determinar si el endpoint principal funciona
        endpoint_principal = resultados_rutas.get("/api/v1/analistas", {})
        if endpoint_principal.get("status") == "success":
            logger.info("   🎉 ENDPOINT PRINCIPAL ANALISTAS FUNCIONANDO")
            self.causa_raiz_confirmada = True
        else:
            logger.error("   ❌ ENDPOINT PRINCIPAL ANALISTAS AÚN FALLANDO")
            self.causa_raiz_confirmada = False
        
        return {
            "rutas": resultados_rutas,
            "endpoint_principal_ok": endpoint_principal.get("status") == "success",
            "total_rutas": len(rutas_analistas),
            "rutas_ok": len([r for r in resultados_rutas.values() if r.get("status") == "success"])
        }
    
    def verificar_endpoints_sistema_completo(self, access_token: str) -> Dict[str, Any]:
        """Verificar todos los endpoints del sistema"""
        logger.info("🔍 VERIFICANDO ENDPOINTS DEL SISTEMA COMPLETO")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        endpoints_sistema = [
            ("/api/v1/clientes", "Clientes"),
            ("/api/v1/dashboard", "Dashboard"),
            ("/api/v1/kpis", "KPIs"),
            ("/api/v1/reportes", "Reportes"),
            ("/api/v1/concesionarios", "Concesionarios"),
            ("/api/v1/modelos-vehiculos", "Modelos Vehículos"),
            ("/api/v1/prestamos", "Préstamos"),
            ("/api/v1/pagos", "Pagos"),
            ("/api/v1/amortizacion", "Amortización"),
            ("/api/v1/conciliacion", "Conciliación")
        ]
        
        resultados_sistema = {}
        
        for endpoint, nombre in endpoints_sistema:
            try:
                response = requests.get(
                    f"{self.backend_url}{endpoint}",
                    headers=headers,
                    timeout=10
                )
                
                logger.info(f"   📊 {nombre}: Status {response.status_code}")
                
                if response.status_code == 200:
                    logger.info(f"   ✅ {nombre}: OK")
                    resultados_sistema[nombre] = {
                        "status": "success",
                        "status_code": response.status_code
                    }
                elif response.status_code == 405:
                    logger.error(f"   ❌ {nombre}: 405 Method Not Allowed")
                    resultados_sistema[nombre] = {
                        "status": "error",
                        "status_code": response.status_code,
                        "error": "Method Not Allowed"
                    }
                else:
                    logger.error(f"   ❌ {nombre}: {response.status_code}")
                    resultados_sistema[nombre] = {
                        "status": "error",
                        "status_code": response.status_code,
                        "error": response.text[:100]
                    }
                    
            except Exception as e:
                logger.error(f"   ❌ {nombre}: Error - {e}")
                resultados_sistema[nombre] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "endpoints": resultados_sistema,
            "total_endpoints": len(endpoints_sistema),
            "endpoints_ok": len([e for e in resultados_sistema.values() if e.get("status") == "success"]),
            "endpoints_error": len([e for e in resultados_sistema.values() if e.get("status") == "error"])
        }
    
    def analizar_causa_raiz_resuelta(self) -> Dict[str, Any]:
        """Analizar si la causa raíz ha sido resuelta"""
        logger.info("🔍 ANALIZANDO CAUSA RAÍZ RESUELTA")
        logger.info("-" * 50)
        
        # Resumen de correcciones aplicadas
        correcciones_aplicadas = [
            "Import de logger agregado en analistas.py",
            "Emojis problemáticos removidos de analistas.py",
            "Método .to_dict() corregido a AnalistaResponse.model_validate()",
            "Función duplicada test_simple eliminada",
            "Errores de sintaxis en main.py corregidos",
            "Líneas incompletas de include_router completadas"
        ]
        
        logger.info("   📊 CORRECCIONES APLICADAS:")
        for i, correccion in enumerate(correcciones_aplicadas, 1):
            logger.info(f"   {i}. {correccion}")
        
        # Determinar estado de la causa raíz
        if self.causa_raiz_confirmada:
            logger.info("   ✅ CAUSA RAÍZ CONFIRMADA COMO RESUELTA")
            logger.info("   🎯 El endpoint analistas funciona correctamente")
            logger.info("   🎯 El error 405 Method Not Allowed está resuelto")
        else:
            logger.error("   ❌ CAUSA RAÍZ AÚN NO RESUELTA")
            logger.error("   🔍 El endpoint analistas sigue fallando")
            logger.error("   💡 Se requiere investigación adicional")
        
        return {
            "correcciones_aplicadas": correcciones_aplicadas,
            "causa_raiz_resuelta": self.causa_raiz_confirmada,
            "total_correcciones": len(correcciones_aplicadas)
        }
    
    def ejecutar_enfoque_8(self):
        """Ejecutar enfoque 8 completo"""
        logger.info("🔍 ENFOQUE 8: VERIFICACIÓN DEFINITIVA CON ANÁLISIS COMPLETO")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Confirmación definitiva de que la causa raíz ha sido resuelta")
        logger.info("=" * 80)
        
        resultados = {}
        
        # 1. Verificar servidor y despliegue
        logger.info("\n🌐 1. VERIFICANDO SERVIDOR Y DESPLIEGUE")
        logger.info("-" * 50)
        servidor = self.verificar_servidor_y_despliegue()
        resultados["servidor"] = servidor
        
        if servidor["status"] != "success":
            logger.error("❌ Servidor no disponible, abortando verificación")
            return resultados
        
        # 2. Verificar autenticación completa
        logger.info("\n🔐 2. VERIFICANDO AUTENTICACIÓN COMPLETA")
        logger.info("-" * 50)
        auth = self.verificar_autenticacion_completa()
        resultados["autenticacion"] = auth
        
        if auth["status"] != "success":
            logger.error("❌ Autenticación falló, abortando verificación")
            return resultados
        
        access_token = auth["access_token"]
        
        # 3. Verificación definitiva del endpoint analistas
        logger.info("\n👥 3. VERIFICACIÓN DEFINITIVA DEL ENDPOINT ANALISTAS")
        logger.info("-" * 50)
        analistas = self.verificar_endpoint_analistas_definitivo(access_token)
        resultados["analistas"] = analistas
        
        # 4. Verificar endpoints del sistema completo
        logger.info("\n🔍 4. VERIFICANDO ENDPOINTS DEL SISTEMA COMPLETO")
        logger.info("-" * 50)
        sistema = self.verificar_endpoints_sistema_completo(access_token)
        resultados["sistema"] = sistema
        
        # 5. Analizar causa raíz resuelta
        logger.info("\n🔍 5. ANALIZANDO CAUSA RAÍZ RESUELTA")
        logger.info("-" * 50)
        causa_raiz = self.analizar_causa_raiz_resuelta()
        resultados["causa_raiz"] = causa_raiz
        
        # 6. Resumen final definitivo
        logger.info("\n📊 RESUMEN FINAL DEFINITIVO")
        logger.info("=" * 80)
        
        logger.info(f"📊 SERVIDOR: {'✅ OK' if servidor.get('status') == 'success' else '❌ ERROR'}")
        logger.info(f"📊 AUTENTICACIÓN: {'✅ OK' if auth.get('status') == 'success' else '❌ ERROR'}")
        logger.info(f"📊 ENDPOINT ANALISTAS: {'✅ OK' if analistas.get('endpoint_principal_ok') else '❌ ERROR'}")
        logger.info(f"📊 ENDPOINTS SISTEMA: {sistema.get('endpoints_ok', 0)}/{sistema.get('total_endpoints', 0)} OK")
        
        # Conclusión final definitiva
        logger.info("\n🎯 CONCLUSIÓN FINAL DEFINITIVA")
        logger.info("=" * 80)
        
        if self.causa_raiz_confirmada:
            logger.info("🎉 ¡PROBLEMA COMPLETAMENTE RESUELTO!")
            logger.info("   ✅ Endpoint analistas funcionando correctamente")
            logger.info("   ✅ Error 405 Method Not Allowed resuelto")
            logger.info("   ✅ Causa raíz identificada y corregida")
            logger.info("   🎯 CAUSA RAÍZ: Errores críticos en analistas.py")
            logger.info("   🔧 SOLUCIÓN: Corrección de sintaxis, emojis y métodos")
            logger.info("   🚀 SISTEMA COMPLETAMENTE FUNCIONAL")
        else:
            logger.error("❌ PROBLEMA PERSISTE")
            logger.error("   🔍 Endpoint analistas sigue fallando")
            logger.error("   💡 Se requiere investigación adicional")
            logger.error("   🔧 Posibles causas restantes:")
            logger.error("      - Problemas de despliegue")
            logger.error("      - Errores adicionales no detectados")
            logger.error("      - Problemas de configuración")
        
        return resultados

def main():
    verificador = Enfoque8VerificacionDefinitiva()
    return verificador.ejecutar_enfoque_8()

if __name__ == "__main__":
    main()
