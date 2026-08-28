import { useParams, useNavigate } from 'react-router-dom'

import {
  ChevronLeft,
  Edit,
  Phone,
  Mail,
  MapPin,
  Briefcase,
  Calendar,
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
      <span className="uppercase text-xs font-medium tracking-wide text-slate-500">
        {label}
      </span>

      <p className="text-sm text-slate-900">{value ?? '-'}</p>
    </div>
  )
}

export function ClienteDetalle() {
  const { id } = useParams<{ id: string }>()

  const navigate = useNavigate()

  const queryClient = useQueryClient()

  const [showEditar, setShowEditar] = useState(false)

  const clienteId = id ? parseInt(id, 10) : null

  const isValidId = clienteId != null && !Number.isNaN(clienteId)

  const {
    data: cliente,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['cliente', clienteId],

    queryFn: () => clienteService.getCliente(String(clienteId!)),

    enabled: isValidId,
  })

  const { data: prestamosData } = useQuery({
    queryKey: ['prestamos', 'cliente', clienteId],

    queryFn: () =>
      prestamoService.getPrestamos({ cliente_id: clienteId! }, 1, 50),

    enabled: isValidId,
  })

  const { data: ticketsData } = useQuery({
    queryKey: ['tickets', 'cliente', clienteId],

    queryFn: () =>
      ticketsService.getTickets({ cliente_id: clienteId!, per_page: 20 }),

    enabled: isValidId,
  })

  const prestamos = prestamosData?.data ?? []

  const tickets = ticketsData?.tickets ?? []

  if (!isValidId) {
    return (
      <div className="space-y-6">
        <Button
          variant="ghost"
          onClick={() => navigate(`${BASE_PATH || ''}/clientes`)}
        >
          <ChevronLeft className="mr-2 h-4 w-4" />
          Volver a clientes
        </Button>

        <p className="text-slate-500">ID de cliente no válido.</p>
      </div>
    )
  }

  if (isLoading || !cliente) {
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
          onClick={() => navigate(`${BASE_PATH || ''}/clientes`)}
        >
          <ChevronLeft className="mr-2 h-4 w-4" />
          Volver a clientes
        </Button>

        <p className="text-red-600">Error al cargar el cliente.</p>
      </div>
    )
  }

  if (showEditar) {
    return (
      <CrearClienteForm
        cliente={cliente}
        onClose={() => setShowEditar(false)}
        onSuccess={() => {
          setShowEditar(false)

          queryClient.inválidosteQueries({
            queryKey: ['cliente', clienteId],
          })
        }}
      />
    )
  }

  const prestamosPath = `${BASE_PATH || ''}/prestamos`

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate(`${BASE_PATH || ''}/clientes`)}
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            Volver
          </Button>

          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              {cliente.nombres}
            </h1>

            <p className="text-slate-500">
              Cédula: {cliente.cedula} · ID: {cliente.id}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowEditar(true)}>
            <Edit className="mr-2 h-4 w-4" />
            Editar
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
            value={cliente.telefono?.trim() || '-'}
          />

          <InfoItem
            label="Correo 1 (prioridad)"
            value={cliente.email?.trim() || '-'}
          />

          <InfoItem
            label="Correo 2 (opcional)"
            value={(() => {
              const s =
                cliente.email_secundario ?? cliente.correo_2 ?? ''

              const t = String(s).trim()

              return t || '-'
            })()}
          />

          <InfoItem
            label="Correos anteriores"
            value={
              Array.isArray(cliente.correos_historial) &&
              cliente.correos_historial.length > 0 ? (
                <span className="break-all">
                  {cliente.correos_historial.join(', ')}
                </span>
              ) : (
                '-'
              )
            }
          />

          <InfoItem
            label="Dirección"
            value={formatAddress(cliente.direccion)}
          />

          <InfoItem
            label="Ocupación/Empleador"
            value={cliente.ocupacion?.trim() || '-'}
          />

          <InfoItem
            label="Fecha de nacimiento"
            value={
              cliente.fecha_nacimiento
                ? formatDate(cliente.fecha_nacimiento)
                : '-'
            }
          />

          <InfoItem
            label="Estado"
            value={
              <Badge
                variant={
                  cliente.estado === 'ACTIVO' ? 'default' : 'secondary'
                }
                className={
                  cliente.estado === 'APROBADO'
                    ? 'border-emerald-200 bg-emerald-100 text-emerald-800 hover:bg-emerald-100'
                    : ''
                }
              >
                {cliente.estado}
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
                navigate(`${prestamosPath}?cliente_id=${cliente.id}`)
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
                      {p.modelo_vehiculo || p.producto || 'Préstamo'}
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
