import { useState, useEffect, useRef } from 'react'

import {
  MessageSquare,
  User,
  Brain,
  ChevronRight,
  Loader2,
  Trash2,
} from 'lucide-react'

import { Card, CardContent } from '../../components/ui/card'

import { Button } from '../../components/ui/button'

import { Textarea } from '../../components/ui/textarea'

import { toast } from 'sonner'

import { apiClient } from '../../services/api'

import { type AIConfigState, type MensajeChatAI } from '../../types/aiConfig'

interface AITestTabProps {
  config: AIConfigState
}

export function AITestTab({ config }: AITestTabProps) {
  const [probando, setProbando] = useState(false)

  const [preguntaPrueba, setPreguntaPrueba] = useState('')

  const [usarDocumentos, setUsarDocumentos] = useState(true)

  const [resultadoPrueba, setResultadoPrueba] = useState<any>(null)

  const [mensajesChat, setMensajesChat] = useState<MensajeChatAI[]>([])

  const chatEndRef = useRef<HTMLDivElement>(null)

  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajesChat, probando])

  const handleProbar = async () => {
    const pregunta = preguntaPrueba.trim()

    if (!pregunta) {
      toast.error('Por favor, escribe una pregunta')

      return
    }

    if (!config.configured) {
      toast.error(
        'Ingresa tu API Key de OpenRouter en el campo de arriba y guarda.'
      )

      return
    }

    const mensajeUsuario = {
      id: `user-${Date.now()}`,

      tipo: 'user' as const,

      texto: pregunta,

      timestamp: new Date(),
    }

    setMensajesChat(prev => [...prev, mensajeUsuario])

    setPreguntaPrueba('')

    setProbando(true)

    setResultadoPrueba(null)

    try {
      const resultado = await apiClient.post<{
        success: boolean

        mensaje: string

        pregunta?: string

        respuesta?: string

        tokens_usados?: number

        modelo_usado?: string

        tiempo_respuesta?: number

        usar_documentos?: boolean

        documentos_consultados?: number

        error_code?: string
      }>('/api/v1/configuracion/ai/probar', {
        pregunta: pregunta,

        usar_documentos: usarDocumentos,
      })

      setResultadoPrueba(resultado)

      if (resultado.success && resultado.respuesta) {
        const mensajeAI = {
          id: `ai-${Date.now()}`,

          tipo: 'ai' as const,

          texto: resultado.respuesta,

          timestamp: new Date(),

          metadata: {
            tokens: resultado.tokens_usados,

            tiempo: resultado.tiempo_respuesta,

            modelo: resultado.modelo_usado,

            documentos: resultado.documentos_consultados,
          },
        }

        setMensajesChat(prev => [...prev, mensajeAI])

        toast.success('Respuesta generada exitosamente')
      } else {
        const mensajeError = {
          id: `error-${Date.now()}`,

          tipo: 'ai' as const,

          texto: resultado.mensaje || 'Error generando respuesta',

          timestamp: new Date(),
        }

        setMensajesChat(prev => [...prev, mensajeError])

        toast.error(resultado.mensaje || 'Error generando respuesta')
      }
    } catch (error: any) {
      console.error('Error probando AI:', error)

      const mensajeError =
        error?.response?.data?.detail || error?.message || 'Error probando AI'

      const mensajeErrorChat = {
        id: `error-${Date.now()}`,

        tipo: 'ai' as const,

        texto: `âŒ Error: ${mensajeError}`,

        timestamp: new Date(),
      }

      setMensajesChat(prev => [...prev, mensajeErrorChat])

      toast.error(mensajeError)

      setResultadoPrueba({ success: false, mensaje: mensajeError })
    } finally {
      setProbando(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()

      if (!probando && preguntaPrueba.trim()) {
        handleProbar()
      }
    }
  }

  const limpiarChat = () => {
    setMensajesChat([])

    setResultadoPrueba(null)
  }

  return (
    <Card className="border-2 border-gray-200 shadow-sm">
      <CardContent className="p-0 pt-6">
        <div className="rounded-t-lg bg-gradient-to-r from-blue-500 to-blue-600 p-4 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />

              <h3 className="font-semibold">Chat de Prueba de AI</h3>
            </div>

            {mensajesChat.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={limpiarChat}
                className="text-white hover:bg-blue-700"
              >
                <Trash2 className="mr-1 h-4 w-4" />
                Limpiar
              </Button>
            )}
          </div>

          <p className="mt-1 text-sm text-blue-100">
            Haz cualquier pregunta y recibe respuestas. Presiona Enter para
            enviar.
          </p>
        </div>

        <div className="flex h-[500px] flex-col bg-gray-50">
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {mensajesChat.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center text-gray-400">
                <MessageSquare className="mb-3 h-12 w-12 opacity-50" />

                <p className="text-sm">No hay mensajes aún</p>

                <p className="mt-1 text-xs">
                  Escribe una pregunta para comenzar
                </p>
              </div>
            ) : (
              mensajesChat.map(mensaje => (
                <div
                  key={mensaje.id}
                  className={`flex gap-3 ${
                    mensaje.tipo === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {mensaje.tipo === 'ai' && (
                    <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-blue-500">
                      <Brain className="h-4 w-4 text-white" />
                    </div>
                  )}

                  <div
                    className={`max-w-[80%] rounded-lg p-3 ${
                      mensaje.tipo === 'user'
                        ? 'bg-blue-500 text-white'
                        : 'border border-gray-200 bg-white text-gray-800'
                    }`}
                  >
                    <p className="whitespace-pre-wrap break-words text-sm">
                      {mensaje.texto}
                    </p>

                    {mensaje.metadata && mensaje.tipo === 'ai' && (
                      <div className="mt-2 flex flex-wrap gap-2 border-t border-gray-200 pt-2 text-xs text-gray-500">
                        {mensaje.metadata.tokens && (
                          <span>Tokens: {mensaje.metadata.tokens}</span>
                        )}

                        {mensaje.metadata.tiempo && (
                          <span>
                            Tiempo: {mensaje.metadata.tiempo.toFixed(2)}s
                          </span>
                        )}

                        {mensaje.metadata.modelo && (
                          <span>Modelo: {mensaje.metadata.modelo}</span>
                        )}

                        {mensaje.metadata.documentos !== undefined && (
                          <span>Documentos: {mensaje.metadata.documentos}</span>
                        )}
                      </div>
                    )}

                    <p className="mt-1 text-xs opacity-70">
                      {mensaje.timestamp.toLocaleTimeString('es-ES', {
                        hour: '2-digit',

                        minute: '2-digit',
                      })}
                    </p>
                  </div>

                  {mensaje.tipo === 'user' && (
                    <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-gray-300">
                      <User className="h-4 w-4 text-gray-600" />
                    </div>
                  )}
                </div>
              ))
            )}

            {probando && (
              <div className="flex justify-start gap-3">
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-blue-500">
                  <Brain className="h-4 w-4 text-white" />
                </div>

                <div className="rounded-lg border border-gray-200 bg-white p-3">
                  <div className="flex gap-1">
                    <div
                      className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                      style={{ animationDelay: '0ms' }}
                    ></div>

                    <div
                      className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                      style={{ animationDelay: '150ms' }}
                    ></div>

                    <div
                      className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                      style={{ animationDelay: '300ms' }}
                    ></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          <div className="border-t bg-white p-4">
            <div className="flex items-end gap-2">
              <div className="relative flex-1">
                <Textarea
                  ref={textareaRef}
                  value={preguntaPrueba}
                  onChange={e => setPreguntaPrueba(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Escribe tu pregunta aquí... (Presiona Enter para enviar)"
                  rows={3}
                  className="resize-none pr-12"
                  disabled={probando || !config.configured}
                />

                <div className="absolute bottom-2 right-2 text-xs text-gray-400">
                  {preguntaPrueba.length > 0 &&
                    `${preguntaPrueba.length} caracteres`}
                </div>
              </div>

              <Button
                onClick={handleProbar}
                disabled={
                  probando || !preguntaPrueba.trim() || !config.configured
                }
                className="h-[72px] px-4"
              >
                {probando ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <ChevronRight className="h-5 w-5" />
                )}
              </Button>
            </div>

            <div className="mt-2 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="usar-documentos"
                  checked={usarDocumentos}
                  onChange={e => setUsarDocumentos(e.target.checked)}
                  className="rounded"
                />

                <label
                  htmlFor="usar-documentos"
                  className="cursor-pointer text-xs text-gray-600"
                >
                  Usar documentos de contexto
                </label>
              </div>

              <p className="text-xs text-gray-500">
                Enter para enviar • Shift+Enter para nueva línea
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
