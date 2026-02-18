import { useParams } from 'react-router-dom'
import { ClientesList } from '../components/clientes/ClientesList'
import { ClienteDetalle } from '../components/clientes/ClienteDetalle'

export function Clientes() {
  const { id } = useParams<{ id: string }>()
  const isDetailView = id != null && id !== 'nuevo'

  if (isDetailView) {
    return <ClienteDetalle />
  }
  return <ClientesList />
}

export default Clientes
