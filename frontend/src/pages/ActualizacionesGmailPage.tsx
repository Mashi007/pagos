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
import { ComprobanteThumb } from '../components/pagos/ComprobanteThumb'
import { RegistrarPagoForm } from '../components/pagos/RegistrarPagoForm'
import {
  pagoService,
  type GmailPreviewItemUI,
  type GmailSyncItemUI,
  type PagoInicialRegistrar,
} from '../services/pagoService'
import type { PagoConError } from '../services/pagoConErrorService'
import { useGmailPipeline } from '../hooks/useGmailPipeline'
import { getErrorMessage } from '../types/errors'

/**
 * Mapea un PagoConError recién migrado al shape `PagoInicialRegistrar` que necesita
 * el modal `RegistrarPagoForm` (mismo mapeo que usa PagosList para revisión manual).
 */
function pagoInicialDesdePagoConError(
  pe: PagoConError
): PagoInicialRegistrar {
  return {
    cedula_cliente: pe.cedula_cliente,
    prestamo_id: pe.prestamo_id,
    fecha_pago:
      typeof pe.fecha_pago === 'string'
        ? pe.fecha_pago.slice(0, 10)
        : new Date(pe.fecha_pago).toISOString().slice(0, 10),
    monto_pagado:
      pe.moneda_registro === 'BS' && pe.monto_bs_original != null
        ? Number(pe.monto_bs_original)
        : Number(pe.monto_pagado),
    monto_bs_original: pe.monto_bs_original ?? null,
    moneda_registro: pe.moneda_registro === 'BS' ? 'BS' : 'USD',
    numero_documento: pe.numero_documento,
    codigo_documento: pe.codigo_documento ?? null,
    institucion_bancaria: pe.institucion_bancaria,
    notas: pe.notas || null,
    link_comprobante: null,
    documento_ruta: pe.documento_ruta ?? null,
    duplicado_documento_en_pagos: pe.duplicado_documento_en_pagos,
    duplicado_en_cartera_prestamo_id: pe.duplicado_en_cartera_prestamo_id,
    duplicado_en_cartera_pago_id: pe.duplicado_en_cartera_pago_id,
  }
}

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
  const [diagnostico, setDiagnostico] = useState<DiagnosticoGmail | null>(null)
  const [probandoGmail, setProbandoGmail] = useState(false)
  /** Modal de revisión manual abierto sobre un pago_con_error recién migrado. */
  const [editPago, setEditPago] = useState<{
    pagoConErrorId: number
    inicial: PagoInicialRegistrar
  } | null>(null)
  const [migrandoId, setMigrandoId] = useState<number | null>(null)

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
    suppressDoneToasts: true,
    onDone: status => {
      if (!correoActivo) {
        void queryClient.invalidateQueries({ queryKey: QK_LIST })
        return
      }
      // Refrescamos la tabla del remitente y luego mostramos un toast con el
      // conteo real (la cuenta global `last_emails` puede ser 0 cuando todos los
      // correos del remitente ya estaban digitalizados en pagos: el pipeline
      // funcionó, simplemente no creó altas nuevas).
      void queryClient
        .invalidateQueries({ queryKey: QK_LIST })
        .then(async () => {
          let totalFilas = 0
          let yaEnPagos = 0
          try {
            const res = await queryClient.fetchQuery({
              queryKey: [...QK_LIST, correoActivo, 1],
              queryFn: () =>
                pagoService.listGmailSyncItems({
                  correo: correoActivo,
                  limit: PAGE_SIZE,
                  offset: 0,
                }),
            })
            totalFilas = res.total ?? res.items.length
            yaEnPagos = res.items.filter(it => it.duplicado_en_pagos).length
          } catch {
            /* tabla no se pudo recargar; usa fallback abajo */
          }
          if (status.last_status === 'error') {
            toast.error(
              `Pipeline termino con error: ${status.last_error || 'desconocido'}`,
              { duration: 12000 }
            )
            return
          }
          if (totalFilas > 0) {
            const pendientes = Math.max(0, totalFilas - yaEnPagos)
            toast.success(
              `Pipeline terminado para ${correoActivo}. Filas extraidas: ${totalFilas} ` +
                `(${yaEnPagos} ya estan en pagos; ${pendientes} pendientes de validar).`,
              { duration: 12000 }
            )
          } else {
            toast(
              `Pipeline terminado para ${correoActivo}: no se generaron filas. ` +
                'Posibles causas: Gmail no encontro correos del remitente con imagen/PDF en bandeja, ' +
                'o todos los candidatos fueron descartados por Gemini. Pulsa "Probar Gmail" para diagnostico.',
              { duration: 14000 }
            )
          }
        })
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

  /**
   * "Editar" abre el flujo de revisión manual: migra la fila a `pagos_con_errores`
   * y abre el modal `RegistrarPagoForm` con `esPagoConError=true` y
   * `modoGuardarYProcesar=true`. Al guardar y procesar dentro del modal, se aplica
   * la cascada de cuotas estándar.
   */
  const handleEditar = useCallback(
    async (item: GmailSyncItemUI) => {
      setMigrandoId(item.id)
      try {
        const res = await pagoService.migrarGmailSyncItemAPendientes(item.id)
        if (!res.pago_con_error || res.pago_con_error_id == null) {
          toast.error(
            'No se pudo abrir la revision manual (respuesta incompleta del backend).'
          )
          return
        }
        if (res.ya_en_pagos) {
          // Serial repetido: el modal abre con `duplicado_documento_en_pagos=true`
          // y `mostrarCampoCodigoDocumento=true`, permitiendo agregar sufijo
          // (mismo flujo que revisión manual de préstamos).
          toast(
            res.mensaje ||
              `Serial ${item.numero_referencia || '(s/r)'} ya existe en cartera. ` +
                `Agregue un código (sufijo) para diferenciar el pago.`,
            { duration: 8000 }
          )
        }
        const inicial = pagoInicialDesdePagoConError(res.pago_con_error)
        setEditPago({
          pagoConErrorId: res.pago_con_error_id,
          inicial,
        })
        void queryClient.invalidateQueries({ queryKey: QK_LIST })
      } catch (e) {
        toast.error(
          getErrorMessage(e) || 'No se pudo migrar la fila a pagos_con_errores'
        )
      } finally {
        setMigrandoId(null)
      }
    },
    [queryClient]
  )

  const cerrarModalEdit = useCallback(() => {
    setEditPago(null)
  }, [])

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
                      const dup = item.duplicado_en_pagos
                      const compUrl = urlComprobante(item.comprobante_url)
                      const migrandoEste = migrandoId === item.id
                      return (
                        <tr
                          key={item.id}
                          className={`border-t ${dup ? 'bg-emerald-50/40' : ''}`}
                        >
                          <td className="px-3 py-2 align-top text-xs tabular-nums">
                            {item.fecha_correo || '-'}
                          </td>
                          <td className="px-3 py-2 align-top">
                            <ComprobanteThumb
                              url={compUrl}
                              alt="Comprobante"
                              placeholderText="Sin imagen"
                            />
                          </td>
                          <td className="px-3 py-2 align-top">
                            {item.banco || '-'}
                          </td>
                          <td className="px-3 py-2 align-top">
                            {item.fecha_pago || '-'}
                          </td>
                          <td className="px-3 py-2 text-right align-top tabular-nums">
                            {safeMonto(item)}
                          </td>
                          <td className="px-3 py-2 align-top">
                            {item.numero_referencia || '-'}
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
                          </td>
                          <td className="px-3 py-2 text-right align-top">
                            <div className="flex flex-wrap justify-end gap-1.5">
                              <Button
                                size="sm"
                                onClick={() => handleGuardar(item)}
                                disabled={
                                  guardarMutation.isPending ||
                                  eliminarMutation.isPending ||
                                  migrandoEste
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
                                onClick={() => void handleEditar(item)}
                                disabled={
                                  guardarMutation.isPending ||
                                  eliminarMutation.isPending ||
                                  migrandoEste
                                }
                                title="Migra la fila a pagos_con_errores y abre el modal de revision manual (mismo flujo que pagos pendientes)"
                              >
                                {migrandoEste ? (
                                  <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                                ) : (
                                  <Pencil className="mr-1 h-3.5 w-3.5" />
                                )}
                                Editar
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleEliminar(item)}
                                disabled={
                                  eliminarMutation.isPending || migrandoEste
                                }
                              >
                                <Trash2 className="mr-1 h-3.5 w-3.5" />
                                Eliminar
                              </Button>
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

      {editPago != null && (
        <RegistrarPagoForm
          pagoId={editPago.pagoConErrorId}
          pagoInicial={editPago.inicial}
          esPagoConError
          modoGuardarYProcesar
          mostrarCampoCodigoDocumento
          onClose={cerrarModalEdit}
          onSuccess={() => {
            cerrarModalEdit()
            void queryClient.invalidateQueries({ queryKey: QK_LIST })
            toast.success('Pago aplicado a cartera con cascada de cuotas.')
          }}
        />
      )}
    </div>
  )
}
