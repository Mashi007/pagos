#!/usr/bin/env python3
"""
Script para corregir errores de sintaxis de manera más agresiva
"""

import os
import re

def fix_file_syntax(file_path):
    """Corregir errores de sintaxis en un archivo específico"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Lista de imports que deben estar al inicio del archivo
        required_imports = [
            'import os',
            'import re',
            'import json',
            'import time',
            'import logging',
            'from datetime import datetime, date, timedelta',
            'from typing import Optional, List, Dict, Any, Tuple',
            'from decimal import Decimal',
            'from sqlalchemy.orm import Session, relationship',
            'from sqlalchemy import ForeignKey, Text, Numeric, JSON, Boolean, Enum',
            'from fastapi import APIRouter, Depends, HTTPException, Query, status',
            'from app.core.config import settings',
            'from app.models.user import User',
            'from app.models.cliente import Cliente',
            'from app.models.prestamo import Prestamo',
            'from app.models.notificacion import Notificacion',
            'from app.models.auditoria import Auditoria',
            'from app.models.aprobacion import EstadoAprobacion',
            'from app.models.prestamo import EstadoPrestamo',
            'from app.models.notificacion import EstadoNotificacion, TipoNotificacion',
            'from app.models.auditoria import TipoAccion',
            'from app.db.session import get_db',
            'from app.api.deps import get_current_user',
            'from collections import deque',
            'import psutil',
        ]
        
        # Dividir el contenido en líneas
        lines = content.split('\n')
        
        # Encontrar dónde insertar los imports
        insert_index = 0
        
        # Buscar la primera línea que no sea comentario o docstring
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('"""') and not stripped.startswith("'''"):
                insert_index = i
                break
        
        # Insertar imports requeridos si no están presentes
        for import_stmt in required_imports:
            if import_stmt not in content:
                lines.insert(insert_index, import_stmt)
                insert_index += 1
        
        # Reconstruir el contenido
        content = '\n'.join(lines)
        
        # Corregir errores de sintaxis específicos
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
            (r'^psutil$', 'import psutil'),
            (r'^os$', 'import os'),
            (r'^deque$', 'from collections import deque'),
            (r'^EstadoAprobacion$', 'from app.models.aprobacion import EstadoAprobacion'),
            (r'^EstadoPrestamo$', 'from app.models.prestamo import EstadoPrestamo'),
            (r'^EstadoNotificacion$', 'from app.models.notificacion import EstadoNotificacion'),
            (r'^TipoNotificacion$', 'from app.models.notificacion import TipoNotificacion'),
            (r'^TipoAccion$', 'from app.models.auditoria import TipoAccion'),
            
            # Corregir errores de sintaxis específicos
            (r'^import logging\nimport logging\n', 'import logging\n'),
            (r'^from datetime import datetime\nfrom datetime import datetime\n', 'from datetime import datetime\n'),
            (r'^from typing import Optional\nfrom typing import Optional\n', 'from typing import Optional\n'),
            (r'^from sqlalchemy.orm import Session\nfrom sqlalchemy.orm import Session\n', 'from sqlalchemy.orm import Session\n'),
            
            # Corregir líneas que empiezan con caracteres especiales
            (r'^[^a-zA-Z_#\s]', ''),
            
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
    print("Corrigiendo errores de sintaxis en todos los archivos...")
    
    # Recorrer todos los archivos .py en la carpeta 'app'
    base_dir = 'app'
    total_corrected = 0
    
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_file_syntax(file_path):
                    total_corrected += 1
    
    print(f"Total de archivos corregidos: {total_corrected}")

if __name__ == "__main__":
    main()
