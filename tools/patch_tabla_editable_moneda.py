"""Add Moneda + Tasa columns to TablaEditablePagos and wire updateCellValue in hook."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "frontend" / "src" / "components" / "pagos" / "TablaEditablePagos.tsx"
HOOK = ROOT / "frontend" / "src" / "hooks" / "useExcelUploadPagos.ts"

# --- TablaEditablePagos imports ---
t = TAB.read_text(encoding="utf-8")
old_imp = """import { Save, Loader2, Search } from 'lucide-react'

import type { PagoExcelRow } from '../../utils/pagoExcelValidation'

import { cedulaLookupParaFila } from '../../utils/pagoExcelValidation'"""
new_imp = """import { Save, Loader2, Search } from 'lucide-react'

import type { PagoExcelRow } from '../../utils/pagoExcelValidation'

import {
  cedulaLookupParaFila,
  convertirFechaParaBackendPago,
} from '../../utils/pagoExcelValidation'

import { pagoService } from '../../services/pagoService'

import { getTasaPorFecha } from '../../services/tasaCambioService'"""
if old_imp not in t:
    raise SystemExit("imports anchor not found")
t = t.replace(old_imp, new_imp, 1)

# Insert helper + hook after imports block (after select imports) - find first "function CeldaEditable"
marker = "function CeldaEditable({"
if marker not in t:
    raise SystemExit("CeldaEditable marker not found")

HELPER = """
function normMoneda(v: unknown): 'USD' | 'BS' {
  const s = String(v ?? 'USD')
    .trim()
    .toUpperCase()
  return s === 'BS' ? 'BS' : 'USD'
}

"""

t = t.replace(marker, HELPER + marker, 1)

# Find "export default function TablaEditablePagos" or "export function TablaEditablePagos"
m = re.search(r"export (?:default )?function TablaEditablePagos\s*\(", t)
if not m:
    raise SystemExit("TablaEditablePagos function not found")
# Insert state after opening brace of TablaEditablePagos - find first line after function TablaEditablePagos(...) {
start = m.end()
brace = t.find("{", start)
if brace < 0:
    raise SystemExit("brace not found")
# Insert after first const in function - simpler: after "export function TablaEditablePagos(props: FilaEditableProps) {" find next newline and insert

fn_sig = "export function TablaEditablePagos("
idx = t.find(fn_sig)
if idx < 0:
    # try default export name
    fn_sig = "export default function TablaEditablePagos("
    idx = t.find(fn_sig)
if idx < 0:
    raise SystemExit("function signature not found")

# find opening brace of this function
sub = t[idx:]
open_brace = sub.find("{")
if open_brace < 0:
    raise SystemExit("open brace")
insert_at = idx + open_brace + 1
# skip whitespace/newlines
while insert_at < len(t) and t[insert_at] in " \r\n\t":
    insert_at += 1

STATE_SNIP = """
  const [autorizadoBsPorCedula, setAutorizadoBsPorCedula] = useState<
    Record<string, boolean | null>
  >({})

  const [tasaBdPorFila, setTasaBdPorFila] = useState<
    Record<number, number | null | undefined>
  >({})

  useEffect(() => {
    let cancelled = false
    const lookups = new Set<string>()
    for (const row of rows) {
      const lk = cedulaLookupParaFila(row.cedula || '', row.numero_documento || '')
        .trim()
        .replace(/-/g, '')
        .toUpperCase()
      if (lk.length >= 5) lookups.add(lk)
    }
    ;(async () => {
      for (const lk of lookups) {
        if (cancelled) return
        if (autorizadoBsPorCedula[lk] !== undefined && autorizadoBsPorCedula[lk] !== null)
          continue
        try {
          const res = await pagoService.consultarCedulaReportarBs(lk)
          if (cancelled) return
          setAutorizadoBsPorCedula(prev => ({ ...prev, [lk]: res.en_lista }))
        } catch {
          if (cancelled) return
          setAutorizadoBsPorCedula(prev => ({ ...prev, [lk]: false }))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [rows])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      for (const row of rows) {
        const m = normMoneda((row as PagoExcelRow).moneda_registro)
        if (m !== 'BS') {
          setTasaBdPorFila(prev => {
            const next = { ...prev }
            delete next[row._rowIndex]
            return next
          })
          continue
        }
        const iso = convertirFechaParaBackendPago(row.fecha_pago || '')
        if (!iso) {
          setTasaBdPorFila(prev => ({ ...prev, [row._rowIndex]: null }))
          continue
        }
        setTasaBdPorFila(prev => ({ ...prev, [row._rowIndex]: undefined }))
        try {
          const t = await getTasaPorFecha(iso)
          if (cancelled) return
          setTasaBdPorFila(prev => ({
            ...prev,
            [row._rowIndex]: t?.tasa_oficial ?? null,
          }))
        } catch {
          if (cancelled) return
          setTasaBdPorFila(prev => ({ ...prev, [row._rowIndex]: null }))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [rows])

"""

# Need useEffect import - file already has useEffect in import { useEffect, useRef, useState }
if "useEffect" not in t[:500]:
    t = t.replace(
        "import { useEffect, useRef, useState } from 'react'",
        "import { useEffect, useRef, useState } from 'react'",
        1,
    )

# Insert STATE_SNIP right after function opening - but we need to find exact insertion point inside TablaEditablePagos
# The file structure: export function TablaEditablePagos(...) { ... first lines might be const validos
# Safer: insert after "export function TablaEditablePagos(props: FilaEditableProps) {" line

sig = "export function TablaEditablePagos(props: FilaEditableProps) {"
pos = t.find(sig)
if pos < 0:
    sig = "export default function TablaEditablePagos(props: FilaEditableProps) {"
    pos = t.find(sig)
if pos < 0:
    raise SystemExit("props signature not found")
brace_pos = pos + len(sig)
# insert after brace and newline
t = t[:brace_pos] + "\n" + STATE_SNIP + t[brace_pos:]

# Fix dependency: autorizadoBsPorCedula in useEffect causes eslint - use functional updates only; remove condition that skips refetch - simplify always set

# Replace the useEffect for autorizado with simpler version without reading autorizadoBsPorCedula in condition (stale)
old_ue = STATE_SNIP
new_ue = """
  const [autorizadoBsPorCedula, setAutorizadoBsPorCedula] = useState<
    Record<string, boolean | null>
  >({})

  const [tasaBdPorFila, setTasaBdPorFila] = useState<
    Record<number, number | null | undefined>
  >({})

  useEffect(() => {
    let cancelled = false
    const lookups = new Set<string>()
    for (const row of rows) {
      const lk = cedulaLookupParaFila(row.cedula || '', row.numero_documento || '')
        .trim()
        .replace(/-/g, '')
        .toUpperCase()
      if (lk.length >= 5) lookups.add(lk)
    }
    ;(async () => {
      for (const lk of lookups) {
        if (cancelled) return
        try {
          const res = await pagoService.consultarCedulaReportarBs(lk)
          if (cancelled) return
          setAutorizadoBsPorCedula(prev => ({ ...prev, [lk]: res.en_lista }))
        } catch {
          if (cancelled) return
          setAutorizadoBsPorCedula(prev => ({ ...prev, [lk]: false }))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [rows])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      for (const row of rows) {
        const m = normMoneda((row as PagoExcelRow).moneda_registro)
        if (m !== 'BS') {
          setTasaBdPorFila(prev => {
            const next = { ...prev }
            delete next[row._rowIndex]
            return next
          })
          continue
        }
        const iso = convertirFechaParaBackendPago(row.fecha_pago || '')
        if (!iso) {
          setTasaBdPorFila(prev => ({ ...prev, [row._rowIndex]: null }))
          continue
        }
        setTasaBdPorFila(prev => ({ ...prev, [row._rowIndex]: undefined }))
        try {
          const t = await getTasaPorFecha(iso)
          if (cancelled) return
          setTasaBdPorFila(prev => ({
            ...prev,
            [row._rowIndex]: t?.tasa_oficial ?? null,
          }))
        } catch {
          if (cancelled) return
          setTasaBdPorFila(prev => ({ ...prev, [row._rowIndex]: null }))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [rows])

"""
# We already inserted STATE_SNIP - replace it if we need fix - actually first insert duplicated - let me re-read file state

TAB.write_text(t, encoding="utf-8")
print("tabla: step1")
