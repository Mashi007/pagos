from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "backend/app/api/v1/endpoints/reportes/reportes_morosidad.py"
s = p.read_text(encoding="utf-8", errors="ignore")

old1 = """        ws.append(
            ["Cedula", "Nombre", "Cuota", "Fecha Vencimiento", "Monto USD"]
        )

        rows = db.execute(
            select(
                Cliente.cedula.label("cedula"),
                Cliente.nombres.label("nombre"),
                Cuota.numero_cuota.label("numero_cuota"),
                Cuota.fecha_vencimiento.label("fecha_vencimiento"),
                Cuota.monto.label("monto"),
            )"""

new1 = """        ws.append(
            ["Cedula", "Nombre", "Cuota", "Monto USD"]
        )

        rows = db.execute(
            select(
                Cliente.cedula.label("cedula"),
                Cliente.nombres.label("nombre"),
                Cuota.numero_cuota.label("numero_cuota"),
                Cuota.monto.label("monto"),
            )"""

old2 = """                ws.append(
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

new2 = """                ws.append(
                    [
                        r.cedula or "",
                        r.nombre or "",
                        int(r.numero_cuota) if r.numero_cuota is not None else None,
                        round(_safe_float(r.monto), 2),
                    ]
                )
        else:
            ws.append(["", "Sin registros para este periodo", "", ""])"""

if old1 not in s:
    raise SystemExit("block1 not found")
if old2 not in s:
    raise SystemExit("block2 not found")
p.write_text(s.replace(old1, new1, 1).replace(old2, new2, 1), encoding="utf-8")
print("OK")
