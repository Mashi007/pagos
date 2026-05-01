"""
Elimina filas de `pagos` con estado ANULADO_IMPORT.

Por defecto solo borra pagos **sin** filas en `cuota_pagos`, para no romper cartera.

Muchos ANULADO_IMPORT pueden tener aplicaciones históricas en `cuota_pagos`; borrar esos
pagos CASCADE eliminaría esas filas y desajustaría cuotas. Por eso el modo que incluye
esos registros requiere `--incluir-con-aplicacion-cuotas`.

En modelos SQLAlchemy, `cuota_pagos` y tablas de auditoría referencian `pagos.id`
con ON DELETE CASCADE; `cuotas.pago_id` y `pagos_gmail_abcd_cuotas_traza.pago_id`
usan SET NULL.

Uso (desde carpeta backend, con .env cargado):

  python eliminar_pagos_anulado_import.py              # solo cuenta (dry-run)
  python eliminar_pagos_anulado_import.py --execute    # borra solo sin cuota_pagos
  python eliminar_pagos_anulado_import.py --execute --incluir-con-aplicacion-cuotas
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Raíz backend (este archivo vive en backend/)
_BACKEND_ROOT = Path(__file__).resolve().parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

load_dotenv(_BACKEND_ROOT / ".env")

from sqlalchemy import delete, exists, func, not_, select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models.cuota_pago import CuotaPago  # noqa: E402
from app.models.pago import Pago  # noqa: E402

ESTADO = "ANULADO_IMPORT"


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Borrar pagos con estado {ESTADO}.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Ejecutar DELETE y COMMIT. Sin este flag solo muestra conteos.",
    )
    parser.add_argument(
        "--incluir-con-aplicacion-cuotas",
        action="store_true",
        help=(
            "Incluir pagos ANULADO_IMPORT que tienen filas en cuota_pagos (peligroso: CASCADE "
            "borra aplicaciones y puede desajustar cartera)."
        ),
    )
    args = parser.parse_args()

    url_preview = (settings.DATABASE_URL or "")[:60]
    print(f"BD (preview): {url_preview}...")
    db = SessionLocal()
    try:
        n_total = db.execute(
            select(func.count()).select_from(Pago).where(Pago.estado == ESTADO)
        ).scalar()
        n_total = int(n_total or 0)
        print(f"Filas con estado={ESTADO!r}: {n_total}")

        tiene_cp = exists(select(CuotaPago.id).where(CuotaPago.pago_id == Pago.id))
        n_con_cuotas = db.execute(
            select(func.count()).select_from(Pago).where(Pago.estado == ESTADO, tiene_cp)
        ).scalar()
        n_con_cuotas = int(n_con_cuotas or 0)
        n_sin_cuotas = n_total - n_con_cuotas
        print(f"  Con filas en cuota_pagos: {n_con_cuotas}")
        print(f"  Sin filas en cuota_pagos: {n_sin_cuotas}")

        if n_con_cuotas and not args.incluir_con_aplicacion_cuotas:
            print(
                "Por defecto NO se borrarán los que tienen cuota_pagos. "
                "Use --incluir-con-aplicacion-cuotas si asume el riesgo (revisar cartera después)."
            )

        if not args.execute:
            print("Dry-run: no se borró nada. Use --execute para aplicar DELETE.")
            return 0

        if n_total == 0:
            print("Nada que borrar.")
            return 0

        cond_estado = Pago.estado == ESTADO
        if args.incluir_con_aplicacion_cuotas:
            where_del = cond_estado
        else:
            where_del = cond_estado & (not_(tiene_cp))

        deleted = db.execute(delete(Pago).where(where_del)).rowcount
        db.commit()
        modo = "todos ANULADO_IMPORT" if args.incluir_con_aplicacion_cuotas else "solo sin cuota_pagos"
        print(f"DELETE ({modo}); filas borradas (reportado por driver): {deleted}")
        return 0
    except Exception as e:
        db.rollback()
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
