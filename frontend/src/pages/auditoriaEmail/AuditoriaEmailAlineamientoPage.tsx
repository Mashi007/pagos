import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { auditoriaEmailService } from '../../services/auditoriaEmailService'

export default function AuditoriaEmailAlineamientoPage() {
  const q = useQuery({
    queryKey: ['auditoria-email', 'alineamiento'],
    queryFn: () => auditoriaEmailService.alineamiento(),
  })
  if (q.isLoading) return <Loader2 className="h-5 w-5 animate-spin" />
  const checks = (q.data?.checks as Array<Record<string, unknown>>) || []
  const backlog = (q.data?.backlog as string[]) || []
  const flujo = (q.data?.flujo as string[]) || []
  return (
    <div className="space-y-4">
      {flujo.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Flujo vigente</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="list-decimal space-y-1 pl-5 text-sm">
              {flujo.map(step => (
                <li key={step}>{step.replace(/^\d+\.\s*/, '')}</li>
              ))}
            </ol>
          </CardContent>
        </Card>
      ) : null}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Alineamiento · manifiesto v{String(q.data?.manifest_version)}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {checks.map(c => (
            <div key={String(c.id)} className="rounded border px-3 py-2 text-sm">
              <div className="font-medium">
                {c.ok ? 'Cumple' : 'Pendiente'} — {String(c.id)}
              </div>
              <div className="break-all text-muted-foreground">
                {String(c.detalle)}
              </div>
            </div>
          ))}
          <div>
            <p className="mb-1 text-sm font-medium">Backlog</p>
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {backlog.map(b => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
