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
        return 'OAuth falló: Client ID / Secret no válidos para el cliente Web cobranzas (…bitt…). Guarda Client ID + Secret en Configuración → Informe de pagos (itmaster) y vuelve a conectar cobranza@.'
      if (oauthReason === 'redirect_uri_mismatch')
        return 'OAuth falló: redirect_uri no coincide. En Google Cloud agrega la URI que muestra abajo al cliente cobranzas.'
      if (oauthReason === 'invalid_grant')
        return 'OAuth falló: código expirado o ya usado. Pulsa Conectar de nuevo (sin recargar la pestaña de Google).'
      return `OAuth falló${oauthReason ? `: ${oauthReason}` : ''}. Reintenta entrando como cobranza@.`
    }
    if (s.oauth_client_source === 'shared_client_informe_pagos_bd')
      return 'OAuth listo: cobranza@ usa el mismo Client ID/Secret que Informe de pagos (BD). Pulsa Conectar e inicia sesión como cobranza@.'
    if (s.oauth_client_source === 'misconfigured_client_without_secret')
      return 'Falta Client Secret: guárdalo en Configuración → Informe de pagos o en Render (AUDITORIA_EMAIL_GOOGLE_CLIENT_SECRET).'
    if (s.oauth_client_source === 'missing_auditoria_and_informe_oauth')
      return 'Falta OAuth: configura Client ID + Secret en Informe de pagos y AUDITORIA_EMAIL_GOOGLE_CLIENT_ID en Render (cliente Web …bitt…).'
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
          <strong>OAuth efectivo:</strong>{' '}
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
              (secret activo …{String(s.oauth_client_secret_suffix)}, len{' '}
              {String(s.oauth_client_secret_len)})
            </>
          ) : null}
          {s.oauth_client_secret_source === 'informe_pagos_bd' ? (
            <span className="text-emerald-700">
              {' '}
              — secret desde Informe de pagos (BD)
            </span>
          ) : null}
          {s.oauth_env_secret_suffix &&
          s.oauth_client_secret_suffix &&
          s.oauth_env_secret_suffix !== s.oauth_client_secret_suffix ? (
            <span className="text-muted-foreground">
              {' '}
              (Render env …{String(s.oauth_env_secret_suffix)} ignorado; usa BD)
            </span>
          ) : null}
        </p>
        {s.informe_pagos_oauth_configured ? (
          <p>
            <strong>Informe de pagos (BD, itmaster):</strong>{' '}
            {String(s.informe_pagos_oauth_client_id_suffix || '—')}
            {s.informe_pagos_oauth_secret_suffix ? (
              <>
                {' '}
                (secret …{String(s.informe_pagos_oauth_secret_suffix)}, len{' '}
                {String(s.informe_pagos_oauth_secret_len)})
              </>
            ) : null}
            {s.informe_pagos_oauth_client_id_matches_auditoria_env === false ? (
              <span className="text-amber-700">
                {' '}
                — Client ID distinto al de Render; cobranza@ no puede reutilizar este
                secret
              </span>
            ) : null}
          </p>
        ) : (
          <p className="text-muted-foreground">
            <strong>Informe de pagos (BD):</strong> sin OAuth guardado — configura
            Client ID + Secret allí primero (itmaster).
          </p>
        )}
        <p>
          <strong>Mensajes / recibos en BD (tránsito):</strong>{' '}
          {String(s.mensajes_bd)} / {String(s.recibos_bd)}
        </p>
        {s.error ? (
          <p className="text-amber-700">Detalle: {String(s.error)}</p>
        ) : null}
        <p className="text-muted-foreground">
          itmaster@ e cobranza@ comparten el cliente OAuth Web cobranzas (…bitt…) pero
          tokens distintos. El secret se guarda en Informe de pagos; cobranza@ lo
          reutiliza automáticamente. Autoriza cobranza@ con su cuenta en Google.
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
