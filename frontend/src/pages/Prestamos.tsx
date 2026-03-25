import { PrestamosList } from '../components/prestamos/PrestamosList'

import { Bell, Search } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { usePrestamos } from '../hooks/usePrestamos'

import { Link } from 'react-router-dom'

export function Prestamos() {
  const { data: enRevisionData } = usePrestamos({ estado: 'EN_REVISION' }, 1, 1)

  const enRevisionCount = enRevisionData?.total ?? 0

  return (
    <div className="space-y-6 p-6">
      {/* Novedades: información para el usuario */}

      <Card className="border-blue-100 bg-blue-50/50">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Bell className="h-4 w-4 text-blue-600" />
            Novedades
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-2 text-sm text-gray-700">
          {enRevisionCount > 0 ? (
            <p>
              Hay <strong>{enRevisionCount}</strong> préstamo
              {enRevisionCount !== 1 ? 's' : ''} en revisión pendiente
              {enRevisionCount !== 1 ? 's' : ''} de aprobación.
              <Link
                to="/prestamos?estado=EN_REVISION"
                className="ml-2 inline-flex items-center gap-1 font-medium text-blue-600 hover:underline"
              >
                <Search className="h-4 w-4" />
                Ver en lista
              </Link>
            </p>
          ) : (
            <p>
              No hay préstamos pendientes de revisión. Use los filtros para
              buscar por estado, analista o fechas.
            </p>
          )}
        </CardContent>
      </Card>

      <PrestamosList />
    </div>
  )
}

export default Prestamos
