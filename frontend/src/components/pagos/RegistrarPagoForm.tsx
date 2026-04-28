import { useState, useEffect, useMemo, useRef } from 'react'

import { motion, AnimatePresence } from 'framer-motion'

import {
  X,
  DollarSign,
  Calendar,
  CreditCard,
  FileText,
  Building2,
  Upload,
  Loader2,
  CheckCircle,
  AlertCircle,
  Info,
  Eye,
} from 'lucide-react'

import { toast } from 'sonner'

import { Button } from '../../components/ui/button'

import { Input } from '../../components/ui/input'

import { Textarea } from '../../components/ui/textarea'

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'

import {
  pagoService,
  type PagoCreate,
  type PagoInicialRegistrar,
} from '../../services/pagoService'

import { pagoConErrorService } from '../../services/pagoConErrorService'

import { usePrestamosByCedula, usePrestamo } from '../../hooks/usePrestamos'

import { usePermissions } from '../../hooks/usePermissions'

import { useDebounce } from '../../hooks/useDebounce'

import { SEGMENTO_INFOPAGOS } from '../../constants/rutasIngresoPago'

import {
  opcionesBancoConValorActual,
  SIN_ESPECIFICAR_VALUE,
} from '../../constants/institucionesBancariasPagos'

import { BASE_PATH } from '../../config/env'

import { getTasaPorFecha } from '../../services/tasaCambioService'

import {
  getErrorMessage,
  isAxiosError,
  getErrorDetail,
} from '../../types/errors'

import type { Prestamo } from '../../types'

import {
  claveDocumentoPagoListaNormalizada,
  normalizarNumeroDocumento,
  NUMERO_DOCUMENTO_MAX_LEN,
  pareceCedulaEnCampoDocumento,
} from '../../utils/pagoExcelValidation'

import {
  allocarTokenSufijoVistoArchivo,
  letterSufijoVistoDesdeMensajeDuplicado,
  mensajeEdicionManualSufijoVistoProhibida,
  SUFIJO_VISTO_ARCHIVO_RE,
  TOKEN_SUFIJO_VISTO_ARCHIVO_RE,
} from '../../utils/documentoSufijoVisto'

import { hoyYmdCaracas } from '../../utils/fechaZona'

import { splitNumeroDocumentoAlmacenado } from '../../utils/documentoPago'

import { apiClient } from '../../services/api'

import {
  abrirStaffComprobanteDesdeHref,
  fetchStaffComprobanteBlobWithDisplayMime,
  pathApiComprobanteImagenDesdeHref,
} from '../../utils/comprobanteImagenAuth'
import { escanerInfopagosExtraerComprobante } from '../../services/cobrosService'

import {
  formatMontoBsVe,
  parseMontoLatam,
  sanitizeMontoInputLatam,
} from '../../utils/montoLatam'

const DUPLICADO_DOCUMENTO_UI =
  'Este comprobante ya fue registrado. Verifique el numero_documento.'

const DUPLICADO_HUELLA_UI =
  'Pago duplicado detectado para este prestamo, fecha, monto y referencia.'

function pareceUrlImagenComprobanteExterna(u: string): boolean {
  if (!u) return false
  const low = u.toLowerCase()
  const path = u.split('?')[0].toLowerCase()
  if (/\.(jpe?g|png|gif|webp)$/i.test(path)) return true
  return low.includes('googleusercontent')
}

/**
 * Miniatura del comprobante ya guardado: interno vía sesión (blob); externo con <img> si parece imagen.
 */
function useVistaPreviaComprobanteGuardado(
  hrefInicial: string,
  activo: boolean
): { src: string | null; cargando: boolean; error: boolean } {
  const pathAuth = activo
    ? pathApiComprobanteImagenDesdeHref(hrefInicial)
    : null
  const requiereSesion = Boolean(pathAuth)
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!activo || !hrefInicial.trim()) {
      setBlobUrl(u => {
        if (u) URL.revokeObjectURL(u)
        return null
      })
      setCargando(false)
      setError(false)
      return
    }
    if (!requiereSesion || !pathAuth) {
      setBlobUrl(u => {
        if (u) URL.revokeObjectURL(u)
        return null
      })
      setCargando(false)
      setError(false)
      return
    }
    let cancelado = false
    ;(async () => {
      try {
        setCargando(true)
        setError(false)
        const blob = await apiClient.getBlob(pathAuth)
        if (cancelado) return
        const objectUrl = URL.createObjectURL(blob)
        setBlobUrl(prev => {
          if (prev) URL.revokeObjectURL(prev)
          return objectUrl
        })
      } catch {
        if (!cancelado) setError(true)
      } finally {
        if (!cancelado) setCargando(false)
      }
    })()
    return () => {
      cancelado = true
      setBlobUrl(u => {
        if (u) URL.revokeObjectURL(u)
        return null
      })
    }
  }, [activo, hrefInicial, pathAuth, requiereSesion])

  if (!activo || !hrefInicial.trim()) {
    return { src: null, cargando: false, error: false }
  }
  if (requiereSesion) {
    return { src: blobUrl, cargando, error }
  }
  if (pareceUrlImagenComprobanteExterna(hrefInicial)) {
    return { src: hrefInicial, cargando: false, error: false }
  }
  return { src: null, cargando: false, error: false }
}

/** Texto inicial del campo monto: vacío en alta (evita 0 + dígitos → 013). */
function montoInicialTextoDesdeNumero(
  m: number | undefined | null,
  editing: boolean
): string {
  const n = Number(m)
  if (!Number.isFinite(n) || n < 0) return ''
  if (n === 0) return editing ? '0' : ''
  return n.toFixed(2)
}

type PagoInicialMonto = PagoInicialRegistrar

function montoInicialNumericoDesdePago(pagoInicial?: PagoInicialMonto): number {
  if (!pagoInicial) return 0
  if (
    pagoInicial.moneda_registro === 'BS' &&
    pagoInicial.monto_bs_original != null
  ) {
    const n = Number(pagoInicial.monto_bs_original)
    if (Number.isFinite(n) && n >= 0) return n
  }
  const m = Number(pagoInicial.monto_pagado)
  return Number.isFinite(m) && m >= 0 ? m : 0
}

function montoInicialTextoDesdePago(
  pagoInicial: PagoInicialMonto | undefined,
  editing: boolean
): string {
  if (!pagoInicial) return ''
  if (pagoInicial.moneda_registro === 'BS') {
    const n = montoInicialNumericoDesdePago(pagoInicial)
    if (!Number.isFinite(n) || n < 0) return ''
    if (n === 0) return editing ? formatMontoBsVe(0) : ''
    return formatMontoBsVe(n)
  }
  return montoInicialTextoDesdeNumero(pagoInicial.monto_pagado, editing)
}

function resolverLinkComprobanteInicial(
  pagoInicial?: PagoInicialRegistrar
): string {
  const link = (pagoInicial?.link_comprobante || '').trim()
  if (link) return link
  const rutaDocumento = (pagoInicial?.documento_ruta || '').trim()
  return rutaDocumento
}

function descomponerCedula(
  cedulaRaw: string
): { tipo: string; numero: string } | null {
  const clean = String(cedulaRaw || '')
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')
  if (!clean) return null
  const m = /^([VEJPG])?(\d{5,12})$/.exec(clean)
  if (!m) return null
  return { tipo: m[1] || 'V', numero: m[2] }
}

interface RegistrarPagoFormProps {
  onClose: () => void

  onSuccess: () => void

  pagoInicial?: PagoInicialRegistrar

  pagoId?: number // Si está presente, es modo edición

  /** Si true, muestra "Guardar y Procesar": actualiza BD y aplica reglas (conciliación + aplicar a cuotas) */

  modoGuardarYProcesar?: boolean

  /** Si true, edición usa pagos_con_errores */

  esPagoConError?: boolean

  /**
   * Si true, exige URL de comprobante aunque la fecha no sea «hoy» en Caracas.
   * Por defecto el enlace es opcional salvo la regla de fecha (hoy Caracas) y validación de URL si se completa.
   */
  requiereLinkComprobante?: boolean

  /**
   * Revisión manual: ID del préstamo que se está editando. Garantiza que ese crédito
   * (p. ej. LIQUIDADO) figure en el selector y pase validación aunque la lista por cédula falle o venga incompleta.
   */
  prestamoContextoRevisionManualId?: number

  /**
   * Si true, muestra el campo «Código» (mismo comprobante + códigos distintos).
   * Solo revisión manual debe activarlo; el modal del listado general de pagos lo deja en false.
   */
  mostrarCampoCodigoDocumento?: boolean

  /**
   * Revisión manual: claves `claveDocumentoPagoListaNormalizada` ya presentes en la tabla de pagos
   * de la página actual (excluir la fila en edición en el padre). Evita guardar duplicado obvio antes del POST.
   */
  claveDocumentoPagosTablaRevision?: ReadonlySet<string>

  /** Si true, al editar no envía cambios de comprobante/código (regla backend para conciliados/pagados). */
  bloquearCambioComprobanteCodigo?: boolean
}

export function RegistrarPagoForm({
  onClose,
  onSuccess,
  pagoInicial,
  pagoId,
  modoGuardarYProcesar,
  esPagoConError,
  requiereLinkComprobante,
  prestamoContextoRevisionManualId,
  mostrarCampoCodigoDocumento = false,
  claveDocumentoPagosTablaRevision,
  bloquearCambioComprobanteCodigo = false,
}: RegistrarPagoFormProps) {
  const isEditing = !!pagoId

  const { revisionManualFullEdit } = usePermissions()

  const codigoDocumentoInputRef = useRef<HTMLInputElement>(null)

  const comprobanteFileInputRef = useRef<HTMLInputElement>(null)

  const linkComprobanteInicialRef = useRef(resolverLinkComprobanteInicial(pagoInicial))

  const [archivoComprobante, setArchivoComprobante] = useState<File | null>(
    null
  )

  const [objUrlVistaArchivoNuevo, setObjUrlVistaArchivoNuevo] = useState<
    string | null
  >(null)

  useEffect(() => {
    if (!archivoComprobante) {
      setObjUrlVistaArchivoNuevo(null)
      return
    }
    const u = URL.createObjectURL(archivoComprobante)
    setObjUrlVistaArchivoNuevo(u)
    return () => {
      URL.revokeObjectURL(u)
    }
  }, [archivoComprobante])

  const [vistoRevisionManualOpen, setVistoRevisionManualOpen] = useState(false)
  const [isRescanning, setIsRescanning] = useState(false)

  const [formData, setFormData] = useState<PagoCreate>({
    cedula_cliente: pagoInicial?.cedula_cliente || '',

    prestamo_id: pagoInicial?.prestamo_id || null,

    fecha_pago:
      pagoInicial?.fecha_pago || new Date().toISOString().split('T')[0],

    monto_pagado: montoInicialNumericoDesdePago(pagoInicial),

    numero_documento: pagoInicial?.numero_documento || '',

    institucion_bancaria: pagoInicial?.institucion_bancaria || null,

    notas: pagoInicial?.notas || null,

    link_comprobante: resolverLinkComprobanteInicial(pagoInicial) || null,

    codigo_documento:
      (pagoInicial as { codigo_documento?: string | null })?.codigo_documento ??
      null,
  })

  const [montoStr, setMontoStr] = useState(() =>
    montoInicialTextoDesdePago(pagoInicial, isEditing)
  )

  useEffect(() => {
    linkComprobanteInicialRef.current = resolverLinkComprobanteInicial(pagoInicial)
  }, [pagoInicial?.link_comprobante, pagoInicial?.documento_ruta])

  const [isSubmitting, setIsSubmitting] = useState(false)

  const [errors, setErrors] = useState<Record<string, string>>({})

  const [monedaRegistro, setMonedaRegistro] = useState<'USD' | 'BS'>(() =>
    (pagoInicial as { moneda_registro?: string } | undefined)
      ?.moneda_registro === 'BS'
      ? 'BS'
      : 'USD'
  )

  const [puedePagarBs, setPuedePagarBs] = useState<boolean | null>(null)

  const [consultandoBs, setConsultandoBs] = useState(false)

  const [tasaBd, setTasaBd] = useState<number | null>(null)

  const [tasaBdLoading, setTasaBdLoading] = useState(false)

  const [tasaManual, setTasaManual] = useState('')

  // Debounce de la cédula para buscar préstamos

  const debouncedCedula = useDebounce(formData.cedula_cliente, 500)

  // Buscar préstamos cuando cambia la cédula (con al menos 2 caracteres)

  const { data: prestamos, isLoading: isLoadingPrestamos } =
    usePrestamosByCedula(debouncedCedula.length >= 2 ? debouncedCedula : '')

  // Información del préstamo seleccionado (el crédito solo puede ser uno de la lista por cédula)

  const { data: prestamoSeleccionado } = usePrestamo(formData.prestamo_id || 0)

  const pidRevisionCtx =
    prestamoContextoRevisionManualId && prestamoContextoRevisionManualId > 0
      ? prestamoContextoRevisionManualId
      : 0

  const { data: prestamoContextoRevisionManual } = usePrestamo(pidRevisionCtx)

  const linkComprobanteParaVista = (formData.link_comprobante || '').trim()

  const vistaPreviaComprobanteActiva =
    isEditing && Boolean(linkComprobanteParaVista) && !archivoComprobante

  const vistaPreviaComprobante = useVistaPreviaComprobanteGuardado(
    linkComprobanteParaVista,
    vistaPreviaComprobanteActiva
  )

  const handleReescanearDesdeComprobanteActual = async () => {
    if (
      !window.confirm(
        'Escanear reemplazara los campos actuales (fecha, banco, numero, monto y moneda). Desea continuar?'
      )
    ) {
      return
    }

    const cedulaPartes = descomponerCedula(formData.cedula_cliente)
    if (!cedulaPartes) {
      toast.error('Ingrese una cedula valida antes de escanear.')
      return
    }

    setIsRescanning(true)
    try {
      let fileToScan: File | null = archivoComprobante
      if (!fileToScan) {
        const href = (linkComprobanteParaVista || '').trim()
        if (!href) {
          toast.error('No hay comprobante disponible para escanear.')
          return
        }
        const { blob, contentType } = await fetchStaffComprobanteBlobWithDisplayMime(
          href
        )
        const ext =
          contentType === 'image/png'
            ? 'png'
            : contentType === 'image/gif'
              ? 'gif'
              : contentType === 'image/webp'
                ? 'webp'
                : contentType === 'application/pdf'
                  ? 'pdf'
                  : 'jpg'
        fileToScan = new File([blob], `comprobante.${ext}`, {
          type: contentType || 'application/octet-stream',
        })
      }

      const fd = new FormData()
      fd.append('tipo_cedula', cedulaPartes.tipo)
      fd.append('numero_cedula', cedulaPartes.numero)
      fd.append('comprobante', fileToScan)
      fd.append('fuente_tasa_cambio', 'euro')
      const institucionPlantilla = (formData.institucion_bancaria || '').trim()
      if (institucionPlantilla) {
        fd.append('institucion_plantilla', institucionPlantilla)
      }

      const res = await escanerInfopagosExtraerComprobante(fd)
      if (!res.ok || !res.sugerencia) {
        toast.error(
          res.error || 'No se pudo digitalizar el comprobante en este momento.'
        )
        return
      }

      const s = res.sugerencia
      const nextMoneda = s.moneda === 'BS' ? 'BS' : 'USD'
      const nextMonto =
        s.monto != null && Number.isFinite(Number(s.monto))
          ? Number(s.monto)
          : formData.monto_pagado
      setMonedaRegistro(nextMoneda)
      setMontoStr(
        nextMoneda === 'BS' ? formatMontoBsVe(nextMonto) : nextMonto.toFixed(2)
      )
      setFormData(prev => ({
        ...prev,
        fecha_pago: (s.fecha_pago || '').trim() || prev.fecha_pago,
        institucion_bancaria:
          (s.institucion_financiera || '').trim() || prev.institucion_bancaria,
        numero_documento: (s.numero_operacion || '').trim() || prev.numero_documento,
        monto_pagado: nextMonto,
      }))
      setErrors(prev => {
        const next = { ...prev }
        delete next.fecha_pago
        delete next.institucion_bancaria
        delete next.numero_documento
        delete next.monto_pagado
        delete next.general
        return next
      })
      toast.success('Campos actualizados desde el comprobante.')
    } catch {
      toast.error('No se pudo re-escanear el comprobante.')
    } finally {
      setIsRescanning(false)
    }
  }

  /** Incluye el préstamo cargado por ID si la lista por cédula aún no lo trae (evita placeholder "Seleccione el crédito" con valor 478). */
  const opcionesBancoSelect = useMemo(
    () => opcionesBancoConValorActual(formData.institucion_bancaria),
    [formData.institucion_bancaria]
  )

  const bancoSelectValue = (() => {
    const t = (formData.institucion_bancaria || '').trim()
    if (!t) return SIN_ESPECIFICAR_VALUE
    return t
  })()

  const prestamosParaSelect = useMemo((): Prestamo[] => {
    const list = Array.isArray(prestamos) ? [...prestamos] : []

    const mergeIfMissing = (base: Prestamo[], p?: Prestamo): Prestamo[] => {
      if (!p?.id) return base
      if (base.some(x => x.id === p.id)) return base
      return [p, ...base]
    }

    let out = list
    const pCtx = prestamoContextoRevisionManual as Prestamo | undefined
    if (pidRevisionCtx > 0 && pCtx?.id === pidRevisionCtx) {
      out = mergeIfMissing(out, pCtx)
    }

    const pid = formData.prestamo_id
    if (!pid || out.some(p => p.id === pid)) {
      return out
    }
    const psel = prestamoSeleccionado as Prestamo | undefined
    if (psel && psel.id === pid) {
      return mergeIfMissing(out, psel)
    }
    return out
  }, [
    prestamos,
    formData.prestamo_id,
    prestamoSeleccionado,
    pidRevisionCtx,
    prestamoContextoRevisionManual,
  ])

  useEffect(() => {
    let cancelled = false

    const c = debouncedCedula.trim()

    if (c.length < 5) {
      setPuedePagarBs(null)

      return
    }

    setConsultandoBs(true)

    pagoService

      .consultarCedulaReportarBs(c)

      .then(res => {
        if (cancelled) return

        setPuedePagarBs(res.en_lista)

        if (!res.en_lista) setMonedaRegistro('USD')
      })

      .catch(() => {
        if (!cancelled) setPuedePagarBs(false)
      })

      .finally(() => {
        if (!cancelled) setConsultandoBs(false)
      })

    return () => {
      cancelled = true
    }
  }, [debouncedCedula])

  useEffect(() => {
    if (!isEditing || !pagoId) return

    const existingCode = (pagoInicial as { codigo_documento?: string | null })
      ?.codigo_documento

    if (existingCode) return

    const raw = (pagoInicial?.numero_documento || '').trim()

    if (!raw) return

    const { base, codigo } = splitNumeroDocumentoAlmacenado(raw)

    if (!codigo) return

    setFormData(prev => ({
      ...prev,

      numero_documento: base,

      codigo_documento: codigo,
    }))
  }, [isEditing, pagoId, pagoInicial])

  useEffect(() => {
    if (monedaRegistro !== 'BS') {
      setTasaBd(null)

      return
    }

    const fp = formData.fecha_pago

    if (!fp) {
      setTasaBd(null)

      return
    }

    setTasaBdLoading(true)

    getTasaPorFecha(fp)
      .then(r => setTasaBd(r?.tasa_oficial ?? null))

      .catch(() => setTasaBd(null))

      .finally(() => setTasaBdLoading(false))
  }, [formData.fecha_pago, monedaRegistro])

  // Auto-seleccionar préstamo si hay solo uno en la lista efectiva (API + contexto revisión manual).

  useEffect(() => {
    if (isLoadingPrestamos) return

    const opts = prestamosParaSelect

    if (opts.length === 1 && !formData.prestamo_id) {
      setFormData(prev => ({ ...prev, prestamo_id: opts[0].id }))
      return
    }

    if (
      opts.length === 0 &&
      Array.isArray(prestamos) &&
      prestamos.length === 0
    ) {
      // No borrar crédito al editar o si venía préstamo en pagoInicial (lista puede cargar tarde o Radix sin ítem).
      const preservarCredito =
        isEditing ||
        (pagoInicial?.prestamo_id != null &&
          Number(pagoInicial.prestamo_id) > 0)
      if (preservarCredito) {
        return
      }
      setFormData(prev => ({ ...prev, prestamo_id: null }))
    }
  }, [
    isLoadingPrestamos,
    prestamosParaSelect,
    prestamos,
    isEditing,
    pagoInicial?.prestamo_id,
    formData.prestamo_id,
  ])

  /** Validación + POST/PUT usando el snapshot `fd` (p. ej. Visto rellena código y guarda sin esperar re-render). */
  const submitPago = async (fd: PagoCreate) => {
    const newErrors: Record<string, string> = {}

    const hoyCaracas = hoyYmdCaracas()

    if (!fd.cedula_cliente) {
      newErrors.cedula_cliente = 'Cédula requerida'
    }

    if (prestamosParaSelect.length > 0 && !fd.prestamo_id) {
      newErrors.prestamo_id =
        prestamosParaSelect.length > 1
          ? 'Debe escoger un crédito de la lista'
          : 'Debe seleccionar el crédito'
    }

    const permiteCreditoRevisionManual =
      !!prestamoContextoRevisionManualId &&
      fd.prestamo_id === prestamoContextoRevisionManualId

    if (
      fd.prestamo_id &&
      prestamosParaSelect.length > 0 &&
      !prestamosParaSelect.some(p => p.id === fd.prestamo_id) &&
      !permiteCreditoRevisionManual
    ) {
      newErrors.prestamo_id =
        'El crédito debe ser uno de la lista para esta cédula'
    }

    const prestamoParaCedula: Prestamo | undefined =
      permiteCreditoRevisionManual &&
      (prestamoContextoRevisionManual as Prestamo | undefined)?.id ===
        fd.prestamo_id
        ? (prestamoContextoRevisionManual as Prestamo)
        : (prestamoSeleccionado as Prestamo | undefined)

    if (fd.prestamo_id && prestamoParaCedula) {
      if (fd.cedula_cliente !== prestamoParaCedula.cedula) {
        newErrors.cedula_cliente = `La cédula del pago (${fd.cedula_cliente}) no coincide con la cédula del préstamo (${prestamoParaCedula.cedula}). El pago solo se aplicará si las cédulas coinciden.`

        newErrors.prestamo_id =
          'La cédula del pago debe coincidir con la cédula del préstamo seleccionado'
      }
    }

    if (!fd.monto_pagado || fd.monto_pagado <= 0) {
      newErrors.monto_pagado = 'Monto inválido. Debe ser mayor a cero'
    } else if (fd.monto_pagado > (monedaRegistro === 'BS' ? 1e15 : 1_000_000)) {
      newErrors.monto_pagado = 'Monto muy alto. Por favor verifique el valor'
    }

    const numeroDocumentoNormalizado = normalizarNumeroDocumento(
      fd.numero_documento
    )

    if (!numeroDocumentoNormalizado) {
      newErrors.numero_documento = 'Número de documento requerido'
    } else if (pareceCedulaEnCampoDocumento(fd.numero_documento)) {
      newErrors.numero_documento =
        'No ingrese la cédula aquí. Use el campo de cédula del cliente; en documento va la referencia o comprobante del banco (regla alineada con carga masiva).'
    } else if (numeroDocumentoNormalizado.length > NUMERO_DOCUMENTO_MAX_LEN) {
      newErrors.numero_documento = `El número de documento no puede superar ${NUMERO_DOCUMENTO_MAX_LEN} caracteres.`
    } else if (
      claveDocumentoPagosTablaRevision &&
      claveDocumentoPagosTablaRevision.size > 0
    ) {
      const claveNueva = claveDocumentoPagoListaNormalizada(
        numeroDocumentoNormalizado,
        fd.codigo_documento ?? null
      )
      if (claveNueva && claveDocumentoPagosTablaRevision.has(claveNueva)) {
        newErrors.numero_documento =
          'Ya hay un pago con la misma clave comprobante + código entre los listados en esta página. Use «Código» para distinguir o corrija el duplicado.'
      }
    }

    if (!fd.fecha_pago) {
      newErrors.fecha_pago = 'Fecha de pago requerida'
    } else if (fd.fecha_pago > hoyCaracas) {
      newErrors.fecha_pago =
        'La fecha de pago no puede ser posterior a hoy (America/Caracas).'
    }

    const linkComprobanteInicial = (
      linkComprobanteInicialRef.current || ''
    ).trim()

    const linkComprobanteTrim = (fd.link_comprobante || '').trim()

    if (!archivoComprobante) {
      if (!isEditing) {
        newErrors.link_comprobante =
          'Debe adjuntar una imagen del comprobante (JPEG, PNG, WebP o GIF).'
      } else if (!linkComprobanteTrim && !linkComprobanteInicial) {
        newErrors.link_comprobante =
          'Debe adjuntar una imagen del comprobante (JPEG, PNG, WebP o GIF).'
      }
    }

    if (monedaRegistro === 'BS') {
      const tm = parseFloat(String(tasaManual).replace(',', '.'))

      if (!tasaBd && (!Number.isFinite(tm) || tm <= 0)) {
        newErrors.general =
          'Bolivares: no hay tasa en BD para esa fecha; ingrese tasa manual (Bs por 1 USD).'
      }
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)

      return
    }

    setIsSubmitting(true)

    try {
      let linkFinal = linkComprobanteTrim || linkComprobanteInicial

      if (archivoComprobante) {
        const up = await pagoService.uploadComprobanteImagen(archivoComprobante)

        linkFinal = (up.url || '').trim()
      }

      if (!linkFinal) {
        setErrors({
          link_comprobante:
            'Debe adjuntar una imagen del comprobante (JPEG, PNG, WebP o GIF).',
        })

        setIsSubmitting(false)

        return
      }

      try {
        const u = new URL(linkFinal)

        if (!['http:', 'https:'].includes(u.protocol)) {
          throw new Error('protocolo')
        }
      } catch {
        setErrors({
          link_comprobante: 'No se obtuvo una URL valida para el comprobante.',
        })

        setIsSubmitting(false)

        return
      }

      const codigoTrim = String(fd.codigo_documento ?? '').trim()

      const datosEnvio = {
        ...fd,

        numero_documento: numeroDocumentoNormalizado,

        codigo_documento: codigoTrim || null,

        moneda_registro: monedaRegistro,

        link_comprobante: linkFinal,
      } as PagoCreate & { tasa_cambio_manual?: number; conciliado?: boolean }

      if (isEditing && bloquearCambioComprobanteCodigo) {
        delete datosEnvio.link_comprobante
        delete datosEnvio.codigo_documento
      }

      if (monedaRegistro === 'BS' && !tasaBd) {
        const tm = parseFloat(String(tasaManual).replace(',', '.'))

        if (Number.isFinite(tm) && tm > 0) datosEnvio.tasa_cambio_manual = tm
      }

      if (fd.prestamo_id && fd.monto_pagado > 0) {
        datosEnvio.conciliado = true
      }

      if (isEditing && pagoId) {
        if (esPagoConError) {
          await pagoConErrorService.update(pagoId, datosEnvio)
        } else {
          await pagoService.updatePago(pagoId, datosEnvio)
        }
      } else {
        await pagoService.createPago(datosEnvio)
      }

      onSuccess()
    } catch (error: unknown) {
      console.error(
        `Error ${isEditing ? 'actualizando' : 'registrando'} pago:`,
        error
      )

      let errorMessage = getErrorMessage(error)

      if (isAxiosError(error)) {
        const status = error.response?.status
        const detail = getErrorDetail(error)
        const detailLower = (detail || '').toLowerCase()

        if (status === 409 && detailLower.includes('huella funcional')) {
          errorMessage = DUPLICADO_HUELLA_UI
        } else if (
          status === 409 &&
          (detailLower.includes('comprobante') ||
            detailLower.includes('codigo en pagos conciliados') ||
            detailLower.includes('pagos conciliados o pagados'))
        ) {
          errorMessage =
            'Este pago ya está conciliado/pagado. No se permite cambiar comprobante ni código; ajuste otros campos permitidos.'
        } else if (
          status === 409 &&
          (detailLower.includes('numero_documento') ||
            detailLower.includes('documento'))
        ) {
          errorMessage = DUPLICADO_DOCUMENTO_UI
        } else if (detail) {
          errorMessage = detail
        }
      }

      setErrors({
        general:
          errorMessage ||
          `Error al ${isEditing ? 'actualizar' : 'registrar'} el pago`,
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    await submitPago(formData)
  }

  /** Visto (revisión manual): desambigua con código A####/P#### en el campo Código y guarda (BD almacena comprobante + §CD: + código). */
  const handleVistoRellenarCodigoYGuardar = async () => {
    if (
      isSubmitting ||
      !mostrarCampoCodigoDocumento ||
      !revisionManualFullEdit
    ) {
      return
    }

    const msg = [errors.general, errors.numero_documento]
      .filter(Boolean)
      .join(' ')
    const letter = letterSufijoVistoDesdeMensajeDuplicado(msg)
    const usados = new Set<string>()

    const codExistente = String(formData.codigo_documento ?? '').trim()
    const mc = codExistente.match(/^([AP]\d{4})$/i)
    if (mc) usados.add(mc[1].toUpperCase())

    let numeroDoc = String(formData.numero_documento ?? '').trim()
    if (SUFIJO_VISTO_ARCHIVO_RE.test(numeroDoc)) {
      const mDoc = numeroDoc.match(TOKEN_SUFIJO_VISTO_ARCHIVO_RE)
      if (mDoc) usados.add(mDoc[1].toUpperCase())
      numeroDoc = numeroDoc.replace(SUFIJO_VISTO_ARCHIVO_RE, '').trim()
    }

    const token = allocarTokenSufijoVistoArchivo(letter, usados)
    const fd: PagoCreate = {
      ...formData,
      numero_documento: numeroDoc,
      codigo_documento: token,
    }

    setFormData(fd)

    setErrors(prev => {
      const next = { ...prev }
      delete next.numero_documento
      delete next.codigo_documento
      const g = next.general
      if (
        g === DUPLICADO_DOCUMENTO_UI ||
        (g && g.toLowerCase().includes('documento'))
      ) {
        delete next.general
      }
      return next
    })

    await submitPago(fd)
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95 }}
          className={`flex max-h-[90vh] w-full flex-col rounded-lg bg-white shadow-xl ${
            isEditing
              ? 'max-w-[min(72rem,calc(100vw-1.5rem))]'
              : 'max-w-2xl'
          }`}
        >
          {/* Header fijo (fuera del scroll, evita efecto scroll-linked en Firefox) */}

          <div className="flex flex-shrink-0 items-center justify-between rounded-t-lg border-b bg-white p-4">
            <h2 className="text-xl font-bold">
              {isEditing ? 'Editar Pago' : 'Registrar Pago'}
            </h2>

            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Form con scroll */}

          <form
            onSubmit={handleSubmit}
            className="flex min-h-0 flex-1 flex-col overflow-hidden"
          >
            <div
              className={
                isEditing
                  ? 'flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row'
                  : 'min-h-0 flex-1 overflow-y-auto'
              }
            >
              <div
                className={
                  isEditing
                    ? 'min-h-0 flex-1 space-y-6 overflow-y-auto border-slate-200 p-6 lg:w-1/2 lg:max-w-[50%] lg:border-r'
                    : 'space-y-6 p-6'
                }
              >
            {/* Error general */}

            {!isEditing && (
              <div className="rounded border border-amber-100 bg-amber-50/80 px-3 py-2 text-xs text-amber-950">
                <p>
                  <strong>Comprobante obligatorio:</strong> suba una foto del
                  comprobante (hasta 10 MB). Para flujos con moneda Bs., recibo
                  PDF de tasa u otros casos puede usar{' '}
                  <a
                    href={`${BASE_PATH}/${SEGMENTO_INFOPAGOS}`.replace(
                      /\/+/g,
                      '/'
                    )}
                    target="_blank"
                    rel="noreferrer"
                    className="font-semibold text-amber-900 underline"
                  >
                    Infopagos
                  </a>
                  . Este formulario registra o edita pagos en la tabla interna
                  (conciliación).
                </p>
              </div>
            )}

            {requiereLinkComprobante && (
              <div className="rounded border border-sky-100 bg-sky-50/90 px-3 py-2 text-xs text-sky-950">
                <p>
                  <strong>Revisión manual:</strong> el comprobante es una imagen
                  obligatoria. No puede repetirse la misma combinación
                  comprobante + código; use el campo «Código» para distinguir
                  pagos con el mismo texto de referencia bancaria. La huella
                  funcional sigue evitando el mismo pago (crédito, fecha, monto
                  y ref. normalizada).
                </p>
              </div>
            )}

            {errors.general && (
              <div className="rounded border border-red-200 bg-red-50 px-4 py-3 text-red-700">
                {errors.general}
              </div>
            )}

            {isEditing && bloquearCambioComprobanteCodigo ? (
              <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                Este pago ya está conciliado o pagado. El comprobante y el código
                se muestran solo para consulta y no se pueden modificar.
              </div>
            ) : null}

            {/* Cédula e ID Préstamo */}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Cédula Cliente <span className="text-red-500">*</span>
                </label>

                <div className="relative">
                  <CreditCard className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                  <Input
                    type="text"
                    value={formData.cedula_cliente}
                    onChange={e => {
                      setFormData({
                        ...formData,
                        cedula_cliente: e.target.value,
                        prestamo_id: null,
                      })
                    }}
                    className={`pl-10 ${errors.cedula_cliente ? 'border-red-500' : ''}`}
                    placeholder="V12345678"
                  />
                </div>

                {errors.cedula_cliente && (
                  <p className="text-sm text-red-600">
                    {errors.cedula_cliente}
                  </p>
                )}

                {isLoadingPrestamos && formData.cedula_cliente.length >= 2 && (
                  <p className="flex items-center gap-1 text-xs text-blue-600">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Buscando préstamos...
                  </p>
                )}

                {!isLoadingPrestamos &&
                  prestamosParaSelect.length > 0 &&
                  formData.cedula_cliente.length >= 2 && (
                    <p className="flex items-center gap-1 text-xs text-green-600">
                      <CheckCircle className="h-3 w-3" />
                      {prestamosParaSelect.length} préstamo
                      {prestamosParaSelect.length !== 1 ? 's' : ''} en la lista
                      {prestamosParaSelect.length > 1
                        ? ' - elija cuál aplica a este pago'
                        : ''}
                    </p>
                  )}

                {!isLoadingPrestamos &&
                  prestamosParaSelect.length === 0 &&
                  formData.cedula_cliente.length >= 2 && (
                    <p className="text-xs text-yellow-600">
                      No se encontraron préstamos para esta cédula
                    </p>
                  )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Crédito al que aplica el pago{' '}
                  {formData.cedula_cliente &&
                    prestamosParaSelect.length > 0 && (
                      <span className="text-red-500">*</span>
                    )}
                </label>

                {prestamosParaSelect.length > 1 && (
                  <p className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800">
                    Hay {prestamosParaSelect.length} créditos en la lista. Debe
                    elegir en el desplegable a cuál aplica este pago.
                  </p>
                )}

                {prestamosParaSelect.length > 0 ? (
                  <Select
                    value={formData.prestamo_id?.toString() || undefined}
                    onValueChange={value =>
                      setFormData({ ...formData, prestamo_id: parseInt(value) })
                    }
                  >
                    <SelectTrigger
                      className={errors.prestamo_id ? 'border-red-500' : ''}
                    >
                      <SelectValue
                        placeholder={
                          prestamosParaSelect.length > 1
                            ? 'Seleccione el crédito'
                            : 'Seleccione un crédito'
                        }
                      />
                    </SelectTrigger>

                    <SelectContent>
                      {prestamosParaSelect.map(prestamo => {
                        const modelo =
                          (prestamo as any).modelo_vehiculo ||
                          (prestamo as any).modelo ||
                          prestamo.producto ||
                          ''

                        const concesionario =
                          (prestamo as any).concesionario || ''

                        const desc =
                          [modelo, concesionario].filter(Boolean).join(' · ') ||
                          prestamo.estado

                        return (
                          <SelectItem
                            key={prestamo.id}
                            value={prestamo.id.toString()}
                          >
                            ID {prestamo.id} - {desc} - $
                            {Number(prestamo.total_financiamiento ?? 0).toFixed(
                              2
                            )}
                          </SelectItem>
                        )
                      })}
                    </SelectContent>
                  </Select>
                ) : formData.cedula_cliente &&
                  prestamos &&
                  prestamos.length === 0 &&
                  prestamosParaSelect.length === 0 ? (
                  <div className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    No hay préstamo asociado
                  </div>
                ) : null}

                {(errors.prestamo_id ||
                  (formData.cedula_cliente &&
                    prestamosParaSelect.length > 0 &&
                    !formData.prestamo_id)) && (
                  <p className="flex items-center gap-1 text-sm text-red-600">
                    <AlertCircle className="h-4 w-4" />

                    {errors.prestamo_id ||
                      (prestamosParaSelect.length > 1
                        ? 'Debe escoger un crédito de la lista'
                        : 'Debe seleccionar un crédito')}
                  </p>
                )}

                {/* Verificación de cédula del préstamo vs cédula del pago */}

                {formData.prestamo_id &&
                  prestamoSeleccionado &&
                  formData.cedula_cliente && (
                    <div
                      className={`flex items-start gap-2 rounded p-2 text-xs ${
                        formData.cedula_cliente === prestamoSeleccionado.cedula
                          ? 'border border-green-200 bg-green-50 text-green-700'
                          : 'border border-red-200 bg-red-50 text-red-700'
                      }`}
                    >
                      {formData.cedula_cliente ===
                      prestamoSeleccionado.cedula ? (
                        <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                      ) : (
                        <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                      )}

                      <div>
                        {formData.cedula_cliente ===
                        prestamoSeleccionado.cedula ? (
                          <span className="font-medium">Cédulas coinciden</span>
                        ) : (
                          <div>
                            <span className="font-medium">
                              {' '}
                              Cédulas no coinciden
                            </span>

                            <p className="mt-1">
                              Cédula del pago:{' '}
                              <strong>{formData.cedula_cliente}</strong>
                              <br />
                              Cédula del préstamo:{' '}
                              <strong>{prestamoSeleccionado.cedula}</strong>
                              <br />
                              <span className="text-xs">
                                El pago solo se aplicará si las cédulas
                                coinciden.
                              </span>
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
              </div>
            </div>

            {puedePagarBs === true && (
              <div className="space-y-2 rounded border border-slate-200 bg-slate-50/80 p-3">
                <label className="text-sm font-medium text-gray-700">
                  Moneda del pago <span className="text-red-500">*</span>
                </label>

                <Select
                  value={monedaRegistro}
                  onValueChange={v => {
                    const next = v as 'USD' | 'BS'
                    setMonedaRegistro(next)
                    const n = parseMontoLatam(montoStr)
                    if (montoStr.trim() === '') return
                    if (next === 'BS') {
                      setMontoStr(formatMontoBsVe(n))
                    } else {
                      setMontoStr(
                        n === 0 ? (isEditing ? '0.00' : '') : n.toFixed(2)
                      )
                    }
                    setFormData(prev => ({ ...prev, monto_pagado: n }))
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Moneda" />
                  </SelectTrigger>

                  <SelectContent>
                    <SelectItem value="USD">Dolares (USD)</SelectItem>

                    <SelectItem value="BS">Bolivares (Bs.)</SelectItem>
                  </SelectContent>
                </Select>

                <p className="text-xs text-gray-600">
                  La opcion en bolivares solo esta disponible para cedulas
                  autorizadas en la lista de pagos en bolivares.
                </p>
              </div>
            )}

            {consultandoBs && (
              <p className="text-xs text-blue-600">
                Consultando autorizacion bolivares...
              </p>
            )}

            {/* Fecha y Monto */}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Fecha de Pago <span className="text-red-500">*</span>
                </label>

                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                  <Input
                    type="date"
                    value={formData.fecha_pago}
                    onChange={e =>
                      setFormData({ ...formData, fecha_pago: e.target.value })
                    }
                    className={`pl-10 ${errors.fecha_pago ? 'border-red-500' : ''}`}
                    max={hoyYmdCaracas()}
                  />
                </div>

                {errors.fecha_pago && (
                  <p className="flex items-center gap-1 text-sm text-red-600">
                    <AlertCircle className="h-4 w-4" />

                    {errors.fecha_pago}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  {monedaRegistro === 'BS'
                    ? 'Monto (Bs.)'
                    : 'Monto pagado (USD)'}{' '}
                  <span className="text-red-500">*</span>
                </label>

                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                  <Input
                    type="text"
                    inputMode="decimal"
                    autoComplete="off"
                    value={montoStr}
                    onChange={e => {
                      const next = sanitizeMontoInputLatam(e.target.value)
                      setMontoStr(next)
                      setFormData(prev => ({
                        ...prev,
                        monto_pagado: parseMontoLatam(next),
                      }))
                    }}
                    onBlur={() => {
                      const n = parseMontoLatam(montoStr)
                      if (montoStr.trim() === '') {
                        setMontoStr('')
                        setFormData(prev => ({ ...prev, monto_pagado: 0 }))
                        return
                      }
                      if (monedaRegistro === 'BS') {
                        setMontoStr(
                          n === 0
                            ? isEditing
                              ? formatMontoBsVe(0)
                              : ''
                            : formatMontoBsVe(n)
                        )
                      } else {
                        setMontoStr(
                          n === 0 ? (isEditing ? '0.00' : '') : n.toFixed(2)
                        )
                      }
                      setFormData(prev => ({ ...prev, monto_pagado: n }))
                    }}
                    className={`pl-10 ${errors.monto_pagado ? 'border-red-500' : ''}`}
                    placeholder={monedaRegistro === 'BS' ? '0,00' : '0.00'}
                  />
                </div>

                {errors.monto_pagado && (
                  <p className="flex items-center gap-1 text-sm text-red-600">
                    <AlertCircle className="h-4 w-4" />

                    {errors.monto_pagado}
                  </p>
                )}

                {monedaRegistro === 'BS' && (
                  <div className="mt-2 space-y-2 rounded border border-amber-100 bg-amber-50/80 p-2 text-xs text-amber-950">
                    <p>
                      {tasaBdLoading
                        ? 'Consultando tasa en BD para la fecha de pago...'
                        : tasaBd
                          ? `Tasa oficial en BD para esta fecha: ${tasaBd} Bs. por 1 USD.`
                          : 'No hay tasa en BD para esa fecha. Ingrese tasa manual (Bs por 1 USD).'}
                    </p>

                    {!tasaBd && !tasaBdLoading && (
                      <div className="flex flex-col gap-1 sm:flex-row sm:items-center">
                        <label className="font-medium">
                          Tasa manual (Bs/USD)
                        </label>

                        <Input
                          type="number"
                          step="0.000001"
                          value={tasaManual}
                          onChange={e => setTasaManual(e.target.value)}
                          className="max-w-xs"
                        />
                      </div>
                    )}
                  </div>
                )}

                {/* Información sobre cómo se aplicará el pago */}

                {formData.monto_pagado > 0 &&
                  formData.prestamo_id &&
                  prestamoSeleccionado && (
                    <div className="rounded border border-blue-200 bg-blue-50 p-2 text-xs text-blue-700">
                      <div className="flex items-start gap-2">
                        <Info className="mt-0.5 h-4 w-4 flex-shrink-0" />

                        <div>
                          <p className="mb-1 font-medium">
                            {' '}
                            Cómo se aplicará el pago:
                          </p>

                          <ul className="ml-2 list-inside list-disc space-y-1">
                            <li>
                              Se aplicará a las cuotas más antiguas primero (por
                              fecha de vencimiento)
                            </li>

                            <li>
                              Se distribuirá proporcionalmente entre capital e
                              interés
                            </li>

                            {formData.monto_pagado >= 500 && (
                              <li>
                                Si el monto cubre una cuota completa y sobra, el
                                exceso se aplicará a la siguiente cuota
                              </li>
                            )}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}
              </div>
            </div>

            {/* Banco (misma variable que plantilla Excel / listado) */}

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">Banco</label>

              <div className="relative">
                <Building2 className="pointer-events-none absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-gray-400" />

                <Select
                  value={bancoSelectValue}
                  onValueChange={v =>
                    setFormData({
                      ...formData,
                      institucion_bancaria:
                        v === SIN_ESPECIFICAR_VALUE ? null : v,
                    })
                  }
                >
                  <SelectTrigger className="w-full pl-10">
                    <SelectValue placeholder="Seleccione banco" />
                  </SelectTrigger>

                  <SelectContent className="max-h-[min(24rem,70vh)]">
                    <SelectItem value={SIN_ESPECIFICAR_VALUE}>
                      Sin especificar
                    </SelectItem>

                    {opcionesBancoSelect.map(b => (
                      <SelectItem key={b} value={b}>
                        {b}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Número de Documento; «Código» solo en revisión manual (prop) */}

            <div
              className={`grid grid-cols-1 gap-4 ${mostrarCampoCodigoDocumento ? 'md:grid-cols-2' : ''}`}
            >
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-700">
                  Número de Documento <span className="text-red-500">*</span>
                </label>

                <div className="relative">
                  <FileText className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 transform text-gray-400" />

                  <Input
                    type="text"
                    value={formData.numero_documento}
                    onChange={e => {
                      const v = e.target.value
                      const msg = mensajeEdicionManualSufijoVistoProhibida(
                        formData.numero_documento,
                        v
                      )
                      if (msg) {
                        toast.error(msg)
                        return
                      }
                      setFormData({
                        ...formData,
                        numero_documento: v,
                      })
                    }}
                    onBlur={() => {
                      setFormData(prev => {
                        const raw = String(prev.numero_documento ?? '').trim()
                        const n =
                          normalizarNumeroDocumento(prev.numero_documento) ||
                          raw
                        const msg = mensajeEdicionManualSufijoVistoProhibida(
                          raw,
                          n
                        )
                        if (msg) {
                          toast.error(msg)
                          return prev
                        }
                        if (n !== raw) {
                          return { ...prev, numero_documento: n }
                        }
                        return prev
                      })
                    }}
                    className={`pl-10 ${errors.numero_documento ? 'border-red-500' : ''}`}
                    placeholder="Ej. BS. BNC/16622222"
                  />
                </div>

                {errors.numero_documento && (
                  <p className="text-sm text-red-600">
                    {errors.numero_documento}
                  </p>
                )}
              </div>

              {mostrarCampoCodigoDocumento ? (
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Código{' '}
                    <span className="text-xs font-normal text-gray-500">
                      (solo lectura; lo asigna Visto)
                    </span>
                  </label>

                  <Input
                    ref={codigoDocumentoInputRef}
                    type="text"
                    readOnly
                    aria-readonly="true"
                    title="Este campo no se escribe a mano. Se rellena con el botón Visto (revisión manual)."
                    value={String(formData.codigo_documento ?? '')}
                    maxLength={24}
                    className={`cursor-default bg-slate-50 text-slate-800 ${
                      errors.codigo_documento ? 'border-red-500' : ''
                    }`}
                    placeholder="Pendiente: use Visto"
                  />

                  <p className="text-xs text-gray-600">
                    No se puede teclear aquí. El token (formato A#### / P####)
                    lo genera y guarda el sistema al pulsar{' '}
                    <strong>Visto</strong> (mismo criterio que en carga masiva).
                  </p>
                  {bloquearCambioComprobanteCodigo ? (
                    <p className="text-xs text-amber-700">
                      Código bloqueado: el pago está conciliado/pagado.
                    </p>
                  ) : null}

                  {errors.codigo_documento && (
                    <p className="text-sm text-red-600">
                      {errors.codigo_documento}
                    </p>
                  )}
                </div>
              ) : null}
            </div>

            {mostrarCampoCodigoDocumento && revisionManualFullEdit ? (
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-violet-200/70 bg-violet-50 px-3 py-2">
                <p className="min-w-0 flex-1 text-xs text-violet-900">
                  <span className="font-medium">Revisión manual:</span> Visto
                  pone el código y guarda.
                </p>
                <div className="flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    className="text-[11px] font-medium text-violet-700 underline underline-offset-2 hover:text-violet-950"
                    onClick={() => setVistoRevisionManualOpen(true)}
                  >
                    Sin cambiar doc.
                  </button>
                  <Button
                    type="button"
                    size="sm"
                    disabled={isSubmitting || bloquearCambioComprobanteCodigo}
                    className="h-8 min-w-[4.5rem] bg-violet-600 px-3 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-50"
                    onClick={() => void handleVistoRellenarCodigoYGuardar()}
                  >
                    Visto
                  </Button>
                </div>
              </div>
            ) : null}

            {/* Comprobante: carga obligatoria de imagen (URL externa ya no se edita aquí). */}

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Comprobante (imagen) <span className="text-red-500">*</span>
              </label>

              <p className="text-xs text-gray-600">
                JPEG, PNG, WebP o GIF. Tamano maximo 10 MB. Obligatorio para
                guardar; en edicion puede conservar el comprobante ya cargado o
                subir uno nuevo.
              </p>
              {isEditing ? (
                <p className="hidden text-xs text-slate-600 lg:block">
                  Vista ampliada del comprobante a la derecha para verificar sin
                  desplazar el formulario.
                </p>
              ) : null}

              <input
                ref={comprobanteFileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif,.jpg,.jpeg,.png,.webp,.gif"
                className="sr-only"
                disabled={bloquearCambioComprobanteCodigo}
                onChange={e => {
                  if (bloquearCambioComprobanteCodigo) {
                    e.target.value = ''
                    return
                  }
                  const f = e.target.files?.[0] ?? null

                  setArchivoComprobante(f)

                  setErrors(prev => {
                    const next = { ...prev }

                    delete next.link_comprobante

                    return next
                  })

                  e.target.value = ''
                }}
              />

              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  disabled={isSubmitting || bloquearCambioComprobanteCodigo}
                  className="gap-2"
                  onClick={() => comprobanteFileInputRef.current?.click()}
                >
                  <Upload className="h-4 w-4" aria-hidden />
                  Elegir imagen
                </Button>
                {archivoComprobante ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    disabled={isSubmitting || bloquearCambioComprobanteCodigo}
                    className="text-red-600 hover:text-red-700"
                    onClick={() => setArchivoComprobante(null)}
                  >
                    Quitar imagen nueva
                  </Button>
                ) : null}
              </div>

              {bloquearCambioComprobanteCodigo ? (
                <p className="text-xs text-amber-700">
                  Comprobante bloqueado: este pago ya está conciliado/pagado.
                </p>
              ) : null}

              {archivoComprobante ? (
                <div className="space-y-2" role="status">
                  <p className="rounded border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-900">
                    Imagen nueva lista. Se subirá al guardar el pago.
                  </p>
                  {objUrlVistaArchivoNuevo ? (
                    <div className="flex flex-wrap items-end gap-3 lg:hidden">
                      <img
                        src={objUrlVistaArchivoNuevo}
                        alt="Vista previa del comprobante nuevo"
                        className="max-h-64 max-w-full rounded border border-gray-200 object-contain"
                      />
                    </div>
                  ) : null}
                </div>
              ) : null}

              {isEditing && linkComprobanteParaVista && !archivoComprobante ? (
                <div className="space-y-2 rounded border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800">
                  <p className="font-medium text-slate-900">
                    Comprobante ya registrado
                  </p>
                  {vistaPreviaComprobante.cargando ? (
                    <div className="flex items-center gap-2 text-slate-600">
                      <Loader2
                        className="h-5 w-5 shrink-0 animate-spin"
                        aria-hidden
                      />
                      <span>Cargando vista previa…</span>
                    </div>
                  ) : null}
                  {vistaPreviaComprobante.error ? (
                    <p className="text-red-600">
                      No se pudo cargar la imagen. Compruebe su sesión o abra el
                      comprobante en una pestaña nueva.
                    </p>
                  ) : null}
                  {vistaPreviaComprobante.src ? (
                    <div className="flex flex-wrap items-end gap-3 lg:hidden">
                      <img
                        src={vistaPreviaComprobante.src}
                        alt="Comprobante registrado"
                        className="max-h-64 max-w-full rounded border border-gray-200 bg-white object-contain"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="gap-1.5"
                        onClick={() => {
                          void (async () => {
                            try {
                              await abrirStaffComprobanteDesdeHref(
                                linkComprobanteParaVista
                              )
                            } catch {
                              toast.error(
                                'No se pudo abrir el comprobante en una pestaña nueva.'
                              )
                            }
                          })()
                        }}
                      >
                        <Eye className="h-4 w-4" aria-hidden />
                        Abrir
                      </Button>
                    </div>
                  ) : null}
                  {!vistaPreviaComprobante.cargando &&
                  !vistaPreviaComprobante.src &&
                  !vistaPreviaComprobante.error &&
                  linkComprobanteParaVista &&
                  !pathApiComprobanteImagenDesdeHref(
                    linkComprobanteParaVista
                  ) ? (
                    <div className="flex flex-wrap items-center gap-2 lg:hidden">
                      <p className="text-slate-700">
                        Enlace externo (p. ej. Drive). Puede abrirlo para
                        revisar el archivo.
                      </p>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="gap-1.5"
                        onClick={() => {
                          void (async () => {
                            try {
                              await abrirStaffComprobanteDesdeHref(
                                linkComprobanteParaVista
                              )
                            } catch {
                              toast.error('No se pudo abrir el enlace.')
                            }
                          })()
                        }}
                      >
                        <Eye className="h-4 w-4" aria-hidden />
                        Abrir enlace
                      </Button>
                    </div>
                  ) : null}
                  <p className="text-xs text-slate-600">
                    Suba otra imagen solo si desea reemplazar el comprobante.
                  </p>
                </div>
              ) : null}

              {errors.link_comprobante && (
                <p className="text-sm text-red-600">
                  {errors.link_comprobante}
                </p>
              )}
            </div>

            {/* Notas */}

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Notas (Opcional)
              </label>

              <Textarea
                value={formData.notas || ''}
                onChange={e =>
                  setFormData({ ...formData, notas: e.target.value || null })
                }
                placeholder="Observaciones adicionales"
                rows={3}
              />
            </div>

            {modoGuardarYProcesar && (
              <div className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                <div className="flex items-start gap-2">
                  <Info className="mt-0.5 h-4 w-4 flex-shrink-0" />

                  <p>
                    <strong>Guardar y Procesar</strong> actualizará el pago en
                    la base de datos y aplicará las reglas de negocio
                    (conciliación y aplicación a cuotas) automáticamente.
                  </p>
                </div>
              </div>
            )}
              </div>

              {isEditing ? (
                <aside
                  className="hidden max-h-[42vh] min-h-[11rem] flex-shrink-0 flex-col gap-2 border-t border-slate-200 bg-slate-50/95 p-4 lg:flex lg:max-h-none lg:w-1/2 lg:max-w-[50%] lg:min-h-0 lg:border-l lg:border-t-0"
                  aria-label="Vista del comprobante"
                >
                  <h3 className="text-sm font-semibold text-slate-800">
                    Comprobante
                  </h3>
                  <div className="flex justify-start">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={isSubmitting || isRescanning}
                      onClick={() => void handleReescanearDesdeComprobanteActual()}
                    >
                      {isRescanning ? 'Escaneando...' : 'Escanear'}
                    </Button>
                  </div>
                  <div className="flex min-h-0 flex-1 flex-col overflow-y-auto rounded-md border border-slate-200 bg-white p-2">
                    {archivoComprobante && objUrlVistaArchivoNuevo ? (
                      <img
                        src={objUrlVistaArchivoNuevo}
                        alt="Vista previa del comprobante seleccionado"
                        className="mx-auto max-h-[min(68vh,34rem)] w-full max-w-full object-contain"
                      />
                    ) : linkComprobanteParaVista && !archivoComprobante ? (
                      <div className="flex min-h-[10rem] flex-col gap-3">
                        {vistaPreviaComprobante.cargando ? (
                          <div className="flex items-center gap-2 text-slate-600">
                            <Loader2
                              className="h-5 w-5 shrink-0 animate-spin"
                              aria-hidden
                            />
                            <span>Cargando comprobante…</span>
                          </div>
                        ) : null}
                        {vistaPreviaComprobante.error ? (
                          <p className="text-sm text-red-600">
                            No se pudo cargar la imagen. Use Abrir o revise la
                            sesión.
                          </p>
                        ) : null}
                        {vistaPreviaComprobante.src ? (
                          <>
                            <img
                              src={vistaPreviaComprobante.src}
                              alt="Comprobante registrado"
                              className="mx-auto max-h-[min(68vh,34rem)] w-full max-w-full rounded border border-slate-100 object-contain"
                            />
                            <div className="flex justify-center">
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="gap-1.5"
                                onClick={() => {
                                  void (async () => {
                                    try {
                                      await abrirStaffComprobanteDesdeHref(
                                        linkComprobanteParaVista
                                      )
                                    } catch {
                                      toast.error(
                                        'No se pudo abrir el comprobante en una pestaña nueva.'
                                      )
                                    }
                                  })()
                                }}
                              >
                                <Eye className="h-4 w-4" aria-hidden />
                                Abrir en pestaña
                              </Button>
                            </div>
                          </>
                        ) : null}
                        {!vistaPreviaComprobante.cargando &&
                        !vistaPreviaComprobante.src &&
                        !vistaPreviaComprobante.error &&
                        linkComprobanteParaVista &&
                        !pathApiComprobanteImagenDesdeHref(
                          linkComprobanteParaVista
                        ) ? (
                          <div className="flex flex-col items-center gap-2 text-center text-sm text-slate-700">
                            <p>Enlace externo al comprobante.</p>
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              className="gap-1.5"
                              onClick={() => {
                                void (async () => {
                                  try {
                                    await abrirStaffComprobanteDesdeHref(
                                      linkComprobanteParaVista
                                    )
                                  } catch {
                                    toast.error('No se pudo abrir el enlace.')
                                  }
                                })()
                              }}
                            >
                              <Eye className="h-4 w-4" aria-hidden />
                              Abrir enlace
                            </Button>
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      <p className="self-center px-2 text-center text-sm text-slate-600">
                        Use &quot;Elegir imagen&quot; para ver la vista previa, o
                        conserve el comprobante ya guardado para mostrarlo aquí.
                      </p>
                    )}
                  </div>
                </aside>
              ) : null}
            </div>

            <div className="flex shrink-0 justify-end gap-3 border-t bg-white px-6 py-4">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isSubmitting}
              >
                Cancelar
              </Button>

              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />

                    {modoGuardarYProcesar
                      ? 'Guardando y procesando...'
                      : isEditing
                        ? 'Actualizando...'
                        : 'Registrando...'}
                  </>
                ) : (
                  <>
                    <CheckCircle className="mr-2 h-4 w-4" />

                    {modoGuardarYProcesar
                      ? 'Guardar y Procesar'
                      : isEditing
                        ? 'Actualizar Pago'
                        : 'Registrar Pago'}
                  </>
                )}
              </Button>
            </div>
          </form>

          <Dialog
            open={vistoRevisionManualOpen}
            onOpenChange={setVistoRevisionManualOpen}
          >
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>
                  Comprobante duplicado (revisión manual)
                </DialogTitle>
                <div className="space-y-2 text-sm text-gray-600">
                  <p>
                    El botón principal <strong>Visto</strong> rellena el campo{' '}
                    <strong>Código</strong> con un token <strong>A####</strong>{' '}
                    / <strong>P####</strong> y guarda: el comprobante del banco
                    puede quedar igual. No está permitido escribir{' '}
                    <code className="rounded bg-gray-100 px-1">_A####</code> ni{' '}
                    <code className="rounded bg-gray-100 px-1">_P####</code> a
                    mano en el Nº de documento.
                  </p>
                  <ul className="list-inside list-disc space-y-1 text-xs">
                    <li>
                      <strong>Autorizar sin cambiar</strong>: quita avisos de
                      duplicado en pantalla. Si al guardar sigue fallando la
                      unicidad, use <strong>Visto</strong> para asignar{' '}
                      <strong>Código</strong> automáticamente (no se escribe en
                      la caja).
                    </li>
                  </ul>
                </div>
              </DialogHeader>
              <DialogFooter className="flex flex-col gap-2 sm:flex-col sm:justify-stretch">
                <button
                  type="button"
                  className="w-full rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-50"
                  onClick={() => {
                    setErrors(prev => {
                      const next = { ...prev }
                      delete next.numero_documento
                      const g = next.general
                      if (
                        g === DUPLICADO_DOCUMENTO_UI ||
                        g === DUPLICADO_HUELLA_UI ||
                        (g &&
                          (g.toLowerCase().includes('comprobante') ||
                            g.toLowerCase().includes('documento')))
                      ) {
                        delete next.general
                      }
                      return next
                    })
                    toast.success(
                      'Autorizado sin modificar el comprobante. Si persiste duplicado al guardar, use Visto para asignar Código.'
                    )
                    setVistoRevisionManualOpen(false)
                  }}
                >
                  Autorizar sin cambiar el documento
                </button>
                <button
                  type="button"
                  className="w-full rounded-md px-4 py-2 text-sm text-gray-600 hover:bg-gray-100"
                  onClick={() => setVistoRevisionManualOpen(false)}
                >
                  Cancelar
                </button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
