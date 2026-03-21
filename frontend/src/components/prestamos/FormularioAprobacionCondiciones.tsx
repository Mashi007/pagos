import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { X, DollarSign, Calendar, FileText } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { useAplicarCondicionesAprobacion } from '../../hooks/usePrestamos'
import { prestamoService } from '../../services/prestamoService'

interface FormularioAprobacionCondicionesProps {
  prestamo: any
  onClose: () => void
  onSuccess: () => void
}

export function FormularioAprobacionCondiciones({ prestamo, onClose, onSuccess }: FormularioAprobacionCondicionesProps) {
  const [condicionesAprobacion, setCondicionesAprobacion] = useState({
    tasa_interes: 0.0, // Siempre 0% â producto sin interÃ©s
    plazo_maximo: prestamo.numero_cuotas || 36,
    fecha_base_calculo: prestamo.fecha_base_calculo || new Date().toISOString().split('T')[0],
    observaciones: prestamo.observaciones || ''
  })
  const [isLoading, setIsLoading] = useState(false)
  const [sugerencias, setSugerencias] = useState<any>(null)

  const aplicarCondiciones = useAplicarCondicionesAprobacion()

  // Obtener sugerencias desde la Ãºltima evaluaciÃ³n de riesgo
  useEffect(() => {
    const obtenerSugerencias = async () => {
      try {
        await prestamoService.getAuditoria(prestamo.id)
        // tasa_interes siempre 0% â no se sobreescribe desde sugerencias
      } catch (error) {
        console.log('No se encontraron sugerencias previas, usando valores por defecto')
      }
    }
    obtenerSugerencias()
  }, [prestamo.id])

  const handleAprobar = async () => {
    console.log('Ã°Å¸ââ handleAprobar llamado')
    console.log('Ã°Å¸ââ¹ Condiciones:', condicionesAprobacion)

    // Validaciones
    if (!condicionesAprobacion.fecha_base_calculo) {
      console.error('Ã¢ÂÅ ValidaciÃ³n fallida: fecha_base_calculo vacÃ­a')
      toast.error('Debe seleccionar una fecha de desembolso')
      return
    }
    if (condicionesAprobacion.tasa_interes < 0 || condicionesAprobacion.tasa_interes > 100) {
      console.error('Ã¢ÂÅ ValidaciÃ³n fallida: tasa_interes fuera de rango', condicionesAprobacion.tasa_interes)
      toast.error('La tasa de interÃ©s debe estar entre 0 y 100%')
      return
    }
    if (condicionesAprobacion.plazo_maximo <= 0) {
      console.error('Ã¢ÂÅ ValidaciÃ³n fallida: plazo_maximo invÃ¡lido', condicionesAprobacion.plazo_maximo)
      toast.error('El plazo mÃ¡ximo debe ser mayor a 0 meses')
      return
    }

    console.log('Ã¢Åâ¦ Validaciones pasadas')

    const mensajeConfirmacion =
      `Â¿Desea aprobar este prÃ©stamo con las siguientes condiciones?\n\n` +
      `â¢ Tasa de InterÃ©s: ${condicionesAprobacion.tasa_interes}%\n` +
      `â¢ Plazo MÃ¡ximo: ${condicionesAprobacion.plazo_maximo} meses\n` +
      `â¢ Fecha de Desembolso: ${new Date(condicionesAprobacion.fecha_base_calculo).toLocaleDateString()}`

    if (!window.confirm(mensajeConfirmacion)) {
      console.log('Ã¢ÂÅ Usuario cancelÃ³ la confirmaciÃ³n')
      return
    }

    console.log('Ã¢Åâ¦ ConfirmaciÃ³n aceptada por el usuario')
    setIsLoading(true)

    try {
      const condiciones = {
        estado: 'APROBADO',
        tasa_interes: condicionesAprobacion.tasa_interes,
        plazo_maximo: condicionesAprobacion.plazo_maximo,
        fecha_base_calculo: condicionesAprobacion.fecha_base_calculo,
        observaciones: condicionesAprobacion.observaciones || `Aprobado manualmente. PrÃ©stamo ID: ${prestamo.id}`
      }

      console.log('Ã°Å¸âÂ¤ Enviando condiciones al backend:', condiciones)
      console.log('Ã°Å¸â â Prestamo ID:', prestamo.id)

      const resultado = await aplicarCondiciones.mutateAsync({
        prestamoId: prestamo.id,
        condiciones
      })

      console.log('Ã¢Åâ¦ Respuesta del backend:', resultado)

      toast.success('Ã¢Åâ¦ PrÃ©stamo aprobado exitosamente. La tabla de amortizaciÃ³n ha sido generada automÃ¡ticamente.')
      onSuccess()
      onClose()
    } catch (error: any) {
      console.error('Ã¢ÂÅ Error completo al aprobar prÃ©stamo:', error)
      console.error('Ã¢ÂÅ Error response:', error.response)
      console.error('Ã¢ÂÅ Error message:', error.message)
      toast.error(error.response?.data?.detail || error.message || 'Error al aprobar prÃ©stamo')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <Card>
          <CardHeader className="bg-gradient-to-r from-blue-600 to-blue-700 text-white">
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Aprobar CrÃ©dito - PrÃ©stamo #{prestamo.id}
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="text-white hover:bg-blue-800"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>

          <CardContent className="p-6">
            <div className="space-y-6">
              <div className="bg-blue-50 p-4 rounded border border-blue-200">
                <h5 className="font-semibold text-blue-900 mb-4">Ã°Å¸ââ¹ Condiciones para AprobaciÃ³n:</h5>

                <div className="bg-white p-4 rounded border border-blue-300 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">
                        Tasa de InterÃ©s (%) <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                        <Input
                          type="number"
                          step="0.1"
                          min="0"
                          max="100"
                          value={condicionesAprobacion.tasa_interes || ''}
                          onChange={(e) => {
                            const valor = e.target.value === '' ? 0 : parseFloat(e.target.value)
                            console.log('Ã°Å¸âÂ Tasa de interÃ©s cambiada:', valor)
                            setCondicionesAprobacion({
                              ...condicionesAprobacion,
                              tasa_interes: isNaN(valor) ? 0 : valor
                            })
                          }}
                          className="pl-10"
                          placeholder="0.0"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-gray-700">
                        Plazo MÃ¡ximo (meses) <span className="text-red-500">*</span>
                      </label>
                      <Input
                        type="number"
                        step="1"
                        min="1"
                        value={condicionesAprobacion.plazo_maximo || ''}
                        onChange={(e) => {
                          const valor = e.target.value === '' ? 36 : parseInt(e.target.value)
                          console.log('Ã°Å¸âÂ Plazo mÃ¡ximo cambiado:', valor)
                          setCondicionesAprobacion({
                            ...condicionesAprobacion,
                            plazo_maximo: isNaN(valor) ? 36 : valor
                          })
                        }}
                        placeholder="36"
                      />
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
                        Fecha desde la cual se calcularÃ¡n las cuotas
                      </p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700">
                      Observaciones
                    </label>
                    <Textarea
                      value={condicionesAprobacion.observaciones}
                      onChange={(e) => setCondicionesAprobacion({
                        ...condicionesAprobacion,
                        observaciones: e.target.value
                      })}
                      placeholder="Observaciones adicionales sobre la aprobaciÃ³n..."
                      rows={3}
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t">
                <Button type="button" variant="outline" onClick={onClose}>
                  Cancelar
                </Button>
                <Button
                  type="button"
                  className="bg-green-600 hover:bg-green-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    console.log('Ã°Å¸âÂ±Ã¯Â¸Â Click en botÃ³n Aprobar PrÃ©stamo')
                    console.log('Ã°Å¸ââ¹ Estado actual de condiciones:', condicionesAprobacion)
                    handleAprobar()
                  }}
                  disabled={
                    isLoading ||
                    !condicionesAprobacion.fecha_base_calculo ||
                    condicionesAprobacion.tasa_interes < 0 ||
                    condicionesAprobacion.tasa_interes > 100 ||
                    condicionesAprobacion.plazo_maximo <= 0
                  }
                  title={
                    !condicionesAprobacion.fecha_base_calculo
                      ? 'Debe seleccionar una fecha de desembolso'
                      : condicionesAprobacion.tasa_interes < 0 || condicionesAprobacion.tasa_interes > 100
                      ? 'La tasa de interÃ©s debe estar entre 0 y 100%'
                      : condicionesAprobacion.plazo_maximo <= 0
                      ? 'El plazo mÃ¡ximo debe ser mayor a 0'
                      : 'Aprobar prÃ©stamo con las condiciones especificadas'
                  }
                >
                  {isLoading ? 'Aprobando...' : 'Aprobar PrÃ©stamo'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}

