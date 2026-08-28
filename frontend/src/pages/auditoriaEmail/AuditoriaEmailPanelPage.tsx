import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Loader2 } from 'lucide-react'

import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { auditoriaEmailService } from '../../services/auditoriaEmailService'

export default function AuditoriaEmailPanelPage() {
  const kpis = useQuery({
    queryKey: ['auditoria-email', 'kpis'],
    queryFn: () => auditoriaEmailService.kpis(),
  })
  const status = useQuery({
    queryKey: ['auditoria-email', 'status'],
    queryFn: () => auditoriaEmailService.status(),
  })

  if (kpis.isLoading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Cargando panel…
      </div>
    )
  }

  const k = kpis.data
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-5">
            <p className="text-sm text-muted-foreground">Mensajes ingeridos</p>
            <p className="text-2xl font-semibold">{k?.mensajes ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-sm text-muted-foreground">Recibos</p>
            <p className="text-2xl font-semibold">{k?.recibos ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-sm text-muted-foreground">Escaneos pausados</p>
            <p className="text-2xl font-semibold">{k?.escaneos_pausados ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <p className="text-sm text-muted-foreground">Buzón objetivo</p>
            <p className="truncate text-sm font-medium">{k?.mailbox}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {status.data?.ready_for_scan
                ? `Gmail OK: ${String(status.data.gmail_profile_email || 'conectado')}`
                : status.data?.gmail_connected
                  ? 'OAuth activo pero buzón no coincide — revisa Conexión'
                  : 'Sin conexión cobranza@'}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Por ruta de revisión</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {Object.entries(k?.por_ruta || {}).length === 0 && (
              <p className="text-muted-foreground">Sin datos aún.</p>
            )}
            {Object.entries(k?.por_ruta || {}).map(([key, n]) => (
              <div key={key} className="flex justify-between">
                <span>{key}</span>
                <span className="font-medium">{Number(n)}</span>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Por clasificación</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {Object.entries(k?.por_clase || {}).length === 0 && (
              <p className="text-muted-foreground">Sin datos aún.</p>
            )}
            {Object.entries(k?.por_clase || {}).map(([key, n]) => (
              <div key={key} className="flex justify-between">
                <span>{key}</span>
                <span className="font-medium">{Number(n)}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button asChild>
          <Link to="/auditoria/email/escanear">Escanear bandeja</Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/auditoria/email/bandeja">Abrir bandeja</Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/auditoria/email/conexion">Ver conexión</Link>
        </Button>
      </div>
    </div>
  )
}
