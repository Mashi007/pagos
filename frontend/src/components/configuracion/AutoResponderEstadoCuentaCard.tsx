import { useCallback, useEffect, useState } from 'react'

import { Copy, Loader2 } from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../ui/card'

import { Button } from '../ui/button'

import { Input } from '../ui/input'

import { Label } from '../ui/label'

import { toast } from 'sonner'

import {
  whatsappConfigService,
  type AutoresponderEstadoCuentaInstrucciones,
} from '../../services/notificacionService'

async function copiar(texto: string, etiqueta: string) {
  const t = (texto || '').trim()

  if (!t) {
    toast.error('No hay texto para copiar.')

    return
  }

  try {
    await navigator.clipboard.writeText(t)

    toast.success(`${etiqueta} copiado al portapapeles`)
  } catch {
    toast.error('No se pudo copiar. Copie manualmente.')
  }
}

export function AutoResponderEstadoCuentaCard() {
  const [cargando, setCargando] = useState(true)

  const [data, setData] =
    useState<AutoresponderEstadoCuentaInstrucciones | null>(null)

  const [refrescandoMonitor, setRefrescandoMonitor] = useState(false)

  const [probandoConexion, setProbandoConexion] = useState(false)

  const cargarInstrucciones = useCallback(async (soloMonitor: boolean) => {
    if (soloMonitor) setRefrescandoMonitor(true)
    else setCargando(true)

    try {
      const r =
        await whatsappConfigService.obtenerInstruccionesAutoresponderEstadoCuenta()

      setData(r)
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || 'No se pudieron cargar las instrucciones'

      toast.error(String(msg))

      if (!soloMonitor) setData(null)
    } finally {
      if (soloMonitor) setRefrescandoMonitor(false)
      else setCargando(false)
    }
  }, [])

  useEffect(() => {
    void cargarInstrucciones(false)
  }, [cargarInstrucciones])

  const handleProbarConexion = async () => {
    setProbandoConexion(true)

    try {
      const r = await whatsappConfigService.probarConexionAutoresponderWebhook()

      if (r.ok) {
        toast.success(
          r.latencia_ms != null
            ? `${r.mensaje} (${r.latencia_ms} ms)`
            : r.mensaje
        )
      } else {
        toast.error(r.mensaje)
      }

      await cargarInstrucciones(true)
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || 'Error al probar la conexión'

      toast.error(String(msg))
    } finally {
      setProbandoConexion(false)
    }
  }

  if (cargando) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Loader2 className="h-4 w-4 animate-spin" />
            AutoResponder → estado de cuenta
          </CardTitle>
        </CardHeader>
      </Card>
    )
  }

  if (!data) {
    return null
  }

  const envLines = Object.entries(data.variables_entorno_render || {}).map(
    ([k, v]) => `${k}=${v}`
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          AutoResponder (WhatsApp) → estado de cuenta
        </CardTitle>

        <CardDescription>
          Copie estos valores en la app <strong>AutoResponder</strong> en
          «Conectar con tu servidor web». El servidor solo acepta el contrato
          JSON oficial y responde con{' '}
          <code className="rounded bg-muted px-1">replies</code>. Documentación:{' '}
          <a
            href={data.documentacion_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary underline"
          >
            AutoResponder Web Server API (enlace externo)
          </a>
          .
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        <p className="text-sm text-muted-foreground">{data.alcance}</p>

        {data.monitor && (
          <div className="space-y-3 rounded-md border bg-muted/20 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="text-sm font-semibold">Monitor del webhook</h4>

              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={refrescandoMonitor}
                  onClick={() => cargarInstrucciones(true)}
                >
                  {refrescandoMonitor ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : null}
                  Actualizar contadores
                </Button>

                <Button
                  type="button"
                  size="sm"
                  disabled={probandoConexion || !data.basic_auth_configurado}
                  onClick={handleProbarConexion}
                >
                  {probandoConexion ? (
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                  ) : null}
                  Probar conexión (HTTP)
                </Button>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              {data.monitor.nota_contadores}
            </p>

            <div className="grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded border bg-background p-2">
                <div className="text-muted-foreground">Consultas recibidas</div>
                <div className="font-mono text-lg font-semibold">
                  {data.monitor.peticiones_total}
                </div>
              </div>

              <div className="rounded border bg-background p-2">
                <div className="text-muted-foreground">
                  Código solicitado (OK)
                </div>
                <div className="font-mono text-lg font-semibold text-green-700">
                  {data.monitor.solicitudes_codigo_exitosas}
                </div>
              </div>

              <div className="rounded border bg-background p-2">
                <div className="text-muted-foreground">
                  Pruebas (isTestMessage)
                </div>
                <div className="font-mono text-lg font-semibold">
                  {data.monitor.pruebas_recibidas_ok}
                </div>
              </div>

              <div className="rounded border bg-background p-2">
                <div className="text-muted-foreground">
                  Error resp. solicitar
                </div>
                <div className="font-mono text-lg font-semibold text-amber-800">
                  {data.monitor.solicitudes_codigo_respuesta_error}
                </div>
              </div>

              <div className="rounded border bg-background p-2">
                <div className="text-muted-foreground">Fallo auth</div>
                <div className="font-mono text-lg font-semibold text-red-700">
                  {data.monitor.fallos_autenticacion}
                </div>
              </div>

              <div className="rounded border bg-background p-2">
                <div className="text-muted-foreground">
                  JSON inválido / incompleto
                </div>
                <div className="font-mono text-lg font-semibold">
                  {data.monitor.cuerpo_json_invalido +
                    data.monitor.json_incompleto_validacion}
                </div>
              </div>
            </div>

            <div className="grid gap-2 text-xs sm:grid-cols-2">
              <div>
                <span className="text-muted-foreground">Última petición: </span>
                <span className="font-mono">
                  {data.monitor.ultima_peticion_utc || '-'}
                </span>
              </div>

              <div>
                <span className="text-muted-foreground">Último éxito: </span>
                <span className="font-mono">
                  {data.monitor.ultimo_exito_utc || '-'}
                </span>
              </div>
            </div>

            <div className="space-y-2">
              <h5 className="text-xs font-semibold text-muted-foreground">
                Últimas cédulas recibidas (API, máx. 5, enmascaradas)
              </h5>

              {(data.monitor.cedulas_consulta_recientes || []).length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  Aún no hay consultas con cédula en este proceso, o no ha
                  refrescado tras un mensaje real (no cuenta «Probar conexión»
                  con isTestMessage).
                </p>
              ) : (
                <ul className="space-y-1 rounded border bg-background p-2 text-xs">
                  {(data.monitor.cedulas_consulta_recientes || []).map(
                    (c, i) => (
                      <li
                        key={`${c.recibida_en_utc}-${i}`}
                        className="flex flex-wrap justify-between gap-2 font-mono"
                      >
                        <span>{c.cedula_mostrada}</span>
                        <span className="text-muted-foreground">
                          {c.recibida_en_utc}
                        </span>
                      </li>
                    )
                  )}
                </ul>
              )}
            </div>

            {data.monitor.ultimo_error_resumen ? (
              <div className="rounded border border-red-200 bg-red-50 p-2 text-xs text-red-900">
                <span className="font-medium">Último error: </span>
                {data.monitor.ultimo_error_resumen}
              </div>
            ) : null}
          </div>
        )}

        {!data.basic_auth_configurado && (
          <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            Defina en Render (servicio backend) las variables{' '}
            <code className="rounded bg-amber-100 px-1">
              AUTORESPONDER_WEBHOOK_USER
            </code>{' '}
            y{' '}
            <code className="rounded bg-amber-100 px-1">
              AUTORESPONDER_WEBHOOK_PASSWORD
            </code>{' '}
            y reinicie. Sin ambas, el webhook responde 503 y AutoResponder no
            podrá enviar códigos.
          </div>
        )}

        {data.portal_pdf_url ? (
          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Label htmlFor="ar-portal-pdf">
                Portal PDF (cliente: cédula + código)
              </Label>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() =>
                  copiar(data.portal_pdf_url || '', 'URL portal PDF')
                }
              >
                <Copy className="mr-1 h-3 w-3" />
                Copiar
              </Button>
            </div>

            <Input
              id="ar-portal-pdf"
              readOnly
              className="font-mono text-xs"
              value={data.portal_pdf_url}
            />

            <p className="text-xs text-muted-foreground">
              El webhook de AutoResponder no adjunta el PDF en el JSON; el
              cliente obtiene el archivo en esta página tras el correo con el
              código.
            </p>
          </div>
        ) : null}

        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Label htmlFor="ar-post-url">URL (POST)</Label>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => copiar(data.post_url, 'URL')}
            >
              <Copy className="mr-1 h-3 w-3" />
              Copiar URL
            </Button>
          </div>

          <Input
            id="ar-post-url"
            readOnly
            className="font-mono text-xs"
            value={data.post_url}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Label>Basic Auth - Usuario</Label>

              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() =>
                  copiar(data.basic_auth_usuario || '', 'Usuario Basic Auth')
                }
                disabled={!data.basic_auth_usuario}
              >
                <Copy className="mr-1 h-3 w-3" />
                Copiar
              </Button>
            </div>

            <Input
              readOnly
              className="font-mono text-xs"
              value={
                data.basic_auth_usuario ||
                '(defina AUTORESPONDER_WEBHOOK_USER en Render)'
              }
            />
          </div>

          <div className="space-y-2">
            <Label>Basic Auth - Contraseña</Label>

            <Input
              readOnly
              className="font-mono text-xs"
              value="•••••••• (solo en Render: AUTORESPONDER_WEBHOOK_PASSWORD)"
            />

            <p className="text-xs text-muted-foreground">
              No se muestra por seguridad. Debe coincidir con la contraseña que
              configure en la app AutoResponder y con la variable de entorno en
              Render.
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Label>Headers (opcional; recomendado Content-Type)</Label>
          </div>

          {data.headers_recomendados.map(h => (
            <div
              key={h.clave}
              className="flex flex-col gap-2 rounded-md border bg-muted/30 p-3 sm:flex-row sm:items-center"
            >
              <div className="grid flex-1 gap-2 sm:grid-cols-2">
                <Input readOnly className="font-mono text-xs" value={h.clave} />

                <Input readOnly className="font-mono text-xs" value={h.valor} />
              </div>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => copiar(`${h.clave}: ${h.valor}`, 'Cabecera')}
              >
                <Copy className="mr-1 h-3 w-3" />
                Copiar línea
              </Button>
            </div>
          ))}
        </div>

        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Label>Variables de entorno (referencia)</Label>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => copiar(envLines.join('\n'), 'Variables')}
            >
              <Copy className="mr-1 h-3 w-3" />
              Copiar nombres
            </Button>
          </div>

          <textarea
            readOnly
            className="min-h-[72px] w-full rounded-md border bg-muted/30 p-2 font-mono text-xs"
            value={envLines.join('\n')}
          />
        </div>

        <p className="text-sm text-muted-foreground">{data.sugerencia_regla}</p>
      </CardContent>
    </Card>
  )
}
