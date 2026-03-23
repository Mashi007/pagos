from pathlib import Path

P = Path(__file__).resolve().parents[1] / "frontend" / "src" / "hooks" / "useExcelUploadPagos.ts"
t = P.read_text(encoding="utf-8")
old = """          } else if (field === 'tasa_cambio_manual') {
            const n = parseFloat(String(value).replace(',', '.'))
            ;(updated as any).tasa_cambio_manual =
              Number.isFinite(n) && n > 0 ? n : undefined
          } else {"""
new = """          } else if (field === 'tasa_cambio_manual') {
            if (value === '' || value === null || value === undefined) {
              delete (updated as any).tasa_cambio_manual
            } else {
              const n = parseFloat(String(value).replace(',', '.'))
              ;(updated as any).tasa_cambio_manual =
                Number.isFinite(n) && n > 0 ? n : undefined
            }
          } else {"""
if old not in t:
    raise SystemExit("anchor not found")
P.write_text(t.replace(old, new, 1), encoding="utf-8")
print("hook ok")
