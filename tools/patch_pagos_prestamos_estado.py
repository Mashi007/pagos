"""One-off patch: alinear pagos.py y prestamos.py con cuota_estado unificado."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGOS = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
PRESTAMOS = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "prestamos.py"
ESTADO_CUENTA = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "estado_cuenta_publico.py"
LIQUIDADO = ROOT / "backend" / "app" / "services" / "liquidado_notificacion_service.py"


def patch_pagos() -> None:
    text = PAGOS.read_text(encoding="utf-8")
    needle = "from app.schemas.auth import UserResponse\n\n\n\n\nclass MoverRevisarPagosBody"
    repl = (
        "from app.schemas.auth import UserResponse\n\n"
        "from app.services.cuota_estado import clasificar_estado_cuota, dias_retraso_desde_vencimiento\n\n\n"
        "class MoverRevisarPagosBody"
    )
    if needle not in text:
        raise SystemExit("pagos: import anchor not found")
    text = text.replace(needle, repl, 1)

    old_trans = '''    transiciones_permitidas = {

        "PENDIENTE": ["PAGADO", "PAGO_ADELANTADO", "VENCIDO", "MORA", "PENDIENTE"],

        "VENCIDO": ["PAGADO", "PAGO_ADELANTADO", "VENCIDO", "MORA"],

        "MORA": ["PAGADO", "PAGO_ADELANTADO", "VENCIDO", "MORA"],

        "PAGO_ADELANTADO": ["PAGADO", "PAGO_ADELANTADO"],

        "PAGADO": ["PAGADO"],

    }'''
    new_trans = '''    transiciones_permitidas = {

        "PENDIENTE": [
            "PAGADO",
            "PAGO_ADELANTADO",
            "VENCIDO",
            "MORA",
            "PENDIENTE",
            "PARCIAL",
        ],

        "PARCIAL": [
            "PAGADO",
            "PAGO_ADELANTADO",
            "VENCIDO",
            "MORA",
            "PARCIAL",
            "PENDIENTE",
        ],

        "VENCIDO": ["PAGADO", "PAGO_ADELANTADO", "VENCIDO", "MORA", "PARCIAL"],

        "MORA": ["PAGADO", "PAGO_ADELANTADO", "VENCIDO", "MORA", "PARCIAL"],

        "PAGO_ADELANTADO": ["PAGADO", "PAGO_ADELANTADO"],

        "PAGADO": ["PAGADO"],

    }'''
    if old_trans not in text:
        raise SystemExit("pagos: transiciones block not found")
    text = text.replace(old_trans, new_trans, 1)

    old_calc_start = 'def _calcular_dias_mora(fecha_vencimiento: date) -> int:'
    old_calc_end = 'def _safe_float(val) -> float:'
    i0 = text.find(old_calc_start)
    i1 = text.find(old_calc_end)
    if i0 < 0 or i1 < 0 or i1 <= i0:
        raise SystemExit("pagos: calc/clasificar/safe_float block not found")
    new_mid = '''def _calcular_dias_mora(fecha_vencimiento: date) -> int:

    """

    Dias calendario desde fecha_vencimiento hasta hoy (America/Caracas), no negativos.

    """

    return dias_retraso_desde_vencimiento(fecha_vencimiento, _hoy_local())





'''
    text = text[:i0] + new_mid + text[i1:]

    old_estado = '''def _estado_cuota_por_cobertura(total_pagado: float, monto_cuota: float, fecha_vencimiento: date) -> str:

    """

    [MORA] Determina estado según cobertura y fecha de vencimiento.

    Usa la nueva clasificación: PENDIENTE | VENCIDO (1-90d) | MORA (>90d) | PAGO_ADELANTADO

    """

    dias_mora = _calcular_dias_mora(fecha_vencimiento)

    return _clasificar_nivel_mora(dias_mora, total_pagado, monto_cuota)

    # Nota: Si total_pagado > 0 pero < monto_cuota:

    #   - _clasificar_nivel_mora devuelve VENCIDO o MORA según días

    # Si total_pagado == 0:

    #   - devuelve PENDIENTE si dias_mora == 0, sino VENCIDO/MORA'''
    new_estado = '''def _estado_cuota_por_cobertura(total_pagado: float, monto_cuota: float, fecha_vencimiento: date) -> str:

    """

    Delega en app.services.cuota_estado (Caracas, VENCIDO 1-91 dias, MORA desde dia 92).

    """

    return clasificar_estado_cuota(total_pagado, monto_cuota, fecha_vencimiento, _hoy_local())'''
    if old_estado not in text:
        raise SystemExit("pagos: _estado_cuota_por_cobertura block not found")
    text = text.replace(old_estado, new_estado, 1)

    old_pay = '''        if nuevo_total >= monto_cuota - 0.01:

            c.fecha_pago = fecha_pago_date

            estado_nuevo = "PAGADO"'''
    new_pay = '''        if nuevo_total >= monto_cuota - 0.01:

            c.fecha_pago = fecha_pago_date

            if isinstance(fecha_venc, date) and fecha_venc > hoy:

                estado_nuevo = "PAGO_ADELANTADO"

            else:

                estado_nuevo = "PAGADO"'''
    if old_pay not in text:
        raise SystemExit("pagos: pago completo estado block not found")
    text = text.replace(old_pay, new_pay, 1)

    PAGOS.write_text(text, encoding="utf-8")
    print("patched pagos.py")


def patch_prestamos() -> None:
    text = PRESTAMOS.read_text(encoding="utf-8")
    old_imp = "from app.services.cuota_estado import estado_cuota_para_mostrar\n"
    new_imp = "from app.services.cuota_estado import estado_cuota_para_mostrar, hoy_negocio\n"
    if old_imp not in text:
        raise SystemExit("prestamos: import not found")
    text = text.replace(old_imp, new_imp, 1)

    old_cuotas = '''        if total_pagado_f < monto_cuota_f - 0.01:

            fv = c.fecha_vencimiento

            fv_date = fv.date() if fv and hasattr(fv, "date") else fv

            estado_mostrar = estado_cuota_para_mostrar(total_pagado_f, monto_cuota_f, fv_date, date.today())

        else:

            estado_mostrar = "PAGADO"'''
    new_cuotas = '''        fv = c.fecha_vencimiento

        fv_date = fv.date() if fv and hasattr(fv, "date") else fv

        estado_mostrar = estado_cuota_para_mostrar(

            total_pagado_f, monto_cuota_f, fv_date, hoy_negocio()

        )'''
    if old_cuotas not in text:
        raise SystemExit("prestamos: get_cuotas block not found")
    text = text.replace(old_cuotas, new_cuotas, 1)

    old_pdf = '''    hoy = date.today()

    for c in cuotas:

        saldo_inicial = float(c.saldo_capital_inicial) if c.saldo_capital_inicial is not None else 0

        saldo_final = float(c.saldo_capital_final) if c.saldo_capital_final is not None else 0

        monto_cuota = float(c.monto) if c.monto is not None else 0

        total_pagado = float(c.total_pagado or 0)

        monto_capital = max(0, saldo_inicial - saldo_final)

        monto_interes = max(0, monto_cuota - monto_capital)

        fv = c.fecha_vencimiento

        fv_date = fv.date() if fv and hasattr(fv, "date") else fv

        if total_pagado >= monto_cuota - 0.01 and monto_cuota > 0:

            estado_mostrar = "PAGADO"

        else:

            estado_mostrar = estado_cuota_para_mostrar(total_pagado, monto_cuota, fv_date, hoy)'''
    new_pdf = '''    hoy = hoy_negocio()

    for c in cuotas:

        saldo_inicial = float(c.saldo_capital_inicial) if c.saldo_capital_inicial is not None else 0

        saldo_final = float(c.saldo_capital_final) if c.saldo_capital_final is not None else 0

        monto_cuota = float(c.monto) if c.monto is not None else 0

        total_pagado = float(c.total_pagado or 0)

        monto_capital = max(0, saldo_inicial - saldo_final)

        monto_interes = max(0, monto_cuota - monto_capital)

        fv = c.fecha_vencimiento

        fv_date = fv.date() if fv and hasattr(fv, "date") else fv

        estado_mostrar = estado_cuota_para_mostrar(total_pagado, monto_cuota, fv_date, hoy)'''
    if old_pdf not in text:
        raise SystemExit("prestamos: pdf amort block not found")
    text = text.replace(old_pdf, new_pdf, 1)

    PRESTAMOS.write_text(text, encoding="utf-8")
    print("patched prestamos.py")


def patch_estado_cuenta() -> None:
    text = ESTADO_CUENTA.read_text(encoding="utf-8")
    old_imp = "from app.services.cuota_estado import estado_cuota_para_mostrar\n"
    new_imp = "from app.services.cuota_estado import estado_cuota_para_mostrar, hoy_negocio\n"
    if old_imp not in text:
        raise SystemExit("estado_cuenta: import not found")
    text = text.replace(old_imp, new_imp, 1)

    text = text.replace(
        "    fecha_corte = date.today()\n\n    if prestamo_ids:",
        "    fecha_corte = hoy_negocio()\n\n    if prestamo_ids:",
        1,
    )

    old_b = '''        if total_pagado_float < monto_cuota - 0.01:

            fv_date = fecha_venc.date() if fecha_venc and hasattr(fecha_venc, "date") else fecha_venc

            estado_mostrar = estado_cuota_para_mostrar(total_pagado_float, monto_cuota, fv_date, date.today())

        else:

            estado_mostrar = "PAGADO"'''
    new_b = '''        fv_date = fecha_venc.date() if fecha_venc and hasattr(fecha_venc, "date") else fecha_venc

        estado_mostrar = estado_cuota_para_mostrar(

            total_pagado_float, monto_cuota, fv_date, hoy_negocio()

        )'''
    if old_b not in text:
        raise SystemExit("estado_cuenta: amort estado block not found")
    text = text.replace(old_b, new_b, 1)

    ESTADO_CUENTA.write_text(text, encoding="utf-8")
    print("patched estado_cuenta_publico.py")


def patch_liquidado() -> None:
    text = LIQUIDADO.read_text(encoding="utf-8")
    if "hoy_negocio" not in text:
        text = text.replace(
            "from app.services.cuota_estado import estado_cuota_para_mostrar",
            "from app.services.cuota_estado import estado_cuota_para_mostrar, hoy_negocio",
            1,
        )
    old_sql = """                SELECT c.prestamo_id, c.numero_cuota, c.fecha_vencimiento, c.monto_cuota, c.estado
                FROM cuotas c
                INNER JOIN prestamos p ON c.prestamo_id = p.id
                WHERE p.cliente_id = :cliente_id AND c.estado = 'PENDIENTE'
                ORDER BY c.prestamo_id, c.numero_cuota"""
    new_sql = """                SELECT c.prestamo_id, c.numero_cuota, c.fecha_vencimiento,
                       COALESCE(c.monto, 0), COALESCE(c.total_pagado, 0)
                FROM cuotas c
                INNER JOIN prestamos p ON c.prestamo_id = p.id
                WHERE p.cliente_id = :cliente_id
                  AND COALESCE(c.total_pagado, 0) < COALESCE(c.monto, 0) - 0.01
                ORDER BY c.prestamo_id, c.numero_cuota"""
    if old_sql not in text:
        raise SystemExit("liquidado: SQL block not found")
    text = text.replace(old_sql, new_sql, 1)

    old_loop = """            for row in result_cuotas:
                estado_str = estado_cuota_para_mostrar(row[4])
                cuotas_data.append({
                    'prestamo_id': row[0],
                    'numero_cuota': row[1],
                    'fecha_vencimiento': row[2].isoformat() if row[2] else '',
                    'monto': float(row[3] or 0),
                    'estado': estado_str,
                })
                total_pendiente += float(row[3] or 0)"""
    new_loop = """            hoy_ref = hoy_negocio()
            for row in result_cuotas:
                fv = row[2]
                fv_d = fv.date() if fv and hasattr(fv, "date") else fv
                monto_c = float(row[3] or 0)
                total_p = float(row[4] or 0)
                estado_str = estado_cuota_para_mostrar(total_p, monto_c, fv_d, hoy_ref)
                cuotas_data.append({
                    'prestamo_id': row[0],
                    'numero_cuota': row[1],
                    'fecha_vencimiento': row[2].isoformat() if row[2] else '',
                    'monto': max(0.0, monto_c - total_p),
                    'estado': estado_str,
                })
                total_pendiente += max(0.0, monto_c - total_p)"""
    if old_loop not in text:
        raise SystemExit("liquidado: loop block not found")
    text = text.replace(old_loop, new_loop, 1)

    LIQUIDADO.write_text(text, encoding="utf-8")
    print("patched liquidado_notificacion_service.py")


def main() -> None:
    patch_pagos()
    patch_prestamos()
    patch_estado_cuenta()
    patch_liquidado()


if __name__ == "__main__":
    main()
