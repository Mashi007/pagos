import { useState, useLayoutEffect, useRef, useEffect } from 'react'

import { useParams, useNavigate } from 'react-router-dom'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import { motion } from 'framer-motion'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

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
  Trash2,
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
} from 'lucide-react'

import { Input } from '../components/ui/input'

import { Textarea } from '../components/ui/textarea'

import { toast } from 'sonner'

import { revisionManualService } from '../services/revisionManualService'

import { prestamoService } from '../services/prestamoService'

import { useEstadosCliente } from '../hooks/useEstadosCliente'

import { useConcesionariosActivos } from '../hooks/useConcesionarios'

import { useAnalistasActivos } from '../hooks/useAnalistas'

import { useModelosVehiculosActivos } from '../hooks/useModelosVehiculos'

import { prestamoKeys } from '../hooks/usePrestamos'

import { codigoEstadoCuotaParaUi } from '../utils/cuotaEstadoDisplay'

/** Códigos que acepta PUT /revision-manual/cuotas/{id} (mayúsculas). */
const OPCIONES_ESTADO_CUOTA_REVISION: { value: string; label: string }[] = [
  { value: 'PENDIENTE', label: 'Pendiente' },
  { value: 'PARCIAL', label: 'Parcial' },
  { value: 'VENCIDO', label: 'Vencido' },
  { value: 'MORA', label: 'Mora' },
  { value: 'PAGADO', label: 'Pagado' },
  { value: 'PAGO_ADELANTADO', label: 'Pago adelantado' },
  { value: 'CANCELADA', label: 'Cancelada' },
]

function opcionesSelectCuotaRevision(estadoRaw: string | undefined) {
  const codigo = codigoEstadoCuotaParaUi(estadoRaw)

  if (codigo && !OPCIONES_ESTADO_CUOTA_REVISION.some(o => o.value === codigo)) {
    return [
      { value: codigo, label: `${codigo} (legacy)` },
      ...OPCIONES_ESTADO_CUOTA_REVISION,
    ]
  }

  return OPCIONES_ESTADO_CUOTA_REVISION
}

interface ClienteData {
  cliente_id: number

  nombres: string

  cedula: string

  telefono: string

  email: string

  direccion: string

  ocupacion: string

  estado: string

  fecha_nacimiento: string | null

  notas: string
}

interface PrestamoData {
  prestamo_id: number

  cliente_id?: number

  cedula: string

  nombres: string

  total_financiamiento: number

  numero_cuotas: number

  tasa_interes: number

  producto: string

  observaciones: string

  fecha_requerimiento: string | null

  modalidad_pago: string

  cuota_periodo: number

  fecha_base_calculo: string | null

  fecha_aprobacion: string | null

  estado: string

  concesionario: string

  analista: string

  modelo_vehiculo: string

  valor_activo: number | null

  usuario_proponente: string

  usuario_aprobador: string
}

interface CuotaData {
  cuota_id: number

  numero_cuota: number

  monto: number

  fecha_vencimiento: string | null

  fecha_pago: string | null

  total_pagado: number

  estado: string

  observaciones: string
}

/** Fecha comparable YYYY-MM-DD para detectar cambios vs carga inicial. */
function normDateCmp(v: string | null | undefined): string {
  if (v == null || v === '') return ''
  if (typeof v === 'string' && v.length >= 10) return v.slice(0, 10)
  try {
    const d = new Date(v)
    return isNaN(d.getTime()) ? String(v) : d.toISOString().slice(0, 10)
  } catch {
    return String(v)
  }
}

function firmaSoloCliente(cliente: Partial<ClienteData>): string {
  return JSON.stringify({
    nombres: String(cliente.nombres ?? '').trim(),
    telefono: String(cliente.telefono ?? '').trim(),
    email: String(cliente.email ?? '').trim(),
    direccion: String(cliente.direccion ?? '').trim(),
    ocupacion: String(cliente.ocupacion ?? '').trim(),
    estado: String(cliente.estado ?? '').trim(),
    fn:
      cliente.fecha_nacimiento == null || cliente.fecha_nacimiento === ''
        ? ''
        : normDateCmp(String(cliente.fecha_nacimiento)),
    notas: String(cliente.notas ?? ''),
  })
}

function firmaSoloPrestamo(p: Partial<PrestamoData>): string {
  return JSON.stringify({
    tf: Number(p.total_financiamiento) || 0,
    nc: Number(p.numero_cuotas) || 0,
    ti: Number(p.tasa_interes) || 0,
    producto: String(p.producto ?? '').trim(),
    obs: String(p.observaciones ?? ''),
    cedula: String(p.cedula ?? '').trim(),
    nombres: String(p.nombres ?? '').trim(),
    fr: normDateCmp(p.fecha_requerimiento as string | null | undefined),
    mod: String(p.modalidad_pago ?? '').trim(),
    cp: Number(p.cuota_periodo) || 0,
    fa: normDateCmp(p.fecha_aprobacion as string | null | undefined),
    estado: String(p.estado ?? '').trim(),
    conc: String(p.concesionario ?? '').trim(),
    analista: String(p.analista ?? '').trim(),
    mv: String(p.modelo_vehiculo ?? '').trim(),
    va: p.valor_activo == null ? null : Number(p.valor_activo),
    up: String(p.usuario_proponente ?? '').trim(),
    ua: String(p.usuario_aprobador ?? '').trim(),
  })
}

function firmaSoloCuotas(cuotas: Partial<CuotaData>[]): string {
  const sorted = [...cuotas].sort(
    (a, b) => (a.cuota_id ?? 0) - (b.cuota_id ?? 0)
  )
  return JSON.stringify(
    sorted.map(c => ({
      id: c.cuota_id,
      num: c.numero_cuota,
      m: Number(c.monto) || 0,
      fv: normDateCmp(c.fecha_vencimiento as string | null | undefined),
      fp: normDateCmp(c.fecha_pago as string | null | undefined),
      tp: Number(c.total_pagado) || 0,
      est: String(c.estado ?? '').trim(),
      obs: String(c.observaciones ?? ''),
    }))
  )
}

type FirmaCargaRevision = { cliente: string; prestamo: string; cuotas: string }

/** Lista de préstamos (en producción: /pagos/prestamos vía basename). */
const RUTA_LISTA_PRESTAMOS = '/prestamos'

export function EditarRevisionManual() {
  const { prestamoId } = useParams()

  const navigate = useNavigate()

  const queryClient = useQueryClient()

  const irAListaPrestamos = () => {
    const scrollPosition = window.scrollY
    sessionStorage.setItem(
      'prestamoScrollPosition',
      scrollPosition.toString()
    )
    navigate(RUTA_LISTA_PRESTAMOS)
    setTimeout(() => {
      const savedPosition = sessionStorage.getItem('prestamoScrollPosition')
      if (savedPosition) {
        window.scrollTo(0, parseInt(savedPosition, 10))
        sessionStorage.removeItem('prestamoScrollPosition')
      }
    }, 100)
  }

  const [clienteData, setClienteData] = useState<Partial<ClienteData>>({})

  const [prestamoData, setPrestamoData] = useState<Partial<PrestamoData>>({})

  const [cuotasData, setCuotasData] = useState<Partial<CuotaData>[]>([])

  /** IDs pendientes de borrar en BD al guardar (parciales o guardar y cerrar). */
  const [cuotasIdsAEliminar, setCuotasIdsAEliminar] = useState<number[]>([])

  const [guardandoParcial, setGuardandoParcial] = useState(false)

  const [guardandoFinal, setGuardandoFinal] = useState(false)

  const [recalculandoFechasCuotas, setRecalculandoFechasCuotas] =
    useState(false)

  const [showRechazarModal, setShowRechazarModal] = useState(false)

  const [motivoRechazo, setMotivoRechazo] = useState('')

  const [guardandoRechazo, setGuardandoRechazo] = useState(false)

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

  const [errores, setErrores] = useState<Record<string, string>>({})

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
      cuotasIdsAEliminar.length > 0
  }, [
    cambios.cliente,
    cambios.prestamo,
    cambios.cuotas,
    cuotasIdsAEliminar.length,
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

        setCuotasData(data.cuotas)
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

  const estadoRevision = (detalleData?.revision?.estado_revision ?? 'pendiente')
    .toString()
    .toLowerCase()

  const soloLectura = estadoRevision === 'revisado'

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

  /**
   * Guarda en BD el texto actual de observaciones (préstamo + cuotas) y notas del cliente.
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
    for (const cuota of cuotasData) {
      if (cuota.cuota_id) {
        await revisionManualService.editarCuota(cuota.cuota_id, {
          observaciones: String(cuota.observaciones ?? ''),
        })
      }
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

  /** Incluye fechas en el PUT sin enviar solo fecha_base (el backend responde 400). */
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
   * Persiste fecha_aprobacion + fecha_base_calculo en BD y recalcula vencimientos de cuotas.
   * Misma lógica de negocio que al guardar cambios con fecha distinta; actualiza listados/reportes vía BD.
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

    if (cuotasData.length === 0) {
      toast.info(
        'No hay cuotas en este préstamo; no hay vencimientos que recalcular.'
      )
      return
    }

    setRecalculandoFechasCuotas(true)
    try {
      await revisionManualService.editarPrestamo(pid, {
        fecha_aprobacion: fa,
        fecha_base_calculo: fa,
      })

      const res = await prestamoService.recalcularFechasAmortizacion(pid)
      const actualizadas = res?.data?.actualizadas ?? res?.actualizadas ?? '?'

      setFechaAprobacionOriginal(fa)

      const datos = await revisionManualService.getDetallePrestamoRevision(pid)
      if (datos?.cuotas) {
        setCuotasData(datos.cuotas)
      }

      toast.success(
        `Fecha guardada en el servidor y ${actualizadas} cuota(s) con vencimientos actualizados. Los cambios quedan en la base (estado de cuenta, amortización, etc.).`
      )

      queryClient.invalidateQueries({ queryKey: prestamoKeys.all })
      queryClient.invalidateQueries({
        queryKey: ['revision-manual-prestamos'],
        exact: false,
      })
      queryClient.invalidateQueries({
        queryKey: ['revision-editar', prestamoId],
      })
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        'No se pudo guardar la fecha o recalcular vencimientos'
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

    // Sin cambios reales vs datos cargados: no operar (no es validación de negocio)
    if (cuotasIdsAEliminar.length === 0 && !hayDiferenciaVsCargaInicial()) {
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

      const snap = firmaCargaInicialRef.current
      const needGuardarCliente =
        !!clienteData.cliente_id &&
        (!snap || firmaSoloCliente(clienteData) !== snap.cliente)
      const needGuardarPrestamo =
        !!prestamoData.prestamo_id &&
        (!snap || firmaSoloPrestamo(prestamoData) !== snap.prestamo)
      const needGuardarCuotas =
        !snap || firmaSoloCuotas(cuotasData) !== snap.cuotas

      // Guardar cliente si el formulario difiere de la carga inicial

      if (needGuardarCliente) {
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

        if (prestamoData.estado !== undefined)
          prestamoUpdate.estado = prestamoData.estado

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
                  setCuotasData(datosActualizados.cuotas)
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

      // Eliminar cuotas marcadas (BD)

      const pid = parseInt(prestamoId, 10)

      let eliminacionesOk = true

      if (cuotasIdsAEliminar.length > 0) {
        for (const cuotaId of cuotasIdsAEliminar) {
          try {
            await revisionManualService.eliminarCuota(pid, cuotaId)

            savedSomething = true
          } catch (err: any) {
            eliminacionesOk = false

            errorOccurred = true

            const errorMsg =
              err?.response?.data?.detail ||
              err?.message ||
              'Error al eliminar cuota'

            toast.error(`❌ Error al eliminar cuota: ${errorMsg}`)

            console.error('Error eliminando cuota:', err)
          }
        }

        if (eliminacionesOk) setCuotasIdsAEliminar([])
      }

      // Guardar cuotas si difieren de la carga inicial

      if (needGuardarCuotas) {
        for (const cuota of cuotasData) {
          if (cuota.cuota_id) {
            const cuotaUpdate: Record<string, any> = {
              observaciones: String(cuota.observaciones ?? ''),
            }

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
              try {
                await revisionManualService.editarCuota(
                  cuota.cuota_id,
                  cuotaUpdate
                )

                savedSomething = true
              } catch (err: any) {
                errorOccurred = true

                const errorMsg =
                  err?.response?.data?.detail || 'Error al guardar cuota'

                toast.error(
                  `❌ Error en cuota #${cuota.numero_cuota}: ${errorMsg}`
                )

                console.error(
                  `Error guardando cuota ${cuota.numero_cuota}:`,
                  err
                )
              }
            }
          }
        }
      }

      if (!errorOccurred && savedSomething) {
        toast.success('✅ Cambios parciales guardados en BD')

        setCambios({ cliente: false, prestamo: false, cuotas: false })

        // Invalidar todas las vistas que muestran datos de préstamos, clientes y cuotas

        queryClient.invalidateQueries({
          queryKey: ['revision-manual-prestamos'],
        })

        queryClient.invalidateQueries({ queryKey: ['prestamos'] })

        queryClient.invalidateQueries({ queryKey: ['clientes'] })

        queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })

        queryClient.invalidateQueries({
          queryKey: ['kpis-principales-menu'],
          exact: false,
        })

        queryClient.invalidateQueries({
          queryKey: ['dashboard-menu'],
          exact: false,
        })

        setTimeout(() => irAListaPrestamos(), 400)
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

  const handleGuardarYCerrar = async () => {
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

    if (cuotasIdsAEliminar.length === 0 && !hayDiferenciaVsCargaInicial()) {
      toast.info('No hay cambios respecto a los datos cargados')
      return
    }

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

    if (!confirmar) {
      toast.info('ℹ️ Finalización cancelada')

      return
    }

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

        if (prestamoData.estado !== undefined)
          prestamoUpdate.estado = prestamoData.estado

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

      const pidFinal = parseInt(prestamoId, 10)

      for (const cuotaId of cuotasIdsAEliminar) {
        try {
          await revisionManualService.eliminarCuota(pidFinal, cuotaId)
        } catch (err: any) {
          throw new Error(
            `Error al eliminar cuota: ${err?.response?.data?.detail || err?.message || 'Error desconocido'}`
          )
        }
      }

      setCuotasIdsAEliminar([])

      if (needCuotasCierre) {
        for (const cuota of cuotasData) {
          if (cuota.cuota_id) {
            const cuotaUpdate: Record<string, any> = {
              observaciones: String(cuota.observaciones ?? ''),
            }

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
              try {
                await revisionManualService.editarCuota(
                  cuota.cuota_id,
                  cuotaUpdate
                )
              } catch (err: any) {
                throw new Error(
                  `Error en cuota #${cuota.numero_cuota}: ${err?.response?.data?.detail || 'Error desconocido'}`
                )
              }
            }
          }
        }
      }

      await persistObservacionesYNotasRevision()

      // Finalizar revisión

      try {
        const res = await revisionManualService.finalizarRevision(
          parseInt(prestamoId)
        )

        toast.success(res.mensaje)

        // Invalidar todas las vistas para reflejar cambios en tablas originales

        queryClient.invalidateQueries({
          queryKey: ['revision-manual-prestamos'],
        })

        queryClient.invalidateQueries({ queryKey: ['prestamos'] })

        queryClient.invalidateQueries({ queryKey: ['clientes'] })

        queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })

        queryClient.invalidateQueries({
          queryKey: ['kpis-principales-menu'],
          exact: false,
        })

        queryClient.invalidateQueries({
          queryKey: ['dashboard-menu'],
          exact: false,
        })

        // Pequeño delay antes de navegar para que el usuario vea el mensaje
        setTimeout(() => irAListaPrestamos(), 1500)
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

  const handleEliminarFilaCuota = (cuotaId: number | undefined) => {
    if (!cuotaId) return

    if (soloLectura) return

    const ok = window.confirm(
      'Esta cuota desaparecerá de la tabla. Al pulsar Guardar parciales o Guardar y cerrar se eliminará en la base de datos.'
    )

    if (!ok) return

    setCuotasIdsAEliminar(prev => [...prev, cuotaId])

    setCuotasData(prev => prev.filter(c => c.cuota_id !== cuotaId))

    setCambios(c => ({ ...c, cuotas: true }))
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
      queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })
      queryClient.invalidateQueries({ queryKey: ['prestamos'] })
      irAListaPrestamos()
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Error al rechazar'
      toast.error(msg)
    } finally {
      setGuardandoRechazo(false)
    }
  }

  const handleCerrar = () => {
    // Si hay cambios sin guardar, advertir

    if (
      cuotasIdsAEliminar.length > 0 ||
      hayDiferenciaVsCargaInicial()
    ) {
      const confirmar = window.confirm(
        '⚠️ Tienes cambios sin guardar.\n\n' +
          'Si cierras ahora, se perderán todos los cambios realizados.\n' +
          '¿Estás seguro de que deseas cerrar sin guardar?'
      )

      if (!confirmar) return
    }

    // Invalidar para que al volver se muestren datos actualizados

    queryClient.invalidateQueries({ queryKey: ['revision-manual-prestamos'] })

    queryClient.invalidateQueries({ queryKey: ['prestamos'] })

    queryClient.invalidateQueries({ queryKey: ['clientes'] })

    queryClient.invalidateQueries({ queryKey: ['clientes-stats'] })

    navigate('/revision-manual')
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <h2 className="mb-2 text-2xl font-bold text-red-600">Error</h2>

          <p className="mb-4 text-gray-600">
            No se pudieron cargar los datos del préstamo
          </p>

          <Button type="button" onClick={() => navigate(RUTA_LISTA_PRESTAMOS)}>
            Volver a lista de préstamos
          </Button>
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
                  : 'Edita los detalles del préstamo (cambios parciales permitidos)'}
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleGuardarParciales}
              disabled={soloLectura || guardandoParcial || guardandoFinal}
              className="gap-2"
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
              className="gap-2 bg-green-600 text-white hover:bg-green-700"
              onClick={handleGuardarYCerrar}
              disabled={soloLectura || guardandoParcial || guardandoFinal}
              title="Guarda todos los cambios y finaliza la revisión - aparece ✓ en Acciones"
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
                          : ''
                      }
                    />
                  </div>
                  {errores['telefono'] && (
                    <p className="text-xs text-red-600">
                      {errores['telefono']}
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
                      className={`pl-10 ${errores['email'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
                    />
                  </div>
                  {errores['email'] && (
                    <p className="text-xs text-red-600">{errores['email']}</p>
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
                      <SelectItem value="DRAFT">Borrador</SelectItem>
                      <SelectItem value="EN_REVISION">En revisión</SelectItem>
                      <SelectItem value="EVALUADO">Evaluado</SelectItem>
                      <SelectItem value="APROBADO">Aprobado</SelectItem>
                      <SelectItem value="LIQUIDADO">Liquidado</SelectItem>
                      <SelectItem value="DESISTIMIENTO">
                        Desistimiento
                      </SelectItem>
                      <SelectItem value="RECHAZADO">Rechazado</SelectItem>
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
                        setPrestamoData({
                          ...prestamoData,
                          numero_cuotas: parseInt(e.target.value) || 0,
                        })
                        setCambios({ ...cambios, prestamo: true })
                        if (errores['numero_cuotas'])
                          setErrores({ ...errores, numero_cuotas: '' })
                      }}
                      disabled={prestamoData.estado === 'LIQUIDADO'}
                      title={
                        prestamoData.estado === 'LIQUIDADO'
                          ? 'No se puede modificar en préstamos liquidados'
                          : undefined
                      }
                      className={`disabled:cursor-not-allowed disabled:bg-gray-100 ${errores['numero_cuotas'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
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

                  {/* Fecha Requerimiento - OCULTO */}
                  {/* Este campo se usa en gestión de préstamos, no en revisión manual */}

                  {/* Fecha Aprobación + recálculo de vencimientos en la misma caja */}
                  <div className="rounded-lg border border-gray-200 bg-slate-50/80 p-3 md:col-span-2">
                    <label className="mb-2 block text-sm font-medium">
                      Fecha de Aprobación
                    </label>
                    <p className="mb-2 text-xs text-gray-600">
                      Obligatoria para préstamos aprobados/liquidados: debe
                      ingresarla usted (no se infiere de otras fechas). La base
                      de cálculo es la misma fecha. El botón guarda en servidor y
                      recalcula vencimientos. &quot;Guardar cambios&quot; y
                      &quot;Guardar y cerrar&quot; persisten el resto en la base.
                    </p>
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
                      <div className="relative min-w-0 flex-1">
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
                              fecha_base_calculo: v,
                            })
                            setCambios({ ...cambios, prestamo: true })
                            if (errores['fecha_aprobacion'])
                              setErrores({
                                ...errores,
                                fecha_aprobacion: '',
                              })
                          }}
                          className={`pl-10 ${errores['fecha_aprobacion'] ? 'border-red-500 focus-visible:ring-red-400' : ''}`}
                        />
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        className="shrink-0 sm:max-w-[220px]"
                        disabled={
                          soloLectura ||
                          recalculandoFechasCuotas ||
                          cuotasData.length === 0
                        }
                        onClick={handleGuardarFechaYRecalcularVencimientos}
                        title="Guarda la fecha en el servidor y recalcula fechas de vencimiento de las cuotas"
                      >
                        {recalculandoFechasCuotas ? (
                          <Loader2 className="mr-2 h-4 w-4 shrink-0 animate-spin" />
                        ) : (
                          <RefreshCw className="mr-2 h-4 w-4 shrink-0" />
                        )}
                        Recalcular vencimientos
                      </Button>
                    </div>
                    {errores['fecha_aprobacion'] && (
                      <p className="mt-1 text-xs text-red-600">
                        {errores['fecha_aprobacion']}
                      </p>
                    )}
                  </div>

                  {/* Fecha Base Cálculo - OCULTO */}
                  {/* Este campo se sincroniza automáticamente con fecha_aprobacion, no necesita edición manual */}

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

            {/* Cuotas */}

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  💳 Cuotas/Pagos
                </CardTitle>
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

                        <th className="px-4 py-2 text-left">Observaciones</th>

                        <th
                          className="w-12 px-2 py-2 text-center"
                          aria-label="Eliminar"
                        >
                          {' '}
                        </th>
                      </tr>
                    </thead>

                    <tbody className="divide-y">
                      {cuotasData.map((cuota, idx) => (
                        <tr
                          key={cuota.cuota_id ?? `fila-${idx}`}
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

                                newCuotas[idx] = {
                                  ...cuota,
                                  monto: parseFloat(e.target.value) || 0,
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

                                newCuotas[idx] = {
                                  ...cuota,
                                  estado: e.target.value,
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

                          <td className="px-4 py-2">
                            <input
                              type="text"
                              value={cuota.observaciones || ''}
                              onChange={e => {
                                const newCuotas = [...cuotasData]

                                newCuotas[idx] = {
                                  ...cuota,
                                  observaciones: e.target.value,
                                }

                                setCuotasData(newCuotas)

                                setCambios({ ...cambios, cuotas: true })
                              }}
                              className="w-32 rounded border px-2 py-1 text-sm"
                              placeholder="Obs."
                            />
                          </td>

                          <td className="px-2 py-2 text-center align-middle">
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0 text-red-600 hover:bg-red-50 hover:text-red-800"
                              title="Eliminar cuota (se confirma en BD al guardar)"
                              onClick={() =>
                                handleEliminarFilaCuota(cuota.cuota_id)
                              }
                            >
                              <Trash2 className="h-4 w-4" aria-hidden />
                              <span className="sr-only">Eliminar cuota</span>
                            </Button>
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
            className="gap-2"
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
            className="gap-2 bg-green-600 text-white hover:bg-green-700"
            onClick={handleGuardarYCerrar}
            disabled={soloLectura || guardandoParcial || guardandoFinal}
            title="Guarda todos los cambios y finaliza la revisión - aparece ✓ en Acciones"
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
    </motion.div>
  )
}

export default EditarRevisionManual
