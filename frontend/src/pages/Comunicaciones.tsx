import { useSearchParams } from 'react-router-dom'

import { MessageSquare } from 'lucide-react'

import { Comunicaciones } from '../components/comunicaciones/Comunicaciones'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

export function ComunicacionesPage() {
  const [searchParams] = useSearchParams()

  const clienteId = searchParams.get('cliente_id')

  const conversacionIdParam = searchParams.get('conversacion_id')

  return (
    <div className="container mx-auto space-y-4 py-6">
      <ModulePageHeader
        icon={MessageSquare}
        title="CRM - Comunicaciones"
        description="WhatsApp y correo unificados con la base de clientes."
      />

      <Comunicaciones
        clienteId={clienteId ? parseInt(clienteId, 10) : undefined}
        conversacionIdFromUrl={
          conversacionIdParam ? parseInt(conversacionIdParam, 10) : undefined
        }
        mostrarFiltros={true}
        mostrarEstadisticas={true}
      />
    </div>
  )
}

export default ComunicacionesPage
