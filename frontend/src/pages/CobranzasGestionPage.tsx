/**
 * Cobranzas → Gestión: cola de hasta 10 emails, escaneo 1 a 1 en cobranza@
 * (OCR prompts vigentes A–F/NR → pagos). Estadísticas por email; al cargar un
 * lote nuevo (hasta 10) se borra el anterior y las estadísticas vuelven a cero.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  AlertTriangle,
  CheckCircle2,
  FileSpreadsheet,
  Loader2,
  Mail,
  Plus,
  RefreshCw,
  Search,
  Upload,
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
import {
  pagoService,
  type GmailSyncDestinoWorkflow,
  type GmailSyncItemUI,
} from '../services/pagoService'
import { useGmailPipeline } from '../hooks/useGmailPipeline'
import { readExcelToJSON } from '../types/exceljs'
import { validateExcelFile } from '../utils/excelValidation'

function destinoDesdeItem(item: GmailSyncItemUI): GmailSyncDestinoWorkflow {
  const d = item.destino_workflow
  if (d === 'nuevo' || d === 'viejo' || d === 'revision_manual') return d
  // Fallback alineado al backend si falta el campo (deploy mixto).
  const etapa = (item.etapa_final || '').trim().toUpperCase()
  if (etapa === 'CUOTAS_OK' && item.traza_pago_id != null) return 'nuevo'
  if (etapa === 'OMITIDO_DUPLICADO' || item.duplicado_en_pagos) return 'viejo'
  return 'revision_manual'
}

function DestinoWorkflowBadge({ item }: { item: GmailSyncItemUI }) {
  const destino = destinoDesdeItem(item)
  const pagoId =
    destino === 'nuevo'
      ? item.traza_pago_id ?? item.pago_id_existente
      : destino === 'viejo'
        ? item.pago_id_existente ?? item.traza_pago_id
        : null
  const title =
    [
      item.etapa_final ? `etapa=${item.etapa_final}` : null,
      item.traza_motivo ? `motivo=${item.traza_motivo}` : null,
    ]
      .filter(Boolean)
      .join(' · ') || undefined

  if (destino === 'nuevo') {
    return (
      <span
        className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-900"
        title={
          title ||
          'Nuevo: ya fue subido a pagos (pipeline CUOTAS_OK / alta automática)'
        }
      >
        <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
        Nuevo{pagoId != null ? ` — ${pagoId}` : ''}
      </span>
    )
  }
  if (destino === 'viejo') {
    return (
      <span
        className="inline-flex items-center rounded-full bg-slate-200 px-2 py-0.5 text-[11px] font-medium text-slate-800"
        title={
          title ||
          'Viejo: serial ya registrado en pagos (OMITIDO_DUPLICADO)'
        }
      >
        Viejo{pagoId != null ? ` — ${pagoId}` : ''}
      </span>
    )
  }
  return (
    <span
      className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-950"
      title={
        title ||
        'Revisión manual: se verificará en revisión manual (pipeline vigente)'
      }
    >
      <AlertTriangle className="mr-1 h-3.5 w-3.5" />
      Revisión manual
    </span>
  )
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
  /** last_run_summary.gmail_messages_listed */
  emails: number
  /** last_run_summary.comprobantes_digitados */
  recibos: number
  /** last_run_summary.pagos_validos_alta_automatica */
  ingresados: number
  /** last_run_summary.pagos_invalidos_pendientes_revision */
  revisionManual: number
  error?: string
}

function numSummary(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) && n >= 0 ? n : 0
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

function cellToPlainText(raw: unknown): string {
  if (raw == null) return ''
  if (typeof raw === 'string' || typeof raw === 'number') return String(raw)
  if (typeof raw === 'object' && raw !== null && 'text' in raw) {
    return String((raw as { text?: unknown }).text ?? '')
  }
  if (typeof raw === 'object' && raw !== null && 'richText' in raw) {
    const parts = (raw as { richText?: { text?: string }[] }).richText
    if (Array.isArray(parts)) return parts.map(p => p?.text ?? '').join('')
  }
  return String(raw)
}

/** Extrae un email de celda (texto, mailto:, o hiperlink ya aplanado). */
function emailFromCell(raw: unknown): string | null {
  let s = cellToPlainText(raw).trim()
  if (!s) return null
  const mailto = /^mailto:\s*/i.exec(s)
  if (mailto) s = s.slice(mailto[0].length).split('?')[0].trim()
  const direct = normalizeEmail(s)
  if (direct) return direct
  const m = s.match(/[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}/i)
  return m ? normalizeEmail(m[0]) : null
}

/**
 * Lee correos de la 1ª hoja: preferencia columna «correo»/«email»;
 * si no hay encabezado, escanea todas las celdas. Máx. `max`, sin duplicados.
 */
function parseEmailsFromExcelRows(
  rows: unknown[][],
  max = MAX_COLA
): { emails: string[]; truncated: boolean; totalFound: number } {
  const seen = new Set<string>()
  const out: string[] = []

  const push = (e: string | null) => {
    if (!e) return
    if (seen.has(e)) return
    seen.add(e)
    if (out.length < max) out.push(e)
  }

  if (!rows.length) {
    return { emails: out, truncated: false, totalFound: 0 }
  }

  const header = (rows[0] || []).map(c =>
    cellToPlainText(c).trim().toLowerCase()
  )
  const colIdx = header.findIndex(h => {
    const norm = h.replace(/\s+/g, ' ').trim()
    return /^(correo|email|e-?mail|mail|correo_electronico|correo electronico)$/i.test(
      norm
    )
  })

  if (colIdx >= 0) {
    for (let r = 1; r < rows.length; r++) {
      push(emailFromCell(rows[r]?.[colIdx]))
    }
  } else {
    for (const row of rows) {
      if (!Array.isArray(row)) continue
      for (const cell of row) {
        push(emailFromCell(cell))
      }
    }
  }

  return {
    emails: out,
    truncated: seen.size > out.length,
    totalFound: seen.size,
  }
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
  /** Dispara el efecto que toma el siguiente pendiente. */
  const [tickCola, setTickCola] = useState(0)

  const loteRef = useRef(lote)
  loteRef.current = lote
  const indiceEnCursoRef = useRef(-1)
  const maxMessagesRef = useRef(maxMessages)
  maxMessagesRef.current = maxMessages
  const criterioRef = useRef(criterio)
  criterioRef.current = criterio
  const excelInputRef = useRef<HTMLInputElement>(null)
  const [cargandoExcel, setCargandoExcel] = useState(false)

  const offsetTabla = (paginaTabla - 1) * PAGE_SIZE
  const tabla = useQuery({
    queryKey: [...QK_LIST, correoActivo, paginaTabla, 'incluir-autoconciliados'],
    queryFn: () =>
      pagoService.listGmailSyncItems({
        correo: correoActivo,
        limit: PAGE_SIZE,
        offset: offsetTabla,
        // Incluye CUOTAS_OK (Nuevo) para ver a dónde fue cada comprobante.
        excluirAutoconciliados: false,
      }),
    enabled: !!correoActivo,
    refetchOnWindowFocus: false,
  })

  const {
    loading: ejecutandoPipeline,
    gmailStatus,
    run,
    stopPolling,
  } = useGmailPipeline({
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
      // Métricas del pipeline normal (A–F/NR), mismas que last_run_summary.
      const rs = status.last_run_summary
      const emails = numSummary(rs?.gmail_messages_listed)
      const recibos = numSummary(rs?.comprobantes_digitados)
      const ingresados = numSummary(rs?.pagos_validos_alta_automatica)
      const revisionManual = numSummary(
        rs?.pagos_invalidos_pendientes_revision
      )
      const esError = status.last_status === 'error'
      setLote(prev =>
        prev.map((it, i) =>
          i === idx
            ? {
                ...it,
                estado: esError ? 'error' : 'ok',
                emails,
                recibos,
                ingresados,
                revisionManual,
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
          `${emailDone}: ${emails} email(s), ${recibos} recibo(s), ${ingresados} ingresado(s), ${revisionManual} revisión manual.`,
          { duration: 8000 }
        )
      }
      indiceEnCursoRef.current = -1
      setTickCola(t => t + 1)
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
      emails: lote.reduce((a, it) => a + it.emails, 0),
      recibos: lote.reduce((a, it) => a + it.recibos, 0),
      ingresados: lote.reduce((a, it) => a + it.ingresados, 0),
      revisionManual: lote.reduce((a, it) => a + it.revisionManual, 0),
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

  /** Excel (.xlsx/.xls): hasta 10 correos → borrador; luego «Escanear lote» (mismo pipeline). */
  const handleExcelFile = useCallback(
    async (file: File | null | undefined) => {
      if (!file) return
      if (ejecutandoPipeline || colaActiva) {
        toast.error('Espera a que termine el lote en curso.')
        return
      }
      const validation = validateExcelFile(file)
      if (!validation.isValid) {
        toast.error(validation.error || 'Archivo Excel no válido.')
        return
      }
      setCargandoExcel(true)
      try {
        const rows = await readExcelToJSON(file)
        const { emails, truncated, totalFound } = parseEmailsFromExcelRows(
          rows,
          MAX_COLA
        )
        if (emails.length === 0) {
          toast.error(
            'No se encontraron correos válidos. Use una columna «correo»/«email» o celdas con direcciones.'
          )
          return
        }
        let agregados = 0
        let enBorrador = 0
        setBorrador(prev => {
          const seen = new Set(prev)
          const next = [...prev]
          for (const e of emails) {
            if (seen.has(e)) continue
            if (next.length >= MAX_COLA) break
            seen.add(e)
            next.push(e)
            agregados += 1
          }
          enBorrador = next.length
          return next
        })
        if (agregados === 0) {
          toast(
            `Ningún correo nuevo (borrador ya tiene ${enBorrador}/${MAX_COLA} o estaban duplicados).`,
            { duration: 7000 }
          )
          return
        }
        const extras =
          truncated || totalFound > emails.length
            ? ` (Excel tenía ${totalFound}; tope ${MAX_COLA})`
            : ''
        toast.success(
          `${agregados} correo(s) del Excel en el borrador (${enBorrador}/${MAX_COLA})${extras}. Pulse «Escanear lote».`,
          { duration: 8000 }
        )
      } catch (e) {
        toast.error(
          e instanceof Error
            ? e.message
            : 'No se pudo leer el Excel de correos.'
        )
      } finally {
        setCargandoExcel(false)
        if (excelInputRef.current) excelInputRef.current.value = ''
      }
    },
    [ejecutandoPipeline, colaActiva]
  )

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
      emails: 0,
      recibos: 0,
      ingresados: 0,
      revisionManual: 0,
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

  /** Libera sync running en servidor y cancela el resto del lote (desbloquea la UI). */
  const handleDetenerLiberar = useCallback(async () => {
    stopPolling()
    try {
      const r = await pagoService.liberarGmailRunning()
      if (r.liberated) {
        toast.success(r.message || 'Corrida Gmail liberada.')
      } else {
        toast(r.message || 'No había corrida bloqueante.')
      }
    } catch (e) {
      toast.error(
        e instanceof Error ? e.message : 'No se pudo liberar la corrida Gmail.'
      )
    }
    const idx = indiceEnCursoRef.current
    setLote(prev =>
      prev.map((it, i) => {
        if (i === idx && it.estado === 'procesando') {
          return {
            ...it,
            estado: 'error' as const,
            error: 'Detenido / liberado por operador',
          }
        }
        if (it.estado === 'pendiente') {
          return {
            ...it,
            estado: 'error' as const,
            error: 'Cancelado (lote detenido)',
          }
        }
        return it
      })
    )
    indiceEnCursoRef.current = -1
    setColaActiva(false)
  }, [stopPolling])

  const tablaItems: GmailSyncItemUI[] = useMemo(
    () => tabla.data?.items ?? [],
    [tabla.data]
  )
  const tablaTotal = tabla.data?.total ?? 0
  const tablaTotalPaginas = Math.max(1, Math.ceil(tablaTotal / PAGE_SIZE))

  const ocupado = ejecutandoPipeline || colaActiva

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Gestión"
        description={
          'Hasta 10 emails por lote, escaneo uno a uno en cobranza@ (pipeline OCR A–F/NR → pagos). ' +
          'Resumen: emails / recibos / ingresados / revisión manual. ' +
          'En Observaciones se muestra el destino del pipeline normal: Nuevo (subido a pagos), ' +
          'Viejo (serial ya registrado) o Revisión manual. ' +
          'Al cargar otro lote las estadísticas vuelven a cero.'
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
                Emails:{' '}
                <strong className="tabular-nums">{totales.emails}</strong>
              </span>
              <span>
                Recibos:{' '}
                <strong className="tabular-nums">{totales.recibos}</strong>
              </span>
              <span>
                Ingresados:{' '}
                <strong className="tabular-nums">{totales.ingresados}</strong>
              </span>
              <span>
                Revisión manual:{' '}
                <strong className="tabular-nums">
                  {totales.revisionManual}
                </strong>
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
                    <th className="px-2 py-1.5 text-right">Emails</th>
                    <th className="px-2 py-1.5 text-right">Recibos</th>
                    <th className="px-2 py-1.5 text-right">Ingresados</th>
                    <th className="px-2 py-1.5 text-right">Revisión manual</th>
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
                        {it.emails}
                      </td>
                      <td className="px-2 py-1.5 text-right tabular-nums">
                        {it.recibos}
                      </td>
                      <td className="px-2 py-1.5 text-right tabular-nums">
                        {it.ingresados}
                      </td>
                      <td className="px-2 py-1.5 text-right tabular-nums">
                        {it.revisionManual}
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
            <input
              ref={excelInputRef}
              type="file"
              accept=".xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
              className="hidden"
              disabled={ocupado || cargandoExcel}
              onChange={e => {
                const f = e.target.files?.[0]
                void handleExcelFile(f)
              }}
            />
            <Button
              type="button"
              variant="outline"
              disabled={ocupado || cargandoExcel}
              onClick={() => excelInputRef.current?.click()}
              title="Excel con columna correo/email (máx. 10). Luego Escanear lote."
            >
              {cargandoExcel ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              <FileSpreadsheet className="mr-1.5 h-4 w-4" />
              Subir Excel
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
            {ocupado ? (
              <Button
                type="button"
                variant="destructive"
                onClick={() => void handleDetenerLiberar()}
              >
                <X className="mr-2 h-4 w-4" />
                Detener / liberar
              </Button>
            ) : null}
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
            Agrega hasta <strong>{MAX_COLA}</strong> correos (manual o{' '}
            <strong>Subir Excel</strong> .xlsx/.xls con columna correo/email) →
            Escanear lote. Se procesan <strong>uno tras otro</strong> en
            cobranza@ con el pipeline normal (OCR A–F/NR → pagos). Al terminar
            cada email el resumen muestra emails / recibos / ingresados /
            revisión manual. Si cargas otro lote, el anterior y sus números se
            eliminan (vuelven a cero).
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
                    <th className="px-3 py-2">Observaciones</th>
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
                      const destino = destinoDesdeItem(item)
                      return (
                        <tr
                          key={item.id}
                          className={
                            'border-t ' +
                            (destino === 'nuevo'
                              ? 'bg-emerald-50/40'
                              : destino === 'viejo'
                                ? 'bg-slate-50/80'
                                : destino === 'revision_manual'
                                  ? 'bg-amber-50/40'
                                  : '')
                          }
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
                          <td className="px-3 py-2 align-top">
                            <DestinoWorkflowBadge item={item} />
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
    </div>
  )
}
