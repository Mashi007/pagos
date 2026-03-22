# -*- coding: utf-8 -*-
"""Patches cobros_publico, recibo_pdf, pagos endpoint, schemas, validacion, SQL."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_cobros_publico() -> None:
    path = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "cobros_publico.py"
    text = path.read_text(encoding="utf-8")
    if "obtener_tasa_por_fecha" in text and "fecha_hoy_caracas" in text:
        print("cobros_publico: already patched")
        return
    needle = "from app.services.cobros.recibo_pdf import generar_recibo_pago_reportado, WHATSAPP_LINK\n"
    ins = (
        needle
        + "from app.services.tasa_cambio_service import (\n"
        "    obtener_tasa_por_fecha,\n"
        "    fecha_hoy_caracas,\n"
        ")\n"
    )
    if needle not in text:
        raise SystemExit("cobros_publico: import anchor not found")
    text = text.replace(needle, ins, 1)

    err = (
        'ERROR_TASA_BS_NO_REGISTRADA = (\n'
        '    "No hay tasa de cambio oficial para la fecha de pago {fp}. "\n'
        '    "Un administrador debe registrarla en Administracion > Tasas de cambio para esa fecha "\n'
        '    "antes de reportar en bolivares."\n'
        ")\n\n\n"
    )
    anchor = "ERROR_BS_NO_AUTORIZADO = "
    idx = text.find(anchor)
    if idx == -1:
        raise SystemExit("ERROR_BS anchor not found")
    # insert before ERROR_BS line
    text = text[:idx] + err + text[idx:]

    text = text.replace("date.today()", "fecha_hoy_caracas()")

    old_recibo = """    if moneda == "BS":

        try:

            from app.services.tasa_cambio_service import obtener_tasa_hoy

            tasa_obj = obtener_tasa_hoy(db)

            tasa_cambio = float(tasa_obj.tasa_oficial) if tasa_obj else None

        except Exception:

            pass
"""
    new_recibo = """    if moneda == "BS" and pr.fecha_pago:

        tasa_obj = obtener_tasa_por_fecha(db, pr.fecha_pago)

        tasa_cambio = float(tasa_obj.tasa_oficial) if tasa_obj else None

    elif moneda == "BS":

        tasa_cambio = None
"""
    if old_recibo not in text:
        # try without double newlines flexibility
        if "obtener_tasa_hoy(db)" not in text:
            raise SystemExit("recibo block not found")
        text = text.replace(
            """            from app.services.tasa_cambio_service import obtener_tasa_hoy

            tasa_obj = obtener_tasa_hoy(db)

            tasa_cambio = float(tasa_obj.tasa_oficial) if tasa_obj else None""",
            """            tasa_obj = (
                obtener_tasa_por_fecha(db, pr.fecha_pago) if pr.fecha_pago else None
            )

            tasa_cambio = float(tasa_obj.tasa_oficial) if tasa_obj else None""",
        )
        text = text.replace("from app.services.tasa_cambio_service import obtener_tasa_hoy\n\n            ", "")
    else:
        text = text.replace(old_recibo, new_recibo, 1)

    block_pub = """        if not permitido_bs:

            return EnviarReporteResponse(ok=False, error=ERROR_BS_NO_AUTORIZADO)

    if monto <= 0"""
    block_pub_new = """        if not permitido_bs:

            return EnviarReporteResponse(ok=False, error=ERROR_BS_NO_AUTORIZADO)

        tasa_row = obtener_tasa_por_fecha(db, fecha_pago)

        if tasa_row is None:

            return EnviarReporteResponse(

                ok=False,

                error=ERROR_TASA_BS_NO_REGISTRADA.format(

                    fp=fecha_pago.strftime("%d/%m/%Y"),

                ),

            )

    if monto <= 0"""
    if block_pub not in text:
        raise SystemExit("cobros block_pub not found")
    text = text.replace(block_pub, block_pub_new, 1)

    block_info = """        if not permitido_bs:

            return EnviarReporteInfopagosResponse(ok=False, error=ERROR_BS_NO_AUTORIZADO)

    if monto <= 0"""
    block_info_new = """        if not permitido_bs:

            return EnviarReporteInfopagosResponse(ok=False, error=ERROR_BS_NO_AUTORIZADO)

        tasa_row = obtener_tasa_por_fecha(db, fecha_pago)

        if tasa_row is None:

            return EnviarReporteInfopagosResponse(

                ok=False,

                error=ERROR_TASA_BS_NO_REGISTRADA.format(

                    fp=fecha_pago.strftime("%d/%m/%Y"),

                ),

            )

    if monto <= 0"""
    if block_info not in text:
        raise SystemExit("cobros block_info not found")
    text = text.replace(block_info, block_info_new, 1)

    path.write_text(text, encoding="utf-8")
    print("Patched cobros_publico.py")


def patch_recibo_pdf() -> None:
    path = ROOT / "backend" / "app" / "services" / "cobros" / "recibo_pdf.py"
    text = path.read_text(encoding="utf-8")
    if "Monto indicado en" in text:
        print("recibo_pdf: already patched")
        return
    old = """    if banco_valido:
        cuerpo = (
            "Se confirma la recepcion de su reporte de pago, asociado al titular "
            f"<b>{nombre_completo or '-'}</b> (cedula <b>{cedula or '-'}</b>). "
            f"El pago fue reportado por <b>{monto_display or '-'}</b> en la institucion "
            f"<b>{banco_valido}</b>, con numero de operacion <b>{numero_op or '-'}</b>."
        )
    else:
        cuerpo = (
            "Se confirma la recepcion de su reporte de pago, asociado al titular "
            f"<b>{nombre_completo or '-'}</b> (cedula <b>{cedula or '-'}</b>). "
            f"El pago fue reportado por <b>{monto_display or '-'}</b>, "
            f"con numero de operacion <b>{numero_op or '-'}</b>."
        )
    if aplicado_a_cuotas and (aplicado_a_cuotas or "").strip():
        cuerpo += (
            f" Este comprobante corresponde al abono registrado a <b>{(aplicado_a_cuotas or '').strip()}</b> "
            "del credito, segun la tabla de amortizacion."
        )
    story.append(Paragraph(cuerpo, body_style))
"""
    moneda_u = '(moneda or "").strip().upper()'
    new = f"""    moneda_u = {moneda_u}

    if banco_valido:
        cuerpo = (
            "Se confirma la recepcion de su reporte de pago, asociado al titular "
            f"<b>{{nombre_completo or '-'}}</b> (cedula <b>{{cedula or '-'}}</b>). "
            f"El pago fue reportado por <b>{{monto_display or '-'}}</b> en la institucion "
            f"<b>{{banco_valido}}</b>, con numero de operacion <b>{{numero_op or '-'}}</b>."
        )
    else:
        cuerpo = (
            "Se confirma la recepcion de su reporte de pago, asociado al titular "
            f"<b>{{nombre_completo or '-'}}</b> (cedula <b>{{cedula or '-'}}</b>). "
            f"El pago fue reportado por <b>{{monto_display or '-'}}</b>, "
            f"con numero de operacion <b>{{numero_op or '-'}}</b>."
        )
    if aplicado_a_cuotas and (aplicado_a_cuotas or "").strip():
        cuerpo += (
            f" Este comprobante corresponde al abono registrado a <b>{{(aplicado_a_cuotas or '').strip()}}</b> "
            "del credito, segun la tabla de amortizacion."
        )
    if moneda_u == "USD":
        cuerpo += (
            " Monto indicado en <b>USD</b> (dolares estadounidenses)."
        )
    elif moneda_u == "BS" and tasa_cambio is not None:
        cuerpo += (
            f" Monto en <b>bolivares (Bs.)</b>. Tasa de cambio oficial para la fecha de pago "
            f"(<b>{{fecha_pago_str}}</b>): <b>{{tasa_cambio:,.2f}}</b> Bs. por 1 USD."
        )
    story.append(Paragraph(cuerpo, body_style))
"""
    # fix f-string braces: we need real f-strings in output
    new = new.replace("f\"\"\"", "f\"\"\"")  # noop
    # rebuild new properly with Python
    new = (
        '    moneda_u = (moneda or "").strip().upper()\n\n'
        "    if banco_valido:\n"
        "        cuerpo = (\n"
        '            "Se confirma la recepcion de su reporte de pago, asociado al titular "\n'
        '            f"<b>{nombre_completo or \'-\'}</b> (cedula <b>{cedula or \'-\'}</b>). "\n'
        '            f"El pago fue reportado por <b>{monto_display or \'-\'}</b> en la institucion "\n'
        '            f"<b>{banco_valido}</b>, con numero de operacion <b>{numero_op or \'-\'}</b>."\n'
        "        )\n"
        "    else:\n"
        "        cuerpo = (\n"
        '            "Se confirma la recepcion de su reporte de pago, asociado al titular "\n'
        '            f"<b>{nombre_completo or \'-\'}</b> (cedula <b>{cedula or \'-\'}</b>). "\n'
        '            f"El pago fue reportado por <b>{monto_display or \'-\'}</b>, "\n'
        '            f"con numero de operacion <b>{numero_op or \'-\'}</b>."\n'
        "        )\n"
        "    if aplicado_a_cuotas and (aplicado_a_cuotas or \"\").strip():\n"
        "        cuerpo += (\n"
        '            f" Este comprobante corresponde al abono registrado a <b>{(aplicado_a_cuotas or \'\').strip()}</b> "\n'
        '            "del credito, segun la tabla de amortizacion."\n'
        "        )\n"
        '    if moneda_u == "USD":\n'
        "        cuerpo += (\n"
        '            " Monto indicado en <b>USD</b> (dolares estadounidenses)."\n'
        "        )\n"
        '    elif moneda_u == "BS" and tasa_cambio is not None:\n'
        "        cuerpo += (\n"
        '            f" Monto en <b>bolivares (Bs.)</b>. Tasa de cambio oficial para la fecha de pago "\n'
        '            f"(<b>{fecha_pago_str}</b>): <b>{tasa_cambio:,.2f}</b> Bs. por 1 USD."\n'
        "        )\n"
        "    story.append(Paragraph(cuerpo, body_style))\n"
    )
    if old not in text:
        raise SystemExit("recibo_pdf old block not found")
    text = text.replace(old, new, 1)

    # Show USD/Bs next to amounts in table
    old_sym = """    if _m:
        moneda_symbol = _m
    else:
        md_u = (monto_display or "").upper()
        if "USD" in md_u:
            moneda_symbol = ""
        elif "BS" in md_u:
            moneda_symbol = ""
        else:
            moneda_symbol = "Bs."
"""
    new_sym = """    md_u = (monto_display or "").upper()
    moneda_u_sym = (moneda or "").strip().upper()
    if _m:
        moneda_symbol = _m
    elif moneda_u_sym == "USD":
        moneda_symbol = "USD"
    elif moneda_u_sym == "BS":
        moneda_symbol = "Bs."
    elif "USD" in md_u:
        moneda_symbol = "USD"
    elif "BS" in md_u:
        moneda_symbol = "Bs."
    else:
        moneda_symbol = "Bs."
"""
    if old_sym not in text:
        raise SystemExit("recibo_pdf symbol block not found")
    text = text.replace(old_sym, new_sym, 1)

    path.write_text(text, encoding="utf-8")
    print("Patched recibo_pdf.py")


def patch_pagos_endpoint() -> None:
    path = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
    text = path.read_text(encoding="utf-8")
    if "convertir_bs_a_usd" in text and "monto_bs_original" in text:
        print("pagos.py: already patched imports/block")
    else:
        needle = "from app.services.cuota_estado import clasificar_estado_cuota, dias_retraso_desde_vencimiento\n\n\n"
        if needle not in text:
            raise SystemExit("pagos anchor not found")
        text = text.replace(
            needle,
            needle
            + "from app.services.tasa_cambio_service import (\n"
            "    convertir_bs_a_usd,\n"
            "    obtener_tasa_por_fecha,\n"
            ")\n\n\n",
            1,
        )

    # importar_un_pago_reportado_a_pagos: replace monto block
    old = """    prestamo_id = prestamos[0].id

    monto = float(pr.monto or 0)

    if monto < _MIN_MONTO_PAGADO:

        return _err_con_pce(
            f"Monto debe ser mayor a {_MIN_MONTO_PAGADO}",
            cedula_cliente=cedula_raw,
            prestamo_id=prestamo_id,
        )



    ref_pago = (numero_doc_norm or numero_doc_raw or "Cobros")[:_MAX_LEN_NUMERO_DOCUMENTO]

    ahora_imp = datetime.now(ZoneInfo(TZ_NEGOCIO))

    p = Pago(

        cedula_cliente=cedula_raw,

        prestamo_id=prestamo_id,

        fecha_pago=datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now(),

        monto_pagado=Decimal(str(round(monto, 2))),

        numero_documento=numero_doc_norm,

        estado="PENDIENTE",

        referencia_pago=ref_pago,

        usuario_registro=usuario_email,

        conciliado=True,

        fecha_conciliacion=ahora_imp,

        verificado_concordancia="SI",

    )
"""
    new = """    prestamo_id = prestamos[0].id

    moneda_pr = (getattr(pr, "moneda", None) or "USD").strip().upper()

    if moneda_pr == "USDT":
        moneda_pr = "USD"

    monto = float(pr.monto or 0)

    monto_bs_original = None

    tasa_aplicada = None

    fecha_tasa_ref = None

    if moneda_pr == "BS":

        if not pr.fecha_pago:

            return _err_con_pce(

                "Fecha de pago requerida para convertir bolivares a USD",

                cedula_cliente=cedula_raw,

                prestamo_id=prestamo_id,

            )

        tasa_obj = obtener_tasa_por_fecha(db, pr.fecha_pago)

        if tasa_obj is None:

            return _err_con_pce(

                "No hay tasa de cambio registrada para la fecha de pago "

                f"{pr.fecha_pago.isoformat()}; no se puede importar en bolivares",

                cedula_cliente=cedula_raw,

                prestamo_id=prestamo_id,

            )

        tasa_aplicada = float(tasa_obj.tasa_oficial)

        monto_bs_original = monto

        try:

            monto = convertir_bs_a_usd(monto_bs_original, tasa_aplicada)

        except ValueError as e:

            return _err_con_pce(str(e), cedula_cliente=cedula_raw, prestamo_id=prestamo_id)

        fecha_tasa_ref = pr.fecha_pago

    elif moneda_pr != "USD":

        return _err_con_pce(

            f"Moneda no soportada en importacion: {moneda_pr}",

            cedula_cliente=cedula_raw,

            prestamo_id=prestamo_id,

        )

    if monto < _MIN_MONTO_PAGADO:

        return _err_con_pce(

            f"Monto debe ser mayor a {_MIN_MONTO_PAGADO}",

            cedula_cliente=cedula_raw,

            prestamo_id=prestamo_id,

        )

    ref_pago = (numero_doc_norm or numero_doc_raw or "Cobros")[:_MAX_LEN_NUMERO_DOCUMENTO]

    ahora_imp = datetime.now(ZoneInfo(TZ_NEGOCIO))

    p = Pago(

        cedula_cliente=cedula_raw,

        prestamo_id=prestamo_id,

        fecha_pago=datetime.combine(pr.fecha_pago, dt_time.min) if pr.fecha_pago else datetime.now(),

        monto_pagado=Decimal(str(round(monto, 2))),

        numero_documento=numero_doc_norm,

        estado="PENDIENTE",

        referencia_pago=ref_pago,

        usuario_registro=usuario_email,

        conciliado=True,

        fecha_conciliacion=ahora_imp,

        verificado_concordancia="SI",

        moneda_registro=moneda_pr,

        monto_bs_original=Decimal(str(round(monto_bs_original, 2))) if monto_bs_original is not None else None,

        tasa_cambio_bs_usd=Decimal(str(tasa_aplicada)) if tasa_aplicada is not None else None,

        fecha_tasa_referencia=fecha_tasa_ref,

    )
"""
    if old not in text:
        raise SystemExit("pagos importar block not found")
    text = text.replace(old, new, 1)

    old_resp = '''        "documento_ruta": getattr(row, "documento_ruta", None),

        "cuotas_atrasadas": cuotas_atrasadas,
'''
    new_resp = '''        "documento_ruta": getattr(row, "documento_ruta", None),

        "cuotas_atrasadas": cuotas_atrasadas,

        "moneda_registro": getattr(row, "moneda_registro", None),

        "monto_bs_original": float(row.monto_bs_original) if getattr(row, "monto_bs_original", None) is not None else None,

        "tasa_cambio_bs_usd": float(row.tasa_cambio_bs_usd) if getattr(row, "tasa_cambio_bs_usd", None) is not None else None,

        "fecha_tasa_referencia": row.fecha_tasa_referencia.isoformat() if getattr(row, "fecha_tasa_referencia", None) else None,
'''
    if "moneda_registro" in text and '"moneda_registro"' in text:
        print("pagos _pago_to_response: skip")
    else:
        if old_resp not in text:
            raise SystemExit("pagos _pago_to_response anchor not found")
        text = text.replace(old_resp, new_resp, 1)

    path.write_text(text, encoding="utf-8")
    print("Patched pagos.py")


def patch_schemas_pago() -> None:
    path = ROOT / "backend" / "app" / "schemas" / "pago.py"
    text = path.read_text(encoding="utf-8")
    if "moneda_registro" in text:
        print("schemas pago: already patched")
        return
    old = """    documento_ruta: Optional[str] = None
    cuotas_atrasadas: Optional[int] = None  # calculado en listado


"""
    new = """    documento_ruta: Optional[str] = None
    cuotas_atrasadas: Optional[int] = None  # calculado en listado
    moneda_registro: Optional[str] = None
    monto_bs_original: Optional[Decimal] = None
    tasa_cambio_bs_usd: Optional[Decimal] = None
    fecha_tasa_referencia: Optional[date] = None


"""
    if old not in text:
        raise SystemExit("schemas pago anchor not found")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("Patched schemas/pago.py")


def patch_validacion() -> None:
    path = ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "tasa_cambio_validacion.py"
    text = path.read_text(encoding="utf-8")
    if "fecha_pago" in text and "Query(None" in text and "obtener_tasa_por_fecha" in text:
        print("tasa_cambio_validacion: already patched")
        return
    text = text.replace(
        "from fastapi import APIRouter, Depends, HTTPException\n",
        "from datetime import date\n\nfrom fastapi import APIRouter, Depends, HTTPException, Query\n",
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
    old_sig = """def validar_tasa_para_pago(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
"""
    new_sig = """def validar_tasa_para_pago(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
    fecha_pago: Optional[date] = Query(
        None,
        description="Fecha de pago del reporte; si se informa, se valida tasa para esa fecha (Bs).",
    ),
):
"""
    text = text.replace(old_sig, new_sig, 1)
    if "Optional[date]" in text and "from typing import Optional" not in text:
        text = text.replace("from typing import Optional\n", "from typing import Optional\n", 1)

    # Add Optional to typing import if missing
    if "from typing import Optional" not in text:
        text = text.replace("from datetime import date\n\n", "from datetime import date\nfrom typing import Optional\n\n", 1)

    old_body = """    tasa = obtener_tasa_hoy(db)
    debe_ingresar = debe_ingresar_tasa()
    
    # Caso 1: Tasa existe y estamos en horario de ingreso
    if tasa:
"""
    new_body = """    debe_ingresar = debe_ingresar_tasa()
    ref_date = fecha_pago or fecha_hoy_caracas()
    tasa = obtener_tasa_por_fecha(db, ref_date) if fecha_pago else obtener_tasa_hoy(db)

    # Caso 1: Tasa existe para la fecha consultada (pago) o hoy Caracas
    if tasa:
"""
    if old_body not in text:
        raise SystemExit("validacion body anchor not found")
    text = text.replace(old_body, new_body, 1)

    path.write_text(text, encoding="utf-8")
    print("Patched tasa_cambio_validacion.py")


def write_sql() -> None:
    path = ROOT / "sql" / "2026-03-21_pagos_moneda_tasa_bs.sql"
    path.write_text(
        """-- Pagos: auditoria moneda / tasa Bs->USD (fecha de pago = clave de tasa en tasas_cambio_diaria)
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS moneda_registro VARCHAR(10);
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS monto_bs_original NUMERIC(15, 2);
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS tasa_cambio_bs_usd NUMERIC(15, 6);
ALTER TABLE pagos ADD COLUMN IF NOT EXISTS fecha_tasa_referencia DATE;
COMMENT ON COLUMN pagos.monto_pagado IS 'Monto en USD para cartera; si moneda_registro=BS, convertido con tasa del dia fecha_tasa_referencia.';
""",
        encoding="utf-8",
    )
    print("Wrote", path)


def main() -> None:
    patch_cobros_publico()
    patch_recibo_pdf()
    patch_pagos_endpoint()
    patch_schemas_pago()
    patch_validacion()
    write_sql()


if __name__ == "__main__":
    main()
