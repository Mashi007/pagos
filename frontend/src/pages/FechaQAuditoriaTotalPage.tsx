import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Database, Search, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { notificacionService } from '../services/notificacionService'
import { getErrorMessage } from '../types/errors'

const QK = ['notificaciones', 'fecha-q-auditoria-total'] as const

function fmtIso(s?: string | null): string {
  if (!s) return '—'
  const t = String(s).trim()
  return t.length >= 10 ? t.slice(0, 10) : t
}

export default function FechaQAuditoriaTotalPage() {
  const [cedula, setCedula] = useState('')
  const [appliedCedula, setAppliedCedula] = useState('')
  const [soloConDiferencia, setSoloConDiferencia] = useState(true)
  const [offset, setOffset] = useState(0)
  const limit = 200

  const q = useQuery({
    queryKey: [...QK, appliedCedula, soloConDiferencia, offset],
    queryFn: () =>
      notificacionService.getFechaQAuditoriaTotal({
        limit,
        offset,
        cedula_q: appliedCedula || undefined,
        solo_con_diferencia: soloConDiferencia,
      }),
  })

  const total = q.data?.total ?? 0
  const items = q.data?.items ?? []
  const hasPrev = offset > 0
  const hasNext = offset + limit < total
  const rangoTxt = useMemo(() => {
    if (total === 0) return '0 resultados'
    const ini = offset + 1
    const fin = Math.min(offset + limit, total)
    return `${ini}-${fin} de ${total}`
  }, [offset, total])

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Auditoría Total Q vs Sistema"
        description="Verificación profunda de inconsistencias Drive vs sistema por préstamo: columna Q (cache) versus fecha de aprobación en BD."
        icon={Database}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filtros</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 md:flex-row md:items-end">
          <div className="space-y-1">
            <label className="text-sm font-medium text-muted-foreground">Cédula (opcional)</label>
            <Input
              value={cedula}
              onChange={e => setCedula(e.target.value)}
              placeholder="V12345678 / J..."
            />
          </div>
          <label className="inline-flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={soloConDiferencia}
              onChange={e => {
                setSoloConDiferencia(e.target.checked)
                setOffset(0)
              }}
            />
            Solo con diferencia de fecha
          </label>
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
          >
            <RefreshCw className="h-4 w-4" />
            Refrescar
          </Button>
          <Button asChild type="button" variant="outline">
            <Link to="/pagos/notificaciones/fecha">Ir a Notificaciones/Fecha</Link>
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
            <p className="text-sm text-muted-foreground">Sin filas para este filtro.</p>
          ) : (
            <table className="w-full min-w-[1100px] border-collapse text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-2 pr-2 font-medium">Préstamo</th>
                  <th className="py-2 pr-2 font-medium">Cédula</th>
                  <th className="py-2 pr-2 font-medium">Estado</th>
                  <th className="py-2 pr-2 font-medium">Aprobación BD</th>
                  <th className="py-2 pr-2 font-medium">Q (cache)</th>
                  <th className="py-2 pr-2 font-medium">Dif. días</th>
                  <th className="py-2 pr-2 font-medium">Puede aplicar</th>
                  <th className="py-2 pr-2 font-medium">Q anterior corrige</th>
                  <th className="py-2 pr-2 font-medium">Req. auto</th>
                  <th className="py-2 pr-2 font-medium">Base auto</th>
                </tr>
              </thead>
              <tbody>
                {items.map(row => (
                  <tr key={row.prestamo_id} className="border-b border-border/60">
                    <td className="py-2 pr-2 font-mono">{row.prestamo_id}</td>
                    <td className="py-2 pr-2">{row.cedula || '—'}</td>
                    <td className="py-2 pr-2">{row.estado || '—'}</td>
                    <td className="py-2 pr-2">{fmtIso(row.fecha_aprobacion)}</td>
                    <td className="py-2 pr-2">{fmtIso(row.q_fecha_iso)}</td>
                    <td className="py-2 pr-2">{row.diferencia_dias ?? '—'}</td>
                    <td className="py-2 pr-2">
                      {row.puede_aplicar == null ? '—' : row.puede_aplicar ? 'Sí' : 'No'}
                    </td>
                    <td className="py-2 pr-2">
                      {row.correccion_desde_q_anterior_bd == null
                        ? '—'
                        : row.correccion_desde_q_anterior_bd
                          ? 'Sí'
                          : 'No'}
                    </td>
                    <td className="py-2 pr-2">{fmtIso(row.fecha_requerimiento)}</td>
                    <td className="py-2 pr-2">{fmtIso(row.fecha_base_calculo)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div className="mt-4 flex items-center justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={!hasPrev || q.isFetching}
              onClick={() => setOffset(o => Math.max(0, o - limit))}
            >
              Anterior
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={!hasNext || q.isFetching}
              onClick={() => setOffset(o => o + limit)}
            >
              Siguiente
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
