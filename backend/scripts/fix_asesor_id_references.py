"""
Script para reemplazar todas las referencias a asesor_id por asesor_config_id
Este cambio es necesario porque:
- Cliente ya NO tiene asesor_id (relación con User)
- Cliente solo tiene asesor_config_id (relación con Asesor de configuración)
"""

import re
from pathlib import Path

# Archivos a procesar
FILES_TO_PROCESS = [
    "backend/app/api/v1/endpoints/clientes.py",
    "backend/app/schemas/cliente.py",
]

# Patrones a reemplazar
REPLACEMENTS = [
    # En endpoints
    (r'asesor_id: Optional\[int\] = Query\(None, description="ID del asesor asignado"\)', 
     'asesor_config_id: Optional[int] = Query(None, description="ID del asesor de configuración asignado")'),
    
    (r'Cliente\.asesor_id', 'Cliente.asesor_config_id'),
    (r'cliente\.asesor_id', 'cliente.asesor_config_id'),
    
    # En schemas
    (r'asesor_id: Optional\[int\] = None  # Asesor del sistema \(users\)', 
     '# asesor_id eliminado - solo usar asesor_config_id'),
    
    (r'asesor_id: Optional\[int\] = None', 
     'asesor_config_id: Optional[int] = None'),
    
    (r'asesor_id: int = Field\(\.\.\., description="ID del asesor responsable"\)',
     'asesor_config_id: int = Field(..., description="ID del asesor de configuración responsable")'),
    
    # Parámetros de funciones
    (r'nuevo_asesor_id: int', 'nuevo_asesor_config_id: int'),
    (r'nuevo_asesor_id\)', 'nuevo_asesor_config_id)'),
    
    # Queries que buscan en User - cambiar a buscar en Asesor
    (r'db\.query\(User\)\.filter\(User\.id == cliente\.asesor_id\)',
     'db.query(Asesor).filter(Asesor.id == cliente.asesor_config_id)'),
    
    (r'db\.query\(User\)\.filter\(User\.id == cliente_data\.asesor_id\)',
     'db.query(Asesor).filter(Asesor.id == cliente_data.asesor_config_id)'),
    
    (r'db\.query\(User\)\.filter\(User\.id == nuevo_asesor_id\)',
     'db.query(Asesor).filter(Asesor.id == nuevo_asesor_config_id)'),
    
    # Joins con User - cambiar a Asesor
    (r'User\.id == Cliente\.asesor_id', 'Asesor.id == Cliente.asesor_config_id'),
    
    # Diccionarios y strings
    (r'"asesor_id": current_user\.id', '"asesor_config_id": None  # Los clientes NO se asignan automáticamente a users'),
    (r'"asesor_id": cliente\.asesor_id', '"asesor_config_id": cliente.asesor_config_id'),
    (r'"asesor_anterior"', '"asesor_config_anterior"'),
    (r'"asesor_nuevo"', '"asesor_config_nuevo"'),
    (r'asesor_anterior = ', 'asesor_config_anterior = '),
    
    # ADD COLUMN en SQL
    (r'ALTER TABLE clientes ADD COLUMN IF NOT EXISTS asesor_id INTEGER',
     'ALTER TABLE clientes ADD COLUMN IF NOT EXISTS asesor_config_id INTEGER'),
    
    # Filtros
    (r'filters\.asesor_id', 'filters.asesor_config_id'),
]

def fix_file(file_path: str):
    """Aplicar todos los reemplazos a un archivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for pattern, replacement in REPLACEMENTS:
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ {file_path} - Actualizado")
            return True
        else:
            print(f"ℹ️  {file_path} - Sin cambios")
            return False
            
    except Exception as e:
        print(f"❌ Error en {file_path}: {e}")
        return False

def main():
    print("🔧 Iniciando corrección de referencias asesor_id → asesor_config_id")
    print("="*70)
    
    files_updated = 0
    for file_path in FILES_TO_PROCESS:
        if fix_file(file_path):
            files_updated += 1
    
    print("="*70)
    print(f"✅ Proceso completado: {files_updated}/{len(FILES_TO_PROCESS)} archivos actualizados")

if __name__ == "__main__":
    main()

