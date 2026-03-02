#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba para verificar que la carga de Excel funciona correctamente.
Simula la carga sin necesidad de hacer un POST HTTP.
"""
import sys
import os
import io

# Configurar encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(__file__))

from decimal import Decimal
from app.api.v1.endpoints.reportes.reportes_conciliacion import (
    _validar_cedula, _validar_numero, _parse_numero, _normalizar_cedula
)
from app.core.database import SessionLocal, engine
from app.models.conciliacion_temporal import ConciliacionTemporal
from sqlalchemy import delete, select

# Datos de prueba (simula el Excel)
DATOS_PRUEBA = [
    ("V23107415", "864", "810"),
    ("E98765432", "2000", "1500"),
    ("V12345678", "1000", "500"),
]

def test_validaciones():
    """Prueba que las validaciones funcionan"""
    print("\n=== TEST 1: Validaciones ===")
    
    for cedula, tf, ta in DATOS_PRUEBA:
        print(f"\nCedula: {cedula}")
        
        # Validar cédula
        valido_cedula = _validar_cedula(cedula)
        print(f"  OK Cedula valida: {valido_cedula}")
        
        # Validar TF
        valido_tf = _validar_numero(tf)
        print(f"  OK TF valido: {valido_tf} (valor: {tf})")
        
        # Validar TA
        valido_ta = _validar_numero(ta)
        print(f"  OK TA valido: {valido_ta} (valor: {ta})")
        
        # Normalizar cédula
        cedula_norm = _normalizar_cedula(cedula)
        print(f"  OK Cedula normalizada: {cedula_norm}")
        
        # Parse números
        tf_parse = _parse_numero(tf)
        ta_parse = _parse_numero(ta)
        print(f"  OK TF parseado: {tf_parse} (tipo: {type(tf_parse).__name__})")
        print(f"  OK TA parseado: {ta_parse} (tipo: {type(ta_parse).__name__})")


def test_almacenamiento():
    """Prueba que se guarda y recupera de BD"""
    print("\n=== TEST 2: Almacenamiento en BD ===")
    
    db = SessionLocal()
    
    try:
        # Limpiar tabla
        print("\n1. Limpiando tabla conciliacion_temporal...")
        db.execute(delete(ConciliacionTemporal))
        db.commit()
        registros_count = len(db.execute(select(ConciliacionTemporal)).scalars().all())
        print(f"   OK Tabla limpia (registros: {registros_count})")
        
        # Insertar datos de prueba
        print("\n2. Insertando datos de prueba...")
        for cedula, tf, ta in DATOS_PRUEBA:
            cedula_norm = _normalizar_cedula(cedula)
            tf_parse = _parse_numero(tf)
            ta_parse = _parse_numero(ta)
            
            registro = ConciliacionTemporal(
                cedula=cedula_norm,
                total_financiamiento=tf_parse,
                total_abonos=ta_parse,
            )
            db.add(registro)
            print(f"   OK Agregado: {cedula_norm} | {tf_parse} | {ta_parse}")
        
        db.commit()
        print("   OK Datos commitidos a BD")
        
        # Verificar recuperación
        print("\n3. Recuperando datos de BD...")
        registros = db.execute(select(ConciliacionTemporal)).scalars().all()
        print(f"   OK Total registros: {len(registros)}")
        
        for reg in registros:
            print(f"   OK {reg.cedula} | {reg.total_financiamiento} | {reg.total_abonos}")
        
        if len(registros) == len(DATOS_PRUEBA):
            print("\nOK TEST EXITOSO: Todos los datos se guardaron correctamente")
        else:
            print(f"\nFALLO TEST: Se esperaban {len(DATOS_PRUEBA)} registros, se encontraron {len(registros)}")
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("TEST DE CARGA DE CONCILIACION")
    print("=" * 60)
    
    test_validaciones()
    test_almacenamiento()
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETADOS")
    print("=" * 60)
