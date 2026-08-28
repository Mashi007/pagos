import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { auditoriaEmailService } from '../../services/auditoriaEmailService'

export default function AuditoriaEmailPipelinesPage() {
  const q = useQuery({
    queryKey: ['auditoria-email', 'pipelines'],
    queryFn: () => auditoriaEmailService.pipelines(),
  })
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Pipelines</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {q.isLoading && <Loader2 className="h-5 w-5 animate-spin" />}
        {(q.data?.items || []).map(p => (
          <div
            key={p.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded border px-3 py-2 text-sm"
          >
            <div>
              <div className="font-medium">{p.nombre}</div>
              <div className="text-xs text-muted-foreground">{p.id}</div>
            </div>
            <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">
              {p.fase}
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
