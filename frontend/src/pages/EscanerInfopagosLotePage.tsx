/**
 * Escáner Infopagos en lote: misma cédula deudor, hasta 15 comprobantes;
 * digitalización secuencial con Gemini (mismo endpoint que escáner unitario);
 * cada fila editable como el escáner simple; guardado con /infopagos/enviar-reporte.
 */
import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react'

import { Link } from 'react-router-dom'

import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  FileStack,
  Loader2,
  Pencil,
  Save,
  Trash2,
} from 'lucide-react'
import toast from 'react-hot-toast'

import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog'
import {
  eliminarPagoReportado,
  escanerInfopagosLoteDesdeDrive,
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
  TOKEN_SUFIJO_VISTO_ARCHIVO_RE,
} from '../utils/documentoSufijoVisto'

import {
  cancelDigitacionLote,
  getDigitacionLoteUiSnapshot,
  runDigitacionLoteEnSegundoPlano,
  setDigitacionLoteFilasSink,
  subscribeDigitacionLoteUi,
  takePendingDigitacionSession,
} from './escanerInfopagosLoteDigitacion'
import {
  filaVaciaDesdeArchivo,
  filaTrasExtraccion,
  fechaPagoEfectivaParaGuardar,
  hayDuplicadoFila,
  type FilaLote,
} from './escanerInfopagosLoteModel'
import {
  FUENTE_TASA_DEFAULT,
  normalizarFuenteTasaCambio,
  type FuenteTasaCambio,
} from '../constants/fuenteTasaCambio'
import { searchParamsRevisionPagosDesdeNumeroDocumento } from '../utils/linkRevisionPagosDesdeEscaner'

const MAX_ARCHIVOS = 15
const MAX_FILE_SIZE = 10 * 1024 * 1024
const DEFAULT_DRIVE_FOLDER =
  'https://drive.google.com/drive/folders/1gQCgiT2In8BiVMnOkKyzZezWH6M_hzxh?usp=drive_link'

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

type Fase = 'cedula' | 'archivos' | 'revision'

export default function EscanerInfopagosLotePage() {
  const honeypotRef = useRef<HTMLInputElement>(null)
  const tokensSufijoUsadosRef = useRef<Set<string>>(new Set())
  const guardarActivoRef = useRef<Set<string>>(new Set())

  const [fase, setFase] = useState<Fase>('cedula')
  const [cedulaRaw, setCedulaRaw] = useState('')
  const [nombreCliente, setNombreCliente] = useState('')
  const [validandoCedula, setValidandoCedula] = useState(false)
  const [fuenteTasa, setFuenteTasa] =
    useState<FuenteTasaCambio>(FUENTE_TASA_DEFAULT)

  const [archivos, setArchivos] = useState<File[]>([])
  const [driveFolder, setDriveFolder] = useState(DEFAULT_DRIVE_FOLDER)
  const [cargandoDrive, setCargandoDrive] = useState(false)
  const [filas, setFilas] = useState<FilaLote[]>([])
  const [editClientId, setEditClientId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<Partial<FilaLote> | null>(null)
  const filasRef = useRef<FilaLote[]>([])

  const digitacionUi = useSyncExternalStore(
    subscribeDigitacionLoteUi,
    getDigitacionLoteUiSnapshot,
    getDigitacionLoteUiSnapshot
  )

  useEffect(() => {
    filasRef.current = filas
  }, [filas])

  useEffect(() => {
    setDigitacionLoteFilasSink(next => {
      startTransition(() => {
        filasRef.current = next
        setFilas(next)
      })
    })
    return () => {
      setDigitacionLoteFilasSink(null)
    }
  }, [])

  useEffect(() => {
    const bundle = takePendingDigitacionSession()
    if (!bundle?.filas?.length) return
    setCedulaRaw(bundle.cedulaRaw)
    setNombreCliente(bundle.nombreCliente)
    filasRef.current = bundle.filas
    setFilas(bundle.filas)
    setFase('revision')
    toast.success(
      'Se restauró la sesión de lote con resultados de digitalización en segundo plano.'
    )
  }, [])

  const cedulaNormalizada = useMemo(
    () =>
      normalizarCedulaParaProcesar(extraerCaracteresCedulaPublica(cedulaRaw)),
    [cedulaRaw]
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
      setNombreCliente((res.nombre || '').trim())
      setFuenteTasa(normalizarFuenteTasaCambio(res.fuente_tasa_cambio_lista_bs))
      setFase('archivos')
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
  }, [cedulaNormalizada])

  const onPickArchivos = useCallback((list: FileList | null) => {
    if (!list?.length) return
    setArchivos(prev => {
      const base = [...prev]
      for (const file of Array.from(list)) {
        if (base.length >= MAX_ARCHIVOS) {
          toast.error(
            `Máximo ${String(MAX_ARCHIVOS)} archivos. Quite alguno para añadir más.`
          )
          break
        }
        const v = validarArchivo(file)
        if (!v.valido) {
          toast.error(`${file.name}: ${v.error || 'Archivo no válido.'}`)
          continue
        }
        base.push(file)
      }
      if (base.length > prev.length) {
        toast.success(
          base.length === 1
            ? '1 archivo en la lista.'
            : `${String(base.length)} archivos en la lista (máx. ${String(MAX_ARCHIVOS)}).`
        )
      }
      return base.slice(0, MAX_ARCHIVOS)
    })
  }, [])

  const quitarArchivo = useCallback((index: number) => {
    setArchivos(prev => prev.filter((_, i) => i !== index))
  }, [])

  const irARevision = useCallback(() => {
    if (!archivos.length) {
      toast.error('Seleccione al menos un comprobante.')
      return
    }
    tokensSufijoUsadosRef.current = new Set()
    const next = archivos.map(filaVaciaDesdeArchivo)
    filasRef.current = next
    setFilas(next)
    setFase('revision')
  }, [archivos])

  const fileDesdeBase64 = useCallback(
    (b64: string, fileName: string, mimeType: string): File => {
      const bin = atob(b64)
      const bytes = new Uint8Array(bin.length)
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
      return new File([bytes], fileName || 'comprobante', {
        type: mimeType || 'application/octet-stream',
      })
    },
    []
  )

  const handleCargarDesdeDrive = useCallback(async () => {
    if (!cedulaNormalizada.valido || !cedulaNormalizada.valorParaEnviar) {
      toast.error('Primero valide una cédula correcta.')
      return
    }
    const folder = driveFolder.trim()
    if (!folder) {
      toast.error('Indique la carpeta compartida de Drive.')
      return
    }
    setCargandoDrive(true)
    try {
      const tipo = cedulaNormalizada.valorParaEnviar.charAt(0).toUpperCase()
      const numero = cedulaNormalizada.valorParaEnviar
        .slice(1)
        .replace(/\D/g, '')
      const fd = new FormData()
      fd.append('tipo_cedula', tipo)
      fd.append('numero_cedula', numero)
      fd.append('drive_folder', folder)
      fd.append('max_archivos', String(MAX_ARCHIVOS))
      fd.append('fuente_tasa_cambio', fuenteTasa)
      const res = await escanerInfopagosLoteDesdeDrive(fd)
      if (!res.ok) {
        toast.error(res.mensaje || 'No se pudo cargar desde Drive.')
        return
      }
      if (!Array.isArray(res.items) || !res.items.length) {
        toast('No hay archivos en la carpeta compartida.')
        return
      }

      const archivosDrive: File[] = []
      const filasDrive: FilaLote[] = []
      for (const item of res.items.slice(0, MAX_ARCHIVOS)) {
        const b64 = (item.archivo_b64 || '').trim()
        if (!b64) continue
        const f = fileDesdeBase64(b64, item.nombre_archivo, item.mime_type)
        archivosDrive.push(f)
        const base = filaVaciaDesdeArchivo(f)
        if (item.ok && item.sugerencia) {
          filasDrive.push(filaTrasExtraccion(base, item))
        } else {
          filasDrive.push({
            ...base,
            extract: 'error',
            errorExtraccion:
              item.error || 'No se pudo digitalizar el comprobante.',
          })
        }
      }
      if (!filasDrive.length) {
        toast.error('No se pudieron cargar comprobantes válidos desde Drive.')
        return
      }
      setArchivos(archivosDrive)
      tokensSufijoUsadosRef.current = collectTokensSufijoVistoArchivoDesdeFilas(
        filasDrive.map(f => ({ numero_documento: f.numeroOperacion }))
      )
      filasRef.current = filasDrive
      setFilas(filasDrive)
      setFase('revision')
      toast.success(
        `Drive: ${String(res.total_leidos)} leído(s), ${String(res.total_eliminados)} eliminado(s) de la carpeta.`
      )
    } catch (e: unknown) {
      toast.error(
        e instanceof Error ? e.message : 'Error cargando imágenes desde Drive.'
      )
    } finally {
      setCargandoDrive(false)
    }
  }, [cedulaNormalizada, driveFolder, fileDesdeBase64, fuenteTasa])

  const handleDigitalizarTodos = useCallback(() => {
    if (!cedulaNormalizada.valido || !cedulaNormalizada.valorParaEnviar) {
      toast.error('Cédula inválida.')
      return
    }
    const tipo = cedulaNormalizada.valorParaEnviar.charAt(0).toUpperCase()
    const numero = cedulaNormalizada.valorParaEnviar.slice(1).replace(/\D/g, '')
    void runDigitacionLoteEnSegundoPlano(
      filasRef.current,
      tipo,
      numero,
      tokens => {
        for (const t of tokens) {
          tokensSufijoUsadosRef.current.add(t)
        }
      },
      { cedulaRaw, nombreCliente },
      fuenteTasa
    )
  }, [cedulaNormalizada, cedulaRaw, nombreCliente, fuenteTasa])

  const actualizarFila = useCallback(
    (clientId: string, patch: Partial<FilaLote>) => {
      setFilas(prev => {
        const next = prev.map(f =>
          f.clientId === clientId ? { ...f, ...patch } : f
        )
        filasRef.current = next
        return next
      })
    },
    []
  )

  const abrirEditarFila = useCallback((clientId: string) => {
    const fila = filasRef.current.find(f => f.clientId === clientId)
    if (!fila) return
    setEditClientId(clientId)
    setEditDraft({
      fechaPago: fila.fechaPago,
      confirmaFechaDetectada: fila.confirmaFechaDetectada,
      confirmaFechaManual: Boolean(fila.confirmaFechaManual),
      institucion: fila.institucion,
      otroInstitucion: fila.otroInstitucion,
      numeroOperacion: fila.numeroOperacion,
      moneda: fila.moneda,
      montoStr: fila.montoStr,
    })
  }, [])

  const cerrarEditorFila = useCallback(() => {
    setEditClientId(null)
    setEditDraft(null)
  }, [])

  const aplicarEdicionFila = useCallback(() => {
    if (!editClientId || !editDraft) return
    actualizarFila(editClientId, {
      fechaPago: String(editDraft.fechaPago || ''),
      confirmaFechaDetectada:
        editDraft.confirmaFechaDetectada === 'si' ||
        editDraft.confirmaFechaDetectada === 'no'
          ? editDraft.confirmaFechaDetectada
          : null,
      confirmaFechaManual: Boolean(editDraft.confirmaFechaManual),
      institucion: String(editDraft.institucion || ''),
      otroInstitucion: String(editDraft.otroInstitucion || ''),
      numeroOperacion: String(editDraft.numeroOperacion || ''),
      moneda: editDraft.moneda === 'BS' ? 'BS' : 'USD',
      montoStr: String(editDraft.montoStr || ''),
    })
    cerrarEditorFila()
  }, [actualizarFila, cerrarEditorFila, editClientId, editDraft])

  const handleAplicarSufijo = useCallback(
    (clientId: string, letter: 'A' | 'P') => {
      setFilas(prev => {
        const next = prev.map(f => {
          if (f.clientId !== clientId) return f
          const actual = f.numeroOperacion.trim()
          if (!actual) {
            toast.error('Primero escriba un número de operación.')
            return f
          }
          if (SUFIJO_VISTO_ARCHIVO_RE.test(actual)) {
            toast.error('Este número ya tiene sufijo admin (_A#### / _P####).')
            return f
          }
          const nuevo = aplicarSufijoVistoADocumento(
            actual,
            letter,
            tokensSufijoUsadosRef.current
          )
          if (!nuevo || nuevo === actual) {
            toast.error('No se pudo asignar sufijo.')
            return f
          }
          toast.success(`Sufijo _${letter}#### aplicado.`)
          return { ...f, numeroOperacion: nuevo }
        })
        filasRef.current = next
        return next
      })
    },
    []
  )

  const handleEliminarFila = useCallback(async (clientId: string) => {
    const fila = filasRef.current.find(f => f.clientId === clientId)
    if (!fila || fila.guardando) return
    if (fila.guardado && fila.pagoId != null) {
      if (
        !window.confirm(
          '¿Eliminar este pago reportado en Cobros? Esta acción no se puede deshacer.'
        )
      ) {
        return
      }
      try {
        const r = await eliminarPagoReportado(fila.pagoId)
        if (!r.ok) {
          toast.error(r.mensaje || 'No se pudo eliminar.')
          return
        }
        toast.success(r.mensaje || 'Eliminado.')
      } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : 'Error al eliminar.')
        return
      }
    }
    setFilas(prev => {
      const next = prev.filter(f => f.clientId !== clientId)
      filasRef.current = next
      return next
    })
  }, [])

  const handleGuardarFila = useCallback(
    async (clientId: string) => {
      if (guardarActivoRef.current.has(clientId)) return
      const fila = filasRef.current.find(f => f.clientId === clientId)
      if (!fila) return
      if (!cedulaNormalizada.valido || !cedulaNormalizada.valorParaEnviar) {
        toast.error('Cédula inválida.')
        return
      }
      const fechaPagoEnvio = fechaPagoEfectivaParaGuardar(fila)
      const vF = validarFechaPago(fechaPagoEnvio)
      if (!vF.valido) {
        toast.error(vF.error || 'Fecha inválida.')
        return
      }
      if (!fila.institucion.trim()) {
        toast.error('Indique la institución financiera.')
        return
      }
      if (fila.institucion.length > MAX_LENGTH_INSTITUCION) {
        toast.error('Institución demasiado larga.')
        return
      }
      if (!fila.numeroOperacion.trim()) {
        toast.error('Indique el número de operación o referencia.')
        return
      }
      if (fila.numeroOperacion.length > MAX_LENGTH_NUMERO_OPERACION) {
        toast.error('Número de operación demasiado largo.')
        return
      }
      const vM = validarMonto(fila.montoStr, fila.moneda)
      if (!vM.valido || vM.valor == null) {
        toast.error(vM.error || 'Monto inválido.')
        return
      }
      const vA = validarArchivo(fila.archivo)
      if (!vA.valido) {
        toast.error(vA.error || 'Archivo de comprobante inválido.')
        return
      }
      if (honeypotRef.current?.value?.trim()) {
        toast.error('No se pudo procesar el envío.')
        return
      }
      const tipo = cedulaNormalizada.valorParaEnviar.charAt(0).toUpperCase()
      const numero = cedulaNormalizada.valorParaEnviar
        .slice(1)
        .replace(/\D/g, '')
      const form = new FormData()
      form.append('tipo_cedula', tipo)
      form.append('numero_cedula', numero)
      form.append('contact_website', '')
      form.append('fecha_pago', fechaPagoEnvio)
      form.append('institucion_financiera', fila.institucion.trim())
      form.append('numero_operacion', fila.numeroOperacion.trim())
      form.append('monto', montoParaApi(vM.valor))
      form.append('moneda', fila.moneda)
      form.append('fuente_tasa_cambio', fuenteTasa)
      form.append('confirmacion_humana', 'true')
      form.append('comprobante', fila.archivo)
      guardarActivoRef.current.add(clientId)
      actualizarFila(clientId, { guardando: true, guardadoError: undefined })
      try {
        const res = await enviarReporteInfopagos(form)
        if (!res.ok) {
          toast.error(res.error || 'Error al guardar.')
          actualizarFila(clientId, {
            guardando: false,
            guardadoError: res.error || 'Error',
          })
          return
        }
        actualizarFila(clientId, {
          guardando: false,
          guardado: true,
          guardadoError: undefined,
          referencia: res.referencia_interna || '',
          enRevision:
            String(res.estado_reportado ?? '')
              .toLowerCase()
              .replace(/\s+/g, '_') === 'en_revision',
          reciboToken: res.recibo_descarga_token ?? null,
          pagoId: res.pago_id ?? null,
        })
        toast.success(res.mensaje || 'Pago registrado.')
      } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : 'Error al guardar.')
        actualizarFila(clientId, { guardando: false })
      } finally {
        guardarActivoRef.current.delete(clientId)
      }
    },
    [actualizarFila, cedulaNormalizada, fuenteTasa]
  )

  const handleDescargarRecibo = useCallback(
    async (clientId: string) => {
      const fila = filasRef.current.find(f => f.clientId === clientId)
      if (!fila?.reciboToken || fila.pagoId == null) return
      actualizarFila(clientId, { descargandoRecibo: true })
      try {
        const blob = await getReciboInfopagos(fila.reciboToken, fila.pagoId)
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `recibo_${fila.referencia || 'pago'}.pdf`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
      } catch (e: unknown) {
        toast.error(
          e instanceof Error ? e.message : 'No se pudo descargar el recibo.'
        )
      } finally {
        actualizarFila(clientId, { descargandoRecibo: false })
      }
    },
    [actualizarFila]
  )

  const reiniciar = useCallback(() => {
    cancelDigitacionLote()
    setFase('cedula')
    setCedulaRaw('')
    setNombreCliente('')
    setArchivos([])
    filasRef.current = []
    setFilas([])
    tokensSufijoUsadosRef.current = new Set()
    setFuenteTasa(FUENTE_TASA_DEFAULT)
  }, [])

  const volverArchivos = useCallback(() => {
    cancelDigitacionLote()
    setFase('archivos')
    filasRef.current = []
    setFilas([])
  }, [])

  const listoParaDigitalizar = filas.some(f => f.extract !== 'listo')
  const filaEditando = useMemo(
    () =>
      editClientId
        ? filas.find(f => f.clientId === editClientId) || null
        : null,
    [editClientId, filas]
  )

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-4 pb-16">
      <div className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-100 text-violet-800">
          <FileStack className="h-6 w-6" aria-hidden />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Escáner Infopagos (lote)
          </h1>
          <p className="text-sm text-slate-600">
            Una cédula deudor para todos los comprobantes. Hasta{' '}
            {String(MAX_ARCHIVOS)} archivos, digitalización y formulario iguales
            al escáner unitario; cada fila se guarda por separado (mismo proceso
            Infopagos / recibo).
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
            <CardTitle>
              1. Cédula del deudor (común a todos los pagos)
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="cedula-lote">Cédula (V/E/J + número)</Label>
              <Input
                id="cedula-lote"
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

      {fase === 'archivos' && (
        <Card>
          <CardHeader>
            <CardTitle>2. Comprobantes (máx. {String(MAX_ARCHIVOS)})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {nombreCliente ? (
              <p className="text-sm text-slate-700">
                Cliente: <span className="font-semibold">{nombreCliente}</span>
              </p>
            ) : null}
            <div className="space-y-2">
              <Label htmlFor="archivos-lote">
                Añadir comprobantes (PDF, imágenes; 10 MB c/u; hasta{' '}
                {String(MAX_ARCHIVOS)} en total)
              </Label>
              <Input
                id="archivos-lote"
                type="file"
                multiple
                accept=".pdf,.jpg,.jpeg,.png,.webp,.heic,.heif"
                onChange={e => {
                  onPickArchivos(e.target.files)
                  e.target.value = ''
                }}
              />
              <p className="text-xs text-slate-500">
                Cada lectura con IA puede tardar <strong>10-30 s</strong>; en
                lote se procesan en cola. Puede elegir archivos varias veces
                para ir sumando hasta el máximo.
              </p>
            </div>
            <div className="space-y-2 rounded-md border border-violet-200 bg-violet-50 p-3">
              <Label htmlFor="drive-folder-lote">
                Carpeta compartida de Drive (escáner lote)
              </Label>
              <Input
                id="drive-folder-lote"
                value={driveFolder}
                onChange={e => setDriveFolder(e.target.value)}
                placeholder="Pegue aquí el link de carpeta compartida o el folder ID"
              />
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleCargarDesdeDrive}
                  disabled={cargandoDrive}
                >
                  {cargandoDrive ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Cargando desde Drive…
                    </>
                  ) : (
                    'Cargar imágenes desde Drive (máx. 15)'
                  )}
                </Button>
                <p className="text-xs text-slate-600">
                  Toma hasta 15 archivos, los digitaliza y luego los elimina de
                  la carpeta origen.
                </p>
              </div>
            </div>
            {archivos.length > 0 && (
              <div className="flex justify-end">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setArchivos([])}
                >
                  Limpiar lista
                </Button>
              </div>
            )}
            {archivos.length > 0 && (
              <ul className="max-h-56 space-y-1 overflow-y-auto rounded-md border border-slate-200 bg-slate-50 p-2 text-sm">
                {archivos.map((f, i) => (
                  <li
                    key={`${f.name}-${String(i)}-${String(f.size)}`}
                    className="flex items-center justify-between gap-2 rounded px-2 py-1 hover:bg-white"
                  >
                    <span className="truncate font-mono text-xs">{f.name}</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => quitarArchivo(i)}
                    >
                      Quitar
                    </Button>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                type="button"
                onClick={() => setFase('cedula')}
              >
                Volver
              </Button>
              <Button
                type="button"
                onClick={irARevision}
                disabled={!archivos.length}
              >
                Siguiente: revisar y digitalizar
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {fase === 'revision' && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>3. Digitalizar y completar cada pago</CardTitle>
              {nombreCliente ? (
                <p className="text-sm text-slate-600">
                  Cliente:{' '}
                  <span className="font-semibold text-slate-900">
                    {nombreCliente}
                  </span>{' '}
                  - {String(filas.length)} comprobante(s).
                </p>
              ) : null}
            </CardHeader>
            <CardContent className="space-y-4">
              {digitacionUi.running ? (
                <p
                  className="rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm text-indigo-950"
                  role="status"
                >
                  Digitalización en curso en <strong>segundo plano</strong>:
                  puede navegar por el menú; el progreso se actualiza aquí y en
                  la notificación fija. Use «Cancelar» si debe detener la cola.
                </p>
              ) : null}
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  type="button"
                  onClick={volverArchivos}
                  disabled={digitacionUi.running}
                >
                  Volver a archivos
                </Button>
                <Button
                  type="button"
                  onClick={handleDigitalizarTodos}
                  disabled={digitacionUi.running || !listoParaDigitalizar}
                >
                  {digitacionUi.running ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Digitalizando
                      {digitacionUi.progressIndex != null &&
                      digitacionUi.total > 0
                        ? ` (${String(digitacionUi.progressIndex + 1)}/${String(digitacionUi.total)})`
                        : ''}
                      …
                    </>
                  ) : (
                    <>
                      <Brain className="mr-2 h-4 w-4" />
                      Digitalizar comprobantes pendientes
                    </>
                  )}
                </Button>
                {digitacionUi.running ? (
                  <Button
                    type="button"
                    variant="destructive"
                    onClick={() => cancelDigitacionLote()}
                  >
                    Cancelar digitalización
                  </Button>
                ) : null}
                <Button
                  variant="secondary"
                  type="button"
                  onClick={reiniciar}
                  disabled={digitacionUi.running}
                >
                  Reiniciar todo
                </Button>
              </div>
              <p className="text-xs text-slate-500">
                Solo se envían a Gemini las filas que aún no están en estado
                «listo». Puede editar manualmente tras digitalizar y guardar
                cada fila cuando corresponda.
              </p>
            </CardContent>
          </Card>

          <div className="space-y-4">
            {filas.map((fila, index) => {
              const dup = hayDuplicadoFila(fila)
              return (
                <Card key={fila.clientId} className="border-slate-200">
                  <CardHeader className="pb-2">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <CardTitle className="text-base">
                          {String(index + 1)}.{' '}
                          <span className="font-mono text-sm">
                            {fila.nombreArchivo}
                          </span>
                        </CardTitle>
                        <p className="mt-1 text-xs text-slate-500">
                          Extracción:{' '}
                          <span className="font-medium text-slate-700">
                            {fila.extract === 'pendiente' && 'Pendiente'}
                            {fila.extract === 'extrayendo' &&
                              'Leyendo con Gemini…'}
                            {fila.extract === 'listo' && 'Listo'}
                            {fila.extract === 'error' && 'Error'}
                          </span>
                          {fila.extract === 'error' && fila.errorExtraccion
                            ? ` - ${fila.errorExtraccion}`
                            : ''}
                          {fila.guardado ? (
                            <span className="ml-2 text-emerald-700">
                              · Guardado
                              {fila.referencia
                                ? ` · ref. ${fila.referencia}`
                                : ''}
                            </span>
                          ) : null}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => abrirEditarFila(fila.clientId)}
                        >
                          <Pencil className="mr-1 h-3.5 w-3.5" />
                          Editar
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          disabled={fila.guardando}
                          onClick={() => handleEliminarFila(fila.clientId)}
                        >
                          <Trash2 className="mr-1 h-3.5 w-3.5" />
                          Eliminar
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          disabled={fila.guardando || fila.guardado}
                          onClick={() => handleGuardarFila(fila.clientId)}
                        >
                          {fila.guardando ? (
                            <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Save className="mr-1 h-3.5 w-3.5" />
                          )}
                          Guardar
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {!fila.editando && fila.extract === 'listo' && (
                      <p className="text-sm text-slate-700">
                        {fila.fechaPago || '-'} · {fila.institucion || '-'} · Nº{' '}
                        {fila.numeroOperacion || '-'} · {fila.moneda}{' '}
                        {fila.montoStr || '-'}
                      </p>
                    )}

                    {fila.extract !== 'listo' && (
                      <div className="space-y-4">
                        {(fila.validacionCampos || fila.validacionReglas) && (
                          <div
                            className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
                            role="status"
                          >
                            <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0" />
                            <div>
                              {fila.validacionCampos ? (
                                <p>{fila.validacionCampos}</p>
                              ) : null}
                              {fila.validacionReglas ? (
                                <p>{fila.validacionReglas}</p>
                              ) : null}
                            </div>
                          </div>
                        )}
                        {fila.escanerColision?.prestamo_objetivo_id != null ? (
                          <p className="rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-medium text-indigo-950">
                            Pago hacia{' '}
                            <strong>
                              préstamo N°{' '}
                              {fila.escanerColision.prestamo_objetivo_id}
                            </strong>
                            .
                          </p>
                        ) : null}
                        {fila.cedulaPagadorImg ? (
                          <p className="text-xs text-slate-500">
                            <span className="font-medium text-slate-700">
                              Cédula en comprobante:
                            </span>{' '}
                            {fila.cedulaPagadorImg}
                          </p>
                        ) : null}

                        <div className="grid gap-4 sm:grid-cols-2">
                          <div className="space-y-2 sm:col-span-2">
                            <Label>Fecha de pago</Label>
                            {fila.fechaDetectada.trim() ? (
                              <p className="text-xs text-slate-600">
                                Detectada (IA):{' '}
                                <span className="font-mono font-semibold">
                                  {fila.fechaDetectada}
                                </span>
                              </p>
                            ) : (
                              <p className="text-xs text-amber-800">
                                Sin fecha clara en la imagen: se rellenó con la
                                fecha de hoy; ajústela si el comprobante
                                corresponde a otro día.
                              </p>
                            )}
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                              <div className="min-w-0 flex-1">
                                <Input
                                  type="date"
                                  value={fila.fechaPago}
                                  onChange={e =>
                                    actualizarFila(fila.clientId, {
                                      fechaPago: e.target.value,
                                    })
                                  }
                                />
                              </div>
                            </div>
                          </div>
                          <div className="space-y-2 sm:col-span-2">
                            <Label>Institución financiera</Label>
                            <select
                              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                              value={
                                INSTITUCIONES_FINANCIERAS.includes(
                                  fila.institucion as (typeof INSTITUCIONES_FINANCIERAS)[number]
                                )
                                  ? fila.institucion
                                  : 'Otros'
                              }
                              onChange={e => {
                                const v = e.target.value
                                if (v === 'Otros') {
                                  actualizarFila(fila.clientId, {
                                    institucion:
                                      fila.otroInstitucion.trim() || '',
                                  })
                                } else {
                                  actualizarFila(fila.clientId, {
                                    institucion: v,
                                    otroInstitucion: '',
                                  })
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
                              fila.institucion as (typeof INSTITUCIONES_FINANCIERAS)[number]
                            ) && (
                              <Input
                                value={fila.otroInstitucion}
                                onChange={e => {
                                  const val = e.target.value
                                  actualizarFila(fila.clientId, {
                                    otroInstitucion: val,
                                    institucion: val.trim(),
                                  })
                                }}
                                placeholder="Nombre del banco o entidad"
                                maxLength={MAX_LENGTH_INSTITUCION}
                              />
                            )}
                          </div>
                          <div className="space-y-2 sm:col-span-2">
                            <Label>Nº operación / referencia</Label>
                            <Input
                              value={fila.numeroOperacion}
                              onChange={e =>
                                actualizarFila(fila.clientId, {
                                  numeroOperacion: e.target.value,
                                })
                              }
                              maxLength={MAX_LENGTH_NUMERO_OPERACION}
                            />
                            {fila.escanerColision?.duplicado_en_pagos &&
                            typeof fila.escanerColision
                              .prestamo_existente_id === 'number' ? (
                              <p className="text-sm font-medium text-rose-800">
                                Número ya en cartera (préstamo N°{' '}
                                {fila.escanerColision.prestamo_existente_id}
                                ).
                              </p>
                            ) : dup ? (
                              <p className="text-sm font-medium text-rose-800">
                                Posible duplicado. Use sufijo si aplica.
                              </p>
                            ) : null}
                            {dup ? (
                              <div className="rounded-md border border-violet-200 bg-violet-50 px-3 py-2 text-sm text-violet-950">
                                <p className="font-medium">Sufijo admin</p>
                                <div className="mt-2 flex flex-wrap gap-2">
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="secondary"
                                    onClick={() =>
                                      handleAplicarSufijo(fila.clientId, 'A')
                                    }
                                  >
                                    _A…
                                  </Button>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="secondary"
                                    onClick={() =>
                                      handleAplicarSufijo(fila.clientId, 'P')
                                    }
                                  >
                                    _P…
                                  </Button>
                                </div>
                              </div>
                            ) : null}
                            {dup ||
                            (fila.escanerColision?.duplicado_en_pagos &&
                              typeof fila.escanerColision
                                .prestamo_existente_id === 'number') ? (
                              <p className="text-sm text-slate-700">
                                <Link
                                  className="font-medium text-indigo-700 underline underline-offset-2 hover:text-indigo-900"
                                  to={{
                                    pathname: '/pagos',
                                    search:
                                      searchParamsRevisionPagosDesdeNumeroDocumento(
                                        fila.numeroOperacion
                                      ),
                                  }}
                                >
                                  Revisar si está en la pestaña Revisión
                                </Link>
                              </p>
                            ) : null}
                          </div>
                          <div className="space-y-2">
                            <Label>Moneda</Label>
                            <select
                              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                              value={fila.moneda}
                              onChange={e =>
                                actualizarFila(fila.clientId, {
                                  moneda:
                                    e.target.value === 'BS' ? 'BS' : 'USD',
                                })
                              }
                            >
                              <option value="USD">USD / divisas</option>
                              <option value="BS">Bolívares (Bs.)</option>
                            </select>
                          </div>
                          <div className="space-y-2">
                            <Label>Monto</Label>
                            <Input
                              value={fila.montoStr}
                              onChange={e =>
                                actualizarFila(fila.clientId, {
                                  montoStr: e.target.value,
                                })
                              }
                              inputMode="decimal"
                              autoComplete="off"
                            />
                          </div>
                        </div>
                      </div>
                    )}

                    {fila.guardado && (
                      <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-3 text-sm text-emerald-950">
                        <div className="flex items-start gap-2">
                          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
                          <div>
                            <p>
                              Referencia:{' '}
                              <span className="font-mono font-semibold">
                                {fila.referencia || '-'}
                              </span>
                            </p>
                            {fila.enRevision ? (
                              <p className="mt-1">
                                Estado: <strong>en revisión manual</strong>. Sin
                                recibo hasta aprobación.
                              </p>
                            ) : null}
                            {fila.reciboToken && fila.pagoId != null ? (
                              <Button
                                type="button"
                                className="mt-2"
                                size="sm"
                                variant="secondary"
                                onClick={() =>
                                  handleDescargarRecibo(fila.clientId)
                                }
                                disabled={fila.descargandoRecibo}
                              >
                                {fila.descargandoRecibo
                                  ? 'Descargando…'
                                  : 'Descargar recibo PDF'}
                              </Button>
                            ) : null}
                            {fila.guardado &&
                            fila.enRevision &&
                            fila.pagoId == null ? (
                              <p className="mt-2 text-xs text-slate-600">
                                Para anular este borrador use Cobros → Pagos
                                reportados (no hay ID de recibo en este flujo).
                              </p>
                            ) : null}
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </>
      )}
      <Dialog
        open={Boolean(filaEditando)}
        onOpenChange={open => (open ? undefined : cerrarEditorFila())}
      >
        <DialogContent className="flex max-h-[90vh] w-full max-w-2xl flex-col gap-0 p-0 sm:max-w-2xl">
          <DialogHeader className="flex-shrink-0 border-b px-6 py-4">
            <DialogTitle className="text-xl font-bold">Editar Pago</DialogTitle>
          </DialogHeader>
          {filaEditando && editDraft ? (
            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Cédula Cliente *</Label>
                  <Input
                    value={cedulaNormalizada.valorParaEnviar || cedulaRaw}
                    readOnly
                  />
                  <p className="text-xs text-green-700">
                    1 préstamo en la lista
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Crédito al que aplica el pago *</Label>
                  <Input
                    readOnly
                    value={
                      filaEditando.escanerColision?.prestamo_objetivo_id != null
                        ? `Préstamo #${String(filaEditando.escanerColision.prestamo_objetivo_id)}`
                        : 'Pendiente de detección'
                    }
                  />
                  <p className="text-xs text-green-700">Cédulas coinciden</p>
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Fecha de Pago *</Label>
                  <Input
                    type="date"
                    value={String(editDraft.fechaPago || '')}
                    onChange={e =>
                      setEditDraft(prev =>
                        prev ? { ...prev, fechaPago: e.target.value } : prev
                      )
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>
                    Monto pagado ({editDraft.moneda === 'BS' ? 'BS' : 'USD'}) *
                  </Label>
                  <Input
                    value={String(editDraft.montoStr || '')}
                    onChange={e =>
                      setEditDraft(prev =>
                        prev ? { ...prev, montoStr: e.target.value } : prev
                      )
                    }
                  />
                </div>
              </div>
              <div className="rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
                <p className="font-medium">Cómo se aplicará el pago:</p>
                <ul className="ml-5 list-disc">
                  <li>
                    Se aplicará a las cuotas más antiguas primero (por fecha de
                    vencimiento).
                  </li>
                  <li>
                    Se distribuirá proporcionalmente entre capital e interés.
                  </li>
                </ul>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2 sm:col-span-2">
                  <Label>Banco</Label>
                  <select
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={
                      !String(editDraft.institucion || '').trim()
                        ? ''
                        : INSTITUCIONES_FINANCIERAS.includes(
                              String(
                                editDraft.institucion || ''
                              ) as (typeof INSTITUCIONES_FINANCIERAS)[number]
                            )
                          ? String(editDraft.institucion || '')
                          : 'Otros'
                    }
                    onChange={e =>
                      setEditDraft(prev =>
                        prev
                          ? {
                              ...prev,
                              institucion:
                                e.target.value === 'Otros'
                                  ? String(prev.otroInstitucion || '')
                                  : e.target.value,
                              otroInstitucion:
                                e.target.value === 'Otros'
                                  ? String(prev.otroInstitucion || '')
                                  : '',
                            }
                          : prev
                      )
                    }
                  >
                    <option value="">Sin especificar</option>
                    {INSTITUCIONES_FINANCIERAS.map(opt => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                    <option value="Otros">Otro</option>
                  </select>
                  {!INSTITUCIONES_FINANCIERAS.includes(
                    String(
                      editDraft.institucion || ''
                    ) as (typeof INSTITUCIONES_FINANCIERAS)[number]
                  ) ? (
                    <Input
                      placeholder="Nombre del banco o entidad"
                      maxLength={MAX_LENGTH_INSTITUCION}
                      value={String(editDraft.otroInstitucion || '')}
                      onChange={e =>
                        setEditDraft(prev =>
                          prev
                            ? {
                                ...prev,
                                otroInstitucion: e.target.value,
                                institucion: e.target.value.trim(),
                              }
                            : prev
                        )
                      }
                    />
                  ) : null}
                </div>
                <div className="space-y-2">
                  <Label>Número de Documento *</Label>
                  <Input
                    maxLength={MAX_LENGTH_NUMERO_OPERACION}
                    value={String(editDraft.numeroOperacion || '')}
                    onChange={e =>
                      setEditDraft(prev =>
                        prev
                          ? { ...prev, numeroOperacion: e.target.value }
                          : prev
                      )
                    }
                  />
                  <p className="text-xs text-slate-600">
                    Si detecta duplicado, use <strong>Visto _A…</strong> o{' '}
                    <strong>Visto _P…</strong>.
                  </p>
                  {filaEditando &&
                  (hayDuplicadoFila(filaEditando) ||
                    Boolean(filaEditando.escanerColision?.duplicado_en_pagos)) ? (
                    <p className="text-sm text-slate-700">
                      <Link
                        className="font-medium text-indigo-700 underline underline-offset-2 hover:text-indigo-900"
                        to={{
                          pathname: '/pagos',
                          search:
                            searchParamsRevisionPagosDesdeNumeroDocumento(
                              String(editDraft?.numeroOperacion || '')
                            ),
                        }}
                      >
                        Revisar si está en la pestaña Revisión
                      </Link>
                    </p>
                  ) : null}
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        const base = String(
                          editDraft.numeroOperacion || ''
                        ).trim()
                        if (!base) {
                          toast.error('Primero escriba un número de operación.')
                          return
                        }
                        if (SUFIJO_VISTO_ARCHIVO_RE.test(base)) {
                          toast.error('Este número ya tiene sufijo admin.')
                          return
                        }
                        const nuevo = aplicarSufijoVistoADocumento(
                          base,
                          'A',
                          tokensSufijoUsadosRef.current
                        )
                        setEditDraft(prev =>
                          prev ? { ...prev, numeroOperacion: nuevo } : prev
                        )
                      }}
                    >
                      Visto _A…
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        const base = String(
                          editDraft.numeroOperacion || ''
                        ).trim()
                        if (!base) {
                          toast.error('Primero escriba un número de operación.')
                          return
                        }
                        if (SUFIJO_VISTO_ARCHIVO_RE.test(base)) {
                          toast.error('Este número ya tiene sufijo admin.')
                          return
                        }
                        const nuevo = aplicarSufijoVistoADocumento(
                          base,
                          'P',
                          tokensSufijoUsadosRef.current
                        )
                        setEditDraft(prev =>
                          prev ? { ...prev, numeroOperacion: nuevo } : prev
                        )
                      }}
                    >
                      Visto _P…
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Código (solo lectura; lo asigna Visto)</Label>
                  <Input
                    readOnly
                    value={
                      String(editDraft.numeroOperacion || '')
                        .match(TOKEN_SUFIJO_VISTO_ARCHIVO_RE)?.[1]
                        ?.toUpperCase() || 'Pendiente: use Visto'
                    }
                  />
                  <p className="text-xs text-slate-600">
                    No se puede teclear aquí. El token (formato A#### / P####)
                    lo genera y guarda el sistema al pulsar Visto.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Moneda *</Label>
                  <select
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={editDraft.moneda === 'BS' ? 'BS' : 'USD'}
                    onChange={e =>
                      setEditDraft(prev =>
                        prev
                          ? {
                              ...prev,
                              moneda: e.target.value === 'BS' ? 'BS' : 'USD',
                            }
                          : prev
                      )
                    }
                  >
                    <option value="USD">USD / divisas</option>
                    <option value="BS">Bolívares (Bs.)</option>
                  </select>
                </div>
              </div>
            </div>
          ) : null}
          <DialogFooter className="flex-shrink-0 border-t px-6 py-4">
            <Button type="button" variant="outline" onClick={cerrarEditorFila}>
              Cancelar
            </Button>
            <Button type="button" onClick={aplicarEdicionFila}>
              Guardar cambios de edición
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
