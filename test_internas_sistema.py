#!/usr/bin/env python3
"""
🧪 PRUEBAS INTERNAS DEL SISTEMA RAPICREDIT
Verificación completa de respuestas y funcionalidad del sistema
"""
import requests
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SistemaTester:
    """Tester interno del sistema Rapicredit"""
    
    def __init__(self):
        self.base_url = "https://pagos-f2qf.onrender.com"
        self.frontend_url = "https://rapicredit.onrender.com"
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Tokens de autenticación
        self.access_token = None
        self.refresh_token = None
        self.user_data = None
        
        # Resultados de pruebas
        self.results = {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'errors': [],
            'details': []
        }
    
    def log_test(self, test_name: str, status: str, details: str = "", response_data: Any = None):
        """Registrar resultado de prueba"""
        self.results['total_tests'] += 1
        
        if status == 'PASS':
            self.results['passed'] += 1
            logger.info(f"✅ {test_name}: PASS")
        else:
            self.results['failed'] += 1
            self.results['errors'].append(f"{test_name}: {details}")
            logger.error(f"❌ {test_name}: FAIL - {details}")
        
        self.results['details'].append({
            'test': test_name,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'response_data': response_data
        })
    
    def test_health_endpoint(self) -> bool:
        """Probar endpoint de salud del sistema"""
        try:
            logger.info("🔍 Probando endpoint de salud...")
            response = self.session.get(f"{self.base_url}/api/v1/health")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Health Check",
                    "PASS",
                    f"Status: {response.status_code}, Response: {data}",
                    data
                )
                return True
            else:
                self.log_test(
                    "Health Check",
                    "FAIL",
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Health Check",
                "FAIL",
                f"Error de conexión: {str(e)}"
            )
            return False
    
    def test_database_connection(self) -> bool:
        """Probar conexión a base de datos"""
        try:
            logger.info("🔍 Probando conexión a base de datos...")
            response = self.session.get(f"{self.base_url}/api/v1/health/db")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Database Connection",
                    "PASS",
                    f"Status: {response.status_code}, Response: {data}",
                    data
                )
                return True
            else:
                self.log_test(
                    "Database Connection",
                    "FAIL",
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Database Connection",
                "FAIL",
                f"Error de conexión: {str(e)}"
            )
            return False
    
    def test_authentication_flow(self) -> bool:
        """Probar flujo completo de autenticación"""
        try:
            logger.info("🔍 Probando flujo de autenticación...")
            
            # 1. Probar login con credenciales de prueba
            login_data = {
                "email": "admin@rapicredit.com",
                "password": "admin123",
                "remember": True
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json=login_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('data', {}).get('access_token')
                self.refresh_token = data.get('data', {}).get('refresh_token')
                self.user_data = data.get('user')
                
                if self.access_token:
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.access_token}'
                    })
                    
                    self.log_test(
                        "Authentication Login",
                        "PASS",
                        f"Token obtenido: {self.access_token[:20]}...",
                        {"has_token": True, "user": self.user_data}
                    )
                    return True
                else:
                    self.log_test(
                        "Authentication Login",
                        "FAIL",
                        "Token no encontrado en respuesta"
                    )
                    return False
            else:
                self.log_test(
                    "Authentication Login",
                    "FAIL",
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Authentication Login",
                "FAIL",
                f"Error en autenticación: {str(e)}"
            )
            return False
    
    def test_protected_endpoints(self) -> bool:
        """Probar endpoints protegidos"""
        if not self.access_token:
            self.log_test(
                "Protected Endpoints",
                "FAIL",
                "No hay token de autenticación disponible"
            )
            return False
        
        endpoints_to_test = [
            "/api/v1/clientes?page=1&per_page=5",
            "/api/v1/dashboard/admin",
            "/api/v1/concesionarios/activos",
            "/api/v1/asesores/activos",
            "/api/v1/configuracion/validadores"
        ]
        
        all_passed = True
        
        for endpoint in endpoints_to_test:
            try:
                logger.info(f"🔍 Probando endpoint protegido: {endpoint}")
                response = self.session.get(f"{self.base_url}{endpoint}")
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    self.log_test(
                        f"Protected Endpoint: {endpoint}",
                        "PASS",
                        f"Status: {response.status_code}",
                        {"status_code": response.status_code, "has_data": bool(data)}
                    )
                elif response.status_code == 403:
                    self.log_test(
                        f"Protected Endpoint: {endpoint}",
                        "FAIL",
                        f"403 Forbidden - Token inválido o expirado"
                    )
                    all_passed = False
                else:
                    self.log_test(
                        f"Protected Endpoint: {endpoint}",
                        "FAIL",
                        f"Status: {response.status_code}, Response: {response.text}"
                    )
                    all_passed = False
                    
            except Exception as e:
                self.log_test(
                    f"Protected Endpoint: {endpoint}",
                    "FAIL",
                    f"Error: {str(e)}"
                )
                all_passed = False
        
        return all_passed
    
    def test_frontend_accessibility(self) -> bool:
        """Probar accesibilidad del frontend"""
        try:
            logger.info("🔍 Probando accesibilidad del frontend...")
            response = self.session.get(self.frontend_url)
            
            if response.status_code == 200:
                # Verificar que el contenido HTML esté presente
                if "rapicredit" in response.text.lower() or "react" in response.text.lower():
                    self.log_test(
                        "Frontend Accessibility",
                        "PASS",
                        f"Status: {response.status_code}, HTML content present"
                    )
                    return True
                else:
                    self.log_test(
                        "Frontend Accessibility",
                        "FAIL",
                        "HTML content not found or invalid"
                    )
                    return False
            else:
                self.log_test(
                    "Frontend Accessibility",
                    "FAIL",
                    f"Status: {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Frontend Accessibility",
                "FAIL",
                f"Error: {str(e)}"
            )
            return False
    
    def test_data_creation(self) -> bool:
        """Probar creación de datos de prueba"""
        if not self.access_token:
            self.log_test(
                "Data Creation",
                "FAIL",
                "No hay token de autenticación disponible"
            )
            return False
        
        try:
            logger.info("🔍 Probando creación de datos...")
            
            # Crear cliente de prueba
            cliente_data = {
                "nombres": "Cliente",
                "apellidos": "Prueba",
                "cedula": "12345678",
                "telefono": "+58412123456",
                "email": "cliente.prueba@test.com",
                "direccion": "Dirección de prueba",
                "anio_vehiculo": 2020,
                "modelo_vehiculo": "Toyota Corolla",
                "total_financiamiento": 15000.00,
                "numero_amortizaciones": 36,
                "modalidad_pago": "MENSUAL",
                "concesionario_id": 1,
                "asesor_id": 1
            }
            
            response = self.session.post(
                f"{self.base_url}/api/v1/clientes",
                json=cliente_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.log_test(
                    "Data Creation - Cliente",
                    "PASS",
                    f"Cliente creado exitosamente: {data.get('id', 'N/A')}",
                    data
                )
                return True
            else:
                self.log_test(
                    "Data Creation - Cliente",
                    "FAIL",
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Data Creation - Cliente",
                "FAIL",
                f"Error: {str(e)}"
            )
            return False
    
    def test_api_response_times(self) -> bool:
        """Probar tiempos de respuesta de API"""
        if not self.access_token:
            self.log_test(
                "API Response Times",
                "FAIL",
                "No hay token de autenticación disponible"
            )
            return False
        
        endpoints_to_test = [
            "/api/v1/dashboard/admin",
            "/api/v1/clientes?page=1&per_page=10",
            "/api/v1/kpis/dashboard"
        ]
        
        all_passed = True
        max_response_time = 5.0  # 5 segundos máximo
        
        for endpoint in endpoints_to_test:
            try:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{endpoint}")
                end_time = time.time()
                
                response_time = end_time - start_time
                
                if response.status_code == 200 and response_time <= max_response_time:
                    self.log_test(
                        f"Response Time: {endpoint}",
                        "PASS",
                        f"Time: {response_time:.2f}s, Status: {response.status_code}",
                        {"response_time": response_time, "status_code": response.status_code}
                    )
                else:
                    status = "FAIL"
                    details = f"Time: {response_time:.2f}s, Status: {response.status_code}"
                    if response_time > max_response_time:
                        details += f" (Timeout > {max_response_time}s)"
                    
                    self.log_test(
                        f"Response Time: {endpoint}",
                        status,
                        details
                    )
                    all_passed = False
                    
            except Exception as e:
                self.log_test(
                    f"Response Time: {endpoint}",
                    "FAIL",
                    f"Error: {str(e)}"
                )
                all_passed = False
        
        return all_passed
    
    def generate_report(self) -> Dict[str, Any]:
        """Generar reporte completo de pruebas"""
        success_rate = (self.results['passed'] / self.results['total_tests'] * 100) if self.results['total_tests'] > 0 else 0
        
        report = {
            'summary': {
                'total_tests': self.results['total_tests'],
                'passed': self.results['passed'],
                'failed': self.results['failed'],
                'success_rate': round(success_rate, 2),
                'timestamp': datetime.now().isoformat(),
                'system_status': 'HEALTHY' if success_rate >= 80 else 'DEGRADED' if success_rate >= 60 else 'CRITICAL'
            },
            'errors': self.results['errors'],
            'details': self.results['details']
        }
        
        return report
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Ejecutar todas las pruebas"""
        logger.info("Iniciando pruebas internas del sistema...")
        logger.info("=" * 60)
        
        # Ejecutar pruebas en orden
        tests = [
            ("Health Check", self.test_health_endpoint),
            ("Database Connection", self.test_database_connection),
            ("Authentication Flow", self.test_authentication_flow),
            ("Protected Endpoints", self.test_protected_endpoints),
            ("Frontend Accessibility", self.test_frontend_accessibility),
            ("API Response Times", self.test_api_response_times),
            ("Data Creation", self.test_data_creation),
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\nEjecutando: {test_name}")
            try:
                test_func()
            except Exception as e:
                self.log_test(test_name, "FAIL", f"Error inesperado: {str(e)}")
            
            time.sleep(1)  # Pausa entre pruebas
        
        # Generar reporte final
        report = self.generate_report()
        
        logger.info("\n" + "=" * 60)
        logger.info("RESUMEN FINAL DE PRUEBAS:")
        logger.info(f"Pruebas Exitosas: {report['summary']['passed']}")
        logger.info(f"Pruebas Fallidas: {report['summary']['failed']}")
        logger.info(f"Tasa de Exito: {report['summary']['success_rate']}%")
        logger.info(f"Estado del Sistema: {report['summary']['system_status']}")
        
        if report['summary']['errors']:
            logger.info("\nERRORES ENCONTRADOS:")
            for error in report['summary']['errors']:
                logger.info(f"  - {error}")
        
        return report

def main():
    """Función principal"""
    print("PRUEBAS INTERNAS DEL SISTEMA RAPICREDIT")
    print("=" * 60)
    
    tester = SistemaTester()
    report = tester.run_all_tests()
    
    # Guardar reporte en archivo
    with open('reporte_pruebas_internas.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nReporte guardado en: reporte_pruebas_internas.json")
    
    # Exit code basado en el resultado
    if report['summary']['success_rate'] >= 80:
        sys.exit(0)  # Éxito
    else:
        sys.exit(1)  # Fallo

if __name__ == "__main__":
    main()
