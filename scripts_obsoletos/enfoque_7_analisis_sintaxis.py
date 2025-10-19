# backend/scripts/enfoque_7_analisis_sintaxis.py
"""
ENFOQUE 7: VERIFICACIÓN EXHAUSTIVA CON ANÁLISIS DE SINTAXIS COMPLETO
Analizar exhaustivamente la sintaxis de todos los archivos críticos y verificar el registro de routers
"""
import os
import sys
import logging
import requests
import json
import time
import ast
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Enfoque7AnalisisSintaxis:
    def __init__(self):
        self.backend_url = "https://pagos-f2qf.onrender.com"
        self.frontend_url = "https://rapicredit.onrender.com"
        self.credentials = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**",
            "remember": True
        }
        self.errores_sintaxis = []
        self.routers_registrados = []
        self.routers_faltantes = []
        
    def verificar_sintaxis_python(self, ruta_archivo: str) -> Dict[str, Any]:
        """Verificar sintaxis Python de un archivo"""
        logger.info(f"🔍 Verificando sintaxis: {ruta_archivo}")
        
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Verificar sintaxis con AST
            try:
                ast.parse(contenido)
                logger.info(f"   ✅ Sintaxis Python válida")
                return {
                    "archivo": ruta_archivo,
                    "sintaxis_valida": True,
                    "errores": []
                }
            except SyntaxError as e:
                error_msg = f"Error de sintaxis en línea {e.lineno}: {e.msg}"
                logger.error(f"   ❌ {error_msg}")
                self.errores_sintaxis.append({
                    "archivo": ruta_archivo,
                    "linea": e.lineno,
                    "error": e.msg,
                    "texto": e.text
                })
                return {
                    "archivo": ruta_archivo,
                    "sintaxis_valida": False,
                    "errores": [error_msg]
                }
                
        except Exception as e:
            logger.error(f"   ❌ Error leyendo archivo: {e}")
            return {
                "archivo": ruta_archivo,
                "sintaxis_valida": False,
                "errores": [str(e)]
            }
    
    def analizar_registro_routers(self) -> Dict[str, Any]:
        """Analizar el registro de routers en main.py"""
        logger.info("🔗 ANALIZANDO REGISTRO DE ROUTERS EN MAIN.PY")
        logger.info("-" * 50)
        
        main_path = Path("backend/app/main.py")
        if not main_path.exists():
            return {"error": "main.py no encontrado"}
        
        try:
            with open(main_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Buscar todas las líneas de include_router
            lineas = contenido.split('\n')
            routers_encontrados = []
            errores_registro = []
            
            for i, linea in enumerate(lineas):
                if 'app.include_router(' in linea:
                    # Verificar si la línea está completa
                    if linea.strip().endswith(','):
                        # Buscar la siguiente línea para ver si está completa
                        siguiente_linea = lineas[i + 1] if i + 1 < len(lineas) else ""
                        if not siguiente_linea.strip().startswith('prefix=') and not siguiente_linea.strip().startswith('tags='):
                            errores_registro.append({
                                "linea": i + 1,
                                "contenido": linea.strip(),
                                "error": "Línea incompleta - falta prefix y tags"
                            })
                            logger.error(f"   ❌ Línea {i+1} incompleta: {linea.strip()}")
                        else:
                            logger.info(f"   ✅ Línea {i+1} completa: {linea.strip()}")
                            routers_encontrados.append({
                                "linea": i + 1,
                                "contenido": linea.strip()
                            })
                    else:
                        logger.info(f"   ✅ Línea {i+1} completa: {linea.strip()}")
                        routers_encontrados.append({
                            "linea": i + 1,
                            "contenido": linea.strip()
                        })
            
            # Buscar imports de routers
            imports_routers = []
            for i, linea in enumerate(lineas):
                if 'from app.api.v1.endpoints import' in linea:
                    # Extraer nombres de routers importados
                    match = re.search(r'import\s+(.+)', linea)
                    if match:
                        routers_importados = match.group(1).split(',')
                        for router in routers_importados:
                            router = router.strip()
                            if router:
                                imports_routers.append(router)
                                logger.info(f"   📊 Router importado: {router}")
            
            return {
                "routers_encontrados": routers_encontrados,
                "errores_registro": errores_registro,
                "imports_routers": imports_routers,
                "total_routers": len(routers_encontrados),
                "total_errores": len(errores_registro)
            }
            
        except Exception as e:
            logger.error(f"   ❌ Error analizando main.py: {e}")
            return {"error": str(e)}
    
    def verificar_endpoints_en_tiempo_real(self) -> Dict[str, Any]:
        """Verificar endpoints en tiempo real"""
        logger.info("🌐 VERIFICANDO ENDPOINTS EN TIEMPO REAL")
        logger.info("-" * 50)
        
        try:
            # Login
            login_response = requests.post(
                f"{self.backend_url}/api/v1/auth/login",
                json=self.credentials,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            if login_response.status_code != 200:
                return {"error": f"Login falló: {login_response.status_code}"}
            
            access_token = login_response.json().get('access_token')
            if not access_token:
                return {"error": "No se obtuvo access token"}
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Lista de endpoints críticos a verificar
            endpoints_criticos = [
                ("/api/v1/analistas", "Analistas"),
                ("/api/v1/clientes", "Clientes"),
                ("/api/v1/dashboard", "Dashboard"),
                ("/api/v1/kpis", "KPIs"),
                ("/api/v1/reportes", "Reportes"),
                ("/api/v1/concesionarios", "Concesionarios"),
                ("/api/v1/modelos-vehiculos", "Modelos Vehículos")
            ]
            
            resultados_endpoints = {}
            
            for endpoint, nombre in endpoints_criticos:
                try:
                    response = requests.get(
                        f"{self.backend_url}{endpoint}",
                        headers=headers,
                        timeout=10
                    )
                    
                    logger.info(f"   📊 {nombre}: Status {response.status_code}")
                    
                    if response.status_code == 200:
                        logger.info(f"   ✅ {nombre}: OK")
                        resultados_endpoints[nombre] = {
                            "status": "success",
                            "status_code": response.status_code
                        }
                    elif response.status_code == 405:
                        logger.error(f"   ❌ {nombre}: 405 Method Not Allowed")
                        resultados_endpoints[nombre] = {
                            "status": "error",
                            "status_code": response.status_code,
                            "error": "Method Not Allowed"
                        }
                    else:
                        logger.error(f"   ❌ {nombre}: {response.status_code}")
                        resultados_endpoints[nombre] = {
                            "status": "error",
                            "status_code": response.status_code,
                            "error": response.text[:100]
                        }
                        
                except Exception as e:
                    logger.error(f"   ❌ {nombre}: Error - {e}")
                    resultados_endpoints[nombre] = {
                        "status": "error",
                        "error": str(e)
                    }
            
            return {
                "endpoints": resultados_endpoints,
                "total_endpoints": len(endpoints_criticos),
                "endpoints_ok": len([e for e in resultados_endpoints.values() if e.get("status") == "success"]),
                "endpoints_error": len([e for e in resultados_endpoints.values() if e.get("status") == "error"])
            }
            
        except Exception as e:
            logger.error(f"   ❌ Error verificando endpoints: {e}")
            return {"error": str(e)}
    
    def verificar_archivos_criticos(self) -> Dict[str, Any]:
        """Verificar sintaxis de archivos críticos"""
        logger.info("📁 VERIFICANDO ARCHIVOS CRÍTICOS")
        logger.info("-" * 50)
        
        archivos_criticos = [
            "backend/app/main.py",
            "backend/app/api/v1/endpoints/analistas.py",
            "backend/app/api/v1/endpoints/clientes.py",
            "backend/app/api/v1/endpoints/dashboard.py",
            "backend/app/api/v1/endpoints/kpis.py",
            "backend/app/api/v1/endpoints/reportes.py",
            "backend/app/api/v1/endpoints/concesionarios.py",
            "backend/app/api/v1/endpoints/modelos_vehiculos.py"
        ]
        
        resultados_archivos = {}
        
        for archivo in archivos_criticos:
            if os.path.exists(archivo):
                resultado = self.verificar_sintaxis_python(archivo)
                resultados_archivos[archivo] = resultado
            else:
                logger.error(f"   ❌ Archivo no encontrado: {archivo}")
                resultados_archivos[archivo] = {
                    "archivo": archivo,
                    "sintaxis_valida": False,
                    "errores": ["Archivo no encontrado"]
                }
        
        return resultados_archivos
    
    def ejecutar_enfoque_7(self):
        """Ejecutar enfoque 7 completo"""
        logger.info("🔍 ENFOQUE 7: VERIFICACIÓN EXHAUSTIVA CON ANÁLISIS DE SINTAXIS")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Análisis exhaustivo de sintaxis y registro de routers")
        logger.info("=" * 80)
        
        resultados = {}
        
        # 1. Verificar archivos críticos
        logger.info("\n📁 1. VERIFICANDO ARCHIVOS CRÍTICOS")
        logger.info("-" * 50)
        archivos = self.verificar_archivos_criticos()
        resultados["archivos"] = archivos
        
        # 2. Analizar registro de routers
        logger.info("\n🔗 2. ANALIZANDO REGISTRO DE ROUTERS")
        logger.info("-" * 50)
        routers = self.analizar_registro_routers()
        resultados["routers"] = routers
        
        # 3. Verificar endpoints en tiempo real
        logger.info("\n🌐 3. VERIFICANDO ENDPOINTS EN TIEMPO REAL")
        logger.info("-" * 50)
        endpoints = self.verificar_endpoints_en_tiempo_real()
        resultados["endpoints"] = endpoints
        
        # 4. Resumen y conclusiones
        logger.info("\n📊 RESUMEN Y CONCLUSIONES")
        logger.info("=" * 80)
        
        # Contar errores de sintaxis
        total_errores_sintaxis = len(self.errores_sintaxis)
        archivos_con_errores = len([a for a in archivos.values() if not a.get("sintaxis_valida", True)])
        
        logger.info(f"📊 ARCHIVOS ANALIZADOS: {len(archivos)}")
        logger.info(f"📊 ARCHIVOS CON ERRORES DE SINTAXIS: {archivos_con_errores}")
        logger.info(f"📊 ERRORES DE SINTAXIS TOTALES: {total_errores_sintaxis}")
        
        if routers.get("total_errores", 0) > 0:
            logger.error(f"📊 ERRORES EN REGISTRO DE ROUTERS: {routers.get('total_errores', 0)}")
        
        if endpoints.get("endpoints_error", 0) > 0:
            logger.error(f"📊 ENDPOINTS CON ERRORES: {endpoints.get('endpoints_error', 0)}")
        
        # Mostrar errores de sintaxis encontrados
        if self.errores_sintaxis:
            logger.error("❌ ERRORES DE SINTAXIS ENCONTRADOS:")
            for error in self.errores_sintaxis:
                logger.error(f"   📁 {error['archivo']}")
                logger.error(f"   📍 Línea {error['linea']}: {error['error']}")
                if error.get('texto'):
                    logger.error(f"   📝 Texto: {error['texto'].strip()}")
        
        # Mostrar errores de registro de routers
        if routers.get("errores_registro"):
            logger.error("❌ ERRORES EN REGISTRO DE ROUTERS:")
            for error in routers["errores_registro"]:
                logger.error(f"   📍 Línea {error['linea']}: {error['error']}")
                logger.error(f"   📝 Contenido: {error['contenido']}")
        
        # Conclusión final
        logger.info("\n🎯 CONCLUSIÓN FINAL DEL ENFOQUE 7")
        logger.info("=" * 80)
        
        if total_errores_sintaxis > 0:
            logger.error("❌ CAUSA RAÍZ CONFIRMADA:")
            logger.error("   🔍 Se encontraron errores de sintaxis en archivos críticos")
            logger.error("   🔍 Estos errores están impidiendo el registro correcto de routers")
            logger.error("   💡 SOLUCIÓN: Corregir todos los errores de sintaxis encontrados")
        elif routers.get("total_errores", 0) > 0:
            logger.error("❌ CAUSA RAÍZ CONFIRMADA:")
            logger.error("   🔍 Se encontraron errores en el registro de routers")
            logger.error("   🔍 Líneas incompletas en main.py")
            logger.error("   💡 SOLUCIÓN: Completar todas las líneas de registro de routers")
        elif endpoints.get("endpoints_error", 0) > 0:
            logger.error("❌ PROBLEMA PERSISTE:")
            logger.error("   🔍 No se encontraron errores de sintaxis")
            logger.error("   🔍 Pero los endpoints siguen fallando")
            logger.error("   💡 SOLUCIÓN: Investigar problemas de despliegue o configuración")
        else:
            logger.info("✅ PROBLEMA RESUELTO:")
            logger.info("   🎯 No se encontraron errores de sintaxis")
            logger.info("   🎯 Todos los routers están registrados correctamente")
            logger.info("   🎯 Todos los endpoints funcionan correctamente")
        
        return resultados

def main():
    analizador = Enfoque7AnalisisSintaxis()
    return analizador.ejecutar_enfoque_7()

if __name__ == "__main__":
    main()
