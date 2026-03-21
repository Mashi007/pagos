Ã¯Â»Â¿import { useState, useEffect } from 'react'
import { FileText, Save, Eye, EyeOff, CheckCircle, AlertCircle, Link, RefreshCw, Database, FileSpreadsheet, Mail } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { toast } from 'sonner'
import { apiClient } from '../../services/api'
import { env } from '../../config/env'
import { GmailPipelineCard } from './GmailPipelineCard'

export interface InformePagosConfigData {
  google_drive_folder_id?: string
  google_credentials_json?: string
  google_oauth_client_id?: string
  google_oauth_client_secret?: string
  google_oauth_refresh_token?: string
  google_sheets_id?: string
  sheet_tab_principal?: string
  destinatarios_informe_emails?: string
  horarios_envio?: Array<{ hour: number; minute: number }>
  ocr_keywords_numero_documento?: string
  ocr_keywords_nombre_banco?: string
  ocr_keywords_numero_deposito?: string
}

export function getBackendBaseUrl(): string {
  const base = (env.API_URL || (typeof window !== 'undefined' ? window.location.origin : '')).trim()
  return base ? base.replace(/\/$/, '') : (typeof window !== 'undefined' ? window.location.origin : '')
}

export interface EstadoConexion {
  conectado: boolean
  detalle: string
}

export interface EstadoConexiones {
  drive: EstadoConexion
  sheets: EstadoConexion
  ocr: EstadoConexion
  gmail?: EstadoConexion
}

export function InformePagosConfig() {
  const [config, setConfig] = useState<InformePagosConfigData>({})
  const [guardando, setGuardando] = useState(false)
  const [mostrarCredenciales, setMostrarCredenciales] = useState(false)
  const [mostrarOauthSecret, setMostrarOauthSecret] = useState(false)
  const [credencialesEdit, setCredencialesEdit] = useState('')
  const [oauthSecretEdit, setOauthSecretEdit] = useState('')
  const [estado, setEstado] = useState<EstadoConexiones | null>(null)
  const [verificandoEstado, setVerificandoEstado] = useState(false)
  const [redirectUri, setRedirectUri] = useState<string | null>(null)
  /** True solo cuando la ÃÂºltima respuesta del servidor incluyÃÂ³ Client ID (config guardada). Secuencia: guardar Ã¢ÂÂ luego conectar. */
  const [oauthGuardadoEnServidor, setOauthGuardadoEnServidor] = useState(false)

  useEffect(() => {
    cargarConfiguracion()
  }, [])

  useEffect(() => {
    apiClient.get<{ redirect_uri: string }>('/api/v1/configuracion/informe-pagos/redirect-uri')
      .then((r) => setRedirectUri(r?.redirect_uri ? null))
      .catch(() => setRedirectUri(null))
  }, [])

  const verificarEstadoConexiones = async () => {
    try {
      setVerificandoEstado(true)
      const data = await apiClient.get<EstadoConexiones>('/api/v1/configuracion/informe-pagos/estado')
      setEstado(data)
    } catch (error: unknown) {
      const msg = String((error as { message?: string })?.message ? '')
      const code = (error as { code?: string })?.code
      const isAborted = code === 'ERR_CANCELED' || /aborted|canceled/i.test(msg)
      if (isAborted) {
        // Usuario redirigido a Google u otra pestaÃÂ±a; no mostrar error
        return
      }
      console.error('Error verificando estado:', error)
      toast.error('No se pudo verificar el estado de Drive, Sheets, OCR y Gmail')
      setEstado(null)
    } finally {
      setVerificandoEstado(false)
    }
  }


  // Detectar vuelta de Google OAuth (callback redirige con ?google_oauth=ok|error y opcional reason=)
  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const result = params.get('google_oauth')
    const reason = params.get('reason')
    if (result === 'ok') {
      toast.success('Cuenta de Google conectada. Drive, Sheets, OCR y pipeline Gmail usarÃÂ¡n OAuth.')
      cargarConfiguracion()
      const url = new URL(window.location.href)
      url.searchParams.delete('google_oauth')
      window.history.replaceState({}, '', url.pathname + (url.search || '') + (url.hash || ''))
    } else if (result === 'error') {
      const mensajes: Record<string, string> = {
        no_code: 'Google no devolviÃÂ³ autorizaciÃÂ³n (cancelaste o hubo un error). Vuelve a intentar ÃÂ«Conectar con GoogleÃÂ».',
        state_invalid: 'SesiÃÂ³n de autorizaciÃÂ³n no encontrada. Cierra y vuelve a abrir esta pantalla, luego pulsa ÃÂ«Conectar con GoogleÃÂ» de nuevo.',
        state_expired: 'La ventana de autorizaciÃÂ³n tardÃÂ³ mÃÂ¡s de 10 minutos. Vuelve a hacer clic en ÃÂ«Conectar con GoogleÃÂ».',
        no_credentials: 'Faltan Client ID o Client Secret en la configuraciÃÂ³n de Informe pagos.',
        token_exchange: 'Error al intercambiar el cÃÂ³digo por tokens. En Google Cloud > Credenciales OAuth 2.0 aÃÂ±ada exactamente la ÃÂ«URI de redirecciÃÂ³n autorizadaÃÂ» que se muestra en esta pantalla (botÃÂ³n Copiar). Sin barra final.',
        no_refresh_token: 'Google no devolviÃÂ³ refresh_token. Vuelve a ÃÂ«Conectar con GoogleÃÂ» y autoriza de nuevo.',
        redirect_uri_mismatch: 'La URI de redirecciÃÂ³n no coincide. En Google Cloud Console Ã¢ÂÂ Credenciales Ã¢ÂÂ su cliente OAuth Ã¢ÂÂ URIs de redirecciÃÂ³n autorizados, aÃÂ±ada exactamente la URL que se muestra aquÃÂ­ (use Copiar). Debe ser https y sin barra final.',
      }
      const msg = reason && mensajes[reason] ? mensajes[reason] : 'No se pudo conectar con Google. Comprueba Client ID, Client Secret y la URL de redirecciÃÂ³n en Google Cloud.'
      toast.error(msg)
      const url = new URL(window.location.href)
      url.searchParams.delete('google_oauth')
      url.searchParams.delete('reason')
      window.history.replaceState({}, '', url.pathname + (url.search || '') + (url.hash || ''))
    }
  }, [])

  const cargarConfiguracion = async () => {
    try {
      const data = await apiClient.get<InformePagosConfigData>(
        '/api/v1/configuracion/informe-pagos/configuracion'
      )
      setConfig(data)
      setOauthGuardadoEnServidor(!!(data.google_oauth_client_id && String(data.google_oauth_client_id).trim()))
      if (data.google_credentials_json && data.google_credentials_json !== '***') {
        setCredencialesEdit(data.google_credentials_json)
      } else if (data.google_credentials_json === '***') {
        setCredencialesEdit('***')
      }
      if (data.google_oauth_client_secret && data.google_oauth_client_secret !== '***') {
        setOauthSecretEdit(data.google_oauth_client_secret)
      }
      await verificarEstadoConexiones()
    } catch (error) {
      console.error('Error cargando configuraciÃÂ³n informe pagos:', error)
      toast.error('Error cargando configuraciÃÂ³n')
    }
  }

  const handleChange = (campo: keyof InformePagosConfigData, valor: string | undefined) => {
    setConfig((prev) => ({ ...prev, [campo]: valor }))
  }

  const handleGuardar = async () => {
    try {
      setGuardando(true)
      const payload: InformePagosConfigData = {
        ...config,
        google_drive_folder_id: config.google_drive_folder_id || undefined,
        google_sheets_id: config.google_sheets_id || undefined,
        sheet_tab_principal: (config.sheet_tab_principal ? '').trim() || undefined,
        destinatarios_informe_emails: config.destinatarios_informe_emails || undefined,
      }
      // Enviar siempre el campo: vacÃÂ­o para limpiar (usar solo OAuth), o el valor si se editÃÂ³
      if (credencialesEdit === '***') {
        // No incluir para no sobrescribir el valor guardado
      } else {
        payload.google_credentials_json = (credencialesEdit ? '').trim()
      }
      if (oauthSecretEdit && oauthSecretEdit.trim() && oauthSecretEdit !== '***') {
        payload.google_oauth_client_secret = oauthSecretEdit.trim()
      }
      await apiClient.put('/api/v1/configuracion/informe-pagos/configuracion', payload)
      toast.success('ConfiguraciÃÂ³n informe pagos guardada')
      await cargarConfiguracion()
    } catch (error: any) {
      console.error('Error guardando:', error)
      toast.error(error?.response?.data?.detail || 'Error guardando configuraciÃÂ³n')
    } finally {
      setGuardando(false)
    }
  }

  const handleConectarGoogle = async () => {
    if (!oauthGuardadoEnServidor) {
      toast.error('Primero guarde la configuraciÃÂ³n (Client ID y Client Secret) con ÃÂ«Guardar configuraciÃÂ³nÃÂ»; despuÃÂ©s pulse ÃÂ«Conectar con GoogleÃÂ».')
      return
    }
    try {
      const res = await apiClient.get<{ redirect_url: string }>('/api/v1/configuracion/informe-pagos/google/authorize')
      const redirectUrl = res?.redirect_url
      if (redirectUrl) {
        window.location.href = redirectUrl
      } else {
        toast.error('No se pudo obtener la URL de autorizaciÃÂ³n de Google.')
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail ? err?.message ? 'Error al conectar con Google.'
      toast.error(typeof detail === 'string' ? detail : 'Error al conectar con Google.')
    }
  }

  const oauthConectado = !!(config.google_oauth_refresh_token && config.google_oauth_refresh_token !== '')

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-600" />
            Google (Drive, Sheets, OCR y Gmail) Ã¢ÂÂ varios servicios
          </CardTitle>
          <CardDescription>
            Una sola configuraciÃÂ³n para varios flujos: (1) <strong>Informe de pagos / cobranza WhatsApp</strong>: imÃÂ¡genes de papeletas Ã¢ÂÂ Drive Ã¢ÂÂ OCR (Vision) Ã¢ÂÂ digitalizaciÃÂ³n en Sheets Ã¢ÂÂ email 6:00, 13:00 y 16:30 (America/Caracas). (2) <strong>Pipeline Gmail</strong>: ÃÂ«Generar Excel desde GmailÃÂ» usa estas mismas credenciales para leer correos, Drive y Sheets. Todo se guarda aquÃÂ­ (no en Render).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Estado real de conexiones (Drive, Sheets, OCR) */}
          <div className="rounded-lg border bg-muted/40 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-foreground">Estado de conexiones</h4>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={verificarEstadoConexiones}
                disabled={verificandoEstado}
              >
                <RefreshCw className={`h-4 w-4 mr-1 ${verificandoEstado ? 'animate-spin' : ''}`} />
                {verificandoEstado ? 'VerificandoÃ¢ÂÂ¦' : 'Verificar ahora'}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Se comprueba con llamadas reales a Drive, Sheets, Vision (OCR) y Gmail. Las mismas credenciales sirven para informe de pagos y para el pipeline ÃÂ«Generar Excel desde GmailÃÂ». Sin indicios aquÃÂ­ no hay conexiÃÂ³n.
            </p>
            {/* Resumen: ConexiÃÂ³n OK / no OK */}
            {estado ? (
              <div
                className={`flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-semibold ${
                  estado.drive.conectado && estado.sheets.conectado && estado.ocr.conectado && (estado.gmail == null || estado.gmail.conectado)
                    ? 'bg-green-100 text-green-800 dark:bg-green-950/50 dark:text-green-300'
                    : 'bg-red-100 text-red-800 dark:bg-red-950/50 dark:text-red-300'
                }`}
              >
                {estado.drive.conectado && estado.sheets.conectado && estado.ocr.conectado && (estado.gmail == null || estado.gmail.conectado) ? (
                  <>
                    <CheckCircle className="h-5 w-5 shrink-0" />
                    ConexiÃÂ³n OK Ã¢ÂÂ Drive, Sheets, OCR y Gmail operativos.
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-5 w-5 shrink-0" />
                    ConexiÃÂ³n no OK Ã¢ÂÂ Revisa credenciales, ID de carpeta/hoja, comparte con la cuenta o vuelve a ÃÂ«Conectar con GoogleÃÂ».
                  </>
                )}
              </div>
            ) : verificandoEstado ? (
              <div className="flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium bg-muted text-muted-foreground">
                <RefreshCw className="h-5 w-5 shrink-0 animate-spin" />
                Verificando conexionesÃ¢ÂÂ¦
              </div>
            ) : (
              <div className="rounded-lg px-4 py-3 text-sm text-muted-foreground bg-muted/60">
                Sin verificar. Guarda la configuraciÃÂ³n y pulsa &quot;Verificar ahora&quot; para ver si la conexiÃÂ³n es OK.
              </div>
            )}
            <div className="grid gap-2 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
              {estado ? (
                <>
                  <div className={`flex items-start gap-2 rounded-md p-3 ${estado.drive.conectado ? 'bg-green-50 dark:bg-green-950/30' : 'bg-red-50 dark:bg-red-950/30'}`}>
                    <Database className={`h-5 w-5 shrink-0 mt-0.5 ${estado.drive.conectado ? 'text-green-600' : 'text-red-600'}`} />
                    <div className="min-w-0">
                      <span className="text-sm font-medium block">
                        Google Drive
                        <span className={`ml-2 text-xs font-normal ${estado.drive.conectado ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}`}>
                          {estado.drive.conectado ? 'Conectado' : 'No conectado'}
                        </span>
                      </span>
                      <span className="text-xs block mt-0.5">{estado.drive.detalle}</span>
                    </div>
                  </div>
                  <div className={`flex items-start gap-2 rounded-md p-3 ${estado.sheets.conectado ? 'bg-green-50 dark:bg-green-950/30' : 'bg-red-50 dark:bg-red-950/30'}`}>
                    <FileSpreadsheet className={`h-5 w-5 shrink-0 mt-0.5 ${estado.sheets.conectado ? 'text-green-600' : 'text-red-600'}`} />
                    <div className="min-w-0">
                      <span className="text-sm font-medium block">
                        Google Sheets
                        <span className={`ml-2 text-xs font-normal ${estado.sheets.conectado ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}`}>
                          {estado.sheets.conectado ? 'Conectado' : 'No conectado'}
                        </span>
                      </span>
                      <span className="text-xs block mt-0.5">{estado.sheets.detalle}</span>
                    </div>
                  </div>
                  <div className={`flex items-start gap-2 rounded-md p-3 ${estado.ocr.conectado ? 'bg-green-50 dark:bg-green-950/30' : 'bg-red-50 dark:bg-red-950/30'}`}>
                    <FileText className={`h-5 w-5 shrink-0 mt-0.5 ${estado.ocr.conectado ? 'text-green-600' : 'text-red-600'}`} />
                    <div className="min-w-0">
                      <span className="text-sm font-medium block">
                        OCR (Vision)
                        <span className={`ml-2 text-xs font-normal ${estado.ocr.conectado ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}`}>
                          {estado.ocr.conectado ? 'Conectado' : 'No conectado'}
                        </span>
                      </span>
                      <span className="text-xs block mt-0.5">{estado.ocr.detalle}</span>
                    </div>
                  </div>
                  <div className={`flex items-start gap-2 rounded-md p-3 ${estado.gmail?.conectado ? 'bg-green-50 dark:bg-green-950/30' : 'bg-red-50 dark:bg-red-950/30'}`}>
                    <Mail className={`h-5 w-5 shrink-0 mt-0.5 ${estado.gmail?.conectado ? 'text-green-600' : 'text-red-600'}`} />
                    <div className="min-w-0">
                      <span className="text-sm font-medium block">
                        Gmail
                        <span className={`ml-2 text-xs font-normal ${estado.gmail?.conectado ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}`}>
                          {estado.gmail?.conectado ? 'Conectado' : 'No conectado'}
                        </span>
                      </span>
                      <span className="text-xs block mt-0.5">{estado.gmail?.detalle ? 'Pipeline ÃÂ«Generar Excel desde GmailÃÂ».'}</span>
                    </div>
                  </div>
                </>
              ) : verificandoEstado ? (
                <p className="text-sm text-muted-foreground col-span-full">Verificando Drive, Sheets, OCR y GmailÃ¢ÂÂ¦</p>
              ) : (
                <p className="text-sm text-muted-foreground col-span-full">Guarda la configuraciÃÂ³n (carpeta, hoja, credenciales u OAuth) y pulsa &quot;Verificar ahora&quot; para comprobar las conexiones.</p>
              )}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium block mb-2">ID carpeta Google Drive</label>
            <Input
              placeholder="Ej: 1ABC..."
              value={config.google_drive_folder_id ? ''}
              onChange={(e) => handleChange('google_drive_folder_id', e.target.value)}
            />
            <p className="text-xs text-gray-500 mt-1">
              ID de la carpeta donde se guardan las imÃÂ¡genes de papeletas (desde la URL de la carpeta).
            </p>
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Credenciales Google (cuenta de servicio JSON)</label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setMostrarCredenciales(!mostrarCredenciales)}
              >
                {mostrarCredenciales ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
              <Textarea
                placeholder='{"type":"service_account",...}'
                value={config.google_credentials_json === '***' ? credencialesEdit : (credencialesEdit || (config.google_credentials_json ? ''))}
                onChange={(e) => setCredencialesEdit(e.target.value)}
                className="font-mono text-xs min-h-[120px]"
                rows={6}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              JSON de la cuenta de servicio (Drive + Sheets + Vision API). No se muestra despuÃÂ©s de guardar; usa *** para no sobrescribir.
            </p>
          </div>

          <div className="border-t pt-4 mt-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">OAuth (alternativa a cuenta de servicio)</h4>
            <p className="text-xs text-gray-500 mb-2">
              Credenciales para Drive, Sheets, Vision y Gmail. <strong>Orden obligatorio:</strong> primero guardar, luego conectar.
            </p>
            <ol className="text-xs text-gray-600 mb-3 list-decimal list-inside space-y-1.5">
              <li>Pegue <strong>Client ID</strong> y <strong>Client secret</strong> desde Google Cloud (Credenciales OAuth 2.0).</li>
              <li><strong>Guarde la configuraciÃÂ³n</strong> con el botÃÂ³n ÃÂ«Guardar configuraciÃÂ³nÃÂ» (al final de la pÃÂ¡gina). Sin este paso, Conectar con Google fallarÃÂ¡.</li>
              <li>En Google Cloud, en ese cliente OAuth, aÃÂ±ada en <strong>URIs de redirecciÃÂ³n autorizados</strong> exactamente la URL de abajo (sin barra final).</li>
              <li>Pulse <strong>Conectar con Google</strong> y autorice con la cuenta que usarÃÂ¡ Drive, Sheets y Gmail.</li>
            </ol>
            {redirectUri && (
              <div className="mb-3 p-3 bg-amber-50 border border-amber-200 rounded text-xs space-y-2">
                <span className="font-medium text-amber-800">En Google Cloud use esta URI de redirecciÃÂ³n (copie exactamente):</span>
                <div className="flex gap-2 items-start">
                  <code className="flex-1 min-w-0 p-1.5 bg-white border border-amber-200 rounded break-all font-mono text-amber-900" title={redirectUri}>{redirectUri}</code>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="shrink-0"
                    onClick={() => {
                      navigator.clipboard.writeText(redirectUri).then(() => toast.success('URI copiada')).catch(() => {})
                    }}
                  >
                    Copiar
                  </Button>
                </div>
                <p className="text-amber-800">
                  Si Google muestra <strong>ÃÂ«redirect_uri_mismatchÃÂ»</strong> o ÃÂ«Acceso bloqueadoÃÂ»: en Google Cloud Console Ã¢ÂÂ APIs y servicios Ã¢ÂÂ Credenciales Ã¢ÂÂ su cliente OAuth 2.0 Ã¢ÂÂ <strong>URIs de redirecciÃÂ³n autorizados</strong>, aÃÂ±ada la URL de arriba tal cual (https, sin barra final).
                </p>
              </div>
            )}
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium block mb-1">Client ID (OAuth)</label>
                <Input
                  placeholder="Ej: 336520671892-xxx.apps.googleusercontent.com"
                  value={config.google_oauth_client_id ? ''}
                  onChange={(e) => handleChange('google_oauth_client_id', e.target.value)}
                  maxLength={512}
                  className="font-mono text-sm"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Pega el ID completo desde Google Cloud (debe terminar en <code className="bg-gray-100 px-1 rounded">.apps.googleusercontent.com</code>).
                </p>
              </div>
              <div>
                <label className="text-sm font-medium block mb-1">Client Secret (OAuth)</label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setMostrarOauthSecret(!mostrarOauthSecret)}
                  >
                    {mostrarOauthSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                  <Input
                    type={mostrarOauthSecret ? 'text' : 'password'}
                    placeholder={config.google_oauth_client_secret === '***' ? 'Escribe aquÃÂ­ el nuevo secret para cambiarlo' : 'Client secret'}
                    value={config.google_oauth_client_secret === '***' ? oauthSecretEdit : (oauthSecretEdit || (config.google_oauth_client_secret ? ''))}
                    onChange={(e) => setOauthSecretEdit(e.target.value)}
                    maxLength={512}
                    className="flex-1 font-mono text-sm"
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  No se muestra despuÃÂ©s de guardar. Para aÃÂ±adir o cambiar el secret: escribe el valor en el campo y pulsa Guardar configuraciÃÂ³n.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {!oauthGuardadoEnServidor && (
                  <span className="text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded">
                    Primero guarde Client ID y Client Secret con ÃÂ«Guardar configuraciÃÂ³nÃÂ» para habilitar Conectar con Google.
                  </span>
                )}
                {oauthConectado && (
                  <span className="inline-flex items-center gap-1 text-sm text-green-700 bg-green-50 px-2 py-1 rounded">
                    <CheckCircle className="h-4 w-4" />
                    OAuth conectado (Drive, Sheets, OCR y pipeline Gmail usan esta cuenta)
                  </span>
                )}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleConectarGoogle}
                  disabled={!oauthGuardadoEnServidor}
                  className="inline-flex items-center gap-1"
                  title={!oauthGuardadoEnServidor ? 'Guarde primero la configuraciÃÂ³n (Client ID y Client Secret)' : undefined}
                >
                  <Link className="h-4 w-4" />
                  Conectar con Google (OAuth)
                </Button>
              </div>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium block mb-2">ID Google Sheet</label>
            <Input
              placeholder="Ej: 1ABC... (desde la URL de la hoja)"
              value={config.google_sheets_id ? ''}
              onChange={(e) => handleChange('google_sheets_id', e.target.value)}
            />
            <p className="text-xs text-gray-500 mt-1">
              ID que aparece en la URL: docs.google.com/spreadsheets/d/<strong>ESTE_ID</strong>/edit
            </p>
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">PestaÃÂ±a donde escribir (opcional)</label>
            <Input
              placeholder='Ej: Hoja 1 (vacÃÂ­o = pestaÃÂ±as 6am, 1pm, 4h30)'
              value={config.sheet_tab_principal ? ''}
              onChange={(e) => handleChange('sheet_tab_principal', e.target.value)}
            />
            <p className="text-xs text-gray-500 mt-1">
              Si la hoja se ve vacÃÂ­a: pon aquÃÂ­ <strong>Hoja 1</strong> para que las filas se escriban en la primera pestaÃÂ±a. Si lo dejas vacÃÂ­o, se usan pestaÃÂ±as por horario (6am, 1pm, 4h30).
            </p>
          </div>
          <div className="space-y-4">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">SinÃÂ³nimos para que el OCR aprenda</h4>
            <p className="text-xs text-gray-500">
              Palabras o frases que el OCR usa para localizar cada dato en el comprobante. Se rellenan las columnas <strong>C (InstituciÃÂ³n financiera)</strong> y <strong>D (Documento)</strong> de la hoja. Una por lÃÂ­nea o separadas por coma; si estÃÂ¡ vacÃÂ­o se usan valores por defecto.
            </p>
            <div>
              <label className="text-sm font-medium block mb-2">Columna C Ã¢ÂÂ InstituciÃÂ³n financiera</label>
              <Textarea
                placeholder="banco, instituciÃÂ³n financiera, entidad financiera, c.a., s.a...."
                value={config.ocr_keywords_nombre_banco ? ''}
                onChange={(e) => handleChange('ocr_keywords_nombre_banco', e.target.value)}
                className="min-h-[60px]"
                rows={2}
              />
              <p className="text-xs text-gray-500 mt-1">SinÃÂ³nimos con los que el OCR identifica el nombre del banco o instituciÃÂ³n en el comprobante.</p>
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">Columna D Ã¢ÂÂ Documento (nÃÂºmero de comprobante o recibo)</label>
              <Textarea
                placeholder="nÃÂ°, nÃÂº, numero de documento, numero de recibo, comprobante de venta, ci, ruc..."
                value={config.ocr_keywords_numero_documento ? ''}
                onChange={(e) => handleChange('ocr_keywords_numero_documento', e.target.value)}
                className="min-h-[80px]"
                rows={3}
              />
              <p className="text-xs text-gray-500 mt-1">Frases con las que el OCR ubica el nÃÂºmero de documento (ej. NÃÂ° 052-055-000112796). Si estÃÂ¡ vacÃÂ­o se usan unas por defecto.</p>
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">Columna D Ã¢ÂÂ Documento (referencia / nÃÂºmero de depÃÂ³sito)</label>
              <Textarea
                placeholder="comprobante, recibo, ref, referencia, depÃÂ³sito, ruc..."
                value={config.ocr_keywords_numero_deposito ? ''}
                onChange={(e) => handleChange('ocr_keywords_numero_deposito', e.target.value)}
                className="min-h-[60px]"
                rows={2}
              />
              <p className="text-xs text-gray-500 mt-1">Si la lÃÂ­nea contiene alguna de estas palabras, se busca un nÃÂºmero largo (10+ dÃÂ­gitos) como valor de respaldo para la columna Documento.</p>
            </div>
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Destinatarios del informe (emails)</label>
            <Input
              placeholder="email1@ejemplo.com, email2@ejemplo.com"
              value={config.destinatarios_informe_emails ? ''}
              onChange={(e) => handleChange('destinatarios_informe_emails', e.target.value)}
            />
            <p className="text-xs text-gray-500 mt-1">
              Emails que reciben el link a la hoja a las 6:00, 13:00 y 16:30 (America/Caracas).
            </p>
          </div>
          <Button onClick={handleGuardar} disabled={guardando}>
            {guardando ? (
              'Guardando...'
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Guardar configuraciÃÂ³n
              </>
            )}
          </Button>
        </CardContent>
      </Card>
      <GmailPipelineCard />
    </div>
  )
}
