"""One-off patch: sync aplicar_pagos + estado cuenta. Run from repo root: python scripts/patch_estado_cuenta_sync.py"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_pagos() -> None:
    p = ROOT / "backend/app/api/v1/endpoints/pagos.py"
    text = p.read_text(encoding="utf-8")
    old = """    subq = select(CuotaPago.pago_id).where(CuotaPago.pago_id.isnot(None)).distinct()
    rows = db.execute(
        select(Pago).where(
            Pago.prestamo_id == prestamo_id,
            Pago.conciliado == True,
            Pago.monto_pagado > 0,
            ~Pago.id.in_(subq),
        )
    ).scalars().all()"""
    new = """    subq = select(CuotaPago.pago_id).where(CuotaPago.pago_id.isnot(None)).distinct()
    # Mismo criterio que get_cuotas_prestamo: conciliado O verificado_concordancia SI.
    rows = db.execute(
        select(Pago).where(
            Pago.prestamo_id == prestamo_id,
            or_(
                Pago.conciliado.is_(True),
                func.coalesce(func.upper(func.trim(Pago.verificado_concordancia)), "") == "SI",
            ),
            Pago.monto_pagado > 0,
            ~Pago.id.in_(subq),
        )
    ).scalars().all()"""
    if old not in text:
        raise SystemExit("pagos.py: expected block not found (already patched?)")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("patched pagos.py")


def patch_estado_cuenta() -> None:
    p = ROOT / "backend/app/api/v1/endpoints/estado_cuenta_publico.py"
    t = p.read_text(encoding="utf-8")
    imp_line = "from app.services.cobros.recibo_cuota_amortizacion import generar_recibo_cuota_amortizacion\n"
    extra = "from app.api.v1.endpoints.pagos import aplicar_pagos_pendientes_prestamo\n"
    if extra not in t:
        if imp_line not in t:
            raise SystemExit("estado_cuenta_publico.py: import anchor not found")
        t = t.replace(imp_line, imp_line + extra, 1)

    helper = '''

def _sincronizar_pagos_a_cuotas_prestamos(db: Session, prestamo_ids: List[int]) -> None:
    """
    Igual que GET /prestamos/{id}/cuotas: aplica pagos conciliados o verificado_concordancia SI
    que aun no tienen enlace en cuota_pagos; commit si hubo cambios.
    """
    if not prestamo_ids:
        return
    n = 0
    for pid in prestamo_ids:
        n += aplicar_pagos_pendientes_prestamo(pid, db)
    if n > 0:
        db.commit()

'''
    marker = "def _obtener_recibos_cliente(db: Session, cedula_lookup: str) -> List[dict]:"
    if "_sincronizar_pagos_a_cuotas_prestamos" not in t:
        t = t.replace(marker, helper.lstrip("\n") + marker, 1)

    block = """        })
    cuotas_pendientes = []
    total_pendiente = 0.0
    fecha_corte = date.today()
    if prestamo_ids:"""
    insert = """        })
    _sincronizar_pagos_a_cuotas_prestamos(db, prestamo_ids)
    cuotas_pendientes = []
    total_pendiente = 0.0
    fecha_corte = date.today()
    if prestamo_ids:"""
    if insert in t:
        print("estado_cuenta_publico.py already has sync calls")
    else:
        count = t.count(block)
        if count != 2:
            raise SystemExit(f"estado_cuenta_publico.py: expected 2 occurrences of prestamos->cuotas block, got {count}")
        t = t.replace(block, insert, 2)

    p.write_text(t, encoding="utf-8")
    print("patched estado_cuenta_publico.py")


if __name__ == "__main__":
    patch_pagos()
    patch_estado_cuenta()
