#!/usr/bin/env python3
"""
Script para corregir errores de flake8 de manera sistemática
"""

import os
import re

def fix_syntax_errors(file_path):
    """Corregir errores de sintaxis básicos"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Corregir errores de sintaxis comunes
        patterns = [
            # Corregir imports mal formateados
            (r'^time$', 'import time'),
            (r'^datetime$', 'from datetime import datetime'),
            (r'^timedelta$', 'from datetime import timedelta'),
            (r'^date$', 'from datetime import date'),
            (r'^Optional$', 'from typing import Optional'),
            (r'^List$', 'from typing import List'),
            (r'^Dict$', 'from typing import Dict'),
            (r'^Any$', 'from typing import Any'),
            (r'^Tuple$', 'from typing import Tuple'),
            (r'^Session$', 'from sqlalchemy.orm import Session'),
            (r'^User$', 'from app.models.user import User'),
            (r'^Auditoria$', 'from app.models.auditoria import Auditoria'),
            (r'^Decimal$', 'from decimal import Decimal'),
            (r'^re$', 'import re'),
            
            # Corregir comparaciones con True/False
            (r'== True', ''),
            (r'== False', ''),
            (r'==True', ''),
            (r'==False', ''),
            
            # Corregir líneas demasiado largas en f-strings HTML
            (r'(\s+)("cuerpo_html": f"""\s*\n)', r'\1"cuerpo_html": f"""\n'),
            
            # Corregir imports duplicados
            (r'^import logging\nimport logging\n', 'import logging\n'),
            (r'^from datetime import datetime\nfrom datetime import datetime\n', 'from datetime import datetime\n'),
        ]
        
        # Aplicar patrones
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # Limpiar líneas vacías múltiples
        content = re.sub(r'\n\n\n+', '\n\n', content)
        
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

def fix_specific_files():
    """Corregir archivos específicos con problemas conocidos"""
    files_to_fix = [
        "app/api/v1/endpoints/analistas.py",
        "app/utils/date_helpers.py",
        "app/utils/auditoria_helper.py",
        "app/utils/validators.py",
    ]
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            fix_syntax_errors(file_path)

def main():
    """Función principal"""
    print("Corrigiendo errores de sintaxis en archivos específicos...")
    fix_specific_files()
    print("Corrección completada.")

if __name__ == "__main__":
    main()
