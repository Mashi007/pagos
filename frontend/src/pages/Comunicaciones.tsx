import { useSearchParams } from 'react-router-dom'
import { Comunicaciones } from '../components/comunicaciones/Comunicaciones'

export function ComunicacionesPage() {
  const [searchParams] = useSearchParams()
  const clienteId = searchParams.get('cliente_id')
  const conversacionIdParam = searchParams.get('conversacion_id')

  return (
    <div className="container mx-auto py-6 space-y-4">
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

