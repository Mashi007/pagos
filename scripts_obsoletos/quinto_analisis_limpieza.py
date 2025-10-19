"""
Quinto Enfoque de Análisis - Limpieza de Endpoints Innecesarios
Identificación y eliminación de rutas y endpoints redundantes o innecesarios
"""
import os
import re
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Set
import json

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quinto_analisis_limpieza.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class QuintoAnalisisLimpieza:
    """Quinto enfoque de análisis - Limpieza de endpoints innecesarios"""
    
    def __init__(self):
        self.resultados = {
            "fecha_limpieza": datetime.now().isoformat(),
            "endpoints_analizados": [],
            "endpoints_duplicados": [],
            "endpoints_debug": [],
            "endpoints_no_utilizados": [],
            "codigo_muerto": [],
            "endpoints_a_eliminar": [],
            "endpoints_a_mantener": [],
            "resumen": {}
        }
        
        # Patrones para identificar endpoints problemáticos
        self.patrones_problematicos = {
            "debug": [
                r"/debug",
                r"/test",
                r"/ping",
                r"/health",
                r"/status",
                r"/info",
                r"/version"
            ],
            "duplicados": [
                r"/list",
                r"/listar",
                r"/get",
                r"/obtener",
                r"/create",
                r"/crear",
                r"/update",
                r"/actualizar",
                r"/delete",
                r"/eliminar"
            ],
            "innecesarios": [
                r"/temp",
                r"/tmp",
                r"/backup",
                r"/old",
                r"/deprecated",
                r"/legacy"
            ]
        }
        
        # Endpoints esenciales que NO deben eliminarse
        self.endpoints_esenciales = {
            "auth": ["/login", "/logout", "/me", "/refresh", "/change-password"],
            "clientes": ["/", "/{id}", "/crear", "/{id}", "/count"],
            "usuarios": ["/", "/{id}", "/crear", "/{id}"],
            "validadores": ["/ping", "/verificacion-validadores"]
        }
    
    def analizar_endpoints_archivo(self, archivo_path: str) -> Dict:
        """Analiza todos los endpoints de un archivo"""
        logger.info(f"🔍 Analizando endpoints en: {archivo_path}")
        
        resultado = {
            "archivo": archivo_path,
            "existe": False,
            "endpoints_encontrados": [],
            "endpoints_debug": [],
            "endpoints_duplicados": [],
            "endpoints_innecesarios": [],
            "codigo_muerto": [],
            "estado": "OK"
        }
        
        if not os.path.exists(archivo_path):
            resultado["estado"] = "ERROR"
            resultado["codigo_muerto"].append("Archivo no encontrado")
            return resultado
        
        resultado["existe"] = True
        
        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Buscar todos los endpoints
            endpoints_pattern = r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
            endpoints = re.findall(endpoints_pattern, contenido)
            
            for metodo, ruta in endpoints:
                endpoint_info = {
                    "metodo": metodo.upper(),
                    "ruta": ruta,
                    "funcion": self._buscar_funcion_endpoint(contenido, metodo, ruta),
                    "es_debug": False,
                    "es_duplicado": False,
                    "es_innecesario": False,
                    "razon": ""
                }
                
                # Clasificar endpoint
                clasificacion = self._clasificar_endpoint(ruta, metodo)
                endpoint_info.update(clasificacion)
                
                resultado["endpoints_encontrados"].append(endpoint_info)
                
                # Agregar a categorías específicas
                if endpoint_info["es_debug"]:
                    resultado["endpoints_debug"].append(endpoint_info)
                if endpoint_info["es_duplicado"]:
                    resultado["endpoints_duplicados"].append(endpoint_info)
                if endpoint_info["es_innecesario"]:
                    resultado["endpoints_innecesarios"].append(endpoint_info)
                
                logger.info(f"📋 {metodo.upper()} {ruta} - {endpoint_info['razon']}")
            
            # Buscar código muerto
            codigo_muerto = self._buscar_codigo_muerto(contenido)
            resultado["codigo_muerto"] = codigo_muerto
            
        except Exception as e:
            resultado["estado"] = "ERROR"
            resultado["codigo_muerto"].append(f"Error analizando: {str(e)}")
            logger.error(f"❌ Error analizando {archivo_path}: {e}")
        
        return resultado
    
    def _buscar_funcion_endpoint(self, contenido: str, metodo: str, ruta: str) -> Optional[str]:
        """Busca la función asociada a un endpoint"""
        try:
            pattern = rf'@router\.{metodo}\s*\(\s*["\']?{re.escape(ruta)}["\']?\s*\)\s*\n\s*(?:async\s+)?def\s+(\w+)'
            match = re.search(pattern, contenido, re.MULTILINE)
            return match.group(1) if match else None
        except:
            return None
    
    def _clasificar_endpoint(self, ruta: str, metodo: str) -> Dict:
        """Clasifica un endpoint según su utilidad"""
        clasificacion = {
            "es_debug": False,
            "es_duplicado": False,
            "es_innecesario": False,
            "razon": "Endpoint normal"
        }
        
        # Verificar si es endpoint de debug
        for patron in self.patrones_problematicos["debug"]:
            if re.search(patron, ruta, re.IGNORECASE):
                clasificacion["es_debug"] = True
                clasificacion["razon"] = f"Endpoint de debug: {patron}"
                break
        
        # Verificar si es duplicado
        for patron in self.patrones_problematicos["duplicados"]:
            if re.search(patron, ruta, re.IGNORECASE):
                clasificacion["es_duplicado"] = True
                clasificacion["razon"] = f"Posible duplicado: {patron}"
                break
        
        # Verificar si es innecesario
        for patron in self.patrones_problematicos["innecesarios"]:
            if re.search(patron, ruta, re.IGNORECASE):
                clasificacion["es_innecesario"] = True
                clasificacion["razon"] = f"Endpoint innecesario: {patron}"
                break
        
        # Verificar endpoints específicos problemáticos
        if ruta in ["/ping", "/health", "/status"]:
            clasificacion["es_debug"] = True
            clasificacion["razon"] = "Endpoint de monitoreo/debug"
        
        if ruta in ["/test", "/debug", "/info"]:
            clasificacion["es_debug"] = True
            clasificacion["razon"] = "Endpoint de prueba/debug"
        
        return clasificacion
    
    def _buscar_codigo_muerto(self, contenido: str) -> List[str]:
        """Busca código muerto en el archivo"""
        codigo_muerto = []
        
        # Buscar funciones no utilizadas
        funciones_pattern = r'def\s+(\w+)\s*\('
        funciones = re.findall(funciones_pattern, contenido)
        
        for funcion in funciones:
            # Verificar si la función se usa
            if funcion not in ["add_cors_headers", "login", "logout", "get_current_user_info"]:
                # Buscar llamadas a la función
                llamadas_pattern = rf'\b{funcion}\s*\('
                llamadas = re.findall(llamadas_pattern, contenido)
                
                if len(llamadas) <= 1:  # Solo la definición
                    codigo_muerto.append(f"Función no utilizada: {funcion}")
        
        # Buscar imports no utilizados
        imports_pattern = r'from\s+([^\s]+)\s+import\s+([^\n]+)'
        imports = re.findall(imports_pattern, contenido, re.MULTILINE)
        
        for modulo, funciones_importadas in imports:
            funciones_lista = [f.strip() for f in funciones_importadas.split(',')]
            for funcion in funciones_lista:
                if funcion not in contenido.replace(f"from {modulo} import", ""):
                    codigo_muerto.append(f"Import no utilizado: {funcion}")
        
        return codigo_muerto
    
    def identificar_endpoints_duplicados(self, resultados_archivos: List[Dict]) -> List[Dict]:
        """Identifica endpoints duplicados entre archivos"""
        logger.info("🔍 IDENTIFICANDO ENDPOINTS DUPLICADOS")
        logger.info("-" * 50)
        
        todos_endpoints = []
        duplicados = []
        
        # Recopilar todos los endpoints
        for resultado in resultados_archivos:
            for endpoint in resultado["endpoints_encontrados"]:
                endpoint["archivo"] = resultado["archivo"]
                todos_endpoints.append(endpoint)
        
        # Buscar duplicados por ruta y método
        rutas_vistas = {}
        for endpoint in todos_endpoints:
            clave = f"{endpoint['metodo']} {endpoint['ruta']}"
            if clave in rutas_vistas:
                duplicado = {
                    "ruta": endpoint['ruta'],
                    "metodo": endpoint['metodo'],
                    "archivo_original": rutas_vistas[clave]['archivo'],
                    "archivo_duplicado": endpoint['archivo'],
                    "funcion_original": rutas_vistas[clave]['funcion'],
                    "funcion_duplicada": endpoint['funcion']
                }
                duplicados.append(duplicado)
                logger.warning(f"⚠️ Duplicado encontrado: {clave}")
            else:
                rutas_vistas[clave] = endpoint
        
        return duplicados
    
    def generar_recomendaciones_limpieza(self, resultados_archivos: List[Dict]) -> Dict:
        """Genera recomendaciones de limpieza"""
        logger.info("🧹 GENERANDO RECOMENDACIONES DE LIMPIEZA")
        logger.info("-" * 50)
        
        recomendaciones = {
            "endpoints_a_eliminar": [],
            "endpoints_a_mantener": [],
            "codigo_a_limpiar": [],
            "archivos_a_optimizar": []
        }
        
        for resultado in resultados_archivos:
            archivo = resultado["archivo"]
            
            # Endpoints de debug - evaluar eliminación
            for endpoint in resultado["endpoints_debug"]:
                if endpoint["ruta"] in ["/ping"]:
                    # Mantener /ping solo en validadores
                    if "validadores" in archivo:
                        recomendaciones["endpoints_a_mantener"].append({
                            "archivo": archivo,
                            "endpoint": endpoint,
                            "razon": "Endpoint de monitoreo necesario"
                        })
                    else:
                        recomendaciones["endpoints_a_eliminar"].append({
                            "archivo": archivo,
                            "endpoint": endpoint,
                            "razon": "Endpoint de debug innecesario"
                        })
                else:
                    recomendaciones["endpoints_a_eliminar"].append({
                        "archivo": archivo,
                        "endpoint": endpoint,
                        "razon": "Endpoint de debug"
                    })
            
            # Endpoints duplicados - mantener solo uno
            for endpoint in resultado["endpoints_duplicados"]:
                recomendaciones["endpoints_a_eliminar"].append({
                    "archivo": archivo,
                    "endpoint": endpoint,
                    "razon": "Endpoint duplicado"
                })
            
            # Endpoints innecesarios
            for endpoint in resultado["endpoints_innecesarios"]:
                recomendaciones["endpoints_a_eliminar"].append({
                    "archivo": archivo,
                    "endpoint": endpoint,
                    "razon": "Endpoint innecesario"
                })
            
            # Código muerto
            if resultado["codigo_muerto"]:
                recomendaciones["codigo_a_limpiar"].extend(resultado["codigo_muerto"])
                recomendaciones["archivos_a_optimizar"].append(archivo)
        
        return recomendaciones
    
    def ejecutar_limpieza_completa(self) -> Dict:
        """Ejecuta el análisis completo de limpieza"""
        logger.info("🚀 INICIANDO QUINTO ENFOQUE - LIMPIEZA DE ENDPOINTS")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha: {datetime.now()}")
        logger.info(f"🎯 Objetivo: Identificar y eliminar endpoints innecesarios")
        logger.info("=" * 60)
        
        # Archivos de endpoints a analizar
        archivos_endpoints = [
            "backend/app/api/v1/endpoints/auth.py",
            "backend/app/api/v1/endpoints/clientes.py",
            "backend/app/api/v1/endpoints/usuarios.py",
            "backend/app/api/v1/endpoints/validadores.py",
            "backend/app/api/v1/endpoints/auditoria.py"
        ]
        
        resultados_archivos = []
        
        # Analizar cada archivo
        for archivo_path in archivos_endpoints:
            logger.info("")
            logger.info(f"📁 ANALIZANDO: {archivo_path}")
            logger.info("-" * 40)
            
            resultado = self.analizar_endpoints_archivo(archivo_path)
            resultados_archivos.append(resultado)
            
            # Mostrar resumen del archivo
            total = len(resultado["endpoints_encontrados"])
            debug = len(resultado["endpoints_debug"])
            duplicados = len(resultado["endpoints_duplicados"])
            innecesarios = len(resultado["endpoints_innecesarios"])
            codigo_muerto = len(resultado["codigo_muerto"])
            
            logger.info(f"📊 Resumen: {total} endpoints, {debug} debug, {duplicados} duplicados, {innecesarios} innecesarios, {codigo_muerto} código muerto")
        
        # Identificar duplicados entre archivos
        logger.info("")
        duplicados_cross_file = self.identificar_endpoints_duplicados(resultados_archivos)
        
        # Generar recomendaciones
        logger.info("")
        recomendaciones = self.generar_recomendaciones_limpieza(resultados_archivos)
        
        # Compilar resultados finales
        self.resultados["endpoints_analizados"] = resultados_archivos
        self.resultados["endpoints_duplicados"] = duplicados_cross_file
        self.resultados["endpoints_a_eliminar"] = recomendaciones["endpoints_a_eliminar"]
        self.resultados["endpoints_a_mantener"] = recomendaciones["endpoints_a_mantener"]
        self.resultados["codigo_muerto"] = recomendaciones["codigo_a_limpiar"]
        
        # Generar resumen
        total_endpoints = sum(len(r["endpoints_encontrados"]) for r in resultados_archivos)
        endpoints_a_eliminar = len(recomendaciones["endpoints_a_eliminar"])
        endpoints_a_mantener = len(recomendaciones["endpoints_a_mantener"])
        codigo_muerto_total = len(recomendaciones["codigo_a_limpiar"])
        
        self.resultados["resumen"] = {
            "total_endpoints": total_endpoints,
            "endpoints_a_eliminar": endpoints_a_eliminar,
            "endpoints_a_mantener": endpoints_a_mantener,
            "codigo_muerto": codigo_muerto_total,
            "porcentaje_limpieza": (endpoints_a_eliminar / total_endpoints) * 100 if total_endpoints > 0 else 0
        }
        
        # Mostrar resumen final
        logger.info("")
        logger.info("📊 RESUMEN DE LIMPIEZA")
        logger.info("-" * 40)
        logger.info(f"📄 Total endpoints analizados: {total_endpoints}")
        logger.info(f"🗑️ Endpoints a eliminar: {endpoints_a_eliminar}")
        logger.info(f"✅ Endpoints a mantener: {endpoints_a_mantener}")
        logger.info(f"🧹 Código muerto encontrado: {codigo_muerto_total}")
        logger.info(f"📈 Porcentaje de limpieza: {self.resultados['resumen']['porcentaje_limpieza']:.1f}%")
        
        logger.info("")
        logger.info("🎉 QUINTO ENFOQUE DE LIMPIEZA COMPLETADO")
        logger.info("=" * 60)
        
        return self.resultados

def main():
    """Función principal para ejecutar la limpieza"""
    limpiador = QuintoAnalisisLimpieza()
    resultados = limpiador.ejecutar_limpieza_completa()
    
    # Guardar reporte
    with open('reporte_quinto_analisis_limpieza.json', 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    logger.info("💾 Reporte guardado en: reporte_quinto_analisis_limpieza.json")
    
    return resultados

if __name__ == "__main__":
    main()
