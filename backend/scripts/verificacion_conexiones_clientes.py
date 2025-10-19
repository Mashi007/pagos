"""
Verificación de Conexiones del Módulo de Clientes
Análisis de relaciones con otros módulos y base de datos
"""
import os
import logging
from datetime import datetime
from typing import Dict, List, Tuple
import json
import re

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('verificacion_conexiones_clientes.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VerificacionConexionesClientes:
    """Verificación de conexiones del módulo de clientes"""
    
    def __init__(self):
        self.resultados = {
            "fecha_verificacion": datetime.now().isoformat(),
            "relaciones_bd": [],
            "conexiones_modulos": [],
            "foreign_keys": [],
            "imports_relacionados": [],
            "problemas_encontrados": [],
            "recomendaciones": [],
            "estado_final": "OK"
        }
    
    def verificar_relaciones_base_datos(self) -> Dict:
        """Verifica las relaciones del modelo Cliente con la base de datos"""
        logger.info("🗄️ VERIFICANDO RELACIONES CON BASE DE DATOS")
        logger.info("-" * 50)
        
        archivo = "backend/app/models/cliente.py"
        resultado = {
            "archivo": archivo,
            "existe": False,
            "relaciones_encontradas": [],
            "foreign_keys": [],
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
            
            # Verificar relaciones SQLAlchemy
            relaciones_patterns = [
                r'relationship\s*\(\s*["\']([^"\']+)["\']',
                r'ForeignKey\s*\(\s*["\']([^"\']+)["\']',
                r'back_populates\s*=\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in relaciones_patterns:
                matches = re.findall(pattern, contenido)
                for match in matches:
                    resultado["relaciones_encontradas"].append(match)
                    logger.info(f"✅ Relación encontrada: {match}")
            
            # Verificar foreign keys específicas
            fk_patterns = [
                r'cliente_id.*ForeignKey',
                r'user_id.*ForeignKey',
                r'prestamo_id.*ForeignKey'
            ]
            
            for pattern in fk_patterns:
                if re.search(pattern, contenido):
                    resultado["foreign_keys"].append(pattern)
                    logger.info(f"✅ Foreign Key encontrada: {pattern}")
            
            # Verificar imports de otros modelos
            imports_modelos = [
                "from app.models.user import User",
                "from app.models.prestamo import Prestamo",
                "from app.models.pago import Pago",
                "from app.models.auditoria import Auditoria"
            ]
            
            for import_modelo in imports_modelos:
                if import_modelo in contenido:
                    resultado["relaciones_encontradas"].append(import_modelo)
                    logger.info(f"✅ Import de modelo: {import_modelo}")
                else:
                    resultado["problemas"].append(f"Import faltante: {import_modelo}")
                    logger.warning(f"⚠️ Import faltante: {import_modelo}")
            
            if not resultado["problemas"]:
                resultado["estado"] = "PERFECTO"
                logger.info("🎉 Relaciones con BD PERFECTAS")
            else:
                resultado["estado"] = "PROBLEMAS"
                logger.warning(f"⚠️ Relaciones con {len(resultado['problemas'])} problemas")
            
        except Exception as e:
            resultado["problemas"].append(f"Error leyendo archivo: {str(e)}")
            logger.error(f"❌ Error verificando {archivo}: {e}")
        
        return resultado
    
    def verificar_conexiones_modulos(self) -> Dict:
        """Verifica las conexiones con otros módulos"""
        logger.info("🔗 VERIFICANDO CONEXIONES CON OTROS MÓDULOS")
        logger.info("-" * 50)
        
        resultado = {
            "modulos_conectados": [],
            "imports_cruzados": [],
            "problemas": [],
            "estado": "OK"
        }
        
        # Verificar archivos que pueden importar o usar Cliente
        archivos_relacionados = [
            "backend/app/api/v1/endpoints/prestamos.py",
            "backend/app/api/v1/endpoints/pagos.py",
            "backend/app/api/v1/endpoints/auditoria.py",
            "backend/app/services/validators_service.py",
            "backend/app/services/notifications_service.py"
        ]
        
        for archivo in archivos_relacionados:
            if os.path.exists(archivo):
                try:
                    with open(archivo, 'r', encoding='utf-8') as f:
                        contenido = f.read()
                    
                    # Verificar si importa o usa Cliente
                    if "Cliente" in contenido or "cliente" in contenido:
                        resultado["modulos_conectados"].append(archivo)
                        logger.info(f"✅ Módulo conectado: {archivo}")
                        
                        # Buscar imports específicos
                        imports_cliente = re.findall(r'from.*cliente.*import.*Cliente', contenido)
                        for import_cliente in imports_cliente:
                            resultado["imports_cruzados"].append({
                                "archivo": archivo,
                                "import": import_cliente
                            })
                            logger.info(f"✅ Import cruzado: {archivo} -> {import_cliente}")
                    else:
                        logger.info(f"ℹ️ Módulo sin conexión directa: {archivo}")
                
                except Exception as e:
                    resultado["problemas"].append(f"Error leyendo {archivo}: {str(e)}")
                    logger.error(f"❌ Error leyendo {archivo}: {e}")
            else:
                logger.info(f"ℹ️ Archivo no encontrado: {archivo}")
        
        if resultado["problemas"]:
            resultado["estado"] = "PROBLEMAS"
        
        return resultado
    
    def verificar_endpoints_relacionados(self) -> Dict:
        """Verifica endpoints que usan información de clientes"""
        logger.info("🌐 VERIFICANDO ENDPOINTS RELACIONADOS")
        logger.info("-" * 50)
        
        resultado = {
            "endpoints_relacionados": [],
            "problemas": [],
            "estado": "OK"
        }
        
        # Verificar endpoints que pueden usar clientes
        archivos_endpoints = [
            "backend/app/api/v1/endpoints/prestamos.py",
            "backend/app/api/v1/endpoints/pagos.py",
            "backend/app/api/v1/endpoints/auditoria.py",
            "backend/app/api/v1/endpoints/reportes.py"
        ]
        
        for archivo in archivos_endpoints:
            if os.path.exists(archivo):
                try:
                    with open(archivo, 'r', encoding='utf-8') as f:
                        contenido = f.read()
                    
                    # Buscar endpoints que mencionen clientes
                    endpoints_pattern = r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
                    endpoints = re.findall(endpoints_pattern, contenido)
                    
                    endpoints_con_clientes = []
                    for metodo, ruta in endpoints:
                        # Buscar si el endpoint usa información de clientes
                        if "cliente" in ruta.lower() or "Cliente" in contenido:
                            endpoints_con_clientes.append({
                                "metodo": metodo.upper(),
                                "ruta": ruta,
                                "archivo": archivo
                            })
                    
                    if endpoints_con_clientes:
                        resultado["endpoints_relacionados"].extend(endpoints_con_clientes)
                        logger.info(f"✅ {len(endpoints_con_clientes)} endpoints relacionados en {archivo}")
                
                except Exception as e:
                    resultado["problemas"].append(f"Error leyendo {archivo}: {str(e)}")
                    logger.error(f"❌ Error leyendo {archivo}: {e}")
        
        if resultado["problemas"]:
            resultado["estado"] = "PROBLEMAS"
        
        return resultado
    
    def verificar_servicios_relacionados(self) -> Dict:
        """Verifica servicios que usan el módulo de clientes"""
        logger.info("🔧 VERIFICANDO SERVICIOS RELACIONADOS")
        logger.info("-" * 50)
        
        resultado = {
            "servicios_relacionados": [],
            "problemas": [],
            "estado": "OK"
        }
        
        # Verificar servicios que pueden usar clientes
        archivos_servicios = [
            "backend/app/services/validators_service.py",
            "backend/app/services/notifications_service.py",
            "backend/app/services/reports_service.py"
        ]
        
        for archivo in archivos_servicios:
            if os.path.exists(archivo):
                try:
                    with open(archivo, 'r', encoding='utf-8') as f:
                        contenido = f.read()
                    
                    if "Cliente" in contenido or "cliente" in contenido:
                        resultado["servicios_relacionados"].append(archivo)
                        logger.info(f"✅ Servicio relacionado: {archivo}")
                        
                        # Buscar funciones que usan clientes
                        funciones_pattern = r'def\s+(\w+).*cliente'
                        funciones = re.findall(funciones_pattern, contenido, re.IGNORECASE)
                        for funcion in funciones:
                            logger.info(f"✅ Función relacionada: {funcion}")
                
                except Exception as e:
                    resultado["problemas"].append(f"Error leyendo {archivo}: {str(e)}")
                    logger.error(f"❌ Error leyendo {archivo}: {e}")
        
        if resultado["problemas"]:
            resultado["estado"] = "PROBLEMAS"
        
        return resultado
    
    def verificar_migraciones(self) -> Dict:
        """Verifica las migraciones relacionadas con clientes"""
        logger.info("📊 VERIFICANDO MIGRACIONES")
        logger.info("-" * 50)
        
        resultado = {
            "migraciones_encontradas": [],
            "problemas": [],
            "estado": "OK"
        }
        
        # Verificar directorio de migraciones
        directorio_migraciones = "backend/alembic/versions"
        
        if os.path.exists(directorio_migraciones):
            archivos_migraciones = os.listdir(directorio_migraciones)
            
            for archivo in archivos_migraciones:
                if archivo.endswith('.py') and 'cliente' in archivo.lower():
                    resultado["migraciones_encontradas"].append(archivo)
                    logger.info(f"✅ Migración encontrada: {archivo}")
            
            if not resultado["migraciones_encontradas"]:
                resultado["problemas"].append("No se encontraron migraciones específicas de clientes")
                logger.warning("⚠️ No se encontraron migraciones específicas de clientes")
        else:
            resultado["problemas"].append("Directorio de migraciones no encontrado")
            logger.warning("⚠️ Directorio de migraciones no encontrado")
        
        if resultado["problemas"]:
            resultado["estado"] = "PROBLEMAS"
        
        return resultado
    
    def ejecutar_verificacion_completa(self) -> Dict:
        """Ejecuta la verificación completa de conexiones"""
        logger.info("🚀 INICIANDO VERIFICACIÓN COMPLETA DE CONEXIONES DEL MÓDULO CLIENTES")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha: {datetime.now()}")
        logger.info(f"🎯 Objetivo: Verificar conexiones con otros módulos y BD")
        logger.info("=" * 60)
        
        # Verificar relaciones con base de datos
        relaciones_bd = self.verificar_relaciones_base_datos()
        self.resultados["relaciones_bd"] = relaciones_bd
        
        # Verificar conexiones con otros módulos
        conexiones_modulos = self.verificar_conexiones_modulos()
        self.resultados["conexiones_modulos"] = conexiones_modulos
        
        # Verificar endpoints relacionados
        endpoints_relacionados = self.verificar_endpoints_relacionados()
        self.resultados["endpoints_relacionados"] = endpoints_relacionados
        
        # Verificar servicios relacionados
        servicios_relacionados = self.verificar_servicios_relacionados()
        self.resultados["servicios_relacionados"] = servicios_relacionados
        
        # Verificar migraciones
        migraciones = self.verificar_migraciones()
        self.resultados["migraciones"] = migraciones
        
        # Compilar problemas totales
        todos_problemas = []
        todos_problemas.extend(relaciones_bd.get("problemas", []))
        todos_problemas.extend(conexiones_modulos.get("problemas", []))
        todos_problemas.extend(endpoints_relacionados.get("problemas", []))
        todos_problemas.extend(servicios_relacionados.get("problemas", []))
        todos_problemas.extend(migraciones.get("problemas", []))
        
        self.resultados["problemas_encontrados"] = todos_problemas
        
        # Determinar estado final
        if not todos_problemas:
            self.resultados["estado_final"] = "PERFECTO"
            logger.info("🎉 CONEXIONES DEL MÓDULO CLIENTES PERFECTAS")
        else:
            self.resultados["estado_final"] = "PROBLEMAS"
            logger.warning(f"⚠️ MÓDULO CON {len(todos_problemas)} PROBLEMAS DE CONEXIÓN")
        
        # Mostrar resumen
        logger.info("")
        logger.info("📊 RESUMEN DE VERIFICACIÓN DE CONEXIONES")
        logger.info("-" * 50)
        logger.info(f"🗄️ Relaciones BD: {len(relaciones_bd.get('relaciones_encontradas', []))}")
        logger.info(f"🔗 Módulos conectados: {len(conexiones_modulos.get('modulos_conectados', []))}")
        logger.info(f"🌐 Endpoints relacionados: {len(endpoints_relacionados.get('endpoints_relacionados', []))}")
        logger.info(f"🔧 Servicios relacionados: {len(servicios_relacionados.get('servicios_relacionados', []))}")
        logger.info(f"📊 Migraciones: {len(migraciones.get('migraciones_encontradas', []))}")
        logger.info(f"❌ Problemas encontrados: {len(todos_problemas)}")
        logger.info(f"🎯 Estado final: {self.resultados['estado_final']}")
        
        logger.info("")
        logger.info("🎉 VERIFICACIÓN COMPLETA DE CONEXIONES FINALIZADA")
        logger.info("=" * 60)
        
        return self.resultados

def main():
    """Función principal para ejecutar la verificación"""
    verificador = VerificacionConexionesClientes()
    resultados = verificador.ejecutar_verificacion_completa()
    
    # Guardar reporte
    with open('reporte_conexiones_clientes.json', 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    logger.info("💾 Reporte guardado en: reporte_conexiones_clientes.json")
    
    return resultados

if __name__ == "__main__":
    main()
