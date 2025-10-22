#!/usr/bin/env python3
"""
Script para corregir errores de sintaxis críticos (E999)
"""

import os
import re

def fix_syntax_errors_critical(file_path):
    """Corregir errores de sintaxis críticos"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Patrones específicos para errores de sintaxis críticos
        patterns = [
            # Corregir imports mal formateados que causan E999
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
    print("Corrigiendo errores de sintaxis críticos...")
    
    # Archivos específicos con errores E999
    critical_files = [
        "app/core/security.py",
        "app/db/init_db.py",
        "app/services/validators_service.py",
        "app/services/whatsapp_service.py",
    ]
    
    total_corrected = 0
    
    for file_path in critical_files:
        if os.path.exists(file_path):
            if fix_syntax_errors_critical(file_path):
                total_corrected += 1
    
    print(f"Total de archivos críticos corregidos: {total_corrected}")

if __name__ == "__main__":
    main()
