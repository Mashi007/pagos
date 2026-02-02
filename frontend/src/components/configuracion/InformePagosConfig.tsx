import { useState, useEffect } from 'react'
import { FileText, Save, Eye, EyeOff, CheckCircle, AlertCircle, Link, RefreshCw, Database, FileSpreadsheet } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { toast } from 'sonner'
import { apiClient } from '../../services/api'
import { env } from '../../config/env'

export interface InformePagosConfigData {
  google_drive_folder_id?: string
  google_credentials_json?: string
  google_oauth_client_id?: string
  google_oauth_client_secret?: string
  google_oauth_refresh_token?: string
  google_sheets_id?: string
  destinatarios_informe_emails?: string
  horarios_envio?: Array<{ hour: number; minute: number }>
}

function getBackendBaseUrl(): string {
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

  useEffect(() => {
    cargarConfiguracion()
  }, [])

  const verificarEstadoConexiones = async () => {
    try {
      setVerificandoEstado(true)
      const data = await apiClient.get<EstadoConexiones>('/api/v1/configuracion/informe-pagos/estado')
      setEstado(data)
    } catch (error) {
      console.error('Error verificando estado:', error)
      toast.error('No se pudo verificar el estado de Drive, Sheets y OCR')
      setEstado(null)
    } finally {
      setVerificandoEstado(false)
    }
  }


  // Detectar vuelta de Google OAuth (callback redirige con ?google_oauth=ok|error)
  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.search)
    const result = params.get('google_oauth')
    if (result === 'ok') {
      toast.success('Cuenta de Google conectada correctamente. Drive y Sheets usarán OAuth.')
      cargarConfiguracion()
      const url = new URL(window.location.href)
      url.searchParams.delete('google_oauth')
      window.history.replaceState({}, '', url.pathname + (url.search || '') + (url.hash || ''))
    } else if (result === 'error') {
      toast.error('No se pudo conectar con Google. Comprueba Client ID, Client Secret y la URL de redirección en Google Cloud.')
      const url = new URL(window.location.href)
      url.searchParams.delete('google_oauth')
      window.history.replaceState({}, '', url.pathname + (url.search || '') + (url.hash || ''))
    }
  }, [])

  const cargarConfiguracion = async () => {
    try {
      const data = await apiClient.get<InformePagosConfigData>(
        '/api/v1/configuracion/informe-pagos/configuracion'
      )
      setConfig(data)
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
      console.error('Error cargando configuración informe pagos:', error)
      toast.error('Error cargando configuración')
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
        destinatarios_informe_emails: config.destinatarios_informe_emails || undefined,
      }
      // Enviar siempre el campo: vacío para limpiar (usar solo OAuth), o el valor si se editó
      if (credencialesEdit === '***') {
        // No incluir para no sobrescribir el valor guardado
      } else {
        payload.google_credentials_json = (credencialesEdit ?? '').trim()
      }
      if (oauthSecretEdit && oauthSecretEdit.trim() && oauthSecretEdit !== '***') {
        payload.google_oauth_client_secret = oauthSecretEdit.trim()
      }
      await apiClient.put('/api/v1/configuracion/informe-pagos/configuracion', payload)
      toast.success('Configuración informe pagos guardada')
      await cargarConfiguracion()
    } catch (error: any) {
      console.error('Error guardando:', error)
      toast.error(error?.response?.data?.detail || 'Error guardando configuración')
    } finally {
      setGuardando(false)
    }
  }

  const handleConectarGoogle = async () => {
    const clientId = (config.google_oauth_client_id ?? '').trim()
    if (!clientId) {
      toast.error('Guarda primero el Client ID (y Client Secret) y luego pulsa Conectar con Google.')
      return
    }
    try {
      const res = await apiClient.get<{ redirect_url: string }>('/api/v1/configuracion/informe-pagos/google/authorize')
      const redirectUrl = res?.redirect_url
      if (redirectUrl) {
        window.location.href = redirectUrl
      } else {
        toast.error('No se pudo obtener la URL de autorización de Google.')
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? err?.message ?? 'Error al conectar con Google.'
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
            Informe de pagos (Google Drive, Sheets, OCR)
          </CardTitle>
          <CardDescription>
            Configuración para el flujo de cobranza por WhatsApp: imágenes de papeletas se suben a Google Drive,
            se extraen datos con OCR (Google Vision) y se digitalizan en Google Sheets. A las 6:00, 13:00 y 16:30
            (America/Caracas) se envía un email con el link a la hoja.
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
                {verificandoEstado ? 'Verificando…' : 'Verificar ahora'}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Se comprueba con llamadas reales a Drive, Sheets y Vision (OCR). Sin indicios aquí no hay conexión.
            </p>
            {/* Resumen: Conexión OK / no OK */}
            {estado ? (
              <div
                className={`flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-semibold ${
                  estado.drive.conectado && estado.sheets.conectado && estado.ocr.conectado
                    ? 'bg-green-100 text-green-800 dark:bg-green-950/50 dark:text-green-300'
                    : 'bg-red-100 text-red-800 dark:bg-red-950/50 dark:text-red-300'
                }`}
              >
                {estado.drive.conectado && estado.sheets.conectado && estado.ocr.conectado ? (
                  <>
                    <CheckCircle className="h-5 w-5 shrink-0" />
                    Conexión OK — Drive, Sheets y OCR operativos.
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-5 w-5 shrink-0" />
                    Conexión no OK — Revisa credenciales, ID de carpeta/hoja y comparte con la cuenta.
                  </>
                )}
              </div>
            ) : verificandoEstado ? (
              <div className="flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium bg-muted text-muted-foreground">
                <RefreshCw className="h-5 w-5 shrink-0 animate-spin" />
                Verificando conexiones…
              </div>
            ) : (
              <div className="rounded-lg px-4 py-3 text-sm text-muted-foreground bg-muted/60">
                Sin verificar. Guarda la configuración y pulsa &quot;Verificar ahora&quot; para ver si la conexión es OK.
              </div>
            )}
            <div className="grid gap-2 sm:grid-cols-3">
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
                </>
              ) : verificandoEstado ? (
                <p className="text-sm text-muted-foreground col-span-3">Verificando Drive, Sheets y OCR…</p>
              ) : (
                <p className="text-sm text-muted-foreground col-span-3">Guarda la configuración (carpeta, hoja, credenciales u OAuth) y pulsa &quot;Verificar ahora&quot; para comprobar las conexiones.</p>
              )}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium block mb-2">ID carpeta Google Drive</label>
            <Input
              placeholder="Ej: 1ABC..."
              value={config.google_drive_folder_id ?? ''}
              onChange={(e) => handleChange('google_drive_folder_id', e.target.value)}
            />
            <p className="text-xs text-gray-500 mt-1">
              ID de la carpeta donde se guardan las imágenes de papeletas (desde la URL de la carpeta).
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
                value={config.google_credentials_json === '***' ? credencialesEdit : (credencialesEdit || (config.google_credentials_json ?? ''))}
                onChange={(e) => setCredencialesEdit(e.target.value)}
                className="font-mono text-xs min-h-[120px]"
                rows={6}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              JSON de la cuenta de servicio (Drive + Sheets + Vision API). No se muestra después de guardar; usa *** para no sobrescribir.
            </p>
          </div>

          <div className="border-t pt-4 mt-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">OAuth (alternativa a cuenta de servicio)</h4>
            <p className="text-xs text-gray-500 mb-3">
              Si tu organización no permite claves de cuenta de servicio, usa un cliente OAuth en Google Cloud.
              Añade la URL de redirección del backend a tu cliente OAuth (ver documentación).
            </p>
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium block mb-1">Client ID (OAuth)</label>
                <Input
                  placeholder="Ej: 123456789-xxx.apps.googleusercontent.com"
                  value={config.google_oauth_client_id ?? ''}
                  onChange={(e) => handleChange('google_oauth_client_id', e.target.value)}
                />
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
                    placeholder={config.google_oauth_client_secret === '***' ? 'Escribe aquí el nuevo secret para cambiarlo' : 'Client secret'}
                    value={config.google_oauth_client_secret === '***' ? oauthSecretEdit : (oauthSecretEdit || (config.google_oauth_client_secret ?? ''))}
                    onChange={(e) => setOauthSecretEdit(e.target.value)}
                    className="flex-1"
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  No se muestra después de guardar. Para añadir o cambiar el secret: escribe el valor en el campo y pulsa Guardar configuración.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {oauthConectado && (
                  <span className="inline-flex items-center gap-1 text-sm text-green-700 bg-green-50 px-2 py-1 rounded">
                    <CheckCircle className="h-4 w-4" />
                    OAuth conectado (Drive y Sheets usarán esta cuenta)
                  </span>
                )}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleConectarGoogle}
                  className="inline-flex items-center gap-1"
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
              value={config.google_sheets_id ?? ''}
              onChange={(e) => handleChange('google_sheets_id', e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Destinatarios del informe (emails)</label>
            <Input
              placeholder="email1@ejemplo.com, email2@ejemplo.com"
              value={config.destinatarios_informe_emails ?? ''}
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
                Guardar configuración
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
