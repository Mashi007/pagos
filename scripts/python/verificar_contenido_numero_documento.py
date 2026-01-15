#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificar el contenido real del campo numero_documento"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text
from app.db.session import SessionLocal

db = SessionLocal()
try:
    print("="*80)
    print("VERIFICACION: CONTENIDO DEL CAMPO numero_documento")
    print("="*80)
    
    # Verificar valores distintos de numero_documento
    query_distintos = text("""
        SELECT DISTINCT numero_documento 
        FROM pagos 
        WHERE numero_documento IS NOT NULL
        ORDER BY numero_documento
        LIMIT 20
    """)
    result_distintos = db.execute(query_distintos)
    distintos = result_distintos.fetchall()
    
    print(f"\nEjemplos de valores distintos en numero_documento (primeros 20):")
    print("-" * 80)
    for i, row in enumerate(distintos, 1):
        print(f"{i:2}. {row[0]}")
    
    # Verificar si hay algún patrón CV
    query_cv = text("""
        SELECT COUNT(*) 
        FROM pagos 
        WHERE numero_documento LIKE '%CV%'
    """)
    result_cv = db.execute(query_cv)
    contiene_cv = result_cv.scalar()
    
    print(f"\nPagos con numero_documento que contiene 'CV' (en cualquier parte): {contiene_cv:,}")
    
    # Verificar referencia_pago
    query_ref = text("""
        SELECT DISTINCT referencia_pago 
        FROM pagos 
        WHERE referencia_pago IS NOT NULL
        ORDER BY referencia_pago
        LIMIT 10
    """)
    result_ref = db.execute(query_ref)
    refs = result_ref.fetchall()
    
    print(f"\nEjemplos de valores distintos en referencia_pago (primeros 10):")
    print("-" * 80)
    for i, row in enumerate(refs, 1):
        print(f"{i:2}. {row[0]}")
    
    print("\n" + "="*80)
    
finally:
    db.close()
