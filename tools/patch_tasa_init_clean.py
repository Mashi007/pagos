from pathlib import Path

P = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components" / "pagos" / "TablaEditablePagos.tsx"
t = P.read_text(encoding="utf-8")
old = """  const [text, setText] = useState(() =>
    row.tasa_cambio_manual != null && row.tasa_cambio_manual !== ('' as unknown as number)
      ? String(row.tasa_cambio_manual)
      : ''
  )"""
new = """  const [text, setText] = useState(() =>
    row.tasa_cambio_manual != null && typeof row.tasa_cambio_manual === 'number'
      ? String(row.tasa_cambio_manual)
      : ''
  )"""
if old not in t:
    raise SystemExit("useState init not found")
P.write_text(t.replace(old, new, 1), encoding="utf-8")
print("init ok")
