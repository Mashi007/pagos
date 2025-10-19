"""
Tercer Enfoque de Análisis - Revisión de Sintaxis Completa
Análisis sistemático de sintaxis en archivos de login y módulo clientes
"""
import os
import ast
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple
import re

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tercer_analisis_sintaxis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TercerAnalisisSintaxis:
    """Tercer enfoque de análisis enfocado en sintaxis"""
    
    def __init__(self):
        self.resultados = {
            "fecha_analisis": datetime.now().isoformat(),
            "archivos_revisados": [],
            "errores_sintaxis": [],
            "errores_imports": [],
            "archivos_problematicos": [],
            "archivos_ok": [],
            "resumen": {}
        }
        
        # Archivos críticos para revisar
        self.archivos_criticos = {
            "auth": [
                "backend/app/api/v1/endpoints/auth.py",
                "backend/app/services/auth_service.py",
                "backend/app/core/security.py",
                "backend/app/api/deps.py",
                "backend/app/schemas/auth.py"
            ],
            "clientes": [
                "backend/app/api/v1/endpoints/clientes.py",
                "backend/app/models/cliente.py",
                "backend/app/schemas/cliente.py",
                "backend/app/services/validators_service.py"
            ],
            "core": [
                "backend/app/core/config.py",
                "backend/app/core/permissions_simple.py",
                "backend/app/db/session.py",
                "backend/app/models/user.py"
            ]
        }
    
    def verificar_sintaxis_python(self, archivo_path: str) -> Tuple[bool, List[str]]:
        """Verifica la sintaxis de un archivo Python"""
        errores = []
        
        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Intentar compilar el código
            ast.parse(contenido)
            return True, []
            
        except SyntaxError as e:
            error_msg = f"Error de sintaxis en línea {e.lineno}: {e.msg}"
            errores.append(error_msg)
            logger.error(f"❌ {archivo_path}: {error_msg}")
            return False, errores
            
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            errores.append(error_msg)
            logger.error(f"❌ {archivo_path}: {error_msg}")
            return False, errores
    
    def verificar_imports(self, archivo_path: str) -> Tuple[bool, List[str]]:
        """Verifica que los imports sean válidos"""
        errores = []
        
        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Buscar imports problemáticos
            imports_pattern = r'from\s+([^\s]+)\s+import\s+([^\n]+)'
            imports = re.findall(imports_pattern, contenido)
            
            for modulo, funciones in imports:
                # Verificar que el módulo existe
                modulo_path = modulo.replace('.', '/') + '.py'
                posibles_rutas = [
                    f"backend/app/{modulo_path}",
                    f"backend/{modulo_path}",
                    f"{modulo_path}"
                ]
                
                modulo_existe = False
                for ruta in posibles_rutas:
                    if os.path.exists(ruta):
                        modulo_existe = True
                        break
                
                if not modulo_existe:
                    error_msg = f"Import de módulo inexistente: {modulo}"
                    errores.append(error_msg)
                    logger.warning(f"⚠️ {archivo_path}: {error_msg}")
            
            return len(errores) == 0, errores
            
        except Exception as e:
            error_msg = f"Error verificando imports: {str(e)}"
            errores.append(error_msg)
            logger.error(f"❌ {archivo_path}: {error_msg}")
            return False, errores
    
    def verificar_metodos_llamados(self, archivo_path: str) -> Tuple[bool, List[str]]:
        """Verifica que los métodos llamados existan"""
        errores = []
        
        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Buscar llamadas problemáticas conocidas
            llamadas_problematicas = [
                r'AuthService\.create_access_token\s*\(',
                r'AuthService\.verify_password\s*\(',
                r'AuthService\.get_password_hash\s*\(',
                r'ValidadorEmail\.validar_email\s*\(',
                r'ValidadorNombre\.validar_nombre\s*\('
            ]
            
            for patron in llamadas_problematicas:
                matches = re.findall(patron, contenido)
                if matches:
                    error_msg = f"Llamada problemática encontrada: {patron}"
                    errores.append(error_msg)
                    logger.warning(f"⚠️ {archivo_path}: {error_msg}")
            
            return len(errores) == 0, errores
            
        except Exception as e:
            error_msg = f"Error verificando métodos: {str(e)}"
            errores.append(error_msg)
            logger.error(f"❌ {archivo_path}: {error_msg}")
            return False, errores
    
    def analizar_archivo_completo(self, archivo_path: str) -> Dict:
        """Analiza completamente un archivo"""
        logger.info(f"🔍 Analizando: {archivo_path}")
        
        resultado = {
            "archivo": archivo_path,
            "existe": False,
            "sintaxis_ok": False,
            "imports_ok": False,
            "metodos_ok": False,
            "errores": [],
            "estado": "ERROR"
        }
        
        # Verificar que el archivo existe
        if not os.path.exists(archivo_path):
            resultado["errores"].append("Archivo no encontrado")
            logger.error(f"❌ Archivo no encontrado: {archivo_path}")
            return resultado
        
        resultado["existe"] = True
        
        # Verificar sintaxis
        sintaxis_ok, errores_sintaxis = self.verificar_sintaxis_python(archivo_path)
        resultado["sintaxis_ok"] = sintaxis_ok
        resultado["errores"].extend(errores_sintaxis)
        
        # Verificar imports
        imports_ok, errores_imports = self.verificar_imports(archivo_path)
        resultado["imports_ok"] = imports_ok
        resultado["errores"].extend(errores_imports)
        
        # Verificar métodos llamados
        metodos_ok, errores_metodos = self.verificar_metodos_llamados(archivo_path)
        resultado["metodos_ok"] = metodos_ok
        resultado["errores"].extend(errores_metodos)
        
        # Determinar estado final
        if sintaxis_ok and imports_ok and metodos_ok:
            resultado["estado"] = "OK"
            logger.info(f"✅ {archivo_path}: OK")
        else:
            resultado["estado"] = "PROBLEMAS"
            logger.warning(f"⚠️ {archivo_path}: PROBLEMAS")
        
        return resultado
    
    def analizar_categoria_archivos(self, categoria: str, archivos: List[str]) -> Dict:
        """Analiza una categoría de archivos"""
        logger.info(f"📁 ANALIZANDO CATEGORÍA: {categoria.upper()}")
        logger.info("-" * 50)
        
        resultados_categoria = []
        archivos_ok = 0
        archivos_problemas = 0
        
        for archivo in archivos:
            resultado = self.analizar_archivo_completo(archivo)
            resultados_categoria.append(resultado)
            
            if resultado["estado"] == "OK":
                archivos_ok += 1
            else:
                archivos_problemas += 1
        
        resumen_categoria = {
            "categoria": categoria,
            "total_archivos": len(archivos),
            "archivos_ok": archivos_ok,
            "archivos_problemas": archivos_problemas,
            "porcentaje_ok": (archivos_ok / len(archivos)) * 100 if archivos else 0,
            "resultados": resultados_categoria
        }
        
        logger.info(f"📊 {categoria}: {archivos_ok}/{len(archivos)} archivos OK ({resumen_categoria['porcentaje_ok']:.1f}%)")
        
        return resumen_categoria
    
    def ejecutar_analisis_completo(self) -> Dict:
        """Ejecuta el análisis completo de sintaxis"""
        logger.info("🚀 INICIANDO TERCER ENFOQUE DE ANÁLISIS - SINTAXIS")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha: {datetime.now()}")
        logger.info(f"🎯 Objetivo: Revisar sintaxis de archivos de login y clientes")
        logger.info("=" * 60)
        
        resultados_categorias = {}
        
        # Analizar cada categoría
        for categoria, archivos in self.archivos_criticos.items():
            logger.info("")
            resultado_categoria = self.analizar_categoria_archivos(categoria, archivos)
            resultados_categorias[categoria] = resultado_categoria
            
            # Agregar a resultados generales
            self.resultados["archivos_revisados"].extend(resultado_categoria["resultados"])
            
            for resultado in resultado_categoria["resultados"]:
                if resultado["estado"] == "OK":
                    self.resultados["archivos_ok"].append(resultado["archivo"])
                else:
                    self.resultados["archivos_problematicos"].append(resultado["archivo"])
                    self.resultados["errores_sintaxis"].extend(resultado["errores"])
        
        # Generar resumen general
        total_archivos = sum(len(archivos) for archivos in self.archivos_criticos.values())
        total_ok = len(self.resultados["archivos_ok"])
        total_problemas = len(self.resultados["archivos_problematicos"])
        
        self.resultados["resumen"] = {
            "total_archivos": total_archivos,
            "archivos_ok": total_ok,
            "archivos_problemas": total_problemas,
            "porcentaje_ok": (total_ok / total_archivos) * 100 if total_archivos > 0 else 0,
            "categorias": resultados_categorias
        }
        
        # Generar conclusiones
        logger.info("")
        logger.info("📊 RESUMEN GENERAL")
        logger.info("-" * 40)
        logger.info(f"📄 Total archivos revisados: {total_archivos}")
        logger.info(f"✅ Archivos OK: {total_ok}")
        logger.info(f"⚠️ Archivos con problemas: {total_problemas}")
        logger.info(f"📈 Porcentaje OK: {self.resultados['resumen']['porcentaje_ok']:.1f}%")
        
        logger.info("")
        logger.info("🎯 CONCLUSIONES DEL TERCER ANÁLISIS:")
        logger.info("-" * 40)
        
        if total_problemas == 0:
            logger.info("🎉 TODOS LOS ARCHIVOS TIENEN SINTAXIS CORRECTA")
            logger.info("✅ NO HAY ERRORES DE SINTAXIS QUE CAUSEN PROBLEMAS")
        else:
            logger.info(f"⚠️ SE ENCONTRARON {total_problemas} ARCHIVOS CON PROBLEMAS")
            logger.info("🔧 REQUIERE CORRECCIÓN DE SINTAXIS")
        
        logger.info("")
        logger.info("🎉 TERCER ANÁLISIS DE SINTAXIS COMPLETADO")
        logger.info("=" * 60)
        
        return self.resultados

def main():
    """Función principal para ejecutar el tercer análisis"""
    analizador = TercerAnalisisSintaxis()
    resultados = analizador.ejecutar_analisis_completo()
    
    # Guardar reporte
    import json
    with open('reporte_tercer_analisis_sintaxis.json', 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    logger.info("💾 Reporte guardado en: reporte_tercer_analisis_sintaxis.json")
    
    return resultados

if __name__ == "__main__":
    main()
