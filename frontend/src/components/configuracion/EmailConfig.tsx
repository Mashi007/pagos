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
  const [config, setConfig] = useState<EmailConfigData>({
    smtp_host: 'smtp.gmail.com',
    smtp_port: '587',
    smtp_user: '',
    smtp_password: '',
    from_email: '',
    from_name: 'RapiCredit',
    smtp_use_tls: 'true'
  })
  
  const [mostrarPassword, setMostrarPassword] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [probando, setProbando] = useState(false)
  const [resultadoPrueba, setResultadoPrueba] = useState<any>(null)
  const [modoPruebas, setModoPruebas] = useState<string>('true') // Por defecto: Pruebas (más seguro)
  const [emailPruebas, setEmailPruebas] = useState('')
  const [emailPruebaDestino, setEmailPruebaDestino] = useState('') // Email para prueba de envío
  const [subjectPrueba, setSubjectPrueba] = useState('') // Subject para prueba de envío
  const [mensajePrueba, setMensajePrueba] = useState('') // Mensaje para prueba de envío
  const [enviosRecientes, setEnviosRecientes] = useState<Notificacion[]>([])
  const [cargandoEnvios, setCargandoEnvios] = useState(false)
  const [errorValidacion, setErrorValidacion] = useState<string | null>(null)
  const [vinculacionConfirmada, setVinculacionConfirmada] = useState<boolean>(false)
  const [mensajeVinculacion, setMensajeVinculacion] = useState<string | null>(null)
  const [requiereAppPassword, setRequiereAppPassword] = useState<boolean>(false)

  useEffect(() => {
    cargarConfiguracion()
    cargarEnviosRecientes()
  }, [])

  const cargarConfiguracion = async () => {
    try {
      const data = await emailConfigService.obtenerConfiguracionEmail()
      
      // ESCENARIO 1: Si from_email está vacío pero smtp_user tiene valor, usar smtp_user como from_email por defecto
      // Esto asegura que en la primera carga, ambos campos tengan el mismo valor si from_email no está configurado
      if ((!data.from_email || data.from_email.trim() === '') && data.smtp_user && data.smtp_user.trim() !== '') {
        data.from_email = data.smtp_user
      }
      
      setConfig(data)
      setModoPruebas(data.modo_pruebas || 'true') // Por defecto: Pruebas si no hay configuración
      setEmailPruebas(data.email_pruebas || '')
    } catch (error) {
      console.error('Error cargando configuración de email:', error)
      toast.error('Error cargando configuración')
    }
  }

  const cargarEnviosRecientes = async () => {
    setCargandoEnvios(true)
    try {
      const resultado = await notificacionService.listarNotificaciones(1, 10)
      setEnviosRecientes(resultado.items || [])
    } catch (error) {
      console.error('Error cargando envíos recientes:', error)
    } finally {
      setCargandoEnvios(false)
    }
  }

  const handleChange = (campo: keyof EmailConfigData, valor: string) => {
    setConfig(prev => {
      const nuevoConfig = { ...prev, [campo]: valor }
      
      // ESCENARIO 1: Si se cambia smtp_user y from_email está vacío o es igual al valor anterior de smtp_user,
      // actualizar from_email automáticamente con el nuevo valor
      if (campo === 'smtp_user') {
        const fromEmailVacio = !prev.from_email || prev.from_email.trim() === ''
        const fromEmailIgualAlAnterior = prev.from_email === prev.smtp_user
        
        // Si from_email está vacío O si from_email es igual al smtp_user anterior (estaba sincronizado),
        // entonces sincronizar con el nuevo smtp_user
        if (fromEmailVacio || fromEmailIgualAlAnterior) {
          nuevoConfig.from_email = valor
        }
      }
      
      return nuevoConfig
    })
    
    // Limpiar error de validación cuando el usuario modifica los campos
    if (errorValidacion) {
      setErrorValidacion(null)
    }
  }

  // Función para obtener mensaje de campos faltantes (para mostrar al usuario)
  const obtenerCamposFaltantes = (): string[] => {
    const camposFaltantes: string[] = []
    if (!config.smtp_host) camposFaltantes.push('Servidor SMTP')
    if (!config.smtp_port) camposFaltantes.push('Puerto SMTP')
    if (!config.smtp_user) camposFaltantes.push('Email de Usuario')
    if (!config.from_email) camposFaltantes.push('Email del Remitente')
    
    const puerto = parseInt(config.smtp_port || '0')
    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {
      camposFaltantes.push('Puerto SMTP válido')
    }
    
    if (config.smtp_host?.toLowerCase().includes('gmail.com')) {
      if (!config.smtp_password || config.smtp_password.trim().length === 0) {
        camposFaltantes.push('Contraseña de Aplicación')
      }
      if (puerto === 587 && config.smtp_use_tls !== 'true') {
        camposFaltantes.push('TLS habilitado (requerido para puerto 587)')
      }
    }
    
    return camposFaltantes
  }

  // Función para determinar si el botón debe estar habilitado
  // NOTA: Solo valida campos OBLIGATORIOS para guardar. El email de pruebas NO es obligatorio.
  // Usa useMemo para evitar recalcular en cada render
  const puedeGuardar = useMemo((): boolean => {
    // Solo loguear en modo debug (desarrollo)
    if (process.env.NODE_ENV === 'development') {
      console.debug('🔍 [EmailConfig] Verificando si puede guardar:', {
        smtp_host: config.smtp_host,
        smtp_port: config.smtp_port,
        smtp_user: config.smtp_user,
        from_email: config.from_email,
        tiene_password: !!config.smtp_password,
        password_length: config.smtp_password?.length || 0,
        smtp_use_tls: config.smtp_use_tls,
        es_gmail: config.smtp_host?.toLowerCase().includes('gmail.com')
      })
    }
    
    // Campos obligatorios básicos
    if (!config.smtp_host || !config.smtp_port || !config.smtp_user || !config.from_email) {
      if (process.env.NODE_ENV === 'development') {
        console.debug('❌ [EmailConfig] Faltan campos obligatorios básicos')
      }
      return false
    }
    
    // Validar puerto numérico
    const puerto = parseInt(config.smtp_port)
    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {
      if (process.env.NODE_ENV === 'development') {
        console.debug('❌ [EmailConfig] Puerto inválido:', config.smtp_port)
      }
      return false
    }
    
    // Si es Gmail/Google Workspace, requiere contraseña
    if (config.smtp_host.toLowerCase().includes('gmail.com')) {
      if (!config.smtp_password || config.smtp_password.trim().length === 0) {
        if (process.env.NODE_ENV === 'development') {
          console.debug('❌ [EmailConfig] Gmail requiere contraseña')
        }
        return false
      }
      
      // Validar TLS para puerto 587
      if (puerto === 587 && config.smtp_use_tls !== 'true') {
        if (process.env.NODE_ENV === 'development') {
          console.debug('❌ [EmailConfig] Puerto 587 requiere TLS')
        }
        return false
      }
    }
    
    // NOTA: NO validamos el email de pruebas aquí porque NO es obligatorio para guardar
    // El email de pruebas solo se valida cuando se intenta enviar un email de prueba
    
    if (process.env.NODE_ENV === 'development') {
      console.debug('✅ [EmailConfig] Puede guardar - todos los campos obligatorios están completos')
    }
    return true
  }, [config.smtp_host, config.smtp_port, config.smtp_user, config.from_email, config.smtp_password, config.smtp_use_tls])

  const validarConfiguracionGmail = (): string | null => {
    console.log('🔍 [EmailConfig] Validando configuración:', {
      smtp_host: config.smtp_host,
      smtp_port: config.smtp_port,
      smtp_user: config.smtp_user,
      from_email: config.from_email,
      tiene_password: !!config.smtp_password,
      password_length: config.smtp_password?.length || 0,
      modo_pruebas: modoPruebas,
      email_pruebas: emailPruebas
    })
    
    // Validaciones generales primero - solo campos obligatorios
    if (!config.smtp_host || !config.smtp_port || !config.smtp_user || !config.from_email) {
      const camposFaltantes: string[] = []
      if (!config.smtp_host) camposFaltantes.push('Servidor SMTP')
      if (!config.smtp_port) camposFaltantes.push('Puerto SMTP')
      if (!config.smtp_user) camposFaltantes.push('Email de Usuario')
      if (!config.from_email) camposFaltantes.push('Email del Remitente')
      
      console.warn('⚠️ [EmailConfig] Campos faltantes:', camposFaltantes)
      return `Por favor completa todos los campos requeridos. Faltan: ${camposFaltantes.join(', ')}`
    }
    
    // NOTA: El email de pruebas NO es obligatorio para guardar la configuración
    // Solo se validará cuando se intente enviar un email de prueba en modo pruebas
    // Esto permite guardar la configuración SMTP primero y luego configurar las pruebas
    
    // Validar formato de email de pruebas solo si está configurado (opcional)
    if (emailPruebas && emailPruebas.trim().length > 0) {
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!emailPattern.test(emailPruebas.trim())) {
        console.warn('⚠️ [EmailConfig] Email de pruebas con formato inválido')
        return 'El Email de Pruebas debe tener un formato válido (ejemplo: pruebas@ejemplo.com).'
      }
    }
    
    // Validar puerto numérico válido
    const puerto = parseInt(config.smtp_port)
    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {
      console.warn('⚠️ [EmailConfig] Puerto inválido:', config.smtp_port)
      return 'El puerto SMTP debe ser un número válido entre 1 y 65535.'
    }
    
    // Validar que si es Gmail/Google Workspace, tenga configuración básica correcta
    if (config.smtp_host.toLowerCase().includes('gmail.com')) {
      // Validar puerto recomendado para Gmail/Google Workspace
      if (puerto !== 587 && puerto !== 465) {
        console.warn('⚠️ [EmailConfig] Puerto no estándar para Gmail:', puerto)
        // Solo advertir, no bloquear - permitir otros puertos
      }
      
      // Validar que TLS esté habilitado para puerto 587
      if (puerto === 587 && config.smtp_use_tls !== 'true') {
        console.warn('⚠️ [EmailConfig] TLS no habilitado para puerto 587')
        return 'Para puerto 587, TLS debe estar habilitado (requerido por Gmail/Google Workspace).'
      }
      
      // Validar que tenga contraseña (pero no validar longitud estricta)
      // La validación real se hará en el backend al intentar enviar emails
      if (!config.smtp_password || config.smtp_password.trim().length === 0) {
        console.warn('⚠️ [EmailConfig] Contraseña faltante')
        return 'Debes ingresar una contraseña para autenticarte con Gmail/Google Workspace.'
      }
      
      // NOTA: Ya no validamos la longitud de la contraseña estrictamente
      // El backend probará la conexión y mostrará el error real si la contraseña no es válida
      // Esto permite usar OAuth2 tokens u otros métodos de autenticación si están disponibles
    }
    
    console.log('✅ [EmailConfig] Validación exitosa')
    return null
  }

  const handleGuardar = async () => {
    console.log('🔄 [EmailConfig] handleGuardar llamado', { config, modoPruebas, emailPruebas })
    
    // Validar configuración antes de guardar
    const errorValidacion = validarConfiguracionGmail()
    if (errorValidacion) {
      console.warn('⚠️ [EmailConfig] Validación falló:', errorValidacion)
      setErrorValidacion(errorValidacion)
      toast.error(errorValidacion, {
        duration: 8000, // Mostrar por más tiempo
      })
      return
    }
    
    // Limpiar error de validación si pasa
    setErrorValidacion(null)
    
    try {
      setGuardando(true)
      console.log('💾 [EmailConfig] Iniciando guardado de configuración...')
      
      // Limpiar espacios de la contraseña de aplicación (Gmail puede mostrarla con espacios)
      const passwordLimpia = config.smtp_password ? config.smtp_password.replace(/\s/g, '') : ''
      
      const configCompleta = {
        ...config,
        smtp_password: passwordLimpia,
        modo_pruebas: modoPruebas,
        email_pruebas: modoPruebas === 'true' ? emailPruebas : ''
      }
      
      console.log('📤 [EmailConfig] Enviando configuración al backend:', {
        ...configCompleta,
        smtp_password: configCompleta.smtp_password ? '***' : '(vacío)'
      })
      
      const resultado = await emailConfigService.actualizarConfiguracionEmail(configCompleta)
      console.log('✅ [EmailConfig] Configuración guardada exitosamente:', resultado)
      
      // Guardar estado de vinculación para mostrar banner permanente
      const confirmada = resultado?.vinculacion_confirmada === true
      const requiereAppPasswordFlag = resultado?.requiere_app_password === true
      setVinculacionConfirmada(confirmada)
      setMensajeVinculacion(resultado?.mensaje_vinculacion || null)
      setRequiereAppPassword(requiereAppPasswordFlag)
      
      // Mostrar mensaje de éxito con información de vinculación si está disponible
      if (confirmada) {
        toast.success(
          resultado.mensaje_vinculacion || '✅ Sistema vinculado correctamente con Google/Google Workspace',
          {
            duration: 10000, // Mostrar por más tiempo para que el usuario vea la confirmación
          }
        )
      } else if (requiereAppPasswordFlag) {
        // Mostrar advertencia si requiere App Password
        toast.warning(
          resultado.mensaje_vinculacion || '⚠️ Configuración guardada pero requiere App Password',
          {
            duration: 15000, // Mostrar por más tiempo para que el usuario vea las instrucciones
          }
        )
      } else {
        toast.success('Configuración de email guardada exitosamente')
      }
      
      await cargarConfiguracion()
    } catch (error: any) {
      console.error('❌ [EmailConfig] Error guardando configuración:', error)
      console.error('❌ [EmailConfig] Detalles del error:', {
        message: error?.message,
        response: error?.response?.data,
        status: error?.response?.status,
        statusText: error?.response?.statusText
      })
      
      // Limpiar estado de vinculación si hay error (Google rechazó la conexión)
      setVinculacionConfirmada(false)
      setMensajeVinculacion(null)
      setRequiereAppPassword(false)
      
      // Extraer mensaje de error específico del backend
      let mensajeError = 'Error guardando configuración'
      if (error?.response?.data?.detail) {
        mensajeError = error.response.data.detail
      } else if (error?.response?.data?.message) {
        mensajeError = error.response.data.message
      } else if (error?.message) {
        mensajeError = error.message
      }
      
      // Mostrar error con formato mejorado (preservar saltos de línea si existen)
      toast.error(mensajeError, {
        duration: 10000, // Mostrar por más tiempo si es un error largo
      })
      
      // También mostrar el error en el área de error visual
      setErrorValidacion(mensajeError)
    } finally {
      setGuardando(false)
    }
  }

  const handleProbar = async () => {
    try {
      setProbando(true)
      setResultadoPrueba(null)
      
      // Validar que si está en modo pruebas, tenga email de pruebas configurado
      if (modoPruebas === 'true' && (!emailPruebas || emailPruebas.trim().length === 0)) {
        toast.error('En modo Pruebas, debes configurar un Email de Pruebas antes de enviar un email de prueba.')
        setProbando(false)
        return
      }
      
      // Validar formato de email de pruebas si está configurado
      if (emailPruebas && emailPruebas.trim().length > 0) {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (!emailPattern.test(emailPruebas.trim())) {
          toast.error('El Email de Pruebas tiene un formato inválido. Por favor, corrígelo antes de enviar.')
          setProbando(false)
          return
        }
      }
      
      // Validar email de destino si se proporcionó
      if (emailPruebaDestino && emailPruebaDestino.trim()) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
        if (!emailRegex.test(emailPruebaDestino.trim())) {
          toast.error('Por favor ingresa un email válido')
          setProbando(false)
          return
        }
      }
      
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

  return (
    <div className="space-y-6">
      {/* Información */}
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
          {/* Banner de Estado de Vinculación con Google */}
          {config.smtp_host.toLowerCase().includes('gmail.com') && (
            <>
              {vinculacionConfirmada ? (
                <div className="bg-green-50 border-2 border-green-500 rounded-lg p-4 shadow-sm">
                  <div className="flex items-start gap-3">
                    <CheckCircle className="h-6 w-6 text-green-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="font-bold text-green-900 mb-1 text-base">
                        ✅ Sistema Vinculado Correctamente con Google/Google Workspace
                      </p>
                      <p className="text-sm text-green-800 mb-2">
                        {mensajeVinculacion || 'Google aceptó tu configuración. El sistema está autorizado para enviar emails.'}
                      </p>
                      <p className="text-xs text-green-700 font-medium">
                        📧 Puedes enviar notificaciones por email a tus clientes
                      </p>
                    </div>
                  </div>
                </div>
              ) : requiereAppPassword ? (
                <div className="bg-amber-50 border-2 border-amber-400 rounded-lg p-4 shadow-sm">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-6 w-6 text-amber-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="font-bold text-amber-900 mb-2 text-base">
                        ⚠️ Configuración Guardada - Requiere App Password
                      </p>
                      <p className="text-sm text-amber-800 mb-3 whitespace-pre-line">
                        {mensajeVinculacion || 'Google requiere una Contraseña de Aplicación (App Password) para enviar emails.'}
                      </p>
                      <div className="bg-amber-100 border border-amber-300 rounded p-3 mt-2">
                        <p className="text-xs font-semibold text-amber-900 mb-2">Pasos para corregir:</p>
                        <ol className="text-xs text-amber-800 space-y-1 list-decimal list-inside">
                          <li>Activa 2FA en tu cuenta de Google: <a href="https://myaccount.google.com/security" target="_blank" rel="noopener noreferrer" className="underline font-medium">https://myaccount.google.com/security</a></li>
                          <li>Genera una App Password: <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" className="underline font-medium">https://myaccount.google.com/apppasswords</a></li>
                          <li>Actualiza el campo "Contraseña de Aplicación" con la nueva contraseña de 16 caracteres</li>
                        </ol>
                      </div>
                    </div>
                  </div>
                </div>
              ) : config.smtp_user && config.smtp_password ? (
                <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Clock className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="font-semibold text-yellow-900 mb-1">
                        ⏳ Vinculación Pendiente
                      </p>
                      <p className="text-sm text-yellow-800">
                        Guarda la configuración para verificar la conexión con Google. El sistema probará automáticamente si Google acepta tus credenciales.
                      </p>
                    </div>
                  </div>
                </div>
              ) : null}
            </>
          )}

          {/* Advertencia sobre requisitos de Gmail/Google Workspace */}
          {config.smtp_host.toLowerCase().includes('gmail.com') && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="font-semibold text-amber-900 mb-1">Requisitos obligatorios para Gmail / Google Workspace:</p>
                  <ul className="text-sm text-amber-800 space-y-1 list-disc list-inside">
                    <li><strong>Autenticación de 2 factores (2FA) debe estar ACTIVADA</strong> en tu cuenta de Google</li>
                    <li>Debes usar una <strong>Contraseña de Aplicación</strong> (16 caracteres), NO tu contraseña normal</li>
                    <li>Puerto recomendado: <strong>587 con TLS</strong> (o 465 con SSL)</li>
                    <li>Soporta cuentas de <strong>Gmail (@gmail.com)</strong> y <strong>Google Workspace</strong> (dominios personalizados como @rapicreditca.com)</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
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

          {/* Selector de Ambiente */}
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
                <div className="mb-3">
                  <label className="text-sm font-medium block mb-2">
                    Email de Pruebas <span className="text-gray-500 text-xs">(Opcional - Requerido solo para enviar emails de prueba)</span>
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
                    Puedes guardar la configuración SMTP sin este campo y configurarlo después.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Mensaje de error de validación */}
          {errorValidacion && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mt-4">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="font-semibold text-red-900 mb-1">Error de validación:</p>
                  <p className="text-sm text-red-800 whitespace-pre-line">{errorValidacion}</p>
                </div>
              </div>
            </div>
          )}

          {/* Botones de Acción */}
          <div className="flex gap-2 pt-4 border-t mt-4">
            <Button
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                
                // Si el botón está deshabilitado, mostrar mensaje específico
                if (!puedeGuardar && !guardando) {
                  const camposFaltantes = obtenerCamposFaltantes()
                  const mensaje = camposFaltantes.length > 0 
                    ? `Completa los siguientes campos: ${camposFaltantes.join(', ')}`
                    : 'Completa todos los campos obligatorios para guardar la configuración'
                  
                  console.warn('⚠️ [EmailConfig] Intento de guardar con campos incompletos:', camposFaltantes)
                  setErrorValidacion(mensaje)
                  toast.error(mensaje, {
                    duration: 6000,
                  })
                  return
                }
                
                handleGuardar()
              }}
              disabled={guardando || !puedeGuardar}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              type="button"
            >
              <Save className="h-4 w-4" />
              {guardando ? 'Guardando...' : 'Guardar Configuración'}
            </Button>
            {!puedeGuardar && !guardando && (() => {
              const camposFaltantes = obtenerCamposFaltantes()
              return (
                <p className="text-xs text-amber-600 self-center font-medium">
                  {camposFaltantes.length > 0 
                    ? `Completa: ${camposFaltantes.join(', ')}`
                    : 'Completa los campos obligatorios para habilitar el botón'
                  }
                </p>
              )
            })()}
          </div>

          {/* Ambiente de Prueba - Envío de Email de Prueba */}
          <div className="border-t pt-4 mt-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                <TestTube className="h-5 w-5" />
                Envío de Email de Prueba
              </h3>
              <p className="text-sm text-blue-700 mb-4">
                Envía un correo de prueba personalizado para verificar que la configuración SMTP funciona correctamente.
              </p>
              {modoPruebas === 'false' && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
                  <p className="text-sm text-green-800 font-semibold mb-1">
                    ✅ Modo Producción activo
                  </p>
                  <p className="text-xs text-green-700">
                    El email de prueba se enviará <strong>REALMENTE</strong> al destinatario especificado. 
                    Si recibes el correo, es prueba de que el servicio está bien configurado y funcionando correctamente.
                  </p>
                </div>
              )}
              {modoPruebas === 'true' && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                  <p className="text-sm text-yellow-800 font-semibold mb-1">
                    ⚠️ Modo Pruebas activo
                  </p>
                  <p className="text-xs text-yellow-700">
                    El email se redirigirá a la dirección de pruebas configurada ({emailPruebas || 'no configurada'}), 
                    no al destinatario especificado.
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
                  <p className="text-xs text-gray-500 mt-1">
                    Si no especificas un email, se enviará a tu correo de usuario ({config.smtp_user || 'no configurado'})
                  </p>
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
                  <p className="text-xs text-gray-500 mt-1">
                    Si no especificas un asunto, se usará el asunto predeterminado
                  </p>
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
                  <p className="text-xs text-gray-500 mt-1">
                    Si no especificas un mensaje, se usará el mensaje predeterminado
                  </p>
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

          {/* Resultado de la prueba */}
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

      {/* Verificación de Envíos Reales */}
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
            <div className="text-sm text-gray-600">
              Últimos 10 envíos de notificaciones
            </div>
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
                <div
                  key={envio.id}
                  className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge
                          className={
                            envio.estado === 'ENVIADA'
                              ? 'bg-green-100 text-green-800'
                              : envio.estado === 'FALLIDA'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }
                        >
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
                        {envio.tipo && (
                          <div className="text-xs text-gray-600">
                            Tipo: {envio.tipo}
                          </div>
                        )}
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

      {/* Instrucciones */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-amber-600" />
            Instrucciones para Gmail (Requisitos Obligatorios)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          {/* Paso 1: Activar 2FA */}
          <div className="bg-red-50 border-l-4 border-red-500 pl-4 py-3 rounded">
            <p className="font-bold text-red-900 mb-2">PASO 1: Activar Autenticación de 2 Factores (OBLIGATORIO)</p>
            <ol className="list-decimal ml-5 space-y-1 text-red-800">
              <li>Ve a tu cuenta de Google: <a href="https://myaccount.google.com/security" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">https://myaccount.google.com/security</a></li>
              <li>Selecciona <strong>Seguridad</strong> en el menú lateral</li>
              <li>Busca la sección <strong>"Verificación en 2 pasos"</strong></li>
              <li>Haz clic en <strong>"Activar"</strong> y sigue los pasos para configurarlo</li>
              <li><strong className="text-red-900">⚠️ Sin 2FA activado, NO podrás generar Contraseñas de Aplicación</strong></li>
            </ol>
          </div>

          {/* Paso 2: Generar App Password */}
          <div className="bg-blue-50 border-l-4 border-blue-500 pl-4 py-3 rounded">
            <p className="font-bold text-blue-900 mb-2">PASO 2: Generar Contraseña de Aplicación</p>
            <ol className="list-decimal ml-5 space-y-1 text-blue-800">
              <li>Una vez que tengas 2FA activado, vuelve a <strong>Seguridad</strong></li>
              <li>Busca la sección <strong>"Contraseñas de aplicaciones"</strong> (aparece solo si 2FA está activo)</li>
              <li>Si no la ves, ve directamente a: <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">https://myaccount.google.com/apppasswords</a></li>
              <li>Selecciona <strong>"Correo"</strong> como aplicación</li>
              <li>Selecciona el dispositivo (puedes elegir "Otro" y escribir "RapiCredit")</li>
              <li>Haz clic en <strong>"Generar"</strong></li>
              <li>Google te mostrará una contraseña de <strong>16 caracteres</strong> (sin espacios)</li>
              <li><strong className="text-blue-900">Copia TODA la contraseña de 16 caracteres</strong> (ejemplo: abcd efgh ijkl mnop)</li>
              <li>Pégala en el campo "Contraseña de Aplicación" de este formulario</li>
            </ol>
            <div className="mt-3 p-3 bg-white rounded border border-blue-200">
              <p className="font-semibold text-red-700 mb-1">⚠️ IMPORTANTE:</p>
              <ul className="list-disc ml-5 space-y-1 text-red-800">
                <li>La Contraseña de Aplicación tiene <strong>16 caracteres</strong> (puede tener espacios, pero se eliminan automáticamente)</li>
                <li><strong>NO es tu contraseña normal de Gmail</strong></li>
                <li>Solo puedes verla una vez al generarla - guárdala en un lugar seguro</li>
                <li>Si la pierdes, deberás generar una nueva</li>
              </ul>
            </div>
          </div>

          {/* Configuración recomendada */}
          <div className="bg-green-50 border-l-4 border-green-500 pl-4 py-3 rounded">
            <p className="font-bold text-green-900 mb-2">✓ Configuración Recomendada para Gmail:</p>
            <ul className="list-disc ml-5 space-y-1 text-green-800">
              <li><strong>Servidor SMTP:</strong> smtp.gmail.com</li>
              <li><strong>Puerto:</strong> 587 (recomendado) o 465</li>
              <li><strong>TLS:</strong> Activado (obligatorio para puerto 587)</li>
              <li><strong>Email:</strong> Tu email de Gmail completo (ejemplo: tu-email@gmail.com)</li>
              <li><strong>Contraseña:</strong> La Contraseña de Aplicación de 16 caracteres</li>
            </ul>
          </div>

          {/* Solución de problemas */}
          <div className="bg-gray-50 border-l-4 border-gray-400 pl-4 py-3 rounded">
            <p className="font-bold text-gray-900 mb-2">🔧 Si tienes problemas:</p>
            <ul className="list-disc ml-5 space-y-1 text-gray-700">
              <li><strong>Error "Usuario o contraseña incorrectos":</strong> Verifica que estés usando la Contraseña de Aplicación, NO tu contraseña normal</li>
              <li><strong>No aparece "Contraseñas de aplicaciones":</strong> Asegúrate de que 2FA esté activado y que hayas iniciado sesión recientemente</li>
              <li><strong>Error de conexión:</strong> Verifica que el puerto sea 587 y TLS esté activado</li>
              <li><strong>Gmail bloquea el acceso:</strong> Puede requerir "Permitir aplicaciones menos seguras" o usar OAuth2 (más avanzado)</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}


