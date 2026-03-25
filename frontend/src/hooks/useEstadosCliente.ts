import { useQuery } from '@tanstack/react-query'

import { clienteService } from '../services/clienteService'

export interface EstadoClienteOption {
  valor: string

  etiqueta: string

  orden: number
}

/**




 * Hook para obtener estados de cliente desde la BD.




 * Usado en CrearClienteForm, EditarRevisionManual, ClientesList, ExcelUploader.




 */

export function useEstadosCliente(options?: { alwaysFresh?: boolean }) {
  const alwaysFresh = options?.alwaysFresh === true

  const { data, isLoading } = useQuery({
    queryKey: ['estados-cliente'],

    queryFn: () => clienteService.getEstadosCliente(),

    staleTime: alwaysFresh ? 0 : 10 * 60 * 1000,

    refetchOnMount: alwaysFresh ? 'always' : true,
  })

  const opciones: EstadoClienteOption[] = data?.estados ?? []

  return { opciones, isLoading }
}
