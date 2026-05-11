/**
 * Actualizaciones > Gmail: re-escaneo por remitente con un solo paso.
 *
 * Flujo:
 *   1) Operador escribe un correo y elige cuántos correos rastrear (default 20, tope duro 5000).
 *   2) Backend lista en Gmail los correos `from:<correo>` que cumplen el criterio (imagen/PDF en
 *      bandeja), corta a "Hasta N" (head, más reciente primero) y los procesa todos con el mismo
 *      pipeline vigente (Gemini -> plantillas A-F -> BD -> cascada cuotas -> etiqueta final).
 *   3) Al terminar, la tabla de resultados muestra las filas extraídas para ese remitente con
 *      acciones Guardar / Editar / Eliminar (Guardar = migrar a pagos_con_errores + mover-a-pagos).
 *
 * No hay paso intermedio de "preview + checkbox": Gemini solo se gasta en los correos del
 * remitente (típicamente pocos), nunca en toda la bandeja.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Mail,
  Pencil,
  RefreshCw,
  Save,
  Search,
  TestTube,
  Trash2,
  X,
} from 'lucide-react'

import { toast } from 'sonner'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import { Input } from '../components/ui/input'
import {
  pagoService,
  type GmailPreviewItemUI,
  type GmailSyncItemUI,
} from '../services/pagoService'
import { useGmailPipeline } from '../hooks/useGmailPipeline'
import { getErrorMessage } from '../types/errors'

const QK_LIST = ['actualizaciones', 'gmail', 'sync-items'] as const

const PAGE_SIZE = 50

/** Tope "Hasta N correos" del rastreo Gmail; default 20, máximo absoluto backend = 10000. */
const MAX_MESSAGES_DEFAULT = 20
const MAX_MESSAGES_OPTIONS = [20, 50, 100, 500, 1000, 5000, 10000] as const

function urlComprobante(raw: string | null | undefined): string | null {
  const s = (raw || '').trim()
  if (!s) return null
  return s
}

function safeMonto(item: GmailSyncItemUI): string {
  const m = (item.monto || '').trim()
  return m || '-'
}

interface FilaEnEdicion {
  banco: string
  cedula: string
  fecha_pago: string
  monto: string
  numero_referencia: string
}

function filaInicialDesdeItem(item: GmailSyncItemUI): FilaEnEdicion {
  return {
    banco: item.banco || '',
    cedula: item.cedula || '',
    fecha_pago: item.fecha_pago || '',
    monto: item.monto || '',
    numero_referencia: item.numero_referencia || '',
  }
}

interface DiagnosticoGmail {
  correo: string
  total: number
  conMedia: number
  yaProcesados: number
  hayMasEnGmail: boolean
  items: GmailPreviewItemUI[]
  mensaje?: string
}

export default function ActualizacionesGmailPage() {
  const queryClient = useQueryClient()
  const [correoInput, setCorreoInput] = useState('')
  const [correoActivo, setCorreoActivo] = useState('')
  const [maxMessages, setMaxMessages] = useState<number>(MAX_MESSAGES_DEFAULT)
  const [paginaTabla, setPaginaTabla] = useState(1)
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [edicion, setEdicion] = useState<FilaEnEdicion | null>(null)
  const [diagnostico, setDiagnostico] = useState<DiagnosticoGmail | null>(null)
  const [probandoGmail, setProbandoGmail] = useState(false)

  const offsetTabla = (paginaTabla - 1) * PAGE_SIZE
  const tabla = useQuery({
    queryKey: [...QK_LIST, correoActivo, paginaTabla],
    queryFn: () =>
      pagoService.listGmailSyncItems({
        correo: correoActivo,
        limit: PAGE_SIZE,
        offset: offsetTabla,
      }),
    enabled: !!correoActivo,
    refetchOnWindowFocus: false,
  })

  const { loading: ejecutandoPipeline, gmailStatus, run } = useGmailPipeline({
    onDone: () => {
      void queryClient.invalidateQueries({ queryKey: QK_LIST })
    },
  })

  const tablaItems: GmailSyncItemUI[] = useMemo(
    () => tabla.data?.items ?? [],
    [tabla.data]
  )

  const tablaTotal = tabla.data?.total ?? 0
  const tablaTotalPaginas = Math.max(1, Math.ceil(tablaTotal / PAGE_SIZE))

  const handleBuscarYProcesar = useCallback(async () => {
    const email = correoInput.trim().toLowerCase()
    if (!email || !email.includes('@')) {
      toast.error('Indica un correo valido (ej. cliente@dominio.com).')
      return
    }
    setCorreoActivo(email)
    setPaginaTabla(1)
    await run('manual_redigitaliza_por_remitente', email, maxMessages)
  }, [correoInput, maxMessages, run])

  const handleProbarGmail = useCallback(async () => {
    const email = correoInput.trim().toLowerCase()
    if (!email || !email.includes('@')) {
      toast.error('Indica un correo valido (ej. cliente@dominio.com).')
      return
    }
    setProbandoGmail(true)
    setDiagnostico(null)
    try {
      const res = await pagoService.previewGmailRemitente(email, {
        maxResults: Math.max(20, Math.min(maxMessages, 100)),
      })
      const items = res.items || []
      const conMedia = items.filter(it => it.tiene_media).length
      const yaProcesados = items.filter(it => it.ya_procesado_en_bd).length
      setDiagnostico({
        correo: email,
        total: res.total ?? items.length,
        conMedia,
        yaProcesados,
        hayMasEnGmail: !!res.hay_mas_en_gmail,
        items,
        mensaje: res.mensaje,
      })
      if ((res.total ?? items.length) === 0) {
        toast(
          `Gmail no encontro correos para "${email}" con el criterio (in:inbox + imagen/PDF). ` +
            'Verifica que la cuenta Gmail conectada al sistema sea la correcta, ' +
            'que el correo este bien escrito y que los mensajes esten en bandeja (no archivados).',
          { duration: 9000 }
        )
      } else {
        toast.success(
          `Gmail encontro ${res.total ?? items.length} correo(s) del remitente; ${conMedia} con adjunto imagen/PDF.`
        )
      }
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo probar Gmail')
    } finally {
      setProbandoGmail(false)
    }
  }, [correoInput, maxMessages])

  const handleLimpiar = useCallback(() => {
    setCorreoInput('')
    setCorreoActivo('')
    setPaginaTabla(1)
    setDiagnostico(null)
  }, [])

  const guardarMutation = useMutation({
    mutationFn: (itemId: number) => pagoService.guardarGmailSyncItem(itemId),
    onSuccess: res => {
      toast.success(res.mensaje || 'Pago guardado.')
      void queryClient.invalidateQueries({ queryKey: QK_LIST })
    },
    onError: err => {
      toast.error(getErrorMessage(err) || 'No se pudo guardar')
    },
  })

  const eliminarMutation = useMutation({
    mutationFn: (itemId: number) => pagoService.deleteGmailSyncItem(itemId),
    onSuccess: () => {
      toast.success('Fila eliminada.')
      void queryClient.invalidateQueries({ queryKey: QK_LIST })
    },
    onError: err => {
      toast.error(getErrorMessage(err) || 'No se pudo eliminar')
    },
  })

  const editarMutation = useMutation({
    mutationFn: ({
      itemId,
      cambios,
    }: {
      itemId: number
      cambios: FilaEnEdicion
    }) => pagoService.editGmailSyncItem(itemId, cambios),
    onSuccess: () => {
      toast.success('Cambios guardados.')
      setEditandoId(null)
      setEdicion(null)
      void queryClient.invalidateQueries({ queryKey: QK_LIST })
    },
    onError: err => {
      toast.error(getErrorMessage(err) || 'No se pudo editar')
    },
  })

  const handleEditar = useCallback((item: GmailSyncItemUI) => {
    setEditandoId(item.id)
    setEdicion(filaInicialDesdeItem(item))
  }, [])

  const handleCancelarEdicion = useCallback(() => {
    setEditandoId(null)
    setEdicion(null)
  }, [])

  const handleGuardarEdicion = useCallback(() => {
    if (editandoId == null || edicion == null) return
    editarMutation.mutate({ itemId: editandoId, cambios: edicion })
  }, [editandoId, edicion, editarMutation])

  const handleEliminar = useCallback(
    (item: GmailSyncItemUI) => {
      const ok = window.confirm(
        `Eliminar la fila del comprobante ${item.numero_referencia || '(sin serial)'} (${item.banco || 'sin banco'})?\n\n` +
          'Esto borra la fila local (no toca Gmail).'
      )
      if (!ok) return
      eliminarMutation.mutate(item.id)
    },
    [eliminarMutation]
  )

  const handleGuardar = useCallback(
    (item: GmailSyncItemUI) => {
      if (item.duplicado_en_pagos) {
        const ok = window.confirm(
          `El serial ${item.numero_referencia || '(s/r)'} ya existe en pagos (id ${item.pago_id_existente ?? '?'}). ` +
            'Eliminar esta fila de revision? No se creara un duplicado en cartera.'
        )
        if (!ok) return
      }
      guardarMutation.mutate(item.id)
    },
    [guardarMutation]
  )

  useEffect(() => {
    if (!ejecutandoPipeline && gmailStatus?.last_status === 'success') {
      void queryClient.invalidateQueries({ queryKey: QK_LIST })
    }
  }, [ejecutandoPipeline, gmailStatus?.last_status, queryClient])

  const editingActive = editandoId != null && edicion != null

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Actualizaciones · Gmail"
        description={
          'Re-escaneo por remitente en un solo paso. Pones un correo, eliges cuantos correos rastrear ' +
          '(por defecto 20, maximo 10000), y el sistema lista en Gmail los mensajes `from:<correo>` con ' +
          'imagen/PDF en bandeja y los procesa con el flujo vigente (Gemini -> plantillas A-F -> BD -> ' +
          'cascada cuotas -> etiqueta final). Gemini solo se gasta en los correos del remitente.'
        }
        icon={Mail}
      />

      <Card>
        <CardHeader className="space-y-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <CardTitle className="text-lg">
              Rastrear y procesar correos del remitente
            </CardTitle>
            <div className="text-xs text-muted-foreground">
              {ejecutandoPipeline || gmailStatus?.last_status === 'running' ? (
                <span className="text-amber-700">Pipeline en curso...</span>
              ) : gmailStatus?.last_run ? (
                <span>
                  Ultima sync Gmail:{' '}
                  {new Date(gmailStatus.last_run).toLocaleString()}
                </span>
              ) : (
                <span>Sin sync Gmail aun</span>
              )}
            </div>
          </div>
          <form
            onSubmit={e => {
              e.preventDefault()
              void handleBuscarYProcesar()
            }}
            className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center"
          >
            <Input
              type="email"
              autoComplete="email"
              placeholder="correo@dominio.com"
              value={correoInput}
              onChange={e => setCorreoInput(e.target.value)}
              className="sm:max-w-md"
              disabled={ejecutandoPipeline}
            />
            <label className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Hasta</span>
              <select
                value={maxMessages}
                onChange={e => setMaxMessages(Number(e.target.value))}
                className="rounded-md border border-input bg-background px-2 py-1 text-xs"
                disabled={ejecutandoPipeline}
              >
                {MAX_MESSAGES_OPTIONS.map(v => (
                  <option key={v} value={v}>
                    {v} correo(s)
                  </option>
                ))}
              </select>
            </label>
            <div className="flex flex-wrap gap-2">
              <Button
                type="submit"
                disabled={ejecutandoPipeline || !correoInput.trim()}
                title={
                  'Lista en Gmail los correos `from:<correo>` con imagen/PDF y procesa los primeros N ' +
                  '(mas reciente primero) con el flujo vigente. Gemini solo gasta en estos correos.'
                }
              >
                {ejecutandoPipeline ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Search className="mr-2 h-4 w-4" />
                )}
                Buscar y procesar
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => void handleProbarGmail()}
                disabled={
                  probandoGmail || ejecutandoPipeline || !correoInput.trim()
                }
                title="Solo cuenta y lista (sin escanear con Gemini) lo que Gmail encuentra con la misma query. Util para diagnostico cuando 'Buscar y procesar' devuelve 0 resultados."
              >
                {probandoGmail ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <TestTube className="mr-2 h-4 w-4" />
                )}
                Probar Gmail
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => void tabla.refetch()}
                disabled={!correoActivo || tabla.isFetching}
                title="Refrescar tabla de resultados"
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                Refrescar tabla
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={handleLimpiar}
                disabled={ejecutandoPipeline || (!correoActivo && !correoInput)}
              >
                Limpiar
              </Button>
            </div>
          </form>
          <div className="rounded-md border border-dashed bg-muted/20 p-3 text-xs text-muted-foreground">
            <strong>Como funciona:</strong> el sistema rastrea en Gmail solo los
            correos del remitente (filtro <code>from:&lt;correo&gt;</code> +
            adjunto imagen/PDF en bandeja), toma los <strong>N mas recientes</strong>
            (segun el selector &laquo;Hasta&raquo;) y los procesa todos con el
            pipeline vigente. Asi no se gasta Gemini en la bandeja completa
            (~6000 correos), solo en los del remitente (tipicamente ~20). El
            tope absoluto por corrida es 10000.
            <br />
            Si <strong>Buscar y procesar</strong> reporta 0 correos pero en Gmail si
            hay, pulsa <strong>Probar Gmail</strong> para ver que encuentra la
            query (sin gastar Gemini).
          </div>
          {diagnostico ? (
            <div
              className={
                'rounded-md border p-3 text-xs ' +
                (diagnostico.total === 0
                  ? 'border-amber-300 bg-amber-50 text-amber-900'
                  : 'border-emerald-300 bg-emerald-50 text-emerald-900')
              }
            >
              <div className="flex items-center gap-2 font-medium">
                {diagnostico.total === 0 ? (
                  <AlertTriangle className="h-4 w-4" />
                ) : (
                  <CheckCircle2 className="h-4 w-4" />
                )}
                Diagnostico Gmail para <code>{diagnostico.correo}</code>
              </div>
              <ul className="mt-2 list-disc pl-5">
                <li>
                  Correos del remitente listados por Gmail (criterio inbox +
                  imagen/PDF): <strong>{diagnostico.total}</strong>
                </li>
                <li>
                  Con adjunto imagen/PDF detectado:{' '}
                  <strong>{diagnostico.conMedia}</strong>
                </li>
                <li>
                  Ya procesados antes en BD (mismo gmail_message_id):{' '}
                  <strong>{diagnostico.yaProcesados}</strong>
                </li>
                {diagnostico.hayMasEnGmail ? (
                  <li>
                    Hay <strong>mas correos</strong> del remitente en Gmail mas
                    alla del tope &laquo;Hasta&raquo;. Sube el selector para
                    cubrirlos.
                  </li>
                ) : null}
              </ul>
              {diagnostico.total === 0 ? (
                <div className="mt-2">
                  <strong>Posibles causas:</strong>
                  <ul className="mt-1 list-disc pl-5">
                    <li>
                      La cuenta Gmail conectada al sistema no es la que ve esos
                      correos (cuenta empresarial vs personal).
                    </li>
                    <li>
                      El correo esta mal escrito (revisa mayusculas/dominio).
                    </li>
                    <li>
                      Los mensajes estan archivados o en otra carpeta (no
                      cumplen <code>in:inbox</code>).
                    </li>
                    <li>
                      Los comprobantes vienen como imagenes inline sin filename
                      estandar y Gmail no los considera adjunto. Reporta este
                      caso.
                    </li>
                  </ul>
                </div>
              ) : null}
              {diagnostico.items.length > 0 ? (
                <div className="mt-3 overflow-x-auto rounded border bg-white">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/30 text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                      <tr>
                        <th className="px-2 py-1">Fecha</th>
                        <th className="px-2 py-1">Asunto</th>
                        <th className="px-2 py-1">Adjunto</th>
                        <th className="px-2 py-1">Etiquetas</th>
                      </tr>
                    </thead>
                    <tbody>
                      {diagnostico.items.slice(0, 20).map(it => (
                        <tr key={it.gmail_message_id} className="border-t">
                          <td className="px-2 py-1 tabular-nums">
                            {it.fecha_iso
                              ? new Date(it.fecha_iso).toLocaleString()
                              : '-'}
                          </td>
                          <td
                            className="max-w-[20rem] truncate px-2 py-1"
                            title={it.asunto}
                          >
                            {it.asunto || '(sin asunto)'}
                          </td>
                          <td className="px-2 py-1">
                            {it.tiene_media ? 'Si' : 'No'}
                          </td>
                          <td className="px-2 py-1">
                            {it.etiquetas_usuario.length === 0
                              ? '-'
                              : it.etiquetas_usuario.join(', ')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </div>
          ) : null}
        </CardHeader>
      </Card>

      {correoActivo ? (
        <Card>
          <CardHeader className="space-y-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="text-lg">
                Resultados extraidos por el pipeline
              </CardTitle>
              <Button
                size="sm"
                variant="outline"
                onClick={() => void tabla.refetch()}
                disabled={tabla.isFetching}
              >
                {tabla.isFetching ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Refrescar
              </Button>
            </div>
            <div className="text-xs text-muted-foreground">
              Filas extraidas para <strong>{correoActivo}</strong>: {tablaTotal}
              {tablaTotalPaginas > 1
                ? ` - pagina ${paginaTabla} de ${tablaTotalPaginas}`
                : ''}
            </div>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Fecha correo</th>
                    <th className="px-3 py-2">Imagen</th>
                    <th className="px-3 py-2">Banco</th>
                    <th className="px-3 py-2">Fecha pago</th>
                    <th className="px-3 py-2 text-right">Monto</th>
                    <th className="px-3 py-2">Serial</th>
                    <th className="px-3 py-2">En pagos?</th>
                    <th className="px-3 py-2 text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {tabla.isLoading ? (
                    <tr>
                      <td
                        colSpan={8}
                        className="px-3 py-6 text-center text-muted-foreground"
                      >
                        <Loader2 className="mr-2 inline h-4 w-4 animate-spin" />
                        Cargando...
                      </td>
                    </tr>
                  ) : tablaItems.length === 0 ? (
                    <tr>
                      <td
                        colSpan={8}
                        className="px-3 py-6 text-center text-muted-foreground"
                      >
                        {ejecutandoPipeline
                          ? 'Procesando correos en segundo plano... los resultados apareceran aqui al terminar.'
                          : 'Aun no hay filas. Pulsa "Buscar y procesar" para rastrear y digitalizar los correos del remitente.'}
                      </td>
                    </tr>
                  ) : (
                    tablaItems.map(item => {
                      const enEdicion = editingActive && editandoId === item.id
                      const dup = item.duplicado_en_pagos
                      const compUrl = urlComprobante(item.comprobante_url)
                      return (
                        <tr
                          key={item.id}
                          className={`border-t ${dup ? 'bg-emerald-50/40' : ''}`}
                        >
                          <td className="px-3 py-2 align-top text-xs tabular-nums">
                            {item.fecha_correo || '-'}
                          </td>
                          <td className="px-3 py-2 align-top">
                            {compUrl ? (
                              <a
                                href={compUrl}
                                target="_blank"
                                rel="noreferrer"
                                title="Abrir comprobante"
                                className="inline-block"
                              >
                                <img
                                  src={compUrl}
                                  alt="Comprobante"
                                  className="h-16 w-16 rounded border object-cover"
                                  loading="lazy"
                                  onError={e => {
                                    ;(e.currentTarget as HTMLImageElement).style.display =
                                      'none'
                                  }}
                                />
                              </a>
                            ) : (
                              <span className="inline-flex items-center rounded border border-dashed border-muted-foreground/40 px-2 py-1 text-[11px] text-muted-foreground">
                                Sin imagen
                              </span>
                            )}
                          </td>
                          <td className="px-3 py-2 align-top">
                            {enEdicion ? (
                              <Input
                                value={edicion?.banco || ''}
                                onChange={e =>
                                  setEdicion(
                                    prev =>
                                      prev && { ...prev, banco: e.target.value }
                                  )
                                }
                                className="h-8 text-xs"
                              />
                            ) : (
                              item.banco || '-'
                            )}
                          </td>
                          <td className="px-3 py-2 align-top">
                            {enEdicion ? (
                              <Input
                                value={edicion?.fecha_pago || ''}
                                onChange={e =>
                                  setEdicion(
                                    prev =>
                                      prev && {
                                        ...prev,
                                        fecha_pago: e.target.value,
                                      }
                                  )
                                }
                                placeholder="dd/MM/yyyy o YYYY-MM-DD"
                                className="h-8 text-xs"
                              />
                            ) : (
                              item.fecha_pago || '-'
                            )}
                          </td>
                          <td className="px-3 py-2 text-right align-top tabular-nums">
                            {enEdicion ? (
                              <Input
                                value={edicion?.monto || ''}
                                onChange={e =>
                                  setEdicion(
                                    prev =>
                                      prev && { ...prev, monto: e.target.value }
                                  )
                                }
                                className="h-8 text-right text-xs"
                              />
                            ) : (
                              safeMonto(item)
                            )}
                          </td>
                          <td className="px-3 py-2 align-top">
                            {enEdicion ? (
                              <Input
                                value={edicion?.numero_referencia || ''}
                                onChange={e =>
                                  setEdicion(
                                    prev =>
                                      prev && {
                                        ...prev,
                                        numero_referencia: e.target.value,
                                      }
                                  )
                                }
                                className="h-8 text-xs"
                              />
                            ) : (
                              item.numero_referencia || '-'
                            )}
                          </td>
                          <td className="px-3 py-2 align-top text-xs">
                            {dup ? (
                              <span
                                className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-900"
                                title={`Ya existe en pagos (id ${item.pago_id_existente ?? '?'})`}
                              >
                                <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                                Si - pago {item.pago_id_existente ?? '?'}
                              </span>
                            ) : (
                              <span className="text-muted-foreground">No</span>
                            )}
                            {enEdicion ? (
                              <div className="mt-2">
                                <Input
                                  value={edicion?.cedula || ''}
                                  onChange={e =>
                                    setEdicion(
                                      prev =>
                                        prev && {
                                          ...prev,
                                          cedula: e.target.value,
                                        }
                                    )
                                  }
                                  placeholder="Cedula"
                                  className="h-8 text-xs"
                                />
                              </div>
                            ) : null}
                          </td>
                          <td className="px-3 py-2 text-right align-top">
                            <div className="flex flex-wrap justify-end gap-1.5">
                              {enEdicion ? (
                                <>
                                  <Button
                                    size="sm"
                                    onClick={handleGuardarEdicion}
                                    disabled={editarMutation.isPending}
                                  >
                                    {editarMutation.isPending ? (
                                      <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                                    ) : (
                                      <Save className="mr-1 h-3.5 w-3.5" />
                                    )}
                                    OK
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={handleCancelarEdicion}
                                    disabled={editarMutation.isPending}
                                  >
                                    <X className="mr-1 h-3.5 w-3.5" />
                                    Cancelar
                                  </Button>
                                </>
                              ) : (
                                <>
                                  <Button
                                    size="sm"
                                    onClick={() => handleGuardar(item)}
                                    disabled={
                                      guardarMutation.isPending ||
                                      eliminarMutation.isPending
                                    }
                                    title="Migrar a pagos_con_errores y aplicar mover-a-pagos (cascada cuotas)"
                                  >
                                    {guardarMutation.isPending ? (
                                      <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                                    ) : (
                                      <Save className="mr-1 h-3.5 w-3.5" />
                                    )}
                                    Guardar
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleEditar(item)}
                                    disabled={guardarMutation.isPending}
                                  >
                                    <Pencil className="mr-1 h-3.5 w-3.5" />
                                    Editar
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleEliminar(item)}
                                    disabled={eliminarMutation.isPending}
                                  >
                                    <Trash2 className="mr-1 h-3.5 w-3.5" />
                                    Eliminar
                                  </Button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>

            {tablaTotalPaginas > 1 ? (
              <div className="mt-3 flex items-center justify-between text-xs">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setPaginaTabla(p => Math.max(1, p - 1))}
                  disabled={paginaTabla <= 1 || tabla.isFetching}
                >
                  Anterior
                </Button>
                <span className="text-muted-foreground">
                  Pagina {paginaTabla} de {tablaTotalPaginas}
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    setPaginaTabla(p => Math.min(tablaTotalPaginas, p + 1))
                  }
                  disabled={paginaTabla >= tablaTotalPaginas || tabla.isFetching}
                >
                  Siguiente
                </Button>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
