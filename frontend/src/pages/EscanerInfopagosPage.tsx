/**
 * Escáner Infopagos: primero cédula del deudor, luego imagen del comprobante;
 * Gemini sugiere campos alineados con Infopagos; validadores backend + edición manual y guardado vía enviar-reporte público Infopagos.
 */
import { useCallback, useMemo, useRef, useState } from 'react'

import { Brain, Loader2, CheckCircle2, AlertTriangle, Lock } from 'lucide-react'
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

const MAX_FILE_SIZE = 10 * 1024 * 1024

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

  const [fase, setFase] = useState<Fase>('cedula')
  const [cedulaRaw, setCedulaRaw] = useState('')
  const [nombreCliente, setNombreCliente] = useState('')
  const [validandoCedula, setValidandoCedula] = useState(false)

  const [archivo, setArchivo] = useState<File | null>(null)
  const [escaneando, setEscaneando] = useState(false)
  const [validacionCampos, setValidacionCampos] = useState<string | null>(null)
  const [validacionReglas, setValidacionReglas] = useState<string | null>(null)
  const [notasModelo, setNotasModelo] = useState('')
  const [cedulaPagadorImg, setCedulaPagadorImg] = useState('')

  const [fechaPago, setFechaPago] = useState('')
  const [fechaDetectada, setFechaDetectada] = useState('')
  const [habilitarEdicionFecha, setHabilitarEdicionFecha] = useState(false)
  const [justificacionFecha, setJustificacionFecha] = useState('')
  const [institucion, setInstitucion] = useState('')
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
    const vA = validarArchivo(archivo)
    if (!vA.valido) {
      toast.error(vA.error || 'Archivo inválido.')
      return
    }
    const tipo = cedulaNormalizada.valorParaEnviar.charAt(0).toUpperCase()
    const numero = cedulaNormalizada.valorParaEnviar.slice(1).replace(/\D/g, '')
    const fd = new FormData()
    fd.append('tipo_cedula', tipo)
    fd.append('numero_cedula', numero)
    fd.append('comprobante', archivo!)
    setEscaneando(true)
    setValidacionCampos(null)
    setValidacionReglas(null)
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
      setHabilitarEdicionFecha(!fechaExtraida)
      setJustificacionFecha('')
      setInstitucion(s.institucion_financiera || '')
      setNumeroOperacion(s.numero_operacion || '')
      setMoneda(s.moneda === 'BS' ? 'BS' : 'USD')
      if (s.monto != null && Number.isFinite(s.monto)) {
        setMontoStr(formatoMontoParaMostrar(s.monto, s.moneda === 'BS' ? 'BS' : 'USD'))
      } else {
        setMontoStr('')
      }
      setNotasModelo(s.notas_modelo || '')
      setCedulaPagadorImg(s.cedula_pagador_en_comprobante || '')
      setValidacionCampos(res.validacion_campos ?? null)
      setValidacionReglas(res.validacion_reglas ?? null)
      setFase('formulario')
      toast.success('Datos sugeridos. Revise y corrija si hace falta antes de guardar.')
    } catch {
      /* apiClient ya muestra toast en errores HTTP */
    } finally {
      setEscaneando(false)
    }
  }, [archivo, cedulaNormalizada])

  const handleGuardar = useCallback(async () => {
    if (!cedulaNormalizada.valido || !cedulaNormalizada.valorParaEnviar) {
      toast.error('Cédula inválida.')
      return
    }
    const vF = validarFechaPago(fechaPago)
    if (!vF.valido) {
      toast.error(vF.error || 'Fecha inválida.')
      return
    }
    const fechaCambioManual =
      Boolean(fechaDetectada) &&
      Boolean(habilitarEdicionFecha) &&
      fechaPago.trim() !== fechaDetectada.trim()
    if (habilitarEdicionFecha && justificacionFecha.trim().length < 12) {
      toast.error('Indique una justificación mínima de 12 caracteres para corregir la fecha.')
      return
    }
    if (fechaCambioManual && !justificacionFecha.trim()) {
      toast.error('Debe justificar por qué corrige la fecha detectada en el comprobante.')
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
    if (habilitarEdicionFecha && justificacionFecha.trim()) {
      const motivoFecha = fechaCambioManual
        ? `Ajuste manual de fecha: ${fechaDetectada || 'sin fecha detectada'} -> ${fechaPago}. ${justificacionFecha.trim()}`
        : `Fecha ingresada manualmente por baja legibilidad en comprobante: ${justificacionFecha.trim()}`
      form.append('observacion', motivoFecha)
    }
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
      setEnviando(false)
    }
  }, [
    archivo,
    cedulaNormalizada,
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
    setHabilitarEdicionFecha(false)
    setJustificacionFecha('')
    setInstitucion('')
    setNumeroOperacion('')
    setMontoStr('')
    setMoneda('USD')
    setValidacionCampos(null)
    setValidacionReglas(null)
    setNotasModelo('')
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
          </CardContent>
        </Card>
      )}

      {fase === 'formulario' && (
        <Card>
          <CardHeader>
            <CardTitle>3. Formulario (editable)</CardTitle>
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
            {notasModelo ? (
              <p className="text-xs text-slate-500">
                <span className="font-medium text-slate-700">Notas del modelo:</span> {notasModelo}
              </p>
            ) : null}
            {cedulaPagadorImg ? (
              <p className="text-xs text-slate-500">
                <span className="font-medium text-slate-700">Cédula en comprobante (pagador):</span>{' '}
                {cedulaPagadorImg}
              </p>
            ) : null}

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="fecha">Fecha de pago</Label>
                <Input
                  id="fecha"
                  type="date"
                  value={fechaPago}
                  disabled={!habilitarEdicionFecha}
                  onChange={e => setFechaPago(e.target.value)}
                />
                {!habilitarEdicionFecha ? (
                  <div
                    className="flex gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950 shadow-sm"
                    role="status"
                  >
                    <Lock
                      className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-800"
                      aria-hidden
                    />
                    <div>
                      <p className="font-semibold text-amber-950">
                        Fecha bloqueada (lectura del comprobante)
                      </p>
                      <p className="mt-0.5 text-xs leading-snug text-amber-900">
                        El valor mostrado sale solo de la imagen escaneada. No se reutiliza la fecha del
                        correo ni metadatos del archivo. Si la lectura fue incorrecta, use{' '}
                        <span className="font-medium">Corregir fecha</span> y deje la justificación
                        obligatoria.
                      </p>
                    </div>
                  </div>
                ) : null}
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setHabilitarEdicionFecha(v => {
                        const next = !v
                        if (!next && fechaDetectada) {
                          setFechaPago(fechaDetectada)
                          setJustificacionFecha('')
                        }
                        return next
                      })
                    }
                  >
                    {habilitarEdicionFecha
                      ? 'Usar fecha detectada'
                      : 'Corregir fecha (con justificación)'}
                  </Button>
                </div>
                {habilitarEdicionFecha && (
                  <div className="space-y-2">
                    <Label htmlFor="justificacion-fecha">
                      Justificación de corrección de fecha
                    </Label>
                    <Input
                      id="justificacion-fecha"
                      value={justificacionFecha}
                      onChange={e => setJustificacionFecha(e.target.value)}
                      placeholder="Ej. el comprobante tenía sello borroso y la fecha legible era del bloque inferior."
                      maxLength={300}
                    />
                  </div>
                )}
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="inst">Institución financiera</Label>
                <Input
                  id="inst"
                  value={institucion}
                  onChange={e => setInstitucion(e.target.value)}
                  maxLength={MAX_LENGTH_INSTITUCION}
                />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="nrop">Nº operación / referencia / serial</Label>
                <Input
                  id="nrop"
                  value={numeroOperacion}
                  onChange={e => setNumeroOperacion(e.target.value)}
                  maxLength={MAX_LENGTH_NUMERO_OPERACION}
                />
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
                Estado: <strong>en revisión manual</strong>. No hay recibo automático hasta aprobación.
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
