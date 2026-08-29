import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Play, RefreshCw, Square, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
import { Progress } from '../../components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'
import {
  auditoriaEmailService,
  type AuditoriaEmailCriteria,
  type AuditoriaEmailScan,
} from '../../services/auditoriaEmailService'
import { getErrorMessage } from '../../types/errors'

/** Hoy calendario en America/Caracas (YYYY-MM-DD). */
function caracasTodayYmd(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Caracas',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

/** Suma/resta días a un YYYY-MM-DD (calendario, sin TZ drift). */
function addDaysYmd(ymd: string, delta: number): string {
  const [y, m, d] = ymd.split('-').map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d))
  dt.setUTCDate(dt.getUTCDate() + delta)
  return dt.toISOString().slice(0, 10)
}

/**
 * Normaliza Desde/Hasta: si hay Desde sin Hasta → Hasta=hoy Caracas;
 * corrige orden invertido. Sin newer_than en UI (Gmail usa after/before).
 */
function criteriaWithLinkedDates(
  base: AuditoriaEmailCriteria,
  patch: Partial<AuditoriaEmailCriteria>
): AuditoriaEmailCriteria {
  const next: AuditoriaEmailCriteria = { ...base, ...patch }
  const today = caracasTodayYmd()

  // Ya no usamos newerThanDays en la UI; no lo enviamos a Gmail.
  delete next.newerThanDays

  const fromTouched = Object.prototype.hasOwnProperty.call(patch, 'dateFrom')
  const toTouched = Object.prototype.hasOwnProperty.call(patch, 'dateTo')

  if (fromTouched || toTouched) {
    let from = next.dateFrom || undefined
    let to = next.dateTo || undefined
    if (fromTouched && !from) {
      // Borró Desde → últimos 7 días por defecto.
      next.dateTo = today
      next.dateFrom = addDaysYmd(today, -6)
      return next
    }
    if (from && !to) to = today
    if (to && !from) from = to
    if (from && to && from > to) {
      const tmp = from
      from = to
      to = tmp
    }
    if (from && to) {
      next.dateFrom = from
      next.dateTo = to
      return next
    }
  }

  return next
}

const DEFAULT_CRITERIA: AuditoriaEmailCriteria = (() => {
  const today = caracasTodayYmd()
  return {
    dateFrom: addDaysYmd(today, -6),
    dateTo: today,
    subject: 'comprobante OR pago',
    subjectMode: 'contains',
    attachments: 'pagos_gmail',
  }
})()

/** Criterios limpios para Gmail: sin vacíos ni newerThan. */
function criteriaForScan(c: AuditoriaEmailCriteria): AuditoriaEmailCriteria {
  const linked = criteriaWithLinkedDates(c, {})
  const out: AuditoriaEmailCriteria = {
    dateFrom: linked.dateFrom,
    dateTo: linked.dateTo,
    attachments: linked.attachments || 'pagos_gmail',
  }
  const subj = (linked.subject || '').trim()
  if (subj) {
    out.subject = subj
    out.subjectMode = linked.subjectMode || 'contains'
  }
  const frm = (linked.from || '').trim()
  if (frm) out.from = frm
  if (linked.attachmentMinKb && linked.attachmentMinKb > 0) {
    out.attachmentMinKb = linked.attachmentMinKb
  }
  if (linked.excludeAnalizados) out.excludeAnalizados = true
  if (linked.filenamePattern?.trim()) {
    out.filenamePattern = linked.filenamePattern.trim()
  }
  if (linked.subjectExclude?.trim()) {
    out.subjectExclude = linked.subjectExclude.trim()
  }
  if (linked.excludeFrom?.trim()) out.excludeFrom = linked.excludeFrom.trim()
  return out
}

/** Lotes pequeños para no saturar Gmail/OCR al traer “todos” del rango. */
const LOT_SIZE_SAFE = 50

const POLL_MS_RUNNING = 2000
const POLL_MS_IDLE = 4000
/** Espera antes de reintentar cuando Pagos Gmail tiene el lock. */
const BUSY_RETRY_MS = 45000

function statusLabel(status: string, stopped?: boolean): string {
  if (stopped) return 'Detenido por el usuario'
  if (status === 'running') return 'En curso (OCR / Gmail)…'
  if (status === 'paused') return 'Pausado — usa Reanudar o Auto-reanudar'
  if (status === 'complete') return 'Completado'
  return status
}

export default function AuditoriaEmailEscanearPage() {
  const qc = useQueryClient()
  const [mode, setMode] = useState<'single' | 'batch'>('single')
  const [criteria, setCriteria] = useState<AuditoriaEmailCriteria>(
    () => ({ ...DEFAULT_CRITERIA })
  )
  const [lotSize, setLotSize] = useState(LOT_SIZE_SAFE)
  const [maxMessages, setMaxMessages] = useState(32000)
  const [busy, setBusy] = useState(false)
  const [autoContinue, setAutoContinue] = useState(true)
  const [active, setActive] = useState<AuditoriaEmailScan | null>(null)
  const advancingRef = useRef(false)
  const busyUntilRef = useRef(0)
  const restoredRef = useRef(false)

  const scanLive =
    Boolean(active) &&
    active?.status !== 'complete' &&
    active?.status !== undefined &&
    !Boolean(active?.stopped) &&
    !String(active?.lastError || '')
      .toLowerCase()
      .includes('detenido')

  const statusQ = useQuery({
    queryKey: ['auditoria-email', 'status'],
    queryFn: () => auditoriaEmailService.status(),
    refetchInterval: scanLive ? POLL_MS_RUNNING : false,
  })

  const kpisQ = useQuery({
    queryKey: ['auditoria-email', 'kpis'],
    queryFn: () => auditoriaEmailService.kpis(),
    refetchInterval: scanLive ? POLL_MS_RUNNING : false,
    enabled: Boolean(active) && scanLive,
  })

  const paused = useQuery({
    queryKey: ['auditoria-email', 'paused'],
    queryFn: () => auditoriaEmailService.pausedScans(),
  })

  // Al abrir Escanear: recuperar job running/paused (no los detenidos por el usuario).
  useEffect(() => {
    if (restoredRef.current || active) return
    let cancelled = false
    ;(async () => {
      try {
        const [p, bit] = await Promise.all([
          auditoriaEmailService.pausedScans(),
          auditoriaEmailService.bitacora(15),
        ])
        if (cancelled) return
        const pool = [...(p.items || []), ...(bit.items || [])]
        const best = pool
          .filter(s => {
            if (s.stopped) return false
            if (
              String(s.lastError || '')
                .toLowerCase()
                .includes('detenido')
            ) {
              return false
            }
            return (
              s.status === 'running' ||
              (s.status === 'paused' &&
                (Boolean(s.paused) ||
                  (s.processedTotal === 0 && !s.finishedAt)))
            )
          })
          .sort((a, b) => Number(b.id) - Number(a.id))[0]
        if (best) {
          restoredRef.current = true
          setActive(best)
        } else {
          restoredRef.current = true
        }
      } catch {
        restoredRef.current = true
      }
    })()
    return () => {
      cancelled = true
    }
  }, [active])

  const hasFullDateRange = Boolean(criteria.dateFrom && criteria.dateTo)

  const patch = useCallback((p: Partial<AuditoriaEmailCriteria>) => {
    setCriteria(prev => criteriaWithLinkedDates(prev, p))
  }, [])

  const refreshActive = useCallback(async (id: number) => {
    const s = await auditoriaEmailService.getScan(id)
    setActive(s)
    return s
  }, [])

  // Poll + auto-reanudar 1 lote cuando paused (fluidez sin saturar HTTP).
  useEffect(() => {
    if (!active || active.status === 'complete') return
    let cancelled = false
    const pollMs =
      active.status === 'running' ? POLL_MS_RUNNING : POLL_MS_IDLE
    const tick = async () => {
      if (cancelled || advancingRef.current) return
      try {
        const s = await refreshActive(active.id)
        if (cancelled) return
        if (s.status === 'complete') {
          toast.success(`Escaneo #${s.id} completo · ${s.processedTotal} procesados`)
          await qc.invalidateQueries({ queryKey: ['auditoria-email'] })
          return
        }
        const err = String(s.lastError || '').toLowerCase()
        // Pipeline ocupado no aborta el job: se reintenta con espera hasta que
        // Pagos Gmail libere el lock.
        if (err.includes('ocupado') && Date.now() < busyUntilRef.current) return
        if (
          autoContinue &&
          s.status === 'paused' &&
          s.paused &&
          !s.stopped &&
          !err.includes('detenido')
        ) {
          advancingRef.current = true
          try {
            await auditoriaEmailService.advanceScan(s.id, 1)
            const after = await refreshActive(s.id)
            busyUntilRef.current = String(after.lastError || '')
              .toLowerCase()
              .includes('ocupado')
              ? Date.now() + BUSY_RETRY_MS
              : 0
          } catch (e) {
            const msg = getErrorMessage(e) || 'No se pudo reanudar lote'
            if (msg.toLowerCase().includes('ocupado')) {
              busyUntilRef.current = Date.now() + BUSY_RETRY_MS
            } else {
              toast.error(msg)
            }
          } finally {
            advancingRef.current = false
          }
        }
      } catch {
        /* ignore poll errors */
      }
    }
    const t = window.setInterval(() => void tick(), pollMs)
    void tick()
    return () => {
      cancelled = true
      window.clearInterval(t)
    }
  }, [active?.id, active?.status, autoContinue, qc, refreshActive])

  const onEstimate = async () => {
    const ready = criteriaForScan(criteria)
    if (!ready.dateFrom || !ready.dateTo) {
      toast.error('Fijá Desde y Hasta para estimar')
      return
    }
    setBusy(true)
    try {
      const res = await auditoriaEmailService.estimate(ready)
      toast.message(
        `${res.estimated.toLocaleString()} mensajes est. (${res.source}${res.exact ? ', exacto' : ', aprox.'})`
      )
      if (res.gmail_query) {
        toast.message(`Filtro Gmail: ${res.gmail_query}`)
      }
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo estimar')
    } finally {
      setBusy(false)
    }
  }

  const onStart = async () => {
    if (!statusQ.data?.ready_for_scan && !statusQ.data?.gmail_connected) {
      toast.error('Conecta cobranza@ en Conexión antes de escanear')
      return
    }
    if (statusQ.data?.mailbox_match === false) {
      toast.error('El OAuth no es el buzón objetivo. Reautoriza en Conexión.')
      return
    }
    const ready = criteriaForScan(criteria)
    if (!ready.dateFrom || !ready.dateTo) {
      toast.error('Fijá Desde y Hasta antes de iniciar')
      return
    }
    setCriteria({ ...criteria, ...ready })
    setBusy(true)
    try {
      // Con Desde+Hasta: escanear TODOS los del filtro en lotes de 50
      // hasta agotar el periodo (tope de seguridad 32k).
      let startMode: 'single' | 'batch' = 'batch'
      let startMax = Math.min(Math.max(1, maxMessages), 32000)
      const startLot = LOT_SIZE_SAFE
      setLotSize(LOT_SIZE_SAFE)
      setMode('batch')
      try {
        const est = await auditoriaEmailService.estimate(ready)
        const n = Number(est.estimated || 0)
        if (est.gmail_query) {
          toast.message(`Filtro Gmail: ${est.gmail_query}`)
        }
        if (n > 0) {
          startMax = Math.min(32000, Math.max(n, 1))
          setMaxMessages(startMax)
          toast.message(
            `Rango ${ready.dateFrom} → ${ready.dateTo}: ~${n.toLocaleString()} msgs · lotes de ${LOT_SIZE_SAFE}.`
          )
        } else {
          startMax = 32000
          setMaxMessages(32000)
        }
      } catch {
        startMax = Math.min(32000, Math.max(1, maxMessages))
      }
      // POST /scans ya crea el job con estos criteria y avanza el 1.er lote.
      const started = await auditoriaEmailService.createScan({
        mode: startMode,
        criteria: ready,
        lotSize: startLot,
        maxMessages: startMax,
      })
      setActive(started)
      const q =
        started.gmailQuery ||
        `after:${ready.dateFrom} before:${ready.dateTo}`
      toast.success(
        `Escaneo #${started.id} con tus criterios · ${started.processedTotal}/${started.maxMessages}`
      )
      toast.message(`Condiciones fijadas: ${q}`)
      await qc.invalidateQueries({ queryKey: ['auditoria-email'] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo iniciar el escaneo')
    } finally {
      setBusy(false)
    }
  }

  const onAdvance = async (id: number) => {
    setBusy(true)
    advancingRef.current = true
    setAutoContinue(true)
    try {
      await auditoriaEmailService.advanceScan(id, 1)
      const s = await refreshActive(id)
      toast.success(
        `Avance #${id}: ${s.processedTotal}/${s.maxMessages} · ${s.status}`
      )
      await qc.invalidateQueries({ queryKey: ['auditoria-email'] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo avanzar')
    } finally {
      advancingRef.current = false
      setBusy(false)
    }
  }

  const onPause = async (id: number) => {
    setBusy(true)
    setAutoContinue(false)
    advancingRef.current = true
    try {
      const s = await auditoriaEmailService.pauseScan(id)
      // Encerar barra: no dejar el job detenido como “activo” en pantalla.
      setActive(null)
      restoredRef.current = true
      toast.success(
        `Escaneo #${id} detenido (${s.processedTotal}/${s.maxMessages}). Barra limpia — no auto-reanuda. Reanudá desde Jobs pausados si querés seguir.`
      )
      await qc.invalidateQueries({ queryKey: ['auditoria-email'] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo detener')
    } finally {
      advancingRef.current = false
      setBusy(false)
    }
  }

  const onResetCola = async () => {
    if (
      !window.confirm(
        '¿Borrar TODA la cola Auditoría Email?\n\n• Jobs de escaneo\n• Bandeja\n• Recibos pending\n\nNo toca pagos/cartera ni Gmail. Recibos ya aplicados a cuotas se conservan.'
      )
    ) {
      return
    }
    if (
      !window.confirm(
        'Confirmá de nuevo: empezar limpio desde lote 0.'
      )
    ) {
      return
    }
    setBusy(true)
    setAutoContinue(false)
    advancingRef.current = true
    try {
      const res = await auditoriaEmailService.resetCola()
      setActive(null)
      restoredRef.current = true
      toast.success(
        `Cola limpia · scans ${res.scansEliminados} · msgs ${res.mensajesEliminados} · recibos ${res.recibosEliminados}` +
          (res.recibosApprovedConservados
            ? ` · approved conservados ${res.recibosApprovedConservados}`
            : '')
      )
      await qc.invalidateQueries({ queryKey: ['auditoria-email'] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo resetear la cola')
    } finally {
      advancingRef.current = false
      setBusy(false)
    }
  }

  const ready = Boolean(statusQ.data?.ready_for_scan)
  const pct =
    active && active.maxMessages > 0
      ? Math.min(100, Math.round((active.processedTotal / active.maxMessages) * 100))
      : 0
  const mensajesBd = Number(
    kpisQ.data?.mensajes ?? statusQ.data?.mensajes_bd ?? 0
  )
  const recibosBd = Number(kpisQ.data?.recibos ?? statusQ.data?.recibos_bd ?? 0)
  const recibosPending = Number(kpisQ.data?.recibos_pending ?? 0)
  const enProcesoN = Number(kpisQ.data?.en_proceso ?? 0)
  const enColaN = Number(kpisQ.data?.en_cola ?? 0)
  const currentOcr = kpisQ.data?.current
  const isStopped =
    Boolean(active?.stopped) ||
    String(active?.lastError || '')
      .toLowerCase()
      .includes('detenido')
  const isRunning = active?.status === 'running' && !isStopped
  const isComplete = active?.status === 'complete'

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-2 pt-5 text-sm">
          <div>
            <span className="text-muted-foreground">Conexión: </span>
            {statusQ.isLoading ? (
              '…'
            ) : ready ? (
              <span className="text-emerald-700">
                OK · {String(statusQ.data?.gmail_profile_email)}
              </span>
            ) : (
              <span className="text-amber-700">
                Pendiente —{' '}
                <Link className="underline" to="/auditoria/email/conexion">
                  conectar cobranza@
                </Link>
              </span>
            )}
          </div>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={autoContinue}
              disabled={isStopped}
              onChange={e => setAutoContinue(e.target.checked)}
            />
            Auto-reanudar lotes
            {isStopped ? (
              <span className="text-xs text-muted-foreground">(off: detenido)</span>
            ) : null}
          </label>
          <Button
            type="button"
            size="sm"
            variant="destructive"
            disabled={busy}
            onClick={() => void onResetCola()}
          >
            {busy ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="mr-2 h-4 w-4" />
            )}
            Borrar cola y empezar en 0
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Criterios de filtrado (Gmail)</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          <div>
            <label className="mb-1 block text-sm font-medium">Desde</label>
            <Input
              type="date"
              disabled={scanLive || busy}
              value={criteria.dateFrom || ''}
              onChange={e => patch({ dateFrom: e.target.value || undefined })}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Hasta</label>
            <Input
              type="date"
              disabled={scanLive || busy}
              value={criteria.dateTo || ''}
              onChange={e => patch({ dateTo: e.target.value || undefined })}
            />
          </div>
          {hasFullDateRange ? (
            <div className="md:col-span-2 lg:col-span-3 rounded-md border border-emerald-200 bg-emerald-50/60 px-3 py-2 text-xs text-emerald-900">
              Al <strong>Iniciar escaneo</strong> el job queda fijado con este
              rango{' '}
              <strong>
                {criteria.dateFrom} → {criteria.dateTo}
              </strong>{' '}
              y el resto de criterios (asunto, adjuntos, etc.). Cambiar el
              formulario después no altera un escaneo ya en curso.
            </div>
          ) : (
            <div className="md:col-span-2 lg:col-span-3 rounded-md border border-amber-200 bg-amber-50/60 px-3 py-2 text-xs text-amber-950">
              Completá <strong>Desde</strong> y <strong>Hasta</strong> para
              poder iniciar.
            </div>
          )}
          <div>
            <label className="mb-1 block text-sm font-medium">Asunto</label>
            <Input
              disabled={scanLive || busy}
              value={criteria.subject || ''}
              onChange={e => patch({ subject: e.target.value })}
              placeholder="comprobante OR pago"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Modo asunto</label>
            <Select
              disabled={scanLive || busy}
              value={criteria.subjectMode || 'contains'}
              onValueChange={v =>
                patch({
                  subjectMode: v as AuditoriaEmailCriteria['subjectMode'],
                })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="contains">Contiene</SelectItem>
                <SelectItem value="exact">Exacto</SelectItem>
                <SelectItem value="any_word">Cualquier palabra</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Remitente</label>
            <Input
              disabled={scanLive || busy}
              value={criteria.from || ''}
              onChange={e => patch({ from: e.target.value })}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Adjuntos</label>
            <Select
              disabled={scanLive || busy}
              value={criteria.attachments || 'pagos_gmail'}
              onValueChange={v =>
                patch({
                  attachments: v as AuditoriaEmailCriteria['attachments'],
                })
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pagos_gmail">
                  Como Pagos Gmail (adjunto/embebido)
                </SelectItem>
                <SelectItem value="none">Sin adjuntos</SelectItem>
                <SelectItem value="any">Cualquier adjunto</SelectItem>
                <SelectItem value="receipt_strong">Recibo fuerte</SelectItem>
                <SelectItem value="pdf_or_image">PDF o imagen</SelectItem>
                <SelectItem value="pdf_only">Solo PDF</SelectItem>
                <SelectItem value="image_only">Solo imagen</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">
              Adjunto mín. (KB)
            </label>
            <Input
              type="number"
              min={0}
              disabled={scanLive || busy}
              value={criteria.attachmentMinKb ?? ''}
              onChange={e =>
                patch({
                  attachmentMinKb: e.target.value
                    ? Number(e.target.value)
                    : undefined,
                })
              }
            />
          </div>
          <div className="md:col-span-2 lg:col-span-3">
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-1"
                disabled={scanLive || busy}
                checked={Boolean(criteria.excludeAnalizados)}
                onChange={e =>
                  patch({ excludeAnalizados: e.target.checked || undefined })
                }
              />
              <span>
                Excluir ya analizados (etiqueta ANALIZADOS)
                <span className="mt-0.5 block text-xs font-normal text-muted-foreground">
                  Por defecto apagado: se escanean todos los que cumplan el
                  filtro, con o sin etiqueta.
                </span>
              </span>
            </label>
          </div>
        </CardContent>
      </Card>

      <Card className={active ? 'border-primary/30' : undefined}>
        <CardHeader>
          <CardTitle className="flex flex-wrap items-center gap-2 text-base">
            Modo de escaneo
            {active ? (
              <>
                <span className="text-muted-foreground">·</span>
                <span className="font-normal text-muted-foreground">
                  #{active.id}
                </span>
                {isRunning ? (
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                ) : null}
                <span
                  className={
                    isComplete
                      ? 'text-sm font-normal text-emerald-700'
                      : 'text-sm font-normal text-muted-foreground'
                  }
                >
                  {statusLabel(active.status, isStopped)}
                </span>
              </>
            ) : null}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium">Modo</label>
              <Select
                value={mode}
                onValueChange={v => setMode(v as 'single' | 'batch')}
              >
                <SelectTrigger className="w-[160px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="single">Rápido (lotes ≤100)</SelectItem>
                  <SelectItem value="batch">Lotes (hasta 32k)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {(mode === 'batch' || hasFullDateRange) && (
              <div>
                <label className="mb-1 block text-sm font-medium">
                  Tamaño lote
                </label>
                <Input
                  type="number"
                  min={1}
                  max={100}
                  className="w-[120px]"
                  value={hasFullDateRange ? LOT_SIZE_SAFE : lotSize}
                  disabled={hasFullDateRange}
                  onChange={e =>
                    setLotSize(
                      Math.min(
                        100,
                        Math.max(1, Number(e.target.value) || LOT_SIZE_SAFE)
                      )
                    )
                  }
                />
                {hasFullDateRange ? (
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Fijo en {LOT_SIZE_SAFE} para no sobrecargar.
                  </p>
                ) : null}
              </div>
            )}
            <div>
              <label className="mb-1 block text-sm font-medium">
                Máx. mensajes
                {hasFullDateRange ? (
                  <span className="ml-1 text-xs font-normal text-muted-foreground">
                    (auto = todos en el rango)
                  </span>
                ) : null}
              </label>
              <Input
                type="number"
                min={1}
                max={32000}
                className="w-[140px]"
                value={maxMessages}
                onChange={e =>
                  setMaxMessages(
                    Math.min(32000, Math.max(1, Number(e.target.value) || 1))
                  )
                }
              />
            </div>
            <Button
              type="button"
              variant="outline"
              disabled={busy}
              onClick={() => void onEstimate()}
            >
              Estimar
            </Button>
            <Button
              type="button"
              disabled={busy || !ready || isRunning || !hasFullDateRange}
              onClick={() => void onStart()}
            >
              {busy || isRunning ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              {isRunning ? 'Escaneando…' : 'Iniciar escaneo'}
            </Button>
          </div>

          <div className="space-y-1.5 rounded-md border bg-muted/30 px-3 py-3">
            <div className="flex items-center justify-between gap-2 text-sm">
              <span className="font-medium tabular-nums">
                {active
                  ? `${active.processedTotal} / ${active.maxMessages} mensajes`
                  : 'Sin escaneo activo'}
              </span>
              <span className="tabular-nums text-muted-foreground">
                {active ? `${pct}%` : '—'}
              </span>
            </div>
            <Progress
              value={active ? pct : 0}
              className={
                isComplete
                  ? 'h-3 [&>div]:bg-emerald-600'
                  : 'h-3'
              }
              aria-label={
                active
                  ? `Avance del escaneo ${pct} por ciento`
                  : 'Sin escaneo activo'
              }
            />
            <p className="text-xs text-muted-foreground">
              {!active
                ? 'Sin escaneo activo. Iniciar arranca uno nuevo con los criterios de arriba; Jobs pausados permite reanudar uno detenido.'
                : isStopped
                  ? 'Detenido: no avanza ni auto-reanuda. Reanudar 1 lote para continuar, o Iniciar para otro job.'
                  : isRunning && active.processedTotal === 0
                    ? 'OCR en curso… la barra avanza al procesar cada correo (1–2+ min c/u).'
                    : isRunning
                      ? 'Procesando… actualización cada ~2 s. Recibos aparecen al digitalizar cada correo.'
                      : isComplete
                        ? 'Escaneo terminado.'
                        : autoContinue
                          ? 'Pausado entre lotes — Auto-reanudar activo.'
                          : 'Pausado — Auto-reanudar off; usá Reanudar 1 lote.'}
            </p>
            {active?.gmailQuery ? (
              <div className="rounded border border-sky-200 bg-sky-50/60 px-2 py-1.5 text-xs text-sky-950">
                <span className="font-medium">Condiciones del job: </span>
                <code className="break-all">{active.gmailQuery}</code>
                {active.criteria?.dateFrom && active.criteria?.dateTo ? (
                  <span className="mt-0.5 block text-sky-900/80">
                    Rango {active.criteria.dateFrom} → {active.criteria.dateTo}
                    {active.criteria.subject
                      ? ` · asunto: ${active.criteria.subject}`
                      : ''}
                  </span>
                ) : null}
              </div>
            ) : null}
            {active && !isStopped && (isRunning || enProcesoN > 0 || enColaN > 0) ? (
              <div className="rounded border border-amber-200 bg-amber-50/50 px-2 py-1.5 text-xs text-amber-950">
                <span className="font-medium">Ahora: </span>
                {enProcesoN > 0 ? (
                  <>
                    OCR activo ({enProcesoN})
                    {currentOcr?.subject
                      ? ` · ${String(currentOcr.subject).slice(0, 80)}`
                      : currentOcr?.fromEmail
                        ? ` · ${currentOcr.fromEmail}`
                        : ''}
                    {enColaN > 0 ? ` · En cola: ${enColaN}` : ''}
                  </>
                ) : enColaN > 0 ? (
                  <>En cola: {enColaN} (esperando OCR)</>
                ) : (
                  <>Preparando lote…</>
                )}
                {recibosPending > 0 ? (
                  <span className="ml-2 text-emerald-800">
                    · Recibos pending: {recibosPending}
                  </span>
                ) : null}
              </div>
            ) : null}
            {active?.lastError ? (
              <p className="text-xs text-amber-800">
                Último aviso: {String(active.lastError).slice(0, 200)}
              </p>
            ) : null}
            {active ? (
              <div className="grid grid-cols-2 gap-2 pt-1 sm:grid-cols-4">
                <div className="rounded border bg-background px-2 py-1.5">
                  <div className="text-xs text-muted-foreground">Procesados</div>
                  <div className="text-lg font-semibold tabular-nums">
                    {active.processedTotal}
                  </div>
                </div>
                <div className="rounded border bg-background px-2 py-1.5">
                  <div className="text-xs text-muted-foreground">Listados</div>
                  <div className="text-lg font-semibold tabular-nums">
                    {active.listedTotal}
                  </div>
                </div>
                <div className="rounded border bg-background px-2 py-1.5">
                  <div className="text-xs text-muted-foreground">En Bandeja</div>
                  <div className="text-lg font-semibold tabular-nums">
                    {mensajesBd}
                  </div>
                </div>
                <div className="rounded border bg-background px-2 py-1.5">
                  <div className="text-xs text-muted-foreground">Recibos</div>
                  <div className="text-lg font-semibold tabular-nums">
                    {recibosBd}
                    {recibosPending > 0 ? (
                      <span className="ml-1 text-xs font-normal text-muted-foreground">
                        ({recibosPending} pend.)
                      </span>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : null}
            {active ? (
              <div className="flex flex-wrap gap-2 pt-1">
                {isRunning ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="destructive"
                    disabled={busy}
                    onClick={() => void onPause(active.id)}
                  >
                    <Square className="mr-2 h-4 w-4" />
                    Detener y limpiar
                  </Button>
                ) : null}
                {(active.status === 'paused' || isStopped) && (
                  <Button
                    type="button"
                    size="sm"
                    disabled={busy}
                    onClick={() => void onAdvance(active.id)}
                  >
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Reanudar 1 lote
                  </Button>
                )}
                {!isRunning ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={busy}
                    onClick={() => {
                      setActive(null)
                      setAutoContinue(false)
                      restoredRef.current = true
                      toast.message('Barra limpia. El job queda en Jobs pausados si estaba detenido.')
                    }}
                  >
                    Limpiar barra
                  </Button>
                ) : null}
                <Button type="button" size="sm" variant="outline" asChild>
                  <Link to="/auditoria/email/bandeja">Ver Bandeja</Link>
                </Button>
                <Button type="button" size="sm" variant="outline" asChild>
                  <Link to="/auditoria/email/recibos">Ver Recibos</Link>
                </Button>
              </div>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Jobs pausados</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(paused.data?.items || []).length === 0 && (
            <p className="text-sm text-muted-foreground">Ninguno.</p>
          )}
          {(paused.data?.items || []).map(s => (
            <div
              key={s.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded border px-3 py-2 text-sm"
            >
              <span>
                #{s.id} · {s.processedTotal}/{s.maxMessages}
                {s.lastError ? ` · ${s.lastError.slice(0, 80)}` : ''}
              </span>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={busy}
                onClick={() => {
                  setActive(s)
                  void onAdvance(s.id)
                }}
              >
                Reanudar
              </Button>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
