/**
 * Consulta PÚBLICA de estado de cuenta por cédula.
 * Flujo: bienvenida → ingresar cédula → bienvenida con nombre → PDF + envío al email.
 * Sin login. Misma lógica y seguridades que rapicredit-cobros (rate limit, validación).
 * Marca sesión para que, si intentan ir a login/sistema, vean "Acceso prohibido" y puedan volver aquí.
 */
import React, { useState, useEffect } from 'react'
import { solicitarCodigo, verificarCodigo } from '../services/estadoCuentaService'
import { PUBLIC_FLOW_SESSION_KEY } from '../config/env'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

const CEDULA_REGEX = /^[VEGJ]\d{6,11}$/i

/** Normaliza para validar: quita espacios, guiones y puntos. Si solo 6-11 dígitos, al procesar se antepone V. No acepta puntos ni signos intermedios. */
function normalizarCedulaParaProcesar(val: string): { valido: boolean; valorParaEnviar?: string; error?: string } {
  const s = val.trim().toUpperCase().replace(/[\s.\-]/g, '')
  if (!s) return { valido: false, error: 'Ingrese el número de cédula.' }
  if (!/^[VEGJ]?\d+$/.test(s)) {
    return { valido: false, error: 'No use puntos ni signos intermedios. Solo letra (V, E, G o J) y dígitos.' }
  }
  if (/^\d{6,11}$/.test(s)) return { valido: true, valorParaEnviar: 'V' + s }
  if (CEDULA_REGEX.test(s)) return { valido: true, valorParaEnviar: s }
  return { valido: false, error: 'Cédula inválida. Use letra V, E, G o J seguida de 6 a 11 dígitos.' }
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
      className={`w-full max-w-md min-w-0 rounded-xl px-3 sm:px-4 py-3 sm:py-3.5 flex items-center gap-2 sm:gap-3 shadow-lg border-2 ${
        isError ? 'bg-red-600 border-red-700 text-white' : 'bg-emerald-600 border-emerald-700 text-white'
      }`}
    >
      <span className="flex-shrink-0 w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center bg-white/20" aria-hidden>
        {isError ? (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )}
      </span>
      <p className="flex-1 min-w-0 font-semibold text-sm sm:text-base leading-snug break-words">{notification.message}</p>
      <button
        type="button"
        onClick={onDismiss}
        className="flex-shrink-0 p-2 rounded-md hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white/50 touch-manipulation min-h-[44px] min-w-[44px] flex items-center justify-center"
        aria-label="Cerrar notificación"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
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
  const [notification, setNotification] = useState<NotificationState>(null)


  useEffect(() => {
    return () => { if (pdfBlobUrl) URL.revokeObjectURL(pdfBlobUrl) }
  }, [pdfBlobUrl])

  const showNotification = (type: 'error' | 'success', message: string) => {
    setNotification({ type, message })
    const t = setTimeout(() => setNotification(null), 10000)
    return () => clearTimeout(t)
  }
  const dismissNotification = () => setNotification(null)

  const resetForm = (irAStep: number) => {
    if (pdfBlobUrl) { URL.revokeObjectURL(pdfBlobUrl); setPdfBlobUrl(null) }
    setCedula('')
    setCodigo('')
    setPdfDataUrl(null)
    setMensajeEnvio('')
    setStep(irAStep)
  }

  const stepAnnouncements: Record<number, string> = {
    0: 'Pantalla de bienvenida: consulta de estado de cuenta',
    1: 'Ingrese su número de cédula',
    2: 'Estado de cuenta',
  }
  const stepAnnouncement = stepAnnouncements[step] ?? `Paso ${step}`

  // Marcar flujo público para que, si intentan ir a login, vean "Acceso prohibido" y puedan volver aquí
  useEffect(() => {
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY, '1')
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY + '_path', 'rapicredit-estadocuenta')
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
      const res = await solicitarCodigo(cedulaEnviar)
      if (!res.ok) {
        showNotification('error', res.error || 'Cédula no válida.')
        return
      }
      setCedula(cedulaEnviar)
      setMensajeEnvio(res.mensaje ?? 'Si la cedula esta registrada, recibiras un codigo en tu correo.')
      setStep(2)
    } catch (e: unknown) {
      showNotification('error', (e as Error)?.message || 'Error al validar cédula.')
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
      showNotification('error', (e as Error)?.message || 'Error al verificar codigo.')
    } finally {
      setLoadingPdf(false)
    }
  }
// Paso 0: Bienvenida (logo y colores RapiCredit: azul oscuro, naranja/marrón)
  const LOGO_PUBLIC_SRC = `${(import.meta.env.BASE_URL || '/').replace(/\/?$/, '')}/logos/rapicredit-public.png`
  if (step === 0) {
    return (
      <div className="min-h-screen min-h-[100dvh] bg-gradient-to-b from-slate-100 via-[#e8eef5] to-slate-200 flex flex-col items-center justify-center p-3 sm:p-4 overflow-x-hidden">
        <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
          {stepAnnouncement}
        </div>
        <Card className="w-full max-w-lg min-w-0 shadow-xl border border-slate-200/80 overflow-hidden mx-1 sm:mx-0">
          <div className="bg-white px-4 sm:px-6 py-5 sm:py-6 text-center rounded-t-lg border-b border-slate-100">
            <div className="inline-flex flex-col items-center justify-center">
              <img src={LOGO_PUBLIC_SRC} alt="RapiCredit" className="h-14 sm:h-16 mx-auto object-contain" />
              <p className="text-[#c4a35a] text-sm sm:text-base mt-2 sm:mt-3 font-semibold">Consulta de estado de cuenta</p>
            </div>
          </div>
          <CardHeader className="text-center pb-2 px-4 sm:px-6">
            <CardTitle className="text-xl sm:text-2xl text-[#1e3a5f]">Bienvenido</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 sm:space-y-5 px-4 sm:px-6 pb-6">
            <p className="text-slate-700 text-center text-sm sm:text-base">
              Desde aquí puede consultar su estado de cuenta. Solo debe ingresar su cédula; el documento se generará y se enviará al correo registrado.
            </p>
            <ul className="text-sm text-slate-600 space-y-2 list-disc list-inside">
              <li>Ingrese su número de cédula (V, E, G o J + dígitos).</li>
              <li>Se generará un PDF con sus préstamos y cuotas pendientes.</li>
              <li>Una copia se enviará al correo electrónico registrado.</li>
            </ul>
            <p className="text-xs text-slate-500 text-center">
              Este servicio solo permite consultar su propio estado de cuenta. No da acceso a otros servicios.
            </p>
            <p className="text-xs text-slate-500 text-center">
              Si desea consultar otra cédula, al finalizar use el botón «Consultar otra cédula» o reinicie el proceso.
            </p>
            <Button className="w-full text-base py-5 sm:py-6 min-h-[48px] font-semibold bg-[#1e3a5f] hover:bg-[#152a47] text-white touch-manipulation" size="lg" onClick={() => setStep(1)}>
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
      <div className="min-h-screen min-h-[100dvh] bg-slate-50 flex flex-col items-center justify-center p-3 sm:p-4 overflow-x-hidden">
        <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
          {stepAnnouncement}
        </div>
        <div className="w-full max-w-md min-w-0 flex flex-col items-center gap-3 px-1 sm:px-0">
          <NotificationBanner notification={notification} onDismiss={dismissNotification} />
          <Card className="w-full max-w-md min-w-0">
            <CardHeader className="px-4 sm:px-6">
              <CardTitle className="text-lg sm:text-xl">Estado de cuenta</CardTitle>
              <p className="text-sm text-gray-600">Solo letra (V, E, G o J) y 6 a 11 dígitos. No use puntos ni signos. Si solo ingresa números se procesará con V.</p>
            </CardHeader>
            <CardContent className="px-4 sm:px-6 space-y-4">
              <Input
                className="min-h-[44px] touch-manipulation"
                placeholder="Ej: V12345678, E12345678 o 12345678"
                value={cedula}
                onChange={(e) => setCedula(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSolicitarCodigo()}
                maxLength={20}
              />
              <div className="flex gap-2 flex-wrap sm:flex-nowrap">
                <Button variant="outline" className="flex-1 min-h-[48px] min-w-[100px] touch-manipulation" onClick={() => setStep(0)}>
                  Atrás
                </Button>
                <Button className="flex-1 min-h-[48px] min-w-0 touch-manipulation" onClick={handleSolicitarCodigo} disabled={loading}>
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
      <div className="min-h-screen min-h-[100dvh] bg-slate-50 flex flex-col items-center justify-center p-3 sm:p-4 overflow-x-hidden">
        <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">{stepAnnouncement}</div>
        <div className="w-full max-w-md min-w-0 flex flex-col items-center gap-3 px-1 sm:px-0">
          <NotificationBanner notification={notification} onDismiss={dismissNotification} />
          <Card className="w-full max-w-md min-w-0">
            <CardHeader className="px-4 sm:px-6">
              <CardTitle className="text-lg sm:text-xl">Verificacion por correo</CardTitle>
              <p className="text-sm text-gray-600">{mensajeEnvio || 'Revisa tu correo e ingresa el codigo de 6 digitos.'}</p>
            </CardHeader>
            <CardContent className="px-4 sm:px-6 space-y-4">
              <Input
                className="min-h-[44px] touch-manipulation text-center text-lg tracking-widest"
                placeholder="Codigo de 6 digitos"
                value={codigo}
                onChange={(e) => setCodigo(e.target.value.replace(/\D/g, '').slice(0, 6))}
                onKeyDown={(e) => e.key === 'Enter' && handleVerificarCodigo()}
                maxLength={6}
                inputMode="numeric"
                autoComplete="one-time-code"
              />
              <div className="flex gap-2 flex-wrap sm:flex-nowrap">
                <Button variant="outline" className="flex-1 min-h-[48px] min-w-[100px] touch-manipulation" onClick={() => setStep(1)}>Atras</Button>
                <Button className="flex-1 min-h-[48px] min-w-0 touch-manipulation" onClick={handleVerificarCodigo} disabled={loadingPdf}>
                  {loadingPdf ? 'Verificando...' : 'Ver estado de cuenta'}
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
    <div className="min-h-screen min-h-[100dvh] bg-slate-50 flex flex-col items-center p-3 sm:p-4 overflow-x-hidden">
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {stepAnnouncement}
      </div>
      <div className="w-full max-w-3xl min-w-0 flex flex-col items-center gap-3 px-1 sm:px-0">
        <NotificationBanner notification={notification} onDismiss={dismissNotification} />
        <Card className="w-full max-w-3xl min-w-0">
          <CardHeader className="px-4 sm:px-6">
            <CardTitle className="text-lg sm:text-xl">Estado de cuenta</CardTitle>
            {mensajeEnvio && (
              <p className="text-sm text-emerald-700 font-medium break-words">{mensajeEnvio}</p>
            )}
          </CardHeader>
          <CardContent className="px-4 sm:px-6 space-y-4">
            {loadingPdf && (
              <p className="text-gray-600">Generando estado de cuenta...</p>
            )}
            {pdfDataUrl && !loadingPdf && (
              <div className="w-full min-w-0 border rounded-lg overflow-hidden bg-gray-100">
                <iframe
                  title="Estado de cuenta PDF"
                  src={pdfBlobUrl || pdfDataUrl || ''}
                  className="w-full min-h-[50vh] sm:min-h-[60vh] aspect-[3/4] max-h-[70vh] sm:max-h-[80vh] border-0"
                />
              </div>
            )}
            <div className="flex flex-col sm:flex-row gap-3 flex-wrap">
              <Button variant="outline" className="flex-1 min-h-[48px] touch-manipulation min-w-0" onClick={() => resetForm(0)}>
                Termina
              </Button>
              <Button className="flex-1 min-h-[48px] bg-[#1e3a5f] hover:bg-[#152a47] touch-manipulation min-w-0" onClick={() => resetForm(1)}>
                Consultar otra cédula
              </Button>
              {pdfDataUrl && (
                <a
                  href={pdfDataUrl}
                  download={`estado_cuenta_${cedula.replace(/\s/g, '_')}.pdf`}
                  className="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 min-h-[48px] px-4 py-2 flex-1 min-w-0 touch-manipulation"
                >
                  Descargar PDF
                </a>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
