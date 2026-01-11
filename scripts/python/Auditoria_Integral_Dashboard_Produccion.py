"""
Auditoría Integral del Dashboard en Producción
Verifica conectividad, endpoints, datos, rendimiento y errores
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
from urllib.parse import urljoin

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# URL base del dashboard en producción
BASE_URL = "https://rapicredit.onrender.com"

# Timeout para requests
REQUEST_TIMEOUT = 30

# Lista de endpoints a verificar
ENDPOINTS_AUDITORIA = [
    {
        "nombre": "Health Check",
        "endpoint": "/api/v1/health",
        "metodo": "GET",
        "requiere_auth": False,
        "verificar": ["status", "database"]
    },
    {
        "nombre": "Health Ready",
        "endpoint": "/api/v1/health/ready",
        "metodo": "GET",
        "requiere_auth": False,
        "verificar": ["status"]
    },
    {
        "nombre": "KPIs Principales",
        "endpoint": "/api/v1/dashboard/kpis-principales",
        "metodo": "GET",
        "requiere_auth": True,
        "verificar": ["total_prestamos", "creditos_nuevos_mes", "total_clientes", "total_morosidad_usd"]
    },
    {
        "nombre": "Dashboard Admin",
        "endpoint": "/api/v1/dashboard/admin",
        "metodo": "GET",
        "requiere_auth": True,
        "verificar": ["financieros", "meta_mensual", "evolucion_mensual"]
    },
    {
        "nombre": "Financiamiento Tendencia Mensual",
        "endpoint": "/api/v1/dashboard/financiamiento-tendencia-mensual",
        "metodo": "GET",
        "requiere_auth": True,
        "params": {"meses": "12"},
        "verificar": ["meses"]
    },
    {
        "nombre": "Préstamos por Concesionario",
        "endpoint": "/api/v1/dashboard/prestamos-por-concesionario",
        "metodo": "GET",
        "requiere_auth": True,
        "verificar": ["concesionarios"]
    },
    {
        "nombre": "Préstamos por Modelo",
        "endpoint": "/api/v1/dashboard/prestamos-por-modelo",
        "metodo": "GET",
        "requiere_auth": True,
        "verificar": ["modelos"]
    },
    {
        "nombre": "Financiamiento por Rangos",
        "endpoint": "/api/v1/dashboard/financiamiento-por-rangos",
        "metodo": "GET",
        "requiere_auth": True,
        "verificar": ["rangos", "total_prestamos"]
    },
    {
        "nombre": "Composición Morosidad",
        "endpoint": "/api/v1/dashboard/composicion-morosidad",
        "metodo": "GET",
        "requiere_auth": True,
        "verificar": ["puntos", "total_morosidad"]
    },
    {
        "nombre": "Cobranzas Mensuales",
        "endpoint": "/api/v1/dashboard/cobranzas-mensuales",
        "metodo": "GET",
        "requiere_auth": True,
        "verificar": ["meses"]
    },
    {
        "nombre": "Cobranzas Semanales",
        "endpoint": "/api/v1/dashboard/cobranzas-semanales",
        "metodo": "GET",
        "requiere_auth": True,
        "params": {"semanas": "12"},
        "verificar": ["semanas"]
    },
    {
        "nombre": "Morosidad por Analista",
        "endpoint": "/api/v1/dashboard/morosidad-por-analista",
        "metodo": "GET",
        "requiere_auth": True,
        "verificar": ["analistas"]
    },
    {
        "nombre": "Evolución Morosidad",
        "endpoint": "/api/v1/dashboard/evolucion-morosidad",
        "metodo": "GET",
        "requiere_auth": True,
        "params": {"meses": "12"},
        "verificar": ["meses"]
    },
    {
        "nombre": "Evolución Pagos",
        "endpoint": "/api/v1/dashboard/evolucion-pagos",
        "metodo": "GET",
        "requiere_auth": True,
        "params": {"meses": "12"},
        "verificar": ["meses"]
    },
    {
        "nombre": "Evolución General Mensual",
        "endpoint": "/api/v1/dashboard/evolucion-general-mensual",
        "metodo": "GET",
        "requiere_auth": True,
        "verificar": ["meses"]
    },
    {
        "nombre": "Opciones Filtros",
        "endpoint": "/api/v1/dashboard/opciones-filtros",
        "metodo": "GET",
        "requiere_auth": True,
        "verificar": ["analistas", "concesionarios", "modelos"]
    },
]

class AuditoriaDashboard:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Dashboard-Auditoria/1.0',
            'Accept': 'application/json'
        })
        if token:
            self.session.headers.update({
                'Authorization': f'Bearer {token}'
            })
        self.resultados = {
            "fecha_auditoria": datetime.now().isoformat(),
            "url_base": base_url,
            "endpoints_verificados": [],
            "resumen": {
                "total_endpoints": len(ENDPOINTS_AUDITORIA),
                "exitosos": 0,
                "fallidos": 0,
                "con_errores": 0,
                "tiempo_promedio": 0.0
            }
        }

    def verificar_endpoint(self, endpoint_info: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica un endpoint individual"""
        nombre = endpoint_info["nombre"]
        endpoint = endpoint_info["endpoint"]
        metodo = endpoint_info.get("metodo", "GET")
        requiere_auth = endpoint_info.get("requiere_auth", False)
        params = endpoint_info.get("params", {})
        verificar_campos = endpoint_info.get("verificar", [])
        
        url = urljoin(self.base_url, endpoint)
        
        resultado = {
            "nombre": nombre,
            "endpoint": endpoint,
            "url": url,
            "status_code": None,
            "tiempo_respuesta_ms": 0,
            "exitoso": False,
            "error": None,
            "datos_presentes": [],
            "datos_faltantes": [],
            "tamano_respuesta_kb": 0
        }
        
        try:
            start_time = time.time()
            
            if metodo == "GET":
                response = self.session.get(
                    url,
                    params=params,
                    timeout=REQUEST_TIMEOUT
                )
            else:
                response = self.session.request(
                    metodo,
                    url,
                    params=params,
                    timeout=REQUEST_TIMEOUT
                )
            
            tiempo_respuesta = (time.time() - start_time) * 1000
            resultado["tiempo_respuesta_ms"] = round(tiempo_respuesta, 2)
            resultado["status_code"] = response.status_code
            resultado["tamano_respuesta_kb"] = round(len(response.content) / 1024, 2)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    resultado["exitoso"] = True
                    
                    # Verificar campos requeridos
                    for campo in verificar_campos:
                        if self._campo_presente(data, campo):
                            resultado["datos_presentes"].append(campo)
                        else:
                            resultado["datos_faltantes"].append(campo)
                    
                    # Verificar que haya datos
                    if isinstance(data, dict):
                        if "meses" in data and isinstance(data["meses"], list):
                            resultado["cantidad_meses"] = len(data["meses"])
                        if "concesionarios" in data and isinstance(data["concesionarios"], list):
                            resultado["cantidad_concesionarios"] = len(data["concesionarios"])
                        if "modelos" in data and isinstance(data["modelos"], list):
                            resultado["cantidad_modelos"] = len(data["modelos"])
                        if "analistas" in data and isinstance(data["analistas"], list):
                            resultado["cantidad_analistas"] = len(data["analistas"])
                        if "semanas" in data and isinstance(data["semanas"], list):
                            resultado["cantidad_semanas"] = len(data["semanas"])
                        if "puntos" in data and isinstance(data["puntos"], list):
                            resultado["cantidad_puntos"] = len(data["puntos"])
                    
                except json.JSONDecodeError as e:
                    resultado["error"] = f"Error parseando JSON: {str(e)}"
                    resultado["exitoso"] = False
            elif response.status_code == 401:
                resultado["error"] = "No autorizado - Token requerido o inválido"
                resultado["exitoso"] = False
            elif response.status_code == 403:
                resultado["error"] = "Acceso denegado"
                resultado["exitoso"] = False
            elif response.status_code == 404:
                resultado["error"] = "Endpoint no encontrado"
                resultado["exitoso"] = False
            elif response.status_code >= 500:
                resultado["error"] = f"Error del servidor: {response.status_code}"
                resultado["exitoso"] = False
            else:
                resultado["error"] = f"Código de estado inesperado: {response.status_code}"
                resultado["exitoso"] = False
                
        except requests.exceptions.Timeout:
            resultado["error"] = f"Timeout después de {REQUEST_TIMEOUT}s"
            resultado["exitoso"] = False
        except requests.exceptions.ConnectionError as e:
            resultado["error"] = f"Error de conexión: {str(e)}"
            resultado["exitoso"] = False
        except Exception as e:
            resultado["error"] = f"Error inesperado: {type(e).__name__}: {str(e)}"
            resultado["exitoso"] = False
        
        return resultado

    def _campo_presente(self, data: Any, campo: str) -> bool:
        """Verifica si un campo está presente en los datos"""
        if isinstance(data, dict):
            if campo in data:
                valor = data[campo]
                if isinstance(valor, (list, dict)):
                    return len(valor) > 0 if isinstance(valor, list) else bool(valor)
                return valor is not None
            # Buscar recursivamente
            for key, value in data.items():
                if isinstance(value, dict) and self._campo_presente(value, campo):
                    return True
        return False

    def ejecutar_auditoria(self):
        """Ejecuta la auditoría completa"""
        print("=" * 80)
        print("AUDITORÍA INTEGRAL DEL DASHBOARD EN PRODUCCIÓN")
        print("=" * 80)
        print(f"\nURL Base: {self.base_url}")
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total de endpoints a verificar: {len(ENDPOINTS_AUDITORIA)}")
        
        tiempos_respuesta = []
        
        for i, endpoint_info in enumerate(ENDPOINTS_AUDITORIA, 1):
            print(f"\n[{i}/{len(ENDPOINTS_AUDITORIA)}] Verificando: {endpoint_info['nombre']}")
            print(f"  Endpoint: {endpoint_info['endpoint']}")
            
            resultado = self.verificar_endpoint(endpoint_info)
            self.resultados["endpoints_verificados"].append(resultado)
            
            if resultado["exitoso"]:
                self.resultados["resumen"]["exitosos"] += 1
                tiempos_respuesta.append(resultado["tiempo_respuesta_ms"])
                print(f"  [OK] Status: {resultado['status_code']}, Tiempo: {resultado['tiempo_respuesta_ms']}ms")
                if resultado.get("datos_presentes"):
                    print(f"  [OK] Datos presentes: {', '.join(resultado['datos_presentes'])}")
                if resultado.get("datos_faltantes"):
                    print(f"  [ADVERTENCIA] Datos faltantes: {', '.join(resultado['datos_faltantes'])}")
                if "cantidad_meses" in resultado:
                    print(f"  [INFO] Meses retornados: {resultado['cantidad_meses']}")
            else:
                self.resultados["resumen"]["fallidos"] += 1
                print(f"  [ERROR] {resultado.get('error', 'Error desconocido')}")
                if resultado.get("status_code"):
                    print(f"  [INFO] Status Code: {resultado['status_code']}")
        
        # Calcular tiempo promedio
        if tiempos_respuesta:
            self.resultados["resumen"]["tiempo_promedio"] = round(
                sum(tiempos_respuesta) / len(tiempos_respuesta), 2
            )
        
        # Generar resumen
        self._generar_resumen()

    def _generar_resumen(self):
        """Genera un resumen de la auditoría"""
        print("\n" + "=" * 80)
        print("RESUMEN DE AUDITORÍA")
        print("=" * 80)
        
        resumen = self.resultados["resumen"]
        total = resumen["total_endpoints"]
        exitosos = resumen["exitosos"]
        fallidos = resumen["fallidos"]
        
        print(f"\nTotal de endpoints verificados: {total}")
        print(f"Endpoints exitosos: {exitosos} ({exitosos/total*100:.1f}%)")
        print(f"Endpoints fallidos: {fallidos} ({fallidos/total*100:.1f}%)")
        print(f"Tiempo promedio de respuesta: {resumen['tiempo_promedio']}ms")
        
        # Endpoints con problemas
        endpoints_con_problemas = [
            e for e in self.resultados["endpoints_verificados"]
            if not e["exitoso"] or e.get("datos_faltantes")
        ]
        
        if endpoints_con_problemas:
            print("\n[ADVERTENCIA] Endpoints con problemas:")
            for endpoint in endpoints_con_problemas:
                print(f"  - {endpoint['nombre']} ({endpoint['endpoint']})")
                if endpoint.get("error"):
                    print(f"    Error: {endpoint['error']}")
                if endpoint.get("datos_faltantes"):
                    print(f"    Datos faltantes: {', '.join(endpoint['datos_faltantes'])}")
        
        # Endpoints lentos (> 5 segundos)
        endpoints_lentos = [
            e for e in self.resultados["endpoints_verificados"]
            if e.get("tiempo_respuesta_ms", 0) > 5000
        ]
        
        if endpoints_lentos:
            print("\n[ADVERTENCIA] Endpoints con tiempo de respuesta > 5s:")
            for endpoint in endpoints_lentos:
                print(f"  - {endpoint['nombre']}: {endpoint['tiempo_respuesta_ms']}ms")
        
        # Verificar conectividad de base de datos
        health_endpoint = next(
            (e for e in self.resultados["endpoints_verificados"] if e["nombre"] == "Health Check"),
            None
        )
        
        if health_endpoint and health_endpoint["exitoso"]:
            print("\n[OK] Health Check disponible")
        else:
            print("\n[ERROR] Health Check no disponible o con errores")
        
        # Estado general
        if exitosos == total:
            print("\n[OK] Todos los endpoints están funcionando correctamente")
        elif exitosos >= total * 0.8:
            print("\n[ADVERTENCIA] La mayoría de los endpoints funcionan, pero hay algunos problemas")
        else:
            print("\n[ERROR] Muchos endpoints tienen problemas - Revisar urgentemente")

    def guardar_resultados(self, archivo: str = "auditoria_dashboard_produccion.json"):
        """Guarda los resultados en un archivo JSON"""
        ruta_archivo = Path(__file__).parent.parent / "Documentos" / "Auditorias" / archivo
        ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
        
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, indent=2, ensure_ascii=False)
        
        print(f"\n[INFO] Resultados guardados en: {ruta_archivo}")


def main():
    """Función principal"""
    print("Iniciando auditoría del dashboard en producción...")
    print(f"URL: {BASE_URL}")
    
    # Nota: Para endpoints que requieren autenticación, necesitarías un token
    # Por ahora verificamos los endpoints públicos primero
    auditoria = AuditoriaDashboard(BASE_URL)
    
    try:
        auditoria.ejecutar_auditoria()
        auditoria.guardar_resultados()
        
        # Retornar código de salida apropiado
        resumen = auditoria.resultados["resumen"]
        if resumen["exitosos"] == resumen["total_endpoints"]:
            return 0
        elif resumen["exitosos"] >= resumen["total_endpoints"] * 0.8:
            return 1
        else:
            return 2
            
    except KeyboardInterrupt:
        print("\n[INFO] Auditoría interrumpida por el usuario")
        return 130
    except Exception as e:
        print(f"\n[ERROR] Error inesperado durante la auditoría: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
