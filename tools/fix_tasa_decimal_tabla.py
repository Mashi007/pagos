# -*- coding: utf-8 -*-
"""Fix manual tasa input: allow typing decimals (local string state); clarify no BD insert."""
from pathlib import Path

TAB = Path(__file__).resolve().parents[1] / "frontend" / "src" / "components" / "pagos" / "TablaEditablePagos.tsx"
t = TAB.read_text(encoding="utf-8")

HELPER_INSERT = """
/** Entrada de tasa manual (Bs/USD): texto para permitir decimales mientras se escribe. */
function TasaManualInput({
  row,
  onUpdateCell,
}: {
  row: PagoExcelRow
  onUpdateCell: (
    row: PagoExcelRow,
    field: string,
    value: string | number
  ) => void
}) {
  const [text, setText] = useState(() =>
    row.tasa_cambio_manual != null && row.tasa_cambio_manual !== ('' as unknown as number)
      ? String(row.tasa_cambio_manual)
      : ''
  )

  useEffect(() => {
    const v = row.tasa_cambio_manual
    if (v != null && typeof v === 'number' && Number.isFinite(v)) {
      setText(String(v))
    } else if (v == null || v === undefined) {
      setText('')
    }
  }, [row._rowIndex, row.tasa_cambio_manual])

  return (
    <div className="space-y-0.5">
      <input
        type="text"
        inputMode="decimal"
        autoComplete="off"
        className="w-full rounded border border-amber-300 p-1 text-xs"
        placeholder="Ej: 526.12"
        value={text}
        onChange={e => {
          let s = e.target.value.trim().replace(',', '.')
          if (s === '') {
            setText('')
            onUpdateCell(row, 'tasa_cambio_manual', '')
            return
          }
          if (!/^\d*\.?\d*$/.test(s)) return
          setText(s)
          if (s === '.' || s.endsWith('.')) {
            return
          }
          const n = parseFloat(s)
          if (Number.isFinite(n) && n > 0) {
            onUpdateCell(row, 'tasa_cambio_manual', n)
          }
        }}
        onBlur={() => {
          const s = text.trim().replace(',', '.')
          if (s === '' || s === '.') {
            setText('')
            onUpdateCell(row, 'tasa_cambio_manual', '')
            return
          }
          const n = parseFloat(s)
          if (Number.isFinite(n) && n > 0) {
            onUpdateCell(row, 'tasa_cambio_manual', n)
            setText(String(n))
          } else {
            setText('')
            onUpdateCell(row, 'tasa_cambio_manual', '')
          }
        }}
      />
      <p className="text-[10px] leading-tight text-amber-900/80">
        No se guarda en la tabla de tasas diarias; solo aplica a este pago.
      </p>
    </div>
  )
}

"""

# Insert after normMoneda function closing brace - find "function normMoneda" and insert after next "}\n\nfunction prestamoIdVacio"
anchor = "function normMoneda(v: unknown): 'USD' | 'BS' {\n  const s = String(v ?? 'USD')\n    .trim()\n    .toUpperCase()\n  return s === 'BS' ? 'BS' : 'USD'\n}\n\nfunction prestamoIdVacio"
if anchor not in t:
    raise SystemExit("normMoneda anchor not found")
t = t.replace(
    anchor,
    "function normMoneda(v: unknown): 'USD' | 'BS' {\n  const s = String(v ?? 'USD')\n    .trim()\n    .toUpperCase()\n  return s === 'BS' ? 'BS' : 'USD'\n}\n"
    + HELPER_INSERT
    + "\nfunction prestamoIdVacio",
    1,
)

# Replace manual input block with TasaManualInput
old_block = """                    return (
                      <input
                        type="number"
                        step="0.000001"
                        className="w-full rounded border border-amber-300 p-1 text-xs"
                        placeholder="Manual"
                        value={row.tasa_cambio_manual ?? ''}
                        onChange={e =>
                          onUpdateCell(row, 'tasa_cambio_manual', e.target.value)
                        }
                      />
                    )"""
new_block = """                    return (
                      <TasaManualInput row={row} onUpdateCell={onUpdateCell} />
                    )"""

if old_block not in t:
    raise SystemExit("old manual input block not found")
t = t.replace(old_block, new_block, 1)

# Help paragraph extend - add line about BD
old_p = """          pago; si no existe, ingrese la tasa manual (Bs por 1 USD) en la columna
          correspondiente.
        </p>"""
new_p = """          pago; si no existe, ingrese la tasa manual (Bs por 1 USD) en la columna
          correspondiente. Esa tasa no se copia a la tabla de tasas diarias (solo queda
          en el registro del pago); para dejarla en el calendario de tasas use Administracion.
        </p>"""
if old_p not in t:
    raise SystemExit("help paragraph not found")
t = t.replace(old_p, new_p, 1)

TAB.write_text(t, encoding="utf-8")
print("ok")
