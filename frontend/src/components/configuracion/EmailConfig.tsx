import { useState, useEffect, useMemo } from 'react'

import {
  Mail,
  Save,
  TestTube,
  CheckCircle,
  AlertCircle,
  Eye,
  EyeOff,
  Clock,
  XCircle,
  RefreshCw,
} from 'lucide-react'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '../../components/ui/card'

import { Button } from '../../components/ui/button'

import { Input } from '../../components/ui/input'

import { Textarea } from '../../components/ui/textarea'

import { Badge } from '../../components/ui/badge'

import { toast } from 'sonner'

import { validarEmail } from '../../utils/validators'

import {
  emailConfigService,
  notificacionService,
  type Notificacion,
} from '../../services/notificacionService'

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

  /** On/Off por funcionalidad: si está en 'false', ese servicio no envía email (el resto sigue funcionando). */

  email_activo_notificaciones?: string

  email_activo_informe_pagos?: string

  email_activo_estado_cuenta?: string

  email_activo_cobros?: string

  email_activo_campanas?: string

  email_activo_tickets?: string

  /** Modo prueba por funcionalidad: 'true' = redirigir envíos de este servicio al correo de pruebas; 'false' = producción (envío real). */

  modo_pruebas_notificaciones?: string

  modo_pruebas_informe_pagos?: string

  modo_pruebas_estado_cuenta?: string

  modo_pruebas_cobros?: string

  modo_pruebas_campanas?: string

  modo_pruebas_tickets?: string
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

    smtp_use_tls: 'true',
  })

  // Estado de UI

  const [mostrarPassword, setMostrarPassword] = useState(false)

  const [guardando, setGuardando] = useState(false)

  const [probando, setProbando] = useState(false)

  const [envioManualEnCurso, setEnvioManualEnCurso] = useState(false)

  const [modoPruebas, setModoPruebas] = useState<string>('true')

  const [emailPruebas, setEmailPruebas] = useState('')

  const [emailActivo, setEmailActivo] = useState<boolean>(true) // ✓ Estado activo/inactivo

  const [emailPrincipalPrueba, setEmailPrincipalPrueba] = useState('')

  const [emailCCPrueba, setEmailCCPrueba] = useState('')

  const [emailPruebaDestino, setEmailPruebaDestino] = useState('')

  const [subjectPrueba, setSubjectPrueba] = useState('')

  const [mensajePrueba, setMensajePrueba] = useState('')

  const [errorValidacion, setErrorValidacion] = useState<string | null>(null)

  // Estado de vinculación y monitoreo

  const [vinculacionConfirmada, setVinculacionConfirmada] =
    useState<boolean>(false)

  const [mensajeVinculacion, setMensajeVinculacion] = useState<string | null>(
    null
  )

  const [requiereAppPassword, setRequiereAppPassword] = useState<boolean>(false)

  const [estadoConfiguracion, setEstadoConfiguracion] = useState<{
    configurada: boolean

    mensaje: string

    problemas: string[]

    conexion_smtp?: { success: boolean; message?: string }
  } | null>(null)

  const [, setVerificandoEstado] = useState<boolean>(false)

  // Estado de envíos

  const [enviosRecientes, setEnviosRecientes] = useState<Notificacion[]>([])

  const [cargandoEnvios, setCargandoEnvios] = useState(false)

  const [resultadoPrueba, setResultadoPrueba] = useState<any>(null)

  const [emailEnviadoExitoso, setEmailEnviadoExitoso] = useState(false)

  const [mostrarPasswordImap, setMostrarPasswordImap] = useState(false)

  const [probandoImap, setProbandoImap] = useState(false)

  const [resultadoImap, setResultadoImap] = useState<{
    success?: boolean
    mensaje?: string
  } | null>(null)

  // Cargar configuración al montar

  useEffect(() => {
    cargarConfiguracion()

    cargarEnviosRecientes()

    verificarEstadoGoogle() // ✓ Verificar estado de Google/Gmail al cargar
  }, [])

  // ✓ Verificar estado de configuración con Google/Gmail

  const verificarEstadoGoogle = async () => {
    try {
      setVerificandoEstado(true)

      const estado =
        await emailConfigService.verificarEstadoConfiguracionEmail()

      setEstadoConfiguracion(estado)

      // ✓ Actualizar estado de vinculación basado en la verificación REAL de Gmail

      // La conexión SMTP exitosa significa que Gmail ACEPTÓ las credenciales

      if (estado.configurada && estado.conexion_smtp?.success === true) {
        setVinculacionConfirmada(true)

        setMensajeVinculacion(
          '✓ Sistema vinculado correctamente con Google/Google Workspace'
        )

        setRequiereAppPassword(false)

        if (process.env.NODE_ENV === 'development') {
          console.log(
            '✓ Gmail confirmó: Configuración correcta y conexión aceptada'
          )
        }
      } else {
        // Si hay problemas o la conexión SMTP falló, Gmail RECHAZÓ la conexión

        setVinculacionConfirmada(false)

        // Verificar si el problema es específico de App Password

        const requiereAppPass =
          estado.problemas.some(
            p =>
              p.toLowerCase().includes('app password') ||
              p.toLowerCase().includes('contraseña de aplicación') ||
              p.toLowerCase().includes('application-specific password') ||
              p.toLowerCase().includes('requiere una contraseña de aplicación')
          ) ||
          (estado.conexion_smtp?.message
            ?.toLowerCase()
            .includes('app password') ??
            false) ||
          (estado.conexion_smtp?.message
            ?.toLowerCase()
            .includes('contraseña de aplicación') ??
            false)

        setRequiereAppPassword(Boolean(requiereAppPass))

        setMensajeVinculacion(
          estado.mensaje ||
            '✗ Gmail rechazó la conexión. Verifica tus credenciales.'
        )

        if (process.env.NODE_ENV === 'development') {
          console.log('✗ Gmail rechazó:', {
            problemas: estado.problemas,

            conexion_smtp: estado.conexion_smtp,

            requiereAppPassword: requiereAppPass,
          })
        }
      }
    } catch (error) {
      console.error('Error verificando estado de Google:', error)

      setEstadoConfiguracion({
        configurada: false,

        mensaje: 'Error al verificar estado de configuración',

        problemas: ['No se pudo verificar el estado con Google'],

        conexion_smtp: {
          success: false,
          message: 'Error al conectar con Gmail',
        },
      })
    } finally {
      setVerificandoEstado(false)
    }
  }

  // Cargar configuración desde backend

  const cargarConfiguracion = async () => {
    try {
      const data = await emailConfigService.obtenerConfiguracionEmail()

      // ✓ CRÍTICO: Sincronizar from_email con smtp_user si está vacío

      // Esto asegura que el botón se habilite correctamente

      if (
        (!data.from_email || data.from_email.trim() === '') &&
        data.smtp_user?.trim()
      ) {
        data.from_email = data.smtp_user
      }

      // ✓ Asegurar que from_email tenga un valor por defecto si smtp_user existe

      if (!data.from_email && data.smtp_user) {
        data.from_email = data.smtp_user
      }

      // Normalizar smtp_use_tls a string 'true' o 'false'

      if (data.smtp_use_tls === undefined || data.smtp_use_tls === null) {
        data.smtp_use_tls = 'true'
      } else if (typeof data.smtp_use_tls === 'boolean') {
        data.smtp_use_tls = data.smtp_use_tls ? 'true' : 'false'
      } else if (typeof data.smtp_use_tls === 'string') {
        data.smtp_use_tls =
          data.smtp_use_tls.toLowerCase() === 'true' ||
          data.smtp_use_tls === '1'
            ? 'true'
            : 'false'
      }

      // ✓ Asegurar valores por defecto para campos requeridos

      if (!data.smtp_host) data.smtp_host = 'smtp.gmail.com'

      if (!data.smtp_port) data.smtp_port = '587'

      if (!data.from_name) data.from_name = 'RapiCredit'

      if (data.imap_host === undefined) data.imap_host = ''

      if (data.imap_port === undefined) data.imap_port = '993'

      if (data.imap_user === undefined) data.imap_user = ''

      const apiSmtpMasked =
        data.smtp_password === undefined || data.smtp_password === '***'
      const apiImapMasked =
        data.imap_password === undefined || data.imap_password === '***'

      if (apiImapMasked) data.imap_password = ''
      if (apiSmtpMasked) data.smtp_password = ''

      if (data.imap_use_ssl === undefined) data.imap_use_ssl = 'true'

      if (data.tickets_notify_emails === undefined)
        data.tickets_notify_emails = ''

      const serviceKeys = [
        'email_activo_notificaciones',
        'email_activo_informe_pagos',
        'email_activo_estado_cuenta',
        'email_activo_cobros',
        'email_activo_campanas',
        'email_activo_tickets',
      ]

      serviceKeys.forEach(k => {
        if (data[k] === undefined || data[k] === null) data[k] = 'true'
      })

      const modoPruebasKeys = [
        'modo_pruebas_notificaciones',
        'modo_pruebas_informe_pagos',
        'modo_pruebas_estado_cuenta',
        'modo_pruebas_cobros',
        'modo_pruebas_campanas',
        'modo_pruebas_tickets',
      ]

      modoPruebasKeys.forEach(k => {
        if (data[k] === undefined || data[k] === null) data[k] = 'false'
      })

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

      setConfig(prev => {
        const next = { ...data } as EmailConfigData

        // Si el API devuelve ***, mantener el valor que el usuario tenia (no borrar la contraseña del campo)

        if (apiSmtpMasked)
          next.smtp_password =
            prev.smtp_password && prev.smtp_password !== '***'
              ? prev.smtp_password
              : ''

        if (apiImapMasked)
          next.imap_password =
            prev.imap_password && prev.imap_password !== '***'
              ? prev.imap_password
              : ''

        return next
      })

      setModoPruebas(data.modo_pruebas || 'true')

      setEmailPruebas(data.email_pruebas || '')

      // Integracion con Notificaciones: modo_pruebas y correos se comparten con notificaciones_envios

      try {
        const envios =
          (await emailConfigService.obtenerConfiguracionEnvios()) as Record<
            string,
            unknown
          >

        if (envios && typeof envios === 'object') {
          const modoEnvios = envios.modo_pruebas

          if (modoEnvios === true || modoEnvios === false) {
            setModoPruebas(modoEnvios ? 'true' : 'false')
          }

          const emailsArr = envios.emails_pruebas

          const emailSingle = envios.email_pruebas

          if (
            Array.isArray(emailsArr) &&
            emailsArr.length > 0 &&
            typeof emailsArr[0] === 'string'
          ) {
            setEmailPruebas(emailsArr[0].trim())
          } else if (typeof emailSingle === 'string' && emailSingle.trim()) {
            setEmailPruebas(emailSingle.trim())
          }
        }
      } catch (_) {}

      // ✓ Cargar estado activo/inactivo

      const emailActivoValue =
        data.email_activo === undefined || data.email_activo === null
          ? true
          : data.email_activo === 'true' || data.email_activo === '1'

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

      // ✓ Sincronizar from_email con smtp_user automáticamente

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
    // ✓ CONDICIÓN 1: Campos obligatorios básicos (siempre requeridos)

    const tieneHost = config.smtp_host?.trim() || ''

    const tienePort = config.smtp_port?.trim() || ''

    const tieneUser = config.smtp_user?.trim() || ''

    const tieneFromEmail = config.from_email?.trim() || ''

    if (!tieneHost || !tienePort || !tieneUser || !tieneFromEmail) {
      return false
    }

    // ✓ CONDICIÓN 2: Puerto válido (número entre 1 y 65535)

    const puerto = parseInt(config.smtp_port || '0')

    if (isNaN(puerto) || puerto < 1 || puerto > 65535) {
      return false
    }

    // ✓ CONDICIÓN 3: Validaciones específicas para Gmail/Google Workspace

    const esGmail =
      config.smtp_host?.toLowerCase().includes('gmail.com') || false

    if (esGmail) {
      // ✓ 3.1: Gmail requiere contraseña siempre

      const tienePassword = config.smtp_password?.trim() || ''

      if (!tienePassword) {
        return false
      }

      // ✓ 3.2: Gmail solo acepta puertos 587 (TLS) o 465 (SSL)

      if (puerto !== 587 && puerto !== 465) {
        return false
      }

      // ✓ 3.3: Puerto 587 requiere TLS habilitado

      if (puerto === 587 && config.smtp_use_tls !== 'true') {
        return false
      }
    }

    // ✓ CONDICIÓN 4: En modo Pruebas, el correo de pruebas es obligatorio y debe ser válido

    if (modoPruebas === 'true') {
      const email = (emailPruebas ?? '').trim()

      if (!email || !email.includes('@')) {
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

    config.smtp_use_tls,

    modoPruebas,

    emailPruebas,
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
        faltantes.push('Contraseña')
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

    // En modo Pruebas, el correo de pruebas es obligatorio

    if (modoPruebas === 'true') {
      const email = (emailPruebas ?? '').trim()

      if (!email || !email.includes('@')) {
        faltantes.push('Email de Pruebas (obligatorio en modo Pruebas)')
      }
    }

    return faltantes
  }

  // Guardar: validación única en backend (PUT); errores 400 se muestran en toast.

  const handleGuardar = async () => {
    setErrorValidacion(null)

    try {
      setGuardando(true)

      // Limpiar espacios de la contraseña

      const passwordLimpia = (
        config.smtp_password?.replace(/\s/g, '') || ''
      ).trim()

      const smtpPasswordParaEnviar =
        passwordLimpia && passwordLimpia !== '***' ? passwordLimpia : undefined

      const imapVal = (config.imap_password?.replace(/\s/g, '') || '').trim()

      const imapPasswordParaEnviar =
        imapVal && imapVal !== '***' ? imapVal : undefined

      const configCompleta = {
        ...config,

        smtp_password: smtpPasswordParaEnviar,

        modo_pruebas: modoPruebas,

        email_pruebas: modoPruebas === 'true' ? emailPruebas : '',

        email_activo: emailActivo ? 'true' : 'false',

        imap_host: config.imap_host || '',

        imap_port: config.imap_port || '993',

        imap_user: config.imap_user || '',

        imap_password: imapPasswordParaEnviar,

        imap_use_ssl: config.imap_use_ssl ?? 'true',

        tickets_notify_emails: config.tickets_notify_emails ?? '',
      }

      const resultado =
        await emailConfigService.actualizarConfiguracionEmail(configCompleta)

      // Sincronizar modo_pruebas y correos con notificaciones_envios (Notificaciones)

      try {
        const enviosActual =
          (await emailConfigService.obtenerConfiguracionEnvios()) as Record<
            string,
            unknown
          >

        const merged = {
          ...(enviosActual && typeof enviosActual === 'object'
            ? enviosActual
            : {}),
          modo_pruebas: modoPruebas === 'true',
          email_pruebas: modoPruebas === 'true' ? emailPruebas.trim() : '',
          emails_pruebas:
            modoPruebas === 'true' && emailPruebas.trim()
              ? [emailPruebas.trim()]
              : [],
        }

        await emailConfigService.actualizarConfiguracionEnvios(merged)
      } catch (_) {}

      // ✓ Actualizar estado de vinculación INMEDIATAMENTE con la respuesta del guardado

      // Esto asegura que las banderas se actualicen de inmediato

      const nuevaVinculacion = resultado?.vinculacion_confirmada === true

      const nuevoMensaje = resultado?.mensaje_vinculacion || null

      const nuevoRequiereAppPassword = resultado?.requiere_app_password === true

      setVinculacionConfirmada(nuevaVinculacion)

      setMensajeVinculacion(nuevoMensaje)

      setRequiereAppPassword(nuevoRequiereAppPassword)

      // Mostrar mensaje de éxito

      if (nuevaVinculacion) {
        toast.success(
          nuevoMensaje || '✓ Sistema vinculado correctamente con Google',
          { duration: 10000 }
        )
      } else if (nuevoRequiereAppPassword) {
        toast.warning(
          nuevoMensaje || 'Configuración guardada pero requiere App Password',
          { duration: 15000 }
        )
      } else {
        toast.success('Configuración guardada exitosamente')
      }

      if (resultado?.password_not_updated || passwordLimpia === '***') {
        toast.warning(
          resultado?.mensaje_password ||
            'La contraseña no se actualizó (el campo tenía ***). Para cambiarla, escríbela de nuevo y guarda.',
          { duration: 12000 }
        )
      }

      await cargarConfiguracion()

      // ✓ Verificar estado de Google después de guardar (prueba conexión SMTP real con Gmail)

      // IMPORTANTE: Preservar los estados de requiereAppPassword y vinculacionConfirmada

      // que vienen de la respuesta del guardado, ya que son más precisos

      const requiereAppPasswordAntes = nuevoRequiereAppPassword

      const vinculacionAntes = nuevaVinculacion

      await verificarEstadoGoogle()

      // ✓ Si el guardado indicó que requiere App Password, mantener ese estado

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

      const mensajeError =
        error?.response?.data?.detail ||
        error?.message ||
        'Error guardando configuración'

      setErrorValidacion(mensajeError)

      toast.error(mensajeError, { duration: 10000 })
    } finally {
      setGuardando(false)
    }
  }

  // Probar envío de email

  const handleProbar = async () => {
    // Validate email addresses based on mode

    if (modoPruebas === 'true') {
      if (!emailPrincipalPrueba?.trim()) {
        toast.error(
          'Debes configurar el Correo Principal para enviar el email de prueba'
        )

        return
      }

      if (!validarEmail(emailPrincipalPrueba)) {
        toast.error('El Correo Principal debe ser un email válido')

        return
      }

      if (emailCCPrueba && !validarEmail(emailCCPrueba)) {
        toast.error('El Correo CC debe ser un email válido')

        return
      }
    } else {
      if (emailPruebaDestino && !validarEmail(emailPruebaDestino)) {
        toast.error('Por favor ingresa un email válido')

        return
      }
    }

    try {
      setProbando(true)

      setResultadoPrueba(null)

      setEmailEnviadoExitoso(false) // ✓ Resetear estado de éxito

      const resultado = await emailConfigService.probarConfiguracionEmail(
        modoPruebas === 'true'
          ? emailPrincipalPrueba.trim()
          : emailPruebaDestino.trim() || undefined,

        subjectPrueba.trim() || undefined,

        mensajePrueba.trim() || undefined,

        modoPruebas === 'true' ? emailCCPrueba.trim() || undefined : undefined
      )

      setResultadoPrueba(resultado)

      if (resultado.success === false) {
        const mensaje = resultado.mensaje || 'No se pudo enviar el correo.'

        toast.error(mensaje)

        setResultadoPrueba({ ...resultado, error: mensaje })

        setEmailEnviadoExitoso(false)

        // Si falla por usuario/contraseña, mostrar aviso de App Password

        const esErrorCredenciales =
          /usuario|contraseña|app password|contraseña de aplicación/i.test(
            mensaje
          )

        if (esErrorCredenciales) {
          setRequiereAppPassword(true)

          setVinculacionConfirmada(false)

          setMensajeVinculacion(mensaje)
        }
      } else if (resultado.mensaje?.includes('enviado')) {
        toast.success(
          `Email de prueba enviado exitosamente a ${resultado.email_destino || 'tu correo'}`
        )

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

      const mensajeError =
        error?.response?.data?.detail || error?.message || 'Error desconocido'

      toast.error(`Error probando configuración: ${mensajeError}`)

      setResultadoPrueba({ error: mensajeError })

      setEmailEnviadoExitoso(false)

      const esErrorCredenciales =
        /usuario|contraseña|app password|contraseña de aplicación/i.test(
          String(mensajeError)
        )

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

  // Función para envío manual automático a correos de prueba

  const handleEnvioManual = async () => {
    // Validar que estamos en modo pruebas

    if (modoPruebas !== 'true') {
      toast.error('El envío manual solo está disponible en modo Pruebas')

      return
    }

    // Validar correos de prueba

    if (!emailPruebas?.trim()) {
      toast.error('Debes configurar al menos el email de pruebas principal')

      return
    }

    if (!validarEmail(emailPruebas)) {
      toast.error('El email de pruebas debe ser válido')

      return
    }

    try {
      setEnvioManualEnCurso(true)

      setResultadoPrueba(null)

      const resultado = await emailConfigService.probarConfiguracionEmail(
        emailPruebas.trim(),

        'Prueba de estructura de plantilla - RapiCredit',

        'Este es un correo de prueba automático para verificar que la estructura de la plantilla es correcta.',

        undefined
      )

      setResultadoPrueba(resultado)

      if (resultado.success === false) {
        const mensaje = resultado.mensaje || 'No se pudo enviar el correo.'

        toast.error(mensaje)

        setResultadoPrueba({ ...resultado, error: mensaje })
      } else if (resultado.mensaje?.includes('enviado')) {
        toast.success('Correo de prueba enviado exitosamente a ' + emailPruebas)

        setTimeout(() => {
          setEmailEnviadoExitoso(false)
        }, 3000)
      } else {
        toast.error('Error enviando correo de prueba')
      }
    } catch (error: any) {
      console.error('Error en envío manual:', error)

      const mensajeError =
        error?.response?.data?.detail || error?.message || 'Error desconocido'

      toast.error('Error: ' + mensajeError)

      setResultadoPrueba({ error: mensajeError })
    } finally {
      setEnvioManualEnCurso(false)
    }
  }

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
            Ingresa tus credenciales de Gmail o Google Workspace para enviar
            notificaciones
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* ✓ Toggle Activar/Desactivar Email */}

          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <label className="mb-1 block text-sm font-semibold text-gray-900">
                  Servicio de Email
                </label>

                <p className="text-xs text-gray-600">
                  {emailActivo
                    ? '✓ El sistema está enviando emails automáticamente'
                    : 'El sistema NO enviará emails. Activa el servicio para habilitar envíos.'}
                </p>
              </div>

              <label className="relative inline-flex cursor-pointer items-center">
                <input
                  type="checkbox"
                  checked={emailActivo}
                  onChange={e => {
                    setEmailActivo(e.target.checked)

                    toast.info(
                      e.target.checked
                        ? 'Email activado - Los envíos se habilitarán al guardar'
                        : 'Email desactivado - Los envíos se deshabilitarán al guardar'
                    )
                  }}
                  className="toggle-input-peer peer sr-only"
                />

                <div className="toggle-switch-track-lg"></div>

                <span className="ml-3 text-sm font-medium text-gray-700">
                  {emailActivo ? 'Activo' : 'Inactivo'}
                </span>
              </label>
            </div>
          </div>

          {/* On/Off por funcionalidad: cada una tiene su interruptor; si apagas uno, los demás siguen funcionando. */}

          <div className="mt-4 space-y-3">
            <p className="text-sm font-medium text-gray-700">
              Email por servicio
            </p>

            <p className="text-xs text-gray-600">
              Activa o desactiva el envío de email para cada tipo de uso. Si
              apagas uno, los demás siguen funcionando.
            </p>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {[
                {
                  key: 'email_activo_notificaciones' as const,
                  label: 'Notificaciones (plantillas a clientes)',
                },

                {
                  key: 'email_activo_informe_pagos' as const,
                  label: 'Informe de pagos (cron)',
                },

                {
                  key: 'email_activo_estado_cuenta' as const,
                  label: 'Estado de cuenta (código y PDF)',
                },

                {
                  key: 'email_activo_cobros' as const,
                  label: 'Cobros (recibos)',
                },

                {
                  key: 'email_activo_campanas' as const,
                  label: 'Campañas CRM',
                },

                {
                  key: 'email_activo_tickets' as const,
                  label: 'Tickets (aviso interno)',
                },
              ].map(({ key, label }) => (
                <label
                  key={key}
                  className="flex items-center justify-between gap-2 rounded border border-gray-200 bg-gray-50/50 p-2"
                >
                  <span className="text-sm text-gray-700">{label}</span>

                  <input
                    type="checkbox"
                    checked={(config[key] ?? 'true') === 'true'}
                    onChange={e =>
                      handleChange(key, e.target.checked ? 'true' : 'false')
                    }
                    className="rounded border-gray-300"
                  />
                </label>
              ))}
            </div>
          </div>

          {/* Modo prueba por funcionalidad: cada una puede ir a producción o a correo de pruebas de forma independiente. */}

          <div className="mt-4 space-y-3 border-t pt-4">
            <p className="text-sm font-medium text-gray-700">
              Modo prueba por funcionalidad
            </p>

            <p className="text-xs text-gray-600">
              Para cada tipo de envío puedes elegir Producción (correos reales a
              clientes) o Pruebas (todos los correos de ese tipo van al Email de
              Pruebas). Así puedes probar uno sin afectar al resto.
            </p>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {[
                {
                  key: 'modo_pruebas_notificaciones' as const,
                  label: 'Notificaciones (plantillas a clientes)',
                },

                {
                  key: 'modo_pruebas_informe_pagos' as const,
                  label: 'Informe de pagos (cron)',
                },

                {
                  key: 'modo_pruebas_estado_cuenta' as const,
                  label: 'Estado de cuenta (código y PDF)',
                },

                {
                  key: 'modo_pruebas_cobros' as const,
                  label: 'Cobros (recibos)',
                },

                {
                  key: 'modo_pruebas_campanas' as const,
                  label: 'Campañas CRM',
                },

                {
                  key: 'modo_pruebas_tickets' as const,
                  label: 'Tickets (aviso interno)',
                },
              ].map(({ key, label }) => (
                <label
                  key={key}
                  className="flex items-center justify-between gap-2 rounded border border-amber-100 bg-amber-50/50 p-2"
                >
                  <span className="text-sm text-gray-700">{label}</span>

                  <span className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">
                      {(config[key] ?? 'false') === 'true'
                        ? 'Pruebas'
                        : 'Producción'}
                    </span>

                    <input
                      type="checkbox"
                      checked={(config[key] ?? 'false') === 'true'}
                      onChange={e =>
                        handleChange(key, e.target.checked ? 'true' : 'false')
                      }
                      className="rounded border-gray-300"
                    />
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Banners de estado y monitoreo de Google */}

          {esGmail && (
            <>
              {/* ✓ Estado: Configurado y vinculado correctamente */}

              {vinculacionConfirmada && estadoConfiguracion?.configurada && (
                <div className="rounded-lg border-2 border-green-500 bg-white p-4">
                  <div className="flex items-center gap-3">
                    {/* Semáforo Verde */}

                    <div className="flex flex-shrink-0 flex-col items-center gap-1">
                      <div className="h-4 w-4 rounded-full bg-green-500 shadow-lg"></div>

                      <div className="h-4 w-4 rounded-full bg-gray-200"></div>

                      <div className="h-4 w-4 rounded-full bg-gray-200"></div>
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

              {/* Estado: Requiere App Password (prioridad sobre otros estados) */}

              {requiereAppPassword && !vinculacionConfirmada && (
                <div className="rounded-lg border-2 border-amber-400 bg-white p-4">
                  <div className="flex items-center gap-3">
                    {/* Semáforo Amarillo */}

                    <div className="flex flex-shrink-0 flex-col items-center gap-1">
                      <div className="h-4 w-4 rounded-full bg-gray-200"></div>

                      <div className="h-4 w-4 rounded-full bg-amber-500 shadow-lg"></div>

                      <div className="h-4 w-4 rounded-full bg-gray-200"></div>
                    </div>

                    <div className="flex-1">
                      <p className="mb-2 font-semibold text-gray-900">
                        Requiere App Password
                      </p>

                      <div className="space-y-1 text-sm text-gray-600">
                        <p>
                          1. Activa 2FA:{' '}
                          <a
                            href="https://myaccount.google.com/security"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 underline"
                          >
                            myaccount.google.com/security
                          </a>
                        </p>

                        <p>
                          2. Genera App Password:{' '}
                          <a
                            href="https://myaccount.google.com/apppasswords"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 underline"
                          >
                            myaccount.google.com/apppasswords
                          </a>
                        </p>

                        <p>3. Pega la contraseña de 16 caracteres y guarda</p>
                        <p className="mt-2 font-medium text-blue-700">
                          Cuentas corporativas / Google Workspace: puedes usar
                          tu contraseña normal en el campo Contraseña.
                        </p>
                      </div>

                      {mensajeVinculacion && (
                        <p className="mt-2 text-xs italic text-gray-500">
                          {mensajeVinculacion}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* ✗ Estado: No configurado o con problemas (solo si no requiere App Password) */}

              {/* Datos completos, pendiente de verificar con Enviar Email de Prueba */}

              {estadoConfiguracion?.configurada &&
                !vinculacionConfirmada &&
                !requiereAppPassword && (
                  <div className="rounded-lg border-2 border-amber-400 bg-white p-4">
                    <div className="flex items-center gap-3">
                      <div className="flex flex-shrink-0 flex-col items-center gap-1">
                        <div className="h-4 w-4 rounded-full bg-gray-200"></div>

                        <div className="h-4 w-4 rounded-full bg-amber-500 shadow-lg"></div>

                        <div className="h-4 w-4 rounded-full bg-gray-200"></div>
                      </div>

                      <div className="flex-1">
                        <p className="font-semibold text-gray-900">
                          Datos completos
                        </p>

                        <p className="text-sm text-gray-600">
                          Usa &quot;Enviar Email de Prueba&quot; para verificar.
                          Gmail personal: suele requerir Contraseña de
                          aplicación. Cuentas corporativas / Google Workspace:
                          puedes usar tu contraseña normal.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

              {!vinculacionConfirmada &&
                !requiereAppPassword &&
                estadoConfiguracion &&
                !estadoConfiguracion.configurada &&
                !resultadoPrueba?.success && (
                  <div className="rounded-lg border-2 border-red-500 bg-white p-4">
                    <div className="flex items-center gap-3">
                      {/* Semáforo Rojo */}

                      <div className="flex flex-shrink-0 flex-col items-center gap-1">
                        <div className="h-4 w-4 rounded-full bg-gray-200"></div>

                        <div className="h-4 w-4 rounded-full bg-gray-200"></div>

                        <div className="h-4 w-4 rounded-full bg-red-500 shadow-lg"></div>
                      </div>

                      <div className="flex-1">
                        <p className="font-semibold text-gray-900">
                          Error de conexión
                        </p>

                        <p className="text-sm text-gray-600">
                          {estadoConfiguracion.mensaje ||
                            mensajeVinculacion ||
                            'No se pudo conectar. Verifica tus credenciales.'}
                        </p>

                        {estadoConfiguracion.problemas &&
                          estadoConfiguracion.problemas.length > 0 && (
                            <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-gray-600">
                              {estadoConfiguracion.problemas.map(
                                (problema, idx) => (
                                  <li key={idx}>{problema}</li>
                                )
                              )}
                            </ul>
                          )}
                      </div>
                    </div>
                  </div>
                )}

              {/* ⏳ Estado: Pendiente de verificación (solo si no hay estado verificado) */}

              {!estadoConfiguracion &&
                config.smtp_user &&
                config.smtp_password &&
                !vinculacionConfirmada &&
                !requiereAppPassword && (
                  <div className="rounded-lg border border-gray-300 bg-white p-4">
                    <div className="flex items-center gap-3">
                      {/* Semáforo Amarillo (pendiente) */}

                      <div className="flex flex-shrink-0 flex-col items-center gap-1">
                        <div className="h-4 w-4 rounded-full bg-gray-200"></div>

                        <div className="h-4 w-4 rounded-full bg-amber-500 shadow-lg"></div>

                        <div className="h-4 w-4 rounded-full bg-gray-200"></div>
                      </div>

                      <div className="flex-1">
                        <p className="font-semibold text-gray-900">
                          Guarda la configuración para verificar la conexión con
                          Gmail
                        </p>
                      </div>
                    </div>
                  </div>
                )}
            </>
          )}

          {/* Campos de configuración */}

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium">
                Servidor SMTP
              </label>

              <Input
                value={config.smtp_host}
                onChange={e => handleChange('smtp_host', e.target.value)}
                placeholder="smtp.gmail.com"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Puerto SMTP
              </label>

              <Input
                value={config.smtp_port}
                onChange={e => handleChange('smtp_port', e.target.value)}
                placeholder="587"
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium">
                Email (Usuario Gmail / Google Workspace)
              </label>

              <Input
                type="email"
                value={config.smtp_user}
                onChange={e => handleChange('smtp_user', e.target.value)}
                placeholder="tu-email@gmail.com o usuario@tudominio.com"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Contraseña
              </label>

              <div className="relative">
                <Input
                  type={mostrarPassword ? 'text' : 'password'}
                  value={config.smtp_password || ''}
                  onChange={e => handleChange('smtp_password', e.target.value)}
                  placeholder="Contraseña normal o App Password (cuentas corporativas: contraseña normal)"
                  className="pr-10"
                />

                <button
                  type="button"
                  onClick={() => setMostrarPassword(!mostrarPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 transform text-gray-400 hover:text-gray-600"
                >
                  {mostrarPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>

              <p className="mt-1 text-xs text-gray-500">
                <strong>Gmail personal:</strong> con 2FA activado usa una App
                Password (16 caracteres).{' '}
                <strong>Cuentas corporativas / Google Workspace:</strong> puedes
                usar tu contraseña normal.
              </p>

              <p className="mt-1 text-sm text-amber-700">
                <strong>Importante:</strong> Si cambiaste de cuenta o
                contraseña, escríbela aquí. El valor *** no actualiza la
                contraseña en el servidor.
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm font-medium">
                Email del Remitente
              </label>

              <Input
                type="email"
                value={config.from_email}
                onChange={e => handleChange('from_email', e.target.value)}
                placeholder="tu-email@gmail.com o usuario@tudominio.com"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Nombre del Remitente
              </label>

              <Input
                value={config.from_name}
                onChange={e => handleChange('from_name', e.target.value)}
                placeholder="RapiCredit"
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={config.smtp_use_tls === 'true'}
              onChange={e =>
                handleChange(
                  'smtp_use_tls',
                  e.target.checked ? 'true' : 'false'
                )
              }
              className="rounded"
            />

            <label className="text-sm font-medium">
              Usar TLS (Recomendado para Gmail / Google Workspace)
            </label>
          </div>

          {/* Políticas Gmail IMAP (recibir correo) */}

          <div className="mt-6 border-t pt-6">
            <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
              <h3 className="mb-2 flex items-center gap-2 font-semibold text-slate-900">
                <Mail className="h-5 w-5 text-slate-600" />
                Políticas Gmail IMAP (recibir correo)
              </h3>

              <p className="mb-2 text-sm text-slate-700">
                Configura IMAP para recibir correo (lectura de bandeja). Gmail:{' '}
                <strong>imap.gmail.com</strong>, puerto <strong>993</strong>{' '}
                (SSL) o <strong>143</strong> (STARTTLS). Usa la misma contraseña
                que SMTP (normal o de aplicación).
              </p>

              <p className="text-xs text-slate-600">
                Habilita IMAP en Gmail: Ajustes → Reenvío y POP/IMAP → Activar
                IMAP. Ref:{' '}
                <a
                  href="https://support.google.com/mail/answer/7126229"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 underline"
                >
                  support.google.com/mail/answer/7126229
                </a>
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium">
                  Servidor IMAP
                </label>

                <Input
                  value={config.imap_host || ''}
                  onChange={e => handleChange('imap_host', e.target.value)}
                  placeholder="imap.gmail.com"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium">
                  Puerto IMAP
                </label>

                <Input
                  value={config.imap_port || '993'}
                  onChange={e => handleChange('imap_port', e.target.value)}
                  placeholder="993"
                />

                <p className="mt-1 text-xs text-gray-500">
                  993 (SSL) o 143 (STARTTLS). Gmail recomienda 993.
                </p>
              </div>
            </div>

            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium">
                  Email IMAP (usuario)
                </label>

                <Input
                  type="email"
                  value={config.imap_user || ''}
                  onChange={e => handleChange('imap_user', e.target.value)}
                  placeholder="tu-email@gmail.com"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium">
                  Contraseña (IMAP)
                </label>

                <div className="relative">
                  <Input
                    type={mostrarPasswordImap ? 'text' : 'password'}
                    value={config.imap_password || ''}
                    onChange={e =>
                      handleChange('imap_password', e.target.value)
                    }
                    placeholder="Misma contraseña que SMTP"
                    className="pr-10"
                  />

                  <button
                    type="button"
                    onClick={() => setMostrarPasswordImap(!mostrarPasswordImap)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {mostrarPasswordImap ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-4 flex items-center space-x-2">
              <input
                type="checkbox"
                checked={(config.imap_use_ssl ?? 'true') === 'true'}
                onChange={e =>
                  handleChange(
                    'imap_use_ssl',
                    e.target.checked ? 'true' : 'false'
                  )
                }
                className="rounded"
              />

              <label className="text-sm font-medium">
                Usar SSL (puerto 993). Desmarca para STARTTLS (143).
              </label>
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

                    const mensajeImap =
                      r.mensaje &&
                      (r.mensaje.startsWith("b'") ||
                        /AUTHENTICATIONFAILED|Invalid credentials/i.test(
                          r.mensaje
                        ))
                        ? 'Usuario o contraseña no aceptados. Gmail personal: usa Contraseña de aplicación. Cuentas corporativas/Google Workspace: prueba con tu contraseña normal.'
                        : r.mensaje || ''

                    setResultadoImap({
                      ...r,
                      mensaje: r.success ? r.mensaje : mensajeImap,
                    })

                    if (r.success)
                      toast.success(r.mensaje || 'Conexión IMAP correcta')
                    else toast.error(mensajeImap || 'Error probando IMAP')
                  } catch (err: any) {
                    const msg =
                      err?.response?.data?.detail ||
                      err?.message ||
                      'Error probando IMAP'

                    setResultadoImap({ success: false, mensaje: msg })

                    toast.error(msg)
                  } finally {
                    setProbandoImap(false)
                  }
                }}
                disabled={
                  probandoImap ||
                  !config.imap_host?.trim() ||
                  !config.imap_user?.trim() ||
                  !config.imap_password?.trim()
                }
              >
                {probandoImap ? (
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <TestTube className="mr-2 h-4 w-4" />
                )}
                Probar conexión IMAP
              </Button>

              {resultadoImap && (
                <span
                  className={`text-sm ${resultadoImap.success ? 'text-green-600' : 'text-red-600'}`}
                >
                  {resultadoImap.success
                    ? 'OK'
                    : resultadoImap.mensaje?.startsWith("b'") ||
                        /AUTHENTICATIONFAILED|Invalid credentials/i.test(
                          resultadoImap.mensaje || ''
                        )
                      ? 'Usuario o contraseña no aceptados. Gmail personal: usa Contraseña de aplicación. Cuentas corporativas/Google Workspace: prueba con tu contraseña normal.'
                      : resultadoImap.mensaje}
                </span>
              )}
            </div>
          </div>

          {/* Notificación automática de tickets CRM */}

          <div className="mt-6 border-t pt-6">
            <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
              <h3 className="mb-2 flex items-center gap-2 font-semibold text-blue-900">
                <Mail className="h-5 w-5 text-blue-600" />
                Notificación automática de tickets (CRM)
              </h3>

              <p className="mb-2 text-sm text-blue-800">
                Cuando se <strong>crea</strong> un ticket (por ejemplo desde
                comunicaciones), se envía automáticamente un correo{' '}
                <strong>con un informe en PDF adjunto</strong> a los contactos
                que indiques aquí. El envío se hace{' '}
                <strong>desde el email configurado arriba</strong> (remitente
                por defecto).
              </p>

              <p className="text-xs text-blue-700">
                Introduce uno o varios emails separados por coma (destino del
                informe de ticket). Ej:{' '}
                <code className="rounded bg-blue-100 px-1">
                  soporte@empresa.com, gerencia@empresa.com
                </code>
              </p>
            </div>

            <div>
              <label className="mb-2 block text-sm font-medium">
                Contactos para notificación de tickets
              </label>

              <Textarea
                value={config.tickets_notify_emails || ''}
                onChange={e =>
                  handleChange('tickets_notify_emails', e.target.value)
                }
                placeholder="email1@ejemplo.com, email2@ejemplo.com"
                rows={3}
                className="font-mono text-sm"
              />

              <p className="mt-1 text-xs text-gray-500">
                Estos contactos recibirán un correo con el informe en PDF
                adjunto cada vez que se cree un ticket en el CRM.
              </p>
            </div>
          </div>

          {/* Selector de ambiente */}

          <div className="mt-4 border-t pt-4">
            <div className="mb-4">
              <label className="mb-2 block text-sm font-medium">
                Ambiente de Envío
              </label>

              <div className="flex gap-4">
                <label className="flex cursor-pointer items-center space-x-2">
                  <input
                    type="radio"
                    name="ambiente"
                    value="false"
                    checked={modoPruebas === 'false'}
                    onChange={e => setModoPruebas(e.target.value)}
                    className="rounded"
                  />

                  <span className="text-sm">
                    1) Producción: cada email a cada cliente
                  </span>
                </label>

                <label className="flex cursor-pointer items-center space-x-2">
                  <input
                    type="radio"
                    name="ambiente"
                    value="true"
                    checked={modoPruebas === 'true'}
                    onChange={e => setModoPruebas(e.target.value)}
                    className="rounded"
                  />

                  <span className="text-sm">
                    2) Pruebas: todos los emails al mismo correo de pruebas
                  </span>
                </label>
              </div>
            </div>

            {modoPruebas === 'true' && (
              <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
                <label className="mb-2 block text-sm font-medium">
                  Email de Pruebas{' '}
                  <span className="text-xs text-red-500">
                    (Requerido en modo Pruebas)
                  </span>
                </label>

                <Input
                  type="email"
                  value={emailPruebas}
                  onChange={e => setEmailPruebas(e.target.value)}
                  placeholder="pruebas@ejemplo.com"
                  className="max-w-md"
                />

                <p className="mt-1 text-xs text-gray-500">
                  En modo pruebas, todos los emails se enviarán a esta dirección
                  en lugar de a los clientes reales.
                </p>
              </div>
            )}
          </div>

          {modoPruebas === 'true' && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
              <label className="mb-2 block text-sm font-medium">
                Correo Principal{' '}
                <span className="text-gray-500">(para envío de prueba)</span>
              </label>

              <Input
                type="email"
                value={emailPrincipalPrueba}
                onChange={e => setEmailPrincipalPrueba(e.target.value)}
                placeholder="correo.principal@ejemplo.com"
                className="max-w-md"
              />
            </div>
          )}

          {modoPruebas === 'true' && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
              <label className="mb-2 block text-sm font-medium">
                Correo CC <span className="text-gray-500">(opcional)</span>
              </label>

              <Input
                type="email"
                value={emailCCPrueba}
                onChange={e => setEmailCCPrueba(e.target.value)}
                placeholder="correo.cc@ejemplo.com"
                className="max-w-md"
              />
            </div>
          )}

          {/* Error de validación */}

          {errorValidacion && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4">
              <div className="flex items-start gap-2">
                <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-red-600" />

                <div className="flex-1">
                  <p className="mb-1 font-semibold text-red-900">
                    Error de validación:
                  </p>

                  <p className="whitespace-pre-line text-sm text-red-800">
                    {errorValidacion}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Botones */}

          <div className="mt-4 flex gap-2 border-t pt-4">
            <Button
              type="button"
              onClick={handleGuardar}
              disabled={guardando || !puedeGuardar}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Save className="h-4 w-4" />

              {guardando ? 'Guardando...' : 'Guardar Configuración'}
            </Button>

            {!puedeGuardar && !guardando && (
              <p className="self-center text-xs font-medium text-amber-600">
                Completa: {obtenerCamposFaltantes().join(', ')}
              </p>
            )}
          </div>

          {/* Botón de Envío Manual - DESTACADO */}

          {modoPruebas === 'true' && emailPruebas?.trim() && (
            <div className="mt-6 rounded-lg border-2 border-green-400 bg-gradient-to-r from-green-50 to-emerald-50 p-5">
              <div className="mb-3">
                <h4 className="flex items-center gap-2 font-semibold text-green-900">
                  <Mail className="h-5 w-5" />
                  Envío Manual de Prueba
                </h4>

                <p className="mt-1 text-sm text-green-700">
                  Envía un correo de prueba automáticamente para verificar la
                  estructura de la plantilla
                </p>
              </div>

              <Button
                onClick={handleEnvioManual}
                disabled={envioManualEnCurso}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-green-600 py-2 font-semibold text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Mail className="h-5 w-5" />

                {envioManualEnCurso
                  ? 'Enviando correo de prueba...'
                  : 'Enviar Correo de Prueba Ahora'}
              </Button>
            </div>
          )}

          {/* Prueba de envío */}

          <div className="mt-4 border-t pt-4">
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
              <h3 className="mb-2 flex items-center gap-2 font-semibold text-blue-900">
                <TestTube className="h-5 w-5" />
                Envío de Email de Prueba
              </h3>

              <p className="mb-4 text-sm text-blue-700">
                Envía un correo de prueba personalizado para verificar que la
                configuración SMTP funciona correctamente.
              </p>

              {modoPruebas === 'false' && (
                <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-3">
                  <p className="mb-1 text-sm font-semibold text-green-800">
                    ✓ Modo Producción activo
                  </p>

                  <p className="text-xs text-green-700">
                    El email de prueba se enviará <strong>REALMENTE</strong> al
                    destinatario especificado.
                  </p>
                </div>
              )}

              {modoPruebas === 'true' && (
                <div className="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3">
                  <p className="mb-1 text-sm font-semibold text-yellow-800">
                    Modo Pruebas activo
                  </p>

                  <p className="text-xs text-yellow-700">
                    El email de prueba se enviará al Correo Principal y CC que
                    indiques arriba (no se redirige).
                  </p>
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <label className="mb-2 block text-sm font-medium">
                    Email de Destino{' '}
                    <span className="text-gray-500">(opcional)</span>
                  </label>

                  <Input
                    type="email"
                    value={emailPruebaDestino}
                    onChange={e => setEmailPruebaDestino(e.target.value)}
                    placeholder={config.smtp_user || 'ejemplo@email.com'}
                    className="max-w-md"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium">
                    Asunto <span className="text-gray-500">(opcional)</span>
                  </label>

                  <Input
                    type="text"
                    value={subjectPrueba}
                    onChange={e => setSubjectPrueba(e.target.value)}
                    placeholder="Prueba de configuración - RapiCredit"
                    className="max-w-md"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium">
                    Mensaje de Prueba{' '}
                    <span className="text-gray-500">(opcional)</span>
                  </label>

                  <Textarea
                    value={mensajePrueba}
                    onChange={e => setMensajePrueba(e.target.value)}
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
                      ? 'bg-green-600 hover:bg-green-700' // ✓ Verde cuando fue enviado exitosamente
                      : 'bg-blue-600 hover:bg-blue-700' // Azul normal
                  }`}
                >
                  <TestTube className="h-4 w-4" />

                  {probando
                    ? 'Enviando Email de Prueba...'
                    : emailEnviadoExitoso
                      ? '✓ Email Enviado'
                      : 'Enviar Email de Prueba'}
                </Button>
              </div>
            </div>
          </div>

          {/* Resultado de prueba */}

          {resultadoPrueba && (
            <div
              className={`rounded-lg border p-4 ${
                resultadoPrueba.mensaje?.includes('enviado')
                  ? 'border-green-200 bg-green-50'
                  : 'border-red-200 bg-red-50'
              }`}
            >
              <div className="flex items-start gap-2">
                {resultadoPrueba.mensaje?.includes('enviado') ? (
                  <CheckCircle className="mt-0.5 h-5 w-5 text-green-600" />
                ) : (
                  <AlertCircle className="mt-0.5 h-5 w-5 text-red-600" />
                )}

                <div className="flex-1">
                  <p
                    className={`font-medium ${
                      resultadoPrueba.mensaje?.includes('enviado')
                        ? 'text-green-900'
                        : 'text-red-900'
                    }`}
                  >
                    {resultadoPrueba.mensaje}
                  </p>

                  {resultadoPrueba.error && (
                    <p className="mt-1 text-sm text-red-600">
                      {resultadoPrueba.error}
                    </p>
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
            Historial reciente de correos enviados para verificar que el sistema
            está funcionando correctamente
          </CardDescription>
        </CardHeader>

        <CardContent>
          <div className="mb-4 flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Últimos 10 envíos de notificaciones
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={cargarEnviosRecientes}
              disabled={cargandoEnvios}
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${cargandoEnvios ? 'animate-spin' : ''}`}
              />
              Actualizar
            </Button>
          </div>

          {cargandoEnvios ? (
            <div className="py-8 text-center text-gray-500">
              Cargando envíos...
            </div>
          ) : enviosRecientes.length === 0 ? (
            <div className="py-8 text-center text-gray-500">
              <AlertCircle className="mx-auto mb-4 h-12 w-12 text-gray-400" />

              <p>No hay envíos recientes</p>
            </div>
          ) : (
            <div className="space-y-3">
              {enviosRecientes.map(envio => (
                <div
                  key={envio.id}
                  className="rounded-lg border p-4 transition-colors hover:bg-gray-50"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="mb-2 flex items-center gap-2">
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

                      <div className="space-y-1 text-xs text-gray-500">
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />

                          {envio.fecha_envio
                            ? new Date(envio.fecha_envio).toLocaleString(
                                'es-ES'
                              )
                            : envio.fecha_creacion
                              ? new Date(envio.fecha_creacion).toLocaleString(
                                  'es-ES'
                                )
                              : 'Sin fecha'}
                        </div>

                        {envio.error_mensaje && (
                          <div className="flex items-start gap-1 text-xs text-red-600">
                            <XCircle className="mt-0.5 h-3 w-3 flex-shrink-0" />

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
