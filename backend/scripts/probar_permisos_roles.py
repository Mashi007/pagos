#!/usr/bin/env python3
"""
Script para probar endpoints con diferentes roles
Verifica que los permisos funcionen correctamente después de la limpieza de roles
"""
import requests
import json
import time
from typing import Dict, List, Tuple

class RolePermissionTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def create_test_user(self, email: str, password: str, rol: str) -> bool:
        """Crear usuario de prueba"""
        try:
            user_data = {
                "email": email,
                "password": password,
                "full_name": f"Test {rol}",
                "rol": rol,
                "cargo": f"Cargo {rol}",
                "is_active": True
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/users/",
                json=user_data,
                headers={"Authorization": f"Bearer {self.get_admin_token()}"}
            )
            
            return response.status_code in [200, 201]
            
        except Exception as e:
            print(f"Error creando usuario {email}: {e}")
            return False
    
    def get_admin_token(self) -> str:
        """Obtener token de administrador"""
        try:
            login_data = {
                "username": "itmaster@rapicreditca.com",
                "password": "admin123"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                data=login_data
            )
            
            if response.status_code == 200:
                return response.json().get("access_token")
            return ""
            
        except:
            return ""
    
    def login_user(self, email: str, password: str) -> str:
        """Iniciar sesión como usuario específico"""
        try:
            login_data = {
                "username": email,
                "password": password
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                data=login_data
            )
            
            if response.status_code == 200:
                token = response.json().get("access_token")
                self.session.headers.update({
                    "Authorization": f"Bearer {token}"
                })
                return token
            return ""
            
        except:
            return ""
    
    def test_endpoint_with_role(self, method: str, endpoint: str, role: str, expected_status: int = 200) -> Dict:
        """Probar endpoint con rol específico"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json={})
            elif method.upper() == "PUT":
                response = self.session.put(url, json={})
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                return {"success": False, "error": f"Método {method} no soportado"}
            
            result = {
                "method": method,
                "endpoint": endpoint,
                "role": role,
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
                "role": role,
                "success": False,
                "error": str(e)
            }
    
    def test_role_permissions(self):
        """Probar permisos de diferentes roles"""
        print("🔐 INICIANDO PRUEBAS DE PERMISOS POR ROLES")
        print("=" * 60)
        
        # Crear usuarios de prueba para cada rol
        test_users = [
            ("test_admin@example.com", "admin123", "ADMIN"),
            ("test_gerente@example.com", "gerente123", "GERENTE"),
            ("test_cobranzas@example.com", "cobranzas123", "COBRANZAS"),
            ("test_user@example.com", "user123", "USER")
        ]
        
        admin_token = self.get_admin_token()
        if not admin_token:
            print("❌ No se pudo obtener token de administrador")
            return
        
        self.session.headers.update({"Authorization": f"Bearer {admin_token}"})
        
        print("👥 Creando usuarios de prueba...")
        for email, password, rol in test_users:
            if self.create_test_user(email, password, rol):
                print(f"  ✅ Usuario {rol} creado: {email}")
            else:
                print(f"  ❌ Error creando usuario {rol}: {email}")
        
        print()
        
        # Endpoints a probar con diferentes roles
        endpoints_to_test = [
            # Endpoints que solo ADMIN puede acceder
            ("GET", "/api/v1/users/", "ADMIN", 200),
            ("GET", "/api/v1/users/", "GERENTE", 403),
            ("GET", "/api/v1/users/", "COBRANZAS", 403),
            ("GET", "/api/v1/users/", "USER", 403),
            
            # Endpoints que ADMIN y GERENTE pueden acceder
            ("GET", "/api/v1/dashboard/", "ADMIN", 200),
            ("GET", "/api/v1/dashboard/", "GERENTE", 200),
            ("GET", "/api/v1/dashboard/", "COBRANZAS", 200),
            ("GET", "/api/v1/dashboard/", "USER", 200),
            
            # Endpoints de clientes (todos pueden acceder)
            ("GET", "/api/v1/clientes/", "ADMIN", 200),
            ("GET", "/api/v1/clientes/", "GERENTE", 200),
            ("GET", "/api/v1/clientes/", "COBRANZAS", 200),
            ("GET", "/api/v1/clientes/", "USER", 200),
            
            # Endpoints de pagos
            ("GET", "/api/v1/pagos/", "ADMIN", 200),
            ("GET", "/api/v1/pagos/", "GERENTE", 200),
            ("GET", "/api/v1/pagos/", "COBRANZAS", 200),
            ("GET", "/api/v1/pagos/", "USER", 200),
            
            # Endpoints de auditoría (solo ADMIN)
            ("GET", "/api/v1/auditoria/", "ADMIN", 200),
            ("GET", "/api/v1/auditoria/", "GERENTE", 403),
            ("GET", "/api/v1/auditoria/", "COBRANZAS", 403),
            ("GET", "/api/v1/auditoria/", "USER", 403),
        ]
        
        print(f"🧪 Probando {len(endpoints_to_test)} combinaciones de rol-endpoint...")
        print()
        
        successful_tests = 0
        failed_tests = 0
        
        for method, endpoint, role, expected_status in endpoints_to_test:
            # Buscar credenciales del rol
            email, password = None, None
            for test_email, test_password, test_role in test_users:
                if test_role == role:
                    email, password = test_email, test_password
                    break
            
            if not email:
                print(f"❌ No se encontraron credenciales para rol {role}")
                continue
            
            # Hacer login con el rol
            token = self.login_user(email, password)
            if not token:
                print(f"❌ No se pudo hacer login con rol {role}")
                continue
            
            print(f"🔍 Probando {method} {endpoint} con rol {role}...")
            
            result = self.test_endpoint_with_role(method, endpoint, role, expected_status)
            self.test_results.append(result)
            
            if result["success"]:
                print(f"  ✅ {result['status_code']} - {result['response_time']:.2f}s")
                successful_tests += 1
            else:
                print(f"  ❌ {result['status_code']} (esperado: {expected_status}) - {result.get('error', 'Error desconocido')}")
                failed_tests += 1
            
            time.sleep(0.1)
        
        self.generate_permission_report(successful_tests, failed_tests)
    
    def generate_permission_report(self, successful: int, failed: int):
        """Generar reporte de permisos"""
        print("\n" + "=" * 60)
        print("🔐 REPORTE DE PRUEBAS DE PERMISOS")
        print("=" * 60)
        
        print(f"\n📊 RESUMEN:")
        print(f"  ✅ Pruebas exitosas: {successful}")
        print(f"  ❌ Pruebas fallidas: {failed}")
        print(f"  📈 Tasa de éxito: {(successful/(successful+failed)*100):.1f}%")
        
        # Agrupar resultados por rol
        roles_tested = {}
        for result in self.test_results:
            role = result["role"]
            if role not in roles_tested:
                roles_tested[role] = {"successful": 0, "failed": 0}
            
            if result["success"]:
                roles_tested[role]["successful"] += 1
            else:
                roles_tested[role]["failed"] += 1
        
        print(f"\n👥 RESULTADOS POR ROL:")
        for role, stats in roles_tested.items():
            total = stats["successful"] + stats["failed"]
            success_rate = (stats["successful"] / total * 100) if total > 0 else 0
            print(f"  {role}: {stats['successful']}/{total} ({success_rate:.1f}%)")
        
        if failed > 0:
            print(f"\n❌ PRUEBAS FALLIDAS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['role']}: {result['method']} {result['endpoint']}")
                    print(f"    Status: {result['status_code']} (esperado: {result['expected_status']})")
                    if "error" in result:
                        print(f"    Error: {result['error']}")
                    print()
        
        # Guardar reporte
        self.save_permission_report()
    
    def save_permission_report(self):
        """Guardar reporte de permisos"""
        report_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_url": self.base_url,
            "total_tests": len(self.test_results),
            "successful_tests": sum(1 for r in self.test_results if r["success"]),
            "failed_tests": sum(1 for r in self.test_results if not r["success"]),
            "results": self.test_results
        }
        
        filename = f"permission_test_report_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Reporte de permisos guardado en: {filename}")

def main():
    """Función principal"""
    print("🔐 INICIANDO PRUEBAS DE PERMISOS POR ROLES")
    print("=" * 60)
    
    # Verificar conexión
    base_url = "http://localhost:8000"
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor detectado")
        else:
            print("⚠️ Servidor puede no estar completamente funcional")
    except:
        print("❌ No se puede conectar al servidor")
        return
    
    # Ejecutar pruebas
    tester = RolePermissionTester(base_url)
    tester.test_role_permissions()

if __name__ == "__main__":
    main()
