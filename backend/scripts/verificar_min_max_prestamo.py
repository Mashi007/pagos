"""
Script para verificar el préstamo de menor y mayor cuantía en toda la base de datos.
Ejecutar desde la raíz del backend: python -m scripts.verificar_min_max_prestamo
"""
import sys
from pathlib import Path

# Añadir el directorio backend al path para imports
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, func
from app.core.database import SessionLocal
from app.models.prestamo import Prestamo
from app.models.cliente import Cliente


def main():
    db = SessionLocal()
    try:
        # Obtener valores min/max y total
        min_val = db.scalar(select(func.min(Prestamo.total_financiamiento)).select_from(Prestamo)) or 0
        max_val = db.scalar(select(func.max(Prestamo.total_financiamiento)).select_from(Prestamo)) or 0
        total = db.scalar(select(func.count()).select_from(Prestamo)) or 0

        # Préstamos de menor cuantía
        q_min = (
            select(Prestamo, Cliente.nombres, Cliente.cedula)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Prestamo.total_financiamiento == min_val)
        )
        rows_min = db.execute(q_min).all()

        # Préstamos de mayor cuantía
        q_max = (
            select(Prestamo, Cliente.nombres, Cliente.cedula)
            .join(Cliente, Prestamo.cliente_id == Cliente.id)
            .where(Prestamo.total_financiamiento == max_val)
        )
        rows_max = db.execute(q_max).all()

        print("=" * 70)
        print("VERIFICACIÓN: PRÉSTAMO DE MENOR Y MAYOR CUANTÍA")
        print("=" * 70)
        print(f"Total de préstamos en BD: {total}")
        print()

        if total == 0:
            print("No hay préstamos en la base de datos.")
            return
        print()

        print("--- MENOR CUANTÍA ---")
        print(f"Monto mínimo: ${float(min_val):,.2f}")
        if rows_min:
            for row in rows_min:
                p, nombres, cedula = row[0], row[1], row[2]
                print(f"  ID: {p.id} | Cuantía: ${float(p.total_financiamiento):,.2f} | Cliente: {nombres} ({cedula}) | Estado: {p.estado}")
        else:
            print("  No hay préstamos")
        print()

        print("--- MAYOR CUANTÍA ---")
        print(f"Monto máximo: ${float(max_val):,.2f}")
        if rows_max:
            for row in rows_max:
                p, nombres, cedula = row[0], row[1], row[2]
                print(f"  ID: {p.id} | Cuantía: ${float(p.total_financiamiento):,.2f} | Cliente: {nombres} ({cedula}) | Estado: {p.estado}")
        else:
            print("  No hay préstamos")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()
