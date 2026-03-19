# python scripts/patch_cobros_importado_estado.py
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend/app/api/v1/endpoints/cobros.py"
t = p.read_text(encoding="utf-8")

t = t.replace(
    '    counts = {"pendiente": 0, "en_revision": 0, "aprobado": 0, "rechazado": 0}',
    '    counts = {"pendiente": 0, "en_revision": 0, "aprobado": 0, "rechazado": 0, "importado": 0}',
    1,
)
t = t.replace(
    '    counts["total"] = sum(counts[k] for k in ("pendiente", "en_revision", "aprobado", "rechazado"))',
    '    counts["total"] = sum(counts[k] for k in ("pendiente", "en_revision", "aprobado", "rechazado", "importado"))',
    1,
)

old_edit = '    if pr.estado == "aprobado":\n        raise HTTPException(status_code=400, detail="No se puede editar un pago ya aprobado.")'
new_edit = '''    if pr.estado in ("aprobado", "importado"):
        raise HTTPException(status_code=400, detail="No se puede editar un pago ya aprobado o importado a pagos.")'''
if old_edit in t:
    t = t.replace(old_edit, new_edit, 1)

old_ap = '    if pr.estado == "aprobado":\n        try:\n            _crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)'
if old_ap in t:
    ins = '''    if pr.estado == "importado":
        return {"ok": True, "mensaje": "Ya importado a la tabla de pagos."}
    if pr.estado == "aprobado":
        try:
            _crear_pago_desde_reportado_y_aplicar_cuotas(db, pr, usuario_email)'''
    t = t.replace(old_ap, ins, 1)

p.write_text(t, encoding="utf-8")
print("patched cobros importado handling")
