#!/usr/bin/env python3
"""
Script para corregir imports no utilizados (F401) en archivos Python
"""

import os
import re

def fix_unused_imports(file_path):
    """Corregir imports no utilizados en un archivo"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Patrones comunes de imports no utilizados
        patterns = [
            # Remover imports específicos no utilizados
            (r'from typing import Generator,', 'from typing import'),
            (r'from typing import List, Optional', 'from typing import Optional'),
            (r'from typing import Dict, List, Any, Optional, Tuple', 'from typing import Dict, Any'),
            (r'from typing import Dict, Any, List, Optional, Tuple', 'from typing import Dict, Any'),
            (r'from typing import List, Optional, Dict, Any', 'from typing import Dict, Any'),
            (r'from typing import Optional, List', 'from typing import Optional'),
            (r'from typing import Dict, Any, Optional', 'from typing import Dict, Any'),
            (r'from typing import Dict, List, Any', 'from typing import Dict, Any'),
            (r'from typing import List,', 'from typing import'),
            (r'from typing import Dict,', 'from typing import'),
            (r'from typing import Any,', 'from typing import'),
            (r'from typing import Tuple,', 'from typing import'),
            (r'from typing import Optional,', 'from typing import'),
            
            # Imports específicos no utilizados
            (r'import json\n', ''),
            (r'import os\n', ''),
            (r'import time\n', ''),
            (r'import asyncio\n', ''),
            (r'import math\n', ''),
            (r'import hmac\n', ''),
            (r'import pickle\n', ''),
            (r'import inspect\n', ''),
            (r'import re\n', ''),
            (r'import csv\n', ''),
            (r'import tempfile\n', ''),
            (r'import subprocess\n', ''),
            (r'import platform\n', ''),
            (r'import traceback\n', ''),
            (r'import statistics\n', ''),
            (r'import numpy as np\n', ''),
            (r'import pandas as pd\n', ''),
            
            # Imports de datetime no utilizados
            (r'from datetime import datetime, timedelta', 'from datetime import datetime'),
            (r'from datetime import date, datetime, timedelta', 'from datetime import datetime'),
            (r'from datetime import datetime, timedelta, date, time', 'from datetime import datetime'),
            (r'from datetime import datetime, date', 'from datetime import datetime'),
            (r'from datetime import timedelta', ''),
            (r'from datetime import date', ''),
            (r'from datetime import time', ''),
            
            # Imports de SQLAlchemy no utilizados
            (r'from sqlalchemy import func, and_, or_', 'from sqlalchemy import func'),
            (r'from sqlalchemy import func, and_', 'from sqlalchemy import func'),
            (r'from sqlalchemy import func, or_', 'from sqlalchemy import func'),
            (r'from sqlalchemy import and_, or_, func', 'from sqlalchemy import func'),
            (r'from sqlalchemy import or_, desc', 'from sqlalchemy import or_'),
            (r'from sqlalchemy import func, and_, or_, case, desc', 'from sqlalchemy import func, case'),
            (r'from sqlalchemy import func, and_, or_, case', 'from sqlalchemy import func, case'),
            (r'from sqlalchemy import func, and_, or_', 'from sqlalchemy import func'),
            (r'from sqlalchemy import and_', ''),
            (r'from sqlalchemy import or_', ''),
            (r'from sqlalchemy import desc', ''),
            (r'from sqlalchemy import text', ''),
            
            # Imports de FastAPI no utilizados
            (r'from fastapi import APIRouter, Depends, HTTPException, Request', 'from fastapi import APIRouter, Depends, HTTPException'),
            (r'from fastapi import APIRouter, Depends, HTTPException, Query, status', 'from fastapi import APIRouter, Depends, HTTPException, Query'),
            (r'from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks', 'from fastapi import APIRouter, Depends, HTTPException'),
            (r'from fastapi import APIRouter, Depends, Request, Response', 'from fastapi import APIRouter, Depends'),
            (r'from fastapi import APIRouter, Depends, Request', 'from fastapi import APIRouter, Depends'),
            (r'from fastapi import APIRouter, Depends, HTTPException, Request, Response', 'from fastapi import APIRouter, Depends, HTTPException'),
            (r'from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, BackgroundTasks', 'from fastapi import APIRouter, Depends, HTTPException, UploadFile, File'),
            (r'from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form', 'from fastapi import APIRouter, Depends, HTTPException, UploadFile, File'),
            (r'from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File', 'from fastapi import APIRouter, Depends, HTTPException, UploadFile, File'),
            (r'from fastapi import APIRouter, Depends, HTTPException, Query', 'from fastapi import APIRouter, Depends, HTTPException'),
            (r'from fastapi import APIRouter, Depends, HTTPException', 'from fastapi import APIRouter, Depends'),
            (r'from fastapi import APIRouter, Depends', 'from fastapi import APIRouter'),
            (r'from fastapi import Depends, HTTPException, status', 'from fastapi import Depends'),
            (r'from fastapi import HTTPException', ''),
            (r'from fastapi import Request', ''),
            (r'from fastapi import Response', ''),
            (r'from fastapi import BackgroundTasks', ''),
            (r'from fastapi import Form', ''),
            (r'from fastapi import status', ''),
            
            # Imports de collections no utilizados
            (r'from collections import defaultdict, deque', 'from collections import defaultdict'),
            (r'from collections import deque', ''),
            
            # Imports de jose no utilizados
            (r'from jose import JWTError', ''),
            
            # Imports de jwt no utilizados
            (r'import jwt', ''),
            
            # Imports de pydantic no utilizados
            (r'from pydantic import BaseModel, Field', 'from pydantic import BaseModel'),
            (r'from pydantic import BaseModel, EmailStr', 'from pydantic import BaseModel'),
            (r'from pydantic import Field', ''),
            (r'from pydantic import EmailStr', ''),
            
            # Imports de decimal no utilizados
            (r'from decimal import Decimal', ''),
            
            # Imports de sqlalchemy.orm no utilizados
            (r'from sqlalchemy.orm import Session', ''),
            (r'from sqlalchemy.orm import relationship', ''),
            
            # Imports de sqlalchemy no utilizados
            (r'from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text', 'from sqlalchemy import Column, Integer, String, Boolean, DateTime'),
            (r'from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, Text, Boolean, Numeric, ForeignKey', 'from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, Text, Boolean'),
            (r'from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, JSON', 'from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON'),
            (r'from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric', 'from sqlalchemy import Column, Integer, String, Boolean, DateTime'),
            (r'from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, JSON, Enum', 'from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum'),
            (r'from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Text, ForeignKey', 'from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, Text'),
            (r'from sqlalchemy import Text', ''),
            (r'from sqlalchemy import Numeric', ''),
            (r'from sqlalchemy import ForeignKey', ''),
            (r'from sqlalchemy import Boolean', ''),
            
            # Imports de datetime no utilizados en modelos
            (r'from datetime import datetime', ''),
            
            # Imports de slowapi no utilizados
            (r'from slowapi import Limiter, _rate_limit_exceeded_handler', ''),
            (r'from slowapi.util import get_remote_address', ''),
            (r'from slowapi.errors import RateLimitExceeded', ''),
            
            # Imports de openpyxl no utilizados
            (r'from openpyxl.styles import Font, PatternFill', ''),
            (r'from openpyxl.styles import Font, Alignment, PatternFill', ''),
            
            # Imports de reportlab no utilizados
            (r'from reportlab.lib.units import inch', ''),
            (r'from reportlab.lib.pagesizes import letter, A4', ''),
            (r'from reportlab.pdfgen import canvas', ''),
            
            # Imports de app.core no utilizados
            (r'from app.core.config import settings', ''),
            (r'from app.core.security import decode_token', ''),
            (r'from app.core.security import create_access_token', ''),
            (r'from app.core.security import verify_password', ''),
            (r'from app.core.permissions_simple import Permission, get_user_permissions', ''),
            (r'from app.core.permissions_simple import Permission', ''),
            (r'from app.core.permissions_simple import get_user_permissions', ''),
            
            # Imports de app.api no utilizados
            (r'from app.api.deps import get_current_user', ''),
            
            # Imports de app.db no utilizados
            (r'from app.db.session import get_db', ''),
            
            # Imports de app.models no utilizados
            (r'from app.models.cliente import Cliente', ''),
            (r'from app.models.prestamo import Prestamo', ''),
            (r'from app.models.pago import Pago', ''),
            (r'from app.models.user import User', ''),
            (r'from app.models.auditoria import Auditoria', ''),
            (r'from app.models.notificacion import Notificacion', ''),
            (r'from app.models.aprobacion import Aprobacion', ''),
            (r'from app.models.amortizacion import pago_cuotas', ''),
            
            # Imports de app.schemas no utilizados
            (r'from app.schemas.pago import PagoUpdate', ''),
            (r'from app.schemas.pago import ConciliacionCreate', ''),
            (r'from app.schemas.pago import ConciliacionResponse', ''),
            (r'from app.schemas.reportes import FiltrosReporte', ''),
            
            # Imports de app.services no utilizados
            (r'from app.services.validators_service import ValidadorTelefono', ''),
            (r'from app.services.validators_service import ValidadorCedula', ''),
            (r'from app.services.validators_service import ValidadorFecha', ''),
            (r'from app.services.validators_service import ValidadorEmail', ''),
            
            # Imports de app.utils no utilizados
            (r'from app.utils.auditoria_helper import registrar_actualizacion', ''),
            (r'from app.utils.auditoria_helper import registrar_error', ''),
            
            # Imports de app.core.impact_monitoring no utilizados
            (r'from app.core.impact_monitoring import get_impact_analyzer, ImpactAnalyzer', ''),
            (r'from app.core.error_impact_analysis import get_error_analyzer, ErrorImpactAnalyzer', ''),
            
            # Imports de psutil no utilizados
            (r'import psutil', ''),
            
            # Imports de typing no utilizados
            (r'from typing import Type', ''),
            (r'from typing import Callable', ''),
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
    app_dir = "app"
    fixed_count = 0
    
    for root, dirs, files in os.walk(app_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_unused_imports(file_path):
                    fixed_count += 1
    
    print(f"Total de archivos corregidos: {fixed_count}")

if __name__ == "__main__":
    main()

