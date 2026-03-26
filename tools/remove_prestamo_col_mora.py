from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "backend/app/api/v1/endpoints/reportes/reportes_morosidad.py"
s = p.read_text(encoding="utf-8", errors="ignore")

old1 = """        ws.append(
            ["Cedula", "Nombre", "Prestamo ID", "Cuota", "Fecha Vencimiento", "Monto USD"]
        )

        rows = db.execute(
            select(
                Cliente.cedula.label("cedula"),
                Cliente.nombres.label("nombre"),
                Prestamo.id.label("prestamo_id"),
                Cuota.numero_cuota.label("numero_cuota"),"""

new1 = """        ws.append(
            ["Cedula", "Nombre", "Cuota", "Fecha Vencimiento", "Monto USD"]
        )

        rows = db.execute(
            select(
                Cliente.cedula.label("cedula"),
                Cliente.nombres.label("nombre"),
                Cuota.numero_cuota.label("numero_cuota"),"""

old2 = """                ws.append(
                    [
                        r.cedula or "",
                        r.nombre or "",
                        int(r.prestamo_id) if r.prestamo_id is not None else None,
                        int(r.numero_cuota) if r.numero_cuota is not None else None,
                        r.fecha_vencimiento.isoformat() if r.fecha_vencimiento else "",
                        round(_safe_float(r.monto), 2),
                    ]
                )
        else:
            ws.append(["", "Sin registros para este periodo", "", "", "", ""])"""

new2 = """                ws.append(
                    [
                        r.cedula or "",
                        r.nombre or "",
                        int(r.numero_cuota) if r.numero_cuota is not None else None,
                        r.fecha_vencimiento.isoformat() if r.fecha_vencimiento else "",
                        round(_safe_float(r.monto), 2),
                    ]
                )
        else:
            ws.append(["", "Sin registros para este periodo", "", "", ""])"""

if old1 not in s:
    raise SystemExit("block1 not found")
if old2 not in s:
    raise SystemExit("block2 not found")
s = s.replace(old1, new1, 1).replace(old2, new2, 1)
p.write_text(s, encoding="utf-8")
print("patched", p)
