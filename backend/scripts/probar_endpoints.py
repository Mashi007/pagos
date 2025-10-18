#!/usr/bin/env python3
"""
Script para probar todos los endpoints del sistema
Verifica que todos los endpoints funcionen correctamente después de la limpieza de roles
"""
import requests
import json
import time
from typing import Dict, List, Tuple
import sys
import os

class EndpointTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        
    def login_admin(self) -> bool:
        """Iniciar sesión como administrador"""
        try:
            login_data = {
                "username": "itmaster@rapicreditca.com",
                "password": "admin123"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                data=login_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.auth_token}"
                })
                print("✅ Login exitoso como ADMIN")
                return True
            else:
                print(f"❌ Error en login: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error de conexión en login: {e}")
            return False
    
    def test_endpoint(self, method: str, endpoint: str, data: dict = None, expected_status: int = 200) -> Dict:
        """Probar un endpoint específico"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                return {"success": False, "error": f"Método {method} no soportado"}
            
            result = {
                "method": method,
                "endpoint": endpoint,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "success": response.status_code == expected_status,
                "response_time": response.elapsed.total_seconds(),
                "response_size": len(response.content)
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
    
    def test_all_endpoints(self):
        """Probar todos los endpoints del sistema"""
        print("🧪 INICIANDO PRUEBAS DE ENDPOINTS")
        print("=" * 60)
        
        # Primero hacer login
        if not self.login_admin():
            print("❌ No se pudo hacer login. Abortando pruebas.")
            return
        
        # Lista de endpoints a probar
        endpoints_to_test = [
            # Autenticación
            ("GET", "/api/v1/auth/me", None, 200),
            
            # Usuarios
            ("GET", "/api/v1/users/", None, 200),
            ("GET", "/api/v1/users/me", None, 200),
            
            # Dashboard
            ("GET", "/api/v1/dashboard/", None, 200),
            ("GET", "/api/v1/dashboard/kpis", None, 200),
            ("GET", "/api/v1/dashboard/estadisticas", None, 200),
            
            # Clientes
            ("GET", "/api/v1/clientes/", None, 200),
            ("POST", "/api/v1/clientes/", {
                "nombre": "Test Cliente",
                "apellido": "Prueba",
                "cedula": "12345678",
                "telefono": "1234567890",
                "email": "test@example.com"
            }, 201),
            
            # Préstamos
            ("GET", "/api/v1/prestamos/", None, 200),
            
            # Pagos
            ("GET", "/api/v1/pagos/", None, 200),
            
            # Conciliación
            ("GET", "/api/v1/conciliacion/", None, 200),
            
            # Reportes
            ("GET", "/api/v1/reportes/", None, 200),
            
            # Notificaciones
            ("GET", "/api/v1/notificaciones/", None, 200),
            
            # Configuración
            ("GET", "/api/v1/configuracion/", None, 200),
            
            # Auditoría
            ("GET", "/api/v1/auditoria/", None, 200),
            
            # Aprobaciones
            ("GET", "/api/v1/aprobaciones/", None, 200),
            
            # Carga masiva
            ("GET", "/api/v1/carga-masiva/", None, 200),
            
            # Scheduler
            ("GET", "/api/v1/scheduler/", None, 200),
            
            # Inteligencia Artificial
            ("GET", "/api/v1/ia/", None, 200),
            
            # Monitoreo
            ("GET", "/api/v1/monitoreo/", None, 200),
            
            # Validadores
            ("GET", "/api/v1/validadores/cedula/12345678", None, 200),
        ]
        
        print(f"📊 Probando {len(endpoints_to_test)} endpoints...")
        print()
        
        successful_tests = 0
        failed_tests = 0
        
        for method, endpoint, data, expected_status in endpoints_to_test:
            print(f"🔍 Probando {method} {endpoint}...")
            
            result = self.test_endpoint(method, endpoint, data, expected_status)
            self.test_results.append(result)
            
            if result["success"]:
                print(f"  ✅ {result['status_code']} - {result['response_time']:.2f}s")
                successful_tests += 1
            else:
                print(f"  ❌ {result['status_code']} - {result.get('error', 'Error desconocido')}")
                failed_tests += 1
            
            # Pequeña pausa entre requests
            time.sleep(0.1)
        
        self.generate_test_report(successful_tests, failed_tests)
    
    def generate_test_report(self, successful: int, failed: int):
        """Generar reporte de pruebas"""
        print("\n" + "=" * 60)
        print("📋 REPORTE DE PRUEBAS DE ENDPOINTS")
        print("=" * 60)
        
        print(f"\n📊 RESUMEN:")
        print(f"  ✅ Exitosos: {successful}")
        print(f"  ❌ Fallidos: {failed}")
        print(f"  📈 Tasa de éxito: {(successful/(successful+failed)*100):.1f}%")
        
        if failed > 0:
            print(f"\n❌ ENDPOINTS FALLIDOS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['method']} {result['endpoint']}")
                    print(f"    Status: {result['status_code']} (esperado: {result['expected_status']})")
                    if "error" in result:
                        print(f"    Error: {result['error']}")
                    print()
        
        print(f"\n✅ ENDPOINTS EXITOSOS:")
        for result in self.test_results:
            if result["success"]:
                print(f"  - {result['method']} {result['endpoint']} ({result['response_time']:.2f}s)")
        
        # Guardar reporte detallado
        self.save_detailed_report()
    
    def save_detailed_report(self):
        """Guardar reporte detallado en archivo"""
        report_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_url": self.base_url,
            "total_tests": len(self.test_results),
            "successful_tests": sum(1 for r in self.test_results if r["success"]),
            "failed_tests": sum(1 for r in self.test_results if not r["success"]),
            "results": self.test_results
        }
        
        filename = f"endpoint_test_report_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Reporte detallado guardado en: {filename}")

def main():
    """Función principal"""
    print("🚀 INICIANDO PRUEBAS DE ENDPOINTS DEL SISTEMA")
    print("=" * 60)
    
    # Verificar si el servidor está corriendo
    base_url = "http://localhost:8000"
    
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor detectado en http://localhost:8000")
        else:
            print("⚠️ Servidor responde pero puede no estar completamente funcional")
    except:
        print("❌ No se puede conectar al servidor en http://localhost:8000")
        print("💡 Asegúrate de que el servidor esté corriendo:")
        print("   cd backend && uvicorn app.main:app --reload")
        return
    
    # Ejecutar pruebas
    tester = EndpointTester(base_url)
    tester.test_all_endpoints()

if __name__ == "__main__":
    main()
