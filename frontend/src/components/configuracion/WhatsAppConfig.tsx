import { useState, useEffect } from 'react'
import { MessageSquare, Save, TestTube, CheckCircle, AlertCircle, Eye, EyeOff, Clock, XCircle, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { whatsappConfigService, notificacionService, type Notificacion, type WhatsAppConfig } from '@/services/notificacionService'

export function WhatsAppConfig() {
  const [config, setConfig] = useState<WhatsAppConfig>({
    api_url: 'https://graph.facebook.com/v18.0',
    access_token: '',
    phone_number_id: '',
    business_account_id: '',
    webhook_verify_token: '',
    modo_pruebas: 'true',
    telefono_pruebas: ''
  })
  
  const [mostrarToken, setMostrarToken] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [probando, setProbando] = useState(false)
  const [resultadoPrueba, setResultadoPrueba] = useState<any>(null)
  const [modoPruebas, setModoPruebas] = useState<string>('true')
  const [telefonoPruebas, setTelefonoPruebas] = useState('')
  const [telefonoPruebaDestino, setTelefonoPruebaDestino] = useState('')
  const [mensajePrueba, setMensajePrueba] = useState('')
  const [enviosRecientes, setEnviosRecientes] = useState<Notificacion[]>([])
  const [cargandoEnvios, setCargandoEnvios] = useState(false)
  const [errorValidacion, setErrorValidacion] = useState<string | null>(null)
  const [ejecutandoTestCompleto, setEjecutandoTestCompleto] = useState(false)
  const [resultadoTestCompleto, setResultadoTestCompleto] = useState<any>(null)

  useEffect(() => {
    cargarConfiguracion()
    cargarEnviosRecientes()
  }, [])

  const cargarConfiguracion = async () => {
    try {
      const data = await whatsappConfigService.obtenerConfiguracionWhatsApp()
      setConfig(data)
      setModoPruebas(data.modo_pruebas || 'true')
      setTelefonoPruebas(data.telefono_pruebas || '')
    } catch (error) {
      console.error('Error cargando configuración de WhatsApp:', error)
      toast.error('Error cargando configuración')
    }
  }

  const cargarEnviosRecientes = async () => {
    setCargandoEnvios(true)
    try {
      const resultado = await notificacionService.listarNotificaciones(1, 10, undefined, 'WHATSAPP')
      setEnviosRecientes(resultado.items || [])
    } catch (error) {
      console.error('Error cargando envíos recientes:', error)
    } finally {
      setCargandoEnvios(false)
    }
  }

  const handleChange = (campo: keyof WhatsAppConfig, valor: string) => {
    setConfig(prev => ({ ...prev, [campo]: valor }))
    if (errorValidacion) {
      setErrorValidacion(null)
    }
  }

  const validarConfiguracion = (): string | null => {
    if (!config.api_url || !config.access_token || !config.phone_number_id) {
      const camposFaltantes: string[] = []
      if (!config.api_url) camposFaltantes.push('API URL')
      if (!config.access_token) camposFaltantes.push('Access Token')
      if (!config.phone_number_id) camposFaltantes.push('Phone Number ID')
      return `Por favor completa todos los campos requeridos. Faltan: ${camposFaltantes.join(', ')}`
    }

    // Validar formato de API URL
    try {
      new URL(config.api_url)
    } catch {
      return 'La URL de la API no es válida'
    }

    return null
  }

  const handleGuardar = async () => {
    const errorValidacion = validarConfiguracion()
    if (errorValidacion) {
      setErrorValidacion(errorValidacion)
      toast.error(errorValidacion)
      return
    }

    setErrorValidacion(null)

    try {
      setGuardando(true)
      const configCompleta = {
        ...config,
        modo_pruebas: modoPruebas,
        telefono_pruebas: modoPruebas === 'true' ? telefonoPruebas : ''
      }

      await whatsappConfigService.actualizarConfiguracionWhatsApp(configCompleta)
      toast.success('Configuración de WhatsApp guardada exitosamente')
      await cargarConfiguracion()
    } catch (error: any) {
      console.error('Error guardando configuración:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error guardando configuración'
      toast.error(mensajeError)
    } finally {
      setGuardando(false)
    }
  }

  const handleProbar = async () => {
    try {
      setProbando(true)
      setResultadoPrueba(null)
      
      if (telefonoPruebaDestino && telefonoPruebaDestino.trim()) {
        const telefonoRegex = /^\+?[1-9]\d{9,14}$/
        const telefonoLimpio = telefonoPruebaDestino.replace(/[\s\-\(\)]/g, '')
        if (!telefonoRegex.test(telefonoLimpio)) {
          toast.error('Por favor ingresa un número de teléfono válido con código de país (ej: +584121234567)')
          setProbando(false)
          return
        }
      }

      const resultado = await whatsappConfigService.probarConfiguracionWhatsApp(
        telefonoPruebaDestino.trim() || undefined,
        mensajePrueba.trim() || undefined
      )
      setResultadoPrueba(resultado)
      
      if (resultado.mensaje?.includes('enviado')) {
        toast.success(`Mensaje de prueba enviado exitosamente a ${resultado.telefono_destino || 'tu teléfono'}`)
      } else {
        toast.error('Error enviando mensaje de prueba')
      }
    } catch (error: any) {
      console.error('Error probando configuración:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error desconocido'
      toast.error(`Error probando configuración: ${mensajeError}`)
      setResultadoPrueba({ error: mensajeError })
    } finally {
      setProbando(false)
    }
  }

  const handleTestCompleto = async () => {
    try {
      setEjecutandoTestCompleto(true)
      setResultadoTestCompleto(null)
      toast.info('Ejecutando test completo de WhatsApp...')
      
      const resultado = await whatsappConfigService.testCompletoWhatsApp()
      setResultadoTestCompleto(resultado)
      
      const resumen = resultado.resumen || {}
      if (resumen.fallidos === 0) {
        toast.success(`✅ Test completo: ${resumen.exitosos}/${resumen.total} tests exitosos`)
      } else {
        toast.warning(`⚠️ Test completo: ${resumen.exitosos}/${resumen.total} exitosos, ${resumen.fallidos} fallidos`)
      }
    } catch (error: any) {
      console.error('Error ejecutando test completo:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error desconocido'
      toast.error(`Error ejecutando test completo: ${mensajeError}`)
      setResultadoTestCompleto({ error: mensajeError })
    } finally {
      setEjecutandoTestCompleto(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Información */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <MessageSquare className="h-5 w-5 text-green-600" />
          <h3 className="font-semibold text-green-900">Configuración de WhatsApp</h3>
        </div>
        <p className="text-sm text-green-700">
          Configura la integración con Meta WhatsApp Business API para enviar notificaciones por WhatsApp a los clientes.
        </p>
      </div>

      {/* Configuración Meta API */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-green-600" />
            Configuración Meta WhatsApp Business API
          </CardTitle>
          <CardDescription>
            Ingresa tus credenciales de Meta Developers para enviar notificaciones por WhatsApp
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div className="flex items-start gap-2">
              <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="font-semibold text-amber-900 mb-1">Requisitos para Meta WhatsApp Business API:</p>
                <ul className="text-sm text-amber-800 space-y-1 list-disc list-inside">
                  <li>Debes tener una cuenta de <strong>Meta Business</strong> configurada</li>
                  <li>Necesitas un <strong>Access Token</strong> de Meta Developers</li>
                  <li>Debes tener un <strong>Phone Number ID</strong> verificado</li>
                  <li>Opcional: <strong>Business Account ID</strong> y <strong>Webhook Verify Token</strong></li>
                </ul>
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium block mb-2">API URL</label>
              <Input
                value={config.api_url}
                onChange={(e) => handleChange('api_url', e.target.value)}
                placeholder="https://graph.facebook.com/v18.0"
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">Phone Number ID</label>
              <Input
                value={config.phone_number_id}
                onChange={(e) => handleChange('phone_number_id', e.target.value)}
                placeholder="123456789012345"
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium block mb-2">Access Token</label>
            <div className="relative">
              <Input
                type={mostrarToken ? 'text' : 'password'}
                value={config.access_token || ''}
                onChange={(e) => handleChange('access_token', e.target.value)}
                placeholder="EAAxxxxxxxxxxxxx"
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setMostrarToken(!mostrarToken)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {mostrarToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Token de acceso de Meta Developers. Obtén uno en: <a href="https://developers.facebook.com/apps" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">developers.facebook.com</a>
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-sm font-medium block mb-2">Business Account ID <span className="text-gray-500">(opcional)</span></label>
              <Input
                value={config.business_account_id || ''}
                onChange={(e) => handleChange('business_account_id', e.target.value)}
                placeholder="123456789012345"
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-2">Webhook Verify Token <span className="text-gray-500">(opcional)</span></label>
              <Input
                value={config.webhook_verify_token || ''}
                onChange={(e) => handleChange('webhook_verify_token', e.target.value)}
                placeholder="mi_token_secreto"
              />
            </div>
          </div>

          {/* Selector de Ambiente */}
          <div className="border-t pt-4 mt-4">
            <div className="mb-4">
              <label className="text-sm font-medium block mb-2">Ambiente de Envío</label>
              <div className="flex gap-4">
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="ambiente"
                    value="false"
                    checked={modoPruebas === 'false'}
                    onChange={(e) => setModoPruebas(e.target.value)}
                    className="rounded"
                  />
                  <span className="text-sm">Producción (Envíos reales a clientes)</span>
                </label>
                <label className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="radio"
                    name="ambiente"
                    value="true"
                    checked={modoPruebas === 'true'}
                    onChange={(e) => setModoPruebas(e.target.value)}
                    className="rounded"
                  />
                  <span className="text-sm">Pruebas (Todos los mensajes a número de prueba)</span>
                </label>
              </div>
            </div>

            {modoPruebas === 'true' && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="mb-3">
                  <label className="text-sm font-medium block mb-2">
                    Teléfono de Pruebas <span className="text-red-500">*</span>
                  </label>
                  <Input
                    type="tel"
                    value={telefonoPruebas}
                    onChange={(e) => setTelefonoPruebas(e.target.value)}
                    placeholder="+584121234567"
                    className="max-w-md"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    En modo pruebas, todos los mensajes se enviarán a este número en lugar de a los clientes reales.
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Mensaje de error de validación */}
          {errorValidacion && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mt-4">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="font-semibold text-red-900 mb-1">Error de validación:</p>
                  <p className="text-sm text-red-800 whitespace-pre-line">{errorValidacion}</p>
                </div>
              </div>
            </div>
          )}

          {/* Botones de Acción */}
          <div className="flex gap-2 pt-4 border-t mt-4">
            <Button
              onClick={handleGuardar}
              disabled={guardando}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              type="button"
            >
              <Save className="h-4 w-4" />
              {guardando ? 'Guardando...' : 'Guardar Configuración'}
            </Button>
            <Button
              onClick={handleTestCompleto}
              disabled={ejecutandoTestCompleto}
              variant="outline"
              className="flex items-center gap-2 border-blue-600 text-blue-600 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed"
              type="button"
            >
              <RefreshCw className={`h-4 w-4 ${ejecutandoTestCompleto ? 'animate-spin' : ''}`} />
              {ejecutandoTestCompleto ? 'Ejecutando Test...' : 'Test Completo'}
            </Button>
          </div>

          {/* Resultados del Test Completo */}
          {resultadoTestCompleto && (
            <div className="border-t pt-4 mt-4">
              <div className={`rounded-lg p-4 ${
                resultadoTestCompleto.resumen?.fallidos === 0
                  ? 'bg-green-50 border border-green-200'
                  : 'bg-yellow-50 border border-yellow-200'
              }`}>
                <div className="flex items-start gap-2 mb-4">
                  {resultadoTestCompleto.resumen?.fallidos === 0 ? (
                    <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                  )}
                  <div className="flex-1">
                    <h3 className="font-semibold mb-2">
                      {resultadoTestCompleto.resumen?.estado_general || 'Resultado del Test'}
                    </h3>
                    {resultadoTestCompleto.resumen && (
                      <div className="text-sm space-y-1 mb-3">
                        <p>✅ Exitosos: {resultadoTestCompleto.resumen.exitosos}</p>
                        <p>❌ Fallidos: {resultadoTestCompleto.resumen.fallidos}</p>
                        {resultadoTestCompleto.resumen.advertencias > 0 && (
                          <p>⚠️ Advertencias: {resultadoTestCompleto.resumen.advertencias}</p>
                        )}
                      </div>
                    )}
                    {resultadoTestCompleto.tests && (
                      <div className="space-y-2 mt-4">
                        {Object.entries(resultadoTestCompleto.tests).map(([key, test]: [string, any]) => (
                          <div key={key} className="bg-white rounded p-3 border">
                            <div className="flex items-center gap-2 mb-1">
                              {test.exito ? (
                                <CheckCircle className="h-4 w-4 text-green-600" />
                              ) : (
                                <XCircle className="h-4 w-4 text-red-600" />
                              )}
                              <span className="font-medium text-sm">{test.nombre}</span>
                            </div>
                            {test.mensaje && (
                              <p className="text-xs text-gray-600 ml-6">{test.mensaje}</p>
                            )}
                            {test.error && (
                              <p className="text-xs text-red-600 ml-6">{test.error}</p>
                            )}
                            {test.detalles && Object.keys(test.detalles).length > 0 && (
                              <details className="ml-6 mt-2">
                                <summary className="text-xs text-gray-500 cursor-pointer">Ver detalles</summary>
                                <pre className="text-xs mt-2 p-2 bg-gray-50 rounded overflow-auto max-h-40">
                                  {JSON.stringify(test.detalles, null, 2)}
                                </pre>
                              </details>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    {resultadoTestCompleto.resumen?.recomendaciones && resultadoTestCompleto.resumen.recomendaciones.length > 0 && (
                      <div className="mt-4">
                        <p className="font-semibold text-sm mb-2">Recomendaciones:</p>
                        <ul className="text-sm space-y-1 list-disc list-inside">
                          {resultadoTestCompleto.resumen.recomendaciones.map((rec: string, idx: number) => (
                            <li key={idx} className="text-gray-700">{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Ambiente de Prueba - Envío de Mensaje de Prueba */}
          <div className="border-t pt-4 mt-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
              <h3 className="font-semibold text-green-900 mb-2 flex items-center gap-2">
                <TestTube className="h-5 w-5" />
                Envío de Mensaje de Prueba
              </h3>
              <p className="text-sm text-green-700 mb-4">
                Envía un mensaje de prueba personalizado para verificar que la configuración de WhatsApp funciona correctamente.
              </p>
              {modoPruebas === 'false' && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4">
                  <p className="text-sm text-green-800 font-semibold mb-1">
                    ✅ Modo Producción activo
                  </p>
                  <p className="text-xs text-green-700">
                    El mensaje de prueba se enviará <strong>REALMENTE</strong> al destinatario especificado.
                  </p>
                </div>
              )}
              {modoPruebas === 'true' && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                  <p className="text-sm text-yellow-800 font-semibold mb-1">
                    ⚠️ Modo Pruebas activo
                  </p>
                  <p className="text-xs text-yellow-700">
                    El mensaje se redirigirá a la dirección de pruebas configurada ({telefonoPruebas || 'no configurada'}).
                  </p>
                </div>
              )}
              
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium block mb-2">
                    Teléfono de Destino <span className="text-gray-500">(opcional)</span>
                  </label>
                  <Input
                    type="tel"
                    value={telefonoPruebaDestino}
                    onChange={(e) => setTelefonoPruebaDestino(e.target.value)}
                    placeholder="+584121234567"
                    className="max-w-md"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Debe incluir código de país (ej: +584121234567). Si no especificas, se usará el teléfono de pruebas.
                  </p>
                </div>

                <div>
                  <label className="text-sm font-medium block mb-2">
                    Mensaje de Prueba <span className="text-gray-500">(opcional)</span>
                  </label>
                  <Textarea
                    value={mensajePrueba}
                    onChange={(e) => setMensajePrueba(e.target.value)}
                    placeholder="Escribe aquí tu mensaje de prueba..."
                    rows={6}
                    className="max-w-md resize-y"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Si no especificas un mensaje, se usará el mensaje predeterminado
                  </p>
                </div>
                
                <Button
                  onClick={handleProbar}
                  disabled={probando || !config.access_token}
                  className="flex items-center gap-2 bg-green-600 hover:bg-green-700"
                >
                  <TestTube className="h-4 w-4" />
                  {probando ? 'Enviando Mensaje de Prueba...' : 'Enviar Mensaje de Prueba'}
                </Button>
              </div>
            </div>
          </div>

          {/* Resultado de la prueba */}
          {resultadoPrueba && (
            <div className={`p-4 rounded-lg border ${
              resultadoPrueba.mensaje?.includes('enviado') 
                ? 'bg-green-50 border-green-200' 
                : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-start gap-2">
                {resultadoPrueba.mensaje?.includes('enviado') ? (
                  <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                )}
                <div className="flex-1">
                  <p className={`font-medium ${
                    resultadoPrueba.mensaje?.includes('enviado') ? 'text-green-900' : 'text-red-900'
                  }`}>
                    {resultadoPrueba.mensaje}
                  </p>
                  {resultadoPrueba.error && (
                    <p className="text-sm text-red-600 mt-1">{resultadoPrueba.error}</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Verificación de Envíos Recientes */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-green-600" />
            Verificación de Envíos Recientes
          </CardTitle>
          <CardDescription>
            Historial reciente de mensajes WhatsApp enviados para verificar que el sistema está funcionando correctamente
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex justify-between items-center mb-4">
            <div className="text-sm text-gray-600">
              Últimos 10 envíos de notificaciones WhatsApp
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={cargarEnviosRecientes}
              disabled={cargandoEnvios}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${cargandoEnvios ? 'animate-spin' : ''}`} />
              Actualizar
            </Button>
          </div>

          {cargandoEnvios ? (
            <div className="text-center py-8 text-gray-500">Cargando envíos...</div>
          ) : enviosRecientes.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p>No hay envíos recientes</p>
            </div>
          ) : (
            <div className="space-y-3">
              {enviosRecientes.map((envio) => (
                <div
                  key={envio.id}
                  className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge
                          className={
                            envio.estado === 'ENVIADA'
                              ? 'bg-green-100 text-green-800'
                              : envio.estado === 'FALLIDA'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-yellow-100 text-yellow-800'
                          }
                        >
                          {envio.estado}
                        </Badge>
                        <span className="text-sm font-medium text-gray-700">
                          {envio.asunto || 'Sin asunto'}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 space-y-1">
                        <div className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {envio.fecha_envio
                            ? new Date(envio.fecha_envio).toLocaleString('es-ES')
                            : envio.fecha_creacion
                            ? new Date(envio.fecha_creacion).toLocaleString('es-ES')
                            : 'Sin fecha'}
                        </div>
                        {envio.tipo && (
                          <div className="text-xs text-gray-600">
                            Tipo: {envio.tipo}
                          </div>
                        )}
                        {envio.error_mensaje && (
                          <div className="text-xs text-red-600 flex items-start gap-1">
                            <XCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                            <span>{envio.error_mensaje}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

