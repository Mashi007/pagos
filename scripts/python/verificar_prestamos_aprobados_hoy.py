#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar préstamos aprobados hoy y validar la consulta del AI Chat
"""

import sys
import io
from pathlib import Path
from datetime import datetime, date

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar backend al path para imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import func
from app.db.session import SessionLocal
from app.models.prestamo import Prestamo

def verificar_prestamos_aprobados_hoy():
    """Verifica préstamos aprobados hoy usando diferentes métodos"""
    db = SessionLocal()
    
    try:
        hoy = date.today()
        fecha_actual = datetime.now()
        
        print("=" * 70)
        print("VERIFICACIÓN: PRÉSTAMOS APROBADOS HOY")
        print("=" * 70)
        print(f"Fecha actual del sistema: {fecha_actual.strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"Fecha de hoy (date): {hoy.strftime('%d/%m/%Y')}")
        print()
        
        # Método 1: Usando func.date() (método usado en la consulta dinámica)
        print("📊 MÉTODO 1: Usando func.date() (método del AI Chat)")
        print("-" * 70)
        prestamos_m1 = (
            db.query(Prestamo)
            .filter(
                Prestamo.estado == "APROBADO",
                Prestamo.fecha_aprobacion.isnot(None),
                func.date(Prestamo.fecha_aprobacion) == hoy
            )
            .all()
        )
        print(f"✅ Préstamos encontrados: {len(prestamos_m1)}")
        if prestamos_m1:
            for p in prestamos_m1[:10]:
                print(f"   - ID: {p.id}, Cliente: {p.nombres}, Cédula: {p.cedula}")
                print(f"     Fecha aprobación: {p.fecha_aprobacion}, Monto: {float(p.total_financiamiento or 0):,.2f}")
            if len(prestamos_m1) > 10:
                print(f"   ... y {len(prestamos_m1) - 10} préstamo(s) más")
        print()
        
        # Método 2: Usando datetime.combine() (método anterior)
        print("📊 MÉTODO 2: Usando datetime.combine() (método anterior)")
        print("-" * 70)
        prestamos_m2 = (
            db.query(Prestamo)
            .filter(
                Prestamo.estado == "APROBADO",
                Prestamo.fecha_aprobacion >= datetime.combine(hoy, datetime.min.time()),
                Prestamo.fecha_aprobacion <= datetime.combine(hoy, datetime.max.time()),
            )
            .all()
        )
        print(f"✅ Préstamos encontrados: {len(prestamos_m2)}")
        if prestamos_m2:
            for p in prestamos_m2[:10]:
                print(f"   - ID: {p.id}, Cliente: {p.nombres}, Cédula: {p.cedula}")
                print(f"     Fecha aprobación: {p.fecha_aprobacion}, Monto: {float(p.total_financiamiento or 0):,.2f}")
            if len(prestamos_m2) > 10:
                print(f"   ... y {len(prestamos_m2) - 10} préstamo(s) más")
        print()
        
        # Método 3: Verificar todos los préstamos aprobados recientes
        print("📊 MÉTODO 3: Préstamos aprobados en los últimos 7 días")
        print("-" * 70)
        from datetime import timedelta
        hace_7_dias = hoy - timedelta(days=7)
        prestamos_recientes = (
            db.query(Prestamo)
            .filter(
                Prestamo.estado == "APROBADO",
                Prestamo.fecha_aprobacion.isnot(None),
                func.date(Prestamo.fecha_aprobacion) >= hace_7_dias
            )
            .order_by(Prestamo.fecha_aprobacion.desc())
            .all()
        )
        print(f"✅ Préstamos aprobados en últimos 7 días: {len(prestamos_recientes)}")
        if prestamos_recientes:
            for p in prestamos_recientes[:10]:
                fecha_aprob = p.fecha_aprobacion.date() if p.fecha_aprobacion else None
                es_hoy = fecha_aprob == hoy if fecha_aprob else False
                marcador = "🟢 HOY" if es_hoy else ""
                print(f"   - ID: {p.id}, Cliente: {p.nombres}, Fecha: {fecha_aprob} {marcador}")
        print()
        
        # Resumen
        print("=" * 70)
        print("RESUMEN")
        print("=" * 70)
        print(f"Préstamos aprobados HOY (método func.date()): {len(prestamos_m1)}")
        print(f"Préstamos aprobados HOY (método datetime.combine()): {len(prestamos_m2)}")
        print(f"Préstamos aprobados últimos 7 días: {len(prestamos_recientes)}")
        print()
        
        if len(prestamos_m1) == 0:
            print("⚠️  NO se encontraron préstamos aprobados hoy.")
            print("   Esto confirma que la respuesta del AI es CORRECTA.")
        else:
            print(f"✅ Se encontraron {len(prestamos_m1)} préstamo(s) aprobado(s) hoy.")
            print("   La respuesta del AI debería mostrar estos préstamos.")
        
        # Verificar si hay diferencia entre métodos
        if len(prestamos_m1) != len(prestamos_m2):
            print()
            print("⚠️  DIFERENCIA DETECTADA entre métodos:")
            print(f"   Método func.date(): {len(prestamos_m1)} préstamos")
            print(f"   Método datetime.combine(): {len(prestamos_m2)} préstamos")
            print("   Esto podría indicar un problema con la zona horaria o formato de fecha.")
        
    except Exception as e:
        print(f"❌ Error durante la verificación: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(verificar_prestamos_aprobados_hoy())
