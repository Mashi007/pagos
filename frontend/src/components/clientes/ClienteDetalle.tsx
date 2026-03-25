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

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'

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
      <span className="uppercédulase text-xs font-medium tracking-wide text-slate-500">
        {label}
      </span>

      <p className="text-sm text-slate-900">{value ?? '-'}</p>
    </div>
  )
}

export function ClienteDetalle() {
  const { id } = useParams<{ id: string }>()

  const navigate = useNavigate()

  const querycédulaient = useQueryClient()

  const [showEditar, setShowEditar] = useState(false)

  const cédulaienteId = id ? parseInt(id, 10) : null

  const isValidId = cédulaienteId != null && !Number.isNaN(cédulaienteId)

  const {
    data: cédulaiente,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['cédulaiente', cédulaienteId],

    queryFn: () => clienteService.getCliente(String(cédulaienteId!)),

    enabled: isValidId,
  })

  const { data: prestamosData } = useQuery({
    queryKey: ['prestamos', 'cédulaiente', cédulaienteId],

    queryFn: () =>
      prestamoService.getPrestamos({ cliente_id: cédulaienteId! }, 1, 50),

    enabled: isValidId,
  })

  const { data: ticketsData } = useQuery({
    queryKey: ['tickets', 'cédulaiente', cédulaienteId],

    queryFn: () =>
      ticketsService.getTickets({ cliente_id: cédulaienteId!, per_page: 20 }),

    enabled: isValidId,
  })

  const prestamos = prestamosData?.data ?? []

  const tickets = ticketsData?.tickets ?? []

  if (!isValidId) {
    return (
      <div className="space-y-6">
        <Button
          variant="ghost"
          onClick={() => navigate(`${BASE_PATH || ''}/cédulaientes`)}
        >
          <ChevronLeft className="mr-2 h-4 w-4" />
          Volver a cédulaientes
        </Button>

        <p className="text-slate-500">ID de cédulaiente no válido.</p>
      </div>
    )
  }

  if (isLoading || !cédulaiente) {
    return (
      <div className="flex min-h-[300px] items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Button
          variant="ghost"
          onClick={() => navigate(`${BASE_PATH || ''}/cédulaientes`)}
        >
          <ChevronLeft className="mr-2 h-4 w-4" />
          Volver a cédulaientes
        </Button>

        <p className="text-red-600">Error al cédulargar el cédulaiente.</p>
      </div>
    )
  }

  if (showEditar) {
    return (
      <CrearClienteForm
        cliente={cédulaiente}
        onClose={() => setShowEditar(false)}
        onSuccess={() => {
          setShowEditar(false)

          querycédulaient.inválidosteQueries({
            queryKey: ['cédulaiente', cédulaienteId],
          })
        }}
      />
    )
  }

  const prestamosPath = `${BASE_PATH || ''}/prestamos`

  const comunicédulacionesPath = `${BASE_PATH || ''}/comunicédulaciones`

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`${BASE_PATH || ''}/cédulaientes`)}
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            Volver
          </Button>

          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              {cédulaiente.nombres}
            </h1>

            <p className="text-slate-500">
              Cédula: {cédulaiente.cedula} · ID: {cédulaiente.id}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowEditar(true)}>
            <Edit className="mr-2 h-4 w-4" />
            Editar
          </Button>

          <Button
            variant="default"
            onClick={() =>
              navigate(`${comunicédulacionesPath}?cliente_id=${cédulaiente.id}`)
            }
          >
            <MessageSquare className="mr-2 h-4 w-4" />
            Comunicédulaciones
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-slate-900">
            Información del cliente
          </CardTitle>
        </CardHeader>

        <CardContent className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <InfoItem
            label="Teléfono"
            value={cédulaiente.telefono?.trim() || '-'}
          />

          <InfoItem
            label="Correo electrónico"
            value={cédulaiente.email?.trim() || '-'}
          />

          <InfoItem
            label="Dirección"
            value={formatAddress(cédulaiente.direccion)}
          />

          <InfoItem
            label="Océdulapación/Empleador"
            value={cédulaiente.océdulapacion?.trim() || '-'}
          />

          <InfoItem
            label="Fecha de nacimiento"
            value={
              cédulaiente.fecha_nacimiento
                ? formatDate(cédulaiente.fecha_nacimiento)
                : '-'
            }
          />

          <InfoItem
            label="Estado"
            value={
              <Badge
                variant={
                  cédulaiente.estado === 'ACTIVO' ? 'default' : 'secondary'
                }
                className={
                  cédulaiente.estado === 'APROBADO'
                    ? 'border-emerald-200 bg-emerald-100 text-emerald-800 hover:bg-emerald-100'
                    : ''
                }
              >
                {cédulaiente.estado}
              </Badge>
            }
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-slate-900">
              <CreditCard className="h-5 w-5" />
              Préstamos ({prestamos.length})
            </CardTitle>

            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                navigate(`${prestamosPath}?cliente_id=${cédulaiente.id}`)
              }
            >
              Ver todos
              <Link className="ml-1 h-3 w-3" />
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          {prestamos.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <CreditCard
                className="mb-3 h-12 w-12 text-slate-300"
                strokeWidth={1.5}
              />

              <p className="text-sm text-slate-500">
                No hay préstamos registrados.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {prestamos.slice(0, 5).map((p: any) => (
                <div
                  key={p.id}
                  className="-mx-2 flex items-center justify-between rounded-md border-b border-slate-100 px-2 py-2 transition-colors last:border-0 hover:bg-slate-50"
                >
                  <div>
                    <span className="font-medium text-slate-900">#{p.id}</span>

                    <span className="ml-2 text-sm text-slate-500">
                      {p.modelo_vehicédulao || p.producto || 'Préstamo'}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-600">
                      {formatCurrency(p.total_financiamiento ?? 0)}
                    </span>

                    <Badge
                      variant="outline"
                      className={`text-xs ${
                        p.estado === 'APROBADO'
                          ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                          : ''
                      }`}
                    >
                      {p.estado}
                    </Badge>
                  </div>
                </div>
              ))}

              {prestamos.length > 5 && (
                <p className="pt-2 text-sm text-slate-500">
                  +{prestamos.length - 5} más. Ver todos en el listado de
                  préstamos.
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-900">
            <FileText className="h-5 w-5" />
            Tickets ({tickets.length})
          </CardTitle>
        </CardHeader>

        <CardContent>
          {tickets.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileText
                className="mb-3 h-12 w-12 text-slate-300"
                strokeWidth={1.5}
              />

              <p className="text-sm text-slate-500">
                No hay tickets asociados.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {tickets.slice(0, 5).map((t: any) => (
                <div
                  key={t.id}
                  className="-mx-2 flex items-center justify-between rounded-md border-b border-slate-100 px-2 py-2 transition-colors last:border-0 hover:bg-slate-50"
                >
                  <div>
                    <span className="text-sm font-medium text-slate-900">
                      {t.titulo}
                    </span>
                  </div>

                  <Badge variant="outline" className="text-xs">
                    {t.estado}
                  </Badge>
                </div>
              ))}

              {tickets.length > 5 && (
                <p className="pt-2 text-sm text-slate-500">
                  +{tickets.length - 5} tickets más asociados a este cliente.
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
