import { useCallback, useEffect, useMemo, useState } from 'react'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  ChevronLeft,
  ChevronRight,
  Download,
  Edit2,
  FileSpreadsheet,
  RefreshCw,
  Save,
  Trash2,
  User,
} from 'lucide-react'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Textarea } from '../components/ui/textarea'
import { useEstadosCliente } from '../hooks/useEstadosCliente'
import { clienteService } from '../services/clienteService'
import { reporteService } from '../services/reporteService'
import { toast } from 'sonner'
import { getErrorMessage, isAxiosError } from '../types/errors'

const QK = ['notificaciones', 'clientes-drive', 'candidatos'] as const
const QK_AUD = ['notificaciones', 'clientes-drive', 'auditoria'] as const

const STORAGE_HIDDEN = 'notificaciones-drive-candidatos-ocultos'
const EMAIL_PLACEHOLDER_DRIVE = 'revisar@email.com'
const CANDIDATOS_PAGE_SIZE = 20
const CANDIDATOS_PAGE_BUTTONS = 5

function candidatosPageWindow(current: number, total: number, maxButtons: number): number[] {
  if (total <= 0) return []
  if (total <= maxButtons) return Array.from({ length: total }, (_, i) => i + 1)
  let start = Math.max(1, current - Math.floor(maxButtons / 2))
  let end = start + maxButtons - 1
  if (end > total) {
    end = total
    start = Math.max(1, end - maxButtons + 1)
  }
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
}

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

/** Regla alineada con el backend: solo filas «verdes» (cédula válida y no duplicada en snapshot Drive). */
function filaCumpleValidadoresImportacion(r: DriveCandidate | undefined): r is DriveCandidate {
  return r != null && r.seleccionable === true
}

/** Origen del estado en lista (antes de importar a `clientes`). */
function etiquetaValidadorPantalla(r: DriveCandidate): string {
  if (!r.cedula_valida) {
    return 'Validador: validate_cedula (backend /validadores, formato V|E|G|J + 6–11 dígitos)'
  }
  if (r.duplicada_en_hoja) {
    return 'Regla: cédula normalizada repetida en más de una fila del snapshot Drive (columna E)'
  }
  return 'Pantalla OK: cédula válida y única en hoja · al guardar: ClienteCreate + anti-duplicados en clientes'
}

function mensajeErrorImportCliente(error: unknown, contexto: string): string {
  const base = getErrorMessage(error) || 'Error desconocido'
  if (!isAxiosError(error)) return `${contexto}: ${base}`
  const st = error.response?.status
  if (st === 409) {
    return `${contexto} — 409 en BD (cédula, nombre completo o correo ya usado por otro cliente): ${base}`
  }
  if (st === 422) {
    return `${contexto} — 422 validación ClienteCreate / Pydantic: ${base}`
  }
  if (st === 400) {
    return `${contexto} — 400 (p. ej. cédula no coincide con fila Drive o fila no importable): ${base}`
  }
  if (st === 404) {
    return `${contexto} — 404 (fila ya no está entre candidatos): ${base}`
  }
  if (st === 502 || st === 503) {
    return `${contexto} — error de servidor/red (${st ?? '—'}): ${base}`
  }
  return `${contexto} (${st ?? '—'}): ${base}`
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
  const [candidatosPage, setCandidatosPage] = useState(1)
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

  /** Solo filas que pasan validadores de esta pantalla (mismo criterio que `seleccionable` en API). */
  const filasValidasVisibles = useMemo(
    () => visibleRows.filter(r => filaCumpleValidadoresImportacion(r)),
    [visibleRows]
  )

  const editSourceRow = useMemo(
    () => (editDraft ? rows.find(r => r.sheet_row_number === editDraft.sheet_row_number) : undefined),
    [rows, editDraft]
  )

  const totalCandidatosVisibles = visibleRows.length
  const totalCandidatosPages =
    totalCandidatosVisibles === 0 ? 0 : Math.ceil(totalCandidatosVisibles / CANDIDATOS_PAGE_SIZE)

  useEffect(() => {
    if (totalCandidatosPages === 0) return
    setCandidatosPage(p => Math.min(Math.max(1, p), totalCandidatosPages))
  }, [totalCandidatosPages])

  const candidatosPageNumbers = useMemo(
    () => candidatosPageWindow(candidatosPage, totalCandidatosPages, CANDIDATOS_PAGE_BUTTONS),
    [candidatosPage, totalCandidatosPages]
  )

  const pagedVisibleRows = useMemo(() => {
    if (!visibleRows.length) return []
    const start = (candidatosPage - 1) * CANDIDATOS_PAGE_SIZE
    return visibleRows.slice(start, start + CANDIDATOS_PAGE_SIZE)
  }, [visibleRows, candidatosPage])

  const toggle = useCallback((sheetRow: number, checked: boolean) => {
    setSelected(prev => ({ ...prev, [sheetRow]: checked }))
  }, [])

  const seleccionados = useMemo(
    () => Object.entries(selected).filter(([, v]) => v).map(([k]) => Number(k)),
    [selected]
  )

  const seleccionadosTodosImportables = useMemo(() => {
    if (seleccionados.length === 0) return false
    return seleccionados.every(sr =>
      filaCumpleValidadoresImportacion(rows.find(r => r.sheet_row_number === sr))
    )
  }, [seleccionados, rows])

  const [saving, setSaving] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  /** Descarga la pestaña CONCILIACIÓN desde Google (POST /conciliacion-sheet/sync-now) y luego recalcula candidatos. */
  const [manualSyncing, setManualSyncing] = useState(false)
  const [exportingModo, setExportingModo] = useState<
    null | 'solo_no_seleccionable' | 'todos_candidatos'
  >(null)

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

  const importarLote = useCallback(
    async (sheet_row_numbers: number[], comentarioAuditoria: string | null) => {
      setSaving(true)
      try {
        const res = await clienteService.postDriveImportImportar({
          sheet_row_numbers,
          comentario: comentarioAuditoria,
        })
        toast.success(
          `Proceso terminado: ${res.insertados_ok} insertado(s), ${res.errores} error(es). Lote ${res.batch_id}`
        )
        if (res.errores > 0 && Array.isArray(res.resultados)) {
          const fallos = res.resultados.filter(x => !x.ok).slice(0, 4)
          const partes = fallos.map(f => {
            const err = String(f.error ?? 'Error')
            const short = err.length > 140 ? `${err.slice(0, 140)}…` : err
            return `Fila ${f.sheet_row_number}: ${short}`
          })
          toast.warning(
            `Fallos por fila (${res.errores}): ${partes.join(' · ')}${res.errores > fallos.length ? ' …' : ''}`,
            { duration: 14000 }
          )
        }
        setSelected({})
        setComentario('')
        await refetchCandidatosYAuditoria()
      } catch (e) {
        toast.error(
          mensajeErrorImportCliente(e, 'Importación masiva (POST /clientes/drive-import/importar)')
        )
      } finally {
        setSaving(false)
      }
    },
    [refetchCandidatosYAuditoria]
  )

  const onGuardar = async () => {
    if (!seleccionados.length) {
      toast.message('Seleccione al menos una fila.')
      return
    }
    const noImportables = seleccionados.filter(
      sr => !filaCumpleValidadoresImportacion(rows.find(r => r.sheet_row_number === sr))
    )
    if (noImportables.length > 0) {
      toast.error(
        `No se puede guardar: ${noImportables.length} fila(s) no cumplen el 100% de validadores de esta pantalla (cédula válida y única en el snapshot de la hoja). Quite esas filas de la selección o corríjalas en Drive y sincronice.`
      )
      return
    }
    await importarLote(seleccionados, comentario.trim() || null)
  }

  /** Importa todas las filas 100% válidas en la vista (seleccionable), sin usar checkboxes. */
  const onGuardarSoloValidasSinMarcar = async () => {
    const nums = filasValidasVisibles.map(r => r.sheet_row_number)
    if (!nums.length) {
      toast.message(
        'No hay filas que cumplan el 100% de validadores (cédula válida y no duplicada en hoja) en la lista visible.'
      )
      return
    }
    const audit =
      [comentario.trim(), 'Importación automática: solo filas que cumplen validadores (sin marcar).']
        .filter(Boolean)
        .join(' — ') || null
    await importarLote(nums, audit)
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
    if (!filaCumpleValidadoresImportacion(r)) {
      toast.error(
        'No se puede guardar: la fila no cumple el 100% de validadores (cédula válida y no duplicada en el snapshot de la hoja). Corrija en Google Sheet y sincronice, o use Excel según su flujo.'
      )
      return
    }
    setSavingRowId(r.sheet_row_number)
    try {
      await postImportarFila(buildImportarFilaPayload(r, comentario))
    } catch (e) {
      toast.error(
        mensajeErrorImportCliente(e, 'Guardar fila (POST /clientes/drive-import/importar-fila)')
      )
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
      toast.error(
        mensajeErrorImportCliente(e, 'Guardar desde edición (POST /clientes/drive-import/importar-fila)')
      )
    } finally {
      setSavingRowId(null)
    }
  }

  const onExportarExcel = async (modo: 'solo_no_seleccionable' | 'todos_candidatos') => {
    setExportingModo(modo)
    try {
      await clienteService.postDriveImportExportarExcel(modo)
      toast.success(
        modo === 'solo_no_seleccionable'
          ? 'Excel descargado. Las filas no válidas (rojo/ámbar) se eliminaron del snapshot en BD; vuelven con «Actualización manual» desde Google.'
          : 'Excel descargado. Todas las filas exportadas se eliminaron del snapshot en BD; vuelven con «Actualización manual» desde Google.'
      )
      setSelected({})
      await refetchCandidatosYAuditoria()
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo generar el Excel')
    } finally {
      setExportingModo(null)
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
        description="Cédulas en la pestaña CONCILIACIÓN (columna E) que aún no están en la tabla clientes. Origen: snapshot en BD (D=nombres, F=teléfono, G=email). Regla fija: solo las filas en verde (100% validadores de hoja: cédula válida y no duplicada en el snapshot) pueden guardarse en clientes, en lote o por fila; las rojas o ámbar no permiten guardar hasta corregir en Drive y sincronizar. Puede exportarlas a Excel (cada exportación borra esas filas del snapshot en BD hasta el próximo sync). Use «Actualización manual» para traer la hoja desde Google ahora; «Actualizar lista» solo recalcula candidatos desde el snapshot ya en BD. Con jobs activos, la lista se materializa dom/mié 03:00 Caracas (tras el sync 02:00). Solo administradores."
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
            <Button
              type="button"
              variant="outline"
              size="sm"
              title="Solo filas rojo/ámbar. Descarga Excel y elimina esas filas del snapshot drive en BD."
              onClick={() => void onExportarExcel('solo_no_seleccionable')}
              disabled={
                manualSyncing ||
                refreshing ||
                q.isFetching ||
                saving ||
                exportingModo !== null
              }
            >
              <FileSpreadsheet
                className={`mr-2 h-4 w-4 ${exportingModo === 'solo_no_seleccionable' ? 'animate-pulse' : ''}`}
              />
              {exportingModo === 'solo_no_seleccionable' ? 'Excel…' : 'Excel no válidas'}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              title="Toda la lista actual de candidatos. Descarga Excel y elimina esas filas del snapshot drive en BD."
              onClick={() => void onExportarExcel('todos_candidatos')}
              disabled={
                manualSyncing ||
                refreshing ||
                q.isFetching ||
                saving ||
                exportingModo !== null
              }
            >
              <FileSpreadsheet
                className={`mr-2 h-4 w-4 ${exportingModo === 'todos_candidatos' ? 'animate-pulse' : ''}`}
              />
              {exportingModo === 'todos_candidatos' ? 'Excel…' : 'Excel todos'}
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
            <table className="w-full min-w-[920px] table-fixed border-collapse text-left text-sm">
              <colgroup>
                <col className="w-[4%]" />
                <col className="w-[6%]" />
                <col className="w-[12%]" />
                <col className="w-[22%]" />
                <col className="w-[11%]" />
                <col className="w-[18%]" />
                <col className="w-[19%]" />
                <col className="w-[8%]" />
              </colgroup>
              <thead className="bg-muted/60">
                <tr>
                  <th className="px-2 py-2"></th>
                  <th className="px-2 py-2">Fila</th>
                  <th className="px-2 py-2">Cédula (E)</th>
                  <th className="px-2 py-2">Nombres (D)</th>
                  <th className="px-2 py-2">Teléfono (F)</th>
                  <th className="px-2 py-2">Email (G)</th>
                  <th className="px-2 py-2">Estado</th>
                  <th className="px-2 py-2 text-center whitespace-nowrap">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {pagedVisibleRows.map(r => {
                  const blocked = !r.seleccionable
                  const chk = !!selected[r.sheet_row_number]
                  const busy = savingRowId === r.sheet_row_number
                  const rowTint = r.seleccionable
                    ? 'bg-emerald-50/90 hover:bg-emerald-50 dark:bg-emerald-950/25 dark:hover:bg-emerald-950/35'
                    : !r.cedula_valida
                      ? 'bg-red-50/90 hover:bg-red-50 dark:bg-red-950/25 dark:hover:bg-red-950/35'
                      : 'bg-amber-50/90 hover:bg-amber-50 dark:bg-amber-950/20 dark:hover:bg-amber-950/30'
                  return (
                    <tr key={r.sheet_row_number} className={`border-t ${rowTint}`}>
                      <td className="min-w-0 px-2 py-2 align-top">
                        <input
                          type="checkbox"
                          className="h-4 w-4 accent-primary"
                          checked={chk}
                          disabled={blocked || manualSyncing || refreshing}
                          onChange={e => toggle(r.sheet_row_number, e.target.checked)}
                          aria-label={`Seleccionar fila ${r.sheet_row_number}`}
                        />
                      </td>
                      <td className="min-w-0 px-2 py-2 align-top font-mono tabular-nums">
                        {r.sheet_row_number}
                      </td>
                      <td className="min-w-0 px-2 py-2 align-top font-mono break-words">
                        {r.col_e_cedula ?? ''}
                      </td>
                      <td className="min-w-0 px-2 py-2 align-top break-words">{r.defaults.nombres}</td>
                      <td className="min-w-0 px-2 py-2 align-top font-mono break-words">
                        {r.defaults.telefono || '—'}
                      </td>
                      <td className="min-w-0 px-2 py-2 align-top break-all">{r.defaults.email}</td>
                      <td className="min-w-0 px-2 py-2 align-top text-xs break-words">
                        <div className="space-y-1">
                          {!r.cedula_valida && (
                            <div className="font-medium text-red-600">Inválida: {r.cedula_error}</div>
                          )}
                          {r.cedula_valida && r.duplicada_en_hoja && (
                            <div className="font-medium text-amber-700">
                              Repetida en hoja (no importable)
                            </div>
                          )}
                          {r.cedula_valida && !r.duplicada_en_hoja && (
                            <div className="font-medium text-emerald-700">Listo para revisión</div>
                          )}
                          <p className="text-[11px] leading-snug text-muted-foreground">
                            {etiquetaValidadorPantalla(r)}
                          </p>
                          {r.defaults.email === EMAIL_PLACEHOLDER_DRIVE && (
                            <p className="text-[11px] leading-snug text-amber-800/90 dark:text-amber-200/90">
                              Columna G: el correo no pasó la validación básica en servidor; se propone
                              placeholder hasta corregir en edición.
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="min-w-0 px-2 py-2 align-top">
                        <div className="flex flex-wrap justify-center gap-1">
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

          {totalCandidatosPages > 0 && (
            <div className="flex flex-col items-center gap-2 py-1">
              <div className="flex flex-wrap items-center justify-center gap-1.5">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="gap-1 rounded-md border-border"
                  disabled={candidatosPage <= 1 || manualSyncing || refreshing || saving}
                  onClick={() => setCandidatosPage(p => Math.max(1, p - 1))}
                >
                  <ChevronLeft className="h-4 w-4 shrink-0" aria-hidden />
                  Anterior
                </Button>
                {candidatosPageNumbers.map(n => (
                  <Button
                    key={n}
                    type="button"
                    variant={n === candidatosPage ? 'default' : 'outline'}
                    size="sm"
                    className="min-w-9 rounded-md px-2"
                    disabled={manualSyncing || refreshing || saving}
                    onClick={() => setCandidatosPage(n)}
                  >
                    {n}
                  </Button>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="gap-1 rounded-md border-border"
                  disabled={candidatosPage >= totalCandidatosPages || manualSyncing || refreshing || saving}
                  onClick={() => setCandidatosPage(p => Math.min(totalCandidatosPages, p + 1))}
                >
                  Siguiente
                  <ChevronRight className="h-4 w-4 shrink-0" aria-hidden />
                </Button>
              </div>
              <p className="text-center text-sm text-muted-foreground">
                Página {candidatosPage} de {totalCandidatosPages}
              </p>
            </div>
          )}

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
                cédula, nombre, correo, teléfono). Además, en esta pantalla no se permite guardar ninguna
                fila que no esté en verde: cédula válida y única en el snapshot de la hoja. Si una fila
                del lote no cumple, no se envía el lote entero hasta que quite esas filas de la
                selección. Cada fila puede editarse u ocultarse en esta sesión; el botón guardar por
                fila solo actúa si la fila cumple el 100% de validadores de hoja.
              </p>
              <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                <Button
                  type="button"
                  onClick={() => void onGuardarSoloValidasSinMarcar()}
                  disabled={saving || q.isFetching || manualSyncing || refreshing || filasValidasVisibles.length === 0}
                >
                  {saving ? 'Guardando…' : `Guardar (${filasValidasVisibles.length} válida(s))`}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={onGuardar}
                  disabled={
                    saving ||
                    q.isFetching ||
                    manualSyncing ||
                    refreshing ||
                    seleccionados.length === 0 ||
                    !seleccionadosTodosImportables
                  }
                  title={
                    seleccionados.length && !seleccionadosTodosImportables
                      ? 'Hay filas seleccionadas que no cumplen el 100% de validadores de hoja; no se puede guardar.'
                      : undefined
                  }
                >
                  {saving ? 'Guardando…' : `Guardar seleccionados (${seleccionados.length})`}
                </Button>
              </div>
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
            <table className="w-full min-w-[900px] table-fixed border-collapse text-left text-sm">
              <colgroup>
                <col className="w-[13%]" />
                <col className="w-[14%]" />
                <col className="w-[9%]" />
                <col className="w-[6%]" />
                <col className="w-[10%]" />
                <col className="w-[22%]" />
                <col className="w-[26%]" />
              </colgroup>
              <thead className="bg-muted/60">
                <tr>
                  <th className="px-2 py-2">Fecha</th>
                  <th className="px-2 py-2">Usuario</th>
                  <th className="px-2 py-2">Estado</th>
                  <th className="px-2 py-2">Fila</th>
                  <th className="px-2 py-2">Cédula</th>
                  <th className="px-2 py-2">Comentario</th>
                  <th className="px-2 py-2">Detalle</th>
                </tr>
              </thead>
              <tbody>
                {(qa.data?.items ?? []).map(it => (
                  <tr key={it.id} className="border-t">
                    <td className="min-w-0 whitespace-nowrap px-2 py-2 text-xs">
                      {it.creado_en
                        ? new Date(it.creado_en).toLocaleString('es-VE', {
                            timeZone: 'America/Caracas',
                          })
                        : '—'}
                    </td>
                    <td className="min-w-0 break-words px-2 py-2 text-xs">{it.usuario_email}</td>
                    <td className="min-w-0 break-words px-2 py-2 text-xs">{it.estado}</td>
                    <td className="min-w-0 px-2 py-2 font-mono text-xs tabular-nums">
                      {it.sheet_row_number}
                    </td>
                    <td className="min-w-0 break-words px-2 py-2 font-mono text-xs">{it.cedula}</td>
                    <td className="min-w-0 break-words px-2 py-2 text-xs">{it.comentario ?? '—'}</td>
                    <td className="min-w-0 break-words px-2 py-2 text-xs text-red-700">
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
                  disabled={
                    savingRowId === editDraft.sheet_row_number ||
                    !filaCumpleValidadoresImportacion(editSourceRow)
                  }
                  title={
                    !filaCumpleValidadoresImportacion(editSourceRow)
                      ? 'Solo se puede guardar si la fila cumple el 100% de validadores de hoja (fila en verde en la lista).'
                      : undefined
                  }
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
