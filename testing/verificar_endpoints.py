#!/usr/bin/env python3
"""
Script de verificación de endpoints - Sistema de Préstamos y Cobranza
Verifica todos los endpoints de la API y genera un reporte detallado
"""

import requests
import json
import sys
from datetime import datetime
from typing import Dict, Optional, List, Tuple

# Configuración
API_URL = "https://tu-app.railway.app"  # CAMBIAR POR TU URL REAL
# Ejemplo Railway: https://web-production-XXXX.up.railway.app

# Colores ANSI
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color

class EndpointTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.results: List[Dict] = []
        self.token: Optional[str] = None
        
    def print_header(self, text: str):
        print(f"\n{Colors.BLUE}{'='*60}")
        print(f"{text}")
        print(f"{'='*60}{Colors.NC}\n")
    
    def print_success(self, text: str):
        print(f"{Colors.GREEN}✅ {text}{Colors.NC}")
    
    def print_error(self, text: str):
        print(f"{Colors.RED}❌ {text}{Colors.NC}")
    
    def print_warning(self, text: str):
        print(f"{Colors.YELLOW}⚠️  {text}{Colors.NC}")
    
    def print_info(self, text: str):
        print(f"{Colors.CYAN}ℹ️  {text}{Colors.NC}")
    
    def test_endpoint(
        self,
        method: str,
        endpoint: str,
        description: str,
        data: Optional[Dict] = None,
        use_auth: bool = False,
        expected_status: int = 200
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Prueba un endpoint y retorna el resultado
        """
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if use_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        print(f"\n{Colors.YELLOW}Testing:{Colors.NC} {method} {endpoint}")
        print(f"{Colors.CYAN}Descripción:{Colors.NC} {description}")
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                self.print_error(f"Método HTTP no soportado: {method}")
                return False, None
            
            # Mostrar resultado
            status_ok = response.status_code == expected_status
            
            if status_ok:
                self.print_success(f"Status: {response.status_code}")
            elif 200 <= response.status_code < 300:
                self.print_warning(f"Status: {response.status_code} (esperado: {expected_status})")
            else:
                self.print_error(f"Status: {response.status_code}")
            
            # Intentar parsear JSON
            try:
                response_data = response.json()
                print(f"{Colors.CYAN}Response:{Colors.NC}")
                print(json.dumps(response_data, indent=2, ensure_ascii=False))
            except:
                print(f"{Colors.CYAN}Response (text):{Colors.NC}")
                print(response.text[:500])  # Limitar salida
            
            # Guardar resultado
            self.results.append({
                "method": method,
                "endpoint": endpoint,
                "description": description,
                "status_code": response.status_code,
                "success": status_ok,
                "timestamp": datetime.now().isoformat()
            })
            
            return status_ok, response_data if 'response_data' in locals() else None
            
        except requests.exceptions.ConnectionError:
            self.print_error(f"Error de conexión: No se puede conectar a {url}")
            self.print_warning("Verifica que la URL sea correcta y el servidor esté corriendo")
            return False, None
        except requests.exceptions.Timeout:
            self.print_error("Timeout: El servidor no respondió a tiempo")
            return False, None
        except Exception as e:
            self.print_error(f"Error inesperado: {str(e)}")
            return False, None
        finally:
            print()
    
    def run_tests(self):
        """Ejecuta todos los tests de endpoints"""
        
        self.print_header("🔍 VERIFICACIÓN DE ENDPOINTS - API PRÉSTAMOS Y COBRANZA")
        print(f"{Colors.BOLD}API URL:{Colors.NC} {self.base_url}\n")
        print(f"{Colors.BOLD}Timestamp:{Colors.NC} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # ========================================
        # 1. HEALTH CHECK
        # ========================================
        self.print_header("📊 1. HEALTH CHECK")
        
        self.test_endpoint(
            "GET", "/health",
            "Verificar estado general del servidor"
        )
        
        self.test_endpoint(
            "GET", "/api/v1/health",
            "Health check de la API v1"
        )
        
        # ========================================
        # 2. DOCUMENTACIÓN
        # ========================================
        self.print_header("📚 2. DOCUMENTACIÓN")
        
        self.print_info(f"Swagger UI: {self.base_url}/docs")
        self.print_info(f"ReDoc: {self.base_url}/redoc")
        self.print_info(f"OpenAPI Schema: {self.base_url}/openapi.json")
        
        self.test_endpoint(
            "GET", "/openapi.json",
            "Obtener esquema OpenAPI"
        )
        
        # ========================================
        # 3. AUTENTICACIÓN
        # ========================================
        self.print_header("🔐 3. AUTENTICACIÓN")
        
        login_data = {
            "email": "admin@example.com",
            "password": "admin123"
        }
        
        success, response = self.test_endpoint(
            "POST", "/api/v1/auth/login",
            "Login con credenciales de prueba",
            data=login_data,
            expected_status=200
        )
        
        if success and response and "access_token" in response:
            self.token = response["access_token"]
            self.print_success(f"Token obtenido: {self.token[:20]}...")
        else:
            self.print_warning("No se pudo obtener token. Los tests con autenticación pueden fallar.")
        
        # ========================================
        # 4. CLIENTES
        # ========================================
        self.print_header("👥 4. ENDPOINTS DE CLIENTES")
        
        self.test_endpoint(
            "GET", "/api/v1/clientes",
            "Listar todos los clientes",
            use_auth=True
        )
        
        self.test_endpoint(
            "GET", "/api/v1/clientes?skip=0&limit=10",
            "Listar clientes con paginación",
            use_auth=True
        )
        
        cliente_data = {
            "nombre": "Juan",
            "apellido": "Pérez",
            "dni": "12345678",
            "telefono": "+51999999999",
            "email": f"test.{datetime.now().timestamp()}@example.com",
            "direccion": "Av. Principal 123",
            "fecha_nacimiento": "1990-01-01"
        }
        
        success, cliente_response = self.test_endpoint(
            "POST", "/api/v1/clientes",
            "Crear nuevo cliente",
            data=cliente_data,
            use_auth=True,
            expected_status=201
        )
        
        cliente_id = None
        if success and cliente_response:
            cliente_id = cliente_response.get("id")
            if cliente_id:
                self.print_success(f"Cliente creado con ID: {cliente_id}")
        
        if cliente_id:
            self.test_endpoint(
                "GET", f"/api/v1/clientes/{cliente_id}",
                f"Obtener cliente con ID {cliente_id}",
                use_auth=True
            )
            
            update_data = {
                "telefono": "+51888888888",
                "direccion": "Nueva dirección 456"
            }
            
            self.test_endpoint(
                "PUT", f"/api/v1/clientes/{cliente_id}",
                f"Actualizar cliente con ID {cliente_id}",
                data=update_data,
                use_auth=True
            )
        
        # ========================================
        # 5. PRÉSTAMOS
        # ========================================
        self.print_header("💰 5. ENDPOINTS DE PRÉSTAMOS")
        
        self.test_endpoint(
            "GET", "/api/v1/prestamos",
            "Listar todos los préstamos",
            use_auth=True
        )
        
        if cliente_id:
            prestamo_data = {
                "cliente_id": cliente_id,
                "monto": 5000.00,
                "tasa_interes": 15.0,
                "plazo_dias": 90,
                "fecha_desembolso": datetime.now().strftime("%Y-%m-%d"),
                "tipo_prestamo": "PERSONAL"
            }
            
            success, prestamo_response = self.test_endpoint(
                "POST", "/api/v1/prestamos",
                "Crear nuevo préstamo",
                data=prestamo_data,
                use_auth=True,
                expected_status=201
            )
            
            prestamo_id = None
            if success and prestamo_response:
                prestamo_id = prestamo_response.get("id")
                if prestamo_id:
                    self.print_success(f"Préstamo creado con ID: {prestamo_id}")
            
            self.test_endpoint(
                "GET", f"/api/v1/prestamos/cliente/{cliente_id}",
                f"Obtener préstamos del cliente {cliente_id}",
                use_auth=True
            )
            
            if prestamo_id:
                self.test_endpoint(
                    "GET", f"/api/v1/prestamos/{prestamo_id}",
                    f"Obtener préstamo con ID {prestamo_id}",
                    use_auth=True
                )
                
                self.test_endpoint(
                    "GET", f"/api/v1/prestamos/{prestamo_id}/cuotas",
                    f"Obtener cuotas del préstamo {prestamo_id}",
                    use_auth=True
                )
        else:
            self.print_warning("No se pudo crear cliente. Saltando tests de préstamos.")
        
        # ========================================
        # 6. PAGOS
        # ========================================
        self.print_header("💳 6. ENDPOINTS DE PAGOS")
        
        self.test_endpoint(
            "GET", "/api/v1/pagos",
            "Listar todos los pagos",
            use_auth=True
        )
        
        if 'prestamo_id' in locals() and prestamo_id:
            pago_data = {
                "prestamo_id": prestamo_id,
                "monto": 500.00,
                "metodo_pago": "EFECTIVO",
                "fecha_pago": datetime.now().strftime("%Y-%m-%d")
            }
            
            success, pago_response = self.test_endpoint(
                "POST", "/api/v1/pagos",
                "Registrar nuevo pago",
                data=pago_data,
                use_auth=True,
                expected_status=201
            )
            
            pago_id = None
            if success and pago_response:
                pago_id = pago_response.get("id")
                if pago_id:
                    self.print_success(f"Pago registrado con ID: {pago_id}")
            
            self.test_endpoint(
                "GET", f"/api/v1/pagos/prestamo/{prestamo_id}",
                f"Obtener pagos del préstamo {prestamo_id}",
                use_auth=True
            )
            
            if pago_id:
                self.test_endpoint(
                    "GET", f"/api/v1/pagos/{pago_id}",
                    f"Obtener pago con ID {pago_id}",
                    use_auth=True
                )
        else:
            self.print_warning("No se pudo crear préstamo. Saltando tests de pagos.")
        
        # ========================================
        # 7. USUARIOS
        # ========================================
        self.print_header("👤 7. ENDPOINTS DE USUARIOS")
        
        self.test_endpoint(
            "GET", "/api/v1/users/me",
            "Obtener perfil del usuario actual",
            use_auth=True
        )
        
        self.test_endpoint(
            "GET", "/api/v1/users",
            "Listar usuarios",
            use_auth=True
        )
        
        # ========================================
        # RESUMEN FINAL
        # ========================================
        self.print_summary()
    
    def print_summary(self):
        """Imprime un resumen de los resultados"""
        self.print_header("📊 RESUMEN DE VERIFICACIÓN")
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total - successful
        
        print(f"{Colors.BOLD}Total de endpoints probados:{Colors.NC} {total}")
        self.print_success(f"Exitosos: {successful}")
        if failed > 0:
            self.print_error(f"Fallidos: {failed}")
        
        if failed > 0:
            print(f"\n{Colors.YELLOW}Endpoints que fallaron:{Colors.NC}")
            for result in self.results:
                if not result["success"]:
                    print(f"  • {result['method']} {result['endpoint']} - Status: {result['status_code']}")
        
        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.BOLD}Próximos pasos:{Colors.NC}")
        print(f"1. Revisar endpoints que fallaron")
        print(f"2. Verificar documentación interactiva: {self.base_url}/docs")
        print(f"3. Revisar logs del servidor para más detalles")
        print(f"4. Probar flujos completos en Swagger UI")
        print(f"{Colors.CYAN}{'='*60}{Colors.NC}\n")

def main():
    """Función principal"""
    print(f"{Colors.BOLD}Sistema de Verificación de Endpoints{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}\n")
    
    # Obtener URL de la API
    if len(sys.argv) > 1:
        api_url = sys.argv[1]
    else:
        print(f"{Colors.YELLOW}Uso: python verificar_endpoints.py <URL_API>{Colors.NC}")
        print(f"{Colors.YELLOW}Ejemplo: python verificar_endpoints.py https://tu-app.railway.app{Colors.NC}\n")
        api_url = input(f"{Colors.CYAN}Ingresa la URL de tu API (o presiona Enter para usar localhost): {Colors.NC}").strip()
        
        if not api_url:
            api_url = "http://localhost:8080"
            print(f"{Colors.YELLOW}Usando URL por defecto: {api_url}{Colors.NC}\n")
    
    # Crear tester y ejecutar
    tester = EndpointTester(api_url)
    
    try:
        tester.run_tests()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Verificación interrumpida por el usuario{Colors.NC}")
        tester.print_summary()
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error fatal: {str(e)}{Colors.NC}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
