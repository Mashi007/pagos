import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2, Play, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Input } from '../../components/ui/input'
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

const PRESETS = [
  { id: 'lote-comprobantes', label: 'Lote comprobantes' },
  { id: 'ultimos-7', label: 'Últimos 7 días' },
  { id: 'ultimos-30', label: 'Últimos 30 días' },
  { id: 'comprobantes-ocr', label: 'Comprobantes OCR' },
  { id: 'comprobantes', label: 'Comprobantes' },
  { id: 'promesas', label: 'Promesas' },
  { id: 'reclamos', label: 'Reclamos' },
  { id: 'legal', label: 'Legal' },
  { id: 'rebotes', label: 'Rebotes' },
  { id: 'sla', label: 'SLA / urgentes' },
  { id: 'adjuntos-fuertes', label: 'Adjuntos fuertes' },
]

const POLL_MS = 4000

export default function AuditoriaEmailEscanearPage() {
  const qc = useQueryClient()
  const [mode, setMode] = useState<'single' | 'batch'>('single')
  const [criteria, setCriteria] = useState<AuditoriaEmailCriteria>({
    preset: 'ultimos-7',
    newerThanDays: 7,
    attachments: 'pdf_or_image',
  })
  const [lotSize, setLotSize] = useState(100)
  const [maxMessages, setMaxMessages] = useState(100)
  const [busy, setBusy] = useState(false)
  const [autoContinue, setAutoContinue] = useState(true)
  const [active, setActive] = useState<AuditoriaEmailScan | null>(null)
  const advancingRef = useRef(false)

  const statusQ = useQuery({
    queryKey: ['auditoria-email', 'status'],
    queryFn: () => auditoriaEmailService.status(),
  })

  const paused = useQuery({
    queryKey: ['auditoria-email', 'paused'],
    queryFn: () => auditoriaEmailService.pausedScans(),
  })

  const patch = useCallback((p: Partial<AuditoriaEmailCriteria>) => {
    setCriteria(prev => ({ ...prev, ...p }))
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
          !String(s.lastError || '').toLowerCase().includes('ocupado')
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
    const t = window.setInterval(() => void tick(), POLL_MS)
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
      const res = await auditoriaEmailService.createScan({
        mode,
        criteria,
        lotSize: mode === 'batch' ? lotSize : undefined,
        maxMessages:
          mode === 'single' ? Math.min(maxMessages, 100) : maxMessages,
      })
      setActive(res)
      toast.success(
        `Escaneo #${res.id} en curso · ${res.status} (lotes en background)`
      )
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

  const ready = Boolean(statusQ.data?.ready_for_scan)
  const pct =
    active && active.maxMessages > 0
      ? Math.min(100, Math.round((active.processedTotal / active.maxMessages) * 100))
      : 0

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
            <label className="mb-1 block text-sm font-medium">Preset</label>
            <Select
              value={criteria.preset || 'ultimos-7'}
              onValueChange={v => patch({ preset: v })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRESETS.map(p => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
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
          <div>
            <label className="mb-1 block text-sm font-medium">
              Newer than (días)
            </label>
            <Input
              type="number"
              min={1}
              value={criteria.newerThanDays ?? ''}
              onChange={e =>
                patch({
                  newerThanDays: e.target.value
                    ? Number(e.target.value)
                    : undefined,
                })
              }
            />
          </div>
          <div>
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
              value={criteria.attachments || 'pdf_or_image'}
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
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Modo de escaneo</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
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
                <SelectItem value="single">Rápido (≤100)</SelectItem>
                <SelectItem value="batch">Lotes (hasta 32k)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {mode === 'batch' && (
            <div>
              <label className="mb-1 block text-sm font-medium">
                Tamaño lote
              </label>
              <Input
                type="number"
                min={1}
                max={100}
                className="w-[120px]"
                value={lotSize}
                onChange={e =>
                  setLotSize(Math.min(100, Number(e.target.value) || 100))
                }
              />
            </div>
          )}
          <div>
            <label className="mb-1 block text-sm font-medium">Máx. mensajes</label>
            <Input
              type="number"
              min={1}
              max={mode === 'single' ? 100 : 32000}
              className="w-[140px]"
              value={maxMessages}
              onChange={e => setMaxMessages(Number(e.target.value) || 100)}
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
            disabled={busy || !ready}
            onClick={() => void onStart()}
          >
            {busy ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            Iniciar escaneo
          </Button>
        </CardContent>
      </Card>

      {active && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Escaneo activo #{active.id}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              Estado: <strong>{active.status}</strong>
              {active.status === 'running' ? (
                <Loader2 className="ml-2 inline h-3.5 w-3.5 animate-spin" />
              ) : null}
            </p>
            <div className="h-2 w-full overflow-hidden rounded bg-muted">
              <div
                className="h-full bg-primary transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <p>
              Procesados: {active.processedTotal} / {active.maxMessages} ·
              Listados: {active.listedTotal} · Rechazados:{' '}
              {active.rejectedTotal} · Lotes: {active.lotsDone}
            </p>
            {active.lastError ? (
              <p className="text-amber-700">Último error: {active.lastError}</p>
            ) : null}
            {active.gmailQuery && (
              <p className="break-all text-xs text-muted-foreground">
                Query: {active.gmailQuery}
              </p>
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
          </CardContent>
        </Card>
      )}

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
