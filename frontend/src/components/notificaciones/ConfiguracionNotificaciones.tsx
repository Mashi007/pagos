import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { FileText, Settings, Zap, Copy, X } from 'lucide-react'
import { emailConfigService } from '@/services/notificacionService'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'

export function ConfiguracionNotificaciones() {
  console.log('🔄 [ConfiguracionNotificaciones] Componente renderizado')
  
  const [configEnvios, setConfigEnvios] = useState<Record<string, { habilitado: boolean, cco: string[] }>>({})
  const [guardandoEnvios, setGuardandoEnvios] = useState(false)
  const [cargando, setCargando] = useState(true)

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
          <div className="space-y-3">
            {/* Grid compacto para todas las notificaciones */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
              {/* Función helper para renderizar cada tipo */}
              {tiposOrdenados.map(tipo => {
                const mapeo = mapeoTipos[tipo as keyof typeof mapeoTipos]
                const config = configEnvios[tipo] || { habilitado: true, cco: [] }
                const habilitado = config.habilitado
                const ccoList = config.cco || []
                
                return (
                  <div key={tipo} className="border rounded-md p-3 space-y-2 bg-gray-50/50">
                    {/* Header compacto con toggle */}
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-700 truncate">{mapeo?.caso || tipo}</div>
                        <div className="text-xs text-gray-500">{mapeo?.categoria || 'Sin categoría'}</div>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <span className={`text-xs w-8 text-center ${!habilitado ? 'text-gray-900 font-medium' : 'text-gray-400'}`}>OFF</span>
                        <button
                          type="button"
                          onClick={() => toggleEnvio(tipo)}
                          className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${
                            habilitado ? 'bg-blue-600' : 'bg-gray-300'
                          }`}
                        >
                          <span
                            className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                              habilitado ? 'translate-x-5' : 'translate-x-0.5'
                            }`}
                          />
                        </button>
                        <span className={`text-xs w-8 text-center ${habilitado ? 'text-gray-900 font-medium' : 'text-gray-400'}`}>ON</span>
                      </div>
                    </div>
                    
                    {/* CCO compacto */}
                    <div className="pt-2 border-t border-gray-200">
                      <div className="flex items-center gap-1.5 mb-1.5">
                        <Copy className="h-3.5 w-3.5 text-gray-400" />
                        <label className="text-xs font-medium text-gray-600">CCO:</label>
                      </div>
                      <div className="grid grid-cols-3 gap-1.5">
                        {[0, 1, 2].map(index => (
                          <div key={index} className="flex items-center gap-1">
                            <Input
                              type="email"
                              placeholder={`CCO${index + 1}`}
                              value={ccoList[index] || ''}
                              onChange={(e) => actualizarCCO(tipo, index, e.target.value)}
                              className="h-7 text-xs px-2"
                              disabled={!habilitado}
                            />
                            {ccoList[index] && (
                              <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => eliminarCCO(tipo, index)}
                                className="h-7 w-7 p-0 flex-shrink-0"
                                disabled={!habilitado}
                              >
                                <X className="h-3 w-3" />
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

            {/* Botón Guardar compacto */}
            <div className="flex justify-end pt-2 border-t">
              <Button
                onClick={guardarConfiguracionEnvios}
                disabled={guardandoEnvios}
                size="sm"
                className="flex items-center gap-2"
              >
                <Settings className="h-4 w-4" />
                {guardandoEnvios ? 'Guardando...' : 'Guardar Configuración'}
              </Button>
            </div>
          </div>
          )}
        </CardContent>
      </Card>

      {/* Información sobre dónde configurar plantillas */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-4 w-4 text-blue-600" />
            Configuración de Plantillas
          </CardTitle>
          <CardDescription className="text-xs">
            Para crear, editar o gestionar plantillas, ve a <strong>Herramientas → Plantillas</strong>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              💡 Para ver el resumen completo de todas las plantillas configuradas, ve a <strong>Herramientas → Plantillas → Resumen</strong>.
              Allí podrás ver todas las plantillas organizadas por tipo y caso, con opciones para editar o eliminar.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

