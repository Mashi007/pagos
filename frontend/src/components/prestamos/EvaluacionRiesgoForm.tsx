import { motion } from 'framer-motion'
import { AlertCircle, CheckCircle, DollarSign, Calendar } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Badge } from '../../components/ui/badge'
import { useEscapeClose } from '../../hooks/useEscapeClose'
import { usePermissions } from '../../hooks/usePermissions'
import { Prestamo } from '../../types'
import { useEvaluacionRiesgo } from '../../hooks/useEvaluacionRiesgo'
import { EvaluacionRiesgoHeader } from './evaluacion/EvaluacionRiesgoHeader'
import { EvaluacionRiesgoCriteriosSection } from './evaluacion/EvaluacionRiesgoCriteriosSection'
import { EvaluacionRiesgoMLSection } from './evaluacion/EvaluacionRiesgoMLSection'
import { EvaluacionRiesgoActions } from './evaluacion/EvaluacionRiesgoActions'

interface EvaluacionRiesgoFormProps {
  prestamo: Prestamo
  onClose: () => void
  onSuccess: () => void
}

export function EvaluacionRiesgoForm({ prestamo, onClose, onSuccess }: EvaluacionRiesgoFormProps) {
  useEscapeClose(onClose, true)
  const { isAdmin } = usePermissions()

  const {
    formData,
    handleChange,
    handleSubmit,
    isLoading,
    resultado,
    showSection,
    setShowSection,
    clienteEdad,
    showFormularioAprobacion,
    setShowFormularioAprobacion,
    resumenPrestamos,
    bloqueadoPorMora,
    condicionesAprobacion,
    setCondicionesAprobacion,
    seccion1Completa,
    seccion2Completa,
    seccion3Completa,
    seccion4Completa,
    seccion5Completa,
    seccion6Completa,
    seccion7Completa,
    todasSeccionesCompletas,
    criteriosFaltantes,
    seccionCompleta,
    prestamo: prestamoFromHook,
  } = useEvaluacionRiesgo({ prestamo, onSuccess, onClose })

  if (!isAdmin) {
    return null
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
        <EvaluacionRiesgoHeader prestamo={prestamo} onClose={onClose} />

        <div className="bg-gray-50 px-4 py-2 border-b overflow-x-auto">
          <div className="flex gap-2">
            {secciones.map((seccion) => (
              <button
                key={seccion.id}
                type="button"
                onClick={() => setShowSection(seccion.id)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors flex items-center gap-2 ${
                  showSection === seccion.id ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'
                }`}
              >
                {seccionCompleta(seccion.id) && seccion.id.startsWith('criterio') && (
                  <CheckCircle className="h-4 w-4 text-green-600" />
                )}
                {!seccionCompleta(seccion.id) && seccion.id.startsWith('criterio') && (
                  <AlertCircle className="h-4 w-4 text-amber-600" />
                )}
                {seccion.label.split(':')[0]} {seccion.puntos ? `(${seccion.puntos} pts)` : ''}
              </button>
            ))}
          </div>
          {!todasSeccionesCompletas && (
            <div className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 px-3 py-2 rounded">
              <strong>⚠️ Debe completar todos los 7 criterios antes de evaluar.</strong> Faltan:{' '}
              {[
                !seccion1Completa && 'Criterio 1',
                !seccion2Completa && 'Criterio 2',
                !seccion3Completa && 'Criterio 3',
                !seccion4Completa && 'Criterio 4',
                !seccion5Completa && 'Criterio 5',
                !seccion6Completa && 'Criterio 6',
                !seccion7Completa && 'Criterio 7',
              ]
                .filter(Boolean)
                .join(', ')}
              .
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto max-h-[60vh]">
          {(showSection === 'situacion' || showSection.startsWith('criterio')) && (
            <EvaluacionRiesgoCriteriosSection
              showSection={showSection}
              formData={formData}
              handleChange={handleChange}
              prestamo={prestamoFromHook}
              clienteEdad={clienteEdad}
              resumenPrestamos={resumenPrestamos}
              bloqueadoPorMora={bloqueadoPorMora}
            />
          )}

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
                    <Badge
                      className="text-lg"
                      variant={
                        resultado.clasificacion_riesgo === 'A'
                          ? 'default'
                          : resultado.clasificacion_riesgo === 'B'
                          ? 'default'
                          : 'outline'
                      }
                    >
                      {resultado.clasificacion_riesgo}
                    </Badge>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">Decisión Final</label>
                    <Badge
                      variant={
                        resultado.decision_final?.includes('RECHAZADO') ? 'destructive' : 'default'
                      }
                      className="text-lg"
                    >
                      {resultado.decision_final}
                    </Badge>
                  </div>
                </div>

                {resultado.sugerencias && (
                  <div className="bg-blue-50 p-4 rounded border border-blue-200">
                    <div className="flex justify-between items-center mb-3">
                      <h5 className="font-semibold text-blue-900">Condiciones para Aprobación:</h5>
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
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <label className="text-xs text-blue-700">Tasa de Interés Sugerida:</label>
                          <p className="text-lg font-bold text-blue-900">
                            {resultado.sugerencias.tasa_interes_sugerida || 8.0}%
                          </p>
                        </div>
                        <div>
                          <label className="text-xs text-blue-700">Plazo Máximo Sugerido:</label>
                          <p className="text-lg font-bold text-blue-900">
                            {resultado.sugerencias.plazo_maximo_sugerido || 36} meses
                          </p>
                        </div>
                        <div>
                          <label className="text-xs text-blue-700">Enganche Mínimo:</label>
                          <p className="text-lg font-bold text-blue-900">
                            {resultado.sugerencias.enganche_minimo_sugerido || 15.0}%
                          </p>
                        </div>
                      </div>
                    ) : (
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
                                min={0}
                                max={100}
                                value={condicionesAprobacion.tasa_interes}
                                onChange={(e) =>
                                  setCondicionesAprobacion({
                                    ...condicionesAprobacion,
                                    tasa_interes: parseFloat(e.target.value) || 0,
                                  })
                                }
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
                              min={1}
                              value={condicionesAprobacion.plazo_maximo}
                              onChange={(e) =>
                                setCondicionesAprobacion({
                                  ...condicionesAprobacion,
                                  plazo_maximo: parseInt(e.target.value) || 36,
                                })
                              }
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
                                onChange={(e) =>
                                  setCondicionesAprobacion({
                                    ...condicionesAprobacion,
                                    fecha_base_calculo: e.target.value,
                                  })
                                }
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
                          <label className="text-sm font-medium text-gray-700">Observaciones</label>
                          <textarea
                            value={condicionesAprobacion.observaciones}
                            onChange={(e) =>
                              setCondicionesAprobacion({
                                ...condicionesAprobacion,
                                observaciones: e.target.value,
                              })
                            }
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

                {resultado.prediccion_ml && (
                  <EvaluacionRiesgoMLSection
                    prediccion_ml={resultado.prediccion_ml}
                    clasificacion_riesgo={resultado.clasificacion_riesgo}
                    puntuacion_total={resultado.puntuacion_total}
                  />
                )}

                <div className="bg-white p-3 rounded border">
                  <h5 className="font-semibold mb-2">Detalle de Criterios:</h5>
                  <ul className="list-disc list-inside text-sm space-y-1">
                    <li>
                      <strong>1. Capacidad de Pago:</strong>{' '}
                      {resultado.detalle_criterios?.ratio_endeudamiento?.puntos?.toFixed(1)} pts (Endeudamiento) +{' '}
                      {resultado.detalle_criterios?.ratio_cobertura?.puntos?.toFixed(1)} pts (Cobertura) (Total:{' '}
                      {(
                        (resultado.detalle_criterios?.ratio_endeudamiento?.puntos ?? 0) +
                        (resultado.detalle_criterios?.ratio_cobertura?.puntos ?? 0)
                      ).toFixed(1)}
                      /29 pts)
                    </li>
                    <li>
                      <strong>2. Estabilidad Laboral:</strong>{' '}
                      {resultado.detalle_criterios?.antiguedad_trabajo?.puntos?.toFixed(1)} pts (Antigüedad) +{' '}
                      {resultado.detalle_criterios?.tipo_empleo?.puntos?.toFixed(1)} pts (Tipo Empleo) +{' '}
                      {resultado.detalle_criterios?.sector_economico?.puntos?.toFixed(1)} pts (Sector) (Total:{' '}
                      {(
                        (resultado.detalle_criterios?.antiguedad_trabajo?.puntos ?? 0) +
                        (resultado.detalle_criterios?.tipo_empleo?.puntos ?? 0) +
                        (resultado.detalle_criterios?.sector_economico?.puntos ?? 0)
                      ).toFixed(1)}
                      /23 pts)
                    </li>
                    <li>
                      <strong>3. Referencias Personales:</strong>{' '}
                      {resultado.detalle_criterios?.referencias?.puntos?.toFixed(1)}/9 pts (Ref1:{' '}
                      {resultado.detalle_criterios?.referencias?.referencia1_calificacion}, Ref2:{' '}
                      {resultado.detalle_criterios?.referencias?.referencia2_calificacion}, Ref3:{' '}
                      {resultado.detalle_criterios?.referencias?.referencia3_calificacion})
                    </li>
                    <li>
                      <strong>4. Arraigo Geográfico:</strong>{' '}
                      {resultado.detalle_criterios?.arraigo_vivienda?.toFixed(1)} pts (Vivienda) +{' '}
                      {resultado.detalle_criterios?.arraigo_laboral?.toFixed(1)} pts (Laboral) (Total:{' '}
                      {(
                        (resultado.detalle_criterios?.arraigo_familiar ?? 0) +
                        (resultado.detalle_criterios?.arraigo_laboral ?? 0)
                      ).toFixed(1)}
                      /7 pts)
                    </li>
                    <li>
                      <strong>5. Perfil Sociodemográfico:</strong>{' '}
                      {resultado.detalle_criterios?.vivienda?.puntos?.toFixed(1)} pts (Vivienda) +{' '}
                      {resultado.detalle_criterios?.estado_civil?.puntos?.toFixed(1)} pts (Estado Civil) +{' '}
                      {resultado.detalle_criterios?.hijos?.puntos?.toFixed(1)} pts (Hijos) (Total:{' '}
                      {(
                        (resultado.detalle_criterios?.vivienda?.puntos ?? 0) +
                        (resultado.detalle_criterios?.estado_civil?.puntos ?? 0) +
                        (resultado.detalle_criterios?.hijos?.puntos ?? 0)
                      ).toFixed(1)}
                      /17 pts)
                    </li>
                    <li>
                      <strong>6. Edad del Cliente:</strong>{' '}
                      {resultado.detalle_criterios?.edad?.puntos?.toFixed(1)}/10 pts (
                      {resultado.detalle_criterios?.edad?.cliente} años)
                    </li>
                    <li>
                      <strong>7. Capacidad de Maniobra:</strong>{' '}
                      {resultado.detalle_criterios?.capacidad_maniobra?.puntos?.toFixed(1)}/5 pts (
                      {resultado.detalle_criterios?.capacidad_maniobra?.porcentaje_residual?.toFixed(2)}%
                      residual)
                    </li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          )}

          <EvaluacionRiesgoActions
            resultado={resultado}
            isLoading={isLoading}
            todasSeccionesCompletas={todasSeccionesCompletas}
            bloqueadoPorMora={bloqueadoPorMora}
            criteriosFaltantes={criteriosFaltantes}
            onClose={onClose}
            onSuccess={onSuccess}
          />
        </form>
      </motion.div>
    </motion.div>
  )
}
