import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, RefreshCw, Search, Wrench } from 'lucide-react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog'
import {
  prestamoService,
  type CuotaVsFechaBaseItem,
} from '../services/prestamoService'
import { getErrorMessage } from '../types/errors'
import { useSimpleAuth } from '../store/simpleAuthStore'

const QK = ['actualizaciones', 'cuotas-vs-fecha-base'] as const

const PAGE_SIZE = 50

function fmtIso(s?: string | null): string {
  if (!s) return '—'
  const t = String(s).trim()
  return t.length >= 10 ? t.slice(0, 10) : t
}

export default function CuotasVsFechaBaseAdminPage() {
  const queryClient = useQueryClient()
  const { user } = useSimpleAuth()
  const esAdmin = (user?.rol || '').toLowerCase() === 'admin'

  const [cedula, setCedula] = useState('')
  const [appliedCedula, setAppliedCedula] = useState('')
  const [offset, setOffset] = useState(0)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [confirmRow, setConfirmRow] = useState<CuotaVsFechaBaseItem | null>(null)

  const q = useQuery({
    queryKey: [...QK, appliedCedula, offset],
    queryFn: () =>
      prestamoService.getCuotasVsFechaBaseDesalineadas({
        limit: PAGE_SIZE,
        offset,
        cedula_q: appliedCedula || undefined,
      }),
  })

  const total = q.data?.total ?? 0
  const items = q.data?.items ?? []
  const hasPrev = offset > 0
  const hasNext = offset + PAGE_SIZE < total

  const rangoTxt = useMemo(() => {
    if (total === 0) return '0 resultados'
    const ini = offset + 1
    const fin = Math.min(offset + PAGE_SIZE, total)
    return `${ini}-${fin} de ${total}`
  }, [offset, total])

  const ejecutarReconstruir = async (row: CuotaVsFechaBaseItem) => {
    if (!esAdmin || busyId != null) return
    setBusyId(row.prestamo_id)
    setConfirmRow(null)
    try {
      const res = await prestamoService.postReconstruirTablaCuotasDesdePrestamo(
        row.prestamo_id
      )
      const creadas = (res as { cuotas_creadas?: unknown })?.cuotas_creadas
      const pagos = (res as { pagos_con_aplicacion?: unknown })
        ?.pagos_con_aplicacion
      toast.success(
        `Préstamo #${row.prestamo_id}: cuotas regeneradas${
          typeof creadas === 'number' ? ` (${creadas})` : ''
        }${
          typeof pagos === 'number' ? `; pagos con aplicación: ${pagos}` : ''
        }.`
      )
      await queryClient.invalidateQueries({ queryKey: [...QK] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo reconstruir la tabla de cuotas.')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Actualizaciones · Cuotas vs fecha base"
        description="Préstamos donde el vencimiento de la cuota 1 es anterior a la fecha base de amortización (fecha_base_calculo o día de fecha_aprobacion). Suele indicar cuotas no alineadas tras cambiar la aprobación. Revise pagos y cartera; luego puede reconstruir la tabla de cuotas desde el préstamo (misma lógica que el endpoint de reconstrucción en API)."
        icon={AlertTriangle}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filtros</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 md:flex-row md:items-end">
          <div className="space-y-1">
            <label className="text-sm font-medium text-muted-foreground">
              Cédula (opcional)
            </label>
            <Input
              value={cedula}
              onChange={e => setCedula(e.target.value)}
              placeholder="V12345678…"
            />
          </div>
          <Button
            type="button"
            onClick={() => {
              setAppliedCedula(cedula.trim())
              setOffset(0)
            }}
            className="gap-2"
          >
            <Search className="h-4 w-4" />
            Buscar
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => void q.refetch()}
            className="gap-2"
            disabled={q.isFetching}
          >
            <RefreshCw className={`h-4 w-4 ${q.isFetching ? 'animate-spin' : ''}`} />
            Refrescar
          </Button>
          <Button asChild type="button" variant="outline">
            <Link to="/notificaciones/fecha">Ir a Fechas (Q vs BD)</Link>
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Resultados ({rangoTxt})</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {q.isFetching ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : q.isError ? (
            <p className="text-sm text-destructive">{getErrorMessage(q.error)}</p>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Sin casos para este filtro (total global puede ser 0).
            </p>
          ) : (
            <table className="w-full min-w-[880px] border-collapse text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-2 pr-2 font-medium">Préstamo</th>
                  <th className="py-2 pr-2 font-medium">Cédula</th>
                  <th className="py-2 pr-2 font-medium">Estado</th>
                  <th className="py-2 pr-2 font-medium">Fecha base</th>
                  <th className="py-2 pr-2 font-medium">Venc. cuota 1</th>
                  <th className="py-2 pr-2 font-medium">Días (C1 − base)</th>
                  <th className="py-2 pr-2 font-medium">Modalidad</th>
                  <th className="py-2 pr-2 font-medium">Nº cuotas</th>
                  <th className="py-2 pr-2 font-medium">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {items.map(row => (
                  <tr key={row.prestamo_id} className="border-b border-border/60">
                    <td className="py-2 pr-2 font-mono">{row.prestamo_id}</td>
                    <td className="py-2 pr-2">{row.cedula || '—'}</td>
                    <td className="py-2 pr-2">{row.estado || '—'}</td>
                    <td className="py-2 pr-2">{fmtIso(row.fecha_base)}</td>
                    <td className="py-2 pr-2">{fmtIso(row.vencimiento_cuota_1)}</td>
                    <td className="py-2 pr-2 font-mono">
                      {row.dias_cuota1_menos_base ?? '—'}
                    </td>
                    <td className="py-2 pr-2">{row.modalidad_pago || '—'}</td>
                    <td className="py-2 pr-2">{row.numero_cuotas}</td>
                    <td className="py-2 pr-2">
                      <div className="flex flex-wrap gap-1">
                        <Button asChild size="sm" variant="outline" className="h-7 px-2 text-xs">
                          <Link to={`/prestamos?prestamo_id=${row.prestamo_id}`}>
                            Ver préstamo
                          </Link>
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="default"
                          className="h-7 gap-1 px-2 text-xs"
                          disabled={!esAdmin || busyId != null}
                          title={
                            esAdmin
                              ? 'Elimina cuotas actuales y las regenera desde el préstamo; reaplica pagos pendientes de vínculo.'
                              : 'Solo administrador.'
                          }
                          onClick={() => {
                            if (!esAdmin || busyId != null) return
                            setConfirmRow(row)
                          }}
                        >
                          <Wrench className="h-3.5 w-3.5" aria-hidden />
                          Reconstruir cuotas
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {total > PAGE_SIZE ? (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!hasPrev || q.isFetching}
                onClick={() => setOffset(o => Math.max(0, o - PAGE_SIZE))}
              >
                Anterior
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!hasNext || q.isFetching}
                onClick={() => setOffset(o => o + PAGE_SIZE)}
              >
                Siguiente
              </Button>
              <span className="text-xs text-muted-foreground">
                Página {Math.floor(offset / PAGE_SIZE) + 1} de{' '}
                {Math.max(1, Math.ceil(total / PAGE_SIZE))}
              </span>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Dialog open={confirmRow != null} onOpenChange={open => !open && setConfirmRow(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reconstruir tabla de cuotas</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Se eliminarán las cuotas del préstamo <strong>#{confirmRow?.prestamo_id}</strong> y se
            volverán a crear según los datos actuales del préstamo (montos, modalidad, fecha base).
            Luego el sistema intenta reaplicar pagos pendientes de vínculo. Esta acción no se puede
            deshacer desde la interfaz.
          </p>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" onClick={() => setConfirmRow(null)}>
              Cancelar
            </Button>
            <Button
              type="button"
              disabled={!confirmRow || busyId != null}
              onClick={() => {
                if (confirmRow) void ejecutarReconstruir(confirmRow)
              }}
            >
              {busyId != null ? 'Procesando…' : 'Confirmar'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
