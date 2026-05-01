import { useState, useEffect, useMemo, useRef } from 'react'

import { useQuery } from '@tanstack/react-query'

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
  Trash2,
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
  type Pago,
  type PagoCreate,
  type PagoInicialRegistrar,
} from '../../services/pagoService'

import {
  pagoConErrorService,
  type PagoConError,
} from '../../services/pagoConErrorService'

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

import { fechaPagoParaInputDate, hoyYmdCaracas } from '../../utils/fechaZona'

import {
  composeNumeroDocumentoAlmacenado,
  splitNumeroDocumentoAlmacenado,
} from '../../utils/documentoPago'

import {
  extraerCaracteresCedulaPublica,
  normalizarCedulaParaProcesar,
} from '../../utils/cedulaConsultaPublica'

import { apiClient } from '../../services/api'

import {
  abrirStaffComprobanteDesdeHref,
  esUrlComprobanteImagenConAuth,
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

function etiquetaPrestamoLinea(
  prestamoId: number | null | undefined,
  detalle: Prestamo | undefined
): string {
  const pidRaw = prestamoId != null ? Number(prestamoId) : NaN
  const pid = Number.isFinite(pidRaw) && pidRaw > 0 ? Math.trunc(pidRaw) : null
  if (!pid) {
    return 'Sin préstamo asignado.'
  }
  const frag =
    (detalle?.producto || '').trim() ||
    (detalle?.modelo_vehiculo || '').trim() ||
    (detalle?.nombres || '').trim()
  return frag ? `ID ${pid} - ${frag}` : `ID ${pid}`
}

function pareceUrlImagenComprobanteExterna(u: string): boolean {
  if (!u) return false
  const low = u.toLowerCase()
  const path = u.split('?')[0].toLowerCase()
  if (/\.(jpe?g|png|gif|webp)$/i.test(path)) return true
  return low.includes('googleusercontent')
}

async function clasificarBlobComprobanteVisual(
  b: Blob
): Promise<'image' | 'pdf'> {
  const ct = (b.type || '').toLowerCase()
  if (ct.includes('pdf')) return 'pdf'
  if (ct.startsWith('image/')) return 'image'
  try {
    const buf = await b.slice(0, 5).arrayBuffer()
    const head = new Uint8Array(buf)
    let sig = ''
    for (let i = 0; i < head.length; i++) sig += String.fromCharCode(head[i]!)
    if (sig.startsWith('%PDF')) return 'pdf'
  } catch {
    /* ignore */
  }
  return 'image'
}

/**
 * Miniatura del comprobante ya guardado: interno vía sesión (blob); externo con <img> si parece imagen.
 * PDF se muestra en `<iframe>` ( `<img>` no renderiza application/pdf → zona en blanco).
 */
function useVistaPreviaComprobanteGuardado(
  hrefInicial: string,
  activo: boolean
): {
  src: string | null
  kind: 'image' | 'pdf'
  cargando: boolean
  error: boolean
} {
  const pathAuth = activo
    ? pathApiComprobanteImagenDesdeHref(hrefInicial)
    : null
  const requiereSesion = Boolean(pathAuth)
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [kind, setKind] = useState<'image' | 'pdf'>('image')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!activo || !hrefInicial.trim()) {
      setBlobUrl(u => {
        if (u) URL.revokeObjectURL(u)
        return null
      })
      setKind('image')
      setCargando(false)
      setError(false)
      return
    }
    if (!requiereSesion || !pathAuth) {
      setBlobUrl(u => {
        if (u) URL.revokeObjectURL(u)
        return null
      })
      setKind('image')
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
        const visual = await clasificarBlobComprobanteVisual(blob)
        const objectUrl = URL.createObjectURL(blob)
        setKind(visual)
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
      setKind('image')
    }
  }, [activo, hrefInicial, pathAuth, requiereSesion])

  if (!activo || !hrefInicial.trim()) {
    return { src: null, kind: 'image', cargando: false, error: false }
  }
  if (requiereSesion) {
    return { src: blobUrl, kind, cargando, error }
  }
  if (pareceUrlImagenComprobanteExterna(hrefInicial)) {
    return { src: hrefInicial, kind: 'image', cargando: false, error: false }
  }
  return { src: null, kind: 'image', cargando: false, error: false }
}

function VistaEmbebidaComprobante({
  src,
  kind,
  classNameImg,
  classNamePdf,
}: {
  src: string
  kind: 'image' | 'pdf'
  classNameImg: string
  classNamePdf: string
}) {
  if (kind === 'pdf') {
    return (
      <iframe
        src={src}
        title="Vista del comprobante"
        className={classNamePdf}
      />
    )
  }
  return <img src={src} alt="Comprobante" className={classNameImg} />
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

/** OCR suele devolver solo dígitos; BD usa V/E/J + dígitos. Si coinciden los números, es la misma persona. */
function cedulasMismaPersonaParaPrestamo(a: string, b: string): boolean {
  const da = String(a || '').replace(/\D/g, '')
  const db = String(b || '').replace(/\D/g, '')
  if (da.length >= 6 && db.length >= 6 && da === db) return true
  const norm = (s: string) =>
    String(s || '')
      .toUpperCase()
      .replace(/[^VEJG0-9]/g, '')
  const na = norm(a)
  const nb = norm(b)
  return Boolean(na && nb && na === nb)
}

/** Meta opcional para el padre (p. ej. evitar DELETE duplicado tras mover-a-pagos). */
export type RegistrarPagoOnSuccessMeta = {
  skipDeleteConError?: boolean
}

interface RegistrarPagoFormProps {
  onClose: () => void

  onSuccess: (procesado?: boolean, meta?: RegistrarPagoOnSuccessMeta) => void

  /**
   * Callback cuando se detecta documento duplicado (error 409).
   * Se pasa el pago actual para abrir revisión manual.
   */
  onDuplicadoDetectado?: (pago: Pago | PagoConError) => void

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
  onDuplicadoDetectado,
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

  const linkComprobanteInicialRef = useRef(
    resolverLinkComprobanteInicial(pagoInicial)
  )

  const [archivoComprobante, setArchivoComprobante] = useState<File | null>(
    null
  )

  const archivoNuevoComprobanteEsPdf = useMemo(
    () =>
      Boolean(
        archivoComprobante &&
        (archivoComprobante.type === 'application/pdf' ||
          /\.pdf$/i.test(archivoComprobante.name || ''))
      ),
    [archivoComprobante]
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
      fechaPagoParaInputDate(pagoInicial?.fecha_pago) || hoyYmdCaracas(),

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
    linkComprobanteInicialRef.current =
      resolverLinkComprobanteInicial(pagoInicial)
  }, [pagoInicial?.link_comprobante, pagoInicial?.documento_ruta])

  const [isSubmitting, setIsSubmitting] = useState(false)

  const [isDeleting, setIsDeleting] = useState(false)

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

  /**
   * Cédula canónica para la búsqueda: limpia separadores (`3.14.552` → `314552`),
   * mayúsculas y, cuando ya hay 6-11 dígitos sin letra, antepone `V` (igual que el flujo público).
   * Acelera el match en BD porque la API recibe la misma forma con la que está almacenada.
   */
  const cedulaCanonicaBusqueda = useMemo(() => {
    const limpia = extraerCaracteresCedulaPublica(debouncedCedula || '')
    if (limpia.length < 2) return ''
    const norm = normalizarCedulaParaProcesar(limpia)
    if (norm.valido && norm.valorParaEnviar) return norm.valorParaEnviar
    return limpia
  }, [debouncedCedula])

  // Buscar préstamos cuando cambia la cédula (con al menos 2 caracteres)

  const { data: prestamos, isLoading: isLoadingPrestamos } =
    usePrestamosByCedula(cedulaCanonicaBusqueda)

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

  const debouncedNumeroDoc = useDebounce(
    String(formData.numero_documento ?? '').trim(),
    400
  )

  /** Misma clave que persiste la API (`comprobante` + `§CD:` + código); el GET conflicto debe usarla para alinear con `pagos.numero_documento`. */
  const claveDocumentoConflicto = useMemo(() => {
    const b =
      normalizarNumeroDocumento(
        String(formData.numero_documento ?? '').trim()
      ) ?? ''
    const c = String(formData.codigo_documento ?? '').trim()
    return (
      composeNumeroDocumentoAlmacenado(b || null, c || null) ?? ''
    )
  }, [formData.numero_documento, formData.codigo_documento])

  const debouncedClaveDocumentoConflicto = useDebounce(
    claveDocumentoConflicto,
    400
  )

  const claveDocumentoInicial = useMemo(() => {
    const b =
      normalizarNumeroDocumento(
        String(pagoInicial?.numero_documento ?? '').trim()
      ) ?? ''
    const c = String(
      (pagoInicial as { codigo_documento?: string | null })
        ?.codigo_documento ?? ''
    ).trim()
    return (
      composeNumeroDocumentoAlmacenado(b || null, c || null) ?? ''
    )
  }, [pagoInicial])

  const excludeIdConflicto =
    isEditing && !esPagoConError && pagoId ? pagoId : undefined

  /** En revisión manual el usuario debe ver siempre el estado del Nº doc.; no exigir comprobante enlazado. */
  const conflictoDocQueryEnabled =
    debouncedClaveDocumentoConflicto.length > 0 &&
    (mostrarCampoCodigoDocumento ||
      (isEditing && Boolean(linkComprobanteParaVista && !archivoComprobante)))

  const {
    data: conflictoDocApi,
    isPending: conflictoDocPendiente,
    isError: conflictoDocError,
  } = useQuery({
    queryKey: [
      'conflicto-documento-cartera',
      debouncedClaveDocumentoConflicto,
      excludeIdConflicto,
    ],
    queryFn: () =>
      pagoService.getConflictoDocumentoCartera({
        numero_documento: debouncedClaveDocumentoConflicto,
        exclude_pago_id: excludeIdConflicto,
      }),
    enabled: conflictoDocQueryEnabled,
    staleTime: 15_000,
  })

  const mismoDocQueInicial =
    debouncedClaveDocumentoConflicto === claveDocumentoInicial

  const pidConflictoParaDetalle =
    conflictoDocApi?.conflicto && conflictoDocApi.prestamo_id
      ? conflictoDocApi.prestamo_id
      : conflictoDocPendiente &&
          mismoDocQueInicial &&
          pagoInicial?.duplicado_documento_en_pagos &&
          pagoInicial?.duplicado_en_cartera_prestamo_id
        ? pagoInicial.duplicado_en_cartera_prestamo_id
        : 0

  const { data: prestamoConflictoDetalle } = usePrestamo(
    pidConflictoParaDetalle
  )

  const handleReescanearDesdeComprobanteActual = async () => {
    if (
      !window.confirm(
        'Escanear reemplazara los campos actuales (fecha, banco, numero, monto y moneda). Desea continuar?'
      )
    ) {
      return
    }

    let cedulaPartes = descomponerCedula(formData.cedula_cliente)

    // Imagen nueva (File) o comprobante ya guardado en BD (sin archivo nuevo en memoria)
    const tieneComprobanteParaEscanear =
      Boolean(archivoComprobante) ||
      Boolean(linkComprobanteParaVista && !archivoComprobante)

    let extraccionSinCliente = false

    if (!cedulaPartes && !tieneComprobanteParaEscanear) {
      toast.error('Ingrese una cédula válida antes de escanear.')
      return
    }

    // Sin cédula válida pero hay imagen: placeholder sintácticamente válido + backend extraccion_sin_cliente
    // (V+0 fallaba validate_cedula 6-11 dígitos; el backend exige cliente salvo esta bandera.)
    if (!cedulaPartes && tieneComprobanteParaEscanear) {
      cedulaPartes = { tipo: 'V', numero: '12345678' }
      extraccionSinCliente = true
      toast.info('Re-escaneando para extraer cédula del comprobante...')
    }

    setIsRescanning(true)
    try {
      let fileToScan: File | null = archivoComprobante
      if (!fileToScan) {
        const href = (linkComprobanteParaVista || '').trim()
        if (!href) {
          toast.error('No hay comprobante disponible para escanear.')
          setIsRescanning(false)
          return
        }

        // URL absoluta https solo bloquea si NO es el endpoint interno de comprobante (misma sesión Bearer).
        // Antes se rechazaba cualquier http(s), incluso .../api/v1/pagos/comprobante-imagen/... guardado en BD.
        if (
          /^https?:\/\//i.test(href) &&
          !esUrlComprobanteImagenConAuth(href)
        ) {
          toast.error(
            'Este enlace no es un comprobante interno (p. ej. Drive). Para re-escanear, adjunte la imagen con "Elegir imagen".'
          )
          setIsRescanning(false)
          return
        }

        try {
          const { blob, contentType } =
            await fetchStaffComprobanteBlobWithDisplayMime(href)
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
        } catch (fetchErr) {
          toast.error(
            'No se pudo acceder al comprobante guardado. Adjunte la imagen nuevamente.'
          )
          setIsRescanning(false)
          return
        }
      }

      const fd = new FormData()
      fd.append('tipo_cedula', cedulaPartes!.tipo)
      fd.append('numero_cedula', cedulaPartes!.numero)
      if (extraccionSinCliente) {
        fd.append('extraccion_sin_cliente', 'true')
      }
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

      // Procesar cédula extraída del comprobante (solo dígitos para Mercantil/BNC)
      let nextCedula = formData.cedula_cliente
      const cedulaExtraida = (s.cedula_pagador_en_comprobante || '').trim()
      if (cedulaExtraida) {
        // Gemini retorna solo dígitos; el validador busca con prefijos V/E/J/G
        nextCedula = cedulaExtraida
      }

      setFormData(prev => {
        const antes = (prev.cedula_cliente || '').trim()
        const despues = (nextCedula || '').trim()
        const cedulaCambio = despues !== antes

        let nextPrestamoId: number | null = prev.prestamo_id ?? null
        // Antes: siempre null aquí → "Guardar y Procesar" no llamaba aplicar-cuotas sin préstamo.
        if (cedulaCambio) {
          nextPrestamoId = null
          const prevPid = prev.prestamo_id
          if (prevPid && prestamoSeleccionado?.id === prevPid) {
            if (
              cedulasMismaPersonaParaPrestamo(
                despues,
                prestamoSeleccionado.cedula || ''
              )
            ) {
              nextPrestamoId = prevPid
            }
          }
          if (nextPrestamoId === null && pidRevisionCtx > 0) {
            const pCtx = prestamoContextoRevisionManual as Prestamo | undefined
            if (
              pCtx?.id === pidRevisionCtx &&
              cedulasMismaPersonaParaPrestamo(despues, pCtx.cedula || '')
            ) {
              nextPrestamoId = pidRevisionCtx
            }
          }
        }

        return {
          ...prev,
          cedula_cliente: nextCedula,
          fecha_pago: (s.fecha_pago || '').trim() || prev.fecha_pago,
          institucion_bancaria:
            (s.institucion_financiera || '').trim() ||
            prev.institucion_bancaria,
          numero_documento:
            (s.numero_operacion || '').trim() || prev.numero_documento,
          monto_pagado: nextMonto,
          prestamo_id: nextPrestamoId,
        }
      })
      setErrors(prev => {
        const next = { ...prev }
        delete next.fecha_pago
        delete next.institucion_bancaria
        delete next.numero_documento
        delete next.monto_pagado
        delete next.general
        return next
      })

      if (cedulaExtraida) {
        toast.success(
          `Campos actualizados desde el comprobante. Cédula detectada: ${cedulaExtraida}`
        )
      } else {
        toast.success('Campos actualizados desde el comprobante.')
      }
    } catch (error) {
      console.error('Error re-escaneando:', error)
      toast.error(
        error instanceof Error
          ? error.message
          : 'No se pudo re-escanear el comprobante.'
      )
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
    } else if (/^error$/i.test(String(fd.cedula_cliente).trim())) {
      newErrors.cedula_cliente =
        'Corrija la cédula del cliente (no puede quedar «ERROR»). Use la del comprobante, p. ej. V28102491.'
    }

    if (prestamosParaSelect.length > 0 && !fd.prestamo_id) {
      newErrors.prestamo_id =
        prestamosParaSelect.length > 1
          ? 'Debe escoger un crédito de la lista'
          : 'Debe seleccionar el crédito'
    }

    if (
      modoGuardarYProcesar &&
      fd.monto_pagado > 0 &&
      !fd.prestamo_id &&
      !newErrors.prestamo_id
    ) {
      newErrors.prestamo_id =
        prestamosParaSelect.length === 0
          ? 'Para «Guardar y procesar» hace falta un crédito. Corrija la cédula hasta que carguen los préstamos (p. ej. V28102491 según el comprobante) y elija el crédito; sin préstamo no se aplica a cuotas.'
          : 'Debe seleccionar el crédito para aplicar el pago a cuotas.'
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
      if (
        !cedulasMismaPersonaParaPrestamo(
          fd.cedula_cliente,
          prestamoParaCedula.cedula || ''
        )
      ) {
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

      // Aceptar comprobantes ya registrados con rutas internas/no-URL
      // (p. ej. documento_ruta histórico o identificador de storage).

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
        datosEnvio.conciliado = true // ✅ AUTOCONCILIAR si hay préstamo y monto
      }

      let idPagoParaProcesar: number | undefined = pagoId

      if (isEditing && idPagoParaProcesar) {
        if (esPagoConError) {
          await pagoConErrorService.update(idPagoParaProcesar, datosEnvio)
        } else {
          await pagoService.updatePago(idPagoParaProcesar, datosEnvio)
        }
      } else {
        const pagoCreado = await pagoService.createPago(datosEnvio)
        idPagoParaProcesar = pagoCreado.id

        if (import.meta.env.DEV) {
          console.log(
            `Pago creado: id=${pagoCreado.id}, conciliado=${pagoCreado.conciliado}`
          )
        }
      }

      let metaExito: RegistrarPagoOnSuccessMeta | undefined

      // "Guardar y Procesar": desde pagos_con_errores hay que mover a `pagos` y aplicar allí;
      // aplicar-cuotas por ID solo existe en la tabla `pagos`.
      if (modoGuardarYProcesar && fd.prestamo_id && fd.monto_pagado > 0) {
        const moverDesdeConErrores = Boolean(
          esPagoConError && isEditing && pagoId
        )

        if (moverDesdeConErrores && pagoId != null) {
          const idConError = pagoId

          try {
            const resultMover = await pagoConErrorService.moverAPagosNormales([
              idConError,
            ])

            if (resultMover.movidos < 1) {
              const detalle =
                resultMover.errores?.filter(Boolean).join(' ') ||
                resultMover.mensaje ||
                'No se pudo mover el pago a la tabla operativa (pagos).'

              const dupDocumentoCartera =
                /ya existe en tabla pagos/i.test(detalle) ||
                (/documento/i.test(detalle) && /ya existe/i.test(detalle))

              setErrors(prev => ({
                ...prev,
                general: dupDocumentoCartera
                  ? 'Comprobante duplicado en cartera: ese comprobante ya está registrado en pagos. Pulse «Visto» para asignar un código (sufijo) distinto y guarde de nuevo; sin código distinto «Guardar y procesar» no puede mover el pago.'
                  : detalle,
              }))

              toast.error(detalle, { duration: 7000 })

              if (
                dupDocumentoCartera &&
                mostrarCampoCodigoDocumento &&
                revisionManualFullEdit
              ) {
                setVistoRevisionManualOpen(true)
              }

              onSuccess(false)

              return
            }

            if (resultMover.errores?.length) {
              toast.warning(
                `Pago pasado a cartera, pero hubo incidencias al aplicar cuotas: ${resultMover.errores.join(
                  ' '
                )}`,
                { duration: 7000 }
              )
            } else {
              const nCuotas =
                typeof resultMover.cuotas_aplicadas === 'number'
                  ? resultMover.cuotas_aplicadas
                  : 0

              toast.success(
                nCuotas > 0
                  ? `Pago en cartera y aplicado a cuotas (${nCuotas} aplicación(es) en cascada).`
                  : 'Pago movido a la tabla de pagos operativa.',
                { duration: 4000 }
              )
            }

            metaExito = { skipDeleteConError: true }
          } catch (moverErr: unknown) {
            toast.warning(
              getErrorMessage(moverErr) ||
                'No se pudo mover el pago a cartera. Revise duplicados o reintente.',
              { duration: 6000 }
            )
            if (import.meta.env.DEV) {
              console.warn('mover-a-pagos tras guardar:', moverErr)
            }
            onSuccess(false)

            return
          }
        } else {
          try {
            const resultAplicar = await pagoService.aplicarPagoACuotas(
              idPagoParaProcesar!
            )

            let mostroToastLote = false

            if (
              resultAplicar?.success &&
              !resultAplicar.ya_aplicado &&
              resultAplicar.cuotas_completadas === 0 &&
              resultAplicar.cuotas_parciales === 0 &&
              fd.prestamo_id != null &&
              Number(fd.prestamo_id) > 0
            ) {
              try {
                const lote =
                  await pagoService.aplicarPagosPendientesCuotasPorPrestamo(
                    Number(fd.prestamo_id)
                  )
                const nAplic = Number(lote.pagos_con_aplicacion ?? 0)
                if (nAplic > 0) {
                  mostroToastLote = true
                  toast.success(
                    lote.mensaje?.trim()
                      ? lote.mensaje
                      : `Cascada por préstamo: ${nAplic} pago(s) con abono en cuotas.`,
                    { duration: 6500 }
                  )
                }
              } catch {
                /* continuar con toasts según resultAplicar */
              }
            }

            if (!mostroToastLote) {
              if (resultAplicar?.success) {
                if (resultAplicar.ya_aplicado) {
                  toast.success(
                    'Pago ya estaba articulado en cuotas (no se duplicó la cascada). Suele ocurrir si el guardado ya aplicó la amortización.',
                    { duration: 5500 }
                  )
                } else if (
                  resultAplicar.cuotas_completadas === 0 &&
                  resultAplicar.cuotas_parciales === 0
                ) {
                  toast.warning(
                    resultAplicar.message?.trim()
                      ? `Pago guardado; cascada sin abono en cuotas: ${resultAplicar.message}`
                      : 'Pago guardado; no hubo abono en cuotas (sin saldo pendiente, préstamo no aplicable o monto no distribuible). Revise la tabla de amortización.',
                    { duration: 6500 }
                  )
                } else {
                  const detalleAplicacion = `${resultAplicar.cuotas_completadas} cuota(s) completada(s)${
                    resultAplicar.cuotas_parciales > 0
                      ? `, ${resultAplicar.cuotas_parciales} parcial(es)`
                      : ''
                  }`
                  toast.success(
                    `Pago aplicado a cuotas: ${detalleAplicacion}`,
                    {
                      duration: 4000,
                    }
                  )
                }
              } else if (resultAplicar?.message) {
                toast.warning(
                  `Pago guardado, pero no se aplicó a cuotas: ${resultAplicar.message}`,
                  { duration: 6000 }
                )
              }
            }

            if (import.meta.env.DEV) {
              console.log('Aplicación a cuotas:', resultAplicar)
            }
          } catch (applyErr) {
            toast.warning(
              'Pago guardado pero no se pudo aplicar automáticamente a cuotas (tiempo de espera agotado o error de red). Reintente o use «Aplicar pagos a cuotas» por préstamo en amortización.',
              { duration: 7000 }
            )
            if (import.meta.env.DEV) {
              console.warn(
                'Error aplicando a cuotas (pero pago guardado):',
                applyErr
              )
            }
          }
        }
      }

      onSuccess(modoGuardarYProcesar, metaExito)
    } catch (error: unknown) {
      console.error(
        `Error ${isEditing ? 'actualizando' : 'registrando'} pago:`,
        error
      )

      let errorMessage = getErrorMessage(error)
      let esDocumentoDuplicado = false

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
          esDocumentoDuplicado = true
        } else if (detail) {
          errorMessage = detail
        }
      }

      // Si es documento duplicado y estamos editando, abrir Revisión Manual
      if (esDocumentoDuplicado && isEditing && pagoId && onDuplicadoDetectado) {
        // Cerramos el formulario
        onClose()
        // Simplemente pasamos el pago ID - el callback solo lo usa para el toast
        const pagoActual = {
          id: pagoId,
          cedula_cliente: formData.cedula_cliente,
          prestamo_id: formData.prestamo_id,
          fecha_pago: formData.fecha_pago,
          monto_pagado: formData.monto_pagado,
          numero_documento: formData.numero_documento,
          codigo_documento: formData.codigo_documento ?? null,
          institucion_bancaria: formData.institucion_bancaria || null,
          estado: 'PENDIENTE',
          fecha_registro: new Date().toISOString(),
          fecha_conciliacion: null,
          conciliado: false,
          usuario_registro: '',
          notas: formData.notas || null,
        } as Pago
        onDuplicadoDetectado(pagoActual)
        return
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

  const handleEliminarPago = async () => {
    if (!isEditing || !pagoId) return
    if (
      !window.confirm(
        '¿Eliminar este pago de forma permanente? Si tiene préstamo asociado, se actualizarán las cuotas.'
      )
    ) {
      return
    }
    setIsDeleting(true)
    try {
      if (esPagoConError) {
        await pagoConErrorService.delete(pagoId)
      } else {
        await pagoService.deletePago(pagoId)
      }
      toast.success('Pago eliminado.')
      onSuccess(false)
      onClose()
    } catch (error: unknown) {
      toast.error(getErrorMessage(error) || 'No se pudo eliminar el pago.')
    } finally {
      setIsDeleting(false)
    }
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
            isEditing ? 'max-w-[min(72rem,calc(100vw-1.5rem))]' : 'max-w-2xl'
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
                      <strong>Comprobante obligatorio:</strong> suba una foto
                      del comprobante (hasta 10 MB). Para flujos con moneda Bs.,
                      recibo PDF de tasa u otros casos puede usar{' '}
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
                      . Este formulario registra o edita pagos en la tabla
                      interna (conciliación).
                    </p>
                  </div>
                )}

                {requiereLinkComprobante && (
                  <div className="rounded border border-sky-100 bg-sky-50/90 px-3 py-2 text-xs text-sky-950">
                    <p>
                      <strong>Revisión manual:</strong> el comprobante es una
                      imagen obligatoria. No puede repetirse la misma
                      combinación comprobante + código; use el campo «Código»
                      para distinguir pagos con el mismo texto de referencia
                      bancaria. La huella funcional sigue evitando el mismo pago
                      (crédito, fecha, monto y ref. normalizada).
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
                    Este pago ya está conciliado o pagado. El comprobante y el
                    código se muestran solo para consulta y no se pueden
                    modificar.
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
                        inputMode="text"
                        autoComplete="off"
                        value={formData.cedula_cliente}
                        onChange={e => {
                          // Tolerar `3.14.552`, `V-12.345.678`, espacios, NBSP, etc.: dejar solo V/E/G/J + dígitos.
                          const limpia = extraerCaracteresCedulaPublica(
                            e.target.value
                          )
                          setFormData({
                            ...formData,
                            cedula_cliente: limpia,
                            prestamo_id: null,
                          })
                        }}
                        onBlur={() => {
                          // Al desfocar: si hay 6-11 dígitos sin letra inicial, anteponer V
                          // (búsqueda exacta contra `clientes.cedula` formato V########).
                          const limpia = extraerCaracteresCedulaPublica(
                            formData.cedula_cliente || ''
                          )
                          if (!limpia) return
                          const norm = normalizarCedulaParaProcesar(limpia)
                          if (
                            norm.valido &&
                            norm.valorParaEnviar &&
                            norm.valorParaEnviar !== formData.cedula_cliente
                          ) {
                            setFormData(prev => ({
                              ...prev,
                              cedula_cliente: norm.valorParaEnviar!,
                            }))
                          }
                        }}
                        className={`pl-10 ${errors.cedula_cliente ? 'border-red-500' : ''}`}
                        placeholder="V12345678 (acepta 3.14.552, V-12.345.678…)"
                      />
                    </div>

                    {errors.cedula_cliente && (
                      <p className="text-sm text-red-600">
                        {errors.cedula_cliente}
                      </p>
                    )}

                    {isLoadingPrestamos &&
                      formData.cedula_cliente.length >= 2 && (
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
                          {prestamosParaSelect.length !== 1 ? 's' : ''} en la
                          lista
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
                        Hay {prestamosParaSelect.length} créditos en la lista.
                        Debe elegir en el desplegable a cuál aplica este pago.
                      </p>
                    )}

                    {prestamosParaSelect.length > 0 ? (
                      <Select
                        value={
                          formData.prestamo_id != null &&
                          Number(formData.prestamo_id) > 0 &&
                          (prestamosParaSelect.some(
                            p => p.id === formData.prestamo_id
                          ) ||
                            prestamoSeleccionado?.id === formData.prestamo_id)
                            ? String(formData.prestamo_id)
                            : 'none'
                        }
                        onValueChange={value =>
                          setFormData({
                            ...formData,
                            prestamo_id:
                              value === 'none'
                                ? null
                                : parseInt(value, 10),
                          })
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
                          <SelectItem value="none">
                            — Seleccione el crédito —
                          </SelectItem>
                          {prestamosParaSelect.map(prestamo => {
                            const modelo =
                              (prestamo as any).modelo_vehiculo ||
                              (prestamo as any).modelo ||
                              prestamo.producto ||
                              ''

                            const concesionario =
                              (prestamo as any).concesionario || ''

                            const desc =
                              [modelo, concesionario]
                                .filter(Boolean)
                                .join(' · ') || prestamo.estado

                            return (
                              <SelectItem
                                key={prestamo.id}
                                value={prestamo.id.toString()}
                              >
                                ID {prestamo.id} - {desc} - $
                                {Number(
                                  prestamo.total_financiamiento ?? 0
                                ).toFixed(2)}
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
                            cedulasMismaPersonaParaPrestamo(
                              formData.cedula_cliente,
                              prestamoSeleccionado.cedula || ''
                            )
                              ? 'border border-green-200 bg-green-50 text-green-700'
                              : 'border border-red-200 bg-red-50 text-red-700'
                          }`}
                        >
                          {cedulasMismaPersonaParaPrestamo(
                            formData.cedula_cliente,
                            prestamoSeleccionado.cedula || ''
                          ) ? (
                            <CheckCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                          ) : (
                            <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                          )}

                          <div>
                            {cedulasMismaPersonaParaPrestamo(
                              formData.cedula_cliente,
                              prestamoSeleccionado.cedula || ''
                            ) ? (
                              <span className="font-medium">
                                Cédulas coinciden
                              </span>
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
                          setFormData({
                            ...formData,
                            fecha_pago: e.target.value,
                          })
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
                                  Se aplicará a las cuotas más antiguas primero
                                  (por fecha de vencimiento)
                                </li>

                                <li>
                                  Se distribuirá proporcionalmente entre capital
                                  e interés
                                </li>

                                {formData.monto_pagado >= 500 && (
                                  <li>
                                    Si el monto cubre una cuota completa y
                                    sobra, el exceso se aplicará a la siguiente
                                    cuota
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
                  <label className="text-sm font-medium text-gray-700">
                    Banco
                  </label>

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
                      Número de Documento{' '}
                      <span className="text-red-500">*</span>
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
                            const raw = String(
                              prev.numero_documento ?? ''
                            ).trim()
                            const n =
                              normalizarNumeroDocumento(
                                prev.numero_documento
                              ) || raw
                            const msg =
                              mensajeEdicionManualSufijoVistoProhibida(raw, n)
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

                    {mostrarCampoCodigoDocumento ? (
                      <div className="space-y-2">
                        <div
                          className="rounded border border-slate-200 bg-slate-50 px-2.5 py-2 text-xs leading-snug text-slate-800"
                          role="status"
                          aria-live="polite"
                        >
                          {!debouncedNumeroDoc.trim() ? (
                            <span className="text-slate-600">
                              Indique el número de documento para verificar si
                              ya existe en cartera.
                            </span>
                          ) : conflictoDocError ? (
                            <span className="text-red-600">
                              No se pudo verificar duplicados. Intente de nuevo.
                            </span>
                          ) : conflictoDocPendiente ? (
                            <span className="text-slate-500">
                              Consultando unicidad en cartera…
                            </span>
                          ) : conflictoDocApi?.conflicto ? (
                            <span>
                              <span className="font-semibold text-amber-900">
                                Documento ya registrado
                              </span>
                              {conflictoDocApi.prestamo_id != null ? (
                                <>
                                  : en préstamo{' '}
                                  <span className="font-mono font-semibold">
                                    #{conflictoDocApi.prestamo_id}
                                  </span>
                                </>
                              ) : (
                                ': en otro pago de cartera'
                              )}
                              {conflictoDocApi.pago_id != null ? (
                                <>
                                  {' '}
                                  (pago ID{' '}
                                  <span className="font-mono">
                                    {conflictoDocApi.pago_id}
                                  </span>
                                  )
                                </>
                              ) : null}
                              . Se pretende aplicar este pago al préstamo{' '}
                              <span className="font-mono font-semibold">
                                {formData.prestamo_id != null
                                  ? `#${formData.prestamo_id}`
                                  : '- (sin préstamo)'}
                              </span>
                              .
                            </span>
                          ) : (
                            <span>
                              {excludeIdConflicto ? (
                                <>
                                  <span className="font-semibold text-green-800">
                                    Este pago ya está registrado en cartera
                                  </span>
                                  {pagoId != null ? (
                                    <>
                                      {' '}
                                      (pago ID{' '}
                                      <span className="font-mono">
                                        {pagoId}
                                      </span>
                                      ).
                                    </>
                                  ) : (
                                    '.'
                                  )}{' '}
                                  No hay <strong>otro</strong> pago distinto
                                  con este mismo Nº de documento.
                                </>
                              ) : (
                                <>
                                  <span className="font-semibold text-green-800">
                                    NO REPETIDO
                                  </span>
                                  {' - no hay ningún pago en cartera con este Nº documento.'}
                                </>
                              )}{' '}
                              Préstamo destino en este formulario:{' '}
                              <span className="font-mono font-semibold">
                                {formData.prestamo_id != null
                                  ? `#${formData.prestamo_id}`
                                  : '- (sin préstamo)'}
                              </span>
                              .
                              {conflictoDocApi?.clave_buscada ? (
                                <>
                                  <br />
                                  <span className="text-[11px] text-slate-500">
                                    Buscado en BD (
                                    <code className="font-mono">
                                      pagos.numero_documento
                                    </code>
                                    ):{' '}
                                  </span>
                                  <code className="break-all font-mono text-[11px] text-slate-700">
                                    {conflictoDocApi.clave_buscada}
                                  </code>
                                </>
                              ) : null}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-600">
                          {excludeIdConflicto
                            ? 'Este Nº de documento ya está guardado para este pago. La validación solo busca duplicados contra OTROS pagos.'
                            : 'Cada número de documento es único en cartera. Si este comprobante ya existe en otro pago, use Visto para asignar un código (sufijo); sin código distinto no se puede duplicar.'}
                        </p>
                      </div>
                    ) : null}
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
                        No se puede teclear aquí. El token (formato A#### /
                        P####) lo genera y guarda el sistema al pulsar{' '}
                        <strong>Visto</strong> (mismo criterio que en carga
                        masiva).
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
                      <span className="font-medium">Revisión manual:</span>{' '}
                      Visto pone el código y guarda.
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
                        disabled={
                          isSubmitting || bloquearCambioComprobanteCodigo
                        }
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
                    guardar; en edicion puede conservar el comprobante ya
                    cargado o subir uno nuevo.
                  </p>
                  {isEditing ? (
                    <p className="hidden text-xs text-slate-600 lg:block">
                      Vista ampliada del comprobante a la derecha para verificar
                      sin desplazar el formulario.
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
                        disabled={
                          isSubmitting || bloquearCambioComprobanteCodigo
                        }
                        className="text-red-600 hover:text-red-700"
                        onClick={() => setArchivoComprobante(null)}
                      >
                        Quitar imagen nueva
                      </Button>
                    ) : null}
                  </div>

                  {bloquearCambioComprobanteCodigo ? (
                    <p className="text-xs text-amber-700">
                      Comprobante bloqueado: este pago ya está
                      conciliado/pagado.
                    </p>
                  ) : null}

                  {archivoComprobante ? (
                    <div className="space-y-2" role="status">
                      <p className="rounded border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-900">
                        Imagen nueva lista. Se subirá al guardar el pago.
                      </p>
                      {objUrlVistaArchivoNuevo ? (
                        <div className="flex flex-wrap items-end gap-3 lg:hidden">
                          <VistaEmbebidaComprobante
                            src={objUrlVistaArchivoNuevo}
                            kind={
                              archivoNuevoComprobanteEsPdf ? 'pdf' : 'image'
                            }
                            classNameImg="max-h-64 max-w-full rounded border border-gray-200 object-contain"
                            classNamePdf="h-64 w-full rounded border border-gray-200"
                          />
                        </div>
                      ) : null}
                    </div>
                  ) : null}

                  {isEditing &&
                  linkComprobanteParaVista &&
                  !archivoComprobante ? (
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
                          No se pudo cargar la imagen. Compruebe su sesión o
                          abra el comprobante en una pestaña nueva.
                        </p>
                      ) : null}
                      {vistaPreviaComprobante.src ? (
                        <div className="flex flex-wrap items-end gap-3 lg:hidden">
                          <VistaEmbebidaComprobante
                            src={vistaPreviaComprobante.src}
                            kind={vistaPreviaComprobante.kind}
                            classNameImg="max-h-64 max-w-full rounded border border-gray-200 bg-white object-contain"
                            classNamePdf="h-64 w-full rounded border border-gray-200 bg-white"
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
                            Comprobante guardado sin vista previa embebida.
                            Puede abrirlo para revisarlo.
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
                                  toast.error(
                                    'No se pudo abrir el comprobante.'
                                  )
                                }
                              })()
                            }}
                          >
                            <Eye className="h-4 w-4" aria-hidden />
                            Abrir comprobante
                          </Button>
                        </div>
                      ) : null}
                      <div className="mt-2 space-y-2 border-t border-slate-200 pt-2 text-xs text-slate-700">
                        <p>
                          <span className="font-medium text-slate-900">
                            Préstamo donde ya está este Nº documento (cartera):
                          </span>{' '}
                          {conflictoDocError ? (
                            <span className="text-red-600">
                              No se pudo verificar duplicados. Intente de nuevo.
                            </span>
                          ) : !debouncedNumeroDoc ? (
                            <span className="text-slate-600">
                              Indique el número de documento del comprobante
                              para comparar con la cartera.
                            </span>
                          ) : conflictoDocPendiente &&
                            (!mismoDocQueInicial ||
                              !pagoInicial?.duplicado_documento_en_pagos) ? (
                            <span className="text-slate-500">Consultando…</span>
                          ) : conflictoDocPendiente &&
                            mismoDocQueInicial &&
                            pagoInicial?.duplicado_documento_en_pagos ? (
                            <>
                              <span>
                                {etiquetaPrestamoLinea(
                                  pagoInicial.duplicado_en_cartera_prestamo_id,
                                  prestamoConflictoDetalle
                                )}
                              </span>
                              {pagoInicial.duplicado_en_cartera_pago_id !=
                              null ? (
                                <span className="text-slate-500">
                                  {' '}
                                  (pago ID{' '}
                                  {pagoInicial.duplicado_en_cartera_pago_id})
                                </span>
                              ) : null}
                              <span className="text-slate-500">
                                {' '}
                                · Verificando…
                              </span>
                            </>
                          ) : conflictoDocApi?.conflicto ? (
                            <>
                              {etiquetaPrestamoLinea(
                                conflictoDocApi.prestamo_id,
                                prestamoConflictoDetalle
                              )}
                              {conflictoDocApi.pago_id != null ? (
                                <span className="text-slate-500">
                                  {' '}
                                  (pago ID {conflictoDocApi.pago_id})
                                </span>
                              ) : null}
                            </>
                          ) : (
                            <span className="text-slate-600">
                              No hay otro pago en cartera con este mismo Nº
                              documento.
                            </span>
                          )}
                        </p>
                        <p>
                          <span className="font-medium text-slate-900">
                            Préstamo al que se aplicará este pago (formulario):
                          </span>{' '}
                          {etiquetaPrestamoLinea(
                            formData.prestamo_id,
                            prestamoSeleccionado
                          )}
                        </p>
                      </div>
                      <p className="text-xs text-slate-600">
                        Suba otra imagen solo si desea reemplazar el
                        comprobante.
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
                      setFormData({
                        ...formData,
                        notas: e.target.value || null,
                      })
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
                        <strong>Guardar y Procesar</strong> actualizará el pago
                        en la base de datos y aplicará las reglas de negocio
                        (conciliación y aplicación a cuotas) automáticamente.
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {isEditing ? (
                <aside
                  className="hidden max-h-[42vh] min-h-[11rem] flex-shrink-0 flex-col gap-2 border-t border-slate-200 bg-slate-50/95 p-4 lg:flex lg:max-h-none lg:min-h-0 lg:w-1/2 lg:max-w-[50%] lg:border-l lg:border-t-0"
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
                      onClick={() =>
                        void handleReescanearDesdeComprobanteActual()
                      }
                    >
                      {isRescanning ? 'Escaneando...' : 'Escanear'}
                    </Button>
                  </div>
                  <div className="flex min-h-0 flex-1 flex-col overflow-y-auto rounded-md border border-slate-200 bg-white p-2">
                    {archivoComprobante && objUrlVistaArchivoNuevo ? (
                      <VistaEmbebidaComprobante
                        src={objUrlVistaArchivoNuevo}
                        kind={archivoNuevoComprobanteEsPdf ? 'pdf' : 'image'}
                        classNameImg="mx-auto max-h-[min(68vh,34rem)] w-full max-w-full object-contain"
                        classNamePdf="mx-auto h-[min(68vh,34rem)] min-h-[24rem] w-full max-w-full rounded border border-slate-100"
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
                            <VistaEmbebidaComprobante
                              src={vistaPreviaComprobante.src}
                              kind={vistaPreviaComprobante.kind}
                              classNameImg="mx-auto max-h-[min(68vh,34rem)] w-full max-w-full rounded border border-slate-100 object-contain"
                              classNamePdf="mx-auto h-[min(68vh,34rem)] min-h-[24rem] w-full max-w-full rounded border border-slate-100"
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
                            <p>
                              Comprobante guardado sin vista previa embebida.
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
                                    toast.error(
                                      'No se pudo abrir el comprobante.'
                                    )
                                  }
                                })()
                              }}
                            >
                              <Eye className="h-4 w-4" aria-hidden />
                              Abrir comprobante
                            </Button>
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      <p className="self-center px-2 text-center text-sm text-slate-600">
                        Use &quot;Elegir imagen&quot; para ver la vista previa,
                        o conserve el comprobante ya guardado para mostrarlo
                        aquí.
                      </p>
                    )}
                  </div>
                </aside>
              ) : null}
            </div>

            <div className="flex shrink-0 flex-wrap items-center justify-end gap-3 border-t bg-white px-6 py-4">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={isSubmitting || isDeleting}
              >
                Cancelar
              </Button>

              {isEditing && pagoId ? (
                <Button
                  type="button"
                  variant="outline"
                  className="border-red-300 text-red-700 hover:bg-red-50"
                  onClick={() => void handleEliminarPago()}
                  disabled={isSubmitting || isDeleting}
                >
                  {isDeleting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Eliminando...
                    </>
                  ) : (
                    <>
                      <Trash2 className="mr-2 h-4 w-4" aria-hidden />
                      Eliminar
                    </>
                  )}
                </Button>
              ) : null}

              <Button type="submit" disabled={isSubmitting || isDeleting}>
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
