import { useState, useRef, useEffect } from 'react'
import { Brain, ChevronRight, Loader2, AlertCircle, MessageSquare } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { apiClient } from '@/services/api'

interface Mensaje {
  id: string
  tipo: 'usuario' | 'ai'
  contenido: string
  timestamp: Date
  error?: boolean
}

export function ChatAI() {
  const [mensajes, setMensajes] = useState<Mensaje[]>([])
  const [pregunta, setPregunta] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [aiConfigurado, setAiConfigurado] = useState(false)
  const [verificando, setVerificando] = useState(true)
  const mensajesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    verificarConfiguracionAI()
    // Mensaje de bienvenida
    setMensajes([{
      id: 'bienvenida',
      tipo: 'ai',
      contenido: '¡Hola! Soy tu asistente de IA. Puedo ayudarte a consultar información de la base de datos. ¿En qué puedo ayudarte?',
      timestamp: new Date()
    }])
  }, [])

  useEffect(() => {
    mensajesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajes])

  const verificarConfiguracionAI = async () => {
    setVerificando(true)
    try {
      const config = await apiClient.get<{
        openai_api_key?: string
        activo?: string
      }>('/api/v1/configuracion/ai/configuracion')
      const tieneToken = !!(config?.openai_api_key && config.openai_api_key.trim())
      const estaActivo = config?.activo?.toLowerCase() === 'true'
      setAiConfigurado(tieneToken && estaActivo)
      
      if (!tieneToken) {
        toast.error('OpenAI API Key no configurado. Configúralo en Configuración > Inteligencia Artificial')
      } else if (!estaActivo) {
        toast.warning('AI está inactivo. Actívalo en Configuración > Inteligencia Artificial')
      }
    } catch (error) {
      console.error('Error verificando configuración AI:', error)
      setAiConfigurado(false)
    } finally {
      setVerificando(false)
    }
  }

  const enviarPregunta = async () => {
    if (!pregunta.trim()) return
    if (!aiConfigurado) {
      toast.error('AI no está configurado o activo. Configúralo primero.')
      return
    }

    const preguntaTexto = pregunta.trim()
    setPregunta('')
    
    // Agregar mensaje del usuario
    const mensajeUsuario: Mensaje = {
      id: Date.now().toString(),
      tipo: 'usuario',
      contenido: preguntaTexto,
      timestamp: new Date()
    }
    setMensajes(prev => [...prev, mensajeUsuario])
    setEnviando(true)

    try {
      const respuesta = await apiClient.post<{
        success: boolean
        respuesta: string
        pregunta: string
        tokens_usados?: number
        modelo_usado?: string
        tiempo_respuesta?: number
        error?: string
      }>('/api/v1/ai/chat', {
        pregunta: preguntaTexto
      })

      if (respuesta.success) {
        const mensajeAI: Mensaje = {
          id: (Date.now() + 1).toString(),
          tipo: 'ai',
          contenido: respuesta.respuesta,
          timestamp: new Date()
        }
        setMensajes(prev => [...prev, mensajeAI])
      } else {
        throw new Error(respuesta.error || 'Error generando respuesta')
      }
    } catch (error: any) {
      console.error('Error enviando pregunta:', error)
      const mensajeError: Mensaje = {
        id: (Date.now() + 1).toString(),
        tipo: 'ai',
        contenido: `Error: ${error?.response?.data?.detail || error?.message || 'No se pudo generar la respuesta'}`,
        timestamp: new Date(),
        error: true
      }
      setMensajes(prev => [...prev, mensajeError])
      toast.error('Error al generar respuesta')
    } finally {
      setEnviando(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      enviarPregunta()
    }
  }

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <Brain className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold">Chat AI</h1>
        </div>
        <p className="text-gray-600">
          Consulta información de la base de datos usando inteligencia artificial
        </p>
      </div>

      {/* Estado de configuración */}
      {verificando ? (
        <Card className="mb-4">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Verificando configuración de AI...</span>
            </div>
          </CardContent>
        </Card>
      ) : !aiConfigurado ? (
        <Card className="mb-4 border-amber-200 bg-amber-50">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold text-amber-900 mb-1">AI no configurado</p>
                <p className="text-sm text-amber-700">
                  Para usar Chat AI, necesitas configurar y activar la Inteligencia Artificial en{' '}
                  <a href="/configuracion?tab=ai" className="underline font-medium">
                    Configuración &gt; Inteligencia Artificial
                  </a>
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {/* Chat */}
      <Card className="h-[calc(100vh-280px)] flex flex-col">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Conversación
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col p-0">
          {/* Área de mensajes */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {mensajes.map((mensaje) => (
              <div
                key={mensaje.id}
                className={`flex gap-3 ${
                  mensaje.tipo === 'usuario' ? 'justify-end' : 'justify-start'
                }`}
              >
                {mensaje.tipo === 'ai' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                    <Brain className="h-4 w-4 text-blue-600" />
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-lg p-3 ${
                    mensaje.tipo === 'usuario'
                      ? 'bg-blue-600 text-white'
                      : mensaje.error
                      ? 'bg-red-50 text-red-900 border border-red-200'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{mensaje.contenido}</p>
                  <span className="text-xs opacity-70 mt-1 block">
                    {mensaje.timestamp.toLocaleTimeString('es-ES', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                </div>
                {mensaje.tipo === 'usuario' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center">
                    <span className="text-xs font-semibold">Tú</span>
                  </div>
                )}
              </div>
            ))}
            {enviando && (
              <div className="flex gap-3 justify-start">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                  <Brain className="h-4 w-4 text-blue-600" />
                </div>
                <div className="bg-gray-100 rounded-lg p-3">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                </div>
              </div>
            )}
            <div ref={mensajesEndRef} />
          </div>

          {/* Input de pregunta */}
          <div className="border-t p-4">
            <div className="flex gap-2">
              <Textarea
                value={pregunta}
                onChange={(e) => setPregunta(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={
                  aiConfigurado
                    ? "Escribe tu pregunta sobre la base de datos... (Presiona Enter para enviar, Shift+Enter para nueva línea)"
                    : "Configura AI primero para usar el chat..."
                }
                disabled={!aiConfigurado || enviando}
                rows={3}
                className="resize-none"
              />
              <Button
                onClick={enviarPregunta}
                disabled={!aiConfigurado || enviando || !pregunta.trim()}
                className="self-end"
              >
                {enviando ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Ejemplos: "¿Cuántos préstamos activos hay?", "¿Cuál es el total de pagos del mes?", "Muéstrame los clientes en mora"
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

