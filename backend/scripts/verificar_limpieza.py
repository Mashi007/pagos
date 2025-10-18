#!/usr/bin/env python3
"""
Script para verificar que no queden referencias a roles obsoletos
"""
import os
import re
from pathlib import Path

def verificar_referencias_obsoletas():
    """Verificar que no queden referencias a roles obsoletos"""
    
    scripts_dir = Path(__file__).parent
    
    # Patrones a buscar
    patrones_obsoletos = [
        r'\.rol\b',  # Referencias a .rol
        r'UserRole\b',  # Referencias a UserRole
        r'rol\s*=',  # Asignaciones de rol
        r'rol\s*:',  # Diccionarios con rol
        r'"rol"',  # Strings con rol
        r"'rol'",  # Strings con rol
    ]
    
    print("🔍 VERIFICACIÓN DE REFERENCIAS OBSOLETAS")
    print("=" * 50)
    
    archivos_con_problemas = []
    
    for archivo in scripts_dir.glob("*.py"):
        if archivo.name == __file__.split("/")[-1]:  # Saltar este archivo
            continue
            
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                contenido = f.read()
                
            problemas = []
            for patron in patrones_obsoletos:
                matches = re.findall(patron, contenido)
                if matches:
                    problemas.extend(matches)
            
            if problemas:
                archivos_con_problemas.append((archivo.name, problemas))
                
        except Exception as e:
            print(f"❌ Error leyendo {archivo.name}: {e}")
    
    if archivos_con_problemas:
        print("❌ ARCHIVOS CON REFERENCIAS OBSOLETAS:")
        for archivo, problemas in archivos_con_problemas:
            print(f"   📁 {archivo}")
            for problema in set(problemas):
                print(f"      - {problema}")
    else:
        print("✅ No se encontraron referencias obsoletas")
    
    print("=" * 50)

if __name__ == "__main__":
    verificar_referencias_obsoletas()
