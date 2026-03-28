/**









 * Listado de pagos reportados (módulo Cobros). Filtros, tabla, acciones Ver detalle / Aprobar / Rechazar.
 * Vista por defecto (sin filtro de estado): el API no devuelve aprobados, importados ni rechazados; los rechazados solo con filtro o tarjeta Rechazado. Al aprobar, la fila desaparece y el Excel agrupa aprobados pendientes de exportar.









 */

import React, { useState, useEffect } from 'react'

import { useNavigate } from 'react-router-dom'

import {
  listPagosReportadosConKpis,
  cambiarEstadoPago,
  openComprobanteInNewTab,
  eliminarPagoReportado,
  exportarPagosReportadosAprobadosExcel,
  type PagoReportadoItem,
  type ListPagosReportadosResponse,
  type PagosReportadosKpis,
  type CambiarEstadoPagoResponse,
} from '../services/cobrosService'

import { Button } from '../components/ui/button'

import { Input } from '../components/ui/input'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { Badge } from '../components/ui/badge'

import toast from 'react-hot-toast'

/** Toast según envío real del correo de rechazo (API devuelve mensaje + flags). */
function toastAfterRechazoCobros(data: CambiarEstadoPagoResponse) {
  const msg = data.mensaje ?? 'Estado actualizado a rechazado.'
  if (data.rechazo_correo_enviado === true) {
    toast.success(msg)
  } else if (data.rechazo_correo_enviado === false) {
    const err = data.rechazo_correo_error
    toast.error(
      err ? `${msg} (${err.length > 160 ? `${err.slice(0, 160)}…` : err})` : msg
    )
  } else {
    toast(msg, { duration: 7000 })
  }
}

import {
  Loader2,
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
  Eye,
} from 'lucide-react'

import { PUBLIC_REPORTE_PAGO_PATH } from '../config/env'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../components/ui/dialog'

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '../components/ui/popover'

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

  const [descargandoExcelAprobados, setDescargandoExcelAprobados] =
    useState(false)

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

      const res = await listPagosReportadosConKpis({
        page: effectivePage,

        per_page: 20,

        estado: effectiveEstado || undefined,

        ...filterParams,
      })

      setData(res)

      setKpis(res.kpis)
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
    nuevoEstado: string,
    motivo?: string
  ) => {
    setChangingEstadoId(id)

    try {
      const data = await cambiarEstadoPago(id, nuevoEstado, motivo)

      if (nuevoEstado === 'rechazado') {
        toastAfterRechazoCobros(data)
      } else {
        toast.success(data.mensaje || 'Estado actualizado.')
      }

      // Quitar la fila al instante si la vista actual no lista aprobados (coincide con el API por defecto).
      if (nuevoEstado === 'aprobado' && estado !== 'aprobado') {
        setData(prev => {
          if (!prev) return prev

          return {
            ...prev,
            items: prev.items.filter(r => r.id !== id),
            total: Math.max(0, prev.total - 1),
          }
        })
      }

      await load()

      if (nuevoEstado === 'rechazado') {
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

      await load()
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
    // Servidor: solo aprobados no exportados; mismo criterio de cédula/institución; sin fechas.
    // El Excel y el marcado en BD son atómicos (un solo request).
    setDescargandoExcelAprobados(true)

    try {
      const stats = await exportarPagosReportadosAprobadosExcel({
        cedula: cedula.trim() || undefined,
        institucion: institucion.trim() || undefined,
      })

      toast.success(
        'Excel con ' +
          String(stats.totalFilas) +
          ' aprobado(s). Nuevos exportados: ' +
          String(stats.marcados) +
          (stats.yaExportados > 0
            ? ' (ya constaban ' + String(stats.yaExportados) + ')'
            : '') +
          '. Cola temporal: quitados ' +
          String(stats.quitadosCola) +
          ' registro(s).'
      )

      await load({ page: 1 })
    } catch (e: any) {
      toast.error(e?.message || 'No se pudo exportar el Excel de aprobados.')
    } finally {
      setDescargandoExcelAprobados(false)
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
          <div className="flex min-w-[min(100%,280px)] flex-col gap-1">
            <select
              className="rounded-md border px-3 py-2"
              value={estado}
              onChange={e => setEstado(e.target.value)}
              aria-label="Filtrar por estado del reporte"
            >
              <option value="">
                Por gestionar (excluye aprobados, importados y rechazados)
              </option>

              <option value="pendiente">Pendiente</option>

              <option value="en_revision">En revisión</option>

              <option value="aprobado">
                Aprobado (pendientes de exportar)
              </option>

              <option value="rechazado">Rechazado</option>

              <option value="importado">Importado a Pagos</option>
            </select>

            <p className="text-xs text-muted-foreground">
              La opción por defecto coincide con el listado: al aprobar, la fila
              deja de mostrarse aquí y pasa al Excel &quot;Descargar Excel
              Aprobados&quot;. Los rechazados no se listan aquí: use la tarjeta
              o el filtro &quot;Rechazado&quot;. Si elige &quot;Aprobado&quot;
              en el filtro, las filas aprobadas siguen visibles hasta
              exportarlas.
            </p>
          </div>

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
            placeholder="Cédula"
            value={cedula}
            onChange={e => setCedula(e.target.value)}
            className="w-40"
          />

          <Input
            placeholder="Institución"
            value={institucion}
            onChange={e => setInstitucion(e.target.value)}
            className="w-48"
          />

          <Button onClick={() => load()}>Buscar</Button>

          <Button
            variant="outline"
            onClick={handleDescargarExcelAprobados}
            disabled={descargandoExcelAprobados}
            title="Aprobados pendientes de exportar. No usa fechas del filtro; sí cédula/institución si las llenaste."
          >
            {descargandoExcelAprobados ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : null}
            Descargar Excel Aprobados
          </Button>
        </CardContent>
      </Card>

      {kpis != null && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => handleKpiClick('')}
            title="Cola operativa: pendiente y en revisión (sin aprobados, importados ni rechazados). Ver rechazados con la tarjeta Rechazado o el filtro."
            className={
              'min-w-28 rounded-lg border-2 px-4 py-3 text-left transition-colors ' +
              (estado === ''
                ? 'border-primary bg-primary/10 font-semibold'
                : 'border-muted hover:bg-muted/50')
            }
          >
            <span className="block text-xs uppercase tracking-wide text-muted-foreground">
              Por gestionar
            </span>

            <span className="text-2xl font-bold">
              {kpis.pendiente + kpis.en_revision}
            </span>
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
              <table className="w-full min-w-[1100px] table-fixed text-sm">
                <colgroup>
                  <col style={{ width: '12%' }} />

                  <col style={{ width: '8%' }} />

                  <col style={{ width: '9%' }} />

                  <col style={{ width: '7%' }} />

                  <col style={{ width: '7%' }} />

                  <col style={{ width: '9%' }} />

                  <col style={{ width: '7%' }} />

                  <col style={{ width: '9%' }} />

                  <col style={{ width: '11%' }} />

                  <col style={{ width: '7%' }} />

                  <col style={{ width: '14%' }} />
                </colgroup>

                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-3 py-3 text-left font-semibold">
                      Nombre
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Cédula
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">Banco</th>

                    <th className="px-3 py-3 text-right font-semibold">
                      Monto
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Fecha pago
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Nº operación
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Fecha reporte
                    </th>

                    <th className="px-3 py-3 text-center font-semibold">
                      Comprobante
                    </th>

                    <th className="px-3 py-3 text-left font-semibold">
                      Observación
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

                      <td
                        className={
                          'min-w-0 px-3 py-3 align-top ' +
                          (/DUPLICADO/i.test(row.observacion || '')
                            ? 'bg-amber-500/15 font-medium text-amber-900 dark:text-amber-100'
                            : '')
                        }
                        title={
                          /DUPLICADO/i.test(row.observacion || '')
                            ? 'DUPLICADO: el número de operación / documento coincide con otro registro en pagos o con otro reporte en esta página.'
                            : row.numero_operacion
                        }
                      >
                        <span className="block truncate font-mono text-xs">
                          {row.numero_operacion}
                        </span>
                      </td>

                      <td className="whitespace-nowrap px-3 py-3 align-top">
                        {new Date(row.fecha_reporte).toLocaleDateString()}
                      </td>

                      <td className="px-2 py-3 align-middle">
                        {row.tiene_comprobante ? (
                          <button
                            type="button"
                            onClick={() => handleVerComprobante(row.id)}
                            disabled={viewingComprobanteId === row.id}
                            className="flex w-full min-w-0 flex-col items-center justify-center gap-1 rounded-lg border border-slate-200/80 bg-slate-50/80 px-2 py-2 text-center text-xs font-semibold text-[#1e3a5f] shadow-sm transition-colors hover:border-[#1e3a5f]/30 hover:bg-white focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/25 disabled:opacity-60 sm:flex-row sm:text-left"
                            title="Abrir imagen o PDF del comprobante"
                          >
                            {viewingComprobanteId === row.id ? (
                              <Loader2
                                className="h-4 w-4 shrink-0 animate-spin"
                                aria-hidden
                              />
                            ) : (
                              <Eye
                                className="h-4 w-4 shrink-0 opacity-80"
                                aria-hidden
                              />
                            )}
                            <span className="leading-tight underline decoration-[#1e3a5f]/35 underline-offset-2">
                              Ver comprobante
                            </span>
                          </button>
                        ) : (
                          <div
                            className="flex min-h-[52px] flex-col items-center justify-center rounded-lg border border-dashed border-muted-foreground/25 bg-muted/20 px-2 py-2 text-center"
                            title="Sin archivo adjunto en este reporte"
                          >
                            <span className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                              No disponible
                            </span>
                          </div>
                        )}
                      </td>

                      <td
                        className="min-w-0 px-3 py-3 align-top"
                        title={
                          /NO CLIENTES/i.test(row.observacion || '')
                            ? 'NO CLIENTES: la cédula del reporte (' +
                              row.cedula_display +
                              ') no figura en la tabla clientes. Se compara normalizada (sin guión, sin ceros a la izquierda). Verifique en Préstamos > Clientes o registre al cliente.'
                            : /DUPLICADO/i.test(row.observacion || '')
                              ? 'DUPLICADO: ya existe en la tabla pagos (documento/referencia normalizado) o hay otro reporte con el mismo número en esta página. No se debe aprobar dos veces el mismo comprobante.'
                              : /No pag Bs|solo Bs|Bolívares/i.test(
                                    row.observacion || ''
                                  )
                                ? 'No pag Bs.: la cédula no está en la lista autorizada para bolívares (cedulas_reportar_bs). Use USD o agregue la cédula en Configuración > Pagos.'
                                : (row.observacion ?? '')
                        }
                      >
                        {row.observacion ? (
                          <span
                            className={
                              'line-clamp-2 text-xs ' +
                              (/NO CLIENTES/i.test(row.observacion || '')
                                ? 'font-medium text-destructive'
                                : /DUPLICADO/i.test(row.observacion || '')
                                  ? 'font-semibold text-amber-900 dark:text-amber-100'
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
                          {/* Estado envío recibo: X = no enviado, visto = entregado, triángulo = en revisión */}

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
                            row.estado === 'en_revision' ||
                            row.estado === 'rechazado') && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 shrink-0"
                              title="Editar (monto, referencia, cédula, etc.)"
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
                          )}

                          {(row.estado === 'pendiente' ||
                            row.estado === 'en_revision') && (
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
                              <option value="">Seleccionar estado</option>

                              <option value="en_revision">En revisión</option>

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

      {/* Modal: interfaz rápida para escribir mensaje de rechazo y enviar correo al cliente */}

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
              placeholder="Indique el motivo del rechazo. Este texto se enviará por correo al cliente."
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
