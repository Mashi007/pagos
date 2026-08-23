import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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
import { getErrorDetail, getErrorMessage } from '../../types/errors'

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
  origen?: 'pagos' | 'pagos_reportados' | string
  pago_id: number | null
  reportado_id?: number | null
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
  initialCedula = '',
  initialPrestamoId = '',
  initialPagoId = '',
}: {
  fetchEnabled?: boolean
  /** Deep-link desde URL (?cedula=). */
  initialCedula?: string
  /** Deep-link desde URL (?prestamo_id=). */
  initialPrestamoId?: string
  /** Deep-link desde URL (?pago_id=). */
  initialPagoId?: string
}) {
  const [page, setPage] = useState(1)
  const [perPage] = useState(10)
  const [filters, setFilters] = useState({
    cedula: '',
    estado: '',
  })
  const [pagoIdInput, setPagoIdInput] = useState('')
  const [prestamoIdInput, setPrestamoIdInput] = useState('')
  const [serialInput, setSerialInput] = useState('')
  const [identificando, setIdentificando] = useState(false)
  const [serialBuscando, setSerialBuscando] = useState(false)
  const [serialHits, setSerialHits] = useState<SerialHit[] | null>(null)
  const [serialBuscado, setSerialBuscado] = useState<string | null>(null)
  const [cedulaDetalle, setCedulaDetalle] = useState<string | null>(null)
  /** Si se identificó por préstamo, el historial puede resaltarlo. */
  const [prestamoDetalleFiltro, setPrestamoDetalleFiltro] = useState<
    number | null
  >(null)
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
    queryKey: [
      'pagos-por-cedula',
      cedulaDetalle,
      pageDetalle,
      perPageDetalle,
      prestamoDetalleFiltro,
    ],
    queryFn: () =>
      pagoService.getAllPagos(pageDetalle, perPageDetalle, {
        cedula: cedulaDetalle || '',
        prestamo_cartera: 'todos',
        ...(prestamoDetalleFiltro != null
          ? { prestamo_id: prestamoDetalleFiltro }
          : {}),
      }),
    enabled: !!cedulaDetalle,
    staleTime: 0,
  })

  const handleFilterChange = (key: string, value: string) => {
    const filterValue = value === 'all' ? '' : value
    setFilters(prev => ({ ...prev, [key]: filterValue }))
    setPage(1)
  }

  const abrirDetalleCedula = (
    cedula: string,
    opts?: { prestamoId?: number | null }
  ) => {
    const c = (cedula || '').trim()
    if (!c) {
      toast.error('Sin cédula en ese pago; no se puede abrir el detalle.')
      return
    }
    setFilters(prev => ({ ...prev, cedula: c }))
    setPage(1)
    setCedulaDetalle(c)
    setPageDetalle(1)
    setPrestamoDetalleFiltro(
      opts?.prestamoId != null && Number.isFinite(opts.prestamoId)
        ? Math.trunc(opts.prestamoId)
        : null
    )
  }

  /** Identifica por cédula, ID pago o ID préstamo y abre detalle por cliente. */
  const handleIdentificar = async () => {
    const ced = filters.cedula.trim()
    const pagoRaw = pagoIdInput.trim()
    const prestRaw = prestamoIdInput.trim()

    if (!ced && !pagoRaw && !prestRaw) {
      toast.error('Indique cédula, ID de pago o ID de préstamo')
      return
    }

    setIdentificando(true)
    setSerialHits(null)
    try {
      if (pagoRaw) {
        const pid = Number(pagoRaw)
        if (!Number.isFinite(pid) || pid < 1) {
          toast.error('ID de pago inválido')
          return
        }
        const pago = await pagoService.getPago(Math.trunc(pid))
        const cedulaPago = (
          pago.cedula_cliente ||
          (pago as { cedula?: string }).cedula ||
          ''
        ).trim()
        if (!cedulaPago) {
          toast.error(`Pago #${pid} sin cédula; no se puede abrir el detalle.`)
          return
        }
        setPagoIdInput(String(Math.trunc(pid)))
        if (pago.prestamo_id != null) {
          setPrestamoIdInput(String(pago.prestamo_id))
        }
        abrirDetalleCedula(cedulaPago, {
          prestamoId: pago.prestamo_id ?? null,
        })
        toast.success(
          `Pago #${pid} → cliente ${cedulaPago}` +
            (pago.prestamo_id != null ? ` · préstamo ${pago.prestamo_id}` : '')
        )
        return
      }

      if (prestRaw) {
        const prestamoId = Number(prestRaw)
        if (!Number.isFinite(prestamoId) || prestamoId < 1) {
          toast.error('ID de préstamo inválido')
          return
        }
        const res = await pagoService.getAllPagos(1, 1, {
          prestamo_id: Math.trunc(prestamoId),
          prestamo_cartera: 'todos',
        })
        const primero = res.pagos?.[0]
        const cedulaP = (primero?.cedula_cliente || '').trim()
        if (!cedulaP) {
          toast.message(
            `Sin pagos en cartera para préstamo #${Math.trunc(prestamoId)}`
          )
          return
        }
        setPrestamoIdInput(String(Math.trunc(prestamoId)))
        abrirDetalleCedula(cedulaP, {
          prestamoId: Math.trunc(prestamoId),
        })
        toast.success(
          `Préstamo #${Math.trunc(prestamoId)} → cliente ${cedulaP}`
        )
        return
      }

      // Solo cédula: filtrar rollup y abrir historial.
      abrirDetalleCedula(ced)
    } catch (error: unknown) {
      let errorMessage = getErrorMessage(error)
      const detail = getErrorDetail(error)
      if (detail) errorMessage = detail
      toast.error(errorMessage || 'No se pudo identificar el pago')
    } finally {
      setIdentificando(false)
    }
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
      toast.success('PDF abierto en nueva pestaña')
    } catch (error: unknown) {
      toast.dismiss()
      const errorMessage = getErrorMessage(error)
      console.error('Error descargando PDF:', errorMessage)
      toast.error(errorMessage || 'Error al descargar PDF')
    }
  }

  // Deep-links desde PagosList (?cedula / ?pago_id / ?prestamo_id).
  useEffect(() => {
    const c = (initialCedula || '').trim()
    const p = (initialPagoId || '').trim()
    const pr = (initialPrestamoId || '').trim()
    if (!c && !p && !pr) return
    if (c) setFilters(prev => ({ ...prev, cedula: c }))
    if (p) setPagoIdInput(p)
    if (pr) setPrestamoIdInput(pr)
    // Auto-identificar si viene pago o préstamo (abre detalle por cliente).
    if (p || pr) {
      void (async () => {
        setIdentificando(true)
        try {
          if (p) {
            const pid = Number(p)
            if (!Number.isFinite(pid) || pid < 1) return
            const pago = await pagoService.getPago(Math.trunc(pid))
            const cedulaPago = (
              pago.cedula_cliente ||
              (pago as { cedula?: string }).cedula ||
              ''
            ).trim()
            if (cedulaPago) {
              abrirDetalleCedula(cedulaPago, {
                prestamoId: pago.prestamo_id ?? null,
              })
            }
            return
          }
          if (pr) {
            const prestamoId = Number(pr)
            if (!Number.isFinite(prestamoId) || prestamoId < 1) return
            const res = await pagoService.getAllPagos(1, 1, {
              prestamo_id: Math.trunc(prestamoId),
              prestamo_cartera: 'todos',
            })
            const cedulaP = (res.pagos?.[0]?.cedula_cliente || '').trim()
            if (cedulaP) {
              abrirDetalleCedula(cedulaP, {
                prestamoId: Math.trunc(prestamoId),
              })
            }
          }
        } catch {
          /* toast al usar Identificar manualmente */
        } finally {
          setIdentificando(false)
        }
      })()
    } else if (c) {
      setCedulaDetalle(c)
      setPageDetalle(1)
    }
    // Solo al montar / cambiar deep-link props
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialCedula, initialPagoId, initialPrestamoId])

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Filter className="h-5 w-5" />
            Identificar pago
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-2 lg:grid-cols-12">
            <div className="lg:col-span-3">
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Cédula
              </label>
              <Input
                placeholder="Ej. V12345678"
                value={filters.cedula}
                onChange={e => handleFilterChange('cedula', e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    void handleIdentificar()
                  }
                }}
              />
            </div>
            <div className="lg:col-span-2">
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                ID pago
              </label>
              <Input
                placeholder="Ej. 60321"
                inputMode="numeric"
                value={pagoIdInput}
                onChange={e => setPagoIdInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    void handleIdentificar()
                  }
                }}
              />
            </div>
            <div className="lg:col-span-2">
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                ID préstamo
              </label>
              <Input
                placeholder="Ej. 7105"
                inputMode="numeric"
                value={prestamoIdInput}
                onChange={e => setPrestamoIdInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    void handleIdentificar()
                  }
                }}
              />
            </div>
            <div className="lg:col-span-2">
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Estado (lista)
              </label>
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
            <div className="flex flex-wrap gap-2 sm:col-span-2 lg:col-span-3 lg:justify-end">
              <Button
                type="button"
                className="min-w-[7.5rem] flex-1 sm:flex-none"
                onClick={() => void handleIdentificar()}
                disabled={identificando}
              >
                {identificando ? (
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                ) : (
                  <Search className="mr-1.5 h-4 w-4" />
                )}
                Identificar
              </Button>
              <Button
                type="button"
                variant="outline"
                className="min-w-[5.5rem] flex-1 sm:flex-none"
                onClick={() => {
                  setFilters({ cedula: '', estado: '' })
                  setPagoIdInput('')
                  setPrestamoIdInput('')
                  setSerialInput('')
                  setSerialHits(null)
                  setSerialBuscado(null)
                  setCedulaDetalle(null)
                  setPrestamoDetalleFiltro(null)
                  setPage(1)
                }}
              >
                Limpiar
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 items-end gap-3 border-t border-slate-100 pt-5 sm:grid-cols-2 lg:grid-cols-12">
            <div className="sm:col-span-2 lg:col-span-9">
              <label className="mb-1.5 block text-sm font-medium text-gray-700">
                Serial / Nº documento
              </label>
              <Input
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
            </div>
            <div className="flex lg:col-span-3 lg:justify-end">
              <Button
                type="button"
                variant="outline"
                className="w-full min-w-[7.5rem] lg:w-auto"
                onClick={() => void handleBuscarSerial()}
                disabled={serialBuscando}
              >
                {serialBuscando ? (
                  <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
                ) : (
                  <Search className="mr-1.5 h-4 w-4" />
                )}
                Buscar serial
              </Button>
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
                No hay coincidencias en cartera ni en pagos reportados.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="px-3 py-2 text-left">Origen</th>
                      <th className="px-3 py-2 text-left">Cédula</th>
                      <th className="px-3 py-2 text-left">Préstamo</th>
                      <th className="px-3 py-2 text-left">ID pago</th>
                      <th className="px-3 py-2 text-left">Nº documento</th>
                      <th className="px-3 py-2 text-right">Monto</th>
                      <th className="px-3 py-2 text-left">Fecha</th>
                      <th className="px-3 py-2 text-left">Estado</th>
                      <th className="px-3 py-2 text-left">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {serialHits.map(hit => {
                      const esReportado = hit.origen === 'pagos_reportados'
                      const rowKey = esReportado
                        ? `rep-${hit.reportado_id}`
                        : `pago-${hit.pago_id}`
                      return (
                        <tr
                          key={rowKey}
                          className="border-b hover:bg-gray-50"
                        >
                          <td className="px-3 py-2">
                            {esReportado ? (
                              <Badge variant="secondary">Reportado</Badge>
                            ) : (
                              <Badge className="bg-slate-700 text-white">
                                Cartera
                              </Badge>
                            )}
                          </td>
                          <td className="px-3 py-2 font-medium">
                            {hit.cedula || '—'}
                          </td>
                          <td className="px-3 py-2">
                            {hit.prestamo_id != null ? hit.prestamo_id : '—'}
                          </td>
                          <td className="px-3 py-2 font-mono text-xs">
                            {esReportado
                              ? hit.reportado_id != null
                                ? `rep #${hit.reportado_id}`
                                : '—'
                              : hit.pago_id != null
                                ? `#${hit.pago_id}`
                                : '—'}
                          </td>
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
                            {hit.estado ? (
                              esReportado ? (
                                <Badge variant="outline">{hit.estado}</Badge>
                              ) : (
                                getEstadoBadge(hit.estado)
                              )
                            ) : (
                              '—'
                            )}
                          </td>
                          <td className="px-3 py-2">
                            <div className="flex flex-wrap gap-1">
                              {hit.cedula ? (
                                <Button
                                  size="sm"
                                  variant="default"
                                  onClick={() =>
                                    abrirDetalleCedula(hit.cedula!, {
                                      prestamoId: hit.prestamo_id,
                                    })
                                  }
                                  title="Abrir historial del cliente"
                                >
                                  <Eye className="mr-1 h-4 w-4" />
                                  Ver cédula
                                </Button>
                              ) : null}
                              {esReportado && hit.reportado_id != null ? (
                                <Button size="sm" variant="outline" asChild>
                                  <Link
                                    to={`/cobros/pagos-reportados/${hit.reportado_id}/editar`}
                                  >
                                    Abrir reporte
                                  </Link>
                                </Button>
                              ) : null}
                            </div>
                          </td>
                        </tr>
                      )
                    })}
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
            Detalle por Cliente
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
                      <th className="px-4 py-3 text-left">ID pago</th>
                      <th className="px-4 py-3 text-left">Préstamo</th>
                      <th className="px-4 py-3 text-left">Estado</th>
                      <th className="px-4 py-3 text-right">Monto último</th>
                      <th className="px-4 py-3 text-left">Fecha último</th>
                      <th className="px-4 py-3 text-right">Cuotas atrasadas</th>
                      <th className="px-4 py-3 text-right">Saldo vencido</th>
                      <th className="px-4 py-3 text-left">Total préstamos</th>
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
                        <td className="px-4 py-3 font-mono text-sm">
                          {item.pago_id}
                        </td>
                        <td className="px-4 py-3">
                          {item.prestamo_id != null ? item.prestamo_id : '—'}
                        </td>
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
                              onClick={() =>
                                abrirDetalleCedula(item.cedula, {
                                  prestamoId: item.prestamo_id,
                                })
                              }
                              title="Ver todos los pagos del cliente"
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
        onOpenChange={open => {
          if (!open) {
            setCedulaDetalle(null)
            setPrestamoDetalleFiltro(null)
          }
        }}
      >
        <DialogContent className="max-h-[90vh] max-w-4xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>
                Pagos del cliente: {cedulaDetalle}
                {prestamoDetalleFiltro != null
                  ? ` · préstamo #${prestamoDetalleFiltro}`
                  : ''}
              </span>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => {
                  setCedulaDetalle(null)
                  setPrestamoDetalleFiltro(null)
                }}
                aria-label="Cerrar"
              >
                <X className="h-4 w-4" />
              </Button>
            </DialogTitle>
          </DialogHeader>
          {prestamoDetalleFiltro != null ? (
            <p className="mb-4 text-sm text-gray-600">
              Préstamo #{prestamoDetalleFiltro}
            </p>
          ) : null}
          {loadingDetalle ? (
            <div className="py-8 text-center text-gray-500">
              Cargando pagos...
            </div>
          ) : !detalleData?.pagos?.length ? (
            <div className="py-8 text-center text-gray-500">
              No hay pagos para esta cédula
              {prestamoDetalleFiltro != null
                ? ` / préstamo #${prestamoDetalleFiltro}`
                : ''}
              .
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
