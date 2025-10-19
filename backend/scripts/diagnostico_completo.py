#!/usr/bin/env python3
"""
Script de verificación de endpoints críticos
Tercer enfoque para diagnóstico completo del sistema
"""
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

# Configuración
BASE_URL = "https://pagos-f2qf.onrender.com"
API_PREFIX = "/api/v1"

class EndpointChecker:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'RapiCredit-Diagnostic-Tool/1.0'
        })
    
    def check_endpoint(self, endpoint: str, method: str = "GET", data: Dict = None, 
                      expected_status: int = 200, requires_auth: bool = False) -> Dict[str, Any]:
        """
        Verificar un endpoint específico
        """
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method == "GET":
                response = self.session.get(url, timeout=10)
            elif method == "POST":
                response = self.session.post(url, json=data, timeout=10)
            else:
                response = self.session.request(method, url, json=data, timeout=10)
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            result = {
                "endpoint": endpoint,
                "method": method,
                "status_code": response.status_code,
                "response_time_ms": round(response_time, 2),
                "success": response.status_code == expected_status,
                "requires_auth": requires_auth,
                "timestamp": datetime.now().isoformat(),
                "error": None
            }
            
            # Intentar parsear JSON si es posible
            try:
                result["response_data"] = response.json()
            except:
                result["response_text"] = response.text[:200]  # Primeros 200 caracteres
            
            return result
            
        except requests.exceptions.Timeout:
            return {
                "endpoint": endpoint,
                "method": method,
                "status_code": None,
                "response_time_ms": None,
                "success": False,
                "requires_auth": requires_auth,
                "timestamp": datetime.now().isoformat(),
                "error": "Timeout"
            }
        except requests.exceptions.ConnectionError:
            return {
                "endpoint": endpoint,
                "method": method,
                "status_code": None,
                "response_time_ms": None,
                "success": False,
                "requires_auth": requires_auth,
                "timestamp": datetime.now().isoformat(),
                "error": "Connection Error"
            }
        except Exception as e:
            return {
                "endpoint": endpoint,
                "method": method,
                "status_code": None,
                "response_time_ms": None,
                "success": False,
                "requires_auth": requires_auth,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def run_comprehensive_check(self) -> Dict[str, Any]:
        """
        Ejecutar verificación completa de todos los endpoints críticos
        """
        print("🔍 Iniciando verificación completa del sistema...")
        
        # Endpoints críticos para verificar
        endpoints_to_check = [
            # Endpoints de diagnóstico (sin auth)
            {"endpoint": f"{API_PREFIX}/diagnostico/salud", "method": "GET", "expected_status": 200, "requires_auth": False},
            {"endpoint": f"{API_PREFIX}/diagnostico/sistema", "method": "GET", "expected_status": 200, "requires_auth": False},
            {"endpoint": f"{API_PREFIX}/diagnostico/configuracion", "method": "GET", "expected_status": 200, "requires_auth": False},
            
            # Endpoints de configuración (sin auth)
            {"endpoint": f"{API_PREFIX}/analistas/activos", "method": "GET", "expected_status": 200, "requires_auth": False},
            {"endpoint": f"{API_PREFIX}/concesionarios/activos", "method": "GET", "expected_status": 200, "requires_auth": False},
            {"endpoint": f"{API_PREFIX}/modelos-vehiculos/activos", "method": "GET", "expected_status": 200, "requires_auth": False},
            
            # Endpoints de autenticación
            {"endpoint": f"{API_PREFIX}/auth/login", "method": "POST", "expected_status": 422, "requires_auth": False, "data": {}},  # 422 esperado sin credenciales
            
            # Endpoints protegidos (esperamos 401 sin auth)
            {"endpoint": f"{API_PREFIX}/auth/me", "method": "GET", "expected_status": 401, "requires_auth": True},
            {"endpoint": f"{API_PREFIX}/clientes/", "method": "GET", "expected_status": 401, "requires_auth": True},
            {"endpoint": f"{API_PREFIX}/usuarios/", "method": "GET", "expected_status": 401, "requires_auth": True},
        ]
        
        results = []
        successful_checks = 0
        failed_checks = 0
        
        for endpoint_config in endpoints_to_check:
            print(f"🔗 Verificando {endpoint_config['method']} {endpoint_config['endpoint']}...")
            
            result = self.check_endpoint(
                endpoint=endpoint_config["endpoint"],
                method=endpoint_config["method"],
                data=endpoint_config.get("data"),
                expected_status=endpoint_config["expected_status"],
                requires_auth=endpoint_config["requires_auth"]
            )
            
            results.append(result)
            
            if result["success"]:
                successful_checks += 1
                print(f"✅ {endpoint_config['endpoint']} - OK ({result['status_code']}) - {result['response_time_ms']}ms")
            else:
                failed_checks += 1
                error_msg = result.get("error", f"Status {result['status_code']}")
                print(f"❌ {endpoint_config['endpoint']} - ERROR: {error_msg}")
        
        # Resumen
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_endpoints": len(endpoints_to_check),
            "successful_checks": successful_checks,
            "failed_checks": failed_checks,
            "success_rate": round((successful_checks / len(endpoints_to_check)) * 100, 2),
            "results": results
        }
        
        print(f"\n📊 RESUMEN:")
        print(f"✅ Exitosos: {successful_checks}/{len(endpoints_to_check)}")
        print(f"❌ Fallidos: {failed_checks}/{len(endpoints_to_check)}")
        print(f"📈 Tasa de éxito: {summary['success_rate']}%")
        
        return summary
    
    def test_authentication_flow(self) -> Dict[str, Any]:
        """
        Probar flujo completo de autenticación
        """
        print("\n🔐 Probando flujo de autenticación...")
        
        # Credenciales de prueba (usuario admin)
        login_data = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**",
            "remember": True
        }
        
        # 1. Intentar login
        login_result = self.check_endpoint(
            endpoint=f"{API_PREFIX}/auth/login",
            method="POST",
            data=login_data,
            expected_status=200,
            requires_auth=False
        )
        
        auth_results = {
            "login": login_result,
            "access_token": None,
            "protected_endpoints": []
        }
        
        if login_result["success"] and "response_data" in login_result:
            access_token = login_result["response_data"].get("access_token")
            auth_results["access_token"] = access_token
            
            if access_token:
                # Actualizar headers con token
                self.session.headers.update({
                    'Authorization': f'Bearer {access_token}'
                })
                
                # Probar endpoints protegidos
                protected_endpoints = [
                    f"{API_PREFIX}/auth/me",
                    f"{API_PREFIX}/clientes/",
                    f"{API_PREFIX}/usuarios/"
                ]
                
                for endpoint in protected_endpoints:
                    result = self.check_endpoint(
                        endpoint=endpoint,
                        method="GET",
                        expected_status=200,
                        requires_auth=True
                    )
                    auth_results["protected_endpoints"].append(result)
        
        return auth_results

def main():
    """
    Función principal
    """
    print("🚀 RapiCredit - Diagnóstico Completo del Sistema")
    print("=" * 60)
    
    checker = EndpointChecker(BASE_URL)
    
    # Verificación completa
    comprehensive_results = checker.run_comprehensive_check()
    
    # Prueba de autenticación
    auth_results = checker.test_authentication_flow()
    
    # Generar reporte final
    final_report = {
        "diagnostico_general": comprehensive_results,
        "prueba_autenticacion": auth_results,
        "timestamp": datetime.now().isoformat(),
        "base_url": BASE_URL
    }
    
    # Guardar reporte
    report_filename = f"diagnostico_sistema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Reporte guardado en: {report_filename}")
    
    # Mostrar problemas críticos
    print("\n🚨 PROBLEMAS CRÍTICOS IDENTIFICADOS:")
    critical_issues = []
    
    for result in comprehensive_results["results"]:
        if not result["success"] and not result["requires_auth"]:
            critical_issues.append(f"- {result['endpoint']}: {result.get('error', 'Error desconocido')}")
    
    if critical_issues:
        for issue in critical_issues:
            print(issue)
    else:
        print("✅ No se identificaron problemas críticos")
    
    print("\n🎯 DIAGNÓSTICO COMPLETADO")

if __name__ == "__main__":
    main()
