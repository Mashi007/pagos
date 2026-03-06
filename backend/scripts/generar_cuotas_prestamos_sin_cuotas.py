#!/usr/bin/env python3
"""
Genera cuotas (tabla de amortización) para préstamos que no tienen ninguna.
Útil para los 74 préstamos que se pasaron de DRAFT a APROBADO solo con UPDATE en BD.

Uso (desde la raíz del repo o desde backend/):
  cd backend && python -m scripts.generar_cuotas_prestamos_sin_cuotas
  cd backend && python scripts/generar_cuotas_prestamos_sin_cuotas.py
"""
import os
import sys
from datetime import date

# Asegurar que el backend esté en el path
_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from sqlalchemy import select, func
from app.core.database import SessionLocal
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.api.v1.endpoints.prestamos import _generar_cuotas_amortizacion, _resolver_monto_cuota


def main(dry_run: bool = False):
    db = SessionLocal()
    try:
        # Préstamos que tienen 0 cuotas (subconsulta por prestamo_id)
        subq = select(Cuota.prestamo_id, func.count().label("n")).group_by(Cuota.prestamo_id).subquery()
        rows = db.execute(
            select(Prestamo.id)
            .select_from(Prestamo)
            .outerjoin(subq, Prestamo.id == subq.c.prestamo_id)
            .where((subq.c.n.is_(None)) | (subq.c.n == 0))
        ).all()
        ids_sin_cuotas = [r[0] for r in rows]

        if not ids_sin_cuotas:
            print("No hay préstamos sin cuotas. Nada que hacer.")
            return

        print(f"Préstamos sin cuotas: {len(ids_sin_cuotas)}")
        if dry_run:
            print("(Modo dry-run: no se escriben cambios)")
            for pid in ids_sin_cuotas:
                print(f"  - préstamo_id {pid}")
            return

        ok = 0
        err = 0
        for pid in ids_sin_cuotas:
            p = db.get(Prestamo, pid)
            if not p:
                print(f"  Préstamo {pid}: no encontrado")
                err += 1
                continue
            numero_cuotas = p.numero_cuotas or 12
            total_fin = float(p.total_financiamiento or 0)
            if numero_cuotas <= 0 or total_fin <= 0:
                print(f"  Préstamo {pid}: numero_cuotas o total_financiamiento inválido, se omite")
                err += 1
                continue
            try:
                monto_cuota = _resolver_monto_cuota(p, total_fin, numero_cuotas)
                fecha_base = None
                if getattr(p, "fecha_aprobacion", None):
                    fecha_base = getattr(p.fecha_aprobacion, "date", lambda: p.fecha_aprobacion)()
                elif getattr(p, "fecha_registro", None):
                    fecha_base = getattr(p.fecha_registro, "date", lambda: p.fecha_registro)()
                if fecha_base is None:
                    fecha_base = date.today()
                if hasattr(fecha_base, "date") and callable(getattr(fecha_base, "date", None)):
                    fecha_base = fecha_base.date()
                n_creadas = _generar_cuotas_amortizacion(db, p, fecha_base, numero_cuotas, monto_cuota)
                print(f"  Préstamo {pid}: {n_creadas} cuotas generadas")
                ok += 1
            except Exception as e:
                print(f"  Préstamo {pid}: error - {e}")
                err += 1
        db.commit()
        print(f"\nListo: {ok} préstamos con cuotas generadas, {err} errores.")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generar cuotas para préstamos que no tienen.")
    parser.add_argument("--dry-run", action="store_true", help="Solo listar préstamos sin cuotas, no escribir")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
