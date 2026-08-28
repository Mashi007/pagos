import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { auditoriaEmailService } from '../../services/auditoriaEmailService'

export default function AuditoriaEmailHallazgosPage() {
  const kpis = useQuery({
    queryKey: ['auditoria-email', 'kpis'],
    queryFn: () => auditoriaEmailService.kpis(),
  })
  const aline = useQuery({
    queryKey: ['auditoria-email', 'alineamiento'],
    queryFn: () => auditoriaEmailService.alineamiento(),
  })

  if (kpis.isLoading || aline.isLoading) {
    return <Loader2 className="h-5 w-5 animate-spin" />
  }

  const checks = (aline.data?.checks as Array<Record<string, unknown>>) || []
  const backlog = (aline.data?.backlog as string[]) || []

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Hallazgos operativos</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>
            Mensajes en riesgo alto:{' '}
            <strong>
              {Object.entries(kpis.data?.por_ruta || {})
                .filter(([k]) => k === 'revision_manual')
                .reduce((a, [, n]) => a + Number(n), 0)}
            </strong>
          </p>
          <p>
            Rutas autoconciliación:{' '}
            <strong>{kpis.data?.por_ruta?.autoconciliacion ?? 0}</strong>
          </p>
          <p>
            Cascada / cargo a cuota:{' '}
            <strong>
              {(kpis.data?.por_ruta?.cascada ?? 0) +
                (kpis.data?.por_ruta?.cargo_a_cuota ?? 0)}
            </strong>
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Checks de alineamiento</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {checks.map(c => (
            <div
              key={String(c.id)}
              className="rounded border px-3 py-2 text-sm"
            >
              <div className="font-medium">
                {c.ok ? 'OK' : 'Pendiente'} · {String(c.id)}
              </div>
              <div className="text-muted-foreground">{String(c.detalle)}</div>
            </div>
          ))}
          {backlog.length > 0 && (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {backlog.map(b => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
