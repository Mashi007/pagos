# -*- coding: utf-8 -*-
"""Apply pagos realizados changes to estado_cuenta_datos, estado_cuenta_pdf, callers."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATOS = ROOT / "app" / "services" / "estado_cuenta_datos.py"
PDF = ROOT / "app" / "services" / "estado_cuenta_pdf.py"

BLOCK_DATOS = '''

def _fmt_fecha_hora_pago_estado_cuenta(dt) -> str:
    if dt is None:
        return "-"
    try:
        if hasattr(dt, "strftime"):
            return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        pass
    return str(dt)


def _prestamo_cuota_recibo_desde_pago(db, pago_id: int):
    from typing import Optional, Tuple

    from sqlalchemy import select

    from app.models.cuota import Cuota
    from app.models.cuota_pago import CuotaPago

    row = db.execute(
        select(Cuota.prestamo_id, Cuota.id)
        .where(Cuota.pago_id == pago_id)
        .order_by(Cuota.numero_cuota.asc())
        .limit(1)
    ).first()
    if row:
        return int(row[0]), int(row[1])
    row = db.execute(
        select(Cuota.prestamo_id, Cuota.id)
        .join(CuotaPago, CuotaPago.cuota_id == Cuota.id)
        .where(CuotaPago.pago_id == pago_id)
        .order_by(Cuota.numero_cuota.asc())
        .limit(1)
    ).first()
    if row:
        return int(row[0]), int(row[1])
    return None


def listar_pagos_realizados_estado_cuenta(db, prestamo_ids: List[int]) -> List[dict]:
    """
    Pagos aplicados (tabla pagos, estado PAGADO) vinculados a los prestamos indicados.
    subtotal_usd usa monto_pagado (USD cartera). Columna Monto segun moneda_registro.
    """
    from sqlalchemy import select

    if not prestamo_ids:
        return []
    ids = sorted({int(x) for x in prestamo_ids if x is not None})
    if not ids:
        return []
    rows = db.execute(
        select(Pago)
        .where(
            Pago.prestamo_id.in_(ids),
            func.upper(func.coalesce(Pago.estado, "")) == "PAGADO",
        )
        .order_by(Pago.fecha_pago.desc(), Pago.id.desc())
    ).scalars().all()
    resultado: List[dict] = []
    for raw in rows:
        pg = raw[0] if hasattr(raw, "__getitem__") else raw
        pago_id = int(getattr(pg, "id", 0) or 0)
        prestamo_id = getattr(pg, "prestamo_id", None)
        banco = (getattr(pg, "institucion_bancaria", None) or "").strip() or "no disponible"
        fp = getattr(pg, "fecha_pago", None)
        fr = getattr(pg, "fecha_registro", None)
        moneda_raw = (getattr(pg, "moneda_registro", None) or "").strip().upper()
        es_bs = moneda_raw in ("BS", "BOLIVAR", "BOLIVARES")
        monto_usd = float(getattr(pg, "monto_pagado", 0) or 0)
        monto_bs_val = getattr(pg, "monto_bs_original", None)
        monto_bs_f = float(monto_bs_val) if monto_bs_val is not None else None
        tasa_val = getattr(pg, "tasa_cambio_bs_usd", None)
        tasa_f = float(tasa_val) if tasa_val is not None else None
        if es_bs:
            if monto_bs_f is not None:
                monto_display = f"{monto_bs_f:,.2f} Bs"
            else:
                monto_display = "Bs (monto no disponible en BD)"
            tasa_display = f"{tasa_f:,.6f}" if tasa_f is not None else "-"
        else:
            monto_display = f"{monto_usd:,.2f} USD"
            tasa_display = "-"
        rec = _prestamo_cuota_recibo_desde_pago(db, pago_id)
        if rec:
            rp, rc = rec
        else:
            rp = int(prestamo_id) if prestamo_id is not None else None
            rc = None
        resultado.append(
            {
                "pago_id": pago_id,
                "prestamo_id": int(prestamo_id) if prestamo_id is not None else None,
                "banco": banco,
                "fecha_pago_display": _fmt_fecha_hora_pago_estado_cuenta(fp),
                "fecha_registro_display": _fmt_fecha_hora_pago_estado_cuenta(fr),
                "monto_display": monto_display,
                "tasa_display": tasa_display,
                "subtotal_usd": monto_usd,
                "es_bs": es_bs,
                "recibo_prestamo_id": rp,
                "recibo_cuota_id": rc,
            }
        )
    return resultado

'''


def patch_datos() -> None:
    t = DATOS.read_text(encoding="utf-8")
    if "listar_pagos_realizados_estado_cuenta" in t:
        print("datos: skip listar (exists)")
    else:
        if "from app.models.cuota_pago import CuotaPago" not in t:
            t = t.replace(
                "from app.models.cuota import Cuota\nfrom app.models.pago import Pago",
                "from app.models.cuota import Cuota\nfrom app.models.cuota_pago import CuotaPago\nfrom app.models.pago import Pago",
                1,
            )
        anchor = "    return out\n\n\ndef _cargar_prestamo_para_estado_cuenta"
        if anchor not in t:
            anchor = "    return out\n\n\n\ndef _cargar_prestamo_para_estado_cuenta"
        if anchor not in t:
            raise SystemExit("datos anchor not found")
        t = t.replace(anchor, "    return out\n" + BLOCK_DATOS + "\n\ndef _cargar_prestamo_para_estado_cuenta", 1)
        DATOS.write_text(t, encoding="utf-8")
        print("datos: inserted listar")

    t = DATOS.read_text(encoding="utf-8")
    if '"pagos_realizados"' in t and "listar_pagos_realizados_estado_cuenta(db, [prestamo_id])" in t:
        print("datos: skip returns")
    else:
        old_ret = '''        "amortizaciones_por_prestamo": amortizaciones_por_prestamo,

    }'''
        new_ret = '''        "amortizaciones_por_prestamo": amortizaciones_por_prestamo,
        "pagos_realizados": listar_pagos_realizados_estado_cuenta(db, [prestamo_id]),
    }'''
        if old_ret not in t:
            raise SystemExit("datos return prestamo not found")
        t = t.replace(old_ret, new_ret, 1)
        old_m = '''        "amortizaciones_por_prestamo": [],

    }'''
        new_m = '''        "amortizaciones_por_prestamo": [],
        "pagos_realizados": [],
    }'''
        if old_m not in t:
            raise SystemExit("datos merged init not found")
        t = t.replace(old_m, new_m, 1)
        insert_after = '        merged["amortizaciones_por_prestamo"].extend(part["amortizaciones_por_prestamo"])\n\n    return merged'
        if insert_after not in t:
            raise SystemExit("datos cliente merge not found")
        t = t.replace(
            insert_after,
            '        merged["amortizaciones_por_prestamo"].extend(part["amortizaciones_por_prestamo"])\n\n'
            '    merged["pagos_realizados"] = listar_pagos_realizados_estado_cuenta(db, prestamo_ids)\n\n    return merged',
            1,
        )
        DATOS.write_text(t, encoding="utf-8")
        print("datos: patched returns")


def patch_pdf() -> None:
    t = PDF.read_text(encoding="utf-8")
    if "pagos_realizados" in t and "Pagos realizados" in t:
        print("pdf: skip")
        return
    old_sig = """def generar_pdf_estado_cuenta(

    cedula: str,

    nombre: str,

    prestamos: List[dict],

    cuotas_pendientes: List[dict],

    total_pendiente: float,

    fecha_corte: date,

    amortizaciones_por_prestamo: Optional[List[dict]] = None,

    recibos: Optional[List[dict]] = None,

    recibo_token: Optional[str] = None,

    base_url: str = "",

) -> bytes:"""
    new_sig = """def generar_pdf_estado_cuenta(

    cedula: str,

    nombre: str,

    prestamos: List[dict],

    cuotas_pendientes: List[dict],

    total_pendiente: float,

    fecha_corte: date,

    amortizaciones_por_prestamo: Optional[List[dict]] = None,

    pagos_realizados: Optional[List[dict]] = None,

    recibos: Optional[List[dict]] = None,

    recibo_token: Optional[str] = None,

    base_url: str = "",

) -> bytes:"""
    if old_sig not in t:
        # try compact
        old_sig2 = "def generar_pdf_estado_cuenta(\n    cedula: str,\n    nombre: str,\n    prestamos: List[dict],\n    cuotas_pendientes: List[dict],\n    total_pendiente: float,\n    fecha_corte: date,\n    amortizaciones_por_prestamo: Optional[List[dict]] = None,\n    recibos: Optional[List[dict]] = None,\n    recibo_token: Optional[str] = None,\n    base_url: str = \"\",\n) -> bytes:"
        if old_sig2 not in t:
            raise SystemExit("pdf signature not found")
        t = t.replace(
            old_sig2,
            "def generar_pdf_estado_cuenta(\n    cedula: str,\n    nombre: str,\n    prestamos: List[dict],\n    cuotas_pendientes: List[dict],\n    total_pendiente: float,\n    fecha_corte: date,\n    amortizaciones_por_prestamo: Optional[List[dict]] = None,\n    pagos_realizados: Optional[List[dict]] = None,\n    recibos: Optional[List[dict]] = None,\n    recibo_token: Optional[str] = None,\n    base_url: str = \"\",\n) -> bytes:",
            1,
        )
    else:
        t = t.replace(old_sig, new_sig, 1)

    insert_after = "        story.append(Spacer(1, 12))\n\n\n\n    # ----- Cuotas pendientes -----"
    block = r'''        story.append(Spacer(1, 12))


    # ----- Pagos realizados (tabla pagos) -----
    pagos_realizados = pagos_realizados or []
    if pagos_realizados:
        story.append(Paragraph("Pagos realizados", styles["SectionTitle"]))
        style_rec = ParagraphStyle(
            name="PagoReciboLink",
            fontSize=7,
            textColor=COLOR_HEADER,
            spaceAfter=2,
        )
        rows_p = [
            [
                "Banco",
                "Fecha de pago",
                "Fecha ingreso sistema",
                "Monto",
                "Tasa",
                "Subtotal (USD)",
                "Recibo",
            ]
        ]
        total_usd = 0.0
        for pr in pagos_realizados:
            total_usd += float(pr.get("subtotal_usd") or 0)
            pid = pr.get("recibo_prestamo_id")
            cid = pr.get("recibo_cuota_id")
            puede = (
                pid
                and cid
                and base_url
                and recibo_token
            )
            if puede:
                url_r = f"{base_url}/api/v1/estado-cuenta/public/recibo-cuota?token={recibo_token}&prestamo_id={pid}&cuota_id={cid}"
                rec_cell = Paragraph(f'<a href="{url_r}" color="{COLOR_HEADER}">Ver recibo</a>', style_rec)
            else:
                rec_cell = Paragraph("&mdash;", style_rec)
            rows_p.append(
                [
                    (pr.get("banco") or "no disponible")[:28],
                    (pr.get("fecha_pago_display") or "-")[:16],
                    (pr.get("fecha_registro_display") or "-")[:16],
                    (pr.get("monto_display") or "-")[:22],
                    str(pr.get("tasa_display") or "-")[:12],
                    f"{float(pr.get('subtotal_usd') or 0):,.2f}",
                    rec_cell,
                ]
            )
        rows_p.append(
            [
                "",
                "",
                "",
                "",
                "",
                f"{total_usd:,.2f}",
                Paragraph("<b>Total pagado (USD)</b>", styles["Normal"]),
            ]
        )
        tp = Table(
            rows_p,
            colWidths=[78, 62, 62, 64, 44, 56, 48],
        )
        tp.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADER_BG),
                    ("TEXTCOLOR", (0, 0), (-1, 0), "white"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (5, 0), (5, -2), "RIGHT"),
                    ("ALIGN", (5, -1), (5, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -2), ["white", COLOR_ROW_ALT]),
                    ("FONTSIZE", (0, 1), (-1, -1), 7),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("SPAN", (0, -1), (4, -1)),
                    ("ALIGN", (0, -1), (4, -1), "RIGHT"),
                ]
            )
        )
        story.append(tp)
        story.append(Spacer(1, 12))


    # ----- Cuotas pendientes -----'''
    if insert_after not in t:
        raise SystemExit("pdf insert anchor not found")
    t = t.replace(insert_after, block + "\n\n    # ----- Cuotas pendientes -----", 1)
    PDF.write_text(t, encoding="utf-8")
    print("pdf: patched")


def patch_callers() -> None:
    files = [
        ROOT / "app" / "api" / "v1" / "endpoints" / "estado_cuenta_publico.py",
        ROOT / "app" / "api" / "v1" / "endpoints" / "prestamos.py",
        ROOT / "app" / "services" / "liquidado_notificacion_service.py",
    ]
    needle = "amortizaciones_por_prestamo=datos.get(\"amortizaciones_por_prestamo\") or [],"
    repl = needle + "\n            pagos_realizados=datos.get(\"pagos_realizados\") or [],"
    for p in files:
        t = p.read_text(encoding="utf-8")
        if "pagos_realizados=datos.get" in t:
            print(p.name, "skip")
            continue
        if needle not in t:
            print(p.name, "needle missing")
            continue
        p.write_text(t.replace(needle, repl, 1), encoding="utf-8")
        print(p.name, "ok")

    pub = ROOT / "app" / "api" / "v1" / "endpoints" / "estado_cuenta_publico.py"
    t = pub.read_text(encoding="utf-8")
    needle2 = "amortizaciones_por_prestamo=datos.get(\"amortizaciones_por_prestamo\") or [],\n            recibos=recibos,"
    repl2 = "amortizaciones_por_prestamo=datos.get(\"amortizaciones_por_prestamo\") or [],\n            pagos_realizados=datos.get(\"pagos_realizados\") or [],\n            recibos=recibos,"
    if needle2 in t and "pagos_realizados=datos.get(\"pagos_realizados\") or []," not in t.split("recibos=recibos")[0][-400:]:
        t = t.replace(needle2, repl2, 1)
        pub.write_text(t, encoding="utf-8")
        print("estado_cuenta_publico second call ok")


def main() -> None:
    patch_datos()
    patch_pdf()
    patch_callers()


if __name__ == "__main__":
    main()
