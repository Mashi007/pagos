#!/usr/bin/env python3
"""
Script para corregir errores de flake8 de manera sistemática y agresiva
"""

import os
import re

def fix_file_imports(file_path):
    """Corregir imports faltantes en un archivo específico"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Lista de imports comunes que faltan
        common_imports = {
            'Session': 'from sqlalchemy.orm import Session',
            'User': 'from app.models.user import User',
            'Cliente': 'from app.models.cliente import Cliente',
            'Prestamo': 'from app.models.prestamo import Prestamo',
            'Notificacion': 'from app.models.notificacion import Notificacion',
            'Auditoria': 'from app.models.auditoria import Auditoria',
            'Decimal': 'from decimal import Decimal',
            'datetime': 'from datetime import datetime',
            'date': 'from datetime import date',
            'timedelta': 'from datetime import timedelta',
            'Optional': 'from typing import Optional',
            'List': 'from typing import List',
            'Dict': 'from typing import Dict',
            'Any': 'from typing import Any',
            'Tuple': 'from typing import Tuple',
            're': 'import re',
            'json': 'import json',
            'time': 'import time',
            'settings': 'from app.core.config import settings',
            'HTTPException': 'from fastapi import HTTPException',
            'relationship': 'from sqlalchemy.orm import relationship',
            'ForeignKey': 'from sqlalchemy import ForeignKey',
            'Text': 'from sqlalchemy import Text',
            'Numeric': 'from sqlalchemy import Numeric',
            'JSON': 'from sqlalchemy import JSON',
            'Boolean': 'from sqlalchemy import Boolean',
            'Enum': 'from sqlalchemy import Enum',
        }
        
        # Buscar qué imports faltan
        missing_imports = []
        for name, import_stmt in common_imports.items():
            if f'F821 undefined name \'{name}\'' in str(content) or f'undefined name \'{name}\'' in str(content):
                missing_imports.append(import_stmt)
        
        # Si hay imports faltantes, agregarlos al inicio del archivo
        if missing_imports:
            # Encontrar dónde insertar los imports
            lines = content.split('\n')
            insert_index = 0
            
            # Buscar la primera línea que no sea comentario o docstring
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                    insert_index = i
                    break
            
            # Insertar imports faltantes
            for import_stmt in missing_imports:
                if import_stmt not in content:
                    lines.insert(insert_index, import_stmt)
                    insert_index += 1
            
            content = '\n'.join(lines)
        
        # Corregir comparaciones con True/False
        content = re.sub(r'== True', '', content)
        content = re.sub(r'== False', '', content)
        content = re.sub(r'==True', '', content)
        content = re.sub(r'==False', '', content)
        
        # Corregir imports duplicados
        lines = content.split('\n')
        seen_imports = set()
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                if stripped not in seen_imports:
                    seen_imports.add(stripped)
                    new_lines.append(line)
                # else: skip duplicate import
            else:
                new_lines.append(line)
        
        content = '\n'.join(new_lines)
        
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

def fix_syntax_errors(file_path):
    """Corregir errores de sintaxis específicos"""
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
            (r'^json$', 'import json'),
            (r'^settings$', 'from app.core.config import settings'),
            (r'^HTTPException$', 'from fastapi import HTTPException'),
            (r'^relationship$', 'from sqlalchemy.orm import relationship'),
            (r'^ForeignKey$', 'from sqlalchemy import ForeignKey'),
            (r'^Text$', 'from sqlalchemy import Text'),
            (r'^Numeric$', 'from sqlalchemy import Numeric'),
            (r'^JSON$', 'from sqlalchemy import JSON'),
            (r'^Boolean$', 'from sqlalchemy import Boolean'),
            (r'^Enum$', 'from sqlalchemy import Enum'),
            
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

def main():
    """Función principal"""
    print("Corrigiendo errores de sintaxis e imports en todos los archivos...")
    
    # Recorrer todos los archivos .py en la carpeta 'app'
    base_dir = 'app'
    total_corrected = 0
    
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_file_imports(file_path):
                    total_corrected += 1
                if fix_syntax_errors(file_path):
                    total_corrected += 1
    
    print(f"Total de archivos corregidos: {total_corrected}")

if __name__ == "__main__":
    main()
