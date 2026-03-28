from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "services" / "estado_cuenta_pdf.py"
t = p.read_text(encoding="utf-8")
old = """            pid = pr.get("recibo_prestamo_id")
            cid = pr.get("recibo_cuota_id")
            puede = bool(pid and cid and base_url and recibo_token)
            if puede:
                url_r = f"{base_url}/api/v1/estado-cuenta/public/recibo-cuota?token={recibo_token}&prestamo_id={pid}&cuota_id={cid}"
                rec_cell = Paragraph(
                    f'<a href="{url_r}" color="{COLOR_ACCENT}">Ver recibo</a>',
                    styles["EC_Link"],
                )
            else:
                rec_cell = Paragraph('<font color="#94a3b8">\u2014</font>', styles["EC_Link"])"""
if old not in t:
    old2 = old.replace("\u2014", "")
    if old2 in t:
        old = old2
    else:
        raise SystemExit("old snippet not found")
new = """            pago_row_id = pr.get("pago_id")
            puede_rec = bool(pago_row_id and base_url and recibo_token)
            if puede_rec:
                url_r = f"{base_url}/api/v1/estado-cuenta/public/recibo-pago?token={recibo_token}&pago_id={pago_row_id}"
                rec_cell = Paragraph(
                    f'<a href="{url_r}" color="{COLOR_ACCENT}">Ver recibo</a>',
                    styles["EC_Link"],
                )
            else:
                rec_cell = Paragraph('<font color="#94a3b8">-</font>', styles["EC_Link"])"""
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok")
