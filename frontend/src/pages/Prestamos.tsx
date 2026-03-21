import { PrestamosList } from '../components/prestamos/PrestamosList'
import { DollarSign, Bell, Search, CheckCircle2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { usePrestamos } from '../hooks/usePrestamos'
import { Link, useNavigate } from 'react-router-dom'

export function Prestamos() {
  const { data: enRevisionData } = usePrestamos({ estado: 'EN_REVISION' }, 1, 1)
  const enRevisionCount = enRevisionData?.total ? 0
  const navigate = useNavigate()

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <DollarSign className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900">PrÃÂ©stamos</h1>
        </div>
        <Button
          onClick={() => navigate('/revision-manual')}
          className="bg-green-600 hover:bg-green-700 text-white gap-2"
        >
          <CheckCircle2 className="h-4 w-4" />
          RevisiÃÂ³n Manual Post-MigraciÃÂ³n
        </Button>
      </div>

      {/* Novedades: informaciÃÂ³n para el usuario */}
      <Card className="border-blue-100 bg-blue-50/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Bell className="h-4 w-4 text-blue-600" />
            Novedades
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-gray-700 space-y-2">
          {enRevisionCount > 0 ? (
            <p>
              Hay <strong>{enRevisionCount}</strong> prÃÂ©stamo{enRevisionCount !== 1 ? 's' : ''} en revisiÃÂ³n pendiente{enRevisionCount !== 1 ? 's' : ''} de aprobaciÃÂ³n.
              <Link
                to="/prestamos?estado=EN_REVISION"
                className="ml-2 inline-flex items-center gap-1 text-blue-600 hover:underline font-medium"
              >
                <Search className="h-4 w-4" />
                Ver en lista
              </Link>
            </p>
          ) : (
            <p>No hay prÃÂ©stamos pendientes de revisiÃÂ³n. Use los filtros para buscar por estado, analista o fechas.</p>
          )}
        </CardContent>
      </Card>

      <PrestamosList />
    </div>
  )
}

export default Prestamos
