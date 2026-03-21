/**









 * Listado de pagos reportados (mÃÆ'ƒÂ³dulo Cobros). Filtros, tabla, acciones Ver detalle / Aprobar / Rechazar.









 */

import React, { useState, useEffect } from 'react'

import { useNavigate } from 'react-router-dom'

import {
  listPagosReportados,
  getPagosReportadosKpis,
  cambiarEstadoPago,
  openComprobanteInNewTab,
  eliminarPagoReportado,
  markPagosReportadosExportados,
  type PagoReportadoItem,
  descargarPagosAprobadosExcel,
  type ListPagosReportadosResponse,
  type PagosReportadosKpis,
} from '../services/cobrosService'

import { Button } from '../components/ui/button'

import { Input } from '../components/ui/input'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { Badge } from '../components/ui/badge'

import toast from 'react-hot-toast'

import {
  Loader2,
  Eye,
  FileText,
  Settings,
  Clock,
  Search,
  CheckCircle,
  XCircle,
  Trash2,
  AlertCircle,
  AlertTriangle,
  Edit,
  Mail,
} from 'lucide-react'

import { PUBLIC_REPORTE_PAGO_PATH } from '../config/env'

import { createAndDownloadExcel } from '../types/exceljs'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../components/ui/dialog'

const MENSAJE_RECHAZO_POR_DEFECTO = `Buenas tardes



















La imagen no se aprecia detalles, agradezco enviar una imagen sin recortar a cobranza@rapicreditca.com



















Gracias`

const ESTADO_CONFIG: Record<
  string,
  {
    label: string
    short: string
    variant: 'default' | 'secondary' | 'destructive' | 'outline'
    Icon: typeof Clock
  }
> = {
  pendiente: {
    label: 'Pendiente',
    short: 'Pend.',
    variant: 'secondary',
    Icon: Clock,
  },

  en_revision: {
    label: 'En revisión (manual)',
    short: 'Revisión',
    variant: 'outline',
    Icon: Search,
  },

  aprobado: {
    label: 'Aprobado',
    short: 'Aprobado',
    variant: 'default',
    Icon: CheckCircle,
  },

  importado: {
    label: 'Importado a Pagos',
    short: 'Import.',
    variant: 'default',
    Icon: CheckCircle,
  },

  rechazado: {
    label: 'Rechazado',
    short: 'Rechazado',
    variant: 'destructive',
    Icon: XCircle,
  },
}

const normalizeEstadoValue = (value: string) =>
  String(value ?? '')
    .normalize('NFD')

    .replace(/[\u0300-\u036f]/g, '')

    .trim()

    .replace(/\s+/g, '_')

    .toLowerCase()

const isEstadoAprobado = (estadoValue: string) =>
  normalizeEstadoValue(estadoValue) === 'aprobado'

export default function CobrosPagosReportadosPage() {
  const navigate = useNavigate()

  const [data, setData] = useState<ListPagosReportadosResponse | null>(null)

  const [loading, setLoading] = useState(true)

  const [page, setPage] = useState(1)

  const [estado, setEstado] = useState<string>('')

  const [fechaDesde, setFechaDesde] = useState('')

  const [fechaHasta, setFechaHasta] = useState('')

  const [cedula, setCedula] = useState('')

  const [institucion, setInstitucion] = useState('')

  const [changingEstadoId, setChangingEstadoId] = useState<number | null>(null)

  const [viewingComprobanteId, setViewingComprobanteId] = useState<
    number | null
  >(null)

  const [deletingId, setDeletingId] = useState<number | null>(null)

  const [rechazarModal, setRechazarModal] = useState<{
    open: boolean
    row: PagoReportadoItem | null
  }>({ open: false, row: null })

  const [motivoRechazo, setMotivoRechazo] = useState('')

  const [descargandoTabla, setDescargandoTabla] = useState(false)

  const [kpis, setKpis] = useState<PagosReportadosKpis | null>(null)

  const load = async (overrides?: { estado?: string; page?: number }) => {
    const effectiveEstado =
      overrides?.estado !== undefined ? overrides.estado : estado

    const effectivePage = overrides?.page !== undefined ? overrides.page : page

    if (overrides) {
      if (overrides.estado !== undefined) setEstado(overrides.estado)

      if (overrides.page !== undefined) setPage(overrides.page)
    }

    setLoading(true)

    try {
      const filterParams = {
        fecha_desde: fechaDesde || undefined,

        fecha_hasta: fechaHasta || undefined,

        cedula: cedula.trim() || undefined,

        institucion: institucion.trim() || undefined,
      }

      const [res, kpisRes] = await Promise.all([
        listPagosReportados({
          page: effectivePage,

          per_page: 20,

          estado: effectiveEstado || undefined,

          ...filterParams,
        }),

        getPagosReportadosKpis(filterParams),
      ])

      setData(res)

      setKpis(kpisRes)
    } catch (e: any) {
      toast.error(e?.message || 'Error al cargar.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [page])

  const handleKpiClick = (estadoKey: string) => {
    load({ estado: estadoKey, page: 1 })
  }

  const handleCambiarEstado = async (
    id: number,
    estado: string,
    motivo?: string
  ) => {
    setChangingEstadoId(id)

    try {
      await cambiarEstadoPago(id, estado, motivo)

      toast.success(
        estado === 'rechazado'
          ? 'Pago rechazado. Correo enviado al cliente desde notificaciones@rapicreditca.com.'
          : 'Estado actualizado.'
      )

      load()

      if (estado === 'rechazado') {
        setRechazarModal({ open: false, row: null })

        setMotivoRechazo('')
      }
    } catch (e: any) {
      toast.error(e?.message || 'Error al actualizar.')
    } finally {
      setChangingEstadoId(null)
    }
  }

  const handleAbrirModalRechazo = (row: PagoReportadoItem) => {
    setMotivoRechazo(MENSAJE_RECHAZO_POR_DEFECTO)

    const rowToOpen = { ...row }

    setTimeout(() => setRechazarModal({ open: true, row: rowToOpen }), 0)
  }

  const handleConfirmarRechazo = () => {
    if (!rechazarModal.row || !motivoRechazo.trim()) {
      toast.error('El motivo de rechazo es obligatorio.')

      return
    }

    handleCambiarEstado(rechazarModal.row.id, 'rechazado', motivoRechazo.trim())
  }

  const handleEliminar = async (id: number, ref: string) => {
    if (
      !window.confirm(
        'Eliminar el pago reportado ' +
          ref +
          '? Esta acción no se puede deshacer.'
      )
    )
      return

    setDeletingId(id)

    try {
      await eliminarPagoReportado(id)

      toast.success('Pago reportado eliminado.')

      load()
    } catch (e: any) {
      toast.error(e?.message || 'Error al eliminar.')
    } finally {
      setDeletingId(null)
    }
  }

  const handleVerComprobante = async (id: number) => {
    setViewingComprobanteId(id)

    try {
      await openComprobanteInNewTab(id)
    } catch (e: any) {
      toast.error(e?.message || 'No se pudo abrir el comprobante.')
    } finally {
      setViewingComprobanteId(null)
    }
  }

  const handleDescargarExcelAprobados = async () => {
    const aprobados = (data?.items ?? []).filter(row =>
      isEstadoAprobado(row.estado)
    )

    if (!aprobados.length) {
      toast('No hay pagos aprobados para exportar con los filtros actuales.')

      return
    }

    const rows = aprobados.map(row => {
      return {
        Nombre: String(row.nombres) + ' ' + String(row.apellidos),
        Cedula: row.cedula_display,
        Banco: row.institucion_financiera,
        Monto: String(row.monto) + ' ' + String(row.moneda),
        'Fecha pago': row.fecha_pago,
        'Numero operacion': row.numero_operacion,
        'Fecha reporte': row.fecha_reporte
          ? new Date(row.fecha_reporte).toLocaleDateString()
          : '',
        Observacion: row.observacion ?? '',
        Estado:
          ESTADO_CONFIG[normalizeEstadoValue(row.estado)]?.label ?? row.estado,
      }
    })

    const fecha = new Date().toISOString().slice(0, 10)

    try {
      await createAndDownloadExcel(
        rows,
        'Pagos Aprobados',
        'pagos_reportados_aprobados_' + fecha + '.xlsx'
      )

      const idsAprobados = aprobados.map(row => row.id)

      const markResult = await markPagosReportadosExportados(idsAprobados)

      toast.success(
        'Excel generado con ' +
          String(rows.length) +
          ' pago(s) aprobado(s). Marcados exportados: ' +
          String(markResult.marcados) +
          '.'
      )

      await load({ page: 1 })
    } catch (e: any) {
      toast.error(
        e?.message ||
          'Se descarg? el Excel, pero fall? el marcado de exportados. Recargue e intente de nuevo.'
      )
    }

    const handleDescargarPagosTablaTemporalExcel = async () => {
      setDescargandoTabla(true)

      try {
        await descargarPagosAprobadosExcel()

        toast.success(
          'Excel descargado. Los pagos han sido eliminados de la tabla temporal.'
        )

        // Recargar la lista después de descargar

        await load({ page: 1 })
      } catch (e: any) {
        toast.error(e?.message || 'Error al descargar el Excel.')
      } finally {
        setDescargandoTabla(false)
      }
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Pagos Reportados</h1>

        <a
          href={
            (typeof window !== 'undefined' ? window.location.origin : '') +
            (import.meta.env.BASE_URL || '/').replace(/\/$/, '') +
            '/' +
            PUBLIC_REPORTE_PAGO_PATH
          }
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-600 hover:underline"
        >
          Link al formulario público
        </a>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filtros</CardTitle>
        </CardHeader>

        <CardContent className="flex flex-wrap gap-4">
          <select
            className="rounded-md border px-3 py-2"
            value={estado}
            onChange={e => setEstado(e.target.value)}
          >
            <option value="">Todos los estados</option>

            <option value="pendiente">Pendiente</option>

            <option value="en_revision">En revisiÃÆ'ƒÂ³n</option>

            <option value="aprobado">Aprobado</option>

            <option value="rechazado">Rechazado</option>

            <option value="importado">Importado a Pagos</option>
          </select>

          <Input
            type="date"
            placeholder="Fecha desde"
            value={fechaDesde}
            onChange={e => setFechaDesde(e.target.value)}
            className="w-40"
          />

          <Input
            type="date"
            placeholder="Fecha hasta"
            value={fechaHasta}
            onChange={e => setFechaHasta(e.target.value)}
            className="w-40"
          />

          <Input
            placeholder="CÃÆ'ƒÂ©dula"
            value={cedula}
            onChange={e => setCedula(e.target.value)}
            className="w-40"
          />

          <Input
            placeholder="InstituciÃÆ'ƒÂ³n"
            value={institucion}
            onChange={e => setInstitucion(e.target.value)}
            className="w-48"
          />

          <Button onClick={() => load()}>Buscar</Button>

          <Button variant="outline" onClick={handleDescargarExcelAprobados}>
            Descargar Excel Aprobados
          </Button>

          <Button
            variant="outline"
            onClick={handleDescargarPagosTablaTemporalExcel}
            disabled={descargandoTabla}
          >
            {descargandoTabla ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <FileText className="mr-2 h-4 w-4" />
            )}
            Descargar de Tabla Temporal
          </Button>
        </CardContent>
      </Card>

      {kpis != null && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => handleKpiClick('')}
            className={
              'min-w-28 rounded-lg border-2 px-4 py-3 text-left transition-colors ' +
              (estado === ''
                ? 'border-primary bg-primary/10 font-semibold'
                : 'border-muted hover:bg-muted/50')
            }
          >
            <span className="block text-xs uppercase tracking-wide text-muted-foreground">
              Todos
            </span>

            <span className="text-2xl font-bold">{kpis.total}</span>
          </button>

          {(['pendiente', 'en_revision', 'aprobado', 'rechazado'] as const).map(
            key => {
              const cfg = ESTADO_CONFIG[key]

              const Icon = cfg.Icon

              const selected = estado === key

              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => handleKpiClick(key)}
                  className={
                    'flex min-w-28 flex-col gap-0.5 rounded-lg border-2 px-4 py-3 text-left transition-colors ' +
                    (selected
                      ? 'border-primary bg-primary/10 font-semibold'
                      : 'border-muted hover:bg-muted/50')
                  }
                >
                  <span className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-muted-foreground">
                    <Icon className="h-3.5 w-3.5" />

                    {cfg.label}
                  </span>

                  <span className="text-2xl font-bold">{kpis[key]}</span>
                </button>
              )
            }
          )}
        </div>
      )}

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p>Cargando...</p>
          ) : !data?.items?.length ? (
            <p className="text-gray-500">No hay registros.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[1000px] table-fixed text-sm">
                <colgroup>
                  <col style={{ width: '14%' }} />

                  <col style={{ width: '8%' }} />

                  <col style={{ width: '10%' }} />

                  <col style={{ width: '7%' }} />

                  <col style={{ width: '8%' }} />

                  <col style={{ width: '11%' }} />

                  <col style={{ width: '7%' }} />

                  <col style={{ width: '12%' }} />

                  <col style={{ width: '8%' }} />

                  <col style={{ width: '15%' }} />
                </colgroup>

                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-3 py-3 text-left font-semibold">
                      Nombre
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      CÃÆ'ƒÂ©dula
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">Banco</th>

                    <th className="px-3 py-3 text-right font-semibold">
                      Monto
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Fecha pago
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      NÃÆ''º operaciÃÆ'ƒÂ³n
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Fecha reporte
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      ObservaciÃÆ'ƒÂ³n
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Estado
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Acciones
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {data.items.map((row: PagoReportadoItem) => (
                    <tr
                      key={row.id}
                      className="border-b transition-colors hover:bg-muted/20"
                    >
                      <td className="min-w-0 px-3 py-3 align-top">
                        <span
                          className="block truncate"
                          title={
                            String(row.nombres) + ' ' + String(row.apellidos)
                          }
                        >
                          {row.nombres} {row.apellidos}
                        </span>
                      </td>

                      <td
                        className={
                          'whitespace-nowrap px-3 py-3 align-top ' +
                          (/c[eé]dula/i.test(row.observacion || '')
                            ? 'bg-destructive/10 font-medium text-destructive'
                            : '')
                        }
                        title={
                          /c[eé]dula/i.test(row.observacion || '')
                            ? 'Observación: ' + (row.observacion || '')
                            : undefined
                        }
                      >
                        {/c[eé]dula/i.test(row.observacion || '') && (
                          <AlertCircle
                            className="mr-1 inline-block h-4 w-4 align-middle"
                            aria-hidden
                          />
                        )}

                        {row.cedula_display}
                      </td>

                      <td className="min-w-0 px-3 py-3 align-top">
                        <span
                          className="block truncate"
                          title={row.institucion_financiera}
                        >
                          {row.institucion_financiera}
                        </span>
                      </td>

                      <td className="whitespace-nowrap px-3 py-3 text-right align-top">
                        {row.monto} {row.moneda}
                      </td>

                      <td className="whitespace-nowrap px-3 py-3 align-top">
                        {row.fecha_pago}
                      </td>

                      <td className="min-w-0 px-3 py-3 align-top">
                        <span
                          className="block truncate font-mono text-xs"
                          title={row.numero_operacion}
                        >
                          {row.numero_operacion}
                        </span>
                      </td>

                      <td className="whitespace-nowrap px-3 py-3 align-top">
                        {new Date(row.fecha_reporte).toLocaleDateString()}
                      </td>

                      <td
                        className="min-w-0 px-3 py-3 align-top"
                        title={
                          /NO CLIENTES/i.test(row.observacion || '')
                            ? 'NO CLIENTES: la cédula del reporte (' +
                              row.cedula_display +
                              ') no figura en la tabla clientes. Se compara normalizada (sin guión, sin ceros a la izquierda). Verifique en Préstamos > Clientes o registre al cliente.'
                            : /solo Bs|Bolívares/i.test(row.observacion || '')
                              ? 'Monto en Bs: solo está permitido si la cédula está en la lista de autorizadas para Bolívares (tabla cedulas_reportar_bs). Si no está, use USD o agregue la cédula a la lista en Configuración.'
                              : (row.observacion ?? '')
                        }
                      >
                        {row.observacion ? (
                          <span
                            className={
                              'line-clamp-2 text-xs ' +
                              (/NO CLIENTES/i.test(row.observacion || '')
                                ? 'font-medium text-destructive'
                                : 'text-muted-foreground')
                            }
                          >
                            {row.observacion}
                          </span>
                        ) : (
                          '-'
                        )}
                      </td>

                      <td className="whitespace-nowrap px-3 py-3 align-top">
                        {(() => {
                          const cfg = ESTADO_CONFIG[row.estado] ?? {
                            label: row.estado,
                            short: row.estado,
                            variant: 'outline' as const,
                            Icon: Clock,
                          }

                          const Icon = cfg.Icon

                          return (
                            <Badge
                              variant={cfg.variant}
                              className="inline-flex items-center gap-1 font-normal"
                              title={cfg.label}
                            >
                              <Icon
                                className="h-3.5 w-3.5 shrink-0"
                                aria-hidden
                              />

                              <span>{cfg.short}</span>
                            </Badge>
                          )
                        })()}
                      </td>

                      <td className="px-3 py-3 align-top">
                        <div className="flex flex-wrap items-center justify-start gap-1">
                          {/* Estado envÃÆ'ƒÂ­o recibo: X = no enviado, visto = entregado, triÃÆ'ƒÂ¡ngulo = en revisiÃÆ'ƒÂ³n */}

                          <span
                            className="flex h-8 w-8 shrink-0 items-center justify-center text-muted-foreground"
                            title={
                              row.estado === 'aprobado'
                                ? row.tiene_recibo_pdf && row.correo_enviado_a
                                  ? 'Recibo enviado por correo'
                                  : 'No se envió recibo por correo'
                                : 'En revisión'
                            }
                          >
                            {row.estado === 'aprobado' ? (
                              row.tiene_recibo_pdf && row.correo_enviado_a ? (
                                <CheckCircle
                                  className="h-4 w-4 text-green-600"
                                  aria-hidden
                                />
                              ) : (
                                <XCircle
                                  className="h-4 w-4 text-muted-foreground"
                                  aria-hidden
                                />
                              )
                            ) : (
                              <AlertTriangle
                                className="h-4 w-4 text-blue-600"
                                aria-hidden
                              />
                            )}
                          </span>

                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 shrink-0"
                            title="Ver comprobante (imagen)"
                            onClick={() => handleVerComprobante(row.id)}
                            disabled={viewingComprobanteId === row.id}
                          >
                            {viewingComprobanteId === row.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </Button>

                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            title="Ver detalle"
                            onClick={() =>
                              navigate(
                                '/cobros/pagos-reportados/' + String(row.id)
                              )
                            }
                          >
                            <FileText className="h-4 w-4" />
                          </Button>

                          {(row.estado === 'pendiente' ||
                            row.estado === 'en_revision') && (
                            <>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 shrink-0"
                                title="Editar (modificar valores para cumplir validadores)"
                                onClick={() =>
                                  navigate(
                                    '/cobros/pagos-reportados/' +
                                      String(row.id) +
                                      '/editar'
                                  )
                                }
                              >
                                <Edit className="h-4 w-4" />
                              </Button>

                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 shrink-0 text-destructive hover:bg-destructive/10 hover:text-destructive"
                                title="Rechazar (escribir mensaje y enviar correo)"
                                onClick={() => handleAbrirModalRechazo(row)}
                                disabled={changingEstadoId === row.id}
                              >
                                {changingEstadoId === row.id ? (
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                  <XCircle className="h-4 w-4" />
                                )}
                              </Button>
                            </>
                          )}

                          <div className="relative inline-block h-8 w-8">
                            <select
                              className="absolute inset-0 h-full w-full min-w-0 cursor-pointer opacity-0 disabled:cursor-not-allowed"
                              value=""
                              title="Estado"
                              onChange={e => {
                                const v = e.target.value

                                e.target.value = ''

                                if (!v) return

                                if (v === 'rechazado') {
                                  handleAbrirModalRechazo(row)

                                  return
                                }

                                handleCambiarEstado(row.id, v)
                              }}
                              disabled={changingEstadoId === row.id}
                            >
                              <option value="">ÃÆ'¢â'¬â€</option>

                              <option value="en_revision">
                                En revisiÃÆ'ƒÂ³n
                              </option>

                              <option value="aprobado">Aprobar</option>

                              <option value="rechazado">Rechazar</option>
                            </select>

                            <span
                              className="pointer-events-none flex h-8 w-8 items-center justify-center rounded-md border border-input bg-background"
                              title="Estado"
                            >
                              {changingEstadoId === row.id ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                              ) : (
                                <Settings className="h-4 w-4" />
                              )}
                            </span>
                          </div>

                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:bg-destructive/10 hover:text-destructive"
                            title="Eliminar"
                            onClick={() =>
                              handleEliminar(row.id, row.referencia_interna)
                            }
                            disabled={deletingId === row.id}
                          >
                            {deletingId === row.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {data && data.total > data.per_page && (
            <div className="mt-4 flex justify-between">
              <p className="text-sm text-gray-600">Total: {data.total}</p>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage(p => p - 1)}
                >
                  Anterior
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  disabled={page * data.per_page >= data.total}
                  onClick={() => setPage(p => p + 1)}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Modal: interfaz rÃÆ'ƒÂ¡pida para escribir mensaje de rechazo y enviar correo al cliente */}

      <Dialog
        open={rechazarModal.open}
        onOpenChange={open => {
          if (!open) {
            setRechazarModal({ open: false, row: null })

            setMotivoRechazo('')
          }
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <XCircle className="h-5 w-5" /> Rechazar pago reportado
            </DialogTitle>

            <DialogDescription>
              {rechazarModal.row && (
                <>
                  Referencia:{' '}
                  <strong>
                    {rechazarModal.row.referencia_interna?.startsWith('#')
                      ? rechazarModal.row.referencia_interna
                      : '#' + String(rechazarModal.row.referencia_interna)}
                  </strong>
                  {rechazarModal.row.correo_enviado_a && (
                    <span className="mt-1 block">
                      Se enviará un correo automáticamente a{' '}
                      <strong>{rechazarModal.row.correo_enviado_a}</strong>{' '}
                      desde <strong>notificaciones@rapicreditca.com</strong> con
                      el mensaje y el comprobante adjunto.
                    </span>
                  )}
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-2">
            <label className="block text-sm font-medium">
              Mensaje para el cliente (obligatorio)
            </label>

            <textarea
              className="min-h-[100px] w-full resize-y rounded-md border px-3 py-2 text-sm"
              placeholder="Indique el motivo del rechazo. Este texto se enviarÃÆ'ƒÂ¡ por correo al cliente."
              value={motivoRechazo}
              onChange={e => setMotivoRechazo(e.target.value)}
              autoFocus
            />
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setRechazarModal({ open: false, row: null })

                setMotivoRechazo('')
              }}
            >
              Cancelar
            </Button>

            <Button
              variant="destructive"
              onClick={handleConfirmarRechazo}
              disabled={
                !motivoRechazo.trim() ||
                changingEstadoId === rechazarModal.row?.id
              }
            >
              {changingEstadoId === rechazarModal.row?.id ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Mail className="mr-2 h-4 w-4" />
              )}
              Rechazar y enviar correo
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
