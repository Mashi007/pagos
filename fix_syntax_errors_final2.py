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
        ("backend/app/api/v1/endpoints/amortizacion.py", 308,
         'de pagos', 'de pagos'),
         
        ("backend/app/api/v1/endpoints/analistas.py", 489,
         'propiedad calculada', 'propiedad calculada'),
         
        ("backend/app/api/v1/endpoints/migracion_emergencia.py", 26,
         'ser.email}"', 'user.email}"'),
         
        ("backend/app/api/v1/endpoints/modelos_vehiculos.py", 248,
         'delo.id})"', 'modelo.id})"'),
         
        ("backend/app/api/v1/endpoints/kpis.py", 266,
         '_modalidad', 'modalidad'),
         
        ("backend/app/api/v1/endpoints/predictive_analyzer.py", 116,
         'uccess_trend[\'slope\']:.3f})",', 'success_trend[\'slope\']:.3f})",'),
         
        ("backend/app/api/v1/endpoints/scheduler_notificaciones.py", 106,
         'a 10PM, Lun-Sab', 'a 10PM, Lun-Sab'),
         
        ("backend/app/api/v1/endpoints/predictive_token_analyzer.py", 277,
         'sponse_time:.2f}s",', 'response_time:.2f}s",'),
         
        ("backend/app/api/v1/endpoints/verificar_concesionarios.py", 29,
         't_user.email}"', 'current_user.email}"'),
         
        ("backend/app/api/v1/endpoints/dashboard.py", 851,
         'f"Contactar {len([c for c in clientes_mora_detalle" + \\', 
         'f"Contactar {len([c for c in clientes_mora_detalle])}"'),
         
        ("backend/app/core/security.py", 114,
         'en app/api/deps.py', 'en app/api/deps.py'),
         
        ("backend/app/models/cliente.py", 85,
         'plantillas vacías', 'plantillas vacías'),
         
        ("backend/app/db/init_db.py", 112,
         'ng_admin.email}"', 'admin_user.email}"'),
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
        "backend/app/api/v1/endpoints/amortizacion.py",
        "backend/app/api/v1/endpoints/analistas.py",
        "backend/app/api/v1/endpoints/migracion_emergencia.py",
        "backend/app/api/v1/endpoints/modelos_vehiculos.py",
        "backend/app/api/v1/endpoints/kpis.py",
        "backend/app/api/v1/endpoints/predictive_analyzer.py",
        "backend/app/api/v1/endpoints/scheduler_notificaciones.py",
        "backend/app/api/v1/endpoints/predictive_token_analyzer.py",
        "backend/app/api/v1/endpoints/verificar_concesionarios.py",
        "backend/app/api/v1/endpoints/dashboard.py",
        "backend/app/core/security.py",
        "backend/app/models/cliente.py",
        "backend/app/db/init_db.py"
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
                
                # Corregir f-strings rotos
                content = re.sub(r'f"([^"]*)\s*\\\s*\n\s*([^"]*)"', r'f"\1\2"', content)
                
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
