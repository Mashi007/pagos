import { useState, useEffect, useMemo } from 'react'
import { Mail, Save, TestTube, CheckCircle, AlertCircle, Eye, EyeOff, Clock, XCircle, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Badge } from '../../components/ui/badge'
import { toast } from 'sonner'
import { validarEmail, validarConfiguracionGmail, validarConfiguracionImapGmail } from '../../utils/validators'
import { emailConfigService, notificacionService, type Notificacion } from '../../services/notificacionService'
import { BASE_PATH } from '../../config/env'

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
  email_activo?: string
  imap_host?: string
  imap_port?: string
  imap_user?: string
  imap_password?: string
  imap_use_ssl?: string
  tickets_notify_emails?: string
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
  const [emailActivo, setEmailActivo] = useState<boolean>(true) // âœ… Estado activo/inactivo
  const [emailPruebaDestino, setEmailPruebaDestino] = useState('')
  const [subjectPrueba, setSubjectPrueba] = useState('')
  const [mensajePrueba, setMensajePrueba] = useState('')
  const [errorValidacion, setErrorValidacion] = useState<string | null>(null)

  // Estado de vinculación y monitoreo
  const [vinculacionConfirmada, setVinculacionConfirmada] = useState<boolean>(false)
  const [mensajeVinculacion, setMensajeVinculacion] = useState<string | null>(null)
  const [requiereAppPassword, setRequiereAppPassword] = useState<boolean>(false)
  const [estadoConfiguracion, setEstadoConfiguracion] = useState<{
    configurada: boolean
    mensaje: string
    problemas: string[]
    conexion_smtp?: { success: boolean, message?: string }
  } | null>(null)
  const [, setVerificandoEstado] = useState<boolean>(false)

  // Estado de envíos
  const [enviosRecientes, setEnviosRecientes] = useState<Notificacion[]>([])
  const [cargandoEnvios, setCargandoEnvios] = useState(false)
  const [resultadoPrueba, setResultadoPrueba] = useState<any>(null)
  const [emailEnviadoExitoso, setEmailEnviadoExitoso] = useState(false)
  const [mostrarPasswordImap, setMostrarPasswordImap] = useState(false)
  const [probandoImap, setProbandoImap] = useState(false)
  const [resultadoImap, setResultadoImap] = useState<{ success?: boolean; mensaje?: string } | null>(null)

  // Cargar configuración al montar
  useEffect(() => {
    cargarConfiguracion()
    cargarEnviosRecientes()
    verificarEstadoGoogle() // âœ… Verificar estado de Google/Gmail al cargar
  }, [])

  // âœ… Verificar estado de configuración con Google/Gmail
  const verificarEstadoGoogle = async () => {
    try {
      setVerificandoEstado(true)
      const estado = await emailConfigService.verificarEstadoConfiguracionEmail()
      setEstadoConfiguracion(estado)

      // âœ… Actualizar estado de vinculación basado en la verificación REAL de Gmail
      // La conexión SMTP exitosa significa que Gmail ACEPTÓ las credenciales
      if (estado.configurada && estado.conexion_smtp?.success === true) {
        setVinculacionConfirmada(true)
        setMensajeVinculacion('âœ… Sistema vinculado correctamente con Google/Google Workspace')
        setRequiereAppPassword(false)
        if (process.env.NODE_ENV === 'development') {
          console.log('âœ… Gmail confirmó: Configuración correcta y conexión aceptada')
        }
      } else {
        // Si hay problemas o la conexión SMTP falló, Gmail RECHAZÓ la conexión
        setVinculacionConfirmada(false)

        // Verificar si el problema es específico de App Password
        const requiereAppPass = estado.problemas.some(p =>
          p.toLowerCase().includes('app password') ||
          p.toLowerCase().includes('contraseña de aplicación') ||
          p.toLowerCase().includes('application-specific password') ||
          p.toLowerCase().includes('requiere una contraseña de aplicación')
        ) || (estado.conexion_smtp?.message?.toLowerCase().includes('app password') ?? false) ||
           (estado.conexion_smtp?.message?.toLowerCase().includes('contraseña de aplicación') ?? false)

        setRequiereAppPassword(Boolean(requiereAppPass))
        setMensajeVinculacion(estado.mensaje || 'âš ï¸ Gmail rechazó la conexión. Verifica tus credenciales.')

        if (process.env.NODE_ENV === 'development') {
          console.log('âŒ Gmail rechazó:', {
            problemas: estado.problemas,
            conexion_smtp: estado.conexion_smtp,
            requiereAppPassword: requiereAppPass
          })
        }
      }
    } catch (error) {
      console.error('Error verificando estado de Google:', error)
      setEstadoConfiguracion({
        configurada: false,
        mensaje: 'Error al verificar estado de configuración',
        problemas: ['No se pudo verificar el estado con Google'],
        conexion_smtp: { success: false, message: 'Error al conectar con Gmail' }
      })
    } finally {
      setVerificandoEstado(false)
    }
  }

  // Cargar configuración desde backend
  const cargarConfiguracion = async () => {
    try {
      const data = await emailConfigService.obtenerConfiguracionEmail()

      // âœ… CRÍTICO: Sincronizar from_email con smtp_user si está vacío
      // Esto asegura que el botón se habilite correctamente
      if ((!data.from_email || data.from_email.trim() === '') && data.smtp_user?.trim()) {
        data.from_email = data.smtp_user
      }

      // âœ… Asegurar que from_email tenga un valor por defecto si smtp_user existe
      if (!data.from_email && data.smtp_user) {
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

      // âœ… Asegurar valores por defecto para campos requeridos
      if (!data.smtp_host) data.smtp_host = 'smtp.gmail.com'
      if (!data.smtp_port) data.smtp_port = '587'
      if (!data.from_name) data.from_name = 'RapiCredit'
      if (data.imap_host === undefined) data.imap_host = ''
      if (data.imap_port === undefined) data.imap_port = '993'
      if (data.imap_user === undefined) data.imap_user = ''
      if (data.imap_password === undefined || data.imap_password === '***') data.imap_password = ''
      if (data.imap_use_ssl === undefined) data.imap_use_ssl = 'true'
      if (data.tickets_notify_emails === undefined) data.tickets_notify_emails = ''

      // Normalizar email_activo a string
      if (data.email_activo !== undefined && data.email_activo !== null) {
        if (typeof data.email_activo === 'boolean') {
          data.email_activo = data.email_activo ? 'true' : 'false'
        } else if (typeof data.email_activo === 'string') {
          // Ya es string, mantenerlo
        } else {
          data.email_activo = String(data.email_activo)
        }
      }

      setConfig(data as EmailConfigData)
      setModoPruebas(data.modo_pruebas || 'true')
      setEmailPruebas(data.email_pruebas || '')
      // âœ… Cargar estado activo/inactivo
      const emailActivoValue = data.email_activo === undefined || data.email_activo === null
        ? true
        : (data.email_activo === 'true' || data.email_activo === '1')
      setEmailActivo(emailActivoValue)
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

      // âœ… Sincronizar from_email con smtp_user automáticamente
      // Esto asegura que siempre tengan el mismo valor si from_email está vacío o igual al anterior
      if (campo === 'smtp_user') {
        // Si from_email está vacío o es igual al smtp_user anterior, sincronizar
        if (!prev.from_email?.trim() || prev.from_email === prev.smtp_user) {
          nuevo.from_email = valor
        }
      }

      return nuevo
    })

    // Limpiar error de validación cuando el usuario edita
    if (errorValidacion) {
      setErrorValidacion(null)
    }
  }

  // Validar si se puede guardar
  const puedeGuardar = useMemo((): boolean => {
    // âœ… CONDICIÓN 1: Campos obligatorios básicos (siempre requeridos)
    const tieneHost = config.smtp_host?.trim() || ''
    const tienePort = config.smtp_port?.trim() || ''
    const tieneUser = config.smtp_user?.trim() || ''
    const tieneFromEmail = config.from_email?.trim() || ''

    if (!tieneHost || !tienePort || !tieneUser || !tieneFromEmail) {
      return false
    }

    // âœ… CONDICIÓN 2: Puerto válido (número entre 1 y 65535)
    const puerto = parseInt(config.smtp_port || '0')
    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {
      return false
    }

    // âœ… CONDICIÓN 3: Validaciones específicas para Gmail/Google Workspace
    const esGmail = config.smtp_host?.toLowerCase().includes('gmail.com') || false
    if (esGmail) {
      // âœ… 3.1: Gmail requiere contraseña siempre
      const tienePassword = config.smtp_password?.trim() || ''
      if (!tienePassword) {
        return false
      }

      // âœ… 3.2: Gmail solo acepta puertos 587 (TLS) o 465 (SSL)
      if (puerto !== 587 && puerto !== 465) {
        return false
      }

      // âœ… 3.3: Puerto 587 requiere TLS habilitado
      if (puerto === 587 && config.smtp_use_tls !== 'true') {
        return false
      }
    }

    return true
  }, [
    config.smtp_host,
    config.smtp_port,
    config.smtp_user,
    config.from_email,
    config.smtp_password,
    config.smtp_use_tls
  ])

  // Obtener campos faltantes para mensaje
  const obtenerCamposFaltantes = (): string[] => {
    const faltantes: string[] = []

    // Campos obligatorios básicos
    if (!config.smtp_host?.trim()) faltantes.push('Servidor SMTP')
    if (!config.smtp_port?.trim()) faltantes.push('Puerto SMTP')
    if (!config.smtp_user?.trim()) faltantes.push('Email de Usuario')
    if (!config.from_email?.trim()) faltantes.push('Email del Remitente')

    // Validar puerto numérico
    const puerto = parseInt(config.smtp_port || '0')
    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {
      faltantes.push('Puerto SMTP válido (1-65535)')
    }

    // Validaciones específicas para Gmail
    if (config.smtp_host?.toLowerCase().includes('gmail.com')) {
      if (!config.smtp_password?.trim()) {
        faltantes.push('Contraseña de Aplicación')
      }

      // Gmail solo acepta puertos 587 o 465
      if (puerto !== 587 && puerto !== 465) {
        faltantes.push('Puerto 587 (TLS) o 465 (SSL) para Gmail')
      }

      // Puerto 587 requiere TLS
      if (puerto === 587 && config.smtp_use_tls !== 'true') {
        faltantes.push('TLS habilitado (requerido para puerto 587)')
      }
    }

    return faltantes
  }

  const validarConfiguracion = (): string | null => {
    const validacion = validarConfiguracionGmail({
      smtp_host: config.smtp_host,
      smtp_port: config.smtp_port,
      smtp_user: config.smtp_user,
      smtp_password: config.smtp_password,
      smtp_use_tls: config.smtp_use_tls,
      from_email: config.from_email
    })
    if (!validacion.valido) return validacion.errores.join('. ')
    const tieneImap = !!(config.imap_host?.trim() || config.imap_user?.trim() || config.imap_password?.trim())
    if (tieneImap) {
      const validacionImap = validarConfiguracionImapGmail({
        imap_host: config.imap_host || 'imap.gmail.com',
        imap_port: config.imap_port || '993',
        imap_user: config.imap_user,
        imap_password: config.imap_password,
        imap_use_ssl: config.imap_use_ssl ?? 'true',
      })
      if (!validacionImap.valido) return `IMAP: ${validacionImap.errores.join('. ')}`
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
            email_pruebas: modoPruebas === 'true' ? emailPruebas : '',
            email_activo: emailActivo ? 'true' : 'false',
            imap_host: config.imap_host || '',
            imap_port: config.imap_port || '993',
            imap_user: config.imap_user || '',
            imap_password: (config.imap_password?.replace(/\s/g, '') || '') || undefined,
            imap_use_ssl: config.imap_use_ssl ?? 'true',
            tickets_notify_emails: config.tickets_notify_emails ?? '',
          }

      const resultado = await emailConfigService.actualizarConfiguracionEmail(configCompleta)

      // âœ… Actualizar estado de vinculación INMEDIATAMENTE con la respuesta del guardado
      // Esto asegura que las banderas se actualicen de inmediato
      const nuevaVinculacion = resultado?.vinculacion_confirmada === true
      const nuevoMensaje = resultado?.mensaje_vinculacion || null
      const nuevoRequiereAppPassword = resultado?.requiere_app_password === true

      setVinculacionConfirmada(nuevaVinculacion)
      setMensajeVinculacion(nuevoMensaje)
      setRequiereAppPassword(nuevoRequiereAppPassword)

      // Mostrar mensaje de éxito
      if (nuevaVinculacion) {
        toast.success(nuevoMensaje || 'âœ… Sistema vinculado correctamente con Google', { duration: 10000 })
      } else if (nuevoRequiereAppPassword) {
        toast.warning(nuevoMensaje || 'âš ï¸ Configuración guardada pero requiere App Password', { duration: 15000 })
      } else {
        toast.success('Configuración guardada exitosamente')
      }

      await cargarConfiguracion()

      // âœ… Verificar estado de Google después de guardar (prueba conexión SMTP real con Gmail)
      // IMPORTANTE: Preservar los estados de requiereAppPassword y vinculacionConfirmada
      // que vienen de la respuesta del guardado, ya que son más precisos
      const requiereAppPasswordAntes = nuevoRequiereAppPassword
      const vinculacionAntes = nuevaVinculacion

      await verificarEstadoGoogle()

      // âœ… Si el guardado indicó que requiere App Password, mantener ese estado
      // incluso si la verificación posterior muestra otro resultado
      if (requiereAppPasswordAntes) {
        setRequiereAppPassword(true)
        setMensajeVinculacion(nuevoMensaje)
        setVinculacionConfirmada(false)
      } else if (vinculacionAntes) {
        // Si el guardado fue exitoso, mantener el estado de éxito
        setVinculacionConfirmada(true)
        setRequiereAppPassword(false)
      }
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

    if (emailPruebaDestino && !validarEmail(emailPruebaDestino)) {
      toast.error('Por favor ingresa un email válido')
      return
    }

    try {
      setProbando(true)
      setResultadoPrueba(null)
      setEmailEnviadoExitoso(false) // âœ… Resetear estado de éxito

      const resultado = await emailConfigService.probarConfiguracionEmail(
        emailPruebaDestino.trim() || undefined,
        subjectPrueba.trim() || undefined,
        mensajePrueba.trim() || undefined
      )

      setResultadoPrueba(resultado)

      if (resultado.success === false) {
        const mensaje = resultado.mensaje || 'No se pudo enviar el correo.'
        toast.error(mensaje)
        setResultadoPrueba({ ...resultado, error: mensaje })
        setEmailEnviadoExitoso(false)
        // Si falla por usuario/contraseña, mostrar aviso de App Password
        const esErrorCredenciales = /usuario|contraseña|app password|contraseña de aplicación/i.test(mensaje)
        if (esErrorCredenciales) {
          setRequiereAppPassword(true)
          setVinculacionConfirmada(false)
          setMensajeVinculacion(mensaje)
        }
      } else if (resultado.mensaje?.includes('enviado')) {
        toast.success(`Email de prueba enviado exitosamente a ${resultado.email_destino || 'tu correo'}`)
        setEmailEnviadoExitoso(true)
        setVinculacionConfirmada(true)
        setRequiereAppPassword(false)
        setMensajeVinculacion(null)
        setTimeout(() => {
          setEmailEnviadoExitoso(false)
        }, 3000)
      } else {
        toast.error('Error enviando email de prueba')
        setEmailEnviadoExitoso(false)
      }
    } catch (error: any) {
      console.error('Error probando configuración:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error desconocido'
      toast.error(`Error probando configuración: ${mensajeError}`)
      setResultadoPrueba({ error: mensajeError })
      setEmailEnviadoExitoso(false)
      const esErrorCredenciales = /usuario|contraseña|app password|contraseña de aplicación/i.test(String(mensajeError))
      if (esErrorCredenciales) {
        setRequiereAppPassword(true)
        setVinculacionConfirmada(false)
        setMensajeVinculacion(String(mensajeError))
      }
    } finally {
      setProbando(false)
    }
  }

  const esGmail = config.smtp_host?.toLowerCase().includes('gmail.com')

  return (
    <div className="space-y-6">
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
          {/* âœ… Toggle Activar/Desactivar Email */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <label className="text-sm font-semibold text-gray-900 block mb-1">
                  Servicio de Email
                </label>
                <p className="text-xs text-gray-600">
                  {emailActivo
                    ? 'âœ… El sistema está enviando emails automáticamente'
                    : 'âš ï¸ El sistema NO enviará emails. Activa el servicio para habilitar envíos.'}
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={emailActivo}
                  onChange={(e) => {
                    setEmailActivo(e.target.checked)
                    toast.info(e.target.checked ? 'Email activado - Los envíos se habilitarán al guardar' : 'Email desactivado - Los envíos se deshabilitarán al guardar')
                  }}
                  className="sr-only peer toggle-input-peer"
                />
                <div className="toggle-switch-track-lg"></div>
                <span className="ml-3 text-sm font-medium text-gray-700">
                  {emailActivo ? 'Activo' : 'Inactivo'}
                </span>
              </label>
            </div>
          </div>

          {/* Banners de estado y monitoreo de Google */}
          {esGmail && (
            <>
              {/* âœ… Estado: Configurado y vinculado correctamente */}
              {vinculacionConfirmada && estadoConfiguracion?.configurada && (
                <div className="bg-white border-2 border-green-500 rounded-lg p-4">
                  <div className="flex items-center gap-3">
                    {/* Semáforo Verde */}
                    <div className="flex flex-col items-center gap-1 flex-shrink-0">
                      <div className="w-4 h-4 bg-green-500 rounded-full shadow-lg"></div>
                      <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                      <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-gray-900">
                        Configuración correcta
                      </p>
                      <p className="text-sm text-gray-600">
                        Gmail aceptó la conexión. Puedes enviar emails.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* âš ï¸ Estado: Requiere App Password (prioridad sobre otros estados) */}
              {requiereAppPassword && !vinculacionConfirmada && (
                <div className="bg-white border-2 border-amber-400 rounded-lg p-4">
                  <div className="flex items-center gap-3">
                    {/* Semáforo Amarillo */}
                    <div className="flex flex-col items-center gap-1 flex-shrink-0">
                      <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                      <div className="w-4 h-4 bg-amber-500 rounded-full shadow-lg"></div>
                      <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-gray-900 mb-2">
                        Requiere App Password
                      </p>
                      <div className="text-sm text-gray-600 space-y-1">
                        <p>1. Activa 2FA: <a href="https://myaccount.google.com/security" target="_blank" rel="noopener noreferrer" className="underline text-blue-600">myaccount.google.com/security</a></p>
                        <p>2. Genera App Password: <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" className="underline text-blue-600">myaccount.google.com/apppasswords</a></p>
                        <p>3. Pega la contraseña de 16 caracteres y guarda</p>
                      </div>
                      {mensajeVinculacion && (
                        <p className="text-xs text-gray-500 mt-2 italic">
                          {mensajeVinculacion}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* âŒ Estado: No configurado o con problemas (solo si no requiere App Password) */}
              {/* Datos completos, pendiente de verificar con Enviar Email de Prueba */}
              {estadoConfiguracion?.configurada && !vinculacionConfirmada && !requiereAppPassword && (
                <div className="bg-white border-2 border-amber-400 rounded-lg p-4">
                  <div className="flex items-center gap-3">
                    <div className="flex flex-col items-center gap-1 flex-shrink-0">
                      <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                      <div className="w-4 h-4 bg-amber-500 rounded-full shadow-lg"></div>
                      <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-gray-900">Datos completos</p>
                      <p className="text-sm text-gray-600">
                        Usa &quot;Enviar Email de Prueba&quot; para verificar la conexión con Gmail. Si falla con &quot;usuario o contraseña no aceptados&quot;, usa una <strong>Contraseña de aplicación</strong> (no la contraseña normal).
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {!vinculacionConfirmada && !requiereAppPassword && estadoConfiguracion && !estadoConfiguracion.configurada && (
                <div className="bg-white border-2 border-red-500 rounded-lg p-4">
                  <div className="flex items-center gap-3">
                    {/* Semáforo Rojo */}
                    <div className="flex flex-col items-center gap-1 flex-shrink-0">
                      <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                      <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                      <div className="w-4 h-4 bg-red-500 rounded-full shadow-lg"></div>
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-gray-900">
                        Error de conexión
                      </p>
                      <p className="text-sm text-gray-600">
                        {estadoConfiguracion.mensaje || mensajeVinculacion || 'No se pudo conectar. Verifica tus credenciales.'}
                      </p>
                      {estadoConfiguracion.problemas && estadoConfiguracion.problemas.length > 0 && (
                        <ul className="text-xs text-gray-600 space-y-1 mt-2 list-disc list-inside">
                          {estadoConfiguracion.problemas.map((problema, idx) => (
                            <li key={idx}>{problema}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* â³ Estado: Pendiente de verificación (solo si no hay estado verificado) */}
              {!estadoConfiguracion && config.smtp_user && config.smtp_password && !vinculacionConfirmada && !requiereAppPassword && (
                <div className="bg-white border border-gray-300 rounded-lg p-4">
                  <div className="flex items-center gap-3">
                    {/* Semáforo Amarillo (pendiente) */}
                    <div className="flex flex-col items-center gap-1 flex-shrink-0">
                      <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                      <div className="w-4 h-4 bg-amber-500 rounded-full shadow-lg"></div>
                      <div className="w-4 h-4 bg-gray-200 rounded-full"></div>
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-gray-900">Guarda la configuración para verificar la conexión con Gmail</p>
                    </div>
                  </div>
                </div>
              )}
            </>
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

          {/* Políticas Gmail IMAP (recibir correo) */}
          <div className="border-t pt-6 mt-6">
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 mb-4">
              <h3 className="font-semibold text-slate-900 mb-2 flex items-center gap-2">
                <Mail className="h-5 w-5 text-slate-600" />
                Políticas Gmail IMAP (recibir correo)
              </h3>
              <p className="text-sm text-slate-700 mb-2">
                Configura IMAP para recibir correo (lectura de bandeja). Gmail: <strong>imap.gmail.com</strong>, puerto <strong>993</strong> (SSL) o <strong>143</strong> (STARTTLS). Requiere la misma <strong>Contraseña de Aplicación</strong> que SMTP.
              </p>
              <p className="text-xs text-slate-600">
                Habilita IMAP en Gmail: Ajustes → Reenvío y POP/IMAP → Activar IMAP. Ref:{' '}
                <a href="https://support.google.com/mail/answer/7126229" target="_blank" rel="noopener noreferrer" className="underline text-blue-600">support.google.com/mail/answer/7126229</a>
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium block mb-2">Servidor IMAP</label>
                <Input
                  value={config.imap_host || ''}
                  onChange={(e) => handleChange('imap_host', e.target.value)}
                  placeholder="imap.gmail.com"
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Puerto IMAP</label>
                <Input
                  value={config.imap_port || '993'}
                  onChange={(e) => handleChange('imap_port', e.target.value)}
                  placeholder="993"
                />
                <p className="text-xs text-gray-500 mt-1">993 (SSL) o 143 (STARTTLS). Gmail recomienda 993.</p>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2 mt-4">
              <div>
                <label className="text-sm font-medium block mb-2">Email IMAP (usuario)</label>
                <Input
                  type="email"
                  value={config.imap_user || ''}
                  onChange={(e) => handleChange('imap_user', e.target.value)}
                  placeholder="tu-email@gmail.com"
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Contraseña de Aplicación (IMAP)</label>
                <div className="relative">
                  <Input
                    type={mostrarPasswordImap ? 'text' : 'password'}
                    value={config.imap_password || ''}
                    onChange={(e) => handleChange('imap_password', e.target.value)}
                    placeholder="Misma App Password que SMTP"
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setMostrarPasswordImap(!mostrarPasswordImap)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {mostrarPasswordImap ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-2 mt-4">
              <input
                type="checkbox"
                checked={(config.imap_use_ssl ?? 'true') === 'true'}
                onChange={(e) => handleChange('imap_use_ssl', e.target.checked ? 'true' : 'false')}
                className="rounded"
              />
              <label className="text-sm font-medium">Usar SSL (puerto 993). Desmarca para STARTTLS (143).</label>
            </div>
            <div className="mt-4 flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={async () => {
                  setProbandoImap(true)
                  setResultadoImap(null)
                  try {
                    const r = await emailConfigService.probarConfiguracionImap({
                      imap_host: config.imap_host || undefined,
                      imap_port: config.imap_port || undefined,
                      imap_user: config.imap_user || undefined,
                      imap_password: config.imap_password || undefined,
                      imap_use_ssl: config.imap_use_ssl ?? undefined,
                    })
                    setResultadoImap(r)
                    if (r.success) toast.success(r.mensaje || 'Conexión IMAP correcta')
                    else toast.error(r.mensaje || 'Error probando IMAP')
                  } catch (err: any) {
                    const msg = err?.response?.data?.detail || err?.message || 'Error probando IMAP'
                    setResultadoImap({ success: false, mensaje: msg })
                    toast.error(msg)
                  } finally {
                    setProbandoImap(false)
                  }
                }}
                disabled={probandoImap || !config.imap_host?.trim() || !config.imap_user?.trim() || !config.imap_password?.trim()}
              >
                {probandoImap ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <TestTube className="h-4 w-4 mr-2" />}
                Probar conexión IMAP
              </Button>
              {resultadoImap && (
                <span className={`text-sm ${resultadoImap.success ? 'text-green-600' : 'text-red-600'}`}>
                  {resultadoImap.success ? 'OK' : resultadoImap.mensaje}
                </span>
              )}
            </div>
          </div>

          {/* Notificación automática de tickets CRM */}
          <div className="border-t pt-6 mt-6">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                <Mail className="h-5 w-5 text-blue-600" />
                Notificación automática de tickets (CRM)
              </h3>
              <p className="text-sm text-blue-800 mb-2">
                Cuando se crea o actualiza un ticket en <a href={BASE_PATH + '/crm/tickets'} className="underline font-medium">CRM → Tickets</a>, se envía un correo automáticamente <strong>desde el email configurado arriba</strong> hacia los contactos que indiques aquí.
              </p>
              <p className="text-xs text-blue-700">
                Introduce uno o varios emails separados por coma (contactos prestablecidos). Ej: <code className="bg-blue-100 px-1 rounded">soporte@empresa.com, gerencia@empresa.com</code>
              </p>
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">Contactos para notificación de tickets</label>
              <Textarea
                value={config.tickets_notify_emails || ''}
                onChange={(e) => handleChange('tickets_notify_emails', e.target.value)}
                placeholder="email1@ejemplo.com, email2@ejemplo.com"
                rows={3}
                className="font-mono text-sm"
              />
              <p className="text-xs text-gray-500 mt-1">
                Estos contactos recibirán un correo cada vez que se cree o actualice un ticket en el CRM.
              </p>
            </div>
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
              type="button"
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
                  <p className="text-sm text-green-800 font-semibold mb-1">âœ… Modo Producción activo</p>
                  <p className="text-xs text-green-700">
                    El email de prueba se enviará <strong>REALMENTE</strong> al destinatario especificado.
                  </p>
                </div>
              )}

              {modoPruebas === 'true' && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                  <p className="text-sm text-yellow-800 font-semibold mb-1">âš ï¸ Modo Pruebas activo</p>
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
                  type="button"
                  onClick={handleProbar}
                  disabled={probando || !config.smtp_user}
                  className={`flex items-center gap-2 transition-colors duration-300 ${
                    emailEnviadoExitoso
                      ? 'bg-green-600 hover:bg-green-700' // âœ… Verde cuando fue enviado exitosamente
                      : 'bg-blue-600 hover:bg-blue-700' // Azul normal
                  }`}
                >
                  <TestTube className="h-4 w-4" />
                  {probando
                    ? 'Enviando Email de Prueba...'
                    : emailEnviadoExitoso
                      ? 'âœ… Email Enviado'
                      : 'Enviar Email de Prueba'}
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
            <div className="text-sm text-gray-600">Ãšltimos 10 envíos de notificaciones</div>
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

