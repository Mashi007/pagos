import { useState, useEffect, useMemo } from 'react'
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
  AlertCircle,
  CheckCircle,
  XCircle,
  Plus,
  FileText,
  Clock,
  X,
  Upload,
  Zap,
  Settings,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import {
  comunicacionesService,
  ComunicacionUnificada,
  CrearClienteAutomaticoRequest,
} from '@/services/comunicacionesService'
import { CrearClienteForm } from '@/components/clientes/CrearClienteForm'
import { clienteService } from '@/services/clienteService'
import { ticketsService, TicketCreate, Ticket, TicketUpdate } from '@/services/ticketsService'
import { userService } from '@/services/userService'
import { formatDate } from '@/utils'
import { toast } from 'sonner'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { mockComunicaciones, mockNombresClientes } from '@/data/mockComunicaciones'
import { conversacionesWhatsAppService } from '@/services/conversacionesWhatsAppService'

interface ComunicacionesProps {
  clienteId?: number
  mostrarFiltros?: boolean
  mostrarEstadisticas?: boolean
}

// Interfaz para conversaciones agrupadas (separadas por tipo)
interface ConversacionAgrupada {
  id: string // Identificador único: cliente_id_tipo o contacto_tipo
  nombre: string
  contacto: string
  tipo: 'whatsapp' | 'email' // NO mixto - separadas
  cliente_id: number | null
  esNuevo: boolean // No está en base de datos
  leido: boolean // Si está leído (procesado = true)
  noLeidos: number
  ultimaComunicacion: ComunicacionUnificada
  comunicaciones: ComunicacionUnificada[] // Solo se cargan cuando se selecciona
}

export function Comunicaciones({
  clienteId,
  mostrarFiltros = true,
  mostrarEstadisticas = false,
}: ComunicacionesProps) {
  const { user } = useSimpleAuth()
  const queryClient = useQueryClient()
  const [busqueda, setBusqueda] = useState('')
  
  // Estado para selección
  const [conversacionSeleccionada, setConversacionSeleccionada] = useState<string | null>(null)
  const [comunicacionSeleccionada, setComunicacionSeleccionada] = useState<ComunicacionUnificada | null>(null)
  
  // Estado para carga de mensajes (solo cuando se selecciona)
  const [mensajesCargados, setMensajesCargados] = useState<Map<string, ComunicacionUnificada[]>>(new Map())
  const [cargandoMensajes, setCargandoMensajes] = useState<string | null>(null)
  
  // Estado para envío de mensajes
  const [mensajeTexto, setMensajeTexto] = useState('')
  const [asuntoEmail, setAsuntoEmail] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [modoAutomatico, setModoAutomatico] = useState(true) // Automático por defecto
  
  // Estado para creación de cliente y ticket
  const [mostrarCrearCliente, setMostrarCrearCliente] = useState(false)
  const [creandoClienteAuto, setCreandoClienteAuto] = useState(false)
  const [clienteRecienCreado, setClienteRecienCreado] = useState<{ contacto: string; tipo: string } | null>(null)
  const [ticketForm, setTicketForm] = useState({
    titulo: '',
    descripcion: '',
    tipo: 'consulta',
    prioridad: 'media',
    estado: 'abierto',
    fecha_limite: '',
    responsable_id: user?.id || undefined,
    archivos: [] as File[],
  })
  const [creandoTicket, setCreandoTicket] = useState(false)
  const [ticketsCliente, setTicketsCliente] = useState<Ticket[]>([])
  const [ticketEditando, setTicketEditando] = useState<Ticket | null>(null)
  
  // Estado para usuarios (para asignación y escalación)
  const [usuarios, setUsuarios] = useState<Array<{ id: number; nombre: string; apellido: string; email: string; is_admin: boolean }>>([])

  // Query para obtener todas las comunicaciones (sin paginación para agrupar)
  const {
    data: comunicacionesData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['comunicaciones', clienteId],
    queryFn: () => comunicacionesService.listarComunicaciones(1, 1000, undefined, clienteId),
  })

  // Usar mockdata si no hay datos reales (en desarrollo siempre, en producción solo si no hay datos)
  const usarMockData = (!comunicacionesData?.comunicaciones || comunicacionesData.comunicaciones.length === 0) || process.env.NODE_ENV === 'development'
  const todasComunicaciones = usarMockData && (!comunicacionesData?.comunicaciones || comunicacionesData.comunicaciones.length === 0) 
    ? mockComunicaciones 
    : (comunicacionesData?.comunicaciones || [])

  // Cargar usuarios al montar
  useEffect(() => {
    const cargarUsuarios = async () => {
      try {
        const response = await userService.listarUsuarios(1, 100, true)
        setUsuarios(response.items || [])
      } catch (error) {
        console.error('Error cargando usuarios:', error)
      }
    }
    cargarUsuarios()
  }, [])

  // Agrupar comunicaciones por cliente/contacto Y TIPO (separadas)
  // PRIMERO por leído/no leído, LUEGO por fecha/hora
  const conversacionesAgrupadas = useMemo(() => {
    const grupos = new Map<string, ConversacionAgrupada>()

    todasComunicaciones.forEach((comm) => {
      // Identificador: cliente_id_tipo o contacto_tipo (SEPARADAS por tipo)
      const idBase = comm.cliente_id ? `cliente_${comm.cliente_id}` : `contacto_${comm.from_contact}`
      const id = `${idBase}_${comm.tipo}` // Separar WhatsApp y Email
      
      if (!grupos.has(id)) {
        // Determinar nombre del cliente o contacto
        let nombre = comm.from_contact
        let esNuevo = !comm.cliente_id
        
        // Si tiene cliente_id, intentar obtener nombre del cliente
        if (comm.cliente_id) {
          // Usar nombre del mockdata si está disponible
          nombre = mockNombresClientes[comm.cliente_id] || `Cliente #${comm.cliente_id}`
        }

        // Determinar si está leído (procesado = true)
        const leido = comm.procesado

        grupos.set(id, {
          id,
          nombre,
          contacto: comm.from_contact,
          tipo: comm.tipo,
          cliente_id: comm.cliente_id,
          esNuevo,
          leido,
          noLeidos: 0,
          ultimaComunicacion: comm,
          comunicaciones: [], // Se cargarán cuando se seleccione
        })
      }

      const grupo = grupos.get(id)!
      
      // Actualizar última comunicación (más reciente)
      if (new Date(comm.timestamp) > new Date(grupo.ultimaComunicacion.timestamp)) {
        grupo.ultimaComunicacion = comm
        grupo.leido = comm.procesado // Actualizar estado de leído
      }
      
      // Contar no leídos (requiere_respuesta y no procesado)
      if (comm.requiere_respuesta && !comm.procesado) {
        grupo.noLeidos++
      }
    })

    // Convertir a array y ordenar: PRIMERO por leído/no leído, LUEGO por fecha/hora
    const conversacionesArray = Array.from(grupos.values())
    
    // Separar en dos grupos: no leídos y leídos
    const noLeidos = conversacionesArray.filter(c => !c.leido || c.noLeidos > 0)
    const leidos = conversacionesArray.filter(c => c.leido && c.noLeidos === 0)
    
    // Ordenar cada grupo por fecha/hora (más reciente primero)
    noLeidos.sort((a, b) => {
      const fechaA = new Date(a.ultimaComunicacion.timestamp).getTime()
      const fechaB = new Date(b.ultimaComunicacion.timestamp).getTime()
      return fechaB - fechaA
    })
    
    leidos.sort((a, b) => {
      const fechaA = new Date(a.ultimaComunicacion.timestamp).getTime()
      const fechaB = new Date(b.ultimaComunicacion.timestamp).getTime()
      return fechaB - fechaA
    })
    
    // Combinar: primero no leídos, luego leídos
    return [...noLeidos, ...leidos]
  }, [todasComunicaciones])

  // Filtrar conversaciones por búsqueda
  const conversacionesFiltradas = useMemo(() => {
    if (!busqueda) return conversacionesAgrupadas
    
    const busquedaLower = busqueda.toLowerCase()
    return conversacionesAgrupadas.filter(
      (conv) =>
        conv.nombre.toLowerCase().includes(busquedaLower) ||
        conv.contacto.toLowerCase().includes(busquedaLower) ||
        conv.ultimaComunicacion.body?.toLowerCase().includes(busquedaLower) ||
        conv.ultimaComunicacion.subject?.toLowerCase().includes(busquedaLower)
    )
  }, [conversacionesAgrupadas, busqueda])

  // Obtener conversación seleccionada
  const conversacionActual = useMemo(() => {
    if (!conversacionSeleccionada) return null
    return conversacionesAgrupadas.find((c) => c.id === conversacionSeleccionada) || null
  }, [conversacionSeleccionada, conversacionesAgrupadas])

  // Efecto para buscar conversación actualizada después de crear cliente
  useEffect(() => {
    if (clienteRecienCreado && conversacionesAgrupadas.length > 0) {
      const conversacionActualizada = conversacionesAgrupadas.find(
        (c) => c.contacto === clienteRecienCreado.contacto && c.tipo === clienteRecienCreado.tipo
      )
      if (conversacionActualizada) {
        setConversacionSeleccionada(conversacionActualizada.id)
        setClienteRecienCreado(null) // Limpiar flag
      }
    }
  }, [clienteRecienCreado, conversacionesAgrupadas])

  // Cargar mensajes cuando se selecciona una conversación
  useEffect(() => {
    if (!conversacionActual) return
    
    // Si ya están cargados, no volver a cargar
    if (mensajesCargados.has(conversacionActual.id)) return
    
    // Cargar mensajes de esta conversación específica
    setCargandoMensajes(conversacionActual.id)
    
    const cargarMensajes = async () => {
      try {
        // Filtrar comunicaciones de esta conversación específica
        const mensajes = todasComunicaciones.filter(
          (comm) => {
            const idBase = comm.cliente_id ? `cliente_${comm.cliente_id}` : `contacto_${comm.from_contact}`
            const id = `${idBase}_${comm.tipo}`
            return id === conversacionActual.id
          }
        )
        
        // Ordenar por fecha/hora
        mensajes.sort((a, b) => {
          return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        })
        
        setMensajesCargados(prev => new Map(prev).set(conversacionActual.id, mensajes))
      } catch (error) {
        console.error('Error cargando mensajes:', error)
        toast.error('Error cargando mensajes')
      } finally {
        setCargandoMensajes(null)
      }
    }
    
    cargarMensajes()
  }, [conversacionActual, todasComunicaciones, mensajesCargados])

  // Obtener mensajes de la conversación actual
  const mensajesOrdenados = useMemo(() => {
    if (!conversacionActual) return []
    return mensajesCargados.get(conversacionActual.id) || []
  }, [conversacionActual, mensajesCargados])

  // Cargar tickets del cliente cuando se selecciona una conversación
  useEffect(() => {
    if (conversacionActual?.cliente_id) {
      ticketsService
        .getTickets({ cliente_id: conversacionActual.cliente_id })
        .then((response) => {
          setTicketsCliente(response.tickets || [])
        })
        .catch((error) => {
          console.error('Error cargando tickets:', error)
          setTicketsCliente([])
        })
    } else {
      setTicketsCliente([])
    }
  }, [conversacionActual])

  // Seleccionar conversación
  const handleSeleccionarConversacion = (conversacion: ConversacionAgrupada) => {
    setConversacionSeleccionada(conversacion.id)
    setComunicacionSeleccionada(conversacion.ultimaComunicacion)
    setTicketEditando(null)
  }

  // Crear cliente automáticamente
  const handleCrearCliente = async (conversacion: ConversacionAgrupada) => {
    setCreandoClienteAuto(true)
    try {
      const request: CrearClienteAutomaticoRequest = {
        nombres: conversacion.nombre,
      }
      
      if (conversacion.tipo === 'whatsapp') {
        request.telefono = conversacion.contacto
      } else if (conversacion.tipo === 'email') {
        request.email = conversacion.contacto
      }

      const resultado = await comunicacionesService.crearClienteAutomatico(request)
      
      if (resultado.success && resultado.cliente) {
        toast.success('Cliente creado exitosamente')
        queryClient.invalidateQueries({ queryKey: ['comunicaciones'] })
        setTimeout(() => refetch(), 500)
      }
    } catch (error: any) {
      console.error('Error creando cliente:', error)
      toast.error(error?.response?.data?.detail || 'Error creando cliente')
    } finally {
      setCreandoClienteAuto(false)
    }
  }

  // Crear ticket desde conversación
  const handleCrearTicket = async () => {
    if (!conversacionActual || !comunicacionSeleccionada) return

    if (!ticketForm.titulo.trim() || !ticketForm.descripcion.trim()) {
      toast.error('Por favor completa el título y descripción del ticket')
      return
    }

    // Si es nuevo, primero crear cliente
    if (conversacionActual.esNuevo) {
      await handleCrearCliente(conversacionActual)
      // Esperar a que se actualice la conversación
      await new Promise(resolve => setTimeout(resolve, 1000))
      await refetch()
      toast.info('Cliente creado. Por favor, crea el ticket nuevamente.')
      return
    }

    setCreandoTicket(true)
    try {
      // Subir archivos si hay
      let archivosJson: string | null = null
      if (ticketForm.archivos.length > 0) {
        // TODO: Implementar subida de archivos
        // Por ahora, solo guardamos los nombres
        archivosJson = JSON.stringify(ticketForm.archivos.map(f => f.name))
      }

      const ticketData: TicketCreate = {
        titulo: ticketForm.titulo,
        descripcion: ticketForm.descripcion,
        tipo: ticketForm.tipo,
        prioridad: ticketForm.prioridad,
        estado: ticketForm.estado,
        cliente_id: conversacionActual.cliente_id || undefined,
        conversacion_whatsapp_id: comunicacionSeleccionada.tipo === 'whatsapp' ? comunicacionSeleccionada.id : undefined,
        comunicacion_email_id: comunicacionSeleccionada.tipo === 'email' ? comunicacionSeleccionada.id : undefined,
        asignado_a: ticketForm.responsable_id ? usuarios.find(u => u.id === ticketForm.responsable_id)?.email : undefined,
        asignado_a_id: ticketForm.responsable_id,
        fecha_limite: ticketForm.fecha_limite || undefined,
        archivos: archivosJson || undefined,
      }

      const ticket = await ticketsService.createTicket(ticketData)
      toast.success(`Ticket #${ticket.id} creado exitosamente`)
      
      // Limpiar formulario
      setTicketForm({
        titulo: '',
        descripcion: '',
        tipo: 'consulta',
        prioridad: 'media',
        estado: 'abierto',
        fecha_limite: '',
        responsable_id: user?.id || undefined,
        archivos: [],
      })
      
      // Refrescar tickets
      if (conversacionActual.cliente_id) {
        const response = await ticketsService.getTickets({ cliente_id: conversacionActual.cliente_id })
        setTicketsCliente(response.tickets || [])
      }
      
      // Refrescar comunicaciones
      queryClient.invalidateQueries({ queryKey: ['comunicaciones'] })
    } catch (error: any) {
      console.error('Error creando ticket:', error)
      toast.error(error?.response?.data?.detail || 'Error creando ticket')
    } finally {
      setCreandoTicket(false)
    }
  }

  // Actualizar ticket (solo campos permitidos)
  const handleActualizarTicket = async (ticket: Ticket) => {
    if (!ticketEditando) return
    
    setCreandoTicket(true)
    try {
      const updateData: TicketUpdate = {
        estado: ticketEditando.estado,
        prioridad: ticketEditando.prioridad,
        asignado_a_id: ticketEditando.asignado_a_id,
        escalado_a_id: ticketEditando.escalado_a_id,
        escalado: ticketEditando.escalado,
        fecha_limite: ticketEditando.fecha_limite,
      }

      await ticketsService.updateTicket(ticket.id, updateData)
      toast.success(`Ticket #${ticket.id} actualizado exitosamente`)
      
      setTicketEditando(null)
      
      // Refrescar tickets
      if (conversacionActual?.cliente_id) {
        const response = await ticketsService.getTickets({ cliente_id: conversacionActual.cliente_id })
        setTicketsCliente(response.tickets || [])
      }
    } catch (error: any) {
      console.error('Error actualizando ticket:', error)
      toast.error(error?.response?.data?.detail || 'Error actualizando ticket')
    } finally {
      setCreandoTicket(false)
    }
  }

  // Enviar mensaje (manual o automático)
  const handleEnviarMensaje = async () => {
    if (!conversacionActual || !mensajeTexto.trim()) return

    setEnviando(true)
    try {
      if (conversacionActual.tipo === 'whatsapp') {
        // Enviar mensaje de WhatsApp
        // El contacto es el número que envió el mensaje (from_contact para INBOUND)
        // Necesitamos obtener el número correcto desde la última comunicación
        const ultimaComunicacion = conversacionActual.ultimaComunicacion
        const numeroDestino = ultimaComunicacion.direccion === 'INBOUND' 
          ? ultimaComunicacion.from_contact 
          : ultimaComunicacion.to_contact
        
        const resultado = await conversacionesWhatsAppService.enviarMensaje(
          numeroDestino,
          mensajeTexto,
          conversacionActual.cliente_id || undefined
        )
        
        if (resultado.success) {
          toast.success('Mensaje enviado exitosamente')
          setMensajeTexto('')
          setAsuntoEmail('')
          // Refrescar comunicaciones
          setTimeout(() => refetch(), 1000)
        } else {
          toast.error('Error enviando mensaje')
        }
      } else if (conversacionActual.tipo === 'email') {
        // TODO: Implementar envío de email
        toast.info('Envío de email en desarrollo')
      }
    } catch (error: any) {
      console.error('Error enviando mensaje:', error)
      toast.error(error?.response?.data?.detail || 'Error enviando mensaje')
    } finally {
      setEnviando(false)
    }
  }

  const formatearFecha = (fecha: string) => {
    try {
      const date = new Date(fecha)
      const ahora = new Date()
      const diffMs = ahora.getTime() - date.getTime()
      const diffMins = Math.floor(diffMs / 60000)
      const diffHours = Math.floor(diffMs / 3600000)
      const diffDays = Math.floor(diffMs / 86400000)

      if (diffMins < 1) return 'Ahora'
      if (diffMins < 60) return `Hace ${diffMins} min`
      if (diffHours < 24) return `Hace ${diffHours} h`
      if (diffDays < 7) return `Hace ${diffDays} días`
      
      return date.toLocaleDateString('es-ES', {
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

  return (
    <div className="flex h-[calc(100vh-120px)] gap-0 bg-white overflow-hidden">
      {/* COLUMNA IZQUIERDA: Lista de conversaciones */}
      <div className="w-80 flex-shrink-0 border-r border-gray-200 flex flex-col bg-white">
        {/* Header con búsqueda */}
        <div className="p-3 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-white">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-bold text-gray-900">Comunicaciones</h2>
            <Button variant="ghost" size="sm" onClick={() => refetch()} disabled={isLoading} className="hover:bg-blue-100">
              <RefreshCw className={`h-4 w-4 text-blue-600 ${isLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Buscar conversaciones..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              className="pl-9 bg-white border-gray-200 focus:border-blue-500 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Lista de conversaciones */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            </div>
          ) : error ? (
            <div className="text-center py-12 px-4">
              <AlertCircle className="h-8 w-8 mx-auto mb-2 text-red-500" />
              <p className="text-sm text-red-600">Error cargando comunicaciones</p>
            </div>
          ) : conversacionesFiltradas.length === 0 ? (
            <div className="text-center py-12 px-4">
              <MessageSquare className="h-8 w-8 mx-auto mb-2 text-gray-400" />
              <p className="text-sm text-gray-500">No hay conversaciones</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {/* Separador visual para no leídos */}
              {conversacionesFiltradas.some(c => !c.leido || c.noLeidos > 0) && (
                <div className="px-4 py-2.5 bg-gradient-to-r from-blue-50 to-blue-100 border-b-2 border-blue-300">
                  <p className="text-xs font-bold text-blue-800 uppercase tracking-wide">No Leídos</p>
                </div>
              )}
              
              {conversacionesFiltradas.map((conversacion, index) => {
                // Mostrar separador de leídos cuando cambia de no leído a leído
                const mostrarSeparadorLeidos = 
                  index > 0 && 
                  (conversacion.leido && conversacion.noLeidos === 0) &&
                  (!conversacionesFiltradas[index - 1].leido || conversacionesFiltradas[index - 1].noLeidos > 0)
                
                return (
                  <div key={conversacion.id}>
                    {mostrarSeparadorLeidos && (
                      <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-200">
                        <p className="text-xs font-bold text-gray-600 uppercase tracking-wide">Leídos</p>
                      </div>
                    )}
                    <div
                      onClick={() => handleSeleccionarConversacion(conversacion)}
                      className={`p-3 cursor-pointer transition-all duration-200 ${
                        conversacionSeleccionada === conversacion.id 
                          ? 'bg-gradient-to-r from-blue-50 to-blue-100 border-l-4 border-blue-600' 
                          : 'hover:bg-gray-50 border-l-4 border-transparent'
                      } ${conversacion.noLeidos > 0 ? 'font-semibold bg-blue-50/50' : ''}`}
                    >
                      <div className="flex items-start justify-between mb-1">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <div className="flex-shrink-0">
                            {conversacion.tipo === 'whatsapp' ? (
                              <div className="p-1.5 rounded-full bg-green-100">
                                <MessageSquare className="h-4 w-4 text-green-600" />
                              </div>
                            ) : (
                              <div className="p-1.5 rounded-full bg-purple-100">
                                <Mail className="h-4 w-4 text-purple-600" />
                              </div>
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className={`text-sm truncate ${conversacion.noLeidos > 0 ? 'text-gray-900' : 'text-gray-700'}`}>
                                {conversacion.nombre}
                              </span>
                              {conversacion.esNuevo && (
                                <Badge variant="destructive" className="text-xs px-2 py-0.5 font-bold animate-pulse">
                                  NUEVO
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                        {conversacion.noLeidos > 0 && (
                          <Badge className="ml-2 flex-shrink-0 bg-blue-600 text-white font-bold min-w-[24px] justify-center">
                            {conversacion.noLeidos}
                          </Badge>
                        )}
                      </div>
                      <div className="text-xs text-gray-600 truncate mt-2 line-clamp-2">
                        {conversacion.ultimaComunicacion.body?.substring(0, 60) || conversacion.ultimaComunicacion.subject || '[Sin contenido]'}
                        {conversacion.ultimaComunicacion.body && conversacion.ultimaComunicacion.body.length > 60 && '...'}
                      </div>
                      <div className="text-xs text-gray-400 mt-2 flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatearFecha(conversacion.ultimaComunicacion.timestamp)}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* COLUMNA CENTRO: Vista de conversación */}
      <div className="flex-1 flex flex-col min-w-0 bg-white">
        {!conversacionActual ? (
          <div className="flex items-center justify-center h-full bg-gradient-to-br from-gray-50 to-white">
            <div className="text-center">
              <div className="p-4 rounded-full bg-blue-100 w-20 h-20 flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="h-10 w-10 text-blue-600" />
              </div>
              <p className="text-gray-600 font-medium">Selecciona una conversación para ver los mensajes</p>
              <p className="text-sm text-gray-400 mt-2">Los mensajes aparecerán aquí</p>
            </div>
          </div>
        ) : (
          <>
            {/* Header de conversación */}
            <div className="p-3 border-b border-gray-200 bg-gradient-to-r from-white to-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-white shadow-sm">
                    {conversacionActual.tipo === 'whatsapp' ? (
                      <div className="p-2 rounded-full bg-green-100">
                        <MessageSquare className="h-5 w-5 text-green-600" />
                      </div>
                    ) : (
                      <div className="p-2 rounded-full bg-purple-100">
                        <Mail className="h-5 w-5 text-purple-600" />
                      </div>
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-gray-900">{conversacionActual.nombre}</h3>
                      {conversacionActual.esNuevo && (
                        <Badge variant="destructive" className="text-xs font-bold animate-pulse">
                          NUEVO
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 flex items-center gap-1 mt-1">
                      {conversacionActual.tipo === 'whatsapp' ? (
                        <Phone className="h-3 w-3" />
                      ) : (
                        <Mail className="h-3 w-3" />
                      )}
                      {conversacionActual.contacto}
                    </p>
                  </div>
                </div>
                {conversacionActual.esNuevo && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setMostrarCrearCliente(true)}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Crear Cliente
                  </Button>
                )}
              </div>
            </div>

            {/* Mensajes */}
            <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-gray-50">
              {cargandoMensajes === conversacionActual.id ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                </div>
              ) : mensajesOrdenados.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-500">No hay mensajes en esta conversación</p>
                </div>
              ) : (
                mensajesOrdenados.map((mensaje) => (
                  <div
                    key={`${mensaje.tipo}-${mensaje.id}`}
                    className={`flex ${mensaje.direccion === 'INBOUND' ? 'justify-start' : 'justify-end'}`}
                  >
                    <div
                      className={`max-w-[75%] rounded-lg p-3 shadow-sm ${
                        mensaje.direccion === 'INBOUND'
                          ? 'bg-white border border-gray-200 shadow-md'
                          : 'bg-gradient-to-br from-blue-600 to-blue-700 text-white shadow-lg'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        {mensaje.tipo === 'whatsapp' ? (
                          <MessageSquare className={`h-3 w-3 ${mensaje.direccion === 'OUTBOUND' ? 'text-white' : 'text-green-600'}`} />
                        ) : (
                          <Mail className={`h-3 w-3 ${mensaje.direccion === 'OUTBOUND' ? 'text-white' : 'text-purple-600'}`} />
                        )}
                        <span className={`text-xs ${mensaje.direccion === 'OUTBOUND' ? 'text-blue-100' : 'text-gray-500'}`}>
                          {formatearFecha(mensaje.timestamp)}
                        </span>
                      </div>
                      {mensaje.subject && (
                        <div className={`font-semibold mb-1 ${mensaje.direccion === 'OUTBOUND' ? 'text-white' : 'text-gray-900'}`}>
                          {mensaje.subject}
                        </div>
                      )}
                      <div className={`text-sm whitespace-pre-wrap ${mensaje.direccion === 'OUTBOUND' ? 'text-white' : 'text-gray-700'}`}>
                        {mensaje.body || '[Sin contenido]'}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Input para enviar mensaje */}
            <div className="p-3 border-t border-gray-200 bg-gradient-to-r from-white to-gray-50">
              {/* Botón Manual/Automático (solo para WhatsApp) */}
              {conversacionActual.tipo === 'whatsapp' && (
                <div className="flex items-center justify-between mb-2 p-2 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex items-center gap-2">
                    {modoAutomatico ? (
                      <Zap className="h-4 w-4 text-blue-600" />
                    ) : (
                      <User className="h-4 w-4 text-gray-600" />
                    )}
                    <span className="text-sm font-medium text-gray-700">
                      Modo: <span className={modoAutomatico ? 'text-blue-600 font-bold' : 'text-gray-600 font-bold'}>
                        {modoAutomatico ? 'Automático (Bot)' : 'Manual'}
                      </span>
                    </span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setModoAutomatico(!modoAutomatico)}
                    className="flex items-center gap-2"
                  >
                    <Settings className="h-4 w-4" />
                    <span className="text-xs">
                      {modoAutomatico ? 'Cambiar a Manual' : 'Cambiar a Automático'}
                    </span>
                  </Button>
                </div>
              )}
              
              {conversacionActual.tipo === 'email' && (
                <Input
                  placeholder="Asunto..."
                  value={asuntoEmail}
                  onChange={(e) => setAsuntoEmail(e.target.value)}
                  className="mb-2"
                />
              )}
              
              {/* En modo automático, mostrar info; en manual, mostrar input */}
              {conversacionActual.tipo === 'whatsapp' && modoAutomatico ? (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-start gap-2">
                    <Zap className="h-5 w-5 text-blue-600 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-blue-900">Bot Automático Activo</p>
                      <p className="text-xs text-blue-700 mt-1">
                        El bot responderá automáticamente a los mensajes recibidos. Cambia a modo manual para enviar mensajes personalizados.
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex gap-2">
                  <Textarea
                    placeholder={conversacionActual.tipo === 'whatsapp' ? 'Escribe un mensaje...' : 'Escribe tu respuesta...'}
                    value={mensajeTexto}
                    onChange={(e) => setMensajeTexto(e.target.value)}
                    className="flex-1 min-h-[80px]"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                        handleEnviarMensaje()
                      }
                    }}
                  />
                  <Button onClick={handleEnviarMensaje} disabled={!mensajeTexto.trim() || enviando}>
                    {enviando ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Enviando...
                      </>
                    ) : (
                      'Enviar'
                    )}
                  </Button>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* COLUMNA DERECHA: Panel de Tickets */}
      <div className="w-96 flex-shrink-0 border-l border-gray-200 flex flex-col bg-white">
        {!conversacionActual ? (
          <div className="flex items-center justify-center h-full p-4 bg-gradient-to-br from-gray-50 to-white">
            <div className="text-center">
              <div className="p-4 rounded-full bg-gray-100 w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <FileText className="h-8 w-8 text-gray-400" />
              </div>
              <p className="text-sm text-gray-600 font-medium">Selecciona una conversación para ver los tickets</p>
              <p className="text-xs text-gray-400 mt-2">Los tickets aparecerán aquí</p>
            </div>
          </div>
        ) : (
          <>
            <div className="p-3 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-white">
              <h3 className="font-bold text-gray-900 flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-blue-100">
                  <FileText className="h-5 w-5 text-blue-600" />
                </div>
                Tickets
              </h3>
              {conversacionActual.esNuevo && (
                <p className="text-xs text-orange-600 mt-2 font-medium bg-orange-50 px-2 py-1 rounded">
                  ⚠️ Crea un cliente para gestionar tickets
                </p>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-3">
              {/* Formulario para crear ticket */}
              {!ticketEditando && (
                <Card className="border-2 border-blue-100 shadow-md">
                  <CardHeader className="pb-2 pt-3 px-3 bg-gradient-to-r from-blue-50 to-white">
                    <CardTitle className="text-sm font-bold text-gray-900 flex items-center gap-2">
                      <Plus className="h-4 w-4 text-blue-600" />
                      Crear Nuevo Ticket
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 p-3">
                    <Input
                      placeholder="Título del ticket"
                      value={ticketForm.titulo}
                      onChange={(e) => setTicketForm({ ...ticketForm, titulo: e.target.value })}
                      className="text-sm"
                    />
                    <Textarea
                      placeholder="Descripción..."
                      value={ticketForm.descripcion}
                      onChange={(e) => setTicketForm({ ...ticketForm, descripcion: e.target.value })}
                      className="text-sm min-h-[80px]"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <Select
                        value={ticketForm.tipo}
                        onValueChange={(value) => setTicketForm({ ...ticketForm, tipo: value })}
                      >
                        <SelectTrigger className="text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="consulta">Consulta</SelectItem>
                          <SelectItem value="incidencia">Incidencia</SelectItem>
                          <SelectItem value="solicitud">Solicitud</SelectItem>
                          <SelectItem value="reclamo">Reclamo</SelectItem>
                          <SelectItem value="contacto">Contacto</SelectItem>
                        </SelectContent>
                      </Select>
                      <Select
                        value={ticketForm.prioridad}
                        onValueChange={(value) => setTicketForm({ ...ticketForm, prioridad: value })}
                      >
                        <SelectTrigger className="text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="baja">Baja</SelectItem>
                          <SelectItem value="media">Media</SelectItem>
                          <SelectItem value="urgente">Urgente</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    {/* Fecha límite (agenda) */}
                    <div>
                      <label className="text-xs text-gray-600 mb-1 block">Fecha límite (Agenda)</label>
                      <Input
                        type="datetime-local"
                        value={ticketForm.fecha_limite}
                        onChange={(e) => setTicketForm({ ...ticketForm, fecha_limite: e.target.value })}
                        className="text-sm"
                      />
                    </div>
                    
                    {/* Responsable */}
                    <div>
                      <label className="text-xs text-gray-600 mb-1 block">Responsable</label>
                      <Select
                        value={ticketForm.responsable_id?.toString() || ''}
                        onValueChange={(value) => setTicketForm({ ...ticketForm, responsable_id: parseInt(value) })}
                      >
                        <SelectTrigger className="text-xs">
                          <SelectValue placeholder="Seleccionar responsable" />
                        </SelectTrigger>
                        <SelectContent>
                          {usuarios.map((u) => (
                            <SelectItem key={u.id} value={u.id.toString()}>
                              {u.nombre} {u.apellido} {u.is_admin ? '(Admin)' : ''}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    {/* Archivos */}
                    <div>
                      <label className="text-xs text-gray-600 mb-1 block">Archivos adjuntos</label>
                      <div className="flex items-center gap-2">
                        <Input
                          type="file"
                          multiple
                          onChange={(e) => {
                            const files = Array.from(e.target.files || [])
                            setTicketForm({ ...ticketForm, archivos: files })
                          }}
                          className="text-xs"
                        />
                      </div>
                      {ticketForm.archivos.length > 0 && (
                        <div className="mt-2 space-y-1">
                          {ticketForm.archivos.map((file, idx) => (
                            <div key={idx} className="text-xs text-gray-600 flex items-center gap-2">
                              <FileText className="h-3 w-3" />
                              {file.name}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    
                    <Button
                      onClick={handleCrearTicket}
                      disabled={!ticketForm.titulo.trim() || !ticketForm.descripcion.trim() || creandoTicket || conversacionActual.esNuevo}
                      className="w-full text-sm"
                      size="sm"
                    >
                      {creandoTicket ? (
                        <>
                          <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                          Creando...
                        </>
                      ) : (
                        <>
                          <Plus className="h-3 w-3 mr-2" />
                          Crear Ticket
                        </>
                      )}
                    </Button>
                    {conversacionActual.esNuevo && (
                      <p className="text-xs text-orange-600 text-center">
                        Crea el cliente primero para generar tickets
                      </p>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Formulario para actualizar ticket (solo campos permitidos) */}
              {ticketEditando && (
                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">Actualizar Ticket #{ticketEditando.id}</CardTitle>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setTicketEditando(null)}
                        className="h-6 w-6 p-0"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      Título y descripción no se pueden editar después de guardar
                    </p>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <label className="text-xs text-gray-600 mb-1 block">Título (no editable)</label>
                      <Input value={ticketEditando.titulo} disabled className="text-sm bg-gray-50" />
                    </div>
                    <div>
                      <label className="text-xs text-gray-600 mb-1 block">Descripción (no editable)</label>
                      <Textarea value={ticketEditando.descripcion} disabled className="text-sm bg-gray-50 min-h-[60px]" />
                    </div>
                    
                    <Select
                      value={ticketEditando.estado}
                      onValueChange={(value) => setTicketEditando({ ...ticketEditando, estado: value })}
                    >
                      <SelectTrigger className="text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="abierto">Abierto</SelectItem>
                        <SelectItem value="en_proceso">En Proceso</SelectItem>
                        <SelectItem value="resuelto">Resuelto</SelectItem>
                        <SelectItem value="cerrado">Cerrado</SelectItem>
                      </SelectContent>
                    </Select>
                    
                    <Select
                      value={ticketEditando.prioridad}
                      onValueChange={(value) => setTicketEditando({ ...ticketEditando, prioridad: value })}
                    >
                      <SelectTrigger className="text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="baja">Baja</SelectItem>
                        <SelectItem value="media">Media</SelectItem>
                        <SelectItem value="urgente">Urgente</SelectItem>
                      </SelectContent>
                    </Select>
                    
                    {/* Escalar a admin */}
                    <div>
                      <label className="text-xs text-gray-600 mb-1 block">Escalar a Admin</label>
                      <Select
                        value={ticketEditando.escalado_a_id?.toString() || ''}
                        onValueChange={(value) => {
                          const adminId = parseInt(value)
                          setTicketEditando({
                            ...ticketEditando,
                            escalado_a_id: adminId,
                            escalado: true,
                          })
                        }}
                      >
                        <SelectTrigger className="text-xs">
                          <SelectValue placeholder="Seleccionar admin" />
                        </SelectTrigger>
                        <SelectContent>
                          {usuarios.filter(u => u.is_admin).map((u) => (
                            <SelectItem key={u.id} value={u.id.toString()}>
                              {u.nombre} {u.apellido}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <Button
                      onClick={() => handleActualizarTicket(ticketEditando)}
                      disabled={creandoTicket}
                      className="w-full text-sm"
                      size="sm"
                    >
                      {creandoTicket ? (
                        <>
                          <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                          Actualizando...
                        </>
                      ) : (
                        'Actualizar Ticket'
                      )}
                    </Button>
                  </CardContent>
                </Card>
              )}

              {/* Lista de tickets existentes */}
              {ticketsCliente.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-semibold text-gray-700">Tickets del Cliente</h4>
                  {ticketsCliente.map((ticket) => (
                    <Card
                      key={ticket.id}
                      className="p-3 cursor-pointer hover:shadow-md transition-all duration-200 border-2 hover:border-blue-300"
                      onClick={() => setTicketEditando(ticket)}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1 min-w-0">
                          <div className="font-bold text-sm text-gray-900 truncate">{ticket.titulo}</div>
                          <div className="text-xs text-gray-500 mt-1 flex items-center gap-2">
                            <span className="font-semibold">#{ticket.id}</span>
                            <span>•</span>
                            <Badge 
                              variant={ticket.estado === 'resuelto' ? 'default' : ticket.estado === 'cerrado' ? 'secondary' : 'outline'} 
                              className="text-xs"
                            >
                              {ticket.estado}
                            </Badge>
                          </div>
                        </div>
                        <Badge 
                          variant={ticket.prioridad === 'urgente' ? 'destructive' : ticket.prioridad === 'media' ? 'default' : 'secondary'} 
                          className="text-xs font-bold"
                        >
                          {ticket.prioridad}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-600 line-clamp-2 mt-2">{ticket.descripcion}</p>
                      {ticket.fecha_limite && (
                        <div className="text-xs text-blue-600 mt-2 flex items-center gap-1 font-medium bg-blue-50 px-2 py-1 rounded">
                          <Calendar className="h-3 w-3" />
                          {new Date(ticket.fecha_limite).toLocaleDateString('es-ES', { 
                            day: '2-digit', 
                            month: 'short', 
                            year: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </div>
                      )}
                    </Card>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Formulario para Crear Cliente */}
      {mostrarCrearCliente && conversacionActual && (
        <CrearClienteForm
          cliente={{
            // Pre-llenar con datos de la conversación
            // No incluir 'id' para que se trate como creación, no edición
            telefono: conversacionActual.tipo === 'whatsapp' ? conversacionActual.contacto : '',
            email: conversacionActual.tipo === 'email' ? conversacionActual.contacto : '',
            nombres: conversacionActual.nombre !== conversacionActual.contacto ? conversacionActual.nombre : '',
          }}
          onClose={() => {
            setMostrarCrearCliente(false)
          }}
          onSuccess={() => {
            // Al guardar exitosamente, cerrar el formulario y volver a Comunicaciones
            setMostrarCrearCliente(false)
            // Guardar información de la conversación actual para buscarla después
            if (conversacionActual?.contacto && conversacionActual?.tipo) {
              setClienteRecienCreado({
                contacto: conversacionActual.contacto,
                tipo: conversacionActual.tipo,
              })
            }
            
            // Actualizar comunicaciones para reflejar el nuevo cliente
            queryClient.invalidateQueries({ queryKey: ['comunicaciones'] })
            
            setTimeout(() => {
              refetch()
              toast.success('Cliente creado exitosamente. Las comunicaciones se han actualizado.')
            }, 500)
          }}
          onClienteCreated={() => {
            // Cuando se crea el cliente, actualizar comunicaciones
            queryClient.invalidateQueries({ queryKey: ['comunicaciones'] })
            // Guardar información para buscar la conversación actualizada
            if (conversacionActual?.contacto && conversacionActual?.tipo) {
              setClienteRecienCreado({
                contacto: conversacionActual.contacto,
                tipo: conversacionActual.tipo,
              })
            }
            
            setTimeout(() => {
              refetch()
            }, 500)
          }}
        />
      )}
    </div>
  )
}
