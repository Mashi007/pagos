"""
Auditoría Integral Completa del Dashboard en Producción
Verifica conectividad, estructura, frontend, y genera reporte completo
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_URL = "https://rapicredit.onrender.com"
REQUEST_TIMEOUT = 30

class AuditoriaCompletaDashboard:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/json,application/xhtml+xml,*/*'
        })
        self.resultados = {
            "fecha_auditoria": datetime.now().isoformat(),
            "url_base": base_url,
            "conectividad": {},
            "health_checks": {},
            "frontend": {},
            "estructura": {},
            "recomendaciones": []
        }

    def verificar_conectividad(self):
        """Verifica conectividad básica"""
        print("\n" + "=" * 80)
        print("1. VERIFICACIÓN DE CONECTIVIDAD")
        print("=" * 80)
        
        try:
            start_time = time.time()
            response = self.session.get(self.base_url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            tiempo_respuesta = (time.time() - start_time) * 1000
            
            self.resultados["conectividad"] = {
                "accesible": response.status_code == 200,
                "status_code": response.status_code,
                "tiempo_respuesta_ms": round(tiempo_respuesta, 2),
                "url_final": response.url,
                "redirecciones": len(response.history)
            }
            
            if response.status_code == 200:
                print(f"[OK] Dashboard accesible - Status: {response.status_code}")
                print(f"[OK] Tiempo de respuesta: {tiempo_respuesta:.2f}ms")
                print(f"[OK] URL final: {response.url}")
            else:
                print(f"[ADVERTENCIA] Status code: {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.resultados["conectividad"]["accesible"] = False
            self.resultados["conectividad"]["error"] = "Timeout"
            print("[ERROR] Timeout al conectar")
        except requests.exceptions.ConnectionError as e:
            self.resultados["conectividad"]["accesible"] = False
            self.resultados["conectividad"]["error"] = str(e)
            print(f"[ERROR] Error de conexión: {e}")
        except Exception as e:
            self.resultados["conectividad"]["accesible"] = False
            self.resultados["conectividad"]["error"] = str(e)
            print(f"[ERROR] Error inesperado: {e}")

    def verificar_health_checks(self):
        """Verifica endpoints de health check"""
        print("\n" + "=" * 80)
        print("2. VERIFICACIÓN DE HEALTH CHECKS")
        print("=" * 80)
        
        health_endpoints = [
            ("/api/v1/health", "Health Check General"),
            ("/api/v1/health/ready", "Health Check Ready"),
            ("/api/v1/health/render", "Health Check Render")
        ]
        
        resultados_health = {}
        
        for endpoint, nombre in health_endpoints:
            url = urljoin(self.base_url, endpoint)
            try:
                start_time = time.time()
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                tiempo_respuesta = (time.time() - start_time) * 1000
                
                resultado = {
                    "status_code": response.status_code,
                    "tiempo_respuesta_ms": round(tiempo_respuesta, 2),
                    "exitoso": response.status_code == 200
                }
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        resultado["datos"] = data
                        
                        # Verificar estado de base de datos
                        if "database" in data:
                            db_status = data["database"]
                            if isinstance(db_status, dict):
                                resultado["database_connected"] = db_status.get("status") or db_status.get("connected", False)
                            else:
                                resultado["database_connected"] = bool(db_status)
                        
                        print(f"[OK] {nombre}: Status {response.status_code}, Tiempo: {tiempo_respuesta:.2f}ms")
                        if resultado.get("database_connected"):
                            print(f"  [OK] Base de datos conectada")
                        else:
                            print(f"  [ADVERTENCIA] Estado de base de datos no confirmado")
                    except json.JSONDecodeError:
                        resultado["error"] = "Respuesta no es JSON válido"
                        print(f"[ADVERTENCIA] {nombre}: Respuesta no es JSON")
                else:
                    resultado["error"] = f"Status code: {response.status_code}"
                    print(f"[ADVERTENCIA] {nombre}: Status {response.status_code}")
                
                resultados_health[endpoint] = resultado
                
            except Exception as e:
                resultados_health[endpoint] = {
                    "exitoso": False,
                    "error": str(e)
                }
                print(f"[ERROR] {nombre}: {e}")
        
        self.resultados["health_checks"] = resultados_health

    def verificar_frontend(self):
        """Verifica el frontend del dashboard"""
        print("\n" + "=" * 80)
        print("3. VERIFICACIÓN DEL FRONTEND")
        print("=" * 80)
        
        dashboard_url = urljoin(self.base_url, "/dashboard/menu")
        
        try:
            start_time = time.time()
            response = self.session.get(dashboard_url, timeout=REQUEST_TIMEOUT)
            tiempo_respuesta = (time.time() - start_time) * 1000
            
            resultado_frontend = {
                "url": dashboard_url,
                "status_code": response.status_code,
                "tiempo_respuesta_ms": round(tiempo_respuesta, 2),
                "tamano_kb": round(len(response.content) / 1024, 2),
                "accesible": response.status_code == 200
            }
            
            if response.status_code == 200:
                print(f"[OK] Frontend accesible - Status: {response.status_code}")
                print(f"[OK] Tiempo de carga: {tiempo_respuesta:.2f}ms")
                print(f"[OK] Tamaño: {resultado_frontend['tamano_kb']} KB")
                
                # Analizar HTML
                try:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Verificar elementos clave
                    titulo = soup.find('title')
                    resultado_frontend["titulo"] = titulo.get_text() if titulo else None
                    
                    # Verificar scripts
                    scripts = soup.find_all('script', src=True)
                    resultado_frontend["scripts_externos"] = len(scripts)
                    
                    # Verificar si hay errores en el HTML
                    errores_html = []
                    if not titulo:
                        errores_html.append("Sin título")
                    
                    resultado_frontend["errores_html"] = errores_html
                    
                    print(f"  [INFO] Título: {resultado_frontend['titulo']}")
                    print(f"  [INFO] Scripts externos: {resultado_frontend['scripts_externos']}")
                    
                except Exception as e:
                    resultado_frontend["error_analisis"] = str(e)
                    print(f"  [ADVERTENCIA] Error analizando HTML: {e}")
            else:
                print(f"[ERROR] Frontend no accesible - Status: {response.status_code}")
                resultado_frontend["error"] = f"Status code: {response.status_code}"
            
            self.resultados["frontend"] = resultado_frontend
            
        except Exception as e:
            self.resultados["frontend"] = {
                "accesible": False,
                "error": str(e)
            }
            print(f"[ERROR] Error verificando frontend: {e}")

    def verificar_estructura_api(self):
        """Verifica la estructura de la API (sin autenticación)"""
        print("\n" + "=" * 80)
        print("4. VERIFICACIÓN DE ESTRUCTURA DE API")
        print("=" * 80)
        
        # Endpoints que no requieren autenticación o dan información útil incluso con 403
        endpoints_verificar = [
            "/api/v1/health",
            "/api/v1/health/ready",
            "/api/v1/dashboard/kpis-principales",
            "/api/v1/dashboard/financiamiento-tendencia-mensual?meses=12",
        ]
        
        estructura = {}
        
        for endpoint in endpoints_verificar:
            url = urljoin(self.base_url, endpoint)
            try:
                start_time = time.time()
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                tiempo_respuesta = (time.time() - start_time) * 1000
                
                estructura[endpoint] = {
                    "status_code": response.status_code,
                    "tiempo_respuesta_ms": round(tiempo_respuesta, 2),
                    "existe": response.status_code != 404,
                    "requiere_auth": response.status_code == 401 or response.status_code == 403
                }
                
                if response.status_code == 200:
                    print(f"[OK] {endpoint}: Disponible ({tiempo_respuesta:.2f}ms)")
                elif response.status_code in [401, 403]:
                    print(f"[INFO] {endpoint}: Requiere autenticación (Status {response.status_code})")
                elif response.status_code == 404:
                    print(f"[ERROR] {endpoint}: No encontrado")
                else:
                    print(f"[ADVERTENCIA] {endpoint}: Status {response.status_code}")
                    
            except Exception as e:
                estructura[endpoint] = {
                    "existe": False,
                    "error": str(e)
                }
                print(f"[ERROR] {endpoint}: {e}")
        
        self.resultados["estructura"] = estructura

    def generar_recomendaciones(self):
        """Genera recomendaciones basadas en los resultados"""
        print("\n" + "=" * 80)
        print("5. RECOMENDACIONES")
        print("=" * 80)
        
        recomendaciones = []
        
        # Verificar conectividad
        if not self.resultados["conectividad"].get("accesible"):
            recomendaciones.append({
                "prioridad": "ALTA",
                "categoria": "Conectividad",
                "descripcion": "El dashboard no es accesible. Verificar que el servicio esté corriendo.",
                "accion": "Verificar estado del servicio en Render.com"
            })
        
        # Verificar health checks
        health_ok = any(
            h.get("exitoso", False) 
            for h in self.resultados["health_checks"].values()
        )
        if not health_ok:
            recomendaciones.append({
                "prioridad": "ALTA",
                "categoria": "Health Checks",
                "descripcion": "Los health checks no están respondiendo correctamente.",
                "accion": "Verificar configuración de health checks en Render.com"
            })
        
        # Verificar base de datos
        db_connected = False
        for health in self.resultados["health_checks"].values():
            if health.get("database_connected"):
                db_connected = True
                break
        
        if not db_connected:
            recomendaciones.append({
                "prioridad": "ALTA",
                "categoria": "Base de Datos",
                "descripcion": "No se pudo confirmar la conexión a la base de datos.",
                "accion": "Verificar DATABASE_URL y conexión a PostgreSQL"
            })
        
        # Verificar frontend
        if not self.resultados["frontend"].get("accesible"):
            recomendaciones.append({
                "prioridad": "ALTA",
                "categoria": "Frontend",
                "descripcion": "El frontend del dashboard no es accesible.",
                "accion": "Verificar build y deployment del frontend"
            })
        
        # Verificar tiempos de respuesta
        tiempos = []
        for health in self.resultados["health_checks"].values():
            if "tiempo_respuesta_ms" in health:
                tiempos.append(health["tiempo_respuesta_ms"])
        
        if tiempos:
            tiempo_promedio = sum(tiempos) / len(tiempos)
            if tiempo_promedio > 3000:
                recomendaciones.append({
                    "prioridad": "MEDIA",
                    "categoria": "Rendimiento",
                    "descripcion": f"Tiempo de respuesta promedio alto: {tiempo_promedio:.2f}ms",
                    "accion": "Optimizar queries y considerar cache adicional"
                })
        
        self.resultados["recomendaciones"] = recomendaciones
        
        if recomendaciones:
            print("\nRecomendaciones generadas:")
            for i, rec in enumerate(recomendaciones, 1):
                print(f"\n{i}. [{rec['prioridad']}] {rec['categoria']}")
                print(f"   Descripción: {rec['descripcion']}")
                print(f"   Acción: {rec['accion']}")
        else:
            print("\n[OK] No se encontraron problemas críticos")

    def generar_resumen(self):
        """Genera resumen ejecutivo"""
        print("\n" + "=" * 80)
        print("RESUMEN EJECUTIVO")
        print("=" * 80)
        
        conectividad_ok = self.resultados["conectividad"].get("accesible", False)
        health_ok = any(h.get("exitoso", False) for h in self.resultados["health_checks"].values())
        frontend_ok = self.resultados["frontend"].get("accesible", False)
        
        print(f"\nConectividad: {'[OK]' if conectividad_ok else '[ERROR]'}")
        print(f"Health Checks: {'[OK]' if health_ok else '[ERROR]'}")
        print(f"Frontend: {'[OK]' if frontend_ok else '[ERROR]'}")
        
        # Estado general
        if conectividad_ok and health_ok and frontend_ok:
            print("\n[OK] Dashboard operativo y accesible")
            estado = "OPERATIVO"
        elif conectividad_ok and health_ok:
            print("\n[ADVERTENCIA] Dashboard accesible pero frontend puede tener problemas")
            estado = "PARCIALMENTE OPERATIVO"
        else:
            print("\n[ERROR] Dashboard tiene problemas críticos")
            estado = "CON PROBLEMAS"
        
        self.resultados["estado_general"] = estado
        print(f"\nEstado General: {estado}")

    def ejecutar_auditoria_completa(self):
        """Ejecuta la auditoría completa"""
        print("=" * 80)
        print("AUDITORÍA INTEGRAL DEL DASHBOARD EN PRODUCCIÓN")
        print("=" * 80)
        print(f"\nURL Base: {self.base_url}")
        print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.verificar_conectividad()
        self.verificar_health_checks()
        self.verificar_frontend()
        self.verificar_estructura_api()
        self.generar_recomendaciones()
        self.generar_resumen()

    def guardar_resultados(self, archivo: str = "auditoria_integral_dashboard_produccion.json"):
        """Guarda los resultados en un archivo JSON"""
        ruta_archivo = Path(__file__).parent.parent / "Documentos" / "Auditorias" / archivo
        ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
        
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, indent=2, ensure_ascii=False)
        
        print(f"\n[INFO] Resultados guardados en: {ruta_archivo}")
        
        # También generar reporte en markdown
        self.generar_reporte_markdown()

    def generar_reporte_markdown(self):
        """Genera un reporte en formato Markdown"""
        ruta_md = Path(__file__).parent.parent / "Documentos" / "Auditorias" / "AUDITORIA_INTEGRAL_DASHBOARD_PRODUCCION.md"
        
        with open(ruta_md, 'w', encoding='utf-8') as f:
            f.write("# 🔍 AUDITORÍA INTEGRAL DEL DASHBOARD EN PRODUCCIÓN\n\n")
            f.write(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**URL:** {self.base_url}\n\n")
            
            f.write("## 📊 RESUMEN EJECUTIVO\n\n")
            f.write(f"**Estado General:** {self.resultados.get('estado_general', 'NO DISPONIBLE')}\n\n")
            
            conectividad = self.resultados["conectividad"]
            f.write("### Conectividad\n")
            f.write(f"- **Accesible:** {'✅ Sí' if conectividad.get('accesible') else '❌ No'}\n")
            if conectividad.get('tiempo_respuesta_ms'):
                f.write(f"- **Tiempo de respuesta:** {conectividad['tiempo_respuesta_ms']}ms\n")
            f.write("\n")
            
            f.write("### Health Checks\n")
            for endpoint, resultado in self.resultados["health_checks"].items():
                estado = "✅" if resultado.get("exitoso") else "❌"
                f.write(f"- **{endpoint}:** {estado} ")
                if resultado.get("tiempo_respuesta_ms"):
                    f.write(f"({resultado['tiempo_respuesta_ms']}ms)")
                f.write("\n")
            f.write("\n")
            
            frontend = self.resultados["frontend"]
            f.write("### Frontend\n")
            f.write(f"- **Accesible:** {'✅ Sí' if frontend.get('accesible') else '❌ No'}\n")
            if frontend.get('tiempo_respuesta_ms'):
                f.write(f"- **Tiempo de carga:** {frontend['tiempo_respuesta_ms']}ms\n")
            f.write("\n")
            
            if self.resultados["recomendaciones"]:
                f.write("## ⚠️ RECOMENDACIONES\n\n")
                for rec in self.resultados["recomendaciones"]:
                    f.write(f"### [{rec['prioridad']}] {rec['categoria']}\n")
                    f.write(f"- **Descripción:** {rec['descripcion']}\n")
                    f.write(f"- **Acción:** {rec['accion']}\n\n")
        
        print(f"[INFO] Reporte Markdown guardado en: {ruta_md}")


def main():
    """Función principal"""
    try:
        auditoria = AuditoriaCompletaDashboard(BASE_URL)
        auditoria.ejecutar_auditoria_completa()
        auditoria.guardar_resultados()
        
        # Código de salida basado en el estado
        estado = auditoria.resultados.get("estado_general", "CON PROBLEMAS")
        if estado == "OPERATIVO":
            return 0
        elif estado == "PARCIALMENTE OPERATIVO":
            return 1
        else:
            return 2
            
    except KeyboardInterrupt:
        print("\n[INFO] Auditoría interrumpida")
        return 130
    except Exception as e:
        print(f"\n[ERROR] Error inesperado: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Instalar BeautifulSoup4 si no está disponible
    try:
        import bs4
    except ImportError:
        print("[ADVERTENCIA] BeautifulSoup4 no está instalado. Instalando...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4", "-q"])
    
    sys.exit(main())
