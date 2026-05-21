import { useCallback, useState } from 'react'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import { AlertTriangle, CheckCircle2, Loader2, ScanSearch } from 'lucide-react'

import { Button } from '../ui/button'
import { reporteService, type DriveScanCoverage } from '../../services/reporteService'
import { toast } from 'sonner'
import { getErrorMessage } from '../../types/errors'
import { cn } from '../../utils'

const QK_SCAN_COVERAGE = ['conciliacion-sheet', 'scan-coverage'] as const

function fmtCaracas(iso: string | null | undefined): string {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleString('es-VE', { timeZone: 'America/Caracas' })
  } catch {
    return iso
  }
}

function coverageTone(cov: DriveScanCoverage | undefined): 'ok' | 'warn' | 'neutral' {
  if (!cov) return 'neutral'
  if (cov.tail_aligned_with_drive_table === true && cov.bd_internally_consistent === true) {
    return 'ok'
  }
  if (
    cov.tail_aligned_with_drive_table === false ||
    cov.bd_internally_consistent === false
  ) {
    return 'warn'
  }
  return 'neutral'
}

type Props = {
  className?: string
  /** Tras sync manual en la misma pantalla, invalidar cobertura. */
  onAfterProbe?: () => void
}

export function DriveScanCoveragePanel({ className, onAfterProbe }: Props) {
  const qc = useQueryClient()
  const [probing, setProbing] = useState(false)

  const statusQuery = useQuery({
    queryKey: QK_SCAN_COVERAGE,
    queryFn: () => reporteService.getConciliacionSheetStatus(),
    staleTime: 60_000,
  })

  const cov = statusQuery.data?.scan_coverage
  const tone = coverageTone(cov)

  const onVerificarCola = useCallback(async () => {
    setProbing(true)
    try {
      const res = await reporteService.verificarConciliacionSheetCola()
      const aligned = res.scan_coverage?.tail_aligned_with_drive_table
      const msg =
        res.scan_coverage?.tail_message ||
        (aligned === true
          ? `Cola verificada: fila ${res.google_tail_row_number ?? '?'}.`
          : 'Verificación completada; revise el detalle.')
      if (aligned === true) toast.success(msg)
      else if (aligned === false) toast.warning(msg)
      else toast.message(msg)
      await qc.invalidateQueries({ queryKey: QK_SCAN_COVERAGE })
      onAfterProbe?.()
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo verificar la cola en Google')
    } finally {
      setProbing(false)
    }
  }, [qc, onAfterProbe])

  const border =
    tone === 'ok'
      ? 'border-emerald-200 bg-emerald-50/80 dark:border-emerald-900 dark:bg-emerald-950/30'
      : tone === 'warn'
        ? 'border-amber-200 bg-amber-50/80 dark:border-amber-900 dark:bg-amber-950/30'
        : 'border-border bg-muted/30'

  return (
    <div
      className={cn(
        'rounded-lg border px-3 py-2.5 text-sm',
        border,
        className
      )}
      role="status"
      aria-live="polite"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex min-w-0 flex-1 items-start gap-2">
          {tone === 'ok' ? (
            <CheckCircle2
              className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700"
              aria-hidden
            />
          ) : tone === 'warn' ? (
            <AlertTriangle
              className="mt-0.5 h-4 w-4 shrink-0 text-amber-700"
              aria-hidden
            />
          ) : (
            <ScanSearch
              className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
              aria-hidden
            />
          )}
          <div className="min-w-0 space-y-1">
            <p className="font-medium text-foreground">
              Cobertura del escaneo Drive (CONCILIACIÓN)
            </p>
            {statusQuery.isPending && !cov ? (
              <p className="text-muted-foreground">Cargando métricas…</p>
            ) : statusQuery.isError ? (
              <p className="text-red-600">
                {getErrorMessage(statusQuery.error) || 'No se pudo cargar cobertura.'}
              </p>
            ) : (
              <ul className="list-none space-y-0.5 text-muted-foreground">
                <li>
                  Filas en BD (tabla <code className="text-xs">drive</code>):{' '}
                  <strong className="tabular-nums text-foreground">
                    {cov?.drive_row_count ?? '-'}
                  </strong>
                  {cov?.drive_max_sheet_row != null && (
                    <>
                      {' '}
                      · Última fila hoja en BD:{' '}
                      <strong className="tabular-nums text-foreground">
                        {cov.drive_max_sheet_row}
                      </strong>
                    </>
                  )}
                </li>
                <li>
                  Última fila esperada tras sync (cabecera + datos):{' '}
                  <strong className="tabular-nums text-foreground">
                    {cov?.expected_last_data_sheet_row ?? '-'}
                  </strong>
                  {cov?.bd_internally_consistent === true && (
                    <span className="ml-1 text-emerald-800">· BD coherente</span>
                  )}
                  {cov?.bd_internally_consistent === false && (
                    <span className="ml-1 text-amber-800">
                      · BD incoherente (re-sincronice)
                    </span>
                  )}
                </li>
                <li>
                  Cola en Google (columna A):{' '}
                  <strong className="tabular-nums text-foreground">
                    {cov?.google_tail_row_number ?? 'sin verificar'}
                  </strong>
                  {cov?.google_tail_row_probed_at && (
                    <span className="ml-1 text-xs">
                      · probado {fmtCaracas(cov.google_tail_row_probed_at)}
                    </span>
                  )}
                </li>
                {cov?.tail_message && (
                  <li
                    className={
                      cov.tail_aligned_with_drive_table === false
                        ? 'text-amber-900'
                        : 'text-emerald-900'
                    }
                  >
                    {cov.tail_message}
                  </li>
                )}
                <li className="text-xs">
                  Sync hoja: {fmtCaracas(cov?.drive_synced_at ?? null)}. Jobs 01:00 / 02:00 Caracas
                  (si ENABLE_AUTOMATIC_SCHEDULED_JOBS): columna A → sync hasta última fila → guardado
                  automático solo de filas que cumplen validadores; el resto queda en pantalla.
                </li>
              </ul>
            )}
          </div>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="shrink-0"
          disabled={probing || statusQuery.isFetching}
          onClick={() => void onVerificarCola()}
          title="Lee solo un tramo de la columna A cerca de la última fila importada y compara con la BD."
        >
          <Loader2
            className={cn('mr-2 h-4 w-4', probing && 'animate-spin')}
            aria-hidden
          />
          Verificar cola en Google
        </Button>
      </div>
    </div>
  )
}

export function invalidateDriveScanCoverage(queryClient: {
  invalidateQueries: (opts: { queryKey: readonly string[] }) => Promise<unknown>
}) {
  return queryClient.invalidateQueries({ queryKey: [...QK_SCAN_COVERAGE] })
}
