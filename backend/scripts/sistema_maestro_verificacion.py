"""
Sistema Maestro de Verificación - Integración Completa
Combina todos los enfoques de verificación implementados
"""
import json
import logging
import time
from datetime import datetime
from typing import Dict, List
import subprocess
import sys
import os

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sistema_maestro_verificacion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SistemaMaestroVerificacion:
    """Sistema maestro que integra todos los enfoques de verificación"""
    
    def __init__(self):
        self.enfoques_disponibles = {
            "segundo_enfoque": {
                "archivo": "verificacion_sistema.py",
                "descripcion": "Segundo enfoque básico - Verificación simple",
                "comando": "python verificacion_sistema.py"
            },
            "tercer_enfoque": {
                "archivo": "tercer_enfoque_verificacion_avanzada.py",
                "descripcion": "Tercer enfoque avanzado - Monitoreo con métricas",
                "comando": "python tercer_enfoque_verificacion_avanzada.py"
            },
            "retry_automatico": {
                "archivo": "verificacion_con_retry_automatico.py",
                "descripcion": "Verificación con retry automático",
                "comando": "python verificacion_con_retry_automatico.py"
            },
            "metricas_rendimiento": {
                "archivo": "metricas_rendimiento_avanzadas.py",
                "descripcion": "Análisis de métricas de rendimiento",
                "comando": "python metricas_rendimiento_avanzadas.py"
            },
            "dashboard_tiempo_real": {
                "archivo": "dashboard_estado_tiempo_real.py",
                "descripcion": "Dashboard de estado en tiempo real",
                "comando": "python dashboard_estado_tiempo_real.py"
            }
        }
        
        self.reportes_generados = []
        self.estado_general = "Pendiente"
    
    def mostrar_menu_principal(self):
        """Muestra el menú principal del sistema"""
        print("\n" + "="*80)
        print("🚀 SISTEMA MAESTRO DE VERIFICACIÓN - RAPICREDIT")
        print("="*80)
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("🎯 Integración completa de todos los enfoques de verificación")
        print("="*80)
        
        print("\n📋 ENFOQUES DISPONIBLES:")
        print("-" * 50)
        
        for i, (clave, info) in enumerate(self.enfoques_disponibles.items(), 1):
            estado_archivo = "✅" if os.path.exists(info["archivo"]) else "❌"
            print(f"{i}. {estado_archivo} {info['descripcion']}")
            print(f"   📁 Archivo: {info['archivo']}")
            print()
        
        print("0. 🚀 Ejecutar TODOS los enfoques secuencialmente")
        print("9. 📊 Generar reporte consolidado")
        print("X. 🚪 Salir")
        print("-" * 50)
    
    def ejecutar_enfoque(self, clave_enfoque: str) -> Dict:
        """Ejecuta un enfoque específico"""
        if clave_enfoque not in self.enfoques_disponibles:
            logger.error(f"❌ Enfoque '{clave_enfoque}' no encontrado")
            return {"error": "Enfoque no encontrado"}
        
        info = self.enfoques_disponibles[clave_enfoque]
        
        if not os.path.exists(info["archivo"]):
            logger.error(f"❌ Archivo no encontrado: {info['archivo']}")
            return {"error": "Archivo no encontrado"}
        
        logger.info(f"🚀 Ejecutando: {info['descripcion']}")
        logger.info(f"📁 Archivo: {info['archivo']}")
        
        try:
            # Ejecutar el script
            resultado = subprocess.run(
                info["comando"].split(),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos máximo
            )
            
            if resultado.returncode == 0:
                logger.info(f"✅ {info['descripcion']} ejecutado exitosamente")
                
                reporte = {
                    "enfoque": clave_enfoque,
                    "descripcion": info["descripcion"],
                    "fecha_ejecucion": datetime.now().isoformat(),
                    "estado": "exitoso",
                    "salida": resultado.stdout,
                    "archivo": info["archivo"]
                }
                
                # Buscar archivos de reporte generados
                archivos_reporte = self._buscar_archivos_reporte()
                if archivos_reporte:
                    reporte["archivos_generados"] = archivos_reporte
                
                return reporte
                
            else:
                logger.error(f"❌ Error ejecutando {info['descripcion']}")
                logger.error(f"Error: {resultado.stderr}")
                
                return {
                    "enfoque": clave_enfoque,
                    "descripcion": info["descripcion"],
                    "fecha_ejecucion": datetime.now().isoformat(),
                    "estado": "error",
                    "error": resultado.stderr,
                    "archivo": info["archivo"]
                }
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ Timeout ejecutando {info['descripcion']}")
            return {
                "enfoque": clave_enfoque,
                "descripcion": info["descripcion"],
                "fecha_ejecucion": datetime.now().isoformat(),
                "estado": "timeout",
                "error": "Timeout después de 5 minutos",
                "archivo": info["archivo"]
            }
        except Exception as e:
            logger.error(f"❌ Excepción ejecutando {info['descripcion']}: {e}")
            return {
                "enfoque": clave_enfoque,
                "descripcion": info["descripcion"],
                "fecha_ejecucion": datetime.now().isoformat(),
                "estado": "excepcion",
                "error": str(e),
                "archivo": info["archivo"]
            }
    
    def ejecutar_todos_enfoques(self) -> List[Dict]:
        """Ejecuta todos los enfoques secuencialmente"""
        logger.info("🚀 EJECUTANDO TODOS LOS ENFOQUES SECUENCIALMENTE")
        logger.info("=" * 60)
        
        resultados = []
        
        # Orden de ejecución recomendado
        orden_ejecucion = [
            "segundo_enfoque",
            "tercer_enfoque", 
            "retry_automatico",
            "metricas_rendimiento"
            # dashboard_tiempo_real se ejecuta por separado ya que es un servidor web
        ]
        
        for i, clave_enfoque in enumerate(orden_ejecucion, 1):
            logger.info(f"\n📋 Ejecutando enfoque {i}/{len(orden_ejecucion)}: {clave_enfoque}")
            logger.info("-" * 50)
            
            resultado = self.ejecutar_enfoque(clave_enfoque)
            resultados.append(resultado)
            
            # Pequeña pausa entre enfoques
            if i < len(orden_ejecucion):
                logger.info("⏳ Esperando 5 segundos antes del siguiente enfoque...")
                time.sleep(5)
        
        logger.info("\n🎉 EJECUCIÓN DE TODOS LOS ENFOQUES COMPLETADA")
        logger.info("=" * 60)
        
        return resultados
    
    def _buscar_archivos_reporte(self) -> List[str]:
        """Busca archivos de reporte generados"""
        archivos_reporte = []
        patrones = [
            "reporte_*.json",
            "*_verificacion.log",
            "*_enfoque*.json"
        ]
        
        for patron in patrones:
            try:
                import glob
                archivos = glob.glob(patron)
                archivos_reporte.extend(archivos)
            except:
                pass
        
        return list(set(archivos_reporte))  # Eliminar duplicados
    
    def generar_reporte_consolidado(self, resultados: List[Dict] = None) -> Dict:
        """Genera un reporte consolidado de todos los enfoques"""
        logger.info("📊 GENERANDO REPORTE CONSOLIDADO")
        logger.info("-" * 40)
        
        if resultados is None:
            resultados = self.reportes_generados
        
        # Estadísticas generales
        total_enfoques = len(resultados)
        exitosos = sum(1 for r in resultados if r.get("estado") == "exitoso")
        fallidos = total_enfoques - exitosos
        
        # Análisis por enfoque
        analisis_enfoques = {}
        for resultado in resultados:
            enfoque = resultado.get("enfoque", "desconocido")
            if enfoque not in analisis_enfoques:
                analisis_enfoques[enfoque] = {
                    "total_ejecuciones": 0,
                    "exitosos": 0,
                    "fallidos": 0,
                    "ultima_ejecucion": None
                }
            
            analisis_enfoques[enfoque]["total_ejecuciones"] += 1
            if resultado.get("estado") == "exitoso":
                analisis_enfoques[enfoque]["exitosos"] += 1
            else:
                analisis_enfoques[enfoque]["fallidos"] += 1
            
            analisis_enfoques[enfoque]["ultima_ejecucion"] = resultado.get("fecha_ejecucion")
        
        # Determinar estado general
        if exitosos == total_enfoques:
            estado_general = "🟢 EXCELENTE"
        elif exitosos >= total_enfoques * 0.8:
            estado_general = "🟡 BUENO"
        elif exitosos >= total_enfoques * 0.5:
            estado_general = "🟠 ACEPTABLE"
        else:
            estado_general = "🔴 CRÍTICO"
        
        # Generar recomendaciones
        recomendaciones = self._generar_recomendaciones_consolidadas(resultados)
        
        reporte_consolidado = {
            "fecha_generacion": datetime.now().isoformat(),
            "resumen_ejecutivo": {
                "estado_general": estado_general,
                "total_enfoques": total_enfoques,
                "exitosos": exitosos,
                "fallidos": fallidos,
                "porcentaje_exito": round((exitosos / total_enfoques) * 100, 1) if total_enfoques > 0 else 0
            },
            "analisis_por_enfoque": analisis_enfoques,
            "resultados_detallados": resultados,
            "archivos_generados": self._buscar_archivos_reporte(),
            "recomendaciones": recomendaciones,
            "configuracion_sistema": {
                "enfoques_disponibles": len(self.enfoques_disponibles),
                "scripts_implementados": [info["archivo"] for info in self.enfoques_disponibles.values()],
                "version": "1.0.0"
            }
        }
        
        # Log del reporte
        logger.info(f"📈 Estado general: {estado_general}")
        logger.info(f"📊 Total enfoques: {total_enfoques}")
        logger.info(f"✅ Exitosos: {exitosos}")
        logger.info(f"❌ Fallidos: {fallidos}")
        logger.info(f"📈 Porcentaje éxito: {reporte_consolidado['resumen_ejecutivo']['porcentaje_exito']}%")
        
        return reporte_consolidado
    
    def _generar_recomendaciones_consolidadas(self, resultados: List[Dict]) -> List[str]:
        """Genera recomendaciones consolidadas"""
        recomendaciones = []
        
        # Analizar resultados fallidos
        fallidos = [r for r in resultados if r.get("estado") != "exitoso"]
        if fallidos:
            recomendaciones.append(f"🔧 Revisar {len(fallidos)} enfoque(s) que fallaron")
            for fallido in fallidos:
                recomendaciones.append(f"   - {fallido.get('descripcion', 'Desconocido')}: {fallido.get('error', 'Error desconocido')}")
        
        # Analizar archivos faltantes
        archivos_faltantes = []
        for clave, info in self.enfoques_disponibles.items():
            if not os.path.exists(info["archivo"]):
                archivos_faltantes.append(info["archivo"])
        
        if archivos_faltantes:
            recomendaciones.append(f"📁 Archivos faltantes: {', '.join(archivos_faltantes)}")
        
        # Recomendaciones generales
        exitosos = sum(1 for r in resultados if r.get("estado") == "exitoso")
        total = len(resultados)
        
        if exitosos == total:
            recomendaciones.append("✅ Todos los enfoques funcionando correctamente")
            recomendaciones.append("🔄 Considerar ejecución periódica para monitoreo continuo")
        elif exitosos >= total * 0.8:
            recomendaciones.append("⚠️ Mayoría de enfoques funcionando - revisar los fallidos")
        else:
            recomendaciones.append("🚨 Problemas significativos detectados - revisión urgente requerida")
        
        return recomendaciones
    
    def guardar_reporte_consolidado(self, reporte: Dict):
        """Guarda el reporte consolidado en archivo"""
        nombre_archivo = f"reporte_consolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Reporte consolidado guardado en: {nombre_archivo}")
        return nombre_archivo
    
    def ejecutar_sistema_interactivo(self):
        """Ejecuta el sistema en modo interactivo"""
        logger.info("🎮 Iniciando sistema interactivo")
        
        while True:
            try:
                self.mostrar_menu_principal()
                
                opcion = input("\n🔍 Seleccione una opción: ").strip().upper()
                
                if opcion == 'X':
                    logger.info("👋 Saliendo del sistema")
                    break
                elif opcion == '0':
                    logger.info("🚀 Ejecutando todos los enfoques...")
                    resultados = self.ejecutar_todos_enfoques()
                    self.reportes_generados.extend(resultados)
                    
                    # Generar reporte consolidado automáticamente
                    reporte = self.generar_reporte_consolidado(resultados)
                    archivo = self.guardar_reporte_consolidado(reporte)
                    
                    print(f"\n✅ Ejecución completada. Reporte guardado en: {archivo}")
                    
                elif opcion == '9':
                    if self.reportes_generados:
                        reporte = self.generar_reporte_consolidado()
                        archivo = self.guardar_reporte_consolidado(reporte)
                        print(f"\n📊 Reporte consolidado generado: {archivo}")
                    else:
                        print("\n⚠️ No hay reportes disponibles. Ejecute algunos enfoques primero.")
                        
                elif opcion.isdigit():
                    indice = int(opcion) - 1
                    claves = list(self.enfoques_disponibles.keys())
                    
                    if 0 <= indice < len(claves):
                        clave_enfoque = claves[indice]
                        resultado = self.ejecutar_enfoque(clave_enfoque)
                        self.reportes_generados.append(resultado)
                        
                        if resultado.get("estado") == "exitoso":
                            print(f"\n✅ {self.enfoques_disponibles[clave_enfoque]['descripcion']} ejecutado exitosamente")
                        else:
                            print(f"\n❌ Error ejecutando {self.enfoques_disponibles[clave_enfoque]['descripcion']}")
                    else:
                        print("\n❌ Opción inválida")
                else:
                    print("\n❌ Opción inválida")
                
                input("\n⏸️ Presione Enter para continuar...")
                
            except KeyboardInterrupt:
                logger.info("\n👋 Interrumpido por usuario")
                break
            except Exception as e:
                logger.error(f"❌ Error en sistema interactivo: {e}")
                print(f"\n❌ Error: {e}")

def main():
    """Función principal"""
    print("🚀 SISTEMA MAESTRO DE VERIFICACIÓN - RAPICREDIT")
    print("=" * 60)
    
    sistema = SistemaMaestroVerificacion()
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("verificacion_sistema.py"):
        print("❌ Error: Ejecute este script desde el directorio backend/scripts/")
        print("📁 Archivos esperados:")
        for info in sistema.enfoques_disponibles.values():
            print(f"   - {info['archivo']}")
        return
    
    # Ejecutar sistema interactivo
    sistema.ejecutar_sistema_interactivo()

if __name__ == "__main__":
    main()
