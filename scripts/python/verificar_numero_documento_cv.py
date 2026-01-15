#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verificar si todos los pagos tienen numero_documento que comienza con CV"""

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
    print("VERIFICACION: NUMERO DE DOCUMENTO QUE COMIENZA CON 'CV'")
    print("="*80)
    
    # 1. Total de pagos
    query_total = text("SELECT COUNT(*) FROM pagos")
    result_total = db.execute(query_total)
    total_pagos = result_total.scalar()
    
    print(f"\nTotal de pagos en la tabla: {total_pagos:,}")
    
    # 2. Pagos con numero_documento que comienza con 'CV'
    query_cv = text("""
        SELECT COUNT(*) 
        FROM pagos 
        WHERE numero_documento LIKE 'CV%'
    """)
    result_cv = db.execute(query_cv)
    pagos_con_cv = result_cv.scalar()
    
    # 3. Pagos con numero_documento NULL
    query_null = text("""
        SELECT COUNT(*) 
        FROM pagos 
        WHERE numero_documento IS NULL
    """)
    result_null = db.execute(query_null)
    pagos_null = result_null.scalar()
    
    # 4. Pagos con numero_documento que NO comienza con 'CV'
    query_no_cv = text("""
        SELECT COUNT(*) 
        FROM pagos 
        WHERE numero_documento IS NOT NULL 
          AND numero_documento NOT LIKE 'CV%'
    """)
    result_no_cv = db.execute(query_no_cv)
    pagos_sin_cv = result_no_cv.scalar()
    
    # 5. Ejemplos de pagos que NO comienzan con CV (si existen)
    query_ejemplos = text("""
        SELECT DISTINCT numero_documento 
        FROM pagos 
        WHERE numero_documento IS NOT NULL 
          AND numero_documento NOT LIKE 'CV%'
        LIMIT 10
    """)
    result_ejemplos = db.execute(query_ejemplos)
    ejemplos = result_ejemplos.fetchall()
    
    print(f"\nPagos con numero_documento que comienza con 'CV': {pagos_con_cv:,}")
    print(f"Pagos con numero_documento NULL: {pagos_null:,}")
    print(f"Pagos con numero_documento que NO comienza con 'CV': {pagos_sin_cv:,}")
    
    # 6. Verificación
    print("\n" + "-"*80)
    if pagos_sin_cv == 0 and pagos_null == 0:
        print("[CONFIRMACION] SI: Todos los pagos tienen numero_documento que comienza con 'CV'")
        print(f"Total verificado: {pagos_con_cv:,} de {total_pagos:,} pagos")
    else:
        print("[CONFIRMACION] NO: No todos los pagos tienen numero_documento que comienza con 'CV'")
        if pagos_null > 0:
            print(f"  - Pagos con numero_documento NULL: {pagos_null:,}")
        if pagos_sin_cv > 0:
            print(f"  - Pagos con numero_documento que NO comienza con 'CV': {pagos_sin_cv:,}")
            if ejemplos:
                print("\nEjemplos de numero_documento que NO comienza con 'CV':")
                for ejemplo in ejemplos:
                    print(f"  - '{ejemplo[0]}'")
    
    print("\n" + "="*80)
    
finally:
    db.close()
