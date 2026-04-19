import { useCallback, useMemo, useState } from 'react'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import { RefreshCw, User } from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Textarea } from '../components/ui/textarea'
import { clienteService } from '../services/clienteService'
import { toast } from 'sonner'
import { getErrorMessage } from '../types/errors'

const QK = ['notificaciones', 'clientes-drive', 'candidatos'] as const
const QK_AUD = ['notificaciones', 'clientes-drive', 'auditoria'] as const

export default function NotificacionesClientesDrive() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<Record<number, boolean>>({})
  const [comentario, setComentario] = useState('')
  const [audPage, setAudPage] = useState(1)

  const q = useQuery({
    queryKey: [...QK],
    queryFn: () => clienteService.getDriveImportCandidatos(),
  })

  const qa = useQuery({
    queryKey: [...QK_AUD, audPage],
    queryFn: () => clienteService.getDriveImportAuditoria(audPage, 30),
  })

  const rows = q.data?.candidatos ?? []

  const toggle = useCallback((sheetRow: number, checked: boolean) => {
    setSelected(prev => ({ ...prev, [sheetRow]: checked }))
  }, [])

  const seleccionados = useMemo(
    () => Object.entries(selected).filter(([, v]) => v).map(([k]) => Number(k)),
    [selected]
  )

  const [saving, setSaving] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const onActualizarLista = async () => {
    setRefreshing(true)
    try {
      await clienteService.postDriveImportRefreshCache()
      await qc.invalidateQueries({ queryKey: [...QK] })
      await qc.refetchQueries({ queryKey: [...QK] })
      toast.success('Lista recalculada y guardada en caché.')
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo actualizar la lista')
    } finally {
      setRefreshing(false)
    }
  }

  const onGuardar = async () => {
    if (!seleccionados.length) {
      toast.message('Seleccione al menos una fila.')
      return
    }
    setSaving(true)
    try {
      const res = await clienteService.postDriveImportImportar({
        sheet_row_numbers: seleccionados,
        comentario: comentario.trim() || null,
      })
      toast.success(
        `Proceso terminado: ${res.insertados_ok} insertado(s), ${res.errores} error(es). Lote ${res.batch_id}`
      )
      setSelected({})
      setComentario('')
      await qc.invalidateQueries({ queryKey: [...QK] })
      await qc.invalidateQueries({ queryKey: [...QK_AUD] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo importar')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Clientes (Drive)"
        description="Cédulas en la pestaña CONCILIACIÓN (columna E) que aún no están en la tabla clientes. Origen: snapshot en BD (D=nombres, F=teléfono, G=email). Con jobs activos, la lista se materializa dom/mié 03:00 Caracas (tras el sync 02:00). Solo administradores."
        icon={User}
      />

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-lg">Candidatos</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Último sync Drive:{' '}
              {q.data?.drive_synced_at
                ? new Date(q.data.drive_synced_at).toLocaleString('es-VE', {
                    timeZone: 'America/Caracas',
                  })
                : '—'}
              {q.data?.from_cache === true && (
                <span className="ml-2 rounded bg-emerald-100 px-2 py-0.5 text-emerald-900">
                  Lista en caché
                  {q.data.cache_computed_at
                    ? ` · ${new Date(q.data.cache_computed_at).toLocaleString('es-VE', { timeZone: 'America/Caracas' })}`
                    : ''}
                </span>
              )}
              {q.data?.from_cache === false && q.data?.cache_computed_at && (
                <span className="ml-2 text-xs text-muted-foreground">
                  Recalculado {new Date(q.data.cache_computed_at).toLocaleString('es-VE', { timeZone: 'America/Caracas' })}
                </span>
              )}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onActualizarLista()}
              disabled={refreshing || q.isFetching}
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${refreshing || q.isFetching ? 'animate-spin' : ''}`}
              />
              Actualizar lista
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {q.isError && (
            <p className="text-sm text-red-600">
              {getErrorMessage(q.error) || 'Error al cargar'}
            </p>
          )}
          {q.isLoading && <p className="text-sm text-muted-foreground">Cargando…</p>}

          <div className="overflow-x-auto rounded-md border">
            <table className="w-full min-w-[880px] text-left text-sm">
              <thead className="bg-muted/60">
                <tr>
                  <th className="px-3 py-2 w-10"></th>
                  <th className="px-3 py-2">Fila</th>
                  <th className="px-3 py-2">Cédula (E)</th>
                  <th className="px-3 py-2">Nombres (D)</th>
                  <th className="px-3 py-2">Teléfono (F)</th>
                  <th className="px-3 py-2">Email (G)</th>
                  <th className="px-3 py-2">Estado</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(r => {
                  const blocked = !r.seleccionable
                  const chk = !!selected[r.sheet_row_number]
                  return (
                    <tr key={r.sheet_row_number} className="border-t">
                      <td className="px-3 py-2 align-top">
                        <input
                          type="checkbox"
                          className="h-4 w-4 accent-primary"
                          checked={chk}
                          disabled={blocked}
                          onChange={e => toggle(r.sheet_row_number, e.target.checked)}
                          aria-label={`Seleccionar fila ${r.sheet_row_number}`}
                        />
                      </td>
                      <td className="px-3 py-2 align-top font-mono">{r.sheet_row_number}</td>
                      <td className="px-3 py-2 align-top font-mono">{r.col_e_cedula ?? ''}</td>
                      <td className="px-3 py-2 align-top">{r.defaults.nombres}</td>
                      <td className="px-3 py-2 align-top">{r.defaults.telefono || '—'}</td>
                      <td className="px-3 py-2 align-top break-all">{r.defaults.email}</td>
                      <td className="px-3 py-2 align-top text-xs">
                        {!r.cedula_valida && (
                          <span className="text-red-600">Inválida: {r.cedula_error}</span>
                        )}
                        {r.cedula_valida && r.duplicada_en_hoja && (
                          <span className="text-amber-700">Repetida en hoja (no importable)</span>
                        )}
                        {r.cedula_valida && !r.duplicada_en_hoja && (
                          <span className="text-emerald-700">Listo para revisión</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
                {!q.isLoading && rows.length === 0 && (
                  <tr>
                    <td className="px-3 py-6 text-muted-foreground" colSpan={7}>
                      No hay filas pendientes: todas las cédulas del Drive ya existen en clientes, o el
                      snapshot está vacío. Verifique la sincronización en Configuración (Google), el job interno
                      (sync dom/mié 02:00 y caché de lista 03:00 Caracas si ENABLE_AUTOMATIC_SCHEDULED_JOBS=true) o
                      un cron externo alineado (POST /api/v1/conciliacion-sheet/sync con secreto). Puede pulsar
                      «Actualizar lista» para materializar ahora.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="com-import">
                Comentario (auditoría)
              </label>
              <Textarea
                id="com-import"
                value={comentario}
                onChange={e => setComentario(e.target.value)}
                rows={3}
                placeholder="Opcional: motivo o referencia del lote"
              />
            </div>
            <div className="flex flex-col justify-end gap-2">
              <p className="text-sm text-muted-foreground">
                Se aplican las mismas reglas que «Nuevo cliente» / POST /clientes (duplicados por
                cédula, nombre, correo, teléfono). Si una fila falla, las demás del mismo guardado
                siguen.
              </p>
              <Button type="button" onClick={onGuardar} disabled={saving || q.isFetching}>
                {saving ? 'Guardando…' : `Guardar seleccionados (${seleccionados.length})`}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-lg">Auditoría de importaciones</CardTitle>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={audPage <= 1}
              onClick={() => setAudPage(p => Math.max(1, p - 1))}
            >
              Anterior
            </Button>
            <span className="text-sm text-muted-foreground">
              Página {qa.data?.page ?? audPage} /{' '}
              {qa.data
                ? Math.max(1, Math.ceil(qa.data.total / (qa.data.per_page || 30)))
                : 1}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={
                !qa.data ||
                audPage >= Math.max(1, Math.ceil(qa.data.total / (qa.data.per_page || 30)))
              }
              onClick={() => setAudPage(p => p + 1)}
            >
              Siguiente
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {qa.isLoading && <p className="text-sm text-muted-foreground">Cargando auditoría…</p>}
          {qa.isError && (
            <p className="text-sm text-red-600">
              {getErrorMessage(qa.error) || 'Error al cargar'}
            </p>
          )}
          <div className="overflow-x-auto rounded-md border">
            <table className="w-full min-w-[960px] text-left text-sm">
              <thead className="bg-muted/60">
                <tr>
                  <th className="px-3 py-2">Fecha</th>
                  <th className="px-3 py-2">Usuario</th>
                  <th className="px-3 py-2">Estado</th>
                  <th className="px-3 py-2">Fila</th>
                  <th className="px-3 py-2">Cédula</th>
                  <th className="px-3 py-2">Comentario</th>
                  <th className="px-3 py-2">Detalle</th>
                </tr>
              </thead>
              <tbody>
                {(qa.data?.items ?? []).map(it => (
                  <tr key={it.id} className="border-t">
                    <td className="px-3 py-2 whitespace-nowrap text-xs">
                      {it.creado_en
                        ? new Date(it.creado_en).toLocaleString('es-VE', {
                            timeZone: 'America/Caracas',
                          })
                        : '—'}
                    </td>
                    <td className="px-3 py-2 break-all text-xs">{it.usuario_email}</td>
                    <td className="px-3 py-2 text-xs">{it.estado}</td>
                    <td className="px-3 py-2 font-mono text-xs">{it.sheet_row_number}</td>
                    <td className="px-3 py-2 font-mono text-xs">{it.cedula}</td>
                    <td className="px-3 py-2 text-xs break-all">{it.comentario ?? '—'}</td>
                    <td className="px-3 py-2 text-xs text-red-700 break-all">
                      {it.detalle_error ?? '—'}
                    </td>
                  </tr>
                ))}
                {!qa.isLoading && (qa.data?.items?.length ?? 0) === 0 && (
                  <tr>
                    <td className="px-3 py-6 text-muted-foreground" colSpan={7}>
                      Sin registros de auditoría.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
