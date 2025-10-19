"""
Verificación Completa del Sistema de Login
Análisis detallado mientras el deploy sucede
"""
import os
import logging
from datetime import datetime
from typing import Dict, List, Tuple
import json

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('verificacion_login_completa.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VerificacionLoginCompleta:
    """Verificación completa del sistema de login"""
    
    def __init__(self):
        self.resultados = {
            "fecha_verificacion": datetime.now().isoformat(),
            "archivos_verificados": [],
            "endpoints_verificados": [],
            "servicios_verificados": [],
            "dependencias_verificadas": [],
            "problemas_encontrados": [],
            "recomendaciones": [],
            "estado_final": "OK"
        }
    
    def verificar_archivo_auth(self) -> Dict:
        """Verifica el archivo principal de autenticación"""
        logger.info("🔐 VERIFICANDO ARCHIVO DE AUTENTICACIÓN")
        logger.info("-" * 50)
        
        archivo = "backend/app/api/v1/endpoints/auth.py"
        resultado = {
            "archivo": archivo,
            "existe": False,
            "endpoints_encontrados": [],
            "imports_correctos": [],
            "problemas": [],
            "estado": "ERROR"
        }
        
        if not os.path.exists(archivo):
            resultado["problemas"].append("Archivo no encontrado")
            return resultado
        
        resultado["existe"] = True
        
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Verificar endpoints
            endpoints_pattern = r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
            endpoints = re.findall(endpoints_pattern, contenido)
            
            for metodo, ruta in endpoints:
                endpoint_info = {
                    "metodo": metodo.upper(),
                    "ruta": ruta,
                    "funcion": self._buscar_funcion_endpoint(contenido, metodo, ruta)
                }
                resultado["endpoints_encontrados"].append(endpoint_info)
                logger.info(f"✅ Endpoint: {metodo.upper()} {ruta}")
            
            # Verificar imports críticos
            imports_criticos = [
                "create_access_token",
                "verify_password", 
                "get_password_hash",
                "validate_password_strength",
                "AuthService"
            ]
            
            for import_critico in imports_criticos:
                if import_critico in contenido:
                    resultado["imports_correctos"].append(import_critico)
                    logger.info(f"✅ Import correcto: {import_critico}")
                else:
                    resultado["problemas"].append(f"Import faltante: {import_critico}")
                    logger.warning(f"⚠️ Import faltante: {import_critico}")
            
            # Verificar funciones críticas
            funciones_criticas = [
                "login",
                "logout", 
                "get_current_user_info",
                "refresh_token",
                "change_password"
            ]
            
            for funcion in funciones_criticas:
                if f"def {funcion}" in contenido:
                    logger.info(f"✅ Función encontrada: {funcion}")
                else:
                    resultado["problemas"].append(f"Función faltante: {funcion}")
                    logger.warning(f"⚠️ Función faltante: {funcion}")
            
            if not resultado["problemas"]:
                resultado["estado"] = "PERFECTO"
                logger.info("🎉 Archivo de autenticación PERFECTO")
            else:
                resultado["estado"] = "PROBLEMAS"
                logger.warning(f"⚠️ Archivo con {len(resultado['problemas'])} problemas")
            
        except Exception as e:
            resultado["problemas"].append(f"Error leyendo archivo: {str(e)}")
            logger.error(f"❌ Error verificando {archivo}: {e}")
        
        return resultado
    
    def verificar_auth_service(self) -> Dict:
        """Verifica el servicio de autenticación"""
        logger.info("🔧 VERIFICANDO AUTH SERVICE")
        logger.info("-" * 50)
        
        archivo = "backend/app/services/auth_service.py"
        resultado = {
            "archivo": archivo,
            "existe": False,
            "metodos_encontrados": [],
            "imports_correctos": [],
            "problemas": [],
            "estado": "ERROR"
        }
        
        if not os.path.exists(archivo):
            resultado["problemas"].append("Archivo no encontrado")
            return resultado
        
        resultado["existe"] = True
        
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Verificar métodos críticos
            metodos_criticos = [
                "authenticate_user",
                "login",
                "refresh_access_token",
                "change_password",
                "get_user_permissions"
            ]
            
            for metodo in metodos_criticos:
                if f"def {metodo}" in contenido:
                    resultado["metodos_encontrados"].append(metodo)
                    logger.info(f"✅ Método encontrado: {metodo}")
                else:
                    resultado["problemas"].append(f"Método faltante: {metodo}")
                    logger.warning(f"⚠️ Método faltante: {metodo}")
            
            # Verificar imports críticos
            imports_criticos = [
                "verify_password",
                "get_password_hash",
                "create_access_token",
                "create_refresh_token",
                "decode_token"
            ]
            
            for import_critico in imports_criticos:
                if import_critico in contenido:
                    resultado["imports_correctos"].append(import_critico)
                    logger.info(f"✅ Import correcto: {import_critico}")
                else:
                    resultado["problemas"].append(f"Import faltante: {import_critico}")
                    logger.warning(f"⚠️ Import faltante: {import_critico}")
            
            if not resultado["problemas"]:
                resultado["estado"] = "PERFECTO"
                logger.info("🎉 Auth Service PERFECTO")
            else:
                resultado["estado"] = "PROBLEMAS"
                logger.warning(f"⚠️ Auth Service con {len(resultado['problemas'])} problemas")
            
        except Exception as e:
            resultado["problemas"].append(f"Error leyendo archivo: {str(e)}")
            logger.error(f"❌ Error verificando {archivo}: {e}")
        
        return resultado
    
    def verificar_security_core(self) -> Dict:
        """Verifica el módulo de seguridad"""
        logger.info("🛡️ VERIFICANDO SECURITY CORE")
        logger.info("-" * 50)
        
        archivo = "backend/app/core/security.py"
        resultado = {
            "archivo": archivo,
            "existe": False,
            "funciones_encontradas": [],
            "problemas": [],
            "estado": "ERROR"
        }
        
        if not os.path.exists(archivo):
            resultado["problemas"].append("Archivo no encontrado")
            return resultado
        
        resultado["existe"] = True
        
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Verificar funciones críticas
            funciones_criticas = [
                "verify_password",
                "get_password_hash",
                "create_access_token",
                "create_refresh_token",
                "decode_token",
                "validate_password_strength"
            ]
            
            for funcion in funciones_criticas:
                if f"def {funcion}" in contenido:
                    resultado["funciones_encontradas"].append(funcion)
                    logger.info(f"✅ Función encontrada: {funcion}")
                else:
                    resultado["problemas"].append(f"Función faltante: {funcion}")
                    logger.warning(f"⚠️ Función faltante: {funcion}")
            
            if not resultado["problemas"]:
                resultado["estado"] = "PERFECTO"
                logger.info("🎉 Security Core PERFECTO")
            else:
                resultado["estado"] = "PROBLEMAS"
                logger.warning(f"⚠️ Security Core con {len(resultado['problemas'])} problemas")
            
        except Exception as e:
            resultado["problemas"].append(f"Error leyendo archivo: {str(e)}")
            logger.error(f"❌ Error verificando {archivo}: {e}")
        
        return resultado
    
    def verificar_dependencias(self) -> Dict:
        """Verifica las dependencias del sistema de login"""
        logger.info("🔗 VERIFICANDO DEPENDENCIAS")
        logger.info("-" * 50)
        
        resultado = {
            "dependencias_verificadas": [],
            "problemas": [],
            "estado": "OK"
        }
        
        # Verificar archivos de dependencias
        archivos_dependencias = [
            "backend/app/api/deps.py",
            "backend/app/db/session.py",
            "backend/app/models/user.py",
            "backend/app/schemas/auth.py"
        ]
        
        for archivo in archivos_dependencias:
            if os.path.exists(archivo):
                resultado["dependencias_verificadas"].append(archivo)
                logger.info(f"✅ Dependencia encontrada: {archivo}")
            else:
                resultado["problemas"].append(f"Dependencia faltante: {archivo}")
                logger.warning(f"⚠️ Dependencia faltante: {archivo}")
        
        if resultado["problemas"]:
            resultado["estado"] = "PROBLEMAS"
        
        return resultado
    
    def _buscar_funcion_endpoint(self, contenido: str, metodo: str, ruta: str) -> str:
        """Busca la función asociada a un endpoint"""
        import re
        try:
            pattern = rf'@router\.{metodo}\s*\(\s*["\']?{re.escape(ruta)}["\']?\s*\)\s*\n\s*(?:async\s+)?def\s+(\w+)'
            match = re.search(pattern, contenido, re.MULTILINE)
            return match.group(1) if match else "No encontrada"
        except:
            return "Error"
    
    def ejecutar_verificacion_completa(self) -> Dict:
        """Ejecuta la verificación completa del sistema de login"""
        logger.info("🚀 INICIANDO VERIFICACIÓN COMPLETA DEL SISTEMA DE LOGIN")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha: {datetime.now()}")
        logger.info(f"🎯 Objetivo: Verificar sistema de login mientras deploy sucede")
        logger.info("=" * 60)
        
        # Verificar archivo de autenticación
        auth_endpoint = self.verificar_archivo_auth()
        self.resultados["archivos_verificados"].append(auth_endpoint)
        
        # Verificar auth service
        auth_service = self.verificar_auth_service()
        self.resultados["servicios_verificados"].append(auth_service)
        
        # Verificar security core
        security_core = self.verificar_security_core()
        self.resultados["servicios_verificados"].append(security_core)
        
        # Verificar dependencias
        dependencias = self.verificar_dependencias()
        self.resultados["dependencias_verificadas"] = dependencias
        
        # Compilar problemas totales
        todos_problemas = []
        todos_problemas.extend(auth_endpoint.get("problemas", []))
        todos_problemas.extend(auth_service.get("problemas", []))
        todos_problemas.extend(security_core.get("problemas", []))
        todos_problemas.extend(dependencias.get("problemas", []))
        
        self.resultados["problemas_encontrados"] = todos_problemas
        
        # Determinar estado final
        if not todos_problemas:
            self.resultados["estado_final"] = "PERFECTO"
            logger.info("🎉 SISTEMA DE LOGIN PERFECTO")
        else:
            self.resultados["estado_final"] = "PROBLEMAS"
            logger.warning(f"⚠️ SISTEMA CON {len(todos_problemas)} PROBLEMAS")
        
        # Mostrar resumen
        logger.info("")
        logger.info("📊 RESUMEN DE VERIFICACIÓN")
        logger.info("-" * 40)
        logger.info(f"📄 Archivos verificados: {len(self.resultados['archivos_verificados'])}")
        logger.info(f"🔧 Servicios verificados: {len(self.resultados['servicios_verificados'])}")
        logger.info(f"🔗 Dependencias verificadas: {len(self.resultados['dependencias_verificadas']['dependencias_verificadas'])}")
        logger.info(f"❌ Problemas encontrados: {len(todos_problemas)}")
        logger.info(f"🎯 Estado final: {self.resultados['estado_final']}")
        
        logger.info("")
        logger.info("🎉 VERIFICACIÓN COMPLETA DEL SISTEMA DE LOGIN FINALIZADA")
        logger.info("=" * 60)
        
        return self.resultados

def main():
    """Función principal para ejecutar la verificación"""
    verificador = VerificacionLoginCompleta()
    resultados = verificador.ejecutar_verificacion_completa()
    
    # Guardar reporte
    with open('reporte_verificacion_login_completa.json', 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    logger.info("💾 Reporte guardado en: reporte_verificacion_login_completa.json")
    
    return resultados

if __name__ == "__main__":
    main()
