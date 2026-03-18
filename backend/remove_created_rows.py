from pathlib import Path
p = Path("app/api/v1/endpoints/pagos.py")
t = p.read_text(encoding="utf-8", errors="replace")
t = t.replace(
    "        results: list[dict] = []\n        created_rows: list[Pago] = []\n        try:",
    "        results: list[dict] = []\n        try:",
)
t = t.replace(
    '                results.append({"index": idx, "success": True, "pago": _pago_to_response(row)})\n                created_rows.append(row)',
    '                results.append({"index": idx, "success": True, "pago": _pago_to_response(row)})',
)
p.write_text(t, encoding="utf-8")
print("done")
