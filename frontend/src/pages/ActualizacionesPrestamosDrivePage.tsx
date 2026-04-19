import { useCallback, useEffect, useState } from 'react'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  CreditCard,
  Download,
  Edit2,
  Loader2,
  RefreshCw,
  Save,
  Trash2,
} from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import {
  getPrestamosCandidatosDriveSnapshot,
  postPrestamosCandidatosDriveGuardarValidados100,
  postPrestamosCandidatosDriveRefrescar,
  type PrestamoCandidatoDriveFila,
} from '../services/prestamosCandidatosDriveService'
import { toast } from 'sonner'
import { getErrorMessage } from '../types/errors'

const QK_BASE = ['actualizaciones', 'prestamos-drive', 'snapshot'] as const

/** Filas por página (offset en API = (página − 1) × PAGE_SIZE). */
const PAGE_SIZE = 100
/** Botones numéricos visibles a la vez (ventana deslizante). */
const PAGE_WINDOW = 5

/** Ventana de números de página centrada hacia `current`, acotada a `totalPages`. */
function numerosPaginaVisibles(current: number, totalPages: number, maxButtons: number): number[] {
  if (totalPages <= maxButtons) {
    return Array.from({ length: totalPages }, (_, i) => i + 1)
  }
  const half = Math.floor(maxButtons / 2)
  let start = current - half
  let end = start + maxButtons - 1
  if (start < 1) {
    start = 1
    end = maxButtons
  }
  if (end > totalPages) {
    end = totalPages
    start = Math.max(1, end - maxButtons + 1)
  }
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
}

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

/** 1 formato cédula · 2 regla V vs tabla préstamos · 3 sin duplicado en hoja */
function validadoresTresFlags(p: PrestamoCandidatoDriveFila['payload']) {
  const formatoOk = (p.validador_formato_cedula_ok ?? p.cedula_valida) === true
  const hojaOk = (p.validador_sin_duplicado_en_hoja_ok ?? p.duplicada_en_hoja !== true) === true
  const nPrest = Number(p.prestamos_misma_cedula_norm_count ?? 0)
  const esV = p.cedula_es_tipo_v_venezolano === true
  const tablaVOk =
    (p.validador_v_max_un_prestamo_ok ?? !(esV && nPrest >= 1)) === true
  return { formatoOk, tablaVOk, hojaOk, nPrest, esV }
}

function exportarCsvVistaActual(filas: PrestamoCandidatoDriveFila[]) {
  const headers = [
    'fila',
    'cedula_e',
    'prestamos_misma_cedula_n',
    'es_tipo_v',
    'val_formato',
    'val_tabla_v',
    'val_hoja',
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
    const { formatoOk, tablaVOk, hojaOk, nPrest, esV } = validadoresTresFlags(p)
    const ok = p.cedula_valida === true
    const dup = p.duplicada_en_hoja === true
    let estado = 'revisión'
    if (!ok) estado = `inválida: ${String(p.cedula_error ?? '')}`
    else if (dup) estado = 'repetida_hoja'
    else if (!tablaVOk) estado = 'tipo_V: ya hay préstamo en tabla'
    else estado = 'listo'
    lines.push(
      [
        r.sheet_row_number,
        strPayload(p, 'col_e_cedula'),
        String(nPrest),
        esV ? 'si' : 'no',
        formatoOk ? 'ok' : 'no',
        tablaVOk ? 'ok' : 'no',
        hojaOk ? 'ok' : 'no',
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

/** Iconos de acción por fila (revisión tipo grilla). */
function AccionesPorFilaCandidatoDrive({
  fila,
  disabled,
}: {
  fila: PrestamoCandidatoDriveFila
  disabled: boolean
}) {
  const iconBtn =
    'h-8 w-8 shrink-0 rounded-md border border-slate-200 bg-white p-0 shadow-sm hover:bg-slate-50 disabled:opacity-50'
  const sr = fila.sheet_row_number

  return (
    <div className="flex flex-nowrap items-center justify-end gap-1">
      <Button
        type="button"
        variant="outline"
        size="icon"
        className={iconBtn}
        title={`Editar fila hoja ${sr} (próximamente)`}
        aria-label={`Editar fila ${sr}`}
        disabled={disabled}
        onClick={() =>
          toast.message(`Edición de fila ${sr} (hoja): próximamente.`)
        }
      >
        <Edit2 className="h-3.5 w-3.5 text-foreground" strokeWidth={2} aria-hidden />
      </Button>
      <Button
        type="button"
        variant="outline"
        size="icon"
        className={iconBtn}
        title={`Guardar solo esta fila en préstamos (próximamente). Mientras tanto use «Guardar (100%)» arriba.`}
        aria-label={`Guardar fila ${sr}`}
        disabled={disabled}
        onClick={() =>
          toast.message(
            `Guardar solo la fila ${sr}: próximamente. Use el botón «Guardar (100%)» para crear préstamos válidos en lote.`
          )
        }
      >
        <Save className="h-3.5 w-3.5 text-foreground" strokeWidth={2} aria-hidden />
      </Button>
      <Button
        type="button"
        variant="outline"
        size="icon"
        className={iconBtn}
        title={`Quitar candidato fila ${sr} (próximamente)`}
        aria-label={`Borrar fila ${sr}`}
        disabled={disabled}
        onClick={() =>
          toast.message(`Quitar candidato fila ${sr}: próximamente.`)
        }
      >
        <Trash2 className="h-3.5 w-3.5 text-red-600" strokeWidth={2} aria-hidden />
      </Button>
    </div>
  )
}

function TableSkeletonRows({ n = 6 }: { n?: number }) {
  return (
    <>
      {Array.from({ length: n }).map((_, i) => (
        <tr key={i} className="border-t">
          {Array.from({ length: 12 }).map((__, j) => (
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
  const [manualUpdating, setManualUpdating] = useState(false)
  const [guardarValidosSaving, setGuardarValidosSaving] = useState(false)
  const [page, setPage] = useState(1)

  useEffect(() => {
    const t = window.setTimeout(() => setCedulaDebounced(cedulaInput.trim()), 400)
    return () => window.clearTimeout(t)
  }, [cedulaInput])

  useEffect(() => {
    setPage(1)
  }, [cedulaDebounced])

  const snapshotQuery = useQuery({
    queryKey: [...QK_BASE, cedulaDebounced, page],
    queryFn: () =>
      getPrestamosCandidatosDriveSnapshot(
        PAGE_SIZE,
        (page - 1) * PAGE_SIZE,
        cedulaDebounced || undefined
      ),
  })

  const data = snapshotQuery.data
  const rows = data?.filas ?? []
  const total = data?.total ?? 0
  const totalSinFiltro = data?.total_sin_filtro
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const pageNumbers = numerosPaginaVisibles(page, totalPages, PAGE_WINDOW)

  useEffect(() => {
    if (page > totalPages) setPage(totalPages)
  }, [page, totalPages])

  const onRecalcular = useCallback(async () => {
    setManualUpdating(true)
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
    } finally {
      setManualUpdating(false)
    }
  }, [qc, forzarVacio, cedulaDebounced])

  const refetchLista = snapshotQuery.refetch

  const onGuardarValidos100 = useCallback(async () => {
    setGuardarValidosSaving(true)
    try {
      const res = await postPrestamosCandidatosDriveGuardarValidados100()
      const ins = Number(res.insertados_ok ?? 0)
      const om = Number(res.omitidos_no_100 ?? 0)
      const err = Number(res.errores_al_guardar ?? 0)
      if (err > 0) {
        toast.warning(res.mensaje || `Creados: ${ins}. Omitidos: ${om}. Errores: ${err}.`)
      } else if (ins > 0) {
        toast.success(res.mensaje || `${ins} préstamo(s) creado(s) (solo 100% validadores).`)
      } else {
        toast.message(res.mensaje || 'Ninguna fila cumplió el 100% de validadores; no se guardó nada.')
      }
      await qc.resetQueries({ queryKey: [...QK_BASE, cedulaDebounced] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo guardar')
    } finally {
      setGuardarValidosSaving(false)
    }
  }, [qc, cedulaDebounced])

  const onRefrescarLista = useCallback(async () => {
    try {
      await refetchLista()
      toast.message('Lista actualizada desde el servidor.')
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo refrescar la lista')
    }
  }, [refetchLista])

  const fmtCaracas = useCallback((iso: string | null | undefined) => {
    if (!iso) return '—'
    try {
      return new Date(iso).toLocaleString('es-VE', { timeZone: 'America/Caracas' })
    } catch {
      return iso
    }
  }, [])

  const estadoFila = useCallback((p: PrestamoCandidatoDriveFila['payload']) => {
    const { formatoOk, tablaVOk, hojaOk } = validadoresTresFlags(p)
    if (!formatoOk) {
      return (
        <span className="text-red-600">
          (1) Formato: {String(p.cedula_error ?? 'cédula inválida')}
        </span>
      )
    }
    if (!hojaOk) return <span className="text-amber-700">(3) Repetida en hoja</span>
    if (!tablaVOk) {
      return (
        <span className="text-red-600">
          (2) Cédula V: ya hay préstamo en tabla (máximo uno)
        </span>
      )
    }
    return <span className="text-emerald-700">Listo (validadores 1·2·3 OK)</span>
  }, [])

  const showSkeleton = snapshotQuery.isPending && !snapshotQuery.data
  const isBusy = snapshotQuery.isFetching
  const listRefreshing = isBusy && !manualUpdating

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Préstamos"
        description="Actualizaciones: cédulas en CONCILIACIÓN (columna E) sin ningún préstamo en el sistema. Lista paginada (100 filas por página). El job programado recalcula domingo y miércoles ~04:05 (tras sync 04:00 Caracas). Solo administradores."
        icon={CreditCard}
      />

      <Card>
        <CardHeader className="space-y-1">
          <CardTitle className="text-lg">Candidatos desde Drive</CardTitle>
          <p className="text-sm text-muted-foreground">
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
            Página <strong>{page}</strong> de {totalPages} · Esta página: <strong>{rows.length}</strong> filas
            {' · '}
            Último sync hoja: {fmtCaracas(data?.drive_synced_at ?? null)}
            {' · '}
            Snapshot: {fmtCaracas(data?.computed_at ?? null)}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-4 rounded-lg border border-blue-100 bg-blue-50/40 p-4">
            <div className="min-w-0 space-y-3">
              <div className="space-y-1 text-sm text-muted-foreground">
                <p className="font-medium text-foreground">Actualización</p>
                <p>
                  Use <strong>Actualización manual</strong> para volver a calcular el snapshot desde la tabla{' '}
                  <code className="rounded bg-white/80 px-1">drive</code> (mismo proceso que el cron). Use{' '}
                  <strong>Refrescar lista</strong> solo para releer en pantalla lo ya guardado.{' '}
                  <strong>Guardar (100%)</strong> crea préstamos solo para filas que cumplen todos los validadores, sin
                  marcar filas en la tabla. Validadores resumidos en columna <strong>Val. 1·2·3</strong>: (1) formato de
                  cédula, (2) tipo V — a lo sumo un préstamo en tabla <code className="rounded bg-white/80 px-1">prestamos</code>, (3) no
                  duplicada en la hoja. La columna <strong>Acciones</strong> de cada fila permite editar, guardar o
                  borrar ese candidato (funciones por fila en desarrollo).
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  onClick={() => void onGuardarValidos100()}
                  disabled={manualUpdating || guardarValidosSaving || isBusy}
                >
                  <Save
                    className={`mr-2 h-4 w-4 ${guardarValidosSaving ? 'animate-pulse' : ''}`}
                    aria-hidden
                  />
                  Guardar (100%)
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={() => void onRecalcular()}
                  disabled={manualUpdating || guardarValidosSaving || isBusy}
                >
                  <RefreshCw
                    className={`mr-2 h-4 w-4 ${manualUpdating ? 'animate-spin' : ''}`}
                    aria-hidden
                  />
                  Actualización manual
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => void onRefrescarLista()}
                  disabled={manualUpdating || guardarValidosSaving || listRefreshing}
                >
                  <Loader2 className={`mr-2 h-4 w-4 ${listRefreshing ? 'animate-spin' : ''}`} aria-hidden />
                  Refrescar lista
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  title="Exporta solo las filas de la página actual"
                  onClick={() => exportarCsvVistaActual(rows)}
                  disabled={rows.length === 0 || manualUpdating || guardarValidosSaving || isBusy}
                >
                  <Download className="mr-2 h-4 w-4" aria-hidden />
                  Exportar CSV
                </Button>
              </div>
            </div>
          </div>

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

          {snapshotQuery.isError && (
            <p className="text-sm text-red-600" role="alert">
              {getErrorMessage(snapshotQuery.error) || 'Error al cargar'}
            </p>
          )}

          <div className="overflow-x-auto rounded-md border">
            <table className="w-full min-w-[1120px] text-left text-sm">
              <thead className="bg-muted/60">
                <tr>
                  <th className="px-3 py-2">Fila</th>
                  <th className="px-3 py-2">Cédula (E)</th>
                  <th
                    className="px-3 py-2 whitespace-nowrap"
                    title="1 formato · 2 tabla préstamos (V) · 3 hoja"
                  >
                    Val. 1·2·3
                  </th>
                  <th className="px-3 py-2">Total (N)</th>
                  <th className="px-3 py-2">Modalidad (S)</th>
                  <th className="px-3 py-2">Fecha (Q)</th>
                  <th className="px-3 py-2">Cuotas (R)</th>
                  <th className="px-3 py-2">Analista (J)</th>
                  <th className="px-3 py-2">Concesionario (K)</th>
                  <th className="px-3 py-2">Modelo (I)</th>
                  <th className="px-3 py-2">Estado</th>
                  <th className="sticky right-0 z-[1] bg-muted/95 px-3 py-2 text-right shadow-[-4px_0_8px_-4px_rgba(0,0,0,0.08)] backdrop-blur-sm">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody>
                {showSkeleton && <TableSkeletonRows />}
                {!showSkeleton &&
                  rows.map(r => {
                    const { formatoOk, tablaVOk, hojaOk } = validadoresTresFlags(r.payload)
                    const mk = (x: boolean) => (
                      <span className={x ? 'text-emerald-700' : 'text-red-600'}>{x ? '✓' : '✗'}</span>
                    )
                    return (
                      <tr key={`${r.id}-${r.sheet_row_number}`} className="border-t">
                        <td className="px-3 py-2 font-mono">{r.sheet_row_number}</td>
                        <td className="px-3 py-2 font-mono">{strPayload(r.payload, 'col_e_cedula')}</td>
                        <td className="px-3 py-2 font-mono text-xs" title="1 formato · 2 tabla V · 3 hoja">
                          {mk(formatoOk)}
                          {mk(tablaVOk)}
                          {mk(hojaOk)}
                        </td>
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
                        <td className="sticky right-0 z-[1] border-l border-border bg-background/95 px-2 py-1.5 text-right backdrop-blur-sm">
                          <AccionesPorFilaCandidatoDrive
                            fila={r}
                            disabled={manualUpdating || guardarValidosSaving || isBusy}
                          />
                        </td>
                      </tr>
                    )
                  })}
                {!showSkeleton && !snapshotQuery.isPending && rows.length === 0 && (
                  <tr>
                    <td className="px-3 py-6 text-muted-foreground" colSpan={12}>
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

          <nav
            className="flex flex-col items-center gap-3 border-t border-border pt-4"
            aria-label="Paginación de candidatos"
          >
            <div className="flex flex-wrap items-center justify-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-w-[7.5rem] rounded-md border-slate-200 bg-white text-foreground shadow-sm hover:bg-slate-50 disabled:text-muted-foreground"
                disabled={page <= 1 || snapshotQuery.isFetching}
                onClick={() => setPage(p => Math.max(1, p - 1))}
              >
                ← Anterior
              </Button>
              {pageNumbers.map(n => (
                <Button
                  key={n}
                  type="button"
                  variant={n === page ? 'default' : 'outline'}
                  size="sm"
                  className={
                    n === page
                      ? 'h-9 min-w-[2.25rem] rounded-md px-3 shadow-sm'
                      : 'h-9 min-w-[2.25rem] rounded-md border-slate-200 bg-white px-3 text-foreground shadow-sm hover:bg-slate-50'
                  }
                  disabled={snapshotQuery.isFetching}
                  onClick={() => setPage(n)}
                  aria-label={`Ir a página ${n}`}
                  aria-current={n === page ? 'page' : undefined}
                >
                  {n}
                </Button>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-w-[7.5rem] rounded-md border-slate-200 bg-white text-foreground shadow-sm hover:bg-slate-50 disabled:text-muted-foreground"
                disabled={page >= totalPages || snapshotQuery.isFetching}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              >
                Siguiente →
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              Página {page} de {totalPages}
            </p>
          </nav>
        </CardContent>
      </Card>
    </div>
  )
}
