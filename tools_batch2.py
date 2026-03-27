from pathlib import Path
path = Path("backend/app/api/v1/endpoints/pagos.py")
s = path.read_text(encoding="utf-8")
old = """            if payload.prestamo_id and payload.prestamo_id not in valid_prestamo_ids:

                errors_by_index[idx] = {\"error\": f\"Credito #{payload.prestamo_id} no existe.\", \"status_code\": 400}

                continue"""
new = """            if payload.prestamo_id and payload.prestamo_id not in valid_prestamo_ids:

                errors_by_index[idx] = {\"error\": f\"Credito #{payload.prestamo_id} no existe.\", \"status_code\": 400}

                continue

            if payload.prestamo_id and (prestamo_estado_por_id.get(payload.prestamo_id) or \"\").strip().upper() == \"DESISTIMIENTO\":

                errors_by_index[idx] = {

                    \"error\": \"El prestamo esta en desistimiento; no se registran pagos.\",

                    \"status_code\": 400,

                }

                continue"""
if old not in s:
    raise SystemExit("batch validation anchor not found")
path.write_text(s.replace(old, new, 1), encoding="utf-8", newline="\n")
print("batch validation ok")
