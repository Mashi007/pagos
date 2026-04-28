/**
 * Escáner Infopagos: primero cédula del deudor, luego imagen del comprobante;
 * Gemini sugiere campos alineados con Infopagos; validadores backend + edición manual y guardado vía enviar-reporte público Infopagos.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { Link, useNavigate } from 'react-router-dom'

import {
  Brain,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Eye,
} from 'lucide-react'
import toast from 'react-hot-toast'

import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import {
  escanerInfopagosExtraerComprobante,
  enviarReporteInfopagos,
  getInfopagosBorradorEscaneer,
  openInfopagosBorradorComprobanteInNewTab,
  getInfopagosBorradorComprobanteBlob,
  getReciboInfopagos,
  getReciboInfopagosStatus,
  validarCedulaPublico,
  type EscanerInfopagosExtraerResponse,
} from '../services/cobrosService'
import { DuplicadoPrestamosComparacion } from '../components/cobros/DuplicadoPrestamosComparacion'
import { formatMontoBsVe, parseMontoLatam } from '../utils/montoLatam'
import {
  extraerCaracteresCedulaPublica,
  normalizarCedulaParaProcesar,
} from '../utils/cedulaConsultaPublica'
import {
  aplicarSufijoVistoADocumento,
  collectTokensSufijoVistoArchivoDesdeFilas,
  SUFIJO_VISTO_ARCHIVO_RE,
} from '../utils/documentoSufijoVisto'
import {
  FUENTE_TASA_DEFAULT,
  normalizarFuenteTasaCambio,
  type FuenteTasaCambio,
} from '../constants/fuenteTasaCambio'
import { fechaLocalHoyISO } from './escanerInfopagosLoteModel'
import { searchParamsRevisionPagosDesdeNumeroDocumento } from '../utils/linkRevisionPagosDesdeEscaner'

type Fase = 'cedula' | 'imagen' | 'formulario' | 'exito'

/** Sesión del escáner: cédula validada y tasa para reutilizar sin revalidar en cada visita. */
const SK_ESCANER_CEDULA = {
  cedula: 'rapicredit:escanerInfopagos:cedulaRaw',
  nombre: 'rapicredit:escanerInfopagos:nombreCliente',
  fuente: 'rapicredit:escanerInfopagos:fuenteTasa',
  validada: 'rapicredit:escanerInfopagos:cedulaValidada',
} as const

function readPersistedCedulaFull(): {
  cedulaRaw: string
  nombreCliente: string
  fuenteTasa: FuenteTasaCambio
  faseInicial: Fase
} {
  try {
    const cedulaRaw = sessionStorage.getItem(SK_ESCANER_CEDULA.cedula) || ''
    const validada =
      sessionStorage.getItem(SK_ESCANER_CEDULA.validada) === '1'
    const nombreCliente = sessionStorage.getItem(SK_ESCANER_CEDULA.nombre) || ''
    const fuenteTasa = normalizarFuenteTasaCambio(
      sessionStorage.getItem(SK_ESCANER_CEDULA.fuente)
    )
    const faseInicial: Fase =
      cedulaRaw.trim() && validada ? 'imagen' : 'cedula'
    return { cedulaRaw, nombreCliente, fuenteTasa, faseInicial }
  } catch {
    return {
      cedulaRaw: '',
      nombreCliente: '',
      fuenteTasa: FUENTE_TASA_DEFAULT,
      faseInicial: 'cedula',
    }
  }
}

function persistirCedulaSesion(args: {
  cedulaRaw: string
  nombreCliente: string
  fuenteTasa: FuenteTasaCambio
  validada: boolean
}) {
  try {
    if (!args.validada || !args.cedulaRaw.trim()) return
    sessionStorage.setItem(SK_ESCANER_CEDULA.cedula, args.cedulaRaw)
    sessionStorage.setItem(SK_ESCANER_CEDULA.nombre, args.nombreCliente || '')
    sessionStorage.setItem(SK_ESCANER_CEDULA.fuente, args.fuenteTasa)
    sessionStorage.setItem(SK_ESCANER_CEDULA.validada, '1')
  } catch {
    /* ignore quota / private mode */
  }
}

function limpiarCedulaSesion() {
  try {
    sessionStorage.removeItem(SK_ESCANER_CEDULA.cedula)
    sessionStorage.removeItem(SK_ESCANER_CEDULA.nombre)
    sessionStorage.removeItem(SK_ESCANER_CEDULA.fuente)
    sessionStorage.removeItem(SK_ESCANER_CEDULA.validada)
  } catch {
    /* ignore */
  }
}

const MAX_FILE_SIZE = 10 * 1024 * 1024

const INSTITUCIONES_FINANCIERAS = [
  'BINANCE',
  'BNC',
  'Banco de Venezuela',
  'Mercantil',
  'Recibos',
] as const

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

function extensionArchivoLower(file: File): string {
  const n = (file.name || '').toLowerCase()
  const i = n.lastIndexOf('.')
  return i >= 0 ? n.slice(i) : ''
}

function mimeEfectivoCliente(file: File): string {
  let t = (file.type || '').split(';')[0].trim().toLowerCase()
  const ext = extensionArchivoLower(file)
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

function validarArchivo(file: File | null): {
  valido: boolean
  error?: string
} {
  if (!file)
    return {
      valido: false,
      error:
        'Seleccione un archivo de comprobante (PDF, JPEG, PNG, HEIC o WebP).',
    }
  const type = mimeEfectivoCliente(file)
  if (!ALLOWED_FILE_TYPES.includes(type)) {
    return {
      valido: false,
      error: 'Solo se permiten archivos PDF, JPEG, PNG, HEIC, HEIF o WebP.',
    }
  }
  if (file.size > MAX_FILE_SIZE) {
    return {
      valido: false,
      error: 'El comprobante no puede superar 10 MB.',
    }
  }
  if (file.size < 4)
    return { valido: false, error: 'El archivo está vacío o no es válido.' }
  return { valido: true }
}

const MAX_LENGTH_INSTITUCION = 100
const MAX_LENGTH_NUMERO_OPERACION = 100
const MIN_MONTO = 0.01
const MAX_MONTO = 999_999_999.99
const MIN_MONTO_BS_REPORTAR = 1
const MAX_MONTO_BS_REPORTAR = 10_000_000

function roundMontoDosDecimales(n: number): number {
  return Math.round(n * 100) / 100
}

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

function montoParaApi(num: number): string {
  return num.toFixed(2)
}

function validarFechaPago(fecha: string): { valido: boolean; error?: string } {
  if (!fecha?.trim())
    return { valido: false, error: 'Seleccione la fecha de pago.' }
  const hoy = new Date()
  hoy.setHours(0, 0, 0, 0)
  const d = new Date(fecha)
  if (Number.isNaN(d.getTime()))
    return { valido: false, error: 'Fecha no válida.' }
  d.setHours(0, 0, 0, 0)
  if (d > hoy)
    return { valido: false, error: 'La fecha de pago no puede ser futura.' }
  return { valido: true }
}

function validarMonto(
  val: string,
  moneda: 'BS' | 'USD'
): { valido: boolean; valor?: number; error?: string } {
  if (val === '' || val == null)
    return { valido: false, error: 'Ingrese el monto del pago.' }
  const num = parseMontoIngresado(val, moneda)
  if (num == null)
    return {
      valido: false,
      error:
        moneda === 'BS'
          ? 'Monto no válido. Use miles con punto y decimales con coma (ej: 1.500,50).'
          : 'Monto no válido. Use punto para decimales (ej: 150.50).',
    }
  if (moneda === 'BS') {
    if (num < MIN_MONTO_BS_REPORTAR)
      return {
        valido: false,
        error: 'En bolívares el monto debe ser al menos 1 Bs.',
      }
    if (num > MAX_MONTO_BS_REPORTAR)
      return {
        valido: false,
        error: 'En bolívares el monto no puede superar 10.000.000 Bs.',
      }
    return { valido: true, valor: num }
  }
  if (num < MIN_MONTO)
    return {
      valido: false,
      error: `El monto debe ser mayor a ${String(MIN_MONTO)}.`,
    }
  if (num > MAX_MONTO)
    return { valido: false, error: 'Monto fuera del rango permitido.' }
  return { valido: true, valor: num }
}

export default function EscanerInfopagosPage() {
  const honeypotRef = useRef<HTMLInputElement>(null)
  const tokensSufijoUsadosRef = useRef<Set<string>>(new Set())
  /** Evita doble envío antes de que React actualice `escaneando` / `enviando`. */
  const escanearActivoRef = useRef(false)
  const enviarActivoRef = useRef(false)
  const ultimoIntentoGuardarRef = useRef(0)

  const initialFromSession = useMemo(() => readPersistedCedulaFull(), [])
  const [fase, setFase] = useState<Fase>(initialFromSession.faseInicial)
  const [cedulaRaw, setCedulaRaw] = useState(initialFromSession.cedulaRaw)
  const [nombreCliente, setNombreCliente] = useState(
    initialFromSession.nombreCliente
  )
  const [validandoCedula, setValidandoCedula] = useState(false)
  const [fuenteTasa, setFuenteTasa] = useState<FuenteTasaCambio>(
    initialFromSession.fuenteTasa
  )

  const [archivo, setArchivo] = useState<File | null>(null)
  /** Borrador persistido en BD tras escanear (reutiliza comprobante al guardar). */
  const [borradorId, setBorradorId] = useState<string | null>(null)
  const navigate = useNavigate()
  const [comprobantePreviewUrl, setComprobantePreviewUrl] = useState<
    string | null
  >(null)
  const [comprobantePreviewLoading, setComprobantePreviewLoading] =
    useState(false)
  const [comprobantePreviewError, setComprobantePreviewError] = useState<
    string | null
  >(null)
  const [escaneando, setEscaneando] = useState(false)
  const [validacionCampos, setValidacionCampos] = useState<string | null>(null)
  const [validacionReglas, setValidacionReglas] = useState<string | null>(null)
  const [cedulaPagadorImg, setCedulaPagadorImg] = useState('')

  const [fechaPago, setFechaPago] = useState('')
  const [fechaDetectada, setFechaDetectada] = useState('')
  const [institucion, setInstitucion] = useState('')
  const [otroInstitucion, setOtroInstitucion] = useState('')
  const [escanerColision, setEscanerColision] = useState<{
    duplicado_en_pagos: boolean
    pago_existente_id: number | null
    prestamo_existente_id: number | null
    prestamo_objetivo_id: number | null
  } | null>(null)
  const [numeroOperacion, setNumeroOperacion] = useState('')
  const [montoStr, setMontoStr] = useState('')
  const [moneda, setMoneda] = useState<'BS' | 'USD'>('USD')

  const [enviando, setEnviando] = useState(false)
  const [referencia, setReferencia] = useState('')
  const [reciboToken, setReciboToken] = useState<string | null>(null)
  const [pagoId, setPagoId] = useState<number | null>(null)
  const [enRevision, setEnRevision] = useState(false)
  const [reciboListo, setReciboListo] = useState<boolean | null>(null)
  const [consultandoRecibo, setConsultandoRecibo] = useState(false)
  const [descargandoRecibo, setDescargandoRecibo] = useState(false)
  const borradorQueryAplicadoRef = useRef(false)
  useEffect(() => {
    if (fase !== 'exito') return
    if (enRevision) return
    if (!reciboToken || pagoId == null) return
    if (reciboListo === true) return

    let cancelled = false
    const run = async () => {
      try {
        if (!cancelled) setConsultandoRecibo(true)
        const st = await getReciboInfopagosStatus(reciboToken, pagoId)
        if (cancelled) return
        setReciboListo(Boolean(st.recibo_listo))
      } catch {
        if (!cancelled) setReciboListo(false)
      } finally {
        if (!cancelled) setConsultandoRecibo(false)
      }
    }

    void run()
    const id = window.setInterval(() => {
      void run()
    }, 4000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [enRevision, fase, pagoId, reciboListo, reciboToken])

  const cedulaNormalizada = useMemo(
    () =>
      normalizarCedulaParaProcesar(extraerCaracteresCedulaPublica(cedulaRaw)),
    [cedulaRaw]
  )

  const hayDuplicadoOperacion = useMemo(() => {
    const v = `${validacionCampos ?? ''} ${validacionReglas ?? ''}`
    if (/DUPLICADO/i.test(v)) return true
    return Boolean(escanerColision?.duplicado_en_pagos)
  }, [escanerColision, validacionCampos, validacionReglas])

  const fechaComparacionDup = useMemo(() => {
    const m = fechaPago.trim()
    if (m) return m
    const d = fechaDetectada.trim()
    if (d) return d
    return fechaLocalHoyISO()
  }, [fechaPago, fechaDetectada])

  const prestamoDuplicadoEsObjetivoEscaneer = useMemo(() => {
    const ex = escanerColision?.prestamo_existente_id
    const ob = escanerColision?.prestamo_objetivo_id
    if (typeof ex !== 'number' || typeof ob !== 'number') return null
    return ex === ob
  }, [escanerColision])

  useEffect(() => {
    let cancelled = false

    if (fase !== 'formulario') {
      setComprobantePreviewUrl(prev => {
        if (prev) URL.revokeObjectURL(prev)
        return null
      })
      setComprobantePreviewLoading(false)
      setComprobantePreviewError(null)
      return
    }

    if (archivo) {
      const u = URL.createObjectURL(archivo)
      setComprobantePreviewUrl(prev => {
        if (prev) URL.revokeObjectURL(prev)
        return u
      })
      setComprobantePreviewLoading(false)
      setComprobantePreviewError(null)
      return () => {
        URL.revokeObjectURL(u)
      }
    }

    const bid = (borradorId || '').trim()
    if (bid) {
      setComprobantePreviewLoading(true)
      setComprobantePreviewUrl(prev => {
        if (prev) URL.revokeObjectURL(prev)
        return null
      })
      setComprobantePreviewError(null)
      ;(async () => {
        try {
          const blob = await getInfopagosBorradorComprobanteBlob(bid)
          if (cancelled) return
          const u = URL.createObjectURL(blob)
          setComprobantePreviewUrl(u)
          setComprobantePreviewError(null)
        } catch {
          if (!cancelled) {
            setComprobantePreviewError(
              'No se pudo cargar el comprobante desde el servidor.'
            )
          }
        } finally {
          if (!cancelled) setComprobantePreviewLoading(false)
        }
      })()
      return () => {
        cancelled = true
        setComprobantePreviewUrl(prev => {
          if (prev) URL.revokeObjectURL(prev)
          return null
        })
      }
    }

    setComprobantePreviewUrl(prev => {
      if (prev) URL.revokeObjectURL(prev)
      return null
    })
    setComprobantePreviewLoading(false)
    setComprobantePreviewError(null)
    return undefined
  }, [fase, archivo, borradorId])

  const abrirComprobanteFormularioEnPestana = useCallback(async () => {
    if (archivo) {
      const u = URL.createObjectURL(archivo)
      window.open(u, '_blank')
      window.setTimeout(() => URL.revokeObjectURL(u), 120_000)
      return
    }
    const bid = (borradorId || '').trim()
    if (bid) {
      await openInfopagosBorradorComprobanteInNewTab(bid)
    }
  }, [archivo, borradorId])

  const aplicarExtraccionInfopagosAlFormulario = useCallback(
    (res: EscanerInfopagosExtraerResponse) => {
      const s = res.sugerencia
      if (!s) return false
      const fechaExtraida = (s.fecha_pago || '').trim()
      if (fechaExtraida) {
        setFechaPago(fechaExtraida)
        setFechaDetectada(fechaExtraida)
      } else {
        const hoy = fechaLocalHoyISO()
        setFechaPago(hoy)
        setFechaDetectada('')
      }
      const inst = (s.institucion_financiera || '').trim()
      if (
        INSTITUCIONES_FINANCIERAS.includes(
          inst as (typeof INSTITUCIONES_FINANCIERAS)[number]
        )
      ) {
        setInstitucion(inst)
        setOtroInstitucion('')
      } else {
        setInstitucion(inst)
        setOtroInstitucion(inst)
      }
      setNumeroOperacion(s.numero_operacion || '')
      setMoneda(s.moneda === 'BS' ? 'BS' : 'USD')
      if (s.monto != null && Number.isFinite(s.monto)) {
        setMontoStr(
          formatoMontoParaMostrar(s.monto, s.moneda === 'BS' ? 'BS' : 'USD')
        )
      } else {
        setMontoStr('')
      }
      setCedulaPagadorImg(s.cedula_pagador_en_comprobante || '')
      setValidacionCampos(res.validacion_campos ?? null)
      setValidacionReglas(res.validacion_reglas ?? null)
      setEscanerColision({
        duplicado_en_pagos: Boolean(res.duplicado_en_pagos),
        pago_existente_id:
          typeof res.pago_existente_id === 'number'
            ? res.pago_existente_id
            : null,
        prestamo_existente_id:
          typeof res.prestamo_existente_id === 'number'
            ? res.prestamo_existente_id
            : null,
        prestamo_objetivo_id:
          typeof res.prestamo_objetivo_id === 'number'
            ? res.prestamo_objetivo_id
            : null,
      })
      tokensSufijoUsadosRef.current = collectTokensSufijoVistoArchivoDesdeFilas(
        [{ numero_documento: s.numero_operacion || '' }]
      )
      const bid =
        typeof res.borrador_id === 'string' && res.borrador_id.trim()
          ? res.borrador_id.trim()
          : null
      setBorradorId(bid)
      setFase('formulario')
      return true
    },
    []
  )

  const handleAplicarSufijoOperacion = useCallback(
    (letter: 'A' | 'P') => {
      const actual = numeroOperacion.trim()
      if (!actual) {
        toast.error('Primero escriba un número de operación.')
        return
      }
      if (SUFIJO_VISTO_ARCHIVO_RE.test(actual)) {
        toast.error('Este número ya tiene sufijo admin (_A#### / _P####).')
        return
      }
      const nuevo = aplicarSufijoVistoADocumento(
        actual,
        letter,
        tokensSufijoUsadosRef.current
      )
      if (!nuevo || nuevo === actual) {
        toast.error('No se pudo asignar sufijo.')
        return
      }
      setNumeroOperacion(nuevo)
      toast.success(`Sufijo _${letter}#### aplicado al número de operación.`)
    },
    [numeroOperacion]
  )

  const handleValidarCedula = useCallback(async () => {
    if (!cedulaNormalizada.valido) {
      toast.error(cedulaNormalizada.error ?? 'Cédula inválida.')
      return
    }
    setValidandoCedula(true)
    try {
      const res = await validarCedulaPublico(
        cedulaNormalizada.valorParaEnviar!,
        {
          origen: 'infopagos',
        }
      )
      if (!res.ok) {
        toast.error(res.error || 'No se pudo validar la cédula.')
        return
      }
      const nombreOk = (res.nombre || '').trim()
      const fuenteOk = normalizarFuenteTasaCambio(
        res.fuente_tasa_cambio_lista_bs
      )
      setNombreCliente(nombreOk)
      setFuenteTasa(fuenteOk)
      persistirCedulaSesion({
        cedulaRaw,
        nombreCliente: nombreOk,
        fuenteTasa: fuenteOk,
        validada: true,
      })
      setFase('imagen')
      toast.success(
        'Cédula verificada. Se usará la tasa configurada en Pago Bs.'
      )
    } catch (e: unknown) {
      toast.error(
        e instanceof Error ? e.message : 'Error al validar la cédula.'
      )
    } finally {
      setValidandoCedula(false)
    }
  }, [cedulaRaw, cedulaNormalizada])

  const handleEscanear = useCallback(async () => {
    if (!cedulaNormalizada.valido || !cedulaNormalizada.valorParaEnviar) {
      toast.error('Cédula inválida.')
      return
    }
    if (escanearActivoRef.current) return
    setBorradorId(null)
    const vA = validarArchivo(archivo)
    if (!vA.valido) {
      toast.error(vA.error || 'Archivo inválido.')
      return
    }
    escanearActivoRef.current = true
    const tipo = cedulaNormalizada.valorParaEnviar.charAt(0).toUpperCase()
    const numero = cedulaNormalizada.valorParaEnviar.slice(1).replace(/\D/g, '')
    const fd = new FormData()
    fd.append('tipo_cedula', tipo)
    fd.append('numero_cedula', numero)
    fd.append('fuente_tasa_cambio', fuenteTasa)
    fd.append('comprobante', archivo!)
    setEscaneando(true)
    setValidacionCampos(null)
    setValidacionReglas(null)
    setEscanerColision(null)
    try {
      const res = await escanerInfopagosExtraerComprobante(fd)
      if (!res.ok) {
        const bid =
          typeof res.borrador_id === 'string' && res.borrador_id.trim()
            ? res.borrador_id.trim()
            : null
        setBorradorId(bid)
        setValidacionCampos(res.validacion_campos ?? null)
        setValidacionReglas(
          res.validacion_reglas ??
            res.error ??
            'No se pudo digitalizar con Gemini. Pase a revisión manual.'
        )
        // Mantener al usuario en la misma pestaña y llevarlo al formulario manual.
        setFase('formulario')
        toast(
          bid
            ? 'No se digitalizó con Gemini. Se creó borrador en servidor para revisión manual en esta misma pestaña.'
            : 'No se digitalizó con Gemini. Complete manualmente el formulario en esta misma pestaña.'
        )
        return
      }
      if (!aplicarExtraccionInfopagosAlFormulario(res)) {
        toast.error('Sin sugerencias del modelo.')
        return
      }
      const bid =
        typeof res.borrador_id === 'string' && res.borrador_id.trim()
          ? res.borrador_id.trim()
          : null
      toast.success(
        bid
          ? 'Hay observaciones de validación: el comprobante quedó en borrador en el servidor. Corrija y guarde, o gestione el borrador desde la lista.'
          : 'Datos sugeridos. Revise y corrija si hace falta antes de guardar.'
      )
    } catch {
      /* apiClient ya muestra toast en errores HTTP */
    } finally {
      escanearActivoRef.current = false
      setEscaneando(false)
    }
  }, [aplicarExtraccionInfopagosAlFormulario, archivo, cedulaNormalizada, fuenteTasa])

  const handleEditarBorrador = useCallback(
    async (id: string) => {
      try {
        const data = await getInfopagosBorradorEscaneer(id)
        const b = data.borrador
        const cedulaDisplay = `${(b.tipo_cedula || '').trim()}-${(b.numero_cedula || '').trim()}`
        setCedulaRaw(cedulaDisplay)
        setNombreCliente((b.cliente_nombre || '').trim())
        setFuenteTasa(normalizarFuenteTasaCambio(b.fuente_tasa_cambio))
        setArchivo(null)
        const snap = b.payload || {}
        const sug = snap.sugerencia
        if (!sug || typeof sug !== 'object') {
          toast.error('Borrador sin datos de sugerencia.')
          return
        }
        const resLike: EscanerInfopagosExtraerResponse = {
          ok: true,
          sugerencia: sug as EscanerInfopagosExtraerResponse['sugerencia'],
          validacion_campos:
            typeof snap.validacion_campos === 'string'
              ? snap.validacion_campos
              : null,
          validacion_reglas:
            typeof snap.validacion_reglas === 'string'
              ? snap.validacion_reglas
              : null,
          duplicado_en_pagos: Boolean(snap.duplicado_en_pagos),
          pago_existente_id:
            typeof snap.pago_existente_id === 'number'
              ? snap.pago_existente_id
              : null,
          prestamo_existente_id:
            typeof snap.prestamo_existente_id === 'number'
              ? snap.prestamo_existente_id
              : null,
          prestamo_objetivo_id:
            typeof snap.prestamo_objetivo_id === 'number'
              ? snap.prestamo_objetivo_id
              : null,
          borrador_id: b.id,
        }
        if (!aplicarExtraccionInfopagosAlFormulario(resLike)) {
          toast.error('No se pudieron aplicar los datos del borrador.')
          return
        }
        persistirCedulaSesion({
          cedulaRaw: cedulaDisplay,
          nombreCliente: (b.cliente_nombre || '').trim(),
          fuenteTasa: normalizarFuenteTasaCambio(b.fuente_tasa_cambio),
          validada: true,
        })
        toast.success(
          'Borrador cargado. El comprobante está en el servidor; corrija y guarde para pasar al flujo normal.'
        )
      } catch (e: unknown) {
        toast.error(
          e instanceof Error ? e.message : 'No se pudo abrir el borrador.'
        )
      }
    },
    [aplicarExtraccionInfopagosAlFormulario]
  )

  useEffect(() => {
    if (borradorQueryAplicadoRef.current) return
    const bid = new URLSearchParams(window.location.search).get('borrador')
    const borradorIdUrl = (bid || '').trim()
    if (!borradorIdUrl) return
    borradorQueryAplicadoRef.current = true
    void handleEditarBorrador(borradorIdUrl)
    navigate('/escaner', { replace: true })
  }, [handleEditarBorrador, navigate])

  const handleGuardar = useCallback(async () => {
    const ahora = Date.now()
    if (ahora - ultimoIntentoGuardarRef.current < 150) return
    ultimoIntentoGuardarRef.current = ahora
    if (enviarActivoRef.current) return
    if (!cedulaNormalizada.valido || !cedulaNormalizada.valorParaEnviar) {
      toast.error('Cédula inválida.')
      return
    }
    const fechaPagoEnvio =
      fechaPago.trim() || fechaDetectada.trim() || fechaLocalHoyISO()
    const vF = validarFechaPago(fechaPagoEnvio)
    if (!vF.valido) {
      toast.error(vF.error || 'Fecha inválida.')
      return
    }
    if (!institucion.trim()) {
      toast.error('Indique la institución financiera.')
      return
    }
    if (institucion.length > MAX_LENGTH_INSTITUCION) {
      toast.error('Institución demasiado larga.')
      return
    }
    if (!numeroOperacion.trim()) {
      toast.error('Indique el número de operación o referencia.')
      return
    }
    if (numeroOperacion.length > MAX_LENGTH_NUMERO_OPERACION) {
      toast.error('Número de operación demasiado largo.')
      return
    }
    const vM = validarMonto(montoStr, moneda)
    if (!vM.valido || vM.valor == null) {
      toast.error(vM.error || 'Monto inválido.')
      return
    }
    if (!borradorId) {
      const vA = validarArchivo(archivo)
      if (!vA.valido) {
        toast.error(vA.error || 'Adjunte el mismo comprobante escaneado.')
        return
      }
    }
    if (honeypotRef.current?.value?.trim()) {
      toast.error('No se pudo procesar el envío.')
      return
    }
    const tipo = cedulaNormalizada.valorParaEnviar.charAt(0).toUpperCase()
    const numero = cedulaNormalizada.valorParaEnviar.slice(1).replace(/\D/g, '')
    const form = new FormData()
    form.append('tipo_cedula', tipo)
    form.append('numero_cedula', numero)
    form.append('contact_website', '')
    form.append('fecha_pago', fechaPagoEnvio)
    form.append('institucion_financiera', institucion.trim())
    form.append('numero_operacion', numeroOperacion.trim())
    form.append('monto', montoParaApi(vM.valor))
    form.append('moneda', moneda)
    form.append('fuente_tasa_cambio', fuenteTasa)
    form.append('confirmacion_humana', 'true')
    if (borradorId) {
      form.append('borrador_id', borradorId)
    }
    if (archivo) {
      form.append('comprobante', archivo)
    } else if (!borradorId) {
      toast.error('Adjunte el comprobante o recupere un borrador con comprobante en servidor.')
      return
    }
    enviarActivoRef.current = true
    setEnviando(true)
    try {
      const res = await enviarReporteInfopagos(form)
      if (!res.ok) {
        toast.error(res.error || 'Error al guardar.')
        return
      }
      setReferencia(res.referencia_interna || '')
      setEnRevision(
        String(res.estado_reportado ?? '')
          .toLowerCase()
          .replace(/\s+/g, '_') === 'en_revision'
      )
      if (res.recibo_descarga_token) {
        setReciboToken(res.recibo_descarga_token)
        if (res.pago_id != null) setPagoId(res.pago_id)
        setReciboListo(
          typeof res.recibo_listo === 'boolean'
            ? Boolean(res.recibo_listo)
            : false
        )
      } else {
        setReciboToken(null)
        setPagoId(null)
        setReciboListo(null)
      }
      setFase('exito')
      setBorradorId(null)
      persistirCedulaSesion({
        cedulaRaw,
        nombreCliente: nombreCliente.trim(),
        fuenteTasa,
        validada: true,
      })
      toast.success(res.mensaje || 'Pago registrado.')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al guardar.')
    } finally {
      enviarActivoRef.current = false
      setEnviando(false)
    }
  }, [
    archivo,
    borradorId,
    cedulaNormalizada,
    fechaDetectada,
    fechaPago,
    institucion,
    moneda,
    montoStr,
    nombreCliente,
    numeroOperacion,
    fuenteTasa,
  ])

  const handleDescargarRecibo = useCallback(async () => {
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
    } catch (e: unknown) {
      toast.error(
        e instanceof Error ? e.message : 'No se pudo descargar el recibo.'
      )
    } finally {
      setDescargandoRecibo(false)
    }
  }, [pagoId, reciboToken, referencia])

  /** Tras éxito: conserva cédula, nombre, tasa e imagen en memoria para otro comprobante o reintento. */
  const reiniciar = () => {
    setBorradorId(null)
    setFase('imagen')
    setFechaPago('')
    setFechaDetectada('')
    setInstitucion('')
    setOtroInstitucion('')
    setEscanerColision(null)
    tokensSufijoUsadosRef.current = new Set()
    setNumeroOperacion('')
    setMontoStr('')
    setMoneda('USD')
    setValidacionCampos(null)
    setValidacionReglas(null)
    setCedulaPagadorImg('')
    setReferencia('')
    setReciboToken(null)
    setPagoId(null)
    setReciboListo(null)
    setConsultandoRecibo(false)
    setEnRevision(false)
  }

  const handleCambiarCedula = () => {
    setBorradorId(null)
    limpiarCedulaSesion()
    setFase('cedula')
    setCedulaRaw('')
    setNombreCliente('')
    setArchivo(null)
    setFechaPago('')
    setFechaDetectada('')
    setInstitucion('')
    setOtroInstitucion('')
    setEscanerColision(null)
    tokensSufijoUsadosRef.current = new Set()
    setNumeroOperacion('')
    setMontoStr('')
    setMoneda('USD')
    setValidacionCampos(null)
    setValidacionReglas(null)
    setCedulaPagadorImg('')
    setReferencia('')
    setReciboToken(null)
    setPagoId(null)
    setReciboListo(null)
    setConsultandoRecibo(false)
    setEnRevision(false)
    setFuenteTasa(FUENTE_TASA_DEFAULT)
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-4 pb-16">
      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-100 text-indigo-700">
          <Brain className="h-6 w-6" aria-hidden />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Escáner Infopagos
          </h1>
          <p className="text-sm text-slate-600">
            Cédula del deudor → comprobante → IA (Gemini) sugiere el formulario
            → validar, editar y guardar como en Infopagos.
          </p>
        </div>
      </div>

      <Card className="border-amber-200 bg-amber-50/40">
        <CardContent className="py-3">
          <p className="text-sm text-amber-950">
            Los borradores con validación pendiente se gestionan desde{' '}
            <Link
              to="/pagos?pestana=revision"
              className="font-semibold underline underline-offset-2"
            >
              Pagos &gt; Revisión
            </Link>
            , para evitar duplicar pantallas.
          </p>
        </CardContent>
      </Card>

      <input
        ref={honeypotRef}
        type="text"
        name="contact_website"
        tabIndex={-1}
        autoComplete="off"
        className="pointer-events-none absolute left-[-9999px] h-0 w-0 opacity-0"
        aria-hidden
      />

      {fase === 'cedula' && (
        <Card>
          <CardHeader>
            <CardTitle>1. Cédula del deudor</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="cedula-escaner">Cédula (V/E/J + número)</Label>
              <Input
                id="cedula-escaner"
                value={cedulaRaw}
                onChange={e => setCedulaRaw(e.target.value)}
                placeholder="Ej. V-12345678"
                autoComplete="off"
              />
              {!cedulaNormalizada.valido && cedulaRaw.trim().length > 3 && (
                <p className="text-sm text-amber-700">
                  {cedulaNormalizada.error}
                </p>
              )}
            </div>
            <Button onClick={handleValidarCedula} disabled={validandoCedula}>
              {validandoCedula ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Validando…
                </>
              ) : (
                'Continuar'
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {fase === 'imagen' && (
        <Card>
          <CardHeader className="space-y-2">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <CardTitle>2. Comprobante</CardTitle>
              <Button
                variant="ghost"
                type="button"
                className="h-auto shrink-0 px-2 py-1 text-xs text-slate-600"
                onClick={handleCambiarCedula}
              >
                Cambiar cédula / otro deudor
              </Button>
            </div>
            {initialFromSession.faseInicial === 'imagen' ? (
              <p className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
                Cédula y tasa recuperadas de esta sesión. Puede adjuntar el
                comprobante y continuar.
              </p>
            ) : null}
          </CardHeader>
          <CardContent className="space-y-4">
            {nombreCliente ? (
              <p className="text-sm text-slate-700">
                Cliente: <span className="font-semibold">{nombreCliente}</span>
              </p>
            ) : null}
            <div className="space-y-2">
              <Label htmlFor="archivo-escaner">Imagen o PDF (máx. 10 MB)</Label>
              <Input
                id="archivo-escaner"
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.webp,.heic,.heif"
                onChange={e => {
                  const f = e.target.files?.[0] ?? null
                  setArchivo(f)
                  if (f) {
                    setBorradorId(null)
                  }
                }}
              />
              {archivo ? (
                <p className="text-xs text-slate-600">
                  Comprobante en memoria:{' '}
                  <span className="font-mono font-medium">{archivo.name}</span>{' '}
                  ({Math.max(1, Math.round(archivo.size / 1024))} KB). Se conserva
                  al volver desde el formulario o al pulsar &quot;Nuevo
                  escaneo&quot; tras guardar.
                </p>
              ) : null}
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                type="button"
                onClick={() => setFase('cedula')}
              >
                Volver
              </Button>
              <Button
                onClick={handleEscanear}
                disabled={escaneando || !archivo}
              >
                {escaneando ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Leyendo con Gemini…
                  </>
                ) : (
                  <>
                    <Brain className="mr-2 h-4 w-4" />
                    Escanear y rellenar formulario
                  </>
                )}
              </Button>
            </div>
            <p className="text-xs text-slate-500">
              La lectura con IA suele tardar <strong>10-30 s</strong> según
              tamaño del archivo y la red; no cierre la pestaña. Un segundo clic
              no repetirá el envío.
            </p>
          </CardContent>
        </Card>
      )}

      {fase === 'formulario' && (
        <div className="-mx-4 flex w-[calc(100%+2rem)] max-w-none flex-col gap-0 border-y border-slate-200/70 bg-white lg:grid lg:h-[calc(100dvh-8rem)] lg:max-h-[calc(100dvh-8rem)] lg:grid-cols-2 lg:items-stretch lg:divide-x lg:divide-slate-200/70 lg:overflow-hidden">
          <aside className="flex min-h-[min(42vh,380px)] min-w-0 flex-col bg-slate-100 lg:h-full lg:max-h-full lg:min-h-0 lg:overflow-y-auto lg:overscroll-y-contain">
            <Card className="flex h-full min-h-0 flex-col rounded-none border-0 shadow-none">
              <CardHeader className="shrink-0 border-b border-slate-200/80 px-3 pb-2 pt-3 lg:pl-3 lg:pr-3">
                <CardTitle className="text-base">Comprobante</CardTitle>
                <p className="text-xs text-slate-600">
                  Misma disposición que revisión manual en Cobros: vista previa a
                  la izquierda y formulario a la derecha en pantalla ancha.
                </p>
              </CardHeader>
              <CardContent className="flex min-h-0 flex-1 flex-col space-y-2 overflow-hidden p-2 sm:p-3 lg:pl-0 lg:pr-2">
                {comprobantePreviewLoading ? (
                  <div className="flex items-center gap-2 py-12 text-sm text-slate-600">
                    <Loader2 className="h-5 w-5 shrink-0 animate-spin" />
                    Cargando comprobante…
                  </div>
                ) : comprobantePreviewError ? (
                  <p className="text-sm text-red-700">{comprobantePreviewError}</p>
                ) : comprobantePreviewUrl ? (
                  <>
                    <div className="min-h-0 flex-1 overflow-auto rounded-md border border-slate-200/80 bg-white lg:rounded-l-none lg:border-l-0">
                      <iframe
                        title="Comprobante del escáner"
                        src={comprobantePreviewUrl}
                        className="block h-[min(42vh,380px)] min-h-[240px] w-full border-0 lg:h-full lg:min-h-[min(50vh,520px)]"
                      />
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="w-full shrink-0"
                      onClick={() => void abrirComprobanteFormularioEnPestana()}
                    >
                      <Eye className="mr-1 h-4 w-4" />
                      Abrir en nueva pestaña
                    </Button>
                  </>
                ) : (
                  <p className="text-sm text-slate-600">
                    No hay vista previa (adjunte un comprobante en el paso 2 o
                    cargue un borrador con archivo en el servidor).
                  </p>
                )}
              </CardContent>
            </Card>
          </aside>

          <div className="min-h-0 min-w-0 space-y-6 overflow-y-auto overscroll-y-contain px-3 py-4 sm:px-4 lg:py-4 lg:pl-5 lg:pr-2">
            <Card className="border-0 shadow-none lg:border lg:border-slate-200/80 lg:shadow-sm">
          <CardHeader className="space-y-2">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <CardTitle>3. Formulario (editable)</CardTitle>
              <Button
                variant="ghost"
                type="button"
                className="h-auto shrink-0 px-2 py-1 text-xs text-slate-600"
                onClick={handleCambiarCedula}
              >
                Cambiar cédula / otro deudor
              </Button>
            </div>
            <p className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-medium text-sky-950">
              Usted está ingresando un pago para{' '}
              <strong>
                {nombreCliente?.trim() ||
                  cedulaNormalizada.valorParaEnviar ||
                  'cliente seleccionado'}
              </strong>
              {escanerColision?.prestamo_objetivo_id != null ? (
                <>
                  {' '}
                  y préstamo N°{' '}
                  <strong>{escanerColision.prestamo_objetivo_id}</strong>.
                </>
              ) : (
                '.'
              )}
            </p>
            {escanerColision?.prestamo_objetivo_id != null ? (
              <p className="rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-950">
                Este pago se está cargando al{' '}
                <strong>
                  préstamo N° {escanerColision.prestamo_objetivo_id}
                </strong>
                .
              </p>
            ) : null}
          </CardHeader>
          <CardContent className="space-y-4">
            {(validacionCampos || validacionReglas) && (
              <div
                className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
                role="status"
              >
                <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0" />
                <div>
                  {validacionCampos ? <p>{validacionCampos}</p> : null}
                  {validacionReglas ? <p>{validacionReglas}</p> : null}
                </div>
              </div>
            )}
            {cedulaPagadorImg ? (
              <p className="text-xs text-slate-500">
                <span className="font-medium text-slate-700">
                  Cédula en comprobante (pagador):
                </span>{' '}
                {cedulaPagadorImg}
              </p>
            ) : null}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="fecha">Fecha de pago</Label>
                {fechaDetectada.trim() ? (
                  <p className="text-xs text-slate-600">
                    Fecha detectada en la imagen (IA):{' '}
                    <span className="font-mono font-semibold text-slate-900">
                      {fechaDetectada}
                    </span>
                    . Puede ajustar el campo de fecha manualmente si la lectura
                    de la IA no coincide con el comprobante.
                  </p>
                ) : (
                  <p className="text-xs text-amber-800">
                    No se detectó fecha clara en la imagen: el campo quedó con
                    la fecha de hoy; cámbiela si el comprobante corresponde a
                    otro día.
                  </p>
                )}
                <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                  <div className="min-w-0 flex-1">
                    <Input
                      id="fecha"
                      type="date"
                      value={fechaPago}
                      onChange={e => setFechaPago(e.target.value)}
                    />
                  </div>
                </div>
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="inst">Institución financiera</Label>
                <select
                  id="inst"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={
                    INSTITUCIONES_FINANCIERAS.includes(
                      institucion as (typeof INSTITUCIONES_FINANCIERAS)[number]
                    )
                      ? institucion
                      : 'Otros'
                  }
                  onChange={e => {
                    const v = e.target.value
                    if (v === 'Otros') {
                      setInstitucion(otroInstitucion.trim() || '')
                    } else {
                      setInstitucion(v)
                      setOtroInstitucion('')
                    }
                  }}
                >
                  <option value="">Seleccione banco…</option>
                  {INSTITUCIONES_FINANCIERAS.map(opt => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                  <option value="Otros">Otro</option>
                </select>
                {!INSTITUCIONES_FINANCIERAS.includes(
                  institucion as (typeof INSTITUCIONES_FINANCIERAS)[number]
                ) && (
                  <Input
                    value={otroInstitucion}
                    onChange={e => {
                      const val = e.target.value
                      setOtroInstitucion(val)
                      setInstitucion(val.trim())
                    }}
                    placeholder="Nombre del banco o entidad"
                    maxLength={MAX_LENGTH_INSTITUCION}
                  />
                )}
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="nrop">Nº operación / referencia / serial</Label>
                <Input
                  id="nrop"
                  value={numeroOperacion}
                  onChange={e => setNumeroOperacion(e.target.value)}
                  maxLength={MAX_LENGTH_NUMERO_OPERACION}
                />
                {hayDuplicadoOperacion ? (
                  <div className="space-y-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
                    <p className="font-medium text-rose-950">
                      Hay coincidencia o posible duplicado con cartera. Compare
                      préstamo y fecha antes de sufijo o guardar (misma vista que
                      Cobros).
                    </p>
                    <DuplicadoPrestamosComparacion
                      prestamoExistenteId={escanerColision?.prestamo_existente_id}
                      pagoExistenteId={escanerColision?.pago_existente_id}
                      pagoExistenteEstado={null}
                      pagoExistenteFechaPago={null}
                      prestamoObjetivoId={escanerColision?.prestamo_objetivo_id}
                      fechaPagoReporteIso={fechaComparacionDup}
                      prestamoDuplicadoEsObjetivo={
                        prestamoDuplicadoEsObjetivoEscaneer
                      }
                      prestamoObjetivoMultiple={null}
                    />
                    <div className="flex flex-wrap gap-2">
                      {typeof escanerColision?.prestamo_existente_id ===
                      'number' ? (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            navigate(
                              `/prestamos?filtro_prestamo_id=${escanerColision.prestamo_existente_id}`
                            )
                          }
                        >
                          Abrir préstamo #{escanerColision.prestamo_existente_id}
                        </Button>
                      ) : null}
                      {typeof escanerColision?.prestamo_objetivo_id ===
                        'number' &&
                      typeof escanerColision?.prestamo_existente_id ===
                        'number' &&
                      escanerColision.prestamo_objetivo_id !==
                        escanerColision.prestamo_existente_id ? (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            navigate(
                              `/prestamos?filtro_prestamo_id=${escanerColision.prestamo_objetivo_id}`
                            )
                          }
                        >
                          Abrir préstamo actual #
                          {escanerColision.prestamo_objetivo_id}
                        </Button>
                      ) : null}
                    </div>
                  </div>
                ) : null}
                {hayDuplicadoOperacion ? (
                  <div className="rounded-md border border-violet-200 bg-violet-50 px-3 py-2 text-sm text-violet-950">
                    <p className="font-medium">Sufijo admin (carga masiva)</p>
                    <p className="mt-1 text-xs leading-snug">
                      Añade{' '}
                      <code className="rounded bg-white/80 px-1">_A####</code> o{' '}
                      <code className="rounded bg-white/80 px-1">_P####</code> al
                      final del número para que el documento sea único en
                      cartera. Luego guarde el reporte.
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        title="Sufijo en borrador: _A#### (luego Guardar)"
                        onClick={() => handleAplicarSufijoOperacion('A')}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        Agregar sufijo A
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        title="Sufijo en borrador: _P#### (luego Guardar)"
                        onClick={() => handleAplicarSufijoOperacion('P')}
                      >
                        <Eye className="mr-2 h-4 w-4" />
                        Agregar sufijo P
                      </Button>
                    </div>
                  </div>
                ) : null}
                {hayDuplicadoOperacion ? (
                  <p className="text-sm text-slate-700">
                    <Link
                      className="font-medium text-indigo-700 underline underline-offset-2 hover:text-indigo-900"
                      to={{
                        pathname: '/pagos',
                        search:
                          searchParamsRevisionPagosDesdeNumeroDocumento(
                            numeroOperacion
                          ),
                      }}
                    >
                      Revisar si está en la pestaña Revisión
                    </Link>
                  </p>
                ) : null}
              </div>
              <div className="space-y-2">
                <Label>Moneda (detectada por escáner; editable)</Label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={moneda}
                  onChange={e =>
                    setMoneda(e.target.value === 'BS' ? 'BS' : 'USD')
                  }
                >
                  <option value="USD">USD / divisas</option>
                  <option value="BS">Bolívares (Bs.)</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="monto">Monto</Label>
                <Input
                  id="monto"
                  value={montoStr}
                  onChange={e => setMontoStr(e.target.value)}
                  inputMode="decimal"
                  autoComplete="off"
                />
              </div>
            </div>

            <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
              {borradorId && !archivo ? (
                <>
                  El comprobante de este borrador está guardado en el servidor.
                  Puede guardar sin adjuntar de nuevo. Si en el paso anterior elige
                  otro archivo, se descarta el enlace al borrador y se usará ese
                  archivo al guardar.
                </>
              ) : (
                <>
                  Se reutiliza automáticamente el comprobante escaneado al inicio
                  para guardar y para procesos siguientes (por ejemplo, recibo). No
                  es necesario volver a cargarlo.
                </>
              )}
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                type="button"
                onClick={() => setFase('imagen')}
              >
                Volver
              </Button>
              <Button onClick={handleGuardar} disabled={enviando}>
                {enviando ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Guardando…
                  </>
                ) : (
                  'Guardar reporte Infopagos'
                )}
              </Button>
            </div>
            {enviando ? (
              <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-900">
                Espere, estoy procesando su pago.
              </p>
            ) : null}
          </CardContent>
        </Card>
          </div>
        </div>
      )}

      {fase === 'exito' && (
        <Card className="border-emerald-200 bg-emerald-50/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-emerald-900">
              <CheckCircle2 className="h-6 w-6" />
              Reporte enviado
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-emerald-950">
            <p>
              Referencia:{' '}
              <span className="font-mono font-semibold">
                {referencia || '-'}
              </span>
            </p>
            {enRevision ? (
              <p>
                Su pago está siendo revisado para asegurar coherencia con los
                datos de la imagen. Cuando sea aprobado, el recibo quedará
                disponible para descarga.
              </p>
            ) : null}
            {reciboToken && pagoId != null && reciboListo ? (
              <Button
                type="button"
                variant="secondary"
                onClick={handleDescargarRecibo}
                disabled={descargandoRecibo}
              >
                {descargandoRecibo ? 'Descargando…' : 'Descargar recibo PDF'}
              </Button>
            ) : !enRevision && reciboToken && pagoId != null ? (
              <p className="rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs text-indigo-950">
                {consultandoRecibo
                  ? 'Espere, estamos generando su recibo. Esta pantalla se actualizará automáticamente.'
                  : 'Estamos terminando de generar su recibo. Actualizando estado...'}
              </p>
            ) : !enRevision ? (
              <p className="rounded-md border border-emerald-200 bg-emerald-100/60 px-3 py-2 text-xs text-emerald-900">
                El pago fue aprobado. Si no ve el botón de descarga, actualice
                la página para obtener el enlace del recibo.
              </p>
            ) : null}
            <div className="space-y-2">
              <Button type="button" onClick={reiniciar}>
                Nuevo escaneo
              </Button>
              <p className="text-xs text-emerald-900/90">
                Se conservan la cédula validada, la tasa y el archivo del
                comprobante en esta pestaña para otro envío o corrección; use
                &quot;Cambiar cédula&quot; en el paso del comprobante si corresponde
                otro deudor.
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

