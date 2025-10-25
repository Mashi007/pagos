#!/usr/bin/env python3
"""
Script para corregir errores de sintaxis introducidos por el formateo automático
"""

import os
import re

def fix_syntax_errors():
    """Corregir errores de sintaxis específicos"""
    
    fixes = [
        # Archivo: línea, patrón incorrecto, patrón correcto
        ("backend/app/api/v1/endpoints/conciliacion.py", 1251, 
         'roceso_id}",', 'proceso_id}",'),
        
        ("backend/app/api/v1/endpoints/predictive_token_analyzer.py", 277,
         'sponse_time:.2f}s",', 'response_time:.2f}s",'),
         
        ("backend/app/api/v1/endpoints/scheduler_notificaciones.py", 106,
         '6AM a 10PM, Lun-Sab', '6AM a 10PM, Lun-Sab'),
         
        ("backend/app/api/v1/endpoints/verificar_concesionarios.py", 29,
         'urrent_user.email}"', 'current_user.email}"'),
         
        ("backend/app/core/constants.py", 14,
         'con is_admin', 'con is_admin'),
         
        ("backend/app/core/config.py", 101,
         'if self.ADMIN_PASSWORD == "R@pi_2025**" and', 
         'if self.ADMIN_PASSWORD == "R@pi_2025**" and'),
         
        ("backend/app/db/init_db.py", 168,
         'conflictos con enum', 'conflictos con enum'),
         
        ("backend/app/models/aprobacion.py", 38,
         'ndex=True)', 'index=True)'),
         
        ("backend/app/models/conciliacion.py", 65,
         'de confianza', 'de confianza'),
         
        ("backend/app/models/pago.py", 37,
         'ullable=False)', 'nullable=False)'),
         
        ("backend/app/models/user.py", 25,
         'able=False)', 'nullable=False)'),
         
        ("backend/app/schemas/__init__.py", 112,
         '"EstadoConciliacion",', '"EstadoConciliacion",'),
         
        ("backend/app/models/prestamo.py", 71,
         'llable=False)', 'nullable=False)'),
         
        ("backend/app/utils/validators.py", 70,
         'empezar por 0)', 'empezar por 0)'),
         
        ("backend/app/api/v1/endpoints/solicitudes.py", 1583,
         'icitante.full_name}</td>', 'solicitante.full_name}</td>'),
    ]
    
    for file_path, line_num, old_pattern, new_pattern in fixes:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                if line_num <= len(lines):
                    line = lines[line_num - 1]
                    if old_pattern in line:
                        lines[line_num - 1] = line.replace(old_pattern, new_pattern)
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.writelines(lines)
                        
                        print(f"Corregido: {file_path}:{line_num}")
        except Exception as e:
            print(f"Error corrigiendo {file_path}:{line_num}: {e}")

def fix_continuation_lines():
    """Corregir líneas de continuación mal formateadas"""
    
    files_to_fix = [
        "backend/app/api/v1/endpoints/scheduler_notificaciones.py",
        "backend/app/core/constants.py", 
        "backend/app/core/config.py",
        "backend/app/db/init_db.py",
        "backend/app/models/aprobacion.py",
        "backend/app/models/conciliacion.py",
        "backend/app/models/pago.py",
        "backend/app/models/user.py",
        "backend/app/schemas/__init__.py",
        "backend/app/models/prestamo.py",
        "backend/app/utils/validators.py",
        "backend/app/api/v1/endpoints/solicitudes.py"
    ]
    
    for file_path in files_to_fix:
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Corregir líneas de continuación mal formateadas
                # Buscar patrones como "palabra \n palabra" y unirlos
                content = re.sub(r'(\w+)\s*\\\s*\n\s*(\w+)', r'\1\2', content)
                
                # Corregir strings rotos
                content = re.sub(r'(\w+)\s*\\\s*\n\s*"([^"]*)"', r'\1"\2"', content)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"Corregido formato en: {file_path}")
                
        except Exception as e:
            print(f"Error corrigiendo formato en {file_path}: {e}")

if __name__ == "__main__":
    print("Corrigiendo errores de sintaxis...")
    fix_syntax_errors()
    fix_continuation_lines()
    print("Corrección completada.")
