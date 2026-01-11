import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, Loader2, ChevronRight } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { apiClient } from '@/services/api'

interface DiferenciaAbono {
  prestamo_id: number
  cedula: string
  nombres: string
  total_abonos_bd: number
  total_abonos_imagen: number
  diferencia: number
  detalle: string
}

export function DiferenciasAbonosInformativo() {
  const navigate = useNavigate()

  // Obtener conteo de diferencias de abonos
  const { data: diferencias, isLoading, error } = useQuery({
    queryKey: ['diferencias-abonos'],
    queryFn: async (): Promise<DiferenciaAbono[]> => {
      const response = await apiClient.get<DiferenciaAbono[]>('/api/v1/reportes/diferencias-abonos')
      return response
    },
    refetchInterval: 30000, // Refrescar cada 30 segundos
  })

  const cantidadPrestamos = diferencias?.length || 0

  const handleVerPrestamos = () => {
    // Navegar a la página de préstamos con filtro de requiere_revision
    navigate('/prestamos?requiere_revision=true')
  }

  // Si hay error o está cargando, mostrar estado correspondiente
  if (isLoading) {
    return (
      <Card className="border-l-4 border-l-orange-500">
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-orange-600" />
              <div>
                <p className="font-semibold text-gray-900">Diferencias de Abonos</p>
                <p className="text-sm text-gray-600">Cargando información...</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className="border-l-4 border-l-red-500">
        <CardContent className="py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-600" />
              <div>
                <p className="font-semibold text-gray-900">Diferencias de Abonos</p>
                <p className="text-sm text-red-600">Error al cargar información</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Si no hay diferencias, mostrar mensaje informativo
  if (cantidadPrestamos === 0) {
    return (
      <Card className="border-l-4 border-l-gray-300">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-gray-400" />
            Diferencias de Abonos
          </CardTitle>
          <CardDescription>
            Préstamos marcados para revisión con diferencias entre BD y valores de referencia
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="text-center flex-1">
              <p className="text-lg font-medium text-gray-500">No hay diferencias pendientes</p>
              <p className="text-sm text-gray-400 mt-1">
                Marca préstamos para revisar en la página de Préstamos para que aparezcan aquí.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Si hay diferencias, mostrar conteo y botón
  return (
    <Card className="border-l-4 border-l-orange-500 bg-orange-50/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-orange-600" />
              Diferencias de Abonos
            </CardTitle>
            <CardDescription className="mt-1">
              Préstamos marcados para revisión con diferencias entre BD y valores de referencia
            </CardDescription>
          </div>
          <Badge variant="destructive" className="text-lg px-3 py-1">
            {cantidadPrestamos}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-lg font-semibold text-gray-900">
              {cantidadPrestamos} {cantidadPrestamos === 1 ? 'préstamo' : 'préstamos'} que validar
            </p>
            <p className="text-sm text-gray-600 mt-1">
              Hay préstamos con diferencias pendientes de revisión
            </p>
          </div>
          <Button
            onClick={handleVerPrestamos}
            className="bg-orange-600 hover:bg-orange-700 text-white"
          >
            Ver Préstamos
            <ChevronRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
