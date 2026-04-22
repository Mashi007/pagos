/**
 * Escáner Infopagos: primero cédula del deudor, luego imagen del comprobante;
 * Gemini sugiere campos alineados con Infopagos; validadores backend + edición manual y guardado vía enviar-reporte público Infopagos.
 */
import { useCallback, useMemo, useRef, useState } from 'react'

import { Brain, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'

import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import {
  escanerInfopagosExtraerComprobante,
  enviarReporteInfopagos,
  getReciboInfopagos,
  validarCedulaPublico,
} from '../services/cobrosService'
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

function validarArchivo(file: File | null): { valido: boolean; error?: string } {
  if (!file)
    return {
      valido: false,
      error: 'Seleccione un archivo de comprobante (PDF, JPEG, PNG, HEIC o WebP).',
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
  if (!fecha?.trim()) return { valido: false, error: 'Seleccione la fecha de pago.' }
  const hoy = new Date()
  hoy.setHours(0, 0, 0, 0)
  const d = new Date(fecha)
  if (Number.isNaN(d.getTime()))
    return { valido: false, error: 'Fecha no válida.' }
  d.setHours(0, 0, 0, 0)
  if (d > hoy) return { valido: false, error: 'La fecha de pago no puede ser futura.' }
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
      return { valido: false, error: 'En bolívares el monto debe ser al menos 1 Bs.' }
    if (num > MAX_MONTO_BS_REPORTAR)
      return {
        valido: false,
        error: 'En bolívares el monto no puede superar 10.000.000 Bs.',
      }
    return { valido: true, valor: num }
  }
  if (num < MIN_MONTO)
    return { valido: false, error: `El monto debe ser mayor a ${String(MIN_MONTO)}.` }
  if (num > MAX_MONTO) return { valido: false, error: 'Monto fuera del rango permitido.' }
  return { valido: true, valor: num }
}

type Fase = 'cedula' | 'imagen' | 'formulario' | 'exito'

export default function EscanerInfopagosPage() {
  const honeypotRef = useRef<HTMLInputElement>(null)
  const tokensSufijoUsadosRef = useRef<Set<string>>(new Set())
  /** Evita doble envío antes de que React actualice `escaneando` / `enviando`. */
  const escanearActivoRef = useRef(false)
  const enviarActivoRef = useRef(false)

  const [fase, setFase] = useState<Fase>('cedula')
  const [cedulaRaw, setCedulaRaw] = useState('')
  const [nombreCliente, setNombreCliente] = useState('')
  const [validandoCedula, setValidandoCedula] = useState(false)

  const [archivo, setArchivo] = useState<File | null>(null)
  const [escaneando, setEscaneando] = useState(false)
  const [validacionCampos, setValidacionCampos] = useState<string | null>(null)
  const [validacionReglas, setValidacionReglas] = useState<string | null>(null)
  const [cedulaPagadorImg, setCedulaPagadorImg] = useState('')

  const [fechaPago, setFechaPago] = useState('')
  const [fechaDetectada, setFechaDetectada] = useState('')
  /** Si hay fecha en imagen: el usuario debe confirmar o rechazar explícitamente. */
  const [confirmaFechaDetectada, setConfirmaFechaDetectada] = useState<
    null | 'si' | 'no'
  >(null)
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
  const [descargandoRecibo, setDescargandoRecibo] = useState(false)

  const cedulaNormalizada = useMemo(
    () => normalizarCedulaParaProcesar(extraerCaracteresCedulaPublica(cedulaRaw)),
    [cedulaRaw]
  )

  const hayDuplicadoOperacion = useMemo(() => {
    const v = `${validacionCampos ?? ''} ${validacionReglas ?? ''}`
    if (/DUPLICADO/i.test(v)) return true
    return Boolean(escanerColision?.duplicado_en_pagos)
  }, [escanerColision, validacionCampos, validacionReglas])

  const handleAplicarSufijoOperacion = useCallback((letter: 'A' | 'P') => {
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
  }, [numeroOperacion])

  const handleValidarCedula = useCallback(async () => {
    if (!cedulaNormalizada.valido) {
      toast.error(cedulaNormalizada.error ?? 'Cédula inválida.')
      return
    }
    setValidandoCedula(true)
    try {
      const res = await validarCedulaPublico(cedulaNormalizada.valorParaEnviar!, {
        origen: 'infopagos',
      })
      if (!res.ok) {
        toast.error(res.error || 'No se pudo validar la cédula.')
        return
      }
      setNombreCliente((res.nombre || '').trim())
      setFase('imagen')
      toast.success('Cédula verificada. Adjunte el comprobante.')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al validar la cédula.')
    } finally {
      setValidandoCedula(false)
    }
  }, [cedulaNormalizada])

  const handleEscanear = useCallback(async () => {
    if (!cedulaNormalizada.valido || !cedulaNormalizada.valorParaEnviar) {
      toast.error('Cédula inválida.')
      return
    }
    if (escanearActivoRef.current) return
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
    fd.append('comprobante', archivo!)
    setEscaneando(true)
    setValidacionCampos(null)
    setValidacionReglas(null)
    setEscanerColision(null)
    try {
      const res = await escanerInfopagosExtraerComprobante(fd)
      if (!res.ok) {
        toast.error(res.error || 'No se pudo leer el comprobante.')
        return
      }
      const s = res.sugerencia
      if (!s) {
        toast.error('Sin sugerencias del modelo.')
        return
      }
      const fechaExtraida = s.fecha_pago || ''
      setFechaPago(fechaExtraida)
      setFechaDetectada(fechaExtraida)
      setConfirmaFechaDetectada(null)
      const inst = (s.institucion_financiera || '').trim()
      if (INSTITUCIONES_FINANCIERAS.includes(inst as (typeof INSTITUCIONES_FINANCIERAS)[number])) {
        setInstitucion(inst)
        setOtroInstitucion('')
      } else {
        setInstitucion(inst)
        setOtroInstitucion(inst)
      }
      setNumeroOperacion(s.numero_operacion || '')
      setMoneda(s.moneda === 'BS' ? 'BS' : 'USD')
      if (s.monto != null && Number.isFinite(s.monto)) {
        setMontoStr(formatoMontoParaMostrar(s.monto, s.moneda === 'BS' ? 'BS' : 'USD'))
      } else {
        setMontoStr('')
      }
      setCedulaPagadorImg(s.cedula_pagador_en_comprobante || '')
      setValidacionCampos(res.validacion_campos ?? null)
      setValidacionReglas(res.validacion_reglas ?? null)
      setEscanerColision({
        duplicado_en_pagos: Boolean(res.duplicado_en_pagos),
        pago_existente_id:
          typeof res.pago_existente_id === 'number' ? res.pago_existente_id : null,
        prestamo_existente_id:
          typeof res.prestamo_existente_id === 'number'
            ? res.prestamo_existente_id
            : null,
        prestamo_objetivo_id:
          typeof res.prestamo_objetivo_id === 'number'
            ? res.prestamo_objetivo_id
            : null,
      })
      tokensSufijoUsadosRef.current = collectTokensSufijoVistoArchivoDesdeFilas([
        { numero_documento: s.numero_operacion || '' },
      ])
      setFase('formulario')
      toast.success('Datos sugeridos. Revise y corrija si hace falta antes de guardar.')
    } catch {
      /* apiClient ya muestra toast en errores HTTP */
    } finally {
      escanearActivoRef.current = false
      setEscaneando(false)
    }
  }, [archivo, cedulaNormalizada])

  const handleGuardar = useCallback(async () => {
    if (enviarActivoRef.current) return
    if (!cedulaNormalizada.valido || !cedulaNormalizada.valorParaEnviar) {
      toast.error('Cédula inválida.')
      return
    }
    const vF = validarFechaPago(fechaPago)
    if (!vF.valido) {
      toast.error(vF.error || 'Fecha inválida.')
      return
    }
    const hayFechaDetectada = Boolean(fechaDetectada.trim())
    if (hayFechaDetectada && confirmaFechaDetectada == null) {
      toast.error(
        'Indique si la fecha leída del comprobante es correcta (Sí) o si la corregirá (No).'
      )
      return
    }
    if (
      hayFechaDetectada &&
      confirmaFechaDetectada === 'si' &&
      fechaPago.trim() !== fechaDetectada.trim()
    ) {
      toast.error(
        'Marcó «Sí» a la fecha del comprobante: el campo debe coincidir con la fecha detectada en la imagen, o elija «No» si corrige la fecha.'
      )
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
    const vA = validarArchivo(archivo)
    if (!vA.valido) {
      toast.error(vA.error || 'Adjunte el mismo comprobante escaneado.')
      return
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
    form.append('fecha_pago', fechaPago)
    form.append('institucion_financiera', institucion.trim())
    form.append('numero_operacion', numeroOperacion.trim())
    form.append('monto', montoParaApi(vM.valor))
    form.append('moneda', moneda)
    form.append('comprobante', archivo!)
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
      } else {
        setReciboToken(null)
        setPagoId(null)
      }
      setFase('exito')
      toast.success(res.mensaje || 'Pago registrado.')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al guardar.')
    } finally {
      enviarActivoRef.current = false
      setEnviando(false)
    }
  }, [
    archivo,
    cedulaNormalizada,
    confirmaFechaDetectada,
    fechaDetectada,
    fechaPago,
    institucion,
    moneda,
    montoStr,
    numeroOperacion,
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
      toast.error(e instanceof Error ? e.message : 'No se pudo descargar el recibo.')
    } finally {
      setDescargandoRecibo(false)
    }
  }, [pagoId, reciboToken, referencia])

  const reiniciar = () => {
    setFase('cedula')
    setCedulaRaw('')
    setNombreCliente('')
    setArchivo(null)
    setFechaPago('')
    setFechaDetectada('')
    setConfirmaFechaDetectada(null)
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
    setEnRevision(false)
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
            Cédula del deudor → comprobante → IA (Gemini) sugiere el formulario → validar, editar y
            guardar como en Infopagos.
          </p>
        </div>
      </div>

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
                <p className="text-sm text-amber-700">{cedulaNormalizada.error}</p>
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
          <CardHeader>
            <CardTitle>2. Comprobante</CardTitle>
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
                onChange={e => setArchivo(e.target.files?.[0] ?? null)}
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" type="button" onClick={() => setFase('cedula')}>
                Volver
              </Button>
              <Button onClick={handleEscanear} disabled={escaneando || !archivo}>
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
              La lectura con IA suele tardar <strong>10–30 s</strong> según tamaño del archivo y la red;
              no cierre la pestaña. Un segundo clic no repetirá el envío.
            </p>
          </CardContent>
        </Card>
      )}

      {fase === 'formulario' && (
        <Card>
          <CardHeader>
            <CardTitle>3. Formulario (editable)</CardTitle>
            <p className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm font-medium text-sky-950">
              Usted está ingresando un pago para{' '}
              <strong>
                {nombreCliente?.trim() || cedulaNormalizada.valorParaEnviar || 'cliente seleccionado'}
              </strong>
              {escanerColision?.prestamo_objetivo_id != null ? (
                <>
                  {' '}
                  y préstamo N° <strong>{escanerColision.prestamo_objetivo_id}</strong>.
                </>
              ) : (
                '.'
              )}
            </p>
            {escanerColision?.prestamo_objetivo_id != null ? (
              <p className="rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-950">
                Este pago se está cargando al{' '}
                <strong>préstamo N° {escanerColision.prestamo_objetivo_id}</strong>.
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
                <span className="font-medium text-slate-700">Cédula en comprobante (pagador):</span>{' '}
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
                    . Puede ajustar el campo de fecha manualmente si la lectura de la IA no coincide con el comprobante.
                  </p>
                ) : (
                  <p className="text-xs text-amber-800">
                    No se detectó fecha clara en la imagen: indique la fecha de pago manualmente.
                  </p>
                )}
                <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                  <div className="min-w-0 flex-1">
                    <Input
                      id="fecha"
                      type="date"
                      value={fechaPago}
                      onChange={e => {
                        const v = e.target.value
                        setFechaPago(v)
                        if (fechaDetectada.trim() && v.trim() !== fechaDetectada.trim()) {
                          setConfirmaFechaDetectada('no')
                        }
                      }}
                    />
                  </div>
                  {fechaDetectada.trim() ? (
                    <div className="flex shrink-0 flex-col gap-1">
                      <span className="text-xs font-medium text-slate-700">
                        ¿La fecha leída del comprobante es correcta?
                      </span>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant={confirmaFechaDetectada === 'si' ? 'default' : 'outline'}
                          className={
                            confirmaFechaDetectada === 'si'
                              ? 'bg-emerald-600 hover:bg-emerald-700'
                              : ''
                          }
                          onClick={() => {
                            setConfirmaFechaDetectada('si')
                            setFechaPago(fechaDetectada)
                          }}
                        >
                          Sí
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant={confirmaFechaDetectada === 'no' ? 'default' : 'outline'}
                          className={
                            confirmaFechaDetectada === 'no'
                              ? 'bg-amber-600 hover:bg-amber-700'
                              : ''
                          }
                          onClick={() => setConfirmaFechaDetectada('no')}
                        >
                          No
                        </Button>
                      </div>
                    </div>
                  ) : null}
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
                {escanerColision?.duplicado_en_pagos &&
                typeof escanerColision.prestamo_existente_id === 'number' ? (
                  <p className="text-sm font-medium text-rose-800">
                    Este número ya está cargado en cartera, aplicado al{' '}
                    <strong>préstamo N° {escanerColision.prestamo_existente_id}</strong>.
                    {typeof escanerColision.pago_existente_id === 'number'
                      ? ` (pago #${escanerColision.pago_existente_id})`
                      : ''}
                  </p>
                ) : hayDuplicadoOperacion ? (
                  <p className="text-sm font-medium text-rose-800">
                    Validación: posible duplicado de número de operación / documento. Use un sufijo
                    distinto si corresponde el mismo comprobante para otro caso.
                  </p>
                ) : null}
                {hayDuplicadoOperacion ? (
                  <div className="rounded-md border border-violet-200 bg-violet-50 px-3 py-2 text-sm text-violet-950">
                    <p className="font-medium">Sufijo admin (misma lógica que carga masiva)</p>
                    <p className="mt-1 text-xs leading-snug">
                      Añade <code className="rounded bg-white/80 px-1">_A####</code> o{' '}
                      <code className="rounded bg-white/80 px-1">_P####</code> al final del número
                      para que el documento sea único en cartera.
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={() => handleAplicarSufijoOperacion('A')}
                      >
                        Aplicar sufijo _A…
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={() => handleAplicarSufijoOperacion('P')}
                      >
                        Aplicar sufijo _P…
                      </Button>
                    </div>
                  </div>
                ) : null}
              </div>
              <div className="space-y-2">
                <Label>Moneda</Label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  value={moneda}
                  onChange={e => setMoneda(e.target.value === 'BS' ? 'BS' : 'USD')}
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
              Se reutiliza automáticamente el comprobante escaneado al inicio para guardar y para procesos
              siguientes (por ejemplo, recibo). No es necesario volver a cargarlo.
            </div>

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" type="button" onClick={() => setFase('imagen')}>
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
              Referencia: <span className="font-mono font-semibold">{referencia || '—'}</span>
            </p>
            {enRevision ? (
              <p>
                Su pago está siendo revisado para asegurar coherencia con los datos de la imagen.
                Cuando sea aprobado, el recibo quedará disponible para descarga.
              </p>
            ) : null}
            {reciboToken && pagoId != null ? (
              <Button
                type="button"
                variant="secondary"
                onClick={handleDescargarRecibo}
                disabled={descargandoRecibo}
              >
                {descargandoRecibo ? 'Descargando…' : 'Descargar recibo PDF'}
              </Button>
            ) : !enRevision ? (
              <p className="rounded-md border border-emerald-200 bg-emerald-100/60 px-3 py-2 text-xs text-emerald-900">
                El pago fue aprobado. Si no ve el botón de descarga, actualice la página para
                obtener el enlace del recibo.
              </p>
            ) : null}
            <Button type="button" onClick={reiniciar}>
              Nuevo escaneo
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
