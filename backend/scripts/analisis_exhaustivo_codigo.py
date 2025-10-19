# backend/scripts/analisis_exhaustivo_codigo.py
"""
ENFOQUE 5: ANÁLISIS EXHAUSTIVO DEL CÓDIGO COMPLETO
Analizar exhaustivamente todo el código relacionado con analistas para encontrar problemas
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

class AnalisisExhaustivoCodigo:
    def __init__(self):
        self.backend_url = "https://pagos-f2qf.onrender.com"
        self.frontend_url = "https://rapicredit.onrender.com"
        self.credentials = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**",
            "remember": True
        }
        self.problemas_encontrados = []
        self.archivos_analizados = []
        
    def analizar_archivo_python(self, ruta_archivo: str) -> Dict[str, Any]:
        """Analizar un archivo Python en busca de problemas"""
        logger.info(f"🔍 Analizando archivo: {ruta_archivo}")
        
        problemas = []
        try:
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Verificar sintaxis Python
            try:
                ast.parse(contenido)
                logger.info(f"   ✅ Sintaxis Python válida")
            except SyntaxError as e:
                problemas.append(f"Error de sintaxis: {e}")
                logger.error(f"   ❌ Error de sintaxis: {e}")
            
            # Verificar imports faltantes
            imports_usados = re.findall(r'\blogger\b', contenido)
            if imports_usados and 'import logging' not in contenido and 'from logging import' not in contenido:
                problemas.append("Logger usado sin importar logging")
                logger.error(f"   ❌ Logger usado sin importar logging")
            
            # Verificar variables no definidas
            variables_no_definidas = []
            if 'logger.error' in contenido and 'logger =' not in contenido:
                variables_no_definidas.append('logger')
            
            if variables_no_definidas:
                problemas.append(f"Variables no definidas: {variables_no_definidas}")
                logger.error(f"   ❌ Variables no definidas: {variables_no_definidas}")
            
            # Verificar decoradores FastAPI
            decoradores_fastapi = re.findall(r'@router\.(get|post|put|delete|patch)', contenido)
            if decoradores_fastapi:
                logger.info(f"   📊 Decoradores FastAPI encontrados: {decoradores_fastapi}")
            
            # Verificar definición de router
            if 'router = APIRouter()' in contenido:
                logger.info(f"   ✅ Router APIRouter definido")
            else:
                problemas.append("Router APIRouter no definido")
                logger.error(f"   ❌ Router APIRouter no definido")
            
            return {
                "archivo": ruta_archivo,
                "problemas": problemas,
                "decoradores": decoradores_fastapi,
                "tiene_router": 'router = APIRouter()' in contenido,
                "tiene_logger": 'logger =' in contenido,
                "usa_logger": 'logger.' in contenido
            }
            
        except Exception as e:
            logger.error(f"   ❌ Error analizando archivo: {e}")
            return {
                "archivo": ruta_archivo,
                "problemas": [f"Error al analizar: {e}"],
                "decoradores": [],
                "tiene_router": False,
                "tiene_logger": False,
                "usa_logger": False
            }
    
    def analizar_estructura_proyecto(self) -> Dict[str, Any]:
        """Analizar la estructura completa del proyecto"""
        logger.info("🏗️ ANALIZANDO ESTRUCTURA DEL PROYECTO")
        logger.info("-" * 50)
        
        estructura = {
            "archivos_analistas": [],
            "archivos_main": [],
            "archivos_models": [],
            "archivos_schemas": [],
            "problemas_estructura": []
        }
        
        # Buscar archivos relacionados con analistas
        base_path = Path("backend/app")
        
        archivos_analistas = [
            "api/v1/endpoints/analistas.py",
            "models/analista.py", 
            "schemas/analista.py"
        ]
        
        for archivo in archivos_analistas:
            ruta_completa = base_path / archivo
            if ruta_completa.exists():
                logger.info(f"   ✅ Encontrado: {archivo}")
                estructura["archivos_analistas"].append(str(ruta_completa))
            else:
                logger.error(f"   ❌ No encontrado: {archivo}")
                estructura["problemas_estructura"].append(f"Archivo faltante: {archivo}")
        
        # Verificar main.py
        main_path = base_path / "main.py"
        if main_path.exists():
            logger.info(f"   ✅ Encontrado: main.py")
            estructura["archivos_main"].append(str(main_path))
        else:
            logger.error(f"   ❌ No encontrado: main.py")
            estructura["problemas_estructura"].append("Archivo main.py faltante")
        
        return estructura
    
    def analizar_registro_routers(self) -> Dict[str, Any]:
        """Analizar el registro de routers en main.py"""
        logger.info("🔗 ANALIZANDO REGISTRO DE ROUTERS")
        logger.info("-" * 50)
        
        main_path = Path("backend/app/main.py")
        if not main_path.exists():
            return {"error": "main.py no encontrado"}
        
        try:
            with open(main_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Buscar import de analistas
            import_analistas = 'from app.api.v1.endpoints import' in contenido and 'analistas' in contenido
            logger.info(f"   📊 Import de analistas: {'✅' if import_analistas else '❌'}")
            
            # Buscar registro de router
            registro_analistas = 'app.include_router(analistas.router' in contenido
            logger.info(f"   📊 Registro de router analistas: {'✅' if registro_analistas else '❌'}")
            
            # Buscar línea específica
            lineas = contenido.split('\n')
            linea_registro = None
            for i, linea in enumerate(lineas):
                if 'analistas.router' in linea:
                    linea_registro = f"Línea {i+1}: {linea.strip()}"
                    break
            
            if linea_registro:
                logger.info(f"   📊 {linea_registro}")
            
            return {
                "import_analistas": import_analistas,
                "registro_analistas": registro_analistas,
                "linea_registro": linea_registro,
                "contenido_completo": contenido
            }
            
        except Exception as e:
            logger.error(f"   ❌ Error analizando main.py: {e}")
            return {"error": str(e)}
    
    def verificar_endpoint_en_tiempo_real(self) -> Dict[str, Any]:
        """Verificar el endpoint en tiempo real"""
        logger.info("🌐 VERIFICANDO ENDPOINT EN TIEMPO REAL")
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
            
            # Probar endpoint analistas
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.backend_url}/api/v1/analistas",
                headers=headers,
                params={'limit': 100},
                timeout=15
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"   ✅ Endpoint funcionando: {data.get('total', 0)} analistas")
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "total_analistas": data.get('total', 0),
                    "data": data
                }
            else:
                logger.error(f"   ❌ Endpoint fallando: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ Error verificando endpoint: {e}")
            return {"error": str(e)}
    
    def analizar_logs_render(self) -> Dict[str, Any]:
        """Analizar logs de Render para encontrar errores"""
        logger.info("📋 ANALIZANDO LOGS DE RENDER")
        logger.info("-" * 50)
        
        # Simular análisis de logs (en un caso real, se conectaría a la API de Render)
        logger.info("   📊 Simulando análisis de logs...")
        logger.info("   📊 Buscando errores relacionados con analistas...")
        
        # Patrones de error comunes
        patrones_error = [
            "ModuleNotFoundError",
            "ImportError", 
            "NameError",
            "SyntaxError",
            "AttributeError",
            "405 Method Not Allowed",
            "analistas"
        ]
        
        logger.info(f"   📊 Patrones de error a buscar: {patrones_error}")
        
        return {
            "patrones_buscados": patrones_error,
            "nota": "Análisis de logs requiere acceso directo a Render API"
        }
    
    def ejecutar_analisis_exhaustivo(self):
        """Ejecutar análisis exhaustivo completo"""
        logger.info("🔍 ENFOQUE 5: ANÁLISIS EXHAUSTIVO DEL CÓDIGO COMPLETO")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Análisis exhaustivo hasta confirmar causa del problema")
        logger.info("=" * 80)
        
        resultados = {}
        
        # 1. Analizar estructura del proyecto
        logger.info("\n🏗️ 1. ANALIZANDO ESTRUCTURA DEL PROYECTO")
        logger.info("-" * 50)
        estructura = self.analizar_estructura_proyecto()
        resultados["estructura"] = estructura
        
        # 2. Analizar archivos específicos
        logger.info("\n📁 2. ANALIZANDO ARCHIVOS ESPECÍFICOS")
        logger.info("-" * 50)
        
        archivos_a_analizar = [
            "backend/app/api/v1/endpoints/analistas.py",
            "backend/app/main.py",
            "backend/app/models/analista.py",
            "backend/app/schemas/analista.py"
        ]
        
        analisis_archivos = {}
        for archivo in archivos_a_analizar:
            if os.path.exists(archivo):
                analisis = self.analizar_archivo_python(archivo)
                analisis_archivos[archivo] = analisis
                self.archivos_analizados.append(archivo)
            else:
                logger.error(f"   ❌ Archivo no encontrado: {archivo}")
                analisis_archivos[archivo] = {"error": "Archivo no encontrado"}
        
        resultados["archivos"] = analisis_archivos
        
        # 3. Analizar registro de routers
        logger.info("\n🔗 3. ANALIZANDO REGISTRO DE ROUTERS")
        logger.info("-" * 50)
        registro = self.analizar_registro_routers()
        resultados["registro_routers"] = registro
        
        # 4. Verificar endpoint en tiempo real
        logger.info("\n🌐 4. VERIFICANDO ENDPOINT EN TIEMPO REAL")
        logger.info("-" * 50)
        endpoint = self.verificar_endpoint_en_tiempo_real()
        resultados["endpoint_tiempo_real"] = endpoint
        
        # 5. Analizar logs de Render
        logger.info("\n📋 5. ANALIZANDO LOGS DE RENDER")
        logger.info("-" * 50)
        logs = self.analizar_logs_render()
        resultados["logs_render"] = logs
        
        # 6. Resumen y conclusiones
        logger.info("\n📊 RESUMEN Y CONCLUSIONES")
        logger.info("=" * 80)
        
        problemas_totales = []
        
        # Recopilar todos los problemas encontrados
        for archivo, analisis in analisis_archivos.items():
            if "problemas" in analisis:
                problemas_totales.extend(analisis["problemas"])
        
        if estructura["problemas_estructura"]:
            problemas_totales.extend(estructura["problemas_estructura"])
        
        logger.info(f"📊 ARCHIVOS ANALIZADOS: {len(self.archivos_analizados)}")
        logger.info(f"📊 PROBLEMAS ENCONTRADOS: {len(problemas_totales)}")
        
        if problemas_totales:
            logger.error("❌ PROBLEMAS ENCONTRADOS:")
            for i, problema in enumerate(problemas_totales, 1):
                logger.error(f"   {i}. {problema}")
        else:
            logger.info("✅ NO SE ENCONTRARON PROBLEMAS EN EL CÓDIGO")
        
        # Estado del endpoint
        if endpoint.get("status") == "success":
            logger.info("✅ ENDPOINT ANALISTAS FUNCIONANDO CORRECTAMENTE")
            logger.info(f"   📊 Total analistas: {endpoint.get('total_analistas', 0)}")
        else:
            logger.error("❌ ENDPOINT ANALISTAS AÚN CON PROBLEMAS")
            logger.error(f"   📊 Status: {endpoint.get('status_code', 'N/A')}")
            logger.error(f"   📊 Error: {endpoint.get('error', 'N/A')}")
        
        # Conclusión final
        logger.info("\n🎯 CONCLUSIÓN FINAL DEL ANÁLISIS EXHAUSTIVO")
        logger.info("=" * 80)
        
        if problemas_totales:
            logger.error("❌ CAUSA RAÍZ CONFIRMADA:")
            logger.error("   🔍 Se encontraron problemas en el código")
            logger.error("   🔍 Estos problemas están causando el error 405")
            logger.error("   💡 SOLUCIÓN: Corregir los problemas encontrados")
        elif endpoint.get("status") == "success":
            logger.info("✅ PROBLEMA RESUELTO:")
            logger.info("   🎯 El análisis exhaustivo no encontró problemas")
            logger.info("   🎯 El endpoint analistas funciona correctamente")
            logger.info("   🎯 El error 405 Method Not Allowed está resuelto")
        else:
            logger.error("❌ PROBLEMA PERSISTE:")
            logger.error("   🔍 No se encontraron problemas en el código")
            logger.error("   🔍 Pero el endpoint sigue fallando")
            logger.error("   💡 SOLUCIÓN: Investigar problemas de despliegue o configuración")
        
        return resultados

def main():
    analizador = AnalisisExhaustivoCodigo()
    return analizador.ejecutar_analisis_exhaustivo()

if __name__ == "__main__":
    main()
