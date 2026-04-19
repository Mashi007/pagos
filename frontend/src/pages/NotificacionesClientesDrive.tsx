import { useCallback, useEffect, useMemo, useState } from 'react'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import { Download, Edit2, RefreshCw, Save, Trash2, User } from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import { useEstadosCliente } from '../hooks/useEstadosCliente'
import { clienteService } from '../services/clienteService'
import { reporteService } from '../services/reporteService'
import { toast } from 'sonner'
import { getErrorMessage } from '../types/errors'

const QK = ['notificaciones', 'clientes-drive', 'candidatos'] as const
const QK_AUD = ['notificaciones', 'clientes-drive', 'auditoria'] as const

const STORAGE_HIDDEN = 'notificaciones-drive-candidatos-ocultos'

type DriveCandidate = NonNullable<
  Awaited<ReturnType<typeof clienteService.getDriveImportCandidatos>>['candidatos']
>[number]

function fechaInputFromDefaults(iso: string | undefined): string {
  if (!iso) return '1990-01-01'
  const s = String(iso).trim()
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10)
  try {
    const d = new Date(s)
    if (!Number.isNaN(d.getTime())) return d.toISOString().slice(0, 10)
  } catch {
    /* ignore */
  }
  return '1990-01-01'
}

function buildImportarFilaPayload(
  r: DriveCandidate,
  comentarioGlobal: string
): Parameters<typeof clienteService.postDriveImportImportarFila>[0] {
  return {
    sheet_row_number: r.sheet_row_number,
    cedula: r.col_e_cedula ?? '',
    nombres: r.defaults.nombres,
    telefono: r.defaults.telefono,
    email: r.defaults.email,
    email_secundario: null,
    direccion: r.defaults.direccion,
    fecha_nacimiento: fechaInputFromDefaults(r.defaults.fecha_nacimiento),
    ocupacion: r.defaults.ocupacion,
    estado: (r.defaults.estado || 'ACTIVO').trim().toUpperCase(),
    notas: null,
    comentario: comentarioGlobal.trim() || null,
  }
}

export default function NotificacionesClientesDrive() {
  const qc = useQueryClient()
  const { opciones: estadosCliente } = useEstadosCliente()
  const [selected, setSelected] = useState<Record<number, boolean>>({})
  const [comentario, setComentario] = useState('')
  const [audPage, setAudPage] = useState(1)
  const [hiddenRows, setHiddenRows] = useState<Set<number>>(() => new Set())
  const [savingRowId, setSavingRowId] = useState<number | null>(null)
  const [editDraft, setEditDraft] = useState<{
    sheet_row_number: number
    cedula: string
    nombres: string
    telefono: string
    email: string
    email_secundario: string
    direccion: string
    fecha_nacimiento: string
    ocupacion: string
    estado: string
    notas: string
    comentario: string
  } | null>(null)

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(STORAGE_HIDDEN)
      if (!raw) return
      const arr = JSON.parse(raw) as unknown
      if (!Array.isArray(arr)) return
      setHiddenRows(new Set(arr.map(n => Number(n)).filter(n => Number.isFinite(n) && n > 0)))
    } catch {
      /* ignore */
    }
  }, [])

  const persistHidden = useCallback((next: Set<number>) => {
    setHiddenRows(next)
    try {
      sessionStorage.setItem(STORAGE_HIDDEN, JSON.stringify([...next]))
    } catch {
      /* ignore */
    }
  }, [])

  const q = useQuery({
    queryKey: [...QK],
    queryFn: () => clienteService.getDriveImportCandidatos(),
  })

  const qa = useQuery({
    queryKey: [...QK_AUD, audPage],
    queryFn: () => clienteService.getDriveImportAuditoria(audPage, 30),
  })

  const rows = q.data?.candidatos ?? []

  const visibleRows = useMemo(
    () => rows.filter(r => !hiddenRows.has(r.sheet_row_number)),
    [rows, hiddenRows]
  )

  const toggle = useCallback((sheetRow: number, checked: boolean) => {
    setSelected(prev => ({ ...prev, [sheetRow]: checked }))
  }, [])

  const seleccionados = useMemo(
    () => Object.entries(selected).filter(([, v]) => v).map(([k]) => Number(k)),
    [selected]
  )

  const [saving, setSaving] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  /** Descarga la pestaña CONCILIACIÓN desde Google (POST /conciliacion-sheet/sync-now) y luego recalcula candidatos. */
  const [manualSyncing, setManualSyncing] = useState(false)

  const refetchCandidatosYAuditoria = useCallback(async () => {
    await qc.invalidateQueries({ queryKey: [...QK] })
    await qc.invalidateQueries({ queryKey: [...QK_AUD] })
    await qc.refetchQueries({ queryKey: [...QK] })
    await qc.refetchQueries({ queryKey: [...QK_AUD, audPage] })
  }, [qc, audPage])

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

  const onActualizacionManualDesdeGoogle = async () => {
    setManualSyncing(true)
    try {
      const syncRes = await reporteService.syncConciliacionSheetDesdeDrive()
      await clienteService.postDriveImportRefreshCache()
      await qc.invalidateQueries({ queryKey: [...QK] })
      await qc.refetchQueries({ queryKey: [...QK] })
      const n = syncRes?.row_count
      const filas = typeof n === 'number' ? `${n} fila(s) en snapshot. ` : ''
      toast.success(`${filas}Hoja CONCILIACIÓN traída desde Drive y lista de candidatos actualizada.`)
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo sincronizar la hoja desde Google')
    } finally {
      setManualSyncing(false)
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
      await refetchCandidatosYAuditoria()
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo importar')
    } finally {
      setSaving(false)
    }
  }

  const openEdit = (r: DriveCandidate) => {
    setEditDraft({
      sheet_row_number: r.sheet_row_number,
      cedula: r.col_e_cedula ?? '',
      nombres: r.defaults.nombres,
      telefono: r.defaults.telefono,
      email: r.defaults.email,
      email_secundario: '',
      direccion: r.defaults.direccion,
      fecha_nacimiento: fechaInputFromDefaults(r.defaults.fecha_nacimiento),
      ocupacion: r.defaults.ocupacion,
      estado: (r.defaults.estado || 'ACTIVO').trim().toUpperCase(),
      notas: '',
      comentario: comentario.trim(),
    })
  }

  const postImportarFila = async (
    payload: Parameters<typeof clienteService.postDriveImportImportarFila>[0]
  ) => {
    const res = await clienteService.postDriveImportImportarFila(payload)
    toast.success(`Cliente creado (ID ${res.cliente_id}).`)
    setSelected(prev => {
      const next = { ...prev }
      delete next[payload.sheet_row_number]
      return next
    })
    setHiddenRows(prev => {
      const n = new Set(prev)
      n.delete(payload.sheet_row_number)
      try {
        sessionStorage.setItem(STORAGE_HIDDEN, JSON.stringify([...n]))
      } catch {
        /* ignore */
      }
      return n
    })
    setEditDraft(null)
    await refetchCandidatosYAuditoria()
  }

  const onGuardarFilaRapido = async (r: DriveCandidate) => {
    if (!r.seleccionable) {
      toast.message('Esta fila no se puede importar tal cual (cédula o duplicado en hoja).')
      return
    }
    setSavingRowId(r.sheet_row_number)
    try {
      await postImportarFila(buildImportarFilaPayload(r, comentario))
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo guardar la fila')
    } finally {
      setSavingRowId(null)
    }
  }

  const onGuardarEdicion = async () => {
    if (!editDraft) return
    setSavingRowId(editDraft.sheet_row_number)
    try {
      await postImportarFila({
        sheet_row_number: editDraft.sheet_row_number,
        cedula: editDraft.cedula,
        nombres: editDraft.nombres,
        telefono: editDraft.telefono,
        email: editDraft.email,
        email_secundario: editDraft.email_secundario.trim() || null,
        direccion: editDraft.direccion,
        fecha_nacimiento: editDraft.fecha_nacimiento,
        ocupacion: editDraft.ocupacion,
        estado: editDraft.estado,
        notas: editDraft.notas.trim() || null,
        comentario: editDraft.comentario.trim() || null,
      })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo guardar')
    } finally {
      setSavingRowId(null)
    }
  }

  const onOcultarFila = (sheetRow: number) => {
    setHiddenRows(prev => {
      const n = new Set(prev)
      n.add(sheetRow)
      try {
        sessionStorage.setItem(STORAGE_HIDDEN, JSON.stringify([...n]))
      } catch {
        /* ignore */
      }
      return n
    })
    setSelected(prev => {
      const next = { ...prev }
      delete next[sheetRow]
      return next
    })
    toast.message(`Fila ${sheetRow} oculta en esta sesión (no borra datos en Drive).`)
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Clientes (Drive)"
        description="Cédulas en la pestaña CONCILIACIÓN (columna E) que aún no están en la tabla clientes. Origen: snapshot en BD (D=nombres, F=teléfono, G=email). Use «Actualización manual» para traer la hoja desde Google ahora; «Actualizar lista» solo recalcula candidatos desde el snapshot ya en BD. Con jobs activos, la lista se materializa dom/mié 03:00 Caracas (tras el sync 02:00). Solo administradores."
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
            {hiddenRows.size > 0 && (
              <Button type="button" variant="ghost" size="sm" onClick={() => persistHidden(new Set())}>
                Mostrar filas ocultas ({hiddenRows.size})
              </Button>
            )}
            <Button
              type="button"
              size="sm"
              onClick={() => void onActualizacionManualDesdeGoogle()}
              disabled={manualSyncing || refreshing || q.isFetching || saving}
            >
              <Download className={`mr-2 h-4 w-4 ${manualSyncing ? 'animate-pulse' : ''}`} />
              {manualSyncing ? 'Sincronizando…' : 'Actualización manual'}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onActualizarLista()}
              disabled={manualSyncing || refreshing || q.isFetching}
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
            <table className="w-full min-w-[980px] text-left text-sm">
              <thead className="bg-muted/60">
                <tr>
                  <th className="px-3 py-2 w-10"></th>
                  <th className="px-3 py-2">Fila</th>
                  <th className="px-3 py-2">Cédula (E)</th>
                  <th className="px-3 py-2">Nombres (D)</th>
                  <th className="px-3 py-2">Teléfono (F)</th>
                  <th className="px-3 py-2">Email (G)</th>
                  <th className="px-3 py-2">Estado</th>
                  <th className="px-3 py-2 whitespace-nowrap">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map(r => {
                  const blocked = !r.seleccionable
                  const chk = !!selected[r.sheet_row_number]
                  const busy = savingRowId === r.sheet_row_number
                  return (
                    <tr key={r.sheet_row_number} className="border-t">
                      <td className="px-3 py-2 align-top">
                        <input
                          type="checkbox"
                          className="h-4 w-4 accent-primary"
                          checked={chk}
                          disabled={blocked || manualSyncing || refreshing}
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
                      <td className="px-3 py-2 align-top">
                        <div className="flex flex-wrap gap-1">
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            className="h-8 w-8"
                            title="Editar y guardar con validación (tabla clientes)"
                            onClick={() => openEdit(r)}
                            disabled={busy || q.isFetching || manualSyncing || refreshing}
                            aria-label={`Editar fila ${r.sheet_row_number}`}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            className="h-8 w-8"
                            title="Guardar esta fila con los valores sugeridos (mismo POST /clientes)"
                            onClick={() => onGuardarFilaRapido(r)}
                            disabled={blocked || busy || q.isFetching || manualSyncing || refreshing}
                            aria-label={`Guardar fila ${r.sheet_row_number}`}
                          >
                            <Save className="h-4 w-4" />
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:text-destructive"
                            title="Ocultar fila en esta sesión"
                            onClick={() => onOcultarFila(r.sheet_row_number)}
                            disabled={busy || manualSyncing}
                            aria-label={`Ocultar fila ${r.sheet_row_number}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
                {!q.isLoading && rows.length > 0 && visibleRows.length === 0 && (
                  <tr>
                    <td className="px-3 py-6 text-muted-foreground" colSpan={8}>
                      Todas las filas están ocultas. Use «Mostrar filas ocultas» arriba para verlas de nuevo.
                    </td>
                  </tr>
                )}
                {!q.isLoading && rows.length === 0 && (
                  <tr>
                    <td className="px-3 py-6 text-muted-foreground" colSpan={8}>
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
                siguen. Cada fila puede editarse, guardarse sola o ocultarse solo en esta pantalla.
              </p>
              <Button
                type="button"
                onClick={onGuardar}
                disabled={saving || q.isFetching || manualSyncing || refreshing}
              >
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

      {editDraft && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="drive-edit-title"
        >
          <Card className="max-h-[90vh] w-full max-w-lg overflow-y-auto shadow-lg">
            <CardHeader>
              <CardTitle id="drive-edit-title" className="text-lg">
                Editar fila {editDraft.sheet_row_number}
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                La cédula debe seguir correspondiendo a la columna E de la hoja (normalización del sistema). El
                guardado usa las mismas validaciones que «Nuevo cliente».
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="ed-ced">
                  Cédula (E)
                </label>
                <Input
                  id="ed-ced"
                  value={editDraft.cedula}
                  onChange={e => setEditDraft(d => (d ? { ...d, cedula: e.target.value } : d))}
                  autoComplete="off"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="ed-nom">
                  Nombres
                </label>
                <Input
                  id="ed-nom"
                  value={editDraft.nombres}
                  onChange={e => setEditDraft(d => (d ? { ...d, nombres: e.target.value } : d))}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="ed-tel">
                  Teléfono
                </label>
                <Input
                  id="ed-tel"
                  value={editDraft.telefono}
                  onChange={e => setEditDraft(d => (d ? { ...d, telefono: e.target.value } : d))}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="ed-mail">
                  Email
                </label>
                <Input
                  id="ed-mail"
                  type="email"
                  value={editDraft.email}
                  onChange={e => setEditDraft(d => (d ? { ...d, email: e.target.value } : d))}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="ed-mail2">
                  Email secundario (opcional)
                </label>
                <Input
                  id="ed-mail2"
                  type="email"
                  value={editDraft.email_secundario}
                  onChange={e => setEditDraft(d => (d ? { ...d, email_secundario: e.target.value } : d))}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="ed-dir">
                  Dirección
                </label>
                <Input
                  id="ed-dir"
                  value={editDraft.direccion}
                  onChange={e => setEditDraft(d => (d ? { ...d, direccion: e.target.value } : d))}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="ed-fn">
                  Fecha de nacimiento
                </label>
                <Input
                  id="ed-fn"
                  type="date"
                  value={editDraft.fecha_nacimiento}
                  onChange={e => setEditDraft(d => (d ? { ...d, fecha_nacimiento: e.target.value } : d))}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="ed-ocu">
                  Ocupación
                </label>
                <Input
                  id="ed-ocu"
                  value={editDraft.ocupacion}
                  onChange={e => setEditDraft(d => (d ? { ...d, ocupacion: e.target.value } : d))}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="ed-est">
                  Estado cliente
                </label>
                <select
                  id="ed-est"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={editDraft.estado}
                  onChange={e => setEditDraft(d => (d ? { ...d, estado: e.target.value } : d))}
                >
                  {(estadosCliente.length ? estadosCliente : [{ valor: 'ACTIVO', etiqueta: 'ACTIVO', orden: 0 }]).map(
                    op => (
                      <option key={op.valor} value={op.valor}>
                        {op.etiqueta}
                      </option>
                    )
                  )}
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="ed-notas">
                  Notas (opcional)
                </label>
                <Textarea
                  id="ed-notas"
                  rows={2}
                  value={editDraft.notas}
                  onChange={e => setEditDraft(d => (d ? { ...d, notas: e.target.value } : d))}
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium" htmlFor="ed-com">
                  Comentario auditoría (opcional)
                </label>
                <Textarea
                  id="ed-com"
                  rows={2}
                  value={editDraft.comentario}
                  onChange={e => setEditDraft(d => (d ? { ...d, comentario: e.target.value } : d))}
                />
              </div>
              <div className="flex flex-wrap justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => setEditDraft(null)}>
                  Cancelar
                </Button>
                <Button
                  type="button"
                  onClick={() => onGuardarEdicion()}
                  disabled={savingRowId === editDraft.sheet_row_number}
                >
                  {savingRowId === editDraft.sheet_row_number ? 'Guardando…' : 'Guardar en clientes'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
