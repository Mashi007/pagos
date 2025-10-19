"""
Cuarto Enfoque de Análisis - Auditoría Completa de Endpoints
Verificación de integridad, encadenamiento y rendimiento de endpoints
"""
import os
import ast
import logging
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cuarto_analisis_endpoints.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CuartoAnalisisEndpoints:
    """Cuarto enfoque de análisis - Auditoría completa de endpoints"""
    
    def __init__(self):
        self.resultados = {
            "fecha_auditoria": datetime.now().isoformat(),
            "endpoints_auditados": [],
            "endpoints_corruptos": [],
            "endpoints_optimizados": [],
            "problemas_encontrados": [],
            "mejoras_aplicadas": [],
            "resumen": {}
        }
        
        # Endpoints críticos para auditar
        self.endpoints_criticos = {
            "auth": "backend/app/api/v1/endpoints/auth.py",
            "clientes": "backend/app/api/v1/endpoints/clientes.py",
            "usuarios": "backend/app/api/v1/endpoints/usuarios.py",
            "validadores": "backend/app/api/v1/endpoints/validadores.py",
            "auditoria": "backend/app/api/v1/endpoints/auditoria.py"
        }
    
    def analizar_estructura_endpoint(self, archivo_path: str) -> Dict:
        """Analiza la estructura de un archivo de endpoints"""
        logger.info(f"🔍 Analizando estructura: {archivo_path}")
        
        resultado = {
            "archivo": archivo_path,
            "existe": False,
            "router_definido": False,
            "endpoints_encontrados": [],
            "dependencias": [],
            "imports": [],
            "problemas_estructura": [],
            "estado": "ERROR"
        }
        
        if not os.path.exists(archivo_path):
            resultado["problemas_estructura"].append("Archivo no encontrado")
            return resultado
        
        resultado["existe"] = True
        
        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Verificar router
            if "APIRouter" in contenido:
                resultado["router_definido"] = True
                logger.info(f"✅ Router definido en {archivo_path}")
            else:
                resultado["problemas_estructura"].append("Router no definido")
                logger.warning(f"⚠️ Router no definido en {archivo_path}")
            
            # Buscar endpoints
            endpoints_pattern = r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
            endpoints = re.findall(endpoints_pattern, contenido)
            
            for metodo, ruta in endpoints:
                endpoint_info = {
                    "metodo": metodo.upper(),
                    "ruta": ruta,
                    "funcion": self._buscar_funcion_endpoint(contenido, metodo, ruta)
                }
                resultado["endpoints_encontrados"].append(endpoint_info)
                logger.info(f"📋 Endpoint encontrado: {metodo.upper()} {ruta}")
            
            # Buscar dependencias
            deps_pattern = r'Depends\(([^)]+)\)'
            dependencias = re.findall(deps_pattern, contenido)
            resultado["dependencias"] = list(set(dependencias))
            
            # Buscar imports
            imports_pattern = r'^from\s+([^\s]+)\s+import\s+([^\n]+)'
            imports = re.findall(imports_pattern, contenido, re.MULTILINE)
            resultado["imports"] = imports
            
            # Determinar estado
            if resultado["router_definido"] and resultado["endpoints_encontrados"]:
                resultado["estado"] = "OK"
            else:
                resultado["estado"] = "PROBLEMAS"
            
        except Exception as e:
            resultado["problemas_estructura"].append(f"Error analizando: {str(e)}")
            logger.error(f"❌ Error analizando {archivo_path}: {e}")
        
        return resultado
    
    def _buscar_funcion_endpoint(self, contenido: str, metodo: str, ruta: str) -> Optional[str]:
        """Busca la función asociada a un endpoint"""
        try:
            # Buscar la función después del decorador
            pattern = rf'@router\.{metodo}\s*\(\s*["\']?{re.escape(ruta)}["\']?\s*\)\s*\n\s*(?:async\s+)?def\s+(\w+)'
            match = re.search(pattern, contenido, re.MULTILINE)
            return match.group(1) if match else None
        except:
            return None
    
    def verificar_encadenamiento_dependencias(self, archivo_path: str) -> Dict:
        """Verifica el encadenamiento y dependencias de endpoints"""
        logger.info(f"🔗 Verificando encadenamiento: {archivo_path}")
        
        resultado = {
            "archivo": archivo_path,
            "dependencias_validas": [],
            "dependencias_invalidas": [],
            "encadenamiento_ok": True,
            "problemas": []
        }
        
        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Verificar dependencias comunes
            dependencias_comunes = [
                "get_db",
                "get_current_user", 
                "get_current_active_user",
                "AuthService",
                "create_access_token"
            ]
            
            for dep in dependencias_comunes:
                if dep in contenido:
                    # Verificar que esté importado
                    if f"import {dep}" in contenido or f"from" in contenido and dep in contenido:
                        resultado["dependencias_validas"].append(dep)
                        logger.info(f"✅ Dependencia válida: {dep}")
                    else:
                        resultado["dependencias_invalidas"].append(dep)
                        resultado["problemas"].append(f"Dependencia {dep} usada pero no importada")
                        logger.warning(f"⚠️ Dependencia inválida: {dep}")
            
            # Verificar encadenamiento de endpoints
            if "get_current_user" in resultado["dependencias_validas"]:
                resultado["encadenamiento_ok"] = True
                logger.info("✅ Encadenamiento de autenticación OK")
            else:
                resultado["encadenamiento_ok"] = False
                resultado["problemas"].append("Falta encadenamiento de autenticación")
                logger.warning("⚠️ Problema de encadenamiento de autenticación")
            
        except Exception as e:
            resultado["problemas"].append(f"Error verificando encadenamiento: {str(e)}")
            logger.error(f"❌ Error verificando encadenamiento en {archivo_path}: {e}")
        
        return resultado
    
    def analizar_rendimiento_endpoints(self, archivo_path: str) -> Dict:
        """Analiza el rendimiento potencial de los endpoints"""
        logger.info(f"⚡ Analizando rendimiento: {archivo_path}")
        
        resultado = {
            "archivo": archivo_path,
            "problemas_rendimiento": [],
            "optimizaciones_sugeridas": [],
            "score_rendimiento": 0,
            "estado": "OK"
        }
        
        try:
            with open(archivo_path, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            score = 100
            
            # Verificar problemas comunes de rendimiento
            
            # 1. Consultas N+1
            if "for" in contenido and "db.query" in contenido:
                resultado["problemas_rendimiento"].append("Posible problema N+1 en consultas")
                resultado["optimizaciones_sugeridas"].append("Usar joinedload o selectinload")
                score -= 20
                logger.warning("⚠️ Posible problema N+1 detectado")
            
            # 2. Falta de paginación
            if "db.query" in contenido and "limit" not in contenido and "offset" not in contenido:
                resultado["problemas_rendimiento"].append("Falta paginación en consultas")
                resultado["optimizaciones_sugeridas"].append("Implementar paginación")
                score -= 15
                logger.warning("⚠️ Falta paginación detectada")
            
            # 3. Transacciones largas
            if "db.commit()" in contenido and len(contenido.split("db.commit()")) > 3:
                resultado["problemas_rendimiento"].append("Múltiples commits en una función")
                resultado["optimizaciones_sugeridas"].append("Optimizar transacciones")
                score -= 10
                logger.warning("⚠️ Múltiples commits detectados")
            
            # 4. Falta de validación de entrada
            if "@router.post" in contenido and "HTTPException" not in contenido:
                resultado["problemas_rendimiento"].append("Falta validación de entrada")
                resultado["optimizaciones_sugeridas"].append("Agregar validaciones")
                score -= 10
                logger.warning("⚠️ Falta validación de entrada")
            
            # 5. Manejo de errores
            if "try:" in contenido and "except" not in contenido:
                resultado["problemas_rendimiento"].append("Manejo de errores incompleto")
                resultado["optimizaciones_sugeridas"].append("Completar manejo de errores")
                score -= 15
                logger.warning("⚠️ Manejo de errores incompleto")
            
            resultado["score_rendimiento"] = max(0, score)
            
            if score < 70:
                resultado["estado"] = "PROBLEMAS"
                logger.warning(f"⚠️ Score de rendimiento bajo: {score}")
            else:
                logger.info(f"✅ Score de rendimiento bueno: {score}")
            
        except Exception as e:
            resultado["problemas_rendimiento"].append(f"Error analizando rendimiento: {str(e)}")
            logger.error(f"❌ Error analizando rendimiento en {archivo_path}: {e}")
        
        return resultado
    
    def auditar_endpoint_completo(self, archivo_path: str) -> Dict:
        """Audita completamente un endpoint"""
        logger.info(f"🔍 AUDITANDO COMPLETAMENTE: {archivo_path}")
        logger.info("-" * 50)
        
        # Análisis de estructura
        estructura = self.analizar_estructura_endpoint(archivo_path)
        
        # Verificación de encadenamiento
        encadenamiento = self.verificar_encadenamiento_dependencias(archivo_path)
        
        # Análisis de rendimiento
        rendimiento = self.analizar_rendimiento_endpoints(archivo_path)
        
        # Resultado combinado
        resultado_completo = {
            "archivo": archivo_path,
            "estructura": estructura,
            "encadenamiento": encadenamiento,
            "rendimiento": rendimiento,
            "estado_general": "OK",
            "requiere_reescritura": False,
            "problemas_totales": []
        }
        
        # Determinar estado general
        problemas = []
        problemas.extend(estructura.get("problemas_estructura", []))
        problemas.extend(encadenamiento.get("problemas", []))
        problemas.extend(rendimiento.get("problemas_rendimiento", []))
        
        resultado_completo["problemas_totales"] = problemas
        
        if problemas:
            resultado_completo["estado_general"] = "PROBLEMAS"
            if len(problemas) > 3 or rendimiento["score_rendimiento"] < 50:
                resultado_completo["requiere_reescritura"] = True
                logger.warning(f"⚠️ {archivo_path} requiere reescritura")
            else:
                logger.warning(f"⚠️ {archivo_path} tiene problemas menores")
        else:
            logger.info(f"✅ {archivo_path} está en buen estado")
        
        return resultado_completo
    
    def ejecutar_auditoria_completa(self) -> Dict:
        """Ejecuta la auditoría completa de todos los endpoints"""
        logger.info("🚀 INICIANDO CUARTO ENFOQUE - AUDITORÍA COMPLETA DE ENDPOINTS")
        logger.info("=" * 60)
        logger.info(f"📅 Fecha: {datetime.now()}")
        logger.info(f"🎯 Objetivo: Auditar integridad, encadenamiento y rendimiento")
        logger.info("=" * 60)
        
        resultados_auditoria = []
        endpoints_problematicos = []
        endpoints_para_reescribir = []
        
        # Auditar cada endpoint crítico
        for nombre, archivo_path in self.endpoints_criticos.items():
            logger.info("")
            logger.info(f"📁 AUDITANDO: {nombre.upper()}")
            logger.info("-" * 30)
            
            resultado = self.auditar_endpoint_completo(archivo_path)
            resultados_auditoria.append(resultado)
            
            if resultado["estado_general"] == "PROBLEMAS":
                endpoints_problematicos.append(resultado)
            
            if resultado["requiere_reescritura"]:
                endpoints_para_reescribir.append(resultado)
        
        # Generar resumen
        total_endpoints = len(resultados_auditoria)
        endpoints_ok = total_endpoints - len(endpoints_problematicos)
        
        self.resultados["endpoints_auditados"] = resultados_auditoria
        self.resultados["endpoints_corruptos"] = endpoints_problematicos
        self.resultados["endpoints_optimizados"] = endpoints_para_reescribir
        
        self.resultados["resumen"] = {
            "total_endpoints": total_endpoints,
            "endpoints_ok": endpoints_ok,
            "endpoints_problematicos": len(endpoints_problematicos),
            "endpoints_para_reescribir": len(endpoints_para_reescribir),
            "porcentaje_ok": (endpoints_ok / total_endpoints) * 100 if total_endpoints > 0 else 0
        }
        
        # Mostrar resumen
        logger.info("")
        logger.info("📊 RESUMEN DE AUDITORÍA")
        logger.info("-" * 40)
        logger.info(f"📄 Total endpoints auditados: {total_endpoints}")
        logger.info(f"✅ Endpoints OK: {endpoints_ok}")
        logger.info(f"⚠️ Endpoints problemáticos: {len(endpoints_problematicos)}")
        logger.info(f"🔧 Endpoints para reescribir: {len(endpoints_para_reescribir)}")
        logger.info(f"📈 Porcentaje OK: {self.resultados['resumen']['porcentaje_ok']:.1f}%")
        
        logger.info("")
        logger.info("🎉 CUARTO ENFOQUE DE AUDITORÍA COMPLETADO")
        logger.info("=" * 60)
        
        return self.resultados

def main():
    """Función principal para ejecutar la auditoría"""
    auditor = CuartoAnalisisEndpoints()
    resultados = auditor.ejecutar_auditoria_completa()
    
    # Guardar reporte
    with open('reporte_cuarto_analisis_endpoints.json', 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    logger.info("💾 Reporte guardado en: reporte_cuarto_analisis_endpoints.json")
    
    return resultados

if __name__ == "__main__":
    main()
