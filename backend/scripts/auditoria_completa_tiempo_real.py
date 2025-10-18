# backend/scripts/auditoria_completa_tiempo_real.py
"""
AUDITORÍA COMPLETA EN TIEMPO REAL - TERCERA AUDITORÍA
Script maestro que ejecuta todos los diagnósticos para confirmar la causa raíz
"""
import os
import sys
import logging
import subprocess
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ejecutar_auditoria_completa():
    """
    Ejecutar auditoría completa en tiempo real
    """
    logger.info("🚀 INICIANDO AUDITORÍA COMPLETA EN TIEMPO REAL")
    logger.info("=" * 80)
    logger.info(f"📅 Fecha y hora: {datetime.now()}")
    logger.info(f"🎯 Objetivo: Confirmar causa raíz del problema 'Rol: USER'")
    logger.info("=" * 80)
    
    scripts = [
        {
            'nombre': 'Diagnóstico de Base de Datos',
            'archivo': 'diagnostico_tiempo_real.py',
            'descripcion': 'Verificar datos reales en base de datos de producción'
        },
        {
            'nombre': 'Verificación de Logs',
            'archivo': 'verificar_logs_tiempo_real.py',
            'descripcion': 'Analizar logs de producción en tiempo real'
        },
        {
            'nombre': 'Prueba de Endpoints',
            'archivo': 'probar_endpoints_tiempo_real.py',
            'descripcion': 'Probar endpoints específicos con datos reales'
        },
        {
            'nombre': 'Verificación de Respuesta /me',
            'archivo': 'verificar_respuesta_me.py',
            'descripcion': 'Verificar respuesta exacta del endpoint /me'
        },
        {
            'nombre': 'Comparación Frontend vs Backend',
            'archivo': 'comparar_frontend_backend.py',
            'descripcion': 'Comparar datos frontend vs backend en tiempo real'
        }
    ]
    
    resultados = []
    
    for i, script in enumerate(scripts, 1):
        logger.info(f"\n🔍 {i}. {script['nombre']}")
        logger.info("-" * 60)
        logger.info(f"📋 Descripción: {script['descripcion']}")
        logger.info(f"📁 Archivo: {script['archivo']}")
        
        try:
            # Ejecutar script
            script_path = os.path.join(os.path.dirname(__file__), script['archivo'])
            
            if os.path.exists(script_path):
                logger.info(f"▶️ Ejecutando {script['archivo']}...")
                
                result = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    logger.info(f"✅ {script['nombre']} completado exitosamente")
                    resultados.append({
                        'script': script['nombre'],
                        'estado': 'EXITOSO',
                        'output': result.stdout
                    })
                else:
                    logger.error(f"❌ {script['nombre']} falló")
                    logger.error(f"   Error: {result.stderr}")
                    resultados.append({
                        'script': script['nombre'],
                        'estado': 'FALLÓ',
                        'error': result.stderr
                    })
            else:
                logger.error(f"❌ Archivo no encontrado: {script_path}")
                resultados.append({
                    'script': script['nombre'],
                    'estado': 'ARCHIVO_NO_ENCONTRADO',
                    'error': f"Archivo {script['archivo']} no existe"
                })
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ {script['nombre']} excedió el tiempo límite")
            resultados.append({
                'script': script['nombre'],
                'estado': 'TIMEOUT',
                'error': 'Tiempo límite excedido'
            })
        except Exception as e:
            logger.error(f"❌ Error ejecutando {script['nombre']}: {e}")
            resultados.append({
                'script': script['nombre'],
                'estado': 'ERROR',
                'error': str(e)
            })
    
    # RESUMEN FINAL
    logger.info("\n📊 RESUMEN FINAL DE AUDITORÍA COMPLETA")
    logger.info("=" * 80)
    
    exitosos = len([r for r in resultados if r['estado'] == 'EXITOSO'])
    fallidos = len([r for r in resultados if r['estado'] != 'EXITOSO'])
    
    logger.info(f"✅ Scripts exitosos: {exitosos}/{len(scripts)}")
    logger.info(f"❌ Scripts fallidos: {fallidos}/{len(scripts)}")
    
    logger.info("\n📋 Detalle de resultados:")
    for resultado in resultados:
        estado_emoji = "✅" if resultado['estado'] == 'EXITOSO' else "❌"
        logger.info(f"   {estado_emoji} {resultado['script']}: {resultado['estado']}")
    
    # CONCLUSIONES
    logger.info("\n🎯 CONCLUSIONES Y RECOMENDACIONES")
    logger.info("=" * 80)
    
    if exitosos == len(scripts):
        logger.info("✅ Todos los diagnósticos se ejecutaron exitosamente")
        logger.info("💡 Revisar los logs individuales para identificar la causa raíz")
    else:
        logger.warning(f"⚠️ {fallidos} diagnósticos fallaron")
        logger.warning("💡 Revisar errores y ejecutar diagnósticos individuales")
    
    logger.info("\n🔍 PRÓXIMOS PASOS RECOMENDADOS:")
    logger.info("   1. Revisar logs detallados de cada script")
    logger.info("   2. Identificar discrepancias entre frontend y backend")
    logger.info("   3. Verificar datos en base de datos de producción")
    logger.info("   4. Confirmar respuesta exacta del endpoint /me")
    logger.info("   5. Implementar solución basada en hallazgos")
    
    logger.info(f"\n🏁 Auditoría completada: {datetime.now()}")
    logger.info("=" * 80)
    
    return resultados

if __name__ == "__main__":
    ejecutar_auditoria_completa()
