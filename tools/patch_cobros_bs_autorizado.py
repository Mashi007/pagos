from pathlib import Path

P = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "pagos.py"
text = P.read_text(encoding="utf-8")
old = """    if moneda_pr == "BS":

        if not pr.fecha_pago:"""
new = """    if moneda_pr == "BS":

        if not cedula_autorizada_para_bs(db, cedula_raw):

            return _err_con_pce(

                "Cedula no autorizada para pagos en bolivares",

                cedula_cliente=cedula_raw,

                prestamo_id=prestamo_id,

            )

        if not pr.fecha_pago:"""
if old not in text:
    raise SystemExit("cobros BS anchor not found")
text = text.replace(old, new, 1)
P.write_text(text, encoding="utf-8")
print("ok")
