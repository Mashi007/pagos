from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "frontend/src/components/notificaciones/PlantillasNotificaciones.tsx"
s = p.read_text(encoding="utf-8")
old = """  const tiposSugeridos = [
    'PAGO_1_DIA_ATRASADO',
    'PAGO_3_DIAS_ATRASADO',
    'PAGO_5_DIAS_ATRASADO',
    'PREJUDICIAL',
    'COBRANZA',
  ]"""
new = """  const tiposSugeridos = [
    'PAGO_1_DIA_ATRASADO',
    'PAGO_3_DIAS_ATRASADO',
    'PAGO_5_DIAS_ATRASADO',
    'PREJUDICIAL',
    'MASIVOS',
    'COBRANZA',
  ]"""
if old not in s:
    raise SystemExit("block not found")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("ok")
