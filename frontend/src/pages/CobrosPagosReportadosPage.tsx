/**
 * Listado de pagos reportados (módulo Cobros). Filtros, tabla, acciones Ver detalle / Aprobar / Rechazar.
 */
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  listPagosReportados,
  cambiarEstadoPago,
  openComprobanteInNewTab,
  eliminarPagoReportado,
  type PagoReportadoItem,
  type ListPagosReportadosResponse,
} from '../services/cobrosService'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import toast from 'react-hot-toast'
import { Loader2, Eye, FileText, Settings, Clock, Search, CheckCircle, XCircle, Trash2, AlertCircle, AlertTriangle } from 'lucide-react'
import { PUBLIC_REPORTE_PAGO_PATH } from '../config/env'

const ESTADO_CONFIG: Record<string, { label: string; short: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; Icon: typeof Clock }> = {
  pendiente: { label: 'Pendiente', short: 'Pend.', variant: 'secondary', Icon: Clock },
  en_revision: { label: 'En revisión (manual)', short: 'Revisión', variant: 'outline', Icon: Search },
  aprobado: { label: 'Aprobado', short: 'Aprobado', variant: 'default', Icon: CheckCircle },
  rechazado: { label: 'Rechazado', short: 'Rechazado', variant: 'destructive', Icon: XCircle },
}

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
  const [viewingComprobanteId, setViewingComprobanteId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const res = await listPagosReportados({
        page,
        per_page: 20,
        estado: estado || undefined,
        fecha_desde: fechaDesde || undefined,
        fecha_hasta: fechaHasta || undefined,
        cedula: cedula.trim() || undefined,
        institucion: institucion.trim() || undefined,
      })
      setData(res)
    } catch (e: any) {
      toast.error(e?.message || 'Error al cargar.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [page])

  const handleCambiarEstado = async (id: number, estado: string, motivo?: string) => {
    setChangingEstadoId(id)
    try {
      await cambiarEstadoPago(id, estado, motivo)
      toast.success('Estado actualizado.')
      load()
    } catch (e: any) {
      toast.error(e?.message || 'Error al actualizar.')
    } finally {
      setChangingEstadoId(null)
    }
  }

  const handleEliminar = async (id: number, ref: string) => {
    if (!window.confirm(`¿Eliminar el pago reportado ${ref}? Esta acción no se puede deshacer.`)) return
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

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Pagos Reportados</h1>
        <a
          href={`${typeof window !== 'undefined' ? window.location.origin : ''}${(import.meta.env.BASE_URL || '/').replace(/\/$/, '')}/${PUBLIC_REPORTE_PAGO_PATH}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-blue-600 hover:underline"
        >
          Link formulario público →
        </a>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filtros</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-4">
          <select
            className="border rounded-md px-3 py-2"
            value={estado}
            onChange={(e) => setEstado(e.target.value)}
          >
            <option value="">Todos los estados</option>
            <option value="pendiente">Pendiente</option>
            <option value="en_revision">En revisión</option>
            <option value="aprobado">Aprobado</option>
            <option value="rechazado">Rechazado</option>
          </select>
          <Input
            type="date"
            placeholder="Fecha desde"
            value={fechaDesde}
            onChange={(e) => setFechaDesde(e.target.value)}
            className="w-40"
          />
          <Input
            type="date"
            placeholder="Fecha hasta"
            value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)}
            className="w-40"
          />
          <Input
            placeholder="Cédula"
            value={cedula}
            onChange={(e) => setCedula(e.target.value)}
            className="w-40"
          />
          <Input
            placeholder="Institución"
            value={institucion}
            onChange={(e) => setInstitucion(e.target.value)}
            className="w-48"
          />
          <Button onClick={load}>Buscar</Button>
        </CardContent>
        <p className="text-sm text-muted-foreground px-6 pb-4">
          Los pagos en <strong>En revisión (manual)</strong> no coincidieron 100% con Gemini; use Aprobar (envía recibo) o Rechazar (se notifica al cliente por correo electrónico).
        </p>
      </Card>

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p>Cargando...</p>
          ) : !data?.items?.length ? (
            <p className="text-gray-500">No hay registros.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[1000px] text-sm table-fixed">
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
                    <th className="text-left py-3 px-3 font-semibold">Nombre</th>
                    <th className="text-left py-3 px-3 font-semibold">Cédula</th>
                    <th className="text-left py-3 px-3 font-semibold">Banco</th>
                    <th className="text-right py-3 px-3 font-semibold">Monto</th>
                    <th className="text-left py-3 px-3 font-semibold">Fecha pago</th>
                    <th className="text-left py-3 px-3 font-semibold">Nº operación</th>
                    <th className="text-left py-3 px-3 font-semibold">Fecha reporte</th>
                    <th className="text-left py-3 px-3 font-semibold">Observación</th>
                    <th className="text-left py-3 px-3 font-semibold">Estado</th>
                    <th className="text-left py-3 px-3 font-semibold">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row: PagoReportadoItem) => (
                    <tr key={row.id} className="border-b hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-3 align-top min-w-0">
                        <span className="block truncate" title={`${row.nombres} ${row.apellidos}`}>{row.nombres} {row.apellidos}</span>
                      </td>
                      <td className={`py-3 px-3 align-top whitespace-nowrap ${/c[eé]dula/i.test(row.observacion || '') ? 'bg-destructive/10 text-destructive font-medium' : ''}`} title={/c[eé]dula/i.test(row.observacion || '') ? 'Observación: ' + (row.observacion || '') : undefined}>
                        {/c[eé]dula/i.test(row.observacion || '') && <AlertCircle className="inline-block h-4 w-4 mr-1 align-middle" aria-hidden />}
                        {row.cedula_display}
                      </td>
                      <td className="py-3 px-3 align-top min-w-0">
                        <span className="block truncate" title={row.institucion_financiera}>{row.institucion_financiera}</span>
                      </td>
                      <td className="py-3 px-3 align-top text-right whitespace-nowrap">{row.monto} {row.moneda}</td>
                      <td className="py-3 px-3 align-top whitespace-nowrap">{row.fecha_pago}</td>
                      <td className="py-3 px-3 align-top min-w-0">
                        <span className="block truncate font-mono text-xs" title={row.numero_operacion}>{row.numero_operacion}</span>
                      </td>
                      <td className="py-3 px-3 align-top whitespace-nowrap">{new Date(row.fecha_reporte).toLocaleDateString()}</td>
                      <td className="py-3 px-3 align-top min-w-0" title={row.observacion ?? ''}>
                        {row.observacion ? (
                          <span className={`text-xs line-clamp-2 ${/c[eé]dula/i.test(row.observacion || '') ? 'text-destructive font-medium' : 'text-amber-700'}`}>{row.observacion}</span>
                        ) : '—'}
                      </td>
                      <td className="py-3 px-3 align-top whitespace-nowrap">
                        {(() => {
                          const cfg = ESTADO_CONFIG[row.estado] ?? { label: row.estado, short: row.estado, variant: 'outline' as const, Icon: Clock }
                          const Icon = cfg.Icon
                          return (
                            <Badge variant={cfg.variant} className="inline-flex items-center gap-1 font-normal" title={cfg.label}>
                              <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />
                              <span>{cfg.short}</span>
                            </Badge>
                          )
                        })()}
                      </td>
                      <td className="py-3 px-3 align-top">
                        <div className="flex flex-wrap gap-1 items-center justify-start">
                          {/* Estado envío recibo: X = no enviado, visto = entregado, triángulo = en revisión */}
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center text-muted-foreground" title={
                            row.estado === 'aprobado'
                              ? (row.tiene_recibo_pdf && row.correo_enviado_a ? 'Recibo enviado por correo' : 'No se envió recibo por correo')
                              : 'En revisión'
                          }>
                            {row.estado === 'aprobado' ? (
                              row.tiene_recibo_pdf && row.correo_enviado_a ? (
                                <CheckCircle className="h-4 w-4 text-green-600" aria-hidden />
                              ) : (
                                <XCircle className="h-4 w-4 text-muted-foreground" aria-hidden />
                              )
                            ) : (
                              <AlertTriangle className="h-4 w-4 text-blue-600" aria-hidden />
                            )}
                          </span>
                          <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" title="Ver comprobante (imagen)" onClick={() => handleVerComprobante(row.id)} disabled={viewingComprobanteId === row.id}>
                            {viewingComprobanteId === row.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />}
                          </Button>
                          <Button variant="ghost" size="icon" className="h-8 w-8" title="Ver detalle" onClick={() => navigate(`/cobros/pagos-reportados/${row.id}`)}>
                            <FileText className="h-4 w-4" />
                          </Button>
                          <div className="relative inline-block h-8 w-8">
                            <select
                              className="absolute inset-0 w-full h-full min-w-0 opacity-0 cursor-pointer disabled:cursor-not-allowed"
                              value=""
                              title="Cambiar estado"
                              onChange={(e) => {
                                const v = e.target.value
                                e.target.value = ''
                                if (!v) return
                                if (v === 'rechazado') {
                                  const motivo = window.prompt('Motivo de rechazo (obligatorio):')
                                  if (motivo?.trim()) handleCambiarEstado(row.id, v, motivo.trim())
                                  return
                                }
                                handleCambiarEstado(row.id, v)
                              }}
                              disabled={changingEstadoId === row.id}
                            >
                              <option value="">Cambiar estado</option>
                              <option value="pendiente">Pendiente</option>
                              <option value="en_revision">En revisión</option>
                              <option value="aprobado">Aprobar</option>
                              <option value="rechazado">Rechazar</option>
                            </select>
                            <span className="pointer-events-none flex h-8 w-8 items-center justify-center rounded-md border border-input bg-background" title="Cambiar estado">
                              {changingEstadoId === row.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Settings className="h-4 w-4" />}
                            </span>
                          </div>
                          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10" title="Eliminar" onClick={() => handleEliminar(row.id, row.referencia_interna)} disabled={deletingId === row.id}>
                            {deletingId === row.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
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
                <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page * data.per_page >= data.total}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
