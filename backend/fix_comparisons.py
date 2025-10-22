#!/usr/bin/env python3
"""
Script para corregir comparaciones con True/False (E712)
"""

import os
import re

def fix_comparison_errors(file_path):
    """Corregir comparaciones con True/False"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Patrones para corregir comparaciones con True/False
        patterns = [
            # Comparaciones con True
            (r'== True', ''),
            (r'==True', ''),
            (r' == True', ''),
            (r' ==True', ''),
            
            # Comparaciones con False
            (r'== False', ''),
            (r'==False', ''),
            (r' == False', ''),
            (r' ==False', ''),
            
            # Casos específicos en f-strings
            (r'Cliente\.activo == True', 'Cliente.activo'),
            (r'User\.is_admin == True', 'User.is_admin'),
            (r'User\.is_active == True', 'User.is_active'),
            (r'Analista\.activo == True', 'Analista.activo'),
            (r'ModeloVehiculo\.activo == True', 'ModeloVehiculo.activo'),
            (r'Concesionario\.activo == True', 'Concesionario.activo'),
            (r'Pago\.activo == True', 'Pago.activo'),
            (r'Pago\.conciliado == True', 'Pago.conciliado'),
            
            # Casos específicos con False
            (r'User\.is_admin == False', '~User.is_admin'),
            (r'User\.is_active == False', '~User.is_active'),
        ]
        
        # Aplicar patrones
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        # Si el contenido cambió, escribir el archivo
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Corregido: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error procesando {file_path}: {e}")
        return False

def main():
    """Función principal"""
    app_dir = "app"
    fixed_count = 0
    
    for root, dirs, files in os.walk(app_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_comparison_errors(file_path):
                    fixed_count += 1
    
    print(f"Total de archivos corregidos: {fixed_count}")

if __name__ == "__main__":
    main()

