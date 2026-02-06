import { useSearchParams } from 'react-router-dom'
import { Comunicaciones } from '../components/comunicaciones/Comunicaciones'
import { useQuery } from '@tanstack/react-query'
import { whatsappConfigService } from '../services/notificacionService'
import { MessageSquare } from 'lucide-react'
import { Card, CardContent } from '../components/ui/card'

export function ComunicacionesPage() {
  const [searchParams] = useSearchParams()
  const clienteId = searchParams.get('cliente_id')
  const conversacionIdParam = searchParams.get('conversacion_id')

  const { data: configWhatsApp } = useQuery({
    queryKey: ['config-whatsapp-comunicaciones'],
    queryFn: () => whatsappConfigService.obtenerConfiguracionWhatsApp(),
    staleTime: 60 * 1000,
  })

  const configurada = Boolean(configWhatsApp?.access_token && configWhatsApp?.phone_number_id)

  return (
    <div className="container mx-auto py-6 space-y-4">
      <Card className="border-blue-100 bg-blue-50/50">
        <CardContent className="py-3 px-4 flex flex-wrap items-center gap-2">
          <MessageSquare className="h-4 w-4 text-blue-600 shrink-0" />
          <span className="text-sm text-gray-700">
            Comunicaciones de clientes por <strong>WhatsApp</strong> o <strong>Email</strong>. Puedes responder por ambos.
            Las conversaciones se guardan automáticamente y se mantienen hasta que se borren.
            {configurada ? ' Configuración WhatsApp cargada.' : ' Configura WhatsApp y Email en Configuración para enviar y recibir.'}
          </span>
        </CardContent>
      </Card>
      <Comunicaciones
        clienteId={clienteId ? parseInt(clienteId, 10) : undefined}
        conversacionIdFromUrl={conversacionIdParam ? parseInt(conversacionIdParam, 10) : undefined}
        mostrarFiltros={true}
        mostrarEstadisticas={true}
      />
    </div>
  )
}

export default ComunicacionesPage

