/**





 * Consulta PÚBLICA de estado de cuenta por cédula.





 * Flujo: bienvenida → ingresar cédula → bienvenida con nombre → PDF + envío al email.





 * Sin login. Misma lógica y seguridades que rapicredit-cobros (rate limit, validación).





 * Marca sesión para que, si intentan ir a login/sistema, vean "Acceso prohibido" y puedan volver aquí.





 */

import React, { useState, useEffect, useRef } from 'react'

import { useLocation } from 'react-router-dom'

import {
  validarCedulaEstadoCuenta,
  solicitarCodigo,
  verificarCodigo,
  solicitarEstadoCuenta,
  type ReciboCuotaItem,
} from '../services/estadoCuentaService'

import { PUBLIC_FLOW_SESSION_KEY } from '../config/env'

import { Button } from '../components/ui/button'

import { Input } from '../components/ui/input'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

const CEDULA_REGEX = /^[VEGJ]\d{6,11}$/i

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

export default function EstadoCuentaPublicoPage() {
  const [step, setStep] = useState(0)

  const [cedula, setCedula] = useState('')

  const [codigo, setCodigo] = useState('')

  const [loading, setLoading] = useState(false)

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

  const location = useLocation()

  const publicPath = (location.pathname || '').replace(/^\//, '')

  const isInformesRoute = publicPath === 'informes'

  // Marcar flujo público para que, si intentan ir a login, vean "Acceso prohibido" y puedan volver aquí

  useEffect(() => {
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY, '1')

    sessionStorage.setItem(
      PUBLIC_FLOW_SESSION_KEY + '_path',
      (location.pathname || '').replace(/^\//, '') || 'rapicredit-estadocuenta'
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
      const validacion = await validarCedulaEstadoCuenta(
        cedulaEnviar,

        isInformesRoute ? { origen: 'informes' } : undefined
      )

      if (!validacion.ok) {
        showNotification('error', validacion.error || 'Cédula no válida.')

        return
      }

      if (isInformesRoute) {
        const resPdf = await solicitarEstadoCuenta(cedulaEnviar, {
          origen: 'informes',
        })

        if (!resPdf.ok) {
          showNotification(
            'error',
            resPdf.error || 'No se pudo generar el estado de cuenta.'
          )

          return
        }

        setCedula(cedulaEnviar)

        if (resPdf.pdf_base64) {
          setPdfDataUrl(`data:application/pdf;base64,${resPdf.pdf_base64}`)

          try {
            const bin = atob(resPdf.pdf_base64)

            const bytes = new Uint8Array(bin.length)

            for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)

            const blob = new Blob([bytes], { type: 'application/pdf' })

            setPdfBlobUrl(URL.createObjectURL(blob))
          } catch (_) {
            setPdfBlobUrl(null)
          }

          setStep(3)
        }

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
          const bin = atob(res.pdf_base64)

          const bytes = new Uint8Array(bin.length)

          for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)

          const blob = new Blob([bytes], { type: 'application/pdf' })

          setPdfBlobUrl(URL.createObjectURL(blob))
        } catch (_) {
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

  const LOGO_PUBLIC_SRC = `${(import.meta.env.BASE_URL || '/').replace(/\/?$/, '')}/logos/rapicredit-public.png`

  if (step === 0) {
    return (
      <div className="flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-100 via-[#e0eaf2] to-[#c9d6e8] p-4 sm:p-6">
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {stepAnnouncement}
        </div>

        <Card className="mx-1 w-full min-w-0 max-w-lg overflow-hidden rounded-2xl border border-slate-200/90 shadow-2xl shadow-slate-300/40 ring-1 ring-slate-200/50 sm:mx-0">
          <div className="border-b border-slate-100 bg-gradient-to-b from-white to-slate-50/80 px-6 py-6 text-center sm:px-8 sm:py-8">
            <div className="inline-flex flex-col items-center justify-center">
              <img
                src={LOGO_PUBLIC_SRC}
                alt="RapiCredit"
                className="mx-auto h-16 object-contain drop-shadow-sm sm:h-20"
              />

              <p className="mt-3 text-sm font-semibold tracking-wide text-[#b8954a] sm:text-base">
                Consulta de estado de cuenta
              </p>
            </div>
          </div>

          <CardHeader className="px-4 pb-2 text-center sm:px-6">
            <CardTitle className="text-2xl font-bold tracking-tight text-[#1e3a5f] sm:text-3xl">
              {isInformesRoute ? 'Estado de cuenta' : 'Bienvenido'}
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-4 px-4 pb-6 sm:space-y-5 sm:px-6">
            {isInformesRoute ? (
              <>
                <p className="text-center text-sm text-slate-700 sm:text-base">
                  Generación de estado de cuenta para empleados. Ingrese la
                  cédula del cliente y obtenga el PDF al instante. No se
                  solicita código ni se envía correo.
                </p>

                <ul className="list-inside list-disc space-y-2 text-sm text-slate-600">
                  <li>Ingrese la cédula (V, E, G o J + dígitos).</li>

                  <li>Se generará el PDF y podrá descargarlo directamente.</li>
                </ul>
              </>
            ) : (
              <>
                <p className="text-center text-sm text-slate-700 sm:text-base">
                  Desde aquí puede consultar su estado de cuenta. Solo debe
                  ingresar su cédula; el documento se generará y se enviará al
                  correo registrado.
                </p>

                <ul className="list-inside list-disc space-y-2 text-sm text-slate-600">
                  <li>Ingrese su número de cédula (V, E, G o J + dígitos).</li>

                  <li>
                    Se generará un PDF con sus préstamos y cuotas pendientes.
                  </li>

                  <li>
                    Una copia se enviará al correo electrónico registrado.
                  </li>
                </ul>

                <p className="text-center text-xs text-slate-500">
                  Este servicio solo permite consultar su propio estado de
                  cuenta. No da acceso a otros servicios.
                </p>

                <p className="text-center text-xs text-slate-500">
                  Si desea consultar otra cédula, al finalizar use el botón
                  «Consultar otra cédula» o reinicie el proceso.
                </p>
              </>
            )}

            <Button
              className="min-h-[52px] w-full touch-manipulation rounded-xl bg-[#1e3a5f] py-6 text-base font-semibold text-white shadow-lg shadow-[#1e3a5f]/25 transition-all duration-200 hover:bg-[#152a47] hover:shadow-xl active:scale-[0.98]"
              size="lg"
              onClick={() => goToStep(1)}
            >
              Iniciar
            </Button>
          </CardContent>
        </Card>
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

          <Card className="w-full min-w-0 max-w-md overflow-hidden rounded-2xl border border-slate-200/80 shadow-xl">
            <CardHeader className="px-5 pb-2 sm:px-6">
              <CardTitle className="text-xl font-bold text-[#1e3a5f] sm:text-2xl">
                Estado de cuenta
              </CardTitle>

              <p className="text-sm text-gray-600">
                {isInformesRoute
                  ? 'Uso interno. Ingrese la cédula del cliente para generar el PDF. No se envía correo.'
                  : 'Solo letra (V, E, G o J) y 6 a 11 dígitos. No use puntos ni signos. Si solo ingresa números se procesará con V.'}
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
                  {loading
                    ? isInformesRoute
                      ? 'Generando PDF...'
                      : 'Enviando código...'
                    : isInformesRoute
                      ? 'Generar PDF'
                      : 'Enviar código al correo'}
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

        <Card className="w-full min-w-0 max-w-3xl overflow-hidden rounded-2xl border border-slate-200/80 shadow-xl ring-2 ring-emerald-500/20">
          <CardHeader className="px-5 pb-2 sm:px-6">
            <CardTitle className="text-xl font-bold text-[#1e3a5f] sm:text-2xl">
              Estado de cuenta
            </CardTitle>

            <p className="mt-2 break-words text-sm font-medium text-slate-600">
              Agradecemos que revises tu estado de cuenta. Si encuentras algún
              problema, repórtalo por{' '}
              <a
                href="https://wa.me/584244579934"
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-emerald-600 underline decoration-2 underline-offset-2 transition-colors hover:text-emerald-700"
              >
                WhatsApp
              </a>{' '}
              o ingresa a{' '}
              <a
                href="https://rapicredit.onrender.com/pagos/rapicredit-cobros"
                target="_blank"
                rel="noopener noreferrer"
                className="font-semibold text-[#1e3a5f] underline decoration-2 underline-offset-2 transition-colors hover:text-[#152a47]"
              >
                rapicredit-cobros
              </a>{' '}
              para actualizar tu estado de cuenta en 1 hora.
            </p>
          </CardHeader>

          <CardContent className="space-y-4 px-4 sm:px-6">
            {loadingPdf && (
              <p className="text-gray-600">Generando estado de cuenta...</p>
            )}

            {pdfDataUrl && !loadingPdf && (
              <>
                <p className="py-6 text-center text-xl font-bold text-slate-800 sm:text-2xl">
                  Descarga tu estado de cuenta
                </p>

                <p className="-mt-4 pb-2 text-center text-sm text-slate-500">
                  Los datos reflejan el estado al momento de esta consulta. Cada
                  nueva consulta muestra los pagos más recientes.
                </p>
                <p className="pb-2 text-center text-xs text-slate-500">
                  Los pagos a cuotas se muestran según{' '}
                  <span className="font-semibold text-slate-600">
                    asignación en cascada
                  </span>
                  : se aplican en orden por número de cuota.
                </p>
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
                  Descargar estado de cuenta
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
