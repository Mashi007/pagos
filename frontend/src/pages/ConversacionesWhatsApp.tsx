import { useSearchParams } from 'react-router-dom'
import { ConversacionesWhatsApp } from '@/components/whatsapp/ConversacionesWhatsApp'

export function ConversacionesWhatsAppPage() {
  const [searchParams] = useSearchParams()
  const clienteId = searchParams.get('cliente_id')

  return (
    <div className="container mx-auto py-6">
      <ConversacionesWhatsApp
        clienteId={clienteId ? parseInt(clienteId, 10) : undefined}
        mostrarFiltros={true}
        mostrarEstadisticas={true}
      />
    </div>
  )
}

