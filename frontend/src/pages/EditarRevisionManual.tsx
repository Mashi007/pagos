import {
  useState,
  useLayoutEffect,
  useRef,
  useEffect,
  useCallback,
  useMemo,
  type ChangeEvent,
} from 'react'

import { flushSync } from 'react-dom'

import { useParams, useNavigate, useLocation, Link } from 'react-router-dom'

import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'

import { motion } from 'framer-motion'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { Badge } from '../components/ui/badge'

import { Button } from '../components/ui/button'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'

import {
  Loader2,
  Save,
  X,
  ChevronLeft,
  Check,
  AlertTriangle,
  User,
  CreditCard,
  Phone,
  Mail,
  MapPin,
  Calendar,
  Briefcase,
  FileText,
  DollarSign,
  RefreshCw,
  Plus,
  Edit,
  Eye,
  Trash2,
  BarChart3,
  CheckSquare,
  Upload,
} from 'lucide-react'

import { Input } from '../components/ui/input'

import { Textarea } from '../components/ui/textarea'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'

import { toast } from 'sonner'

import { formatDate } from '../utils'

import { revisionManualService } from '../services/revisionManualService'

import {
  pagoService,
  type Pago,
  type PagoCreate,
  type PagoInicialRegistrar,
} from '../services/pagoService'

import { RegistrarPagoForm } from '../components/pagos/RegistrarPagoForm'
import { ConciliarCarteraRevisionManualButton } from '../components/pagos/ConciliarCarteraRevisionManualButton'
import {
  ConciliarCarteraPagosProgreso,
  type ConciliarCarteraFaseTabla,
} from '../components/pagos/ConciliarCarteraPagosProgreso'
import type { ConciliarCarteraRevisionResponse } from '../services/revisionManualService'

import { prestamoService } from '../services/prestamoService'

import {
  invalidateListasNotificacionesMora,
  invalidatePagosPrestamosRevisionYCuotas,
  PAGOS_RQ_BROADCAST_CHANNEL,
} from '../constants/queryKeys'

import {
  esReturnToRevisionDesdeNotificaciones,
  leerYConsumirReturnRevisionSesion,
  limpiarReturnRevisionSesion,
  normalizarReturnToRevisionPath,
  RUTA_RETORNO_FINIQUITOS_GESTION,
} from '../constants/revisionNavigation'

import { useEstadosCliente } from '../hooks/useEstadosCliente'

import { useDebounce } from '../hooks/useDebounce'

import { usePermissions } from '../hooks/usePermissions'

import { useConcesionariosActivos } from '../hooks/useConcesionarios'

import { useAnalistasActivos } from '../hooks/useAnalistas'

import { useModelosVehiculosActivos } from '../hooks/useModelosVehiculos'

import { codigoEstadoCuotaParaUi } from '../utils/cuotaEstadoDisplay'

import { getErrorMessage, isAxiosError } from '../types/errors'

import {
  claveDocumentoPagoListaNormalizada,
  textoDocumentoPagoParaListado,
} from '../utils/pagoExcelValidation'

import {
  abrirStaffComprobanteDesdeHref,
  blobComprobanteAFileParaEscaneo,
  esUrlComprobanteImagenConAuth,
} from '../utils/comprobanteImagenAuth'

import {
  validarEmailRevisionLocal,
  validarTelefonoVenezuelaRevisionLocal,
  mensajeValidacionCampoLocal,
} from '../utils/validadoresCampoLocal'

import {
  escanerInfopagosExtraerComprobante,
  COBROS_ESCANER_EXTRAER_REESCANEO_TIMEOUT_MS,
} from '../services/cobrosService'

import { normalizarComprobanteArchivoParaEscaneo } from '../utils/normalizarComprobanteArchivo'
import {
  buildFormDataEscanerComprobante,
  mensajeFalloExtraccionEscaner,
} from '../utils/escanerComprobanteInfopagos'

import {
  CUOTAS_REVISION_PUT_CONCURRENCY,
  COHERENCIA_USD_TOL,
  PER_PAGE_PAGOS_REGISTRADOS,
  RUTA_LISTA_PRESTAMOS,
  descripcionDiagnosticoCascada,
  ejecutarEnLotes,
  firmaSoloCliente,
  firmaSoloCuotas,
  firmaSoloPrestamo,
  buildPrestamoPatchGuardarRevision,
  mergeCuotasParaMostrar,
  opcionesSelectCuotaRevision,
  opcionesSelectEstadoPrestamoRevision,
  pagoInicialDesdeSugerenciaEscaneoRevision,
  cedulaPartesReescaneoCartera,
  partesCedulaParaEscaneoRevision,
  pagoRowAPagoCreateInicial,
  timestampOrdenFechaPago,
  type ClienteData,
  type CuotaData,
  type EstadoValidadorCierreContacto,
  type FirmaCargaRevision,
  type PrestamoData,
} from './revisionManual/EditarRevisionManual.helpers'
import { reescanearComprobantesCarteraPrestamo } from './revisionManual/reescanearComprobantesCarteraRevision'
import { ClienteRevisionCard } from './revisionManual/ClienteRevisionCard'
import { PrestamoRevisionCard } from './revisionManual/PrestamoRevisionCard'
import { PagosRegistradosRevisionSection } from './revisionManual/PagosRegistradosRevisionSection'

export function EditarRevisionManual() {
  const { prestamoId } = useParams()

  const navigate = useNavigate()

  const location = useLocation()

  const returnToRevision = useMemo(() => {
    const normReturnState = normalizarReturnToRevisionPath(
      (location.state as { returnTo?: unknown } | null)?.returnTo
    )
    if (
      normReturnState &&
      esReturnToRevisionDesdeNotificaciones(normReturnState)
    ) {
      limpiarReturnRevisionSesion()
      return normReturnState
    }
    return leerYConsumirReturnRevisionSesion()
  }, [location.key, location.state])

  const queryClient = useQueryClient()

  const vieneDesdeFiniquitos =
    returnToRevision === RUTA_RETORNO_FINIQUITOS_GESTION ||
    Boolean(returnToRevision?.startsWith(`${RUTA_RETORNO_FINIQUITOS_GESTION}?`))

  const irAListaPrestamos = () => {
    const scrollPosition = window.scrollY
    sessionStorage.setItem('prestamoScrollPosition', scrollPosition.toString())
    navigate(RUTA_LISTA_PRESTAMOS, { state: { focusPrestamosSearch: true } })
    setTimeout(() => {
      const savedPosition = sessionStorage.getItem('prestamoScrollPosition')
      if (savedPosition) {
        window.scrollTo(0, parseInt(savedPosition, 10))
        sessionStorage.removeItem('prestamoScrollPosition')
      }
    }, 100)
  }

  /** Tras guardar/cerrar/rechazo: vuelve a la pantalla de origen si vino con `state.returnTo`. */
  const navegarTrasGuardarRevision = () => {
    if (returnToRevision) {
      navigate(returnToRevision, { replace: true })
      return
    }
    irAListaPrestamos()
  }

  /** Cerrar sin finalizar: misma regla que lista, salvo que sin `returnTo` va a la cola de revisión. */
  const navegarTrasCerrarRevision = () => {
    if (returnToRevision) {
      navigate(returnToRevision, { replace: true })
      return
    }
    navigate('/revision-manual')
  }

  const [clienteData, setClienteData] = useState<Partial<ClienteData>>({})

  const [prestamoData, setPrestamoData] = useState<Partial<PrestamoData>>({})

  const [cuotasData, setCuotasData] = useState<Partial<CuotaData>[]>([])

  const [guardandoParcial, setGuardandoParcial] = useState(false)

  const [guardandoFinal, setGuardandoFinal] = useState(false)

  const [recalculandoFechasCuotas, setRecalculandoFechasCuotas] =
    useState(false)

  const [showRechazarModal, setShowRechazarModal] = useState(false)

  const [motivoRechazo, setMotivoRechazo] = useState('')

  const [guardandoRechazo, setGuardandoRechazo] = useState(false)

  const [pagePagosRegistrados, setPagePagosRegistrados] = useState(1)

  const [pagoModalAbierto, setPagoModalAbierto] = useState(false)

  const [pagoModalId, setPagoModalId] = useState<number | undefined>(undefined)

  const [pagoModalInicial, setPagoModalInicial] = useState<
    PagoInicialRegistrar | undefined
  >(undefined)

  const [pagoModalComprobanteInicial, setPagoModalComprobanteInicial] =
    useState<File | null>(null)

  const [pagoModalConciliadoPagado, setPagoModalConciliadoPagado] =
    useState(false)

  const [
    escaneandoComprobanteAgregarPago,
    setEscaneandoComprobanteAgregarPago,
  ] = useState(false)

  const [reescaneandoCartera, setReescaneandoCartera] = useState(false)
  const [reescaneoCarteraProgreso, setReescaneoCarteraProgreso] = useState<{
    hecho: number
    total: number
    fase: 'ocr' | 'cascada'
  } | null>(null)
  const [alertasReescaneoPorPagoId, setAlertasReescaneoPorPagoId] = useState<
    Record<number, string[]>
  >({})

  const escaneoComprobanteAgregarPagoRef = useRef<HTMLInputElement>(null)

  const [eliminandoPagoId, setEliminandoPagoId] = useState<number | null>(null)

  /** Progreso visible en tabla «Pagos registrados» durante Conciliar */
  const [conciliarTablaUi, setConciliarTablaUi] = useState<{
    fase: ConciliarCarteraFaseTabla
    pagosAntes: number
    idsAnteriores?: number[]
    idsRecreados?: number[]
    ocrOk?: number
    ocrTotal?: number
  } | null>(null)
  const pagosRegistradosCardRef = useRef<HTMLDivElement>(null)
  const conciliarListoTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  )

  /** Fecha de aprobación original cargada desde BD - para detectar si cambió */
  const [fechaAprobacionOriginal, setFechaAprobacionOriginal] = useState<
    string | null
  >(null)

  /** Confirmación pendiente de recálculo: 'parcial' | 'final' | null */
  const [pendingGuardarTipo, setPendingGuardarTipo] = useState<
    'parcial' | 'final' | null
  >(null)

  const [cambios, setCambios] = useState({
    cliente: false,
    prestamo: false,
    cuotas: false,
  })

  /**
   * Pagos, cascada, conciliación o recálculo de vencimientos ya persistidos en BD pero
   * aún no «reconocidos» con Guardar / Guardar y cerrar (sincroniza línea base y aviso al salir).
   */
  const [revisionOperativaSucia, setRevisionOperativaSucia] = useState(false)

  const [errores, setErrores] = useState<Record<string, string>>({})

  const telefonoDebouncCierre = useDebounce(clienteData.telefono ?? '', 400)

  const emailDebouncCierre = useDebounce(clienteData.email ?? '', 400)

  const [telValidadorCierre, setTelValidadorCierre] =
    useState<EstadoValidadorCierreContacto>({ listo: true, validando: false })

  const [emailValidadorCierre, setEmailValidadorCierre] =
    useState<EstadoValidadorCierreContacto>({ listo: true, validando: false })

  useEffect(() => {
    const raw = telefonoDebouncCierre.trim()
    if (!raw) {
      setTelValidadorCierre({ listo: true, validando: false })
      return
    }
    const v = validarTelefonoVenezuelaRevisionLocal(raw)
    setTelValidadorCierre({
      listo: v.valido,
      validando: false,
      mensaje: v.valido ? undefined : mensajeValidacionCampoLocal(v),
    })
  }, [telefonoDebouncCierre])

  useEffect(() => {
    const raw = emailDebouncCierre.trim()
    if (!raw) {
      setEmailValidadorCierre({ listo: true, validando: false })
      return
    }
    const v = validarEmailRevisionLocal(raw)
    setEmailValidadorCierre({
      listo: v.valido,
      validando: false,
      mensaje: v.valido ? undefined : mensajeValidacionCampoLocal(v),
    })
  }, [emailDebouncCierre])

  const bloqueoGuardarYCerrarPorContacto = useMemo(() => {
    // Solo bloquear cuando el servidor respondió «inválido»; no durante validación en curso
    // ni por timeout de red (listo=true en ese caso). handleGuardarYCerrar revalida al pulsar.
    if (!telValidadorCierre.validando && !telValidadorCierre.listo) {
      return {
        bloqueado: true,
        motivo:
          telValidadorCierre.mensaje ||
          'El teléfono no cumple los validadores. Use «Guardar cambios» para seguir corrigiendo; «Guardar y cerrar» se habilitará cuando sea válido.',
      }
    }
    if (!emailValidadorCierre.validando && !emailValidadorCierre.listo) {
      return {
        bloqueado: true,
        motivo:
          emailValidadorCierre.mensaje ||
          'El correo no cumple los validadores. Use «Guardar cambios» para seguir corrigiendo; «Guardar y cerrar» se habilitará cuando sea válido.',
      }
    }
    return {
      bloqueado: false as const,
      motivo: undefined as string | undefined,
    }
  }, [telValidadorCierre, emailValidadorCierre])

  /**
   * Si el queryFn del detalle vuelve a correr (refetch al enfocar ventana, invalidación,
   * etc.) y aquí sigue true, NO se sincroniza cliente/préstamo/cuotas desde el servidor
   * para no pisar lo que el usuario está editando (típico: fecha de aprobación).
   */
  const formDirtyRef = useRef(false)

  /** Firma del detalle servida por API (sin depender de flags cambios.* en cada campo). */
  const firmaCargaInicialRef = useRef<FirmaCargaRevision | null>(null)

  useLayoutEffect(() => {
    formDirtyRef.current =
      cambios.cliente ||
      cambios.prestamo ||
      cambios.cuotas ||
      revisionOperativaSucia
  }, [
    cambios.cliente,
    cambios.prestamo,
    cambios.cuotas,
    revisionOperativaSucia,
  ])

  const validarFormulario = (): boolean => {
    const e: Record<string, string> = {}

    // --- Cliente ---
    // nombres: solo validar si el usuario lo borró explícitamente (hay cambios en cliente y quedó vacío)
    if (
      cambios.cliente &&
      clienteData.nombres !== undefined &&
      !clienteData.nombres?.trim()
    ) {
      e['nombres'] = 'El nombre no puede quedar vacío'
    }
    const telSinPrefijo = (clienteData.telefono || '')
      .replace(/^\+?58/, '')
      .replace(/\D/g, '')
    if (
      clienteData.telefono &&
      (telSinPrefijo.length < 7 || telSinPrefijo.length > 11)
    ) {
      e['telefono'] = 'Teléfono inválido (7-11 dígitos después del +58)'
    }
    if (
      clienteData.email &&
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(clienteData.email)
    ) {
      e['email'] = 'Email inválido'
    }
    if (clienteData.fecha_nacimiento) {
      const fn = new Date(clienteData.fecha_nacimiento)
      const hoy = new Date()
      const edad = hoy.getFullYear() - fn.getFullYear()
      if (isNaN(fn.getTime())) {
        e['fecha_nacimiento'] = 'Fecha inválida'
      } else if (edad < 18 || edad > 100) {
        e['fecha_nacimiento'] = 'La edad debe estar entre 18 y 100 años'
      }
    }

    // --- Préstamo ---
    if (
      prestamoData.total_financiamiento !== undefined &&
      prestamoData.total_financiamiento <= 0
    ) {
      e['total_financiamiento'] = 'Debe ser mayor a 0'
    }
    if (
      prestamoData.cuota_periodo !== undefined &&
      prestamoData.cuota_periodo < 0
    ) {
      e['cuota_periodo'] = 'No puede ser negativo'
    }
    if (
      prestamoData.numero_cuotas !== undefined &&
      (prestamoData.numero_cuotas < 1 ||
        !Number.isInteger(prestamoData.numero_cuotas))
    ) {
      e['numero_cuotas'] = 'Debe ser un entero mayor a 0'
    }

    const estadoPr = (prestamoData.estado || '').toString().trim().toUpperCase()
    const exigeFechaAprobacionManual =
      estadoPr === 'APROBADO' ||
      estadoPr === 'DESEMBOLSADO' ||
      estadoPr === 'LIQUIDADO'

    let faYmd = ''
    const faRaw = prestamoData.fecha_aprobacion
    if (faRaw != null && faRaw !== '') {
      if (typeof faRaw === 'string' && faRaw.length >= 10) {
        faYmd = faRaw.slice(0, 10)
      } else {
        const d = new Date(faRaw as string | number | Date)
        if (!isNaN(d.getTime())) faYmd = d.toISOString().split('T')[0]
      }
    }
    if (exigeFechaAprobacionManual && !faYmd.trim()) {
      e['fecha_aprobacion'] =
        'La fecha de aprobación es obligatoria (ingreso manual). Sin ella no se guardan cambios ni se puede cerrar la revisión.'
    }
    if (faYmd) {
      const fa = new Date(faYmd)
      if (isNaN(fa.getTime())) {
        e['fecha_aprobacion'] = 'Fecha inválida'
      }
    }

    setErrores(e)
    return Object.keys(e).length === 0
  }

  /**
   * Tras cualquier persistencia en revisión manual: invalida cachés que leen las mismas tablas
   * de BD (pagos, cuotas, préstamos, clientes, revisión, mora, KPIs) para alinear listados y reportes.
   */
  const refrescarOrigenDatosTrasRevisionManual = useCallback(
    async (opts?: { skipRevisionEditar?: boolean }) => {
      await invalidatePagosPrestamosRevisionYCuotas(queryClient, {
        skipNotificacionesMora: true,
        includeDashboardMenu: true,
        skipRevisionEditar: opts?.skipRevisionEditar,
      })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['clientes'], exact: false }),
        queryClient.invalidateQueries({
          queryKey: ['clientes-stats'],
          exact: false,
        }),
      ])
      await invalidateListasNotificacionesMora(queryClient)
    },
    [queryClient]
  )

  const {
    data: detalleData,
    isLoading,
    error,
    refetch: refetchDetalle,
  } = useQuery({
    queryKey: ['revision-editar', prestamoId],

    queryFn: async () => {
      if (!prestamoId) throw new Error('ID de préstamo requerido')

      const pid = parseInt(prestamoId, 10)
      if (!Number.isFinite(pid) || pid <= 0) {
        throw new Error('ID de préstamo inválido')
      }

      let data = await revisionManualService.getDetallePrestamoRevision(pid)

      if (import.meta.env.DEV) {
        console.log('[EditarRevisionManual] Datos cargados del backend:', {
          prestamo: data.prestamo,
          cliente: data.cliente,
          revision: data.revision,
          cuotas:
            data.cuotas?.map((c: any) => ({
              numero_cuota: c.numero_cuota,
              monto: c.monto,
              fecha_vencimiento: c.fecha_vencimiento,
              fecha_pago: c.fecha_pago,
              total_pagado: c.total_pagado,
              estado: c.estado,
              observaciones: c.observaciones,
            })) || [],
        })
      }

      const estRev = (data.revision?.estado_revision ?? 'pendiente')
        .toString()
        .toLowerCase()

      if (estRev === 'pendiente') {
        await revisionManualService.iniciarRevision(pid)
        data = await revisionManualService.getDetallePrestamoRevision(pid)
        void refrescarOrigenDatosTrasRevisionManual({
          skipRevisionEditar: true,
        })
      }

      if (!formDirtyRef.current) {
        const fn = data.cliente?.fecha_nacimiento
        const fnNorm =
          typeof fn === 'string' && fn.length >= 10 ? fn.slice(0, 10) : fn

        setClienteData({
          ...data.cliente,
          fecha_nacimiento: fnNorm ?? null,
        })

        setPrestamoData(data.prestamo)

        const faOrig = data.prestamo?.fecha_aprobacion
        setFechaAprobacionOriginal(
          typeof faOrig === 'string' && faOrig.length >= 10
            ? faOrig.slice(0, 10)
            : null
        )

        setCuotasData(
          mergeCuotasParaMostrar(data.cuotas, data.prestamo?.numero_cuotas)
        )
      }

      return data
    },

    enabled: !!prestamoId,
    // Siempre traer datos frescos de la BD
    staleTime: 0, // Los datos están obsoletos inmediatamente
    gcTime: 0, // No cachear en el tiempo
    refetchOnMount: true, // Retraer cuando el componente se monta
    // Evita refetch al volver el foco (calendario nativo, otra pestaña): antes pisaba el formulario.
    refetchOnWindowFocus: false,
  })

  const cedulaParaPagosRealizados = (
    detalleData?.cliente?.cedula ??
    detalleData?.prestamo?.cedula ??
    ''
  )
    .toString()
    .trim()

  useEffect(() => {
    setPagePagosRegistrados(1)
  }, [cedulaParaPagosRealizados])

  const prestamoIdNumParaResumenPagos = useMemo(() => {
    const n = Number(prestamoId)
    return Number.isFinite(n) && n > 0 ? n : undefined
  }, [prestamoId])

  const {
    data: pagosRealizadosData,
    isLoading: loadingPagosRealizados,
    isFetching: fetchingPagosRealizados,
    refetch: refetchPagosRealizados,
  } = useQuery({
    queryKey: [
      'pagos-por-cedula',
      cedulaParaPagosRealizados,
      pagePagosRegistrados,
      PER_PAGE_PAGOS_REGISTRADOS,
      prestamoIdNumParaResumenPagos ?? 0,
    ],
    queryFn: () =>
      pagoService.getAllPagos(
        pagePagosRegistrados,
        PER_PAGE_PAGOS_REGISTRADOS,
        {
          cedula: cedulaParaPagosRealizados,
          prestamo_cartera: 'todos',
          ...(prestamoIdNumParaResumenPagos != null && {
            resumen_prestamo_id: prestamoIdNumParaResumenPagos,
          }),
        }
      ),
    enabled: cedulaParaPagosRealizados.length > 0,
    // 15 s: reduce GET /pagos duplicados al abrir detalle+listado; tras guardar, invalidate fuerza refetch.
    staleTime: 15_000,
    refetchOnWindowFocus: false,
    refetchInterval: 60_000,
  })

  /**
   * Otras pestañas del mismo origen no reciben invalidateQueries de React Query.
   * Tras registrar/aplicar pagos en Pagos o Notificaciones, este canal fuerza refetch del listado
   * agrupado (clave duplicado/mismo documento) sin depender solo del intervalo de 60 s.
   */
  useEffect(() => {
    if (typeof BroadcastChannel === 'undefined') return
    const ch = new BroadcastChannel(PAGOS_RQ_BROADCAST_CHANNEL)
    ch.onmessage = () => {
      void refetchPagosRealizados()
    }
    return () => {
      ch.close()
    }
  }, [refetchPagosRealizados])

  const conteoDocumentoPagosRevision = useMemo(() => {
    const m = new Map<string, number>()
    const rows = pagosRealizadosData?.pagos ?? []
    for (const p of rows) {
      const k = claveDocumentoPagoListaNormalizada(
        p.numero_documento,
        p.codigo_documento ?? null
      )
      if (!k) continue
      m.set(k, (m.get(k) || 0) + 1)
    }
    return m
  }, [pagosRealizadosData?.pagos])

  /** Tabla «Pagos registrados»: siempre por fecha de pago descendente (más cercana a hoy arriba). */
  const pagosRegistradosOrdenados = useMemo(() => {
    const pid = Number(prestamoData.prestamo_id)
    const rows = (pagosRealizadosData?.pagos ?? []).filter(p => {
      if (!Number.isFinite(pid) || pid <= 0) return true
      return Number(p.prestamo_id) === pid
    })
    return [...rows].sort((a, b) => {
      const tb = timestampOrdenFechaPago(b.fecha_pago)
      const ta = timestampOrdenFechaPago(a.fecha_pago)
      if (tb !== ta) return tb - ta
      return (b.id ?? 0) - (a.id ?? 0)
    })
  }, [pagosRealizadosData?.pagos, prestamoData.prestamo_id])

  const idsPagosPrestamoEnTabla = useCallback((): number[] => {
    const pid = Number(prestamoData.prestamo_id)
    if (!Number.isFinite(pid) || pid <= 0) return []
    return (pagosRealizadosData?.pagos ?? [])
      .filter(p => Number(p.prestamo_id) === pid)
      .map(p => Number(p.id))
      .filter(id => Number.isFinite(id) && id > 0)
  }, [pagosRealizadosData?.pagos, prestamoData.prestamo_id])

  const contarPagosPrestamoEnTabla = useCallback(
    () => idsPagosPrestamoEnTabla().length,
    [idsPagosPrestamoEnTabla]
  )

  useEffect(() => {
    return () => {
      if (conciliarListoTimeoutRef.current) {
        clearTimeout(conciliarListoTimeoutRef.current)
      }
    }
  }, [])

  const limpiarConciliarTablaUi = useCallback(() => {
    if (conciliarListoTimeoutRef.current) {
      clearTimeout(conciliarListoTimeoutRef.current)
      conciliarListoTimeoutRef.current = null
    }
    setConciliarTablaUi(null)
  }, [])

  /** Claves comprobante+código en la página actual; excluye la fila abierta en el modal de edición. */
  const claveDocumentoPagosTablaRevision = useMemo(() => {
    const s = new Set<string>()
    for (const p of pagosRegistradosOrdenados) {
      if (pagoModalId != null && p.id === pagoModalId) continue
      const k = claveDocumentoPagoListaNormalizada(
        p.numero_documento,
        p.codigo_documento ?? null
      )
      if (k) s.add(k)
    }
    return s
  }, [pagosRegistradosOrdenados, pagoModalId])

  const agregadosCuotasRevision = useMemo(() => {
    let sumMonto = 0
    let sumPagado = 0
    for (const c of cuotasData) {
      sumMonto += Number(c.monto) || 0
      sumPagado += Number(c.total_pagado) || 0
    }
    return { sumMonto, sumPagado }
  }, [cuotasData])

  const estadoPrestamoNorm = useMemo(
    () => (prestamoData.estado ?? '').toString().trim().toUpperCase(),
    [prestamoData.estado]
  )

  const auditoriaCoherenciaActiva =
    estadoPrestamoNorm === 'APROBADO' || estadoPrestamoNorm === 'LIQUIDADO'

  const estadoRevision = (detalleData?.revision?.estado_revision ?? 'pendiente')
    .toString()
    .toLowerCase()

  const { revisionManualFullEdit, isAdmin } = usePermissions()

  const soloLectura = estadoRevision === 'revisado' && !revisionManualFullEdit

  /**
   * En cuotas marcadas como pagadas al 100 %, «Pagado» debe reflejar el mismo número que «Monto»
   * de esa fila (no valores derivados de otros paneles). Útil tras cargas inconsistentes o al ajustar Monto.
   */
  const alinearPagadoAlMontoCuotasPagadas = useCallback(() => {
    if (soloLectura) return
    const estadosFull = new Set(['PAGADO', 'PAGO_ADELANTADO'])
    let cambiadas = 0
    const next = cuotasData.map(c => {
      const code = codigoEstadoCuotaParaUi(c.estado)
      if (!estadosFull.has(code)) return c
      const montoNum = Number(c.monto) || 0
      const cur = Number(c.total_pagado) || 0
      if (Math.abs(cur - montoNum) <= 1e-9) return c
      cambiadas += 1
      return { ...c, total_pagado: montoNum }
    })
    if (cambiadas === 0) {
      toast.message(
        'Sin cambios: en filas Pagado / Pago adelantado el importe Pagado ya coincide con el Monto de la misma fila.'
      )
      return
    }
    setCuotasData(next)
    setCambios(prev => ({ ...prev, cuotas: true }))
    toast.success(
      `Pagado igualado al Monto de la misma fila en ${cambiadas} cuota(s) (estados Pagado / Pago adelantado).`
    )
  }, [cuotasData, soloLectura])

  const refrescarTrasCambioPagosRevision = useCallback(async () => {
    // invalidatePagosPrestamosRevisionYCuotas ya incluye `pagos-por-cedula` → un solo refetch activo.
    await refrescarOrigenDatosTrasRevisionManual()
  }, [refrescarOrigenDatosTrasRevisionManual])

  /** Tras cascada o guardar pago: cuotas + panel de coherencia alineados con BD. */
  const sincronizarDetalleCuotasTrasOperacionPagos = useCallback(async () => {
    await refrescarTrasCambioPagosRevision()
    await refetchPagosRealizados()
    if (!prestamoId) return
    const pidNum = parseInt(prestamoId, 10)
    if (!Number.isFinite(pidNum) || pidNum <= 0) return
    try {
      const datos =
        await revisionManualService.getDetallePrestamoRevision(pidNum)
      if (datos?.prestamo) {
        setPrestamoData(datos.prestamo)
        const faG = formatDateForInput(datos.prestamo.fecha_aprobacion)
        if (faG) setFechaAprobacionOriginal(faG)
      }
      if (datos?.cuotas) {
        const mergedCuotas = mergeCuotasParaMostrar(
          datos.cuotas,
          datos.prestamo?.numero_cuotas
        )
        setCuotasData(mergedCuotas)
        setCambios(prev => ({
          ...prev,
          cuotas: false,
          prestamo: false,
        }))
        const base = firmaCargaInicialRef.current
        if (base) {
          firmaCargaInicialRef.current = {
            ...base,
            ...(datos.prestamo
              ? { prestamo: firmaSoloPrestamo(datos.prestamo) }
              : {}),
            cuotas: firmaSoloCuotas(mergedCuotas),
          }
        }
      }
    } catch (e) {
      console.error(e)
    }
  }, [prestamoId, refrescarTrasCambioPagosRevision, refetchPagosRealizados])

  /** Cascada: no exige cliente/email válidos; solo crédito y cuotas si hay que reconstruir. */
  const validarMinimoParaCascadaRevision = useCallback((): boolean => {
    const pid = Number(prestamoData.prestamo_id)
    if (!Number.isFinite(pid) || pid <= 0) {
      toast.error('No hay crédito válido para aplicar la cascada.')
      return false
    }
    const esperadas = Math.floor(Number(prestamoData.numero_cuotas) || 0)
    const persistidas = cuotasData.filter(c => c.cuota_id != null).length
    const necesitaReconstruir =
      esperadas > 0 && (persistidas === 0 || persistidas < esperadas)
    if (necesitaReconstruir) {
      const fa =
        formatDateForInput(prestamoData.fecha_aprobacion) ||
        formatDateForInput(prestamoData.fecha_base_calculo)
      if (!fa) {
        toast.error(
          'Indique fecha de aprobación (o base de cálculo) para generar las cuotas faltantes antes de la cascada.'
        )
        return false
      }
    }
    return true
  }, [prestamoData, cuotasData])

  const manejarConciliarExito = useCallback(
    async (res: ConciliarCarteraRevisionResponse) => {
      const ids =
        res.detalle
          ?.filter(d => d.ok && d.pago_id != null)
          .map(d => Number(d.pago_id)) ?? []
      setConciliarTablaUi(prev => ({
        fase: 'recargando',
        pagosAntes: prev?.pagosAntes ?? 0,
        idsAnteriores: prev?.idsAnteriores ?? [],
        idsRecreados: ids,
        ocrOk: res.ocr_ok,
        ocrTotal: res.ocr_total,
      }))
      await refrescarTrasCambioPagosRevision()
      await refetchPagosRealizados()
      setConciliarTablaUi(prev => ({
        fase: 'listo',
        pagosAntes: prev?.pagosAntes ?? 0,
        idsAnteriores: prev?.idsAnteriores ?? [],
        idsRecreados: ids,
        ocrOk: res.ocr_ok,
        ocrTotal: res.ocr_total,
      }))
      pagosRegistradosCardRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      })
      if (conciliarListoTimeoutRef.current) {
        clearTimeout(conciliarListoTimeoutRef.current)
      }
      conciliarListoTimeoutRef.current = setTimeout(() => {
        setConciliarTablaUi(null)
        conciliarListoTimeoutRef.current = null
      }, 12_000)
      setRevisionOperativaSucia(true)
    },
    [refrescarTrasCambioPagosRevision, refetchPagosRealizados]
  )

  const aplicarCascadaPagosMutation = useMutation({
    mutationFn: async () => {
      if (!validarMinimoParaCascadaRevision()) {
        throw new Error(
          'No se puede aplicar la cascada con los datos actuales.'
        )
      }
      const pid = Number(prestamoData.prestamo_id)

      const patch = buildPrestamoPatchGuardarRevision(
        prestamoData,
        formatDateForInput
      )
      const esperadas = Math.floor(Number(prestamoData.numero_cuotas) || 0)
      const persistidas = cuotasData.filter(c => c.cuota_id != null).length
      const necesitaReconstruir =
        esperadas > 0 && (persistidas === 0 || persistidas < esperadas)

      if (necesitaReconstruir) {
        await revisionManualService.guardarPrestamoYReconstruirCuotas(
          pid,
          patch
        )
      } else if (Object.keys(patch).length > 0) {
        await revisionManualService.editarPrestamo(pid, patch)
      }

      return pagoService.aplicarPagosPendientesCuotasPorPrestamo(pid)
    },
    onSuccess: async data => {
      const aplicados = Number(data.pagos_con_aplicacion ?? 0)
      const texto = data.mensaje || 'Operación completada'
      const desc =
        data.diagnostico != null
          ? descripcionDiagnosticoCascada(data.diagnostico)
          : undefined
      if (aplicados > 0) {
        toast.success(texto, desc != null ? { description: desc } : undefined)
      } else {
        toast.info(texto, desc != null ? { description: desc } : undefined)
      }
      await sincronizarDetalleCuotasTrasOperacionPagos()
      setRevisionOperativaSucia(true)
    },
    onError: (err: unknown) => {
      const msg =
        err &&
        typeof err === 'object' &&
        'message' in err &&
        typeof (err as { message: unknown }).message === 'string'
          ? (err as { message: string }).message
          : String(err)
      toast.error(msg || 'No se pudo aplicar pagos a cuotas')
    },
  })

  const eliminarPagoRevision = async (pago: Pago) => {
    if (soloLectura) return
    const doc = pago.numero_documento?.trim()
      ? pago.numero_documento
      : `#${pago.id}`
    if (
      !window.confirm(
        `Eliminar el pago ${doc} por $${Number(pago.monto_pagado || 0).toFixed(2)} USD? Esta acción no se puede deshacer.`
      )
    ) {
      return
    }
    setEliminandoPagoId(pago.id)
    try {
      await pagoService.deletePago(pago.id)
      quitarAlertaReescaneoPago(Number(pago.id))
      toast.success('Pago eliminado')
      await sincronizarDetalleCuotasTrasOperacionPagos()
      setRevisionOperativaSucia(true)
    } catch (err: unknown) {
      const msg =
        err &&
        typeof err === 'object' &&
        'message' in err &&
        typeof (err as { message: unknown }).message === 'string'
          ? (err as { message: string }).message
          : String(err)
      toast.error(msg || 'No se pudo eliminar el pago')
    } finally {
      setEliminandoPagoId(null)
    }
  }

  const pagoEstaConciliadoOPagado = (pago: Pago) =>
    Boolean(pago.conciliado) ||
    ['PAGADO', 'PAGO_ADELANTADO'].includes(
      String(pago.estado ?? '').toUpperCase()
    )

  const cerrarModalPagoRevision = () => {
    setPagoModalAbierto(false)
    setPagoModalId(undefined)
    setPagoModalInicial(undefined)
    setPagoModalComprobanteInicial(null)
    setPagoModalConciliadoPagado(false)
  }

  const quitarAlertaReescaneoPago = useCallback((pagoId: number) => {
    const id = Number(pagoId)
    if (!Number.isFinite(id) || id <= 0) return
    setAlertasReescaneoPorPagoId(prev => {
      if (!prev[id]?.length) return prev
      const { [id]: _omit, ...rest } = prev
      return rest
    })
  }, [])

  const abrirAgregarPagoRevision = () => {
    if (soloLectura) return
    const ced = cedulaParaPagosRealizados
    const pid = prestamoData.prestamo_id
    setPagoModalComprobanteInicial(null)
    setPagoModalId(undefined)
    setPagoModalInicial({
      cedula_cliente: ced,
      prestamo_id: pid != null && pid > 0 ? pid : null,
      fecha_pago: '',
      monto_pagado: 0,
      numero_documento: '',
      institucion_bancaria: null,
      notas: null,
      link_comprobante: null,
    })
    setPagoModalAbierto(true)
  }

  const abrirSelectorEscaneoComprobanteAgregarPago = () => {
    if (soloLectura || escaneandoComprobanteAgregarPago) return
    escaneoComprobanteAgregarPagoRef.current?.click()
  }

  const ejecutarReescaneoCartera = useCallback(async () => {
    if (soloLectura || reescaneandoCartera) return
    const ced = cedulaParaPagosRealizados
    const pid = Number(prestamoData.prestamo_id)
    if (!ced || !Number.isFinite(pid) || pid <= 0) {
      toast.error('Falta cédula o préstamo para re-escanear comprobantes.')
      return
    }
    setReescaneandoCartera(true)
    setReescaneoCarteraProgreso(null)
    try {
      const resultado = await reescanearComprobantesCarteraPrestamo({
        cedula: ced,
        prestamoId: pid,
        onProgreso: p => setReescaneoCarteraProgreso(p),
      })
      setAlertasReescaneoPorPagoId(resultado.alertas)

      if (resultado.escaneados === 0) {
        toast.info(
          resultado.omitidosSinImagen > 0
            ? `No hay comprobantes insertados en este préstamo (${resultado.omitidosSinImagen} pago(s) sin imagen se mantienen igual).`
            : 'No hay pagos en cartera para re-escanear.'
        )
        return
      }

      await sincronizarDetalleCuotasTrasOperacionPagos()

      setReescaneoCarteraProgreso({
        hecho: resultado.escaneados,
        total: resultado.escaneados,
        fase: 'cascada',
      })

      try {
        await aplicarCascadaPagosMutation.mutateAsync()
      } catch (cascadaErr) {
        toast.warning(
          cascadaErr instanceof Error
            ? cascadaErr.message
            : 'Re-escaneo listo; revise la cascada manualmente.'
        )
      }

      const nAlertas = Object.keys(resultado.alertas).length
      const partesMsg = [
        `${resultado.actualizados}/${resultado.escaneados} comprobante(s) actualizado(s) desde OCR.`,
        resultado.fallidosPersistencia > 0
          ? `${resultado.fallidosPersistencia} no se guardaron (revise el aviso en la fila).`
          : null,
        resultado.omitidosSinImagen > 0
          ? `${resultado.omitidosSinImagen} pago(s) sin imagen no se modificaron.`
          : null,
        nAlertas > 0 ? `${nAlertas} requieren revisión manual (⚠).` : null,
      ]
        .filter(Boolean)
        .join(' ')

      if (nAlertas > 0) {
        toast.warning(partesMsg)
      } else {
        toast.success(partesMsg)
      }
      setRevisionOperativaSucia(true)
    } catch (e) {
      toast.error(
        e instanceof Error
          ? e.message
          : 'Error al re-escanear comprobantes de cartera.'
      )
    } finally {
      setReescaneandoCartera(false)
      setReescaneoCarteraProgreso(null)
    }
  }, [
    soloLectura,
    reescaneandoCartera,
    cedulaParaPagosRealizados,
    prestamoData.prestamo_id,
    refrescarTrasCambioPagosRevision,
    refetchPagosRealizados,
    sincronizarDetalleCuotasTrasOperacionPagos,
    aplicarCascadaPagosMutation,
  ])

  const handleArchivoEscaneoComprobanteAgregarPago = async (
    event: ChangeEvent<HTMLInputElement>
  ) => {
    const input = event.target
    const fileRaw = input.files?.[0]
    input.value = ''
    if (!fileRaw || soloLectura) return

    const ced = cedulaParaPagosRealizados
    const cedulaPartes = cedulaPartesReescaneoCartera(ced, ced)
    const pid = Number(prestamoData.prestamo_id)

    setEscaneandoComprobanteAgregarPago(true)
    try {
      const archivo = await normalizarComprobanteArchivoParaEscaneo(
        await blobComprobanteAFileParaEscaneo(fileRaw, fileRaw.type)
      )
      const fd = buildFormDataEscanerComprobante({
        tipoCedula: cedulaPartes.tipo,
        numeroCedula: cedulaPartes.numero,
        comprobante: archivo,
        extraccionSinCliente: true,
        prestamoObjetivoId: pid,
      })

      const res = await escanerInfopagosExtraerComprobante(fd, {
        timeoutMs: COBROS_ESCANER_EXTRAER_REESCANEO_TIMEOUT_MS,
      })
      if (!res.ok || !res.sugerencia) {
        toast.error(mensajeFalloExtraccionEscaner(res))
        return
      }

      setPagoModalId(undefined)
      setPagoModalComprobanteInicial(archivo)
      setPagoModalInicial(
        pagoInicialDesdeSugerenciaEscaneoRevision(ced, pid, res.sugerencia, {
          duplicado_en_pagos: res.duplicado_en_pagos,
          pago_existente_id: res.pago_existente_id,
          prestamo_existente_id: res.prestamo_existente_id,
        })
      )
      setPagoModalAbierto(true)

      const aviso =
        res.validacion_campos || res.validacion_reglas
          ? ' Revise los datos sugeridos antes de guardar.'
          : ''
      toast.success(`Comprobante escaneado.${aviso}`)
    } catch (convErr) {
      toast.error(
        convErr instanceof Error
          ? convErr.message
          : 'No se pudo preparar el comprobante para escanear.'
      )
    } finally {
      setEscaneandoComprobanteAgregarPago(false)
    }
  }

  const abrirEditarPagoRevision = (pago: Pago) => {
    if (soloLectura) return
    setPagoModalComprobanteInicial(null)
    setPagoModalId(pago.id)
    setPagoModalConciliadoPagado(pagoEstaConciliadoOPagado(pago))
    setPagoModalInicial(pagoRowAPagoCreateInicial(pago))
    setPagoModalAbierto(true)
  }

  const onExitoModalPagoRevision = async (procesado?: boolean) => {
    const fueEdicion = pagoModalId != null
    const idEditado = pagoModalId
    cerrarModalPagoRevision()
    if (procesado === false) return
    toast.success(fueEdicion ? 'Pago actualizado' : 'Pago registrado')
    if (fueEdicion && idEditado != null) {
      quitarAlertaReescaneoPago(Number(idEditado))
    }
    await sincronizarDetalleCuotasTrasOperacionPagos()
    setRevisionOperativaSucia(true)
  }

  useEffect(() => {
    if (!detalleData) return
    if (formDirtyRef.current) return
    const fn = detalleData.cliente?.fecha_nacimiento
    const fnNorm =
      typeof fn === 'string' && fn.length >= 10 ? fn.slice(0, 10) : fn
    const clienteNorm = {
      ...detalleData.cliente,
      fecha_nacimiento: (fnNorm ?? null) as string | null,
    }
    firmaCargaInicialRef.current = {
      cliente: firmaSoloCliente(clienteNorm),
      prestamo: firmaSoloPrestamo(detalleData.prestamo),
      cuotas: firmaSoloCuotas(detalleData.cuotas ?? []),
    }
  }, [detalleData])

  const hayDiferenciaVsCargaInicial = (): boolean => {
    const s = firmaCargaInicialRef.current
    if (!s) return true
    return (
      firmaSoloCliente(clienteData) !== s.cliente ||
      firmaSoloPrestamo(prestamoData) !== s.prestamo ||
      firmaSoloCuotas(cuotasData) !== s.cuotas
    )
  }

  const hayCambiosPendientesRevision = (): boolean =>
    hayDiferenciaVsCargaInicial() || revisionOperativaSucia

  /**
   * Guarda en BD observaciones del préstamo y notas del cliente.
   * Se usa antes de rechazar o finalizar para no perder comentarios aunque no hubiera otros "cambios".
   */
  const persistObservacionesYNotasRevision = async () => {
    if (soloLectura || !prestamoId) return
    const pid = parseInt(prestamoId, 10)
    if (!Number.isFinite(pid)) return

    if (prestamoData.prestamo_id) {
      await revisionManualService.editarPrestamo(prestamoData.prestamo_id, {
        observaciones: String(prestamoData.observaciones ?? ''),
      })
    }
    if (clienteData.cliente_id) {
      await revisionManualService.editarCliente(
        clienteData.cliente_id,
        { notas: String(clienteData.notas ?? '') },
        { prestamoId: pid }
      )
    }
  }

  // Estados de cliente desde BD (tabla estados_cliente)

  const { opciones: opcionesBD } = useEstadosCliente({ alwaysFresh: true })

  const { data: concesionarios = [] } = useConcesionariosActivos()

  const { data: analistas = [] } = useAnalistasActivos()

  const { data: modelosVehiculos = [] } = useModelosVehiculosActivos()

  // Función helper para convertir ISO datetime a YYYY-MM-DD para input type="date"
  const formatDateForInput = (isoDate: string | null | undefined): string => {
    if (!isoDate) return ''
    if (typeof isoDate === 'string' && isoDate.length >= 10) {
      return isoDate.slice(0, 10)
    }
    return ''
  }

  /**
   * Incluye fechas en el PUT sin enviar solo fecha_base (el backend responde 400).
   * Aprobación y base de cálculo = mismo YYYY-MM-DD que el selector; el API fija fecha_registro al día anterior.
   */
  const applyFechaAprobacionAlPayload = (out: Record<string, unknown>) => {
    const faNorm = formatDateForInput(prestamoData.fecha_aprobacion)
    const fbNorm = formatDateForInput(prestamoData.fecha_base_calculo)
    if (faNorm) {
      out.fecha_aprobacion = faNorm
      out.fecha_base_calculo = faNorm
      return
    }
    if (fbNorm) {
      out.fecha_aprobacion = fbNorm
      out.fecha_base_calculo = fbNorm
    }
  }

  /**
   * Persiste en BD los datos de préstamo del formulario (incl. amortización) y reconstruye
   * la tabla de cuotas: número de filas, montos por período y fechas de vencimiento según
   * total, plazo, modalidad y fecha base; luego reaplica pagos pendientes del préstamo.
   */
  const handleGuardarFechaYRecalcularVencimientos = async () => {
    if (!prestamoId || soloLectura) {
      if (soloLectura) {
        toast.info(
          'Este préstamo está en solo lectura; no se puede modificar la fecha.'
        )
      }
      return
    }

    if (!validarFormulario()) {
      toast.error('Corrija los errores marcados en rojo antes de recalcular')
      return
    }

    const pid = prestamoData.prestamo_id ?? parseInt(prestamoId, 10)
    if (!Number.isFinite(pid)) return

    const fa =
      formatDateForInput(prestamoData.fecha_aprobacion) ||
      formatDateForInput(prestamoData.fecha_base_calculo)
    if (!fa) {
      toast.error('Indique una fecha de aprobación válida')
      return
    }

    const faDate = new Date(fa)
    if (isNaN(faDate.getTime())) {
      toast.error('Fecha de aprobación inválida')
      return
    }

    setRecalculandoFechasCuotas(true)
    try {
      const prestamoPatch = buildPrestamoPatchGuardarRevision(
        prestamoData,
        formatDateForInput
      )

      const res = await revisionManualService.guardarPrestamoYReconstruirCuotas(
        pid,
        prestamoPatch
      )
      const r = res as {
        reconstruccion_cuotas?: {
          cuotas_creadas?: number
          pagos_con_aplicacion?: number
        }
      }
      const stats = r.reconstruccion_cuotas
      const creadas = stats?.cuotas_creadas ?? '?'
      const pagosAplic = stats?.pagos_con_aplicacion ?? '?'

      const datos = await revisionManualService.getDetallePrestamoRevision(pid)
      if (datos?.prestamo) {
        setPrestamoData(datos.prestamo)
        const faGuardada = formatDateForInput(datos.prestamo.fecha_aprobacion)
        if (faGuardada) setFechaAprobacionOriginal(faGuardada)
      } else {
        setFechaAprobacionOriginal(fa)
      }
      if (datos?.cuotas) {
        setCuotasData(
          mergeCuotasParaMostrar(datos.cuotas, datos.prestamo?.numero_cuotas)
        )
      }

      toast.success(
        `Datos de préstamo guardados y tabla de cuotas reconstruida: ${creadas} cuota(s); ` +
          `pagos con nueva aplicación a cuotas: ${pagosAplic}. Los cambios quedan en la base.`
      )

      setRevisionOperativaSucia(true)

      await refrescarOrigenDatosTrasRevisionManual({ skipRevisionEditar: true })
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        'No se pudo guardar los datos del préstamo o reconstruir la tabla de cuotas'
      toast.error(msg)
      console.error(err)
    } finally {
      setRecalculandoFechasCuotas(false)
    }
  }

  const opcionesBase = (
    opcionesBD.length > 0
      ? opcionesBD
      : [
          { valor: 'ACTIVO', etiqueta: 'Activo', orden: 1 },

          { valor: 'INACTIVO', etiqueta: 'Inactivo', orden: 2 },

          { valor: 'FINALIZADO', etiqueta: 'Finalizado', orden: 3 },

          { valor: 'LEGACY', etiqueta: 'Legacy', orden: 4 },
        ]
  ).map(e => ({ value: e.valor, label: e.etiqueta }))

  // Incluir estado actual del cliente si no está en la lista (valor legacy en BD)

  const estadoActual = clienteData.estado

  const opcionesEstado =
    estadoActual && !opcionesBase.some(e => e.value === estadoActual)
      ? [
          { value: estadoActual, label: `${estadoActual} (legacy)` },
          ...opcionesBase,
        ]
      : opcionesBase

  /** Botón "Guardar Cambios": PUT a BD (cliente, préstamo incl. estado, cuotas). */
  const handleGuardarParciales = async (opts?: {
    volverAunqueNoHayaCambios?: boolean
  }) => {
    if (!prestamoId) return

    if (soloLectura) {
      toast.info(
        'Este préstamo está en solo lectura (revisión ya cerrada en el sistema).'
      )
      if (opts?.volverAunqueNoHayaCambios) {
        await refrescarOrigenDatosTrasRevisionManual()
        navegarTrasGuardarRevision()
      }

      return
    }

    if (!validarFormulario()) {
      toast.error('Corrige los errores marcados en rojo antes de guardar')
      return
    }

    // Sin cambios de formulario ni operaciones (pagos/cascada/etc.) pendientes de reconocer
    if (!hayDiferenciaVsCargaInicial() && !revisionOperativaSucia) {
      toast.info('ℹ️ No hay cambios para guardar')
      if (opts?.volverAunqueNoHayaCambios) {
        await refrescarOrigenDatosTrasRevisionManual()
        navegarTrasGuardarRevision()
      }
      return
    }

    // Confirmar si cambió la fecha de aprobación y hay cuotas
    const nuevaFechaCheck = formatDateForInput(prestamoData.fecha_aprobacion)
    const snapFecha = firmaCargaInicialRef.current
    const prestamoDistintoVsInicial =
      !snapFecha || firmaSoloPrestamo(prestamoData) !== snapFecha.prestamo
    if (
      prestamoDistintoVsInicial &&
      nuevaFechaCheck &&
      fechaAprobacionOriginal &&
      nuevaFechaCheck !== fechaAprobacionOriginal &&
      cuotasData.length > 0
    ) {
      const ok = window.confirm(
        `⚠️ CAMBIO DE FECHA DE APROBACIÓN\n\n` +
          `Fecha anterior: ${fechaAprobacionOriginal}\n` +
          `Fecha nueva:    ${nuevaFechaCheck}\n\n` +
          `Se recalcularán ÚNICAMENTE las fechas de vencimiento de las ${cuotasData.length} cuota(s) de la tabla de amortización.\n` +
          `Los montos, pagos y saldos NO cambiarán.\n\n` +
          `¿Deseas continuar?`
      )
      if (!ok) return
    }

    setGuardandoParcial(true)
    toast.info('Guardando cambios…')

    try {
      let savedSomething = false

      let errorOccurred = false

      let huboSoloSincOperativaBd = false

      const snap = firmaCargaInicialRef.current
      const needGuardarCliente =
        !!clienteData.cliente_id &&
        (!snap || firmaSoloCliente(clienteData) !== snap.cliente)
      const needGuardarPrestamo =
        !!prestamoData.prestamo_id &&
        (!snap || firmaSoloPrestamo(prestamoData) !== snap.prestamo)
      const needGuardarCuotas =
        !snap || firmaSoloCuotas(cuotasData) !== snap.cuotas

      const soloSincOperativaBd =
        revisionOperativaSucia &&
        !needGuardarCliente &&
        !needGuardarPrestamo &&
        !needGuardarCuotas

      if (soloSincOperativaBd) {
        try {
          const pidSync = parseInt(prestamoId, 10)
          if (!Number.isFinite(pidSync) || pidSync <= 0) {
            errorOccurred = true
            toast.error('ID de préstamo inválido')
          } else {
            flushSync(() => setRevisionOperativaSucia(false))
            await refetchDetalle()
            toast.success(
              'Cambios de pagos/cuotas ya están en la base; revisión sincronizada con la última información.'
            )
            savedSomething = true
            huboSoloSincOperativaBd = true
          }
        } catch (soloErr: unknown) {
          errorOccurred = true
          setRevisionOperativaSucia(true)
          toast.error(
            getErrorMessage(soloErr) ||
              'No se pudo sincronizar después de pagos o cascada'
          )
          console.error(soloErr)
        }
      } else if (needGuardarCliente) {
        const clienteUpdate: Record<string, any> = {}

        if (clienteData.nombres) clienteUpdate.nombres = clienteData.nombres

        if (clienteData.telefono) clienteUpdate.telefono = clienteData.telefono

        if (clienteData.email) clienteUpdate.email = clienteData.email

        if (clienteData.direccion)
          clienteUpdate.direccion = clienteData.direccion

        if (clienteData.ocupacion)
          clienteUpdate.ocupacion = clienteData.ocupacion

        if (clienteData.estado) clienteUpdate.estado = clienteData.estado

        if (clienteData.fecha_nacimiento !== undefined)
          clienteUpdate.fecha_nacimiento = clienteData.fecha_nacimiento || null

        clienteUpdate.notas = String(clienteData.notas ?? '')

        if (
          Object.keys(clienteUpdate).length > 0 &&
          clienteData.cliente_id != null
        ) {
          try {
            await revisionManualService.editarCliente(
              clienteData.cliente_id,
              clienteUpdate,
              { prestamoId: parseInt(prestamoId, 10) }
            )

            savedSomething = true
          } catch (err: any) {
            errorOccurred = true

            const errorMsg =
              err?.response?.data?.detail || 'Error al guardar cliente'

            toast.error(`❌ Error en cliente: ${errorMsg}`)

            console.error('Error guardando cliente:', err)
          }
        }
      }

      // Guardar préstamo si difiere de la carga inicial

      if (needGuardarPrestamo) {
        const prestamoUpdate: Record<string, any> = {}

        if (
          prestamoData.total_financiamiento !== undefined &&
          prestamoData.total_financiamiento >= 0
        )
          prestamoUpdate.total_financiamiento =
            prestamoData.total_financiamiento

        if (
          prestamoData.numero_cuotas !== undefined &&
          prestamoData.numero_cuotas >= 1
        )
          prestamoUpdate.numero_cuotas = prestamoData.numero_cuotas

        if (prestamoData.producto !== undefined)
          prestamoUpdate.producto = prestamoData.producto

        if (prestamoData.cedula !== undefined)
          prestamoUpdate.cedula = prestamoData.cedula

        if (prestamoData.nombres !== undefined)
          prestamoUpdate.nombres = prestamoData.nombres

        if (prestamoData.fecha_requerimiento !== undefined)
          prestamoUpdate.fecha_requerimiento =
            prestamoData.fecha_requerimiento || null

        if (prestamoData.modalidad_pago !== undefined)
          prestamoUpdate.modalidad_pago = prestamoData.modalidad_pago

        if (
          prestamoData.cuota_periodo !== undefined &&
          prestamoData.cuota_periodo >= 0
        )
          prestamoUpdate.cuota_periodo = prestamoData.cuota_periodo

        applyFechaAprobacionAlPayload(prestamoUpdate)

        const estadoPrestamoNormParcial = (prestamoData.estado ?? '')
          .toString()
          .trim()
          .toUpperCase()
        if (estadoPrestamoNormParcial)
          prestamoUpdate.estado = estadoPrestamoNormParcial

        if (prestamoData.concesionario !== undefined)
          prestamoUpdate.concesionario = prestamoData.concesionario

        if (prestamoData.analista !== undefined)
          prestamoUpdate.analista = prestamoData.analista

        if (prestamoData.modelo_vehiculo !== undefined)
          prestamoUpdate.modelo_vehiculo = prestamoData.modelo_vehiculo

        if (
          prestamoData.valor_activo !== undefined &&
          prestamoData.valor_activo !== null
        )
          prestamoUpdate.valor_activo = prestamoData.valor_activo

        if (prestamoData.usuario_proponente !== undefined)
          prestamoUpdate.usuario_proponente = prestamoData.usuario_proponente

        if (prestamoData.usuario_aprobador !== undefined)
          prestamoUpdate.usuario_aprobador = prestamoData.usuario_aprobador

        prestamoUpdate.observaciones = String(prestamoData.observaciones ?? '')

        if (
          Object.keys(prestamoUpdate).length > 0 &&
          prestamoData.prestamo_id != null
        ) {
          try {
            await revisionManualService.editarPrestamo(
              prestamoData.prestamo_id,
              prestamoUpdate
            )

            savedSomething = true

            // Si cambió la fecha de aprobación y hay cuotas → recalcular SOLO fechas de vencimiento
            const nuevaFecha =
              formatDateForInput(prestamoData.fecha_aprobacion) ||
              formatDateForInput(prestamoData.fecha_base_calculo)
            const pid2 = parseInt(prestamoId, 10)
            if (
              prestamoUpdate.fecha_aprobacion &&
              nuevaFecha &&
              fechaAprobacionOriginal &&
              nuevaFecha !== fechaAprobacionOriginal &&
              cuotasData.length > 0
            ) {
              try {
                const res =
                  await prestamoService.recalcularFechasAmortizacion(pid2)
                const actualizadas =
                  res?.data?.actualizadas ?? res?.actualizadas ?? '?'
                toast.success(
                  `📅 Fechas de vencimiento actualizadas: ${actualizadas} cuota(s) recalculadas`
                )
                setFechaAprobacionOriginal(nuevaFecha)
                // Recargar datos frescos de BD para mostrar nuevas fechas en tabla
                const datosActualizados =
                  await revisionManualService.getDetallePrestamoRevision(pid2)
                if (datosActualizados?.cuotas) {
                  setCuotasData(
                    mergeCuotasParaMostrar(
                      datosActualizados.cuotas,
                      datosActualizados.prestamo?.numero_cuotas
                    )
                  )
                }
              } catch (errRecalc: any) {
                toast.warning(
                  '⚠️ Préstamo guardado, pero no se pudieron recalcular las fechas de vencimiento'
                )
                console.error('Error recalculando fechas:', errRecalc)
              }
            }
          } catch (err: any) {
            errorOccurred = true

            const errorMsg =
              err?.response?.data?.detail || 'Error al guardar préstamo'

            toast.error(`❌ Error en préstamo: ${errorMsg}`)

            console.error('Error guardando préstamo:', err)
          }
        }
      }

      // Guardar cuotas si difieren de la carga inicial

      if (needGuardarCuotas) {
        type JobCuota = {
          cuota_id: number
          cuotaUpdate: Record<string, any>
          numero_cuota: number | undefined
        }
        const jobsCuotas: JobCuota[] = []
        for (const cuota of cuotasData) {
          if (!cuota.cuota_id) continue
          const cuotaUpdate: Record<string, any> = {}

          if (cuota.fecha_pago)
            cuotaUpdate.fecha_pago = cuota.fecha_pago.split('T')[0]

          if (cuota.fecha_vencimiento)
            cuotaUpdate.fecha_vencimiento =
              cuota.fecha_vencimiento.split('T')[0]

          if (cuota.monto !== undefined && cuota.monto >= 0)
            cuotaUpdate.monto = cuota.monto

          if (cuota.total_pagado !== undefined && cuota.total_pagado >= 0)
            cuotaUpdate.total_pagado = cuota.total_pagado

          if (cuota.estado) cuotaUpdate.estado = cuota.estado

          if (Object.keys(cuotaUpdate).length > 0) {
            jobsCuotas.push({
              cuota_id: cuota.cuota_id,
              cuotaUpdate,
              numero_cuota: cuota.numero_cuota,
            })
          }
        }

        await ejecutarEnLotes(
          jobsCuotas,
          CUOTAS_REVISION_PUT_CONCURRENCY,
          async job => {
            try {
              await revisionManualService.editarCuota(
                job.cuota_id,
                job.cuotaUpdate
              )

              savedSomething = true
            } catch (err: any) {
              errorOccurred = true

              const errorMsg =
                err?.response?.data?.detail || 'Error al guardar cuota'

              toast.error(`❌ Error en cuota #${job.numero_cuota}: ${errorMsg}`)

              console.error(`Error guardando cuota ${job.numero_cuota}:`, err)
            }
          }
        )
      }

      if (!errorOccurred && savedSomething) {
        if (!huboSoloSincOperativaBd) {
          toast.success('✅ Cambios parciales guardados en BD')
        }

        setCambios({ cliente: false, prestamo: false, cuotas: false })

        setRevisionOperativaSucia(false)

        await refrescarOrigenDatosTrasRevisionManual()

        if (opts?.volverAunqueNoHayaCambios || returnToRevision) {
          setTimeout(() => navegarTrasGuardarRevision(), 400)
        }
      } else if (errorOccurred) {
        toast.warning(
          '⚠️ Algunos cambios no se guardaron. Revisa los errores arriba'
        )
      }
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || 'Error desconocido'

      toast.error(`❌ Error general: ${errorMsg}`)

      console.error('Error general guardando:', err)
    } finally {
      setGuardandoParcial(false)
    }
  }

  /** Botón "Guardar y Cerrar": mismo guardado a BD + finalizar revisión manual (estado revisado). */
  const handleGuardarYCerrar = async () => {
    if (!prestamoId) return

    if (soloLectura) {
      toast.info(
        'Este préstamo está en solo lectura (revisión ya cerrada en el sistema).'
      )

      return
    }

    if (bloqueoGuardarYCerrarPorContacto.bloqueado) {
      toast.error(
        bloqueoGuardarYCerrarPorContacto.motivo ||
          'Teléfono o correo no cumplen validadores; use «Guardar cambios» para corregir.'
      )
      return
    }

    const tLive = (clienteData.telefono || '').trim()
    if (tLive) {
      const rt = validarTelefonoVenezuelaRevisionLocal(tLive)
      if (!rt.valido) {
        toast.error(
          mensajeValidacionCampoLocal(rt) ||
            'El teléfono no es válido para cerrar la revisión.'
        )
        return
      }
    }

    const eLive = (clienteData.email || '').trim()
    if (eLive) {
      const re = validarEmailRevisionLocal(eLive)
      if (!re.valido) {
        toast.error(
          mensajeValidacionCampoLocal(re) ||
            'El correo no es válido para cerrar la revisión.'
        )
        return
      }
    }

    if (!validarFormulario()) {
      toast.error('Corrige los errores marcados en rojo antes de guardar')
      return
    }

    // «Guardar y Cerrar» también debe poder marcar la revisión como revisada (Visto)
    // aunque el formulario coincida con la carga inicial (revisión sin ediciones).
    // «Guardar cambios» acepta además operaciones ya persistidas (pagos, cascada, etc.)
    // vía revisionOperativaSucia hasta que el usuario confirme.

    // Confirmar si cambió la fecha de aprobación y hay cuotas
    const nuevaFechaFinalCheck = formatDateForInput(
      prestamoData.fecha_aprobacion
    )
    const snapFin = firmaCargaInicialRef.current
    const prestamoDistintoFin =
      !snapFin || firmaSoloPrestamo(prestamoData) !== snapFin.prestamo
    if (
      prestamoDistintoFin &&
      nuevaFechaFinalCheck &&
      fechaAprobacionOriginal &&
      nuevaFechaFinalCheck !== fechaAprobacionOriginal &&
      cuotasData.length > 0
    ) {
      const okFecha = window.confirm(
        `⚠️ CAMBIO DE FECHA DE APROBACIÓN\n\n` +
          `Fecha anterior: ${fechaAprobacionOriginal}\n` +
          `Fecha nueva:    ${nuevaFechaFinalCheck}\n\n` +
          `Se recalcularán ÚNICAMENTE las fechas de vencimiento de las ${cuotasData.length} cuota(s) de la tabla de amortización.\n` +
          `Los montos, pagos y saldos NO cambiarán.\n\n` +
          `¿Deseas continuar?`
      )
      if (!okFecha) return
    }

    const confirmar = window.confirm(
      '⚠️ CONFIRMAR FINALIZACIÓN DE REVISIÓN\n\n' +
        '✓ Se guardarán todos los cambios pendientes\n' +
        '✓ El préstamo se marcará como REVISADO\n' +
        '✓ NO PODRÁS EDITAR ESTE PRÉSTAMO DE NUEVO\n\n' +
        '¿Estás completamente seguro?'
    )

    // Usuario pulsó «Cancelar» en el diálogo nativo: no mostrar toast (se confundía con error).
    if (!confirmar) return

    setGuardandoFinal(true)

    try {
      const snapCierre = firmaCargaInicialRef.current
      const needClienteCierre =
        !!clienteData.cliente_id &&
        (!snapCierre || firmaSoloCliente(clienteData) !== snapCierre.cliente)
      const needPrestamoCierre =
        !!prestamoData.prestamo_id &&
        (!snapCierre || firmaSoloPrestamo(prestamoData) !== snapCierre.prestamo)
      const needCuotasCierre =
        !snapCierre || firmaSoloCuotas(cuotasData) !== snapCierre.cuotas

      if (needClienteCierre) {
        const clienteUpdate: Record<string, any> = {}

        if (clienteData.nombres) clienteUpdate.nombres = clienteData.nombres

        if (clienteData.telefono) clienteUpdate.telefono = clienteData.telefono

        if (clienteData.email) clienteUpdate.email = clienteData.email

        if (clienteData.direccion)
          clienteUpdate.direccion = clienteData.direccion

        if (clienteData.ocupacion)
          clienteUpdate.ocupacion = clienteData.ocupacion

        if (clienteData.estado) clienteUpdate.estado = clienteData.estado

        if (clienteData.fecha_nacimiento !== undefined)
          clienteUpdate.fecha_nacimiento = clienteData.fecha_nacimiento || null

        clienteUpdate.notas = String(clienteData.notas ?? '')

        if (
          Object.keys(clienteUpdate).length > 0 &&
          clienteData.cliente_id != null
        ) {
          try {
            await revisionManualService.editarCliente(
              clienteData.cliente_id,
              clienteUpdate,
              { prestamoId: parseInt(prestamoId, 10) }
            )
          } catch (err: any) {
            throw new Error(
              `Error en cliente: ${err?.response?.data?.detail || 'Error desconocido'}`
            )
          }
        }
      }

      if (needPrestamoCierre) {
        const prestamoUpdate: Record<string, any> = {}

        if (
          prestamoData.total_financiamiento !== undefined &&
          prestamoData.total_financiamiento >= 0
        )
          prestamoUpdate.total_financiamiento =
            prestamoData.total_financiamiento

        if (
          prestamoData.numero_cuotas !== undefined &&
          prestamoData.numero_cuotas >= 1
        )
          prestamoUpdate.numero_cuotas = prestamoData.numero_cuotas

        if (prestamoData.producto !== undefined)
          prestamoUpdate.producto = prestamoData.producto

        if (prestamoData.cedula !== undefined)
          prestamoUpdate.cedula = prestamoData.cedula

        if (prestamoData.nombres !== undefined)
          prestamoUpdate.nombres = prestamoData.nombres

        if (prestamoData.fecha_requerimiento !== undefined)
          prestamoUpdate.fecha_requerimiento =
            prestamoData.fecha_requerimiento || null

        if (prestamoData.modalidad_pago !== undefined)
          prestamoUpdate.modalidad_pago = prestamoData.modalidad_pago

        if (
          prestamoData.cuota_periodo !== undefined &&
          prestamoData.cuota_periodo >= 0
        )
          prestamoUpdate.cuota_periodo = prestamoData.cuota_periodo

        applyFechaAprobacionAlPayload(prestamoUpdate)

        const estadoPrestamoNormCierre = (prestamoData.estado ?? '')
          .toString()
          .trim()
          .toUpperCase()
        if (estadoPrestamoNormCierre)
          prestamoUpdate.estado = estadoPrestamoNormCierre

        if (prestamoData.concesionario !== undefined)
          prestamoUpdate.concesionario = prestamoData.concesionario

        if (prestamoData.analista !== undefined)
          prestamoUpdate.analista = prestamoData.analista

        if (prestamoData.modelo_vehiculo !== undefined)
          prestamoUpdate.modelo_vehiculo = prestamoData.modelo_vehiculo

        if (
          prestamoData.valor_activo !== undefined &&
          prestamoData.valor_activo !== null
        )
          prestamoUpdate.valor_activo = prestamoData.valor_activo

        if (prestamoData.usuario_proponente !== undefined)
          prestamoUpdate.usuario_proponente = prestamoData.usuario_proponente

        if (prestamoData.usuario_aprobador !== undefined)
          prestamoUpdate.usuario_aprobador = prestamoData.usuario_aprobador

        prestamoUpdate.observaciones = String(prestamoData.observaciones ?? '')

        if (
          Object.keys(prestamoUpdate).length > 0 &&
          prestamoData.prestamo_id != null
        ) {
          try {
            await revisionManualService.editarPrestamo(
              prestamoData.prestamo_id,
              prestamoUpdate
            )

            // Si cambió la fecha de aprobación y hay cuotas → recalcular SOLO fechas de vencimiento
            const nuevaFechaFinal =
              formatDateForInput(prestamoData.fecha_aprobacion) ||
              formatDateForInput(prestamoData.fecha_base_calculo)
            const pidFechas = parseInt(prestamoId, 10)
            if (
              prestamoUpdate.fecha_aprobacion &&
              nuevaFechaFinal &&
              fechaAprobacionOriginal &&
              nuevaFechaFinal !== fechaAprobacionOriginal &&
              cuotasData.length > 0
            ) {
              try {
                await prestamoService.recalcularFechasAmortizacion(pidFechas)
                setFechaAprobacionOriginal(nuevaFechaFinal)
              } catch (errRecalc: any) {
                console.error(
                  'Error recalculando fechas (guardar y cerrar):',
                  errRecalc
                )
              }
            }
          } catch (err: any) {
            throw new Error(
              `Error en préstamo: ${err?.response?.data?.detail || 'Error desconocido'}`
            )
          }
        }
      }

      if (needCuotasCierre) {
        type JobCuotaCierre = {
          cuota_id: number
          cuotaUpdate: Record<string, any>
          numero_cuota: number | undefined
        }
        const jobsCierre: JobCuotaCierre[] = []
        for (const cuota of cuotasData) {
          if (!cuota.cuota_id) continue
          const cuotaUpdate: Record<string, any> = {}

          if (cuota.fecha_pago)
            cuotaUpdate.fecha_pago = cuota.fecha_pago.split('T')[0]

          if (cuota.fecha_vencimiento)
            cuotaUpdate.fecha_vencimiento =
              cuota.fecha_vencimiento.split('T')[0]

          if (cuota.monto !== undefined && cuota.monto >= 0)
            cuotaUpdate.monto = cuota.monto

          if (cuota.total_pagado !== undefined && cuota.total_pagado >= 0)
            cuotaUpdate.total_pagado = cuota.total_pagado

          if (cuota.estado) cuotaUpdate.estado = cuota.estado

          if (Object.keys(cuotaUpdate).length > 0) {
            jobsCierre.push({
              cuota_id: cuota.cuota_id,
              cuotaUpdate,
              numero_cuota: cuota.numero_cuota,
            })
          }
        }

        await ejecutarEnLotes(
          jobsCierre,
          CUOTAS_REVISION_PUT_CONCURRENCY,
          async job => {
            try {
              await revisionManualService.editarCuota(
                job.cuota_id,
                job.cuotaUpdate
              )
            } catch (err: any) {
              throw new Error(
                `Error en cuota #${job.numero_cuota}: ${err?.response?.data?.detail || 'Error desconocido'}`
              )
            }
          }
        )
      }

      await persistObservacionesYNotasRevision()

      // Finalizar revisión

      try {
        const res = await revisionManualService.finalizarRevision(
          parseInt(prestamoId)
        )

        toast.success(res.mensaje)

        setRevisionOperativaSucia(false)

        await refrescarOrigenDatosTrasRevisionManual()

        // Pequeño delay antes de navegar para que el usuario vea el mensaje
        setTimeout(() => navegarTrasGuardarRevision(), 1500)
      } catch (err: any) {
        throw new Error(
          `Error al finalizar: ${err?.response?.data?.detail || 'Error desconocido'}`
        )
      }
    } catch (err: any) {
      const errorMsg = err.message || 'Error al guardar y cerrar'

      toast.error(`❌ ${errorMsg}`)

      console.error('Error finalizando:', err)
    } finally {
      setGuardandoFinal(false)
    }
  }

  const handleConfirmarRechazo = async () => {
    if (!prestamoId || !motivoRechazo.trim()) {
      toast.error('Debes ingresar un motivo de rechazo')
      return
    }
    setGuardandoRechazo(true)
    try {
      await persistObservacionesYNotasRevision()
      await revisionManualService.cambiarEstadoRevision(Number(prestamoId), {
        nuevo_estado: 'rechazado',
        motivo_rechazo: motivoRechazo.trim(),
      })
      toast.success('Préstamo marcado como rechazado')
      setShowRechazarModal(false)
      setMotivoRechazo('')
      await refrescarOrigenDatosTrasRevisionManual()
      navegarTrasGuardarRevision()
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Error al rechazar'
      toast.error(msg)
    } finally {
      setGuardandoRechazo(false)
    }
  }

  const handleCerrar = () => {
    // Si hay cambios sin guardar, advertir

    if (hayCambiosPendientesRevision()) {
      const confirmar = window.confirm(
        '⚠️ Hay cambios pendientes de reconocer.\n\n' +
          'Incluye ediciones del formulario y operaciones ya hechas en pagos, conciliación o cascada ' +
          'que aún no confirmaste con «Guardar cambios» o «Guardar y cerrar».\n\n' +
          '¿Seguro que deseas salir sin confirmar?'
      )

      if (!confirmar) return
    }

    void refrescarOrigenDatosTrasRevisionManual()

    navegarTrasCerrarRevision()
  }

  const hayPendienteRevision = hayCambiosPendientesRevision()

  const claseResaltarGuardarRevision =
    hayPendienteRevision && !soloLectura
      ? 'ring-2 ring-amber-400 ring-offset-2 rounded-md'
      : ''

  const deshabilitarGuardarYCerrar =
    soloLectura ||
    guardandoParcial ||
    guardandoFinal ||
    bloqueoGuardarYCerrarPorContacto.bloqueado

  const tituloGuardarYCerrarBoton = bloqueoGuardarYCerrarPorContacto.bloqueado
    ? bloqueoGuardarYCerrarPorContacto.motivo
    : 'Guarda todos los cambios y finaliza la revisión - aparece ✓ en Acciones'

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (error) {
    const detalleErrorMsg = getErrorMessage(error)
    const httpStatus = isAxiosError(error) ? error.response?.status : undefined

    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="max-w-lg text-center">
          <h2 className="mb-2 text-2xl font-bold text-red-600">Error</h2>

          <p className="mb-2 text-gray-600">
            No se pudieron cargar los datos del préstamo
            {httpStatus != null ? ` (${httpStatus})` : ''}.
          </p>

          <p className="mb-6 break-words text-sm text-gray-700">
            {detalleErrorMsg}
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => void refetchDetalle()}
            >
              Reintentar
            </Button>
            <Button
              type="button"
              onClick={() =>
                navigate(RUTA_LISTA_PRESTAMOS, {
                  state: { focusPrestamosSearch: true },
                })
              }
            >
              Volver a lista de préstamos
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6 p-6"
    >
      {/* Modal de rechazo */}
      {showRechazarModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100">
                <AlertTriangle className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-gray-900">
                  Rechazar préstamo
                </h2>
                <p className="text-sm text-gray-500">
                  No se guardarán cambios. Solo se marcará como rechazado.
                </p>
              </div>
            </div>

            <label className="mb-1 block text-sm font-medium text-gray-700">
              Motivo del rechazo <span className="text-red-500">*</span>
            </label>
            <textarea
              className="w-full rounded-lg border border-gray-300 p-3 text-sm focus:border-red-400 focus:outline-none focus:ring-1 focus:ring-red-400"
              rows={4}
              placeholder="Describe el motivo del rechazo..."
              value={motivoRechazo}
              onChange={e => setMotivoRechazo(e.target.value)}
              autoFocus
            />

            <div className="mt-4 flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setShowRechazarModal(false)
                  setMotivoRechazo('')
                }}
                disabled={guardandoRechazo}
              >
                Cancelar
              </Button>
              <Button
                className="gap-2 bg-red-600 text-white hover:bg-red-700"
                onClick={handleConfirmarRechazo}
                disabled={guardandoRechazo || !motivoRechazo.trim()}
              >
                {guardandoRechazo ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <X className="h-4 w-4" />
                )}
                Confirmar rechazo
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Contenido principal */}
      <div>
        {/* Header */}

        <div className="sticky top-0 z-10 -mx-6 mb-4 flex items-center justify-between bg-white p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={handleCerrar}
              className="h-8 w-8 p-0"
              title="Volver sin guardar"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>

            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Revisión: {clienteData.nombres}
              </h1>

              <p className="text-sm text-gray-600">
                {soloLectura
                  ? 'Solo lectura: la revisión de este préstamo ya fue cerrada.'
                  : estadoRevision === 'revisado' && revisionManualFullEdit
                    ? 'Revisión cerrada (Visto); puede editar, guardar y cambiar el estado desde la lista (icono de revisión manual).'
                    : 'Edita los detalles del préstamo (cambios parciales permitidos)'}
              </p>
              {!soloLectura && hayPendienteRevision ? (
                <p className="mt-1 text-sm font-medium text-amber-800">
                  Pendiente: confirme con «Guardar cambios» o «Guardar y cerrar»
                  (incluye nombre u otros campos, pagos, conciliación, cascada o
                  recálculo de vencimientos ya aplicados en base).
                </p>
              ) : null}
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => void handleGuardarParciales()}
              disabled={soloLectura || guardandoParcial || guardandoFinal}
              className={`gap-2 ${claseResaltarGuardarRevision}`}
              title="Guarda los cambios y continúa revisando - estado cambia a ?"
            >
              {guardandoParcial ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              {guardandoParcial ? 'Guardando…' : 'Guardar Cambios'}
            </Button>

            {vieneDesdeFiniquitos ? (
              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  void handleGuardarParciales({
                    volverAunqueNoHayaCambios: true,
                  })
                }
                disabled={
                  guardandoParcial || guardandoFinal || guardandoRechazo
                }
                className="gap-2 border-emerald-300 text-emerald-700 hover:bg-emerald-50"
                title="Guarda cambios pendientes y vuelve al área de trabajo de Finiquitos"
              >
                <ChevronLeft className="h-4 w-4" />
                Volver a finiquitos
              </Button>
            ) : (
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowRechazarModal(true)}
                disabled={
                  guardandoParcial || guardandoFinal || guardandoRechazo
                }
                className="gap-2 border-red-300 text-red-600 hover:bg-red-50"
                title="Marcar como rechazado - no guarda cambios, solo marca el préstamo"
              >
                <X className="h-4 w-4" />
                Rechazar
              </Button>
            )}

            <Button
              type="button"
              className={`gap-2 bg-green-600 text-white hover:bg-green-700 ${claseResaltarGuardarRevision}`}
              onClick={() => void handleGuardarYCerrar()}
              disabled={deshabilitarGuardarYCerrar}
              title={tituloGuardarYCerrarBoton}
            >
              {guardandoFinal ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Check className="h-4 w-4" />
              )}
              {guardandoFinal ? 'Finalizando…' : 'Guardar y Cerrar'}
            </Button>
          </div>
        </div>

        {soloLectura && (
          <div
            className="-mx-6 border-y border-amber-200 bg-amber-50 px-6 py-3 text-sm text-amber-950"
            role="status"
          >
            <strong>Solo lectura.</strong> La revisión de este préstamo ya fue
            cerrada; no se pueden guardar cambios ni eliminar cuotas.
            {detalleData?.revision?.fecha_revision ? (
              <span className="ml-2 text-amber-900">
                Cierre:{' '}
                {new Date(detalleData.revision.fecha_revision).toLocaleString()}
              </span>
            ) : null}
            {detalleData?.revision?.usuario_revision_email ? (
              <span className="ml-2">
                Usuario: {detalleData.revision.usuario_revision_email}
              </span>
            ) : null}
          </div>
        )}

        {estadoRevision === 'revisado' &&
          revisionManualFullEdit &&
          !soloLectura && (
            <div
              className="-mx-6 border-y border-sky-200 bg-sky-50 px-6 py-3 text-sm text-sky-950"
              role="status"
            >
              <strong>Edición con revisión cerrada.</strong> La revisión figura
              como cerrada (Visto); puede editar y guardar. Para volver a
              pendiente / en revisión / otros estados use el icono de revisión
              manual en la lista de préstamos.
              {detalleData?.revision?.fecha_revision ? (
                <span className="ml-2 text-sky-900">
                  Cierre:{' '}
                  {new Date(
                    detalleData.revision.fecha_revision
                  ).toLocaleString()}
                </span>
              ) : null}
              {detalleData?.revision?.usuario_revision_email ? (
                <span className="ml-2">
                  Usuario: {detalleData.revision.usuario_revision_email}
                </span>
              ) : null}
            </div>
          )}

        {/* Secciones */}

        <div className="relative">
          {soloLectura ? (
            <div
              className="absolute inset-0 z-20 cursor-not-allowed rounded-lg bg-gray-100/70"
              aria-hidden
            />
          ) : null}

          <div
            className={
              soloLectura
                ? 'pointer-events-none grid select-none gap-6'
                : 'grid gap-6'
            }
          >
            {/* Cliente */}

            <ClienteRevisionCard
              clienteData={clienteData}
              setClienteData={setClienteData}
              cambios={cambios}
              setCambios={setCambios}
              errores={errores}
              setErrores={setErrores}
              opcionesEstado={opcionesEstado}
              emailValidadorCierre={emailValidadorCierre}
              telValidadorCierre={telValidadorCierre}
            />

            {/* Préstamo */}

            <PrestamoRevisionCard
              prestamoData={prestamoData}
              setPrestamoData={setPrestamoData}
              setCuotasData={setCuotasData}
              cambios={cambios}
              setCambios={setCambios}
              errores={errores}
              setErrores={setErrores}
              concesionarios={concesionarios}
              analistas={analistas}
              modelosVehiculos={modelosVehiculos}
              soloLectura={soloLectura}
              formDirtyRef={formDirtyRef}
              recalculandoFechasCuotas={recalculandoFechasCuotas}
              handleGuardarFechaYRecalcularVencimientos={
                handleGuardarFechaYRecalcularVencimientos
              }
              formatDateForInput={formatDateForInput}
            />

            {/* Pagos reales en tabla pagos (mismo origen que carga masiva / módulo Pagos) */}
            {cedulaParaPagosRealizados ? (
              <PagosRegistradosRevisionSection
                cedulaParaPagosRealizados={cedulaParaPagosRealizados}
                pagosRegistradosCardRef={pagosRegistradosCardRef}
                vieneDesdeFiniquitos={vieneDesdeFiniquitos}
                prestamoData={prestamoData}
                soloLectura={soloLectura}
                aplicarCascadaPagosMutation={aplicarCascadaPagosMutation}
                abrirAgregarPagoRevision={abrirAgregarPagoRevision}
                escaneandoComprobanteAgregarPago={
                  escaneandoComprobanteAgregarPago
                }
                abrirSelectorEscaneoComprobanteAgregarPago={
                  abrirSelectorEscaneoComprobanteAgregarPago
                }
                reescaneandoCartera={reescaneandoCartera}
                reescaneoCarteraProgreso={reescaneoCarteraProgreso}
                ejecutarReescaneoCartera={ejecutarReescaneoCartera}
                loadingPagosRealizados={loadingPagosRealizados}
                fetchingPagosRealizados={fetchingPagosRealizados}
                refetchPagosRealizados={refetchPagosRealizados}
                isAdmin={isAdmin}
                conciliarTablaUi={conciliarTablaUi}
                setConciliarTablaUi={setConciliarTablaUi}
                idsPagosPrestamoEnTabla={idsPagosPrestamoEnTabla}
                contarPagosPrestamoEnTabla={contarPagosPrestamoEnTabla}
                limpiarConciliarTablaUi={limpiarConciliarTablaUi}
                manejarConciliarExito={manejarConciliarExito}
                pagosRealizadosData={pagosRealizadosData}
                pagosRegistradosOrdenados={pagosRegistradosOrdenados}
                conteoDocumentoPagosRevision={conteoDocumentoPagosRevision}
                alertasReescaneoPorPagoId={alertasReescaneoPorPagoId}
                abrirEditarPagoRevision={abrirEditarPagoRevision}
                pagoEstaConciliadoOPagado={pagoEstaConciliadoOPagado}
                eliminandoPagoId={eliminandoPagoId}
                eliminarPagoRevision={eliminarPagoRevision}
                pagePagosRegistrados={pagePagosRegistrados}
                setPagePagosRegistrados={setPagePagosRegistrados}
                hayPendienteRevision={hayPendienteRevision}
                auditoriaCoherenciaActiva={auditoriaCoherenciaActiva}
                estadoPrestamoNorm={estadoPrestamoNorm}
                agregadosCuotasRevision={agregadosCuotasRevision}
              />
            ) : null}

            {/* Cuotas (después del reporte de pagos en cartera) */}

            <Card>
              <CardHeader className="space-y-3">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <CardTitle className="flex items-center gap-2">
                    💳 Cuotas/Pagos
                  </CardTitle>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="shrink-0 gap-1.5 self-start sm:self-center"
                    disabled={soloLectura || cuotasData.length === 0}
                    onClick={alinearPagadoAlMontoCuotasPagadas}
                    title={
                      soloLectura
                        ? 'Revisión cerrada: solo lectura'
                        : 'En filas con estado Pagado o Pago adelantado, copia el Monto de esa misma fila a Pagado (sin calcular desde otros datos).'
                    }
                  >
                    <CheckSquare className="h-4 w-4" />
                    Verificar: Pagado = Monto
                  </Button>
                </div>
              </CardHeader>

              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left">Cuota</th>

                        <th className="px-4 py-2 text-right">Monto</th>

                        <th className="px-4 py-2 text-left">Vencimiento</th>

                        <th className="px-4 py-2 text-left">Fecha Pago</th>

                        <th className="px-4 py-2 text-right">Pagado</th>

                        <th className="px-4 py-2 text-left">Estado</th>
                      </tr>
                    </thead>

                    <tbody className="divide-y">
                      {cuotasData.map((cuota, idx) => (
                        <tr
                          key={
                            cuota.cuota_id != null
                              ? `id-${cuota.cuota_id}`
                              : `n-${cuota.numero_cuota ?? idx}`
                          }
                          className="hover:bg-gray-50"
                        >
                          <td className="px-4 py-2 font-medium">
                            {cuota.numero_cuota}
                          </td>

                          <td className="px-4 py-2">
                            <input
                              type="number"
                              step="0.01"
                              value={cuota.monto ?? ''}
                              onChange={e => {
                                const newCuotas = [...cuotasData]

                                const nuevoMonto =
                                  parseFloat(e.target.value) || 0
                                const est = codigoEstadoCuotaParaUi(
                                  cuota.estado
                                )
                                const syncPagado =
                                  est === 'PAGADO' || est === 'PAGO_ADELANTADO'

                                newCuotas[idx] = {
                                  ...cuota,
                                  monto: nuevoMonto,
                                  ...(syncPagado
                                    ? { total_pagado: nuevoMonto }
                                    : {}),
                                }

                                setCuotasData(newCuotas)

                                setCambios({ ...cambios, cuotas: true })
                              }}
                              className="w-20 rounded border px-2 py-1 text-right text-sm"
                            />
                          </td>

                          <td className="px-4 py-2">
                            <input
                              type="date"
                              value={
                                cuota.fecha_vencimiento
                                  ? formatDateForInput(cuota.fecha_vencimiento)
                                  : ''
                              }
                              onChange={e => {
                                const newCuotas = [...cuotasData]

                                newCuotas[idx] = {
                                  ...cuota,
                                  fecha_vencimiento: e.target.value
                                    ? `${e.target.value}T00:00:00`
                                    : null,
                                }

                                setCuotasData(newCuotas)

                                setCambios({ ...cambios, cuotas: true })
                              }}
                              className="w-full rounded border px-2 py-1 text-sm"
                            />
                          </td>

                          <td className="px-4 py-2">
                            <input
                              type="date"
                              value={
                                cuota.fecha_pago
                                  ? formatDateForInput(cuota.fecha_pago)
                                  : ''
                              }
                              onChange={e => {
                                const newCuotas = [...cuotasData]

                                newCuotas[idx] = {
                                  ...cuota,
                                  fecha_pago: e.target.value
                                    ? `${e.target.value}T00:00:00`
                                    : null,
                                }

                                setCuotasData(newCuotas)

                                setCambios({ ...cambios, cuotas: true })
                              }}
                              className="w-full rounded border px-2 py-1 text-sm"
                            />
                          </td>

                          <td className="px-4 py-2">
                            <input
                              type="number"
                              step="0.01"
                              value={cuota.total_pagado || ''}
                              onChange={e => {
                                const newCuotas = [...cuotasData]

                                newCuotas[idx] = {
                                  ...cuota,
                                  total_pagado: parseFloat(e.target.value) || 0,
                                }

                                setCuotasData(newCuotas)

                                setCambios({ ...cambios, cuotas: true })
                              }}
                              className="w-20 rounded border px-2 py-1 text-sm"
                              placeholder="0.00"
                            />
                          </td>

                          <td className="px-4 py-2">
                            <select
                              value={codigoEstadoCuotaParaUi(cuota.estado)}
                              onChange={e => {
                                const newCuotas = [...cuotasData]

                                const nuevoEstado = e.target.value
                                const code =
                                  codigoEstadoCuotaParaUi(nuevoEstado)
                                const syncPagado =
                                  code === 'PAGADO' ||
                                  code === 'PAGO_ADELANTADO'

                                newCuotas[idx] = {
                                  ...cuota,
                                  estado: nuevoEstado,
                                  ...(syncPagado
                                    ? {
                                        total_pagado: Number(cuota.monto) || 0,
                                      }
                                    : {}),
                                }

                                setCuotasData(newCuotas)

                                setCambios({ ...cambios, cuotas: true })
                              }}
                              className="rounded border px-2 py-1 text-sm"
                            >
                              {opcionesSelectCuotaRevision(cuota.estado).map(
                                opt => (
                                  <option key={opt.value} value={opt.value}>
                                    {opt.label}
                                  </option>
                                )
                              )}
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Botones inferiores sticky */}

        <div className="sticky bottom-6 -mx-6 flex justify-end gap-3 rounded-t-lg bg-white p-4 shadow-lg">
          <Button
            type="button"
            variant="outline"
            onClick={() => void handleGuardarParciales()}
            disabled={soloLectura || guardandoParcial || guardandoFinal}
            className={`gap-2 ${claseResaltarGuardarRevision}`}
            title="Guarda los cambios y continúa revisando - estado cambia a ?"
          >
            {guardandoParcial ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {guardandoParcial ? 'Guardando…' : 'Guardar Cambios'}
          </Button>

          {vieneDesdeFiniquitos ? (
            <Button
              type="button"
              variant="outline"
              onClick={() =>
                void handleGuardarParciales({ volverAunqueNoHayaCambios: true })
              }
              disabled={guardandoParcial || guardandoFinal || guardandoRechazo}
              className="gap-2 border-emerald-300 text-emerald-700 hover:bg-emerald-50"
              title="Guarda cambios pendientes y vuelve al área de trabajo de Finiquitos"
            >
              <ChevronLeft className="h-4 w-4" />
              Volver a finiquitos
            </Button>
          ) : (
            <Button
              type="button"
              variant="outline"
              onClick={() => setShowRechazarModal(true)}
              disabled={guardandoParcial || guardandoFinal || guardandoRechazo}
              className="gap-2 border-red-300 text-red-600 hover:bg-red-50"
              title="Marcar como rechazado - no guarda cambios, solo marca el préstamo"
            >
              <X className="h-4 w-4" />
              Rechazar
            </Button>
          )}

          <Button
            type="button"
            className={`gap-2 bg-green-600 text-white hover:bg-green-700 ${claseResaltarGuardarRevision}`}
            onClick={() => void handleGuardarYCerrar()}
            disabled={deshabilitarGuardarYCerrar}
            title={tituloGuardarYCerrarBoton}
          >
            {guardandoFinal ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Check className="h-4 w-4" />
            )}
            {guardandoFinal ? 'Finalizando…' : 'Guardar y Cerrar'}
          </Button>
        </div>
      </div>

      <input
        ref={escaneoComprobanteAgregarPagoRef}
        type="file"
        accept="image/*,application/pdf"
        className="hidden"
        onChange={e => void handleArchivoEscaneoComprobanteAgregarPago(e)}
      />

      {pagoModalAbierto && pagoModalInicial != null && (
        <RegistrarPagoForm
          onClose={cerrarModalPagoRevision}
          onSuccess={onExitoModalPagoRevision}
          pagoInicial={pagoModalInicial}
          pagoId={pagoModalId}
          modoGuardarYProcesar
          esPagoConError={false}
          mostrarCampoCodigoDocumento
          bloquearCambioComprobanteCodigo={
            !isAdmin && pagoModalConciliadoPagado
          }
          comprobanteArchivoInicial={pagoModalComprobanteInicial}
          prestamoContextoRevisionManualId={
            prestamoData.prestamo_id != null &&
            Number(prestamoData.prestamo_id) > 0
              ? Number(prestamoData.prestamo_id)
              : undefined
          }
          claveDocumentoPagosTablaRevision={claveDocumentoPagosTablaRevision}
        />
      )}
    </motion.div>
  )
}

export default EditarRevisionManual
