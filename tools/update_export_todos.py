# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
t = p.read_text(encoding="utf-8")

old = '''@router.get("/export/excel/pagos-sin-aplicar-cuotas")
def export_excel_pagos_sin_aplicar_cuotas(
    cohorte: str = Query(
        "fifo",
        description="fifo: cola tipo job (sin cuota_pagos, monto>0, prestamo_id, no ANULADO_IMPORT). "
        "sin_cupo: mismos filtros y ademas sin cupo aplicable en cuotas PENDIENTE/MORA/PARCIAL.",
    ),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Descarga Excel con pagos que aun no tienen filas en cuota_pagos.
    Requiere autenticacion. Maximo 50000 filas.
    """
    c = (cohorte or "fifo").strip().lower()
    if c not in ("fifo", "sin_cupo"):
        raise HTTPException(status_code=400, detail="cohorte debe ser fifo o sin_cupo")

    import openpyxl

    tiene_cuota_pago = exists(select(CuotaPago.id).where(CuotaPago.pago_id == Pago.id))
    cond_base = and_(
        ~tiene_cuota_pago,
        func.coalesce(Pago.monto_pagado, 0) > 0,
        func.upper(func.coalesce(Pago.estado, "")) != "ANULADO_IMPORT",
        Pago.prestamo_id.isnot(None),
    )
    if c == "sin_cupo":
        aplicado_en_cuota = (
            select(func.coalesce(func.sum(CuotaPago.monto_aplicado), 0))
            .where(CuotaPago.cuota_id == Cuota.id)
            .correlate(Cuota)
            .scalar_subquery()
        )
        hay_cupo_aplicable = exists(
            select(1)
            .select_from(Cuota)
            .where(
                and_(
                    Cuota.prestamo_id == Pago.prestamo_id,
                    Cuota.estado.in_(["PENDIENTE", "MORA", "PARCIAL"]),
                    (func.coalesce(Cuota.monto, 0) - aplicado_en_cuota) > 0.01,
                )
            )
        )
        cond_final = and_(cond_base, ~hay_cupo_aplicable)
    else:
        cond_final = cond_base

    rows = (
        db.execute(
            select(Pago)
            .where(cond_final)
            .order_by(Pago.fecha_registro.asc(), Pago.id.asc())
            .limit(50000)
        )
        .scalars()
        .all()
    )'''

new = '''@router.get("/export/excel/pagos-sin-aplicar-cuotas")
def export_excel_pagos_sin_aplicar_cuotas(
    cohorte: str = Query(
        "todos",
        description="todos (default): sin ninguna fila en cuota_pagos (no aplicados a cuotas). "
        "fifo: ademas monto>0, prestamo_id, no ANULADO_IMPORT (cola del job). "
        "sin_cupo: como fifo y sin cupo aplicable en cuotas PENDIENTE/MORA/PARCIAL.",
    ),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """
    Descarga Excel con pagos que no tienen aplicacion a cuotas (sin filas en cuota_pagos).
    Por defecto cohorte=todos incluye todos esos pagos. Requiere autenticacion. Maximo 200000 filas.
    """
    c = (cohorte or "todos").strip().lower()
    if c not in ("todos", "fifo", "sin_cupo"):
        raise HTTPException(status_code=400, detail="cohorte debe ser todos, fifo o sin_cupo")

    import openpyxl

    tiene_cuota_pago = exists(select(CuotaPago.id).where(CuotaPago.pago_id == Pago.id))
    if c == "todos":
        cond_final = ~tiene_cuota_pago
    else:
        cond_base = and_(
            ~tiene_cuota_pago,
            func.coalesce(Pago.monto_pagado, 0) > 0,
            func.upper(func.coalesce(Pago.estado, "")) != "ANULADO_IMPORT",
            Pago.prestamo_id.isnot(None),
        )
        if c == "sin_cupo":
            aplicado_en_cuota = (
                select(func.coalesce(func.sum(CuotaPago.monto_aplicado), 0))
                .where(CuotaPago.cuota_id == Cuota.id)
                .correlate(Cuota)
                .scalar_subquery()
            )
            hay_cupo_aplicable = exists(
                select(1)
                .select_from(Cuota)
                .where(
                    and_(
                        Cuota.prestamo_id == Pago.prestamo_id,
                        Cuota.estado.in_(["PENDIENTE", "MORA", "PARCIAL"]),
                        (func.coalesce(Cuota.monto, 0) - aplicado_en_cuota) > 0.01,
                    )
                )
            )
            cond_final = and_(cond_base, ~hay_cupo_aplicable)
        else:
            cond_final = cond_base

    rows = (
        db.execute(
            select(Pago)
            .where(cond_final)
            .order_by(Pago.fecha_registro.asc(), Pago.id.asc())
            .limit(200000)
        )
        .scalars()
        .all()
    )'''

if old not in t:
    raise SystemExit("OLD BLOCK NOT FOUND")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("OK", p)
