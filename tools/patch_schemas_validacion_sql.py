from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_schemas() -> None:
    path = ROOT / "backend" / "app" / "schemas" / "pago.py"
    text = path.read_text(encoding="utf-8")
    if "moneda_registro" in text:
        print("schemas ok")
        return
    needle = "    cuotas_atrasadas: Optional[int] = None  # calculado en listado"
    if needle not in text:
        raise SystemExit("schemas needle missing")
    text = text.replace(
        needle,
        needle
        + "\n    moneda_registro: Optional[str] = None\n"
        "    monto_bs_original: Optional[Decimal] = None\n"
        "    tasa_cambio_bs_usd: Optional[Decimal] = None\n"
        "    fecha_tasa_referencia: Optional[date] = None",
        1,
    )
    path.write_text(text, encoding="utf-8")
    print("schemas patched")


def patch_validacion() -> None:
    path = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "tasa_cambio_validacion.py"
    text = path.read_text(encoding="utf-8")
    if "fecha_pago: Optional[date] = Query" in text:
        print("validacion ok")
        return
    if "from datetime import date" not in text:
        text = text.replace(
            "# -*- coding: utf-8 -*-\n",
            "# -*- coding: utf-8 -*-\nfrom datetime import date\n",
            1,
        )
    if "from typing import Optional" not in text:
        text = text.replace("from datetime import date\n", "from datetime import date\nfrom typing import Optional\n", 1)

    text = text.replace(
        "from fastapi import APIRouter, Depends, HTTPException\n",
        "from fastapi import APIRouter, Depends, HTTPException, Query\n",
        1,
    )
    text = text.replace(
        "from app.services.tasa_cambio_service import obtener_tasa_hoy, debe_ingresar_tasa\n",
        "from app.services.tasa_cambio_service import (\n"
        "    obtener_tasa_hoy,\n"
        "    obtener_tasa_por_fecha,\n"
        "    debe_ingresar_tasa,\n"
        "    fecha_hoy_caracas,\n"
        ")\n",
        1,
    )
    old = """def validar_tasa_para_pago(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
"""
    new = """def validar_tasa_para_pago(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
    fecha_pago: Optional[date] = Query(
        None,
        description="Fecha de pago del reporte; valida tasa en tasas_cambio_diaria para esa fecha (Bs).",
    ),
):
"""
    if old not in text:
        raise SystemExit("validar sig not found")
    text = text.replace(old, new, 1)

    old_body = """    tasa = obtener_tasa_hoy(db)
    debe_ingresar = debe_ingresar_tasa()
    
    # Caso 1: Tasa existe y estamos en horario de ingreso
    if tasa:
"""
    new_body = """    debe_ingresar = debe_ingresar_tasa()
    if fecha_pago is not None:
        tasa = obtener_tasa_por_fecha(db, fecha_pago)
    else:
        tasa = obtener_tasa_hoy(db)

    # Caso 1: Tasa existe para la fecha de pago indicada o para hoy (Caracas)
    if tasa:
"""
    if old_body not in text:
        raise SystemExit("validar body not found")
    text = text.replace(old_body, new_body, 1)

    path.write_text(text, encoding="utf-8")
    print("validacion patched")


def write_sql() -> None:
    path = ROOT / "sql" / "2026-03-21_pagos_moneda_tasa_bs.sql"
    if path.exists():
        print("sql exists", path)
        return
    path.write_text(
        """-- Pagos: auditoria moneda / tasa Bs->USD (fecha de pago = clave en tasas_cambio_diaria)
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS moneda_registro VARCHAR(10);
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS monto_bs_original NUMERIC(15, 2);
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS tasa_cambio_bs_usd NUMERIC(15, 6);
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS fecha_tasa_referencia DATE;
COMMENT ON COLUMN pagos.monto_pagado IS 'Monto en USD para cartera; si moneda_registro=BS, convertido con tasa del dia fecha_tasa_referencia.';
""",
        encoding="utf-8",
    )
    print("wrote", path)


if __name__ == "__main__":
    patch_schemas()
    patch_validacion()
    write_sql()
