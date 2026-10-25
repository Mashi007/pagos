import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useMemo } from 'react'

import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { auditoriaEmailService } from '../../services/auditoriaEmailService'

export default function AuditoriaEmailPanelPage() {
  const qc = useQueryClient()
  const [params] = useSearchParams()
  const oauthFlash = params.get('oauth')
  const oauthReason = params.get('reason')

  const kpis = useQuery({
    queryKey: ['auditoria-email', 'kpis'],
    queryFn: () => auditoriaEmailService.kpis(),
  })
  const status = useQuery({
    queryKey: ['auditoria-email', 'status'],
    queryFn: () => auditoriaEmailService.status(),
  })

  const authorize = useMutation({
    mutationFn: () => auditoriaEmailService.oauthAuthorize(),
    onSuccess: data => {
      const url = data?.redirect_url
      if (url) window.location.href = url
    },
  })

  const s = status.data || {}
  const oauthHint = useMemo(() => {
    if (oauthFlash === 'ok') return 'Conexión OAuth de cobranza@ guardada.'
    if (oauthFlash === 'error') {
      if (oauthReason === 'invalid_client')
        return 'OAuth falló: Client ID / Secret no válidos. Revise Configuración → Informe de pagos.'
      if (oauthReason === 'redirect_uri_mismatch')
        return 'OAuth falló: redirect_uri no coincide en Google Cloud.'
      if (oauthReason === 'invalid_grant')
        return 'OAuth falló: código expirado. Pulse Conectar de nuevo.'
      if (oauthReason === 'save_failed')
        return 'OAuth OK pero no se guardaron los tokens. Reintente Conectar.'
      return `OAuth falló${oauthReason ? `: ${oauthReason}` : ''}.`
    }
    return null
  }, [oauthFlash, oauthReason])

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
      {oauthHint ? (
        <p
          className={
            oauthFlash === 'ok' ? 'text-sm text-emerald-700' : 'text-sm text-amber-700'
          }
        >
          {oauthHint}
        </p>
      ) : null}

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
            <p className="text-sm text-muted-foreground">Buzón cobranza@</p>
            <p className="truncate text-sm font-medium">{k?.mailbox}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {s.ready_for_scan
                ? `Gmail OK: ${String(s.gmail_profile_email || 'conectado')}`
                : s.gmail_connected
                  ? 'OAuth activo pero buzón no coincide'
                  : 'Sin conexión'}
            </p>
            {!s.ready_for_scan ? (
              <Button
                className="mt-2"
                size="sm"
                disabled={authorize.isPending}
                onClick={() => authorize.mutate()}
              >
                {authorize.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Conectar cobranza@'
                )}
              </Button>
            ) : null}
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
        {s.ready_for_scan ? (
          <Button
            variant="outline"
            disabled={authorize.isPending}
            onClick={() => authorize.mutate()}
          >
            Reconectar cobranza@
          </Button>
        ) : null}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            void qc.invalidateQueries({ queryKey: ['auditoria-email'] })
          }}
        >
          Actualizar estado
        </Button>
      </div>
    </div>
  )
}
