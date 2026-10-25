/**
 * Cobranzas → Gestión: cola de hasta 10 emails, escaneo 1 a 1 en cobranza@
 * (OCR prompts vigentes A–F/NR → pagos). Estadísticas por email; al cargar un
 * lote nuevo (hasta 10) se borra el anterior y las estadísticas vuelven a cero.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  CheckCircle2,
  Loader2,
  Mail,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Search,
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
import { ComprobanteThumb } from '../components/pagos/ComprobanteThumb'
import { RegistrarPagoForm } from '../components/pagos/RegistrarPagoForm'
import {
  pagoService,
  type GmailSyncItemUI,
  type PagoInicialRegistrar,
} from '../services/pagoService'
import type { PagoConError } from '../services/pagoConErrorService'
import { useGmailPipeline } from '../hooks/useGmailPipeline'
import { getErrorMessage } from '../types/errors'

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

const QK_LIST = ['cobranzas', 'gestion', 'gmail', 'sync-items'] as const
const MAX_COLA = 10
const PAGE_SIZE = 50
const MAX_MESSAGES_DEFAULT = 20
const MAX_MESSAGES_OPTIONS = [20, 50, 100, 500, 1000, 5000, 10000] as const

type CriterioBusqueda = 'remitente' | 'destinatario' | 'participante'

type EstadoLote = 'pendiente' | 'procesando' | 'ok' | 'error'

type ItemLote = {
  correo: string
  estado: EstadoLote
  correosEscaneados: number
  pagosNuevosNoVerificados: number
  error?: string
}

const EMAIL_RE = /^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$/

function normalizeEmail(raw: string): string | null {
  const s = raw.trim().toLowerCase()
  if (!s || !EMAIL_RE.test(s)) return null
  return s
}

/** Parsea pegado: líneas, comas o ; — máx MAX_COLA, sin duplicados. */
function parseEmailsLista(raw: string, max = MAX_COLA): string[] {
  const parts = raw
    .split(/[\n,;]+/)
    .map(p => normalizeEmail(p))
    .filter((x): x is string => !!x)
  const seen = new Set<string>()
  const out: string[] = []
  for (const e of parts) {
    if (seen.has(e)) continue
    seen.add(e)
    out.push(e)
    if (out.length >= max) break
  }
  return out
}

function urlComprobante(raw: string | null | undefined): string | null {
  const s = (raw || '').trim()
  return s || null
}

function safeMonto(item: GmailSyncItemUI): string {
  const m = (item.monto || '').trim()
  return m || '-'
}

export default function CobranzasGestionPage() {
  const queryClient = useQueryClient()
  const [correoInput, setCorreoInput] = useState('')
  const [borrador, setBorrador] = useState<string[]>([])
  const [lote, setLote] = useState<ItemLote[]>([])
  const [colaActiva, setColaActiva] = useState(false)
  const [correoActivo, setCorreoActivo] = useState('')
  const [maxMessages, setMaxMessages] = useState<number>(MAX_MESSAGES_DEFAULT)
  const [criterio, setCriterio] = useState<CriterioBusqueda>('remitente')
  const [paginaTabla, setPaginaTabla] = useState(1)
  const [editPago, setEditPago] = useState<{
    pagoConErrorId: number
    inicial: PagoInicialRegistrar
  } | null>(null)
  const [migrandoId, setMigrandoId] = useState<number | null>(null)
  /** Dispara el efecto que toma el siguiente pendiente. */
  const [tickCola, setTickCola] = useState(0)

  const loteRef = useRef(lote)
  loteRef.current = lote
  const indiceEnCursoRef = useRef(-1)
  const maxMessagesRef = useRef(maxMessages)
  maxMessagesRef.current = maxMessages
  const criterioRef = useRef(criterio)
  criterioRef.current = criterio

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
      const idx = indiceEnCursoRef.current
      const emailDone =
        idx >= 0 ? loteRef.current[idx]?.correo : correoActivo
      if (!emailDone) {
        indiceEnCursoRef.current = -1
        setTickCola(t => t + 1)
        void queryClient.invalidateQueries({ queryKey: QK_LIST })
        return
      }
      void (async () => {
        let totalFilas = 0
        let yaEnPagos = 0
        try {
          const res = await queryClient.fetchQuery({
            queryKey: [...QK_LIST, emailDone, 1],
            queryFn: () =>
              pagoService.listGmailSyncItems({
                correo: emailDone,
                limit: PAGE_SIZE,
                offset: 0,
              }),
          })
          totalFilas = res.total ?? res.items.length
          yaEnPagos = res.items.filter(it => it.duplicado_en_pagos).length
        } catch {
          /* fallback abajo */
        }
        const listed = Number(status.last_run_summary?.gmail_messages_listed)
        const correosEscaneados = Math.max(
          0,
          Number.isFinite(listed) && listed > 0
            ? listed
            : Number(status.last_emails) || totalFilas
        )
        const pagosNuevos = Math.max(0, totalFilas - yaEnPagos)
        const esError = status.last_status === 'error'
        setLote(prev =>
          prev.map((it, i) =>
            i === idx
              ? {
                  ...it,
                  estado: esError ? 'error' : 'ok',
                  correosEscaneados,
                  pagosNuevosNoVerificados: pagosNuevos,
                  error: esError
                    ? status.last_error || 'error pipeline'
                    : undefined,
                }
              : it
          )
        )
        setCorreoActivo(emailDone)
        setPaginaTabla(1)
        void queryClient.invalidateQueries({ queryKey: QK_LIST })
        if (esError) {
          toast.error(
            `${emailDone}: pipeline con error — ${status.last_error || 'desconocido'}`,
            { duration: 10000 }
          )
        } else {
          toast.success(
            `${emailDone}: ${correosEscaneados} correo(s), ${pagosNuevos} pago(s) nuevo(s).`,
            { duration: 8000 }
          )
        }
        indiceEnCursoRef.current = -1
        setTickCola(t => t + 1)
      })()
    },
  })

  const ejecutandoRef = useRef(ejecutandoPipeline)
  ejecutandoRef.current = ejecutandoPipeline

  /** Arranca el siguiente email pendiente (1 a 1). */
  useEffect(() => {
    if (!colaActiva) return
    if (ejecutandoPipeline) return
    if (indiceEnCursoRef.current >= 0) return

    const nextIdx = lote.findIndex(it => it.estado === 'pendiente')
    if (nextIdx < 0) {
      if (lote.length > 0 && lote.every(it => it.estado === 'ok' || it.estado === 'error')) {
        setColaActiva(false)
        const okN = lote.filter(it => it.estado === 'ok').length
        const errN = lote.filter(it => it.estado === 'error').length
        toast.success(
          `Lote terminado: ${okN} OK` + (errN ? `, ${errN} con error` : '') + '.',
          { duration: 10000 }
        )
      }
      return
    }

    const email = lote[nextIdx].correo
    indiceEnCursoRef.current = nextIdx
    setLote(prev =>
      prev.map((it, i) =>
        i === nextIdx ? { ...it, estado: 'procesando' as const } : it
      )
    )
    setCorreoActivo(email)
    setPaginaTabla(1)
    void queryClient.removeQueries({ queryKey: QK_LIST })
    void run(
      'manual_redigitaliza_por_remitente',
      email,
      maxMessagesRef.current,
      criterioRef.current,
      'cobranza'
    )
  }, [colaActiva, ejecutandoPipeline, lote, tickCola, run, queryClient])

  const totales = useMemo(() => {
    return {
      correosEscaneados: lote.reduce((a, it) => a + it.correosEscaneados, 0),
      pagosNuevos: lote.reduce((a, it) => a + it.pagosNuevosNoVerificados, 0),
      ok: lote.filter(it => it.estado === 'ok').length,
      error: lote.filter(it => it.estado === 'error').length,
      pendiente: lote.filter(it => it.estado === 'pendiente').length,
      procesando: lote.filter(it => it.estado === 'procesando').length,
    }
  }, [lote])

  const agregarAlBorrador = useCallback(() => {
    const parsed = parseEmailsLista(correoInput, MAX_COLA)
    if (parsed.length === 0) {
      toast.error('Indica al menos un correo válido.')
      return
    }
    setBorrador(prev => {
      const seen = new Set(prev)
      const next = [...prev]
      for (const e of parsed) {
        if (seen.has(e)) continue
        if (next.length >= MAX_COLA) {
          toast.error(`Máximo ${MAX_COLA} correos por lote.`)
          break
        }
        seen.add(e)
        next.push(e)
      }
      return next
    })
    setCorreoInput('')
  }, [correoInput])

  const quitarBorrador = useCallback((email: string) => {
    setBorrador(prev => prev.filter(e => e !== email))
  }, [])

  /** Nuevo lote: borra estadísticas anteriores y arranca de cero (hasta 10). */
  const cargarLoteYEscanear = useCallback(() => {
    let emails = borrador
    if (emails.length === 0) {
      emails = parseEmailsLista(correoInput, MAX_COLA)
    }
    if (emails.length === 0) {
      toast.error('Agrega hasta 10 correos al lote.')
      return
    }
    if (ejecutandoPipeline || colaActiva) {
      toast.error('Espera a que termine el lote en curso.')
      return
    }
    const nuevo: ItemLote[] = emails.slice(0, MAX_COLA).map(correo => ({
      correo,
      estado: 'pendiente',
      correosEscaneados: 0,
      pagosNuevosNoVerificados: 0,
    }))
    // Reset total: elimina lote/estadísticas previas.
    indiceEnCursoRef.current = -1
    setLote(nuevo)
    setBorrador([])
    setCorreoInput('')
    setCorreoActivo(nuevo[0]?.correo || '')
    setPaginaTabla(1)
    void queryClient.removeQueries({ queryKey: QK_LIST })
    setColaActiva(true)
    setTickCola(t => t + 1)
    toast(
      `Lote de ${nuevo.length} email(s): se escanean uno a uno. Estadísticas en cero.`,
      { duration: 6000 }
    )
  }, [
    borrador,
    correoInput,
    ejecutandoPipeline,
    colaActiva,
    queryClient,
  ])

  const handleLimpiar = useCallback(() => {
    if (ejecutandoPipeline || colaActiva) {
      toast.error('No se puede limpiar mientras hay un lote en curso.')
      return
    }
    setCorreoInput('')
    setBorrador([])
    setLote([])
    setCorreoActivo('')
    setPaginaTabla(1)
    setColaActiva(false)
    indiceEnCursoRef.current = -1
    void queryClient.removeQueries({ queryKey: QK_LIST })
  }, [ejecutandoPipeline, colaActiva, queryClient])

  const tablaItems: GmailSyncItemUI[] = useMemo(
    () => tabla.data?.items ?? [],
    [tabla.data]
  )
  const tablaTotal = tabla.data?.total ?? 0
  const tablaTotalPaginas = Math.max(1, Math.ceil(tablaTotal / PAGE_SIZE))

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
          toast(
            res.mensaje ||
              `Serial ${item.numero_referencia || '(s/r)'} ya existe en cartera. ` +
                `Agregue un código (sufijo) para diferenciar el pago.`,
            { duration: 8000 }
          )
        }
        setEditPago({
          pagoConErrorId: res.pago_con_error_id,
          inicial: pagoInicialDesdePagoConError(res.pago_con_error),
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

  const cerrarModalEdit = useCallback(() => setEditPago(null), [])

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

  const ocupado = ejecutandoPipeline || colaActiva

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Gestión"
        description={
          'Hasta 10 emails por lote, escaneo uno a uno en cobranza@ (OCR A–F/NR → pagos). ' +
          'Las estadísticas se actualizan al terminar cada email. Al cargar otro lote se borran y vuelven a cero.'
        }
        icon={Mail}
      />

      {lote.length > 0 ? (
        <Card className="border-blue-200 bg-blue-50/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              Estadísticas del lote ({lote.length}/{MAX_COLA})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-800">
            <div className="flex flex-wrap gap-4 text-xs sm:text-sm">
              <span>
                Escaneados:{' '}
                <strong className="tabular-nums">
                  {totales.correosEscaneados}
                </strong>
              </span>
              <span>
                Pagos nuevos:{' '}
                <strong className="tabular-nums">{totales.pagosNuevos}</strong>
              </span>
              <span>
                OK <strong className="tabular-nums">{totales.ok}</strong> · Error{' '}
                <strong className="tabular-nums">{totales.error}</strong> · Pend.{' '}
                <strong className="tabular-nums">{totales.pendiente}</strong>
                {totales.procesando > 0 ? (
                  <>
                    {' '}
                    · En curso{' '}
                    <strong className="tabular-nums text-amber-700">
                      {totales.procesando}
                    </strong>
                  </>
                ) : null}
              </span>
            </div>
            <div className="overflow-x-auto rounded-md border bg-white">
              <table className="w-full text-xs sm:text-sm">
                <thead className="bg-muted/40 text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-2 py-1.5">#</th>
                    <th className="px-2 py-1.5">Email</th>
                    <th className="px-2 py-1.5">Estado</th>
                    <th className="px-2 py-1.5 text-right">Correos escaneados</th>
                    <th className="px-2 py-1.5 text-right">Pagos nuevos</th>
                  </tr>
                </thead>
                <tbody>
                  {lote.map((it, i) => (
                    <tr
                      key={it.correo}
                      className={
                        'border-t cursor-pointer hover:bg-blue-50/60 ' +
                        (correoActivo === it.correo ? 'bg-blue-50' : '') +
                        (it.estado === 'procesando' ? ' bg-amber-50' : '')
                      }
                      onClick={() => {
                        setCorreoActivo(it.correo)
                        setPaginaTabla(1)
                      }}
                    >
                      <td className="px-2 py-1.5 tabular-nums">{i + 1}</td>
                      <td className="px-2 py-1.5 font-medium">{it.correo}</td>
                      <td className="px-2 py-1.5">
                        {it.estado === 'procesando' ? (
                          <span className="inline-flex items-center gap-1 text-amber-800">
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            Procesando
                          </span>
                        ) : it.estado === 'ok' ? (
                          <span className="text-emerald-700">OK</span>
                        ) : it.estado === 'error' ? (
                          <span
                            className="text-red-700"
                            title={it.error || ''}
                          >
                            Error
                          </span>
                        ) : (
                          <span className="text-muted-foreground">
                            Pendiente
                          </span>
                        )}
                      </td>
                      <td className="px-2 py-1.5 text-right tabular-nums">
                        {it.correosEscaneados}
                      </td>
                      <td className="px-2 py-1.5 text-right tabular-nums">
                        {it.pagosNuevosNoVerificados}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-muted-foreground">
              Pulsa una fila para ver sus resultados en la tabla de abajo. Al
              cargar otro lote (hasta {MAX_COLA}), estas estadísticas se eliminan
              y vuelven a cero.
            </p>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader className="space-y-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <CardTitle className="text-lg">
              Lote de emails (máx. {MAX_COLA})
            </CardTitle>
            <div className="text-xs text-muted-foreground">
              {ocupado ? (
                <span className="text-amber-700">
                  Escaneando uno a uno…
                  {gmailStatus?.last_status === 'running'
                    ? ` (${gmailStatus.last_emails ?? 0} correos en sync)`
                    : ''}
                </span>
              ) : gmailStatus?.last_run ? (
                <span>
                  Última sync Gmail:{' '}
                  {new Date(gmailStatus.last_run).toLocaleString()}
                </span>
              ) : (
                <span>Sin sync aún</span>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
            <Input
              type="text"
              autoComplete="email"
              placeholder="correo@dominio.com (o varios separados por coma/línea)"
              value={correoInput}
              onChange={e => setCorreoInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  agregarAlBorrador()
                }
              }}
              className="sm:max-w-md"
              disabled={ocupado}
            />
            <Button
              type="button"
              variant="outline"
              onClick={agregarAlBorrador}
              disabled={ocupado || !correoInput.trim()}
            >
              <Plus className="mr-2 h-4 w-4" />
              Agregar ({borrador.length}/{MAX_COLA})
            </Button>
            <label className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Hasta</span>
              <select
                value={maxMessages}
                onChange={e => setMaxMessages(Number(e.target.value))}
                className="rounded-md border border-input bg-background px-2 py-1 text-xs"
                disabled={ocupado}
              >
                {MAX_MESSAGES_OPTIONS.map(v => (
                  <option key={v} value={v}>
                    {v} msg/email
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Buscar como</span>
              <select
                value={criterio}
                onChange={e =>
                  setCriterio(e.target.value as CriterioBusqueda)
                }
                className="rounded-md border border-input bg-background px-2 py-1 text-xs"
                disabled={ocupado}
              >
                <option value="remitente">Remitente (from:)</option>
                <option value="destinatario">Destinatario (to:)</option>
                <option value="participante">Participante</option>
              </select>
            </label>
          </div>

          {borrador.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {borrador.map(e => (
                <span
                  key={e}
                  className="inline-flex items-center gap-1 rounded-md border bg-white px-2 py-1 text-xs"
                >
                  {e}
                  <button
                    type="button"
                    className="text-muted-foreground hover:text-red-600"
                    disabled={ocupado}
                    onClick={() => quitarBorrador(e)}
                    aria-label={`Quitar ${e}`}
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </span>
              ))}
            </div>
          ) : null}

          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              onClick={cargarLoteYEscanear}
              disabled={
                ocupado ||
                (borrador.length === 0 && !correoInput.trim())
              }
            >
              {ocupado ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-2 h-4 w-4" />
              )}
              Escanear lote
              {borrador.length > 0 ? ` (${borrador.length})` : ''}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => void tabla.refetch()}
              disabled={!correoActivo || tabla.isFetching || ocupado}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Refrescar tabla
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={handleLimpiar}
              disabled={ocupado}
            >
              Limpiar / nuevo lote en cero
            </Button>
          </div>

          <div className="rounded-md border border-dashed bg-muted/20 p-3 text-xs text-muted-foreground">
            Agrega hasta <strong>{MAX_COLA}</strong> correos → Escanear lote. Se
            procesan <strong>uno tras otro</strong> (termina 1, empieza el
            siguiente) en cobranza@ con los prompts vigentes. Las estadísticas
            de cada email se actualizan al terminar. Si cargas otro lote, el
            anterior y sus números se eliminan (vuelven a cero).
          </div>
        </CardHeader>
      </Card>

      {correoActivo ? (
        <Card>
          <CardHeader className="space-y-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="text-lg">
                Resultados — {correoActivo}
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
              Filas: {tablaTotal}
              {tablaTotalPaginas > 1
                ? ` — página ${paginaTabla} de ${tablaTotalPaginas}`
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
                        {ocupado
                          ? 'Procesando… los resultados aparecerán al terminar este email.'
                          : 'Sin filas para este email.'}
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
                              <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-900">
                                <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                                Si — {item.pago_id_existente ?? '?'}
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
                  Página {paginaTabla} de {tablaTotalPaginas}
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    setPaginaTabla(p => Math.min(tablaTotalPaginas, p + 1))
                  }
                  disabled={
                    paginaTabla >= tablaTotalPaginas || tabla.isFetching
                  }
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
