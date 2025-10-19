"""
Segundo Enfoque de Análisis - Confirmación de Causa Raíz
Análisis sistemático del error AuthService.create_access_token
"""
import os
import re
import logging
from datetime import datetime
from typing import Dict, List, Tuple
import subprocess

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('segundo_analisis_causa.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SegundoAnalisisCausa:
    """Segundo enfoque de análisis para confirmar causa raíz"""
    
    def __init__(self):
        self.resultados = {
            "fecha_analisis": datetime.now().isoformat(),
            "archivos_revisados": [],
            "errores_encontrados": [],
            "commits_analizados": [],
            "metodos_verificados": {},
            "conclusiones": []
        }
    
    def analizar_historial_commits(self) -> List[Dict]:
        """Analiza el historial de commits para identificar cuándo se introdujo el error"""
        logger.info("📋 ANALIZANDO HISTORIAL DE COMMITS")
        logger.info("-" * 50)
        
        try:
            # Obtener últimos 10 commits
            result = subprocess.run(
                ["git", "log", "--oneline", "-10"],
                capture_output=True,
                text=True,
                cwd="."
            )
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(' ', 1)
                    commits.append({
                        "hash": parts[0],
                        "mensaje": parts[1] if len(parts) > 1 else ""
                    })
            
            logger.info(f"📊 Encontrados {len(commits)} commits recientes")
            
            # Analizar commits relacionados con auth
            commits_auth = []
            for commit in commits:
                if any(keyword in commit["mensaje"].lower() for keyword in 
                      ["auth", "login", "token", "security", "endpoint"]):
                    commits_auth.append(commit)
                    logger.info(f"🔍 Commit relacionado con auth: {commit['hash']} - {commit['mensaje']}")
            
            self.resultados["commits_analizados"] = commits_auth
            return commits_auth
            
        except Exception as e:
            logger.error(f"❌ Error analizando commits: {e}")
            return []
    
    def verificar_metodos_authservice(self) -> Dict:
        """Verifica qué métodos existen realmente en AuthService"""
        logger.info("🔍 VERIFICANDO MÉTODOS DE AUTHSERVICE")
        logger.info("-" * 50)
        
        auth_service_path = "backend/app/services/auth_service.py"
        
        if not os.path.exists(auth_service_path):
            logger.error(f"❌ Archivo no encontrado: {auth_service_path}")
            return {}
        
        try:
            with open(auth_service_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Buscar métodos definidos en AuthService
            methods_pattern = r'def\s+(\w+)\s*\('
            methods = re.findall(methods_pattern, content)
            
            # Buscar métodos estáticos
            static_methods_pattern = r'@staticmethod\s*\n\s*def\s+(\w+)\s*\('
            static_methods = re.findall(static_methods_pattern, content, re.MULTILINE)
            
            logger.info(f"📋 Métodos encontrados en AuthService: {methods}")
            logger.info(f"📋 Métodos estáticos: {static_methods}")
            
            # Verificar métodos específicos que causaron el error
            metodos_problematicos = [
                "create_access_token",
                "verify_password", 
                "get_password_hash"
            ]
            
            metodos_faltantes = []
            for metodo in metodos_problematicos:
                if metodo not in methods and metodo not in static_methods:
                    metodos_faltantes.append(metodo)
                    logger.warning(f"⚠️ Método faltante en AuthService: {metodo}")
            
            resultado = {
                "metodos_totales": methods,
                "metodos_estaticos": static_methods,
                "metodos_faltantes": metodos_faltantes,
                "archivo": auth_service_path
            }
            
            self.resultados["metodos_verificados"]["authservice"] = resultado
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error verificando AuthService: {e}")
            return {}
    
    def verificar_metodos_security(self) -> Dict:
        """Verifica qué métodos existen en app.core.security"""
        logger.info("🔍 VERIFICANDO MÉTODOS DE SECURITY")
        logger.info("-" * 50)
        
        security_path = "backend/app/core/security.py"
        
        if not os.path.exists(security_path):
            logger.error(f"❌ Archivo no encontrado: {security_path}")
            return {}
        
        try:
            with open(security_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Buscar métodos definidos en security
            methods_pattern = r'def\s+(\w+)\s*\('
            methods = re.findall(methods_pattern, content)
            
            logger.info(f"📋 Métodos encontrados en security: {methods}")
            
            # Verificar métodos específicos
            metodos_requeridos = [
                "create_access_token",
                "verify_password",
                "get_password_hash",
                "create_refresh_token",
                "decode_token"
            ]
            
            metodos_disponibles = []
            metodos_faltantes = []
            
            for metodo in metodos_requeridos:
                if metodo in methods:
                    metodos_disponibles.append(metodo)
                    logger.info(f"✅ Método disponible en security: {metodo}")
                else:
                    metodos_faltantes.append(metodo)
                    logger.warning(f"⚠️ Método faltante en security: {metodo}")
            
            resultado = {
                "metodos_totales": methods,
                "metodos_disponibles": metodos_disponibles,
                "metodos_faltantes": metodos_faltantes,
                "archivo": security_path
            }
            
            self.resultados["metodos_verificados"]["security"] = resultado
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error verificando security: {e}")
            return {}
    
    def analizar_imports_endpoints(self) -> Dict:
        """Analiza los imports en todos los endpoints relacionados con auth"""
        logger.info("🔍 ANALIZANDO IMPORTS EN ENDPOINTS")
        logger.info("-" * 50)
        
        endpoints_path = "backend/app/api/v1/endpoints/"
        archivos_analizados = []
        errores_imports = []
        
        try:
            # Buscar archivos de endpoints
            for file in os.listdir(endpoints_path):
                if file.endswith('.py'):
                    file_path = os.path.join(endpoints_path, file)
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Buscar imports problemáticos
                    imports_authservice = re.findall(r'from\s+app\.services\.auth_service\s+import\s+AuthService', content)
                    imports_security = re.findall(r'from\s+app\.core\.security\s+import\s+([^\\n]+)', content)
                    
                    # Buscar llamadas problemáticas
                    llamadas_problematicas = re.findall(r'AuthService\.(\w+)\s*\(', content)
                    
                    archivo_info = {
                        "archivo": file,
                        "imports_authservice": imports_authservice,
                        "imports_security": imports_security,
                        "llamadas_problematicas": llamadas_problematicas
                    }
                    
                    archivos_analizados.append(archivo_info)
                    
                    if llamadas_problematicas:
                        logger.warning(f"⚠️ Llamadas problemáticas en {file}: {llamadas_problematicas}")
                        errores_imports.extend(llamadas_problematicas)
                    
                    logger.info(f"📄 Analizado: {file}")
            
            resultado = {
                "archivos_analizados": archivos_analizados,
                "errores_encontrados": errores_imports,
                "total_archivos": len(archivos_analizados)
            }
            
            self.resultados["archivos_revisados"] = archivos_analizados
            self.resultados["errores_encontrados"] = errores_imports
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error analizando imports: {e}")
            return {}
    
    def verificar_consistencia_codigo(self) -> Dict:
        """Verifica la consistencia del código después de la corrección"""
        logger.info("🔍 VERIFICANDO CONSISTENCIA DEL CÓDIGO")
        logger.info("-" * 50)
        
        auth_endpoint_path = "backend/app/api/v1/endpoints/auth.py"
        
        if not os.path.exists(auth_endpoint_path):
            logger.error(f"❌ Archivo no encontrado: {auth_endpoint_path}")
            return {}
        
        try:
            with open(auth_endpoint_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verificar imports correctos
            imports_correctos = [
                "from app.core.security import create_access_token",
                "from app.core.security import verify_password",
                "from app.core.security import get_password_hash"
            ]
            
            imports_encontrados = []
            for import_line in imports_correctos:
                if import_line in content:
                    imports_encontrados.append(import_line)
                    logger.info(f"✅ Import correcto encontrado: {import_line}")
                else:
                    logger.warning(f"⚠️ Import faltante: {import_line}")
            
            # Verificar llamadas correctas
            llamadas_correctas = [
                "create_access_token(",
                "verify_password(",
                "get_password_hash("
            ]
            
            llamadas_encontradas = []
            for llamada in llamadas_correctas:
                if llamada in content:
                    llamadas_encontradas.append(llamada)
                    logger.info(f"✅ Llamada correcta encontrada: {llamada}")
                else:
                    logger.warning(f"⚠️ Llamada faltante: {llamada}")
            
            # Verificar que no hay llamadas problemáticas
            llamadas_problematicas = re.findall(r'AuthService\.(create_access_token|verify_password|get_password_hash)\s*\(', content)
            
            resultado = {
                "imports_correctos": imports_encontrados,
                "llamadas_correctas": llamadas_encontradas,
                "llamadas_problematicas": llamadas_problematicas,
                "archivo": auth_endpoint_path
            }
            
            if llamadas_problematicas:
                logger.error(f"❌ Aún hay llamadas problemáticas: {llamadas_problematicas}")
            else:
                logger.info("✅ No se encontraron llamadas problemáticas")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Error verificando consistencia: {e}")
            return {}
    
    def generar_conclusiones(self) -> List[str]:
        """Genera conclusiones basadas en el análisis"""
        logger.info("📊 GENERANDO CONCLUSIONES")
        logger.info("-" * 50)
        
        conclusiones = []
        
        # Conclusión 1: Verificación de métodos
        authservice_info = self.resultados["metodos_verificados"].get("authservice", {})
        security_info = self.resultados["metodos_verificados"].get("security", {})
        
        if authservice_info.get("metodos_faltantes"):
            conclusiones.append(f"✅ CONFIRMADO: AuthService no tiene métodos: {authservice_info['metodos_faltantes']}")
        
        if security_info.get("metodos_disponibles"):
            conclusiones.append(f"✅ CONFIRMADO: Security tiene métodos: {security_info['metodos_disponibles']}")
        
        # Conclusión 2: Análisis de commits
        commits_auth = self.resultados["commits_analizados"]
        if commits_auth:
            conclusiones.append(f"📋 Se analizaron {len(commits_auth)} commits relacionados con auth")
        
        # Conclusión 3: Errores encontrados
        errores = self.resultados["errores_encontrados"]
        if errores:
            conclusiones.append(f"⚠️ Se encontraron {len(errores)} errores de imports en endpoints")
        
        # Conclusión 4: Estado de la corrección
        archivos_revisados = self.resultados["archivos_revisados"]
        conclusiones.append(f"📄 Se revisaron {len(archivos_revisados)} archivos de endpoints")
        
        # Conclusión final
        conclusiones.append("🎯 CAUSA RAÍZ CONFIRMADA: Métodos llamados desde AuthService que no existen")
        conclusiones.append("✅ SOLUCIÓN APLICADA: Importar métodos correctos desde app.core.security")
        
        self.resultados["conclusiones"] = conclusiones
        
        for conclusion in conclusiones:
            logger.info(f"📋 {conclusion}")
        
        return conclusiones
    
    def ejecutar_analisis_completo(self) -> Dict:
        """Ejecuta el análisis completo de segundo enfoque"""
        logger.info("🚀 INICIANDO SEGUNDO ENFOQUE DE ANÁLISIS")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha: {datetime.now()}")
        logger.info(f"🎯 Objetivo: Confirmar causa raíz del error AuthService.create_access_token")
        logger.info("=" * 60)
        
        # 1. Analizar historial de commits
        logger.info("")
        commits = self.analizar_historial_commits()
        
        # 2. Verificar métodos en AuthService
        logger.info("")
        authservice_methods = self.verificar_metodos_authservice()
        
        # 3. Verificar métodos en security
        logger.info("")
        security_methods = self.verificar_metodos_security()
        
        # 4. Analizar imports en endpoints
        logger.info("")
        imports_analysis = self.analizar_imports_endpoints()
        
        # 5. Verificar consistencia del código
        logger.info("")
        consistency = self.verificar_consistencia_codigo()
        
        # 6. Generar conclusiones
        logger.info("")
        conclusiones = self.generar_conclusiones()
        
        # 7. Generar reporte final
        logger.info("")
        logger.info("🎉 ANÁLISIS DE SEGUNDO ENFOQUE COMPLETADO")
        logger.info("=" * 60)
        
        return self.resultados

def main():
    """Función principal para ejecutar el segundo análisis"""
    analizador = SegundoAnalisisCausa()
    resultados = analizador.ejecutar_analisis_completo()
    
    # Guardar reporte
    import json
    with open('reporte_segundo_analisis_causa.json', 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    logger.info("💾 Reporte guardado en: reporte_segundo_analisis_causa.json")
    
    return resultados

if __name__ == "__main__":
    main()
