import { useSearchParams, Link } from 'react-router-dom'
import { Comunicaciones } from '../components/comunicaciones/Comunicaciones'
import { useQuery } from '@tanstack/react-query'
import { whatsappConfigService } from '../services/notificacionService'
import { MessageSquare, Settings } from 'lucide-react'
import { Card, CardContent } from '../components/ui/card'

export function ComunicacionesPage() {
  const [searchParams] = useSearchParams()
  const clienteId = searchParams.get('cliente_id')

  const { data: configWhatsApp } = useQuery({
    queryKey: ['config-whatsapp-comunicaciones'],
    queryFn: () => whatsappConfigService.obtenerConfiguracionWhatsApp(),
    staleTime: 60 * 1000,
  })

  const configurada = Boolean(configWhatsApp?.access_token && configWhatsApp?.phone_number_id)

  return (
    <div className="container mx-auto py-6 space-y-4">
      <Card className="border-blue-100 bg-blue-50/50">
        <CardContent className="py-3 px-4 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm text-gray-700">
            <MessageSquare className="h-4 w-4 text-blue-600" />
            <span>
              Comunicaciones de clientes por <strong>WhatsApp</strong> o <strong>Email</strong>. Puedes responder por ambos.
              {configurada ? ' Configuración WhatsApp cargada.' : ' Configura WhatsApp y Email para enviar y recibir.'}
            </span>
          </div>
          <Link
            to="/configuracion?tab=whatsapp"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            <Settings className="h-4 w-4" />
            Configurar en Configuración (WhatsApp)
          </Link>
        </CardContent>
      </Card>
      <Comunicaciones
        clienteId={clienteId ? parseInt(clienteId, 10) : undefined}
        mostrarFiltros={true}
        mostrarEstadisticas={true}
      />
    </div>
  )
}

export default ComunicacionesPage

