import { useSearchParams } from 'react-router-dom'
import { Comunicaciones } from '../components/comunicaciones/Comunicaciones'

export function ComunicacionesPage() {
  const [searchParams] = useSearchParams()
  const clienteId = searchParams.get('cliente_id')

  return (
    <div className="container mx-auto py-6">
      <Comunicaciones
        clienteId={clienteId ? parseInt(clienteId, 10) : undefined}
        mostrarFiltros={true}
        mostrarEstadisticas={true}
      />
    </div>
  )
}

export default ComunicacionesPage

