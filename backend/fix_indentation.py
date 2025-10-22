#!/usr/bin/env python3
"""
Script para corregir errores de indentación comunes
"""

import os
import re

def fix_indentation_errors(file_path):
    """Corregir errores de indentación comunes"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Correcciones comunes de indentación
        fixes = [
            # Corregir imports sueltos que causan indentación
            (r'^ asc, func$', 'from sqlalchemy import asc, func'),
            (r'^ or_, desc$', 'from sqlalchemy import or_, desc'),
            (r'^ and_$', 'from sqlalchemy import and_'),
            (r'^ or_$', 'from sqlalchemy import or_'),
            (r'^ case$', 'from sqlalchemy import case'),
            (r'^ text$', 'from sqlalchemy import text'),
            (r'^ func$', 'from sqlalchemy import func'),
            (r'^ extract$', 'from sqlalchemy import extract'),
            (r'^ desc$', 'from sqlalchemy import desc'),
            
            # Corregir imports de datetime sueltos
            (r'^ datetime$', 'from datetime import datetime'),
            (r'^ date$', 'from datetime import date'),
            (r'^ timedelta$', 'from datetime import timedelta'),
            (r'^ time$', 'from datetime import time'),
            
            # Corregir imports de typing sueltos
            (r'^ Optional$', 'from typing import Optional'),
            (r'^ List$', 'from typing import List'),
            (r'^ Dict$', 'from typing import Dict'),
            (r'^ Any$', 'from typing import Any'),
            (r'^ Tuple$', 'from typing import Tuple'),
            (r'^ Generator$', 'from typing import Generator'),
            (r'^ Type$', 'from typing import Type'),
            
            # Corregir imports de decimal sueltos
            (r'^ Decimal$', 'from decimal import Decimal'),
            
            # Corregir imports de collections sueltos
            (r'^ deque$', 'from collections import deque'),
            (r'^ defaultdict$', 'from collections import defaultdict'),
            
            # Corregir imports de fastapi sueltos
            (r'^ APIRouter$', 'from fastapi import APIRouter'),
            (r'^ Depends$', 'from fastapi import Depends'),
            (r'^ HTTPException$', 'from fastapi import HTTPException'),
            (r'^ Query$', 'from fastapi import Query'),
            (r'^ status$', 'from fastapi import status'),
            (r'^ Request$', 'from fastapi import Request'),
            (r'^ Response$', 'from fastapi import Response'),
            (r'^ BackgroundTasks$', 'from fastapi import BackgroundTasks'),
            (r'^ FileResponse$', 'from fastapi.responses import FileResponse'),
            
            # Corregir imports de pydantic sueltos
            (r'^ Field$', 'from pydantic import Field'),
            (r'^ EmailStr$', 'from pydantic import EmailStr'),
            (r'^ BaseModel$', 'from pydantic import BaseModel'),
            (r'^ ConfigDict$', 'from pydantic import ConfigDict'),
            (r'^ field_validator$', 'from pydantic import field_validator'),
            
            # Corregir imports básicos sueltos
            (r'^ logging$', 'import logging'),
            (r'^ os$', 'import os'),
            (r'^ re$', 'import re'),
            (r'^ json$', 'import json'),
            (r'^ time$', 'import time'),
            (r'^ math$', 'import math'),
            (r'^ statistics$', 'import statistics'),
            (r'^ asyncio$', 'import asyncio'),
            (r'^ csv$', 'import csv'),
            (r'^ tempfile$', 'import tempfile'),
            (r'^ traceback$', 'import traceback'),
            (r'^ hmac$', 'import hmac'),
            (r'^ platform$', 'import platform'),
            (r'^ subprocess$', 'import subprocess'),
            (r'^ pickle$', 'import pickle'),
            (r'^ inspect$', 'import inspect'),
            (r'^ io$', 'import io'),
            (r'^ uuid$', 'import uuid'),
            (r'^ random$', 'import random'),
            (r'^ string$', 'import string'),
            (r'^ itertools$', 'import itertools'),
            (r'^ functools$', 'import functools'),
            (r'^ collections$', 'import collections'),
            (r'^ operator$', 'import operator'),
            (r'^ pathlib$', 'import pathlib'),
            (r'^ shutil$', 'import shutil'),
            (r'^ glob$', 'import glob'),
            (r'^ fnmatch$', 'import fnmatch'),
            (r'^ hashlib$', 'import hashlib'),
            (r'^ base64$', 'import base64'),
            (r'^ urllib$', 'import urllib'),
            (r'^ requests$', 'import requests'),
            (r'^ numpy as np$', 'import numpy as np'),
            (r'^ pandas as pd$', 'import pandas as pd'),
            
            # Corregir imports de librerías externas sueltos
            (r'^ Font$', 'from openpyxl.styles import Font'),
            (r'^ PatternFill$', 'from openpyxl.styles import PatternFill'),
            (r'^ Alignment$', 'from openpyxl.styles import Alignment'),
            (r'^ inch$', 'from reportlab.lib.units import inch'),
            (r'^ letter$', 'from reportlab.lib.pagesizes import letter'),
            (r'^ A4$', 'from reportlab.lib.pagesizes import A4'),
            (r'^ canvas$', 'from reportlab.pdfgen import canvas'),
            (r'^ SimpleDocTemplate$', 'from reportlab.platypus import SimpleDocTemplate'),
            (r'^ Paragraph$', 'from reportlab.platypus import Paragraph'),
            (r'^ Spacer$', 'from reportlab.platypus import Spacer'),
            (r'^ Table$', 'from reportlab.platypus import Table'),
            (r'^ TableStyle$', 'from reportlab.platypus import TableStyle'),
            (r'^ Process$', 'from psutil import Process'),
            (r'^ Limiter$', 'from slowapi import Limiter'),
            (r'^ _rate_limit_exceeded_handler$', 'from slowapi import _rate_limit_exceeded_handler'),
            (r'^ get_remote_address$', 'from slowapi.util import get_remote_address'),
            (r'^ RateLimitExceeded$', 'from slowapi.errors import RateLimitExceeded'),
            (r'^ jwt$', 'import jwt'),
            (r'^ JWTError$', 'from jose import JWTError'),
            
            # Corregir imports de psutil sueltos
            (r'^ psutil$', 'import psutil'),
        ]
        
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            fixed_line = line
            
            # Aplicar correcciones
            for pattern, replacement in fixes:
                if re.match(pattern, line.strip()):
                    fixed_line = replacement
                    break
            
            fixed_lines.append(fixed_line)
        
        # Unir las líneas y escribir de vuelta
        fixed_content = '\n'.join(fixed_lines)
        
        # Solo escribir si hay cambios
        if fixed_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error procesando {file_path}: {e}")
        return False

def main():
    """Función principal"""
    base_dir = 'app'
    fixed_files = 0
    
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_indentation_errors(file_path):
                    print(f"Corregido: {file_path}")
                    fixed_files += 1
    
    print(f"\nTotal de archivos corregidos: {fixed_files}")

if __name__ == "__main__":
    main()
