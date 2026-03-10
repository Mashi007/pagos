/**
 * Consulta PÚBLICA de estado de cuenta por cédula.
 * Flujo: bienvenida → ingresar cédula → bienvenida con nombre → PDF + envío al email.
 * Sin login. Misma lógica y seguridades que rapicredit-cobros (rate limit, validación).
 */
import React, { useState, useEffect } from 'react'
import { validarCedulaEstadoCuenta, solicitarEstadoCuenta } from '../services/estadoCuentaService'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

const CEDULA_REGEX = /^[VEGJ]\d{6,11}$/i

function normalizarCedulaInput(val: string): string {
  return val.trim().toUpperCase().replace(/-/g, '').replace(/\s/g, '')
}

function validarCedulaFormato(cedula: string): { valido: boolean; error?: string } {
  const s = cedula.trim()
  if (!s) return { valido: false, error: 'Ingrese el número de cédula.' }
  const norm = normalizarCedulaInput(s)
  if (!CEDULA_REGEX.test(norm)) {
    return {
      valido: false,
      error: 'Cédula inválida. Use letra V, E, G o J seguida de 6 a 11 dígitos (ej: V12345678).',
    }
  }
  return { valido: true }
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
      className={`w-full max-w-md rounded-xl px-4 py-3.5 flex items-center gap-3 shadow-lg border-2 ${
        isError ? 'bg-red-600 border-red-700 text-white' : 'bg-emerald-600 border-emerald-700 text-white'
      }`}
    >
      <span className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center bg-white/20" aria-hidden>
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
      <p className="flex-1 font-semibold text-base leading-snug">{notification.message}</p>
      <button
        type="button"
        onClick={onDismiss}
        className="flex-shrink-0 p-1 rounded-md hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white/50"
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
  const [nombre, setNombre] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingPdf, setLoadingPdf] = useState(false)
  const [pdfDataUrl, setPdfDataUrl] = useState<string | null>(null)
  const [mensajeEnvio, setMensajeEnvio] = useState('')
  const [notification, setNotification] = useState<NotificationState>(null)

  const showNotification = (type: 'error' | 'success', message: string) => {
    setNotification({ type, message })
    const t = setTimeout(() => setNotification(null), 10000)
    return () => clearTimeout(t)
  }
  const dismissNotification = () => setNotification(null)

  const stepAnnouncements: Record<number, string> = {
    0: 'Pantalla de bienvenida: consulta de estado de cuenta',
    1: 'Ingrese su número de cédula',
    2: 'Estado de cuenta',
  }
  const stepAnnouncement = stepAnnouncements[step] ?? `Paso ${step}`

  const handleValidarCedula = async () => {
    const v = validarCedulaFormato(cedula)
    if (!v.valido) {
      showNotification('error', v.error ?? 'Cédula inválida.')
      return
    }
    setLoading(true)
    try {
      const res = await validarCedulaEstadoCuenta(cedula.trim())
      if (!res.ok) {
        showNotification('error', res.error || 'Cédula no válida.')
        return
      }
      setNombre(res.nombre ?? '')
      setStep(2)
    } catch (e: unknown) {
      showNotification('error', (e as Error)?.message || 'Error al validar cédula.')
    } finally {
      setLoading(false)
    }
  }

  // En step 2: al montar o al llegar, solicitar PDF y mostrarlo
  useEffect(() => {
    if (step !== 2 || !cedula.trim() || loadingPdf || pdfDataUrl) return
    const norm = normalizarCedulaInput(cedula)
    if (!CEDULA_REGEX.test(norm)) return

    setLoadingPdf(true)
    solicitarEstadoCuenta(cedula.trim())
      .then((res) => {
        if (!res.ok) {
          showNotification('error', res.error || 'Error al generar estado de cuenta.')
          return
        }
        setMensajeEnvio(res.mensaje ?? 'Se ha enviado una copia al correo registrado.')
        if (res.pdf_base64) {
          setPdfDataUrl(`data:application/pdf;base64,${res.pdf_base64}`)
        }
      })
      .catch((e) => {
        showNotification('error', (e as Error)?.message || 'Error al generar estado de cuenta.')
      })
      .finally(() => setLoadingPdf(false))
  }, [step, cedula, loadingPdf, pdfDataUrl])

  // Paso 0: Bienvenida
  if (step === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-100 to-slate-200 flex flex-col items-center justify-center p-4">
        <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
          {stepAnnouncement}
        </div>
        <Card className="w-full max-w-lg shadow-xl border-2 border-slate-200">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-2xl text-slate-800">Bienvenido</CardTitle>
            <p className="text-slate-600 mt-1">Consulta de estado de cuenta — RapiCredit</p>
          </CardHeader>
          <CardContent className="space-y-5">
            <p className="text-slate-700 text-center">
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
            <Button className="w-full text-base py-6 font-semibold" size="lg" onClick={() => setStep(1)}>
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
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
        <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
          {stepAnnouncement}
        </div>
        <div className="w-full max-w-md flex flex-col items-center gap-3">
          <NotificationBanner notification={notification} onDismiss={dismissNotification} />
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Estado de cuenta</CardTitle>
              <p className="text-sm text-gray-600">Ingrese su número de cédula (V, E, G o J + 6 a 11 dígitos)</p>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                placeholder="Ej: V12345678 o V-12345678"
                value={cedula}
                onChange={(e) => setCedula(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleValidarCedula()}
                maxLength={20}
              />
              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" onClick={() => setStep(0)}>
                  Atrás
                </Button>
                <Button className="flex-1" onClick={handleValidarCedula} disabled={loading}>
                  {loading ? 'Verificando...' : 'Continuar'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  // Paso 2: Bienvenida con nombre + PDF + mensaje de envío al email
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center p-4">
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {stepAnnouncement}
      </div>
      <div className="w-full max-w-3xl flex flex-col items-center gap-3">
        <NotificationBanner notification={notification} onDismiss={dismissNotification} />
        <Card className="w-full max-w-3xl">
          <CardHeader>
            <CardTitle>Bienvenido, {nombre || 'Cliente'}</CardTitle>
            {mensajeEnvio && (
              <p className="text-sm text-emerald-700 font-medium">{mensajeEnvio}</p>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            {loadingPdf && (
              <p className="text-gray-600">Generando estado de cuenta...</p>
            )}
            {pdfDataUrl && !loadingPdf && (
              <div className="w-full border rounded-lg overflow-hidden bg-gray-100">
                <iframe
                  title="Estado de cuenta PDF"
                  src={pdfDataUrl}
                  className="w-full min-h-[60vh] aspect-[3/4] max-h-[80vh]"
                />
              </div>
            )}
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => { setStep(1); setPdfDataUrl(null); setMensajeEnvio(''); }}>
                Consultar otra cédula
              </Button>
              {pdfDataUrl && (
                <a
                  href={pdfDataUrl}
                  download={`estado_cuenta_${cedula.replace(/\s/g, '_')}.pdf`}
                  className="inline-flex items-center justify-center rounded-md text-sm font-medium bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
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
