import { useState, useEffect, useCallback, useMemo } from 'react'

import { motion, AnimatePresence } from 'framer-motion'

import { toast } from 'sonner'

import {
  DollarSign,
  Calendar,
  CreditCard,
  Search,
  X,
  ChevronDown,
  ChevronUp,
  Save,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react'

import { useDebounce } from '../../hooks/useDebounce'

import { useEscapeClose } from '../../hooks/useEscapeClose'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'

import { Button } from '../../components/ui/button'

import { Input } from '../../components/ui/input'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'

import { Badge } from '../../components/ui/badge'

import { Textarea } from '../../components/ui/textarea'

import { clienteService } from '../../services/clienteService'

import { useCreatePrestamo, useUpdatePrestamo } from '../../hooks/usePrestamos'

import { useSearchClientes } from '../../hooks/useClientes'

import { usePermissions } from '../../hooks/usePermissions'

import { useConcesionariosActivos } from '../../hooks/useConcesionarios'

import { useAnalistasActivos } from '../../hooks/useAnalistas'

import { useModelosVehiculosActivos } from '../../hooks/useModelosVehiculos'

import { useSimpleAuth } from '../../store/simpleAuthStore'

import { prestamoService } from '../../services/prestamoService'

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog'

import { Prestamo, PrestamoForm } from '../../types'

import { ModalValidacionPrestamoExistente } from './ModalValidacionPrestamoExistente'

/** Fecha API (date o ISO) a YYYY-MM-DD para inputs type="date". */
function fechaInputYmd(v: unknown): string {
  if (v == null || v === '') return ''

  const s = String(v)

  return s.length >= 10 ? s.slice(0, 10) : s
}

/** Colapsa espacios para comparar modelo guardado vs catalogo. */
function normalizarTextoModelo(s: string): string {
  return String(s || '')
    .trim()
    .replace(/\s+/g, ' ')
}

/** Texto de modelo guardado en BD/API (modelo_vehiculo, alias modelo o producto). */
function modeloTextoDesdePrestamo(p?: Prestamo): string {
  if (!p) return ''
  const mv =
    p.modelo_vehiculo != null && String(p.modelo_vehiculo).trim() !== ''
      ? String(p.modelo_vehiculo).trim()
      : ''
  if (mv) return mv
  const m = (p as { modelo?: string | null }).modelo
  if (m != null && String(m).trim() !== '') return String(m).trim()
  const prod = (p.producto || '').trim()
  if (prod) return prod
  return ''
}

interface CrearPrestamoFormProps {
  prestamo?: Prestamo // Préstamo existente para edición

  onClose: () => void

  onSuccess: () => void

  onAprobarManual?: (prestamo: Prestamo) => void
}

export function CrearPrestamoForm({
  prestamo,
  onClose,
  onSuccess,
  onAprobarManual,
}: CrearPrestamoFormProps) {
  const createPrestamo = useCreatePrestamo()

  const updatePrestamo = useUpdatePrestamo()

  const { canEditPrestamo, canApprovePrestamo } = usePermissions()

  // Cerrar con ESC

  useEscapeClose(onClose, true)

  // Función para obtener la fecha actual en formato YYYY-MM-DD

  const getCurrentDate = () => {
    const today = new Date()

    const year = today.getFullYear()

    const month = String(today.getMonth() + 1).padStart(2, '0')

    const day = String(today.getDate()).padStart(2, '0')

    return `${year}-${month}-${day}`
  }

  const modeloInicial = modeloTextoDesdePrestamo(prestamo)

  const [formData, setFormData] = useState<Partial<PrestamoForm>>({
    cedula: prestamo?.cedula || '',

    total_financiamiento: prestamo?.total_financiamiento || 0,

    modalidad_pago: prestamo?.modalidad_pago || 'MENSUAL',

    fecha_requerimiento: prestamo
      ? fechaInputYmd(prestamo.fecha_requerimiento)
      : '',

    fecha_aprobacion: prestamo?.fecha_aprobacion
      ? fechaInputYmd(prestamo.fecha_aprobacion)
      : undefined,

    fecha_base_calculo: prestamo?.fecha_base_calculo
      ? fechaInputYmd(prestamo.fecha_base_calculo)
      : undefined,

    tasa_interes:
      prestamo?.tasa_interes != null
        ? Number(prestamo.tasa_interes)
        : undefined,

    producto: prestamo?.producto || '',

    concesionario: prestamo?.concesionario || '',

    analista: prestamo?.analista || '',

    analista_id:
      prestamo?.analista_id != null ? Number(prestamo.analista_id) : undefined,

    modelo_vehiculo: modeloInicial,

    estado: prestamo?.estado,

    observaciones: prestamo?.observaciones || '',
  })

  // Obtener datos de configuración con manejo de errores

  const { data: concesionarios = [], error: errorConcesionarios } =
    useConcesionariosActivos()

  const { data: analistas = [], error: errorAnalistas } = useAnalistasActivos()

  const analistaSelectValue = useMemo(() => {
    if (
      formData.analista_id != null &&
      Number.isFinite(Number(formData.analista_id))
    ) {
      return String(formData.analista_id)
    }
    const match = analistas.find(
      a => a.nombre === (formData.analista || '').trim()
    )
    return match ? String(match.id) : ''
  }, [formData.analista_id, formData.analista, analistas])

  const { data: modelosVehiculos = [], error: errorModelos } =
    useModelosVehiculosActivos()

  type ModeloCat = { id: number; modelo: string; precio?: number | null }

  /** Texto efectivo del modelo en edicion: formulario o lo que trae el prestamo (API). */
  const textoModeloGuardado = useMemo(() => {
    const fromForm = (formData.modelo_vehiculo || '').trim()
    if (fromForm) return fromForm
    return modeloTextoDesdePrestamo(prestamo).trim()
  }, [formData.modelo_vehiculo, prestamo])

  const { modelosParaSelect, valorSelectModelo } = useMemo(() => {
    const base = (modelosVehiculos || []) as ModeloCat[]
    const g = textoModeloGuardado
    if (!g) {
      return {
        modelosParaSelect: base,
        valorSelectModelo: undefined as string | undefined,
      }
    }
    const gn = normalizarTextoModelo(g)
    const matchCat = base.find(
      m => normalizarTextoModelo(String(m.modelo)) === gn
    )
    if (matchCat) {
      return {
        modelosParaSelect: base,
        valorSelectModelo: matchCat.modelo,
      }
    }
    return {
      modelosParaSelect: [{ id: -1, modelo: g, precio: null }, ...base],
      valorSelectModelo: g,
    }
  }, [modelosVehiculos, textoModeloGuardado])

  const { user } = useSimpleAuth()
  useEffect(() => {
    if (!prestamo?.id || !textoModeloGuardado) return
    const base = (modelosVehiculos || []) as ModeloCat[]
    if (!base.length) return
    const gn = normalizarTextoModelo(textoModeloGuardado)
    const matchCat = base.find(
      m => normalizarTextoModelo(String(m.modelo)) === gn
    )
    if (!matchCat) return
    setFormData(prev => {
      const cur = (prev.modelo_vehiculo || '').trim()
      if (normalizarTextoModelo(cur) === gn && cur === matchCat.modelo) {
        return prev
      }
      if (cur !== '' && normalizarTextoModelo(cur) !== gn) {
        return prev
      }
      return { ...prev, modelo_vehiculo: matchCat.modelo }
    })
  }, [prestamo?.id, modelosVehiculos, textoModeloGuardado])

  // Errores de carga de configuración (sin bloquear renderizado; solo en desarrollo se puede loguear)

  if (errorConcesionarios || errorAnalistas || errorModelos) {
    // Opcional: logger condicionado por NODE_ENV
  }

  const [valorActivo, setValorActivo] = useState<number>(() => {
    if (!prestamo) return 0
    const va = prestamo.valor_activo
    if (va == null) return 0
    const n = Number(va)
    return Number.isFinite(n) ? n : 0
  })

  // Estados para validación de préstamos existentes

  const [showModalValidacion, setShowModalValidacion] = useState(false)

  const [resumenPrestamos, setResumenPrestamos] = useState<any>(null)

  const [justificacionAutorizacion, setJustificacionAutorizacion] = useState('')

  const [anticipo, setAnticipo] = useState<number>(0)

  const [showAdditionalInfo, setShowAdditionalInfo] = useState(false)

  const [clienteData, setClienteData] = useState<any>(null)

  const [numeroCuotas, setNumeroCuotas] = useState<number>(
    prestamo?.numero_cuotas && prestamo.numero_cuotas > 0
      ? prestamo.numero_cuotas
      : 12
  )

  const [cuotaPeriodo, setCuotaPeriodo] = useState<number>(() => {
    if (!prestamo) return 0
    const cp =
      prestamo.cuota_periodo != null && Number(prestamo.cuota_periodo) > 0
        ? Number(prestamo.cuota_periodo)
        : 0
    if (cp > 0) return cp
    const tf = Number(prestamo.total_financiamiento || 0)
    const n =
      prestamo.numero_cuotas && prestamo.numero_cuotas > 0
        ? prestamo.numero_cuotas
        : 12
    return n > 0 && tf > 0 ? tf / n : 0
  })

  const [showConfirmCreate, setShowConfirmCreate] = useState(false)

  const [isRecalculatingAmortizacion, setIsRecalculatingAmortizacion] =
    useState(false)

  const [fechaAprobacionAnterior, setFechaAprobacionAnterior] = useState<
    string | undefined
  >(
    prestamo?.fecha_aprobacion
      ? fechaInputYmd(prestamo.fecha_aprobacion)
      : undefined
  )

  useEffect(() => {
    if (!prestamo?.id) return
    const mv = modeloTextoDesdePrestamo(prestamo)
    setFormData({
      cedula: prestamo.cedula || '',
      total_financiamiento: Number(prestamo.total_financiamiento) || 0,
      modalidad_pago: prestamo.modalidad_pago || 'MENSUAL',
      fecha_requerimiento: fechaInputYmd(prestamo.fecha_requerimiento),
      fecha_aprobacion: prestamo.fecha_aprobacion
        ? fechaInputYmd(prestamo.fecha_aprobacion)
        : undefined,
      fecha_base_calculo: prestamo.fecha_base_calculo
        ? fechaInputYmd(prestamo.fecha_base_calculo)
        : undefined,
      tasa_interes:
        prestamo.tasa_interes != null
          ? Number(prestamo.tasa_interes)
          : undefined,
      producto: prestamo.producto || '',
      concesionario: prestamo.concesionario || '',
      analista: prestamo.analista || '',
      analista_id:
        prestamo.analista_id != null ? Number(prestamo.analista_id) : undefined,
      modelo_vehiculo: mv,
      estado: prestamo.estado,
      observaciones: prestamo.observaciones || '',
    })
    const va = prestamo.valor_activo
    setValorActivo(
      va != null && String(va).trim() !== '' && !Number.isNaN(Number(va))
        ? Number(va)
        : 0
    )
    const n = prestamo.numero_cuotas
    setNumeroCuotas(n && Number(n) > 0 ? Number(n) : 12)
    const cpRaw = prestamo.cuota_periodo
    const cp = cpRaw != null && Number(cpRaw) > 0 ? Number(cpRaw) : 0
    if (cp > 0) {
      setCuotaPeriodo(cp)
    } else {
      const tf = Number(prestamo.total_financiamiento || 0)
      const nn = n && Number(n) > 0 ? Number(n) : 12
      setCuotaPeriodo(nn > 0 && tf > 0 ? Math.round((tf / nn) * 100) / 100 : 0)
    }
  }, [prestamo?.id])

  const [showRechazarDialog, setShowRechazarDialog] = useState(false)

  // Errores de UI para marcar campos obligatorios visualmente

  const [uiErrors, setUiErrors] = useState<{
    concesionario?: boolean
    analista?: boolean
  }>({})

  // Total financiamiento = cuota manual x numero de cuotas; anticipo = valor activo - total

  useEffect(() => {
    const cuota = Number.isFinite(cuotaPeriodo) ? Math.max(0, cuotaPeriodo) : 0
    const n =
      Number.isFinite(numeroCuotas) && numeroCuotas > 0 ? numeroCuotas : 0
    const va = Number.isFinite(valorActivo) ? Math.max(0, valorActivo) : 0
    if (cuota <= 0 || n <= 0) {
      setAnticipo(0)
      setFormData(prev => ({
        ...prev,
        total_financiamiento: 0,
      }))
      return
    }
    const totalFin = Math.round(cuota * n * 100) / 100
    const ant = Math.round(Math.max(0, va - totalFin) * 100) / 100
    setAnticipo(ant)
    setFormData(prev => ({
      ...prev,
      total_financiamiento: totalFin,
    }))
  }, [cuotaPeriodo, numeroCuotas, valorActivo])

  // Si se selecciona modelo o llegan modelos desde configuracion, cargar su precio

  useEffect(() => {
    // En edición no pisar el valor activo guardado con el precio del catálogo al abrir el formulario.

    if (prestamo) return

    if (
      formData.modelo_vehiculo &&
      modelosVehiculos &&
      modelosVehiculos.length > 0
    ) {
      const modeloSel: any = modelosVehiculos.find(
        (m: any) => m.modelo === formData.modelo_vehiculo
      )

      if (modeloSel && modeloSel.precio != null) {
        const precioNum =
          typeof modeloSel.precio === 'number'
            ? modeloSel.precio
            : parseFloat(String(modeloSel.precio))

        if (!Number.isNaN(precioNum)) {
          setValorActivo(precioNum)
        }
      }
    }
  }, [formData.modelo_vehiculo, modelosVehiculos, prestamo])

  // Buscar cliente por cedula con debounce mejorado

  const debouncedCedula = useDebounce(formData.cedula || '', 500)

  const { data: clienteInfo, isLoading: isLoadingCliente } = useSearchClientes(
    debouncedCedula && debouncedCedula.length >= 2 ? debouncedCedula : ''
  )

  // Cargar datos del cliente cuando se encuentra

  // IMPORTANTE: Solo recibimos clientes ACTIVOS gracias al filtro en el servicio

  useEffect(() => {
    if (clienteInfo && clienteInfo.length > 0) {
      const cliente = clienteInfo[0]

      // Establecer clienteData con todos los datos del cliente disponibles

      // El modelo Cliente contiene: id, cedula, nombres, telefono, email, direccion,

      // fecha_nacimiento, ocupacion, estado, fecha_registro, fecha_actualizacion, usuario_registro, notas

      setClienteData(cliente)

      // No autocompletamos campos del préstamo porque el cliente no tiene esos datos

      // (modelo_vehiculo, analista, concesionario son campos del préstamo, no del cliente)
    } else if (
      formData.cedula &&
      formData.cedula.length >= 2 &&
      clienteInfo &&
      clienteInfo.length === 0
    ) {
      // Cliente no encontrado o no está ACTIVO (no aparecerá en la búsqueda)

      setClienteData(null)
    }
  }, [clienteInfo, formData.cedula])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validaciones requeridas

    const errors: string[] = []

    // Validar cédula

    if (!formData.cedula || formData.cedula.trim() === '') {
      errors.push('La cédula es requerida')
    }

    // Validar que el cliente exista (solo para nuevos préstamos)

    // NOTA: Solo aparecen clientes ACTIVOS en la búsqueda, pero validamos por seguridad

    if (!prestamo && !clienteData) {
      errors.push(
        'Debe buscar y seleccionar un cliente válido con estado ACTIVO'
      )
    }

    // Validar Valor Activo

    if (valorActivo <= 0) {
      errors.push('El Valor Activo debe ser mayor a 0')
    }

    // Cuota por periodo: manual; total = cuota x cuotas no puede superar el valor del activo

    if (!cuotaPeriodo || cuotaPeriodo <= 0) {
      errors.push('Ingrese la Cuota por Periodo (USD) mayor a 0')
    }

    const totalCuotas =
      Number.isFinite(cuotaPeriodo) && Number.isFinite(numeroCuotas)
        ? Math.round(cuotaPeriodo * numeroCuotas * 100) / 100
        : 0

    if (
      valorActivo > 0 &&
      totalCuotas > 0 &&
      totalCuotas > valorActivo + 0.01
    ) {
      errors.push(
        'Cuota por periodo x numero de cuotas no puede superar el Valor Activo (el anticipo quedaria negativo)'
      )
    }

    // Validar Numero de Cuotas

    if (
      numeroCuotas < 1 ||
      numeroCuotas > 50 ||
      !Number.isInteger(numeroCuotas)
    ) {
      errors.push('El número de cuotas debe ser un entero entre 1 y 50')
    }

    // Validar Total de Financiamiento

    if (!formData.total_financiamiento || formData.total_financiamiento <= 0) {
      errors.push('El Total de Financiamiento debe ser mayor a 0')
    }

    // Validar Modalidad de Pago

    if (!formData.modalidad_pago) {
      errors.push('La modalidad de pago es requerida')
    }

    // Validar Fecha de Requerimiento

    if (
      !formData.fecha_requerimiento ||
      formData.fecha_requerimiento.trim() === ''
    ) {
      errors.push('La fecha de requerimiento es requerida')
    }

    // Requeridos adicionales del formulario

    const faltaConcesionario =
      !formData.concesionario || String(formData.concesionario).trim() === ''

    const faltaAnalista =
      !formData.analista || String(formData.analista).trim() === ''

    if (faltaConcesionario) errors.push('Debe seleccionar un Concesionario')

    if (faltaAnalista) errors.push('Debe seleccionar un Analista')

    setUiErrors({ concesionario: faltaConcesionario, analista: faltaAnalista })

    if (
      !formData.modelo_vehiculo ||
      String(formData.modelo_vehiculo).trim() === ''
    ) {
      errors.push('Debe seleccionar un Modelo de Vehículo')
    }

    // Si hay errores, mostrar notificación consolidada y bloquear envío

    if (errors.length > 0) {
      const listado = errors.map(e => `• ${e}`).join('\n')

      toast.error(`Faltan datos obligatorios:\n${listado}`)

      // Desplazar al inicio del formulario para que el operador corrija

      try {
        const formEl = e.target as HTMLFormElement

        formEl?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      } catch {}

      return
    }

    // Si es un nuevo préstamo, verificar si el cliente ya tiene préstamos

    if (!prestamo && formData.cedula) {
      try {
        const resumen = await prestamoService.getResumenPrestamos(
          formData.cedula
        )

        // Solo bloquear con modal si hay cuotas en mora (>0)

        if (resumen.tiene_prestamos && (resumen.total_cuotas_mora || 0) > 0) {
          setResumenPrestamos(resumen)

          setShowModalValidacion(true)

          return
        }
      } catch {
        // Continuar con el proceso si hay error (no bloquear al usuario)
      }
    }

    // Para nuevo préstamo: mostrar modal de confirmación accesible

    if (!prestamo) {
      setShowConfirmCreate(true)

      return
    }

    // Edición: proceder directamente

    await crearOActualizarPrestamo()
  }

  const crearOActualizarPrestamo = async () => {
    try {
      setShowConfirmCreate(false)

      // Preparar datos con numero_cuotas y cuota_periodo

      const fechaApr = formData.fecha_aprobacion
        ? String(formData.fecha_aprobacion).trim()
        : ''

      const prestamoData: Record<string, unknown> = {
        ...formData,

        modelo: formData.modelo_vehiculo || undefined,

        // Incluir 0 si aplica para que el PUT persista valor_activo en BD (antes se omitía).

        valor_activo:
          Number.isFinite(valorActivo) && valorActivo >= 0
            ? valorActivo
            : undefined,

        producto:
          formData.producto && String(formData.producto).trim() !== ''
            ? formData.producto
            : formData.modelo_vehiculo || '',

        analista:
          formData.analista && String(formData.analista).trim() !== ''
            ? formData.analista
            : '',

        analista_id:
          formData.analista_id != null &&
          Number.isFinite(Number(formData.analista_id))
            ? Number(formData.analista_id)
            : undefined,

        numero_cuotas: numeroCuotas,

        cuota_periodo: cuotaPeriodo,

        fecha_base_calculo: formData.fecha_base_calculo,

        usuario_autoriza:
          !prestamo && justificacionAutorizacion ? user?.email : undefined,

        observaciones: justificacionAutorizacion
          ? `${formData.observaciones || ''}\n\n--- JUSTIFICACIÓN PARA NUEVO PRÉSTAMO ---\n${justificacionAutorizacion}`.trim()
          : formData.observaciones,
      }

      if (!prestamo) {
        delete prestamoData.estado
      }

      // No enviar fecha_aprobacion vacía: FastAPI rechaza "" como datetime (422).

      if (fechaApr !== '') {
        prestamoData.fecha_aprobacion = `${fechaApr}T00:00:00`
      } else {
        delete prestamoData.fecha_aprobacion
      }

      if (prestamo) {
        await updatePrestamo.mutateAsync({
          id: prestamo.id,

          data: prestamoData as Partial<PrestamoForm>,
        })
      } else {
        // Backend exige cliente_id para crear; se toma del cliente buscado por cédula

        if (clienteData?.id != null) {
          prestamoData.cliente_id = clienteData.id
        }

        await createPrestamo.mutateAsync(
          prestamoData as unknown as PrestamoForm
        )
      }

      onSuccess()

      onClose()
    } catch (error) {
      toast.error('Error al guardar el préstamo')

      if (import.meta.env.DEV) {
        console.error('Error saving loan:', error)
      }
    }
  }

  const recalcularAmortizacion = async () => {
    if (!prestamo?.id) {
      toast.error('No se encontró el ID del préstamo')
      return
    }

    const nuevaFechaAprobacion = formData.fecha_aprobacion
    if (!nuevaFechaAprobacion) {
      toast.error('La fecha de aprobación es requerida')
      return
    }

    if (nuevaFechaAprobacion === fechaAprobacionAnterior) {
      toast.info('La fecha de aprobación no cambió')
      return
    }

    setIsRecalculatingAmortizacion(true)
    try {
      // 1. Primero actualizar la fecha de aprobación del préstamo
      const prestamoDataUpdate = {
        fecha_aprobacion: `${nuevaFechaAprobacion}T00:00:00`,
      }

      await updatePrestamo.mutateAsync({
        id: prestamo.id,
        data: prestamoDataUpdate as Partial<PrestamoForm>,
      })

      // 2. Luego recalcular las fechas de vencimiento de las cuotas
      const resultado = await prestamoService.recalcularFechasAmortizacion(
        prestamo.id
      )

      setFechaAprobacionAnterior(nuevaFechaAprobacion)

      toast.success(
        `Amortización recalculada: ${resultado.data.actualizadas} cuota(s) actualizadas`
      )

      onSuccess()
    } catch (error: any) {
      const mensajeError =
        error?.response?.data?.detail || 'Error al recalcular amortización'
      toast.error(mensajeError)

      if (import.meta.env.DEV) {
        console.error('Error recalculando amortización:', error)
      }
    } finally {
      setIsRecalculatingAmortizacion(false)
    }
  }

  const handleConfirmarAutorizacion = (justificacion: string) => {
    setJustificacionAutorizacion(justificacion)

    setShowModalValidacion(false)

    // Continuar con la creación del préstamo

    crearOActualizarPrestamo()
  }

  // Verificar permisos de edición - Política: no se permite edición de préstamos ya creados

  // Permitir edición si el usuario tiene permisos y está editando un préstamo

  const isReadOnly = prestamo ? !canEditPrestamo(prestamo.estado || '') : false

  const plazoCuotasBloqueadoLiquidado =
    prestamo != null && prestamo.estado === 'LIQUIDADO'

  const canApprove = prestamo ? canApprovePrestamo() : false

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"

        // Eliminado: onClick para evitar cierre por clic fuera
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          className="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-lg bg-white shadow-xl"
          onClick={e => e.stopPropagation()}
        >
          <div className="sticky top-0 z-10 flex items-center justify-between border-b bg-white p-4">
            <h2 className="text-xl font-bold">
              {prestamo ? 'Editar Préstamo' : 'Nuevo Préstamo'}
            </h2>

            {/* Botón X eliminado - solo se puede cerrar con Cancelar o Crear */}
          </div>

          <form onSubmit={handleSubmit} className="space-y-6 p-6">
            {/* Búsqueda de Cliente */}

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="h-5 w-5" />
                  Búsqueda de Cliente
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  La cédula del préstamo debe coincidir con la del cliente: el
                  servidor copia la cédula de la ficha del cliente al guardar.
                  Si el cliente no tiene cédula, no se puede crear un préstamo
                  APROBADO.
                </p>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* Seleccionar primero el Modelo para cargar el precio */}

                <div>
                  <label className="mb-1 block text-sm font-medium">
                    Modelo de Vehículo <span className="text-red-500">*</span>
                  </label>

                  <Select
                    value={valorSelectModelo}
                    onValueChange={value => {
                      setFormData({
                        ...formData,

                        modelo_vehiculo: value,
                      })

                      const modeloSel =
                        modelosVehiculos.find((m: any) => m.modelo === value) ||
                        modelosParaSelect.find((m: any) => m.modelo === value)

                      if (modeloSel && modeloSel.precio != null) {
                        const precioNum =
                          typeof modeloSel.precio === 'number'
                            ? modeloSel.precio
                            : parseFloat(String(modeloSel.precio))

                        if (!Number.isNaN(precioNum)) {
                          setValorActivo(precioNum)
                        }
                      } else {
                        setValorActivo(0)
                      }
                    }}
                    disabled={isReadOnly}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar modelo" />
                    </SelectTrigger>

                    <SelectContent>
                      {modelosParaSelect.map(modelo => (
                        <SelectItem
                          key={
                            modelo.id === -1
                              ? `guardado-${modelo.modelo}`
                              : modelo.id
                          }
                          value={modelo.modelo}
                        >
                          {modelo.modelo}
                          {modelo.id === -1 ? ' (guardado)' : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <p className="mt-1 text-xs text-gray-500">
                    Seleccione el modelo. Si tiene precio configurado, se
                    cargará en Valor Activo; si no, ingréselo manualmente.
                  </p>
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium">
                    Cédula <span className="text-red-500">*</span>
                  </label>

                  <Input
                    placeholder="Buscar por cédula..."
                    value={formData.cedula}
                    onChange={e =>
                      setFormData({
                        ...formData,
                        cedula: e.target.value.toUpperCase(),
                      })
                    }
                    disabled={isReadOnly || isLoadingCliente}
                  />
                </div>

                {isLoadingCliente &&
                  formData.cedula &&
                  formData.cedula.length >= 2 && (
                    <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4">
                      <div className="h-5 w-5 animate-spin rounded-full border-b-2 border-blue-600"></div>

                      <p className="text-sm text-blue-800">
                        Buscando cliente...
                      </p>
                    </div>
                  )}

                {clienteData && !isLoadingCliente && (
                  <div className="rounded-lg border border-green-200 bg-green-50 p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5 text-green-600" />

                      <p className="font-semibold text-green-800">
                        {clienteData.nombres}
                      </p>
                    </div>

                    <p className="text-sm text-green-700">
                      Cliente encontrado y datos cargados automáticamente
                    </p>
                  </div>
                )}

                {!clienteData &&
                  !isLoadingCliente &&
                  formData.cedula &&
                  formData.cedula.length >= 2 && (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                      <div className="flex items-center gap-2">
                        <AlertCircle className="h-5 w-5 text-red-600" />

                        <p className="text-sm text-red-800">
                          Cliente no encontrado con esta cédula
                        </p>
                      </div>
                    </div>
                  )}
              </CardContent>
            </Card>

            {/* Información Adicional del Cliente (Colapsable) */}

            {clienteData && (
              <Card>
                <CardHeader>
                  <button
                    type="button"
                    onClick={() => setShowAdditionalInfo(!showAdditionalInfo)}
                    className="flex w-full items-center justify-between"
                  >
                    <CardTitle>Datos del Cliente</CardTitle>

                    {showAdditionalInfo ? (
                      <ChevronUp className="h-5 w-5" />
                    ) : (
                      <ChevronDown className="h-5 w-5" />
                    )}
                  </button>
                </CardHeader>

                <AnimatePresence>
                  {showAdditionalInfo && (
                    <motion.div
                      initial={{ height: 0 }}
                      animate={{ height: 'auto' }}
                      exit={{ height: 0 }}
                    >
                      <CardContent className="space-y-3">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="text-sm text-gray-600">
                              Cédula
                            </label>

                            <p className="font-medium">{clienteData.cedula}</p>
                          </div>

                          <div>
                            <label className="text-sm text-gray-600">
                              Nombres Completos
                            </label>

                            <p className="font-medium">{clienteData.nombres}</p>
                          </div>

                          <div>
                            <label className="text-sm text-gray-600">
                              Teléfono
                            </label>

                            <p className="font-medium">
                              {clienteData.telefono || 'N/A'}
                            </p>
                          </div>

                          <div>
                            <label className="text-sm text-gray-600">
                              Email
                            </label>

                            <p className="font-medium">
                              {clienteData.email || 'N/A'}
                            </p>
                          </div>

                          <div>
                            <label className="text-sm text-gray-600">
                              Dirección
                            </label>

                            <p className="font-medium">
                              {clienteData.direccion || 'N/A'}
                            </p>
                          </div>

                          <div>
                            <label className="text-sm text-gray-600">
                              Fecha de Nacimiento
                            </label>

                            <p className="font-medium">
                              {clienteData.fecha_nacimiento
                                ? new Date(
                                    clienteData.fecha_nacimiento
                                  ).toLocaleDateString('es-VE')
                                : 'N/A'}
                            </p>
                          </div>

                          <div>
                            <label className="text-sm text-gray-600">
                              Ocupación
                            </label>

                            <p className="font-medium">
                              {clienteData.ocupacion || 'N/A'}
                            </p>
                          </div>

                          <div>
                            <label className="text-sm text-gray-600">
                              Estado
                            </label>

                            <Badge
                              variant={
                                clienteData.estado === 'ACTIVO'
                                  ? 'default'
                                  : 'secondary'
                              }
                            >
                              {clienteData.estado}
                            </Badge>
                          </div>

                          {clienteData.notas && clienteData.notas !== 'NA' && (
                            <div className="col-span-2">
                              <label className="text-sm text-gray-600">
                                Notas
                              </label>

                              <p className="text-sm font-medium">
                                {clienteData.notas}
                              </p>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </motion.div>
                  )}
                </AnimatePresence>
              </Card>
            )}

            {/* Datos del Préstamo */}

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5" />
                  Datos del Préstamo
                </CardTitle>
              </CardHeader>

              <CardContent className="space-y-4">
                {prestamo ? (
                  <div className="rounded-lg border-2 border-indigo-200 bg-indigo-50/90 p-4 shadow-sm">
                    <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="text-sm font-semibold text-indigo-900">
                          Estado del préstamo
                        </p>
                        <p className="mt-0.5 text-xs text-indigo-800/90">
                          Elija el nuevo estado y confirme con el botón
                          Actualizar préstamo al final del formulario.
                        </p>
                      </div>
                      <Badge
                        variant="outline"
                        className="w-fit shrink-0 border-indigo-300 bg-white text-indigo-900"
                      >
                        {String(formData.estado ?? prestamo.estado ?? 'DRAFT')}
                      </Badge>
                    </div>
                    <Select
                      value={String(
                        formData.estado ?? prestamo.estado ?? 'DRAFT'
                      )}
                      onValueChange={value =>
                        setFormData({
                          ...formData,
                          estado: value as Prestamo['estado'],
                        })
                      }
                      disabled={isReadOnly}
                    >
                      <SelectTrigger className="h-11 border-indigo-200 bg-white">
                        <SelectValue placeholder="Estado" />
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
                    <p className="mt-2 text-xs text-indigo-800/80">
                      Al guardar se persistirá el estado en la base de datos.
                      Revise coherencia con cuotas y pagos.
                    </p>
                    {prestamo?.fecha_desistimiento ? (
                      <p className="mt-2 text-xs text-slate-700">
                        Fecha de desistimiento registrada:{' '}
                        {fechaInputYmd(prestamo.fecha_desistimiento)}
                      </p>
                    ) : formData.estado === 'DESISTIMIENTO' ? (
                      <p className="mt-2 text-xs text-amber-800">
                        Al guardar se registrará la fecha de desistimiento en la
                        base de datos.
                      </p>
                    ) : null}
                  </div>
                ) : null}
                {/* Nuevos campos: Valor Activo y Anticipo */}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Valor Activo (USD) <span className="text-red-500">*</span>{' '}
                      <span className="text-blue-600">(Manual)</span>
                    </label>

                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={Number.isFinite(valorActivo) ? valorActivo : ''}
                      onChange={e => {
                        const v =
                          e.target.value === '' ? 0 : parseFloat(e.target.value)

                        if (!Number.isNaN(v) && v >= 0) setValorActivo(v)
                      }}
                      disabled={isReadOnly}
                      placeholder="Ingrese el valor del activo en USD"
                    />

                    <p className="mt-1 text-xs text-gray-500">
                      Ingrese el valor manualmente. Si el modelo tiene precio
                      configurado, se puede cargar al seleccionarlo.
                    </p>
                  </div>

                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Anticipo (USD){' '}
                      <span className="text-green-600">
                        (Calculado: Valor Activo - Cuota x Cuotas)
                      </span>
                    </label>

                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={anticipo === 0 ? '' : anticipo.toFixed(2)}
                      readOnly
                      className="bg-gray-100"
                      disabled={isReadOnly}
                      placeholder="Se calcula al ingresar cuota y cuotas"
                    />

                    <p className="mt-1 text-xs text-gray-500">
                      Anticipo = Valor Activo menos (Cuota por periodo x Numero
                      de cuotas). Total financiamiento = cuota x cuotas.
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Total de Financiamiento (USD){' '}
                      <span className="text-red-500">*</span>
                    </label>

                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={
                        formData.total_financiamiento === 0
                          ? ''
                          : formData.total_financiamiento
                      }
                      readOnly
                      className="bg-gray-100"
                    />

                    <p className="mt-1 text-xs text-gray-500">
                      Cuota por periodo x Numero de cuotas (sincronizado con
                      Anticipo)
                    </p>
                  </div>

                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Modalidad de Pago <span className="text-red-500">*</span>
                    </label>

                    <Select
                      value={formData.modalidad_pago}
                      onValueChange={(value: any) =>
                        setFormData({
                          ...formData,

                          modalidad_pago: value,
                        })
                      }
                      disabled={isReadOnly}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>

                      <SelectContent>
                        <SelectItem value="MENSUAL">Mensual</SelectItem>

                        <SelectItem value="QUINCENAL">Quincenal</SelectItem>

                        <SelectItem value="SEMANAL">Semanal</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Número de Cuotas <span className="text-red-500">*</span>
                    </label>

                    <Input
                      type="number"
                      min={1}
                      max={50}
                      step={1}
                      value={numeroCuotas}
                      onChange={e => {
                        const value = parseInt(e.target.value, 10)

                        if (Number.isNaN(value)) return

                        const validValue = Math.max(1, Math.min(50, value))

                        setNumeroCuotas(validValue)
                      }}
                      disabled={isReadOnly || plazoCuotasBloqueadoLiquidado}
                      title={
                        plazoCuotasBloqueadoLiquidado
                          ? 'No se puede modificar en préstamos liquidados'
                          : undefined
                      }
                    />

                    <p className="mt-1 text-xs text-gray-500">
                      Entero entre 1 y 50
                      {plazoCuotasBloqueadoLiquidado
                        ? ' (bloqueado: préstamo liquidado)'
                        : ''}
                    </p>
                  </div>

                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Cuota por Periodo (USD){' '}
                      <span className="text-red-500">*</span>{' '}
                      <span className="text-blue-600">(Manual)</span>
                    </label>

                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={
                        cuotaPeriodo === 0
                          ? ''
                          : Number.isFinite(cuotaPeriodo)
                            ? cuotaPeriodo
                            : ''
                      }
                      onChange={e => {
                        const raw = e.target.value
                        if (raw === '') {
                          setCuotaPeriodo(0)
                          return
                        }
                        const v = parseFloat(raw)
                        if (!Number.isNaN(v) && v >= 0) setCuotaPeriodo(v)
                      }}
                      disabled={isReadOnly || plazoCuotasBloqueadoLiquidado}
                      placeholder="Ingrese la cuota por periodo"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Fecha de Requerimiento{' '}
                      <span className="text-red-500">*</span>
                    </label>

                    <Input
                      type="date"
                      value={formData.fecha_requerimiento}
                      onChange={e =>
                        setFormData({
                          ...formData,

                          fecha_requerimiento: e.target.value,
                        })
                      }
                      disabled={isReadOnly}
                    />
                  </div>

                  {prestamo ? (
                    <div>
                      <label className="mb-1 block text-sm font-medium">
                        Fecha de aprobación
                      </label>

                      <div className="mb-3 flex gap-2">
                        <Input
                          type="date"
                          value={formData.fecha_aprobacion || ''}
                          onChange={e =>
                            setFormData({
                              ...formData,

                              fecha_aprobacion: e.target.value || undefined,
                            })
                          }
                          disabled={isReadOnly}
                          className="flex-1"
                        />

                        {prestamo.estado === 'APROBADO' &&
                          formData.fecha_aprobacion &&
                          formData.fecha_aprobacion !==
                            fechaAprobacionAnterior && (
                            <Button
                              type="button"
                              size="sm"
                              onClick={recalcularAmortizacion}
                              disabled={
                                isRecalculatingAmortizacion || isReadOnly
                              }
                              className="whitespace-nowrap"
                            >
                              {isRecalculatingAmortizacion
                                ? 'Recalculando...'
                                : 'Recalcular Amortización'}
                            </Button>
                          )}
                      </div>

                      <p className="mt-1 text-xs text-gray-500">
                        Se guarda en BD al confirmar. Debe ser igual o posterior
                        a la fecha de requerimiento.
                      </p>
                    </div>
                  ) : null}
                </div>

                {prestamo && prestamo.estado === 'APROBADO' && (
                  <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
                    <h4 className="mb-2 font-semibold text-blue-900">
                      ðŸ"… Fecha de Desembolso (Día/Mes/Año)
                    </h4>

                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label className="mb-1 block text-sm font-medium">
                          Día <span className="text-red-500">*</span>
                        </label>

                        <Input
                          type="number"
                          min="1"
                          max="31"
                          value={
                            formData.fecha_base_calculo
                              ? formData.fecha_base_calculo.split('-')[2]
                              : ''
                          }
                          onChange={e => {
                            const dia = parseInt(e.target.value) || 1

                            const fechaActual =
                              formData.fecha_base_calculo || getCurrentDate()

                            const [año, mes] = fechaActual.split('-')

                            const nuevaFecha = `${año}-${mes}-${String(dia).padStart(2, '0')}`

                            setFormData({
                              ...formData,
                              fecha_base_calculo: nuevaFecha,
                            })
                          }}
                          disabled={isReadOnly}
                          placeholder="DD"
                        />
                      </div>

                      <div>
                        <label className="mb-1 block text-sm font-medium">
                          Mes <span className="text-red-500">*</span>
                        </label>

                        <Input
                          type="number"
                          min="1"
                          max="12"
                          value={
                            formData.fecha_base_calculo
                              ? formData.fecha_base_calculo.split('-')[1]
                              : ''
                          }
                          onChange={e => {
                            const mes = parseInt(e.target.value) || 1

                            const fechaActual =
                              formData.fecha_base_calculo || getCurrentDate()

                            const [año, , dia] = fechaActual.split('-')

                            const nuevaFecha = `${año}-${String(mes).padStart(2, '0')}-${dia}`

                            setFormData({
                              ...formData,
                              fecha_base_calculo: nuevaFecha,
                            })
                          }}
                          disabled={isReadOnly}
                          placeholder="MM"
                        />
                      </div>

                      <div>
                        <label className="mb-1 block text-sm font-medium">
                          Año <span className="text-red-500">*</span>
                        </label>

                        <Input
                          type="number"
                          min="2024"
                          max="2030"
                          value={
                            formData.fecha_base_calculo
                              ? formData.fecha_base_calculo.split('-')[0]
                              : ''
                          }
                          onChange={e => {
                            const año =
                              parseInt(e.target.value) ||
                              new Date().getFullYear()

                            const fechaActual =
                              formData.fecha_base_calculo || getCurrentDate()

                            const [, mes, dia] = fechaActual.split('-')

                            const nuevaFecha = `${año}-${mes}-${dia}`

                            setFormData({
                              ...formData,
                              fecha_base_calculo: nuevaFecha,
                            })
                          }}
                          disabled={isReadOnly}
                          placeholder="YYYY"
                        />
                      </div>
                    </div>

                    <p className="mt-2 text-xs text-blue-700">
                      Esta es la fecha desde la cual se calcularán las cuotas de
                      la tabla de amortización
                    </p>
                  </div>
                )}

                {/* Eliminados campos duplicados de Producto y Analista Asignado */}

                {/* Nuevos campos de configuración (sin Modelo aquí) */}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Concesionario
                    </label>

                    <Select
                      value={formData.concesionario ?? ''}
                      onValueChange={value =>
                        setFormData({
                          ...formData,

                          concesionario: value,
                        })
                      }
                      disabled={isReadOnly}
                    >
                      <SelectTrigger
                        className={
                          uiErrors.concesionario ? 'border-red-500' : undefined
                        }
                      >
                        <SelectValue placeholder="Seleccionar concesionario" />
                      </SelectTrigger>

                      <SelectContent>
                        {concesionarios.map(concesionario => (
                          <SelectItem
                            key={concesionario.id}
                            value={concesionario.nombre}
                          >
                            {concesionario.nombre}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {uiErrors.concesionario && (
                      <p className="mt-1 text-xs text-red-600">
                        Seleccione un concesionario
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="mb-1 block text-sm font-medium">
                      Analista
                    </label>

                    <Select
                      value={analistaSelectValue}
                      onValueChange={value => {
                        const idNum = value ? parseInt(value, 10) : NaN
                        const row = analistas.find(a => a.id === idNum)
                        setFormData({
                          ...formData,
                          analista_id: row ? row.id : undefined,
                          analista: row ? row.nombre : '',
                        })
                      }}
                      disabled={isReadOnly}
                    >
                      <SelectTrigger
                        className={
                          uiErrors.analista ? 'border-red-500' : undefined
                        }
                      >
                        <SelectValue placeholder="Seleccionar analista" />
                      </SelectTrigger>

                      <SelectContent>
                        {analistas.map(analista => (
                          <SelectItem
                            key={analista.id}
                            value={String(analista.id)}
                          >
                            {analista.nombre}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {uiErrors.analista && (
                      <p className="mt-1 text-xs text-red-600">
                        Seleccione un analista
                      </p>
                    )}
                  </div>

                  {/* Modelo movido arriba */}
                </div>

                <div>
                  <label className="mb-1 block text-sm font-medium">
                    Observaciones
                  </label>

                  <Textarea
                    value={formData.observaciones || ''}
                    onChange={e =>
                      setFormData({
                        ...formData,

                        observaciones: e.target.value,
                      })
                    }
                    disabled={isReadOnly}
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Botones de Aprobación (Solo ADMIN) */}

            {prestamo && canApprove && prestamo.estado === 'EN_REVISION' && (
              <Card className="border-yellow-200 bg-yellow-50">
                <CardContent className="pt-4">
                  <div className="flex gap-3">
                    <Button
                      type="button"
                      onClick={() => {
                        if (onAprobarManual && prestamo) {
                          onAprobarManual(prestamo)

                          onClose()
                        }
                      }}
                      className="flex-1 bg-green-600 hover:bg-green-700"
                    >
                      <CheckCircle2 className="mr-2 h-4 w-4" />
                      Aprobar
                    </Button>

                    <Button
                      type="button"
                      onClick={() => setShowRechazarDialog(true)}
                      variant="destructive"
                      className="flex-1"
                    >
                      <X className="mr-2 h-4 w-4" />
                      Rechazar
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Botones */}

            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>

              {!isReadOnly && (
                <Button type="submit">
                  <Save className="mr-2 h-4 w-4" />
                  {prestamo ? 'Actualizar' : 'Crear'} Préstamo
                </Button>
              )}

              {isReadOnly && <Button disabled>Modo Solo Lectura</Button>}
            </div>
          </form>

          {/* Modal de confirmación antes de crear préstamo */}

          <Dialog open={showConfirmCreate} onOpenChange={setShowConfirmCreate}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Confirmar creación de préstamo</DialogTitle>
              </DialogHeader>

              <p className="text-sm text-gray-600">
                El préstamo se registrará con los datos ingresados. Podrá
                editarlo mientras esté en estado Borrador o En Revisión. La
                tabla de amortización se generará al aprobar el préstamo, usando
                únicamente la fecha de aprobación. ¿Desea continuar?
              </p>

              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setShowConfirmCreate(false)}
                >
                  Cancelar
                </Button>

                <Button
                  onClick={() => crearOActualizarPrestamo()}
                  disabled={createPrestamo.isPending}
                >
                  {createPrestamo.isPending ? 'Guardando...' : 'Continuar'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* Modal de confirmación de rechazo */}

          <Dialog
            open={showRechazarDialog}
            onOpenChange={setShowRechazarDialog}
          >
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Confirmar rechazo del préstamo</DialogTitle>
              </DialogHeader>

              <p className="text-sm text-gray-600">
                ¿Está seguro de rechazar este préstamo? El estado cambiará a
                Rechazado y no podrá revertirse.
              </p>

              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setShowRechazarDialog(false)}
                >
                  Cancelar
                </Button>

                <Button
                  variant="destructive"
                  onClick={async () => {
                    if (prestamo?.id) {
                      await updatePrestamo.mutateAsync({
                        id: prestamo.id,

                        data: { estado: 'RECHAZADO' },
                      })

                      setShowRechazarDialog(false)

                      onSuccess()

                      onClose()
                    }
                  }}
                  disabled={updatePrestamo.isPending}
                >
                  {updatePrestamo.isPending ? 'Rechazando...' : 'Rechazar'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* Modal de Validación de Préstamos Existentes */}

          {showModalValidacion &&
            resumenPrestamos &&
            resumenPrestamos.tiene_prestamos && (
              <ModalValidacionPrestamoExistente
                prestamos={resumenPrestamos.prestamos || []}
                totalSaldo={resumenPrestamos.total_saldo_pendiente || 0}
                totalCuotasMora={resumenPrestamos.total_cuotas_mora || 0}
                onConfirm={handleConfirmarAutorizacion}
                onCancel={() => {
                  setShowModalValidacion(false)

                  setResumenPrestamos(null)

                  setJustificacionAutorizacion('')
                }}
              />
            )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
