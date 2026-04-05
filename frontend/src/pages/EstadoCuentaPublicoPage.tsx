/**





 * Consulta PÚBLICA de estado de cuenta por cédula.





 * Flujo: bienvenida → ingresar cédula → bienvenida con nombre → PDF + envío al email.





 * Sin login. Misma lógica y seguridades que rapicredit-cobros (rate limit, validación).





 * Marca sesión para que, si intentan ir a login/sistema, vean "Acceso prohibido" y puedan volver aquí.





 */

import React, { useState, useEffect, useRef } from 'react'
import { useIsMobile } from '../hooks/useIsMobile'

import {
  validarCedulaEstadoCuenta,
  solicitarCodigo,
  verificarCodigo,
  type ReciboCuotaItem,
} from '../services/estadoCuentaService'

import { PUBLIC_FLOW_SESSION_KEY } from '../config/env'

import { Button } from '../components/ui/button'

import { Input } from '../components/ui/input'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

const CEDULA_REGEX = /^[VEGJ]\d{6,11}$/i

/** Logo marca (misma ruta que rapicredit-cobros; ver public/logos/README.md). */
const LOGO_PUBLIC_SRC = `${(import.meta.env.BASE_URL || '/').replace(/\/?$/, '')}/logos/rapicredit-public.png`

/** Enlace de atención al cliente (mismo número que cobros público). */
const WHATSAPP_ATENCION_HREF = 'https://wa.me/584244579934'

function WhatsAppIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
    >
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.435 9.884-9.883 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
    </svg>
  )
}

function AtencionClienteWhatsAppLink({
  className,
  compact,
}: {
  className?: string
  compact?: boolean
}) {
  return (
    <a
      href={WHATSAPP_ATENCION_HREF}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Atención al cliente por WhatsApp"
      className={
        compact
          ? `inline-flex items-center gap-2 rounded-full bg-[#25D366] px-4 py-2 text-sm font-semibold text-white shadow-md transition hover:bg-[#20bd5a] focus:outline-none focus:ring-2 focus:ring-[#25D366]/50 ${className ?? ''}`
          : `flex w-full items-center justify-center gap-3 rounded-2xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-white px-4 py-3.5 text-left shadow-sm transition hover:border-emerald-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-emerald-400/40 sm:py-4 ${className ?? ''}`
      }
    >
      <span
        className={
          compact
            ? 'flex h-8 w-8 items-center justify-center rounded-full bg-white/20'
            : 'flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-[#25D366] text-white shadow-inner'
        }
        aria-hidden
      >
        <WhatsAppIcon className={compact ? 'h-5 w-5' : 'h-7 w-7'} />
      </span>
      <span className={compact ? '' : 'min-w-0 flex-1'}>
        <span
          className={
            compact
              ? 'block text-sm font-bold text-white'
              : 'block font-bold text-emerald-900'
          }
        >
          Atención al cliente (WhatsApp)
        </span>
        {!compact && (
          <span className="mt-0.5 block text-sm font-normal text-slate-600">
            ¿Dudas? Escríbenos y te ayudamos.
          </span>
        )}
      </span>
    </a>
  )
}

/** Normaliza para validar: quita espacios, guiones y puntos. Si solo 6-11 dígitos, al procesar se antepone V. No acepta puntos ni signos intermedios. */

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

type NotificationState = { type: 'error' | 'success'; message: string } | null

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
      className={`flex w-full min-w-0 max-w-md items-center gap-3 rounded-2xl border-2 px-4 py-4 shadow-xl backdrop-blur-sm sm:px-5 ${
        isError
          ? 'border-red-700 bg-red-600/95 text-white'
          : 'border-emerald-700 bg-emerald-600/95 text-white'
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

/** Convierte base64 PDF en blob URL para el visor inline. */
function base64ToBlobUrl(b64: string): string {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }))
}

function EstadoCuentaPublicoPage() {
  const [step, setStep] = useState(0)

  const [cedula, setCedula] = useState('')

  const [codigo, setCodigo] = useState('')

  const [loading, setLoading] = useState(false)

  const isMobile = useIsMobile()

  const [loadingPdf, setLoadingPdf] = useState(false)

  const [pdfDataUrl, setPdfDataUrl] = useState<string | null>(null)

  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null)

  const [mensajeEnvio, setMensajeEnvio] = useState('')

  const [expiraEn, setExpiraEn] = useState<string | null>(null) // ISO 8601 para "Código válido hasta las HH:MM"

  const [notification, setNotification] = useState<NotificationState>(null)

  const [reenviarCooldown, setReenviarCooldown] = useState(0)

  const [reenviarLoading, setReenviarLoading] = useState(false)

  const [recibosCuotas, setRecibosCuotas] = useState<ReciboCuotaItem[] | null>(
    null
  )

  const notificationTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  )

  useEffect(() => {
    return () => {
      if (pdfBlobUrl) URL.revokeObjectURL(pdfBlobUrl)
    }
  }, [pdfBlobUrl])

  useEffect(() => {
    return () => {
      if (notificationTimeoutRef.current)
        clearTimeout(notificationTimeoutRef.current)
    }
  }, [])

  const showNotification = (type: 'error' | 'success', message: string) => {
    if (notificationTimeoutRef.current) {
      clearTimeout(notificationTimeoutRef.current)

      notificationTimeoutRef.current = null
    }

    setNotification({ type, message })

    notificationTimeoutRef.current = setTimeout(() => {
      notificationTimeoutRef.current = null

      setNotification(null)
    }, 10000)
  }

  const dismissNotification = () => setNotification(null)

  const resetForm = (irAStep: number) => {
    setNotification(null)

    setExpiraEn(null)

    setReenviarCooldown(0)

    setRecibosCuotas(null)

    if (pdfBlobUrl) {
      URL.revokeObjectURL(pdfBlobUrl)
      setPdfBlobUrl(null)
    }

    setCedula('')

    setCodigo('')

    setPdfDataUrl(null)

    setMensajeEnvio('')

    setStep(irAStep)
  }

  /** Formatea expira_en ISO a "HH:MM" (hora local) para mostrar "Código válido hasta las HH:MM" */

  const formatExpiraEn = (iso: string | null | undefined): string | null => {
    if (!iso) return null

    try {
      const d = new Date(iso)

      if (Number.isNaN(d.getTime())) return null

      return d.toLocaleTimeString('es-VE', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      })
    } catch {
      return null
    }
  }

  const goToStep = (newStep: number) => {
    setNotification(null)

    setStep(newStep)
  }

  // Cooldown de reenviar código: baja 1 cada segundo cuando estamos en paso 2

  const REENVIAR_COOLDOWN_SEC = 60

  useEffect(() => {
    if (step !== 2 || reenviarCooldown <= 0) return

    const t = setInterval(() => {
      setReenviarCooldown(s => (s <= 1 ? 0 : s - 1))
    }, 1000)

    return () => clearInterval(t)
  }, [step, reenviarCooldown])

  const handleReenviarCodigo = async () => {
    if (!cedula || reenviarCooldown > 0 || reenviarLoading) return

    setReenviarLoading(true)

    try {
      const res = await solicitarCodigo(cedula)

      if (!res.ok) {
        showNotification('error', res.error || 'No se pudo reenviar el código.')

        return
      }

      setReenviarCooldown(REENVIAR_COOLDOWN_SEC)

      setExpiraEn(res.expira_en ?? null)

      setMensajeEnvio(
        res.mensaje ??
          'Si la cédula está registrada, recibirás un nuevo código en tu correo.'
      )

      showNotification(
        'success',
        'Código reenviado. Revisa tu correo (y carpeta de spam).'
      )
    } catch (e: unknown) {
      showNotification(
        'error',
        (e as Error)?.message || 'Error al reenviar el código.'
      )
    } finally {
      setReenviarLoading(false)
    }
  }

  const stepAnnouncements: Record<number, string> = {
    0: 'Pantalla de bienvenida: consulta de estado de cuenta',

    1: 'Ingrese su número de cédula',

    2: 'Verificación por correo: ingrese el código de 6 dígitos',

    3: 'Estado de cuenta generado',
  }

  const stepAnnouncement = stepAnnouncements[step] ?? `Paso ${step}`

  // Marcar flujo público para que, si intentan ir a login, vean "Acceso prohibido" y puedan volver aquí

  useEffect(() => {
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY, '1')

    sessionStorage.setItem(
      PUBLIC_FLOW_SESSION_KEY + '_path',
      'rapicredit-estadocuenta'
    )
  }, [])

  const handleSolicitarCodigo = async () => {
    const v = normalizarCedulaParaProcesar(cedula)

    if (!v.valido) {
      showNotification('error', v.error ?? 'Cédula inválida.')

      return
    }

    const cedulaEnviar = v.valorParaEnviar!

    setLoading(true)

    try {
      const validacion = await validarCedulaEstadoCuenta(cedulaEnviar)

      if (!validacion.ok) {
        showNotification('error', validacion.error || 'Cédula no válida.')

        return
      }

      const res = await solicitarCodigo(cedulaEnviar)

      if (!res.ok) {
        showNotification('error', res.error || 'Cédula no válida.')

        return
      }

      setCedula(cedulaEnviar)

      setMensajeEnvio(
        res.mensaje ??
          'Si la cedula esta registrada, recibiras un codigo en tu correo.'
      )

      setExpiraEn(res.expira_en ?? null)

      setReenviarCooldown(60)

      setStep(2)
    } catch (e: unknown) {
      showNotification(
        'error',
        (e as Error)?.message || 'Error al validar cédula.'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleVerificarCodigo = async () => {
    if (!codigo.trim()) {
      showNotification('error', 'Ingrese el codigo recibido por correo.')

      return
    }

    setLoadingPdf(true)

    try {
      const res = await verificarCodigo(cedula, codigo.trim())

      if (!res.ok) {
        showNotification('error', res.error || 'Codigo invalido o expirado.')

        return
      }

      if (res.pdf_base64) {
        setPdfDataUrl(`data:application/pdf;base64,${res.pdf_base64}`)

        setRecibosCuotas(res.recibos_cuotas ?? null)

        try {
          setPdfBlobUrl(base64ToBlobUrl(res.pdf_base64))
        } catch (blobErr) {
          console.error('PDF blob URL creation failed:', blobErr)
          setPdfBlobUrl(null)
        }

        setStep(3)
      }
    } catch (e: unknown) {
      showNotification(
        'error',
        (e as Error)?.message || 'Error al verificar codigo.'
      )
    } finally {
      setLoadingPdf(false)
    }
  }

  // Paso 0: Bienvenida (logo y colores RapiCredit: azul oscuro, naranja/marrón)

  if (step === 0) {
    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {stepAnnouncement}
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
                    className="h-12 w-auto max-w-[200px] object-contain sm:h-14"
                  />
                  <div>
                    <p className="text-2xl font-bold text-white sm:text-3xl">
                      RapiCredit
                    </p>
                    <p className="text-xs text-slate-400 sm:text-sm">
                      Estado de cuenta
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <h1 className="text-3xl font-bold text-white sm:text-4xl">
                  Consulta tu estado de cuenta
                </h1>
                <p className="text-base leading-relaxed text-slate-300 sm:text-lg">
                  Accede a tu estado de cuenta y documentos financieros de forma
                  segura y rápida.
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
                    Generación instantánea de PDF
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
                    Datos protegidos y confidenciales
                  </span>
                </div>
              </div>
            </div>

            {/* Sección derecha: Card con información */}
            <Card className="mx-1 border-0 bg-white shadow-2xl sm:mx-0">
              <CardContent className="space-y-4 p-5 sm:space-y-5 sm:p-6">
                <div className="border-b border-slate-100 pb-4">
                  <div className="mb-3 flex justify-center sm:mb-4">
                    <img
                      src={LOGO_PUBLIC_SRC}
                      alt=""
                      aria-hidden
                      className="h-10 w-auto max-w-[180px] object-contain opacity-90"
                    />
                  </div>
                  <h2 className="text-xl font-semibold text-slate-900">
                    Acceso rápido
                  </h2>
                  <p className="mt-1 text-sm text-slate-600">
                    Consulta tu información financiera
                  </p>
                </div>

                {/* Características */}
                <div className="space-y-3">
                  <div className="flex gap-3 rounded-lg bg-slate-50 p-3">
                    <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-[#1e3a5f] text-xs font-semibold text-white">
                      1
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-slate-900">
                        Ingresa cédula
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        Tu cédula (V, E, G o J + dígitos)
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3 rounded-lg bg-slate-50 p-3">
                    <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-[#1e3a5f] text-xs font-semibold text-white">
                      2
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-slate-900">
                        Genera PDF
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        Estado de cuenta al instante
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3 rounded-lg bg-slate-50 p-3">
                    <div className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-[#1e3a5f] text-xs font-semibold text-white">
                      3
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-semibold text-slate-900">
                        Descarga o envío
                      </p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        Se envía a tu correo
                      </p>
                    </div>
                  </div>
                </div>

                {/* Info y CTA */}
                <div className="space-y-3 border-t border-slate-100 pt-4">
                  <p className="text-xs leading-snug text-slate-500">
                    Tus datos se almacenarán de forma segura y se utilizarán
                    únicamente para generar tu estado de cuenta.
                  </p>
                  <Button
                    className="min-h-[48px] w-full touch-manipulation bg-[#1e3a5f] text-base font-semibold text-white shadow-md transition-all hover:bg-[#152a47] hover:shadow-lg"
                    size="lg"
                    onClick={() => goToStep(1)}
                  >
                    Iniciar
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="mt-6 flex justify-center px-2">
            <AtencionClienteWhatsAppLink compact className="max-w-sm" />
          </div>
        </div>
      </div>
    )
  }

  // Paso 1: Ingresar cédula

  if (step === 1) {
    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-b from-slate-50 to-slate-100 p-4 sm:p-6">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-4 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <img
            src={LOGO_PUBLIC_SRC}
            alt="RapiCredit"
            className="h-10 w-auto max-w-[200px] object-contain sm:h-11"
          />

          <Card className="w-full min-w-0 max-w-md overflow-hidden rounded-2xl border border-slate-200/80 shadow-xl">
            <CardHeader className="px-5 pb-2 sm:px-6">
              <CardTitle className="text-xl font-bold text-[#1e3a5f] sm:text-2xl">
                Estado de cuenta
              </CardTitle>

              <p className="text-sm text-gray-600">
                Solo letra (V, E, G o J) y 6 a 11 dígitos. No use puntos ni
                signos. Si solo ingresa números se procesará con V.
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-4 sm:px-6">
              <Input
                className="min-h-[44px] touch-manipulation rounded-xl border-slate-200 focus:border-[#1e3a5f] focus:ring-2 focus:ring-[#1e3a5f]/30"
                placeholder="Ej: V12345678, E12345678 o 12345678"
                value={cedula}
                onChange={e => setCedula(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSolicitarCodigo()}
                maxLength={20}
              />

              <div className="flex flex-wrap gap-2 sm:flex-nowrap">
                <Button
                  variant="outline"
                  className="min-h-[48px] min-w-[100px] flex-1 touch-manipulation rounded-xl border-2"
                  onClick={() => goToStep(0)}
                >
                  Atrás
                </Button>

                <Button
                  className="min-h-[48px] min-w-0 flex-1 touch-manipulation rounded-xl bg-[#1e3a5f] text-white shadow-md hover:bg-[#152a47]"
                  onClick={handleSolicitarCodigo}
                  disabled={loading}
                >
                  {loading ? 'Enviando código...' : 'Enviar código al correo'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  // Paso 2: Ingresar codigo

  if (step === 2) {
    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-b from-slate-50 to-slate-100 p-4 sm:p-6">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {stepAnnouncement}
        </div>

        <div className="flex w-full min-w-0 max-w-md flex-col items-center gap-3 px-1 sm:px-0">
          <NotificationBanner
            notification={notification}
            onDismiss={dismissNotification}
          />

          <img
            src={LOGO_PUBLIC_SRC}
            alt="RapiCredit"
            className="h-10 w-auto max-w-[200px] object-contain sm:h-11"
          />

          <Card className="w-full min-w-0 max-w-md overflow-hidden rounded-2xl border border-slate-200/80 shadow-xl">
            <CardHeader className="px-5 pb-2 sm:px-6">
              <CardTitle className="text-xl font-bold text-[#1e3a5f] sm:text-2xl">
                Verificación por correo
              </CardTitle>

              <p className="text-sm text-gray-600">
                {mensajeEnvio ||
                  'Revisa tu correo e ingresa el código de 6 dígitos.'}
              </p>

              {formatExpiraEn(expiraEn) && (
                <p className="mt-1 text-sm font-medium text-[#1e3a5f]">
                  Código válido hasta las {formatExpiraEn(expiraEn)}
                </p>
              )}

              <p className="mt-1 text-xs text-gray-500">
                Si no lo recibes, revisa la carpeta de spam. Puedes solicitar
                otro código volviendo al paso anterior (límite 5 por hora).
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-4 sm:px-6">
              <Input
                className="min-h-[44px] touch-manipulation rounded-xl border-2 border-slate-200 text-center text-lg tracking-widest focus:border-[#1e3a5f] focus:ring-2 focus:ring-[#1e3a5f]/30"
                placeholder="Código de 6 dígitos"
                value={codigo}
                onChange={e =>
                  setCodigo(e.target.value.replace(/\D/g, '').slice(0, 6))
                }
                onKeyDown={e => e.key === 'Enter' && handleVerificarCodigo()}
                maxLength={6}
                inputMode="numeric"
                autoComplete="one-time-code"
              />

              <div className="flex flex-wrap gap-2 sm:flex-nowrap">
                <Button
                  variant="outline"
                  className="min-h-[48px] min-w-[100px] flex-1 touch-manipulation rounded-xl border-2"
                  onClick={() => goToStep(1)}
                >
                  Atrás
                </Button>

                <Button
                  className="min-h-[48px] min-w-0 flex-1 touch-manipulation rounded-xl bg-[#1e3a5f] text-white shadow-md hover:bg-[#152a47]"
                  onClick={handleVerificarCodigo}
                  disabled={loadingPdf}
                >
                  {loadingPdf ? 'Verificando...' : 'Ver estado de cuenta'}
                </Button>
              </div>

              <div className="border-t border-gray-100 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="w-full text-gray-600 hover:text-[#1e3a5f]"
                  onClick={handleReenviarCodigo}
                  disabled={
                    reenviarCooldown > 0 || reenviarLoading || loadingPdf
                  }
                >
                  {reenviarLoading
                    ? 'Enviando...'
                    : reenviarCooldown > 0
                      ? `¿No llegó el correo? Reenviar código (${reenviarCooldown} s)`
                      : '¿No llegó el correo? Reenviar código'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  // Paso 3: PDF

  return (
    <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-b from-slate-50 to-slate-100 p-4 sm:p-6">
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {stepAnnouncement}
      </div>

      <div className="flex w-full min-w-0 max-w-3xl flex-col items-center gap-4 px-1 sm:px-0">
        <NotificationBanner
          notification={notification}
          onDismiss={dismissNotification}
        />

        <img
          src={LOGO_PUBLIC_SRC}
          alt="RapiCredit"
          className="h-10 w-auto max-w-[220px] object-contain sm:h-12"
        />

        <Card className="w-full min-w-0 max-w-3xl overflow-hidden rounded-2xl border border-slate-200/80 shadow-xl ring-2 ring-emerald-500/20">
          <CardHeader className="space-y-4 px-5 pb-2 sm:px-6">
            <CardTitle className="text-xl font-bold text-[#1e3a5f] sm:text-2xl">
              Estado de cuenta
            </CardTitle>

            <AtencionClienteWhatsAppLink />

            <p className="break-words text-sm text-slate-600">
              Gracias por consultar tu estado de cuenta. Si{' '}
              <strong className="font-semibold text-slate-700">
                reportaste un pago
              </strong>
              , puedes hacerlo también en{' '}
              <a
                href="https://rapicredit.onrender.com/pagos/rapicredit-cobros"
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-[#1e3a5f] underline decoration-2 underline-offset-2 transition-colors hover:text-[#152a47]"
              >
                RapiCredit Cobros
              </a>
              ; allí verás reflejados los pagos aprobados en poco tiempo.
            </p>
          </CardHeader>

          <CardContent className="space-y-4 px-4 sm:px-6">
            {loadingPdf && (
              <p className="text-gray-600">Generando estado de cuenta...</p>
            )}

            {pdfDataUrl && !loadingPdf && (
              <>
                <p className="py-4 text-center text-xl font-bold text-slate-800 sm:text-2xl">
                  {isMobile
                    ? 'Descarga tu estado de cuenta'
                    : 'Vista previa de tu estado de cuenta'}
                </p>

                <p className="-mt-2 pb-2 text-center text-sm text-slate-500">
                  La información corresponde al momento de esta consulta. Si
                  vuelves a consultar, verás los datos más recientes.
                </p>

                {/* Visor PDF solo en desktop/tablet - usa <object> para mayor compatibilidad con blob URLs */}
                {!isMobile && pdfBlobUrl && (
                  <div className="relative w-full overflow-hidden rounded-xl border border-slate-200 bg-slate-50 shadow-md">
                    <object
                      data={pdfBlobUrl}
                      type="application/pdf"
                      className="h-[70vh] w-full"
                      style={{ minHeight: '480px' }}
                    >
                      <embed
                        src={pdfBlobUrl}
                        type="application/pdf"
                        className="h-[70vh] w-full"
                        style={{ minHeight: '480px' }}
                      />
                    </object>
                  </div>
                )}

                {/* Mientras se genera el blob URL muestra spinner */}
                {!isMobile && pdfDataUrl && !pdfBlobUrl && (
                  <div className="flex h-40 w-full items-center justify-center rounded-xl border border-slate-200">
                    <p className="text-sm text-slate-500">
                      Preparando vista previa...
                    </p>
                  </div>
                )}

                {/* En movil: mensaje informativo */}
                {isMobile && (
                  <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-center text-sm text-emerald-800">
                    <span className="font-semibold">Listo.</span> Pulsa el botón
                    para guardar el PDF en tu dispositivo.
                  </div>
                )}
              </>
            )}

            <div className="flex flex-col flex-wrap gap-3 sm:flex-row">
              <Button
                variant="outline"
                className="min-h-[48px] min-w-0 flex-1 touch-manipulation rounded-xl border-2"
                onClick={() => resetForm(0)}
              >
                Termina
              </Button>

              <Button
                className="min-h-[48px] min-w-0 flex-1 touch-manipulation rounded-xl bg-[#1e3a5f] shadow-md hover:bg-[#152a47]"
                onClick={() => resetForm(1)}
              >
                Consultar otra cédula
              </Button>

              {pdfDataUrl && (
                <a
                  href={pdfBlobUrl || pdfDataUrl}
                  download={`estado_cuenta_${cedula.replace(/\s/g, '_')}.pdf`}
                  className="inline-flex min-h-[48px] min-w-0 flex-1 touch-manipulation items-center justify-center rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-600/25 transition-all duration-200 hover:bg-emerald-700 hover:shadow-xl"
                >
                  {isMobile ? 'Descargar estado de cuenta' : 'Guardar PDF'}
                </a>
              )}
            </div>

            {recibosCuotas && recibosCuotas.length > 0 && (
              <div className="border-t border-slate-200 pt-4">
                <p className="mb-2 text-sm font-semibold text-[#1e3a5f]">
                  Recibos de cuotas pagadas
                </p>

                <ul className="space-y-2">
                  {recibosCuotas.map((r, i) => (
                    <li key={`${r.prestamo_id}-${r.cuota_id}-${i}`}>
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 text-sm font-medium text-emerald-700 underline underline-offset-2 hover:text-emerald-800"
                      >
                        Recibo cuota {r.numero_cuota} - Préstamo #
                        {r.prestamo_id} {r.producto}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default EstadoCuentaPublicoPage
