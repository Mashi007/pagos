import { useState, useEffect } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PlantillasNotificaciones } from '@/components/notificaciones/PlantillasNotificaciones'
import { GeneraVariables } from '@/components/notificaciones/GeneraVariables'
import { ResumenPlantillas } from '@/components/notificaciones/ResumenPlantillas'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { FileText, Settings, Database, CheckCircle, AlertCircle, Zap, Copy, X } from 'lucide-react'
import { NotificacionPlantilla, notificacionService, emailConfigService } from '@/services/notificacionService'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'

export function ConfiguracionNotificaciones() {
  const [activeTab, setActiveTab] = useState('plantillas')
  const [plantillaAEditar, setPlantillaAEditar] = useState<NotificacionPlantilla | null>(null)
  const [plantillasActivas, setPlantillasActivas] = useState<NotificacionPlantilla[]>([])
  const [cargandoPlantillas, setCargandoPlantillas] = useState(false)
  const [configEnvios, setConfigEnvios] = useState<Record<string, { habilitado: boolean, cco: string[] }>>({})
  const [guardandoEnvios, setGuardandoEnvios] = useState(false)

  // Mapeo de tipos a casos
  const mapeoTipos = {
    'PAGO_5_DIAS_ANTES': { caso: '5 días antes', categoria: 'Notificación Previa' },
    'PAGO_3_DIAS_ANTES': { caso: '3 días antes', categoria: 'Notificación Previa' },
    'PAGO_1_DIA_ANTES': { caso: '1 día antes', categoria: 'Notificación Previa' },
    'PAGO_DIA_0': { caso: 'Día de pago', categoria: 'Día de Pago' },
    'PAGO_1_DIA_ATRASADO': { caso: '1 día de retraso', categoria: 'Notificación Retrasada' },
    'PAGO_3_DIAS_ATRASADO': { caso: '3 días de retraso', categoria: 'Notificación Retrasada' },
    'PAGO_5_DIAS_ATRASADO': { caso: '5 días de retraso', categoria: 'Notificación Retrasada' },
    'PREJUDICIAL': { caso: 'Prejudicial', categoria: 'Prejudicial' },
  }

  const tiposOrdenados = [
    'PAGO_5_DIAS_ANTES', 'PAGO_3_DIAS_ANTES', 'PAGO_1_DIA_ANTES',
    'PAGO_DIA_0',
    'PAGO_1_DIA_ATRASADO', 'PAGO_3_DIAS_ATRASADO', 'PAGO_5_DIAS_ATRASADO',
    'PREJUDICIAL'
  ]

  useEffect(() => {
    cargarPlantillasActivas()
    cargarConfiguracionEnvios()
  }, [])

  const cargarConfiguracionEnvios = async () => {
    try {
      const data = await emailConfigService.obtenerConfiguracionEnvios()
      setConfigEnvios(data || {})
    } catch (error) {
      console.error('Error cargando configuración de envíos:', error)
    }
  }

  const toggleEnvio = (tipo: string) => {
    setConfigEnvios(prev => {
      const actual = prev[tipo] || { habilitado: true, cco: [] }
      return {
        ...prev,
        [tipo]: {
          ...actual,
          habilitado: !actual.habilitado
        }
      }
    })
  }

  const actualizarCCO = (tipo: string, index: number, email: string) => {
    setConfigEnvios(prev => {
      const actual = prev[tipo] || { habilitado: true, cco: [] }
      const nuevosCCO = [...actual.cco]
      if (index < nuevosCCO.length) {
        nuevosCCO[index] = email
      } else {
        nuevosCCO.push(email)
      }
      // Limitar a 3 correos máximo
      return {
        ...prev,
        [tipo]: {
          ...actual,
          cco: nuevosCCO.slice(0, 3)
        }
      }
    })
  }

  const eliminarCCO = (tipo: string, index: number) => {
    setConfigEnvios(prev => {
      const actual = prev[tipo] || { habilitado: true, cco: [] }
      const nuevosCCO = actual.cco.filter((_, i) => i !== index)
      return {
        ...prev,
        [tipo]: {
          ...actual,
          cco: nuevosCCO
        }
      }
    })
  }

  const guardarConfiguracionEnvios = async () => {
    try {
      setGuardandoEnvios(true)
      await emailConfigService.actualizarConfiguracionEnvios(configEnvios)
      toast.success('Configuración de envíos guardada exitosamente')
    } catch (error) {
      console.error('Error guardando configuración de envíos:', error)
      toast.error('Error guardando configuración de envíos')
    } finally {
      setGuardandoEnvios(false)
    }
  }

  const cargarPlantillasActivas = async () => {
    setCargandoPlantillas(true)
    try {
      const data = await notificacionService.listarPlantillas(undefined, true) // Solo activas
      setPlantillasActivas(data || [])
    } catch (error) {
      console.error('Error cargando plantillas activas:', error)
    } finally {
      setCargandoPlantillas(false)
    }
  }

  // Obtener plantilla activa por tipo
  const obtenerPlantillaPorTipo = (tipo: string) => {
    return plantillasActivas.find(p => p.tipo === tipo)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-blue-600" />
            Configuración de Notificaciones
          </CardTitle>
          <CardDescription>
            Gestiona las plantillas de notificaciones y la configuración de email para enviar correos a los clientes.
            Las plantillas permiten personalizar los mensajes usando variables como {'{{nombre}}'}, {'{{monto}}'}, {'{{fecha_vencimiento}}'}, etc.
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Control de Envíos por Pestaña */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-blue-600" />
            Control de Envíos Automáticos
          </CardTitle>
          <CardDescription>
            Habilita o deshabilita el envío automático de correos para cada tipo de notificación (se ejecutan a las 4 AM diariamente)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Notificación Previa */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Notificación Previa</h3>
              <div className="grid grid-cols-1 gap-4">
                {['PAGO_5_DIAS_ANTES', 'PAGO_3_DIAS_ANTES', 'PAGO_1_DIA_ANTES'].map(tipo => {
                  const mapeo = mapeoTipos[tipo as keyof typeof mapeoTipos]
                  const config = configEnvios[tipo] || { habilitado: true, cco: [] }
                  const habilitado = config.habilitado
                  const ccoList = config.cco || []
                  return (
                    <div key={tipo} className="border rounded-lg p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="text-sm font-medium text-gray-700">{mapeo?.caso || tipo}</div>
                          <div className="text-xs text-gray-500">{mapeo?.categoria || 'Sin categoría'}</div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`text-xs ${!habilitado ? 'text-gray-900' : 'text-gray-500'}`}>OFF</span>
                          <button
                            type="button"
                            onClick={() => toggleEnvio(tipo)}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                              habilitado ? 'bg-blue-600' : 'bg-gray-200'
                            }`}
                          >
                            <span
                              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                habilitado ? 'translate-x-6' : 'translate-x-1'
                              }`}
                            />
                          </button>
                          <span className={`text-xs ${habilitado ? 'text-gray-900' : 'text-gray-500'}`}>ON</span>
                        </div>
                      </div>
                      
                      {/* CCO */}
                      <div className="border-t pt-3">
                        <div className="flex items-center gap-2 mb-2">
                          <Copy className="h-4 w-4 text-gray-500" />
                          <label className="text-xs font-medium text-gray-700">Correos en CCO (hasta 3):</label>
                        </div>
                        <div className="space-y-2">
                          {[0, 1, 2].map(index => (
                            <div key={index} className="flex items-center gap-2">
                              <Input
                                type="email"
                                placeholder={`CCO ${index + 1} (opcional)`}
                                value={ccoList[index] || ''}
                                onChange={(e) => actualizarCCO(tipo, index, e.target.value)}
                                className="flex-1 text-sm"
                                disabled={!habilitado}
                              />
                              {ccoList[index] && (
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => eliminarCCO(tipo, index)}
                                  className="h-8 w-8 p-0"
                                  disabled={!habilitado}
                                >
                                  <X className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Día de Pago */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Día de Pago</h3>
              <div className="grid grid-cols-1 gap-4">
                {['PAGO_DIA_0'].map(tipo => {
                  const mapeo = mapeoTipos[tipo as keyof typeof mapeoTipos]
                  const config = configEnvios[tipo] || { habilitado: true, cco: [] }
                  const habilitado = config.habilitado
                  const ccoList = config.cco || []
                  return (
                    <div key={tipo} className="border rounded-lg p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="text-sm font-medium text-gray-700">{mapeo?.caso || tipo}</div>
                          <div className="text-xs text-gray-500">{mapeo?.categoria || 'Sin categoría'}</div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`text-xs ${!habilitado ? 'text-gray-900' : 'text-gray-500'}`}>OFF</span>
                          <button
                            type="button"
                            onClick={() => toggleEnvio(tipo)}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                              habilitado ? 'bg-blue-600' : 'bg-gray-200'
                            }`}
                          >
                            <span
                              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                habilitado ? 'translate-x-6' : 'translate-x-1'
                              }`}
                            />
                          </button>
                          <span className={`text-xs ${habilitado ? 'text-gray-900' : 'text-gray-500'}`}>ON</span>
                        </div>
                      </div>
                      
                      {/* CCO */}
                      <div className="border-t pt-3">
                        <div className="flex items-center gap-2 mb-2">
                          <Copy className="h-4 w-4 text-gray-500" />
                          <label className="text-xs font-medium text-gray-700">Correos en CCO (hasta 3):</label>
                        </div>
                        <div className="space-y-2">
                          {[0, 1, 2].map(index => (
                            <div key={index} className="flex items-center gap-2">
                              <Input
                                type="email"
                                placeholder={`CCO ${index + 1} (opcional)`}
                                value={ccoList[index] || ''}
                                onChange={(e) => actualizarCCO(tipo, index, e.target.value)}
                                className="flex-1 text-sm"
                                disabled={!habilitado}
                              />
                              {ccoList[index] && (
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => eliminarCCO(tipo, index)}
                                  className="h-8 w-8 p-0"
                                  disabled={!habilitado}
                                >
                                  <X className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Pago Retrasado */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Pago Retrasado</h3>
              <div className="grid grid-cols-1 gap-4">
                {['PAGO_1_DIA_ATRASADO', 'PAGO_3_DIAS_ATRASADO', 'PAGO_5_DIAS_ATRASADO'].map(tipo => {
                  const mapeo = mapeoTipos[tipo as keyof typeof mapeoTipos]
                  const config = configEnvios[tipo] || { habilitado: true, cco: [] }
                  const habilitado = config.habilitado
                  const ccoList = config.cco || []
                  return (
                    <div key={tipo} className="border rounded-lg p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="text-sm font-medium text-gray-700">{mapeo?.caso || tipo}</div>
                          <div className="text-xs text-gray-500">{mapeo?.categoria || 'Sin categoría'}</div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`text-xs ${!habilitado ? 'text-gray-900' : 'text-gray-500'}`}>OFF</span>
                          <button
                            type="button"
                            onClick={() => toggleEnvio(tipo)}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                              habilitado ? 'bg-blue-600' : 'bg-gray-200'
                            }`}
                          >
                            <span
                              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                habilitado ? 'translate-x-6' : 'translate-x-1'
                              }`}
                            />
                          </button>
                          <span className={`text-xs ${habilitado ? 'text-gray-900' : 'text-gray-500'}`}>ON</span>
                        </div>
                      </div>
                      
                      {/* CCO */}
                      <div className="border-t pt-3">
                        <div className="flex items-center gap-2 mb-2">
                          <Copy className="h-4 w-4 text-gray-500" />
                          <label className="text-xs font-medium text-gray-700">Correos en CCO (hasta 3):</label>
                        </div>
                        <div className="space-y-2">
                          {[0, 1, 2].map(index => (
                            <div key={index} className="flex items-center gap-2">
                              <Input
                                type="email"
                                placeholder={`CCO ${index + 1} (opcional)`}
                                value={ccoList[index] || ''}
                                onChange={(e) => actualizarCCO(tipo, index, e.target.value)}
                                className="flex-1 text-sm"
                                disabled={!habilitado}
                              />
                              {ccoList[index] && (
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => eliminarCCO(tipo, index)}
                                  className="h-8 w-8 p-0"
                                  disabled={!habilitado}
                                >
                                  <X className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Prejudicial */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Prejudicial</h3>
              <div className="grid grid-cols-1 gap-4">
                {['PREJUDICIAL'].map(tipo => {
                  const mapeo = mapeoTipos[tipo as keyof typeof mapeoTipos]
                  const config = configEnvios[tipo] || { habilitado: true, cco: [] }
                  const habilitado = config.habilitado
                  const ccoList = config.cco || []
                  return (
                    <div key={tipo} className="border rounded-lg p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="text-sm font-medium text-gray-700">{mapeo?.caso || tipo}</div>
                          <div className="text-xs text-gray-500">{mapeo?.categoria || 'Sin categoría'}</div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`text-xs ${!habilitado ? 'text-gray-900' : 'text-gray-500'}`}>OFF</span>
                          <button
                            type="button"
                            onClick={() => toggleEnvio(tipo)}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                              habilitado ? 'bg-blue-600' : 'bg-gray-200'
                            }`}
                          >
                            <span
                              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                habilitado ? 'translate-x-6' : 'translate-x-1'
                              }`}
                            />
                          </button>
                          <span className={`text-xs ${habilitado ? 'text-gray-900' : 'text-gray-500'}`}>ON</span>
                        </div>
                      </div>
                      
                      {/* CCO */}
                      <div className="border-t pt-3">
                        <div className="flex items-center gap-2 mb-2">
                          <Copy className="h-4 w-4 text-gray-500" />
                          <label className="text-xs font-medium text-gray-700">Correos en CCO (hasta 3):</label>
                        </div>
                        <div className="space-y-2">
                          {[0, 1, 2].map(index => (
                            <div key={index} className="flex items-center gap-2">
                              <Input
                                type="email"
                                placeholder={`CCO ${index + 1} (opcional)`}
                                value={ccoList[index] || ''}
                                onChange={(e) => actualizarCCO(tipo, index, e.target.value)}
                                className="flex-1 text-sm"
                                disabled={!habilitado}
                              />
                              {ccoList[index] && (
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => eliminarCCO(tipo, index)}
                                  className="h-8 w-8 p-0"
                                  disabled={!habilitado}
                                >
                                  <X className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Botón Guardar */}
            <div className="flex justify-end pt-4 border-t">
              <Button
                onClick={guardarConfiguracionEnvios}
                disabled={guardandoEnvios}
                className="flex items-center gap-2"
              >
                <Settings className="h-4 w-4" />
                {guardandoEnvios ? 'Guardando...' : 'Guardar Configuración de Envíos'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Plantillas Preseleccionadas por Caso */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-600" />
            Plantillas Preseleccionadas por Caso
          </CardTitle>
          <CardDescription>
            Plantillas activas configuradas en Herramientas/Plantillas para cada tipo de notificación
          </CardDescription>
        </CardHeader>
        <CardContent>
          {cargandoPlantillas ? (
            <div className="text-center py-4 text-gray-500">Cargando plantillas...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {tiposOrdenados.map(tipo => {
                const plantilla = obtenerPlantillaPorTipo(tipo)
                const mapeo = mapeoTipos[tipo as keyof typeof mapeoTipos]
                
                return (
                  <div
                    key={tipo}
                    className={`border rounded-lg p-4 ${
                      plantilla ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <div className="text-sm font-semibold text-gray-700 mb-1">
                          {mapeo?.caso || tipo}
                        </div>
                        <div className="text-xs text-gray-500 mb-2">
                          {mapeo?.categoria || 'Sin categoría'}
                        </div>
                      </div>
                      {plantilla ? (
                        <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
                      ) : (
                        <AlertCircle className="h-5 w-5 text-gray-400 flex-shrink-0" />
                      )}
                    </div>
                    
                    {plantilla ? (
                      <div className="space-y-1">
                        <div className="text-xs font-medium text-gray-700 truncate" title={plantilla.nombre}>
                          {plantilla.nombre}
                        </div>
                        <div className="text-xs text-gray-600 truncate" title={plantilla.asunto}>
                          {plantilla.asunto || 'Sin asunto'}
                        </div>
                        <Badge variant="success" className="text-xs mt-2">
                          Activa
                        </Badge>
                      </div>
                    ) : (
                      <div className="text-xs text-gray-500 italic">
                        Sin plantilla configurada
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tabs para Email, Plantillas, Variables y Resumen */}
      <Tabs 
        value={activeTab} 
        onValueChange={(value) => {
          setActiveTab(value)
          // Si cambiamos a plantillas y hay una plantilla para editar, cargarla
          if (value === 'plantillas' && plantillaAEditar) {
            // La plantilla se pasará al componente PlantillasNotificaciones
          }
        }} 
        className="space-y-4"
      >
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="plantillas" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Plantillas
          </TabsTrigger>
          <TabsTrigger value="variables" className="flex items-center gap-2">
            <Database className="h-4 w-4" />
            Genera Variables
          </TabsTrigger>
          <TabsTrigger value="resumen" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Resumen
          </TabsTrigger>
        </TabsList>

        <TabsContent value="plantillas" className="space-y-4">
          <PlantillasNotificaciones 
            plantillaInicial={plantillaAEditar}
            onPlantillaCargada={() => setPlantillaAEditar(null)}
          />
        </TabsContent>

        <TabsContent value="variables" className="space-y-4">
          <GeneraVariables />
        </TabsContent>

        <TabsContent value="resumen" className="space-y-4">
          <ResumenPlantillas 
            onEditarPlantilla={(plantilla) => {
              setPlantillaAEditar(plantilla)
              setActiveTab('plantillas')
            }}
            onCambiarPestaña={(pestaña) => setActiveTab(pestaña)}
          />
        </TabsContent>
      </Tabs>
      
      {/* Recargar plantillas cuando se cambie de pestaña */}
      {activeTab === 'plantillas' && (
        <div className="text-xs text-gray-500 text-center">
          💡 Tip: Las plantillas activas se muestran arriba. Ve a la pestaña "Plantillas" para crear o editar plantillas.
        </div>
      )}
    </div>
  )
}

