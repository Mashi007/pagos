import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Loader2 } from 'lucide-react'

import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { auditoriaEmailService } from '../../services/auditoriaEmailService'

export default function AuditoriaEmailBandejaDetallePage() {
  const { id } = useParams()
  const messageId = Number(id)
  const q = useQuery({
    queryKey: ['auditoria-email', 'bandeja', messageId],
    queryFn: () => auditoriaEmailService.bandejaItem(messageId),
    enabled: Number.isFinite(messageId) && messageId > 0,
  })

  if (q.isLoading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Cargando…
      </div>
    )
  }
  if (q.isError || !q.data) {
    return (
      <div className="space-y-2">
        <p className="text-red-600">No se encontró el mensaje.</p>
        <Button asChild variant="outline">
          <Link to="/auditoria/email/bandeja">Volver</Link>
        </Button>
      </div>
    )
  }
  const m = q.data
  const recibos = (m.recibos as Array<Record<string, unknown>>) || []
  return (
    <div className="space-y-4">
      <Button asChild variant="outline" size="sm">
        <Link to="/auditoria/email/bandeja">← Bandeja</Link>
      </Button>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {String(m.subject || '(sin asunto)')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>
            <strong>De:</strong> {String(m.fromEmail || '—')}
          </p>
          <p>
            <strong>Fecha:</strong>{' '}
            {m.internalDate
              ? new Date(String(m.internalDate)).toLocaleString('es-VE')
              : '—'}
          </p>
          <p>
            <strong>Préstamo:</strong>{' '}
            {Array.isArray(m.prestamoEstados) && m.prestamoEstados.length
              ? (m.prestamoEstados as unknown[]).map(String).join(' · ')
              : String(m.prestamoEstado || '—')}
          </p>
          <p>
            <strong>Clase / ruta / riesgo:</strong> {String(m.classify)} ·{' '}
            {String(m.route)} · {String(m.riesgo)}
          </p>
          <p>
            <strong>SLA:</strong>{' '}
            {m.slaHours != null ? `${m.slaHours} h` : '—'} · Evidencia:{' '}
            {String(m.evidencia || '—')}
          </p>
          <p className="text-muted-foreground">{String(m.snippet || '')}</p>
          <pre className="overflow-x-auto rounded bg-slate-50 p-3 text-xs">
            {JSON.stringify(
              { extract: m.extract, ocr: m.ocr },
              null,
              2
            )}
          </pre>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recibos ({recibos.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {recibos.length === 0 && (
            <p className="text-muted-foreground">Sin recibos detectados.</p>
          )}
          {recibos.map(r => (
            <div key={String(r.id)} className="rounded border px-3 py-2">
              {String(r.filename || 'adjunto')} · cédula {String(r.cedula || '—')}{' '}
              · préstamo{' '}
              {Array.isArray(r.prestamoEstados) && r.prestamoEstados.length
                ? (r.prestamoEstados as unknown[]).map(String).join(' · ')
                : String(r.prestamoEstado || '—')}{' '}
              · monto {String(r.monto ?? '—')} · {String(r.route || '—')}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
