#!/usr/bin/env python3
"""
Script para detectar caracteres invisibles y problemas de codificación específicos
"""

import os
import unicodedata

def analyze_file_encoding(file_path):
    """Analizar problemas de codificación y caracteres invisibles"""
    
    if not os.path.exists(file_path):
        print(f"ERROR: Archivo no encontrado: {file_path}")
        return
    
    print(f"\n=== ANALIZANDO {file_path} ===")
    
    # Intentar diferentes codificaciones
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            print(f"✓ Leído exitosamente con {encoding}")
            
            # Analizar caracteres problemáticos
            analyze_problematic_chars(content, file_path)
            break
            
        except UnicodeDecodeError as e:
            print(f"✗ Error con {encoding}: {e}")
            continue
    
    # Analizar bytes raw
    analyze_raw_bytes(file_path)

def analyze_problematic_chars(content, file_path):
    """Analizar caracteres problemáticos en el contenido"""
    
    print(f"\n--- Análisis de caracteres problemáticos ---")
    
    problematic_chars = []
    line_numbers = []
    
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        for j, char in enumerate(line):
            # Detectar caracteres problemáticos
            if ord(char) > 127:  # Caracteres no ASCII
                problematic_chars.append({
                    'char': char,
                    'ord': ord(char),
                    'name': unicodedata.name(char, 'UNKNOWN'),
                    'line': i,
                    'col': j + 1
                })
            
            # Detectar caracteres de control problemáticos
            elif char in ['\t', '\r']:
                problematic_chars.append({
                    'char': repr(char),
                    'ord': ord(char),
                    'name': 'CONTROL_CHAR',
                    'line': i,
                    'col': j + 1
                })
    
    if problematic_chars:
        print(f"Encontrados {len(problematic_chars)} caracteres problemáticos:")
        for char_info in problematic_chars[:10]:  # Mostrar solo los primeros 10
            print(f"  Línea {char_info['line']}, Col {char_info['col']}: "
                  f"'{char_info['char']}' (ord: {char_info['ord']}, name: {char_info['name']})")
        
        if len(problematic_chars) > 10:
            print(f"  ... y {len(problematic_chars) - 10} más")
    else:
        print("✓ No se encontraron caracteres problemáticos")
    
    # Analizar líneas específicas con errores
    error_lines = [110, 54, 57]  # Líneas reportadas por flake8
    print(f"\n--- Análisis de líneas con errores ---")
    
    for line_num in error_lines:
        if line_num <= len(lines):
            line = lines[line_num - 1]
            print(f"Línea {line_num}: {repr(line)}")
            
            # Mostrar caracteres byte por byte
            print(f"  Bytes: {[ord(c) for c in line]}")
            
            # Mostrar espacios vs tabs
            spaces = line.count(' ')
            tabs = line.count('\t')
            print(f"  Espacios: {spaces}, Tabs: {tabs}")

def analyze_raw_bytes(file_path):
    """Analizar bytes raw del archivo"""
    
    print(f"\n--- Análisis de bytes raw ---")
    
    try:
        with open(file_path, 'rb') as f:
            raw_bytes = f.read()
        
        print(f"Tamaño del archivo: {len(raw_bytes)} bytes")
        
        # Buscar secuencias problemáticas
        problematic_sequences = [
            b'\x81',  # Carácter problemático común
            b'\x82',  # Otro carácter problemático
            b'\x91',  # Comilla izquierda
            b'\x92',  # Comilla derecha
            b'\x93',  # Comilla doble izquierda
            b'\x94',  # Comilla doble derecha
            b'\x96',  # Guión largo
            b'\x97',  # Guión largo
        ]
        
        for seq in problematic_sequences:
            count = raw_bytes.count(seq)
            if count > 0:
                print(f"  Encontrado {count} ocurrencias de {seq.hex()}")
        
        # Mostrar primeros 200 bytes en hex
        print(f"Primeros 200 bytes (hex): {raw_bytes[:200].hex()}")
        
    except Exception as e:
        print(f"Error al leer bytes raw: {e}")

def main():
    """Función principal"""
    
    files_to_analyze = [
        "backend/app/api/v1/endpoints/intermittent_failure_analyzer.py",
        "backend/app/api/v1/endpoints/network_diagnostic.py",
        "backend/app/api/v1/endpoints/temporal_analysis.py"
    ]
    
    print("ANÁLISIS DE CARACTERES INVISIBLES Y PROBLEMAS DE CODIFICACIÓN")
    print("=" * 70)
    
    for file_path in files_to_analyze:
        analyze_file_encoding(file_path)
    
    print("\n" + "=" * 70)
    print("ANÁLISIS COMPLETADO")

if __name__ == "__main__":
    main()
