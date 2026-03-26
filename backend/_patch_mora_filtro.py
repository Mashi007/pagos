from pathlib import Path

p = Path(__file__).resolve().parent / "app/api/v1/endpoints/reportes/reportes_morosidad.py"
s = p.read_text(encoding="utf-8", errors="ignore")

old_detail = """            .where(
                Cliente.estado == "MORA",
                Cuota.fecha_pago.is_(None),
                func.extract("year", Cuota.fecha_vencimiento) == ano,
                func.extract("month", Cuota.fecha_vencimiento) == mes,
            )"""

new_detail = """            .where(
                Cliente.estado == "ACTIVO",
                Prestamo.estado == "APROBADO",
                Cuota.fecha_pago.is_(None),
                func.extract("year", Cuota.fecha_vencimiento) == ano,
                func.extract("month", Cuota.fecha_vencimiento) == mes,
            )"""

old_res = """    where_resumen = [
        Cliente.estado == "MORA",
        Cuota.fecha_pago.is_(None),
    ]"""

new_res = """    where_resumen = [
        Cliente.estado == "ACTIVO",
        Prestamo.estado == "APROBADO",
        Cuota.fecha_pago.is_(None),
    ]"""

if old_detail not in s:
    raise SystemExit("detail block not found")
if old_res not in s:
    raise SystemExit("resumen block not found")

s = s.replace(old_detail, new_detail, 1)
s = s.replace(old_res, new_res, 1)
p.write_text(s, encoding="utf-8")
print("patched OK")
