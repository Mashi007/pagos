import { useState, useEffect } from 'react'
import { MessageSquare, Save, TestTube, CheckCircle, AlertCircle, Eye, EyeOff, Clock, XCircle, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Badge } from '../../components/ui/badge'
import { toast } from 'sonner'
import { validarTelefono, validarConfiguracionWhatsApp, normalizarTelefonoParaIngreso, pareceNumeroTelefonoParaMeta } from '../../utils/validators'
import { whatsappConfigService, notificacionService, type Notificacion, type WhatsAppConfig } from '../../services/notificacionService'

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
    // âœ… Usar validación centralizada
    const validacion = validarConfiguracionWhatsApp({
      api_url: config.api_url,
      access_token: config.access_token,
      phone_number_id: config.phone_number_id
    })

    if (!validacion.valido) {
      return validacion.errores.join('. ')
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
      // Limpiar espacios en blanco de los campos importantes
      const configCompleta = {
        ...config,
        api_url: config.api_url?.trim() || '',
        access_token: config.access_token?.trim() || '',
        phone_number_id: config.phone_number_id?.trim() || '',
        business_account_id: config.business_account_id?.trim() || '',
        webhook_verify_token: config.webhook_verify_token?.trim() || '',
        modo_pruebas: modoPruebas,
        telefono_pruebas: modoPruebas === 'true' ? telefonoPruebas.trim() : ''
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
        if (!validarTelefono(telefonoPruebaDestino)) {
          toast.error('Ingresa un número válido con código de país (ej. +58 424 1234567)')
          setProbando(false)
          return
        }
      }

      console.log('ðŸ“¤ [MENSAJE PRUEBA] Enviando mensaje de prueba...')
      const resultado = await whatsappConfigService.probarConfiguracionWhatsApp(
        telefonoPruebaDestino.trim() || undefined,
        mensajePrueba.trim() || undefined
      )
      setResultadoPrueba(resultado)

      // âœ… LOG DETALLADO: Mostrar resultado del mensaje de prueba
      console.log('ðŸ“Š [MENSAJE PRUEBA] Resultado completo:', resultado)

      if (resultado.success || resultado.mensaje?.includes('enviado')) {
        console.log('âœ… [CONFIRMACIÓN] Mensaje de prueba ENVIADO EXITOSAMENTE')
        console.log('âœ… [CONFIRMACIÓN] WhatsApp ACEPTÓ y procesó tu mensaje')
        console.log('âœ… [CONFIRMACIÓN] Meta Developers API está funcionando correctamente')
        console.log('âœ… [CONFIRMACIÓN] Tu configuración es VÁLIDA y está CONECTADA')
        toast.success(`Mensaje de prueba enviado exitosamente a ${resultado.telefono_destino || 'tu teléfono'}`)
      } else {
        console.error('âŒ [CONFIRMACIÓN] Mensaje de prueba FALLÓ')
        console.error('âŒ [CONFIRMACIÓN] Error:', resultado.error || resultado.mensaje)
        console.error('âŒ [CONFIRMACIÓN] WhatsApp/Meta rechazó el envío')
        toast.error('Error enviando mensaje de prueba')
      }
    } catch (error: any) {
      console.error('âŒ [ERROR] Error probando configuración:', error)
      const mensajeError = error?.response?.data?.detail || error?.message || 'Error desconocido'
      console.error('âŒ [ERROR] Detalle del error:', mensajeError)
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

      // âœ… LOG DETALLADO: Mostrar resultados del test completo
      console.log('ðŸ“Š [TEST COMPLETO] Resultado completo:', resultado)

      // Verificar específicamente la conexión con Meta API
      const testConexion = resultado.tests?.conexion
      if (testConexion) {
        console.log('ðŸ” [TEST CONEXIÓN META API]:', {
          nombre: testConexion.nombre,
          exito: testConexion.exito,
          mensaje: testConexion.mensaje || testConexion.error,
          detalles: testConexion.detalles,
          error: testConexion.error
        })

        if (testConexion.exito) {
          console.log('âœ… [CONFIRMACIÓN] WhatsApp ACEPTÓ la conexión - Meta respondió 200 OK')
          console.log('âœ… [CONFIRMACIÓN] Tu Access Token es VÁLIDO')
          console.log('âœ… [CONFIRMACIÓN] Tu Phone Number ID es CORRECTO')
          console.log('âœ… [CONFIRMACIÓN] Estás CONECTADO a Meta Developers API')
        } else {
          console.error('âŒ [CONFIRMACIÓN] WhatsApp RECHAZÓ la conexión')
          console.error('âŒ [CONFIRMACIÓN] Error:', testConexion.error || testConexion.mensaje)
          console.error('âŒ [CONFIRMACIÓN] Meta respondió con error - Revisa tu configuración')
        }
      }

      const resumen = resultado.resumen || {}
      console.log('ðŸ“ˆ [RESUMEN TEST]:', {
        total: resumen.total,
        exitosos: resumen.exitosos,
        fallidos: resumen.fallidos,
        advertencias: resumen.advertencias
      })

      if (resumen.fallidos === 0) {
        toast.success(`âœ… Test completo: ${resumen.exitosos}/${resumen.total} tests exitosos`)
        console.log('âœ… [RESULTADO FINAL] Todos los tests pasaron - WhatsApp está configurado correctamente')
      } else {
        toast.warning(`âš ï¸ Test completo: ${resumen.exitosos}/${resumen.total} exitosos, ${resumen.fallidos} fallidos`)
        console.warn('âš ï¸ [RESULTADO FINAL] Algunos tests fallaron - Revisa la configuración')
      }
    } catch (error: any) {
      console.error('âŒ [ERROR] Error ejecutando test completo:', error)
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
        <CardContent className="space-y-4 pt-6">
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

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="font-semibold text-blue-900 mb-2">¿Cuándo hace falta plantilla aprobada?</p>
            <ul className="text-sm text-blue-800 space-y-1.5">
              <li><strong>No hace falta plantilla</strong> cuando <strong>tú respondes</strong> al cliente dentro de las 24 h desde su último mensaje: flujo de cobranza (pedir cédula, foto de pago, confirmación), respuestas del bot a mensajes entrantes. Todo eso funciona con mensaje de texto libre.</li>
              <li><strong>Sí hace falta plantilla</strong> cuando <strong>tú inicias</strong> la conversación o han pasado más de 24 h desde que el cliente te escribió: notificaciones proactivas (recordatorios de pago, cuota vence), mensaje de prueba a un número que no te ha escrito. Para esos envíos Meta exige una plantilla aprobada en Meta Business Manager (WhatsApp → Plantillas de mensaje).</li>
            </ul>
            <p className="text-xs text-blue-700 mt-2">Resumen: para trabajar con el bot de cobranza (ellos te escriben, tú respondes) no necesitas plantilla. Para enviar recordatorios o notificaciones sin que te hayan escrito antes, sí.</p>
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
                placeholder="1038026026054793"
                className={pareceNumeroTelefonoParaMeta(config.phone_number_id || '') ? 'border-amber-500 bg-amber-50' : ''}
              />
              {pareceNumeroTelefonoParaMeta(config.phone_number_id || '') && (
                <p className="text-xs text-amber-700 mt-1 font-medium">
                  Has puesto un número de teléfono (ej. 4244545242 o +58…). Meta pide el <strong>ID numérico largo</strong> (ej. 1038026026054793), que ves en Meta Developers → WhatsApp → Enviar y recibir mensajes → “Identificador del número de teléfono”. No es el mismo que el número +58 424 4545242.
                </p>
              )}
              <p className="text-xs text-gray-500 mt-1">
                ID numérico largo de Meta (15–16 dígitos), en Business Suite o Meta Developers → WhatsApp → tu número → “Identificador del número de teléfono”. No uses el número de teléfono (424… ni +58…); ese es el número de destino.
              </p>
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
              <label className="text-sm font-medium block mb-2">
                Webhook Verify Token <span className="text-gray-500">(requerido para bot)</span>
              </label>
              <Input
                value={config.webhook_verify_token || ''}
                onChange={(e) => handleChange('webhook_verify_token', e.target.value)}
                placeholder="mi_token_secreto_2024"
                type={mostrarToken ? 'text' : 'password'}
              />
              <p className="text-xs text-gray-500 mt-1">
                Token secreto para verificar webhooks de Meta. Debe ser el mismo que configures en Meta Developers.
              </p>
              <p className="text-xs text-amber-700 mt-2 font-medium">
                Para que lleguen mensajes a Comunicaciones: en Meta Developers → WhatsApp → Configuración, pon <strong>URL del webhook</strong>: <code className="bg-amber-100 px-1 rounded">https://TU_DOMINIO/api/v1/whatsapp/webhook</code> (ej. <code className="bg-amber-100 px-1 rounded">https://rapicredit.onrender.com/api/v1/whatsapp/webhook</code>). El Verify Token de Meta debe coincidir con el de arriba.
              </p>
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
                  <span className="text-sm">Producción (Envíos reales a cualquier número)</span>
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
                  <span className="text-sm">Pruebas (Solo mensaje de prueba a número de prueba)</span>
                </label>
              </div>
              {modoPruebas === 'false' && (
                <p className="text-xs text-gray-500 mt-2">
                  Con token permanente y app en producción en Meta, puedes enviar a cualquier número. La primera vez que contactas un número, Meta puede exigir una plantilla aprobada o que el usuario te haya escrito en las últimas 24 h.
                </p>
              )}
            </div>

            {modoPruebas === 'true' && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="mb-3">
                  <label className="text-sm font-medium block mb-2">
                    Teléfono de Pruebas <span className="text-red-500">*</span>
                  </label>
                  <Input
                    type="tel"
                    inputMode="tel"
                    autoComplete="tel"
                    value={telefonoPruebas}
                    onChange={(e) => setTelefonoPruebas(normalizarTelefonoParaIngreso(e.target.value))}
                    placeholder="+58 424 1234567"
                    className="max-w-md"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Formato: código de país + número (ej. Venezuela +58 424 1234567). En modo pruebas, todos los mensajes se enviarán a este número.
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
                        <p>âœ… Exitosos: {resultadoTestCompleto.resumen.exitosos}</p>
                        <p>âŒ Fallidos: {resultadoTestCompleto.resumen.fallidos}</p>
                        {resultadoTestCompleto.resumen.advertencias > 0 && (
                          <p>âš ï¸ Advertencias: {resultadoTestCompleto.resumen.advertencias}</p>
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
                    ✓ Modo Producción activo
                  </p>
                  <p className="text-xs text-green-700">
                    El mensaje se enviará al número que indiques en Teléfono de Destino (o a cualquier número que uses en Notificaciones/Cobranzas).
                  </p>
                </div>
              )}
              {modoPruebas === 'true' && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                  <p className="text-sm text-yellow-800 font-semibold mb-1">
                    ⚠ Modo Pruebas activo
                  </p>
                  <p className="text-xs text-yellow-700">
                    El mensaje de prueba se redirige al Teléfono de Pruebas ({telefonoPruebas || 'no configurada'}). Las notificaciones a clientes siguen yendo al número real de cada cliente.
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
                    inputMode="tel"
                    autoComplete="tel"
                    value={telefonoPruebaDestino}
                    onChange={(e) => setTelefonoPruebaDestino(normalizarTelefonoParaIngreso(e.target.value))}
                    placeholder="+58 424 1234567"
                    className="max-w-md"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Formato: código de país + número (ej. Venezuela +58 424 1234567). Si no especificas, se usará el teléfono de pruebas.
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
            <div className="space-y-2">
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
                    {resultadoPrueba.telefono_destino && (
                      <p className="text-sm text-gray-600 mt-1">
                        Destino: {resultadoPrueba.telefono_destino}
                      </p>
                    )}
                    {resultadoPrueba.error && (
                      <p className="text-sm text-red-600 mt-1">{resultadoPrueba.error}</p>
                    )}
                  </div>
                </div>
              </div>
              {resultadoPrueba.mensaje?.includes('enviado') && (
                <div className="p-3 rounded-lg border border-blue-200 bg-blue-50 text-sm text-blue-900">
                  <p className="font-medium mb-1">¿No te llega el mensaje?</p>
                  <ul className="list-disc list-inside space-y-0.5 text-blue-800">
                    <li>El mensaje se envió a <strong>{resultadoPrueba.telefono_destino || 'el número indicado'}</strong>. En modo Pruebas, ese es el &quot;Teléfono de Pruebas&quot; configurado arriba. Si esperas recibirlo en otro número (ej. +58…), pon ese número en Teléfono de Pruebas.</li>
                    <li>Ese número debe estar añadido como <strong>número de prueba</strong> en Meta Developers (WhatsApp → Enviar y recibir mensajes → números de prueba).</li>
                    <li>Para <strong>iniciar conversación</strong> con un número que no te ha escrito antes, Meta puede exigir una <strong>plantilla aprobada</strong>. Crea una en Meta Business Manager (WhatsApp → Plantillas de mensaje) o haz que el usuario te escriba primero para abrir la ventana de 24 h.</li>
                  </ul>
                </div>
              )}
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
              Ãšltimos 10 envíos de notificaciones WhatsApp
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

