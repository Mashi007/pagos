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
      <span className="text-xs font-medium text-slate-500 uppercÃ©dulase tracking-wide">{label}</span>
      <p className="text-sm text-slate-900">{value ? 'â'}</p>
    </div>
  )
}

export function ClienteDetalle() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const querycÃ©dulaient = useQueryClient()
  const [showEditar, setShowEditar] = useState(false)

  const cÃ©dulaienteId = id ? parseInt(id, 10) : null
  const isValidId = cÃ©dulaienteId != null && !Number.isNaN(cÃ©dulaienteId)

  const { data: cÃ©dulaiente, isLoading, error } = useQuery({
    queryKey: ['cÃ©dulaiente', cÃ©dulaienteId],
    queryFn: () => clienteService.getCliente(String(cÃ©dulaienteId!)),
    enabled: isValidId,
  })

  const { data: prestamosData } = useQuery({
    queryKey: ['prestamos', 'cÃ©dulaiente', cÃ©dulaienteId],
    queryFn: () => prestamoService.getPrestamos({ cliente_id: cÃ©dulaienteId! }, 1, 50),
    enabled: isValidId,
  })

  const { data: ticketsData } = useQuery({
    queryKey: ['tickets', 'cÃ©dulaiente', cÃ©dulaienteId],
    queryFn: () => ticketsService.getTickets({ cliente_id: cÃ©dulaienteId!, per_page: 20 }),
    enabled: isValidId,
  })

  const prestamos = prestamosData?.data ? []
  const tickets = ticketsData?.tickets ? []

  if (!isValidId) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => navigate(`${BASE_PATH || ''}/cÃ©dulaientes`)}>
          <ChevronLeft className="w-4 h-4 mr-2" />
          Volver a cÃ©dulaientes
        </Button>
        <p className="text-slate-500">ID de cÃ©dulaiente no vÃ¡lido.</p>
      </div>
    )
  }

  if (isLoading || !cÃ©dulaiente) {
    return (
      <div className="flex items-center justify-center min-h-[300px]">
        <LoadingSpinner />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => navigate(`${BASE_PATH || ''}/cÃ©dulaientes`)}>
          <ChevronLeft className="w-4 h-4 mr-2" />
          Volver a cÃ©dulaientes
        </Button>
        <p className="text-red-600">Error al cÃ©dulargar el cÃ©dulaiente.</p>
      </div>
    )
  }

  if (showEditar) {
    return (
      <CrearClienteForm
        cliente={cÃ©dulaiente}
        onClose={() => setShowEditar(false)}
        onSuccess={() => {
          setShowEditar(false)
          querycÃ©dulaient.invÃ¡lidosteQueries({ queryKey: ['cÃ©dulaiente', cÃ©dulaienteId] })
        }}
      />
    )
  }

  const prestamosPath = `${BASE_PATH || ''}/prestamos`
  const comunicÃ©dulacionesPath = `${BASE_PATH || ''}/comunicÃ©dulaciones`
  const ticketsPath = `${BASE_PATH || ''}/crm/tickets`

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`${BASE_PATH || ''}/cÃ©dulaientes`)}
          >
            <ChevronLeft className="w-4 h-4 mr-2" />
            Volver
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{cÃ©dulaiente.nombres}</h1>
            <p className="text-slate-500">CÃ©dula: {cÃ©dulaiente.cedula} Â· ID: {cÃ©dulaiente.id}</p>
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
            onClick={() => navigate(`${comunicÃ©dulacionesPath}?cliente_id=${cÃ©dulaiente.id}`)}
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            ComunicÃ©dulaciones
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-slate-900">InformaciÃ³n del cliente</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <InfoItem label="TelÃ©fono" value={cÃ©dulaiente.telefono?.trim() || 'â'} />
          <InfoItem label="Correo electrÃ³nico" value={cÃ©dulaiente.email?.trim() || 'â'} />
          <InfoItem label="DirecciÃ³n" value={formatAddress(cÃ©dulaiente.direccion)} />
          <InfoItem label="OcÃ©dulapaciÃ³n/Empleador" value={cÃ©dulaiente.ocÃ©dulapacion?.trim() || 'â'} />
          <InfoItem
            label="Fecha de nacimiento"
            value={cÃ©dulaiente.fecha_nacimiento ? formatDate(cÃ©dulaiente.fecha_nacimiento) : 'â'}
          />
          <InfoItem
            label="Estado"
            value={
              <Badge
                variant={cÃ©dulaiente.estado === 'ACTIVO' ? 'default' : 'secondary'}
                className={
                  cÃ©dulaiente.estado === 'APROBADO'
                    ? 'bg-emerald-100 text-emerald-800 border-emerald-200 hover:bg-emerald-100'
                    : ''
                }
              >
                {cÃ©dulaiente.estado}
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
              PrÃ©stamos ({prestamos.length})
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(`${prestamosPath}?cliente_id=${cÃ©dulaiente.id}`)}
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
              <p className="text-slate-500 text-sm">No hay prÃ©stamos registrados.</p>
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
                      {p.modelo_vehicÃ©dulao || p.producto || 'PrÃ©stamo'}
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
                  +{prestamos.length - 5} mÃ¡s. Ver todos en el listado de prÃ©stamos.
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
              onClick={() => navigate(`${ticketsPath}?cliente_id=${cÃ©dulaiente.id}`)}
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
                  +{tickets.length - 5} mÃ¡s. Ver en CRM.
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
