# backend/scripts/auditoria_cuarta_completa.py
"""
AUDITORÍA CUARTA COMPLETA - VERIFICACIÓN DE CAUSA RAÍZ
Ejecutar todas las auditorías para confirmar la causa exacta del problema
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
    Ejecutar auditoría completa con todos los scripts
    """
    logger.info("🔍 AUDITORÍA CUARTA COMPLETA - VERIFICACIÓN DE CAUSA RAÍZ")
    logger.info("=" * 100)
    logger.info(f"📅 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Confirmar la causa exacta del problema 'Rol: USER'")
    logger.info("=" * 100)
    
    # Lista de scripts a ejecutar en orden
    scripts = [
        {
            "nombre": "Verificación de Usuario Exacto",
            "archivo": "verificar_usuario_exacto.py",
            "descripcion": "Verificar datos exactos del usuario en base de datos"
        },
        {
            "nombre": "Simulación de Login Completo",
            "archivo": "simular_login_completo.py",
            "descripcion": "Simular login y capturar respuesta exacta"
        },
        {
            "nombre": "Verificación de Flujo Frontend",
            "archivo": "verificar_flujo_frontend.py",
            "descripcion": "Verificar flujo completo frontend"
        },
        {
            "nombre": "Comparación Almacenado vs Mostrado",
            "archivo": "comparar_almacenado_vs_mostrado.py",
            "descripcion": "Comparar datos almacenados vs mostrados"
        },
        {
            "nombre": "Verificación de Timing y Caché",
            "archivo": "verificar_timing_cache.py",
            "descripcion": "Verificar timing y problemas de caché"
        }
    ]
    
    resultados = []
    
    # Ejecutar cada script
    for i, script in enumerate(scripts, 1):
        logger.info(f"\n🔍 EJECUTANDO AUDITORÍA {i}/5: {script['nombre']}")
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
    logger.info("\n📊 REPORTE CONSOLIDADO DE AUDITORÍA CUARTA")
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
        if "DIAGNÓSTICO:" in stdout:
            # Extraer diagnóstico
            lines = stdout.split('\n')
            for line in lines:
                if "DIAGNÓSTICO:" in line:
                    hallazgos.append({
                        "script": resultado['script'],
                        "hallazgo": line.strip()
                    })
                elif "CAUSA CONFIRMADA:" in line:
                    hallazgos.append({
                        "script": resultado['script'],
                        "hallazgo": line.strip()
                    })
                elif "SOLUCIÓN:" in line:
                    hallazgos.append({
                        "script": resultado['script'],
                        "hallazgo": line.strip()
                    })
    
    # Mostrar hallazgos
    for hallazgo in hallazgos:
        logger.info(f"   📊 {hallazgo['script']}: {hallazgo['hallazgo']}")
    
    # Generar conclusión final
    logger.info(f"\n🎯 CONCLUSIÓN FINAL DE AUDITORÍA CUARTA")
    logger.info("=" * 100)
    
    if len(exitosos) >= 3:  # Al menos 3 scripts exitosos
        logger.info("✅ AUDITORÍA COMPLETA: Suficientes datos para análisis")
        
        # Contar diagnósticos
        diagnosticos_backend = sum(1 for h in hallazgos if "Backend retorna datos correctos" in h['hallazgo'])
        diagnosticos_frontend = sum(1 for h in hallazgos if "Problema en frontend" in h['hallazgo'])
        diagnosticos_bd = sum(1 for h in hallazgos if "Problema en backend/BD" in h['hallazgo'])
        
        logger.info(f"📊 DIAGNÓSTICOS ENCONTRADOS:")
        logger.info(f"   🔧 Backend correcto: {diagnosticos_backend}")
        logger.info(f"   🌐 Frontend problemático: {diagnosticos_frontend}")
        logger.info(f"   🗄️ Base de datos problemática: {diagnosticos_bd}")
        
        if diagnosticos_backend > diagnosticos_frontend and diagnosticos_backend > diagnosticos_bd:
            logger.info("🎯 CAUSA RAÍZ CONFIRMADA: Backend funciona correctamente")
            logger.info("💡 SOLUCIÓN PRINCIPAL: Corregir frontend y caché")
        elif diagnosticos_frontend > diagnosticos_backend and diagnosticos_frontend > diagnosticos_bd:
            logger.info("🎯 CAUSA RAÍZ CONFIRMADA: Problema en frontend")
            logger.info("💡 SOLUCIÓN PRINCIPAL: Verificar y corregir frontend")
        elif diagnosticos_bd > diagnosticos_backend and diagnosticos_bd > diagnosticos_frontend:
            logger.info("🎯 CAUSA RAÍZ CONFIRMADA: Problema en base de datos")
            logger.info("💡 SOLUCIÓN PRINCIPAL: Corregir datos en BD")
        else:
            logger.warning("⚠️ DIAGNÓSTICO INCONCLUSIVO: Múltiples causas posibles")
            logger.info("💡 SOLUCIÓN: Implementar correcciones en múltiples áreas")
    
    else:
        logger.error("❌ AUDITORÍA INCOMPLETA: Insuficientes datos para análisis")
        logger.info("💡 SOLUCIÓN: Revisar y corregir scripts fallidos")
    
    # Recomendaciones finales
    logger.info(f"\n💡 RECOMENDACIONES FINALES:")
    logger.info("   1. Implementar las correcciones basadas en hallazgos")
    logger.info("   2. Probar la solución en ambiente de desarrollo")
    logger.info("   3. Desplegar a producción con monitoreo")
    logger.info("   4. Verificar que el problema esté resuelto")
    logger.info("   5. Documentar la solución para futuras referencias")
    
    # Guardar reporte en archivo
    reporte_archivo = f"auditoria_cuarta_reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        with open(reporte_archivo, 'w', encoding='utf-8') as f:
            f.write("AUDITORÍA CUARTA COMPLETA - REPORTE FINAL\n")
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
    ejecutar_auditoria_completa()
