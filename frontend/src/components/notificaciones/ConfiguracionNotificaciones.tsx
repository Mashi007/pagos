import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Settings, Zap, Copy, X, Bell, Calendar, AlertTriangle, Shield, ChevronUp, ChevronDown } from 'lucide-react'
import { emailConfigService } from '@/services/notificacionService'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'

export function ConfiguracionNotificaciones() {
  console.log('🔄 [ConfiguracionNotificaciones] Componente renderizado')

  const [configEnvios, setConfigEnvios] = useState<Record<string, { habilitado: boolean, cco: string[] }>>({})
  const [guardandoEnvios, setGuardandoEnvios] = useState(false)
  const [cargando, setCargando] = useState(true)
  const [activeTab, setActiveTab] = useState<string>('previa')
  const [ordenamiento, setOrdenamiento] = useState<Record<string, string>>({
    'previa': 'default',
    'dia-pago': 'default',
    'retrasada': 'default',
    'prejudicial': 'default'
  })

  // Mapeo de tipos a casos con colores por categoría
  const mapeoTipos = {
    'PAGO_5_DIAS_ANTES': { caso: '5 días antes', categoria: 'Notificación Previa', color: 'blue' },
    'PAGO_3_DIAS_ANTES': { caso: '3 días antes', categoria: 'Notificación Previa', color: 'blue' },
    'PAGO_1_DIA_ANTES': { caso: '1 día antes', categoria: 'Notificación Previa', color: 'blue' },
    'PAGO_DIA_0': { caso: 'Día de pago', categoria: 'Día de Pago', color: 'green' },
    'PAGO_1_DIA_ATRASADO': { caso: '1 día de retraso', categoria: 'Notificación Retrasada', color: 'orange' },
    'PAGO_3_DIAS_ATRASADO': { caso: '3 días de retraso', categoria: 'Notificación Retrasada', color: 'orange' },
    'PAGO_5_DIAS_ATRASADO': { caso: '5 días de retraso', categoria: 'Notificación Retrasada', color: 'orange' },
    'PREJUDICIAL': { caso: 'Prejudicial', categoria: 'Prejudicial', color: 'red' },
  }

  // Colores por categoría
  const coloresCategoria = {
    'blue': {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      text: 'text-blue-900',
      badge: 'bg-blue-100 text-blue-800'
    },
    'green': {
      bg: 'bg-green-50',
      border: 'border-green-200',
      text: 'text-green-900',
      badge: 'bg-green-100 text-green-800'
    },
    'orange': {
      bg: 'bg-orange-50',
      border: 'border-orange-200',
      text: 'text-orange-900',
      badge: 'bg-orange-100 text-orange-800'
    },
    'red': {
      bg: 'bg-red-50',
      border: 'border-red-200',
      text: 'text-red-900',
      badge: 'bg-red-100 text-red-800'
    }
  }

  // Organización por pestañas (orden de la imagen 1)
  const tiposPorPestaña: Record<string, string[]> = {
    'previa': ['PAGO_5_DIAS_ANTES', 'PAGO_3_DIAS_ANTES', 'PAGO_1_DIA_ANTES'],
    'dia-pago': ['PAGO_DIA_0'],
    'retrasada': ['PAGO_1_DIA_ATRASADO', 'PAGO_3_DIAS_ATRASADO', 'PAGO_5_DIAS_ATRASADO'],
    'prejudicial': ['PREJUDICIAL']
  }

  // Función para extraer número de días del caso
  const extraerDias = (caso: string): number => {
    const match = caso.match(/(\d+)\s*d[ií]a/)
    return match ? parseInt(match[1]) : 0
  }

  // Función para ordenar tipos según el criterio seleccionado
  const ordenarTipos = (tipos: string[], orden: string, pestaña: string): string[] => {
    const tiposConDatos = tipos.map(tipo => ({
      tipo,
      mapeo: mapeoTipos[tipo as keyof typeof mapeoTipos],
      config: configEnvios[tipo] || { habilitado: true, cco: [] }
    }))

    switch (orden) {
      case 'default':
        // Orden por defecto según pestañas (5, 3, 1 para previas; 1, 3, 5 para retrasadas)
        return tiposConDatos.sort((a, b) => {
          const diasA = extraerDias(a.mapeo?.caso || '')
          const diasB = extraerDias(b.mapeo?.caso || '')
          // Para previas: descendente (5, 3, 1)
          // Para retrasadas: ascendente (1, 3, 5)
          if (pestaña === 'previa') {
            return diasB - diasA
          } else if (pestaña === 'retrasada') {
            return diasA - diasB
          }
          return 0
        }).map(t => t.tipo)

      case 'dias-asc':
        return tiposConDatos.sort((a, b) => {
          const diasA = extraerDias(a.mapeo?.caso || '')
          const diasB = extraerDias(b.mapeo?.caso || '')
          return diasA - diasB
        }).map(t => t.tipo)

      case 'dias-desc':
        return tiposConDatos.sort((a, b) => {
          const diasA = extraerDias(a.mapeo?.caso || '')
          const diasB = extraerDias(b.mapeo?.caso || '')
          return diasB - diasA
        }).map(t => t.tipo)

      case 'nombre-asc':
        return tiposConDatos.sort((a, b) => {
          const nombreA = a.mapeo?.caso || ''
          const nombreB = b.mapeo?.caso || ''
          return nombreA.localeCompare(nombreB, 'es')
        }).map(t => t.tipo)

      case 'estado-activas':
        return tiposConDatos.sort((a, b) => {
          if (a.config.habilitado === b.config.habilitado) return 0
          return a.config.habilitado ? -1 : 1
        }).map(t => t.tipo)

      case 'estado-inactivas':
        return tiposConDatos.sort((a, b) => {
          if (a.config.habilitado === b.config.habilitado) return 0
          return a.config.habilitado ? 1 : -1
        }).map(t => t.tipo)

      default:
        return tipos
    }
  }

  useEffect(() => {
    cargarConfiguracionEnvios()
  }, [])

  const cargarConfiguracionEnvios = async () => {
    try {
      setCargando(true)
      console.log('🔄 [ConfiguracionNotificaciones] Cargando configuración de envíos...')
      const data = await emailConfigService.obtenerConfiguracionEnvios()
      console.log('✅ [ConfiguracionNotificaciones] Datos recibidos:', data)
      setConfigEnvios(data || {})
      console.log('📊 [ConfiguracionNotificaciones] Estado actualizado:', Object.keys(data || {}).length, 'tipos configurados')
    } catch (error) {
      console.error('❌ [ConfiguracionNotificaciones] Error cargando configuración de envíos:', error)
      toast.error('Error al cargar la configuración de envíos')
    } finally {
      setCargando(false)
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
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Zap className="h-4 w-4 text-blue-600" />
            Control de Envíos Automáticos
          </CardTitle>
          <CardDescription className="text-xs">
            Habilita o deshabilita el envío automático de correos (se ejecutan a las 4 AM diariamente)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {cargando ? (
            <div className="text-center py-8 text-gray-500">
              <p>Cargando configuración...</p>
            </div>
          ) : (
          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
            <TabsList className="grid w-full grid-cols-4 h-12 bg-gray-100 p-1">
              <TabsTrigger
                value="previa"
                className="flex items-center gap-2 data-[state=active]:bg-blue-500 data-[state=active]:text-white transition-all"
              >
                <Bell className="h-4 w-4" />
                <span className="font-medium">Notificación Previa</span>
              </TabsTrigger>
              <TabsTrigger
                value="dia-pago"
                className="flex items-center gap-2 data-[state=active]:bg-green-500 data-[state=active]:text-white transition-all"
              >
                <Calendar className="h-4 w-4" />
                <span className="font-medium">Día de Pago</span>
              </TabsTrigger>
              <TabsTrigger
                value="retrasada"
                className="flex items-center gap-2 data-[state=active]:bg-orange-500 data-[state=active]:text-white transition-all"
              >
                <AlertTriangle className="h-4 w-4" />
                <span className="font-medium">Retrasada</span>
              </TabsTrigger>
              <TabsTrigger
                value="prejudicial"
                className="flex items-center gap-2 data-[state=active]:bg-red-500 data-[state=active]:text-white transition-all"
              >
                <Shield className="h-4 w-4" />
                <span className="font-medium">Prejudicial</span>
              </TabsTrigger>
            </TabsList>

            {/* Renderizar tarjetas por pestaña */}
            {Object.entries(tiposPorPestaña).map(([pestaña, tipos]) => {
              const primeraTarjeta = mapeoTipos[tipos[0] as keyof typeof mapeoTipos]
              const colorCategoria = primeraTarjeta?.color || 'blue'
              const colores = coloresCategoria[colorCategoria as keyof typeof coloresCategoria]

              // Ordenar tipos según el criterio seleccionado para esta pestaña
              const ordenActual = ordenamiento[pestaña] || 'default'
              const tiposOrdenados = ordenarTipos(tipos, ordenActual, pestaña)

              return (
                <TabsContent key={pestaña} value={pestaña} className="space-y-4 mt-6">
                  {/* Menú de ordenamiento */}
                  {tipos.length > 1 && (
                    <div className="flex justify-end mb-4">
                      <div className="flex items-center gap-2">
                        <div className="flex flex-col -space-y-1">
                          <ChevronUp className="h-3 w-3 text-gray-400" />
                          <ChevronDown className="h-3 w-3 text-gray-400" />
                        </div>
                        <Select
                          value={ordenActual}
                          onValueChange={(value) => {
                            setOrdenamiento(prev => ({
                              ...prev,
                              [pestaña]: value
                            }))
                          }}
                        >
                          <SelectTrigger className="w-[220px] h-9">
                            <SelectValue placeholder="Ordenar por..." />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="default">Orden por defecto</SelectItem>
                            <SelectItem value="dias-asc">Días (menor a mayor)</SelectItem>
                            <SelectItem value="dias-desc">Días (mayor a menor)</SelectItem>
                            <SelectItem value="nombre-asc">Nombre (A-Z)</SelectItem>
                            <SelectItem value="estado-activas">Activas primero</SelectItem>
                            <SelectItem value="estado-inactivas">Inactivas primero</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  )}

                  <div className={`grid grid-cols-1 ${tiposOrdenados.length === 1 ? 'md:grid-cols-1 max-w-2xl mx-auto' : tiposOrdenados.length === 2 ? 'md:grid-cols-2' : 'md:grid-cols-2 lg:grid-cols-3'} gap-5`}>
                    {tiposOrdenados.map(tipo => {
                      const mapeo = mapeoTipos[tipo as keyof typeof mapeoTipos]
                      const config = configEnvios[tipo] || { habilitado: true, cco: [] }
                      const habilitado = config.habilitado
                      const ccoList = config.cco || []
                      const colorTipo = mapeo?.color || 'blue'
                      const coloresTarjeta = coloresCategoria[colorTipo as keyof typeof coloresCategoria]

                      return (
                        <div
                          key={tipo}
                          className={`border-2 rounded-xl p-6 space-y-4 ${coloresTarjeta.bg} ${coloresTarjeta.border} hover:shadow-lg transition-all transform hover:-translate-y-1`}
                        >
                          {/* Header con toggle */}
                          <div className="flex items-center justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <div className={`text-lg font-bold ${coloresTarjeta.text}`}>
                                {mapeo?.caso || tipo}
                              </div>
                              <div className={`text-sm ${coloresTarjeta.text} opacity-75 mt-1`}>
                                {mapeo?.categoria || 'Sin categoría'}
                              </div>
                            </div>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <span className={`text-xs w-8 text-center font-medium ${!habilitado ? 'text-gray-900' : 'text-gray-400'}`}>OFF</span>
                            <button
                              type="button"
                              onClick={() => toggleEnvio(tipo)}
                              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${
                                habilitado ? 'bg-blue-600' : 'bg-gray-300'
                              }`}
                            >
                              <span
                                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm ${
                                  habilitado ? 'translate-x-6' : 'translate-x-1'
                                }`}
                              />
                            </button>
                            <span className={`text-xs w-8 text-center font-medium ${habilitado ? 'text-gray-900' : 'text-gray-400'}`}>ON</span>
                          </div>
                        </div>

                          {/* CCO mejorado - Campos más grandes y cómodos */}
                          <div className={`pt-4 border-t-2 ${colorTipo === 'blue' ? 'border-blue-300' : colorTipo === 'green' ? 'border-green-300' : colorTipo === 'orange' ? 'border-orange-300' : 'border-red-300'} opacity-50`}>
                            <div className="flex items-center gap-2 mb-4">
                              <Copy className={`h-5 w-5 ${coloresTarjeta.text} opacity-75`} />
                              <label className={`text-sm font-bold ${coloresTarjeta.text}`}>
                                Correos en CCO (hasta 3):
                              </label>
                            </div>
                            <div className="space-y-3">
                              {[0, 1, 2].map(index => (
                                <div key={index} className="flex items-center gap-2">
                                  <Input
                                    type="email"
                                    placeholder={`ejemplo${index + 1}@correo.com`}
                                    value={ccoList[index] || ''}
                                    onChange={(e) => actualizarCCO(tipo, index, e.target.value)}
                                    className="h-11 text-base px-4 flex-1 bg-white border-2 border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 rounded-lg"
                                    disabled={!habilitado}
                                  />
                                  {ccoList[index] && (
                                    <Button
                                      type="button"
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => eliminarCCO(tipo, index)}
                                      className="h-11 w-11 p-0 flex-shrink-0 hover:bg-red-100 hover:text-red-600 transition-colors rounded-lg"
                                      disabled={!habilitado}
                                      title="Eliminar correo"
                                    >
                                      <X className="h-5 w-5" />
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
                </TabsContent>
              )
            })}

            {/* Botón Guardar - fuera de las pestañas para que siempre sea visible */}
            <div className="flex justify-end pt-6 border-t-2 border-gray-200 mt-8">
              <Button
                onClick={guardarConfiguracionEnvios}
                disabled={guardandoEnvios}
                size="lg"
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold shadow-md hover:shadow-lg transition-all"
              >
                <Settings className="h-5 w-5" />
                {guardandoEnvios ? 'Guardando...' : 'Guardar Configuración de Envíos'}
              </Button>
            </div>
          </Tabs>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

