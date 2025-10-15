#!/usr/bin/env python3
"""
Script para eliminar todas las referencias al rol GERENTE
Reemplaza listas que incluyen GERENTE con solo ADMINISTRADOR_GENERAL
"""
import re
import os
from pathlib import Path

def process_file(file_path):
    """Procesar un archivo eliminando referencias a GERENTE"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Patrón 1: ["ADMINISTRADOR_GENERAL", "GERENTE", "COBRANZAS"] -> ["ADMINISTRADOR_GENERAL", "COBRANZAS"]
    pattern1 = r'\["ADMINISTRADOR_GENERAL",\s*"GERENTE",\s*"COBRANZAS"\]'
    if re.search(pattern1, content):
        content = re.sub(pattern1, '["ADMINISTRADOR_GENERAL", "COBRANZAS"]', content)
        changes.append("Patrón 1: Lista completa")
    
    # Patrón 2: ["ADMINISTRADOR_GENERAL", "GERENTE"] -> ["ADMINISTRADOR_GENERAL"]
    pattern2 = r'\["ADMINISTRADOR_GENERAL",\s*"GERENTE"\]'
    if re.search(pattern2, content):
        content = re.sub(pattern2, '["ADMINISTRADOR_GENERAL"]', content)
        changes.append("Patrón 2: Solo ADMIN y GERENTE")
    
    # Patrón 3: ["GERENTE", "ADMINISTRADOR_GENERAL"] -> ["ADMINISTRADOR_GENERAL"]
    pattern3 = r'\["GERENTE",\s*"ADMINISTRADOR_GENERAL"\]'
    if re.search(pattern3, content):
        content = re.sub(pattern3, '["ADMINISTRADOR_GENERAL"]', content)
        changes.append("Patrón 3: GERENTE primero")
    
    # Patrón 4: "GERENTE" solo -> "ADMINISTRADOR_GENERAL"
    pattern4 = r'(?<=["\'])GERENTE(?=["\'])'
    if re.search(pattern4, content):
        content = re.sub(pattern4, 'ADMINISTRADOR_GENERAL', content)
        changes.append("Patrón 4: GERENTE solo")
    
    # Patrón 5: , "GERENTE" (en medio de listas)
    pattern5 = r',\s*"GERENTE"'
    if re.search(pattern5, content):
        content = re.sub(pattern5, '', content)
        changes.append("Patrón 5: GERENTE en medio")
    
    # Patrón 6: "GERENTE", (al inicio de listas)
    pattern6 = r'"GERENTE",\s*'
    if re.search(pattern6, content):
        content = re.sub(pattern6, '', content)
        changes.append("Patrón 6: GERENTE al inicio")
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, changes
    
    return False, []

def main():
    """Procesar todos los archivos Python en app/"""
    backend_dir = Path(__file__).parent.parent
    app_dir = backend_dir / "app"
    
    print("🔍 Buscando archivos con referencias a GERENTE...")
    files_changed = 0
    total_changes = 0
    
    for py_file in app_dir.rglob("*.py"):
        changed, changes = process_file(py_file)
        if changed:
            files_changed += 1
            total_changes += len(changes)
            rel_path = py_file.relative_to(backend_dir)
            print(f"✅ {rel_path}")
            for change in changes:
                print(f"   - {change}")
    
    print(f"\n📊 Resumen:")
    print(f"   Archivos modificados: {files_changed}")
    print(f"   Total de cambios: {total_changes}")
    print(f"✅ Proceso completado")

if __name__ == "__main__":
    main()

