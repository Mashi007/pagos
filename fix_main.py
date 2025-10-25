#!/usr/bin/env python3
"""
Script para corregir el formato del archivo main.py
"""

import os
import re

def fix_main_py():
    """Corregir el formato del archivo main.py"""
    
    main_py_path = "backend/app/main.py"
    
    if not os.path.exists(main_py_path):
        print(f"❌ Archivo no encontrado: {main_py_path}")
        return False
    
    try:
        # Leer el archivo
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 Archivo leído: {len(content)} caracteres")
        
        # Verificar si el archivo está en una sola línea
        lines = content.split('\n')
        print(f"📊 Líneas detectadas: {len(lines)}")
        
        if len(lines) == 1:
            print("⚠️  Archivo está en una sola línea - corrigiendo...")
            
            # Dividir por puntos y comas y otros separadores
            content = re.sub(r';\s*', ';\n', content)
            content = re.sub(r'}\s*{', '}\n{', content)
            content = re.sub(r'}\s*@', '}\n@', content)
            content = re.sub(r'}\s*app\.', '}\napp.', content)
            content = re.sub(r'}\s*#', '}\n#', content)
            content = re.sub(r'}\s*from', '}\nfrom', content)
            content = re.sub(r'}\s*import', '}\nimport', content)
            content = re.sub(r'}\s*class', '}\nclass', content)
            content = re.sub(r'}\s*def', '}\ndef', content)
            content = re.sub(r'}\s*async', '}\nasync', content)
            content = re.sub(r'}\s*logger', '}\nlogger', content)
            content = re.sub(r'}\s*app', '}\napp', content)
            
            # Dividir por otros patrones comunes
            content = re.sub(r'from\s+', '\nfrom ', content)
            content = re.sub(r'import\s+', '\nimport ', content)
            content = re.sub(r'class\s+', '\nclass ', content)
            content = re.sub(r'def\s+', '\ndef ', content)
            content = re.sub(r'async\s+def\s+', '\nasync def ', content)
            content = re.sub(r'@\w+', '\n@\\g<0>', content)
            
            # Limpiar líneas vacías múltiples
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            
            # Escribir el archivo corregido
            with open(main_py_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ Archivo corregido y guardado")
            
            # Verificar el resultado
            with open(main_py_path, 'r', encoding='utf-8') as f:
                new_content = f.read()
            
            new_lines = new_content.split('\n')
            print(f"📊 Nuevas líneas: {len(new_lines)}")
            
            return True
            
        else:
            print("✅ Archivo ya tiene formato correcto")
            return True
            
    except Exception as e:
        print(f"❌ Error al procesar archivo: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Corrigiendo formato de main.py...")
    success = fix_main_py()
    
    if success:
        print("✅ Proceso completado exitosamente")
    else:
        print("❌ Proceso falló")
