"""
Script para verificar que los endpoints de cobranzas estén integrados correctamente
con la base de datos y funcionen correctamente.
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import requests
import json
from datetime import date
from typing import Dict, List, Optional

# Configuración
BASE_URL = "https://rapicredit.onrender.com"
# BASE_URL = "http://localhost:8000"  # Para pruebas locales

ENDPOINTS_TO_TEST = [
    {
        "name": "Health Check",
        "method": "GET",
        "url": f"{BASE_URL}/api/v1/cobranzas/health",
        "requires_auth": True,
        "description": "Verifica conectividad con BD y métricas básicas"
    },
    {
        "name": "Resumen",
        "method": "GET",
        "url": f"{BASE_URL}/api/v1/cobranzas/resumen",
        "requires_auth": True,
        "description": "Obtiene resumen general de cobranzas"
    },
    {
        "name": "Clientes Atrasados",
        "method": "GET",
        "url": f"{BASE_URL}/api/v1/cobranzas/clientes-atrasados",
        "requires_auth": True,
        "description": "Lista clientes con cuotas atrasadas"
    },
    {
        "name": "Por Analista",
        "method": "GET",
        "url": f"{BASE_URL}/api/v1/cobranzas/por-analista",
        "requires_auth": True,
        "description": "Cobranzas agrupadas por analista"
    },
    {
        "name": "Montos por Mes",
        "method": "GET",
        "url": f"{BASE_URL}/api/v1/cobranzas/montos-por-mes",
        "requires_auth": True,
        "description": "Montos vencidos agrupados por mes"
    },
    {
        "name": "Diagnóstico",
        "method": "GET",
        "url": f"{BASE_URL}/api/v1/cobranzas/diagnostico",
        "requires_auth": True,
        "description": "Información de diagnóstico del módulo"
    }
]


def print_header(text: str):
    """Imprime un encabezado formateado"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_success(text: str):
    """Imprime un mensaje de éxito"""
    print(f"[OK] {text}")


def print_error(text: str):
    """Imprime un mensaje de error"""
    print(f"[ERROR] {text}")


def print_warning(text: str):
    """Imprime un mensaje de advertencia"""
    print(f"[WARN] {text}")


def print_info(text: str):
    """Imprime un mensaje informativo"""
    print(f"[INFO] {text}")


def test_endpoint(endpoint: Dict, token: Optional[str] = None) -> Dict:
    """
    Prueba un endpoint específico
    
    Args:
        endpoint: Diccionario con información del endpoint
        token: Token de autenticación (opcional)
    
    Returns:
        Diccionario con resultados de la prueba
    """
    result = {
        "name": endpoint["name"],
        "url": endpoint["url"],
        "success": False,
        "status_code": None,
        "response_time_ms": None,
        "error": None,
        "data": None
    }
    
    try:
        headers = {
            "Content-Type": "application/json"
        }
        
        if endpoint.get("requires_auth") and token:
            headers["Authorization"] = f"Bearer {token}"
        
        import time
        start_time = time.time()
        
        response = requests.get(
            endpoint["url"],
            headers=headers,
            timeout=30
        )
        
        result["response_time_ms"] = int((time.time() - start_time) * 1000)
        result["status_code"] = response.status_code
        
        if response.status_code == 200:
            try:
                result["data"] = response.json()
                result["success"] = True
            except json.JSONDecodeError:
                result["error"] = "Respuesta no es JSON válido"
                result["data"] = response.text[:200]  # Primeros 200 caracteres
        elif response.status_code == 401:
            result["error"] = "No autorizado - Token requerido o inválido"
        elif response.status_code == 403:
            result["error"] = "Prohibido - Sin permisos suficientes"
        elif response.status_code == 404:
            result["error"] = "Endpoint no encontrado"
        elif response.status_code == 500:
            try:
                error_detail = response.json().get("detail", "Error interno del servidor")
                result["error"] = f"Error del servidor: {error_detail}"
            except:
                result["error"] = "Error interno del servidor"
        else:
            result["error"] = f"Status code: {response.status_code}"
            
    except requests.exceptions.Timeout:
        result["error"] = "Timeout - El servidor no respondió a tiempo"
    except requests.exceptions.ConnectionError:
        result["error"] = "Error de conexión - No se pudo conectar al servidor"
    except Exception as e:
        result["error"] = f"Error inesperado: {str(e)}"
    
    return result


def print_result(result: Dict):
    """Imprime el resultado de una prueba"""
    print(f"\n[ENDPOINT] {result['name']}")
    print(f"   URL: {result['url']}")
    
    if result["success"]:
        print_success(f"Estado: OK (Status: {result['status_code']})")
        if result["response_time_ms"]:
            print_info(f"Tiempo de respuesta: {result['response_time_ms']}ms")
        
        # Mostrar datos relevantes según el endpoint
        if result["data"]:
            if "metrics" in result["data"]:
                metrics = result["data"]["metrics"]
                print_info(f"  - Total cuotas: {metrics.get('total_cuotas', 'N/A')}")
                print_info(f"  - Cuotas vencidas: {metrics.get('cuotas_vencidas', 'N/A')}")
                print_info(f"  - Monto vencido: ${metrics.get('monto_vencido', 0):,.2f}")
            elif "total_cuotas_vencidas" in result["data"]:
                print_info(f"  - Total cuotas vencidas: {result['data'].get('total_cuotas_vencidas', 'N/A')}")
                print_info(f"  - Monto total adeudado: ${result['data'].get('monto_total_adeudado', 0):,.2f}")
                print_info(f"  - Clientes atrasados: {result['data'].get('clientes_atrasados', 'N/A')}")
            elif isinstance(result["data"], list):
                print_info(f"  - Elementos retornados: {len(result['data'])}")
            else:
                print_info(f"  - Datos recibidos: {json.dumps(result['data'], indent=2)[:200]}...")
    else:
        print_error(f"Estado: FALLIDO")
        if result["status_code"]:
            print_error(f"  Status Code: {result['status_code']}")
        if result["error"]:
            print_error(f"  Error: {result['error']}")
        if result["response_time_ms"]:
            print_info(f"  Tiempo antes del error: {result['response_time_ms']}ms")


def main():
    """Función principal"""
    print_header("VERIFICACIÓN DE ENDPOINTS DE COBRANZAS")
    print_info(f"URL Base: {BASE_URL}")
    print_info(f"Fecha: {date.today().isoformat()}")
    
    # Nota sobre autenticación
    print_warning("NOTA: Algunos endpoints requieren autenticación.")
    print_warning("Si los endpoints fallan con 401, necesitas proporcionar un token válido.")
    print_info("Para obtener un token, inicia sesión en la aplicación y copia el token del localStorage.")
    
    token = None
    # Intentar obtener token de variable de entorno o argumento
    if len(sys.argv) > 1:
        token = sys.argv[1]
        print_info(f"Token proporcionado: {token[:20]}...")
    
    # Probar cada endpoint
    results = []
    for endpoint in ENDPOINTS_TO_TEST:
        result = test_endpoint(endpoint, token)
        results.append(result)
        print_result(result)
    
    # Resumen
    print_header("RESUMEN DE VERIFICACIÓN")
    
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    
    print_info(f"Endpoints probados: {total}")
    print_success(f"Endpoints exitosos: {successful}")
    print_error(f"Endpoints fallidos: {total - successful}")
    
    if successful == total:
        print_success("\n[TODO OK] Todos los endpoints estan funcionando correctamente!")
    elif successful > 0:
        print_warning(f"\n[PARCIAL] {successful}/{total} endpoints funcionan correctamente")
        print_warning("Revisa los errores arriba para mas detalles")
    else:
        print_error("\n[FALLO] Ningun endpoint esta funcionando")
        print_error("Verifica:")
        print_error("  1. Que el servidor este corriendo")
        print_error("  2. Que la URL base sea correcta")
        print_error("  3. Que tengas un token de autenticacion valido (si es requerido)")
    
    # Verificar integración con BD
    print_header("VERIFICACION DE INTEGRACION CON BASE DE DATOS")
    
    health_result = next((r for r in results if r["name"] == "Health Check"), None)
    if health_result and health_result["success"]:
        print_success("[OK] El endpoint de health check confirma conectividad con BD")
        if health_result["data"] and health_result["data"].get("database"):
            print_success("[OK] La base de datos esta accesible")
            if "metrics" in health_result["data"]:
                metrics = health_result["data"]["metrics"]
                if metrics.get("total_cuotas", 0) > 0:
                    print_success(f"[OK] Hay datos en la BD: {metrics['total_cuotas']} cuotas encontradas")
                else:
                    print_warning("[WARN] No hay cuotas en la base de datos (puede ser normal si es un sistema nuevo)")
    else:
        print_error("[ERROR] No se pudo verificar la integracion con BD (health check fallo)")
    
    resumen_result = next((r for r in results if r["name"] == "Resumen"), None)
    if resumen_result and resumen_result["success"]:
        print_success("[OK] El endpoint de resumen esta funcionando y consultando BD")
        if resumen_result["data"]:
            data = resumen_result["data"]
            if "total_cuotas_vencidas" in data:
                print_info(f"  - Total cuotas vencidas: {data['total_cuotas_vencidas']}")
                print_info(f"  - Monto total adeudado: ${data.get('monto_total_adeudado', 0):,.2f}")
                print_info(f"  - Clientes atrasados: {data.get('clientes_atrasados', 0)}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
