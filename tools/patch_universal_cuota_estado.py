# -*- coding: utf-8 -*-
"""Alinear filtros, reportes, SQL y revision manual con cuota_estado (reglas universales)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = ROOT / "backend"

SQL_HOY = "(CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date"

# Subconsulta correlacionada (UPDATE cuotas c SET estado = ...)
SQL_CASE_CORRELATED = f"""
CASE
  WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0)
       >= COALESCE(c.monto_cuota, 0) - 0.01 THEN
    CASE
      WHEN c.fecha_vencimiento IS NOT NULL
        AND c.fecha_vencimiento::date > {SQL_HOY}
      THEN 'PAGO_ADELANTADO'
      ELSE 'PAGADO'
    END
  WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0) > 0.001 THEN
    CASE
      WHEN c.fecha_vencimiento IS NULL THEN 'PARCIAL'
      WHEN {SQL_HOY} <= c.fecha_vencimiento::date THEN 'PARCIAL'
      WHEN ({SQL_HOY} - c.fecha_vencimiento::date) >= 92 THEN 'MORA'
      ELSE 'VENCIDO'
    END
  ELSE
    CASE
      WHEN c.fecha_vencimiento IS NULL THEN 'PENDIENTE'
      WHEN {SQL_HOY} <= c.fecha_vencimiento::date THEN 'PENDIENTE'
      WHEN ({SQL_HOY} - c.fecha_vencimiento::date) >= 92 THEN 'MORA'
      ELSE 'VENCIDO'
    END
END
""".strip()

# Con agregado SUM(cp...) y alias c (GROUP BY c.id, c.monto_cuota, c.fecha_vencimiento)
SQL_CASE_AGGREGATE = f"""
CASE
  WHEN COALESCE(SUM(cp.monto_aplicado), 0) >= COALESCE(c.monto_cuota, 0) - 0.01 THEN
    CASE
      WHEN c.fecha_vencimiento IS NOT NULL
        AND c.fecha_vencimiento::date > {SQL_HOY}
      THEN 'PAGO_ADELANTADO'
      ELSE 'PAGADO'
    END
  WHEN COALESCE(SUM(cp.monto_aplicado), 0) > 0.001 THEN
    CASE
      WHEN c.fecha_vencimiento IS NULL THEN 'PARCIAL'
      WHEN {SQL_HOY} <= c.fecha_vencimiento::date THEN 'PARCIAL'
      WHEN ({SQL_HOY} - c.fecha_vencimiento::date) >= 92 THEN 'MORA'
      ELSE 'VENCIDO'
    END
  ELSE
    CASE
      WHEN c.fecha_vencimiento IS NULL THEN 'PENDIENTE'
      WHEN {SQL_HOY} <= c.fecha_vencimiento::date THEN 'PENDIENTE'
      WHEN ({SQL_HOY} - c.fecha_vencimiento::date) >= 92 THEN 'MORA'
      ELSE 'VENCIDO'
    END
END
""".strip()


def patch_cuota_estado_module() -> None:
    p = B / "app" / "services" / "cuota_estado.py"
    t = p.read_text(encoding="utf-8")
    if "SQL_PG_ESTADO_CUOTA_CASE_CORRELATED" in t:
        return
    extra = f'''

# --- SQL PostgreSQL (misma regla que clasificar_estado_cuota) para scripts/diagnóstico ---
SQL_PG_ESTADO_CUOTA_CASE_CORRELATED = {repr(SQL_CASE_CORRELATED)}

SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE = {repr(SQL_CASE_AGGREGATE)}
'''
    p.write_text(t.rstrip() + extra + "\n", encoding="utf-8")
    print("cuota_estado.py: constantes SQL")


def replace_exact(path: Path, old: str, new: str, label: str) -> None:
    t = path.read_text(encoding="utf-8")
    if old not in t:
        raise SystemExit(f"MISSING {label}: {path}")
    path.write_text(t.replace(old, new, 1), encoding="utf-8")
    print("ok", label, path.name)


def main() -> None:
    patch_cuota_estado_module()

    replace_exact(
        B / "app" / "scripts" / "aplicar_pagos_pendientes_job.py",
        'Cuota.estado.in_(["PENDIENTE", "MORA", "PARCIAL"]),',
        'Cuota.estado.in_(["PENDIENTE", "VENCIDO", "MORA", "PARCIAL"]),',
        "job filtros",
    )

    replace_exact(
        B / "app" / "services" / "conciliacion_automatica_service.py",
        "Cuota.estado.in_([EstadoCuota.PENDIENTE, EstadoCuota.MORA, EstadoCuota.PARCIAL])",
        "Cuota.estado.in_([EstadoCuota.PENDIENTE, EstadoCuota.VENCIDO, EstadoCuota.MORA, EstadoCuota.PARCIAL])",
        "conciliacion filtros",
    )

    replace_exact(
        B / "app" / "api" / "v1" / "endpoints" / "pagos.py",
        'Cuota.estado.in_(["PENDIENTE", "MORA", "PARCIAL"]),',
        'Cuota.estado.in_(["PENDIENTE", "VENCIDO", "MORA", "PARCIAL"]),',
        "pagos cupo",
    )

    paid_in = 'Cuota.estado.in_(["PAGADO", "PAGO_ADELANTADO"])'
    for rp in [
        B / "app" / "api" / "v1" / "endpoints" / "reportes" / "reportes_cedula.py",
        B / "app" / "api" / "v1" / "endpoints" / "reportes" / "reportes_conciliacion.py",
    ]:
        t = rp.read_text(encoding="utf-8")
        t2 = t.replace(
            '.where(Cuota.prestamo_id.in_(ids), Cuota.estado == "PAGADO")',
            f".where(Cuota.prestamo_id.in_(ids), {paid_in})",
        )
        t2 = t2.replace(
            '.where(Cuota.prestamo_id.in_(ids), Cuota.estado != "PAGADO")',
            f".where(Cuota.prestamo_id.in_(ids), ~{paid_in})",
        )
        if t2 == t:
            raise SystemExit(f"reportes replace failed {rp}")
        rp.write_text(t2, encoding="utf-8")
        print("ok reportes", rp.name)

    # amortizacion_service: filtros "no pagada" incluyen PAGO_ADELANTADO como pagada
    amp = B / "app" / "services" / "prestamos" / "amortizacion_service.py"
    at = amp.read_text(encoding="utf-8")
    if "clasificar_estado_cuota" not in at:
        at = at.replace(
            "from app.models.cuota_pago import CuotaPago\n",
            "from app.models.cuota_pago import CuotaPago\n"
            "from app.services.cuota_estado import clasificar_estado_cuota, hoy_negocio\n",
            1,
        )
    at = at.replace(
        "                Cuota.estado != 'PAGADO'\n",
        "                ~Cuota.estado.in_(['PAGADO', 'PAGO_ADELANTADO'])\n",
        2,
    )
    at = at.replace(
        "        hoy = date.today()\n\n        cuotas = self.db.query(Cuota).filter(\n            and_(\n                Cuota.prestamo_id == prestamo_id,\n                Cuota.fecha_vencimiento < hoy,",
        "        hoy = hoy_negocio()\n\n        cuotas = self.db.query(Cuota).filter(\n            and_(\n                Cuota.prestamo_id == prestamo_id,\n                Cuota.fecha_vencimiento < hoy,",
        1,
    )
    at = at.replace(
        "        hoy = date.today()\n        fecha_limite = hoy + timedelta(days=dias_adelante)\n\n        cuotas = self.db.query(Cuota).filter(",
        "        hoy = hoy_negocio()\n        fecha_limite = hoy + timedelta(days=dias_adelante)\n\n        cuotas = self.db.query(Cuota).filter(",
        1,
    )

    old_reg = """        if fecha_pago is None:
            fecha_pago = date.today()

        cuota = self.db.query(Cuota).filter(Cuota.id == cuota_id).first()
        if not cuota:
            raise CuotaNotFoundError(cuota_id)

        monto_cuota = float(getattr(cuota, 'monto_cuota', 0.0))
        monto_actual = float(getattr(cuota, 'monto_pagado', 0.0)) or 0.0

        # Actualizar monto pagado
        nuevo_total = monto_actual + monto_pagado
        monto_restante = max(monto_cuota - nuevo_total, 0.0)

        # Determinar estado
        if monto_restante <= 0:
            estado = 'PAGADO'
            pagado = True
        elif nuevo_total > 0:
            estado = 'PARCIAL'
            pagado = False
        else:
            estado = 'PENDIENTE'
            pagado = False

        # Actualizar cuota
        if hasattr(cuota, 'monto_pagado'):
            cuota.monto_pagado = Decimal(str(nuevo_total))
        if hasattr(cuota, 'estado'):
            cuota.estado = estado
        if hasattr(cuota, 'pagado'):
            cuota.pagado = pagado"""
    new_reg = """        if fecha_pago is None:
            fecha_pago = hoy_negocio()

        cuota = self.db.query(Cuota).filter(Cuota.id == cuota_id).first()
        if not cuota:
            raise CuotaNotFoundError(cuota_id)

        monto_cuota = float(cuota.monto or 0)
        monto_actual = float(cuota.total_pagado or 0) or 0.0

        nuevo_total = monto_actual + monto_pagado
        monto_restante = max(monto_cuota - nuevo_total, 0.0)

        cuota.total_pagado = Decimal(str(round(nuevo_total, 2)))
        estado = clasificar_estado_cuota(
            nuevo_total, monto_cuota, cuota.fecha_vencimiento, hoy_negocio()
        )
        pagado = estado in ("PAGADO", "PAGO_ADELANTADO")

        if hasattr(cuota, 'estado'):
            cuota.estado = estado
        if hasattr(cuota, 'pagado'):
            cuota.pagado = pagado"""
    if old_reg not in at:
        raise SystemExit("amortizacion registrar_pago block missing")
    at = at.replace(old_reg, new_reg, 1)
    amp.write_text(at, encoding="utf-8")
    print("ok amortizacion_service")

    # revision_manual estados
    rev = B / "app" / "api" / "v1" / "endpoints" / "revision_manual.py"
    rt = rev.read_text(encoding="utf-8")
    rt = rt.replace(
        '        estados_validos = ["PENDIENTE", "PAGADO", "CONCILIADO"]\n'
        '        if estado_normalizado not in estados_validos:\n'
        '            raise HTTPException(status_code=400, detail=f"Estado inválido. Válidos: {estados_validos}")',
        '        estados_validos = [\n'
        '            "PENDIENTE",\n'
        '            "PARCIAL",\n'
        '            "VENCIDO",\n'
        '            "MORA",\n'
        '            "PAGADO",\n'
        '            "PAGO_ADELANTADO",\n'
        '        ]\n'
        '        if estado_normalizado not in estados_validos:\n'
        '            raise HTTPException(status_code=400, detail=f"Estado inválido. Válidos: {estados_validos}")',
        1,
    )
    if "CONCILIADO" in rt and 'estados_validos = ["PENDIENTE"' in rt:
        raise SystemExit("revision_manual estados_validos not updated")
    rev.write_text(rt, encoding="utf-8")
    print("ok revision_manual")

    # ejecutar_correcciones_criticas
    ej = B / "app" / "scripts" / "ejecutar_correcciones_criticas.py"
    et = ej.read_text(encoding="utf-8")
    et = et.replace(
        "WHERE c.estado NOT IN ('PAGADO', 'PARCIAL', 'MORA', 'PENDIENTE', 'CANCELADA')",
        "WHERE c.estado NOT IN ('PAGADO', 'PAGO_ADELANTADO', 'PARCIAL', 'VENCIDO', 'MORA', 'PENDIENTE', 'CANCELADA')",
        1,
    )
    old_up = """        result = db.execute(text('''
            UPDATE cuotas c SET estado = CASE 
                WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0) >= c.monto - 0.01 THEN 'PAGADO'
                WHEN COALESCE((SELECT SUM(cp.monto_aplicado) FROM cuota_pagos cp WHERE cp.cuota_id = c.id), 0) > 0 THEN 'PARCIAL'
                WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
                ELSE 'PENDIENTE' END
            WHERE c.estado IS NULL
        '''))"""
    new_up = f"""        result = db.execute(text('''
            UPDATE cuotas c SET estado = {SQL_CASE_CORRELATED}
            WHERE c.estado IS NULL
        '''))"""
    if old_up not in et:
        raise SystemExit("ejecutar UPDATE block missing")
    et = et.replace(old_up, new_up, 1)
    ej.write_text(et, encoding="utf-8")
    print("ok ejecutar_correcciones")

    # diagnostico_critico_service - import and replace CASE in query strings
    dg = B / "app" / "services" / "diagnostico_critico_service.py"
    dt = dg.read_text(encoding="utf-8")
    if "from app.services import cuota_estado" not in dt and "cuota_estado import" not in dt:
        dt = dt.replace(
            "from sqlalchemy.orm import Session\n",
            "from sqlalchemy.orm import Session\nfrom app.services.cuota_estado import (\n"
            "    SQL_PG_ESTADO_CUOTA_CASE_AGGREGATE,\n"
            ")\n",
            1,
        )
    old_case1 = """              CASE 
                WHEN COALESCE(SUM(cp.monto_aplicado), 0) >= c.monto - 0.01 THEN 'PAGADO'
                WHEN COALESCE(SUM(cp.monto_aplicado), 0) > 0 THEN 'PARCIAL'
                WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
                ELSE 'PENDIENTE'
              END as estado_calculado,"""
    new_case1 = f"""              {SQL_CASE_AGGREGATE} as estado_calculado,"""
    if old_case1 not in dt:
        raise SystemExit("diagnostico case1 missing")
    dt = dt.replace(old_case1, new_case1, 1)

    old_case2 = """                    CASE 
                      WHEN COALESCE(SUM(cp.monto_aplicado), 0) >= c.monto - 0.01 THEN 'PAGADO'
                      WHEN COALESCE(SUM(cp.monto_aplicado), 0) > 0 THEN 'PARCIAL'
                      WHEN DATE(c.fecha_vencimiento) < CURRENT_DATE THEN 'MORA'
                      ELSE 'PENDIENTE'
                    END as estado_correcto"""
    new_case2 = f"""                    {SQL_CASE_AGGREGATE} as estado_correcto"""
    if old_case2 not in dt:
        raise SystemExit("diagnostico case2 missing")
    dt = dt.replace(old_case2, new_case2, 1)

    # GROUP BY debe usar monto_cuota si el SELECT lo usa - verificar query usa c.monto
    dt = dt.replace("c.monto,", "c.monto_cuota,", 2)
    dt = dt.replace("float(c[3])", "float(c[3])", 0)
    dg.write_text(dt, encoding="utf-8")
    print("ok diagnostico_critico")

    # Remove unused import if we embedded SQL not import - we used inline SQL_CASE_AGGREGATE in replace
    # Actually I used SQL_CASE_AGGREGATE variable from this script in new_case - that's wrong, it's not in diagnostico file
    # I need to fix: new_case1 should embed the string content not variable reference

    print("WARNING: diagnostico patch used local variable - redo")

if __name__ == "__main__":
    main()
