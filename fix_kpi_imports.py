#!/usr/bin/env python3
"""
Script para corregir las importaciones de KPIs en __init__.py
"""

def corregir_imports_kpi():
    """Corrige las importaciones de KPIs en schemas/__init__.py"""
    
    init_file = "app/schemas/__init__.py"
    
    # Leer el archivo
    with open(init_file, 'r') as f:
        content = f.read()
    
    # Reemplazos necesarios basados en lo que realmente existe
    replacements = [
        # KPIDashboard -> DashboardKPIs (el nombre correcto)
        ('KPIDashboard', 'DashboardKPIs'),
        
        # Si KPIListResponse está siendo importado, lo comentamos
        # porque no existe en kpis.py
        ('KPIListResponse,', '# KPIListResponse,  # No existe, comentado'),
        ('KPIListResponse', '# KPIListResponse  # No existe, comentado'),
    ]
    
    # Aplicar los reemplazos
    for old, new in replacements:
        content = content.replace(old, new)
    
    # Escribir el archivo corregido
    with open(init_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Archivo {init_file} corregido")
    
    # También verificar si hay otros archivos que usen estos nombres incorrectos
    import os
    import glob
    
    # Buscar en endpoints
    endpoint_files = glob.glob("app/api/v1/endpoints/*.py")
    
    for file_path in endpoint_files:
        try:
            with open(file_path, 'r') as f:
                file_content = f.read()
            
            modified = False
            original_content = file_content
            
            # Aplicar las mismas correcciones
            if 'KPIDashboard' in file_content:
                file_content = file_content.replace('KPIDashboard', 'DashboardKPIs')
                modified = True
            
            if 'KPIListResponse' in file_content:
                # En endpoints, mejor crear una respuesta genérica
                if 'from app.schemas.kpis import' in file_content:
                    file_content = file_content.replace('KPIListResponse', 'List[KPIResponse]')
                    # Asegurar que List está importado
                    if 'from typing import' in file_content and 'List' not in file_content:
                        file_content = file_content.replace('from typing import', 'from typing import List,')
                modified = True
            
            if modified:
                with open(file_path, 'w') as f:
                    f.write(file_content)
                print(f"✅ Archivo {file_path} corregido")
        except Exception as e:
            print(f"⚠️ No se pudo procesar {file_path}: {e}")
    
    print("\n✅ Correcciones completadas")
    print("🔧 Reinicia el servidor para aplicar los cambios")

if __name__ == "__main__":
    corregir_imports_kpi()
