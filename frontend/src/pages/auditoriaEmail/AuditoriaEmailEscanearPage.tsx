import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Play, RefreshCw, Square } from 'lucide-react'
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

const DEFAULT_CRITERIA: AuditoriaEmailCriteria = {
  newerThanDays: 7,
  attachments: 'pagos_gmail',
}

/** Lotes pequeños para no saturar Gmail/OCR al traer “todos” del rango. */
const LOT_SIZE_SAFE = 50

const POLL_MS_RUNNING = 2000
const POLL_MS_IDLE = 4000

function statusLabel(status: string): string {
  if (status === 'running') return 'En curso (OCR / Gmail)…'
  if (status === 'paused') return 'Pausado — reanudando lotes'
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
  const restoredRef = useRef(false)

  const scanLive =
    Boolean(active) && active?.status !== 'complete' && active?.status !== undefined

  const statusQ = useQuery({
    queryKey: ['auditoria-email', 'status'],
    queryFn: () => auditoriaEmailService.status(),
    refetchInterval: scanLive ? POLL_MS_RUNNING : false,
  })

  const kpisQ = useQuery({
    queryKey: ['auditoria-email', 'kpis'],
    queryFn: () => auditoriaEmailService.kpis(),
    refetchInterval: scanLive ? POLL_MS_RUNNING : false,
    enabled: Boolean(active),
  })

  const paused = useQuery({
    queryKey: ['auditoria-email', 'paused'],
    queryFn: () => auditoriaEmailService.pausedScans(),
  })

  // Al abrir Escanear: recuperar job running/paused (Bandeja ≠ esta barra).
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
          .filter(
            s =>
              s.status === 'running' ||
              (s.status === 'paused' &&
                (Boolean(s.paused) ||
                  (s.processedTotal === 0 && !s.finishedAt)))
          )
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

  const hasDateRange = Boolean(criteria.dateFrom || criteria.dateTo)
  const hasFullDateRange = Boolean(criteria.dateFrom && criteria.dateTo)

  const patch = useCallback((p: Partial<AuditoriaEmailCriteria>) => {
    setCriteria(prev => {
      const next = { ...prev, ...p }
      // Fechas y newer_than son excluyentes (Gmail ignora newer_than con after/before).
      if (p.dateFrom !== undefined || p.dateTo !== undefined) {
        if (next.dateFrom || next.dateTo) {
          delete next.newerThanDays
        }
      }
      if (p.newerThanDays !== undefined && p.newerThanDays) {
        delete next.dateFrom
        delete next.dateTo
      }
      return next
    })
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
        if (
          autoContinue &&
          s.status === 'paused' &&
          s.paused &&
          !String(s.lastError || '')
            .toLowerCase()
            .includes('ocupado') &&
          !String(s.lastError || '')
            .toLowerCase()
            .includes('detenido')
        ) {
          advancingRef.current = true
          try {
            await auditoriaEmailService.advanceScan(s.id, 1)
            await refreshActive(s.id)
          } catch (e) {
            toast.error(getErrorMessage(e) || 'No se pudo reanudar lote')
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
    setBusy(true)
    try {
      const res = await auditoriaEmailService.estimate(criteria)
      toast.message(
        `${res.estimated.toLocaleString()} mensajes est. (${res.source}${res.exact ? ', exacto' : ', aprox.'})`
      )
      if (res.gmail_query) {
        toast.message(`q: ${res.gmail_query}`)
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
    setBusy(true)
    try {
      // Con Desde+Hasta: escanear TODOS los del filtro en lotes de 50
      // hasta agotar el periodo (tope de seguridad 32k).
      let startMode = mode
      let startMax = Math.min(Math.max(1, maxMessages), 32000)
      let startLot = Math.min(LOT_SIZE_SAFE, Math.max(1, lotSize || LOT_SIZE_SAFE))
      if (hasFullDateRange) {
        startMode = 'batch'
        startLot = LOT_SIZE_SAFE
        setLotSize(LOT_SIZE_SAFE)
        try {
          const est = await auditoriaEmailService.estimate(criteria)
          const n = Number(est.estimated || 0)
          if (n > 0) {
            startMax = Math.min(32000, n)
            setMaxMessages(startMax)
            toast.message(
              `Rango ${criteria.dateFrom} → ${criteria.dateTo}: ~${n.toLocaleString()} msgs · lotes de ${LOT_SIZE_SAFE} hasta terminar.`
            )
          } else {
            startMax = 32000
            setMaxMessages(32000)
            toast.message(
              `Rango ${criteria.dateFrom} → ${criteria.dateTo}: todos los del filtro en lotes de ${LOT_SIZE_SAFE} (tope 32k).`
            )
          }
        } catch {
          startMax = 32000
          setMaxMessages(32000)
        }
        setMode('batch')
      }
      const res = await auditoriaEmailService.createScan({
        mode: startMode,
        criteria,
        lotSize: startMode === 'batch' ? startLot : undefined,
        maxMessages: startMax,
      })
      setActive(res)
      // Arranque inmediato del 1.er lote (create deja paused sin pageToken).
      advancingRef.current = true
      try {
        const started = await auditoriaEmailService.advanceScan(res.id, 1)
        setActive(started)
        toast.success(
          `Escaneo #${started.id} en curso · ${started.processedTotal}/${started.maxMessages}`
        )
      } catch (advErr) {
        toast.message(
          `Escaneo #${res.id} creado · usa Reanudar si no avanza (${getErrorMessage(advErr) || 'error'})`
        )
      } finally {
        advancingRef.current = false
      }
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
    try {
      const s = await auditoriaEmailService.pauseScan(id)
      setActive(s)
      toast.message(
        `Escaneo #${id} detenido · ${s.processedTotal}/${s.maxMessages}. Podés Reanudar.`
      )
      await qc.invalidateQueries({ queryKey: ['auditoria-email'] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo detener')
    } finally {
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
  const isRunning = active?.status === 'running'
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
              onChange={e => setAutoContinue(e.target.checked)}
            />
            Auto-reanudar lotes
          </label>
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
              value={criteria.dateFrom || ''}
              onChange={e => patch({ dateFrom: e.target.value || undefined })}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Hasta</label>
            <Input
              type="date"
              value={criteria.dateTo || ''}
              onChange={e => patch({ dateTo: e.target.value || undefined })}
            />
          </div>
          {hasFullDateRange ? (
            <div className="md:col-span-2 lg:col-span-3 rounded-md border border-emerald-200 bg-emerald-50/60 px-3 py-2 text-xs text-emerald-900">
              Con <strong>Desde</strong> y <strong>Hasta</strong> se escanean{' '}
              <strong>todos</strong> los correos del filtro en ese rango, en{' '}
              <strong>lotes de {LOT_SIZE_SAFE}</strong> (OCR de a uno dentro del
              lote) hasta agotar el periodo. Tope de seguridad 32k.
            </div>
          ) : null}
          <div>
            <label className="mb-1 block text-sm font-medium">
              Newer than (días)
              {hasDateRange ? (
                <span className="ml-1 text-xs font-normal text-muted-foreground">
                  (inactivo con rango)
                </span>
              ) : null}
            </label>
            <Input
              type="number"
              min={1}
              disabled={hasDateRange}
              value={hasDateRange ? '' : (criteria.newerThanDays ?? '')}
              onChange={e =>
                patch({
                  newerThanDays: e.target.value
                    ? Number(e.target.value)
                    : undefined,
                })
              }
            />
          </div>          <div>
            <label className="mb-1 block text-sm font-medium">Asunto</label>
            <Input
              value={criteria.subject || ''}
              onChange={e => patch({ subject: e.target.value })}
              placeholder="comprobante OR pago"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Modo asunto</label>
            <Select
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
              value={criteria.from || ''}
              onChange={e => patch({ from: e.target.value })}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Adjuntos</label>
            <Select
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
                  {statusLabel(active.status)}
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
              disabled={busy || !ready || isRunning}
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
                ? 'Esta barra es del job actual. La Bandeja muestra el historial (puede tener filas de escaneos previos). Pulsa Iniciar o Reanudar abajo.'
                : isRunning && active.processedTotal === 0
                  ? 'OCR en curso… la barra avanza al procesar cada correo (1–2+ min c/u).'
                  : isRunning
                    ? 'Procesando… actualización cada ~2 s. Recibos aparecen al digitalizar cada correo.'
                    : isComplete
                      ? 'Escaneo terminado.'
                      : 'Pausado — reanudando lotes automáticamente si Auto-reanudar está activo.'}
            </p>
            {active && (isRunning || enProcesoN > 0 || enColaN > 0) ? (
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
                {(active.status === 'running' || active.status === 'paused') && (
                  <Button
                    type="button"
                    size="sm"
                    variant="destructive"
                    disabled={busy}
                    onClick={() => void onPause(active.id)}
                  >
                    <Square className="mr-2 h-4 w-4" />
                    Detener
                  </Button>
                )}
                {active.status === 'paused' && (
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
