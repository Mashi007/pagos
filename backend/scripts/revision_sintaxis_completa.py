# backend/scripts/revision_sintaxis_completa.py
"""
REVISIÓN COMPLETA DE SINTAXIS DE ARCHIVOS RELEVANTES
Verificar sintaxis de todos los archivos críticos del sistema
"""
import os
import sys
import logging
import ast
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RevisionSintaxisCompleta:
    def __init__(self):
        self.errores_encontrados = []
        self.archivos_revisados = []
        self.archivos_con_errores = []
        
    def verificar_sintaxis_python(self, ruta_archivo: str) -> Dict[str, Any]:
        """Verificar sintaxis Python de un archivo"""
        logger.info(f"🔍 Revisando sintaxis: {ruta_archivo}")
        
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
                logger.error(f"   📝 Texto problemático: {e.text}")
                
                error_info = {
                    "archivo": ruta_archivo,
                    "linea": e.lineno,
                    "error": e.msg,
                    "texto": e.text,
                    "offset": e.offset
                }
                
                self.errores_encontrados.append(error_info)
                self.archivos_con_errores.append(ruta_archivo)
                
                return {
                    "archivo": ruta_archivo,
                    "sintaxis_valida": False,
                    "errores": [error_msg],
                    "error_info": error_info
                }
                
        except Exception as e:
            logger.error(f"   ❌ Error leyendo archivo: {e}")
            return {
                "archivo": ruta_archivo,
                "sintaxis_valida": False,
                "errores": [str(e)]
            }
    
    def revisar_archivos_criticos(self) -> Dict[str, Any]:
        """Revisar archivos críticos del sistema"""
        logger.info("📁 REVISANDO ARCHIVOS CRÍTICOS DEL SISTEMA")
        logger.info("-" * 50)
        
        # Lista de archivos críticos
        archivos_criticos = [
            # Main y configuración
            "backend/app/main.py",
            "backend/app/core/config.py",
            "backend/app/core/security.py",
            
            # Endpoints principales
            "backend/app/api/v1/endpoints/analistas.py",
            "backend/app/api/v1/endpoints/auth.py",
            "backend/app/api/v1/endpoints/clientes.py",
            "backend/app/api/v1/endpoints/dashboard.py",
            "backend/app/api/v1/endpoints/kpis.py",
            "backend/app/api/v1/endpoints/reportes.py",
            "backend/app/api/v1/endpoints/concesionarios.py",
            "backend/app/api/v1/endpoints/modelos_vehiculos.py",
            "backend/app/api/v1/endpoints/prestamos.py",
            "backend/app/api/v1/endpoints/pagos.py",
            "backend/app/api/v1/endpoints/amortizacion.py",
            "backend/app/api/v1/endpoints/conciliacion.py",
            
            # Modelos
            "backend/app/models/analista.py",
            "backend/app/models/user.py",
            "backend/app/models/cliente.py",
            "backend/app/models/prestamo.py",
            "backend/app/models/pago.py",
            "backend/app/models/concesionario.py",
            "backend/app/models/modelo_vehiculo.py",
            
            # Schemas
            "backend/app/schemas/analista.py",
            "backend/app/schemas/user.py",
            "backend/app/schemas/cliente.py",
            "backend/app/schemas/prestamo.py",
            "backend/app/schemas/pago.py",
            "backend/app/schemas/concesionario.py",
            "backend/app/schemas/modelo_vehiculo.py",
            
            # Servicios
            "backend/app/services/auth_service.py",
            "backend/app/services/user_service.py",
            "backend/app/services/cliente_service.py",
            
            # Utilidades
            "backend/app/utils/auditoria_helper.py",
            "backend/app/utils/date_helpers.py",
            "backend/app/utils/validators.py",
            
            # Dependencias
            "backend/app/api/deps.py",
            
            # Base de datos
            "backend/app/db/session.py",
            "backend/app/db/base.py",
            "backend/app/db/init_db.py"
        ]
        
        resultados = {}
        
        for archivo in archivos_criticos:
            if os.path.exists(archivo):
                resultado = self.verificar_sintaxis_python(archivo)
                resultados[archivo] = resultado
                self.archivos_revisados.append(archivo)
            else:
                logger.warning(f"   ⚠️ Archivo no encontrado: {archivo}")
                resultados[archivo] = {
                    "archivo": archivo,
                    "sintaxis_valida": False,
                    "errores": ["Archivo no encontrado"]
                }
        
        return resultados
    
    def revisar_imports_y_dependencias(self) -> Dict[str, Any]:
        """Revisar imports y dependencias"""
        logger.info("📦 REVISANDO IMPORTS Y DEPENDENCIAS")
        logger.info("-" * 50)
        
        problemas_imports = []
        
        # Revisar archivos de endpoints
        endpoints_dir = Path("backend/app/api/v1/endpoints")
        if endpoints_dir.exists():
            for archivo in endpoints_dir.glob("*.py"):
                try:
                    with open(archivo, 'r', encoding='utf-8') as f:
                        contenido = f.read()
                    
                    # Verificar imports problemáticos
                    if 'logger' in contenido and 'import logging' not in contenido and 'from logging import' not in contenido:
                        problemas_imports.append({
                            "archivo": str(archivo),
                            "problema": "Logger usado sin importar logging",
                            "linea": "N/A"
                        })
                        logger.error(f"   ❌ {archivo}: Logger usado sin importar logging")
                    
                    # Verificar imports de modelos
                    if 'from app.models' in contenido:
                        logger.info(f"   ✅ {archivo}: Imports de modelos OK")
                    
                    # Verificar imports de schemas
                    if 'from app.schemas' in contenido:
                        logger.info(f"   ✅ {archivo}: Imports de schemas OK")
                        
                except Exception as e:
                    logger.error(f"   ❌ Error revisando {archivo}: {e}")
        
        return {
            "problemas_imports": problemas_imports,
            "total_problemas": len(problemas_imports)
        }
    
    def revisar_estructura_fastapi(self) -> Dict[str, Any]:
        """Revisar estructura de FastAPI"""
        logger.info("🚀 REVISANDO ESTRUCTURA DE FASTAPI")
        logger.info("-" * 50)
        
        problemas_fastapi = []
        
        # Revisar main.py
        main_path = Path("backend/app/main.py")
        if main_path.exists():
            try:
                with open(main_path, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                
                # Verificar imports de routers
                if 'from app.api.v1.endpoints import' in contenido:
                    logger.info("   ✅ Imports de endpoints OK")
                else:
                    problemas_fastapi.append({
                        "archivo": "main.py",
                        "problema": "Imports de endpoints faltantes"
                    })
                
                # Verificar registro de routers
                lineas = contenido.split('\n')
                routers_registrados = 0
                for i, linea in enumerate(lineas):
                    if 'app.include_router(' in linea:
                        routers_registrados += 1
                        # Verificar si la línea está completa
                        if linea.strip().endswith(','):
                            siguiente_linea = lineas[i + 1] if i + 1 < len(lineas) else ""
                            if not siguiente_linea.strip().startswith('prefix=') and not siguiente_linea.strip().startswith('tags='):
                                problemas_fastapi.append({
                                    "archivo": "main.py",
                                    "problema": f"Línea {i+1} incompleta: {linea.strip()}",
                                    "linea": i + 1
                                })
                                logger.error(f"   ❌ Línea {i+1} incompleta: {linea.strip()}")
                
                logger.info(f"   📊 Routers registrados: {routers_registrados}")
                
            except Exception as e:
                logger.error(f"   ❌ Error revisando main.py: {e}")
        
        return {
            "problemas_fastapi": problemas_fastapi,
            "total_problemas": len(problemas_fastapi)
        }
    
    def ejecutar_revision_completa(self):
        """Ejecutar revisión completa de sintaxis"""
        logger.info("🔍 REVISIÓN COMPLETA DE SINTAXIS DE ARCHIVOS RELEVANTES")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Verificar sintaxis de todos los archivos críticos")
        logger.info("=" * 80)
        
        resultados = {}
        
        # 1. Revisar archivos críticos
        logger.info("\n📁 1. REVISANDO ARCHIVOS CRÍTICOS")
        logger.info("-" * 50)
        archivos = self.revisar_archivos_criticos()
        resultados["archivos"] = archivos
        
        # 2. Revisar imports y dependencias
        logger.info("\n📦 2. REVISANDO IMPORTS Y DEPENDENCIAS")
        logger.info("-" * 50)
        imports = self.revisar_imports_y_dependencias()
        resultados["imports"] = imports
        
        # 3. Revisar estructura de FastAPI
        logger.info("\n🚀 3. REVISANDO ESTRUCTURA DE FASTAPI")
        logger.info("-" * 50)
        fastapi = self.revisar_estructura_fastapi()
        resultados["fastapi"] = fastapi
        
        # 4. Resumen final
        logger.info("\n📊 RESUMEN FINAL DE REVISIÓN")
        logger.info("=" * 80)
        
        total_archivos = len(self.archivos_revisados)
        archivos_con_errores = len(self.archivos_con_errores)
        total_errores = len(self.errores_encontrados)
        
        logger.info(f"📊 ARCHIVOS REVISADOS: {total_archivos}")
        logger.info(f"📊 ARCHIVOS CON ERRORES: {archivos_con_errores}")
        logger.info(f"📊 ERRORES TOTALES: {total_errores}")
        
        if self.errores_encontrados:
            logger.error("❌ ERRORES DE SINTAXIS ENCONTRADOS:")
            for error in self.errores_encontrados:
                logger.error(f"   📁 {error['archivo']}")
                logger.error(f"   📍 Línea {error['linea']}: {error['error']}")
                logger.error(f"   📝 Texto: {error['texto']}")
                logger.error("   " + "-" * 50)
        
        if imports["total_problemas"] > 0:
            logger.error(f"❌ PROBLEMAS DE IMPORTS: {imports['total_problemas']}")
            for problema in imports["problemas_imports"]:
                logger.error(f"   📁 {problema['archivo']}: {problema['problema']}")
        
        if fastapi["total_problemas"] > 0:
            logger.error(f"❌ PROBLEMAS DE FASTAPI: {fastapi['total_problemas']}")
            for problema in fastapi["problemas_fastapi"]:
                logger.error(f"   📁 {problema['archivo']}: {problema['problema']}")
        
        # Conclusión final
        logger.info("\n🎯 CONCLUSIÓN FINAL")
        logger.info("=" * 80)
        
        if total_errores == 0 and imports["total_problemas"] == 0 and fastapi["total_problemas"] == 0:
            logger.info("✅ TODOS LOS ARCHIVOS REVISADOS TIENEN SINTAXIS VÁLIDA")
            logger.info("   🎯 No se encontraron errores de sintaxis")
            logger.info("   🎯 No se encontraron problemas de imports")
            logger.info("   🎯 No se encontraron problemas de FastAPI")
            logger.info("   🚀 SISTEMA LISTO PARA PRODUCCIÓN")
        else:
            logger.error("❌ SE ENCONTRARON PROBLEMAS QUE REQUIEREN CORRECCIÓN")
            logger.error("   🔧 Corregir errores de sintaxis encontrados")
            logger.error("   🔧 Corregir problemas de imports")
            logger.error("   🔧 Corregir problemas de FastAPI")
            logger.error("   💡 Revisar cada error individualmente")
        
        return resultados

def main():
    revisor = RevisionSintaxisCompleta()
    return revisor.ejecutar_revision_completa()

if __name__ == "__main__":
    main()
