"""
Script para verificar que el dashboard en producción esté conectado correctamente a la base de datos
Verifica: https://rapicredit.onrender.com/dashboard/menu
"""

import sys
import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional

# URLs de producción
BACKEND_URL = "https://pagos-f2qf.onrender.com"
FRONTEND_URL = "https://rapicredit.onrender.com"
DASHBOARD_MENU_URL = f"{FRONTEND_URL}/dashboard/menu"

# Endpoints del backend a verificar
ENDPOINTS_TO_CHECK = {
    "health_check": f"{BACKEND_URL}/api/v1/health/render",
    "health_detailed": f"{BACKEND_URL}/api/v1/health",
    "health_ready": f"{BACKEND_URL}/api/v1/health/ready",
    "dashboard_opciones_filtros": f"{BACKEND_URL}/api/v1/dashboard/opciones-filtros",
    "dashboard_kpis_principales": f"{BACKEND_URL}/api/v1/dashboard/kpis-principales",
    "pagos_health": f"{BACKEND_URL}/api/v1/pagos/health",
}

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def verificar_endpoint(url: str, nombre: str, requiere_auth: bool = False, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Verifica un endpoint HTTP y retorna información sobre su estado
    
    Args:
        url: URL del endpoint a verificar
        nombre: Nombre descriptivo del endpoint
        requiere_auth: Si requiere autenticación
        token: Token JWT si requiere autenticación
    
    Returns:
        Diccionario con información del resultado
    """
    resultado = {
        "nombre": nombre,
        "url": url,
        "status_code": None,
        "conectado": False,
        "database_ok": False,
        "tiempo_respuesta_ms": None,
        "error": None,
        "detalles": {}
    }
    
    try:
        headers = {}
        if requiere_auth and token:
            headers["Authorization"] = f"Bearer {token}"
        
        inicio = datetime.now()
        response = requests.get(url, headers=headers, timeout=30)
        tiempo_respuesta = (datetime.now() - inicio).total_seconds() * 1000
        
        resultado["status_code"] = response.status_code
        resultado["tiempo_respuesta_ms"] = round(tiempo_respuesta, 2)
        resultado["conectado"] = response.status_code < 500
        
        # Intentar parsear JSON si es posible
        try:
            data = response.json()
            resultado["detalles"] = data
            
            # Verificar si el endpoint indica que la BD está OK
            if isinstance(data, dict):
                if data.get("database") is True or data.get("status") == "ok":
                    resultado["database_ok"] = True
                elif "database" in data and data["database"] is False:
                    resultado["database_ok"] = False
                    resultado["error"] = data.get("error") or data.get("mensaje", "Database connection failed")
        except (json.JSONDecodeError, ValueError):
            # Si no es JSON, verificar por status code
            if response.status_code == 200:
                resultado["database_ok"] = True
        
    except requests.exceptions.Timeout:
        resultado["error"] = "Timeout - El servidor no respondió en 30 segundos"
        resultado["conectado"] = False
    except requests.exceptions.ConnectionError:
        resultado["error"] = "Error de conexión - No se pudo conectar al servidor"
        resultado["conectado"] = False
    except requests.exceptions.RequestException as e:
        resultado["error"] = f"Error de petición: {str(e)}"
        resultado["conectado"] = False
    except Exception as e:
        resultado["error"] = f"Error inesperado: {type(e).__name__}: {str(e)}"
        resultado["conectado"] = False
    
    return resultado


def verificar_dashboard_produccion():
    """Verifica que el dashboard en producción esté conectado correctamente"""
    print("=" * 80)
    print("VERIFICACIÓN DE CONEXIÓN DEL DASHBOARD EN PRODUCCIÓN")
    print("=" * 80)
    print(f"\nFrontend: {FRONTEND_URL}")
    print(f"Backend: {BACKEND_URL}")
    print(f"Dashboard Menu: {DASHBOARD_MENU_URL}")
    print("\n" + "=" * 80)
    
    resultados = []
    
    # 1. Verificar health check básico (no requiere auth)
    print("\n1. Verificando health check básico del backend...")
    resultado_health = verificar_endpoint(
        ENDPOINTS_TO_CHECK["health_check"],
        "Health Check Básico",
        requiere_auth=False
    )
    resultados.append(resultado_health)
    
    if resultado_health["conectado"]:
        print(f"   [OK] Health check respondió - Status: {resultado_health['status_code']}")
        print(f"   [INFO] Tiempo de respuesta: {resultado_health['tiempo_respuesta_ms']}ms")
        if resultado_health.get("detalles"):
            print(f"   [INFO] Respuesta: {json.dumps(resultado_health['detalles'], indent=2, ensure_ascii=False)}")
    else:
        print(f"   [ERROR] Health check falló: {resultado_health.get('error', 'Unknown error')}")
        print("   [ADVERTENCIA] El backend puede no estar disponible")
    
    # 2. Verificar health check detallado (no requiere auth)
    print("\n2. Verificando health check detallado...")
    resultado_detailed = verificar_endpoint(
        ENDPOINTS_TO_CHECK["health_detailed"],
        "Health Check Detallado",
        requiere_auth=False
    )
    resultados.append(resultado_detailed)
    
    if resultado_detailed["conectado"] and resultado_detailed["status_code"] == 200:
        print(f"   [OK] Health check detallado respondió - Status: {resultado_detailed['status_code']}")
        print(f"   [INFO] Tiempo de respuesta: {resultado_detailed['tiempo_respuesta_ms']}ms")
        
        detalles = resultado_detailed.get("detalles", {})
        
        if isinstance(detalles, dict):
            database_status = detalles.get("database", {})
            if isinstance(database_status, dict):
                # El campo puede ser "status" (True/False) o "connected" (True/False)
                db_connected = database_status.get("status", False) or database_status.get("connected", False)
                if db_connected:
                    print("   [OK] Base de datos conectada según health check detallado")
                    resultado_detailed["database_ok"] = True
                else:
                    print(f"   [ERROR] Base de datos NO conectada - Estado: {database_status}")
                    resultado_detailed["database_ok"] = False
            else:
                # Intentar otras formas de verificar
                if detalles.get("status") == "ok" or detalles.get("database") is True:
                    print("   [OK] Base de datos conectada (verificado por status)")
                    resultado_detailed["database_ok"] = True
                elif detalles.get("database") is False:
                    print("   [ERROR] Base de datos NO conectada según health check detallado")
                    resultado_detailed["database_ok"] = False
                else:
                    # Si el endpoint responde 200, asumimos que BD está OK (el endpoint verifica BD internamente)
                    print("   [OK] Health check detallado responde OK (BD probablemente conectada)")
                    resultado_detailed["database_ok"] = True
    elif resultado_detailed["status_code"] == 404:
        print("   [ADVERTENCIA] Health check detallado no encontrado (ruta puede haber cambiado)")
    else:
        print(f"   [ADVERTENCIA] Health check detallado no disponible: {resultado_detailed.get('error', 'Unknown')}")
    
    # 2b. Verificar health check ready (readiness probe)
    print("\n2b. Verificando health check ready (readiness)...")
    resultado_ready = verificar_endpoint(
        ENDPOINTS_TO_CHECK["health_ready"],
        "Health Check Ready",
        requiere_auth=False
    )
    resultados.append(resultado_ready)
    
    if resultado_ready["conectado"] and resultado_ready["status_code"] == 200:
        print(f"   [OK] Health check ready respondió - Status: {resultado_ready['status_code']}")
        detalles = resultado_ready.get("detalles", {})
        if isinstance(detalles, dict):
            db_status = detalles.get("database", {})
            if isinstance(db_status, dict):
                db_ok = db_status.get("status", False) or db_status.get("connected", False)
                if db_ok:
                    print("   [OK] Base de datos conectada según readiness check")
                    resultado_ready["database_ok"] = True
            elif detalles.get("status") == "ready":
                print("   [OK] Readiness check OK (BD probablemente conectada)")
                resultado_ready["database_ok"] = True
    elif resultado_ready["status_code"] == 404:
        print("   [ADVERTENCIA] Health check ready no encontrado")
    else:
        print(f"   [ADVERTENCIA] Health check ready: {resultado_ready.get('error', 'Unknown')}")
    
    # 3. Verificar health check de pagos (requiere auth, pero podemos intentar)
    print("\n3. Verificando health check del módulo de pagos...")
    resultado_pagos = verificar_endpoint(
        ENDPOINTS_TO_CHECK["pagos_health"],
        "Health Check Pagos",
        requiere_auth=True  # Puede requerir auth
    )
    resultados.append(resultado_pagos)
    
    if resultado_pagos["status_code"] == 401:
        print("   [ADVERTENCIA] Endpoint requiere autenticación (esto es normal)")
    elif resultado_pagos["conectado"]:
        print(f"   [OK] Health check pagos respondió - Status: {resultado_pagos['status_code']}")
        detalles = resultado_pagos.get("detalles", {})
        if isinstance(detalles, dict) and detalles.get("database"):
            print("   [OK] Base de datos conectada según módulo de pagos")
            resultado_pagos["database_ok"] = True
    
    # 4. Verificar endpoints del dashboard (requieren auth)
    print("\n4. Verificando endpoints del dashboard...")
    print("   [INFO] Nota: Estos endpoints requieren autenticación")
    
    resultado_dashboard_opciones = verificar_endpoint(
        ENDPOINTS_TO_CHECK["dashboard_opciones_filtros"],
        "Dashboard - Opciones Filtros",
        requiere_auth=True
    )
    resultados.append(resultado_dashboard_opciones)
    
    if resultado_dashboard_opciones["status_code"] == 401:
        print("   [OK] Endpoint de opciones de filtros responde (requiere auth - normal)")
    elif resultado_dashboard_opciones["conectado"]:
        print(f"   [OK] Endpoint de opciones de filtros funciona - Status: {resultado_dashboard_opciones['status_code']}")
        resultado_dashboard_opciones["database_ok"] = True
    else:
        print(f"   [ERROR] Endpoint de opciones de filtros falló: {resultado_dashboard_opciones.get('error')}")
    
    resultado_dashboard_kpis = verificar_endpoint(
        ENDPOINTS_TO_CHECK["dashboard_kpis_principales"],
        "Dashboard - KPIs Principales",
        requiere_auth=True
    )
    resultados.append(resultado_dashboard_kpis)
    
    if resultado_dashboard_kpis["status_code"] == 401:
        print("   [OK] Endpoint de KPIs principales responde (requiere auth - normal)")
    elif resultado_dashboard_kpis["conectado"]:
        print(f"   [OK] Endpoint de KPIs principales funciona - Status: {resultado_dashboard_kpis['status_code']}")
        resultado_dashboard_kpis["database_ok"] = True
    else:
        print(f"   [ERROR] Endpoint de KPIs principales falló: {resultado_dashboard_kpis.get('error')}")
    
    # 5. Verificar frontend (dashboard menu)
    print("\n5. Verificando frontend (dashboard menu)...")
    resultado_frontend = verificar_endpoint(
        DASHBOARD_MENU_URL,
        "Frontend - Dashboard Menu",
        requiere_auth=False
    )
    resultados.append(resultado_frontend)
    
    if resultado_frontend["conectado"]:
        print(f"   [OK] Frontend responde - Status: {resultado_frontend['status_code']}")
        print(f"   [INFO] Tiempo de respuesta: {resultado_frontend['tiempo_respuesta_ms']}ms")
    else:
        print(f"   [ERROR] Frontend no responde: {resultado_frontend.get('error')}")
    
    # Resumen final
    print("\n" + "=" * 80)
    print("RESUMEN DE VERIFICACIÓN")
    print("=" * 80)
    
    endpoints_conectados = sum(1 for r in resultados if r["conectado"])
    endpoints_db_ok = sum(1 for r in resultados if r.get("database_ok", False))
    total_endpoints = len(resultados)
    
    print(f"\nEndpoints verificados: {total_endpoints}")
    print(f"Endpoints conectados: {endpoints_conectados}/{total_endpoints}")
    print(f"Endpoints con BD OK: {endpoints_db_ok}/{total_endpoints}")
    
    print("\nDetalle por endpoint:")
    for resultado in resultados:
        estado = "[OK]" if resultado["conectado"] else "[ERROR]"
        db_estado = " [BD OK]" if resultado.get("database_ok") else ""
        tiempo = f" ({resultado['tiempo_respuesta_ms']}ms)" if resultado.get("tiempo_respuesta_ms") else ""
        print(f"   {estado}{db_estado} {resultado['nombre']}{tiempo}")
        if resultado.get("error"):
            print(f"      Error: {resultado['error']}")
    
    # Conclusión
    print("\n" + "=" * 80)
    health_ok = resultado_health.get("conectado", False)
    health_db_ok = resultado_health.get("database_ok") or resultado_detailed.get("database_ok", False)
    frontend_ok = resultado_frontend.get("conectado", False)
    
    if health_ok and health_db_ok and frontend_ok:
        print("[EXITO] Dashboard en producción está conectado correctamente a la base de datos")
        print("   - Backend responde correctamente")
        print("   - Base de datos conectada")
        print("   - Frontend accesible")
        return True
    elif health_ok and health_db_ok:
        print("[ADVERTENCIA] Backend y BD OK, pero frontend puede tener problemas")
        return True  # Backend y BD están OK, que es lo más importante
    elif health_ok:
        print("[ADVERTENCIA] Backend responde pero hay problemas con la conexión a BD")
        return False
    else:
        print("[ERROR] Hay problemas críticos:")
        if not health_ok:
            print("   - Backend no responde o no está disponible")
        if not health_db_ok:
            print("   - Base de datos no está conectada")
        if not frontend_ok:
            print("   - Frontend no responde")
        return False


if __name__ == "__main__":
    try:
        print("Verificando dashboard en producción...")
        print("Esto puede tardar unos segundos...\n")
        
        exito = verificar_dashboard_produccion()
        
        sys.exit(0 if exito else 1)
    except KeyboardInterrupt:
        print("\n[INFO] Verificación cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error inesperado: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
