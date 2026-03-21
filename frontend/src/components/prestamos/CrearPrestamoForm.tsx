import { useState, useEffect, useCallback } from 'react'
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
  CheckCircle2
} from 'lucide-react'
import { useDebounce } from '../../hooks/useDebounce'
import { useEscapeClose } from '../../hooks/useEscapeClose'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
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
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../../components/ui/dialog'
import { Prestamo, PrestamoForm } from '../../types'
import { ModalValidacionPrestamoExistente } from './ModalValidacionPrestamoExistente'

interface CrearPrestamoFormProps {
  prestamo?: Prestamo // PrÃÂ©stamo existente para ediciÃÂ³n
  onClose: () => void
  onSuccess: () => void
  onAprobarManual?: (prestamo: Prestamo) => void
}

export function CrearPrestamoForm({ prestamo, onClose, onSuccess, onAprobarManual }: CrearPrestamoFormProps) {
  const createPrestamo = useCreatePrestamo()
  const updatePrestamo = useUpdatePrestamo()
  const { canEditPrestamo, canApprovePrestamo } = usePermissions()

  // Cerrar con ESC
  useEscapeClose(onClose, true)

  // FunciÃÂ³n para obtener la fecha actual en formato YYYY-MM-DD
  const getCurrentDate = () => {
    const today = new Date()
    const year = today.getFullYear()
    const month = String(today.getMonth() + 1).padStart(2, '0')
    const day = String(today.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  const [formData, setFormData] = useState<Partial<PrestamoForm>>({
    cedula: prestamo?.cedula || '',
    total_financiamiento: prestamo?.total_financiamiento || 0,
    modalidad_pago: prestamo?.modalidad_pago || 'MENSUAL',
    fecha_requerimiento: prestamo?.fecha_requerimiento || '', // Fecha actual por defecto para nuevos prÃÂ©stamos
    fecha_aprobacion: prestamo?.fecha_aprobacion
      ? String(prestamo.fecha_aprobacion).slice(0, 10)
      : undefined,
    producto: prestamo?.producto || '',
    concesionario: prestamo?.concesionario || '',
    analista: prestamo?.analista || '',
    modelo_vehiculo: prestamo?.modelo_vehiculo || '',
    observaciones: prestamo?.observaciones || '',
  })

  // Obtener datos de configuraciÃÂ³n con manejo de errores
  const { data: concesionarios = [], error: errorConcesionarios } = useConcesionariosActivos()
  const { data: analistas = [], error: errorAnalistas } = useAnalistasActivos()
  const { data: modelosVehiculos = [], error: errorModelos } = useModelosVehiculosActivos()
  const { user } = useSimpleAuth()

  // Errores de carga de configuraciÃÂ³n (sin bloquear renderizado; solo en desarrollo se puede loguear)
  if (errorConcesionarios || errorAnalistas || errorModelos) {
    // Opcional: logger condicionado por NODE_ENV
  }

  const [valorActivo, setValorActivo] = useState<number>(prestamo?.valor_activo || 0)

  // Estados para validaciÃÂ³n de prÃÂ©stamos existentes
  const [showModalValidacion, setShowModalValidacion] = useState(false)
  const [resumenPrestamos, setResumenPrestamos] = useState<any>(null)
  const [justificacionAutorizacion, setJustificacionAutorizacion] = useState('')
  const [anticipo, setAnticipo] = useState<number>(0)
  const [showAdditionalInfo, setShowAdditionalInfo] = useState(false)
  const [clienteData, setClienteData] = useState<any>(null)
  const [numeroCuotas, setNumeroCuotas] = useState<number>(12) // Valor por defecto: 12 cuotas
  const [cuotaPeriodo, setCuotaPeriodo] = useState<number>(0)
  const [showConfirmCreate, setShowConfirmCreate] = useState(false)
  const [showRechazarDialog, setShowRechazarDialog] = useState(false)

  // Errores de UI para marcar campos obligatorios visualmente
  const [uiErrors, setUiErrors] = useState<{ concesionario?: boolean; analista?: boolean }>({})

  // Calcular anticipo como 30% del valor activo automÃÂ¡ticamente al inicio o cuando cambia el valor activo
  // Solo si no hay un anticipo ya establecido (para nuevos prÃÂ©stamos) o si el anticipo es igual al 30% calculado
  useEffect(() => {
    if (valorActivo > 0) {
      const anticipoCalculado = valorActivo * 0.30
      // Solo actualizar automÃÂ¡ticamente si el anticipo actual es 0 o igual al 30% calculado
      // Esto permite que el usuario modifique el anticipo sin que se sobrescriba cuando cambia el valor activo
      setAnticipo((prevAnticipo) => {
        if (prevAnticipo === 0 || Math.abs(prevAnticipo - anticipoCalculado) < 0.01) {
          return anticipoCalculado
        }
        return prevAnticipo
      })
    } else {
      setAnticipo(0)
    }
  }, [valorActivo])

  // Si se selecciona modelo o llegan modelos desde configuraciÃÂ³n, cargar su precio
  useEffect(() => {
    if (formData.modelo_vehiculo && modelosVehiculos && modelosVehiculos.length > 0) {
      const modeloSel: any = modelosVehiculos.find((m: any) => m.modelo === formData.modelo_vehiculo)
      if (modeloSel && modeloSel.precio != null) {
        const precioNum = typeof modeloSel.precio === 'number' ? modeloSel.precio : parseFloat(String(modeloSel.precio))
        if (!Number.isNaN(precioNum)) {
          setValorActivo(precioNum)
        }
      }
    }
  }, [formData.modelo_vehiculo, modelosVehiculos])

  // Calcular total_financiamiento automÃÂ¡ticamente
  useEffect(() => {
    const total = valorActivo - anticipo
    setFormData(prev => ({
      ...prev,
      total_financiamiento: Math.max(0, total)
    }))
  }, [valorActivo, anticipo])

  // Buscar cliente por cÃÂ©dula con debounce mejorado
  const debouncedCedula = useDebounce(formData.cedula || '', 500)
  const { data: clienteInfo, isLoading: isLoadingCliente } = useSearchClientes(
    debouncedCedula && debouncedCedula.length >= 2 ? debouncedCedula : ''
  )

  // Calcular cuota por perÃÂ­odo basado en el nÃÂºmero de cuotas manual
  useEffect(() => {
    if (formData.total_financiamiento && formData.total_financiamiento > 0 && numeroCuotas > 0) {
      const cuota = formData.total_financiamiento / numeroCuotas
      setCuotaPeriodo(cuota)
    } else {
      setCuotaPeriodo(0)
    }
  }, [formData.total_financiamiento, numeroCuotas])


  // Cargar datos del cliente cuando se encuentra
  // IMPORTANTE: Solo recibimos clientes ACTIVOS gracias al filtro en el servicio
  useEffect(() => {
    if (clienteInfo && clienteInfo.length > 0) {
      const cliente = clienteInfo[0]
      // Establecer clienteData con todos los datos del cliente disponibles
      // El modelo Cliente contiene: id, cedula, nombres, telefono, email, direccion,
      // fecha_nacimiento, ocupacion, estado, fecha_registro, fecha_actualizacion, usuario_registro, notas
      setClienteData(cliente)
      // No autocompletamos campos del prÃÂ©stamo porque el cliente no tiene esos datos
      // (modelo_vehiculo, analista, concesionario son campos del prÃÂ©stamo, no del cliente)
    } else if (formData.cedula && formData.cedula.length >= 2 && clienteInfo && clienteInfo.length === 0) {
      // Cliente no encontrado o no estÃÂ¡ ACTIVO (no aparecerÃÂ¡ en la bÃÂºsqueda)
      setClienteData(null)
    }
  }, [clienteInfo, formData.cedula])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Validaciones requeridas
    const errors: string[] = []

    // Validar cÃÂ©dula
    if (!formData.cedula || formData.cedula.trim() === '') {
      errors.push('La cÃÂ©dula es requerida')
    }

    // Validar que el cliente exista (solo para nuevos prÃÂ©stamos)
    // NOTA: Solo aparecen clientes ACTIVOS en la bÃÂºsqueda, pero validamos por seguridad
    if (!prestamo && !clienteData) {
      errors.push('Debe buscar y seleccionar un cliente vÃÂ¡lido con estado ACTIVO')
    }

    // Validar Valor Activo
    if (valorActivo <= 0) {
      errors.push('El Valor Activo debe ser mayor a 0')
    }

    // Validar Anticipo - debe ser al menos el 30% del valor activo
    const anticipoMinimo = valorActivo > 0 ? valorActivo * 0.30 : 0
    if (anticipo < anticipoMinimo) {
      errors.push(`El Anticipo debe ser al menos el 30% del Valor Activo (mÃÂ­nimo: ${anticipoMinimo.toFixed(2)} USD)`)
    }
    if (anticipo < 0) {
      errors.push('El Anticipo no puede ser negativo')
    }

    // Validar NÃÂºmero de Cuotas
    if (numeroCuotas < 1 || numeroCuotas > 50 || !Number.isInteger(numeroCuotas)) {
      errors.push('El nÃÂºmero de cuotas debe ser un entero entre 1 y 50')
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
    if (!formData.fecha_requerimiento || formData.fecha_requerimiento.trim() === '') {
      errors.push('La fecha de requerimiento es requerida')
    }

    // Requeridos adicionales del formulario
    const faltaConcesionario = !formData.concesionario || String(formData.concesionario).trim() === ''
    const faltaAnalista = !formData.analista || String(formData.analista).trim() === ''
    if (faltaConcesionario) errors.push('Debe seleccionar un Concesionario')
    if (faltaAnalista) errors.push('Debe seleccionar un Analista')
    setUiErrors({ concesionario: faltaConcesionario, analista: faltaAnalista })
    if (!formData.modelo_vehiculo || String(formData.modelo_vehiculo).trim() === '') {
      errors.push('Debe seleccionar un Modelo de VehÃÂ­culo')
    }

    // Si hay errores, mostrar notificaciÃÂ³n consolidada y bloquear envÃÂ­o
    if (errors.length > 0) {
      const listado = errors.map(e => `Ã¢ÂÂ¢ ${e}`).join('\n')
      toast.error(`Faltan datos obligatorios:\n${listado}`)
      // Desplazar al inicio del formulario para que el operador corrija
      try {
        const formEl = (e.target as HTMLFormElement)
        formEl?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      } catch {}
      return
    }

    // Si es un nuevo prÃÂ©stamo, verificar si el cliente ya tiene prÃÂ©stamos
    if (!prestamo && formData.cedula) {
      try {
        const resumen = await prestamoService.getResumenPrestamos(formData.cedula)
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

    // Para nuevo prÃÂ©stamo: mostrar modal de confirmaciÃÂ³n accesible
    if (!prestamo) {
      setShowConfirmCreate(true)
      return
    }

    // EdiciÃÂ³n: proceder directamente
    await crearOActualizarPrestamo()
  }

  const crearOActualizarPrestamo = async () => {
    try {
      setShowConfirmCreate(false)
      // Preparar datos con numero_cuotas y cuota_periodo
      const prestamoData: Record<string, unknown> = {
        ...formData,
        modelo: formData.modelo_vehiculo ? undefined,
        valor_activo: valorActivo > 0 ? valorActivo : undefined,
        producto: formData.producto && String(formData.producto).trim() !== ''
          ? formData.producto
          : (formData.modelo_vehiculo || ''),
        analista: formData.analista && String(formData.analista).trim() !== ''
          ? formData.analista
          : '',
        numero_cuotas: numeroCuotas,
        cuota_periodo: cuotaPeriodo,
        fecha_base_calculo: formData.fecha_base_calculo,
        ...(prestamo &&
        formData.fecha_aprobacion &&
        String(formData.fecha_aprobacion).trim() !== ""
          ? { fecha_aprobacion: String(formData.fecha_aprobacion).trim() + "T00:00:00" }
          : {}),
        usuario_autoriza: !prestamo && justificacionAutorizacion ? user?.email : undefined,
        observaciones: justificacionAutorizacion
          ? `${formData.observaciones || ''}\n\n--- JUSTIFICACIÃÂN PARA NUEVO PRÃÂSTAMO ---\n${justificacionAutorizacion}`.trim()
          : formData.observaciones,
      }

      if (prestamo) {
        await updatePrestamo.mutateAsync({
          id: prestamo.id,
          data: prestamoData as Partial<PrestamoForm>
        })
      } else {
        // Backend exige cliente_id para crear; se toma del cliente buscado por cÃÂ©dula
        if (clienteData?.id != null) {
          prestamoData.cliente_id = clienteData.id
        }
        await createPrestamo.mutateAsync(prestamoData as unknown as PrestamoForm)
      }

      onSuccess()
      onClose()
    } catch (error) {
      toast.error('Error al guardar el prÃÂ©stamo')
      if (import.meta.env.DEV) {
        console.error('Error saving loan:', error)
      }
    }
  }

  const handleConfirmarAutorizacion = (justificacion: string) => {
    setJustificacionAutorizacion(justificacion)
    setShowModalValidacion(false)
    // Continuar con la creaciÃÂ³n del prÃÂ©stamo
    crearOActualizarPrestamo()
  }

  // Verificar permisos de ediciÃÂ³n - PolÃÂ­tica: no se permite ediciÃÂ³n de prÃÂ©stamos ya creados
  // Permitir ediciÃÂ³n si el usuario tiene permisos y estÃÂ¡ editando un prÃÂ©stamo
  const isReadOnly = prestamo ? !canEditPrestamo(prestamo.estado || '') : false
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
          className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="sticky top-0 bg-white border-b p-4 flex justify-between items-center z-10">
            <h2 className="text-xl font-bold">
              {prestamo ? 'Editar PrÃÂ©stamo' : 'Nuevo PrÃÂ©stamo'}
            </h2>
            {/* BotÃÂ³n X eliminado - solo se puede cerrar con Cancelar o Crear */}
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {/* BÃÂºsqueda de Cliente */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="h-5 w-5" />
                  BÃÂºsqueda de Cliente
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Seleccionar primero el Modelo para cargar el precio */}
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Modelo de VehÃÂ­culo <span className="text-red-500">*</span>
                  </label>
                  <Select
                    value={formData.modelo_vehiculo ? ''}
                    onValueChange={(value) => {
                      setFormData({
                        ...formData,
                        modelo_vehiculo: value,
                      })
                      const modeloSel = modelosVehiculos.find((m:any) => m.modelo === value)
                      if (modeloSel && modeloSel.precio != null) {
                        const precioNum = typeof modeloSel.precio === 'number' ? modeloSel.precio : parseFloat(String(modeloSel.precio))
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
                      {modelosVehiculos.map((modelo) => (
                        <SelectItem key={modelo.id} value={modelo.modelo}>
                          {modelo.modelo}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-gray-500 mt-1">Seleccione el modelo. Si tiene precio configurado, se cargarÃÂ¡ en Valor Activo; si no, ingrÃÂ©selo manualmente.</p>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    CÃÂ©dula <span className="text-red-500">*</span>
                  </label>
                  <Input
                    placeholder="Buscar por cÃÂ©dula..."
                    value={formData.cedula}
                    onChange={(e) => setFormData({ ...formData, cedula: e.target.value.toUpperCase() })}
                    disabled={isReadOnly || isLoadingCliente}
                  />
                </div>

                            {isLoadingCliente && formData.cedula && formData.cedula.length >= 2 && (
                              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-3">
                                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                                <p className="text-sm text-blue-800">Buscando cliente...</p>
                              </div>
                            )}

                            {clienteData && !isLoadingCliente && (
                              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                                <div className="flex items-center gap-2 mb-2">
                                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                                  <p className="font-semibold text-green-800">{clienteData.nombres}</p>
                                </div>
                                <p className="text-sm text-green-700">Cliente encontrado y datos cargados automÃÂ¡ticamente</p>
                              </div>
                            )}

                            {!clienteData && !isLoadingCliente && formData.cedula && formData.cedula.length >= 2 && (
                              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                                <div className="flex items-center gap-2">
                                  <AlertCircle className="h-5 w-5 text-red-600" />
                                  <p className="text-sm text-red-800">Cliente no encontrado con esta cÃÂ©dula</p>
                                </div>
                              </div>
                            )}
              </CardContent>
            </Card>

            {/* InformaciÃÂ³n Adicional del Cliente (Colapsable) */}
            {clienteData && (
              <Card>
                <CardHeader>
                  <button
                    type="button"
                    onClick={() => setShowAdditionalInfo(!showAdditionalInfo)}
                    className="flex items-center justify-between w-full"
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
                            <label className="text-sm text-gray-600">CÃÂ©dula</label>
                            <p className="font-medium">{clienteData.cedula}</p>
                          </div>
                          <div>
                            <label className="text-sm text-gray-600">Nombres Completos</label>
                            <p className="font-medium">{clienteData.nombres}</p>
                          </div>
                          <div>
                            <label className="text-sm text-gray-600">TelÃÂ©fono</label>
                            <p className="font-medium">{clienteData.telefono || 'N/A'}</p>
                          </div>
                          <div>
                            <label className="text-sm text-gray-600">Email</label>
                            <p className="font-medium">{clienteData.email || 'N/A'}</p>
                          </div>
                          <div>
                            <label className="text-sm text-gray-600">DirecciÃÂ³n</label>
                            <p className="font-medium">{clienteData.direccion || 'N/A'}</p>
                          </div>
                          <div>
                            <label className="text-sm text-gray-600">Fecha de Nacimiento</label>
                            <p className="font-medium">
                              {clienteData.fecha_nacimiento 
                                ? new Date(clienteData.fecha_nacimiento).toLocaleDateString('es-VE')
                                : 'N/A'}
                            </p>
                          </div>
                          <div>
                            <label className="text-sm text-gray-600">OcupaciÃÂ³n</label>
                            <p className="font-medium">{clienteData.ocupacion || 'N/A'}</p>
                          </div>
                          <div>
                            <label className="text-sm text-gray-600">Estado</label>
                            <Badge variant={clienteData.estado === 'ACTIVO' ? 'default' : 'secondary'}>
                              {clienteData.estado}
                            </Badge>
                          </div>
                          {clienteData.notas && clienteData.notas !== 'NA' && (
                            <div className="col-span-2">
                              <label className="text-sm text-gray-600">Notas</label>
                              <p className="font-medium text-sm">{clienteData.notas}</p>
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </motion.div>
                  )}
                </AnimatePresence>
              </Card>
            )}

            {/* Datos del PrÃÂ©stamo */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5" />
                  Datos del PrÃÂ©stamo
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Nuevos campos: Valor Activo y Anticipo */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Valor Activo (USD) <span className="text-red-500">*</span> <span className="text-blue-600">(Manual)</span>
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={Number.isFinite(valorActivo) ? valorActivo : ''}
                      onChange={(e) => {
                        const v = e.target.value === '' ? 0 : parseFloat(e.target.value)
                        if (!Number.isNaN(v) && v >= 0) setValorActivo(v)
                      }}
                      disabled={isReadOnly}
                      placeholder="Ingrese el valor del activo en USD"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Ingrese el valor manualmente. Si el modelo tiene precio configurado, se puede cargar al seleccionarlo.
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Anticipo (USD) <span className="text-green-600">(AutomÃÂ¡tico - 30%)</span>
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      min={valorActivo > 0 ? (valorActivo * 0.30).toFixed(2) : "0"}
                      value={anticipo === 0 ? '' : anticipo.toFixed(2)}
                      onChange={(e) => {
                        const value = e.target.value
                        const numericValue = value === '' ? 0 : parseFloat(value)
                        if (!isNaN(numericValue) && numericValue >= 0) {
                          setAnticipo(numericValue)
                        }
                      }}
                      onBlur={(e) => {
                        const value = parseFloat(e.target.value)
                        const anticipoMinimo = valorActivo > 0 ? valorActivo * 0.30 : 0
                        // Si el valor es menor al mÃÂ­nimo, establecer el mÃÂ­nimo
                        if (!isNaN(value) && value < anticipoMinimo) {
                          setAnticipo(anticipoMinimo)
                          toast.warning(`El anticipo mÃÂ­nimo es ${anticipoMinimo.toFixed(2)} USD (30% del valor activo)`)
                        } else if (!isNaN(value) && value >= anticipoMinimo) {
                          setAnticipo(value)
                        }
                      }}
                      disabled={isReadOnly}
                      placeholder="MÃÂ­nimo 30% del Valor Activo"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      {valorActivo > 0 
                        ? `MÃÂ­nimo: ${(valorActivo * 0.30).toFixed(2)} USD (30% del Valor Activo)`
                        : '30% del Valor Activo'}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Total de Financiamiento (USD) <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.total_financiamiento === 0 ? '' : formData.total_financiamiento}
                      readOnly
                      className="bg-gray-100"
                    />
                    <p className="text-xs text-gray-500 mt-1">Calculado automÃÂ¡ticamente (Valor Activo - Anticipo)</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Modalidad de Pago <span className="text-red-500">*</span>
                    </label>
                    <Select
                      value={formData.modalidad_pago}
                      onValueChange={(value: any) => setFormData({
                        ...formData,
                        modalidad_pago: value
                      })}
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
                    <label className="block text-sm font-medium mb-1">NÃÂºmero de Cuotas <span className="text-red-500">*</span></label>
                    <Input
                      type="number"
                      min={1}
                      max={50}
                      step={1}
                      value={numeroCuotas}
                      onChange={(e) => {
                        const value = parseInt(e.target.value, 10)
                        if (Number.isNaN(value)) return
                        const validValue = Math.max(1, Math.min(50, value))
                        setNumeroCuotas(validValue)
                      }}
                      disabled={isReadOnly}
                    />
                    <p className="text-xs text-gray-500 mt-1">Entero entre 1 y 50</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">Cuota por PerÃÂ­odo (USD)</label>
                    <Input
                      value={cuotaPeriodo.toFixed(2)}
                      disabled
                      className="bg-gray-50"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Fecha de Requerimiento <span className="text-red-500">*</span>
                    </label>
                    <Input
                      type="date"
                      value={formData.fecha_requerimiento}
                      onChange={(e) => setFormData({
                        ...formData,
                        fecha_requerimiento: e.target.value
                      })}
                      disabled={isReadOnly}
                    />
                  </div>
                  {prestamo ? (
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Fecha de aprobaciÃÂ³n
                      </label>
                      <Input
                        type="date"
                        value={formData.fecha_aprobacion || ""}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            fecha_aprobacion: e.target.value || undefined,
                          })
                        }
                        disabled={isReadOnly}
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Se guarda en BD al confirmar. Debe ser igual o posterior a la fecha de requerimiento.
                      </p>
                    </div>
                  ) : null}
                </div>

                {prestamo && prestamo.estado === 'APROBADO' && (
                  <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h4 className="font-semibold text-blue-900 mb-2">ÃÂ°ÃÂ¸Ã¢ÂÂÃ¢ÂÂ¦ Fecha de Desembolso (DÃÂ­a/Mes/AÃÂ±o)</h4>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          DÃÂ­a <span className="text-red-500">*</span>
                        </label>
                        <Input
                          type="number"
                          min="1"
                          max="31"
                          value={formData.fecha_base_calculo ? formData.fecha_base_calculo.split('-')[2] : ''}
                          onChange={(e) => {
                            const dia = parseInt(e.target.value) || 1
                            const fechaActual = formData.fecha_base_calculo || getCurrentDate()
                            const [aÃÂ±o, mes] = fechaActual.split('-')
                            const nuevaFecha = `${aÃÂ±o}-${mes}-${String(dia).padStart(2, '0')}`
                            setFormData({ ...formData, fecha_base_calculo: nuevaFecha })
                          }}
                          disabled={isReadOnly}
                          placeholder="DD"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          Mes <span className="text-red-500">*</span>
                        </label>
                        <Input
                          type="number"
                          min="1"
                          max="12"
                          value={formData.fecha_base_calculo ? formData.fecha_base_calculo.split('-')[1] : ''}
                          onChange={(e) => {
                            const mes = parseInt(e.target.value) || 1
                            const fechaActual = formData.fecha_base_calculo || getCurrentDate()
                            const [aÃÂ±o, , dia] = fechaActual.split('-')
                            const nuevaFecha = `${aÃÂ±o}-${String(mes).padStart(2, '0')}-${dia}`
                            setFormData({ ...formData, fecha_base_calculo: nuevaFecha })
                          }}
                          disabled={isReadOnly}
                          placeholder="MM"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-1">
                          AÃÂ±o <span className="text-red-500">*</span>
                        </label>
                        <Input
                          type="number"
                          min="2024"
                          max="2030"
                          value={formData.fecha_base_calculo ? formData.fecha_base_calculo.split('-')[0] : ''}
                          onChange={(e) => {
                            const aÃÂ±o = parseInt(e.target.value) || new Date().getFullYear()
                            const fechaActual = formData.fecha_base_calculo || getCurrentDate()
                            const [, mes, dia] = fechaActual.split('-')
                            const nuevaFecha = `${aÃÂ±o}-${mes}-${dia}`
                            setFormData({ ...formData, fecha_base_calculo: nuevaFecha })
                          }}
                          disabled={isReadOnly}
                          placeholder="YYYY"
                        />
                      </div>
                    </div>
                    <p className="text-xs text-blue-700 mt-2">
                      Esta es la fecha desde la cual se calcularÃÂ¡n las cuotas de la tabla de amortizaciÃÂ³n
                    </p>
                  </div>
                )}

                {/* Eliminados campos duplicados de Producto y Analista Asignado */}

                {/* Nuevos campos de configuraciÃÂ³n (sin Modelo aquÃÂ­) */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Concesionario
                    </label>
                  <Select
                      value={formData.concesionario ? ''}
                      onValueChange={(value) => setFormData({
                        ...formData,
                        concesionario: value
                      })}
                      disabled={isReadOnly}
                    >
                    <SelectTrigger className={uiErrors.concesionario ? 'border-red-500' : undefined}>
                        <SelectValue placeholder="Seleccionar concesionario" />
                      </SelectTrigger>
                      <SelectContent>
                        {concesionarios.map((concesionario) => (
                          <SelectItem key={concesionario.id} value={concesionario.nombre}>
                            {concesionario.nombre}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  {uiErrors.concesionario && (
                    <p className="mt-1 text-xs text-red-600">Seleccione un concesionario</p>
                  )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Analista
                    </label>
                  <Select
                      value={formData.analista ? ''}
                      onValueChange={(value) => setFormData({
                        ...formData,
                        analista: value
                      })}
                      disabled={isReadOnly}
                    >
                    <SelectTrigger className={uiErrors.analista ? 'border-red-500' : undefined}>
                        <SelectValue placeholder="Seleccionar analista" />
                      </SelectTrigger>
                      <SelectContent>
                        {analistas.map((analista) => (
                          <SelectItem key={analista.id} value={analista.nombre}>
                            {analista.nombre}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  {uiErrors.analista && (
                    <p className="mt-1 text-xs text-red-600">Seleccione un analista</p>
                  )}
                  </div>

                  {/* Modelo movido arriba */}
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Observaciones</label>
                  <Textarea
                    value={formData.observaciones || ''}
                    onChange={(e) => setFormData({
                      ...formData,
                      observaciones: e.target.value
                    })}
                    disabled={isReadOnly}
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Botones de AprobaciÃÂ³n (Solo ADMIN) */}
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
                      <CheckCircle2 className="h-4 w-4 mr-2" />
                      Aprobar
                    </Button>
                    <Button
                      type="button"
                      onClick={() => setShowRechazarDialog(true)}
                      variant="destructive"
                      className="flex-1"
                    >
                      <X className="h-4 w-4 mr-2" />
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
                  <Save className="h-4 w-4 mr-2" />
                  {prestamo ? 'Actualizar' : 'Crear'} PrÃÂ©stamo
                </Button>
              )}
              {isReadOnly && (
                <Button disabled>
                  Modo Solo Lectura
                </Button>
              )}
            </div>
          </form>

          {/* Modal de confirmaciÃÂ³n antes de crear prÃÂ©stamo */}
          <Dialog open={showConfirmCreate} onOpenChange={setShowConfirmCreate}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Confirmar creaciÃÂ³n de prÃÂ©stamo</DialogTitle>
              </DialogHeader>
              <p className="text-sm text-gray-600">
                El prÃÂ©stamo se registrarÃÂ¡ con los datos ingresados. PodrÃÂ¡ editarlo mientras estÃÂ© en estado Borrador o En RevisiÃÂ³n.
                La tabla de amortizaciÃÂ³n se generarÃÂ¡ al aprobar el prÃÂ©stamo, usando ÃÂºnicamente la fecha de aprobaciÃÂ³n.
                ÃÂ¿Desea continuar?
              </p>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowConfirmCreate(false)}>
                  Cancelar
                </Button>
                <Button onClick={() => crearOActualizarPrestamo()} disabled={createPrestamo.isPending}>
                  {createPrestamo.isPending ? 'Guardando...' : 'Continuar'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* Modal de confirmaciÃÂ³n de rechazo */}
          <Dialog open={showRechazarDialog} onOpenChange={setShowRechazarDialog}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Confirmar rechazo del prÃÂ©stamo</DialogTitle>
              </DialogHeader>
              <p className="text-sm text-gray-600">
                ÃÂ¿EstÃÂ¡ seguro de rechazar este prÃÂ©stamo? El estado cambiarÃÂ¡ a Rechazado y no podrÃÂ¡ revertirse.
              </p>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowRechazarDialog(false)}>
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

          {/* Modal de ValidaciÃÂ³n de PrÃÂ©stamos Existentes */}
          {showModalValidacion && resumenPrestamos && resumenPrestamos.tiene_prestamos && (
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
