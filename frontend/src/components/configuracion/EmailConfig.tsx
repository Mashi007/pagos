import { useState, useEffect, useMemo } from 'react'
import { Mail, Save, TestTube, CheckCircle, AlertCircle, Eye, EyeOff, Clock, XCircle, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { emailConfigService, notificacionService, type Notificacion } from '@/services/notificacionService'

interface EmailConfigData {
  smtp_host: string
  smtp_port: string
  smtp_user: string
  smtp_password?: string
  from_email: string
  from_name: string
  smtp_use_tls: string
  modo_pruebas?: string
  email_pruebas?: string
}

export function EmailConfig() {
  // Estado principal
  const [config, setConfig] = useState<EmailConfigData>({
    smtp_host: 'smtp.gmail.com',
    smtp_port: '587',
    smtp_user: '',
    smtp_password: '',
    from_email: '',
    from_name: 'RapiCredit',
    smtp_use_tls: 'true'
  })

  // Estado de UI
  const [mostrarPassword, setMostrarPassword] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [probando, setProbando] = useState(false)
  const [modoPruebas, setModoPruebas] = useState<string>('true')
  const [emailPruebas, setEmailPruebas] = useState('')
  const [emailPruebaDestino, setEmailPruebaDestino] = useState('')
  const [subjectPrueba, setSubjectPrueba] = useState('')
  const [mensajePrueba, setMensajePrueba] = useState('')
  const [errorValidacion, setErrorValidacion] = useState<string | null>(null)

  // Estado de vinculación
  const [vinculacionConfirmada, setVinculacionConfirmada] = useState<boolean>(false)
  const [mensajeVinculacion, setMensajeVinculacion] = useState<string | null>(null)
  const [requiereAppPassword, setRequiereAppPassword] = useState<boolean>(false)

  // Estado de envíos
  const [enviosRecientes, setEnviosRecientes] = useState<Notificacion[]>([])
  const [cargandoEnvios, setCargandoEnvios] = useState(false)
  const [resultadoPrueba, setResultadoPrueba] = useState<any>(null)

  // Cargar configuración al montar
  useEffect(() => {
    cargarConfiguracion()
    cargarEnviosRecientes()
  }, [])

  // Cargar configuración desde backend
  const cargarConfiguracion = async () => {
    try {
      const data = await emailConfigService.obtenerConfiguracionEmail()
      
      // Sincronizar from_email con smtp_user si está vacío
      if ((!data.from_email || data.from_email.trim() === '') && data.smtp_user?.trim()) {
        data.from_email = data.smtp_user
      }
      
      // Normalizar smtp_use_tls a string 'true' o 'false'
      if (data.smtp_use_tls === undefined || data.smtp_use_tls === null) {
        data.smtp_use_tls = 'true'
      } else if (typeof data.smtp_use_tls === 'boolean') {
        data.smtp_use_tls = data.smtp_use_tls ? 'true' : 'false'
      } else if (typeof data.smtp_use_tls === 'string') {
        data.smtp_use_tls = (data.smtp_use_tls.toLowerCase() === 'true' || data.smtp_use_tls === '1') ? 'true' : 'false'
      }
      
      setConfig(data)
      setModoPruebas(data.modo_pruebas || 'true')
      setEmailPruebas(data.email_pruebas || '')
    } catch (error) {
      console.error('Error cargando configuración:', error)
      toast.error('Error cargando configuración')
    }
  }

  // Cargar envíos recientes
  const cargarEnviosRecientes = async () => {
    setCargandoEnvios(true)
    try {
      const resultado = await notificacionService.listarNotificaciones(1, 10)
      setEnviosRecientes(resultado.items || [])
    } catch (error) {
      console.error('Error cargando envíos:', error)
    } finally {
      setCargandoEnvios(false)
    }
  }

  // Manejar cambios en campos
  const handleChange = (campo: keyof EmailConfigData, valor: string) => {
    setConfig(prev => {
      const nuevo = { ...prev, [campo]: valor }
      
      // Sincronizar from_email con smtp_user si está vacío o igual al anterior
      if (campo === 'smtp_user' && (!prev.from_email || prev.from_email === prev.smtp_user)) {
        nuevo.from_email = valor
      }
      
      return nuevo
    })
    
    if (errorValidacion) {
      setErrorValidacion(null)
    }
  }

  // Validar si se puede guardar
  const puedeGuardar = useMemo((): boolean => {
    // Campos obligatorios
    if (!config.smtp_host?.trim() || !config.smtp_port?.trim() || 
        !config.smtp_user?.trim() || !config.from_email?.trim()) {
      return false
    }
    
    // Puerto válido
    const puerto = parseInt(config.smtp_port)
    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {
      return false
    }
    
    // Si es Gmail, requiere contraseña y TLS para puerto 587
    if (config.smtp_host.toLowerCase().includes('gmail.com')) {
      if (!config.smtp_password?.trim()) {
        return false
      }
      if (puerto === 587 && config.smtp_use_tls !== 'true') {
        return false
      }
    }
    
    return true
  }, [config])

  // Obtener campos faltantes para mensaje
  const obtenerCamposFaltantes = (): string[] => {
    const faltantes: string[] = []
    if (!config.smtp_host?.trim()) faltantes.push('Servidor SMTP')
    if (!config.smtp_port?.trim()) faltantes.push('Puerto SMTP')
    if (!config.smtp_user?.trim()) faltantes.push('Email de Usuario')
    if (!config.from_email?.trim()) faltantes.push('Email del Remitente')
    
    const puerto = parseInt(config.smtp_port || '0')
    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {
      faltantes.push('Puerto SMTP válido')
    }
    
    if (config.smtp_host?.toLowerCase().includes('gmail.com')) {
      if (!config.smtp_password?.trim()) {
        faltantes.push('Contraseña de Aplicación')
      }
      if (puerto === 587 && config.smtp_use_tls !== 'true') {
        faltantes.push('TLS habilitado')
      }
    }
    
    return faltantes
  }

  // Validar configuración antes de guardar
  const validarConfiguracion = (): string | null => {
    const camposFaltantes = obtenerCamposFaltantes()
    if (camposFaltantes.length > 0) {
      return `Completa los siguientes campos: ${camposFaltantes.join(', ')}`
    }
    
    const puerto = parseInt(config.smtp_port)
    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {
      return 'El puerto SMTP debe ser un número válido entre 1 y 65535'
    }
    
    if (config.smtp_host.toLowerCase().includes('gmail.com')) {
      if (puerto === 587 && config.smtp_use_tls !== 'true') {
        return 'Para puerto 587, TLS debe estar habilitado (requerido por Gmail)'
      }
      if (!config.smtp_password?.trim()) {
        return 'Debes ingresar una contraseña para autenticarte con Gmail/Google Workspace'
      }
    }
    
    return null
  }

  // Guardar configuración
  const handleGuardar = async () => {
    const error = validarConfiguracion()
    if (error) {
      setErrorValidacion(error)
      toast.error(error)
      return
    }
    
    setErrorValidacion(null)
    
    try {
      setGuardando(true)
      
      // Limpiar espacios de la contraseña
      const passwordLimpia = config.smtp_password?.replace(/\s/g, '') || ''
      
      const configCompleta = {
        ...config,
        smtp_password: passwordLimpia,
        modo_pruebas: modoPruebas,
        email_pruebas: modoPruebas === 'true' ? emailPruebas : ''
      }
      
      const resultado = await emailConfigService.actualizarConfiguracionEmail(configCompleta)
      
      // Actualizar estado de vinculación
      setVinculacionConfirmada(resultado?.vinculacion_confirmada === true)
      setMensajeVinculacion(resultado?.mensaje_vinculacion || null)
      setRequiereAppPassword(resultado?.requiere_app_password === true)
      
      // Mostrar mensaje de éxito
      if (resultado?.vinculacion_confirmada) {
        toast.success(resultado.mensaje_vinculacion || '✅ Sistema vinculado correctamente con Google', { duration: 10000 })
      } else if (resultado?.requiere_app_password) {
        toast.warning(resultado.mensaje_vinculacion || '⚠️ Configuración guardada pero requiere App Password', { duration: 15000 })
      } else {
        toast.success('Configuración guardada exitosamente')
      }
      
      await cargarConfiguracion()
    } catch (error: any) {
      console.error('Error guardando configuración:', error)
      
      setVinculacionConfirmada(false)
      setMensajeVinculacion(null)
      setRequiereAppPassword(false)
      
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error guardando configuración'
      setErrorValidacion(mensajeError)
      toast.error(mensajeError, { duration: 10000 })
    } finally {
      setGuardando(false)
    }
  }

  // Probar envío de email
  const handleProbar = async () => {
    if (modoPruebas === 'true' && !emailPruebas?.trim()) {
      toast.error('En modo Pruebas, debes configurar un Email de Pruebas')
      return
    }
    
    if (emailPruebaDestino && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailPruebaDestino.trim())) {
      toast.error('Por favor ingresa un email válido')
      return
    }
    
    try {
      setProbando(true)
      setResultadoPrueba(null)
      
      const resultado = await emailConfigService.probarConfiguracionEmail(
        emailPruebaDestino.trim() || undefined,
        subjectPrueba.trim() || undefined,
        mensajePrueba.trim() || undefined
      )
      
      setResultadoPrueba(resultado)
      
      if (resultado.mensaje?.includes('enviado')) {
        toast.success(`Email de prueba enviado exitosamente a ${resultado.email_destino || 'tu correo'}`)
      } else {
        toast.error('Error enviando email de prueba')
      }
    } catch (error: any) {
      console.error('Error probando configuración:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error desconocido'
      toast.error(`Error probando configuración: ${mensajeError}`)
      setResultadoPrueba({ error: mensajeError })
    } finally {
      setProbando(false)
    }
  }

  const esGmail = config.smtp_host?.toLowerCase().includes('gmail.com')

  return (
    <div className="space-y-6">
      {/* Información inicial */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Mail className="h-5 w-5 text-blue-600" />
          <h3 className="font-semibold text-blue-900">Configuración de Email</h3>
        </div>
        <p className="text-sm text-blue-700">
          Configura el servidor SMTP para enviar notificaciones por email a los clientes.
        </p>
      </div>

      {/* Configuración SMTP */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-blue-600" />
            Configuración SMTP (Gmail / Google Workspace)
          </CardTitle>
          <CardDescription>
            Ingresa tus credenciales de Gmail o Google Workspace para enviar notificaciones
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Banners de estado */}
          {esGmail && (
            <>
              {vinculacionConfirmada && (
                <div className="bg-green-50 border-2 border-green-500 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <CheckCircle className="h-6 w-6 text-green-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="font-bold text-green-900 mb-1">
                        ✅ Sistema Vinculado Correctamente con Google/Google Workspace
                      </p>
                      <p className="text-sm text-green-800">
                        {mensajeVinculacion || 'Google aceptó tu configuración. El sistema está autorizado para enviar emails.'}
                      </p>
                    </div>
                  </div>
                </div>
              )}
              
              {requiereAppPassword && (
                <div className="bg-amber-50 border-2 border-amber-400 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-6 w-6 text-amber-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="font-bold text-amber-900 mb-2">
                        ⚠️ Configuración Guardada - Requiere App Password
                      </p>
                      <p className="text-sm text-amber-800 mb-3 whitespace-pre-line">
                        {mensajeVinculacion || 'Google requiere una Contraseña de Aplicación (App Password) para enviar emails.'}
                      </p>
                      <div className="bg-amber-100 border border-amber-300 rounded p-3">
                        <p className="text-xs font-semibold text-amber-900 mb-2">Pasos para corregir:</p>
                        <ol className="text-xs text-amber-800 space-y-1 list-decimal list-inside">
                          <li>Activa 2FA: <a href="https://myaccount.google.com/security" target="_blank" rel="noopener noreferrer" className="underline">https://myaccount.google.com/security</a></li>
                          <li>Genera App Password: <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" className="underline">https://myaccount.google.com/apppasswords</a></li>
                          <li>Actualiza el campo "Contraseña de Aplicación" con la nueva contraseña de 16 caracteres</li>
                        </ol>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {config.smtp_user && config.smtp_password && !vinculacionConfirmada && !requiereAppPassword && (
                <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Clock className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="font-semibold text-yellow-900 mb-1">⏳ Vinculación Pendiente</p>
                      <p className="text-sm text-yellow-800">
                        Guarda la configuración para verificar la conexión con Google. El sistema probará automáticamente si Google acepta tus credenciales.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {/* Advertencia de requisitos Gmail */}
          {esGmail && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="font-semibold text-amber-900 mb-1">Requisitos obligatorios para Gmail / Google Workspace:</p>
                  <ul className="text-sm text-amber-800 space-y-1 list-disc list-inside">
                    <li><strong>Autenticación de 2 factores (2FA) debe estar ACTIVADA</strong> en tu cuenta de Google</li>
                    <li>Debes usar una <strong>Contraseña de Aplicación</strong> (16 caracteres), NO tu contraseña normal</li>
                    <li>Puerto recomendado: <strong>587 con TLS</strong> (o 465 con SSL)</li>
                    <li>Soporta cuentas de <strong>Gmail (@gmail.com)</strong> y <strong>Google Workspace</strong> (dominios personalizados)</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Campos de configuración */}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium block mb-2">Servidor SMTP</label>
              <Input
                value={config.smtp_host}
                onChange={(e) => handleChange('smtp_host', e.target.value)}
                placeholder="smtp.gmail.com"
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">Puerto SMTP</label>
              <Input
                value={config.smtp_port}
                onChange={(e) => handleChange('smtp_port', e.target.value)}
                placeholder="587"
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium block mb-2">Email (Usuario Gmail / Google Workspace)</label>
              <Input
                type="email"
                value={config.smtp_user}
                onChange={(e) => handleChange('smtp_user', e.target.value)}
                placeholder="tu-email@gmail.com o usuario@tudominio.com"
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">Contraseña de Aplicación</label>
              <div className="relative">
                <Input
                  type={mostrarPassword ? 'text' : 'password'}
                  value={config.smtp_password || ''}
                  onChange={(e) => handleChange('smtp_password', e.target.value)}
                  placeholder="App Password de Gmail"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setMostrarPassword(!mostrarPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {mostrarPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                <strong>IMPORTANTE:</strong> Requiere 2FA activado. Genera una App Password (16 caracteres) en tu cuenta de Google. 
                <strong className="text-red-600"> NO uses tu contraseña normal.</strong> Funciona para Gmail y Google Workspace.
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium block mb-2">Email del Remitente</label>
              <Input
                type="email"
                value={config.from_email}
                onChange={(e) => handleChange('from_email', e.target.value)}
                placeholder="tu-email@gmail.com o usuario@tudominio.com"
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">Nombre del Remitente</label>
              <Input
                value={config.from_name}
                onChange={(e) => handleChange('from_name', e.target.value)}
                placeholder="RapiCredit"
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={config.smtp_use_tls === 'true'}
              onChange={(e) => handleChange('smtp_use_tls', e.target.checked ? 'true' : 'false')}
              className="rounded"
            />
            <label className="text-sm font-medium">Usar TLS (Recomendado para Gmail / Google Workspace)</label>
          </div>

          {/* Selector de ambiente */}
          <div className="border-t pt-4 mt-4">
            <div className="mb-4">
              <label className="text-sm font-medium block mb-2">Ambiente de Envío</label>
              <div className="flex gap-4">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="ambiente"
                    value="false"
                    checked={modoPruebas === 'false'}
                    onChange={(e) => setModoPruebas(e.target.value)}
                    className="rounded"
                  />
                  <span className="text-sm">Producción (Envíos reales a clientes)</span>
                </label>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="ambiente"
                    value="true"
                    checked={modoPruebas === 'true'}
                    onChange={(e) => setModoPruebas(e.target.value)}
                    className="rounded"
                  />
                  <span className="text-sm">Pruebas (Todos los emails a dirección de prueba)</span>
                </label>
              </div>
            </div>

            {modoPruebas === 'true' && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <label className="text-sm font-medium block mb-2">
                  Email de Pruebas <span className="text-gray-500 text-xs">(Opcional)</span>
                </label>
                <Input
                  type="email"
                  value={emailPruebas}
                  onChange={(e) => setEmailPruebas(e.target.value)}
                  placeholder="pruebas@ejemplo.com"
                  className="max-w-md"
                />
                <p className="text-xs text-gray-500 mt-1">
                  En modo pruebas, todos los emails se enviarán a esta dirección en lugar de a los clientes reales.
                </p>
              </div>
            )}
          </div>

          {/* Error de validación */}
          {errorValidacion && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="font-semibold text-red-900 mb-1">Error de validación:</p>
                  <p className="text-sm text-red-800 whitespace-pre-line">{errorValidacion}</p>
                </div>
              </div>
            </div>
          )}

          {/* Botones */}
          <div className="flex gap-2 pt-4 border-t mt-4">
            <Button
              onClick={handleGuardar}
              disabled={guardando || !puedeGuardar}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="h-4 w-4" />
              {guardando ? 'Guardando...' : 'Guardar Configuración'}
            </Button>
            {!puedeGuardar && !guardando && (
              <p className="text-xs text-amber-600 self-center font-medium">
                Completa: {obtenerCamposFaltantes().join(', ')}
              </p>
            )}
          </div>

          {/* Prueba de envío */}
          <div className="border-t pt-4 mt-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                <TestTube className="h-5 w-5" />
                Envío de Email de Prueba
              </h3>
              <p className="text-sm text-blue-700 mb-4">
                Envía un correo de prueba personalizado para verificar que la configuración SMTP funciona correctamente.
              </p>
              
              {modoPruebas === 'false' && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
                  <p className="text-sm text-green-800 font-semibold mb-1">✅ Modo Producción activo</p>
                  <p className="text-xs text-green-700">
                    El email de prueba se enviará <strong>REALMENTE</strong> al destinatario especificado.
                  </p>
                </div>
              )}
              
              {modoPruebas === 'true' && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                  <p className="text-sm text-yellow-800 font-semibold mb-1">⚠️ Modo Pruebas activo</p>
                  <p className="text-xs text-yellow-700">
                    El email se redirigirá a {emailPruebas || 'la dirección de pruebas configurada'}.
                  </p>
                </div>
              )}
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium block mb-2">
                    Email de Destino <span className="text-gray-500">(opcional)</span>
                  </label>
                  <Input
                    type="email"
                    value={emailPruebaDestino}
                    onChange={(e) => setEmailPruebaDestino(e.target.value)}
                    placeholder={config.smtp_user || "ejemplo@email.com"}
                    className="max-w-md"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium block mb-2">
                    Asunto <span className="text-gray-500">(opcional)</span>
                  </label>
                  <Input
                    type="text"
                    value={subjectPrueba}
                    onChange={(e) => setSubjectPrueba(e.target.value)}
                    placeholder="Prueba de configuración - RapiCredit"
                    className="max-w-md"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium block mb-2">
                    Mensaje de Prueba <span className="text-gray-500">(opcional)</span>
                  </label>
                  <Textarea
                    value={mensajePrueba}
                    onChange={(e) => setMensajePrueba(e.target.value)}
                    placeholder="Escribe aquí tu mensaje de prueba..."
                    rows={6}
                    className="max-w-md resize-y"
                  />
                </div>
                
                <Button
                  onClick={handleProbar}
                  disabled={probando || !config.smtp_user}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700"
                >
                  <TestTube className="h-4 w-4" />
                  {probando ? 'Enviando Email de Prueba...' : 'Enviar Email de Prueba'}
                </Button>
              </div>
            </div>
          </div>

          {/* Resultado de prueba */}
          {resultadoPrueba && (
            <div className={`p-4 rounded-lg border ${
              resultadoPrueba.mensaje?.includes('enviado') 
                ? 'bg-green-50 border-green-200' 
                : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-start gap-2">
                {resultadoPrueba.mensaje?.includes('enviado') ? (
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className={`font-medium ${
                    resultadoPrueba.mensaje?.includes('enviado') ? 'text-green-900' : 'text-red-900'
                  }`}>
                    {resultadoPrueba.mensaje}
                  </p>
                  {resultadoPrueba.error && (
                    <p className="text-sm text-red-600 mt-1">{resultadoPrueba.error}</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Envíos recientes */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-blue-600" />
            Verificación de Envíos Reales
          </CardTitle>
          <CardDescription>
            Historial reciente de correos enviados para verificar que el sistema está funcionando correctamente
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex justify-between items-center mb-4">
            <div className="text-sm text-gray-600">Últimos 10 envíos de notificaciones</div>
            <Button
              variant="outline"
              size="sm"
              onClick={cargarEnviosRecientes}
              disabled={cargandoEnvios}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${cargandoEnvios ? 'animate-spin' : ''}`} />
              Actualizar
            </Button>
          </div>

          {cargandoEnvios ? (
            <div className="text-center py-8 text-gray-500">Cargando envíos...</div>
          ) : enviosRecientes.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p>No hay envíos recientes</p>
            </div>
          ) : (
            <div className="space-y-3">
              {enviosRecientes.map((envio) => (
                <div key={envio.id} className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge className={
                          envio.estado === 'ENVIADA'
                            ? 'bg-green-100 text-green-800'
                            : envio.estado === 'FALLIDA'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }>
                          {envio.estado}
                        </Badge>
                        <span className="text-sm font-medium text-gray-700">
                          {envio.asunto || 'Sin asunto'}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 space-y-1">
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {envio.fecha_envio
                            ? new Date(envio.fecha_envio).toLocaleString('es-ES')
                            : envio.fecha_creacion
                            ? new Date(envio.fecha_creacion).toLocaleString('es-ES')
                            : 'Sin fecha'}
                        </div>
                        {envio.error_mensaje && (
                          <div className="text-xs text-red-600 flex items-start gap-1">
                            <XCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                            <span>{envio.error_mensaje}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

