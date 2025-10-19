#!/usr/bin/env python3
"""
Script para limpiar scripts obsoletos que usan el sistema de roles antiguo
"""
import os
import shutil
from pathlib import Path

def limpiar_scripts_obsoletos():
    """Eliminar scripts que usan el sistema de roles obsoleto"""
    
    scripts_dir = Path(__file__).parent
    
    # Scripts obsoletos que deben eliminarse
    scripts_obsoletos = [
        # Scripts de diagnóstico de roles
        "diagnostico_roles_simple.py",
        "diagnostico_roles_especifico.py", 
        "diagnostico_completo.py",
        
        # Scripts de creación de usuarios con roles
        "cambiar_rol_admin.py",
        "crear_usuario_admin_daniel.py",
        "crear_usuario_admin_daniel_simple.py",
        "create_admin.py",
        
        # Scripts de verificación de roles
        "verificar_rol_daniel.py",
        "verificar_usuarios.py",
        "verificar_usuarios_simple.py",
        "verificar_migracion_roles.sql",
        
        # Scripts de testing de roles
        "probar_permisos_roles.py",
        "probar_endpoints.py",
        "probar_endpoints_simple.py",
        "probar_endpoints_completo.py",
        "probar_endpoints_especificos.py",
        
        # Scripts de limpieza de roles legacy
        "limpiar_roles_legacy.py",
        "limpiar_roles_legacy_correcto.py",
        
        # Scripts de verificación de configuraciones con roles
        "verificar_configuraciones.py",
        "verificar_configuraciones_simple.py",
        
        # Scripts de estructura con roles
        "verificar_estructura_bd.py",
        "consultar_estructura_bd.py",
        
        # Scripts de creación de tablas con roles
        "crear_tabla_usuarios_completa.sql",
        "crear_usuario_admin_daniel.sql",
        
        # Scripts de inicio con roles
        "iniciar_y_probar.py",
        
        # Scripts de diagnóstico de BD con roles
        "diagnostico_bd.py",
        
        # Scripts de creación de clientes con roles
        "create_sample_clients.py",
        
        # Scripts de poblar datos con roles
        "poblar_datos_configuracion.py",
        
        # Scripts de verificación de concesionarios con roles
        "verificar_concesionarios.py",
        "verificar_concesionarios_simple.py",
        "verificar_estructura_concesionarios.sql",
        
        # Scripts de verificación de conexión con roles
        "verificar_conexion_frontend_backend.py",
        
        # Scripts de análisis con roles
        "analisis_estructura_tablas.sql",
        
        # Scripts de fix con roles
        "fix_concesionarios_table.sql",
        "fix_produccion_completo.sql",
        
        # Scripts de migración urgente (ya aplicada)
        "migracion_urgente.sql",
        
        # Scripts de auto migración (ya aplicada)
        "auto_migrate.py"
    ]
    
    print("🧹 LIMPIEZA DE SCRIPTS OBSOLETOS")
    print("=" * 50)
    
    eliminados = 0
    no_encontrados = 0
    
    for script in scripts_obsoletos:
        script_path = scripts_dir / script
        
        if script_path.exists():
            try:
                # Crear backup antes de eliminar
                backup_path = scripts_dir / f"{script}.backup"
                shutil.copy2(script_path, backup_path)
                
                # Eliminar script
                script_path.unlink()
                print(f"✅ Eliminado: {script}")
                eliminados += 1
                
            except Exception as e:
                print(f"❌ Error eliminando {script}: {e}")
        else:
            print(f"⚠️  No encontrado: {script}")
            no_encontrados += 1
    
    print("\n" + "=" * 50)
    print(f"📊 RESUMEN:")
    print(f"   ✅ Scripts eliminados: {eliminados}")
    print(f"   ⚠️  Scripts no encontrados: {no_encontrados}")
    print(f"   📁 Backups creados: {eliminados}")
    print("=" * 50)
    
    # Mostrar scripts que permanecen
    print("\n🟢 SCRIPTS VIGENTES QUE PERMANECEN:")
    scripts_vigentes = [
        "migrate_to_is_admin.py",
        "migrate_to_is_admin.sql", 
        "activar_auditoria_completa.py",
        "activar_auditoria_completa.sql",
        "insert_datos_configuracion.sql",
        "poblar_datos_configuracion.py",
        "monitor_despliegue.py",
        "monitor_despliegue_simple.py",
        "verificar_despliegue.py",
        "test_imports.py",
        "test_password_validation.py"
    ]
    
    for script in scripts_vigentes:
        script_path = scripts_dir / script
        if script_path.exists():
            print(f"   ✅ {script}")
        else:
            print(f"   ⚠️  {script} (no encontrado)")

if __name__ == "__main__":
    limpiar_scripts_obsoletos()
