"""
Verificación Completa del Módulo de Clientes
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
        logging.FileHandler('verificacion_clientes_completa.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VerificacionClientesCompleta:
    """Verificación completa del módulo de clientes"""
    
    def __init__(self):
        self.resultados = {
            "fecha_verificacion": datetime.now().isoformat(),
            "archivos_verificados": [],
            "endpoints_verificados": [],
            "modelos_verificados": [],
            "servicios_verificados": [],
            "dependencias_verificadas": [],
            "problemas_encontrados": [],
            "recomendaciones": [],
            "estado_final": "OK"
        }
    
    def verificar_endpoints_clientes(self) -> Dict:
        """Verifica los endpoints de clientes"""
        logger.info("👥 VERIFICANDO ENDPOINTS DE CLIENTES")
        logger.info("-" * 50)
        
        archivo = "backend/app/api/v1/endpoints/clientes.py"
        resultado = {
            "archivo": archivo,
            "existe": False,
            "endpoints_encontrados": [],
            "imports_correctos": [],
            "funciones_criticas": [],
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
                "Cliente",
                "ClienteResponse",
                "ClienteCreate", 
                "ClienteUpdate",
                "get_db",
                "get_current_user"
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
                "listar_clientes",
                "obtener_cliente",
                "obtener_cliente_por_cedula",
                "contar_clientes",
                "opciones_configuracion",
                "crear_cliente",
                "actualizar_cliente",
                "eliminar_cliente"
            ]
            
            for funcion in funciones_criticas:
                if f"def {funcion}" in contenido:
                    resultado["funciones_criticas"].append(funcion)
                    logger.info(f"✅ Función encontrada: {funcion}")
                else:
                    resultado["problemas"].append(f"Función faltante: {funcion}")
                    logger.warning(f"⚠️ Función faltante: {funcion}")
            
            # Verificar características avanzadas
            caracteristicas_avanzadas = [
                "paginación",
                "búsqueda",
                "filtros",
                "validaciones",
                "manejo de errores"
            ]
            
            caracteristicas_encontradas = []
            if "page:" in contenido and "per_page:" in contenido:
                caracteristicas_encontradas.append("paginación")
                logger.info("✅ Paginación implementada")
            
            if "search:" in contenido:
                caracteristicas_encontradas.append("búsqueda")
                logger.info("✅ Búsqueda implementada")
            
            if "estado:" in contenido:
                caracteristicas_encontradas.append("filtros")
                logger.info("✅ Filtros implementados")
            
            if "HTTPException" in contenido:
                caracteristicas_encontradas.append("manejo de errores")
                logger.info("✅ Manejo de errores implementado")
            
            resultado["caracteristicas_avanzadas"] = caracteristicas_encontradas
            
            if not resultado["problemas"]:
                resultado["estado"] = "PERFECTO"
                logger.info("🎉 Endpoints de clientes PERFECTOS")
            else:
                resultado["estado"] = "PROBLEMAS"
                logger.warning(f"⚠️ Endpoints con {len(resultado['problemas'])} problemas")
            
        except Exception as e:
            resultado["problemas"].append(f"Error leyendo archivo: {str(e)}")
            logger.error(f"❌ Error verificando {archivo}: {e}")
        
        return resultado
    
    def verificar_modelo_cliente(self) -> Dict:
        """Verifica el modelo de cliente"""
        logger.info("📊 VERIFICANDO MODELO DE CLIENTE")
        logger.info("-" * 50)
        
        archivo = "backend/app/models/cliente.py"
        resultado = {
            "archivo": archivo,
            "existe": False,
            "campos_encontrados": [],
            "relaciones_encontradas": [],
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
            
            # Verificar campos críticos
            campos_criticos = [
                "id",
                "cedula",
                "nombre",
                "apellido",
                "email",
                "telefono",
                "direccion",
                "fecha_nacimiento",
                "estado",
                "fecha_registro"
            ]
            
            for campo in campos_criticos:
                if campo in contenido:
                    resultado["campos_encontrados"].append(campo)
                    logger.info(f"✅ Campo encontrado: {campo}")
                else:
                    resultado["problemas"].append(f"Campo faltante: {campo}")
                    logger.warning(f"⚠️ Campo faltante: {campo}")
            
            # Verificar relaciones
            relaciones_criticas = [
                "prestamos",
                "pagos",
                "auditoria"
            ]
            
            for relacion in relaciones_criticas:
                if relacion in contenido:
                    resultado["relaciones_encontradas"].append(relacion)
                    logger.info(f"✅ Relación encontrada: {relacion}")
            
            # Verificar herencia de SQLAlchemy
            if "Base" in contenido and "Column" in contenido:
                logger.info("✅ Herencia de SQLAlchemy correcta")
            else:
                resultado["problemas"].append("Herencia de SQLAlchemy incorrecta")
                logger.warning("⚠️ Herencia de SQLAlchemy incorrecta")
            
            if not resultado["problemas"]:
                resultado["estado"] = "PERFECTO"
                logger.info("🎉 Modelo de cliente PERFECTO")
            else:
                resultado["estado"] = "PROBLEMAS"
                logger.warning(f"⚠️ Modelo con {len(resultado['problemas'])} problemas")
            
        except Exception as e:
            resultado["problemas"].append(f"Error leyendo archivo: {str(e)}")
            logger.error(f"❌ Error verificando {archivo}: {e}")
        
        return resultado
    
    def verificar_schemas_cliente(self) -> Dict:
        """Verifica los esquemas de cliente"""
        logger.info("📋 VERIFICANDO SCHEMAS DE CLIENTE")
        logger.info("-" * 50)
        
        archivo = "backend/app/schemas/cliente.py"
        resultado = {
            "archivo": archivo,
            "existe": False,
            "schemas_encontrados": [],
            "validaciones_encontradas": [],
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
            
            # Verificar schemas críticos
            schemas_criticos = [
                "ClienteResponse",
                "ClienteCreate",
                "ClienteUpdate"
            ]
            
            for schema in schemas_criticos:
                if f"class {schema}" in contenido:
                    resultado["schemas_encontrados"].append(schema)
                    logger.info(f"✅ Schema encontrado: {schema}")
                else:
                    resultado["problemas"].append(f"Schema faltante: {schema}")
                    logger.warning(f"⚠️ Schema faltante: {schema}")
            
            # Verificar validaciones
            validaciones_criticas = [
                "email",
                "cedula",
                "telefono",
                "fecha_nacimiento"
            ]
            
            for validacion in validaciones_criticas:
                if validacion in contenido:
                    resultado["validaciones_encontradas"].append(validacion)
                    logger.info(f"✅ Validación encontrada: {validacion}")
            
            # Verificar herencia de Pydantic
            if "BaseModel" in contenido:
                logger.info("✅ Herencia de Pydantic correcta")
            else:
                resultado["problemas"].append("Herencia de Pydantic incorrecta")
                logger.warning("⚠️ Herencia de Pydantic incorrecta")
            
            if not resultado["problemas"]:
                resultado["estado"] = "PERFECTO"
                logger.info("🎉 Schemas de cliente PERFECTOS")
            else:
                resultado["estado"] = "PROBLEMAS"
                logger.warning(f"⚠️ Schemas con {len(resultado['problemas'])} problemas")
            
        except Exception as e:
            resultado["problemas"].append(f"Error leyendo archivo: {str(e)}")
            logger.error(f"❌ Error verificando {archivo}: {e}")
        
        return resultado
    
    def verificar_servicios_clientes(self) -> Dict:
        """Verifica los servicios relacionados con clientes"""
        logger.info("🔧 VERIFICANDO SERVICIOS DE CLIENTES")
        logger.info("-" * 50)
        
        resultado = {
            "servicios_verificados": [],
            "problemas": [],
            "estado": "OK"
        }
        
        # Verificar servicios relacionados
        servicios_relacionados = [
            "backend/app/services/validators_service.py",
            "backend/app/services/notifications_service.py"
        ]
        
        for servicio in servicios_relacionados:
            if os.path.exists(servicio):
                resultado["servicios_verificados"].append(servicio)
                logger.info(f"✅ Servicio encontrado: {servicio}")
            else:
                resultado["problemas"].append(f"Servicio faltante: {servicio}")
                logger.warning(f"⚠️ Servicio faltante: {servicio}")
        
        if resultado["problemas"]:
            resultado["estado"] = "PROBLEMAS"
        
        return resultado
    
    def verificar_dependencias_clientes(self) -> Dict:
        """Verifica las dependencias del módulo de clientes"""
        logger.info("🔗 VERIFICANDO DEPENDENCIAS DE CLIENTES")
        logger.info("-" * 50)
        
        resultado = {
            "dependencias_verificadas": [],
            "problemas": [],
            "estado": "OK"
        }
        
        # Verificar archivos de dependencias
        archivos_dependencias = [
            "backend/app/db/session.py",
            "backend/app/api/deps.py",
            "backend/app/models/user.py"
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
        """Ejecuta la verificación completa del módulo de clientes"""
        logger.info("🚀 INICIANDO VERIFICACIÓN COMPLETA DEL MÓDULO DE CLIENTES")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha: {datetime.now()}")
        logger.info(f"🎯 Objetivo: Verificar módulo de clientes mientras deploy sucede")
        logger.info("=" * 60)
        
        # Verificar endpoints de clientes
        endpoints_clientes = self.verificar_endpoints_clientes()
        self.resultados["endpoints_verificados"].append(endpoints_clientes)
        
        # Verificar modelo de cliente
        modelo_cliente = self.verificar_modelo_cliente()
        self.resultados["modelos_verificados"].append(modelo_cliente)
        
        # Verificar schemas de cliente
        schemas_cliente = self.verificar_schemas_cliente()
        self.resultados["archivos_verificados"].append(schemas_cliente)
        
        # Verificar servicios de clientes
        servicios_clientes = self.verificar_servicios_clientes()
        self.resultados["servicios_verificados"].append(servicios_clientes)
        
        # Verificar dependencias
        dependencias = self.verificar_dependencias_clientes()
        self.resultados["dependencias_verificadas"] = dependencias
        
        # Compilar problemas totales
        todos_problemas = []
        todos_problemas.extend(endpoints_clientes.get("problemas", []))
        todos_problemas.extend(modelo_cliente.get("problemas", []))
        todos_problemas.extend(schemas_cliente.get("problemas", []))
        todos_problemas.extend(servicios_clientes.get("problemas", []))
        todos_problemas.extend(dependencias.get("problemas", []))
        
        self.resultados["problemas_encontrados"] = todos_problemas
        
        # Determinar estado final
        if not todos_problemas:
            self.resultados["estado_final"] = "PERFECTO"
            logger.info("🎉 MÓDULO DE CLIENTES PERFECTO")
        else:
            self.resultados["estado_final"] = "PROBLEMAS"
            logger.warning(f"⚠️ MÓDULO CON {len(todos_problemas)} PROBLEMAS")
        
        # Mostrar resumen
        logger.info("")
        logger.info("📊 RESUMEN DE VERIFICACIÓN")
        logger.info("-" * 40)
        logger.info(f"📄 Endpoints verificados: {len(self.resultados['endpoints_verificados'])}")
        logger.info(f"📊 Modelos verificados: {len(self.resultados['modelos_verificados'])}")
        logger.info(f"📋 Schemas verificados: {len(self.resultados['archivos_verificados'])}")
        logger.info(f"🔧 Servicios verificados: {len(self.resultados['servicios_verificados'])}")
        logger.info(f"🔗 Dependencias verificadas: {len(self.resultados['dependencias_verificadas']['dependencias_verificadas'])}")
        logger.info(f"❌ Problemas encontrados: {len(todos_problemas)}")
        logger.info(f"🎯 Estado final: {self.resultados['estado_final']}")
        
        logger.info("")
        logger.info("🎉 VERIFICACIÓN COMPLETA DEL MÓDULO DE CLIENTES FINALIZADA")
        logger.info("=" * 60)
        
        return self.resultados

def main():
    """Función principal para ejecutar la verificación"""
    verificador = VerificacionClientesCompleta()
    resultados = verificador.ejecutar_verificacion_completa()
    
    # Guardar reporte
    with open('reporte_verificacion_clientes_completa.json', 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    logger.info("💾 Reporte guardado en: reporte_verificacion_clientes_completa.json")
    
    return resultados

if __name__ == "__main__":
    main()
