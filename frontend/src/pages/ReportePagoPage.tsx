/**





 * Formulario PÚBLICO de reporte de pago (sin login).





 * Validadores alineados con el backend: cédula (V/E/J/Z + 6-11 dígitos), monto (>0, máx 999.999.999,99),





 * fecha (obligatoria, no futura, desde calendario), institución y nº documento (longitud), archivo (JPG/PNG/PDF, máx 5 MB).





 * Notificaciones claras por cada error para guiar al cliente.





 * Marca flujo público para que, si intentan ir a login, vean "Acceso prohibido" y puedan volver.





 */

import React, { useState, useRef, useEffect } from 'react'

import {
  validarCedulaPublico,
  enviarReportePublico,
  enviarReporteInfopagos,
  getReciboInfopagos,
} from '../services/cobrosService'

import { PUBLIC_FLOW_SESSION_KEY } from '../config/env'

import { TEXTO_AVISO_NUMERO_OPERACION_FORMULARIO } from '../constants/reporteCobrosDocumento'

import { Button } from '../components/ui/button'

import { Input } from '../components/ui/input'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

// Límites iguales al backend (cobros_publico)

const MAX_MONTO = 999_999_999.99

const MIN_MONTO = 0.01

/** Alineado con backend: cobros_publico MIN/MAX para reporte en Bs. */
const MIN_MONTO_BS_REPORTAR = 1

const MAX_MONTO_BS_REPORTAR = 10_000_000

const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5 MB

const ALLOWED_FILE_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
  'application/pdf',
]

const MAX_LENGTH_INSTITUCION = 100

const MAX_LENGTH_NUMERO_OPERACION = 100

// Cédula: solo letra (V|E|G|J) + 6-11 dígitos; no puntos ni signos intermedios. Si solo dígitos, al procesar se antepone V.

const CEDULA_REGEX = /^[VEGJ]\d{6,11}$/i

/** Normaliza para validar: quita espacios, guiones y puntos. Rechaza si queda otro signo o punto. Si solo 6-11 dígitos, devuelve con V antepuesto. */

function normalizarCedulaParaProcesar(val: string): {
  valido: boolean
  valorParaEnviar?: string
  error?: string
} {
  const s = val
    .trim()
    .toUpperCase()
    .replace(/[\s.\-]/g, '')

  if (!s) return { valido: false, error: 'Ingrese el número de cédula.' }

  if (!/^[VEGJ]?\d+$/.test(s)) {
    return {
      valido: false,
      error:
        'No use puntos ni signos intermedios. Solo letra (V, E, G o J) y dígitos.',
    }
  }

  if (/^\d{6,11}$/.test(s)) return { valido: true, valorParaEnviar: 'V' + s }

  if (CEDULA_REGEX.test(s)) return { valido: true, valorParaEnviar: s }

  return {
    valido: false,
    error: 'Cédula inválida. Use letra V, E, G o J seguida de 6 a 11 dígitos.',
  }
}

function normalizarCedulaInput(val: string): string {
  return val
    .trim()
    .toUpperCase()
    .replace(/[\s.\-]/g, '')
}

function validarMonto(
  val: string,
  moneda: 'BS' | 'USD'
): {
  valido: boolean
  valor?: number
  error?: string
} {
  if (val === '' || val == null)
    return { valido: false, error: 'Ingrese el monto del pago.' }

  const num = Number(val.replace(',', '.'))

  if (Number.isNaN(num))
    return {
      valido: false,
      error: 'Monto no valido. Ingrese un numero (ej: 150.50).',
    }

  if (moneda === 'BS') {
    if (num < MIN_MONTO_BS_REPORTAR)
      return {
        valido: false,
        error: 'En bolivares el monto debe ser al menos 1 Bs.',
      }
    if (num > MAX_MONTO_BS_REPORTAR)
      return {
        valido: false,
        error: 'En bolivares el monto no puede superar 10.000.000 Bs.',
      }
    return { valido: true, valor: num }
  }

  if (num < MIN_MONTO)
    return {
      valido: false,
      error: 'El monto debe ser mayor a ' + String(MIN_MONTO) + '.',
    }

  return { valido: true, valor: num }
}
function validarFechaPago(fecha: string): { valido: boolean; error?: string } {
  if (!fecha || !fecha.trim()) {
    return {
      valido: false,
      error: 'Seleccione la fecha de pago en el calendario.',
    }
  }

  const hoy = new Date()

  hoy.setHours(0, 0, 0, 0)

  const d = new Date(fecha)

  if (Number.isNaN(d.getTime()))
    return {
      valido: false,
      error: 'Fecha no válida. Use el calendario para elegir la fecha.',
    }

  d.setHours(0, 0, 0, 0)

  if (d > hoy)
    return { valido: false, error: 'La fecha de pago no puede ser futura.' }

  return { valido: true }
}

function validarArchivo(file: File | null): {
  valido: boolean
  error?: string
} {
  if (!file)
    return {
      valido: false,
      error: 'Seleccione un archivo de comprobante (JPG, PNG o PDF).',
    }

  const type = (file.type || '').toLowerCase()

  const okType = ALLOWED_FILE_TYPES.some(
    t => type === t || (t === 'image/jpg' && type === 'image/jpeg')
  )

  if (!okType) {
    return { valido: false, error: 'Solo se permiten archivos JPG, PNG o PDF.' }
  }

  if (file.size > MAX_FILE_SIZE) {
    return {
      valido: false,
      error:
        'El comprobante no puede superar 5 MB. Reduzca el tamaño del archivo.',
    }
  }

  if (file.size < 4)
    return { valido: false, error: 'El archivo está vacío o no es válido.' }

  return { valido: true }
}

const INSTITUCIONES = [
  'BINANCE',

  'BNC',

  'Banco de Venezuela',

  'Mercantil',

  'Recibos',
]

const WHATSAPP_LINK = 'https://wa.me/584244579934'

const NOTIFICATION_DURATION_MS = 10000

type NotificationType = 'error' | 'success'

type NotificationState = { type: NotificationType; message: string } | null

function NotificationBanner({
  notification,
  onDismiss,
}: {
  notification: NotificationState
  onDismiss: () => void
}) {
  if (!notification) return null

  const isError = notification.type === 'error'

  return (
    <div
      role="alert"
      className={`flex w-full min-w-0 max-w-md items-center gap-2 rounded-xl border-2 px-3 py-3 shadow-lg sm:gap-3 sm:px-4 sm:py-3.5 ${
        isError
          ? 'border-red-700 bg-red-600 text-white'
          : 'border-emerald-700 bg-emerald-600 text-white'
      }`}
    >
      <span
        className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-white/20 sm:h-10 sm:w-10"
        aria-hidden
      >
        {isError ? (
          <svg
            className="h-6 w-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        ) : (
          <svg
            className="h-6 w-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        )}
      </span>

      <p className="min-w-0 flex-1 break-words text-sm font-semibold leading-snug sm:text-base">
        {notification.message}
      </p>

      <button
        type="button"
        onClick={onDismiss}
        className="flex min-h-[44px] min-w-[44px] flex-shrink-0 touch-manipulation items-center justify-center rounded-md p-2 hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white/50"
        aria-label="Cerrar notificación"
      >
        <svg
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>
  )
}

export type ReportePagoVariant = 'cobros' | 'infopagos'

export default function ReportePagoPage({
  variant = 'cobros',
}: {
  variant?: ReportePagoVariant
}) {
  const isInfopagos = variant === 'infopagos'

  const honeypotRef = useRef<HTMLInputElement>(null)

  const [step, setStep] = useState(0)

  const [loading, setLoading] = useState(false)

  const [cedula, setCedula] = useState('')

  const [nombre, setNombre] = useState('')

  const [emailParaVerificacion, setEmailParaVerificacion] = useState('')

  const [institucion, setInstitucion] = useState('')

  const [institucionOtros, setInstitucionOtros] = useState('')

  const [fechaPago, setFechaPago] = useState('')

  const [monto, setMonto] = useState('')

  const [moneda, setMoneda] = useState<'BS' | 'USD'>('BS')

  const [puedeReportarBs, setPuedeReportarBs] = useState(true)

  const [numeroDocumento, setNumeroDocumento] = useState('')

  const [archivo, setArchivo] = useState<File | null>(null)

  const [referencia, setReferencia] = useState('')

  const [enviado, setEnviado] = useState(false)

  const [reciboToken, setReciboToken] = useState<string | null>(null)

  const [pagoId, setPagoId] = useState<number | null>(null)

  const [descargandoRecibo, setDescargandoRecibo] = useState(false)

  const [aplicadoCuotas, setAplicadoCuotas] = useState<string | null>(null)

  const [infopagosEnRevision, setInfopagosEnRevision] = useState(false)

  const [messageForScreenReader, setMessageForScreenReader] = useState('')

  const [notification, setNotification] = useState<NotificationState>(null)

  const [montoAltoConfirmado, setMontoAltoConfirmado] = useState(false)

  const notificationTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  )

  const showNotification = (type: NotificationType, message: string) => {
    if (notificationTimeoutRef.current)
      clearTimeout(notificationTimeoutRef.current)

    setNotification({ type, message })

    notificationTimeoutRef.current = setTimeout(() => {
      setNotification(null)

      notificationTimeoutRef.current = null
    }, NOTIFICATION_DURATION_MS)
  }

  const dismissNotification = () => {
    if (notificationTimeoutRef.current)
      clearTimeout(notificationTimeoutRef.current)

    notificationTimeoutRef.current = null

    setNotification(null)
  }

  useEffect(
    () => () => {
      if (notificationTimeoutRef.current)
        clearTimeout(notificationTimeoutRef.current)
    },
    []
  )

  // Resetear confirmación de monto alto cuando cambia el monto o moneda
  useEffect(() => {
    setMontoAltoConfirmado(false)
  }, [monto, moneda])

  // Marcar flujo público para que, si intentan ir a login, vean "Acceso prohibido" y puedan volver

  useEffect(() => {
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY, '1')

    sessionStorage.setItem(
      PUBLIC_FLOW_SESSION_KEY + '_path',
      isInfopagos ? 'infopagos' : 'rapicredit-cobros'
    )
  }, [isInfopagos])

  const institucionFinal =
    institucion === 'Otros' ? institucionOtros : institucion

  const resetForm = (irAStep: number) => {
    setCedula('')

    setNombre('')

    setEmailParaVerificacion('')

    setInstitucion('')

    setInstitucionOtros('')

    setFechaPago('')

    setMonto('')

    setPuedeReportarBs(true)

    setMoneda('BS')

    setNumeroDocumento('')

    setArchivo(null)

    setReferencia('')

    setEnviado(false)

    setReciboToken(null)

    setPagoId(null)

    setAplicadoCuotas(null)

    setInfopagosEnRevision(false)

    setMontoAltoConfirmado(false)

    setStep(irAStep)
  }

  const stepAnnouncements: Record<number, string> = {
    0: 'Pantalla de bienvenida: reporte de pago',

    1: 'Paso 1: Ingrese su número de cédula',

    2: 'Paso 2: Camino de moneda y datos del pago',

    3: 'Paso 3: Institución financiera',

    4: 'Paso 4: Fecha y monto segun camino Bs. o USD',

    5: 'Paso 5: Número de documento u operación',

    6: 'Paso 6: Adjuntar comprobante',

    7: 'Paso 7: Confirmar y enviar',

    8: 'Reporte enviado correctamente',
  }

  const stepAnnouncement = stepAnnouncements[step] || `Paso ${step}`

  const handleValidarCedula = async () => {
    const v = normalizarCedulaParaProcesar(cedula)

    if (!v.valido) {
      showNotification('error', v.error ?? 'Cédula inválida.')

      return
    }

    const cedulaEnviar = v.valorParaEnviar!

    setLoading(true)

    try {
      const res = await validarCedulaPublico(
        cedulaEnviar,

        isInfopagos ? { origen: 'infopagos' } : undefined
      )

      if (!res.ok) {
        showNotification('error', res.error || 'Cédula no válida.')

        return
      }

      // Si el backend no envía el flag, no asumir Bs autorizado (seguridad)
      const puedeBs = res.puede_reportar_bs === true

      setPuedeReportarBs(puedeBs)

      if (!puedeBs) setMoneda('USD')

      setCedula(cedulaEnviar)

      setNombre(res.nombre || '')

      setEmailParaVerificacion(res.email ?? res.email_enmascarado ?? '')

      setStep(2)
    } catch (e: any) {
      showNotification('error', e?.message || 'Error al validar cédula.')
    } finally {
      setLoading(false)
    }
  }

  const handleEnviar = async () => {
    const vCedula = normalizarCedulaParaProcesar(cedula)

    if (!vCedula.valido) {
      showNotification('error', vCedula.error ?? 'Cédula inválida.')

      return
    }

    const cedulaEnviar = vCedula.valorParaEnviar!

    if (!institucionFinal.trim()) {
      showNotification('error', 'Seleccione la institución financiera.')

      return
    }

    if (institucionFinal.length > MAX_LENGTH_INSTITUCION) {
      showNotification(
        'error',
        'Nombre de institución demasiado largo. Redúzcalo.'
      )

      return
    }

    const vFecha = validarFechaPago(fechaPago)

    if (!vFecha.valido) {
      showNotification('error', vFecha.error ?? 'Fecha inválida.')

      return
    }

    const vMonto = validarMonto(monto, moneda)

    if (!vMonto.valido) {
      showNotification('error', vMonto.error ?? 'Monto inválido.')

      return
    }

    if (!numeroDocumento.trim()) {
      showNotification('error', 'Ingrese el número de documento u operación.')

      return
    }

    if (numeroDocumento.length > MAX_LENGTH_NUMERO_OPERACION) {
      showNotification(
        'error',
        'Número de documento u operación demasiado largo.'
      )

      return
    }

    const vArchivo = validarArchivo(archivo)

    if (!vArchivo.valido) {
      showNotification('error', vArchivo.error ?? 'Archivo inválido.')

      return
    }

    // Honeypot: si un bot rellenó el campo oculto, no enviar

    const honeypotValue = honeypotRef.current?.value?.trim() ?? ''

    if (honeypotValue) {
      showNotification(
        'error',
        'No se pudo procesar el envío. Intente de nuevo.'
      )

      return
    }

    const tipoCedula = cedulaEnviar.charAt(0).toUpperCase()

    const numeroCedula = cedulaEnviar.slice(1).replace(/\D/g, '')

    const form = new FormData()

    form.append('tipo_cedula', tipoCedula)

    form.append('numero_cedula', numeroCedula)

    form.append('contact_website', '') // honeypot: siempre vacío para usuarios reales

    form.append('fecha_pago', fechaPago)

    form.append('institucion_financiera', institucionFinal)

    form.append('numero_operacion', numeroDocumento)

    form.append('monto', String(monto))

    form.append('moneda', moneda)

    if (archivo) form.append('comprobante', archivo)

    setLoading(true)

    try {
      if (isInfopagos) {
        const res = await enviarReporteInfopagos(form)

        if (!res.ok) {
          showNotification('error', res.error || 'Error al enviar.')

          return
        }

        showNotification('success', res.mensaje || 'Pago registrado.')

        setReferencia(res.referencia_interna || '')

        setAplicadoCuotas(res.aplicado_a_cuotas ?? null)

        setInfopagosEnRevision(
          String(res.estado_reportado ?? '')
            .toLowerCase()
            .replace(/\s+/g, '_') === 'en_revision'
        )

        if (res.recibo_descarga_token) {
          setReciboToken(res.recibo_descarga_token)
          if (res.pago_id != null) setPagoId(res.pago_id)
        } else {
          setReciboToken(null)
          setPagoId(null)
        }

        setEnviado(true)

        setStep(8)
      } else {
        const res = await enviarReportePublico(form)

        if (!res.ok) {
          showNotification('error', res.error || 'Error al enviar.')

          return
        }

        showNotification(
          'success',
          res.mensaje || 'Reporte de pago enviado correctamente.'
        )

        setReferencia(res.referencia_interna || '')

        setEnviado(true)

        setStep(8)
      }
    } catch (e: any) {
      showNotification('error', e?.message || 'Error al enviar el reporte.')
    } finally {
      setLoading(false)
    }
  }

  const handleDescargarRecibo = async () => {
    if (!reciboToken || pagoId == null) return

    setDescargandoRecibo(true)

    try {
      const blob = await getReciboInfopagos(reciboToken, pagoId)

      const url = window.URL.createObjectURL(blob)

      const a = document.createElement('a')

      a.href = url

      a.download = `recibo_${referencia || 'pago'}.pdf`

      document.body.appendChild(a)

      a.click()

      document.body.removeChild(a)

      window.URL.revokeObjectURL(url)
    } catch (e: any) {
      showNotification('error', e?.message || 'No se pudo descargar el recibo.')
    } finally {
      setDescargandoRecibo(false)
    }
  }

  // Pantalla de bienvenida con instrucciones generales (logo y colores RapiCredit: azul oscuro, naranja/marrón)

  const LOGO_PUBLIC_SRC = `${(import.meta.env.BASE_URL || '/').replace(/\/?$/, '')}/logos/rapicredit-public.png`

  if (step === 0) {
    const steps = isInfopagos
      ? [
          {
            icon: 'id' as const,
            text: 'Cédula del deudor',
            desc: '(V, E, G o J + dígitos)',
          },
          {
            icon: 'path' as const,
            text: 'Seleccionar moneda',
            desc: 'Bs. o USD según autorización',
          },
          {
            icon: 'bank' as const,
            text: 'Datos del pago',
            desc: 'Institución, fecha, monto y operación',
          },
          {
            icon: 'file' as const,
            text: 'Comprobante',
            desc: 'JPG, PNG o PDF, máx. 5 MB',
          },
          {
            icon: 'check' as const,
            text: 'Confirmar y enviar',
            desc: 'Recibo al correo registrado',
          },
        ]
      : [
          {
            icon: 'id' as const,
            text: 'Tu cédula',
            desc: '(V, E, G o J + dígitos)',
          },
          {
            icon: 'path' as const,
            text: 'Tu moneda',
            desc: 'Bs. o USD según tu cuenta',
          },
          {
            icon: 'bank' as const,
            text: 'Datos del pago',
            desc: 'Banco, fecha, monto y número',
          },
          {
            icon: 'file' as const,
            text: 'Comprobante',
            desc: 'JPG, PNG o PDF, máx. 5 MB',
          },
          {
            icon: 'check' as const,
            text: 'Confirmar y enviar',
            desc: 'Confirmación por correo',
          },
        ]

    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className="w-full max-w-4xl">
          {/* Main container con layout responsive */}
          <div className="grid gap-6 lg:grid-cols-2 lg:gap-8">
            {/* Sección izquierda: Branding */}
            <div className="flex flex-col justify-center space-y-6 px-2 sm:px-0">
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <img
                    src={LOGO_PUBLIC_SRC}
                    alt="RapiCredit"
                    className="h-12 object-contain sm:h-14"
                  />
                  <div>
                    <p className="text-2xl font-bold text-white sm:text-3xl">
                      RapiCredit
                    </p>
                    <p className="text-xs text-slate-400 sm:text-sm">
                      Sistema de Cobranza
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h1 className="text-3xl font-bold text-white sm:text-4xl">
                  {isInfopagos ? 'Registra pagos' : 'Reporta tu pago'}
                </h1>
                <p className="text-base leading-relaxed text-slate-300 sm:text-lg">
                  {isInfopagos
                    ? 'Registra el pago del deudor de forma segura. El recibo se enviará automáticamente al correo del deudor.'
                    : 'Reporta tu pago de forma segura. Te enviaremos la confirmación al correo registrado en tu contrato.'}
                </p>
              </div>

              {/* Info boxes */}
              <div className="space-y-3 pt-2">
                <div className="flex items-start gap-3 rounded-lg bg-white/10 p-3 backdrop-blur-sm">
                  <svg
                    className="h-5 w-5 flex-shrink-0 text-emerald-400 sm:h-6 sm:w-6"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-sm text-slate-200 sm:text-base">
                    Proceso rápido y seguro
                  </span>
                </div>
                <div className="flex items-start gap-3 rounded-lg bg-white/10 p-3 backdrop-blur-sm">
                  <svg
                    className="h-5 w-5 flex-shrink-0 text-emerald-400 sm:h-6 sm:w-6"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                    />
                  </svg>
                  <span className="text-sm text-slate-200 sm:text-base">
                    Datos cifrados y protegidos
                  </span>
                </div>
              </div>
            </div>

            {/* Sección derecha: Card con pasos */}
            <Card className="mx-1 border-0 bg-white shadow-2xl sm:mx-0">
              <CardContent className="space-y-4 p-5 sm:space-y-5 sm:p-6">
                <div className="border-b border-slate-100 pb-4">
                  <h2 className="text-xl font-semibold text-slate-900">
                    {isInfopagos ? 'Pasos del registro' : 'Cómo reportar'}
                  </h2>
                  <p className="mt-1 text-sm text-slate-600">
                    Sigue estos {steps.length} sencillos pasos
                  </p>
                </div>

                {/* Progress dots */}
                <div className="flex gap-1 sm:gap-1.5">
                  {steps.map((_, i) => (
                    <div
                      key={i}
                      className="h-1 flex-1 rounded-full bg-slate-200"
                    />
                  ))}
                </div>

                {/* Steps list */}
                <ul className="space-y-2" role="list">
                  {steps.map((item, i) => (
                    <li
                      key={i}
                      className="flex items-center gap-2.5 rounded-lg bg-slate-50 p-2.5 hover:bg-slate-100 transition-colors"
                    >
                      <span
                        className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-[#1e3a5f] text-xs font-semibold text-white"
                        aria-hidden
                      >
                        {i + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-slate-900 leading-tight">
                          {item.text}
                        </p>
                        <p className="text-xs text-slate-500 leading-tight">{item.desc}</p>
                      </div>
                    </li>
                  ))}
                </ul>

                {/* Info y CTA */}
                <div className="space-y-3 border-t border-slate-100 pt-4">
                  <p className="text-xs leading-snug text-slate-500">
                    Los datos se almacenarán de forma segura y se utilizarán
                    únicamente para verificar tu pago.
                  </p>
                  <Button
                    className="min-h-[48px] w-full touch-manipulation bg-[#1e3a5f] text-base font-semibold text-white shadow-md transition-all hover:bg-[#152a47] hover:shadow-lg"
                    size="lg"
                    onClick={() => setStep(1)}
                  >
                    {isInfopagos ? 'Comenzar' : 'Iniciar reportes'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Footer mínimo */}
          <div className="mt-6 text-center text-xs text-slate-400">
            <p>
              ¿Preguntas? Contacta a cobranza por
              <a
                href={WHATSAPP_LINK}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-1 text-emerald-400 underline hover:text-emerald-300"
              >
                WhatsApp
              </a>
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (step === 1) {
    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <input
          ref={honeypotRef}
          type="text"
          name="contact_website"
          autoComplete="off"
          tabIndex={-1}
          aria-hidden="true"
          style={{
            position: 'absolute',
            left: '-9999px',
            width: '1px',
            height: '1px',
            opacity: 0,
            pointerEvents: 'none',
          }}
        />

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-4 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md border-0 bg-white shadow-xl">
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  1
                </div>
                <CardTitle className="text-lg sm:text-xl m-0">
                  {isInfopagos ? 'Cédula del deudor' : 'Tu cédula'}
                </CardTitle>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                Formato: Letra (V, E, G o J) seguida de 6 a 11 dígitos. Sin puntos ni signos.
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-5 sm:px-6">
              <Input
                className="min-h-[48px] touch-manipulation bg-slate-50 border-slate-200"
                placeholder="Ej: V12345678 o 12345678"
                value={cedula}
                onChange={e => setCedula(normalizarCedulaInput(e.target.value))}
                onKeyDown={e => e.key === 'Enter' && handleValidarCedula()}
                maxLength={20}
              />

              <Button
                className="min-h-[48px] w-full touch-manipulation bg-slate-900 font-semibold text-white hover:bg-slate-800"
                onClick={handleValidarCedula}
                disabled={loading}
              >
                {loading ? 'Verificando...' : 'Continuar'}
              </Button>

              <p className="text-xs text-slate-500 text-center">
                Presiona Enter o haz clic en continuar
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (step === 2) {
    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-4 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md border-0 bg-white shadow-xl">
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  2
                </div>
                <CardTitle className="text-lg sm:text-xl m-0">
                  {isInfopagos ? `Deudor: ${nombre || '-'}` : `Hola, ${nombre || 'Cliente'}`}
                </CardTitle>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                {isInfopagos
                  ? 'Verifica la moneda disponible para este deudor'
                  : 'Selecciona la moneda en la que reportarás tu pago'}
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-5 sm:px-6">
              {puedeReportarBs ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  <button
                    onClick={() => setMoneda('BS')}
                    className={`relative rounded-lg border-2 p-4 text-left transition-all ${
                      moneda === 'BS'
                        ? 'border-emerald-500 bg-emerald-50'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <p className="font-semibold text-slate-900">Bolivares</p>
                    <p className="mt-1 text-xs text-slate-600">Bs.</p>
                    <p className="mt-2 text-xs leading-snug text-slate-500">
                      Monto: 1 a 10M Bs. Tasa oficial del día.
                    </p>
                    {moneda === 'BS' && (
                      <div className="absolute right-3 top-3 h-5 w-5 rounded-full bg-emerald-500 flex items-center justify-center">
                        <svg
                          className="h-3 w-3 text-white"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                    )}
                  </button>
                  <button
                    onClick={() => setMoneda('USD')}
                    className={`relative rounded-lg border-2 p-4 text-left transition-all ${
                      moneda === 'USD'
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <p className="font-semibold text-slate-900">Dólares</p>
                    <p className="mt-1 text-xs text-slate-600">USD / $</p>
                    <p className="mt-2 text-xs leading-snug text-slate-500">
                      Monto: cualquier cantidad válida en USD.
                    </p>
                    {moneda === 'USD' && (
                      <div className="absolute right-3 top-3 h-5 w-5 rounded-full bg-blue-500 flex items-center justify-center">
                        <svg
                          className="h-3 w-3 text-white"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                    )}
                  </button>
                </div>
              ) : (
                <div className="rounded-lg border-2 border-amber-300 bg-amber-50 p-4">
                  <p className="font-semibold text-amber-900">Solo dólares (USD)</p>
                  <p className="mt-2 text-sm leading-snug text-amber-900/80">
                    Esta cédula no está autorizada para reportar en bolivares.
                    Por favor, reporta el monto en USD.
                  </p>
                </div>
              )}

              <Button
                className="min-h-[48px] w-full touch-manipulation bg-slate-900 font-semibold text-white hover:bg-slate-800"
                onClick={() => setStep(3)}
              >
                Continuar
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (step === 3) {
    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-4 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md border-0 bg-white shadow-xl">
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  3
                </div>
                <CardTitle className="text-lg sm:text-xl m-0">
                  Institución financiera
                </CardTitle>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                Selecciona el banco o plataforma donde se realizó el pago
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-5 sm:px-6">
              <select
                className="min-h-[48px] w-full min-w-0 touch-manipulation rounded-lg border-2 border-slate-200 bg-white px-4 py-2.5 text-base font-medium focus:border-slate-900 focus:outline-none"
                value={institucion}
                onChange={e => setInstitucion(e.target.value)}
                aria-label="Seleccione la institución financiera"
              >
                <option value="">Selecciona una opción...</option>
                {INSTITUCIONES.map(opt => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>

              {institucion === 'Otros' && (
                <Input
                  className="min-h-[48px] touch-manipulation bg-slate-50 border-slate-200"
                  placeholder="Nombre del banco o plataforma"
                  value={institucionOtros}
                  onChange={e => setInstitucionOtros(e.target.value)}
                  maxLength={MAX_LENGTH_INSTITUCION}
                />
              )}

              <div className="flex flex-wrap gap-2 sm:flex-nowrap pt-2">
                <Button
                  variant="outline"
                  className="min-h-[48px] min-w-[100px] flex-1 touch-manipulation border-slate-300 text-slate-900 hover:bg-slate-50"
                  onClick={() => setStep(2)}
                >
                  Atrás
                </Button>

                <Button
                  className="min-h-[48px] min-w-0 flex-1 touch-manipulation bg-slate-900 font-semibold text-white hover:bg-slate-800"
                  onClick={() => {
                    if (!institucionFinal.trim()) {
                      showNotification(
                        'error',
                        'Selecciona la institución financiera.'
                      )
                      return
                    }

                    if (institucionFinal.length > MAX_LENGTH_INSTITUCION) {
                      showNotification(
                        'error',
                        'El nombre es demasiado largo. Redúcelo.'
                      )
                      return
                    }

                    setStep(4)
                  }}
                >
                  Siguiente
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (step === 4) {
    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-4 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md border-0 bg-white shadow-xl">
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  4
                </div>
                <CardTitle className="text-lg sm:text-xl m-0">
                  Fecha y monto
                </CardTitle>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                Modalidad: {moneda === 'BS' ? 'bolivares (Bs.)' : 'dólares (USD)'}
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-5 sm:px-6">
              <div className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                <p className="text-xs font-medium text-slate-700">
                  {moneda === 'BS' ? (
                    <>
                      Ingresa el monto en <strong>bolivares</strong>. El recibo
                      mostrará la <strong>tasa oficial del día</strong> de la
                      fecha de pago.
                    </>
                  ) : (
                    <>
                      Ingresa el monto en <strong>USD</strong>. El recibo y la
                      verificación serán en dólares.
                    </>
                  )}
                </p>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-900">
                  Fecha de pago
                </label>
                <Input
                  type="date"
                  className="min-h-[48px] w-full touch-manipulation bg-slate-50 border-slate-200"
                  value={fechaPago}
                  onChange={e => setFechaPago(e.target.value)}
                  max={new Date().toISOString().slice(0, 10)}
                  aria-label="Seleccione la fecha en el calendario"
                />
                <p className="mt-1 text-xs text-slate-500">
                  No puede ser una fecha futura
                </p>
              </div>

              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-900">
                  Monto
                </label>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Input
                    type="number"
                    step="0.01"
                    min={moneda === 'BS' ? MIN_MONTO_BS_REPORTAR : MIN_MONTO}
                    placeholder={moneda === 'BS' ? 'Ej: 1500.00' : 'Ej: 150.50'}
                    className="min-h-[48px] min-w-0 flex-1 touch-manipulation bg-slate-50 border-slate-200"
                    value={monto}
                    onChange={e => setMonto(e.target.value)}
                  />
                  <select
                    className="min-h-[48px] w-full flex-shrink-0 touch-manipulation rounded-lg border-2 border-slate-200 bg-white px-4 py-2.5 text-base font-medium focus:border-slate-900 focus:outline-none sm:w-24"
                    value={moneda}
                    onChange={e => setMoneda(e.target.value as 'BS' | 'USD')}
                    aria-label="Moneda"
                  >
                    {puedeReportarBs && <option value="BS">Bs.</option>}
                    <option value="USD">USD</option>
                  </select>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {moneda === 'BS'
                    ? 'Entre 1 y 10.000.000 Bs.'
                    : 'Ingresa el monto en USD (sin límite máximo)'}
                </p>
              </div>

              <div className="flex flex-wrap gap-2 sm:flex-nowrap pt-2">
                <Button
                  variant="outline"
                  className="min-h-[48px] min-w-[100px] flex-1 touch-manipulation border-slate-300 text-slate-900 hover:bg-slate-50"
                  onClick={() => setStep(3)}
                >
                  Atrás
                </Button>

                <Button
                  className="min-h-[48px] min-w-0 flex-1 touch-manipulation bg-slate-900 font-semibold text-white hover:bg-slate-800"
                  onClick={() => {
                    const vF = validarFechaPago(fechaPago)

                    if (!vF.valido) {
                      showNotification('error', vF.error ?? 'Fecha inválida.')
                      return
                    }

                    const vM = validarMonto(monto, moneda)

                    if (!vM.valido) {
                      showNotification('error', vM.error ?? 'Monto inválido.')
                      return
                    }

                    // Validar monto alto (>= 4000)
                    const montoNumerico = vM.valor ?? 0
                    if (montoNumerico >= 4000 && !montoAltoConfirmado) {
                      showNotification(
                        'error',
                        '⚠️ Monto alto - Verifica que sea en Bs y no en USD.'
                      )
                      setMontoAltoConfirmado(true)
                      return
                    }

                    setStep(5)
                  }}
                >
                  Siguiente
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (step === 5) {
    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-4 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md border-0 bg-white shadow-xl">
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  5
                </div>
                <CardTitle className="text-lg sm:text-xl m-0">
                  Número de operación
                </CardTitle>
              </div>
              <p className="mt-2 text-xs leading-snug text-slate-600">
                {TEXTO_AVISO_NUMERO_OPERACION_FORMULARIO}
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-5 sm:px-6">
              <Input
                className="min-h-[48px] touch-manipulation bg-slate-50 border-slate-200"
                placeholder="Número de serie, transacción o referencia"
                value={numeroDocumento}
                onChange={e => setNumeroDocumento(e.target.value)}
                maxLength={MAX_LENGTH_NUMERO_OPERACION}
              />

              <p className="text-xs text-slate-500">
                Máximo {MAX_LENGTH_NUMERO_OPERACION} caracteres
              </p>

              <div className="flex flex-wrap gap-2 sm:flex-nowrap pt-2">
                <Button
                  variant="outline"
                  className="min-h-[48px] min-w-[100px] flex-1 touch-manipulation border-slate-300 text-slate-900 hover:bg-slate-50"
                  onClick={() => setStep(4)}
                >
                  Atrás
                </Button>

                <Button
                  className="min-h-[48px] min-w-0 flex-1 touch-manipulation bg-slate-900 font-semibold text-white hover:bg-slate-800"
                  onClick={() => {
                    if (!numeroDocumento.trim()) {
                      showNotification(
                        'error',
                        'Ingresa el número de operación.'
                      )
                      return
                    }

                    if (numeroDocumento.length > MAX_LENGTH_NUMERO_OPERACION) {
                      showNotification(
                        'error',
                        'El número es demasiado largo.'
                      )
                      return
                    }

                    setStep(6)
                  }}
                >
                  Siguiente
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (step === 6) {
    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-4 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md border-0 bg-white shadow-xl">
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  6
                </div>
                <CardTitle className="text-lg sm:text-xl m-0">
                  Comprobante de pago
                </CardTitle>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                JPG, PNG o PDF. Máximo 5 MB.
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-5 sm:px-6">
              {archivo ? (
                <div className="rounded-lg border-2 border-emerald-300 bg-emerald-50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-emerald-900">
                        Archivo seleccionado
                      </p>
                      <p className="mt-1 break-all text-sm text-emerald-800">
                        {archivo.name}
                      </p>
                      <p className="mt-1 text-xs text-emerald-700">
                        {(archivo.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                    <div className="flex-shrink-0">
                      <svg
                        className="h-5 w-5 text-emerald-600"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </div>
                  </div>
                </div>
              ) : (
                <Input
                  type="file"
                  className="min-h-[48px] touch-manipulation file:mr-3 file:rounded-lg file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-slate-800"
                  accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
                  onChange={e => setArchivo(e.target.files?.[0] || null)}
                />
              )}

              <p className="text-xs text-slate-600">
                Carga el comprobante del pago realizado (factura de pago, captura de pantalla, etc.)
              </p>

              <div className="flex flex-wrap gap-2 sm:flex-nowrap pt-2">
                <Button
                  variant="outline"
                  className="min-h-[48px] min-w-[100px] flex-1 touch-manipulation border-slate-300 text-slate-900 hover:bg-slate-50"
                  onClick={() => {
                    setArchivo(null)
                    setStep(5)
                  }}
                >
                  Atrás
                </Button>

                <Button
                  className="min-h-[48px] min-w-0 flex-1 touch-manipulation bg-slate-900 font-semibold text-white hover:bg-slate-800"
                  onClick={() => {
                    const v = validarArchivo(archivo)

                    if (!v.valido) {
                      showNotification('error', v.error ?? 'Archivo inválido.')
                      return
                    }

                    setStep(7)
                  }}
                >
                  Siguiente
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (step === 7) {
    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-4 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md border-0 bg-white shadow-xl">
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  7
                </div>
                <CardTitle className="text-lg sm:text-xl m-0">
                  Confirma tus datos
                </CardTitle>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                Revisa la información antes de enviar
              </p>
            </CardHeader>

            <CardContent className="space-y-3 px-5 sm:px-6">
              {/* Summary grid */}
              <div className="space-y-2 rounded-lg bg-slate-50 p-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Cédula:</span>
                  <span className="font-semibold text-slate-900">{cedula}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Nombre:</span>
                  <span className="font-semibold text-slate-900">{nombre}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Institución:</span>
                  <span className="font-semibold text-slate-900 text-right">
                    {institucionFinal}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Fecha:</span>
                  <span className="font-semibold text-slate-900">{fechaPago}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Monto:</span>
                  <span className="font-semibold text-slate-900">
                    {monto} {moneda}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Operación:</span>
                  <span className="font-semibold text-slate-900">
                    {numeroDocumento}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Archivo:</span>
                  <span className="font-semibold text-slate-900 text-right max-w-[150px] truncate">
                    {archivo?.name}
                  </span>
                </div>
              </div>

              {/* Info note */}
              <div className="rounded-lg bg-blue-50 p-3 border border-blue-200">
                <p className="text-xs leading-snug text-blue-900">
                  {isInfopagos ? (
                    <>
                      El recibo se enviará a{' '}
                      <strong className="break-all">
                        {emailParaVerificacion || 'correo registrado'}
                      </strong>
                    </>
                  ) : (
                    <>
                      Se enviará confirmación a{' '}
                      <strong className="break-all">
                        {emailParaVerificacion || 'tu correo registrado'}
                      </strong>
                    </>
                  )}
                </p>
              </div>

              <div className="flex flex-wrap gap-2 sm:flex-nowrap pt-2">
                <Button
                  variant="outline"
                  className="min-h-[48px] min-w-[100px] flex-1 touch-manipulation border-slate-300 text-slate-900 hover:bg-slate-50"
                  onClick={() => setStep(6)}
                >
                  Editar
                </Button>

                <Button
                  className="min-h-[48px] min-w-0 flex-1 touch-manipulation bg-emerald-600 font-semibold text-white hover:bg-emerald-700"
                  onClick={handleEnviar}
                  disabled={loading}
                >
                  {loading ? 'Enviando...' : 'Confirmar y enviar'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  // step === 8: pantalla final de confirmación
  return (
    <div className="flex min-h-[100dvh] min-h-screen items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4">
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {messageForScreenReader || stepAnnouncement}
      </div>

      <Card className="mx-1 w-full min-w-0 max-w-md border-0 bg-white shadow-2xl sm:mx-0">
        <CardContent className="space-y-5 px-5 pt-6 sm:px-6 sm:pt-8">
          {/* Success icon */}
          <div className="flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 sm:h-20 sm:w-20">
              <svg
                className="h-8 w-8 text-emerald-600 sm:h-10 sm:w-10"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
          </div>

          {/* Title */}
          <div className="text-center space-y-2">
            <h2 className="text-xl font-bold text-slate-900 sm:text-2xl">
              {isInfopagos
                ? infopagosEnRevision
                  ? 'Reporte registrado'
                  : 'Pago confirmado'
                : 'Envío exitoso'}
            </h2>
            <p className="text-sm text-slate-600">
              {isInfopagos
                ? 'El pago del deudor ha sido registrado correctamente'
                : 'Tu pago ha sido recibido y se está procesando'}
            </p>
          </div>

          {/* Reference number */}
          <div className="rounded-lg bg-slate-50 p-4 text-center">
            <p className="text-xs font-semibold uppercase text-slate-600">
              Número de referencia
            </p>
            <p className="mt-2 break-all font-mono text-lg font-bold text-slate-900 select-all">
              {referencia?.startsWith('#') ? referencia : `#${referencia}`}
            </p>
            <p className="mt-2 text-xs text-slate-500">
              Guarda este número para seguimiento
            </p>
          </div>

          {/* Cuotas info */}
          {isInfopagos && aplicadoCuotas ? (
            <div className="rounded-lg border-2 border-blue-200 bg-blue-50 p-3">
              <p className="text-xs font-semibold text-blue-900">
                Abono aplicado a:
              </p>
              <p className="mt-1 font-mono text-sm text-blue-900">{aplicadoCuotas}</p>
            </div>
          ) : null}

          {/* Status message */}
          {isInfopagos ? (
            <div className="rounded-lg bg-amber-50 p-4 text-center border border-amber-200">
              <p className="text-sm text-amber-900">
                {infopagosEnRevision
                  ? 'Este reporte quedó en revisión manual. El recibo se enviará cuando sea aprobado.'
                  : 'Se envió el recibo al correo del deudor. Puedes descargarlo a continuación.'}
              </p>
            </div>
          ) : (
            <div className="rounded-lg bg-blue-50 p-4 text-center border border-blue-200">
              <p className="text-sm text-blue-900">
                El recibo PDF será enviado a tu correo en los próximos minutos.
              </p>
            </div>
          )}

          {/* Download button */}
          {isInfopagos && !infopagosEnRevision && reciboToken && pagoId != null && (
            <Button
              className="min-h-[48px] w-full touch-manipulation bg-blue-600 font-semibold text-white hover:bg-blue-700"
              onClick={handleDescargarRecibo}
              disabled={descargandoRecibo}
            >
              {descargandoRecibo ? 'Descargando...' : '⬇️ Descargar recibo (PDF)'}
            </Button>
          )}

          {/* Action buttons */}
          <div className="flex flex-col gap-3 pt-4 sm:flex-row">
            <Button
              variant="outline"
              className="min-h-[48px] flex-1 touch-manipulation border-slate-300 text-slate-900 hover:bg-slate-50"
              onClick={() => resetForm(0)}
            >
              Terminar
            </Button>

            <Button
              className="min-h-[48px] flex-1 touch-manipulation bg-slate-900 font-semibold text-white hover:bg-slate-800"
              onClick={() => resetForm(1)}
            >
              {isInfopagos ? 'Otro pago' : 'Otro reporte'}
            </Button>
          </div>

          {/* Support info */}
          <div className="border-t border-slate-100 pt-4 text-center">
            <p className="text-xs text-slate-600">
              ¿Necesitas ayuda?{' '}
              <a
                href={WHATSAPP_LINK}
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-emerald-600 hover:text-emerald-700"
              >
                Contacta por WhatsApp
              </a>
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
