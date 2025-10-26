#!/usr/bin/env python3
"""
Script para corregir errores críticos de flake8 que están causando fallos en el backend.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

def run_command(command, cwd=None):
    """Ejecuta un comando y retorna el resultado."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            encoding="utf-8",
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def fix_unused_imports():
    """Elimina imports no utilizados."""
    print("Eliminando imports no utilizados...")
    
    # Lista de archivos con imports no utilizados
    files_with_unused_imports = [
        "app/api/v1/endpoints/architectural_analysis.py",
        "app/api/v1/endpoints/auditoria.py", 
        "app/api/v1/endpoints/carga_masiva.py",
        "app/api/v1/endpoints/comparative_analysis.py",
        "app/api/v1/endpoints/conciliacion_bancaria.py",
        "app/api/v1/endpoints/critical_error_monitor.py",
        "app/api/v1/endpoints/cross_validation_auth.py",
        "app/api/v1/endpoints/dashboard.py",
        "app/api/v1/endpoints/dashboard_diagnostico.py",
        "app/api/v1/endpoints/diagnostico.py",
        "app/api/v1/endpoints/diagnostico_auth.py",
        "app/api/v1/endpoints/diagnostico_refresh_token.py",
        "app/api/v1/endpoints/forensic_analysis.py",
        "app/api/v1/endpoints/health.py",
        "app/api/v1/endpoints/kpis.py",
        "app/api/v1/endpoints/modelos_vehiculos.py",
        "app/api/v1/endpoints/pagos.py",
        "app/api/v1/endpoints/predictive_analyzer.py",
        "app/api/v1/endpoints/predictive_token_analyzer.py",
        "app/api/v1/endpoints/prestamos.py",
        "app/api/v1/endpoints/real_time_monitor.py",
        "app/api/v1/endpoints/realtime_specific_monitor.py",
        "app/api/v1/endpoints/reportes.py",
        "app/api/v1/endpoints/strategic_measurements.py",
        "app/api/v1/endpoints/temporal_analysis.py",
        "app/api/v1/endpoints/token_verification.py",
        "app/api/v1/endpoints/users.py",
        "app/api/v1/endpoints/verificar_concesionarios.py",
        "app/models/auditoria.py",
        "app/services/ml_service.py",
    ]
    
    # Mapeo de imports específicos a eliminar por archivo
    imports_to_remove = {
        "app/api/v1/endpoints/architectural_analysis.py": ["typing.Any", "typing.Dict", "typing.List"],
        "app/api/v1/endpoints/auditoria.py": ["datetime.datetime", "typing.List"],
        "app/api/v1/endpoints/carga_masiva.py": ["typing.Any", "typing.List", "fastapi.Form", "app.models.auditoria.Auditoria", "app.models.auditoria.TipoAccion"],
        "app/api/v1/endpoints/comparative_analysis.py": ["typing.List"],
        "app/api/v1/endpoints/conciliacion_bancaria.py": ["app.schemas.conciliacion.ConciliacionCreate"],
        "app/api/v1/endpoints/critical_error_monitor.py": ["typing.Any", "typing.Dict", "typing.List"],
        "app/api/v1/endpoints/cross_validation_auth.py": ["fastapi.HTTPException"],
        "app/api/v1/endpoints/dashboard.py": ["typing.Any", "typing.Dict", "typing.List", "sqlalchemy.and_", "sqlalchemy.or_"],
        "app/api/v1/endpoints/dashboard_diagnostico.py": ["fastapi.HTTPException"],
        "app/api/v1/endpoints/diagnostico.py": ["typing.List"],
        "app/api/v1/endpoints/diagnostico_auth.py": ["fastapi.HTTPException"],
        "app/api/v1/endpoints/diagnostico_refresh_token.py": ["fastapi.HTTPException"],
        "app/api/v1/endpoints/forensic_analysis.py": ["typing.Any", "typing.Dict", "typing.List"],
        "app/api/v1/endpoints/health.py": ["fastapi.Depends"],
        "app/api/v1/endpoints/kpis.py": ["sqlalchemy.case", "sqlalchemy.or_"],
        "app/api/v1/endpoints/modelos_vehiculos.py": ["typing.List"],
        "app/api/v1/endpoints/pagos.py": ["sqlalchemy.and_", "sqlalchemy.desc", "sqlalchemy.func"],
        "app/api/v1/endpoints/predictive_analyzer.py": ["typing.List", "typing.Optional", "typing.Tuple", "fastapi.Request", "fastapi.status", "app.api.deps.get_db"],
        "app/api/v1/endpoints/predictive_token_analyzer.py": ["typing.Any", "typing.Dict", "typing.List"],
        "app/api/v1/endpoints/prestamos.py": ["typing.Optional"],
        "app/api/v1/endpoints/real_time_monitor.py": ["fastapi.HTTPException"],
        "app/api/v1/endpoints/realtime_specific_monitor.py": ["fastapi.HTTPException"],
        "app/api/v1/endpoints/reportes.py": ["openpyxl.styles.Font", "openpyxl.styles.PatternFill", "reportlab.lib.pagesizes.letter"],
        "app/api/v1/endpoints/strategic_measurements.py": ["typing.Any", "typing.Dict", "typing.List"],
        "app/api/v1/endpoints/temporal_analysis.py": ["typing.Any", "typing.Dict", "typing.List"],
        "app/api/v1/endpoints/token_verification.py": ["datetime.timedelta", "fastapi.status"],
        "app/api/v1/endpoints/users.py": ["typing.List", "typing.Optional"],
        "app/api/v1/endpoints/verificar_concesionarios.py": ["fastapi.HTTPException"],
        "app/models/auditoria.py": ["typing.Any", "typing.Dict"],
        "app/services/ml_service.py": ["typing.Optional"],
    }
    
    for file_path in files_with_unused_imports:
        if os.path.exists(file_path):
            print(f"  Procesando {file_path}...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Eliminar imports específicos
            if file_path in imports_to_remove:
                for import_to_remove in imports_to_remove[file_path]:
                    # Patrones para eliminar imports
                    patterns = [
                        f"from {import_to_remove} import",
                        f"import {import_to_remove}",
                        f", {import_to_remove}",
                        f"{import_to_remove}, ",
                    ]
                    
                    for pattern in patterns:
                        content = re.sub(pattern, "", content)
            
            # Limpiar líneas vacías múltiples
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"    OK - Imports eliminados")
            else:
                print(f"    Sin cambios necesarios")

def fix_trailing_whitespace():
    """Elimina espacios en blanco al final de las líneas."""
    print("Eliminando espacios en blanco al final...")
    
    files_with_whitespace = [
        "app/api/v1/endpoints/schema_analyzer.py",
        "app/schemas/__init__.py", 
        "app/services/whatsapp_service.py",
    ]
    
    for file_path in files_with_whitespace:
        if os.path.exists(file_path):
            print(f"  Procesando {file_path}...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Eliminar espacios en blanco al final de cada línea
            cleaned_lines = [line.rstrip() + '\n' for line in lines]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(cleaned_lines)
            
            print(f"    OK - Espacios en blanco eliminados")

def fix_line_length():
    """Corrige líneas demasiado largas usando Black."""
    print("Corrigiendo líneas demasiado largas...")
    
    files_with_long_lines = [
        "app/api/v1/endpoints/inteligencia_artificial.py",
        "app/api/v1/endpoints/notificaciones_multicanal.py", 
        "app/api/v1/endpoints/validadores.py",
        "app/services/notification_multicanal_service.py",
    ]
    
    for file_path in files_with_long_lines:
        if os.path.exists(file_path):
            print(f"  Reformateando {file_path}...")
            success, output = run_command(f"py -m black {file_path}")
            if success:
                print(f"    OK - Reformateado exitosamente")
            else:
                print(f"    ERROR: {output}")

def main():
    """Función principal."""
    print("Iniciando corrección de errores críticos...")
    
    # Cambiar al directorio backend
    os.chdir("backend")
    
    # Aplicar correcciones
    fix_unused_imports()
    fix_trailing_whitespace() 
    fix_line_length()
    
    # Aplicar Black a todo el directorio app
    print("Aplicando Black a todo el directorio...")
    success, output = run_command("py -m black app/")
    if success:
        print("OK - Black aplicado exitosamente")
    else:
        print(f"ERROR con Black: {output}")
    
    # Aplicar isort
    print("Aplicando isort...")
    success, output = run_command("py -m isort app/")
    if success:
        print("OK - isort aplicado exitosamente")
    else:
        print(f"ERROR con isort: {output}")
    
    print("Corrección de errores críticos completada!")

if __name__ == "__main__":
    main()