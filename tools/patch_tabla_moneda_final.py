# -*- coding: utf-8 -*-
"""Patch TablaEditablePagos + useExcelUploadPagos for moneda/tasa in carga masiva UI."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "frontend" / "src" / "components" / "pagos" / "TablaEditablePagos.tsx"
HOOK = ROOT / "frontend" / "src" / "hooks" / "useExcelUploadPagos.ts"

# ---- TablaEditablePagos ----
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
    raise SystemExit("TAB imports not found")
t = t.replace(old_imp, new_imp, 1)

helper = """
function normMoneda(v: unknown): 'USD' | 'BS' {
  const s = String(v ?? 'USD')
    .trim()
    .toUpperCase()
  return s === 'BS' ? 'BS' : 'USD'
}

"""
if "function normMoneda" not in t:
    t = t.replace("function prestamoIdVacio(v: unknown): boolean {", helper + "function prestamoIdVacio(v: unknown): boolean {", 1)

insert_after = """}: FilaEditableProps) {
  const autoFilledRef = useRef<Set<number>>(new Set())

  const [localSaving, setLocalSaving] = useState<Set<number>>(new Set())"""

state_block = """}: FilaEditableProps) {
  const autoFilledRef = useRef<Set<number>>(new Set())

  const [localSaving, setLocalSaving] = useState<Set<number>>(new Set())

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
        if (normMoneda(row.moneda_registro) !== 'BS') {
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
  }, [rows])"""

if insert_after not in t:
    raise SystemExit("TAB insert after not found")
t = t.replace(insert_after, state_block, 1)

# Table header: add after Monto th
old_th = """              <th className="min-w-[120px] border-r p-2 text-left font-semibold">
                Monto
              </th>

              <th className="min-w-[160px] border-r p-2 text-left font-semibold">
                Documento
              </th>"""
new_th = """              <th className="min-w-[120px] border-r p-2 text-left font-semibold">
                Monto
              </th>

              <th className="min-w-[100px] border-r p-2 text-left font-semibold">
                Moneda
              </th>

              <th className="min-w-[120px] border-r p-2 text-left font-semibold">
                Tasa (Bs/USD)
              </th>

              <th className="min-w-[160px] border-r p-2 text-left font-semibold">
                Documento
              </th>"""
if old_th not in t:
    raise SystemExit("TAB thead not found")
t = t.replace(old_th, new_th, 1)

# Table body: after Monto td block, before Documento
old_td = """                {/* Monto */}

                <td className="border-r p-2">
                  <CeldaEditable
                    value={row.monto_pagado || ''}
                    isValid={row._validation.monto_pagado?.isValid}
                    errorMsg={row._validation.monto_pagado?.message}
                    placeholder="0.00"
                    type="number"
                    onChange={v => onUpdateCell(row, 'monto_pagado', v)}
                  />
                </td>

                {/* Documento */}"""
new_td = """                {/* Monto */}

                <td className="border-r p-2">
                  <CeldaEditable
                    value={row.monto_pagado || ''}
                    isValid={row._validation.monto_pagado?.isValid}
                    errorMsg={row._validation.monto_pagado?.message}
                    placeholder="0.00"
                    type="number"
                    onChange={v => onUpdateCell(row, 'monto_pagado', v)}
                  />
                </td>

                {/* Moneda */}

                <td className="border-r p-2">
                  {(() => {
                    const lk = cedulaLookupParaFila(
                      row.cedula || '',
                      row.numero_documento || ''
                    )
                      .trim()
                      .replace(/-/g, '')
                      .toUpperCase()
                    const enAuth = lk.length >= 5 ? autorizadoBsPorCedula[lk] : null
                    const puedeBs = enAuth === true
                    const m = normMoneda(row.moneda_registro)
                    return (
                      <Select
                        value={m}
                        onValueChange={v => onUpdateCell(row, 'moneda_registro', v)}
                        disabled={enAuth === null}
                      >
                        <SelectTrigger className="h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="USD">USD</SelectItem>
                          <SelectItem value="BS" disabled={!puedeBs}>
                            Bs
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    )
                  })()}
                </td>

                {/* Tasa manual si BS y no hay en BD */}

                <td className="border-r p-2">
                  {(() => {
                    const m = normMoneda(row.moneda_registro)
                    if (m !== 'BS') {
                      return <span className="text-xs text-gray-400">-</span>
                    }
                    const tb = tasaBdPorFila[row._rowIndex]
                    if (tb === undefined) {
                      return (
                        <span className="text-xs text-blue-600">
                          <Loader2 className="mr-1 inline h-3 w-3 animate-spin" />
                          Tasa...
                        </span>
                    )
                    }
                    if (typeof tb === 'number') {
                      return (
                        <span className="text-xs text-green-800">
                          BD: {tb}
                        </span>
                      )
                    }
                    return (
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
                    )
                  })()}
                </td>

                {/* Documento */}"""
if old_td not in t:
    raise SystemExit("TAB tbody mont/doc not found")
t = t.replace(old_td, new_td, 1)

# noPuedeGuardar: extend - find block with const noPuedeGuardar =
old_ng = """                      const noPuedeGuardar =
                        row._hasErrors ||
                        sinCreditoElegido ||
                        sinCreditosActivos"""
new_ng = """                      const lkBs = cedulaLookupParaFila(
                        row.cedula || '',
                        row.numero_documento || ''
                      )
                        .trim()
                        .replace(/-/g, '')
                        .toUpperCase()
                      const enListaBs =
                        lkBs.length >= 5 ? autorizadoBsPorCedula[lkBs] : null
                      const monedaF = normMoneda(row.moneda_registro)
                      const tasaBd = tasaBdPorFila[row._rowIndex]
                      const tasaMan = row.tasa_cambio_manual
                      const bsBloqueado =
                        monedaF === 'BS' &&
                        (enListaBs !== true ||
                          tasaBd === undefined ||
                          (tasaBd === null &&
                            !(typeof tasaMan === 'number' && tasaMan > 0)))

                      const noPuedeGuardar =
                        row._hasErrors ||
                        sinCreditoElegido ||
                        sinCreditosActivos ||
                        bsBloqueado"""
if old_ng not in t:
    raise SystemExit("noPuedeGuardar block not found")
t = t.replace(old_ng, new_ng, 1)

# Help paragraph: add note about moneda/tasa
help_old = """        <p className="mt-1 text-xs text-blue-700">
          <strong>Crédito:</strong> si hay un solo crédito activo por cédula se
          carga automáticamente; si hay varios debe elegir en la lista.
          &quot;Sin crédito&quot; aplica cuando el cliente está registrado pero
          no tiene créditos activos (si no hay cliente, la cédula marca error).
        </p>"""
# file may have encoding - use regex-free smaller anchor
help_old2 = """          no tiene créditos activos (si no hay cliente, la cédula marca error).
        </p>
      </div>

      {/* Tabla */}"""
if help_old2 not in t:
    raise SystemExit("help anchor2 not found")
help_new2 = """          no tiene créditos activos (si no hay cliente, la cédula marca error).
        </p>

        <p className="mt-1 text-xs text-blue-700">
          <strong>Moneda / tasa:</strong> USD por defecto. Bolívares (Bs) solo si la
          cédula está en la lista autorizada. La tasa se toma de la BD por fecha de
          pago; si no existe, ingrese la tasa manual (Bs por 1 USD) en la columna
          correspondiente.
        </p>
      </div>

      {/* Tabla */}"""
t = t.replace(help_old2, help_new2, 1)

TAB.write_text(t, encoding="utf-8")
print("TablaEditablePagos OK")

# ---- useExcelUploadPagos updateCellValue ----
h = HOOK.read_text(encoding="utf-8")
old_u = """          } else if (field === 'conciliado') {
            updated.conciliado =
              value === 'si' || value === 'SI' || String(value) === '1'
          } else {
            ;(updated as any)[field] =
              field === 'monto_pagado' ? Number(value) || 0 : value
          }"""
new_u = """          } else if (field === 'conciliado') {
            updated.conciliado =
              value === 'si' || value === 'SI' || String(value) === '1'
          } else if (field === 'moneda_registro') {
            const m = String(value).toUpperCase() === 'BS' ? 'BS' : 'USD'
            ;(updated as any).moneda_registro = m
            if (m === 'USD') {
              delete (updated as any).tasa_cambio_manual
            }
          } else if (field === 'tasa_cambio_manual') {
            const n = parseFloat(String(value).replace(',', '.'))
            ;(updated as any).tasa_cambio_manual =
              Number.isFinite(n) && n > 0 ? n : undefined
          } else {
            ;(updated as any)[field] =
              field === 'monto_pagado' ? Number(value) || 0 : value
          }"""
if old_u not in h:
    raise SystemExit("HOOK updateCell branch not found")
h = h.replace(old_u, new_u, 1)

HOOK.write_text(h, encoding="utf-8")
print("useExcelUploadPagos OK")
