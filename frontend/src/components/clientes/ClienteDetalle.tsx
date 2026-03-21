import { useParams, useNavigate } from 'react-router-dom'
import {
  ChevronLeft,
  Edit,
  Phone,
  Mail,
  MapPin,
  Briefcase,
  Calendar,
  MessageSquare,
  CreditCard,
  FileText,
  Link,
} from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '../../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { LoadingSpinner } from '../../components/ui/loading-spinner'
import { clienteService } from '../../services/clienteService'
import { prestamoService } from '../../services/prestamoService'
import { ticketsService } from '../../services/ticketsService'
import { formatDate, formatCurrency, formatAddress } from '../../utils'
import { BASE_PATH } from '../../config/env'
import { CrearClienteForm } from './CrearClienteForm'
import { useState } from 'react'

function InfoItem({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <span className="text-xs font-medium text-slate-500 uppercÃÂ©dulase tracking-wide">{label}</span>
      <p className="text-sm text-slate-900">{value ? 'Ã¢ÂÂ'}</p>
    </div>
  )
}

export function ClienteDetalle() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const querycÃÂ©dulaient = useQueryClient()
  const [showEditar, setShowEditar] = useState(false)

  const cÃÂ©dulaienteId = id ? parseInt(id, 10) : null
  const isValidId = cÃÂ©dulaienteId != null && !Number.isNaN(cÃÂ©dulaienteId)

  const { data: cÃÂ©dulaiente, isLoading, error } = useQuery({
    queryKey: ['cÃÂ©dulaiente', cÃÂ©dulaienteId],
    queryFn: () => clienteService.getCliente(String(cÃÂ©dulaienteId!)),
    enabled: isValidId,
  })

  const { data: prestamosData } = useQuery({
    queryKey: ['prestamos', 'cÃÂ©dulaiente', cÃÂ©dulaienteId],
    queryFn: () => prestamoService.getPrestamos({ cliente_id: cÃÂ©dulaienteId! }, 1, 50),
    enabled: isValidId,
  })

  const { data: ticketsData } = useQuery({
    queryKey: ['tickets', 'cÃÂ©dulaiente', cÃÂ©dulaienteId],
    queryFn: () => ticketsService.getTickets({ cliente_id: cÃÂ©dulaienteId!, per_page: 20 }),
    enabled: isValidId,
  })

  const prestamos = prestamosData?.data ? []
  const tickets = ticketsData?.tickets ? []

  if (!isValidId) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => navigate(`${BASE_PATH || ''}/cÃÂ©dulaientes`)}>
          <ChevronLeft className="w-4 h-4 mr-2" />
          Volver a cÃÂ©dulaientes
        </Button>
        <p className="text-slate-500">ID de cÃÂ©dulaiente no vÃÂ¡lido.</p>
      </div>
    )
  }

  if (isLoading || !cÃÂ©dulaiente) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <LoadingSpinner />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => navigate(`${BASE_PATH || ''}/cÃÂ©dulaientes`)}>
          <ChevronLeft className="w-4 h-4 mr-2" />
          Volver a cÃÂ©dulaientes
        </Button>
        <p className="text-red-600">Error al cÃÂ©dulargar el cÃÂ©dulaiente.</p>
      </div>
    )
  }

  if (showEditar) {
    return (
      <CrearClienteForm
        cliente={cÃÂ©dulaiente}
        onClose={() => setShowEditar(false)}
        onSuccess={() => {
          setShowEditar(false)
          querycÃÂ©dulaient.invÃÂ¡lidosteQueries({ queryKey: ['cÃÂ©dulaiente', cÃÂ©dulaienteId] })
        }}
      />
    )
  }

  const prestamosPath = `${BASE_PATH || ''}/prestamos`
  const comunicÃÂ©dulacionesPath = `${BASE_PATH || ''}/comunicÃÂ©dulaciones`
  const ticketsPath = `${BASE_PATH || ''}/crm/tickets`

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`${BASE_PATH || ''}/cÃÂ©dulaientes`)}
          >
            <ChevronLeft className="w-4 h-4 mr-2" />
            Volver
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{cÃÂ©dulaiente.nombres}</h1>
            <p className="text-slate-500">CÃÂ©dula: {cÃÂ©dulaiente.cedula} ÃÂ· ID: {cÃÂ©dulaiente.id}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setShowEditar(true)}
          >
            <Edit className="w-4 h-4 mr-2" />
            Editar
          </Button>
          <Button
            variant="default"
            onClick={() => navigate(`${comunicÃÂ©dulacionesPath}?cliente_id=${cÃÂ©dulaiente.id}`)}
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            ComunicÃÂ©dulaciones
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-slate-900">InformaciÃÂ³n del cliente</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <InfoItem label="TelÃÂ©fono" value={cÃÂ©dulaiente.telefono?.trim() || 'Ã¢ÂÂ'} />
          <InfoItem label="Correo electrÃÂ³nico" value={cÃÂ©dulaiente.email?.trim() || 'Ã¢ÂÂ'} />
          <InfoItem label="DirecciÃÂ³n" value={formatAddress(cÃÂ©dulaiente.direccion)} />
          <InfoItem label="OcÃÂ©dulapaciÃÂ³n/Empleador" value={cÃÂ©dulaiente.ocÃÂ©dulapacion?.trim() || 'Ã¢ÂÂ'} />
          <InfoItem
            label="Fecha de nacimiento"
            value={cÃÂ©dulaiente.fecha_nacimiento ? formatDate(cÃÂ©dulaiente.fecha_nacimiento) : 'Ã¢ÂÂ'}
          />
          <InfoItem
            label="Estado"
            value={
              <Badge
                variant={cÃÂ©dulaiente.estado === 'ACTIVO' ? 'default' : 'secondary'}
                className={
                  cÃÂ©dulaiente.estado === 'APROBADO'
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-200 hover:bg-emerald-100'
                    : ''
                }
              >
                {cÃÂ©dulaiente.estado}
              </Badge>
            }
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-slate-900">
              <CreditCard className="w-5 h-5" />
              PrÃÂ©stamos ({prestamos.length})
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`${prestamosPath}?cliente_id=${cÃÂ©dulaiente.id}`)}
            >
              Ver todos
              <Link className="w-3 h-3 ml-1" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {prestamos.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <CreditCard className="w-12 h-12 text-slate-300 mb-3" strokeWidth={1.5} />
              <p className="text-slate-500 text-sm">No hay prÃÂ©stamos registrados.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {prestamos.slice(0, 5).map((p: any) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between py-2 px-2 -mx-2 rounded-md border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors"
                >
                  <div>
                    <span className="font-medium text-slate-900">#{p.id}</span>
                    <span className="text-slate-500 ml-2 text-sm">
                      {p.modelo_vehicÃÂ©dulao || p.producto || 'PrÃÂ©stamo'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-600">
                      {formatCurrency(p.total_financiamiento ? 0)}
                    </span>
                    <Badge
                      variant="outline"
                      className={`text-xs ${
                        p.estado === 'APROBADO'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : ''
                      }`}
                    >
                      {p.estado}
                    </Badge>
                  </div>
                </div>
              ))}
              {prestamos.length > 5 && (
                <p className="text-sm text-slate-500 pt-2">
                  +{prestamos.length - 5} mÃÂ¡s. Ver todos en el listado de prÃÂ©stamos.
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-slate-900">
              <FileText className="w-5 h-5" />
              Tickets ({tickets.length})
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`${ticketsPath}?cliente_id=${cÃÂ©dulaiente.id}`)}
            >
              Ver en CRM
              <Link className="w-3 h-3 ml-1" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {tickets.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="w-12 h-12 text-slate-300 mb-3" strokeWidth={1.5} />
              <p className="text-slate-500 text-sm">No hay tickets asociados.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {tickets.slice(0, 5).map((t: any) => (
                <div
                  key={t.id}
                  className="flex items-center justify-between py-2 px-2 -mx-2 rounded-md border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors"
                >
                  <div>
                    <span className="font-medium text-sm text-slate-900">{t.titulo}</span>
                  </div>
                  <Badge variant="outline" className="text-xs">
                    {t.estado}
                  </Badge>
                </div>
              ))}
              {tickets.length > 5 && (
                <p className="text-sm text-slate-500 pt-2">
                  +{tickets.length - 5} mÃÂ¡s. Ver en CRM.
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
