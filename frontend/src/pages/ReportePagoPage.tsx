/**
 * Formulario PÚBLICO de reporte de pago (sin login).
 * Validadores alineados con el backend: cédula (V/E/J/Z + 6-11 dígitos), monto (>0, máx 999.999.999,99),
 * fecha (obligatoria, no futura, desde calendario), institución y nº documento (longitud), archivo (JPG/PNG/PDF, máx 5 MB).
 * Notificaciones claras por cada error para guiar al cliente.
 * Marca flujo público para que, si intentan ir a login, vean "Acceso prohibido" y puedan volver.
 */
import React, { useState, useRef, useEffect } from 'react'
import { validarCedulaPublico, enviarReportePublico } from '../services/cobrosService'
import { PUBLIC_FLOW_SESSION_KEY } from '../config/env'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

// Límites iguales al backend (cobros_publico)
const MAX_MONTO = 999_999_999.99
const MIN_MONTO = 0.01
const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5 MB
const ALLOWED_FILE_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']
const MAX_LENGTH_INSTITUCION = 100
const MAX_LENGTH_NUMERO_OPERACION = 100
// Cédula: V|E|G|J + 6-11 dígitos (mismo patrón que backend validadores)
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
      error: 'Cédula inválida. Use letra V, E, G o J seguida de 6 a 11 dígitos (ej: V12345678 o V-12345678).',
    }
  }
  return { valido: true }
}

function validarMonto(val: string): { valido: boolean; valor?: number; error?: string } {
  if (val === '' || val == null) return { valido: false, error: 'Ingrese el monto del pago.' }
  const num = Number(val.replace(',', '.'))
  if (Number.isNaN(num)) return { valido: false, error: 'Monto no válido. Ingrese un número (ej: 150.50).' }
  if (num < MIN_MONTO) return { valido: false, error: `El monto debe ser mayor a ${MIN_MONTO}.` }
  if (num > MAX_MONTO) return { valido: false, error: 'Monto demasiado alto. Revise el valor e intente de nuevo.' }
  return { valido: true, valor: num }
}

function validarFechaPago(fecha: string): { valido: boolean; error?: string } {
  if (!fecha || !fecha.trim()) {
    return { valido: false, error: 'Seleccione la fecha de pago en el calendario.' }
  }
  const hoy = new Date()
  hoy.setHours(0, 0, 0, 0)
  const d = new Date(fecha)
  if (Number.isNaN(d.getTime())) return { valido: false, error: 'Fecha no válida. Use el calendario para elegir la fecha.' }
  d.setHours(0, 0, 0, 0)
  if (d > hoy) return { valido: false, error: 'La fecha de pago no puede ser futura.' }
  return { valido: true }
}

function validarArchivo(file: File | null): { valido: boolean; error?: string } {
  if (!file) return { valido: false, error: 'Seleccione un archivo de comprobante (JPG, PNG o PDF).' }
  const type = (file.type || '').toLowerCase()
  const okType = ALLOWED_FILE_TYPES.some(t => type === t || (t === 'image/jpg' && type === 'image/jpeg'))
  if (!okType) {
    return { valido: false, error: 'Solo se permiten archivos JPG, PNG o PDF.' }
  }
  if (file.size > MAX_FILE_SIZE) {
    return { valido: false, error: 'El comprobante no puede superar 5 MB. Reduzca el tamaño del archivo.' }
  }
  if (file.size < 4) return { valido: false, error: 'El archivo está vacío o no es válido.' }
  return { valido: true }
}

const INSTITUCIONES = [
  'Banco de Venezuela (BDV)',
  'Banesco',
  'Mercantil',
  'BBVA Provincial',
  'Banco Exterior',
  'Banplus',
  'Bancamiga',
  'BNC',
  'Bicentenario',
  'Sofitasa',
  'Banco del Tesoro',
  'Otros',
]

const WHATSAPP_LINK = 'https://wa.me/584244579934'

const NOTIFICATION_DURATION_MS = 10000

type NotificationType = 'error' | 'success'
type NotificationState = { type: NotificationType; message: string } | null

function NotificationBanner({ notification, onDismiss }: { notification: NotificationState; onDismiss: () => void }) {
  if (!notification) return null
  const isError = notification.type === 'error'
  return (
    <div
      role="alert"
      className={`w-full max-w-md rounded-xl px-4 py-3.5 flex items-center gap-3 shadow-lg border-2 ${
        isError
          ? 'bg-red-600 border-red-700 text-white'
          : 'bg-emerald-600 border-emerald-700 text-white'
      }`}
    >
      <span className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center bg-white/20" aria-hidden>
        {isError ? (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
        ) : (
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
        )}
      </span>
      <p className="flex-1 font-semibold text-base leading-snug">{notification.message}</p>
      <button
        type="button"
        onClick={onDismiss}
        className="flex-shrink-0 p-1 rounded-md hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white/50"
        aria-label="Cerrar notificación"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
      </button>
    </div>
  )
}

export default function ReportePagoPage() {
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
  const [numeroDocumento, setNumeroDocumento] = useState('')
  const [archivo, setArchivo] = useState<File | null>(null)
  const [referencia, setReferencia] = useState('')
  const [enviado, setEnviado] = useState(false)
  const [messageForScreenReader, setMessageForScreenReader] = useState('')
  const [notification, setNotification] = useState<NotificationState>(null)
  const notificationTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showNotification = (type: NotificationType, message: string) => {
    if (notificationTimeoutRef.current) clearTimeout(notificationTimeoutRef.current)
    setNotification({ type, message })
    notificationTimeoutRef.current = setTimeout(() => {
      setNotification(null)
      notificationTimeoutRef.current = null
    }, NOTIFICATION_DURATION_MS)
  }
  const dismissNotification = () => {
    if (notificationTimeoutRef.current) clearTimeout(notificationTimeoutRef.current)
    notificationTimeoutRef.current = null
    setNotification(null)
  }
  useEffect(() => () => { if (notificationTimeoutRef.current) clearTimeout(notificationTimeoutRef.current) }, [])

  // Marcar flujo público para que, si intentan ir a login, vean "Acceso prohibido" y puedan volver
  useEffect(() => {
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY, '1')
    sessionStorage.setItem(PUBLIC_FLOW_SESSION_KEY + '_path', 'rapicredit-cobros')
  }, [])

  const institucionFinal = institucion === 'Otros' ? institucionOtros : institucion

  const stepAnnouncements: Record<number, string> = {
    0: 'Pantalla de bienvenida: reporte de pago',
    1: 'Paso 1: Ingrese su número de cédula',
    2: 'Paso 2: Datos del pago',
    3: 'Paso 3: Institución financiera',
    4: 'Paso 4: Fecha y monto del pago',
    5: 'Paso 5: Número de documento u operación',
    6: 'Paso 6: Adjuntar comprobante',
    7: 'Paso 7: Confirmar y enviar',
    8: 'Reporte enviado correctamente',
  }
  const stepAnnouncement = stepAnnouncements[step] || `Paso ${step}`

  const handleValidarCedula = async () => {
    const v = validarCedulaFormato(cedula)
    if (!v.valido) {
      showNotification('error', v.error ?? 'Cédula inválida.')
      return
    }
    setLoading(true)
    try {
      const res = await validarCedulaPublico(cedula.trim())
      if (!res.ok) {
        showNotification('error', res.error || 'Cédula no válida.')
        return
      }
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
    // Validaciones iguales al backend; notificación específica por error
    const vCedula = validarCedulaFormato(cedula)
    if (!vCedula.valido) {
      showNotification('error', vCedula.error ?? 'Cédula inválida.')
      return
    }
    if (!institucionFinal.trim()) {
      showNotification('error', 'Seleccione la institución financiera.')
      return
    }
    if (institucionFinal.length > MAX_LENGTH_INSTITUCION) {
      showNotification('error', 'Nombre de institución demasiado largo. Redúzcalo.')
      return
    }
    const vFecha = validarFechaPago(fechaPago)
    if (!vFecha.valido) {
      showNotification('error', vFecha.error ?? 'Fecha inválida.')
      return
    }
    const vMonto = validarMonto(monto)
    if (!vMonto.valido) {
      showNotification('error', vMonto.error ?? 'Monto inválido.')
      return
    }
    if (!numeroDocumento.trim()) {
      showNotification('error', 'Ingrese el número de documento u operación.')
      return
    }
    if (numeroDocumento.length > MAX_LENGTH_NUMERO_OPERACION) {
      showNotification('error', 'Número de documento u operación demasiado largo.')
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
      showNotification('error', 'No se pudo procesar el envío. Intente de nuevo.')
      return
    }
    const tipoCedula = /^([VEJ])/i.exec(cedula)?.[1]?.toUpperCase() || 'V'
    const numeroCedula = cedula.replace(/^[VEJ]\s*\-?\s*/i, '').replace(/\D/g, '')
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
      const res = await enviarReportePublico(form)
      if (!res.ok) {
        showNotification('error', res.error || 'Error al enviar.')
        return
      }
      setReferencia(res.referencia_interna || '')
      setEnviado(true)
      setStep(8)
    } catch (e: any) {
      showNotification('error', e?.message || 'Error al enviar el reporte.')
    } finally {
      setLoading(false)
    }
  }

  // Pantalla de bienvenida con instrucciones generales (logo y colores RapiCredit: azul oscuro, naranja/marrón)
  const LOGO_PUBLIC_SRC = `${(import.meta.env.BASE_URL || '/').replace(/\/?$/, '')}/logos/rapicredit-public.png`
  if (step === 0) {
    const steps = [
      { icon: 'id', text: 'Ingrese su número de cédula (V, E, G o J + dígitos).' },
      { icon: 'bank', text: 'Indique institución financiera, fecha, monto y número de operación.' },
      { icon: 'file', text: 'Adjunte el comprobante de pago (JPG, PNG o PDF, máx. 5 MB).' },
      { icon: 'check', text: 'Revise los datos y envíe. Recibirá confirmación al correo registrado.' },
    ]
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-[#e8eef5] to-slate-100 flex flex-col items-center justify-center p-4">
        <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
          {messageForScreenReader || stepAnnouncement}
        </div>
        <Card className="w-full max-w-lg shadow-2xl border border-[#c4a35a]/30 overflow-hidden">
          {/* Header con logo RapiCredit (azul oscuro + acento naranja/marrón) */}
          <div className="bg-[#1e3a5f] px-6 py-5 text-center">
            <img src={LOGO_PUBLIC_SRC} alt="RapiCredit" className="h-14 mx-auto object-contain" />
            <p className="text-[#c4a35a] text-sm mt-2 font-medium">Reporte de pago</p>
          </div>
          <CardContent className="p-6 sm:p-8 space-y-6">
            <div className="text-center">
              <h2 className="text-xl font-semibold text-[#1e3a5f]">Bienvenido</h2>
              <p className="text-slate-600 mt-2 text-sm leading-relaxed">
                Reporte su pago de forma segura para que sea verificado por cobranza.
              </p>
            </div>
            <ul className="space-y-3" role="list">
              {steps.map((item, i) => (
                <li key={i} className="flex gap-3 items-start text-sm text-slate-700">
                  <span className="flex-shrink-0 w-8 h-8 rounded-full bg-[#1e3a5f]/10 text-[#1e3a5f] flex items-center justify-center mt-0.5" aria-hidden>
                    {item.icon === 'id' && (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2" /></svg>
                    )}
                    {item.icon === 'bank' && (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" /></svg>
                    )}
                    {item.icon === 'file' && (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                    )}
                    {item.icon === 'check' && (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    )}
                  </span>
                  <span className="pt-1">{item.text}</span>
                </li>
              ))}
            </ul>
            <p className="text-xs text-slate-500 text-center bg-slate-50 rounded-lg px-3 py-2 border border-slate-100">
              Los datos se comprobarán y almacenarán únicamente para validación del pago.
            </p>
            <p className="text-xs text-slate-500 text-center">
              Si toca por error un enlace al sistema o al login, verá «Acceso prohibido» y podrá volver aquí con el botón Continuar.
            </p>
            <Button
              className="w-full text-base py-6 font-semibold bg-[#1e3a5f] hover:bg-[#152a47] text-white shadow-md hover:shadow-lg transition-all"
              size="lg"
              onClick={() => setStep(1)}
            >
              Iniciar reporte
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (step === 1) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
        {/* Zona de mensajes para lectores de pantalla (aria-live) */}
        <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
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
          style={{ position: 'absolute', left: '-9999px', width: '1px', height: '1px', opacity: 0, pointerEvents: 'none' }}
        />
        <div className="w-full max-w-md flex flex-col items-center gap-3">
          <NotificationBanner notification={notification} onDismiss={dismissNotification} />
          <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Reporte de pago</CardTitle>
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
            <Button className="w-full" onClick={handleValidarCedula} disabled={loading}>
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
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
        <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">{messageForScreenReader || stepAnnouncement}</div>
        <div className="w-full max-w-md flex flex-col items-center gap-3">
          <NotificationBanner notification={notification} onDismiss={dismissNotification} />
          <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Hola, {nombre || 'Cliente'}</CardTitle>
            <p className="text-sm text-gray-600 mt-2">
              Recuerda ingresar únicamente datos de tu pago que se comprobarán y almacenarán para fines de validación de pago.
            </p>
          </CardHeader>
          <CardContent>
            <Button className="w-full" onClick={() => setStep(3)}>Continuar</Button>
          </CardContent>
        </Card>
        </div>
      </div>
    )
  }

  if (step === 3) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
        <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">{messageForScreenReader || stepAnnouncement}</div>
        <div className="w-full max-w-md flex flex-col items-center gap-3">
          <NotificationBanner notification={notification} onDismiss={dismissNotification} />
          <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Institución financiera</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <select
              className="w-full border rounded-md px-3 py-2"
              value={institucion}
              onChange={(e) => setInstitucion(e.target.value)}
            >
              <option value="">Seleccione...</option>
              {INSTITUCIONES.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
            {institucion === 'Otros' && (
              <Input
                placeholder="Nombre del banco"
                value={institucionOtros}
                onChange={(e) => setInstitucionOtros(e.target.value)}
                maxLength={MAX_LENGTH_INSTITUCION}
              />
            )}
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep(2)}>Atrás</Button>
              <Button
                className="flex-1"
                onClick={() => {
                  if (!institucionFinal.trim()) {
                    showNotification('error', 'Seleccione la institución financiera.')
                    return
                  }
                  if (institucionFinal.length > MAX_LENGTH_INSTITUCION) {
                    showNotification('error', 'Nombre de institución demasiado largo. Redúzcalo.')
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
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
        <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">{messageForScreenReader || stepAnnouncement}</div>
        <div className="w-full max-w-md flex flex-col items-center gap-3">
          <NotificationBanner notification={notification} onDismiss={dismissNotification} />
          <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Fecha y monto del pago</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Fecha de pago (obligatorio)</label>
              <Input
                type="date"
                value={fechaPago}
                onChange={(e) => setFechaPago(e.target.value)}
                max={new Date().toISOString().slice(0, 10)}
                aria-label="Seleccione la fecha en el calendario"
              />
              <p className="text-xs text-gray-500 mt-1">Seleccione la fecha en el calendario. No puede ser futura.</p>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-1">Monto (obligatorio)</label>
              <div className="flex gap-2">
                <Input
                  type="number"
                  step="0.01"
                  min={MIN_MONTO}
                  max={MAX_MONTO}
                  placeholder="Ej: 150.50"
                  value={monto}
                  onChange={(e) => setMonto(e.target.value)}
                />
                <select
                  className="border rounded-md px-3 py-2 w-24"
                  value={moneda}
                  onChange={(e) => setMoneda(e.target.value as 'BS' | 'USD')}
                >
                  <option value="BS">Bs.</option>
                  <option value="USD">USD</option>
                </select>
              </div>
              <p className="text-xs text-gray-500 mt-1">Monto mayor a 0. Máximo permitido: 999.999.999,99</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep(3)}>Atrás</Button>
              <Button
                className="flex-1"
                onClick={() => {
                  const vF = validarFechaPago(fechaPago)
                  if (!vF.valido) {
                    showNotification('error', vF.error ?? 'Fecha inválida.')
                    return
                  }
                  const vM = validarMonto(monto)
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
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
        <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">{messageForScreenReader || stepAnnouncement}</div>
        <div className="w-full max-w-md flex flex-col items-center gap-3">
          <NotificationBanner notification={notification} onDismiss={dismissNotification} />
          <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Número de documento / operación</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              placeholder="Número de serie, operación o referencia"
              value={numeroDocumento}
              onChange={(e) => setNumeroDocumento(e.target.value)}
              maxLength={MAX_LENGTH_NUMERO_OPERACION}
            />
            <p className="text-xs text-gray-500">Máximo {MAX_LENGTH_NUMERO_OPERACION} caracteres.</p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep(4)}>Atrás</Button>
              <Button
                className="flex-1"
                onClick={() => {
                  if (!numeroDocumento.trim()) {
                    showNotification('error', 'Ingrese el número de documento u operación.')
                    return
                  }
                  if (numeroDocumento.length > MAX_LENGTH_NUMERO_OPERACION) {
                    showNotification('error', 'Número de documento demasiado largo.')
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
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
        <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">{messageForScreenReader || stepAnnouncement}</div>
        <div className="w-full max-w-md flex flex-col items-center gap-3">
          <NotificationBanner notification={notification} onDismiss={dismissNotification} />
          <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Comprobante de pago</CardTitle>
            <p className="text-sm text-gray-600">Un solo archivo. JPG, PNG o PDF. Máximo 5 MB.</p>
            <p className="text-xs text-amber-700 mt-1">Si necesita ingresar otra imagen/pago, ingrese nuevamente al mismo enlace.</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              type="file"
              accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
              onChange={(e) => setArchivo(e.target.files?.[0] || null)}
            />
            {archivo && (
              <p className="text-sm text-gray-600">
                {archivo.name} ({(archivo.size / 1024).toFixed(1)} KB)
              </p>
            )}
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep(5)}>Atrás</Button>
              <Button
                className="flex-1"
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
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
        <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">{messageForScreenReader || stepAnnouncement}</div>
        <div className="w-full max-w-md flex flex-col items-center gap-3">
          <NotificationBanner notification={notification} onDismiss={dismissNotification} />
          <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Confirma los siguientes datos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p><strong>Cédula:</strong> {cedula}</p>
            <p><strong>Nombre:</strong> {nombre}</p>
            <p><strong>Institución:</strong> {institucionFinal}</p>
            <p><strong>Fecha de pago:</strong> {fechaPago}</p>
            <p><strong>Monto:</strong> {monto} {moneda}</p>
            <p><strong>Número de operación:</strong> {numeroDocumento}</p>
            <p><strong>Comprobante:</strong> {archivo?.name}</p>
          </CardContent>
          <CardContent className="pt-0 space-y-3">
            <p className="text-sm text-gray-600">
              Tu pago se procesará y se enviará al correo registrado en tu contrato de financiamiento ({emailParaVerificacion || 'correo registrado'}).
              Si tienes algún problema con el correo, contacta a cobranza@rapicreditca.com o a tu asesor para actualización.
            </p>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep(6)}>No, editar</Button>
              <Button className="flex-1" onClick={handleEnviar} disabled={loading}>
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
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">{messageForScreenReader || stepAnnouncement}</div>
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          <CardTitle className="text-green-700">Tu reporte de pago fue recibido exitosamente.</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-lg">
            <strong>Número de referencia:</strong>{' '}
            <span
              className="select-all font-mono bg-gray-100 px-2 py-1 rounded"
              title="Copiar"
            >
              #{referencia}
            </span>
          </p>
          <p className="text-sm text-gray-600">
            El recibo se emitirá hasta en 24 horas a tu correo registrado.
          </p>
          <p className="text-sm">
            Si necesitas información adicional, comunícate con nosotros por WhatsApp:{' '}
            <a href={WHATSAPP_LINK} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">
              424-4579934
            </a>
          </p>
          <p className="text-sm text-gray-500">Adiós.</p>
        </CardContent>
      </Card>
    </div>
  )
}
