#!/usr/bin/env python3
"""
Script específico para eliminar imports no utilizados restantes.
"""

import os
import re

def remove_unused_imports():
    """Elimina imports no utilizados específicos."""
    print("Eliminando imports no utilizados restantes...")
    
    # Archivos específicos con imports a eliminar
    files_to_fix = {
        "app/api/v1/endpoints/architectural_analysis.py": [
            "from typing import Any, Dict, List",
        ],
        "app/api/v1/endpoints/auditoria.py": [
            "from datetime import datetime",
            "from typing import List",
        ],
        "app/api/v1/endpoints/carga_masiva.py": [
            "from typing import Any, List",
            "from fastapi import Form",
            "from app.models.auditoria import Auditoria, TipoAccion",
        ],
        "app/api/v1/endpoints/comparative_analysis.py": [
            "from typing import List",
        ],
        "app/api/v1/endpoints/conciliacion_bancaria.py": [
            "from app.schemas.conciliacion import ConciliacionCreate",
        ],
        "app/api/v1/endpoints/critical_error_monitor.py": [
            "from typing import Any, Dict, List",
        ],
        "app/api/v1/endpoints/cross_validation_auth.py": [
            "from fastapi import HTTPException",
        ],
        "app/api/v1/endpoints/dashboard.py": [
            "from typing import Any, Dict, List",
            "from sqlalchemy import and_, or_",
        ],
        "app/api/v1/endpoints/dashboard_diagnostico.py": [
            "from fastapi import HTTPException",
        ],
        "app/api/v1/endpoints/diagnostico.py": [
            "from typing import List",
        ],
        "app/api/v1/endpoints/diagnostico_auth.py": [
            "from fastapi import HTTPException",
        ],
        "app/api/v1/endpoints/diagnostico_refresh_token.py": [
            "from fastapi import HTTPException",
        ],
        "app/api/v1/endpoints/forensic_analysis.py": [
            "from typing import Any, Dict, List",
        ],
        "app/api/v1/endpoints/health.py": [
            "from fastapi import Depends",
        ],
        "app/api/v1/endpoints/kpis.py": [
            "from sqlalchemy import case, or_",
        ],
        "app/api/v1/endpoints/modelos_vehiculos.py": [
            "from typing import List",
        ],
        "app/api/v1/endpoints/pagos.py": [
            "from sqlalchemy import and_, desc, func",
        ],
        "app/api/v1/endpoints/predictive_analyzer.py": [
            "from typing import List, Optional, Tuple",
            "from fastapi import Request, status",
            "from app.api.deps import get_db",
        ],
        "app/api/v1/endpoints/predictive_token_analyzer.py": [
            "from typing import Any, Dict, List",
        ],
        "app/api/v1/endpoints/prestamos.py": [
            "from typing import Optional",
        ],
        "app/api/v1/endpoints/real_time_monitor.py": [
            "from fastapi import HTTPException",
        ],
        "app/api/v1/endpoints/realtime_specific_monitor.py": [
            "from fastapi import HTTPException",
        ],
        "app/api/v1/endpoints/reportes.py": [
            "from openpyxl.styles import Font, PatternFill",
            "from reportlab.lib.pagesizes import letter",
        ],
        "app/api/v1/endpoints/strategic_measurements.py": [
            "from typing import Any, Dict, List",
        ],
        "app/api/v1/endpoints/temporal_analysis.py": [
            "from typing import Any, Dict, List",
        ],
        "app/api/v1/endpoints/token_verification.py": [
            "from datetime import timedelta",
            "from fastapi import status",
        ],
        "app/api/v1/endpoints/users.py": [
            "from typing import List, Optional",
        ],
        "app/api/v1/endpoints/verificar_concesionarios.py": [
            "from fastapi import HTTPException",
        ],
        "app/models/auditoria.py": [
            "from typing import Any, Dict",
        ],
        "app/services/ml_service.py": [
            "from typing import Optional",
        ],
    }
    
    for file_path, imports_to_remove in files_to_fix.items():
        if os.path.exists(file_path):
            print(f"Procesando {file_path}...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            new_lines = []
            for line in lines:
                should_remove = False
                for import_line in imports_to_remove:
                    if import_line.strip() in line.strip():
                        should_remove = True
                        break
                
                if not should_remove:
                    new_lines.append(line)
                else:
                    print(f"  Eliminando: {line.strip()}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            print(f"  OK - Imports eliminados")

def main():
    """Función principal."""
    print("Eliminando imports no utilizados restantes...")
    
    # Cambiar al directorio backend
    os.chdir("backend")
    
    remove_unused_imports()
    
    print("Eliminación de imports completada!")

if __name__ == "__main__":
    main()
