# backend/scripts/auditoria_sexta_completa.py
"""
AUDITORÍA SEXTA COMPLETA - CONFIRMACIÓN DE CORRECCIÓN
Ejecutar todas las auditorías para confirmar que la corrección funciona
"""
import os
import sys
import logging
import subprocess
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ejecutar_auditoria_sexta_completa():
    """
    Ejecutar auditoría sexta completa con todos los scripts
    """
    logger.info("✅ AUDITORÍA SEXTA COMPLETA - CONFIRMACIÓN DE CORRECCIÓN")
    logger.info("=" * 100)
    logger.info(f"📅 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Confirmar que la corrección del problema 'Rol: USER' funciona")
    logger.info("=" * 100)
    
    # Lista de scripts a ejecutar en orden
    scripts = [
        {
            "nombre": "Verificación de Consistencia entre Endpoints",
            "archivo": "verificar_consistencia_endpoints.py",
            "descripcion": "Verificar que /login y /me retornan datos consistentes"
        },
        {
            "nombre": "Prueba de Flujo Completo",
            "archivo": "probar_flujo_completo.py",
            "descripcion": "Probar flujo completo desde login hasta header"
        },
        {
            "nombre": "Verificación de Datos en Tiempo Real",
            "archivo": "verificar_datos_tiempo_real.py",
            "descripcion": "Verificar datos en tiempo real en producción"
        },
        {
            "nombre": "Confirmación de Problema Resuelto",
            "archivo": "confirmar_problema_resuelto.py",
            "descripcion": "Confirmar definitivamente que el problema está resuelto"
        }
    ]
    
    resultados = []
    
    # Ejecutar cada script
    for i, script in enumerate(scripts, 1):
        logger.info(f"\n✅ EJECUTANDO AUDITORÍA {i}/4: {script['nombre']}")
        logger.info("=" * 80)
        logger.info(f"📝 Descripción: {script['descripcion']}")
        logger.info(f"📁 Archivo: {script['archivo']}")
        logger.info("-" * 80)
        
        try:
            # Ejecutar el script
            resultado = subprocess.run(
                [sys.executable, script['archivo']],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos timeout
            )
            
            # Guardar resultado
            resultados.append({
                "script": script['nombre'],
                "archivo": script['archivo'],
                "exit_code": resultado.returncode,
                "stdout": resultado.stdout,
                "stderr": resultado.stderr,
                "success": resultado.returncode == 0
            })
            
            if resultado.returncode == 0:
                logger.info(f"✅ {script['nombre']} ejecutado exitosamente")
                logger.info(f"📊 Salida: {len(resultado.stdout)} caracteres")
                if resultado.stderr:
                    logger.warning(f"⚠️ Advertencias: {len(resultado.stderr)} caracteres")
            else:
                logger.error(f"❌ {script['nombre']} falló con código {resultado.returncode}")
                logger.error(f"📊 Error: {resultado.stderr}")
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ {script['nombre']} excedió el tiempo límite")
            resultados.append({
                "script": script['nombre'],
                "archivo": script['archivo'],
                "exit_code": -1,
                "stdout": "",
                "stderr": "Timeout",
                "success": False
            })
        except Exception as e:
            logger.error(f"❌ Error ejecutando {script['nombre']}: {e}")
            resultados.append({
                "script": script['nombre'],
                "archivo": script['archivo'],
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False
            })
    
    # Generar reporte consolidado
    logger.info("\n📊 REPORTE CONSOLIDADO DE AUDITORÍA SEXTA")
    logger.info("=" * 100)
    
    exitosos = [r for r in resultados if r['success']]
    fallidos = [r for r in resultados if not r['success']]
    
    logger.info(f"📈 RESUMEN EJECUTIVO:")
    logger.info(f"   ✅ Scripts exitosos: {len(exitosos)}/{len(scripts)}")
    logger.info(f"   ❌ Scripts fallidos: {len(fallidos)}/{len(scripts)}")
    logger.info(f"   📊 Tasa de éxito: {len(exitosos)/len(scripts)*100:.1f}%")
    
    # Mostrar resultados por script
    logger.info(f"\n📋 RESULTADOS POR SCRIPT:")
    for resultado in resultados:
        status = "✅" if resultado['success'] else "❌"
        logger.info(f"   {status} {resultado['script']}: {resultado['exit_code']}")
    
    # Extraer hallazgos clave de cada script exitoso
    logger.info(f"\n🔍 HALLAZGOS CLAVE:")
    
    hallazgos = []
    
    for resultado in exitosos:
        stdout = resultado['stdout']
        
        # Buscar patrones clave en la salida
        lines = stdout.split('\n')
        for line in lines:
            if "CORRECCIÓN CONFIRMADA" in line:
                hallazgos.append({
                    "script": resultado['script'],
                    "hallazgo": line.strip()
                })
            elif "PROBLEMA RESUELTO" in line:
                hallazgos.append({
                    "script": resultado['script'],
                    "hallazgo": line.strip()
                })
            elif "CONSISTENCIA PERFECTA" in line:
                hallazgos.append({
                    "script": resultado['script'],
                    "hallazgo": line.strip()
                })
            elif "FLUJO COMPLETO EXITOSO" in line:
                hallazgos.append({
                    "script": resultado['script'],
                    "hallazgo": line.strip()
                })
    
    # Mostrar hallazgos
    for hallazgo in hallazgos:
        logger.info(f"   📊 {hallazgo['script']}: {hallazgo['hallazgo']}")
    
    # Generar conclusión final
    logger.info(f"\n🎯 CONCLUSIÓN FINAL DE AUDITORÍA SEXTA")
    logger.info("=" * 100)
    
    if len(exitosos) >= 3:  # Al menos 3 scripts exitosos
        logger.info("✅ AUDITORÍA COMPLETA: Suficientes datos para confirmación")
        
        # Contar confirmaciones de corrección
        correcciones_confirmadas = sum(1 for h in hallazgos if "CORRECCIÓN CONFIRMADA" in h['hallazgo'])
        problemas_resueltos = sum(1 for h in hallazgos if "PROBLEMA RESUELTO" in h['hallazgo'])
        consistencias_perfectas = sum(1 for h in hallazgos if "CONSISTENCIA PERFECTA" in h['hallazgo'])
        
        logger.info(f"📊 CONFIRMACIONES ENCONTRADAS:")
        logger.info(f"   ✅ Correcciones confirmadas: {correcciones_confirmadas}")
        logger.info(f"   🎯 Problemas resueltos: {problemas_resueltos}")
        logger.info(f"   🔄 Consistencias perfectas: {consistencias_perfectas}")
        
        if correcciones_confirmadas >= 2 and problemas_resueltos >= 1:
            logger.info("🎯 CORRECCIÓN CONFIRMADA: El problema está resuelto")
            logger.info("💡 RESULTADO: La corrección del endpoint /login funcionó correctamente")
            logger.info("🚀 PRÓXIMO PASO: El usuario puede probar la aplicación")
        elif correcciones_confirmadas >= 1:
            logger.info("⚠️ CORRECCIÓN PARCIAL: Algunos aspectos funcionan")
            logger.info("💡 RESULTADO: La corrección tiene éxito parcial")
            logger.info("🔧 PRÓXIMO PASO: Revisar aspectos que aún fallan")
        else:
            logger.error("❌ CORRECCIÓN NO CONFIRMADA: El problema persiste")
            logger.error("💡 RESULTADO: La corrección no funcionó como esperado")
            logger.error("🔧 PRÓXIMO PASO: Revisar y aplicar correcciones adicionales")
    
    else:
        logger.error("❌ AUDITORÍA INCOMPLETA: Insuficientes datos para confirmación")
        logger.info("💡 SOLUCIÓN: Revisar y corregir scripts fallidos")
    
    # Recomendaciones finales
    logger.info(f"\n💡 RECOMENDACIONES FINALES:")
    logger.info("   1. Si la corrección está confirmada, probar la aplicación")
    logger.info("   2. Verificar que el header muestra 'Administrador'")
    logger.info("   3. Confirmar acceso a páginas admin")
    logger.info("   4. Monitorear que el problema no regrese")
    logger.info("   5. Documentar la solución para futuras referencias")
    
    # Guardar reporte en archivo
    reporte_archivo = f"auditoria_sexta_reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        with open(reporte_archivo, 'w', encoding='utf-8') as f:
            f.write("AUDITORÍA SEXTA COMPLETA - REPORTE FINAL\n")
            f.write("=" * 50 + "\n")
            f.write(f"Fecha: {datetime.now()}\n")
            f.write(f"Scripts ejecutados: {len(scripts)}\n")
            f.write(f"Scripts exitosos: {len(exitosos)}\n")
            f.write(f"Scripts fallidos: {len(fallidos)}\n")
            f.write("\nHALLAZGOS:\n")
            for hallazgo in hallazgos:
                f.write(f"- {hallazgo['script']}: {hallazgo['hallazgo']}\n")
        
        logger.info(f"📄 Reporte guardado en: {reporte_archivo}")
    except Exception as e:
        logger.error(f"❌ Error guardando reporte: {e}")
    
    return len(exitosos) >= 3

if __name__ == "__main__":
    ejecutar_auditoria_sexta_completa()
