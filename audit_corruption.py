#!/usr/bin/env python3
"""
Auditoría completa de archivos corruptos
Detecta caracteres Unicode invisibles, archivos sin saltos de línea, etc.
"""

import os
import re
import sys
from pathlib import Path

def detect_corruption_issues(file_path):
    """Detecta problemas de corrupción en un archivo"""
    issues = []
    
    try:
        with open(file_path, 'rb') as f:
            content_bytes = f.read()
        
        # Detectar BOM
        if content_bytes.startswith(b'\xef\xbb\xbf'):
            issues.append("BOM (Byte Order Mark) detectado")
        
        # Detectar caracteres extraños
        strange_chars = re.findall(rb'[\x80-\xff]', content_bytes)
        if strange_chars:
            issues.append(f"Caracteres extraños: {len(strange_chars)} encontrados")
        
        # Leer como texto para más análisis
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Detectar archivos sin saltos de línea
        if '\n' not in content and len(content) > 100:
            issues.append("Archivo sin saltos de línea (posible corrupción)")
        
        # Detectar líneas extremadamente largas
        lines = content.split('\n')
        long_lines = [i for i, line in enumerate(lines) if len(line) > 500]
        if long_lines:
            issues.append(f"Líneas extremadamente largas: {len(long_lines)}")
        
        # Detectar caracteres invisibles específicos
        invisible_chars = ['\ufeff', '\u00ad', '\u200b', '\u200c', '\u200d']
        for char in invisible_chars:
            if char in content:
                issues.append(f"Carácter invisible '{char}' detectado")
        
        return issues
        
    except Exception as e:
        return [f"Error leyendo archivo: {e}"]

def audit_project():
    """Auditoría completa del proyecto"""
    backend_path = Path("backend")
    corrupt_files = []
    
    print("🔍 INICIANDO AUDITORÍA COMPLETA DEL PROYECTO")
    print("=" * 60)
    
    # Buscar archivos Python
    python_files = list(backend_path.rglob("*.py"))
    
    for file_path in python_files:
        issues = detect_corruption_issues(file_path)
        if issues:
            corrupt_files.append((file_path, issues))
            print(f"❌ {file_path}")
            for issue in issues:
                print(f"   - {issue}")
    
    print("=" * 60)
    print(f"📊 RESUMEN:")
    print(f"   - Archivos Python analizados: {len(python_files)}")
    print(f"   - Archivos corruptos encontrados: {len(corrupt_files)}")
    
    if corrupt_files:
        print(f"\n🚨 ARCHIVOS QUE NECESITAN CORRECCIÓN:")
        for file_path, issues in corrupt_files:
            print(f"   - {file_path}")
    
    return corrupt_files

if __name__ == "__main__":
    corrupt_files = audit_project()
    
    if corrupt_files:
        print(f"\n⚠️  SE ENCONTRARON {len(corrupt_files)} ARCHIVOS CORRUPTOS")
        print("   Estos archivos necesitan ser reescritos desde cero")
        sys.exit(1)
    else:
        print(f"\n✅ NO SE ENCONTRARON ARCHIVOS CORRUPTOS")
        sys.exit(0)
