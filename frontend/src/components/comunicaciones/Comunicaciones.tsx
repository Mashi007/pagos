import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  MessageSquare,
  Mail,
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
  Plus,
  FileText,
  Clock,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  comunicacionesService,
  ComunicacionUnificada,
  CrearClienteAutomaticoRequest,
} from '@/services/comunicacionesService'
import { CrearClienteForm } from '@/components/clientes/CrearClienteForm'
import { clienteService } from '@/services/clienteService'
import { ticketsService, TicketCreate } from '@/services/ticketsService'
import { formatDate } from '@/utils'
import { toast } from 'sonner'
import { useSimpleAuth } from '@/store/simpleAuthStore'

interface ComunicacionesProps {
  clienteId?: number
  mostrarFiltros?: boolean
  mostrarEstadisticas?: boolean
}

export function Comunicaciones({
  clienteId,
  mostrarFiltros = true,
  mostrarEstadisticas = false,
}: ComunicacionesProps) {
  const { user } = useSimpleAuth()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)
  const [tipoFiltro, setTipoFiltro] = useState<'all' | 'whatsapp' | 'email'>('all')
  const [requiereRespuesta, setRequiereRespuesta] = useState<boolean | undefined>(undefined)
  const [direccionFiltro, setDireccionFiltro] = useState<'INBOUND' | 'OUTBOUND' | undefined>(undefined)
  const [busqueda, setBusqueda] = useState('')
  const [tabActivo, setTabActivo] = useState<'todas' | 'por-responder'>('todas')

  // Estado para envío de mensajes
  const [contactoDestino, setContactoDestino] = useState('')
  const [tipoContacto, setTipoContacto] = useState<'whatsapp' | 'email'>('whatsapp')
  const [mensajeTexto, setMensajeTexto] = useState('')
  const [asuntoEmail, setAsuntoEmail] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [mostrarCrearCliente, setMostrarCrearCliente] = useState(false)
  const [mostrarCrearTicket, setMostrarCrearTicket] = useState(false)
  const [comunicacionParaTicket, setComunicacionParaTicket] = useState<ComunicacionUnificada | null>(null)
  const [creandoTicket, setCreandoTicket] = useState(false)
  const [creandoClienteAuto, setCreandoClienteAuto] = useState(false)
  const [ticketForm, setTicketForm] = useState({
    titulo: '',
    descripcion: '',
    tipo: 'consulta',
    prioridad: 'media',
    estado: 'abierto',
  })
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
      // Obtener información del cliente
      clienteService.getCliente(String(clienteId))
        .then((cliente) => {
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
          if (cliente.telefono) {
            setContactoDestino(cliente.telefono)
            setTipoContacto('whatsapp')
          } else if (cliente.email) {
            setContactoDestino(cliente.email)
            setTipoContacto('email')
          }
        })
        .catch((error) => {
          console.error('Error obteniendo cliente:', error)
        })
    }
  }, [clienteId])

  // Query para obtener comunicaciones
  const {
    data: comunicacionesData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['comunicaciones', page, perPage, tipoFiltro, clienteId, requiereRespuesta, direccionFiltro, tabActivo],
    queryFn: () => {
      if (tabActivo === 'por-responder') {
        return comunicacionesService.obtenerComunicacionesPorResponder(page, perPage)
      }
      return comunicacionesService.listarComunicaciones(
        page,
        perPage,
        tipoFiltro === 'all' ? undefined : tipoFiltro,
        clienteId,
        requiereRespuesta,
        direccionFiltro
      )
    },
  })

  const comunicaciones = comunicacionesData?.comunicaciones || []
  const paginacion = comunicacionesData?.paginacion

  // Filtrar comunicaciones por búsqueda local
  const comunicacionesFiltradas = busqueda
    ? comunicaciones.filter(
        (comm) =>
          comm.body?.toLowerCase().includes(busqueda.toLowerCase()) ||
          comm.from_contact.toLowerCase().includes(busqueda.toLowerCase()) ||
          comm.to_contact.toLowerCase().includes(busqueda.toLowerCase()) ||
          comm.subject?.toLowerCase().includes(busqueda.toLowerCase())
      )
    : comunicaciones

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

  // Buscar o crear cliente automáticamente
  const buscarOcrearCliente = async (contacto: string, tipo: 'whatsapp' | 'email'): Promise<boolean> => {
    if (!contacto || contacto.trim().length < 3) {
      setClienteInfo(null)
      return false
    }

    try {
      // Intentar crear cliente automáticamente
      setCreandoClienteAuto(true)
      const request: CrearClienteAutomaticoRequest = {
        nombres: `Cliente desde ${tipo === 'whatsapp' ? 'WhatsApp' : 'Email'}`,
      }
      
      if (tipo === 'whatsapp') {
        request.telefono = contacto
      } else {
        request.email = contacto
      }

      const resultado = await comunicacionesService.crearClienteAutomatico(request)
      
      if (resultado.success && resultado.cliente) {
        setClienteInfo({
          encontrado: true,
          cliente: resultado.cliente,
        })
        toast.success('Cliente creado automáticamente')
        return true
      }
      
      return false
    } catch (error: any) {
      console.error('Error creando cliente automático:', error)
      // Si falla, intentar buscar cliente existente
      try {
        if (tipo === 'whatsapp') {
          const resultado = await clienteService.buscarClientePorTelefono(contacto)
          if (resultado) {
            setClienteInfo({
              encontrado: true,
              cliente: {
                id: resultado.id,
                cedula: resultado.cedula || '',
                nombres: resultado.nombres || '',
                telefono: resultado.telefono || '',
                email: resultado.email || '',
              },
            })
            return true
          }
        }
      } catch (searchError) {
        console.error('Error buscando cliente:', searchError)
      }
      
      setClienteInfo({
        encontrado: false,
        cliente: null,
      })
      return false
    } finally {
      setCreandoClienteAuto(false)
    }
  }

  // Abrir modal para crear ticket desde comunicación
  const handleAbrirCrearTicket = (comunicacion: ComunicacionUnificada) => {
    setComunicacionParaTicket(comunicacion)
    const tipoTexto = comunicacion.tipo === 'whatsapp' ? 'WhatsApp' : 'Email'
    setTicketForm({
      titulo: `Ticket desde ${tipoTexto} - ${comunicacion.from_contact}`,
      descripcion: `Comunicación de ${tipoTexto}:\n\n${comunicacion.subject ? `Asunto: ${comunicacion.subject}\n\n` : ''}${comunicacion.body || '[Sin contenido]'}\n\nFecha: ${formatearFecha(comunicacion.timestamp)}`,
      tipo: 'consulta',
      prioridad: 'media',
      estado: 'abierto',
    })
    setMostrarCrearTicket(true)
  }

  // Crear ticket
  const handleCrearTicket = async () => {
    if (!comunicacionParaTicket) return

    if (!ticketForm.titulo.trim() || !ticketForm.descripcion.trim()) {
      toast.error('Por favor completa el título y descripción del ticket')
      return
    }

    setCreandoTicket(true)
    try {
      const ticketData: TicketCreate = {
        titulo: ticketForm.titulo,
        descripcion: ticketForm.descripcion,
        tipo: ticketForm.tipo,
        prioridad: ticketForm.prioridad,
        estado: ticketForm.estado,
        cliente_id: comunicacionParaTicket.cliente_id || undefined,
        conversacion_whatsapp_id: comunicacionParaTicket.tipo === 'whatsapp' ? comunicacionParaTicket.id : undefined,
        comunicacion_email_id: comunicacionParaTicket.tipo === 'email' ? comunicacionParaTicket.id : undefined,
        asignado_a: user ? `${user.nombre} ${user.apellido}` : undefined,
        asignado_a_id: user?.id,
      }

      const ticket = await ticketsService.createTicket(ticketData)
      toast.success(`Ticket #${ticket.id} creado exitosamente`)
      setMostrarCrearTicket(false)
      setComunicacionParaTicket(null)
      setTicketForm({
        titulo: '',
        descripcion: '',
        tipo: 'consulta',
        prioridad: 'media',
        estado: 'abierto',
      })
      // Refrescar comunicaciones
      queryClient.invalidateQueries({ queryKey: ['comunicaciones'] })
    } catch (error: any) {
      console.error('Error creando ticket:', error)
      toast.error(error?.response?.data?.detail || 'Error creando ticket')
    } finally {
      setCreandoTicket(false)
    }
  }

  // Estadísticas rápidas
  const estadisticas = {
    total: comunicaciones.length,
    porResponder: comunicaciones.filter(c => c.requiere_respuesta).length,
    whatsapp: comunicaciones.filter(c => c.tipo === 'whatsapp').length,
    email: comunicaciones.filter(c => c.tipo === 'email').length,
  }

  return (
    <div className="space-y-6">
      {/* Header con estadísticas */}
      {mostrarEstadisticas && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-blue-700 font-medium">Total Comunicaciones</p>
                  <p className="text-3xl font-bold text-blue-900">{estadisticas.total}</p>
                </div>
                <MessageSquare className="h-10 w-10 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-orange-700 font-medium">Por Responder</p>
                  <p className="text-3xl font-bold text-orange-900">{estadisticas.porResponder}</p>
                </div>
                <Clock className="h-10 w-10 text-orange-600" />
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-green-700 font-medium">WhatsApp</p>
                  <p className="text-3xl font-bold text-green-900">{estadisticas.whatsapp}</p>
                </div>
                <MessageSquare className="h-10 w-10 text-green-600" />
              </div>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-purple-700 font-medium">Email</p>
                  <p className="text-3xl font-bold text-purple-900">{estadisticas.email}</p>
                </div>
                <Mail className="h-10 w-10 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tabs para Todas / Por Responder */}
      <Tabs value={tabActivo} onValueChange={(v) => setTabActivo(v as 'todas' | 'por-responder')}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="todas" className="flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Todas las Comunicaciones
          </TabsTrigger>
          <TabsTrigger value="por-responder" className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            Por Responder ({estadisticas.porResponder})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="todas" className="space-y-4">
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
                        placeholder="Buscar en comunicaciones..."
                        value={busqueda}
                        onChange={(e) => setBusqueda(e.target.value)}
                        className="pl-8"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600 mb-1 block">Tipo</label>
                    <Select value={tipoFiltro} onValueChange={(v) => setTipoFiltro(v as any)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos</SelectItem>
                        <SelectItem value="whatsapp">WhatsApp</SelectItem>
                        <SelectItem value="email">Email</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <label className="text-sm text-gray-600 mb-1 block">Dirección</label>
                    <Select
                      value={direccionFiltro || 'all'}
                      onValueChange={(v) => setDireccionFiltro(v === 'all' ? undefined : v as any)}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todas</SelectItem>
                        <SelectItem value="INBOUND">Recibidas</SelectItem>
                        <SelectItem value="OUTBOUND">Enviadas</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex items-end">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setTipoFiltro('all')
                        setDireccionFiltro(undefined)
                        setBusqueda('')
                        setRequiereRespuesta(undefined)
                      }}
                      className="w-full"
                    >
                      Limpiar
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Lista de comunicaciones */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="h-5 w-5" />
                    Comunicaciones
                  </CardTitle>
                  <CardDescription>
                    {paginacion ? `${paginacion.total} comunicaciones encontradas` : 'Cargando...'}
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
                  <p className="text-red-600">Error cargando comunicaciones</p>
                  <Button variant="outline" onClick={() => refetch()} className="mt-4">
                    Reintentar
                  </Button>
                </div>
              ) : comunicacionesFiltradas.length === 0 ? (
                <div className="text-center py-12">
                  <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                  <p className="text-gray-500">No hay comunicaciones disponibles</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {comunicacionesFiltradas.map((comunicacion) => (
                    <div
                      key={`${comunicacion.tipo}-${comunicacion.id}`}
                      className={`border rounded-lg p-4 transition-all hover:shadow-md ${
                        comunicacion.direccion === 'INBOUND'
                          ? comunicacion.requiere_respuesta
                            ? 'bg-orange-50 border-orange-300 border-2'
                            : 'bg-blue-50 border-blue-200'
                          : 'bg-green-50 border-green-200'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2 flex-wrap">
                          {comunicacion.tipo === 'whatsapp' ? (
                            <MessageSquare className="h-5 w-5 text-green-600" />
                          ) : (
                            <Mail className="h-5 w-5 text-purple-600" />
                          )}
                          <Badge variant={comunicacion.direccion === 'INBOUND' ? 'default' : 'secondary'}>
                            {comunicacion.direccion === 'INBOUND' ? 'Recibida' : 'Enviada'}
                          </Badge>
                          <Badge variant="outline" className="bg-white">
                            {comunicacion.tipo === 'whatsapp' ? 'WhatsApp' : 'Email'}
                          </Badge>
                          {comunicacion.requiere_respuesta && (
                            <Badge variant="destructive" className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              Requiere Respuesta
                            </Badge>
                          )}
                          {comunicacion.respuesta_enviada && (
                            <Badge variant="outline" className="bg-green-100">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Respondido
                            </Badge>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatearFecha(comunicacion.timestamp)}
                        </div>
                      </div>

                      <div className="space-y-2">
                        {comunicacion.subject && (
                          <div className="font-semibold text-gray-900">{comunicacion.subject}</div>
                        )}
                        <div className="flex items-center gap-2 text-sm text-gray-600">
                          {comunicacion.tipo === 'whatsapp' ? (
                            <Phone className="h-3 w-3" />
                          ) : (
                            <Mail className="h-3 w-3" />
                          )}
                          <span>
                            {comunicacion.direccion === 'INBOUND'
                              ? `De: ${comunicacion.from_contact}`
                              : `Para: ${comunicacion.to_contact}`}
                          </span>
                        </div>

                        {comunicacion.cliente_id && (
                          <div className="flex items-center gap-2 text-sm text-gray-600">
                            <User className="h-3 w-3" />
                            <span>Cliente ID: {comunicacion.cliente_id}</span>
                          </div>
                        )}

                        <div className="mt-3 p-3 bg-white rounded border">
                          <p className="text-sm whitespace-pre-wrap">{comunicacion.body || '[Sin contenido]'}</p>
                        </div>

                        {/* Botones de acción */}
                        {comunicacion.direccion === 'INBOUND' && (
                          <div className="mt-3 pt-3 border-t flex gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleAbrirCrearTicket(comunicacion)}
                              className="flex-1"
                            >
                              <FileText className="h-4 w-4 mr-2" />
                              Crear Ticket
                            </Button>
                            {!comunicacion.cliente_id && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={async () => {
                                  const contacto = comunicacion.from_contact
                                  await buscarOcrearCliente(contacto, comunicacion.tipo)
                                }}
                                disabled={creandoClienteAuto}
                                className="flex-1"
                              >
                                {creandoClienteAuto ? (
                                  <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Creando...
                                  </>
                                ) : (
                                  <>
                                    <Plus className="h-4 w-4 mr-2" />
                                    Crear Cliente
                                  </>
                                )}
                              </Button>
                            )}
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
        </TabsContent>

        <TabsContent value="por-responder" className="space-y-4">
          {/* Similar estructura pero solo comunicaciones por responder */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="h-5 w-5 text-orange-600" />
                    Comunicaciones por Responder
                  </CardTitle>
                  <CardDescription>
                    {paginacion ? `${paginacion.total} comunicaciones pendientes` : 'Cargando...'}
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
              ) : comunicacionesFiltradas.length === 0 ? (
                <div className="text-center py-12">
                  <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
                  <p className="text-gray-500">¡No hay comunicaciones pendientes!</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {comunicacionesFiltradas
                    .filter((c) => c.requiere_respuesta)
                    .map((comunicacion) => (
                      <div
                        key={`${comunicacion.tipo}-${comunicacion.id}`}
                        className="border-2 border-orange-300 rounded-lg p-4 bg-orange-50 hover:shadow-md transition-all"
                      >
                        {/* Mismo contenido que en el tab "todas" */}
                        <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-2 flex-wrap">
                          {comunicacion.tipo === 'whatsapp' ? (
                            <MessageSquare className="h-5 w-5 text-green-600" />
                          ) : (
                            <Mail className="h-5 w-5 text-purple-600" />
                          )}
                            <Badge variant="destructive" className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              Requiere Respuesta
                            </Badge>
                          </div>
                          <div className="text-xs text-gray-500">
                            {formatearFecha(comunicacion.timestamp)}
                          </div>
                        </div>
                        <div className="space-y-2">
                          {comunicacion.subject && (
                            <div className="font-semibold text-gray-900">{comunicacion.subject}</div>
                          )}
                          <div className="flex items-center gap-2 text-sm text-gray-600">
                            {comunicacion.tipo === 'whatsapp' ? (
                              <Phone className="h-3 w-3" />
                            ) : (
                              <Mail className="h-3 w-3" />
                            )}
                            <span>De: {comunicacion.from_contact}</span>
                          </div>
                          <div className="mt-3 p-3 bg-white rounded border">
                            <p className="text-sm whitespace-pre-wrap">{comunicacion.body || '[Sin contenido]'}</p>
                          </div>
                          <div className="mt-3 pt-3 border-t flex gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleAbrirCrearTicket(comunicacion)}
                              className="flex-1"
                            >
                              <FileText className="h-4 w-4 mr-2" />
                              Crear Ticket
                            </Button>
                            {!comunicacion.cliente_id && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={async () => {
                                  await buscarOcrearCliente(comunicacion.from_contact, comunicacion.tipo)
                                }}
                                disabled={creandoClienteAuto}
                                className="flex-1"
                              >
                                <Plus className="h-4 w-4 mr-2" />
                                Crear Cliente
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Modal para crear ticket */}
      <Dialog open={mostrarCrearTicket} onOpenChange={setMostrarCrearTicket}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Crear Ticket desde Comunicación</DialogTitle>
            <p className="text-sm text-gray-600 mt-2">
              Crear un ticket de atención vinculado a esta comunicación
            </p>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Título *</label>
              <Input
                value={ticketForm.titulo}
                onChange={(e) => setTicketForm({ ...ticketForm, titulo: e.target.value })}
                placeholder="Ej: Consulta sobre estado de préstamo"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Descripción *</label>
              <Textarea
                value={ticketForm.descripcion}
                onChange={(e) => setTicketForm({ ...ticketForm, descripcion: e.target.value })}
                placeholder="Describe el problema o consulta..."
                rows={6}
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">Tipo</label>
                <Select
                  value={ticketForm.tipo}
                  onValueChange={(value) => setTicketForm({ ...ticketForm, tipo: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="consulta">Consulta</SelectItem>
                    <SelectItem value="incidencia">Incidencia</SelectItem>
                    <SelectItem value="solicitud">Solicitud</SelectItem>
                    <SelectItem value="reclamo">Reclamo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Prioridad</label>
                <Select
                  value={ticketForm.prioridad}
                  onValueChange={(value) => setTicketForm({ ...ticketForm, prioridad: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="baja">Baja</SelectItem>
                    <SelectItem value="media">Media</SelectItem>
                    <SelectItem value="urgente">Urgente</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Estado</label>
                <Select
                  value={ticketForm.estado}
                  onValueChange={(value) => setTicketForm({ ...ticketForm, estado: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="abierto">Abierto</SelectItem>
                    <SelectItem value="en_proceso">En Proceso</SelectItem>
                    <SelectItem value="resuelto">Resuelto</SelectItem>
                    <SelectItem value="cerrado">Cerrado</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            {comunicacionParaTicket && (
              <div className="p-3 bg-blue-50 rounded border border-blue-200">
                <p className="text-xs text-blue-700 mb-1">
                  <strong>Comunicación vinculada:</strong> {comunicacionParaTicket.from_contact} ({comunicacionParaTicket.tipo})
                </p>
                {comunicacionParaTicket.cliente_id && (
                  <p className="text-xs text-blue-700">
                    <strong>Cliente ID:</strong> {comunicacionParaTicket.cliente_id}
                  </p>
                )}
              </div>
            )}
            <div className="flex justify-end gap-2 pt-4">
              <Button
                variant="outline"
                onClick={() => {
                  setMostrarCrearTicket(false)
                  setComunicacionParaTicket(null)
                }}
                disabled={creandoTicket}
              >
                Cancelar
              </Button>
              <Button onClick={handleCrearTicket} disabled={creandoTicket || !ticketForm.titulo.trim() || !ticketForm.descripcion.trim()}>
                {creandoTicket ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creando...
                  </>
                ) : (
                  <>
                    <FileText className="h-4 w-4 mr-2" />
                    Crear Ticket
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

