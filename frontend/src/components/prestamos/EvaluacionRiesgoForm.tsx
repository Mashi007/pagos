import { useState } from 'react'
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
  DollarSign
} from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { usePermissions } from '@/hooks/usePermissions'
import { Prestamo } from '@/types'
import { prestamoService } from '@/services/prestamoService'
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
  
  // Criterio 4: Arraigo Geográfico
  tipo_vivienda: string
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
  
  // Criterio 7: Enganche
  enganche_pagado: number
  valor_garantia: number
}

export function EvaluacionRiesgoForm({ prestamo, onClose, onSuccess }: EvaluacionRiesgoFormProps) {
  const { isAdmin } = usePermissions()
  const [isLoading, setIsLoading] = useState(false)
  const [resultado, setResultado] = useState<any>(null)
  const [showSection, setShowSection] = useState<string>('criterio1')
  
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
    
    // Criterio 4: Arraigo Geográfico (12 puntos)
    tipo_vivienda: 'alquiler_1_2',
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
    
    // Criterio 6: Edad del Cliente (5 puntos)
    edad: 0,
    
    // Criterio 7: Enganche Pagado (5 puntos)
    enganche_pagado: 0,
    valor_garantia: 0,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const confirmacion = window.confirm(
      '⚠️ CONFIRMACIÓN IMPORTANTE\n\n' +
      '¿Confirma que la información ingresada refleja FIELMENTE los documentos presentados?\n\n' +
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
        
        // Criterio 4
        tipo_vivienda: formData.tipo_vivienda,
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
        
        // Criterio 6
        edad: formData.edad,
        
        // Criterio 7
        enganche_pagado: formData.enganche_pagado,
        valor_garantia: formData.valor_garantia,
      }

      const response = await prestamoService.evaluarRiesgo(prestamo.id, datosEvaluacion)
      setResultado(response)
      toast.success('✅ Evaluación completada exitosamente')
    } catch (error: any) {
      toast.error(error.message || 'Error al evaluar riesgo')
    } finally {
      setIsLoading(false)
    }
  }

  const secciones = [
    { id: 'criterio1', label: 'Criterio 1: Capacidad de Pago', puntos: '29' },
    { id: 'criterio2', label: 'Criterio 2: Estabilidad Laboral', puntos: '23' },
    { id: 'criterio3', label: 'Criterio 3: Referencias', puntos: '9' },
    { id: 'criterio4', label: 'Criterio 4: Arraigo Geográfico', puntos: '12' },
    { id: 'criterio5', label: 'Criterio 5: Perfil Sociodemográfico', puntos: '17' },
    { id: 'criterio6', label: 'Criterio 6: Edad', puntos: '5' },
    { id: 'criterio7', label: 'Criterio 7: Enganche', puntos: '5' },
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
                {seccion.label.split(':')[0]} ({seccion.puntos} pts)
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto max-h-[60vh]">
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

          {/* CRITERIO 4: ARRAIGO GEOGRÁFICO (12 puntos) */}
          {showSection === 'criterio4' && (
            <Card className="border-green-200">
              <CardHeader className="bg-green-50">
                <CardTitle className="flex items-center gap-2 text-green-700">
                  <MapPin className="h-5 w-5" />
                  CRITERIO 4: ARRAIGO GEOGRÁFICO (12 puntos)
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Situación de Vivienda *
                  </label>
                  <Select
                    value={formData.tipo_vivienda}
                    onValueChange={(value) => setFormData({ ...formData, tipo_vivienda: value })}
                    required
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="casa_propia">Casa Propia (5 pts)</SelectItem>
                      <SelectItem value="alquiler_mas_2">Alquiler &gt;2 años (4 pts)</SelectItem>
                      <SelectItem value="alquiler_1_2">Alquiler 1-2 años (3 pts)</SelectItem>
                      <SelectItem value="alquiler_menos_1">Alquiler &lt;1 año (1 pt)</SelectItem>
                      <SelectItem value="prestado">De Prestado (0.5 pts)</SelectItem>
                      <SelectItem value="sin_vivienda">Sin Vivienda Fija (0 pts)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
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

          {/* CRITERIO 6: EDAD (5 puntos) */}
          {showSection === 'criterio6' && (
            <Card className="border-pink-200">
              <CardHeader className="bg-pink-50">
                <CardTitle className="flex items-center gap-2 text-pink-700">
                  <Calendar className="h-5 w-5" />
                  CRITERIO 6: EDAD DEL CLIENTE (5 puntos)
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Edad del Cliente (años) *
                  </label>
                  <Input
                    type="number"
                    min="0"
                    value={formData.edad || ''}
                    onChange={(e) => setFormData({ ...formData, edad: parseInt(e.target.value) || 0 })}
                    required
                  />
                  <div className="bg-pink-50 p-3 rounded border border-pink-200 mt-3">
                    <p className="text-xs text-pink-700">
                      <strong>Escala:</strong><br />
                      25-50 años → 5.0 pts (Óptimo) |<br />
                      22-24 / 51-55 años → 4.0 pts (Muy bueno/Bueno) |<br />
                      18-21 / 56-60 años → 3.0 pts (Regular) |<br />
                      61-65 años → 1.5 pts (Bajo) |<br />
                      &lt; 18 años → RECHAZO AUTOMÁTICO |<br />
                      &gt; 65 años → 1.0 pt (Muy bajo)
                    </p>
                        </div>
                      </div>
              </CardContent>
            </Card>
          )}

          {/* CRITERIO 7: ENGANCHE (5 puntos) */}
          {showSection === 'criterio7' && (
            <Card className="border-red-200">
              <CardHeader className="bg-red-50">
                <CardTitle className="flex items-center gap-2 text-red-700">
                  <DollarSign className="h-5 w-5" />
                  CRITERIO 7: ENGANCHE PAGADO (5 puntos)
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                      Enganche Pagado (USD) *
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.enganche_pagado || ''}
                      onChange={(e) => setFormData({ ...formData, enganche_pagado: parseFloat(e.target.value) || 0 })}
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                      Valor del Activo/Moto (USD) *
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.valor_garantia || ''}
                      onChange={(e) => setFormData({ ...formData, valor_garantia: parseFloat(e.target.value) || 0 })}
                    required
                  />
                </div>
              </div>
                <div className="bg-red-50 p-3 rounded border border-red-200">
                  <p className="text-xs text-red-700">
                    <strong>Escala:</strong> ≥30% → 5 pts | 25-29% → 4.5 pts | 20-24% → 4 pts | 15-19% → 3 pts | 10-14% → 2 pts | 5-9% → 1 pt | &lt;5% → 0.5 pts | 0% → 0 pts
                  </p>
                </div>
            </CardContent>
          </Card>
          )}

          {/* RESULTADO */}
          {resultado && (
            <Card className="border-green-300 bg-green-50 mt-4">
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
                {resultado.requisitos_adicionales && (
                  <div className="bg-white p-3 rounded border">
                    <p className="text-sm font-medium mb-2">Requisitos Adicionales:</p>
                    <p className="text-sm">{resultado.requisitos_adicionales}</p>
                    </div>
                )}
                </CardContent>
              </Card>
          )}

          {/* Botones */}
          {!resultado && (
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isLoading}>
                <Calculator className="h-4 w-4 mr-2" />
                {isLoading ? 'Evaluando...' : 'Evaluar Riesgo'}
              </Button>
            </div>
          )}
          {resultado && (
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button type="button" variant="outline" onClick={onClose}>
                Cerrar
              </Button>
            </div>
          )}
        </form>
      </motion.div>
    </motion.div>
  )
}

