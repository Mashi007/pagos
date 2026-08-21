import { useState } from 'react'

import { useQuery } from '@tanstack/react-query'

import { FileText, Filter, Eye, X, Search, Loader2 } from 'lucide-react'

import { Button } from '../../components/ui/button'

import { ListPaginationBar } from '../../components/ui/ListPaginationBar'

import { Input } from '../../components/ui/input'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'

import { Badge } from '../../components/ui/badge'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../../components/ui/dialog'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table'

import { formatDate } from '../../utils'

import { pagoService, type Pago } from '../../services/pagoService'

import { toast } from 'sonner'

interface UltimoPago {
  cedula: string

  pago_id: number

  prestamo_id: number | null

  estado_pago: string

  monto_ultimo_pago: number

  fecha_ultimo_pago: string | null

  cuotas_atrasadas: number

  saldo_vencido: number

  total_prestamos: number
}

type SerialHit = {
  pago_id: number
  prestamo_id: number | null
  cedula: string | null
  numero_documento: string | null
  monto_pagado: number | null
  fecha_pago: string | null
  estado: string | null
  institucion_bancaria: string | null
  conciliado: boolean
}

export function PagosListResumen({
  fetchEnabled = true,
}: {
  fetchEnabled?: boolean
}) {
  const [page, setPage] = useState(1)

  const [perPage] = useState(10)

  const [filters, setFilters] = useState({
    cedula: '',

    estado: '',
  })

  const [serialInput, setSerialInput] = useState('')
  const [serialBuscando, setSerialBuscando] = useState(false)
  const [serialHits, setSerialHits] = useState<SerialHit[] | null>(null)
  const [serialBuscado, setSerialBuscado] = useState<string | null>(null)

  const [cedulaDetalle, setCedulaDetalle] = useState<string | null>(null)

  const [pageDetalle, setPageDetalle] = useState(1)

  const perPageDetalle = 10

  const { data, isLoading } = useQuery({
    queryKey: ['pagos-ultimos', page, perPage, filters],

    queryFn: () => pagoService.getUltimosPagos(page, perPage, filters),

    staleTime: 0,

    refetchOnMount: true,

    refetchOnWindowFocus: false,

    enabled: fetchEnabled,
  })

  const { data: detalleData, isLoading: loadingDetalle } = useQuery({
    queryKey: ['pagos-por-cedula', cedulaDetalle, pageDetalle, perPageDetalle],

    queryFn: () =>
      pagoService.getAllPagos(pageDetalle, perPageDetalle, {
        cedula: cedulaDetalle || '',
        prestamo_cartera: 'todos',
      }),

    enabled: !!cedulaDetalle,

    staleTime: 0,
  })

  const handleFilterChange = (key: string, value: string) => {
    const filterValue = value === 'all' ? '' : value

    setFilters(prev => ({ ...prev, [key]: filterValue }))

    setPage(1)
  }

  const abrirDetalleCedula = (cedula: string) => {
    const c = (cedula || '').trim()
    if (!c) {
      toast.error('Sin cédula en ese pago; no se puede abrir el detalle.')
      return
    }
    setFilters(prev => ({ ...prev, cedula: c }))
    setPage(1)
    setCedulaDetalle(c)
    setPageDetalle(1)
  }

  const handleBuscarSerial = async () => {
    const s = serialInput.trim()
    if (!s) {
      toast.error('Ingrese el serial / Nº documento')
      return
    }
    const digitos = s.replace(/\D/g, '')
    if (digitos.length < 4) {
      toast.error('Ingrese al menos 4 dígitos del serial')
      return
    }
    setSerialBuscando(true)
    setSerialHits(null)
    setSerialBuscado(null)
    try {
      const res = await pagoService.buscarPorSerial(s)
      setSerialHits(res.items || [])
      setSerialBuscado(res.serial_buscado || digitos)
      if (!res.items?.length) {
        toast.message('No hay pagos con ese serial en cartera')
      } else {
        toast.success(`${res.total} pago(s) con serial ${res.serial_buscado}`)
      }
    } catch (error: unknown) {
      const { getErrorMessage, getErrorDetail } =
        await import('../../types/errors')
      let errorMessage = getErrorMessage(error)
      const detail = getErrorDetail(error)
      if (detail) errorMessage = detail
      toast.error(errorMessage || 'Error al buscar el serial')
    } finally {
      setSerialBuscando(false)
    }
  }

  const getEstadoBadge = (estado: string) => {
    const estados: Record<string, { color: string; label: string }> = {
      PAGADO: { color: 'bg-green-500', label: 'Pagado' },

      PENDIENTE: { color: 'bg-yellow-500', label: 'Pendiente' },

      ATRASADO: { color: 'bg-red-500', label: 'Atrasado' },

      PARCIAL: { color: 'bg-blue-500', label: 'Parcial' },

      ADELANTADO: { color: 'bg-purple-500', label: 'Adelantado' },
    }

    const config = estados[estado] || { color: 'bg-gray-500', label: estado }

    return (
      <Badge className={`${config.color} text-white`}>{config.label}</Badge>
    )
  }

  const handleDescargarPDF = async (cedula: string) => {
    try {
      toast.loading('Generando PDF...')

      const blob = await pagoService.descargarPDFPendientes(cedula)

      const url = window.URL.createObjectURL(blob)
      const opened = window.open(url, '_blank', 'noopener,noreferrer')

      if (!opened) {
        window.URL.revokeObjectURL(url)
        throw new Error(
          'El navegador bloqueo la pestana de previsualizacion del PDF.'
        )
      }

      window.setTimeout(() => window.URL.revokeObjectURL(url), 60_000)

      toast.dismiss()

      toast.success('PDF abierto en una nueva pestana')
    } catch (error: unknown) {
      const { getErrorMessage, getErrorDetail } =
        await import('../../types/errors')

      let errorMessage = getErrorMessage(error)

      const detail = getErrorDetail(error)

      if (detail) {
        errorMessage = detail
      }

      toast.dismiss()

      console.error('Error descargando PDF:', errorMessage)

      toast.error(errorMessage || 'Error al descargar PDF')
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filtros de Búsqueda
          </CardTitle>
        </CardHeader>

        <CardContent>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Buscar por cédula
              </label>

              <Input
                placeholder="Escriba cédula para filtrar..."
                value={filters.cedula}
                onChange={e => handleFilterChange('cedula', e.target.value)}
              />
            </div>

            <Select
              value={filters.estado || 'all'}
              onValueChange={value => handleFilterChange('estado', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Estado" />
              </SelectTrigger>

              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>

                <SelectItem value="PAGADO">Pagado</SelectItem>

                <SelectItem value="PENDIENTE">Pendiente</SelectItem>

                <SelectItem value="ATRASADO">Atrasado</SelectItem>

                <SelectItem value="PARCIAL">Parcial</SelectItem>

                <SelectItem value="ADELANTADO">Adelantado</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="mt-4 border-t border-gray-100 pt-4">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Buscar por serial / Nº documento
            </label>
            <p className="mb-2 text-xs text-gray-500">
              Muestra en qué préstamo y cédula está aplicado el comprobante
              (incluye variantes con código §CD: o sufijo legado).
            </p>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <Input
                className="sm:max-w-md"
                placeholder="Ej. 54879263323"
                value={serialInput}
                onChange={e => setSerialInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    void handleBuscarSerial()
                  }
                }}
              />
              <div className="flex gap-2">
                <Button
                  type="button"
                  onClick={() => void handleBuscarSerial()}
                  disabled={serialBuscando}
                >
                  {serialBuscando ? (
                    <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="mr-1 h-4 w-4" />
                  )}
                  Buscar serial
                </Button>
                {serialHits != null ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setSerialHits(null)
                      setSerialBuscado(null)
                      setSerialInput('')
                    }}
                  >
                    Limpiar
                  </Button>
                ) : null}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {serialHits != null ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Resultado serial
              {serialBuscado ? (
                <span className="ml-2 font-mono text-sm font-normal text-gray-600">
                  {serialBuscado}
                </span>
              ) : null}
              <span className="ml-2 text-sm font-normal text-gray-500">
                ({serialHits.length} pago
                {serialHits.length === 1 ? '' : 's'})
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!serialHits.length ? (
              <p className="py-6 text-center text-sm text-gray-500">
                No hay pagos en cartera con ese serial.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="px-3 py-2 text-left">Cédula</th>
                      <th className="px-3 py-2 text-left">Préstamo</th>
                      <th className="px-3 py-2 text-left">Pago ID</th>
                      <th className="px-3 py-2 text-left">Nº documento</th>
                      <th className="px-3 py-2 text-right">Monto</th>
                      <th className="px-3 py-2 text-left">Fecha</th>
                      <th className="px-3 py-2 text-left">Estado</th>
                      <th className="px-3 py-2 text-left">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {serialHits.map(hit => (
                      <tr
                        key={hit.pago_id}
                        className="border-b hover:bg-gray-50"
                      >
                        <td className="px-3 py-2 font-medium">
                          {hit.cedula || '—'}
                        </td>
                        <td className="px-3 py-2">
                          {hit.prestamo_id != null ? hit.prestamo_id : '—'}
                        </td>
                        <td className="px-3 py-2">{hit.pago_id}</td>
                        <td
                          className="max-w-[14rem] truncate px-3 py-2 font-mono text-xs"
                          title={hit.numero_documento || undefined}
                        >
                          {hit.numero_documento || '—'}
                        </td>
                        <td className="px-3 py-2 text-right">
                          $
                          {(hit.monto_pagado != null
                            ? Number(hit.monto_pagado)
                            : 0
                          ).toFixed(2)}
                        </td>
                        <td className="px-3 py-2">
                          {hit.fecha_pago ? formatDate(hit.fecha_pago) : '—'}
                        </td>
                        <td className="px-3 py-2">
                          {hit.estado ? getEstadoBadge(hit.estado) : '—'}
                        </td>
                        <td className="px-3 py-2">
                          <Button
                            size="sm"
                            variant="default"
                            disabled={!hit.cedula}
                            onClick={() =>
                              hit.cedula && abrirDetalleCedula(hit.cedula)
                            }
                            title="Filtrar por esta cédula y ver historial"
                          >
                            <Eye className="mr-1 h-4 w-4" />
                            Ver cédula
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>
            Detalle por Cliente (último pago y ver historial)
          </CardTitle>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="py-12 text-center">Cargando...</div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="px-4 py-3 text-left">Cédula</th>

                      <th className="px-4 py-3 text-left">ID Último Pago</th>

                      <th className="px-4 py-3 text-left">Estado</th>

                      <th className="px-4 py-3 text-right">
                        Monto Último Pago
                      </th>

                      <th className="px-4 py-3 text-left">Fecha Último Pago</th>

                      <th className="px-4 py-3 text-right">Cuotas Atrasadas</th>

                      <th className="px-4 py-3 text-right">Saldo Vencido</th>

                      <th className="px-4 py-3 text-left">Total Préstamos</th>

                      <th className="px-4 py-3 text-left">Acciones</th>
                    </tr>
                  </thead>

                  <tbody>
                    {data?.items?.map((item: UltimoPago) => (
                      <tr
                        key={`${item.cedula}-${item.pago_id}`}
                        className="border-b hover:bg-gray-50"
                      >
                        <td className="px-4 py-3 font-medium">{item.cedula}</td>

                        <td className="px-4 py-3">{item.pago_id}</td>

                        <td className="px-4 py-3">
                          {getEstadoBadge(item.estado_pago)}
                        </td>

                        <td className="px-4 py-3 text-right">
                          ${item.monto_ultimo_pago.toFixed(2)}
                        </td>

                        <td className="px-4 py-3">
                          {item.fecha_ultimo_pago
                            ? formatDate(item.fecha_ultimo_pago)
                            : 'N/A'}
                        </td>

                        <td className="px-4 py-3 text-right">
                          <Badge
                            variant={
                              item.cuotas_atrasadas > 0
                                ? 'destructive'
                                : 'default'
                            }
                          >
                            {item.cuotas_atrasadas}
                          </Badge>
                        </td>

                        <td className="px-4 py-3 text-right font-semibold">
                          ${item.saldo_vencido.toFixed(2)}
                        </td>

                        <td className="px-4 py-3">{item.total_prestamos}</td>

                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="default"
                              onClick={() => {
                                setCedulaDetalle(item.cedula)

                                setPageDetalle(1)
                              }}
                              title="Ver todos los pagos del cliente (más reciente a más antiguo)"
                            >
                              <Eye className="mr-1 h-4 w-4" />
                              Ver detalle
                            </Button>

                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleDescargarPDF(item.cedula)}
                              title="Descargar PDF de pendientes"
                            >
                              <FileText className="mr-1 h-4 w-4" />
                              PDF
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {data && data.total > 0 && (
                <ListPaginationBar
                  className="mt-4"
                  page={page}
                  totalPages={Math.max(1, data.total_pages)}
                  onPageChange={p => setPage(p)}
                  subtitle={
                    typeof data.per_page === 'number'
                      ? `${data.total} clientes · ${data.per_page} por página`
                      : `${data.total} clientes`
                  }
                />
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Dialog
        open={!!cedulaDetalle}
        onOpenChange={open => !open && setCedulaDetalle(null)}
      >
        <DialogContent className="max-h-[90vh] max-w-4xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>Pagos del cliente: {cedulaDetalle}</span>

              <Button
                variant="ghost"
                size="icon"
                onClick={() => setCedulaDetalle(null)}
                aria-label="Cerrar"
              >
                <X className="h-4 w-4" />
              </Button>
            </DialogTitle>
          </DialogHeader>

          <p className="mb-4 text-sm text-gray-600">
            Orden: del más reciente al más antiguo. Use la paginación para ver
            más registros.
          </p>

          {loadingDetalle ? (
            <div className="py-8 text-center text-gray-500">
              Cargando pagos...
            </div>
          ) : !detalleData?.pagos?.length ? (
            <div className="py-8 text-center text-gray-500">
              No hay pagos para esta cédula.
            </div>
          ) : (
            <>
              <div className="overflow-hidden rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>

                      <TableHead>Préstamo</TableHead>

                      <TableHead>Fecha Pago</TableHead>

                      <TableHead>Monto</TableHead>

                      <TableHead>Estado</TableHead>

                      <TableHead>Nº Documento</TableHead>

                      <TableHead>Conciliado</TableHead>
                    </TableRow>
                  </TableHeader>

                  <TableBody>
                    {detalleData.pagos.map((pago: Pago) => (
                      <TableRow key={pago.id}>
                        <TableCell>{pago.id}</TableCell>

                        <TableCell>
                          {pago.prestamo_id != null ? pago.prestamo_id : '—'}
                        </TableCell>

                        <TableCell>{formatDate(pago.fecha_pago)}</TableCell>

                        <TableCell>
                          $
                          {typeof pago.monto_pagado === 'number'
                            ? pago.monto_pagado.toFixed(2)
                            : parseFloat(
                                String(pago.monto_pagado || 0)
                              ).toFixed(2)}
                        </TableCell>

                        <TableCell>{getEstadoBadge(pago.estado)}</TableCell>

                        <TableCell>{pago.numero_documento ?? '-'}</TableCell>

                        <TableCell>
                          {pago.verificado_concordancia === 'SI' ||
                          pago.conciliado ? (
                            <Badge className="bg-green-500 text-white">
                              Sí
                            </Badge>
                          ) : (
                            <Badge variant="secondary">No</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {detalleData.total > 0 && (
                <ListPaginationBar
                  className="mt-4"
                  page={pageDetalle}
                  totalPages={Math.max(1, detalleData.total_pages)}
                  onPageChange={p => setPageDetalle(p)}
                  subtitle={
                    typeof detalleData.per_page === 'number'
                      ? `${detalleData.total} pagos · ${detalleData.per_page} por página`
                      : `${detalleData.total} pagos`
                  }
                />
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
