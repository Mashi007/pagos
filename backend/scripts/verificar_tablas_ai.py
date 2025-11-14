#!/usr/bin/env python3
"""Verificar si las tablas de AI training existen"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
inspector = inspect(engine)
tablas = ['conversaciones_ai', 'fine_tuning_jobs', 'documento_ai_embeddings', 'modelos_riesgo']
existentes = inspector.get_table_names()

print('Tablas de AI Training:')
for t in tablas:
    estado = 'SI' if t in existentes else 'NO'
    print(f'  {t}: {estado}')

