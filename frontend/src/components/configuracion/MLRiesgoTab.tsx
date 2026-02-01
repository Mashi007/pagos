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
} from 'lucide-react'
import { Card, CardContent } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Badge } from '../../components/ui/badge'
import { Progress } from '../../components/ui/progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { aiTrainingService, ModeloRiesgo } from '../../services/aiTrainingService'
import { toast } from 'sonner'

export function MLRiesgoTab() {
  const [modelos, setModelos] = useState<ModeloRiesgo[]>([])
  const [modeloActivo, setModeloActivo] = useState<ModeloRiesgo | null>(null)
  const [cargando, setCargando] = useState(false)
  const [entrenando, setEntrenando] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const [estadoJob, setEstadoJob] = useState<{
    status: string
    progreso?: number
    modelo?: ModeloRiesgo
    error?: string
  } | null>(null)

  // Formulario de entrenamiento
  const [mostrarFormEntrenamiento, setMostrarFormEntrenamiento] = useState(false)
  const [algoritmo, setAlgoritmo] = useState('random_forest')
  const [testSize, setTestSize] = useState(0.2)

  // Formulario de predicción
  const [mostrarPrediccion, setMostrarPrediccion] = useState(false)
  const [datosCliente, setDatosCliente] = useState({
    edad: '',
    ingreso: '',
    deuda_total: '',
    ratio_deuda_ingreso: '',
    historial_pagos: '',
    dias_ultimo_prestamo: '',
    numero_prestamos_previos: '',
  })
  const [prediccion, setPrediccion] = useState<any>(null)
  const [prediciendo, setPrediciendo] = useState(false)

  const cargarModelos = async () => {
    setCargando(true)
    try {
      const modelosResponse = await aiTrainingService.listarModelosRiesgo()
      const activoData = await aiTrainingService.getModeloRiesgoActivo().catch(() => null)

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

  // Polling para estado de entrenamiento
  useEffect(() => {
    if (!jobId) return

    const interval = setInterval(async () => {
      try {
        const estado = await aiTrainingService.getEstadoEntrenamientoML(jobId)
        setEstadoJob(estado)

        if (estado.status === 'succeeded' || estado.status === 'failed') {
          clearInterval(interval)
          cargarModelos()
          if (estado.status === 'succeeded') {
            toast.success('Modelo entrenado exitosamente')
          } else {
            toast.error('Error en el entrenamiento del modelo')
          }
        }
      } catch (error) {
        console.error('Error verificando estado:', error)
      }
    }, 5000) // Cada 5 segundos

    return () => clearInterval(interval)
  }, [jobId])

  const handleEntrenar = async () => {
    setEntrenando(true)
    setEstadoJob({ status: 'pending', progreso: 0 })
    setMostrarFormEntrenamiento(false)

    // Simular progreso mientras se entrena
    const intervalProgreso = setInterval(() => {
      setEstadoJob((prev) => {
        if (!prev) return { status: 'pending', progreso: 0 }

        let nuevoProgreso = prev.progreso || 0
        if (nuevoProgreso < 90) {
          nuevoProgreso = Math.min(nuevoProgreso + 1.5, 90)
        } else if (nuevoProgreso < 95) {
          nuevoProgreso = Math.min(nuevoProgreso + 0.5, 95)
        }

        return {
          ...prev,
          progreso: nuevoProgreso,
        }
      })
    }, 500)

    try {
      const result = await aiTrainingService.entrenarModeloRiesgo({
        algoritmo,
        test_size: testSize,
      })

      clearInterval(intervalProgreso)

      setJobId(result.job_id)
      setEstadoJob({
        status: 'pending',
        progreso: 0,
      })

      // El modelo se obtendrá cuando se consulte el estado del job
      toast.success('Entrenamiento iniciado. El modelo se creará cuando el proceso termine.')

      // Recargar modelos después de 2 segundos
      setTimeout(async () => {
        await cargarModelos()
      }, 2000)
    } catch (error: any) {
      clearInterval(intervalProgreso)

      const errorMsg = error?.response?.data?.detail || error?.message || 'Error desconocido'
      setEstadoJob({
        status: 'failed',
        progreso: 0,
        error: errorMsg
      })

      toast.error(`Error al entrenar modelo: ${errorMsg}`, {
        duration: 10000,
      })
    } finally {
      setEntrenando(false)
    }
  }

  const handleActivarModelo = async (modeloId: number) => {
    // Verificar si es el modelo activo (para desactivar)
    const esDesactivacion = modeloActivo && modeloActivo.id === modeloId

    // Confirmar activación/desactivación
    const modelo = modelos.find((m) => m.id === modeloId)
    if (!modelo) {
      toast.error('Modelo no encontrado')
      return
    }

    const mensajeConfirmacion = esDesactivacion
      ? `¿Estás seguro de desactivar el modelo "${modelo.nombre}" v${modelo.version}?\n\n` +
        `No habrá modelo activo después de esto.`
      : `¿Estás seguro de ${modeloActivo ? 'cambiar y ' : ''}activar el modelo "${modelo.nombre}" v${modelo.version}?\n\n` +
        `${modeloActivo ? `Esto desactivará el modelo actual "${modeloActivo.nombre}".\n\n` : ''}` +
        `El modelo estará disponible para predicciones.`

    const confirmar = window.confirm(mensajeConfirmacion)

    if (!confirmar) {
      return
    }

    try {
      const result = await aiTrainingService.activarModeloRiesgo(modeloId)
      toast.success(result.mensaje || (esDesactivacion ? 'Modelo desactivado' : 'Modelo activado exitosamente'))

      // Recargar modelos para actualizar el estado
      await cargarModelos()

      // Si hay un modelo activo previo y se está cambiando, mostrar mensaje
      if (modeloActivo && modeloActivo.id !== modeloId && !esDesactivacion) {
        toast.info(`Modelo anterior "${modeloActivo.nombre}" ha sido desactivado`)
      }
    } catch (error: any) {
      console.error('Error activando modelo:', error)
      const mensajeError =
        error?.response?.data?.detail ||
        error?.message ||
        `Error al ${esDesactivacion ? 'desactivar' : 'activar'} modelo. Verifica que el modelo existe y está disponible.`
      toast.error(mensajeError)
    }
  }

  const handlePredecir = async () => {
    setPrediciendo(true)
    try {
      const datos = {
        edad: datosCliente.edad ? parseInt(datosCliente.edad) : undefined,
        ingreso: datosCliente.ingreso ? parseFloat(datosCliente.ingreso) : undefined,
        deuda_total: datosCliente.deuda_total ? parseFloat(datosCliente.deuda_total) : undefined,
        ratio_deuda_ingreso: datosCliente.ratio_deuda_ingreso
          ? parseFloat(datosCliente.ratio_deuda_ingreso)
          : undefined,
        historial_pagos: datosCliente.historial_pagos
          ? parseFloat(datosCliente.historial_pagos)
          : undefined,
        dias_ultimo_prestamo: datosCliente.dias_ultimo_prestamo
          ? parseInt(datosCliente.dias_ultimo_prestamo)
          : undefined,
        numero_prestamos_previos: datosCliente.numero_prestamos_previos
          ? parseInt(datosCliente.numero_prestamos_previos)
          : undefined,
      }

      const result = await aiTrainingService.predecirRiesgo(datos)
      setPrediccion(result)
    } catch (error: any) {
      toast.error('Error al predecir riesgo')
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
            <Brain className="h-6 w-6" />
            ML - Modelo de Riesgo
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Entrena y usa modelos de machine learning para predecir riesgo crediticio
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
                  {modeloActivo.accuracy
                    ? `${(modeloActivo.accuracy * 100).toFixed(1)}%`
                    : 'N/A'}
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
                Probar Predicción
              </Button>
              {modeloActivo && (
                <Button
                  onClick={() => handleActivarModelo(modeloActivo.id)}
                  variant="outline"
                  size="sm"
                  className="text-amber-600 hover:text-amber-700"
                  title="Desactivar modelo actual"
                >
                  <Zap className="h-4 w-4 mr-2" />
                  Desactivar
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Estado de Entrenamiento */}
      {estadoJob && (
        <Card className={
          estadoJob.status === 'succeeded'
            ? 'border-green-200 bg-green-50/50'
            : estadoJob.status === 'failed'
            ? 'border-red-200 bg-red-50/50'
            : 'border-blue-200 bg-blue-50/50'
        }>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 mb-4">
              {estadoJob.status === 'succeeded' ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : estadoJob.status === 'failed' ? (
                <AlertCircle className="h-5 w-5 text-red-600" />
              ) : (
                <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
              )}
              <h4 className="font-semibold">
                {estadoJob.status === 'succeeded'
                  ? 'Entrenamiento Completado'
                  : estadoJob.status === 'failed'
                  ? 'Error en Entrenamiento'
                  : 'Entrenamiento en Progreso'}
              </h4>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">
                  {estadoJob.status === 'succeeded'
                    ? '¡Modelo entrenado exitosamente!'
                    : estadoJob.status === 'failed'
                    ? 'Error durante el entrenamiento'
                    : 'Procesando y entrenando modelo...'}
                </span>
                {estadoJob.progreso !== undefined && (
                  <span className="font-medium text-blue-600">{Math.round(estadoJob.progreso)}%</span>
                )}
              </div>
              {estadoJob.progreso !== undefined && (
                <Progress value={estadoJob.progreso} className="h-2.5" />
              )}
              {estadoJob.status === 'succeeded' && estadoJob.modelo && (
                <div className="mt-4 p-3 bg-green-50 rounded-lg border border-green-200">
                  <div className="text-sm font-semibold text-green-800 mb-2">Modelo Entrenado:</div>
                  <div className="text-sm text-green-700 space-y-1">
                    <div><span className="font-medium">Nombre:</span> {estadoJob.modelo.nombre}</div>
                    <div><span className="font-medium">Algoritmo:</span> {estadoJob.modelo.algoritmo}</div>
                    {estadoJob.modelo.accuracy && (
                      <div>
                        <span className="font-medium">Accuracy:</span>{' '}
                        {(estadoJob.modelo.accuracy * 100).toFixed(1)}%
                      </div>
                    )}
                  </div>
                </div>
              )}
              {estadoJob.error && (
                <div className="mt-4 p-3 bg-red-50 rounded-lg border border-red-200">
                  <div className="text-sm font-semibold text-red-800 mb-1">Error:</div>
                  <div className="text-sm text-red-700">{estadoJob.error}</div>
                </div>
              )}
              {estadoJob.status === 'succeeded' && (
                <Button
                  onClick={() => setEstadoJob(null)}
                  variant="outline"
                  size="sm"
                  className="mt-2"
                >
                  Cerrar
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Formulario de Entrenamiento */}
      {mostrarFormEntrenamiento && (
        <Card>
          <CardContent className="pt-6">
            <h4 className="font-semibold mb-4">Entrenar Nuevo Modelo</h4>
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
                    <SelectItem value="neural_network">Neural Network</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">
                  Tamaño de Test Set ({testSize * 100}%)
                </label>
                <Input
                  type="number"
                  min="0.1"
                  max="0.5"
                  step="0.05"
                  value={testSize}
                  onChange={(e) => setTestSize(parseFloat(e.target.value) || 0.2)}
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleEntrenar} disabled={entrenando}>
                  {entrenando ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Iniciando...
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-2" />
                      Iniciar Entrenamiento
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setMostrarFormEntrenamiento(false)}
                >
                  Cancelar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Lista de Modelos */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-semibold flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Modelos Disponibles ({modelos.length})
            </h4>
            <Button
              onClick={() => setMostrarFormEntrenamiento(true)}
              disabled={mostrarFormEntrenamiento}
            >
              <Play className="h-4 w-4 mr-2" />
              Entrenar Nuevo Modelo
            </Button>
          </div>

          {cargando ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            </div>
          ) : modelos.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <AlertCircle className="h-12 w-12 mx-auto mb-2 text-gray-400" />
              <p>No hay modelos disponibles</p>
              <p className="text-xs mt-1">Entrena tu primer modelo para comenzar</p>
            </div>
          ) : (
            <div className="space-y-4">
              {modelos.map((modelo) => (
                <div key={modelo.id} className="border rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="font-medium">{modelo.nombre}</span>
                        {modelo.activo && <Badge variant="default">Activo</Badge>}
                        <Badge variant="secondary">v{modelo.version}</Badge>
                      </div>
                      <div className="text-sm text-gray-600 space-y-1">
                        <div>Algoritmo: {modelo.algoritmo}</div>
                        {modelo.accuracy && (
                          <div>Accuracy: {(modelo.accuracy * 100).toFixed(1)}%</div>
                        )}
                        {modelo.total_datos_entrenamiento && (
                          <div>Datos de entrenamiento: {modelo.total_datos_entrenamiento}</div>
                        )}
                        <div className="text-xs text-gray-400">
                          Entrenado: {new Date(modelo.entrenado_en).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    {!modelo.activo ? (
                      <Button
                        size="sm"
                        onClick={() => handleActivarModelo(modelo.id)}
                        variant="default"
                      >
                        <Zap className="h-4 w-4 mr-1" />
                        Activar
                      </Button>
                    ) : (
                      <Badge variant="default" className="bg-green-600">
                        <CheckCircle className="h-3 w-3 mr-1" />
                        Activo
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Formulario de Predicción */}
      {mostrarPrediccion && (
        <Card>
          <CardContent className="pt-6">
            <h4 className="font-semibold mb-4">Probar Predicción de Riesgo</h4>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium mb-2 block">Edad</label>
                <Input
                  type="number"
                  value={datosCliente.edad}
                  onChange={(e) =>
                    setDatosCliente({ ...datosCliente, edad: e.target.value })
                  }
                  placeholder="30"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Ingreso</label>
                <Input
                  type="number"
                  value={datosCliente.ingreso}
                  onChange={(e) =>
                    setDatosCliente({ ...datosCliente, ingreso: e.target.value })
                  }
                  placeholder="50000"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Deuda Total</label>
                <Input
                  type="number"
                  value={datosCliente.deuda_total}
                  onChange={(e) =>
                    setDatosCliente({ ...datosCliente, deuda_total: e.target.value })
                  }
                  placeholder="10000"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Ratio Deuda/Ingreso</label>
                <Input
                  type="number"
                  step="0.01"
                  value={datosCliente.ratio_deuda_ingreso}
                  onChange={(e) =>
                    setDatosCliente({ ...datosCliente, ratio_deuda_ingreso: e.target.value })
                  }
                  placeholder="0.2"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Historial de Pagos (0-1)</label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={datosCliente.historial_pagos}
                  onChange={(e) =>
                    setDatosCliente({ ...datosCliente, historial_pagos: e.target.value })
                  }
                  placeholder="0.95"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Días desde Ãšltimo Préstamo</label>
                <Input
                  type="number"
                  value={datosCliente.dias_ultimo_prestamo}
                  onChange={(e) =>
                    setDatosCliente({ ...datosCliente, dias_ultimo_prestamo: e.target.value })
                  }
                  placeholder="90"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Número de Préstamos Previos</label>
                <Input
                  type="number"
                  value={datosCliente.numero_prestamos_previos}
                  onChange={(e) =>
                    setDatosCliente({
                      ...datosCliente,
                      numero_prestamos_previos: e.target.value,
                    })
                  }
                  placeholder="2"
                />
              </div>
            </div>

            <div className="flex gap-2 mt-4">
              <Button onClick={handlePredecir} disabled={prediciendo}>
                {prediciendo ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Prediciendo...
                  </>
                ) : (
                  <>
                    <BarChart3 className="h-4 w-4 mr-2" />
                    Predecir Riesgo
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setMostrarPrediccion(false)
                  setPrediccion(null)
                }}
              >
                Cerrar
              </Button>
            </div>

            {prediccion && (
              <div className="mt-6 border rounded-lg p-4 bg-gray-50">
                <h5 className="font-semibold mb-3">Resultado de la Predicción</h5>
                <div className="space-y-3">
                  <div>
                    <div className="text-sm text-gray-500 mb-1">Nivel de Riesgo</div>
                    <Badge className={getRiesgoColor(prediccion.risk_level)}>
                      {prediccion.risk_level}
                    </Badge>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500 mb-1">Confianza</div>
                    <div className="font-semibold">
                      {(prediccion.confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500 mb-1">Recomendación</div>
                    <div className="text-sm">{prediccion.recommendation}</div>
                  </div>
                  {prediccion.features_used && (
                    <div>
                      <div className="text-sm text-gray-500 mb-1">Características Usadas</div>
                      <div className="text-xs text-gray-600">
                        {Object.entries(prediccion.features_used)
                          .map(([key, value]) => `${key}: ${value}`)
                          .join(', ')}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

