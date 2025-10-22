#!/usr/bin/env python3
"""
Script para corregir los últimos imports no utilizados (F401)
"""

import os
import re

def fix_remaining_imports(file_path):
    """Corregir imports específicos no utilizados"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Patrones específicos para los últimos imports
        patterns = [
            # Remover imports específicos
            (r'from typing import Optional\n', ''),
            (r'from typing import List\n', ''),
            (r'from typing import Any\n', ''),
            (r'from typing import Tuple\n', ''),
            (r'from sqlalchemy import func, case, desc\n', 'from sqlalchemy import func, case\n'),
            (r'from sqlalchemy import func, case, desc', 'from sqlalchemy import func, case'),
            (r'from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric\n', 'from sqlalchemy import Column, Integer, String, Boolean, DateTime\n'),
            (r'from collections import defaultdict\n', ''),
            (r'from app.schemas.pago import \(\n    PagoCreate,\n    PagoResponse,\n    PagoUpdate,\n    ConciliacionCreate,\n    ConciliacionResponse\n\)', 'from app.schemas.pago import (\n    PagoCreate,\n    PagoResponse\n)'),
            (r'from app.utils.auditoria_helper import \(\n    registrar_creacion,\n    registrar_actualizacion,\n    registrar_error\n\)', 'from app.utils.auditoria_helper import (\n    registrar_creacion\n)'),
        ]
        
        # Aplicar patrones
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
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
    files_to_fix = [
        "app/api/v1/endpoints/critical_error_monitor.py",
        "app/api/v1/endpoints/dashboard.py",
        "app/api/v1/endpoints/diagnostico.py",
        "app/api/v1/endpoints/forensic_analysis.py",
        "app/api/v1/endpoints/notificaciones_multicanal.py",
        "app/api/v1/endpoints/pagos.py",
        "app/api/v1/endpoints/predictive_analyzer.py",
        "app/api/v1/endpoints/realtime_specific_monitor.py",
        "app/api/v1/endpoints/scheduler_notificaciones.py",
        "app/api/v1/endpoints/schema_analyzer.py",
        "app/api/v1/endpoints/strategic_measurements.py",
        "app/api/v1/endpoints/users.py",
        "app/models/modelo_vehiculo.py",
        "app/services/ml_service.py",
        "app/services/notification_multicanal_service.py",
        "app/services/quality_standards.py",
    ]
    
    fixed_count = 0
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_remaining_imports(file_path):
                fixed_count += 1
    
    print(f"Total de archivos corregidos: {fixed_count}")

if __name__ == "__main__":
    main()

