import { useCallback, useEffect, useState } from 'react'

import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query'

import { CreditCard, Download, RefreshCw } from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import {
  getPrestamosCandidatosDriveSnapshot,
  postPrestamosCandidatosDriveRefrescar,
  type PrestamoCandidatoDriveFila,
} from '../services/prestamosCandidatosDriveService'
import { toast } from 'sonner'
import { getErrorMessage } from '../types/errors'

const QK_BASE = ['actualizaciones', 'prestamos-drive', 'snapshot'] as const

/** Filas por petición (offset crece de PAGE_SIZE en PAGE_SIZE). */
const PAGE_SIZE = 100
/** Máximo de filas acumulables en pantalla (20 × 100); alineado al límite habitual del API. */
const MAX_ROWS_UI = 2000

function strPayload(p: PrestamoCandidatoDriveFila['payload'], key: string): string {
  const v = p[key]
  if (v == null) return '—'
  return String(v)
}

function escapeCsvCell(s: string): string {
  const t = String(s ?? '').replace(/"/g, '""')
  if (/[",\n\r]/.test(t)) return `"${t}"`
  return t
}

function exportarCsvVistaActual(filas: PrestamoCandidatoDriveFila[]) {
  const headers = [
    'fila',
    'cedula_e',
    'producto',
    'total_n',
    'modalidad_s',
    'fecha_q',
    'cuotas_r',
    'analista_j',
    'concesionario_k',
    'modelo_i',
    'estado',
  ]
  const lines = [headers.join(',')]
  for (const r of filas) {
    const p = r.payload
    const ok = p.cedula_valida === true
    const dup = p.duplicada_en_hoja === true
    let estado = 'revisión'
    if (!ok) estado = `inválida: ${String(p.cedula_error ?? '')}`
    else if (dup) estado = 'repetida_hoja'
    lines.push(
      [
        r.sheet_row_number,
        strPayload(p, 'col_e_cedula'),
        strPayload(p, 'producto'),
        strPayload(p, 'col_n_total_financiamiento'),
        strPayload(p, 'col_s_modalidad_pago'),
        strPayload(p, 'col_q_fecha'),
        strPayload(p, 'col_r_numero_cuotas'),
        strPayload(p, 'col_j_analista'),
        strPayload(p, 'col_k_concesionario'),
        strPayload(p, 'col_i_modelo_vehiculo'),
        estado,
      ]
        .map(v => escapeCsvCell(String(v)))
        .join(',')
    )
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `candidatos-prestamos-drive-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function TableSkeletonRows({ n = 6 }: { n?: number }) {
  return (
    <>
      {Array.from({ length: n }).map((_, i) => (
        <tr key={i} className="border-t">
          {Array.from({ length: 11 }).map((__, j) => (
            <td key={j} className="px-3 py-2">
              <div className="h-4 animate-pulse rounded bg-muted" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

export default function ActualizacionesPrestamosDrivePage() {
  const qc = useQueryClient()
  const [cedulaInput, setCedulaInput] = useState('')
  const [cedulaDebounced, setCedulaDebounced] = useState('')
  const [forzarVacio, setForzarVacio] = useState(false)

  useEffect(() => {
    const t = window.setTimeout(() => setCedulaDebounced(cedulaInput.trim()), 400)
    return () => window.clearTimeout(t)
  }, [cedulaInput])

  const q = useInfiniteQuery({
    queryKey: [...QK_BASE, cedulaDebounced],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      getPrestamosCandidatosDriveSnapshot(
        PAGE_SIZE,
        pageParam as number,
        cedulaDebounced || undefined
      ),
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, p) => sum + p.filas.length, 0)
      const total = lastPage.total ?? 0
      if (loaded >= total) return undefined
      if (lastPage.filas.length === 0) return undefined
      if (loaded >= MAX_ROWS_UI) return undefined
      return loaded
    },
  })

  const rows = q.data?.pages.flatMap(p => p.filas) ?? []
  const first = q.data?.pages[0]
  const total = first?.total ?? 0
  const totalSinFiltro = first?.total_sin_filtro
  const loadedCount = rows.length
  const cappedByUi = loadedCount >= MAX_ROWS_UI && loadedCount < total

  const onRecalcular = useCallback(async () => {
    try {
      const res = await postPrestamosCandidatosDriveRefrescar({
        forzar: forzarVacio,
      })
      if (res?.omitido === true) {
        toast.message(
          (res.motivo as string) === 'tabla_drive_sin_filas'
            ? 'No se recalculó: la tabla drive está vacía (se mantiene el snapshot anterior). Marque «Forzar…» para vaciar el snapshot.'
            : 'Recálculo omitido.'
        )
      } else {
        const motivo = res?.motivo as string | undefined
        if (motivo === 'forzar_con_drive_vacio') {
          toast.success('Snapshot vaciado (drive sin filas, recálculo forzado).')
        } else {
          toast.success(
            `Snapshot actualizado: ${Number(res.candidatos_insertados ?? 0)} candidato(s).`
          )
        }
      }
      await qc.resetQueries({ queryKey: [...QK_BASE, cedulaDebounced] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo recalcular')
    }
  }, [qc, forzarVacio, cedulaDebounced])

  const onVolverInicio = useCallback(() => {
    void qc.resetQueries({ queryKey: [...QK_BASE, cedulaDebounced] })
  }, [qc, cedulaDebounced])

  const fmtCaracas = useCallback((iso: string | null | undefined) => {
    if (!iso) return '—'
    try {
      return new Date(iso).toLocaleString('es-VE', { timeZone: 'America/Caracas' })
    } catch {
      return iso
    }
  }, [])

  const estadoFila = useCallback((p: PrestamoCandidatoDriveFila['payload']) => {
    const ok = p.cedula_valida === true
    const dup = p.duplicada_en_hoja === true
    if (!ok) {
      return (
        <span className="text-red-600">
          Cédula: {String(p.cedula_error ?? 'inválida')}
        </span>
      )
    }
    if (dup) return <span className="text-amber-700">Repetida en hoja</span>
    return <span className="text-emerald-700">Listo para revisión</span>
  }, [])

  const showSkeleton = q.isPending && !q.data
  const isBusy = q.isFetching || q.isFetchingNextPage

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Préstamos"
        description="Actualizaciones: cédulas en CONCILIACIÓN (columna E) sin ningún préstamo en el sistema. Lista paginada por offset (100 filas por carga). El job programado recalcula domingo y miércoles ~04:05 (tras sync 04:00 Caracas). Solo administradores."
        icon={CreditCard}
      />

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-lg">Candidatos desde Drive</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {cedulaDebounced && totalSinFiltro != null ? (
                <>
                  Coincidencias: <strong>{total}</strong> de {totalSinFiltro} en snapshot
                </>
              ) : (
                <>
                  Total: <strong>{total}</strong>
                </>
              )}
              {' · '}
              Mostrando: <strong>{loadedCount}</strong>
              {' · '}
              Último sync hoja: {fmtCaracas(first?.drive_synced_at ?? null)}
              {' · '}
              Snapshot: {fmtCaracas(first?.computed_at ?? null)}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => exportarCsvVistaActual(rows)}
              disabled={rows.length === 0 || isBusy}
            >
              <Download className="mr-2 h-4 w-4" />
              Exportar CSV
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onRecalcular()}
              disabled={isBusy}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${isBusy ? 'animate-spin' : ''}`} />
              Recalcular ahora
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
            <div className="min-w-[200px] flex-1 space-y-1">
              <label htmlFor="filtro-cedula" className="text-sm font-medium text-foreground">
                Filtrar por cédula
              </label>
              <Input
                id="filtro-cedula"
                placeholder="Ej. V12345678 o parte del número"
                value={cedulaInput}
                onChange={e => setCedulaInput(e.target.value)}
                autoComplete="off"
              />
            </div>
            <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-input accent-primary"
                checked={forzarVacio}
                onChange={e => setForzarVacio(e.target.checked)}
              />
              Forzar recálculo si drive vacío (vacía el snapshot)
            </label>
          </div>

          {cappedByUi && (
            <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
              Se muestran como máximo {MAX_ROWS_UI} filas en pantalla. Exporte el CSV por tramos o refine el
              filtro de cédula. En total hay <strong>{total}</strong> coincidencias.
            </p>
          )}

          {q.isError && (
            <p className="text-sm text-red-600" role="alert">
              {getErrorMessage(q.error) || 'Error al cargar'}
            </p>
          )}

          <div className="overflow-x-auto rounded-md border">
            <table className="w-full min-w-[1040px] text-left text-sm">
              <thead className="bg-muted/60">
                <tr>
                  <th className="px-3 py-2">Fila</th>
                  <th className="px-3 py-2">Cédula (E)</th>
                  <th className="px-3 py-2">Producto</th>
                  <th className="px-3 py-2">Total (N)</th>
                  <th className="px-3 py-2">Modalidad (S)</th>
                  <th className="px-3 py-2">Fecha (Q)</th>
                  <th className="px-3 py-2">Cuotas (R)</th>
                  <th className="px-3 py-2">Analista (J)</th>
                  <th className="px-3 py-2">Concesionario (K)</th>
                  <th className="px-3 py-2">Modelo (I)</th>
                  <th className="px-3 py-2">Estado</th>
                </tr>
              </thead>
              <tbody>
                {showSkeleton && <TableSkeletonRows />}
                {!showSkeleton &&
                  rows.map(r => (
                    <tr key={`${r.id}-${r.sheet_row_number}`} className="border-t">
                      <td className="px-3 py-2 font-mono">{r.sheet_row_number}</td>
                      <td className="px-3 py-2 font-mono">{strPayload(r.payload, 'col_e_cedula')}</td>
                      <td className="px-3 py-2 text-xs">{strPayload(r.payload, 'producto')}</td>
                      <td className="px-3 py-2">{strPayload(r.payload, 'col_n_total_financiamiento')}</td>
                      <td className="px-3 py-2">{strPayload(r.payload, 'col_s_modalidad_pago')}</td>
                      <td className="px-3 py-2 whitespace-nowrap">
                        {strPayload(r.payload, 'col_q_fecha')}
                      </td>
                      <td className="px-3 py-2">{strPayload(r.payload, 'col_r_numero_cuotas')}</td>
                      <td className="px-3 py-2">{strPayload(r.payload, 'col_j_analista')}</td>
                      <td className="px-3 py-2">{strPayload(r.payload, 'col_k_concesionario')}</td>
                      <td
                        className="px-3 py-2 max-w-[140px] truncate"
                        title={strPayload(r.payload, 'col_i_modelo_vehiculo')}
                      >
                        {strPayload(r.payload, 'col_i_modelo_vehiculo')}
                      </td>
                      <td className="px-3 py-2 text-xs">{estadoFila(r.payload)}</td>
                    </tr>
                  ))}
                {!showSkeleton && !q.isPending && rows.length === 0 && (
                  <tr>
                    <td className="px-3 py-6 text-muted-foreground" colSpan={11}>
                      No hay candidatos: todas las cédulas del Drive ya tienen al menos un préstamo, o el
                      snapshot está vacío. Verifique la sincronización de CONCILIACIÓN en Configuración (Google)
                      y el job automático (dom/mié 04:00 sync + 04:05 snapshot si está activo en servidor).
                      {cedulaDebounced ? ' Pruebe otro filtro de cédula.' : ''}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {q.hasNextPage && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => void q.fetchNextPage()}
                disabled={q.isFetchingNextPage || isBusy}
              >
                {q.isFetchingNextPage ? 'Cargando…' : `Cargar más (${PAGE_SIZE} filas, offset ${loadedCount})`}
              </Button>
            )}
            {loadedCount > PAGE_SIZE && (
              <Button type="button" variant="ghost" size="sm" onClick={() => onVolverInicio()}>
                Volver al inicio (descartar páginas cargadas)
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
