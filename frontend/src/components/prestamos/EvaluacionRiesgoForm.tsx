import { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  Calculator, 
  AlertCircle,
  X,
  Save,
  CheckCircle,
  XCircle,
  Info,
  TrendingUp,
  TrendingDown
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
  
  // Criterio 3: Referencias
  num_referencias_verificadas: number
  años_conoce: number
  
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
  
  if (!isAdmin) {
    return null
  }
  
  const [formData, setFormData] = useState<EvaluacionFormData>({
    // Criterio 1
    ingresos_mensuales: 0,
    gastos_fijos_mensuales: 0,
    otras_deudas: 0,
    
    // Criterio 2
    meses_trabajo: 0,
    tipo_empleo: 'empleado_formal',
    sector_economico: 'servicios_esenciales',
    
    // Criterio 3
    num_referencias_verificadas: 0,
    años_conoce: 0,
    
    // Criterio 4
    tipo_vivienda: 'alquiler_1_2',
    familia_cercana: false,
    familia_pais: false,
    minutos_trabajo: 0,
    
    // Criterio 5
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
    
    // Criterio 6
    edad: 0,
    
    // Criterio 7
    enganche_pagado: 0,
    valor_garantia: 0,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // ✅ CONFIRMACIÓN OBLIGATORIA
    const confirmacion = window.confirm(
      '⚠️ CONFIRMACIÓN IMPORTANTE\n\n' +
      '¿Confirma que la información ingresada refleja FIELMENTE los documentos presentados por el cliente?\n\n' +
      'Al confirmar, usted certifica que:\n' +
      '✓ Los ingresos declarados coinciden con documentos\n' +
      '✓ Los gastos reportados son verificables\n' +
      '✓ La información de empleo es correcta\n' +
      '✓ Los valores de anticipo y valor del activo son reales\n\n' +
      '¿Desea proceder con la evaluación?'
    )
    
    if (!confirmacion) {
      toast('Evaluación cancelada. Verifique los documentos antes de continuar.')
      return
    }
    
    setIsLoading(true)

    try {
      // Construir datos de evaluación según los 7 criterios
      const datosEvaluacion = {
        // Criterio 1
        ingresos_mensuales: formData.ingresos_mensuales,
        gastos_fijos_mensuales: formData.gastos_fijos_mensuales,
        otras_deudas: formData.otras_deudas,
        
        // Criterio 2
        meses_trabajo: formData.meses_trabajo,
        tipo_empleo: formData.tipo_empleo,
        sector_economico: formData.sector_economico,
        
        // Criterio 3
        num_referencias_verificadas: formData.num_referencias_verificadas,
        años_conoce: formData.años_conoce,
        
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
      toast.success('✅ Evaluación guardada exitosamente')
    } catch (error: any) {
      toast.error(error.message || 'Error al evaluar riesgo')
    } finally {
      setIsLoading(false)
    }
  }

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
        className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[95vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-white border-b p-4 flex justify-between items-center z-10">
          <div className="flex items-center gap-3">
            <Calculator className="h-6 w-6 text-blue-600" />
            <h2 className="text-2xl font-bold">Evaluación de Riesgo</h2>
            <Badge variant="secondary">Préstamo #{prestamo.id}</Badge>
            <Badge>7 Criterios - 100 Puntos</Badge>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* CRITERIO 1: CAPACIDAD DE PAGO (33 puntos) */}
          <Card className="border-blue-200">
            <CardHeader className="bg-blue-50">
              <CardTitle className="flex items-center gap-2 text-blue-700">
                <TrendingDown className="h-5 w-5" />
                Criterio 1: Capacidad de Pago (33 puntos)
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Ingresos Mensuales (USD)
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.ingresos_mensuales || ''}
                    onChange={(e) => setFormData({ ...formData, ingresos_mensuales: parseFloat(e.target.value) || 0 })}
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Gastos Fijos Mensuales (USD)
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
                    Otras Deudas Mensuales (USD)
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.otras_deudas || ''}
                    onChange={(e) => setFormData({ ...formData, otras_deudas: parseFloat(e.target.value) || 0 })}
                    required
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* CRITERIO 2: ESTABILIDAD LABORAL (23 puntos) */}
          <Card className="border-yellow-200">
            <CardHeader className="bg-yellow-50">
              <CardTitle className="flex items-center gap-2 text-yellow-700">
                <AlertCircle className="h-5 w-5" />
                Criterio 2: Estabilidad Laboral (23 puntos)
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Meses de Trabajo
                  </label>
                  <Input
                    type="number"
                    min="0"
                    value={formData.meses_trabajo || ''}
                    onChange={(e) => setFormData({ ...formData, meses_trabajo: parseInt(e.target.value) || 0 })}
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Tipo de Empleo
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
                      <SelectItem value="informal_estable">Informal Estable (6 pts)</SelectItem>
                      <SelectItem value="independiente_formal">Independiente Formal (5 pts)</SelectItem>
                      <SelectItem value="independiente_informal">Independiente Informal (3 pts)</SelectItem>
                      <SelectItem value="sin_empleo">Sin Empleo (0 pts)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Sector Económico
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
              </div>
            </CardContent>
          </Card>

          {/* CRITERIO 3: REFERENCIAS (5 puntos) */}
          <Card className="border-purple-200">
            <CardHeader className="bg-purple-50">
              <CardTitle className="flex items-center gap-2 text-purple-700">
                <CheckCircle className="h-5 w-5" />
                Criterio 3: Referencias Personales (5 puntos)
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Referencias Verificadas
                  </label>
                  <Input
                    type="number"
                    min="0"
                    value={formData.num_referencias_verificadas || ''}
                    onChange={(e) => setFormData({ ...formData, num_referencias_verificadas: parseInt(e.target.value) || 0 })}
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Años de Conocer (promedio)
                  </label>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    value={formData.años_conoce || ''}
                    onChange={(e) => setFormData({ ...formData, años_conoce: parseFloat(e.target.value) || 0 })}
                    required
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* RESULTADO Y ACCIONES */}
          {resultado ? (
            <Card className="border-green-300 bg-green-50">
              <CardHeader>
                <CardTitle className="text-green-700">Resultado de la Evaluación</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="text-sm text-gray-600">Puntuación Total</label>
                    <p className="text-2xl font-bold">{resultado.puntuacion_total?.toFixed(2)} / 100</p>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">Riesgo</label>
                    <Badge className="text-lg">{resultado.clasificacion_riesgo}</Badge>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">Decisión</label>
                    <Badge variant={resultado.decision_final?.includes('RECHAZADO') ? 'destructive' : 'default'}>
                      {resultado.decision_final}
                    </Badge>
                  </div>
                </div>
                {resultado.requisitos_adicionales && (
                  <div>
                    <label className="text-sm text-gray-600">Requisitos Adicionales</label>
                    <p className="text-sm">{resultado.requisitos_adicionales}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
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
        </form>
      </motion.div>
    </motion.div>
  )
}
