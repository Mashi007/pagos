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
    if (oauthFlash === 'error') {
      if (oauthReason === 'invalid_client')
        return 'OAuth falló: Client ID / Secret incorrectos o mezclados. En Render usa AUDITORIA_EMAIL_GOOGLE_CLIENT_ID y AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET del mismo cliente Web cobranzas (…bitt…).'
      if (oauthReason === 'misconfigured_audit_id_without_secret')
        return 'OAuth mal configurado: falta AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET en Render (no uses GOOGLE_CLIENT_SECRET de itmaster).'
      if (oauthReason === 'redirect_uri_mismatch')
        return 'OAuth falló: redirect_uri no coincide. En Google Cloud agrega la URI que muestra abajo al cliente cobranzas.'
      if (oauthReason === 'invalid_grant')
        return 'OAuth falló: código expirado o ya usado. Pulsa Conectar de nuevo (sin recargar la pestaña de Google).'
      return `OAuth falló${oauthReason ? `: ${oauthReason}` : ''}. Reintenta entrando como cobranza@.`
    }
    if (s.oauth_client_source === 'misconfigured_audit_id_without_secret')
      return 'Falta AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET en Render (Client ID cobranzas sí está configurado).'
    if (s.oauth_client_source === 'missing_auditoria_email_env')
      return 'Faltan AUDITORIA_EMAIL_GOOGLE_CLIENT_ID y SECRET en Render. No uses las credenciales de itmaster (Informe de pagos).'
    return null
  }, [oauthFlash, oauthReason, s.oauth_client_source])

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
          <strong>OAuth client (Render):</strong>{' '}
          {String(s.oauth_client_source || '—')}
          {s.oauth_client_id_suffix ? (
            <>
              {' '}
              <code className="text-xs">{String(s.oauth_client_id_suffix)}</code>
            </>
          ) : null}
          {s.oauth_client_configured === false ? (
            <span className="text-amber-700"> — par ID/secret incompleto</span>
          ) : null}
          {s.oauth_client_secret_suffix ? (
            <>
              {' '}
              (secret …{String(s.oauth_client_secret_suffix)}, len{' '}
              {String(s.oauth_client_secret_len)})
            </>
          ) : null}
          {s.oauth_secrets_match_google_env === false ? (
            <span className="text-amber-700">
              {' '}
              — AUDITORIA_EMAIL secret ≠ GOOGLE_CLIENT_SECRET (revisa 0 vs O al pegar)
            </span>
          ) : null}
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
