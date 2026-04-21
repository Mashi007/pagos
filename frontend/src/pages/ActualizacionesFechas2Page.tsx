import { useCallback, useMemo, useState } from 'react'

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Calendar, Edit2, Loader2, Save, Search, Trash2, X } from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'
import {
  type PrestamoFechas2Item,
  type TipoFiltroFechas2,
  prestamoService,
} from '../services/prestamoService'
import { toast } from 'sonner'
import { getErrorMessage } from '../types/errors'

const QK = ['actualizaciones', 'fechas-2'] as const

function isoDateOnly(s: string | null | undefined): string {
  if (s == null || String(s).trim() === '') return ''
  const t = String(s).trim()
  if (t.length >= 10 && t[4] === '-' && t[7] === '-') return t.slice(0, 10)
  return t.slice(0, 10)
}

export default function ActualizacionesFechas2Page() {
  const qc = useQueryClient()
  const [tipo, setTipo] = useState<TipoFiltroFechas2>('fecha_requerimiento')
  const [fechaInput, setFechaInput] = useState('')
  const [appliedTipo, setAppliedTipo] = useState<TipoFiltroFechas2 | null>(null)
  const [appliedFecha, setAppliedFecha] = useState<string | null>(null)

  const queryEnabled = Boolean(appliedTipo && appliedFecha)

  const listQuery = useQuery({
    queryKey: [...QK, appliedTipo, appliedFecha],
    queryFn: () =>
      prestamoService.getPrestamosActualizacionesFechas2({
        tipo: appliedTipo!,
        fecha: appliedFecha!,
      }),
    enabled: queryEnabled,
  })

  const [editingId, setEditingId] = useState<number | null>(null)
  const [draft, setDraft] = useState<{
    fecha_requerimiento: string
    fecha_aprobacion: string
    fecha_base_calculo: string
  } | null>(null)
  const [savingId, setSavingId] = useState<number | null>(null)

  const buscar = useCallback(() => {
    const f = (fechaInput || '').trim()
    if (!f) {
      toast.error('Indique una fecha.')
      return
    }
    setAppliedTipo(tipo)
    setAppliedFecha(f)
    setEditingId(null)
    setDraft(null)
  }, [fechaInput, tipo])

  const items = listQuery.data?.items ?? []

  const startEdit = useCallback((row: PrestamoFechas2Item) => {
    setEditingId(row.id)
    setDraft({
      fecha_requerimiento: isoDateOnly(row.fecha_requerimiento),
      fecha_aprobacion: isoDateOnly(row.fecha_aprobacion),
      fecha_base_calculo: isoDateOnly(row.fecha_base_calculo),
    })
  }, [])

  const cancelEdit = useCallback(() => {
    setEditingId(null)
    setDraft(null)
  }, [])

  const guardar = useCallback(
    async (row: PrestamoFechas2Item) => {
      if (!draft) return
      setSavingId(row.id)
      try {
        const body: Record<string, unknown> = {}
        if (draft.fecha_requerimiento) body.fecha_requerimiento = draft.fecha_requerimiento
        if (draft.fecha_aprobacion) {
          body.fecha_aprobacion = `${draft.fecha_aprobacion}T00:00:00`
        }
        if (draft.fecha_base_calculo) body.fecha_base_calculo = draft.fecha_base_calculo

        const hadApbOrBase = Boolean(draft.fecha_aprobacion || draft.fecha_base_calculo)

        const res = await prestamoService.updatePrestamo(row.id, body)
        const est = String(res.estado || '').toUpperCase()
        if (hadApbOrBase && (est === 'APROBADO' || est === 'LIQUIDADO')) {
          try {
            await prestamoService.recalcularFechasAmortizacion(row.id)
          } catch (e) {
            toast.warning(
              `Préstamo guardado; aviso: no se pudo recalcular amortización automáticamente (${getErrorMessage(e)}).`,
            )
          }
        }
        toast.success(`Préstamo #${row.id} actualizado.`)
        cancelEdit()
        await qc.invalidateQueries({ queryKey: [...QK, appliedTipo, appliedFecha] })
      } catch (e) {
        toast.error(getErrorMessage(e))
      } finally {
        setSavingId(null)
      }
    },
    [appliedFecha, appliedTipo, cancelEdit, draft, qc],
  )

  const eliminar = useCallback(
    async (row: PrestamoFechas2Item) => {
      if (
        !window.confirm(
          `¿Eliminar el préstamo #${row.id} (${row.cedula})? Esta acción no se puede deshacer.`,
        )
      ) {
        return
      }
      try {
        await prestamoService.deletePrestamo(row.id)
        toast.success(`Préstamo #${row.id} eliminado.`)
        await qc.invalidateQueries({ queryKey: [...QK, appliedTipo, appliedFecha] })
        if (editingId === row.id) cancelEdit()
      } catch (e) {
        toast.error(getErrorMessage(e))
      }
    },
    [appliedFecha, appliedTipo, cancelEdit, editingId, qc],
  )

  const tipoLabel = useMemo(
    () => ({
      fecha_registro: 'Fecha de registro (alta)',
      fecha_aprobacion: 'Fecha de aprobación',
      fecha_requerimiento: 'Fecha de requerimiento',
      fecha_base_calculo: 'Fecha base de cálculo',
    }),
    [],
  )

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Fechas 2"
        description="Filtro por día calendario sobre registro, aprobación, requerimiento o base de cálculo. Listado mínimo (cédula, ID y fechas). Al guardar se usa el mismo PUT que revisión manual y, si aplica, recálculo de vencimientos de cuotas."
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Calendar className="h-5 w-5" aria-hidden />
            Filtro
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 md:flex-row md:items-end">
          <div className="grid flex-1 gap-2 md:grid-cols-2">
            <div className="space-y-1">
              <label className="text-sm font-medium text-muted-foreground">Campo</label>
              <Select value={tipo} onValueChange={v => setTipo(v as TipoFiltroFechas2)}>
                <SelectTrigger>
                  <SelectValue placeholder="Campo" />
                </SelectTrigger>
                <SelectContent>
                  {(Object.keys(tipoLabel) as TipoFiltroFechas2[]).map(k => (
                    <SelectItem key={k} value={k}>
                      {tipoLabel[k]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium text-muted-foreground">Día (calendario)</label>
              <Input
                type="date"
                value={fechaInput}
                onChange={e => setFechaInput(e.target.value)}
              />
            </div>
          </div>
          <Button type="button" onClick={() => void buscar()} className="shrink-0 gap-2">
            <Search className="h-4 w-4" aria-hidden />
            Buscar
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Resultados</CardTitle>
          {appliedTipo && appliedFecha ? (
            <p className="text-sm text-muted-foreground">
              {tipoLabel[appliedTipo]} = {appliedFecha} · {listQuery.data?.total ?? 0} fila(s) (máx.{' '}
              {listQuery.data?.limit ?? 500})
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">Pulse Buscar para cargar préstamos.</p>
          )}
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {listQuery.isFetching ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
              Cargando…
            </div>
          ) : listQuery.isError ? (
            <p className="text-sm text-destructive">{getErrorMessage(listQuery.error)}</p>
          ) : !queryEnabled ? null : items.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin préstamos para ese filtro.</p>
          ) : (
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-2 pr-2 font-medium">ID</th>
                  <th className="py-2 pr-2 font-medium">Cédula</th>
                  <th className="py-2 pr-2 font-medium">Req.</th>
                  <th className="py-2 pr-2 font-medium">Aprob.</th>
                  <th className="py-2 pr-2 font-medium">Base cálculo</th>
                  <th className="py-2 pr-2 font-medium text-right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {items.map(row => {
                  const isEditing = editingId === row.id
                  return (
                    <tr key={row.id} className="border-b border-border/60">
                      <td className="py-2 pr-2 font-mono tabular-nums">{row.id}</td>
                      <td className="py-2 pr-2 font-medium">{row.cedula}</td>
                      <td className="py-2 pr-2">
                        {isEditing && draft ? (
                          <Input
                            type="date"
                            value={draft.fecha_requerimiento}
                            onChange={e =>
                              setDraft(d => (d ? { ...d, fecha_requerimiento: e.target.value } : d))
                            }
                            className="h-8"
                          />
                        ) : (
                          isoDateOnly(row.fecha_requerimiento) || '—'
                        )}
                      </td>
                      <td className="py-2 pr-2">
                        {isEditing && draft ? (
                          <Input
                            type="date"
                            value={draft.fecha_aprobacion}
                            onChange={e =>
                              setDraft(d => (d ? { ...d, fecha_aprobacion: e.target.value } : d))
                            }
                            className="h-8"
                          />
                        ) : (
                          isoDateOnly(row.fecha_aprobacion) || '—'
                        )}
                      </td>
                      <td className="py-2 pr-2">
                        {isEditing && draft ? (
                          <Input
                            type="date"
                            value={draft.fecha_base_calculo}
                            onChange={e =>
                              setDraft(d => (d ? { ...d, fecha_base_calculo: e.target.value } : d))
                            }
                            className="h-8"
                          />
                        ) : (
                          isoDateOnly(row.fecha_base_calculo) || '—'
                        )}
                      </td>
                      <td className="py-2 pl-2 text-right">
                        <div className="flex flex-wrap justify-end gap-1">
                          {isEditing ? (
                            <>
                              <Button
                                type="button"
                                size="sm"
                                variant="default"
                                className="gap-1"
                                disabled={savingId === row.id}
                                onClick={() => void guardar(row)}
                              >
                                {savingId === row.id ? (
                                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                                ) : (
                                  <Save className="h-3.5 w-3.5" aria-hidden />
                                )}
                                Guardar
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                className="gap-1"
                                disabled={savingId === row.id}
                                onClick={cancelEdit}
                              >
                                <X className="h-3.5 w-3.5" aria-hidden />
                                Cancelar
                              </Button>
                            </>
                          ) : (
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              className="gap-1"
                              onClick={() => startEdit(row)}
                            >
                              <Edit2 className="h-3.5 w-3.5" aria-hidden />
                              Editar
                            </Button>
                          )}
                          <Button
                            type="button"
                            size="sm"
                            variant="destructive"
                            className="gap-1"
                            disabled={isEditing || savingId === row.id}
                            onClick={() => void eliminar(row)}
                          >
                            <Trash2 className="h-3.5 w-3.5" aria-hidden />
                            Eliminar
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
