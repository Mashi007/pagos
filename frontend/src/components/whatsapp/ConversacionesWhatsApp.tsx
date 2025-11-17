import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  MessageSquare,
  Send,
  Inbox,
  Phone,
  Calendar,
  User,
  Loader2,
  RefreshCw,
  Search,
  Filter,
  AlertCircle,
  CheckCircle,
  XCircle,
  Bot,
  UserPlus,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import {
  conversacionesWhatsAppService,
  ConversacionWhatsApp,
  FiltrosConversaciones,
} from '@/services/conversacionesWhatsAppService'
import { CrearClienteForm } from '@/components/clientes/CrearClienteForm'
import { clienteService } from '@/services/clienteService'
import { formatDate } from '@/utils'
import { toast } from 'sonner'

interface ConversacionesWhatsAppProps {
  clienteId?: number
  numeroTelefono?: string
  mostrarFiltros?: boolean
  mostrarEstadisticas?: boolean
}

export function ConversacionesWhatsApp({
  clienteId,
  numeroTelefono,
  mostrarFiltros = true,
  mostrarEstadisticas = false,
}: ConversacionesWhatsAppProps) {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)
  const [filtros, setFiltros] = useState<FiltrosConversaciones>({})
  const [busqueda, setBusqueda] = useState('')
  
  // Estado para envío de mensajes
  const [numeroDestino, setNumeroDestino] = useState(numeroTelefono || '')
  const [mensajeTexto, setMensajeTexto] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [mostrarCrearCliente, setMostrarCrearCliente] = useState(false)
  const [clienteInfo, setClienteInfo] = useState<{
    encontrado: boolean
    cliente: {
      id: number
      cedula: string
      nombres: string
      telefono: string
      email: string
    } | null
  } | null>(null)

  // Si hay clienteId, filtrar por cliente
  useEffect(() => {
    if (clienteId) {
      setFiltros((prev) => ({ ...prev, cliente_id: clienteId }))
    } else {
      setFiltros((prev) => {
        const { cliente_id, ...rest } = prev
        return rest
      })
    }
  }, [clienteId])

  // Si hay numeroTelefono, filtrar por número
  useEffect(() => {
    if (numeroTelefono) {
      setFiltros((prev) => ({ ...prev, from_number: numeroTelefono }))
      setNumeroDestino(numeroTelefono)
      buscarCliente(numeroTelefono)
    } else {
      setFiltros((prev) => {
        const { from_number, ...rest } = prev
        return rest
      })
    }
  }, [numeroTelefono])

  // Si hay clienteId, obtener información del cliente
  useEffect(() => {
    if (clienteId) {
      // Obtener información del cliente para mostrar su número
      clienteService.getCliente(String(clienteId))
        .then((cliente) => {
          if (cliente.telefono) {
            setNumeroDestino(cliente.telefono)
            buscarCliente(cliente.telefono)
            setClienteInfo({
              encontrado: true,
              cliente: {
                id: cliente.id,
                cedula: cliente.cedula || '',
                nombres: cliente.nombres || '',
                telefono: cliente.telefono || '',
                email: cliente.email || '',
              },
            })
          }
        })
        .catch((error) => {
          console.error('Error obteniendo cliente:', error)
        })
    }
  }, [clienteId])

  // Query para obtener conversaciones
  const {
    data: conversacionesData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['conversaciones-whatsapp', page, perPage, filtros],
    queryFn: () => {
      if (clienteId) {
        return conversacionesWhatsAppService.obtenerConversacionesCliente(clienteId, page, perPage)
      } else if (numeroTelefono) {
        return conversacionesWhatsAppService.obtenerConversacionesNumero(numeroTelefono, page, perPage)
      } else {
        return conversacionesWhatsAppService.listarConversaciones(page, perPage, filtros)
      }
    },
  })

  // Query para estadísticas (solo si se solicita)
  const { data: estadisticas } = useQuery({
    queryKey: ['conversaciones-whatsapp-estadisticas'],
    queryFn: () => conversacionesWhatsAppService.obtenerEstadisticas(),
    enabled: mostrarEstadisticas,
  })

  const conversaciones = conversacionesData?.conversaciones || []
  const paginacion = conversacionesData?.paginacion

  const handleFiltroChange = (key: keyof FiltrosConversaciones, value: any) => {
    setFiltros((prev) => ({ ...prev, [key]: value || undefined }))
    setPage(1) // Resetear a primera página
  }

  const limpiarFiltros = () => {
    setFiltros({})
    setBusqueda('')
    setPage(1)
  }

  // Filtrar conversaciones por búsqueda local
  const conversacionesFiltradas = busqueda
    ? conversaciones.filter(
        (conv) =>
          conv.body?.toLowerCase().includes(busqueda.toLowerCase()) ||
          conv.from_number.includes(busqueda) ||
          conv.to_number.includes(busqueda)
      )
    : conversaciones

  const formatearFecha = (fecha: string) => {
    try {
      const date = new Date(fecha)
      return date.toLocaleString('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return fecha
    }
  }

  // Buscar cliente cuando cambia el número de destino
  const buscarCliente = async (numero: string): Promise<boolean> => {
    if (!numero || numero.trim().length < 8) {
      setClienteInfo(null)
      return false
    }

    try {
      const resultado = await conversacionesWhatsAppService.buscarClientePorNumero(numero)
      setClienteInfo({
        encontrado: resultado.cliente_encontrado,
        cliente: resultado.cliente,
      })
      return resultado.cliente_encontrado
    } catch (error) {
      console.error('Error buscando cliente:', error)
      setClienteInfo(null)
      return false
    }
  }

  // Enviar mensaje
  const handleEnviarMensaje = async () => {
    if (!numeroDestino.trim() || !mensajeTexto.trim()) {
      toast.error('Por favor ingresa un número de teléfono y un mensaje')
      return
    }

    // Buscar cliente primero
    const resultadoBusqueda = await buscarCliente(numeroDestino)
    
    // Esperar un momento para que el estado se actualice
    await new Promise(resolve => setTimeout(resolve, 100))
    
    // Verificar si el cliente existe
    const clienteActual = clienteInfo?.cliente || (clienteId ? { id: clienteId } : null)
    
    // Si no hay cliente y no se está mostrando el modal, mostrarlo
    if (!clienteActual && !clienteId) {
      // Buscar nuevamente para obtener el estado actualizado
      const busquedaActualizada = await conversacionesWhatsAppService.buscarClientePorNumero(numeroDestino)
      if (!busquedaActualizada.cliente_encontrado) {
        setMostrarCrearCliente(true)
        toast.warning('Cliente no encontrado. Por favor crea el cliente primero.')
        return
      } else {
        // Si se encontró, actualizar el estado
        setClienteInfo({
          encontrado: true,
          cliente: busquedaActualizada.cliente,
        })
      }
    }

    // Si hay cliente o se está creando, enviar mensaje
    setEnviando(true)
    try {
      const clienteIdParaEnvio = clienteInfo?.cliente?.id || clienteId
      const resultado = await conversacionesWhatsAppService.enviarMensaje(
        numeroDestino.trim(),
        mensajeTexto.trim(),
        clienteIdParaEnvio || undefined
      )

      if (resultado.success) {
        toast.success('Mensaje enviado exitosamente')
        setMensajeTexto('')
        // Refrescar conversaciones
        queryClient.invalidateQueries({ queryKey: ['conversaciones-whatsapp'] })
        refetch()
      } else {
        toast.error('Error enviando mensaje')
      }
    } catch (error: any) {
      console.error('Error enviando mensaje:', error)
      // Si el error es que no hay cliente, mostrar modal
      if (error?.response?.status === 400 && error?.response?.data?.detail?.includes('cliente')) {
        setMostrarCrearCliente(true)
        toast.warning('Cliente no encontrado. Por favor crea el cliente primero.')
      } else {
        toast.error(error?.response?.data?.detail || 'Error enviando mensaje')
      }
    } finally {
      setEnviando(false)
    }
  }

  // Cuando se crea un cliente nuevo, actualizar la info
  const handleClienteCreado = async (clienteCreado: any) => {
    setMostrarCrearCliente(false)
    setClienteInfo({
      encontrado: true,
      cliente: {
        id: clienteCreado.id,
        cedula: clienteCreado.cedula,
        nombres: clienteCreado.nombres,
        telefono: clienteCreado.telefono,
        email: clienteCreado.email || '',
      },
    })
    // Intentar enviar el mensaje nuevamente
    if (mensajeTexto.trim()) {
      await handleEnviarMensaje()
    }
  }

  // Efecto para buscar cliente cuando cambia el número
  useEffect(() => {
    if (numeroDestino && numeroDestino.trim().length >= 8) {
      const timeoutId = setTimeout(() => {
        buscarCliente(numeroDestino)
      }, 500) // Debounce
      return () => clearTimeout(timeoutId)
    }
  }, [numeroDestino])

  return (
    <div className="space-y-4">
      {/* Estadísticas */}
      {mostrarEstadisticas && estadisticas && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total</p>
                  <p className="text-2xl font-bold">{estadisticas.total}</p>
                </div>
                <MessageSquare className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Recibidos</p>
                  <p className="text-2xl font-bold text-green-600">{estadisticas.inbound}</p>
                </div>
                <Inbox className="h-8 w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Enviados</p>
                  <p className="text-2xl font-bold text-blue-600">{estadisticas.outbound}</p>
                </div>
                <Send className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Últimas 24h</p>
                  <p className="text-2xl font-bold text-purple-600">{estadisticas.ultimas_24h}</p>
                </div>
                <Calendar className="h-8 w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filtros */}
      {mostrarFiltros && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5" />
              Filtros
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="text-sm text-gray-600 mb-1 block">Búsqueda</label>
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Buscar en mensajes..."
                    value={busqueda}
                    onChange={(e) => setBusqueda(e.target.value)}
                    className="pl-8"
                  />
                </div>
              </div>
              {!clienteId && (
                <div>
                  <label className="text-sm text-gray-600 mb-1 block">Número de teléfono</label>
                  <Input
                    placeholder="Número..."
                    value={filtros.from_number || ''}
                    onChange={(e) => handleFiltroChange('from_number', e.target.value)}
                  />
                </div>
              )}
              {!clienteId && (
                <div>
                  <label className="text-sm text-gray-600 mb-1 block">Dirección</label>
                  <Select
                    value={filtros.direccion || 'all'}
                    onValueChange={(value) => handleFiltroChange('direccion', value === 'all' ? undefined : value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Todas" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todas</SelectItem>
                      <SelectItem value="INBOUND">Recibidos</SelectItem>
                      <SelectItem value="OUTBOUND">Enviados</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
              <div className="flex items-end">
                <Button variant="outline" onClick={limpiarFiltros} className="w-full">
                  Limpiar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Lista de conversaciones */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Conversaciones de WhatsApp
              </CardTitle>
              <CardDescription>
                {paginacion ? `${paginacion.total} conversaciones encontradas` : 'Cargando...'}
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              Actualizar
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
              <p className="text-red-600">Error cargando conversaciones</p>
              <Button variant="outline" onClick={() => refetch()} className="mt-4">
                Reintentar
              </Button>
            </div>
          ) : conversacionesFiltradas.length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p className="text-gray-500">No hay conversaciones disponibles</p>
            </div>
          ) : (
            <div className="space-y-4">
              {conversacionesFiltradas.map((conversacion) => (
                <div
                  key={conversacion.id}
                  className={`border rounded-lg p-4 ${
                    conversacion.direccion === 'INBOUND'
                      ? 'bg-blue-50 border-blue-200'
                      : 'bg-green-50 border-green-200'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {conversacion.direccion === 'INBOUND' ? (
                        <Inbox className="h-4 w-4 text-blue-600" />
                      ) : (
                        <Send className="h-4 w-4 text-green-600" />
                      )}
                      <Badge
                        variant={conversacion.direccion === 'INBOUND' ? 'default' : 'secondary'}
                      >
                        {conversacion.direccion === 'INBOUND' ? 'Recibido' : 'Enviado'}
                      </Badge>
                      {conversacion.direccion === 'OUTBOUND' && (
                        <Badge variant="outline" className="bg-green-100">
                          <Bot className="h-3 w-3 mr-1" />
                          Bot
                        </Badge>
                      )}
                      {conversacion.respuesta_enviada && conversacion.direccion === 'INBOUND' && (
                        <Badge variant="outline" className="bg-green-100">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Respondido
                        </Badge>
                      )}
                    </div>
                    <div className="text-xs text-gray-500">
                      {formatearFecha(conversacion.timestamp)}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Phone className="h-3 w-3" />
                      <span>
                        {conversacion.direccion === 'INBOUND'
                          ? `De: ${conversacion.from_number}`
                          : `Para: ${conversacion.to_number}`}
                      </span>
                    </div>

                    {conversacion.cliente_id && (
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <User className="h-3 w-3" />
                        <span>Cliente ID: {conversacion.cliente_id}</span>
                      </div>
                    )}

                    <div className="mt-3 p-3 bg-white rounded border">
                      <p className="text-sm whitespace-pre-wrap">{conversacion.body || '[Sin contenido]'}</p>
                    </div>

                    {conversacion.error && (
                      <div className="flex items-center gap-2 text-sm text-red-600 mt-2">
                        <XCircle className="h-4 w-4" />
                        <span>Error: {conversacion.error}</span>
                      </div>
                    )}

                    {conversacion.respuesta_bot && conversacion.direccion === 'INBOUND' && (
                      <div className="mt-2 p-3 bg-green-100 rounded border border-green-200">
                        <div className="flex items-center gap-2 mb-1">
                          <Bot className="h-3 w-3 text-green-700" />
                          <span className="text-xs font-semibold text-green-700">Respuesta del Bot:</span>
                        </div>
                        <p className="text-sm text-green-900 whitespace-pre-wrap">
                          {conversacion.respuesta_bot}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Paginación */}
              {paginacion && paginacion.pages > 1 && (
                <div className="flex items-center justify-between pt-4 border-t">
                  <div className="text-sm text-gray-600">
                    Página {paginacion.page} de {paginacion.pages} ({paginacion.total} total)
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      Anterior
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(paginacion.pages, p + 1))}
                      disabled={page === paginacion.pages}
                    >
                      Siguiente
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Área de envío de mensajes */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Send className="h-5 w-5" />
            Enviar Mensaje
          </CardTitle>
          <CardDescription>
            {clienteInfo?.encontrado && clienteInfo.cliente ? (
              <span className="text-green-600 flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                Cliente encontrado: {clienteInfo.cliente.nombres} (ID: {clienteInfo.cliente.id})
              </span>
            ) : clienteInfo && !clienteInfo.encontrado ? (
              <span className="text-orange-600 flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                Cliente no encontrado. Debes crear el cliente primero.
              </span>
            ) : (
              'Ingresa un número de teléfono para buscar el cliente'
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Número de Teléfono</label>
              <div className="flex gap-2">
                <Input
                  placeholder="Ej: +584123456789"
                  value={numeroDestino}
                  onChange={(e) => setNumeroDestino(e.target.value)}
                  disabled={!!numeroTelefono} // Si viene desde props, no se puede cambiar
                />
                {clienteInfo && !clienteInfo.encontrado && (
                  <Button
                    variant="outline"
                    onClick={() => setMostrarCrearCliente(true)}
                    className="whitespace-nowrap"
                  >
                    <UserPlus className="h-4 w-4 mr-2" />
                    Crear Cliente
                  </Button>
                )}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Mensaje</label>
              <Textarea
                placeholder="Escribe tu mensaje aquí..."
                value={mensajeTexto}
                onChange={(e) => setMensajeTexto(e.target.value)}
                rows={4}
                className="resize-none"
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setMensajeTexto('')
                  setNumeroDestino(numeroTelefono || '')
                }}
                disabled={enviando}
              >
                Limpiar
              </Button>
              <Button
                onClick={handleEnviarMensaje}
                disabled={enviando || !numeroDestino.trim() || !mensajeTexto.trim()}
              >
                {enviando ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Enviando...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Enviar Mensaje
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Modal para crear cliente nuevo */}
      <Dialog open={mostrarCrearCliente} onOpenChange={setMostrarCrearCliente}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Crear Cliente Nuevo</DialogTitle>
            <DialogDescription>
              El cliente con el número {numeroDestino} no existe. Por favor crea el cliente primero para poder enviar mensajes.
            </DialogDescription>
          </DialogHeader>
          <CrearClienteForm
            cliente={{
              telefono: numeroDestino,
            }}
            onClose={() => setMostrarCrearCliente(false)}
            onSuccess={async () => {
              // Buscar el cliente recién creado
              await buscarCliente(numeroDestino)
              setMostrarCrearCliente(false)
              toast.success('Cliente creado exitosamente. Ahora puedes enviar el mensaje.')
            }}
            onClienteCreated={handleClienteCreado}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}

