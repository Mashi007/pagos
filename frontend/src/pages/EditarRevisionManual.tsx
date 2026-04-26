import {
  useState,
  useLayoutEffect,
  useRef,
  useEffect,
  useCallback,
  useMemo,
} from 'react'

import { flushSync } from 'react-dom'

import { useParams, useNavigate, useLocation } from 'react-router-dom'

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

import { prestamoService } from '../services/prestamoService'

import {
  invalidateListasNotificacionesMora,
  invalidatePagosPrestamosRevisionYCuotas,
} from '../constants/queryKeys'

import {
  esReturnToRevisionDesdeNotificaciones,
  leerYConsumirReturnRevisionSesion,
  limpiarReturnRevisionSesion,
  normalizarReturnToRevisionPath,
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
  esUrlComprobanteImagenConAuth,
} from '../utils/comprobanteImagenAuth'

import { validadoresService } from '../services/validadoresService'

import {
  CUOTAS_REVISION_PUT_CONCURRENCY,
  COHERENCIA_USD_TOL,
  PER_PAGE_PAGOS_REGISTRADOS,
  RUTA_LISTA_PRESTAMOS,
  badgeEstadoPagoRegistrado,
  descripcionDiagnosticoCascada,
  ejecutarEnLotes,
  firmaSoloCliente,
  firmaSoloCuotas,
  firmaSoloPrestamo,
  buildPrestamoPatchGuardarRevision,
  mensajeValidacionServidor,
  mergeCuotasParaMostrar,
  opcionesSelectCuotaRevision,
  opcionesSelectEstadoPrestamoRevision,
  pagoCarteraRevisionBloquearToggleCerrado,
  pagoEstadoExcluyeToggleConciliadoRevision,
  pagoRowAPagoCreateInicial,
  pagoValidadoCarteraRevisionRow,
  timestampOrdenFechaPago,
  type ClienteData,
  type CuotaData,
  type EstadoValidadorCierreContacto,
  type FirmaCargaRevision,
  type PrestamoData,
} from './revisionManual/EditarRevisionManual.helpers'

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

  const [eliminandoPagoId, setEliminandoPagoId] = useState<number | null>(null)

  const [conciliandoPagoId, setConciliandoPagoId] = useState<number | null>(
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
    let cancelled = false
    const raw = telefonoDebouncCierre.trim()
    if (!raw) {
      setTelValidadorCierre({ listo: true, validando: false })
      return () => {
        cancelled = true
      }
    }
    setTelValidadorCierre({ listo: false, validando: true })
    void validadoresService
      .validarCampo('telefono_venezuela', raw, 'VENEZUELA')
      .then(res => {
        if (cancelled) return
        const v = res?.validacion
        const ok = Boolean(v?.valido)
        setTelValidadorCierre({
          listo: ok,
          validando: false,
          mensaje: ok ? undefined : mensajeValidacionServidor(v),
        })
      })
      .catch(err => {
        if (cancelled) return
        setTelValidadorCierre({
          listo: false,
          validando: false,
          mensaje:
            getErrorMessage(err) ||
            'No se pudo validar el teléfono con el sistema',
        })
      })
    return () => {
      cancelled = true
    }
  }, [telefonoDebouncCierre])

  useEffect(() => {
    let cancelled = false
    const raw = emailDebouncCierre.trim()
    if (!raw) {
      setEmailValidadorCierre({ listo: true, validando: false })
      return () => {
        cancelled = true
      }
    }
    setEmailValidadorCierre({ listo: false, validando: true })
    void validadoresService
      .validarCampo('email', raw, 'VENEZUELA')
      .then(res => {
        if (cancelled) return
        const v = res?.validacion
        const ok = Boolean(v?.valido)
        setEmailValidadorCierre({
          listo: ok,
          validando: false,
          mensaje: ok ? undefined : mensajeValidacionServidor(v),
        })
      })
      .catch(err => {
        if (cancelled) return
        setEmailValidadorCierre({
          listo: false,
          validando: false,
          mensaje:
            getErrorMessage(err) ||
            'No se pudo validar el correo con el sistema',
        })
      })
    return () => {
      cancelled = true
    }
  }, [emailDebouncCierre])

  const bloqueoGuardarYCerrarPorContacto = useMemo(() => {
    if (telValidadorCierre.validando || emailValidadorCierre.validando) {
      return {
        bloqueado: true,
        motivo:
          'Validando teléfono o correo con los validadores del sistema. Espere un momento.',
      }
    }
    if (!telValidadorCierre.listo) {
      return {
        bloqueado: true,
        motivo:
          telValidadorCierre.mensaje ||
          'El teléfono no cumple los validadores. Use «Guardar cambios» para seguir corrigiendo; «Guardar y cerrar» se habilitará cuando sea válido.',
      }
    }
    if (!emailValidadorCierre.listo) {
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
    staleTime: 0,
    refetchOnWindowFocus: true,
    refetchInterval: 60_000,
  })

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
    const rows = pagosRealizadosData?.pagos ?? []
    return [...rows].sort((a, b) => {
      const tb = timestampOrdenFechaPago(b.fecha_pago)
      const ta = timestampOrdenFechaPago(a.fecha_pago)
      if (tb !== ta) return tb - ta
      return (b.id ?? 0) - (a.id ?? 0)
    })
  }, [pagosRealizadosData?.pagos])

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

  const { revisionManualFullEdit } = usePermissions()

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
    // La invalidación de `revision-editar` en refrescarOrigen ya dispara un refetch (RQ v5).
    await refrescarOrigenDatosTrasRevisionManual()
    void refetchPagosRealizados()
  }, [refetchPagosRealizados, refrescarOrigenDatosTrasRevisionManual])

  const aplicarCascadaPagosMutation = useMutation({
    mutationFn: async () => {
      if (!validarFormulario()) {
        throw new Error(
          'Corrija los errores marcados en rojo antes de aplicar la cascada.'
        )
      }
      const pid = Number(prestamoData.prestamo_id)
      if (!Number.isFinite(pid) || pid <= 0) {
        throw new Error('No hay crédito válido para aplicar la cascada')
      }

      const patch = buildPrestamoPatchGuardarRevision(
        prestamoData,
        formatDateForInput
      )
      const esperadas = Math.floor(Number(prestamoData.numero_cuotas) || 0)
      const persistidas = cuotasData.filter(c => c.cuota_id != null).length
      const necesitaReconstruir =
        esperadas > 0 && (persistidas === 0 || persistidas < esperadas)

      if (necesitaReconstruir) {
        const fa =
          formatDateForInput(prestamoData.fecha_aprobacion) ||
          formatDateForInput(prestamoData.fecha_base_calculo)
        if (!fa) {
          throw new Error(
            'Indique fecha de aprobación (o base de cálculo) para generar las cuotas faltantes antes de la cascada.'
          )
        }
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
      await refrescarTrasCambioPagosRevision()
      /**
       * Persistimos préstamo en servidor antes/durante la cascada; el detalle en caché puede quedar
       * desalineado con el formulario. Traemos detalle fresco y alineamos préstamo + cuotas (merge N).
       */
      if (prestamoId) {
        const pidNum = parseInt(prestamoId, 10)
        if (Number.isFinite(pidNum) && pidNum > 0) {
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
        }
      }
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
      toast.success('Pago eliminado')
      await refrescarTrasCambioPagosRevision()
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

  const toggleConciliadoPagoRevision = async (pago: Pago, checked: boolean) => {
    if (soloLectura) return
    if (!checked && pagoCarteraRevisionBloquearToggleCerrado(pago)) {
      toast.error(
        'Este pago ya está aplicado a cuotas con cartera validada (Pagado). No se puede quitar desde aquí.'
      )
      return
    }
    if (pagoEstadoExcluyeToggleConciliadoRevision(pago.estado)) {
      toast.error(
        'No se puede cambiar conciliación en pagos anulados, rechazados o duplicado declarado.'
      )
      return
    }
    setConciliandoPagoId(pago.id)
    try {
      if (checked) {
        await pagoService.updateConciliado(pago.id, true)
      } else {
        await pagoService.updatePago(pago.id, {
          conciliado: false,
          verificado_concordancia: 'NO',
        })
      }
      toast.success(
        checked
          ? 'Pago validado para cartera (conciliado / verificado). Use «Aplicar pagos a cuotas» si aún no hay cuota_pagos.'
          : 'Validación de cartera quitada (conciliado no, verificado NO).'
      )
      await refrescarTrasCambioPagosRevision()
      setRevisionOperativaSucia(true)
    } catch (err: unknown) {
      toast.error(getErrorMessage(err) || 'No se pudo actualizar conciliación')
    } finally {
      setConciliandoPagoId(null)
    }
  }

  const cerrarModalPagoRevision = () => {
    setPagoModalAbierto(false)
    setPagoModalId(undefined)
    setPagoModalInicial(undefined)
  }

  const abrirAgregarPagoRevision = () => {
    if (soloLectura) return
    const ced = cedulaParaPagosRealizados
    const pid = prestamoData.prestamo_id
    setPagoModalId(undefined)
    setPagoModalInicial({
      cedula_cliente: ced,
      prestamo_id: pid != null && pid > 0 ? pid : null,
      fecha_pago: new Date().toISOString().slice(0, 10),
      monto_pagado: 0,
      numero_documento: '',
      institucion_bancaria: null,
      notas: null,
      link_comprobante: null,
    })
    setPagoModalAbierto(true)
  }

  const abrirEditarPagoRevision = (pago: Pago) => {
    if (soloLectura) return
    setPagoModalId(pago.id)
    setPagoModalInicial(pagoRowAPagoCreateInicial(pago))
    setPagoModalAbierto(true)
  }

  const onExitoModalPagoRevision = async () => {
    const fueEdicion = pagoModalId != null
    cerrarModalPagoRevision()
    toast.success(fueEdicion ? 'Pago actualizado' : 'Pago registrado')
    await refrescarTrasCambioPagosRevision()
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
  const handleGuardarParciales = async () => {
    if (!prestamoId) return

    if (soloLectura) {
      toast.info(
        'Este préstamo está en solo lectura (revisión ya cerrada en el sistema).'
      )

      return
    }

    if (!validarFormulario()) {
      toast.error('Corrige los errores marcados en rojo antes de guardar')
      return
    }

    // Sin cambios de formulario ni operaciones (pagos/cascada/etc.) pendientes de reconocer
    if (!hayDiferenciaVsCargaInicial() && !revisionOperativaSucia) {
      toast.info('ℹ️ No hay cambios para guardar')
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

        if (
          prestamoData.tasa_interes !== undefined &&
          prestamoData.tasa_interes >= 0
        )
          prestamoUpdate.tasa_interes = prestamoData.tasa_interes

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

        setTimeout(() => navegarTrasGuardarRevision(), 400)
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
      try {
        const rt = await validadoresService.validarCampo(
          'telefono_venezuela',
          tLive,
          'VENEZUELA'
        )
        if (!rt?.validacion?.valido) {
          toast.error(
            mensajeValidacionServidor(rt.validacion) ||
              'El teléfono no es válido para cerrar la revisión.'
          )
          return
        }
      } catch (e) {
        toast.error(getErrorMessage(e) || 'Error al validar el teléfono')
        return
      }
    }

    const eLive = (clienteData.email || '').trim()
    if (eLive) {
      try {
        const re = await validadoresService.validarCampo(
          'email',
          eLive,
          'VENEZUELA'
        )
        if (!re?.validacion?.valido) {
          toast.error(
            mensajeValidacionServidor(re.validacion) ||
              'El correo no es válido para cerrar la revisión.'
          )
          return
        }
      } catch (e) {
        toast.error(getErrorMessage(e) || 'Error al validar el correo')
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

        if (
          prestamoData.tasa_interes !== undefined &&
          prestamoData.tasa_interes >= 0
        )
          prestamoUpdate.tasa_interes = prestamoData.tasa_interes

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
              onClick={handleGuardarParciales}
              disabled={soloLectura || guardandoParcial || guardandoFinal}
              className={`gap-2 ${claseResaltarGuardarRevision}`}
              title="Guarda los cambios y continúa revisando - estado cambia a ?"
            >
              <Save className="h-4 w-4" />
              Guardar Cambios
            </Button>

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

            <Button
              type="button"
              className={`gap-2 bg-green-600 text-white hover:bg-green-700 ${claseResaltarGuardarRevision}`}
              onClick={handleGuardarYCerrar}
              disabled={deshabilitarGuardarYCerrar}
              title={tituloGuardarYCerrarBoton}
            >
              {guardandoFinal ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Check className="h-4 w-4" />
              )}
              Guardar y Cerrar
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

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5 text-blue-600" />
                  Datos del Cliente
                </CardTitle>
              </CardHeader>

              <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {/* Cédula - solo lectura */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Cédula
                  </label>
                  <div className="relative">
                    <CreditCard className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                      value={clienteData.cedula || ''}
                      disabled
                      className="cursor-not-allowed bg-gray-100 pl-10"
                    />
                  </div>
                </div>

                {/* Nombres */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Nombres y Apellidos <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                      type="text"
                      value={clienteData.nombres || ''}
                      onChange={e => {
                        setClienteData({
                          ...clienteData,
                          nombres: e.target.value,
                        })
                        setCambios({ ...cambios, cliente: true })
                        if (errores['nombres'])
                          setErrores({ ...errores, nombres: '' })
                      }}
                      placeholder="Juan Carlos Pérez González"
                      className={`pl-10 ${errores['nombres'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
                    />
                  </div>
                  {errores['nombres'] && (
                    <p className="text-xs text-red-600">{errores['nombres']}</p>
                  )}
                </div>

                {/* Teléfono */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Teléfono
                  </label>
                  <div className="flex items-center gap-2">
                    <div className="flex items-center rounded-md border border-gray-300 bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700">
                      <Phone className="mr-1 h-4 w-4 text-gray-500" />
                      +58
                    </div>
                    <Input
                      type="text"
                      inputMode="numeric"
                      value={(clienteData.telefono || '').replace(/^\+?58/, '')}
                      onChange={e => {
                        const digits = e.target.value.replace(/\D/g, '')
                        setClienteData({
                          ...clienteData,
                          telefono: digits ? `+58${digits}` : '',
                        })
                        setCambios({ ...cambios, cliente: true })
                        if (errores['telefono'])
                          setErrores({ ...errores, telefono: '' })
                      }}
                      placeholder="4141234567"
                      className={
                        errores['telefono']
                          ? 'border-red-500 focus-visible:ring-red-400'
                          : (clienteData.telefono || '').trim() &&
                              telValidadorCierre.validando
                            ? 'border-slate-300 ring-1 ring-slate-200'
                            : (clienteData.telefono || '').trim() &&
                                !telValidadorCierre.validando &&
                                !telValidadorCierre.listo
                              ? 'border-amber-500 focus-visible:ring-amber-400'
                              : ''
                      }
                    />
                  </div>
                  {errores['telefono'] && (
                    <p className="text-xs text-red-600">
                      {errores['telefono']}
                    </p>
                  )}
                  {(clienteData.telefono || '').trim() &&
                    telValidadorCierre.validando && (
                      <p className="text-xs text-muted-foreground">
                        Validando teléfono con el sistema…
                      </p>
                    )}
                  {(clienteData.telefono || '').trim() &&
                    !telValidadorCierre.validando &&
                    !telValidadorCierre.listo && (
                      <p className="text-xs text-amber-800">
                        <span className="font-medium">
                          No se puede «Guardar y cerrar»
                        </span>{' '}
                        hasta que el teléfono cumpla los validadores. Puede usar
                        «Guardar cambios» para seguir editando.
                        {telValidadorCierre.mensaje
                          ? ` Detalle: ${telValidadorCierre.mensaje}`
                          : ''}
                      </p>
                    )}
                </div>

                {/* Email */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Email
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                      type="email"
                      value={clienteData.email || ''}
                      onChange={e => {
                        setClienteData({
                          ...clienteData,
                          email: e.target.value,
                        })
                        setCambios({ ...cambios, cliente: true })
                        if (errores['email'])
                          setErrores({ ...errores, email: '' })
                      }}
                      placeholder="juan@email.com"
                      className={`pl-10 ${
                        errores['email']
                          ? 'border-red-500 focus-visible:ring-red-400'
                          : (clienteData.email || '').trim() &&
                              emailValidadorCierre.validando
                            ? 'border-slate-300 ring-1 ring-slate-200'
                            : (clienteData.email || '').trim() &&
                                !emailValidadorCierre.validando &&
                                !emailValidadorCierre.listo
                              ? 'border-amber-500 focus-visible:ring-amber-400'
                              : ''
                      }`}
                    />
                  </div>
                  {errores['email'] && (
                    <p className="text-xs text-red-600">{errores['email']}</p>
                  )}
                  {(clienteData.email || '').trim() &&
                    emailValidadorCierre.validando && (
                      <p className="text-xs text-muted-foreground">
                        Validando correo con el sistema…
                      </p>
                    )}
                  {(clienteData.email || '').trim() &&
                    !emailValidadorCierre.validando &&
                    !emailValidadorCierre.listo && (
                      <p className="text-xs text-amber-800">
                        <span className="font-medium">
                          No se puede «Guardar y cerrar»
                        </span>{' '}
                        hasta que el correo cumpla los validadores. Puede usar
                        «Guardar cambios» para seguir editando.
                        {emailValidadorCierre.mensaje
                          ? ` Detalle: ${emailValidadorCierre.mensaje}`
                          : ''}
                      </p>
                    )}
                </div>

                {/* Fecha Nacimiento */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Fecha de Nacimiento
                  </label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                      type="date"
                      value={clienteData.fecha_nacimiento || ''}
                      max={new Date(
                        new Date().setFullYear(new Date().getFullYear() - 18)
                      )
                        .toISOString()
                        .slice(0, 10)}
                      onChange={e => {
                        setClienteData({
                          ...clienteData,
                          fecha_nacimiento: e.target.value || null,
                        })
                        setCambios({ ...cambios, cliente: true })
                        if (errores['fecha_nacimiento'])
                          setErrores({ ...errores, fecha_nacimiento: '' })
                      }}
                      className={`pl-10 ${errores['fecha_nacimiento'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
                    />
                  </div>
                  {errores['fecha_nacimiento'] && (
                    <p className="text-xs text-red-600">
                      {errores['fecha_nacimiento']}
                    </p>
                  )}
                </div>

                {/* Ocupación */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Ocupación
                  </label>
                  <div className="relative">
                    <Briefcase className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                      type="text"
                      value={clienteData.ocupacion || ''}
                      onChange={e => {
                        setClienteData({
                          ...clienteData,
                          ocupacion: e.target.value,
                        })
                        setCambios({ ...cambios, cliente: true })
                      }}
                      placeholder="Ingeniero, Gerente..."
                      className="pl-10"
                    />
                  </div>
                </div>

                {/* Estado */}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-700">
                    Estado del cliente
                  </label>
                  <Select
                    value={clienteData.estado || ''}
                    onValueChange={val => {
                      setClienteData({ ...clienteData, estado: val })
                      setCambios({ ...cambios, cliente: true })
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar estado" />
                    </SelectTrigger>
                    <SelectContent>
                      {opcionesEstado.map(est => (
                        <SelectItem key={est.value} value={est.value}>
                          {est.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Dirección - Desglosada en campos */}
                <div className="space-y-4 md:col-span-2">
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
                    <MapPin className="h-5 w-5 text-blue-600" />
                    Dirección Completa
                  </h3>

                  {(() => {
                    const getDireccionObj = () => {
                      try {
                        return typeof clienteData.direccion === 'string' &&
                          clienteData.direccion.startsWith('{')
                          ? JSON.parse(clienteData.direccion)
                          : {}
                      } catch {
                        return {}
                      }
                    }

                    const updateDireccionField = (
                      field: string,
                      value: string
                    ) => {
                      try {
                        const obj = getDireccionObj()
                        const updated = { ...obj, [field]: value }
                        setClienteData({
                          ...clienteData,
                          direccion: JSON.stringify(updated),
                        })
                        setCambios({ ...cambios, cliente: true })
                      } catch {
                        setClienteData({
                          ...clienteData,
                          direccion: JSON.stringify({ [field]: value }),
                        })
                        setCambios({ ...cambios, cliente: true })
                      }
                    }

                    const dirObj = getDireccionObj()

                    return (
                      <div className="grid grid-cols-2 gap-3">
                        {/* Calle Principal */}
                        <div className="space-y-1">
                          <label className="text-xs font-medium text-gray-600">
                            Calle Principal
                          </label>
                          <Input
                            type="text"
                            value={dirObj.callePrincipal || ''}
                            onChange={e =>
                              updateDireccionField(
                                'callePrincipal',
                                e.target.value
                              )
                            }
                            placeholder="Av. Principal, Calle 5..."
                            className="text-xs"
                          />
                        </div>

                        {/* Calle Transversal */}
                        <div className="space-y-1">
                          <label className="text-xs font-medium text-gray-600">
                            Calle Transversal
                          </label>
                          <Input
                            type="text"
                            value={dirObj.calleTransversal || ''}
                            onChange={e =>
                              updateDireccionField(
                                'calleTransversal',
                                e.target.value
                              )
                            }
                            placeholder="Calle 10, Entre..."
                            className="text-xs"
                          />
                        </div>

                        {/* Parroquia */}
                        <div className="space-y-1">
                          <label className="text-xs font-medium text-gray-600">
                            Parroquia
                          </label>
                          <Input
                            type="text"
                            value={dirObj.parroquia || ''}
                            onChange={e =>
                              updateDireccionField('parroquia', e.target.value)
                            }
                            placeholder="Los Robles..."
                            className="text-xs"
                          />
                        </div>

                        {/* Municipio */}
                        <div className="space-y-1">
                          <label className="text-xs font-medium text-gray-600">
                            Municipio
                          </label>
                          <Input
                            type="text"
                            value={dirObj.municipio || ''}
                            onChange={e =>
                              updateDireccionField('municipio', e.target.value)
                            }
                            placeholder="Chacao, Baruta..."
                            className="text-xs"
                          />
                        </div>

                        {/* Ciudad */}
                        <div className="space-y-1">
                          <label className="text-xs font-medium text-gray-600">
                            Ciudad
                          </label>
                          <Input
                            type="text"
                            value={dirObj.ciudad || ''}
                            onChange={e =>
                              updateDireccionField('ciudad', e.target.value)
                            }
                            placeholder="Caracas..."
                            className="text-xs"
                          />
                        </div>

                        {/* Estado (Región) */}
                        <div className="space-y-1">
                          <label className="text-xs font-medium text-gray-600">
                            Estado (Región)
                          </label>
                          <Input
                            type="text"
                            value={dirObj.estado || ''}
                            onChange={e =>
                              updateDireccionField('estado', e.target.value)
                            }
                            placeholder="Miranda, Caracas..."
                            className="text-xs"
                          />
                        </div>

                        {/* Descripción (ancho completo) */}
                        <div className="col-span-2 space-y-1">
                          <label className="text-xs font-medium text-gray-600">
                            Descripción Adicional
                          </label>
                          <Textarea
                            value={dirObj.descripcion || ''}
                            onChange={e =>
                              updateDireccionField(
                                'descripcion',
                                e.target.value
                              )
                            }
                            placeholder="Casa de color blanco, entre Av. A y B, próximo a esquina..."
                            rows={2}
                            className="text-xs"
                          />
                        </div>
                      </div>
                    )
                  })()}
                </div>

                {/* Notas */}
                <div className="space-y-2 md:col-span-2">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <FileText className="h-4 w-4 text-gray-500" />
                    Notas
                  </label>
                  <Textarea
                    value={clienteData.notas || ''}
                    onChange={e => {
                      setClienteData({ ...clienteData, notas: e.target.value })
                      setCambios({ ...cambios, cliente: true })
                    }}
                    placeholder="Observaciones adicionales del cliente..."
                    rows={2}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Préstamo */}

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5 text-green-600" />
                  Datos del Préstamo
                </CardTitle>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* Estado préstamo */}
                <div className="rounded-lg border-2 border-indigo-200 bg-indigo-50/80 p-4">
                  <p className="mb-2 text-sm font-semibold text-indigo-900">
                    Estado del préstamo
                  </p>
                  <Select
                    value={prestamoData.estado || ''}
                    onValueChange={v => {
                      setPrestamoData({ ...prestamoData, estado: v })
                      setCambios({ ...cambios, prestamo: true })
                    }}
                  >
                    <SelectTrigger className="border-indigo-200 bg-white">
                      <SelectValue placeholder="Seleccionar estado" />
                    </SelectTrigger>
                    <SelectContent>
                      {opcionesSelectEstadoPrestamoRevision(
                        prestamoData.estado
                      ).map(o => (
                        <SelectItem key={o.value} value={o.value}>
                          {o.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  {/* Total Financiamiento */}
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Total Financiamiento (USD){' '}
                      <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <DollarSign className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                      <Input
                        type="number"
                        step="0.01"
                        min="0.01"
                        value={prestamoData.total_financiamiento || ''}
                        onChange={e => {
                          setPrestamoData({
                            ...prestamoData,
                            total_financiamiento:
                              parseFloat(e.target.value) || 0,
                          })
                          setCambios({ ...cambios, prestamo: true })
                          if (errores['total_financiamiento'])
                            setErrores({ ...errores, total_financiamiento: '' })
                        }}
                        className={`pl-10 ${errores['total_financiamiento'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
                        placeholder="0.00"
                      />
                    </div>
                    {errores['total_financiamiento'] && (
                      <p className="text-xs text-red-600">
                        {errores['total_financiamiento']}
                      </p>
                    )}
                  </div>

                  {/* Cuota Período */}
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Cuota por Período (USD)
                    </label>
                    <div className="relative">
                      <DollarSign className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={prestamoData.cuota_periodo ?? ''}
                        onChange={e => {
                          setPrestamoData({
                            ...prestamoData,
                            cuota_periodo: parseFloat(e.target.value) || 0,
                          })
                          setCambios({ ...cambios, prestamo: true })
                          if (errores['cuota_periodo'])
                            setErrores({ ...errores, cuota_periodo: '' })
                        }}
                        className={`pl-10 ${errores['cuota_periodo'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
                        placeholder="0.00"
                      />
                    </div>
                    {errores['cuota_periodo'] && (
                      <p className="text-xs text-red-600">
                        {errores['cuota_periodo']}
                      </p>
                    )}
                  </div>

                  {/* Número de Cuotas */}
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Número de Cuotas <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="number"
                      min="1"
                      step="1"
                      value={prestamoData.numero_cuotas || ''}
                      onChange={e => {
                        const nextN = parseInt(e.target.value, 10) || 0
                        setPrestamoData({
                          ...prestamoData,
                          numero_cuotas: nextN,
                        })
                        setCuotasData(prev =>
                          mergeCuotasParaMostrar(prev, nextN)
                        )
                        setCambios({ ...cambios, prestamo: true, cuotas: true })
                        if (errores['numero_cuotas'])
                          setErrores({ ...errores, numero_cuotas: '' })
                      }}
                      title="En revisión manual puede ajustar el plazo; el servidor rechaza cambios inválidos (p. ej. préstamo liquidado con reglas de cuotas)."
                      className={`${errores['numero_cuotas'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
                      placeholder="0"
                    />
                    {errores['numero_cuotas'] && (
                      <p className="text-xs text-red-600">
                        {errores['numero_cuotas']}
                      </p>
                    )}
                  </div>

                  {/* Tasa de Interés - OCULTO (0% por defecto) */}

                  {/* Modalidad Pago */}
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Modalidad de Pago
                    </label>
                    <Select
                      value={prestamoData.modalidad_pago || '-'}
                      onValueChange={v => {
                        setPrestamoData({
                          ...prestamoData,
                          modalidad_pago: v === '-' ? '' : v,
                        })
                        setCambios({ ...cambios, prestamo: true })
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Seleccionar" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="-">-</SelectItem>
                        <SelectItem value="MENSUAL">Mensual</SelectItem>
                        <SelectItem value="QUINCENAL">Quincenal</SelectItem>
                        <SelectItem value="SEMANAL">Semanal</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Valor Activo - OCULTO */}

                  {/* Bloque: fecha de requerimiento (actualización manual en BD). */}
                  <div className="rounded-lg border border-gray-200 bg-slate-50/80 p-3 md:col-span-2">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium">
                        Fecha de requerimiento
                      </span>
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
                        Actualización manual
                      </span>
                    </div>
                    <p className="mb-2 text-xs text-gray-600">
                      Fecha de solicitud/requerimiento del expediente (tabla{' '}
                      <code className="rounded bg-white px-1">
                        prestamos.fecha_requerimiento
                      </code>
                      ). Se muestra el valor cargado desde la base; corríjala
                      aquí si debe alinearse con otros datos del expediente. No
                      altera la tabla de cuotas por sí sola.
                    </p>
                    <div className="relative min-w-0 max-w-md">
                      <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                      <Input
                        type="date"
                        disabled={soloLectura}
                        value={formatDateForInput(
                          prestamoData.fecha_requerimiento
                        )}
                        onChange={e => {
                          formDirtyRef.current = true
                          const v = e.target.value || null
                          setPrestamoData({
                            ...prestamoData,
                            fecha_requerimiento: v,
                          })
                          setCambios({ ...cambios, prestamo: true })
                        }}
                        className="pl-10"
                      />
                    </div>
                  </div>

                  {/* Bloque: fecha de aprobación (manual; en BD se guarda el día anterior al selector). */}
                  <div className="rounded-lg border border-gray-200 bg-slate-50/80 p-3 md:col-span-2">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium">
                        Fecha de aprobación
                      </span>
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
                        Actualización manual
                      </span>
                    </div>
                    <p className="mb-2 text-xs text-gray-600">
                      Columna{' '}
                      <code className="rounded bg-white px-1">
                        prestamos.fecha_aprobacion
                      </code>{' '}
                      y{' '}
                      <code className="rounded bg-white px-1">
                        prestamos.fecha_base_calculo
                      </code>
                      . En esta pantalla, al guardar o al usar «Recalcular
                      vencimientos», el valor persistido en base es el{' '}
                      <strong className="font-medium">
                        día calendario anterior
                      </strong>{' '}
                      al indicado en el selector (inicio de ese día). Es
                      obligatoria si el estado es Aprobado, Desembolsado o
                      Liquidado. «Recalcular vencimientos» usa esa fecha
                      persistida junto con plazo, cuota por período y modalidad.
                    </p>
                    <div className="relative min-w-0 max-w-md">
                      <Calendar className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                      <Input
                        type="date"
                        disabled={soloLectura}
                        value={formatDateForInput(
                          prestamoData.fecha_aprobacion
                        )}
                        onChange={e => {
                          formDirtyRef.current = true
                          const v = e.target.value || null
                          setPrestamoData({
                            ...prestamoData,
                            fecha_aprobacion: v,
                          })
                          setCambios({ ...cambios, prestamo: true })
                          if (errores['fecha_aprobacion']) {
                            setErrores({
                              ...errores,
                              fecha_aprobacion: '',
                            })
                          }
                        }}
                        className={`pl-10 ${errores['fecha_aprobacion'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
                      />
                    </div>
                    {errores['fecha_aprobacion'] && (
                      <p className="mt-2 text-xs text-red-600">
                        {errores['fecha_aprobacion']}
                      </p>
                    )}
                    <Button
                      type="button"
                      variant="outline"
                      className="mt-3 w-full max-w-md shrink-0 sm:w-auto"
                      disabled={soloLectura || recalculandoFechasCuotas}
                      onClick={handleGuardarFechaYRecalcularVencimientos}
                      title="Persiste en BD las condiciones del préstamo (formulario) y reconstruye la tabla de cuotas (plazo, montos y vencimientos); luego reaplica pagos pendientes a cuotas."
                    >
                      {recalculandoFechasCuotas ? (
                        <Loader2 className="mr-2 h-4 w-4 shrink-0 animate-spin" />
                      ) : (
                        <RefreshCw className="mr-2 h-4 w-4 shrink-0" />
                      )}
                      Recalcular vencimientos
                    </Button>
                  </div>

                  {/* Fecha Base Cálculo - OCULTO */}
                  {/* Sincronizada en servidor/BD con fecha_aprobacion cuando aplica; no se edita aquí. */}

                  {/* Producto - OCULTO */}
                  {/* Este campo se maneja en el módulo de gestión de préstamos, no en revisión manual */}

                  {/* Concesionario */}
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Concesionario
                    </label>
                    <Select
                      value={prestamoData.concesionario || '-'}
                      onValueChange={v => {
                        setPrestamoData({
                          ...prestamoData,
                          concesionario: v === '-' ? '' : v,
                        })
                        setCambios({ ...cambios, prestamo: true })
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="-" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="-">-</SelectItem>
                        {prestamoData.concesionario &&
                          !concesionarios.some(
                            (c: any) => c.nombre === prestamoData.concesionario
                          ) && (
                            <SelectItem value={prestamoData.concesionario}>
                              {prestamoData.concesionario}
                            </SelectItem>
                          )}
                        {concesionarios.map((c: any) => (
                          <SelectItem key={c.id} value={c.nombre}>
                            {c.nombre}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Analista */}
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Analista
                    </label>
                    <Select
                      value={prestamoData.analista || '-'}
                      onValueChange={v => {
                        setPrestamoData({
                          ...prestamoData,
                          analista: v === '-' ? '' : v,
                        })
                        setCambios({ ...cambios, prestamo: true })
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="-" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="-">-</SelectItem>
                        {prestamoData.analista &&
                          !analistas.some(
                            (a: any) => a.nombre === prestamoData.analista
                          ) && (
                            <SelectItem value={prestamoData.analista}>
                              {prestamoData.analista}
                            </SelectItem>
                          )}
                        {analistas.map((a: any) => (
                          <SelectItem key={a.id} value={a.nombre}>
                            {a.nombre}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Modelo Vehículo */}
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Modelo de Vehículo
                    </label>
                    <Select
                      value={prestamoData.modelo_vehiculo || '-'}
                      onValueChange={v => {
                        setPrestamoData({
                          ...prestamoData,
                          modelo_vehiculo: v === '-' ? '' : v,
                        })
                        setCambios({ ...cambios, prestamo: true })
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="-" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="-">-</SelectItem>
                        {prestamoData.modelo_vehiculo &&
                          !modelosVehiculos.some(
                            (m: any) =>
                              m.modelo === prestamoData.modelo_vehiculo
                          ) && (
                            <SelectItem value={prestamoData.modelo_vehiculo}>
                              {prestamoData.modelo_vehiculo}
                            </SelectItem>
                          )}
                        {modelosVehiculos.map((m: any) => (
                          <SelectItem key={m.id} value={m.modelo}>
                            {m.modelo}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Cédula préstamo */}
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Cédula (registro préstamo)
                    </label>
                    <div className="relative">
                      <CreditCard className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                      <Input
                        type="text"
                        value={prestamoData.cedula || ''}
                        onChange={e => {
                          setPrestamoData({
                            ...prestamoData,
                            cedula: e.target.value,
                          })
                          setCambios({ ...cambios, prestamo: true })
                        }}
                        className="pl-10"
                        placeholder="Cédula"
                      />
                    </div>
                  </div>

                  {/* Nombres préstamo */}
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Nombres (registro préstamo)
                    </label>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                      <Input
                        type="text"
                        value={prestamoData.nombres || ''}
                        onChange={e => {
                          setPrestamoData({
                            ...prestamoData,
                            nombres: e.target.value,
                          })
                          setCambios({ ...cambios, prestamo: true })
                        }}
                        className="pl-10"
                        placeholder="Nombres"
                      />
                    </div>
                  </div>

                  {/* Usuario Proponente */}
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Usuario Proponente
                    </label>
                    <Input
                      type="text"
                      value={prestamoData.usuario_proponente || ''}
                      onChange={e => {
                        setPrestamoData({
                          ...prestamoData,
                          usuario_proponente: e.target.value,
                        })
                        setCambios({ ...cambios, prestamo: true })
                      }}
                      placeholder="Usuario proponente"
                    />
                  </div>

                  {/* Usuario Aprobador - OCULTO */}
                </div>

                {/* Observaciones - ancho completo */}
                <div>
                  <label className="mb-1 block text-sm font-medium">
                    Observaciones
                  </label>
                  <Textarea
                    value={prestamoData.observaciones || ''}
                    onChange={e => {
                      setPrestamoData({
                        ...prestamoData,
                        observaciones: e.target.value,
                      })
                      setCambios({ ...cambios, prestamo: true })
                    }}
                    placeholder="Ingresa observaciones del préstamo..."
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Pagos reales en tabla pagos (mismo origen que carga masiva / módulo Pagos) */}
            {cedulaParaPagosRealizados ? (
              <>
                <Card>
                  <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2 space-y-0 pb-2">
                    <div>
                      <CardTitle className="flex items-center gap-2 text-base">
                        <CreditCard className="h-5 w-5" />
                        Pagos registrados en cartera
                      </CardTitle>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Cédula {cedulaParaPagosRealizados}: fecha, monto (USD),
                        banco, documento y crédito asociado. Cada alta o edición
                        exige URL de comprobante en el formulario y respeta los
                        validadores del módulo Pagos (clave única comprobante +
                        código opcional). Si la misma clave aparece dos veces en
                        esta página se resalta en la tabla. Use «Agregar pago»,
                        «Editar» o «Eliminar»; «Aplicar a cuotas (cascada)»
                        adjudica en la BD los pagos elegibles de este crédito a
                        las cuotas en orden de vencimiento (cascada por número
                        de cuota; pagos ordenados por fecha). Solo entran pagos
                        conciliados, verificados o en estado Pagado, sin filas
                        en cuota_pagos. La tabla se actualiza al guardar y
                        también al volver a la pestaña o cada minuto.
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-wrap items-center gap-2">
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        className="gap-2"
                        disabled={
                          soloLectura ||
                          aplicarCascadaPagosMutation.isPending ||
                          !prestamoData.prestamo_id ||
                          Number(prestamoData.prestamo_id) <= 0
                        }
                        onClick={() => aplicarCascadaPagosMutation.mutate()}
                        title={
                          soloLectura
                            ? 'Revisión cerrada: solo lectura'
                            : 'Guarda primero las condiciones del préstamo en BD; si faltan cuotas respecto al plazo, reconstruye la tabla y aplica pagos en cascada.'
                        }
                      >
                        {aplicarCascadaPagosMutation.isPending ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <DollarSign className="h-4 w-4" />
                        )}
                        Aplicar a cuotas (cascada)
                      </Button>
                      <Button
                        type="button"
                        variant="default"
                        size="sm"
                        className="gap-2"
                        disabled={soloLectura}
                        onClick={abrirAgregarPagoRevision}
                        title={
                          soloLectura
                            ? 'Revision cerrada: solo lectura'
                            : 'Registrar un pago para esta cedula'
                        }
                      >
                        <Plus className="h-4 w-4" />
                        Agregar pago
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="gap-2"
                        disabled={
                          loadingPagosRealizados || fetchingPagosRealizados
                        }
                        onClick={() => void refetchPagosRealizados()}
                      >
                        <RefreshCw
                          className={`h-4 w-4 ${fetchingPagosRealizados ? 'animate-spin' : ''}`}
                        />
                        Actualizar
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {loadingPagosRealizados && !pagosRealizadosData ? (
                      <div className="flex items-center gap-2 py-8 text-muted-foreground">
                        <Loader2 className="h-5 w-5 animate-spin" />
                        Cargando pagos…
                      </div>
                    ) : !pagosRealizadosData?.pagos?.length ? (
                      <div className="space-y-3 py-6">
                        <p className="text-sm text-muted-foreground">
                          No hay filas en la tabla de pagos para esta cédula
                          todavía. Puede registrar el primero con «Agregar
                          pago».
                        </p>
                        {!soloLectura && (
                          <Button
                            type="button"
                            size="sm"
                            className="gap-2"
                            onClick={abrirAgregarPagoRevision}
                          >
                            <Plus className="h-4 w-4" />
                            Agregar pago
                          </Button>
                        )}
                      </div>
                    ) : (
                      <>
                        {pagosRealizadosData.sum_monto_pagado_cedula !=
                          null && (
                          <p className="mb-3 text-sm font-medium text-foreground">
                            Total acumulado (todos los pagos de la cédula): $
                            {Number(
                              pagosRealizadosData.sum_monto_pagado_cedula
                            ).toFixed(2)}{' '}
                            USD
                          </p>
                        )}
                        <div className="overflow-x-auto rounded-lg border">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead className="whitespace-nowrap">
                                  ID
                                </TableHead>
                                <TableHead className="whitespace-nowrap">
                                  Fecha pago
                                </TableHead>
                                <TableHead className="whitespace-nowrap text-right">
                                  Monto USD
                                </TableHead>
                                <TableHead className="whitespace-nowrap">
                                  Banco
                                </TableHead>
                                <TableHead className="whitespace-nowrap">
                                  Nº documento
                                </TableHead>
                                <TableHead className="whitespace-nowrap">
                                  Crédito
                                </TableHead>
                                <TableHead className="whitespace-nowrap">
                                  Estado
                                </TableHead>
                                <TableHead
                                  className="whitespace-nowrap text-center"
                                  title="Marca validación para cartera (conciliado o verificado Sí en BD), elegible para «Aplicar pagos a cuotas». Tras guardar, si no hubo abono en cuotas el servidor puede dejar verificado Sí y conciliado no: el casillero sigue marcado."
                                >
                                  Cartera
                                </TableHead>
                                <TableHead>Notas</TableHead>
                                <TableHead className="min-w-[88px] whitespace-nowrap text-right">
                                  Acciones
                                </TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {pagosRegistradosOrdenados.map((pago: Pago) => {
                                const docKey =
                                  claveDocumentoPagoListaNormalizada(
                                    pago.numero_documento,
                                    pago.codigo_documento ?? null
                                  )
                                const documentoDuplicadoEnPagina =
                                  !!docKey &&
                                  (conteoDocumentoPagosRevision.get(docKey) ||
                                    0) > 1
                                return (
                                  <TableRow key={pago.id}>
                                    <TableCell className="font-mono text-xs">
                                      {pago.id}
                                    </TableCell>
                                    <TableCell className="whitespace-nowrap">
                                      {formatDate(pago.fecha_pago)}
                                    </TableCell>
                                    <TableCell className="text-right font-medium">
                                      $
                                      {typeof pago.monto_pagado === 'number'
                                        ? pago.monto_pagado.toFixed(2)
                                        : parseFloat(
                                            String(pago.monto_pagado || 0)
                                          ).toFixed(2)}
                                    </TableCell>
                                    <TableCell className="max-w-[180px] truncate text-sm">
                                      {pago.institucion_bancaria?.trim()
                                        ? pago.institucion_bancaria
                                        : '-'}
                                    </TableCell>
                                    <TableCell
                                      className={`max-w-[240px] font-mono text-xs ${
                                        documentoDuplicadoEnPagina
                                          ? 'bg-orange-100 text-orange-950'
                                          : ''
                                      }`}
                                      title={
                                        documentoDuplicadoEnPagina
                                          ? 'Misma clave comprobante + código aparece más de una vez en esta página.'
                                          : undefined
                                      }
                                    >
                                      <div className="flex min-w-0 items-center gap-1">
                                        <span className="min-w-0 truncate">
                                          {textoDocumentoPagoParaListado(
                                            pago.numero_documento,
                                            pago.codigo_documento
                                          )}
                                        </span>
                                        <Button
                                          type="button"
                                          variant="ghost"
                                          size="sm"
                                          className="h-7 w-7 shrink-0 p-0"
                                          disabled={
                                            !esUrlComprobanteImagenConAuth(
                                              pago.link_comprobante || ''
                                            )
                                          }
                                          title={
                                            esUrlComprobanteImagenConAuth(
                                              pago.link_comprobante || ''
                                            )
                                              ? 'Ver comprobante guardado en el sistema'
                                              : pago.link_comprobante?.trim()
                                                ? 'Solo enlace externo; use Editar pago para subir el comprobante al sistema.'
                                                : 'Sin comprobante en el sistema'
                                          }
                                          aria-label="Ver comprobante del sistema"
                                          onClick={() => {
                                            const u =
                                              pago.link_comprobante?.trim()
                                            if (
                                              u &&
                                              esUrlComprobanteImagenConAuth(u)
                                            ) {
                                              void abrirStaffComprobanteDesdeHref(
                                                u
                                              )
                                            }
                                          }}
                                        >
                                          <Eye className="h-4 w-4" />
                                        </Button>
                                      </div>
                                    </TableCell>
                                    <TableCell className="whitespace-nowrap">
                                      {pago.prestamo_id != null
                                        ? pago.prestamo_id
                                        : '-'}
                                    </TableCell>
                                    <TableCell>
                                      {badgeEstadoPagoRegistrado(
                                        (
                                          pago.estado || 'PENDIENTE'
                                        ).toUpperCase()
                                      )}
                                    </TableCell>
                                    <TableCell className="text-center align-middle">
                                      <input
                                        type="checkbox"
                                        className="h-4 w-4 cursor-pointer rounded border-input accent-primary disabled:cursor-not-allowed disabled:opacity-50"
                                        checked={pagoValidadoCarteraRevisionRow(
                                          pago
                                        )}
                                        disabled={
                                          soloLectura ||
                                          conciliandoPagoId === pago.id ||
                                          eliminandoPagoId === pago.id ||
                                          pagoEstadoExcluyeToggleConciliadoRevision(
                                            pago.estado
                                          ) ||
                                          pagoCarteraRevisionBloquearToggleCerrado(
                                            pago
                                          )
                                        }
                                        title={
                                          soloLectura
                                            ? 'Revisión cerrada: solo lectura'
                                            : pagoCarteraRevisionBloquearToggleCerrado(
                                                  pago
                                                )
                                              ? 'Pago aplicado a cuotas con cartera validada (Pagado): no se puede quitar la validación aquí'
                                              : pagoEstadoExcluyeToggleConciliadoRevision(
                                                    pago.estado
                                                  )
                                                ? 'Estado del pago no admite cambiar validación aquí'
                                                : pagoValidadoCarteraRevisionRow(
                                                      pago
                                                    )
                                                  ? 'Quitar validación cartera (conciliado no, verificado NO)'
                                                  : 'Validar para cartera (conciliado; si no abona cuotas puede quedar verificado Sí)'
                                        }
                                        onChange={e => {
                                          void toggleConciliadoPagoRevision(
                                            pago,
                                            e.target.checked
                                          )
                                        }}
                                        aria-label={`Validación cartera pago ${pago.id}`}
                                      />
                                    </TableCell>
                                    <TableCell className="max-w-[220px] truncate text-sm text-muted-foreground">
                                      {pago.notas?.trim() ? pago.notas : '-'}
                                    </TableCell>
                                    <TableCell className="text-right">
                                      <div className="flex flex-wrap items-center justify-end gap-1">
                                        <Button
                                          type="button"
                                          variant="ghost"
                                          size="sm"
                                          className="h-8 w-8 shrink-0 p-0"
                                          disabled={soloLectura}
                                          onClick={() =>
                                            abrirEditarPagoRevision(pago)
                                          }
                                          title={
                                            soloLectura
                                              ? 'Revision cerrada: solo lectura'
                                              : 'Editar pago'
                                          }
                                          aria-label="Editar pago"
                                        >
                                          <Edit className="h-4 w-4" />
                                        </Button>
                                        <Button
                                          type="button"
                                          variant="ghost"
                                          size="sm"
                                          className="h-8 w-8 shrink-0 p-0 text-destructive hover:text-destructive"
                                          disabled={
                                            soloLectura ||
                                            eliminandoPagoId === pago.id
                                          }
                                          onClick={() =>
                                            void eliminarPagoRevision(pago)
                                          }
                                          title={
                                            soloLectura
                                              ? 'Revision cerrada: solo lectura'
                                              : 'Eliminar pago'
                                          }
                                          aria-label="Eliminar pago"
                                        >
                                          {eliminandoPagoId === pago.id ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                          ) : (
                                            <Trash2 className="h-4 w-4" />
                                          )}
                                        </Button>
                                      </div>
                                    </TableCell>
                                  </TableRow>
                                )
                              })}
                            </TableBody>
                          </Table>
                        </div>
                        {pagosRealizadosData.total_pages > 1 && (
                          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
                            <span>
                              Página {pagosRealizadosData.page} de{' '}
                              {pagosRealizadosData.total_pages} (
                              {pagosRealizadosData.total} pagos)
                            </span>
                            <div className="flex gap-2">
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                disabled={pagePagosRegistrados <= 1}
                                onClick={() =>
                                  setPagePagosRegistrados(p =>
                                    Math.max(1, p - 1)
                                  )
                                }
                              >
                                Anterior
                              </Button>
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                disabled={
                                  pagePagosRegistrados >=
                                  pagosRealizadosData.total_pages
                                }
                                onClick={() =>
                                  setPagePagosRegistrados(p =>
                                    Math.min(
                                      pagosRealizadosData.total_pages,
                                      p + 1
                                    )
                                  )
                                }
                              >
                                Siguiente
                              </Button>
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </CardContent>
                </Card>

                <Card className="overflow-hidden border-slate-200/80 shadow-sm">
                  <CardHeader className="space-y-4 border-b border-slate-200/80 bg-gradient-to-br from-slate-50 via-white to-slate-50/90 pb-4">
                    <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                      <div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:items-start sm:gap-3">
                        <div
                          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary shadow-sm ring-1 ring-primary/10"
                          aria-hidden
                        >
                          <BarChart3 className="h-5 w-5" />
                        </div>
                        <div className="min-w-0 space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <CardTitle className="text-lg font-semibold tracking-tight">
                              Resumen: pagos del crédito vs cuotas
                            </CardTitle>
                            {hayPendienteRevision && !soloLectura ? (
                              <Badge
                                variant="outline"
                                className="border-amber-400/80 bg-amber-50 text-amber-950"
                              >
                                Cambios sin confirmar
                              </Badge>
                            ) : null}
                          </div>
                          <p className="max-w-prose text-sm text-muted-foreground">
                            Cifras del crédito en revisión (no solo la página
                            visible de la tabla). Contrasta montos en{' '}
                            <span className="font-medium text-foreground">
                              pagos
                            </span>{' '}
                            con lo aplicado en el{' '}
                            <span className="font-medium text-foreground">
                              plan de cuotas
                            </span>
                            .
                          </p>
                        </div>
                      </div>
                      <div
                        className="flex flex-wrap gap-2 xl:max-w-[min(100%,36rem)] xl:justify-end"
                        role="toolbar"
                        aria-label="Acciones desde el resumen"
                      >
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="gap-1.5"
                          disabled={
                            loadingPagosRealizados || fetchingPagosRealizados
                          }
                          onClick={() => void refetchPagosRealizados()}
                        >
                          <RefreshCw
                            className={`h-4 w-4 ${fetchingPagosRealizados ? 'animate-spin' : ''}`}
                          />
                          Actualizar datos
                        </Button>
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          className="gap-1.5"
                          disabled={
                            soloLectura ||
                            aplicarCascadaPagosMutation.isPending ||
                            !prestamoData.prestamo_id ||
                            Number(prestamoData.prestamo_id) <= 0
                          }
                          onClick={() => aplicarCascadaPagosMutation.mutate()}
                          title={
                            soloLectura
                              ? 'Revisión cerrada: solo lectura'
                              : 'Guarda condiciones del préstamo; si faltan cuotas en BD respecto al plazo, reconstruye y aplica pagos en cascada.'
                          }
                        >
                          {aplicarCascadaPagosMutation.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <DollarSign className="h-4 w-4" />
                          )}
                          Cascada
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4 pt-5 text-sm">
                    {!auditoriaCoherenciaActiva ? (
                      <div className="rounded-lg border border-amber-200 bg-amber-50/90 px-4 py-3 text-amber-950 shadow-sm">
                        <span className="flex items-start gap-3">
                          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                          <span>
                            El panel de coherencia (cuotas vs financiamiento y
                            pagos) se activa cuando el préstamo está en{' '}
                            <span className="font-semibold">Aprobado</span> o{' '}
                            <span className="font-semibold">Liquidado</span>.
                            Estado actual:{' '}
                            <span className="font-semibold">
                              {estadoPrestamoNorm || '-'}
                            </span>
                            . Registre pagos en la tabla de pagos y guarde con
                            los botones al final del formulario.
                          </span>
                        </span>
                      </div>
                    ) : loadingPagosRealizados &&
                      !pagosRealizadosData?.resumen_prestamo ? (
                      <div className="flex items-center gap-2 rounded-lg border bg-muted/20 px-4 py-6 text-muted-foreground">
                        <Loader2 className="h-5 w-5 animate-spin" />
                        Cargando resumen del crédito…
                      </div>
                    ) : !pagosRealizadosData?.resumen_prestamo ? (
                      <div className="rounded-lg border border-dashed bg-muted/10 px-4 py-4 text-muted-foreground">
                        No se recibió el agregado{' '}
                        <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                          resumen_prestamo
                        </span>{' '}
                        del servidor. Pulse «Actualizar datos» o revise el
                        backend.
                      </div>
                    ) : (
                      (() => {
                        const rp = pagosRealizadosData.resumen_prestamo
                        const tf =
                          Number(prestamoData.total_financiamiento) || 0
                        const {
                          sumMonto: sumCuotasMonto,
                          sumPagado: sumCuotasPagado,
                        } = agregadosCuotasRevision
                        const sumPagosCredito =
                          Number(rp.suma_monto_pagado) || 0
                        const cantPagosCredito = Number(rp.cantidad) || 0
                        const diffPlanVsFin = sumCuotasMonto - tf
                        const diffPagosVsCuotas =
                          sumPagosCredito - sumCuotasPagado
                        const faltaCubrirPlan = Math.max(
                          0,
                          sumCuotasMonto - sumCuotasPagado
                        )
                        const planAlineadoFin =
                          Math.abs(diffPlanVsFin) <= COHERENCIA_USD_TOL
                        const pagosAlineadosCuotas =
                          Math.abs(diffPagosVsCuotas) <= COHERENCIA_USD_TOL
                        const pendN = Number(rp.cantidad_pendiente) || 0
                        const pendSum = Number(rp.suma_monto_pendiente) || 0
                        const pagN = Number(rp.cantidad_pagado) || 0
                        const pagSum = Number(rp.suma_monto_estado_pagado) || 0
                        const todoOk = planAlineadoFin && pagosAlineadosCuotas
                        const pctCoberturaPlan =
                          sumCuotasMonto > 0
                            ? Math.min(
                                100,
                                Math.round(
                                  (sumCuotasPagado / sumCuotasMonto) * 1000
                                ) / 10
                              )
                            : 0

                        const sugerencias: string[] = []
                        if (!planAlineadoFin) {
                          sugerencias.push(
                            `Cuotas vs financiamiento: la suma de montos de cuotas (${sumCuotasMonto.toFixed(2)} USD) no coincide con el total declarado (${tf.toFixed(2)} USD); diferencia ${diffPlanVsFin.toFixed(2)}. Revise montos de cuotas o el total del préstamo y guarde.`
                          )
                        }
                        if (!pagosAlineadosCuotas) {
                          if (diffPagosVsCuotas > COHERENCIA_USD_TOL) {
                            sugerencias.push(
                              `Pagos vs aplicado: hay ${diffPagosVsCuotas.toFixed(2)} USD más en pagos del crédito que en total aplicado en cuotas. Pruebe «Cascada», revise pagos sin aplicar o duplicados.`
                            )
                          } else {
                            sugerencias.push(
                              `Pagos vs aplicado: faltan ${Math.abs(diffPagosVsCuotas).toFixed(2)} USD en pagos del crédito respecto a lo aplicado en cuotas. Revise registros en la tabla de pagos o aplicaciones.`
                            )
                          }
                        }
                        if (pendN > 0 && estadoPrestamoNorm === 'APROBADO') {
                          sugerencias.push(
                            `Hay ${pendN} pago(s) en estado Pendiente por ${pendSum.toFixed(2)} USD; valide cartera y luego cascada si corresponde.`
                          )
                        }
                        if (
                          estadoPrestamoNorm === 'LIQUIDADO' &&
                          faltaCubrirPlan > COHERENCIA_USD_TOL
                        ) {
                          sugerencias.push(
                            'Crédito liquidado pero el cronograma muestra saldo pendiente: conviene revisar cuotas y pagos antes de cerrar la revisión.'
                          )
                        }

                        return (
                          <div className="space-y-4">
                            <div className="flex flex-wrap items-center gap-2">
                              <Badge
                                variant="outline"
                                className={
                                  todoOk
                                    ? 'border-emerald-300 bg-emerald-50 text-emerald-950'
                                    : 'border-amber-400 bg-amber-50 text-amber-950'
                                }
                              >
                                {todoOk
                                  ? 'Cuadre: coherente'
                                  : 'Cuadre: revisar'}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                Tolerancia numérica:{' '}
                                {COHERENCIA_USD_TOL.toFixed(2)} USD
                              </span>
                            </div>

                            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                              <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-sm ring-1 ring-slate-100">
                                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                                  Pagos (este crédito, BD)
                                </p>
                                <p className="mt-2 text-2xl font-bold tabular-nums text-foreground">
                                  ${sumPagosCredito.toFixed(2)}{' '}
                                  <span className="text-base font-semibold text-muted-foreground">
                                    USD
                                  </span>
                                </p>
                                <p className="mt-1 text-xs text-muted-foreground">
                                  {cantPagosCredito}{' '}
                                  {cantPagosCredito === 1
                                    ? 'registro'
                                    : 'registros'}{' '}
                                  en base
                                </p>
                                <dl className="mt-3 space-y-1.5 border-t border-slate-100 pt-3 text-xs">
                                  <div className="flex justify-between gap-2">
                                    <dt className="text-muted-foreground">
                                      Pendiente (estado)
                                    </dt>
                                    <dd className="font-medium tabular-nums">
                                      {pendN} · ${pendSum.toFixed(2)}
                                    </dd>
                                  </div>
                                  <div className="flex justify-between gap-2">
                                    <dt className="text-muted-foreground">
                                      Pagado (estado)
                                    </dt>
                                    <dd className="font-medium tabular-nums">
                                      {pagN} · ${pagSum.toFixed(2)}
                                    </dd>
                                  </div>
                                </dl>
                              </div>

                              <div className="rounded-xl border border-slate-200/90 bg-white p-4 shadow-sm ring-1 ring-slate-100">
                                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                                  Plan de cuotas (formulario / BD)
                                </p>
                                <p className="mt-2 text-2xl font-bold tabular-nums text-foreground">
                                  ${sumCuotasMonto.toFixed(2)}{' '}
                                  <span className="text-base font-semibold text-muted-foreground">
                                    USD
                                  </span>
                                </p>
                                <p className="mt-1 text-xs text-muted-foreground">
                                  Aplicado en cuotas:{' '}
                                  <span className="font-semibold text-foreground">
                                    ${sumCuotasPagado.toFixed(2)} USD
                                  </span>
                                </p>
                                <dl className="mt-3 space-y-1.5 border-t border-slate-100 pt-3 text-xs">
                                  <div className="flex justify-between gap-2">
                                    <dt className="text-muted-foreground">
                                      Financiamiento declarado
                                    </dt>
                                    <dd className="font-medium tabular-nums">
                                      ${tf.toFixed(2)}
                                    </dd>
                                  </div>
                                  <div className="flex justify-between gap-2">
                                    <dt className="text-muted-foreground">
                                      Delta cuotas - financiamiento
                                    </dt>
                                    <dd
                                      className={`font-semibold tabular-nums ${planAlineadoFin ? 'text-emerald-700' : 'text-amber-800'}`}
                                    >
                                      {diffPlanVsFin >= 0 ? '+' : ''}
                                      {diffPlanVsFin.toFixed(2)}
                                    </dd>
                                  </div>
                                </dl>
                              </div>

                              <div
                                className={`rounded-xl border p-4 shadow-sm ring-1 sm:col-span-2 xl:col-span-1 ${
                                  pagosAlineadosCuotas
                                    ? 'border-emerald-200/90 bg-emerald-50/40 ring-emerald-100'
                                    : diffPagosVsCuotas > COHERENCIA_USD_TOL
                                      ? 'border-sky-200/90 bg-sky-50/50 ring-sky-100'
                                      : 'border-orange-200/90 bg-orange-50/50 ring-orange-100'
                                }`}
                              >
                                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                                  Pagos del crédito - aplicado en cuotas
                                </p>
                                <p
                                  className={`mt-2 text-2xl font-bold tabular-nums ${
                                    pagosAlineadosCuotas
                                      ? 'text-emerald-800'
                                      : diffPagosVsCuotas > COHERENCIA_USD_TOL
                                        ? 'text-sky-900'
                                        : 'text-orange-900'
                                  }`}
                                >
                                  {diffPagosVsCuotas >= 0 ? '+' : '-'}$
                                  {Math.abs(diffPagosVsCuotas).toFixed(2)} USD
                                </p>
                                <p className="mt-1 text-xs text-muted-foreground">
                                  {pagosAlineadosCuotas
                                    ? 'Dentro de tolerancia: cartera alineada al plan.'
                                    : diffPagosVsCuotas > COHERENCIA_USD_TOL
                                      ? 'Sobrante en cartera vs cuotas.'
                                      : 'Falta monto en pagos vs lo aplicado.'}
                                </p>
                                <div className="mt-4 space-y-1.5">
                                  <div className="flex justify-between text-xs text-muted-foreground">
                                    <span>Cobertura del cronograma</span>
                                    <span className="font-medium tabular-nums text-foreground">
                                      {pctCoberturaPlan}%
                                    </span>
                                  </div>
                                  <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/80 ring-1 ring-slate-200/80">
                                    <div
                                      className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-[width] duration-300"
                                      style={{
                                        width: `${pctCoberturaPlan}%`,
                                      }}
                                    />
                                  </div>
                                  <p className="text-[11px] text-muted-foreground">
                                    Aplicado sobre suma de montos de cuotas (
                                    {sumCuotasMonto > 0
                                      ? 'proporción cubierta'
                                      : 'sin cuotas para medir'}
                                    ).
                                  </p>
                                </div>
                              </div>
                            </div>

                            {!planAlineadoFin && (
                              <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50/90 px-4 py-3 text-amber-950 shadow-sm">
                                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                                <div>
                                  <p className="font-semibold">
                                    Financiamiento vs suma de cuotas
                                  </p>
                                  <p className="mt-1 text-sm">
                                    La suma de montos de cuotas ($
                                    {sumCuotasMonto.toFixed(2)}) no coincide con
                                    el financiamiento (${tf.toFixed(2)});
                                    diferencia {diffPlanVsFin.toFixed(2)} USD.
                                  </p>
                                </div>
                              </div>
                            )}

                            <div
                              className={`flex items-start gap-3 rounded-lg border px-4 py-3 shadow-sm ${
                                pagosAlineadosCuotas
                                  ? 'border-emerald-200 bg-emerald-50/90 text-emerald-950'
                                  : diffPagosVsCuotas > COHERENCIA_USD_TOL
                                    ? 'border-sky-200 bg-sky-50/90 text-sky-950'
                                    : 'border-orange-200 bg-orange-50/90 text-orange-950'
                              }`}
                            >
                              {pagosAlineadosCuotas ? (
                                <Check className="mt-0.5 h-5 w-5 shrink-0" />
                              ) : (
                                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                              )}
                              <div className="min-w-0 space-y-1">
                                <p className="font-semibold">
                                  Pagos del crédito vs total aplicado en cuotas
                                </p>
                                {pagosAlineadosCuotas ? (
                                  <p className="text-sm">
                                    Coherente: la suma de pagos del crédito
                                    coincide con lo aplicado en cuotas
                                    (tolerancia {COHERENCIA_USD_TOL.toFixed(2)}{' '}
                                    USD).
                                  </p>
                                ) : diffPagosVsCuotas > COHERENCIA_USD_TOL ? (
                                  <p className="text-sm">
                                    <span className="font-semibold">
                                      Sobrante en cartera
                                    </span>{' '}
                                    respecto a lo aplicado:{' '}
                                    {diffPagosVsCuotas.toFixed(2)} USD. Suele
                                    deberse a pagos sin cascada o cuotas
                                    desactualizadas.
                                  </p>
                                ) : (
                                  <p className="text-sm">
                                    <span className="font-semibold">
                                      Falta en pagos
                                    </span>{' '}
                                    respecto a lo aplicado:{' '}
                                    {Math.abs(diffPagosVsCuotas).toFixed(2)}{' '}
                                    USD. Revise registros y aplicaciones.
                                  </p>
                                )}
                              </div>
                            </div>

                            <div className="rounded-xl border border-slate-200/90 bg-slate-50/50 p-4 shadow-sm">
                              <p className="text-sm font-semibold text-foreground">
                                Falta por cubrir en el plan de cuotas
                              </p>
                              <p className="mt-1 text-3xl font-bold tabular-nums tracking-tight text-foreground">
                                ${faltaCubrirPlan.toFixed(2)}{' '}
                                <span className="text-lg font-semibold text-muted-foreground">
                                  USD
                                </span>
                              </p>
                              <p className="mt-2 text-xs text-muted-foreground">
                                Saldo pendiente del cronograma (suma montos de
                                cuotas menos total aplicado).
                              </p>
                            </div>

                            {sugerencias.length > 0 ? (
                              <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm ring-1 ring-slate-100">
                                <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-foreground">
                                  <CheckSquare className="h-4 w-4 shrink-0 text-primary" />
                                  Qué revisar (priorizado)
                                </p>
                                <ul className="list-inside list-decimal space-y-2 text-sm text-muted-foreground marker:text-primary">
                                  {sugerencias.map((t, i) => (
                                    <li key={i} className="pl-0.5">
                                      {t}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            ) : null}
                          </div>
                        )
                      })()
                    )}
                  </CardContent>
                </Card>
              </>
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
                <p className="text-sm text-muted-foreground">
                  La cantidad de filas sigue el campo «Número de cuotas» del
                  préstamo (condiciones): si indica 12, se muestran las cuotas 1
                  a 12; las que aún no existen en BD aparecen en blanco hasta
                  guardar o reconstruir. El calendario depende de fechas de
                  aprobación y reglas de amortización.
                </p>
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
            onClick={handleGuardarParciales}
            disabled={soloLectura || guardandoParcial || guardandoFinal}
            className={`gap-2 ${claseResaltarGuardarRevision}`}
            title="Guarda los cambios y continúa revisando - estado cambia a ?"
          >
            <Save className="h-4 w-4" />
            Guardar Cambios
          </Button>

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

          <Button
            type="button"
            className={`gap-2 bg-green-600 text-white hover:bg-green-700 ${claseResaltarGuardarRevision}`}
            onClick={handleGuardarYCerrar}
            disabled={deshabilitarGuardarYCerrar}
            title={tituloGuardarYCerrarBoton}
          >
            {guardandoFinal ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Check className="h-4 w-4" />
            )}
            Guardar y Cerrar
          </Button>
        </div>
      </div>

      {pagoModalAbierto && pagoModalInicial != null && (
        <RegistrarPagoForm
          onClose={cerrarModalPagoRevision}
          onSuccess={onExitoModalPagoRevision}
          pagoInicial={pagoModalInicial}
          pagoId={pagoModalId}
          mostrarCampoCodigoDocumento
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
