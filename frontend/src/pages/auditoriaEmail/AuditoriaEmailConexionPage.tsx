import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { auditoriaEmailService } from '../../services/auditoriaEmailService'

export default function AuditoriaEmailConexionPage() {
  const qc = useQueryClient()
  const [params] = useSearchParams()
  const oauthFlash = params.get('oauth')
  const oauthReason = params.get('reason')

  const q = useQuery({
    queryKey: ['auditoria-email', 'status'],
    queryFn: () => auditoriaEmailService.status(),
  })

  const authorize = useMutation({
    mutationFn: () => auditoriaEmailService.oauthAuthorize(),
    onSuccess: (data) => {
      const url = data?.redirect_url
      if (url) window.location.href = url
    },
  })

  const s = q.data || {}
  const hint = useMemo(() => {
    if (oauthFlash === 'ok') return 'Conexión OAuth guardada. Recarga el estado si hace falta.'
    if (oauthFlash === 'error')
      return `OAuth falló${oauthReason ? `: ${oauthReason}` : ''}. Reintenta entrando como cobranza@.`
    return null
  }, [oauthFlash, oauthReason])

  if (q.isLoading) return <Loader2 className="h-5 w-5 animate-spin" />

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Conexión Gmail — cobranza@</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {hint ? (
          <p className={oauthFlash === 'ok' ? 'text-emerald-700' : 'text-amber-700'}>
            {hint}
          </p>
        ) : null}
        <p>
          <strong>Buzón objetivo:</strong> {String(s.mailbox_target)}
        </p>
        <p>
          <strong>Estado:</strong>{' '}
          {s.gmail_connected ? 'Conectado' : 'No conectado'}
        </p>
        <p>
          <strong>Perfil OAuth:</strong>{' '}
          {String(s.gmail_profile_email || '—')}
          {s.mailbox_match === false ? (
            <span className="text-amber-700">
              {' '}
              (no coincide con el buzón objetivo; vuelve a autorizar como{' '}
              {String(s.mailbox_target)})
            </span>
          ) : null}
        </p>
        <p>
          <strong>Archivo tokens:</strong>{' '}
          {String(s.tokens_path || '—')}{' '}
          {s.tokens_file_ready ? '(OK)' : '(sin refresh_token)'}
        </p>
        <p>
          <strong>Etiqueta al cerrar proceso:</strong>{' '}
          {String(s.label_analizados || 'ANALIZADOS')}
        </p>
        <p>
          <strong>URI redirect (Google Cloud):</strong>{' '}
          <code className="break-all text-xs">
            {String(s.oauth_redirect_uri || s.oauth_redirect_hint || '—')}
          </code>
        </p>
        <p>
          <strong>Mensajes / recibos en BD (tránsito):</strong>{' '}
          {String(s.mensajes_bd)} / {String(s.recibos_bd)}
        </p>
        {s.error ? (
          <p className="text-amber-700">Detalle: {String(s.error)}</p>
        ) : null}
        <p className="text-muted-foreground">
          Tokens separados de Pagos Gmail (`GMAIL_TOKENS_PATH_COBRANZA`). En Google
          Cloud añade la URI de redirect y autoriza entrando como{' '}
          {String(s.mailbox_target)}. Rota el client secret si se filtró.
        </p>
        <div className="flex flex-wrap gap-2 pt-1">
          <Button
            type="button"
            disabled={authorize.isPending}
            onClick={() => authorize.mutate()}
          >
            {authorize.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : null}
            Conectar {String(s.mailbox_target || 'cobranza@')}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              qc.invalidateQueries({ queryKey: ['auditoria-email', 'status'] })
            }
          >
            Actualizar estado
          </Button>
        </div>
        {authorize.isError ? (
          <p className="text-amber-700">
            {(authorize.error as Error)?.message || 'No se pudo iniciar OAuth'}
          </p>
        ) : null}
      </CardContent>
    </Card>
  )
}
