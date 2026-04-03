#!/usr/bin/env python3
"""
Correccion puntual de un pago mal cargado como USD cuando el comprobante es en Bs.

- Lee pagos.fecha_pago, busca tasas_cambio_diaria.tasa_oficial para esa fecha.
- Con --monto-bs (monto en bolivares del comprobante) calcula:
    monto_pagado = round(monto_bs / tasa_oficial, 2)
- Actualiza: moneda_registro='BS', monto_bs_original, tasa_cambio_bs_usd, monto_pagado.

Por defecto solo imprime (dry-run). Use --apply para hacer COMMIT.

Tras corregir todos los pagos de un prestamo, reaplique cascada (solo pagos conciliados / verificado SI):
  POST /api/v1/prestamos/{id}/reaplicar-cascada-aplicacion (admin)
o script alternativo que aplica todos los pagos con monto>0:
  python scripts/rearticular_prestamo_fifo.py <prestamo_id>

Uso (desde carpeta backend, con DATABASE_URL / .env):
  python scripts/corregir_pago_bs_y_usd_desde_tasa.py --pago-id 59822 --monto-bs 4727259.12
  python scripts/corregir_pago_bs_y_usd_desde_tasa.py --pago-id 59822 --monto-bs 4727259.12 --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal, ROUND_HALF_UP

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

env_path = os.path.join(os.path.dirname(BACKEND), ".env")
if os.path.isfile(env_path):
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Corregir pago BS mal registrado como USD (usa tasa del dia).")
    ap.add_argument("--pago-id", type=int, required=True)
    ap.add_argument(
        "--monto-bs",
        type=str,
        required=True,
        help="Monto en bolivares del comprobante (ej. 4727259.12). Punto como decimal.",
    )
    ap.add_argument("--apply", action="store_true", help="Persistir cambios (sin esto solo muestra dry-run).")
    args = ap.parse_args()

    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models.pago import Pago
    from app.models.tasa_cambio_diaria import TasaCambioDiaria

    monto_bs = Decimal(str(args.monto_bs).replace(",", "."))
    if monto_bs <= 0:
        print("monto-bs debe ser positivo", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        pago = db.get(Pago, args.pago_id)
        if not pago:
            print(f"No existe pago id={args.pago_id}", file=sys.stderr)
            return 1

        fp = pago.fecha_pago
        if fp is None:
            print("pago sin fecha_pago", file=sys.stderr)
            return 1
        fecha = fp.date() if hasattr(fp, "date") else fp

        trow = db.execute(select(TasaCambioDiaria).where(TasaCambioDiaria.fecha == fecha)).scalar_one_or_none()
        if not trow or trow.tasa_oficial is None or Decimal(str(trow.tasa_oficial)) <= 0:
            print(
                f"No hay tasa_oficial en tasas_cambio_diaria para fecha={fecha}. "
                "Cargue la tasa antes de corregir el pago.",
                file=sys.stderr,
            )
            return 1

        tasa = Decimal(str(trow.tasa_oficial))
        usd = (monto_bs / tasa).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        print("--- Antes ---")
        print(
            f"  pago_id={pago.id} prestamo_id={pago.prestamo_id} fecha_pago={fp} fecha_tasa={fecha}\n"
            f"  moneda_registro={pago.moneda_registro!r} monto_pagado={pago.monto_pagado}\n"
            f"  monto_bs_original={pago.monto_bs_original} tasa_cambio_bs_usd={pago.tasa_cambio_bs_usd}\n"
            f"  numero_documento={pago.numero_documento!r}"
        )
        print("--- Propuesto ---")
        print(f"  monto_bs={monto_bs} tasa_oficial(dia)={tasa} -> monto_pagado_usd={usd}")
        print("  moneda_registro='BS' monto_bs_original y tasa_cambio_bs_usd alineados con tabla diaria")

        if not args.apply:
            print("\n(dry-run; sin --apply no se escribe en BD)")
            return 0

        pago.moneda_registro = "BS"
        pago.monto_bs_original = monto_bs
        pago.tasa_cambio_bs_usd = tasa
        pago.monto_pagado = usd
        db.commit()
        print("\nOK: cambios guardados. Luego reaplique cascada del prestamo si corresponde.")
        return 0
    except Exception as e:
        db.rollback()
        print(str(e), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
