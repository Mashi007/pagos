"""
Actualiza la tabla de amortizacion (cuotas) de prestamos MENSUAL cuya
fecha de vencimiento no sigue la regla "mismo dia cada mes".

Uso (desde backend, con venv activo):
  python actualizar_amortizacion_mensual.py [--dry-run] [--limit N]

  --dry-run: solo lista prestamos a actualizar, no borra ni regenera.
  --limit N: procesa como maximo N prestamos (default: todos).
"""
import argparse
import os
import sys
from datetime import date
from decimal import Decimal

# Anadir app al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.cuota import Cuota
from app.models.prestamo import Prestamo


def _fecha_base_mas_meses(fecha_base: date, meses: int) -> date:
    import calendar
    if meses <= 0:
        return fecha_base
    year = fecha_base.year + (fecha_base.month + meses - 1) // 12
    month = (fecha_base.month + meses - 1) % 12 + 1
    _, ultimo_dia = calendar.monthrange(year, month)
    day = min(fecha_base.day, ultimo_dia)
    return date(year, month, day)


def _resolver_monto_cuota(prestamo: Prestamo, total: float, numero_cuotas: int) -> float:
    from app.api.v1.endpoints.prestamos import _resolver_monto_cuota as resolver
    return float(resolver(prestamo, total, numero_cuotas))


def _generar_cuotas_amortizacion(db: Session, p: Prestamo, fecha_base: date, numero_cuotas: int, monto_cuota: float) -> int:
    from app.api.v1.endpoints.prestamos import _generar_cuotas_amortizacion as generar
    return generar(db, p, fecha_base, numero_cuotas, monto_cuota)


def prestamos_mensual_desactualizados(db: Session):
    """Ids de prestamos MENSUAL con al menos una cuota con vencimiento incorrecto."""
    r = db.execute(text("""
        WITH base AS (
          SELECT
            p.id AS prestamo_id,
            COALESCE((p.fecha_aprobacion)::date, p.fecha_base_calculo) AS fecha_base
          FROM prestamos p
          WHERE UPPER(TRIM(COALESCE(p.modalidad_pago, ''))) = 'MENSUAL'
            AND (p.fecha_aprobacion IS NOT NULL OR p.fecha_base_calculo IS NOT NULL)
        ),
        expected AS (
          SELECT
            b.prestamo_id,
            c.numero_cuota,
            c.fecha_vencimiento AS actual_vencimiento,
            (b.fecha_base + (c.numero_cuota || ' months')::interval)::date AS esperado_vencimiento
          FROM base b
          JOIN cuotas c ON c.prestamo_id = b.prestamo_id
        )
        SELECT DISTINCT prestamo_id
        FROM expected
        WHERE actual_vencimiento <> esperado_vencimiento
        ORDER BY prestamo_id
    """))
    return [row[0] for row in r.fetchall()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Solo listar, no modificar BD")
    ap.add_argument("--limit", type=int, default=None, help="Maximo numero de prestamos a actualizar")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        ids = prestamos_mensual_desactualizados(db)
        if args.limit is not None:
            ids = ids[: args.limit]
        if not ids:
            print("No hay prestamos MENSUAL con cuotas desactualizadas.")
            return

        print(f"Prestamos MENSUAL con cuotas a actualizar: {len(ids)}")
        if args.dry_run:
            print("IDs:", ids[:20], "..." if len(ids) > 20 else "")
            return

        for prestamo_id in ids:
            p = db.get(Prestamo, prestamo_id)
            if not p:
                continue
            # Regla obligatoria: tabla de amortización solo con fecha de aprobación
            fecha_base = None
            if getattr(p, "fecha_aprobacion", None):
                fa = p.fecha_aprobacion
                fecha_base = fa.date() if hasattr(fa, "date") else fa
            if fecha_base is None:
                print(f"  Prestamo {prestamo_id}: sin fecha_aprobacion, se omite (obligatoria para amortización).")
                continue

            numero_cuotas = p.numero_cuotas or 12
            total = float(p.total_financiamiento or 0)
            if numero_cuotas <= 0 or total <= 0:
                print(f"  Prestamo {prestamo_id}: numero_cuotas o total invalido, se omite.")
                continue

            db.execute(delete(Cuota).where(Cuota.prestamo_id == prestamo_id))
            monto_cuota = _resolver_monto_cuota(p, total, numero_cuotas)
            creadas = _generar_cuotas_amortizacion(db, p, fecha_base, numero_cuotas, monto_cuota)
            print(f"  Prestamo {prestamo_id}: {creadas} cuotas regeneradas (fecha_base={fecha_base}).")

        db.commit()
        print("Listo.")
    except Exception as e:
        db.rollback()
        print("Error:", e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
