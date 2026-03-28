"""One-off patch: fecha reporte de pago en recibo cartera."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

pdf_path = ROOT / "app" / "services" / "cobros" / "recibo_pago_cartera_pdf.py"
ep_path = ROOT / "app" / "api" / "v1" / "endpoints" / "estado_cuenta_publico.py"

t = pdf_path.read_text(encoding="utf-8")

t = t.replace(
    "from app.services.tasa_cambio_service import fecha_hoy_caracas\n\n_LOGO_PATH",
    "_LOGO_PATH",
    1,
)

old_sig = """def generar_recibo_pago_cartera_pdf(
    *,
    referencia_documento: str,
    fecha_pago_display: str,
    titular_credito: str,"""

new_sig = """def generar_recibo_pago_cartera_pdf(
    *,
    referencia_documento: str,
    fecha_reporte_aprobacion_display: str,
    fecha_pago_display: str,
    titular_credito: str,"""

if old_sig not in t:
    raise SystemExit("pdf: signature block not found")
t = t.replace(old_sig, new_sig, 1)

old_block = """    fecha_emision = fecha_hoy_caracas().strftime("%d/%m/%Y")
    info = [
        [
            Paragraph("FECHA DE EMISION", label_style),
            Paragraph(fecha_emision, value_style),
            Paragraph("FECHA DE PAGO", label_style),
            Paragraph(fecha_pago_display or "-", value_style),
        ],"""

new_block = """    info = [
        [
            Paragraph("Fecha de reporte de pago", label_style),
            Paragraph(fecha_reporte_aprobacion_display or "-", value_style),
            Paragraph("FECHA DE PAGO", label_style),
            Paragraph(fecha_pago_display or "-", value_style),
        ],"""

if old_block not in t:
    raise SystemExit("pdf: fecha block not found")
t = t.replace(old_block, new_block, 1)

pdf_path.write_text(t, encoding="utf-8")
print("patched", pdf_path)

e = ep_path.read_text(encoding="utf-8")
needle = """    fp = getattr(pago, "fecha_pago", None)
    fecha_pago_display = fp.strftime("%d/%m/%Y %H:%M") if fp and hasattr(fp, "strftime") else "-"
"""

insert = """    fp = getattr(pago, "fecha_pago", None)
    fecha_pago_display = fp.strftime("%d/%m/%Y %H:%M") if fp and hasattr(fp, "strftime") else "-"
    f_rep = getattr(pago, "fecha_conciliacion", None) or getattr(pago, "fecha_registro", None)
    fecha_reporte_aprobacion_display = (
        f_rep.strftime("%d/%m/%Y %H:%M") if f_rep and hasattr(f_rep, "strftime") else "-"
    )

"""

if needle not in e:
    raise SystemExit("endpoint: needle not found")
e = e.replace(needle, insert, 1)

call_old = """    pdf_bytes = generar_recibo_pago_cartera_pdf(
        referencia_documento=referencia,
        fecha_pago_display=fecha_pago_display,
"""

call_new = """    pdf_bytes = generar_recibo_pago_cartera_pdf(
        referencia_documento=referencia,
        fecha_reporte_aprobacion_display=fecha_reporte_aprobacion_display,
        fecha_pago_display=fecha_pago_display,
"""

if call_old not in e:
    raise SystemExit("endpoint: call block not found")
e = e.replace(call_old, call_new, 1)

ep_path.write_text(e, encoding="utf-8")
print("patched", ep_path)
