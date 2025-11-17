import { useState, useEffect } from 'react'
import {
  Brain,
  Play,
  CheckCircle,
  AlertCircle,
  Loader2,
  TrendingUp,
  BarChart3,
  RefreshCw,
  Zap,
  Shield,
  DollarSign,
  Calendar,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { aiTrainingService, ModeloImpagoCuotas } from '@/services/aiTrainingService'
import { toast } from 'sonner'

interface EstadoEntrenamiento {
  estado: 'iniciando' | 'procesando' | 'entrenando' | 'finalizando' | 'completado' | 'error'
  progreso: number
  mensaje: string
  modelo?: ModeloImpagoCuotas
  error?: string
}

export function MLImpagoCuotasTab() {
  const [modelos, setModelos] = useState<ModeloImpagoCuotas[]>([])
  const [modeloActivo, setModeloActivo] = useState<ModeloImpagoCuotas | null>(null)
  const [cargando, setCargando] = useState(false)
  const [entrenando, setEntrenando] = useState(false)
  const [estadoEntrenamiento, setEstadoEntrenamiento] = useState<EstadoEntrenamiento | null>(null)

  // Formulario de entrenamiento
  const [mostrarFormEntrenamiento, setMostrarFormEntrenamiento] = useState(false)
  const [algoritmo, setAlgoritmo] = useState('random_forest')
  const [testSize, setTestSize] = useState(0.2)

  // Formulario de predicción
  const [mostrarPrediccion, setMostrarPrediccion] = useState(false)
  const [prestamoId, setPrestamoId] = useState('')
  const [prediccion, setPrediccion] = useState<any>(null)
  const [prediciendo, setPrediciendo] = useState(false)

  const cargarModelos = async () => {
    setCargando(true)
    try {
      const modelosResponse = await aiTrainingService.listarModelosImpago()
      const activoData = await aiTrainingService.getModeloImpagoActivo().catch(() => null)
      
      // Manejar respuesta que puede ser array o objeto con error
      if (Array.isArray(modelosResponse)) {
        setModelos(modelosResponse)
      } else {
        setModelos(modelosResponse.modelos || [])
        if (modelosResponse.error) {
          toast.warning(modelosResponse.error)
        }
      }
      setModeloActivo(activoData)
    } catch (error: any) {
      console.error('Error cargando modelos:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error al cargar modelos'
      toast.error(mensajeError)
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    cargarModelos()
  }, [])

  const handleEntrenar = async () => {
    setEntrenando(true)
    setEstadoEntrenamiento({
      estado: 'iniciando',
      progreso: 0,
      mensaje: 'Iniciando entrenamiento...',
    })
    setMostrarFormEntrenamiento(false)

    // Simular progreso mientras se entrena (el backend no devuelve progreso real)
    const intervalProgreso = setInterval(() => {
      setEstadoEntrenamiento((prev) => {
        if (!prev) return null
        
        let nuevoProgreso = prev.progreso
        let nuevoEstado = prev.estado
        let nuevoMensaje = prev.mensaje

        // Simular progreso basado en el estado
        if (prev.estado === 'iniciando' && prev.progreso < 10) {
          nuevoProgreso = Math.min(prev.progreso + 2, 10)
          nuevoMensaje = 'Preparando datos de entrenamiento...'
        } else if (prev.estado === 'iniciando' && prev.progreso >= 10) {
          nuevoEstado = 'procesando'
          nuevoMensaje = 'Procesando préstamos y extrayendo features...'
        } else if (prev.estado === 'procesando' && prev.progreso < 60) {
          nuevoProgreso = Math.min(prev.progreso + 1.5, 60)
          nuevoMensaje = `Procesando datos... ${Math.round(prev.progreso)}%`
        } else if (prev.estado === 'procesando' && prev.progreso >= 60) {
          nuevoEstado = 'entrenando'
          nuevoMensaje = 'Entrenando modelo con algoritmo seleccionado...'
        } else if (prev.estado === 'entrenando' && prev.progreso < 90) {
          nuevoProgreso = Math.min(prev.progreso + 0.8, 90)
          nuevoMensaje = `Entrenando modelo... ${Math.round(prev.progreso)}%`
        } else if (prev.estado === 'entrenando' && prev.progreso >= 90) {
          nuevoEstado = 'finalizando'
          nuevoMensaje = 'Finalizando y guardando modelo...'
          nuevoProgreso = 95
        }

        return {
          ...prev,
          estado: nuevoEstado,
          progreso: nuevoProgreso,
          mensaje: nuevoMensaje,
        }
      })
    }, 500) // Actualizar cada 500ms

    try {
      const resultado = await aiTrainingService.entrenarModeloImpago({
        algoritmo,
        test_size: testSize,
      })
      
      // Limpiar intervalo y mostrar éxito
      clearInterval(intervalProgreso)
      
      setEstadoEntrenamiento({
        estado: 'completado',
        progreso: 100,
        mensaje: '¡Modelo entrenado exitosamente!',
        modelo: resultado.modelo,
      })

      // Notificación mejorada con métricas
      const metricas = resultado.metricas
      const accuracy = metricas?.accuracy ? `${(metricas.accuracy * 100).toFixed(1)}%` : 'N/A'
      const f1 = metricas?.f1_score ? `${(metricas.f1_score * 100).toFixed(1)}%` : 'N/A'
      
      toast.success(
        `Modelo entrenado exitosamente\n` +
        `Accuracy: ${accuracy} | F1 Score: ${f1}`,
        {
          duration: 8000,
          description: `Modelo: ${resultado.modelo.nombre}`,
        }
      )

      // Recargar modelos después de 2 segundos
      setTimeout(async () => {
        await cargarModelos()
        setEstadoEntrenamiento(null)
      }, 2000)

      console.log('✅ Modelo entrenado exitosamente:', resultado)
    } catch (error: any) {
      // Limpiar intervalo en caso de error
      clearInterval(intervalProgreso)
      
      setEstadoEntrenamiento({
        estado: 'error',
        progreso: 0,
        mensaje: 'Error durante el entrenamiento',
        error: error?.response?.data?.detail || error?.message || 'Error desconocido',
      })
      console.group('❌ Error entrenando modelo ML Impago')
      console.error('Error objeto completo:', error)
      console.error('Error response:', error?.response)
      console.error('Error response data:', error?.response?.data)
      console.error('Error response status:', error?.response?.status)
      console.error('Error response headers:', error?.response?.headers)
      
      // Expandir el objeto de error para ver todos los detalles
      if (error?.response?.data) {
        console.error('📋 Detalles del error del servidor:', JSON.stringify(error.response.data, null, 2))
      }
      console.groupEnd()
      
      // Extraer mensaje de error de diferentes posibles ubicaciones
      let mensajeError = 'Error al entrenar modelo'
      
      // Detectar timeout específicamente
      if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
        mensajeError = 'El entrenamiento está tardando más de lo esperado. El proceso continúa en el servidor. Por favor, espera unos minutos y recarga la página para ver el modelo entrenado.'
      } else if (error?.response?.data?.detail) {
        mensajeError = String(error.response.data.detail)
      } else if (error?.response?.data?.message) {
        mensajeError = String(error.response.data.message)
      } else if (error?.message) {
        mensajeError = String(error.message)
      } else if (error?.error?.detail) {
        mensajeError = String(error.error.detail)
      }
      
      console.error('📝 Mensaje de error extraído para mostrar al usuario:', mensajeError)
      
      // Mostrar toast con el mensaje completo
      toast.error(`Error entrenando modelo: ${mensajeError}`, {
        duration: 15000, // 15 segundos para mensajes de timeout
      })
    } finally {
      setEntrenando(false)
    }
  }

  const handleActivarModelo = async (modeloId: number) => {
    const esDesactivacion = modeloActivo && modeloActivo.id === modeloId
    const modelo = modelos.find((m) => m.id === modeloId)
    if (!modelo) {
      toast.error('Modelo no encontrado')
      return
    }

    const mensajeConfirmacion = esDesactivacion
      ? `¿Estás seguro de desactivar el modelo "${modelo.nombre}" v${modelo.version}?`
      : `¿Estás seguro de ${modeloActivo ? 'cambiar y ' : ''}activar el modelo "${modelo.nombre}" v${modelo.version}?`

    if (!window.confirm(mensajeConfirmacion)) {
      return
    }

    try {
      console.log('🔄 Activando modelo ML Impago:', modeloId)
      const resultado = await aiTrainingService.activarModeloImpago(modeloId)
      console.log('✅ Modelo activado exitosamente:', resultado)
      toast.success(esDesactivacion ? 'Modelo desactivado' : 'Modelo activado exitosamente')
      await cargarModelos()
    } catch (error: any) {
      console.error('❌ Error activando modelo ML Impago:', error)
      console.error('Error completo:', JSON.stringify(error, null, 2))
      const mensajeError = error?.response?.data?.detail || error?.message || error?.error?.detail || 'Error al activar modelo'
      toast.error(mensajeError)
    }
  }

  const handlePredecir = async () => {
    if (!prestamoId) {
      toast.error('Ingresa un ID de préstamo')
      return
    }

    setPrediciendo(true)
    try {
      const result = await aiTrainingService.predecirImpago(parseInt(prestamoId))
      setPrediccion(result)
    } catch (error: any) {
      const mensajeError = error?.response?.data?.detail || 'Error al predecir impago'
      toast.error(mensajeError)
    } finally {
      setPrediciendo(false)
    }
  }

  const getRiesgoColor = (nivel: string) => {
    const colores: Record<string, string> = {
      Bajo: 'text-green-600 bg-green-50',
      Medio: 'text-yellow-600 bg-yellow-50',
      Alto: 'text-red-600 bg-red-50',
      Desconocido: 'text-gray-600 bg-gray-50',
      Error: 'text-red-600 bg-red-50',
    }
    return colores[nivel] || colores.Desconocido
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold flex items-center gap-2">
            <DollarSign className="h-6 w-6" />
            ML - Predicción de Impago de Cuotas
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Entrena y usa modelos de machine learning para predecir si un cliente pagará sus cuotas futuras
          </p>
        </div>
        <Button onClick={cargarModelos} variant="outline" size="sm" disabled={cargando}>
          {cargando ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Actualizando...
            </>
          ) : (
            <>
              <RefreshCw className="h-4 w-4 mr-2" />
              Actualizar
            </>
          )}
        </Button>
      </div>

      {/* Modelo Activo */}
      {modeloActivo && (
        <Card className="border-green-200 bg-green-50/50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 mb-4">
              <Shield className="h-5 w-5 text-green-600" />
              <h4 className="font-semibold">Modelo Activo</h4>
              <Badge variant="default" className="bg-green-600">
                <CheckCircle className="h-3 w-3 mr-1" />
                Activo
              </Badge>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div>
                <div className="text-sm text-gray-500 mb-1">Nombre</div>
                <div className="font-semibold">{modeloActivo.nombre}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500 mb-1">Versión</div>
                <div className="font-semibold">{modeloActivo.version}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500 mb-1">Algoritmo</div>
                <div className="font-semibold">{modeloActivo.algoritmo}</div>
              </div>
              <div>
                <div className="text-sm text-gray-500 mb-1">Accuracy</div>
                <div className="font-semibold text-blue-600">
                  {modeloActivo.accuracy ? `${(modeloActivo.accuracy * 100).toFixed(1)}%` : 'N/A'}
                </div>
              </div>
            </div>
            {modeloActivo.precision && modeloActivo.recall && (
              <div className="grid gap-4 md:grid-cols-3 mt-4 pt-4 border-t">
                <div>
                  <div className="text-sm text-gray-500 mb-1">Precision</div>
                  <div className="font-semibold">
                    {modeloActivo.precision ? (modeloActivo.precision * 100).toFixed(1) : 'N/A'}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 mb-1">Recall</div>
                  <div className="font-semibold">
                    {modeloActivo.recall ? (modeloActivo.recall * 100).toFixed(1) : 'N/A'}%
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-500 mb-1">F1 Score</div>
                  <div className="font-semibold">
                    {modeloActivo.f1_score ? (modeloActivo.f1_score * 100).toFixed(1) : 'N/A'}%
                  </div>
                </div>
              </div>
            )}
            <div className="mt-4 flex gap-2">
              <Button onClick={() => setMostrarPrediccion(true)} variant="outline" size="sm">
                <BarChart3 className="h-4 w-4 mr-2" />
                Predecir Impago
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sin Modelo Activo */}
      {!modeloActivo && (
        <Card className="border-amber-200 bg-amber-50/50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="h-5 w-5 text-amber-600" />
              <h4 className="font-semibold">No hay modelo activo</h4>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Entrena un modelo y actívalo para comenzar a predecir impago de cuotas.
            </p>
            <Button onClick={() => setMostrarFormEntrenamiento(true)} variant="outline" size="sm">
              <Play className="h-4 w-4 mr-2" />
              Entrenar Modelo
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Formulario de Entrenamiento */}
      {mostrarFormEntrenamiento && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-semibold">Entrenar Nuevo Modelo</h4>
              <Button variant="ghost" size="sm" onClick={() => setMostrarFormEntrenamiento(false)}>
                ✕
              </Button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Algoritmo</label>
                <Select value={algoritmo} onValueChange={setAlgoritmo}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="random_forest">Random Forest</SelectItem>
                    <SelectItem value="xgboost">XGBoost</SelectItem>
                    <SelectItem value="logistic_regression">Logistic Regression</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Test Size (0.1 - 0.5)</label>
                <Input
                  type="number"
                  min="0.1"
                  max="0.5"
                  step="0.1"
                  value={testSize}
                  onChange={(e) => setTestSize(parseFloat(e.target.value) || 0.2)}
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleEntrenar} disabled={entrenando}>
                  {entrenando ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Entrenando...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      Entrenar Modelo
                    </>
                  )}
                </Button>
                <Button variant="outline" onClick={() => setMostrarFormEntrenamiento(false)}>
                  Cancelar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Formulario de Predicción */}
      {mostrarPrediccion && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-semibold">Predecir Impago de Cuotas</h4>
              <Button variant="ghost" size="sm" onClick={() => setMostrarPrediccion(false)}>
                ✕
              </Button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block">ID del Préstamo</label>
                <Input
                  type="number"
                  placeholder="Ej: 123"
                  value={prestamoId}
                  onChange={(e) => setPrestamoId(e.target.value)}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Ingresa el ID del préstamo para predecir si el cliente pagará sus cuotas futuras
                </p>
              </div>
              <div className="flex gap-2">
                <Button onClick={handlePredecir} disabled={prediciendo || !prestamoId}>
                  {prediciendo ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Prediciendo...
                    </>
                  ) : (
                    <>
                      <BarChart3 className="h-4 w-4 mr-2" />
                      Predecir
                    </>
                  )}
                </Button>
                <Button variant="outline" onClick={() => setMostrarPrediccion(false)}>
                  Cancelar
                </Button>
              </div>

              {/* Resultado de Predicción */}
              {prediccion && (
                <Card className="mt-4 border-blue-200 bg-blue-50/50">
                  <CardContent className="pt-6">
                    <h5 className="font-semibold mb-4 flex items-center gap-2">
                      <TrendingUp className="h-5 w-5" />
                      Resultado de la Predicción
                    </h5>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <div className="text-sm text-gray-500 mb-1">Predicción</div>
                        <div className="font-semibold text-lg">{prediccion.prediccion}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500 mb-1">Nivel de Riesgo</div>
                        <Badge className={getRiesgoColor(prediccion.nivel_riesgo)}>
                          {prediccion.nivel_riesgo}
                        </Badge>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500 mb-1">Probabilidad de Impago</div>
                        <div className="font-semibold text-red-600">
                          {(prediccion.probabilidad_impago * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500 mb-1">Probabilidad de Pago</div>
                        <div className="font-semibold text-green-600">
                          {(prediccion.probabilidad_pago * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500 mb-1">Confianza</div>
                        <div className="font-semibold">{(prediccion.confidence * 100).toFixed(1)}%</div>
                      </div>
                    </div>
                    <div className="mt-4 pt-4 border-t">
                      <div className="text-sm text-gray-500 mb-1">Recomendación</div>
                      <div className="text-sm">{prediccion.recomendacion}</div>
                    </div>
                    {prediccion.modelo_usado && (
                      <div className="mt-4 pt-4 border-t">
                        <div className="text-xs text-gray-500">
                          Modelo: {prediccion.modelo_usado.nombre} v{prediccion.modelo_usado.version} (
                          {prediccion.modelo_usado.algoritmo}) - Accuracy:{' '}
                          {prediccion.modelo_usado.accuracy
                            ? `${(prediccion.modelo_usado.accuracy * 100).toFixed(1)}%`
                            : 'N/A'}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Lista de Modelos */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold">Modelos Entrenados</h4>
            <Button onClick={() => setMostrarFormEntrenamiento(true)} variant="outline" size="sm">
              <Play className="h-4 w-4 mr-2" />
              Entrenar Nuevo
            </Button>
          </div>
          {cargando ? (
            <div className="text-center py-8">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-gray-400" />
              <p className="text-sm text-gray-500 mt-2">Cargando modelos...</p>
            </div>
          ) : modelos.length === 0 ? (
            <div className="text-center py-8">
              <Brain className="h-12 w-12 mx-auto text-gray-400 mb-2" />
              <p className="text-sm text-gray-500">No hay modelos entrenados aún</p>
              <Button
                onClick={() => setMostrarFormEntrenamiento(true)}
                variant="outline"
                size="sm"
                className="mt-4"
              >
                <Play className="h-4 w-4 mr-2" />
                Entrenar Primer Modelo
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {modelos.map((modelo) => (
                <Card
                  key={modelo.id}
                  className={modelo.activo ? 'border-green-200 bg-green-50/30' : ''}
                >
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <h5 className="font-semibold">{modelo.nombre}</h5>
                          {modelo.activo && (
                            <Badge variant="default" className="bg-green-600">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Activo
                            </Badge>
                          )}
                        </div>
                        <div className="grid gap-2 md:grid-cols-4 text-sm">
                          <div>
                            <span className="text-gray-500">Versión:</span> {modelo.version}
                          </div>
                          <div>
                            <span className="text-gray-500">Algoritmo:</span> {modelo.algoritmo}
                          </div>
                          <div>
                            <span className="text-gray-500">Accuracy:</span>{' '}
                            {modelo.accuracy ? `${(modelo.accuracy * 100).toFixed(1)}%` : 'N/A'}
                          </div>
                          <div>
                            <span className="text-gray-500">Entrenado:</span>{' '}
                            {new Date(modelo.entrenado_en).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {!modelo.activo && (
                          <Button
                            onClick={() => handleActivarModelo(modelo.id)}
                            variant="outline"
                            size="sm"
                          >
                            <Zap className="h-4 w-4 mr-1" />
                            Activar
                          </Button>
                        )}
                        {modelo.activo && (
                          <Button
                            onClick={() => handleActivarModelo(modelo.id)}
                            variant="outline"
                            size="sm"
                            className="text-amber-600 hover:text-amber-700"
                          >
                            Desactivar
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

