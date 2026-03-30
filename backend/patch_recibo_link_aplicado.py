# Patch historico: COB-+RPC para aplicado_a_cuotas. El codigo en produccion usa
# claves ampliadas (estado_cuenta_datos / pago_reportado_documento). No re-ejecutar ciegamente.
# Patch: solo enlace "Ver recibo" activo cuando pago aplicado a cuotas (estado_cuenta + pdf)
import re

estado_cuenta_path = "app/api/v1/endpoints/estado_cuenta_publico.py"
pdf_path = "app/services/estado_cuenta_pdf.py"

# --- 1) estado_cuenta_publico.py: add Pago import
with open(estado_cuenta_path, "r", encoding="utf-8") as f:
    content = f.read()
if "from app.models.pago import Pago" not in content:
    content = content.replace(
        "from app.models.pago_reportado import PagoReportado\nfrom app.api.v1.endpoints.validadores",
        "from app.models.pago_reportado import PagoReportado\nfrom app.models.pago import Pago\nfrom app.api.v1.endpoints.validadores",
    )
    print("Added Pago import")
else:
    print("Pago import already present")

# --- 2) estado_cuenta_publico.py: add aplicado_a_cuotas to _obtener_recibos_cliente
old_dict = '''        out.append({
            "id": pr.id,
            "referencia_interna": getattr(pr, "referencia_interna", "") or "",
            "fecha_pago": fecha_str,
            "monto": float(getattr(pr, "monto", 0) or 0),
            "moneda": getattr(pr, "moneda", "BS") or "BS",
        })
    return out'''

new_dict = '''        out.append({
            "id": pr.id,
            "referencia_interna": getattr(pr, "referencia_interna", "") or "",
            "fecha_pago": fecha_str,
            "monto": float(getattr(pr, "monto", 0) or 0),
            "moneda": getattr(pr, "moneda", "BS") or "BS",
            "aplicado_a_cuotas": False,
        })
    if out:
        num_docs = ["COB-" + (r["referencia_interna"] or "")[:90] for r in out]
        pagos_aplicados = set(
            row[0] for row in db.execute(
                select(Pago.numero_documento).where(
                    Pago.numero_documento.in_(num_docs),
                    Pago.estado == "PAGADO",
                )
            ).all()
        )
        for r in out:
            r["aplicado_a_cuotas"] = ("COB-" + (r["referencia_interna"] or "")) in pagos_aplicados
    return out'''

if old_dict in content:
    content = content.replace(old_dict, new_dict)
    print("Updated _obtener_recibos_cliente")
else:
    print("_obtener_recibos_cliente block not found (maybe already patched)")

with open(estado_cuenta_path, "w", encoding="utf-8") as f:
    f.write(content)

# --- 3) estado_cuenta_pdf.py: link solo si aplicado_a_cuotas
with open(pdf_path, "r", encoding="utf-8") as f:
    pdf_content = f.read()

old_pdf = """            monto = f"{float(r.get('monto') or 0):,.2f} {r.get('moneda') or 'BS'}"
            if recibo_token:
                url = f"{base_url}/api/v1/cobros/public/recibo?token={recibo_token}&pago_id={r.get('id', '')}"
            else:
                url = f"{base_url}/api/v1/cobros/pagos-reportados/{r.get('id', '')}/recibo.pdf"
            link_cell = Paragraph(f'<a href="{url}" color="{COLOR_HEADER}">Ver recibo</a>', style_link)
            rows.append([ref, fecha, monto, link_cell])"""

new_pdf = """            monto = f"{float(r.get('monto') or 0):,.2f} {r.get('moneda') or 'BS'}"
            aplicado = r.get("aplicado_a_cuotas", False)
            if aplicado and base_url:
                if recibo_token:
                    url = f"{base_url}/api/v1/cobros/public/recibo?token={recibo_token}&pago_id={r.get('id', '')}"
                else:
                    url = f"{base_url}/api/v1/cobros/pagos-reportados/{r.get('id', '')}/recibo.pdf"
                link_cell = Paragraph(f'<a href="{url}" color="{COLOR_HEADER}">Ver recibo</a>', style_link)
            else:
                link_cell = Paragraph("&mdash;", style_link)
            rows.append([ref, fecha, monto, link_cell])"""

if old_pdf in pdf_content:
    pdf_content = pdf_content.replace(old_pdf, new_pdf)
    print("Updated estado_cuenta_pdf recibos link")
else:
    print("estado_cuenta_pdf block not found (check manually)")

with open(pdf_path, "w", encoding="utf-8") as f:
    f.write(pdf_content)

print("Done.")
