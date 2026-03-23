# -*- coding: utf-8 -*-
from pathlib import Path

path = Path(
    r"c:/Users/PORTATIL/Documents/BIBLIOTECA/GitHub/pagos/frontend/src/components/pagos/TablaEditablePagos.tsx"
)
text = path.read_text(encoding="utf-8")

text = text.replace(
    "import { useEffect, useRef, useState } from 'react'",
    "import { useEffect, useMemo, useRef, useState } from 'react'",
    1,
)

old_effects = """  const autoFilledRef = useRef<Set<number>>(new Set())

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

new_effects = """  const autoFilledRef = useRef<Set<number>>(new Set())

  const cedulaBsCacheRef = useRef<Map<string, boolean>>(new Map())

  const [localSaving, setLocalSaving] = useState<Set<number>>(new Set())

  const [autorizadoBsPorCedula, setAutorizadoBsPorCedula] = useState<
    Record<string, boolean | null>
  >({})

  const [tasaBdPorFila, setTasaBdPorFila] = useState<
    Record<number, number | null | undefined>
  >({})

  const cedulasFirma = useMemo(() => {
    const lookups = new Set<string>()
    for (const row of rows) {
      const lk = cedulaLookupParaFila(row.cedula || '', row.numero_documento || '')
        .trim()
        .replace(/-/g, '')
        .toUpperCase()
      if (lk.length >= 5) lookups.add(lk)
    }
    return [...lookups].sort().join('|')
  }, [rows])

  useEffect(() => {
    if (!cedulasFirma) return
    const lookups = cedulasFirma.split('|').filter(Boolean)
    let cancelled = false
    ;(async () => {
      for (const lk of lookups) {
        if (cancelled) return
        if (cedulaBsCacheRef.current.has(lk)) {
          const cached = cedulaBsCacheRef.current.get(lk)!
          setAutorizadoBsPorCedula(prev =>
            prev[lk] === cached ? prev : { ...prev, [lk]: cached }
          )
          continue
        }
        try {
          const res = await pagoService.consultarCedulaReportarBs(lk)
          if (cancelled) return
          cedulaBsCacheRef.current.set(lk, res.en_lista)
          setAutorizadoBsPorCedula(prev => ({ ...prev, [lk]: res.en_lista }))
        } catch {
          if (cancelled) return
          cedulaBsCacheRef.current.set(lk, false)
          setAutorizadoBsPorCedula(prev => ({ ...prev, [lk]: false }))
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [cedulasFirma])

  const tasaBsFirma = useMemo(() => {
    const parts: string[] = []
    for (const row of rows) {
      if (normMoneda(row.moneda_registro) !== 'BS') continue
      const iso = convertirFechaParaBackendPago(row.fecha_pago || '')
      parts.push(`${row._rowIndex}:${iso || ''}`)
    }
    return parts.sort().join('|')
  }, [rows])

  useEffect(() => {
    let cancelled = false
    const bsRowIndexes = new Set<number>()
    const byIso = new Map<string, number[]>()
    const sinFechaIdx: number[] = []

    for (const row of rows) {
      if (normMoneda(row.moneda_registro) !== 'BS') continue
      bsRowIndexes.add(row._rowIndex)
      const iso = convertirFechaParaBackendPago(row.fecha_pago || '')
      if (!iso) {
        sinFechaIdx.push(row._rowIndex)
        continue
      }
      const arr = byIso.get(iso) ?? []
      arr.push(row._rowIndex)
      byIso.set(iso, arr)
    }

    setTasaBdPorFila(prev => {
      const next = { ...prev }
      for (const key of Object.keys(next)) {
        const idx = Number(key)
        if (!bsRowIndexes.has(idx)) delete next[idx]
      }
      for (const idx of sinFechaIdx) {
        next[idx] = null
      }
      for (const idxs of byIso.values()) {
        for (const idx of idxs) {
          next[idx] = undefined
        }
      }
      return next
    })

    ;(async () => {
      for (const [iso, idxs] of byIso) {
        if (cancelled) return
        try {
          const t = await getTasaPorFecha(iso)
          if (cancelled) return
          const val = t?.tasa_oficial ?? null
          setTasaBdPorFila(prev => {
            const next = { ...prev }
            for (const idx of idxs) next[idx] = val
            return next
          })
        } catch {
          if (cancelled) return
          setTasaBdPorFila(prev => {
            const next = { ...prev }
            for (const idx of idxs) next[idx] = null
            return next
          })
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tasaBsFirma])"""

if old_effects not in text:
    raise SystemExit("old effects block not found")
text = text.replace(old_effects, new_effects, 1)

path.write_text(text, encoding="utf-8", newline="\n")
print("OK TablaEditablePagos.tsx")
