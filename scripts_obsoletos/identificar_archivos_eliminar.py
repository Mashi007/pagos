"""
Lista de Archivos de Endpoints a Eliminar
Archivos de debug, prueba y temporales que deben eliminarse
"""
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def identificar_archivos_a_eliminar():
    """Identifica archivos de endpoints que deben eliminarse"""
    
    # Archivos claramente de debug/prueba
    archivos_debug = [
        "debug_auth.py",
        "debug_logging.py", 
        "debug_refresh_user.py",
        "log_test.py",
        "simple_debug.py",
        "test_auditoria.py",
        "test_auth.py"
    ]
    
    # Archivos de fix/temporal
    archivos_fix = [
        "fix_admin_definitive.py",
        "fix_database.py",
        "fix_refresh_user.py",
        "force_refresh_user.py"
    ]
    
    # Archivos de health/monitoreo redundantes
    archivos_health = [
        "health_check.py",
        "health.py"  # Mantener solo uno
    ]
    
    # Archivos que pueden ser innecesarios
    archivos_innecesarios = [
        "verificar_permisos.py",  # Funcionalidad ya en auth
        "setup_inicial.py",       # Solo para setup inicial
        "monitoreo_auditoria.py"  # Redundante con auditoria.py
    ]
    
    todos_a_eliminar = archivos_debug + archivos_fix + archivos_innecesarios
    
    # Mantener health.py, eliminar health_check.py
    todos_a_eliminar.remove("health.py")
    
    logger.info("🗑️ ARCHIVOS IDENTIFICADOS PARA ELIMINACIÓN:")
    logger.info("-" * 50)
    
    logger.info("🔧 Archivos de Debug/Prueba:")
    for archivo in archivos_debug:
        logger.info(f"   ❌ {archivo}")
    
    logger.info("🔧 Archivos de Fix/Temporal:")
    for archivo in archivos_fix:
        logger.info(f"   ❌ {archivo}")
    
    logger.info("🔧 Archivos Innecesarios:")
    for archivo in archivos_innecesarios:
        logger.info(f"   ❌ {archivo}")
    
    logger.info("🔧 Archivos de Health Redundantes:")
    logger.info(f"   ❌ health_check.py (mantener health.py)")
    
    logger.info("")
    logger.info(f"📊 TOTAL ARCHIVOS A ELIMINAR: {len(todos_a_eliminar)}")
    
    return todos_a_eliminar

def verificar_archivos_esenciales():
    """Verifica que los archivos esenciales se mantengan"""
    
    archivos_esenciales = [
        "auth.py",           # Autenticación
        "clientes.py",       # Gestión de clientes
        "usuarios.py",       # Gestión de usuarios
        "validadores.py",    # Validaciones
        "auditoria.py",      # Auditoría
        "health.py",         # Health check (uno solo)
        "dashboard.py",      # Dashboard
        "reportes.py",       # Reportes
        "configuracion.py",  # Configuración
        "notificaciones.py", # Notificaciones
        "pagos.py",          # Pagos
        "prestamos.py",      # Préstamos
        "amortizacion.py",   # Amortización
        "kpis.py"           # KPIs
    ]
    
    logger.info("✅ ARCHIVOS ESENCIALES A MANTENER:")
    logger.info("-" * 50)
    for archivo in archivos_esenciales:
        logger.info(f"   ✅ {archivo}")
    
    logger.info(f"📊 TOTAL ARCHIVOS ESENCIALES: {len(archivos_esenciales)}")
    
    return archivos_esenciales

def main():
    """Función principal"""
    logger.info("🚀 QUINTO ENFOQUE - IDENTIFICACIÓN DE ARCHIVOS A ELIMINAR")
    logger.info("=" * 60)
    
    archivos_a_eliminar = identificar_archivos_a_eliminar()
    archivos_esenciales = verificar_archivos_esenciales()
    
    logger.info("")
    logger.info("📊 RESUMEN:")
    logger.info(f"🗑️ Archivos a eliminar: {len(archivos_a_eliminar)}")
    logger.info(f"✅ Archivos esenciales: {len(archivos_esenciales)}")
    logger.info(f"📈 Reducción: {len(archivos_a_eliminar)} archivos")
    
    return {
        "archivos_a_eliminar": archivos_a_eliminar,
        "archivos_esenciales": archivos_esenciales,
        "total_eliminacion": len(archivos_a_eliminar)
    }

if __name__ == "__main__":
    main()
