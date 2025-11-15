import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  Calculator, 
  AlertCircle,
  X,
  CheckCircle,
  Info,
  TrendingUp,
  TrendingDown,
  MapPin,
  Users,
  Calendar,
  DollarSign,
  Brain,
  Shield
} from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useEscapeClose } from '@/hooks/useEscapeClose'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { usePermissions } from '@/hooks/usePermissions'
import { useAplicarCondicionesAprobacion, useUpdatePrestamo } from '@/hooks/usePrestamos'
import { Prestamo } from '@/types'
import { prestamoService } from '@/services/prestamoService'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { clienteService } from '@/services/clienteService'
import { toast } from 'sonner'

interface EvaluacionRiesgoFormProps {
  prestamo: Prestamo
  onClose: () => void
  onSuccess: () => void
}

interface EvaluacionFormData {
  // Criterio 1: Capacidad de Pago
  ingresos_mensuales: number
  gastos_fijos_mensuales: number
  otras_deudas: number
  
  // Criterio 2: Estabilidad Laboral
  meses_trabajo: number
  tipo_empleo: string
  sector_economico: string
  
  // Criterio 3: Referencias (3 referencias individuales)
  referencia1_observaciones: string
  referencia1_calificacion: number  // 3=Recomendable, 2=Dudosa, 1=No recomendable
  referencia2_observaciones: string
  referencia2_calificacion: number
  referencia3_observaciones: string
  referencia3_calificacion: number
  
  // Criterio 4: Arraigo Geográfico (7 puntos - sin tipo_vivienda)
  familia_cercana: boolean
  familia_pais: boolean
  minutos_trabajo: number
  
  // Criterio 5: Perfil Sociodemográfico
  tipo_vivienda_detallado: string
  zona_urbana: boolean
  servicios_nombre: boolean
  zona_rural: boolean
  personas_casa: number
  estado_civil: string
  pareja_trabaja: boolean
  pareja_aval: boolean
  pareja_desempleada: boolean
  relacion_conflictiva: boolean
  situacion_hijos: string
  todos_estudian: boolean
  viven_con_cliente: boolean
  necesidades_especiales: boolean
  viven_con_ex: boolean
  embarazo_actual: boolean
  
  // Criterio 6: Edad
  edad: number
  
  // Criterio 7: Capacidad de Maniobra (no requiere campos adicionales)
}

export function EvaluacionRiesgoForm({ prestamo, onClose, onSuccess }: EvaluacionRiesgoFormProps) {
  // Permitir cerrar con Escape
  useEscapeClose(onClose, true)
  const { isAdmin } = usePermissions()
  const { user } = useSimpleAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [isAprobando, setIsAprobando] = useState(false)
  const [resultado, setResultado] = useState<any>(null)
  const [showSection, setShowSection] = useState<string>('criterio1')
  const [clienteEdad, setClienteEdad] = useState<number>(0)
  const [showFormularioAprobacion, setShowFormularioAprobacion] = useState(false)
  const [resumenPrestamos, setResumenPrestamos] = useState<any | null>(null)
  const [bloqueadoPorMora, setBloqueadoPorMora] = useState<boolean>(false)
  
  // Estado para condiciones editables de aprobación
  const [condicionesAprobacion, setCondicionesAprobacion] = useState({
    tasa_interes: 0.0,
    plazo_maximo: 36,
    fecha_base_calculo: new Date().toISOString().split('T')[0],
    observaciones: ''
  })
  
  const aplicarCondiciones = useAplicarCondicionesAprobacion()
  const updatePrestamo = useUpdatePrestamo()

  // (moved below formData) - reglas de completitud por sección
  
  // Calcular edad automáticamente desde la cédula del préstamo
  useEffect(() => {
    const calcularEdad = async () => {
      try {
        // Obtener información del cliente por su cédula usando el servicio
        const response = await clienteService.getClientes({ cedula: prestamo.cedula })
        
        if (response && response.data && response.data.length > 0) {
          const cliente = response.data[0]
          if (cliente.fecha_nacimiento) {
            // Calcular edad desde fecha de nacimiento
            const hoy = new Date()
            const nacimiento = new Date(cliente.fecha_nacimiento)
            let años = hoy.getFullYear() - nacimiento.getFullYear()
            const diferenciaMeses = hoy.getMonth() - nacimiento.getMonth()
            
            if (diferenciaMeses < 0 || (diferenciaMeses === 0 && hoy.getDate() < nacimiento.getDate())) {
              años -= 1
            }
            
            // Calcular meses adicionales
            let meses = 0
            if (hoy.getMonth() >= nacimiento.getMonth()) {
              meses = hoy.getMonth() - nacimiento.getMonth()
              if (hoy.getDate() < nacimiento.getDate()) {
                meses -= 1
              }
            } else {
              meses = (12 - nacimiento.getMonth()) + hoy.getMonth()
              if (hoy.getDate() < nacimiento.getDate()) {
                meses -= 1
              }
            }
            
            // Edad en años decimales
            const edadDecimal = años + (meses / 12)
            setClienteEdad(edadDecimal)
          }
        }
      } catch (error) {
        console.error('Error calculando edad:', error)
      }
    }
    
    calcularEdad()
  }, [prestamo.cedula])

  // Cargar resumen por cédula para validar si existen préstamos y cuotas en mora
  useEffect(() => {
    const cargarResumen = async () => {
      try {
        const resumen = await prestamoService.getResumenPrestamos(prestamo.cedula)
        setResumenPrestamos(resumen)
        const tieneMora = (resumen?.total_cuotas_mora || 0) > 0
        setBloqueadoPorMora(tieneMora)
        if (tieneMora) {
          setShowSection('situacion')
        }
      } catch (e) {
        setResumenPrestamos({ error: true, tiene_prestamos: false, prestamos: [] })
      }
    }
    cargarResumen()
  }, [prestamo.cedula])

  // Actualizar condiciones de aprobación cuando hay resultado de evaluación
  useEffect(() => {
    if (resultado?.sugerencias) {
      setCondicionesAprobacion({
        tasa_interes: resultado.sugerencias.tasa_interes_sugerida || 8.0,
        plazo_maximo: resultado.sugerencias.plazo_maximo_sugerido || 36,
        fecha_base_calculo: new Date().toISOString().split('T')[0],
        observaciones: `Aprobado después de evaluación de riesgo. Puntuación: ${resultado.puntuacion_total?.toFixed(2)}/100, Riesgo: ${resultado.clasificacion_riesgo}`
      })
      // Mostrar automáticamente el formulario de aprobación cuando hay resultado
      setShowFormularioAprobacion(true)
    }
  }, [resultado])
  
  if (!isAdmin) {
    return null
  }
  
  const [formData, setFormData] = useState<EvaluacionFormData>({
    // Criterio 1: Capacidad de Pago (33 puntos)
    ingresos_mensuales: 0,
    gastos_fijos_mensuales: 0,
    otras_deudas: 0,
    
    // Criterio 2: Estabilidad Laboral (23 puntos)
    meses_trabajo: 0,
    tipo_empleo: 'empleado_formal',
    sector_economico: 'servicios_esenciales',
    
    // Criterio 3: Referencias Personales (9 puntos)
    referencia1_observaciones: '',
    referencia1_calificacion: 0,
    referencia2_observaciones: '',
    referencia2_calificacion: 0,
    referencia3_observaciones: '',
    referencia3_calificacion: 0,
    
    // Criterio 4: Arraigo Geográfico (7 puntos - sin tipo_vivienda)
    familia_cercana: false,
    familia_pais: false,
    minutos_trabajo: 0,
    
    // Criterio 5: Perfil Sociodemográfico (17 puntos)
    tipo_vivienda_detallado: 'alquiler_1_3',
    zona_urbana: false,
    servicios_nombre: false,
    zona_rural: false,
    personas_casa: 1,
    estado_civil: 'soltero_sin_pareja',
    pareja_trabaja: false,
    pareja_aval: false,
    pareja_desempleada: false,
    relacion_conflictiva: false,
    situacion_hijos: 'sin_hijos_no_planea',
    todos_estudian: false,
    viven_con_cliente: false,
    necesidades_especiales: false,
    viven_con_ex: false,
    embarazo_actual: false,
    
    // Criterio 6: Edad del Cliente (10 puntos)
    edad: 0,
    
    // Criterio 7: Capacidad de Maniobra (5 puntos - NO requiere campos adicionales)
    // Se calcula automáticamente: Saldo Residual = Ingresos - Gastos - Deudas - Cuota
  })

  // Reglas mínimas para considerar cada sección completa
  const seccion1Completa =
    (formData.ingresos_mensuales ?? 0) > 0 &&
    (formData.gastos_fijos_mensuales ?? 0) >= 0 &&
    (formData.otras_deudas ?? 0) >= 0

  const seccion2Completa =
    (formData.meses_trabajo ?? 0) >= 0 && !!formData.tipo_empleo && !!formData.sector_economico

  // TODO: Añadir secciones 3–5 como obligatorias (cuando definamos mínimos)
  const todasSeccionesCompletas = seccion1Completa && seccion2Completa

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (bloqueadoPorMora) {
      toast.error('No puede continuar: el cliente tiene cuotas en mora.')
      setShowSection('situacion')
      return
    }
    
    const correo = user?.email || 'usuario@dominio'
    const confirmacion = window.confirm(
      '⚠️ CONFIRMACIÓN IMPORTANTE\n\n' +
      `Yo (correo: ${correo}) declaro que he revisado los documentos y que los mismos respaldan:\n` +
      '✓ Los ingresos coinciden con documentos\n' +
      '✓ Los gastos son verificables\n' +
      '✓ La información de empleo es correcta\n' +
      '✓ Los valores de anticipo son reales\n\n' +
      '¿Desea proceder con la evaluación?'
    )
    
    if (!confirmacion) {
      toast('Evaluación cancelada')
      return
    }
    
    setIsLoading(true)

    try {
      const datosEvaluacion = {
        // Criterio 1
        ingresos_mensuales: formData.ingresos_mensuales,
        gastos_fijos_mensuales: formData.gastos_fijos_mensuales,
        otras_deudas: formData.otras_deudas,
        
        // Criterio 2
        meses_trabajo: formData.meses_trabajo,
        tipo_empleo: formData.tipo_empleo,
        sector_economico: formData.sector_economico,
        
    // Criterio 3: Referencias individuales
    referencia1_observaciones: formData.referencia1_observaciones,
    referencia1_calificacion: formData.referencia1_calificacion,
    referencia2_observaciones: formData.referencia2_observaciones,
    referencia2_calificacion: formData.referencia2_calificacion,
    referencia3_observaciones: formData.referencia3_observaciones,
    referencia3_calificacion: formData.referencia3_calificacion,
        
        // Criterio 4 (sin tipo_vivienda)
        familia_cercana: formData.familia_cercana,
        familia_pais: formData.familia_pais,
        minutos_trabajo: formData.minutos_trabajo,
        
        // Criterio 5
        tipo_vivienda_detallado: formData.tipo_vivienda_detallado,
        zona_urbana: formData.zona_urbana,
        servicios_nombre: formData.servicios_nombre,
        zona_rural: formData.zona_rural,
        personas_casa: formData.personas_casa,
        estado_civil: formData.estado_civil,
        pareja_trabaja: formData.pareja_trabaja,
        pareja_aval: formData.pareja_aval,
        pareja_desempleada: formData.pareja_desempleada,
        relacion_conflictiva: formData.relacion_conflictiva,
        situacion_hijos: formData.situacion_hijos,
        todos_estudian: formData.todos_estudian,
        viven_con_cliente: formData.viven_con_cliente,
        necesidades_especiales: formData.necesidades_especiales,
        viven_con_ex: formData.viven_con_ex,
        embarazo_actual: formData.embarazo_actual,
        
        // Criterio 6: Edad calculada automáticamente
        edad: clienteEdad || 0,
        
        // Criterio 7: Capacidad de Maniobra
        // Se calcula automáticamente con los datos del Criterio 1
      }

      const response = await prestamoService.evaluarRiesgo(prestamo.id, datosEvaluacion)
      setResultado(response)
      // Cambiar automáticamente a la pestaña de resultado
      setTimeout(() => setShowSection('resultado'), 100)
      toast.success('✅ Fase 1 Completada: Evaluación de Riesgo guardada. El préstamo ahora está en estado EVALUADO.')
      
      // IMPORTANTE: onSuccess actualiza el dashboard y cambia el icono de calculadora a aprobación
      // Esperar 2 segundos para que el usuario vea el resultado antes de cerrar
      setTimeout(() => {
        onSuccess() // Esto actualizará el dashboard y cambiará el icono
        onClose() // Cierra el formulario
        toast.info('🔄 Ahora puede usar el nuevo icono en el dashboard para proceder con la Aprobación (Fase 2)')
      }, 2000)
    } catch (error: any) {
      toast.error(error.message || 'Error al evaluar riesgo')
    } finally {
      setIsLoading(false)
    }
  }

  const secciones = [
    { id: 'situacion', label: 'Situación del Cliente', puntos: '' },
    { id: 'criterio1', label: 'Criterio 1: Capacidad de Pago', puntos: '29' },
    { id: 'criterio2', label: 'Criterio 2: Estabilidad Laboral', puntos: '23' },
    { id: 'criterio3', label: 'Criterio 3: Referencias', puntos: '9' },
    { id: 'criterio4', label: 'Criterio 4: Arraigo Geográfico', puntos: '7' },
    { id: 'criterio5', label: 'Criterio 5: Perfil Sociodemográfico', puntos: '17' },
    { id: 'criterio6', label: 'Criterio 6: Edad', puntos: '10' },
    { id: 'criterio7', label: 'Criterio 7: Capacidad de Maniobra', puntos: '5' },
    ...(resultado ? [{ id: 'resultado', label: 'Resultado de Evaluación', puntos: '' }] : []),
  ]

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.95, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95 }}
        className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[95vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-gradient-to-r from-blue-600 to-purple-600 text-white p-4 flex justify-between items-center z-10">
          <div className="flex items-center gap-3">
            <Calculator className="h-6 w-6" />
            <div>
              <h2 className="text-xl font-bold">Evaluación de Riesgo</h2>
              <p className="text-sm opacity-90">Préstamo #{prestamo.id} - Sistema 100 Puntos</p>
          </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} className="text-white hover:bg-white/20">
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Navegación por Secciones */}
        <div className="bg-gray-50 px-4 py-2 border-b overflow-x-auto">
          <div className="flex gap-2">
            {secciones.map((seccion) => (
              <button
                key={seccion.id}
                onClick={() => setShowSection(seccion.id)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                  showSection === seccion.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-100'
                }`}
              >
                {seccion.label.split(':')[0]} {seccion.puntos ? `(${seccion.puntos} pts)` : ''}
              </button>
            ))}
          </div>
          {/* Aviso de pendientes */}
          {!todasSeccionesCompletas && (
            <div className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2 rounded">
              Debe completar los campos obligatorios en: { !seccion1Completa ? 'Criterio 1' : '' }{ !seccion1Completa && !seccion2Completa ? ', ' : ''}{ !seccion2Completa ? 'Criterio 2' : '' }.
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto max-h-[60vh]">
          {/* SITUACIÓN DEL CLIENTE (Resumen de préstamos) */}
          {showSection === 'situacion' && (
            <Card className="border-purple-200">
              <CardHeader className="bg-purple-50">
                <CardTitle className="flex items-center gap-2 text-purple-700">
                  <Info className="h-5 w-5" />
                  Situación del Cliente
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-3">
                {!resumenPrestamos && <p>Cargando resumen...</p>}
                {resumenPrestamos && !resumenPrestamos.tiene_prestamos && (
                  <div className="p-3 rounded bg-green-50 border border-green-200 text-green-800">
                    No tiene préstamos vigentes. Puede continuar con el análisis.
                  </div>
                )}
                {resumenPrestamos && resumenPrestamos.tiene_prestamos && (
                  <div className="space-y-3">
                    <div className="p-3 rounded bg-yellow-50 border border-yellow-200 text-yellow-900">
                      Préstamos vigentes: {resumenPrestamos.total_prestamos}. Saldo pendiente total: ${Number(resumenPrestamos.total_saldo_pendiente || 0).toFixed(2)}.
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left border-b">
                            <th className="py-2 pr-4">ID</th>
                            <th className="py-2 pr-4">Modelo</th>
                            <th className="py-2 pr-4">Financiamiento</th>
                            <th className="py-2 pr-4">Saldo</th>
                            <th className="py-2 pr-4">Cuotas en Mora</th>
                            <th className="py-2 pr-4">Estado</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(resumenPrestamos.prestamos || []).map((p:any) => (
                            <tr key={p.id} className="border-b">
                              <td className="py-2 pr-4">{p.id}</td>
                              <td className="py-2 pr-4">{p.modelo_vehiculo}</td>
                              <td className="py-2 pr-4">${Number(p.total_financiamiento).toFixed(2)}</td>
                              <td className="py-2 pr-4">${Number(p.saldo_pendiente).toFixed(2)}</td>
                              <td className="py-2 pr-4">{p.cuotas_en_mora}</td>
                              <td className="py-2 pr-4">{p.estado}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {bloqueadoPorMora ? (
                      <div className="p-3 rounded bg-red-50 border border-red-200 text-red-800">
                        Hay cuotas en mora. No se puede continuar hasta regularizar la situación.
                      </div>
                    ) : (
                      <div className="p-3 rounded bg-blue-50 border border-blue-200 text-blue-800">
                        No hay cuotas en mora. Puede continuar con el análisis.
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
          {/* CRITERIO 1: CAPACIDAD DE PAGO (33 puntos) */}
          {showSection === 'criterio1' && (
          <Card className="border-blue-200">
            <CardHeader className="bg-blue-50">
                <CardTitle className="flex items-center gap-2 text-blue-700">
                  <TrendingDown className="h-5 w-5" />
                  CRITERIO 1: CAPACIDAD DE PAGO (29 puntos)
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Ingresos Mensuales (USD) *
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.ingresos_mensuales || ''}
                      onChange={(e) => setFormData({ ...formData, ingresos_mensuales: parseFloat(e.target.value) || 0 })}
                      required
                    />
                  <Popover>
                    <PopoverTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-6 mt-1 p-0 text-xs text-blue-600">
                          <Info className="h-3 w-3 mr-1" />
                          Ver escala
                      </Button>
                    </PopoverTrigger>
                      <PopoverContent className="w-80">
                        <p className="text-sm font-semibold mb-2">Ratio de Endeudamiento:</p>
                        <ul className="text-xs space-y-1">
                          <li>• &lt; 25% → 14 puntos (Excelente)</li>
                          <li>• 25-35% → 11 puntos (Bueno)</li>
                          <li>• 35-50% → 6 puntos (Regular)</li>
                          <li>• &gt; 50% → 2 puntos (Malo)</li>
                          </ul>
                        <p className="text-sm font-semibold mb-2 mt-4">Ratio de Cobertura:</p>
                        <ul className="text-xs space-y-1">
                          <li>• &gt; 2.5x → 15 puntos (Excelente)</li>
                          <li>• 2.0-2.5x → 12 puntos (Bueno)</li>
                          <li>• 1.5-2.0x → 6 puntos (Regular)</li>
                          <li>• &lt; 1.5x → 0 puntos (RECHAZO)</li>
                        </ul>
                    </PopoverContent>
                  </Popover>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                      Gastos Fijos (USD) *
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                      value={formData.gastos_fijos_mensuales || ''}
                      onChange={(e) => setFormData({ ...formData, gastos_fijos_mensuales: parseFloat(e.target.value) || 0 })}
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                      Otras Deudas (USD) *
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                      value={formData.otras_deudas || ''}
                      onChange={(e) => setFormData({ ...formData, otras_deudas: parseFloat(e.target.value) || 0 })}
                    required
                  />
                    <p className="text-xs text-gray-500 mt-1">Sin incluir la cuota actual</p>
                </div>
              </div>
                <div className="bg-blue-50 p-3 rounded border border-blue-200">
                  <p className="text-xs text-blue-700">
                    <strong>Nota:</strong> La cuota del préstamo se toma automáticamente de la base de datos: ${prestamo.cuota_periodo || 0} USD
                  </p>
              </div>
            </CardContent>
          </Card>
          )}

          {/* CRITERIO 2: ESTABILIDAD LABORAL (23 puntos) */}
          {showSection === 'criterio2' && (
            <Card className="border-yellow-200">
              <CardHeader className="bg-yellow-50">
                <CardTitle className="flex items-center gap-2 text-yellow-700">
                  <AlertCircle className="h-5 w-5" />
                  CRITERIO 2: ESTABILIDAD LABORAL (23 puntos)
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Meses de Trabajo *
                  </label>
                  <Input
                    type="number"
                    min="0"
                    value={formData.meses_trabajo || ''}
                    onChange={(e) => setFormData({ ...formData, meses_trabajo: parseInt(e.target.value) || 0 })}
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Escala: &gt; 24 meses → 9 pts, 12-24 → 7 pts, 6-12 → 4 pts, &lt; 6 → 0 pts
                  </p>
                        </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Tipo de Empleo *
                  </label>
                  <Select
                    value={formData.tipo_empleo}
                    onValueChange={(value) => setFormData({ ...formData, tipo_empleo: value })}
                    required
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="empleado_formal">Empleado Formal (8 pts)</SelectItem>
                      <SelectItem value="informal_estable">Informal Estable (&gt;1 año) (6 pts)</SelectItem>
                      <SelectItem value="independiente_formal">Independiente Formal (RIF/NIT) (5 pts)</SelectItem>
                      <SelectItem value="independiente_informal">Independiente Informal (3 pts)</SelectItem>
                      <SelectItem value="sin_empleo">Sin Empleo Fijo (0 pts)</SelectItem>
                    </SelectContent>
                  </Select>
                      </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Sector Económico *
                  </label>
                  <Select
                    value={formData.sector_economico}
                    onValueChange={(value) => setFormData({ ...formData, sector_economico: value })}
                    required
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="gobierno_publico">Gobierno/Público (6 pts)</SelectItem>
                      <SelectItem value="servicios_esenciales">Servicios Esenciales (5 pts)</SelectItem>
                      <SelectItem value="comercio_establecido">Comercio Establecido (4 pts)</SelectItem>
                      <SelectItem value="construccion_manufactura">Construcción/Manufactura (3 pts)</SelectItem>
                      <SelectItem value="turismo_entretenimiento">Turismo/Entretenimiento (2 pts)</SelectItem>
                      <SelectItem value="servicios_temporales">Servicios Temporales (1 pt)</SelectItem>
                      <SelectItem value="agricultura_estacional">Agricultura Estacional (0 pts)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
            </CardContent>
          </Card>
          )}

          {/* CRITERIO 3: REFERENCIAS (5 puntos) */}
          {showSection === 'criterio3' && (
          <Card className="border-purple-200">
            <CardHeader className="bg-purple-50">
                <CardTitle className="flex items-center gap-2 text-purple-700">
                  <CheckCircle className="h-5 w-5" />
                  CRITERIO 3: REFERENCIAS PERSONALES (9 puntos)
              </CardTitle>
            </CardHeader>
              <CardContent className="pt-4 space-y-4">
                {/* Referencia 1 */}
                <div className="border rounded-lg p-4 bg-purple-50">
                  <h4 className="font-medium text-sm mb-3">Referencia 1</h4>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Observaciones
                      </label>
                      <Input
                        type="text"
                        placeholder="Nombre, relación, etc."
                        value={formData.referencia1_observaciones || ''}
                        onChange={(e) => setFormData({ ...formData, referencia1_observaciones: e.target.value })}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Calificación *
                      </label>
              <Select
                        value={formData.referencia1_calificacion.toString()}
                        onValueChange={(value) => setFormData({ ...formData, referencia1_calificacion: parseInt(value) })}
              >
                <SelectTrigger>
                          <SelectValue placeholder="Seleccionar" />
                </SelectTrigger>
                <SelectContent>
                          <SelectItem value="3">3 - Recomendable</SelectItem>
                          <SelectItem value="2">2 - Dudosa</SelectItem>
                          <SelectItem value="1">1 - No recomendable</SelectItem>
                          <SelectItem value="0">0 - No contestó</SelectItem>
                </SelectContent>
              </Select>
                    </div>
                  </div>
                </div>

                {/* Referencia 2 */}
                <div className="border rounded-lg p-4 bg-purple-50">
                  <h4 className="font-medium text-sm mb-3">Referencia 2</h4>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Observaciones
                      </label>
                      <Input
                        type="text"
                        placeholder="Nombre, relación, etc."
                        value={formData.referencia2_observaciones || ''}
                        onChange={(e) => setFormData({ ...formData, referencia2_observaciones: e.target.value })}
                      />
                      </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Calificación *
                      </label>
                      <Select
                        value={formData.referencia2_calificacion.toString()}
                        onValueChange={(value) => setFormData({ ...formData, referencia2_calificacion: parseInt(value) })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Seleccionar" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="3">3 - Recomendable</SelectItem>
                          <SelectItem value="2">2 - Dudosa</SelectItem>
                          <SelectItem value="1">1 - No recomendable</SelectItem>
                          <SelectItem value="0">0 - No contestó</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                {/* Referencia 3 */}
                <div className="border rounded-lg p-4 bg-purple-50">
                  <h4 className="font-medium text-sm mb-3">Referencia 3</h4>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Observaciones
                      </label>
                      <Input
                        type="text"
                        placeholder="Nombre, relación, etc."
                        value={formData.referencia3_observaciones || ''}
                        onChange={(e) => setFormData({ ...formData, referencia3_observaciones: e.target.value })}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Calificación *
                      </label>
                      <Select
                        value={formData.referencia3_calificacion.toString()}
                        onValueChange={(value) => setFormData({ ...formData, referencia3_calificacion: parseInt(value) })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Seleccionar" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="3">3 - Recomendable</SelectItem>
                          <SelectItem value="2">2 - Dudosa</SelectItem>
                          <SelectItem value="1">1 - No recomendable</SelectItem>
                          <SelectItem value="0">0 - No contestó</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                <div className="bg-purple-50 p-3 rounded border border-purple-200">
                  <p className="text-xs text-purple-700">
                    <strong>Escala:</strong> Calificación 3 → Recomendable (3 pts) | Calificación 2 → Dudosa (2 pts) | Calificación 1 → No recomendable (1 pt) | No contestó (0 pts)
                    <br />
                    <strong>Total máximo:</strong> 9 puntos (3 referencias × 3 pts c/u)
                  </p>
                </div>
            </CardContent>
          </Card>
          )}

          {/* CRITERIO 4: ARRAIGO GEOGRÁFICO (7 puntos) */}
          {showSection === 'criterio4' && (
            <Card className="border-green-200">
              <CardHeader className="bg-green-50">
                <CardTitle className="flex items-center gap-2 text-green-700">
                  <MapPin className="h-5 w-5" />
                  CRITERIO 4: ARRAIGO GEOGRÁFICO (7 puntos)
              </CardTitle>
            </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Distancia al Trabajo (minutos) *
                  </label>
              <Input
                type="number"
                min="0"
                    value={formData.minutos_trabajo || ''}
                    onChange={(e) => setFormData({ ...formData, minutos_trabajo: parseInt(e.target.value) || 0 })}
                required
              />
                  <p className="text-xs text-gray-500 mt-1">&lt; 30 min → 3 pts, 30-60 min → 2 pts, &gt; 60 min → 0 pts</p>
                </div>
                    <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="familia_cercana"
                      checked={formData.familia_cercana}
                      onChange={(e) => setFormData({ ...formData, familia_cercana: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="familia_cercana" className="text-sm cursor-pointer">
                      Familia cercana en la ciudad (4 pts)
                    </label>
                      </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="familia_pais"
                      checked={formData.familia_pais}
                      onChange={(e) => setFormData({ ...formData, familia_pais: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="familia_pais" className="text-sm cursor-pointer">
                      Familia en el país (2 pts)
                    </label>
                    </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* CRITERIO 5: PERFIL SOCIODEMOGRÁFICO (17 puntos) */}
          {showSection === 'criterio5' && (
            <Card className="border-indigo-200">
              <CardHeader className="bg-indigo-50">
                <CardTitle className="flex items-center gap-2 text-indigo-700">
                  <Users className="h-5 w-5" />
                  CRITERIO 5: PERFIL SOCIODEMOGRÁFICO (17 puntos)
              </CardTitle>
            </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Situación de Vivienda Detallada *
                  </label>
              <Select
                    value={formData.tipo_vivienda_detallado}
                    onValueChange={(value) => setFormData({ ...formData, tipo_vivienda_detallado: value })}
                required
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                      <SelectItem value="casa_propia_pagada">Casa Propia Pagada (6 pts)</SelectItem>
                      <SelectItem value="casa_propia_hipoteca">Casa Propia con Hipoteca (5 pts)</SelectItem>
                      <SelectItem value="casa_familiar">Casa Familiar/Heredada (5 pts)</SelectItem>
                      <SelectItem value="alquiler_mas_3">Alquiler &gt;3 años (4 pts)</SelectItem>
                      <SelectItem value="alquiler_1_3">Alquiler 1-3 años (3 pts)</SelectItem>
                      <SelectItem value="alquiler_menos_1">Alquiler &lt;1 año (1 pt)</SelectItem>
                      <SelectItem value="prestado">De Prestado (0.5 pts)</SelectItem>
                      <SelectItem value="sin_vivienda">Sin Vivienda (0 pts)</SelectItem>
                </SelectContent>
              </Select>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="zona_urbana"
                      checked={formData.zona_urbana}
                      onChange={(e) => setFormData({ ...formData, zona_urbana: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="zona_urbana" className="text-sm cursor-pointer">
                      Zona urbana consolidada (+0.5 pts)
                    </label>
                        </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="servicios_nombre"
                      checked={formData.servicios_nombre}
                      onChange={(e) => setFormData({ ...formData, servicios_nombre: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="servicios_nombre" className="text-sm cursor-pointer">
                      Servicios a su nombre (+0.5 pts)
                    </label>
                      </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="zona_rural"
                      checked={formData.zona_rural}
                      onChange={(e) => setFormData({ ...formData, zona_rural: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="zona_rural" className="text-sm cursor-pointer">
                      Zona rural/alejada (-0.5 pts)
                    </label>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                      Personas en Casa
                  </label>
                  <Input
                    type="number"
                      min="1"
                      value={formData.personas_casa || 1}
                      onChange={(e) => setFormData({ ...formData, personas_casa: parseInt(e.target.value) || 1 })}
                    />
                    <p className="text-xs text-gray-500 mt-1">&gt; 5 personas → -0.5 pts</p>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    Estado Civil *
                  </label>
                  <Select
                    value={formData.estado_civil}
                    onValueChange={(value) => setFormData({ ...formData, estado_civil: value })}
                    required
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="casado_mas_3">Casado/a &gt;3 años (3.5 pts)</SelectItem>
                      <SelectItem value="casado_menos_3">Casado/a &lt;3 años (3.0 pts)</SelectItem>
                      <SelectItem value="divorciado_con_hijos">Divorciado/a con hijos (2.5 pts)</SelectItem>
                      <SelectItem value="soltero_con_pareja">Soltero/a con pareja (2.0 pts)</SelectItem>
                      <SelectItem value="soltero_sin_pareja">Soltero/a sin pareja (1.5 pts)</SelectItem>
                      <SelectItem value="divorciado_sin_hijos">Divorciado/a sin hijos (1.0 pt)</SelectItem>
                      <SelectItem value="separado_reciente">Separado/a reciente (0 pts)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                    <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="pareja_trabaja"
                      checked={formData.pareja_trabaja}
                      onChange={(e) => setFormData({ ...formData, pareja_trabaja: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="pareja_trabaja" className="text-sm cursor-pointer">
                      Pareja trabaja (+1.0 pt)
                    </label>
                </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="pareja_aval"
                      checked={formData.pareja_aval}
                      onChange={(e) => setFormData({ ...formData, pareja_aval: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="pareja_aval" className="text-sm cursor-pointer">
                      Pareja es aval (+1.5 pts)
                    </label>
                    </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="pareja_desempleada"
                      checked={formData.pareja_desempleada}
                      onChange={(e) => setFormData({ ...formData, pareja_desempleada: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="pareja_desempleada" className="text-sm cursor-pointer">
                      Pareja desempleada (-0.5 pts)
                    </label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="relacion_conflictiva"
                      checked={formData.relacion_conflictiva}
                      onChange={(e) => setFormData({ ...formData, relacion_conflictiva: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="relacion_conflictiva" className="text-sm cursor-pointer">
                      Relación conflictiva (-1.0 pt)
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    Situación de Hijos *
                  </label>
              <Select
                    value={formData.situacion_hijos}
                    onValueChange={(value) => setFormData({ ...formData, situacion_hijos: value })}
                required
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                      <SelectItem value="1_2_menores">1-2 hijos menores (0-12) (5.0 pts)</SelectItem>
                      <SelectItem value="1_2_mayores">1-2 hijos mayores (13+) (4.0 pts)</SelectItem>
                      <SelectItem value="3_4_mixtos">3-4 hijos mixtos (3.0 pts)</SelectItem>
                      <SelectItem value="sin_hijos_planea">Sin hijos, planea (2.5 pts)</SelectItem>
                      <SelectItem value="5_mas">5+ hijos (1.5 pts)</SelectItem>
                      <SelectItem value="sin_hijos_no_planea">Sin hijos, no planea (2.0 pts)</SelectItem>
                      <SelectItem value="hijos_independientes">Hijos independientes (1.0 pt)</SelectItem>
                </SelectContent>
              </Select>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="todos_estudian"
                      checked={formData.todos_estudian}
                      onChange={(e) => setFormData({ ...formData, todos_estudian: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="todos_estudian" className="text-sm cursor-pointer">
                      Todos estudian (+0.5 pts)
                    </label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="viven_con_cliente"
                      checked={formData.viven_con_cliente}
                      onChange={(e) => setFormData({ ...formData, viven_con_cliente: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="viven_con_cliente" className="text-sm cursor-pointer">
                      Viven con cliente (+0.5 pts)
                    </label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="necesidades_especiales"
                      checked={formData.necesidades_especiales}
                      onChange={(e) => setFormData({ ...formData, necesidades_especiales: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="necesidades_especiales" className="text-sm cursor-pointer">
                      Necesidades especiales (-1.0 pt)
                    </label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="viven_con_ex"
                      checked={formData.viven_con_ex}
                      onChange={(e) => setFormData({ ...formData, viven_con_ex: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="viven_con_ex" className="text-sm cursor-pointer">
                      Viven con ex (-0.5 pts)
                    </label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="embarazo_actual"
                      checked={formData.embarazo_actual}
                      onChange={(e) => setFormData({ ...formData, embarazo_actual: e.target.checked })}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="embarazo_actual" className="text-sm cursor-pointer">
                      Embarazo actual (-0.5 pts)
                    </label>
                  </div>
                </div>
            </CardContent>
          </Card>
          )}

          {/* CRITERIO 6: EDAD (10 puntos) */}
          {showSection === 'criterio6' && (
            <Card className="border-pink-200">
              <CardHeader className="bg-pink-50">
                <CardTitle className="flex items-center gap-2 text-pink-700">
                  <Calendar className="h-5 w-5" />
                  CRITERIO 6: EDAD DEL CLIENTE (10 puntos)
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Edad del Cliente (años y meses) *
                  </label>
                  <Input
                    type="text"
                    value={(() => {
                      const edad = clienteEdad || 0;
                      // Calcula años y meses desde la edad en años (decimal)
                      const años = Math.floor(edad);
                      const meses = Math.round((edad - años) * 12);
                      // Si los meses son negativos (error de cálculo), ajustar
                      const meses_final = meses < 0 ? 0 : meses;
                      return meses_final > 0 ? `${años} años y ${meses_final} meses` : `${años} años`;
                    })()}
                    disabled={true}
                    required
                    className="bg-gray-100 cursor-not-allowed font-semibold text-gray-700"
                    readOnly
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    ℹ️ La edad se calcula automáticamente desde la fecha de nacimiento del cliente en la base de datos (no editable)
                  </p>
                  <div className="bg-pink-50 p-3 rounded border border-pink-200 mt-3">
                    <p className="text-xs text-pink-700">
                      <strong>Escala (10 puntos máx):</strong><br />
                      25-50 años → 10.0 pts (Óptimo) |<br />
                      22-24 / 51-55 años → 8.0 pts (Muy bueno/Bueno) |<br />
                      18-21 / 56-60 años → 6.0 pts (Regular) |<br />
                      61-65 años → 3.0 pts (Bajo) |<br />
                      &lt; 18 años → RECHAZO AUTOMÁTICO |<br />
                      &gt; 65 años → 2.0 pts (Muy bajo)
                    </p>
                </div>
              </div>
            </CardContent>
          </Card>
          )}

          {/* CRITERIO 7: CAPACIDAD DE MANIOBRA (5 puntos) */}
          {showSection === 'criterio7' && (
            <Card className="border-red-200">
              <CardHeader className="bg-red-50">
              <CardTitle className="flex items-center gap-2 text-red-700">
                  <DollarSign className="h-5 w-5" />
                  CRITERIO 7: CAPACIDAD DE MANIOBRA (5 puntos)
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                <h4 className="font-semibold text-blue-900 mb-2">📊 ¿Qué es la Capacidad de Maniobra?</h4>
                <p className="text-sm text-blue-800 mb-3">
                  Es el saldo que le queda al cliente después de pagar todos sus gastos, deudas y la cuota del préstamo propuesto.
                </p>
                <div className="bg-white p-3 rounded border border-blue-100">
                  <p className="text-xs font-mono text-gray-700">
                    <strong>Fórmula:</strong><br />
                    Saldo Residual = Ingresos - Gastos Fijos - Otras Deudas - Cuota Nueva
                  </p>
                </div>
              </div>
              
              {/* PREVISUALIZACIÓN EN TIEMPO REAL */}
              {(() => {
                const ingresos = formData.ingresos_mensuales || 0
                const gastosFijos = formData.gastos_fijos_mensuales || 0
                const otrasDeudas = formData.otras_deudas || 0
                const cuotaNueva = prestamo.cuota_periodo || 0
                const saldoResidual = ingresos - gastosFijos - otrasDeudas - cuotaNueva
                const porcentaje = ingresos > 0 ? (saldoResidual / ingresos) * 100 : 0
                
                let puntos = 0
                let categoria = ''
                let icono = ''
                
                if (porcentaje >= 15) {
                  puntos = 5
                  categoria = 'Holgado'
                  icono = '✅'
                } else if (porcentaje >= 5) {
                  puntos = 3
                  categoria = 'Ajustado'
                  icono = '⚠️'
                } else {
                  puntos = 0
                  categoria = 'Insuficiente'
                  icono = '❌'
                }
                
                return (
                  <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                    <h4 className="font-semibold text-green-900 mb-3">📊 PREVISUALIZACIÓN - CÁLCULO EN TIEMPO REAL</h4>
                    
                    {/* Desglose del cálculo */}
                    <div className="bg-white p-3 rounded border border-green-100 mb-3">
                      <div className="grid grid-cols-2 gap-2 text-sm mb-2">
                        <div className="text-gray-600">💰 Ingresos Mensuales:</div>
                        <div className="font-semibold">${ingresos.toFixed(2)}</div>
                        
                        <div className="text-gray-600">- Gastos Fijos:</div>
                        <div className="font-semibold">-${gastosFijos.toFixed(2)}</div>
                        
                        <div className="text-gray-600">- Otras Deudas:</div>
                        <div className="font-semibold">-${otrasDeudas.toFixed(2)}</div>
                        
                        <div className="text-gray-600">- Cuota Préstamo:</div>
                        <div className="font-semibold">-${cuotaNueva.toFixed(2)}</div>
                        
                        <div className="border-t pt-2 font-bold text-green-700">
                          💵 Saldo Residual:
                        </div>
                        <div className="border-t pt-2 font-bold text-green-700">
                          ${saldoResidual.toFixed(2)}
                        </div>
                      </div>
                    </div>
                    
                    {/* Porcentaje y categoría */}
                    <div className="grid grid-cols-2 gap-3 mb-3">
                      <div className="bg-white p-3 rounded border">
                        <div className="text-xs text-gray-600">% del Ingreso</div>
                        <div className="text-2xl font-bold text-blue-600">
                          {porcentaje.toFixed(2)}%
                        </div>
                      </div>
                      <div className="bg-white p-3 rounded border">
                        <div className="text-xs text-gray-600">Categoría</div>
                        <div className="text-lg font-bold text-green-600">
                          {icono} {categoria}
                        </div>
                      </div>
                    </div>
                    
                    {/* Puntos */}
                    <div className="bg-white p-3 rounded border text-center">
                      <div className="text-xs text-gray-600 mb-1">PUNTOS QUE OBTENDRÍA:</div>
                      <div className="text-3xl font-bold text-purple-600">
                        {puntos} / 5 pts
                      </div>
                    </div>
                    
                    {saldoResidual < 0 && (
                      <div className="bg-red-100 p-2 rounded border border-red-300 mt-3">
                        <p className="text-xs text-red-800 font-semibold">
                          ⚠️ ALERTA: El cliente tendría un déficit de ${Math.abs(saldoResidual).toFixed(2)} USD mensual
                        </p>
                      </div>
                    )}
                  </div>
                )
              })()}
              
              <div className="bg-amber-50 p-3 rounded border border-amber-200">
                <p className="text-xs text-amber-800 font-semibold mb-2">⚡ ESTE CRITERIO SE CALCULA AUTOMÁTICAMENTE</p>
                <p className="text-xs text-amber-700">
                  La previsualización arriba usa los datos que ingresaste. Cuando hagas click en "Evaluar Riesgo", el sistema calculará la capacidad de maniobra usando estos valores.
                </p>
              </div>

              <div className="bg-red-50 p-3 rounded border border-red-200">
                <p className="text-xs text-red-700">
                  <strong>Escala de Puntuación (3 bandas):</strong><br />
                  ✅ ≥15% del ingreso → 5 pts (Holgado) - Margen suficiente para imprevistos<br />
                  ⚠️ 5%-14.9% del ingreso → 3 pts (Ajustado) - Margen mínimo<br />
                  ❌ &lt;5% o déficit → 0 pts (Insuficiente) - Sin margen, alto riesgo
                </p>
              </div>
            </CardContent>
          </Card>
          )}

          {/* RESULTADO - Nueva Pestaña */}
          {showSection === 'resultado' && resultado && (
            <Card className="border-green-300 bg-green-50">
                <CardHeader>
                <CardTitle className="text-green-700">Resultado de la Evaluación</CardTitle>
                </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">Puntuación Total</label>
                    <p className="text-3xl font-bold text-green-700">
                      {resultado.puntuacion_total?.toFixed(2) || '0'} / 100
                    </p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Clasificación de Riesgo</label>
                    <Badge className="text-lg" variant={resultado.clasificacion_riesgo === 'A' ? 'default' : resultado.clasificacion_riesgo === 'B' ? 'default' : 'outline'}>
                        {resultado.clasificacion_riesgo}
                      </Badge>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Decisión Final</label>
                    <Badge variant={resultado.decision_final?.includes('RECHAZADO') ? 'destructive' : 'default'} className="text-lg">
                        {resultado.decision_final}
                      </Badge>
                    </div>
                    </div>
                
                {/* Mostrar y editar condiciones de aprobación */}
                {resultado.sugerencias && (
                  <div className="bg-blue-50 p-4 rounded border border-blue-200">
                    <div className="flex justify-between items-center mb-3">
                      <h5 className="font-semibold text-blue-900">📋 Condiciones para Aprobación:</h5>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setShowFormularioAprobacion(!showFormularioAprobacion)}
                      >
                        {showFormularioAprobacion ? 'Ocultar Edición' : 'Editar Condiciones'}
                      </Button>
                    </div>
                    
                    {!showFormularioAprobacion ? (
                      // Vista de solo lectura
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <label className="text-xs text-blue-700">Tasa de Interés Sugerida:</label>
                          <p className="text-lg font-bold text-blue-900">{resultado.sugerencias.tasa_interes_sugerida || 8.0}%</p>
                        </div>
                        <div>
                          <label className="text-xs text-blue-700">Plazo Máximo Sugerido:</label>
                          <p className="text-lg font-bold text-blue-900">{resultado.sugerencias.plazo_maximo_sugerido || 36} meses</p>
                        </div>
                        <div>
                          <label className="text-xs text-blue-700">Enganche Mínimo:</label>
                          <p className="text-lg font-bold text-blue-900">{resultado.sugerencias.enganche_minimo_sugerido || 15.0}%</p>
                        </div>
                      </div>
                    ) : (
                      // Formulario editable
                      <div className="bg-white p-4 rounded border border-blue-300 space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-700">
                              Tasa de Interés (%) <span className="text-red-500">*</span>
                            </label>
                            <div className="relative">
                              <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                              <Input
                                type="number"
                                step="0.1"
                                min="0"
                                max="100"
                                value={condicionesAprobacion.tasa_interes}
                                onChange={(e) => setCondicionesAprobacion({
                                  ...condicionesAprobacion,
                                  tasa_interes: parseFloat(e.target.value) || 0
                                })}
                                className="pl-10"
                                placeholder={resultado.sugerencias.tasa_interes_sugerida?.toString() || '8.0'}
                              />
                            </div>
                            <p className="text-xs text-gray-500">
                              Sugerido: {resultado.sugerencias.tasa_interes_sugerida || 8.0}%
                            </p>
                          </div>
                          
                          <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-700">
                              Plazo Máximo (meses) <span className="text-red-500">*</span>
                            </label>
                            <Input
                              type="number"
                              step="1"
                              min="1"
                              value={condicionesAprobacion.plazo_maximo}
                              onChange={(e) => setCondicionesAprobacion({
                                ...condicionesAprobacion,
                                plazo_maximo: parseInt(e.target.value) || 36
                              })}
                              placeholder={resultado.sugerencias.plazo_maximo_sugerido?.toString() || '36'}
                            />
                            <p className="text-xs text-gray-500">
                              Sugerido: {resultado.sugerencias.plazo_maximo_sugerido || 36} meses
                            </p>
                          </div>
                          
                          <div className="space-y-2">
                            <label className="text-sm font-medium text-gray-700">
                              Fecha de Desembolso <span className="text-red-500">*</span>
                            </label>
                            <div className="relative">
                              <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                              <Input
                                type="date"
                                value={condicionesAprobacion.fecha_base_calculo}
                                onChange={(e) => setCondicionesAprobacion({
                                  ...condicionesAprobacion,
                                  fecha_base_calculo: e.target.value
                                })}
                                className="pl-10"
                                min={new Date().toISOString().split('T')[0]}
                              />
                            </div>
                            <p className="text-xs text-gray-500">
                              Fecha desde la cual se calcularán las cuotas
                            </p>
                          </div>
                        </div>
                        
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-gray-700">
                            Observaciones
                          </label>
                          <textarea
                            value={condicionesAprobacion.observaciones}
                            onChange={(e) => setCondicionesAprobacion({
                              ...condicionesAprobacion,
                              observaciones: e.target.value
                            })}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            rows={3}
                            placeholder="Aprobado después de evaluación de riesgo..."
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                {resultado.requisitos_adicionales && (
                  <div className="bg-white p-3 rounded border">
                    <p className="text-sm font-medium mb-2">Requisitos Adicionales:</p>
                    <p className="text-sm">{resultado.requisitos_adicionales}</p>
                    </div>
                )}

                {/* Predicción ML */}
                {resultado.prediccion_ml && (
                  <Card className="border-purple-200 bg-purple-50/50">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-purple-700">
                        <Brain className="h-5 w-5" />
                        Predicción de Machine Learning
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="text-sm text-gray-600 mb-1">Nivel de Riesgo ML</div>
                          <Badge 
                            className={`text-lg ${
                              resultado.prediccion_ml.riesgo_level === 'Bajo' 
                                ? 'bg-green-600 text-white' 
                                : resultado.prediccion_ml.riesgo_level === 'Medio'
                                ? 'bg-yellow-600 text-white'
                                : 'bg-red-600 text-white'
                            }`}
                          >
                            <Shield className="h-4 w-4 mr-1" />
                            {resultado.prediccion_ml.riesgo_level}
                          </Badge>
                        </div>
                        <div>
                          <div className="text-sm text-gray-600 mb-1">Confianza</div>
                          <div className="text-2xl font-bold text-purple-600">
                            {(resultado.prediccion_ml.confidence * 100).toFixed(1)}%
                          </div>
                        </div>
                      </div>
                      
                      {resultado.prediccion_ml.recommendation && (
                        <div className="bg-white p-3 rounded border border-purple-200">
                          <div className="text-sm font-medium text-gray-700 mb-1">Recomendación ML:</div>
                          <p className="text-sm text-gray-600">{resultado.prediccion_ml.recommendation}</p>
                        </div>
                      )}

                      {resultado.prediccion_ml.modelo_usado && (
                        <div className="bg-white p-3 rounded border border-purple-200">
                          <div className="text-xs text-gray-500 mb-2">Modelo utilizado:</div>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                              <span className="text-gray-600">Nombre:</span>{' '}
                              <span className="font-semibold">{resultado.prediccion_ml.modelo_usado.nombre}</span>
                            </div>
                            <div>
                              <span className="text-gray-600">Versión:</span>{' '}
                              <span className="font-semibold">v{resultado.prediccion_ml.modelo_usado.version}</span>
                            </div>
                            <div>
                              <span className="text-gray-600">Algoritmo:</span>{' '}
                              <span className="font-semibold">{resultado.prediccion_ml.modelo_usado.algoritmo}</span>
                            </div>
                            {resultado.prediccion_ml.modelo_usado.accuracy && (
                              <div>
                                <span className="text-gray-600">Accuracy:</span>{' '}
                                <span className="font-semibold">
                                  {(resultado.prediccion_ml.modelo_usado.accuracy * 100).toFixed(1)}%
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Comparación con evaluación tradicional */}
                      <div className="bg-blue-50 p-3 rounded border border-blue-200">
                        <div className="text-xs font-semibold text-blue-900 mb-2">📊 Comparación de Métodos:</div>
                        <div className="grid grid-cols-2 gap-3 text-sm">
                          <div>
                            <div className="text-gray-600">Sistema 100 Puntos:</div>
                            <div className="font-semibold text-blue-700">
                              {resultado.clasificacion_riesgo} ({resultado.puntuacion_total?.toFixed(1)}/100)
                            </div>
                          </div>
                          <div>
                            <div className="text-gray-600">Machine Learning:</div>
                            <div className="font-semibold text-purple-700">
                              {resultado.prediccion_ml.riesgo_level} ({(resultado.prediccion_ml.confidence * 100).toFixed(1)}% confianza)
                            </div>
                          </div>
                        </div>
                        {resultado.clasificacion_riesgo === 'A' && resultado.prediccion_ml.riesgo_level === 'Bajo' && (
                          <div className="mt-2 text-xs text-green-700 bg-green-100 p-2 rounded">
                            ✅ Ambos métodos coinciden: Cliente de bajo riesgo
                          </div>
                        )}
                        {resultado.clasificacion_riesgo === 'E' && resultado.prediccion_ml.riesgo_level === 'Alto' && (
                          <div className="mt-2 text-xs text-red-700 bg-red-100 p-2 rounded">
                            ⚠️ Ambos métodos coinciden: Cliente de alto riesgo
                          </div>
                        )}
                        {((resultado.clasificacion_riesgo === 'A' || resultado.clasificacion_riesgo === 'B') && resultado.prediccion_ml.riesgo_level === 'Alto') && (
                          <div className="mt-2 text-xs text-amber-700 bg-amber-100 p-2 rounded">
                            ⚠️ Discrepancia detectada: El ML sugiere mayor riesgo que el sistema de puntos
                          </div>
                        )}
                        {((resultado.clasificacion_riesgo === 'D' || resultado.clasificacion_riesgo === 'E') && resultado.prediccion_ml.riesgo_level === 'Bajo') && (
                          <div className="mt-2 text-xs text-amber-700 bg-amber-100 p-2 rounded">
                            ⚠️ Discrepancia detectada: El ML sugiere menor riesgo que el sistema de puntos
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )}

                <div className="bg-white p-3 rounded border">
                  <h5 className="font-semibold mb-2">Detalle de Criterios:</h5>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    <li>
                      <strong>1. Capacidad de Pago:</strong>{' '}
                      {resultado.detalle_criterios?.ratio_endeudamiento?.puntos?.toFixed(1)} pts (Endeudamiento) +{' '}
                      {resultado.detalle_criterios?.ratio_cobertura?.puntos?.toFixed(1)} pts (Cobertura)
                      (Total: {(resultado.detalle_criterios?.ratio_endeudamiento?.puntos + resultado.detalle_criterios?.ratio_cobertura?.puntos).toFixed(1)}/29 pts)
                    </li>
                    <li>
                      <strong>2. Estabilidad Laboral:</strong>{' '}
                      {resultado.detalle_criterios?.antiguedad_trabajo?.puntos?.toFixed(1)} pts (Antigüedad) +{' '}
                      {resultado.detalle_criterios?.tipo_empleo?.puntos?.toFixed(1)} pts (Tipo Empleo) +{' '}
                      {resultado.detalle_criterios?.sector_economico?.puntos?.toFixed(1)} pts (Sector)
                      (Total: {(resultado.detalle_criterios?.antiguedad_trabajo?.puntos + resultado.detalle_criterios?.tipo_empleo?.puntos + resultado.detalle_criterios?.sector_economico?.puntos).toFixed(1)}/23 pts)
                    </li>
                    <li>
                      <strong>3. Referencias Personales:</strong>{' '}
                      {resultado.detalle_criterios?.referencias?.puntos?.toFixed(1)}/9 pts
                      (Ref1: {resultado.detalle_criterios?.referencias?.referencia1_calificacion}, Ref2: {resultado.detalle_criterios?.referencias?.referencia2_calificacion}, Ref3: {resultado.detalle_criterios?.referencias?.referencia3_calificacion})
                    </li>
                    <li>
                      <strong>4. Arraigo Geográfico:</strong>{' '}
                      {resultado.detalle_criterios?.arraigo_vivienda?.toFixed(1)} pts (Vivienda) +{' '}
                      {resultado.detalle_criterios?.arraigo_laboral?.toFixed(1)} pts (Laboral)
                      (Total: {(resultado.detalle_criterios?.arraigo_familiar + resultado.detalle_criterios?.arraigo_laboral).toFixed(1)}/7 pts)
                    </li>
                    <li>
                      <strong>5. Perfil Sociodemográfico:</strong>{' '}
                      {resultado.detalle_criterios?.vivienda?.puntos?.toFixed(1)} pts (Vivienda) +{' '}
                      {resultado.detalle_criterios?.estado_civil?.puntos?.toFixed(1)} pts (Estado Civil) +{' '}
                      {resultado.detalle_criterios?.hijos?.puntos?.toFixed(1)} pts (Hijos)
                      (Total: {(resultado.detalle_criterios?.vivienda?.puntos + resultado.detalle_criterios?.estado_civil?.puntos + resultado.detalle_criterios?.hijos?.puntos).toFixed(1)}/17 pts)
                    </li>
                    <li>
                      <strong>6. Edad del Cliente:</strong>{' '}
                      {resultado.detalle_criterios?.edad?.puntos?.toFixed(1)}/10 pts ({resultado.detalle_criterios?.edad?.cliente} años)
                    </li>
                    <li>
                      <strong>7. Capacidad de Maniobra:</strong>{' '}
                      {resultado.detalle_criterios?.capacidad_maniobra?.puntos?.toFixed(1)}/5 pts ({resultado.detalle_criterios?.capacidad_maniobra?.porcentaje_residual?.toFixed(2)}% residual)
                    </li>
                  </ul>
                  </div>
                </CardContent>
              </Card>
          )}

          {/* Botones */}
          {!resultado && (
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isLoading || !todasSeccionesCompletas || bloqueadoPorMora} title={!todasSeccionesCompletas ? 'Complete las secciones requeridas' : undefined}>
                <Calculator className="h-4 w-4 mr-2" />
                {isLoading ? 'Evaluando...' : 'Evaluar Riesgo'}
              </Button>
            </div>
          )}
          {resultado && (
            <div className="space-y-4 pt-4 border-t">
              {/* Mensaje informativo */}
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-4 rounded-lg border-2 border-blue-300">
                <div className="flex items-start gap-3">
                  <CheckCircle className="h-6 w-6 text-green-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h3 className="text-base font-bold text-blue-900 mb-2">
                      ✅ FASE 1 COMPLETADA: Evaluación de Riesgo
                    </h3>
                    <div className="space-y-2 text-sm text-blue-800">
                      <p>
                        • <strong>Estado actualizado:</strong> El préstamo ahora está marcado como <span className="font-bold text-blue-600">EVALUADO</span>
                      </p>
                      <p>
                        • <strong>Puntuación obtenida:</strong> {resultado.puntuacion_total?.toFixed(2) || 'N/A'}/100 puntos
                      </p>
                      <p>
                        • <strong>Clasificación de riesgo:</strong> <span className="font-semibold">{resultado.clasificacion_riesgo || 'N/A'}</span>
                      </p>
                      <div className="mt-3 pt-3 border-t border-blue-300">
                        <p className="font-semibold text-purple-700 mb-1">🔄 SIGUIENTE PASO: Fase 2 - Aprobación</p>
                        <p className="text-xs">
                          El icono de <strong>calculadora (Calculator)</strong> en el dashboard desaparecerá y será reemplazado 
                          por el icono de <strong>verde (CheckCircle2)</strong> para "Aprobar Crédito". 
                          Haga clic en ese nuevo icono para continuar con la asignación de:
                        </p>
                        <ul className="list-disc list-inside mt-2 space-y-1 text-xs text-blue-700">
                          <li>Tasa de interés</li>
                          <li>Fecha de desembolso</li>
                          <li>Plazo máximo</li>
                          <li>Observaciones</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Botones de acción */}
              <div className="flex justify-end gap-3">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => {
                    onSuccess() // Actualizar dashboard
                    onClose() // Cerrar formulario
                  }}
                >
                  Continuar al Dashboard
                </Button>
              </div>
            </div>
          )}
        </form>
      </motion.div>
    </motion.div>
  )
}

