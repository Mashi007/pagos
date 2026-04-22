/**





 * Formulario PÚBLICO de reporte de pago (sin login).





 * Validadores alineados con el backend: cédula (V/E/J/Z + 6-11 dígitos), monto (>0, máx 999.999.999,99),





 * fecha (obligatoria, no futura, desde calendario), institución y nº documento (longitud), archivo (PDF, JPEG, PNG, HEIC/HEIF, WebP; máx 10 MB).





 * Notificaciones claras por cada error para guiar al cliente.





 * Marca flujo público para que, si intentan ir a login, vean "Acceso prohibido" y puedan volver.





 */

import React, { useState, useRef, useEffect, useCallback } from 'react'

import { Calendar } from 'lucide-react'

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

import { formatMontoBsVe, parseMontoLatam } from '../utils/montoLatam'
import {
  extraerCaracteresCedulaPublica,
  normalizarCedulaParaProcesar,
} from '../utils/cedulaConsultaPublica'

// Límites iguales al backend (cobros_publico)

const MAX_MONTO = 999_999_999.99

const MIN_MONTO = 0.01

/** Alineado con backend: cobros_publico MIN/MAX para reporte en Bs. */
const MIN_MONTO_BS_REPORTAR = 1

const MAX_MONTO_BS_REPORTAR = 10_000_000

const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10 MB

const ALLOWED_FILE_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/webp',
  'image/gif',
  'image/heic',
  'image/heif',
  'application/pdf',
]

function _extensionArchivoLower(file: File): string {
  const n = (file.name || '').toLowerCase()
  const i = n.lastIndexOf('.')
  return i >= 0 ? n.slice(i) : ''
}

/** Misma idea que backend `mime_efectivo_comprobante_web` (iPhone suele mandar octet-stream). */
function _mimeEfectivoCliente(file: File): string {
  let t = (file.type || '').split(';')[0].trim().toLowerCase()
  const ext = _extensionArchivoLower(file)
  if (!t || t === 'application/octet-stream' || t === 'binary/octet-stream') {
    const map: Record<string, string> = {
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.png': 'image/png',
      '.pdf': 'application/pdf',
      '.heic': 'image/heic',
      '.heif': 'image/heif',
      '.webp': 'image/webp',
      '.gif': 'image/gif',
    }
    const inf = map[ext]
    if (inf) t = inf
  }
  if (t === 'image/jpg') t = 'image/jpeg'
  return t
}

const MAX_LENGTH_INSTITUCION = 100

const MAX_LENGTH_NUMERO_OPERACION = 100

function roundMontoDosDecimales(n: number): number {
  return Math.round(n * 100) / 100
}

/**
 * Interpreta el texto del monto según moneda.
 * BS: usa parseMontoLatam (miles con punto, decimales con coma).
 * USD: miles con coma opcional; decimal con punto (estilo US).
 */
function parseMontoIngresado(raw: string, moneda: 'BS' | 'USD'): number | null {
  const s = raw.trim().replace(/[\s\u00A0\u202F]/g, '')
  if (!s) return null
  if (!/^[\d.,]+$/.test(s)) return null

  if (moneda === 'BS') {
    const n = parseMontoLatam(s)
    if (!Number.isFinite(n)) return null
    return roundMontoDosDecimales(n)
  }

  const normalized = s.replace(/,/g, '')
  const num = Number(normalized)
  if (Number.isNaN(num) || !Number.isFinite(num)) return null
  return roundMontoDosDecimales(num)
}

function formatoMontoParaMostrar(num: number, moneda: 'BS' | 'USD'): string {
  if (moneda === 'BS') return formatMontoBsVe(num)
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num)
}

/** Valor enviado al backend (punto decimal, exactamente 2 decimales). */
function montoParaApi(num: number): string {
  return num.toFixed(2)
}

/** En cobros público no existe el paso interno 2 (moneda); badges van 1..6 en lugar de 1..7. */
function badgePasoFormulario(step: number, isInfopagos: boolean): number {
  if (step >= 3 && step <= 7 && !isInfopagos) return step - 1
  return step
}

function getStepAnnouncement(step: number, isInfopagos: boolean): string {
  if (!isInfopagos) {
    const m: Record<number, string> = {
      0: 'Pantalla de bienvenida: reporte de pago',
      1: 'Paso 1: Ingrese su número de cédula',
      3: 'Paso 2: Institución financiera',
      4: 'Paso 3: Fecha y monto del pago',
      5: 'Paso 4: Número de documento u operación',
      6: 'Paso 5: Adjuntar comprobante',
      7: 'Paso 6: Confirmar y enviar',
      8: 'Reporte enviado correctamente',
    }
    return m[step] ?? `Paso ${step}`
  }
  const m: Record<number, string> = {
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
  return m[step] ?? `Paso ${step}`
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

  const num = parseMontoIngresado(val, moneda)

  if (num == null)
    return {
      valido: false,
      error:
        moneda === 'BS'
          ? 'Monto no valido. Use miles con punto y decimales con coma (ej: 1.500,50).'
          : 'Monto no valido. Use punto para decimales (ej: 150.50) o comas de miles (ej: 1,500.50).',
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
      error: 'Ingrese o seleccione la fecha de pago.',
    }
  }

  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(fecha.trim())
  if (!m)
    return {
      valido: false,
      error: 'Fecha no válida. Puede escribirla o elegirla en el calendario.',
    }

  const y = Number(m[1])
  const mo = Number(m[2])
  const d = Number(m[3])
  if (!fechaYmdCalendarioValida(y, mo, d)) {
    return {
      valido: false,
      error: 'Fecha no válida. Puede escribirla o elegirla en el calendario.',
    }
  }

  const hoyCaracas = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Caracas',
  }).format(new Date())

  if (fecha > hoyCaracas)
    return { valido: false, error: 'La fecha de pago no puede ser futura.' }

  return { valido: true }
}

const MESES_ES = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
] as const

function pad2MesDia(n: number): string {
  return String(n).padStart(2, '0')
}

/** Comprueba que y-m-d existe en calendario gregoriano (m 1-12). */
function fechaYmdCalendarioValida(y: number, m: number, d: number): boolean {
  if (m < 1 || m > 12 || d < 1 || d > 31) return false
  const t = new Date(y, m - 1, d)
  return t.getFullYear() === y && t.getMonth() === m - 1 && t.getDate() === d
}

function focusInputAlSiguienteTick(el: HTMLInputElement | null) {
  if (!el) return
  requestAnimationFrame(() => {
    el.focus()
    try {
      const len = el.value.length
      el.setSelectionRange(len, len)
    } catch {
      /* noop */
    }
  })
}

/**
 * Fecha en tres segmentos (día / mes / año) para escritura rápida:
 * un dígito de día 4-9 → 04-09 y salto a mes; mes numérico 2-9 en un dígito o 01-12 en dos → nombre del mes y salto al año.
 * El valor expuesto sigue siendo YYYY-MM-DD para el backend.
 */
function segmentosInicialesDesdeYmd(value: string): {
  dia: string
  mesCommitted: number | null
  mesDigits: string
  anio: string
} {
  const v = value.trim()
  if (!v || !/^\d{4}-\d{2}-\d{2}$/.test(v)) {
    return { dia: '', mesCommitted: null, mesDigits: '', anio: '' }
  }
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(v)
  if (!m) return { dia: '', mesCommitted: null, mesDigits: '', anio: '' }
  const y = Number(m[1])
  const mo = Number(m[2])
  const d = Number(m[3])
  if (!fechaYmdCalendarioValida(y, mo, d)) {
    return { dia: '', mesCommitted: null, mesDigits: '', anio: '' }
  }
  return { dia: m[3], mesCommitted: mo, mesDigits: '', anio: m[1] }
}

function FechaPagoTecladoRapido({
  value,
  onChange,
  maxYmd,
}: {
  value: string
  onChange: (ymd: string) => void
  maxYmd: string
}) {
  const ini = segmentosInicialesDesdeYmd(value)
  const [dia, setDia] = useState(ini.dia)
  const [mesCommitted, setMesCommitted] = useState<number | null>(ini.mesCommitted)
  const [mesDigits, setMesDigits] = useState(ini.mesDigits)
  const [anio, setAnio] = useState(ini.anio)

  const mesRef = useRef<HTMLInputElement>(null)
  const anioRef = useRef<HTMLInputElement>(null)
  const nativePickerRef = useRef<HTMLInputElement>(null)

  const emitYmd = useCallback(
    (d: string, mesNum: number | null, y: string) => {
      if (d.length === 2 && mesNum != null && y.length === 4) {
        const yi = Number(y)
        const di = Number(d)
        if (
          !Number.isFinite(yi) ||
          !Number.isFinite(di) ||
          !fechaYmdCalendarioValida(yi, mesNum, di)
        ) {
          onChange('')
          return
        }
        const ymd = `${yi}-${pad2MesDia(mesNum)}-${d}`
        if (ymd > maxYmd) {
          onChange('')
          return
        }
        onChange(ymd)
      } else {
        onChange('')
      }
    },
    [maxYmd, onChange]
  )

  /** Sincronizar solo cuando hay un YMD completo válido (p. ej. calendario nativo); no vaciar al pasar a ''. */
  useEffect(() => {
    const s = segmentosInicialesDesdeYmd(value)
    if (!s.dia || s.mesCommitted == null || !s.anio) return
    setDia(s.dia)
    setMesCommitted(s.mesCommitted)
    setMesDigits('')
    setAnio(s.anio)
  }, [value])

  const mesMostrado =
    mesCommitted != null ? MESES_ES[mesCommitted - 1] : mesDigits

  const abrirCalendarioNativo = () => {
    const el = nativePickerRef.current
    if (!el) return
    const anyEl = el as HTMLInputElement & { showPicker?: () => void }
    if (typeof anyEl.showPicker === 'function') {
      anyEl.showPicker()
    } else {
      el.click()
    }
  }

  const onDiaChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let raw = e.target.value.replace(/\D/g, '').slice(0, 2)
    if (raw.length === 1 && raw >= '4' && raw <= '9') {
      raw = `0${raw}`
      setDia(raw)
      emitYmd(raw, mesCommitted, anio)
      focusInputAlSiguienteTick(mesRef.current)
      return
    }
    if (raw.length === 2) {
      const n = Number(raw)
      if (n < 1 || n > 31) {
        return
      }
      setDia(raw)
      emitYmd(raw, mesCommitted, anio)
      focusInputAlSiguienteTick(mesRef.current)
      return
    }
    setDia(raw)
    emitYmd(raw, mesCommitted, anio)
  }

  const onMesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (mesCommitted != null) return
    const digits = e.target.value.replace(/\D/g, '').slice(0, 2)
    if (digits.length === 1) {
      const c = digits[0]!
      if (c >= '2' && c <= '9') {
        const mn = Number(c)
        setMesCommitted(mn)
        setMesDigits('')
        emitYmd(dia, mn, anio)
        focusInputAlSiguienteTick(anioRef.current)
        return
      }
      setMesDigits(digits)
      emitYmd(dia, null, anio)
      return
    }
    if (digits.length === 2) {
      const mn = Number(digits)
      if (mn >= 1 && mn <= 12) {
        setMesCommitted(mn)
        setMesDigits('')
        emitYmd(dia, mn, anio)
        focusInputAlSiguienteTick(anioRef.current)
        return
      }
      setMesDigits(digits)
      emitYmd(dia, null, anio)
      return
    }
    setMesDigits('')
    emitYmd(dia, null, anio)
  }

  const onMesKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (mesCommitted == null) return
    if (e.key.length === 1 && e.key >= '0' && e.key <= '9') {
      e.preventDefault()
      setMesCommitted(null)
      setMesDigits(e.key)
      emitYmd(dia, null, anio)
    }
  }

  const onAnioChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.replace(/\D/g, '').slice(0, 4)
    setAnio(raw)
    emitYmd(dia, mesCommitted, raw)
  }

  const onPickerNative = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value
    if (!v) {
      onChange('')
      return
    }
    onChange(v)
  }

  return (
    <div className="relative">
      <input
        ref={nativePickerRef}
        type="date"
        className="sr-only"
        tabIndex={-1}
        aria-hidden
        value={value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : ''}
        max={maxYmd}
        onChange={onPickerNative}
      />
      <div
        className="flex min-h-[48px] w-full items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-base touch-manipulation focus-within:border-slate-900 focus-within:ring-1 focus-within:ring-slate-900"
        role="group"
        aria-label="Fecha de pago: día, mes y año"
      >
        <input
          type="text"
          inputMode="numeric"
          autoComplete="off"
          maxLength={2}
          placeholder="dd"
          aria-label="Día"
          className="w-9 flex-shrink-0 border-0 bg-transparent p-2 text-center font-medium text-slate-900 outline-none placeholder:text-slate-400"
          value={dia}
          onChange={onDiaChange}
        />
        <span className="text-slate-400" aria-hidden>
          |
        </span>
        <input
          ref={mesRef}
          type="text"
          inputMode={mesCommitted != null ? 'text' : 'numeric'}
          autoComplete="off"
          placeholder="mm"
          aria-label="Mes (número o nombre)"
          className="min-w-0 flex-1 border-0 bg-transparent p-2 font-medium text-slate-900 outline-none placeholder:text-slate-400"
          value={mesMostrado}
          onChange={onMesChange}
          onKeyDown={onMesKeyDown}
          onFocus={() => {
            if (mesCommitted != null) {
              setMesCommitted(null)
              setMesDigits('')
              emitYmd(dia, null, anio)
            }
          }}
        />
        <span className="text-slate-400" aria-hidden>
          |
        </span>
        <input
          ref={anioRef}
          type="text"
          inputMode="numeric"
          autoComplete="off"
          maxLength={4}
          placeholder="aaaa"
          aria-label="Año"
          className="w-14 flex-shrink-0 border-0 bg-transparent p-2 text-center font-medium text-slate-900 outline-none placeholder:text-slate-400"
          value={anio}
          onChange={onAnioChange}
        />
        <button
          type="button"
          className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-md text-slate-600 hover:bg-slate-200 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400"
          onClick={abrirCalendarioNativo}
          aria-label="Abrir calendario"
        >
          <Calendar className="h-5 w-5" aria-hidden />
        </button>
      </div>
    </div>
  )
}

function validarArchivo(file: File | null): {
  valido: boolean
  error?: string
} {
  if (!file)
    return {
      valido: false,
      error: 'Seleccione un archivo de comprobante (PDF, JPEG, PNG, HEIC o WebP).',
    }

  const type = _mimeEfectivoCliente(file)

  const okType = ALLOWED_FILE_TYPES.includes(type)

  if (!okType) {
    return {
      valido: false,
      error: 'Solo se permiten archivos PDF, JPEG, PNG, HEIC, HEIF o WebP.',
    }
  }

  if (file.size > MAX_FILE_SIZE) {
    return {
      valido: false,
      error:
        'El comprobante no puede superar 10 MB. Reduzca el tamaño del archivo.',
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
const ESTADO_CUENTA_LINK = '/rapicredit-estadocuenta'

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
  embedded = false,
}: {
  variant?: ReportePagoVariant
  embedded?: boolean
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

  useEffect(() => {
    if (!isInfopagos && step === 2) setStep(3)
  }, [isInfopagos, step])

  // Resetear confirmación de monto alto cuando cambia el monto o moneda
  useEffect(() => {
    setMontoAltoConfirmado(false)
  }, [monto, moneda])

  // Marcar flujo publico: si entran a /login ven "Acceso limitado" y pueden volver al formulario (no al panel).
  useEffect(() => {
    if (typeof sessionStorage === 'undefined') return

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

    setInfopagosEnRevision(false)

    setMontoAltoConfirmado(false)

    setStep(irAStep)
  }

  const stepAnnouncement = getStepAnnouncement(step, isInfopagos)

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

      setMoneda(puedeBs ? 'BS' : 'USD')

      setCedula(cedulaEnviar)

      setNombre(res.nombre || '')

      setEmailParaVerificacion(res.email_enmascarado ?? '')

      setStep(isInfopagos ? 2 : 3)
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

    form.append('monto', montoParaApi(vMonto.valor!))

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

        const st = String(res.estado_reportado ?? '')
          .toLowerCase()
          .replace(/\s+/g, '_')
        const enRevision = st === 'en_revision'
        let msgPublico =
          res.mensaje || 'Reporte de pago enviado correctamente.'
        if (enRevision) {
          msgPublico =
            'Su reporte fue recibido. El comprobante quedará en revisión manual antes de confirmarse; guarde su número de referencia.'
        } else if (st === 'aprobado' && res.recibo_enviado === false) {
          msgPublico =
            'Reporte aprobado, pero no se pudo enviar el recibo por correo. Guarde su referencia o contacte por WhatsApp.'
        }
        showNotification('success', msgPublico)

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
            desc: 'PDF, JPEG, PNG, HEIC o WebP, máx. 10 MB',
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
            text: 'Tu cedula',
            desc: '(V, E, G o J + digitos)',
          },
          {
            icon: 'bank' as const,
            text: 'Datos del pago',
            desc: 'Banco, fecha, monto y número',
          },
          {
            icon: 'file' as const,
            text: 'Comprobante',
            desc: 'PDF, JPEG, PNG, HEIC o WebP, máx. 10 MB',
          },
          {
            icon: 'check' as const,
            text: 'Confirmar y enviar',
            desc: 'Confirmación por correo',
          },
        ]

    return (
      <div
        className={
          embedded
            ? 'flex flex-col items-center justify-center overflow-x-hidden p-3 sm:p-4'
            : 'flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4'
        }
      >
        <div
          role="status"
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
        >
          {messageForScreenReader || stepAnnouncement}
        </div>

        <div className={embedded ? 'w-full max-w-lg' : 'w-full max-w-4xl'}>
          {/* Main container con layout responsive */}
          <div
            className={
              embedded ? 'flex flex-col' : 'grid gap-6 lg:grid-cols-2 lg:gap-8'
            }
          >
            {/* Sección izquierda: Branding (oculta en modo embedded) */}
            <div
              className={
                embedded
                  ? 'hidden'
                  : 'flex flex-col justify-center space-y-6 px-2 sm:px-0'
              }
            >
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
            <Card
              className={
                embedded
                  ? 'border border-slate-200 bg-white shadow-sm'
                  : 'mx-1 border-0 bg-white shadow-2xl sm:mx-0'
              }
            >
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
                      className="flex items-center gap-2.5 rounded-lg bg-slate-50 p-2.5 transition-colors hover:bg-slate-100"
                    >
                      <span
                        className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-[#1e3a5f] text-xs font-semibold text-white"
                        aria-hidden
                      >
                        {i + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold leading-tight text-slate-900">
                          {item.text}
                        </p>
                        <p className="text-xs leading-tight text-slate-500">
                          {item.desc}
                        </p>
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
      <div
        className={
          embedded
            ? 'flex flex-col items-center justify-center overflow-x-hidden p-3 sm:p-4'
            : 'flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4'
        }
      >
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

          <Card
            className={
              embedded
                ? 'w-full min-w-0 max-w-md border border-slate-200 bg-white shadow-sm'
                : 'w-full min-w-0 max-w-md border-0 bg-white shadow-xl'
            }
          >
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  1
                </div>
                <CardTitle className="m-0 text-lg sm:text-xl">
                  {isInfopagos ? 'Cédula del deudor' : 'Tu cédula'}
                </CardTitle>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                Letra (V, E, G o J) y 6 a 11 dígitos. Puede escribir o pegar con
                puntos, comas o guiones; el sistema los ignora. Si solo pone
                números, se usa V.
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-5 sm:px-6">
              <Input
                className="min-h-[48px] touch-manipulation border-slate-200 bg-slate-50"
                placeholder="Ej: V-16.578.561, 16.578.561 o V16578561"
                value={cedula}
                onChange={e =>
                  setCedula(extraerCaracteresCedulaPublica(e.target.value))
                }
                onKeyDown={e => e.key === 'Enter' && handleValidarCedula()}
                maxLength={28}
              />

              <Button
                className="min-h-[48px] w-full touch-manipulation bg-slate-900 font-semibold text-white hover:bg-slate-800"
                onClick={handleValidarCedula}
                disabled={loading}
              >
                {loading ? 'Verificando...' : 'Continuar'}
              </Button>

              <p className="text-center text-xs text-slate-500">
                Presiona Enter o haz clic en continuar
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  if (step === 2 && isInfopagos) {
    return (
      <div
        className={
          embedded
            ? 'flex flex-col items-center justify-center overflow-x-hidden p-3 sm:p-4'
            : 'flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4'
        }
      >
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

          <Card
            className={
              embedded
                ? 'w-full min-w-0 max-w-md border border-slate-200 bg-white shadow-sm'
                : 'w-full min-w-0 max-w-md border-0 bg-white shadow-xl'
            }
          >
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  2
                </div>
                <CardTitle className="m-0 text-lg sm:text-xl">
                  {isInfopagos
                    ? `Deudor: ${nombre || '-'}`
                    : `Hola, ${nombre || 'Cliente'}`}
                </CardTitle>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                {isInfopagos
                  ? 'Verifica la moneda disponible para este deudor'
                  : 'Selecciona la moneda en la que reportarás tu pago'}
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-5 sm:px-6">
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
                    <div className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500">
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
                    <div className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-blue-500">
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
      <div
        className={
          embedded
            ? 'flex flex-col items-center justify-center overflow-x-hidden p-3 sm:p-4'
            : 'flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4'
        }
      >
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

          <Card
            className={
              embedded
                ? 'w-full min-w-0 max-w-md border border-slate-200 bg-white shadow-sm'
                : 'w-full min-w-0 max-w-md border-0 bg-white shadow-xl'
            }
          >
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  {badgePasoFormulario(3, isInfopagos)}
                </div>
                <CardTitle className="m-0 text-lg sm:text-xl">
                  {!isInfopagos && nombre ? `Hola, ${nombre}` : 'Institución financiera'}
                </CardTitle>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                {!isInfopagos && nombre
                  ? `Cédula validada (${cedula}). Selecciona el banco o plataforma donde realizaste el pago.`
                  : 'Selecciona el banco o plataforma donde se realizó el pago'}
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
                  className="min-h-[48px] touch-manipulation border-slate-200 bg-slate-50"
                  placeholder="Nombre del banco o plataforma"
                  value={institucionOtros}
                  onChange={e => setInstitucionOtros(e.target.value)}
                  maxLength={MAX_LENGTH_INSTITUCION}
                />
              )}

              <div className="flex flex-wrap gap-2 pt-2 sm:flex-nowrap">
                <Button
                  variant="outline"
                  className="min-h-[48px] min-w-[100px] flex-1 touch-manipulation border-slate-300 text-slate-900 hover:bg-slate-50"
                  onClick={() => setStep(isInfopagos ? 2 : 1)}
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
      <div
        className={
          embedded
            ? 'flex flex-col items-center justify-center overflow-x-hidden p-3 sm:p-4'
            : 'flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4'
        }
      >
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

          <Card
            className={
              embedded
                ? 'w-full min-w-0 max-w-md border border-slate-200 bg-white shadow-sm'
                : 'w-full min-w-0 max-w-md border-0 bg-white shadow-xl'
            }
          >
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  {badgePasoFormulario(4, isInfopagos)}
                </div>
                <CardTitle className="m-0 text-lg sm:text-xl">
                  Fecha y monto
                </CardTitle>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                {isInfopagos ? (
                  <>
                    Modalidad:{' '}
                    {moneda === 'BS' ? 'bolivares (Bs.)' : 'dólares (USD)'}
                  </>
                ) : (
                  'Ingresa la fecha y el monto del pago según corresponda a tu caso.'
                )}
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-5 sm:px-6">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
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
                <FechaPagoTecladoRapido
                  value={fechaPago}
                  onChange={setFechaPago}
                  maxYmd={new Date().toISOString().slice(0, 10)}
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
                    type="text"
                    inputMode="decimal"
                    autoComplete="off"
                    placeholder={
                      moneda === 'BS' ? 'Ej: 1.500,50' : 'Ej: 1,500.50'
                    }
                    className="min-h-[48px] min-w-0 flex-1 touch-manipulation border-slate-200 bg-slate-50"
                    value={monto}
                    onChange={e => setMonto(e.target.value)}
                    aria-label={
                      moneda === 'BS'
                        ? 'Monto en bolivares, miles con punto y decimales con coma'
                        : 'Monto en dólares'
                    }
                  />
                  {isInfopagos ? (
                    <select
                      className="min-h-[48px] w-full flex-shrink-0 touch-manipulation rounded-lg border-2 border-slate-200 bg-white px-4 py-2.5 text-base font-medium focus:border-slate-900 focus:outline-none sm:w-24"
                      value={moneda}
                      onChange={e => setMoneda(e.target.value as 'BS' | 'USD')}
                      aria-label="Moneda"
                    >
                      {puedeReportarBs && <option value="BS">Bs.</option>}
                      <option value="USD">USD</option>
                    </select>
                  ) : (
                    <div
                      className="flex min-h-[48px] w-full flex-shrink-0 items-center justify-center rounded-lg border-2 border-slate-200 bg-slate-100 px-3 text-base font-semibold text-slate-800 sm:w-24"
                      aria-label={
                        moneda === 'BS'
                          ? 'Monto en bolívares'
                          : 'Monto en dólares'
                      }
                    >
                      {moneda === 'BS' ? 'Bs.' : 'USD'}
                    </div>
                  )}
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  {moneda === 'BS'
                    ? 'Entre 1 y 10.000.000 Bs. Miles con punto (.), decimales con coma (,); siempre 2 decimales al guardar.'
                    : 'Ingresa el monto en USD (sin límite máximo). Miles con coma, decimales con punto.'}
                </p>
              </div>

              <div className="flex flex-wrap gap-2 pt-2 sm:flex-nowrap">
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
                        moneda === 'BS'
                          ? '⚠️ Monto alto - Verifica que el monto esté en bolívares y no en dólares.'
                          : '⚠️ Monto alto - Verifica que el monto sea correcto.'
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
      <div
        className={
          embedded
            ? 'flex flex-col items-center justify-center overflow-x-hidden p-3 sm:p-4'
            : 'flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4'
        }
      >
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

          <Card
            className={
              embedded
                ? 'w-full min-w-0 max-w-md border border-slate-200 bg-white shadow-sm'
                : 'w-full min-w-0 max-w-md border-0 bg-white shadow-xl'
            }
          >
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  {badgePasoFormulario(5, isInfopagos)}
                </div>
                <CardTitle className="m-0 text-lg sm:text-xl">
                  Número de operación
                </CardTitle>
              </div>
              <p className="mt-2 text-xs leading-snug text-slate-600">
                {TEXTO_AVISO_NUMERO_OPERACION_FORMULARIO}
              </p>
            </CardHeader>

            <CardContent className="space-y-4 px-5 sm:px-6">
              <Input
                className="min-h-[48px] touch-manipulation border-slate-200 bg-slate-50"
                placeholder="Número de serie, transacción o referencia"
                value={numeroDocumento}
                onChange={e => setNumeroDocumento(e.target.value)}
                maxLength={MAX_LENGTH_NUMERO_OPERACION}
              />

              <p className="text-xs text-slate-500">
                Máximo {MAX_LENGTH_NUMERO_OPERACION} caracteres
              </p>

              <div className="flex flex-wrap gap-2 pt-2 sm:flex-nowrap">
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
                      showNotification('error', 'El número es demasiado largo.')
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
      <div
        className={
          embedded
            ? 'flex flex-col items-center justify-center overflow-x-hidden p-3 sm:p-4'
            : 'flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4'
        }
      >
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

          <Card
            className={
              embedded
                ? 'w-full min-w-0 max-w-md border border-slate-200 bg-white shadow-sm'
                : 'w-full min-w-0 max-w-md border-0 bg-white shadow-xl'
            }
          >
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  {badgePasoFormulario(6, isInfopagos)}
                </div>
                <CardTitle className="m-0 text-lg sm:text-xl">
                  Comprobante de pago
                </CardTitle>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                PDF, JPEG, PNG, HEIC (iPhone), WebP. Máximo 10 MB.
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
                  accept=".pdf,.jpg,.jpeg,.png,.heic,.heif,.webp,.gif,application/pdf,image/jpeg,image/png,image/heic,image/heif,image/webp,image/gif"
                  onChange={e => setArchivo(e.target.files?.[0] || null)}
                />
              )}

              <p className="text-xs text-slate-600">
                Carga el comprobante del pago realizado (factura de pago,
                captura de pantalla, etc.)
              </p>

              <div className="flex flex-wrap gap-2 pt-2 sm:flex-nowrap">
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
      <div
        className={
          embedded
            ? 'flex flex-col items-center justify-center overflow-x-hidden p-3 sm:p-4'
            : 'flex min-h-[100dvh] min-h-screen flex-col items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4'
        }
      >
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

          <Card
            className={
              embedded
                ? 'w-full min-w-0 max-w-md border border-slate-200 bg-white shadow-sm'
                : 'w-full min-w-0 max-w-md border-0 bg-white shadow-xl'
            }
          >
            <CardHeader className="border-b border-slate-100 px-5 pb-4 sm:px-6">
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-sm font-semibold text-white">
                  {badgePasoFormulario(7, isInfopagos)}
                </div>
                <CardTitle className="m-0 text-lg sm:text-xl">
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
                  <span className="text-right font-semibold text-slate-900">
                    {institucionFinal}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Fecha:</span>
                  <span className="font-semibold text-slate-900">
                    {fechaPago}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Monto:</span>
                  <span className="font-semibold text-slate-900">
                    {(() => {
                      const n = parseMontoIngresado(monto, moneda)
                      return n != null
                        ? `${formatoMontoParaMostrar(n, moneda)} ${moneda === 'BS' ? 'Bs.' : 'USD'}`
                        : `${monto} ${moneda === 'BS' ? 'Bs.' : 'USD'}`
                    })()}
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
                  <span className="max-w-[150px] truncate text-right font-semibold text-slate-900">
                    {archivo?.name}
                  </span>
                </div>
              </div>

              {/* Info note */}
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
                <p className="text-xs leading-snug text-blue-900">
                  Este pago se acreditará a{' '}
                  <strong>{nombre || 'nombre no disponible'}</strong>.
                </p>
                <p className="mt-1 text-xs leading-snug text-blue-900">
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

              <div className="flex flex-wrap gap-2 pt-2 sm:flex-nowrap">
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
              {loading && (
                <p className="text-center text-xs font-medium text-slate-600">
                  Estamos procesando su pago, un momento por favor...
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  // step === 8: pantalla final de confirmación
  return (
    <div
      className={
        embedded
          ? 'flex items-center justify-center overflow-x-hidden p-3 sm:p-4'
          : 'flex min-h-[100dvh] min-h-screen items-center justify-center overflow-x-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-3 sm:p-4'
      }
    >
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {messageForScreenReader || stepAnnouncement}
      </div>

      <Card
        className={
          embedded
            ? 'mx-1 w-full min-w-0 max-w-md border border-slate-200 bg-white shadow-sm sm:mx-0'
            : 'mx-1 w-full min-w-0 max-w-md border-0 bg-white shadow-2xl sm:mx-0'
        }
      >
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
          <div className="space-y-2 text-center">
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
            <p className="mt-2 select-all break-all font-mono text-lg font-bold text-slate-900">
              {referencia?.startsWith('#') ? referencia : `#${referencia}`}
            </p>
            <p className="mt-2 text-xs text-slate-500">
              Guarda este número para seguimiento
            </p>
          </div>

          {/* Status message */}
          {isInfopagos ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-center">
              <p className="text-sm text-amber-900">
                {infopagosEnRevision
                  ? 'Este reporte quedó en revisión manual. El recibo se enviará cuando sea aprobado.'
                  : 'Se envió el recibo al correo del deudor. Puedes descargarlo a continuación.'}
              </p>
            </div>
          ) : (
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center">
              <p className="text-sm text-blue-900">
                El recibo PDF será enviado a tu correo en los próximos minutos.
              </p>
              <p className="mt-3 text-sm font-medium text-blue-900">
                Revise su estado de cuenta{' '}
                <a
                  href={ESTADO_CUENTA_LINK}
                  className="inline-flex items-center rounded-md bg-blue-700 px-2.5 py-1 font-bold uppercase tracking-wide text-white shadow-sm transition-all hover:bg-blue-800 hover:shadow"
                >
                  aquí
                </a>
                .
              </p>
            </div>
          )}

          {/* Download button */}
          {isInfopagos &&
            !infopagosEnRevision &&
            reciboToken &&
            pagoId != null && (
              <Button
                className="min-h-[48px] w-full touch-manipulation bg-blue-600 font-semibold text-white hover:bg-blue-700"
                onClick={handleDescargarRecibo}
                disabled={descargandoRecibo}
              >
                {descargandoRecibo
                  ? 'Descargando...'
                  : '⬇️ Descargar recibo (PDF)'}
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
              ¿Necesitas ayuda?
            </p>
            <a
              href={WHATSAPP_LINK}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex min-h-[44px] items-center gap-2 rounded-full bg-emerald-600 px-4 py-2 font-semibold text-white shadow-sm transition-all hover:bg-emerald-700 hover:shadow-md"
            >
              <svg
                className="h-5 w-5"
                viewBox="0 0 32 32"
                fill="currentColor"
                aria-hidden
              >
                <path d="M19.11 17.21c-.27-.14-1.6-.79-1.85-.88-.25-.09-.43-.14-.61.14-.18.27-.7.88-.86 1.06-.16.18-.32.2-.59.07-.27-.14-1.14-.42-2.17-1.34-.8-.72-1.34-1.61-1.5-1.88-.16-.27-.02-.42.12-.56.12-.12.27-.32.41-.48.14-.16.18-.27.27-.45.09-.18.05-.34-.02-.48-.07-.14-.61-1.47-.84-2.01-.22-.53-.45-.45-.61-.46-.16-.01-.34-.01-.52-.01-.18 0-.48.07-.73.34-.25.27-.95.93-.95 2.27s.97 2.63 1.11 2.81c.14.18 1.91 2.92 4.64 4.09.65.28 1.16.45 1.56.57.66.21 1.27.18 1.75.11.53-.08 1.6-.65 1.83-1.29.23-.63.23-1.17.16-1.29-.07-.11-.25-.18-.52-.32Z" />
                <path d="M16.03 3.2c-7.04 0-12.76 5.72-12.76 12.76 0 2.24.58 4.43 1.68 6.35L3.2 28.8l6.65-1.74a12.7 12.7 0 0 0 6.18 1.58h.01c7.03 0 12.76-5.72 12.76-12.76 0-3.41-1.33-6.62-3.74-9.03A12.68 12.68 0 0 0 16.03 3.2Zm0 23.27h-.01a10.5 10.5 0 0 1-5.35-1.46l-.38-.22-3.95 1.03 1.05-3.85-.25-.39a10.56 10.56 0 0 1 1.61-13.36 10.48 10.48 0 0 1 7.29-2.94c5.82 0 10.56 4.74 10.56 10.56 0 5.82-4.74 10.56-10.57 10.56Z" />
              </svg>
              <span>Contacta por WhatsApp</span>
            </a>
            <p className="mt-2 text-xs text-slate-600">
              También puedes escribirnos para seguimiento de tu referencia.
            </p>
            <p className="sr-only">
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
