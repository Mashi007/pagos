#!/usr/bin/env python3
"""
Script para verificar el sistema después del despliegue
Verifica que todos los endpoints funcionen correctamente con los nuevos roles
"""
import requests
import json
import time
from typing import Dict, List

class DeploymentVerifier:
    def __init__(self, base_url: str = None):
        # Intentar detectar la URL del despliegue
        self.base_url = base_url or self.detect_deployment_url()
        self.session = requests.Session()
        self.test_results = []
        
    def detect_deployment_url(self) -> str:
        """Detectar URL del despliegue"""
        possible_urls = [
            "http://localhost:8000",  # Desarrollo local
            "https://pagos-backend.onrender.com",  # Render
            "https://pagos-production.up.railway.app",  # Railway
            "https://api.rapicreditca.com",  # Producción
        ]
        
        for url in possible_urls:
            try:
                response = requests.get(f"{url}/docs", timeout=5)
                if response.status_code == 200:
                    print(f"Servidor detectado en: {url}")
                    return url
            except:
                continue
        
        print("No se pudo detectar el servidor. Usando localhost por defecto.")
        return "http://localhost:8000"
    
    def test_authentication(self) -> bool:
        """Probar autenticación con usuario Daniel"""
        print("Probando autenticación...")
        
        try:
            login_data = {
                "username": "itmaster@rapicreditca.com",
                "password": "admin123"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                data=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                
                # Configurar headers de autorización
                self.session.headers.update({
                    "Authorization": f"Bearer {token}"
                })
                
                # Verificar información del usuario
                me_response = self.session.get(f"{self.base_url}/api/v1/auth/me")
                if me_response.status_code == 200:
                    user_data = me_response.json()
                    print(f"  OK - Usuario autenticado: {user_data.get('email')}")
                    print(f"  OK - Rol: {user_data.get('rol')}")
                    print(f"  OK - Nombre: {user_data.get('full_name')}")
                    return True
                else:
                    print(f"  ERROR - Error obteniendo info del usuario: {me_response.status_code}")
                    return False
            else:
                print(f"  ERROR - Error en login: {response.status_code}")
                print(f"  Respuesta: {response.text}")
                return False
                
        except Exception as e:
            print(f"  ERROR - Error de conexión: {e}")
            return False
    
    def test_endpoint(self, method: str, endpoint: str, expected_status: int = 200) -> Dict:
        """Probar un endpoint específico"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, timeout=10)
            elif method.upper() == "POST":
                response = self.session.post(url, json={}, timeout=10)
            else:
                return {"success": False, "error": f"Método {method} no soportado"}
            
            result = {
                "method": method,
                "endpoint": endpoint,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "success": response.status_code == expected_status,
                "response_time": response.elapsed.total_seconds()
            }
            
            if response.status_code < 500:
                try:
                    result["response_data"] = response.json()
                except:
                    result["response_text"] = response.text[:200]
            else:
                result["error"] = response.text[:200]
            
            return result
            
        except Exception as e:
            return {
                "method": method,
                "endpoint": endpoint,
                "success": False,
                "error": str(e)
            }
    
    def test_core_endpoints(self):
        """Probar endpoints principales del sistema"""
        print("\nProbando endpoints principales...")
        
        endpoints = [
            # Dashboard y KPIs
            ("GET", "/api/v1/dashboard/", 200),
            ("GET", "/api/v1/dashboard/kpis", 200),
            ("GET", "/api/v1/dashboard/estadisticas", 200),
            
            # Gestión de usuarios (solo ADMIN)
            ("GET", "/api/v1/users/", 200),
            ("GET", "/api/v1/users/me", 200),
            
            # Clientes
            ("GET", "/api/v1/clientes/", 200),
            
            # Préstamos
            ("GET", "/api/v1/prestamos/", 200),
            
            # Pagos
            ("GET", "/api/v1/pagos/", 200),
            
            # Conciliación
            ("GET", "/api/v1/conciliacion/", 200),
            
            # Reportes
            ("GET", "/api/v1/reportes/", 200),
            
            # Notificaciones
            ("GET", "/api/v1/notificaciones/", 200),
            
            # Configuración
            ("GET", "/api/v1/configuracion/", 200),
            
            # Auditoría (solo ADMIN)
            ("GET", "/api/v1/auditoria/", 200),
            
            # Aprobaciones
            ("GET", "/api/v1/aprobaciones/", 200),
            
            # Carga masiva
            ("GET", "/api/v1/carga-masiva/", 200),
            
            # Scheduler
            ("GET", "/api/v1/scheduler/", 200),
            
            # Inteligencia Artificial
            ("GET", "/api/v1/ia/", 200),
            
            # Monitoreo
            ("GET", "/api/v1/monitoreo/", 200),
            
            # Validadores
            ("GET", "/api/v1/validadores/cedula/12345678", 200),
        ]
        
        successful = 0
        failed = 0
        
        for method, endpoint, expected_status in endpoints:
            print(f"  Probando {method} {endpoint}...")
            
            result = self.test_endpoint(method, endpoint, expected_status)
            self.test_results.append(result)
            
            if result["success"]:
                print(f"    OK - {result['status_code']} ({result['response_time']:.2f}s)")
                successful += 1
            else:
                print(f"    ERROR - {result['status_code']} (esperado: {expected_status})")
                if "error" in result:
                    print(f"    Detalle: {result['error']}")
                failed += 1
            
            time.sleep(0.1)  # Pausa pequeña entre requests
        
        return successful, failed
    
    def test_role_permissions(self):
        """Probar que los permisos de roles funcionen correctamente"""
        print("\nProbando permisos de roles...")
        
        # Crear usuario de prueba con rol USER
        try:
            user_data = {
                "email": "test_user@example.com",
                "password": "test123",
                "full_name": "Test User",
                "rol": "USER",
                "cargo": "Test Cargo",
                "is_active": True
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/users/",
                json=user_data
            )
            
            if response.status_code in [200, 201]:
                print("  OK - Usuario de prueba creado")
                
                # Probar login con usuario USER
                login_data = {
                    "username": "test_user@example.com",
                    "password": "test123"
                }
                
                user_session = requests.Session()
                login_response = user_session.post(
                    f"{self.base_url}/api/v1/auth/login",
                    data=login_data
                )
                
                if login_response.status_code == 200:
                    token = login_response.json().get("access_token")
                    user_session.headers.update({
                        "Authorization": f"Bearer {token}"
                    })
                    
                    # Probar que USER no puede acceder a gestión de usuarios
                    users_response = user_session.get(f"{self.base_url}/api/v1/users/")
                    if users_response.status_code == 403:
                        print("  OK - Usuario USER correctamente bloqueado de gestión de usuarios")
                    else:
                        print(f"  WARNING - Usuario USER puede acceder a gestión de usuarios: {users_response.status_code}")
                    
                    # Probar que USER puede acceder a dashboard
                    dashboard_response = user_session.get(f"{self.base_url}/api/v1/dashboard/")
                    if dashboard_response.status_code == 200:
                        print("  OK - Usuario USER puede acceder a dashboard")
                    else:
                        print(f"  ERROR - Usuario USER no puede acceder a dashboard: {dashboard_response.status_code}")
                        
                else:
                    print(f"  ERROR - No se pudo hacer login con usuario de prueba: {login_response.status_code}")
            else:
                print(f"  WARNING - No se pudo crear usuario de prueba: {response.status_code}")
                
        except Exception as e:
            print(f"  ERROR - Error probando permisos: {e}")
    
    def generate_report(self, auth_success: bool, successful: int, failed: int):
        """Generar reporte final"""
        print("\n" + "=" * 60)
        print("REPORTE DE VERIFICACIÓN POST-DESPLIEGUE")
        print("=" * 60)
        
        print(f"\nRESUMEN:")
        print(f"  URL del servidor: {self.base_url}")
        print(f"  Autenticación: {'OK' if auth_success else 'ERROR'}")
        print(f"  Endpoints exitosos: {successful}")
        print(f"  Endpoints fallidos: {failed}")
        print(f"  Tasa de éxito: {(successful/(successful+failed)*100):.1f}%" if (successful+failed) > 0 else "N/A")
        
        if failed > 0:
            print(f"\nENDPOINTS CON PROBLEMAS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['method']} {result['endpoint']}")
                    print(f"    Status: {result['status_code']} (esperado: {result['expected_status']})")
                    if "error" in result:
                        print(f"    Error: {result['error']}")
                    print()
        
        # Guardar reporte
        report_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_url": self.base_url,
            "authentication_success": auth_success,
            "total_endpoints": len(self.test_results),
            "successful_endpoints": successful,
            "failed_endpoints": failed,
            "results": self.test_results
        }
        
        filename = f"deployment_verification_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nReporte guardado en: {filename}")
        
        # Resultado final
        if auth_success and successful > 0 and failed == 0:
            print("\nRESULTADO: Sistema desplegado correctamente")
        elif auth_success and successful > failed:
            print("\nRESULTADO: Sistema funcionando con algunos problemas menores")
        else:
            print("\nRESULTADO: Sistema con problemas críticos")

def main():
    """Función principal"""
    print("VERIFICACIÓN POST-DESPLIEGUE")
    print("=" * 60)
    
    verifier = DeploymentVerifier()
    
    # Probar autenticación
    auth_success = verifier.test_authentication()
    
    if auth_success:
        # Probar endpoints principales
        successful, failed = verifier.test_core_endpoints()
        
        # Probar permisos de roles
        verifier.test_role_permissions()
        
        # Generar reporte
        verifier.generate_report(auth_success, successful, failed)
    else:
        print("\nERROR: No se pudo autenticar. Verifica las credenciales y el servidor.")
        verifier.generate_report(False, 0, 1)

if __name__ == "__main__":
    main()
