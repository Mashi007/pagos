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

  if (num > MAX_MONTO)
    return {
      valido: false,
      error: 'Monto demasiado alto. Revise el valor e intente de nuevo.',
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

  const [messageForScreenReader, setMessageForScreenReader] = useState('')

  const [notification, setNotification] = useState<NotificationState>(null)

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

        if (res.recibo_descarga_token) setReciboToken(res.recibo_descarga_token)

        if (res.pago_id != null) setPagoId(res.pago_id)

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
            text: 'Ingrese la cédula del deudor (V, E, G o J + dígitos).',
          },

          {
            icon: 'path' as const,
            text: 'Segun la cedula: si esta autorizada para bolivares podra elegir Bs. o USD; si no, solo USD.',
          },

          {
            icon: 'bank' as const,
            text: 'Indique institución financiera, fecha, monto y número de operación.',
          },

          {
            icon: 'file' as const,
            text: 'Adjunte el comprobante de pago (JPG, PNG o PDF, máx. 5 MB).',
          },

          {
            icon: 'check' as const,
            text: 'Al enviar, el recibo se enviará al correo del deudor y podrá descargarlo aquí.',
          },
        ]
      : [
          {
            icon: 'id' as const,
            text: 'Ingrese su número de cédula (V, E, G o J + dígitos).',
          },

          {
            icon: 'path' as const,
            text: 'Segun su cedula: autorizada en bolivares podra elegir Bs. o USD; de lo contrario, solo USD.',
          },

          {
            icon: 'bank' as const,
            text: 'Indique institución financiera, fecha, monto y número de operación.',
          },

          {
            icon: 'file' as const,
            text: 'Adjunte el comprobante de pago (JPG, PNG o PDF, máx. 5 MB).',
          },

          {
            icon: 'check' as const,
            text: 'Revise los datos y envíe. Recibirá confirmación al correo registrado.',
          },
        ]

    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-50 via-[#e8eef5] to-slate-100 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <Card className="mx-1 w-full min-w-0 max-w-lg overflow-hidden border border-slate-200/80 shadow-2xl sm:mx-0">
          {/* Header con logo RapiCredit: fondo blanco para compatibilidad del logo */}

          <div className="rounded-t-lg border-b border-slate-100 bg-white px-4 py-5 text-center sm:px-6 sm:py-6">
            <div className="inline-flex flex-col items-center justify-center">
              <img
                src={LOGO_PUBLIC_SRC}
                alt="RapiCredit"
                className="mx-auto h-14 object-contain sm:h-16"
              />

              <p className="mt-2 text-sm font-semibold text-[#c4a35a] sm:mt-3 sm:text-base">
                {isInfopagos ? 'Infopagos' : 'Reporte de pago'}
              </p>
            </div>
          </div>

          <CardContent className="space-y-5 p-4 sm:space-y-6 sm:p-6 md:p-8">
            <div className="text-center">
              <h2 className="text-lg font-semibold text-[#1e3a5f] sm:text-xl">
                {isInfopagos ? 'Pago a nombre del deudor' : 'Bienvenido'}
              </h2>

              <p className="mt-2 text-sm leading-relaxed text-slate-600">
                {isInfopagos
                  ? 'Registre el pago del deudor. El recibo se enviará a su correo y podrá descargarlo aquí para compartirlo.'
                  : 'Reporte su pago de forma segura para que sea verificado por cobranza.'}
              </p>
            </div>

            <ul className="space-y-3" role="list">
              {steps.map((item, i) => (
                <li
                  key={i}
                  className="flex items-start gap-3 text-sm text-slate-700"
                >
                  <span
                    className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[#1e3a5f]/10 text-[#1e3a5f]"
                    aria-hidden
                  >
                    {item.icon === 'id' && (
                      <svg
                        className="h-4 w-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2"
                        />
                      </svg>
                    )}

                    {item.icon === 'bank' && (
                      <svg
                        className="h-4 w-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                        />
                      </svg>
                    )}

                    {item.icon === 'path' && (
                      <svg
                        className="h-4 w-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 4v5m-3 3l3-3 3 3M12 9v11M7 20h10"
                        />
                      </svg>
                    )}

                    {item.icon === 'file' && (
                      <svg
                        className="h-4 w-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                    )}

                    {item.icon === 'check' && (
                      <svg
                        className="h-4 w-4"
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
                    )}
                  </span>

                  <span className="pt-1">{item.text}</span>
                </li>
              ))}
            </ul>

            <p className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-center text-xs text-slate-500">
              Los datos se comprobarán y almacenarán únicamente para validación
              del pago.
            </p>

            <p className="text-center text-xs text-slate-500">
              Si desea reportar más de un pago, al finalizar cada envío use el
              botón «Ingresar otro pago» o reinicie el proceso.
            </p>

            <Button
              className="min-h-[48px] w-full touch-manipulation bg-[#1e3a5f] py-5 text-base font-semibold text-white shadow-md transition-all hover:bg-[#152a47] hover:shadow-lg sm:py-6"
              size="lg"
              onClick={() => setStep(1)}
            >
              {isInfopagos ? 'Registrar pago del deudor' : 'Iniciar reporte'}
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (step === 1) {
    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-slate-50 p-3 sm:p-4">
        {/* Zona de mensajes para lectores de pantalla (aria-live) */}

        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        {/* Honeypot: campo oculto para usuarios, visible para bots. No usar en navegación ni leer en pantalla. */}

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

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-3 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md">
            <CardHeader className="px-4 pb-2 sm:px-6">
              <CardTitle className="text-lg sm:text-xl">
                {isInfopagos ? 'Cédula del deudor' : 'Reporte de pago'}
              </CardTitle>

              <p className="mt-1 text-sm text-gray-600">
                Solo letra (V, E, G o J) y 6 a 11 dígitos. No use puntos ni
                signos. Si solo ingresa números se procesará con V.
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-4 sm:px-6">
              <Input
                className="min-h-[44px] touch-manipulation"
                placeholder="Ej: V12345678, E12345678 o 12345678"
                value={cedula}
                onChange={e => setCedula(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleValidarCedula()}
                maxLength={20}
              />

              <Button
                className="min-h-[48px] w-full touch-manipulation"
                onClick={handleValidarCedula}
                disabled={loading}
              >
                {loading ? 'Verificando...' : 'Continuar'}
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (step === 2) {
    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-slate-50 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-3 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md">
            <CardHeader className="px-4 sm:px-6">
              <CardTitle className="text-lg sm:text-xl">
                {isInfopagos ? 'Deudor: ' : 'Hola, '}
                {nombre || (isInfopagos ? '-' : 'Cliente')}
              </CardTitle>

              <p className="mt-2 text-sm text-gray-600">
                {isInfopagos
                  ? 'Ingrese los datos del pago del deudor. El recibo se enviará a su correo registrado.'
                  : 'Recuerda ingresar únicamente datos de tu pago que se comprobarán y almacenarán para fines de validación de pago.'}
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-4 sm:px-6">
              <div
                role="region"
                aria-label="Opciones de moneda segun su cedula"
                className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 text-sm text-slate-700"
              >
                <p className="font-semibold text-[#1e3a5f]">
                  Su camino de reporte (moneda)
                </p>
                {puedeReportarBs ? (
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-md border border-emerald-200 bg-white p-3 shadow-sm">
                      <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
                        Bolivares (Bs.)
                      </p>
                      <p className="mt-1 text-xs leading-snug text-slate-600">
                        Puede reportar en bolivares. El recibo usara la tasa
                        oficial del dia de su fecha de pago; en sistema se
                        registra el equivalente en USD con esa misma tasa. Monto
                        permitido: 1 a 10.000.000 Bs.
                      </p>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-white p-3 shadow-sm">
                      <p className="text-xs font-semibold uppercase tracking-wide text-[#1e3a5f]">
                        Dolares (USD)
                      </p>
                      <p className="mt-1 text-xs leading-snug text-slate-600">
                        Tambien puede reportar en USD. El monto y el recibo iran
                        en dolares.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">
                      Solo dolares (USD)
                    </p>
                    <p className="mt-1 text-xs leading-snug text-amber-950/90">
                      Su cedula no esta en la lista para pagos en bolivares.
                      Indique el monto en USD; el recibo y la verificacion seran
                      en dolares.
                    </p>
                  </div>
                )}
              </div>

              <Button
                className="min-h-[48px] w-full touch-manipulation"
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
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-slate-50 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-3 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md">
            <CardHeader className="px-4 sm:px-6">
              <CardTitle className="text-lg sm:text-xl">
                Institución financiera
              </CardTitle>
            </CardHeader>

            <CardContent className="space-y-4 px-4 sm:px-6">
              <select
                className="min-h-[44px] w-full min-w-0 touch-manipulation rounded-md border bg-white px-3 py-2.5 text-base"
                value={institucion}
                onChange={e => setInstitucion(e.target.value)}
                aria-label="Seleccione la institución financiera"
              >
                <option value="">Seleccione...</option>

                {INSTITUCIONES.map(opt => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>

              {institucion === 'Otros' && (
                <Input
                  className="min-h-[44px] touch-manipulation"
                  placeholder="Nombre del banco"
                  value={institucionOtros}
                  onChange={e => setInstitucionOtros(e.target.value)}
                  maxLength={MAX_LENGTH_INSTITUCION}
                />
              )}

              <div className="flex flex-wrap gap-2 sm:flex-nowrap">
                <Button
                  variant="outline"
                  className="min-h-[48px] min-w-[100px] flex-1 touch-manipulation"
                  onClick={() => setStep(2)}
                >
                  Atrás
                </Button>

                <Button
                  className="min-h-[48px] min-w-0 flex-1 touch-manipulation"
                  onClick={() => {
                    if (!institucionFinal.trim()) {
                      showNotification(
                        'error',
                        'Seleccione la institución financiera.'
                      )

                      return
                    }

                    if (institucionFinal.length > MAX_LENGTH_INSTITUCION) {
                      showNotification(
                        'error',
                        'Nombre de institución demasiado largo. Redúzcalo.'
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
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-slate-50 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-3 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md">
            <CardHeader className="space-y-2 px-4 sm:px-6">
              <CardTitle className="text-lg sm:text-xl">
                Fecha y monto del pago
              </CardTitle>

              <p className="text-sm font-medium text-[#1e3a5f]">
                {moneda === 'BS'
                  ? 'Camino activo: bolivares (Bs.)'
                  : 'Camino activo: dolares (USD)'}
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-4 sm:px-6">
              <div
                role="status"
                className={
                  moneda === 'BS'
                    ? 'rounded-md border border-emerald-200 bg-emerald-50/80 p-3 text-xs leading-snug text-emerald-950'
                    : 'rounded-md border border-slate-200 bg-white p-3 text-xs leading-snug text-slate-700'
                }
              >
                {moneda === 'BS' ? (
                  <p>
                    Indique el monto de su comprobante en{' '}
                    <strong>bolivares</strong>. El recibo mostrara el monto en
                    Bs. y la{' '}
                    <strong>tasa oficial del dia de la fecha de pago</strong>.
                    En sistema se guarda el equivalente en USD con esa misma
                    tasa.
                  </p>
                ) : (
                  <p>
                    Indique el monto en <strong>dolares (USD)</strong>. El
                    recibo y la verificacion usaran USD.
                  </p>
                )}
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Fecha de pago (obligatorio)
                </label>

                <Input
                  type="date"
                  className="min-h-[44px] w-full touch-manipulation"
                  value={fechaPago}
                  onChange={e => setFechaPago(e.target.value)}
                  max={new Date().toISOString().slice(0, 10)}
                  aria-label="Seleccione la fecha en el calendario"
                />

                <p className="mt-1 text-xs text-gray-500">
                  Seleccione la fecha en el calendario. No puede ser futura.
                </p>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Monto (obligatorio)
                </label>

                <div className="flex flex-col gap-2 sm:flex-row">
                  <Input
                    type="number"
                    step="0.01"
                    min={moneda === 'BS' ? MIN_MONTO_BS_REPORTAR : MIN_MONTO}
                    max={moneda === 'BS' ? MAX_MONTO_BS_REPORTAR : MAX_MONTO}
                    placeholder={moneda === 'BS' ? 'Ej: 1500.00' : 'Ej: 150.50'}
                    className="min-h-[44px] min-w-0 flex-1 touch-manipulation"
                    value={monto}
                    onChange={e => setMonto(e.target.value)}
                  />

                  <select
                    className="min-h-[44px] w-full flex-shrink-0 touch-manipulation rounded-md border bg-white px-3 py-2.5 text-base sm:w-24"
                    value={moneda}
                    onChange={e => setMoneda(e.target.value as 'BS' | 'USD')}
                    aria-label="Moneda"
                  >
                    {puedeReportarBs && <option value="BS">Bs.</option>}

                    <option value="USD">USD / $</option>
                  </select>
                </div>

                <p className="mt-1 text-xs text-gray-500">
                  {moneda === 'BS'
                    ? 'En bolivares: entre 1 y 10.000.000 Bs. La fecha de pago define la tasa en el recibo.'
                    : 'En USD: mayor a 0. Maximo permitido 999.999.999,99.'}
                </p>
              </div>

              <div className="flex flex-wrap gap-2 sm:flex-nowrap">
                <Button
                  variant="outline"
                  className="min-h-[48px] min-w-[100px] flex-1 touch-manipulation"
                  onClick={() => setStep(3)}
                >
                  Atrás
                </Button>

                <Button
                  className="min-h-[48px] min-w-0 flex-1 touch-manipulation"
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
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-slate-50 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-3 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md">
            <CardHeader className="px-4 sm:px-6">
              <CardTitle className="text-lg sm:text-xl">
                Número de documento / operación
              </CardTitle>
            </CardHeader>

            <CardContent className="space-y-4 px-4 sm:px-6">
              <Input
                className="min-h-[44px] touch-manipulation"
                placeholder="Número de serie, operación o referencia"
                value={numeroDocumento}
                onChange={e => setNumeroDocumento(e.target.value)}
                maxLength={MAX_LENGTH_NUMERO_OPERACION}
              />

              <p className="text-xs text-gray-500">
                Máximo {MAX_LENGTH_NUMERO_OPERACION} caracteres.
              </p>

              <div className="flex flex-wrap gap-2 sm:flex-nowrap">
                <Button
                  variant="outline"
                  className="min-h-[48px] min-w-[100px] flex-1 touch-manipulation"
                  onClick={() => setStep(4)}
                >
                  Atrás
                </Button>

                <Button
                  className="min-h-[48px] min-w-0 flex-1 touch-manipulation"
                  onClick={() => {
                    if (!numeroDocumento.trim()) {
                      showNotification(
                        'error',
                        'Ingrese el número de documento u operación.'
                      )

                      return
                    }

                    if (numeroDocumento.length > MAX_LENGTH_NUMERO_OPERACION) {
                      showNotification(
                        'error',
                        'Número de documento demasiado largo.'
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
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-slate-50 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-3 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md">
            <CardHeader className="px-4 sm:px-6">
              <CardTitle className="text-lg sm:text-xl">
                Comprobante de pago
              </CardTitle>

              <p className="text-sm text-gray-600">
                Un solo archivo por envío. JPG, PNG o PDF. Máximo 5 MB.
              </p>

              <p className="mt-1 text-xs text-amber-700">
                Si desea reportar otro pago, al finalizar use «Ingresar otro
                pago» o reinicie el proceso.
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-4 sm:px-6">
              {archivo ? (
                <>
                  <div className="break-words rounded-lg border border-gray-200 bg-gray-50 px-3 py-3 text-sm text-gray-700">
                    <p className="font-medium">Comprobante seleccionado:</p>

                    <p className="mt-1 break-all">
                      {archivo.name} ({(archivo.size / 1024).toFixed(1)} KB)
                    </p>

                    <p className="mt-2 text-xs text-amber-700">
                      No se puede agregar otra imagen en este envío. Para otro
                      pago, finalice y use «Ingresar otro pago».
                    </p>
                  </div>
                </>
              ) : (
                <Input
                  type="file"
                  className="min-h-[44px] touch-manipulation file:mr-2 file:rounded-md file:border-0 file:bg-[#1e3a5f] file:px-4 file:py-2 file:text-sm file:font-medium file:text-white"
                  accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
                  onChange={e => setArchivo(e.target.files?.[0] || null)}
                />
              )}

              <div className="flex flex-wrap gap-2 sm:flex-nowrap">
                <Button
                  variant="outline"
                  className="min-h-[48px] min-w-[100px] flex-1 touch-manipulation"
                  onClick={() => {
                    setArchivo(null)
                    setStep(5)
                  }}
                >
                  Atrás
                </Button>

                <Button
                  className="min-h-[48px] min-w-0 flex-1 touch-manipulation"
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
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-slate-50 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-3 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <Card className="w-full min-w-0 max-w-md">
            <CardHeader className="px-4 sm:px-6">
              <CardTitle className="text-lg sm:text-xl">
                Confirma los siguientes datos
              </CardTitle>
            </CardHeader>

            <CardContent className="space-y-2 break-words px-4 text-sm sm:px-6">
              <p>
                <strong>Cédula:</strong> {cedula}
              </p>

              <p>
                <strong>Nombre:</strong> {nombre}
              </p>

              <p>
                <strong>Institución:</strong> {institucionFinal}
              </p>

              <p>
                <strong>Fecha de pago:</strong> {fechaPago}
              </p>

              <p>
                <strong>Monto:</strong> {monto} {moneda}
              </p>

              <p className="text-xs text-slate-600">
                {moneda === 'BS'
                  ? 'Recibo en bolivares; tasa oficial del dia de la fecha de pago. Equivalente USD en sistema con esa tasa.'
                  : 'Recibo y registro en dolares (USD).'}
              </p>

              <p>
                <strong>Número de operación:</strong> {numeroDocumento}
              </p>

              <p>
                <strong>Comprobante:</strong> {archivo?.name}
              </p>
            </CardContent>

            <CardContent className="space-y-3 px-4 pt-0 sm:px-6">
              <p className="break-words text-sm text-gray-600">
                {isInfopagos ? (
                  <>
                    El recibo se enviará al correo del deudor (
                    <span className="break-all rounded bg-blue-50 px-1.5 py-0.5 font-semibold text-[#1e3a5f]">
                      {emailParaVerificacion || 'correo registrado'}
                    </span>
                    ) y podrá descargarlo aquí al finalizar.
                  </>
                ) : (
                  <>
                    Tu pago se procesará y se enviará al correo registrado en tu
                    contrato de financiamiento (
                    <span className="break-all rounded bg-blue-50 px-1.5 py-0.5 font-semibold text-[#1e3a5f]">
                      {emailParaVerificacion || 'correo registrado'}
                    </span>
                    ). Si tienes algún problema con el correo, contacta a{' '}
                    <a
                      href="mailto:cobranza@rapicreditca.com"
                      className="break-all font-semibold text-[#1e3a5f] underline hover:no-underline"
                    >
                      cobranza@rapicreditca.com
                    </a>{' '}
                    o a tu asesor para actualización.
                  </>
                )}
              </p>

              <div className="flex flex-wrap gap-2 sm:flex-nowrap">
                <Button
                  variant="outline"
                  className="min-h-[48px] min-w-[100px] flex-1 touch-manipulation"
                  onClick={() => setStep(6)}
                >
                  No, editar
                </Button>

                <Button
                  className="min-h-[48px] min-w-0 flex-1 touch-manipulation"
                  onClick={handleEnviar}
                  disabled={loading}
                >
                  {loading ? 'Enviando...' : 'Sí, enviar'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  // step === 8: confirmación final

  return (
    <div className="flex min-h-[100dvh] min-h-screen items-center justify-center overflow-x-hidden bg-slate-50 p-3 sm:p-4">
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {messageForScreenReader || stepAnnouncement}
      </div>

      <Card className="mx-1 w-full min-w-0 max-w-md text-center sm:mx-0">
        <CardHeader className="px-4 sm:px-6">
          <CardTitle className="text-base text-green-700 sm:text-lg">
            {isInfopagos
              ? 'Pago registrado correctamente.'
              : 'Tu reporte de pago fue recibido exitosamente.'}
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-4 px-4 sm:px-6">
          <div className="break-words text-base sm:text-lg">
            <p className="font-semibold">Número de referencia:</p>

            <p
              className="mt-1 inline-block select-all break-all rounded bg-gray-100 px-2 py-1 font-mono"
              title="Copiar"
            >
              {referencia?.startsWith('#') ? referencia : `#${referencia}`}
            </p>
          </div>

          {isInfopagos && aplicadoCuotas ? (
            <div className="rounded-md border border-slate-200 bg-slate-100 px-3 py-2 text-left text-sm">
              <p className="font-semibold text-[#1e3a5f]">Abono aplicado a</p>

              <p className="mt-1 font-mono text-slate-800">{aplicadoCuotas}</p>

              <p className="mt-1 text-xs text-slate-600">
                Mismo dato aparece en el PDF del recibo.
              </p>
            </div>
          ) : null}

          {isInfopagos ? (
            <>
              <p className="text-sm text-gray-600">
                Se envió el recibo al correo registrado del deudor (según
                cédula). Puede descargar el recibo aquí para compartirlo.
              </p>

              {reciboToken && pagoId != null && (
                <Button
                  className="min-h-[48px] w-full touch-manipulation gap-2"
                  onClick={handleDescargarRecibo}
                  disabled={descargandoRecibo}
                >
                  {descargandoRecibo
                    ? 'Descargando...'
                    : 'Descargar recibo (PDF)'}
                </Button>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-600">
              El recibo (PDF) se enviará a tu correo registrado en un plazo de
              hasta 24 horas.
            </p>
          )}

          <p className="break-words text-sm">
            Si necesitas información adicional, comunícate con nosotros por
            WhatsApp:{' '}
            <a
              href={WHATSAPP_LINK}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 underline"
            >
              424-4579934
            </a>
          </p>

          <div className="flex flex-col gap-3 pt-4 sm:flex-row">
            <Button
              variant="outline"
              className="min-h-[48px] flex-1 touch-manipulation"
              onClick={() => resetForm(0)}
            >
              {isInfopagos ? 'Terminar' : 'Termina'}
            </Button>

            <Button
              className="min-h-[48px] flex-1 touch-manipulation bg-[#1e3a5f] hover:bg-[#152a47]"
              onClick={() => resetForm(1)}
            >
              {isInfopagos ? 'Registrar otro pago' : 'Ingresar otro pago'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
