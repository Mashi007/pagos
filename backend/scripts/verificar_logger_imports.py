#!/usr/bin/env python3
"""
Script para identificar archivos que usan logger pero no importan logging
"""

import os
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verificar_archivo_logger(file_path):
    """Verificar si un archivo usa logger pero no importa logging"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Buscar uso de logger
        usa_logger = bool(re.search(r'\blogger\.', content))
        
        # Buscar import logging
        importa_logging = bool(re.search(r'^import logging', content, re.MULTILINE)) or \
                         bool(re.search(r'^from logging import', content, re.MULTILINE))
        
        if usa_logger and not importa_logging:
            return True, "USA LOGGER SIN IMPORTAR LOGGING"
        elif usa_logger and importa_logging:
            return False, "OK - Logger correctamente importado"
        else:
            return False, "No usa logger"
            
    except Exception as e:
        return False, f"Error leyendo archivo: {e}"

def main():
    logger.info("🔍 VERIFICANDO ARCHIVOS CON PROBLEMAS DE LOGGER")
    logger.info("=" * 60)
    
    backend_path = "backend/app"
    archivos_problematicos = []
    
    # Recorrer todos los archivos Python
    for root, dirs, files in os.walk(backend_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                es_problematico, mensaje = verificar_archivo_logger(file_path)
                
                if es_problematico:
                    archivos_problematicos.append((file_path, mensaje))
                    logger.error(f"❌ {file_path}: {mensaje}")
                elif "USA LOGGER" in mensaje:
                    logger.info(f"✅ {file_path}: {mensaje}")
    
    logger.info("")
    logger.info("📊 RESUMEN")
    logger.info("=" * 60)
    logger.info(f"🔍 Archivos verificados: {len(archivos_problematicos) + len([f for f in os.walk(backend_path)])}")
    logger.info(f"❌ Archivos problemáticos: {len(archivos_problematicos)}")
    
    if archivos_problematicos:
        logger.info("")
        logger.info("🔧 ARCHIVOS QUE NECESITAN CORRECCIÓN:")
        logger.info("-" * 40)
        for file_path, mensaje in archivos_problematicos:
            logger.info(f"   📄 {file_path}")
            logger.info(f"      💡 {mensaje}")
    else:
        logger.info("✅ TODOS LOS ARCHIVOS ESTÁN CORRECTOS")

if __name__ == "__main__":
    main()
