import { useState } from 'react'
import { motion } from 'framer-motion'
import { 
  Calculator, 
  TrendingUp, 
  TrendingDown, 
  AlertCircle,
  X,
  Save,
  CheckCircle,
  XCircle
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { usePermissions } from '@/hooks/usePermissions'
import { Prestamo } from '@/types'
import { prestamoService } from '@/services/prestamoService'
import toast from 'react-hot-toast'

interface EvaluacionRiesgoFormProps {
  prestamo: Prestamo
  onClose: () => void
  onSuccess: () => void
}

interface EvaluacionForm {
  // Ratio de Endeudamiento (Criterio 1)
  ingresos_mensuales: number
  gastos_fijos_mensuales: number
  
  // Ratio de Cobertura (Criterio 2)
  // Calculado automáticamente
  
  // Historial Crediticio (Criterio 3)
  historial_crediticio: 'Excelente' | 'Bueno' | 'Regular' | 'Malo'
  
  // Estabilidad Laboral (Criterio 4)
  anos_empleo: number
  
  // Tipo de Empleo (Criterio 5)
  tipo_empleo: 'Público' | 'Privado' | 'Independiente' | 'Otro'
  
  // Enganche y Garantías (Criterio 6)
  enganche_pagado: number
  valor_garantia: number
  
  // Red Flags (opcional)
  red_flags?: {
    cedula_falsa?: boolean
    ingresos_no_verificables?: boolean
    historial_malo?: boolean
    litigio_legal?: boolean
    mas_de_un_prestamo_activo?: boolean
  }
}

export function EvaluacionRiesgoForm({ prestamo, onClose, onSuccess }: EvaluacionRiesgoFormProps) {
  const { isAdmin } = usePermissions()
  const [isLoading, setIsLoading] = useState(false)
  const [resultado, setResultado] = useState<any>(null)
  
  const [formData, setFormData] = useState<EvaluacionForm>({
    ingresos_mensuales: 0,
    gastos_fijos_mensuales: 0,
    historial_crediticio: 'Regular',
    anos_empleo: 0,
    tipo_empleo: 'Otro',
    enganche_pagado: 0,
    valor_garantia: 0,
  })

  const [redFlags, setRedFlags] = useState({
    cedula_falsa: false,
    ingresos_no_verificables: false,
    historial_malo: false,
    litigio_legal: false,
    mas_de_un_prestamo_activo: false,
  })

  if (!isAdmin) {
    return null
  }

  // Calcular ratios automáticamente
  const calcularRatios = () => {
    const cuotaMensual = prestamo.cuota_periodo || 0
    
    // Ratio de Endeudamiento
    const ratioEndeudamiento = formData.ingresos_mensuales > 0
      ? ((formData.gastos_fijos_mensuales + cuotaMensual) / formData.ingresos_mensuales) * 100
      : 0

    // Ratio de Cobertura
    const ratioCobertura = formData.gastos_fijos_mensuales > 0
      ? formData.ingresos_mensuales / formData.gastos_fijos_mensuales
      : 0

    // LTV (Loan to Value)
    const ltv = prestamo.total_financiamiento > 0
      ? ((prestamo.total_financiamiento - formData.enganche_pagado) / formData.valor_garantia) * 100
      : 0

    return {
      ratioEndeudamiento,
      ratioCobertura,
      ltv
    }
  }

  const ratios = calcularRatios()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // ✅ CONFIRMACIÓN OBLIGATORIA: El usuario debe aceptar que la información refleja los documentos
    const confirmacion = window.confirm(
      '⚠️ CONFIRMACIÓN IMPORTANTE\n\n' +
      '¿Confirma que la información ingresada refleja FIELMENTE los documentos presentados por el cliente?\n\n' +
      'Al confirmar, usted certifica que:\n' +
      '✓ Los ingresos declarados coinciden con documentos\n' +
      '✓ Los gastos reportados son verificables\n' +
      '✓ El historial crediticio está validado\n' +
      '✓ La información de empleo es correcta\n' +
      '✓ Los valores de enganche y garantía son reales\n\n' +
      '¿Desea proceder con la evaluación?'
    )
    
    if (!confirmacion) {
      toast('Evaluación cancelada. Verifique los documentos antes de continuar.')
      return
    }
    
    setIsLoading(true)

    try {
      const datosEvaluacion = {
        prestamo_id: prestamo.id,
        ratio_endeudamiento_calculo: ratios.ratioEndeudamiento,
        ratio_cobertura_calculo: ratios.ratioCobertura,
        historial_crediticio_descripcion: formData.historial_crediticio,
        anos_empleo: formData.anos_empleo,
        tipo_empleo_descripcion: formData.tipo_empleo,
        enganche_garantias_calculo: ratios.ltv,
        red_flags: redFlags,
        verificado_usuario: true,  // ✅ Usuario confirmó verificación
      }

      const response = await prestamoService.evaluarRiesgo(prestamo.id, datosEvaluacion)
      
      setResultado(response)
      toast.success('✅ Evaluación guardada exitosamente. La información ha sido verificada y confirmada.')
      
      // Auto-cerrar después de 2 segundos
      setTimeout(() => {
        onSuccess()
        onClose()
      }, 2000)
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
        className="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-white border-b p-4 flex justify-between items-center z-10">
          <div className="flex items-center gap-3">
            <Calculator className="h-6 w-6 text-blue-600" />
            <h2 className="text-2xl font-bold">Evaluación de Riesgo</h2>
            <Badge variant="secondary">Préstamo #{prestamo.id}</Badge>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* CRITERIO 1: RATIO DE ENDEUDAMIENTO */}
          <Card className="border-blue-200">
            <CardHeader className="bg-blue-50">
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <TrendingDown className="h-5 w-5 text-blue-600" />
                  Criterio 1: Ratio de Endeudamiento (25%)
                </span>
                {ratios.ratioEndeudamiento > 0 && (
                  <Badge variant="outline">
                    {ratios.ratioEndeudamiento.toFixed(2)}%
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Ingresos Mensuales (USD)
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.ingresos_mensuales}
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
                    value={formData.gastos_fijos_mensuales}
                    onChange={(e) => setFormData({ ...formData, gastos_fijos_mensuales: parseFloat(e.target.value) || 0 })}
                    required
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* CRITERIO 2: RATIO DE COBERTURA */}
          <Card className="border-green-200">
            <CardHeader className="bg-green-50">
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-green-600" />
                  Criterio 2: Ratio de Cobertura (20%)
                </span>
                {ratios.ratioCobertura > 0 && (
                  <Badge variant="outline">
                    {ratios.ratioCobertura.toFixed(2)}x
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <p className="text-sm text-gray-600">
                Calculado automáticamente: Ingresos / Gastos Fijos
              </p>
            </CardContent>
          </Card>

          {/* CRITERIO 3: HISTORIAL CREDITICIO */}
          <Card className="border-purple-200">
            <CardHeader className="bg-purple-50">
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-purple-600" />
                Criterio 3: Historial Crediticio (20%)
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <Select
                value={formData.historial_crediticio}
                onValueChange={(value: any) => setFormData({ ...formData, historial_crediticio: value })}
                required
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Excelente">Excelente</SelectItem>
                  <SelectItem value="Bueno">Bueno</SelectItem>
                  <SelectItem value="Regular">Regular</SelectItem>
                  <SelectItem value="Malo">Malo</SelectItem>
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          {/* CRITERIO 4: ESTABILIDAD LABORAL */}
          <Card className="border-yellow-200">
            <CardHeader className="bg-yellow-50">
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="h-5 w-5 text-yellow-600" />
                Criterio 4: Estabilidad Laboral (15%)
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <Input
                type="number"
                step="0.5"
                value={formData.anos_empleo}
                onChange={(e) => setFormData({ ...formData, anos_empleo: parseFloat(e.target.value) || 0 })}
                placeholder="Años en el empleo actual"
                required
              />
            </CardContent>
          </Card>

          {/* CRITERIO 5: TIPO DE EMPLEO */}
          <Card className="border-orange-200">
            <CardHeader className="bg-orange-50">
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-orange-600" />
                Criterio 5: Tipo de Empleo (10%)
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4">
              <Select
                value={formData.tipo_empleo}
                onValueChange={(value: any) => setFormData({ ...formData, tipo_empleo: value })}
                required
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Público">Público</SelectItem>
                  <SelectItem value="Privado">Privado</SelectItem>
                  <SelectItem value="Independiente">Independiente</SelectItem>
                  <SelectItem value="Otro">Otro</SelectItem>
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          {/* CRITERIO 6: ENGANCHE Y GARANTÍAS */}
          <Card className="border-red-200">
            <CardHeader className="bg-red-50">
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Calculator className="h-5 w-5 text-red-600" />
                  Criterio 6: Enganche y Garantías (10%)
                </span>
                {ratios.ltv > 0 && (
                  <Badge variant="outline">
                    LTV: {ratios.ltv.toFixed(2)}%
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Enganche Pagado (USD)
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.enganche_pagado}
                    onChange={(e) => setFormData({ ...formData, enganche_pagado: parseFloat(e.target.value) || 0 })}
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Valor de Garantía (USD)
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.valor_garantia}
                    onChange={(e) => setFormData({ ...formData, valor_garantia: parseFloat(e.target.value) || 0 })}
                    required
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* RED FLAGS */}
          <Card className="border-red-300">
            <CardHeader className="bg-red-100">
              <CardTitle className="flex items-center gap-2 text-red-700">
                <XCircle className="h-5 w-5" />
                Señales de Alerta (Red Flags)
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-4 space-y-3">
              {Object.entries(redFlags).map(([key, value]) => (
                <div key={key} className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id={key}
                    checked={value}
                    onChange={(e) => setRedFlags({ ...redFlags, [key]: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  <label htmlFor={key} className="text-sm">
                    {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </label>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* RESULTADO */}
          {resultado && (
            <Card className="border-blue-300 bg-blue-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-blue-700">
                  <CheckCircle className="h-6 w-6" />
                  Resultado de la Evaluación
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-gray-600">Puntuación Total</label>
                    <p className="text-2xl font-bold">{resultado.puntuacion_total}</p>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">Clasificación</label>
                    <Badge className="text-lg">
                      {resultado.clasificacion_riesgo}
                    </Badge>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">Decisión Final</label>
                    <Badge variant={resultado.decision_final === 'APROBADO' ? 'default' : 'destructive'}>
                      {resultado.decision_final}
                    </Badge>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">Tasa de Interés</label>
                    <p className="text-lg font-semibold">
                      {typeof resultado.tasa_interes_aplicada === 'number' 
                        ? (resultado.tasa_interes_aplicada * 100).toFixed(2) + '%' 
                        : '0.00%'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Botones */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancelar
            </Button>
            <Button type="submit" disabled={isLoading}>
              <Calculator className="h-4 w-4 mr-2" />
              {isLoading ? 'Evaluando...' : 'Evaluar Riesgo'}
            </Button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  )
}

