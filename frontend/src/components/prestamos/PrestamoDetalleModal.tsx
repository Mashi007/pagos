import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Eye, Calendar, DollarSign, User, Building, TrendingUp, AlertTriangle, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Badge } from '../../components/ui/badge'
import { Prestamo } from '../../types'
import { formatDate } from '../../utils'
import { TablaAmortizacionPrestamo } from './TablaAmortizacionPrestamo'
import { AuditoriaPrestamo } from './AuditoriaPrestamo'
import { usePrestamo } from '../../hooks/usePrestamos'
import { aiTrainingService } from '../../services/aiTrainingService'
import { prestamoService } from '../../services/prestamoService'
import { toast } from 'sonner'
import { useQuery } from '@tanstack/react-query'

interface PrestamoDetalleModalProps {
  prestamo: Prestamo
  onClose: () => void
}

export function PrestamoDetalleModal({ prestamo: prestamoInitial, onClose }: PrestamoDetalleModalProps) {
  const [activeTab, setActiveTab] = useState<'detalles' | 'amortizacion' | 'auditoria'>('detalles')
  const [prediccionImpago, setPrediccionImpago] = useState<any>(null)
  const [cargandoPrediccion, setCargandoPrediccion] = useState(false)

  // Recargar datos completos del préstamo
  const { data: prestamo, isLoading } = usePrestamo(prestamoInitial.id)

  // Obtener evaluación de riesgo
  const { data: evaluacionRiesgo, isLoading: loadingEvaluacion } = useQuery({
    queryKey: ['evaluacion-riesgo', prestamoInitial.id],
    queryFn: () => prestamoService.getEvaluacionRiesgo(prestamoInitial.id),
    enabled: !!prestamoInitial.id,
    retry: false, // No reintentar si no hay evaluación
    onError: () => {
      // Silenciar error si no hay evaluación
    }
  })

  // Cargar predicción de impago si el préstamo está aprobado o desembolsado
  useEffect(() => {
    const prestamoData = prestamo || prestamoInitial
    if (prestamoData?.estado === 'APROBADO' || prestamoData?.estado === 'DESEMBOLSADO') {
      cargarPrediccionImpago(prestamoData.id)
    }
  }, [prestamo, prestamoInitial])

  const cargarPrediccionImpago = async (prestamoId: number) => {
    setCargandoPrediccion(true)
    try {
      const resultado = await aiTrainingService.predecirImpago(prestamoId)
      setPrediccionImpago(resultado)
    } catch (error: any) {
      // No mostrar error si no hay modelo activo, solo no mostrar la predicción
      if (error?.response?.status !== 400) {
        console.error('Error cargando predicción de impago:', error)
      }
    } finally {
      setCargandoPrediccion(false)
    }
  }

  const getRiesgoColor = (nivel: string) => {
    const colores: Record<string, string> = {
      Bajo: 'text-green-600 bg-green-50 border-green-200',
      Medio: 'text-yellow-600 bg-yellow-50 border-yellow-200',
      Alto: 'text-red-600 bg-red-50 border-red-200',
    }
    return colores[nivel] || 'text-gray-600 bg-gray-50 border-gray-200'
  }

  if (isLoading) {
    return (
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={(e) => e.target === e.currentTarget && onClose()}
        >
          <div className="text-center bg-white p-8 rounded-lg">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Cargando detalles del préstamo...</p>
          </div>
        </motion.div>
      </AnimatePresence>
    )
  }

  const prestamoData = prestamo || prestamoInitial

  const getEstadoBadge = (estado: string) => {
    const badges = {
      DRAFT: 'bg-gray-100 text-gray-800 border-gray-300',
      EN_REVISION: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      APROBADO: 'bg-green-100 text-green-800 border-green-300',
      DESEMBOLSADO: 'bg-blue-100 text-blue-800 border-blue-300',
      RECHAZADO: 'bg-red-100 text-red-800 border-red-300',
    }
    return badges[estado as keyof typeof badges] || badges.DRAFT
  }

  const getEstadoLabel = (estado: string) => {
    const labels: Record<string, string> = {
      DRAFT: 'Borrador',
      EN_REVISION: 'En Revisión',
      APROBADO: 'Aprobado',
      DESEMBOLSADO: 'Desembolsado',
      RECHAZADO: 'Rechazado',
    }
    return labels[estado] || estado
  }

  return (
    <AnimatePresence>
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
          exit={{ scale: 0.95, y: 20 }}
          className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="sticky top-0 bg-white border-b p-4 flex justify-between items-center z-10">
            <div>
              <h2 className="text-2xl font-bold">Detalles del Préstamo #{prestamoData.id}</h2>
              <p className="text-sm text-gray-600">Cliente: {prestamoData.nombres}</p>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Tabs */}
          <div className="border-b px-4">
            <div className="flex gap-4">
              <button
                onClick={() => setActiveTab('detalles')}
                className={`py-3 px-4 border-b-2 transition-colors ${
                  activeTab === 'detalles'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                Detalles
              </button>
              <button
                onClick={() => setActiveTab('amortizacion')}
                className={`py-3 px-4 border-b-2 transition-colors ${
                  activeTab === 'amortizacion'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                Tabla de Amortización
              </button>
              <button
                onClick={() => setActiveTab('auditoria')}
                className={`py-3 px-4 border-b-2 transition-colors ${
                  activeTab === 'auditoria'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                Auditoría
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {activeTab === 'detalles' && (
              <div className="space-y-6">
                {/* Estado */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Badge className={getEstadoBadge(prestamoData.estado)}>
                        {getEstadoLabel(prestamoData.estado)}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                </Card>

                {/* Información del Cliente */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <User className="h-5 w-5" />
                      Información del Cliente
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">Cédula</label>
                      <p className="font-medium">{prestamoData.cedula}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Nombres</label>
                      <p className="font-medium">{prestamoData.nombres}</p>
                    </div>
                  </CardContent>
                </Card>

                {/* Información del Préstamo */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <DollarSign className="h-5 w-5" />
                      Información del Préstamo
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">Total de Financiamiento</label>
                      <p className="text-2xl font-bold text-green-600">
                        ${typeof prestamoData.total_financiamiento === 'number'
                          ? prestamoData.total_financiamiento.toFixed(2)
                          : '0.00'}
                      </p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Modalidad de Pago</label>
                      <p className="font-medium">
                        {prestamoData.modalidad_pago === 'MENSUAL' ? 'Mensual' :
                         prestamoData.modalidad_pago === 'QUINCENAL' ? 'Quincenal' :
                         prestamoData.modalidad_pago === 'SEMANAL' ? 'Semanal' :
                         prestamoData.modalidad_pago}
                      </p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Número de Cuotas</label>
                      <p className="text-xl font-semibold">{prestamoData.numero_cuotas}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Cuota por Período</label>
                      <p className="text-xl font-semibold">
                        ${typeof prestamoData.cuota_periodo === 'number'
                          ? prestamoData.cuota_periodo.toFixed(2)
                          : '0.00'}
                      </p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Tasa de Interés</label>
                      <p className="font-medium">
                        {typeof prestamoData.tasa_interes === 'number'
                          ? (prestamoData.tasa_interes * 100).toFixed(2) + '%'
                          : '0.00%'}
                      </p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Fecha de Requerimiento</label>
                      <p className="font-medium">{formatDate(prestamoData.fecha_requerimiento)}</p>
                    </div>
                    {prestamoData.fecha_aprobacion && (
                      <div>
                        <label className="text-sm text-gray-600">Fecha de Aprobación</label>
                        <p className="font-medium">{formatDate(prestamoData.fecha_aprobacion)}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Evaluación de Riesgo - Solo lectura */}
                {evaluacionRiesgo && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <TrendingUp className="h-5 w-5" />
                        Evaluación de Riesgo (Solo Lectura)
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-sm text-gray-600">Puntuación Total</label>
                          <p className="text-2xl font-bold text-blue-600">
                            {evaluacionRiesgo.puntuacion_total?.toFixed(2) || '0.00'} / 100
                          </p>
                        </div>
                        <div>
                          <label className="text-sm text-gray-600">Clasificación de Riesgo</label>
                          <Badge className={
                            evaluacionRiesgo.clasificacion_riesgo === 'A' ? 'bg-green-100 text-green-800 border-green-300' :
                            evaluacionRiesgo.clasificacion_riesgo === 'B' ? 'bg-blue-100 text-blue-800 border-blue-300' :
                            evaluacionRiesgo.clasificacion_riesgo === 'C' ? 'bg-yellow-100 text-yellow-800 border-yellow-300' :
                            evaluacionRiesgo.clasificacion_riesgo === 'D' ? 'bg-orange-100 text-orange-800 border-orange-300' :
                            'bg-red-100 text-red-800 border-red-300'
                          }>
                            {evaluacionRiesgo.clasificacion_riesgo || 'N/A'}
                          </Badge>
                        </div>
                        <div>
                          <label className="text-sm text-gray-600">Decisión Final</label>
                          <p className="font-medium">{evaluacionRiesgo.decision_final || 'N/A'}</p>
                        </div>
                        {evaluacionRiesgo.sugerencias?.plazo_maximo_sugerido && (
                          <div>
                            <label className="text-sm text-gray-600">Plazo Máximo Sugerido</label>
                            <p className="font-medium">{evaluacionRiesgo.sugerencias.plazo_maximo_sugerido} meses</p>
                          </div>
                        )}
                      </div>
                      {evaluacionRiesgo.detalle_criterios && (
                        <div className="mt-4 pt-4 border-t">
                          <h4 className="font-semibold mb-2">Detalle por Criterios:</h4>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>Criterio 1 - Capacidad de Pago: {evaluacionRiesgo.detalle_criterios.ratio_endeudamiento?.puntos || 0} pts</div>
                            <div>Criterio 2 - Estabilidad Laboral: {evaluacionRiesgo.detalle_criterios.antiguedad_trabajo?.puntos || 0} pts</div>
                            <div>Criterio 3 - Referencias: {evaluacionRiesgo.detalle_criterios.referencias?.puntos || 0} pts</div>
                            <div>Criterio 4 - Arraigo Geográfico: {(evaluacionRiesgo.detalle_criterios.arraigo_familiar || 0) + (evaluacionRiesgo.detalle_criterios.arraigo_laboral || 0)} pts</div>
                            <div>Criterio 5 - Perfil Sociodemográfico: {evaluacionRiesgo.detalle_criterios.vivienda?.puntos || 0} pts</div>
                            <div>Criterio 6 - Edad: {evaluacionRiesgo.detalle_criterios.edad?.puntos || 0} pts</div>
                            <div>Criterio 7 - Capacidad de Maniobra: {evaluacionRiesgo.detalle_criterios.enganche_garantias?.puntos || 0} pts</div>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* Predicción de Impago de Cuotas */}
                {(prestamoData.estado === 'APROBADO' || prestamoData.estado === 'DESEMBOLSADO') && (
                  <Card className={prediccionImpago ? getRiesgoColor(prediccionImpago.nivel_riesgo) : ''}>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <TrendingUp className="h-5 w-5" />
                        Predicción de Impago de Cuotas
                        {cargandoPrediccion && (
                          <Loader2 className="h-4 w-4 animate-spin ml-2" />
                        )}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {cargandoPrediccion ? (
                        <div className="text-center py-4">
                          <p className="text-sm text-gray-500">Cargando predicción...</p>
                        </div>
                      ) : prediccionImpago ? (
                        <div className="space-y-4">
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <div className="text-sm text-gray-600 mb-1">Predicción</div>
                              <div className="font-semibold text-lg">{prediccionImpago.prediccion}</div>
                            </div>
                            <div>
                              <div className="text-sm text-gray-600 mb-1">Nivel de Riesgo</div>
                              <Badge className={getRiesgoColor(prediccionImpago.nivel_riesgo)}>
                                {prediccionImpago.nivel_riesgo}
                              </Badge>
                            </div>
                            <div>
                              <div className="text-sm text-gray-600 mb-1">Probabilidad de Impago</div>
                              <div className="font-semibold text-red-600">
                                {(prediccionImpago.probabilidad_impago * 100).toFixed(1)}%
                              </div>
                            </div>
                            <div>
                              <div className="text-sm text-gray-600 mb-1">Probabilidad de Pago</div>
                              <div className="font-semibold text-green-600">
                                {(prediccionImpago.probabilidad_pago * 100).toFixed(1)}%
                              </div>
                            </div>
                          </div>
                          <div className="pt-4 border-t">
                            <div className="flex items-start gap-2">
                              {prediccionImpago.nivel_riesgo === 'Alto' && (
                                <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5" />
                              )}
                              <div>
                                <div className="text-sm font-medium mb-1">Recomendación</div>
                                <div className="text-sm">{prediccionImpago.recomendacion}</div>
                              </div>
                            </div>
                          </div>
                          {prediccionImpago.modelo_usado && (
                            <div className="pt-2 text-xs text-gray-500">
                              Modelo: {prediccionImpago.modelo_usado.nombre} v{prediccionImpago.modelo_usado.version}
                              {' '}({prediccionImpago.modelo_usado.algoritmo})
                              {prediccionImpago.modelo_usado.accuracy && (
                                <> - Accuracy: {(prediccionImpago.modelo_usado.accuracy * 100).toFixed(1)}%</>
                              )}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-center py-4">
                          <p className="text-sm text-gray-500">
                            No hay modelo activo para predecir impago. Entrena un modelo en Configuración â†’ AI â†’ ML Impago.
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* Información de Producto */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Building className="h-5 w-5" />
                      Producto
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">Modelo de Vehículo</label>
                      <p className="font-medium">{prestamoData.producto}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Analista Asignado</label>
                      <p className="font-medium">{prestamoData.analista}</p>
                    </div>
                  </CardContent>
                </Card>

                {/* Usuarios y Auditoría */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Calendar className="h-5 w-5" />
                      Usuarios del Proceso
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <label className="text-sm text-gray-600">Proponente</label>
                      <p className="font-medium">{prestamoData.usuario_proponente}</p>
                      <p className="text-xs text-gray-500">{formatDate(prestamoData.fecha_registro)}</p>
                    </div>
                    {prestamoData.usuario_aprobador && (
                      <div>
                        <label className="text-sm text-gray-600">Aprobador</label>
                        <p className="font-medium">{prestamoData.usuario_aprobador}</p>
                        {prestamoData.fecha_aprobacion && (
                          <p className="text-xs text-gray-500">{formatDate(prestamoData.fecha_aprobacion)}</p>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Observaciones */}
                {prestamoData.observaciones && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Observaciones</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm">{prestamoData.observaciones}</p>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            {activeTab === 'amortizacion' && (
              <TablaAmortizacionPrestamo prestamo={prestamoData} />
            )}

            {activeTab === 'auditoria' && (
              <AuditoriaPrestamo prestamoId={prestamoData.id} />
            )}
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-white border-t p-4 flex justify-end">
            <Button onClick={onClose}>Cerrar</Button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

