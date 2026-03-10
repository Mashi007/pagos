/**
 * Listado de pagos reportados (módulo Cobros). Filtros, tabla, acciones Ver detalle / Aprobar / Rechazar.
 */
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  listPagosReportados,
  enviarReciboManual,
  cambiarEstadoPago,
  type PagoReportadoItem,
  type ListPagosReportadosResponse,
} from '../services/cobrosService'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import toast from 'react-hot-toast'
import { Mail, Loader2 } from 'lucide-react'
import { PUBLIC_REPORTE_PAGO_PATH } from '../config/env'

const ESTADO_BADGE: Record<string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  pendiente: { label: 'Pendiente 🟡', variant: 'secondary' },
  en_revision: { label: 'En revisión (manual) 🟠', variant: 'outline' },
  aprobado: { label: 'Aprobado 🟢', variant: 'default' },
  rechazado: { label: 'Rechazado 🔴', variant: 'destructive' },
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
  const [sendingId, setSendingId] = useState<number | null>(null)
  const [changingEstadoId, setChangingEstadoId] = useState<number | null>(null)

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

  const handleEnviarRecibo = async (id: number) => {
    setSendingId(id)
    try {
      await enviarReciboManual(id)
      toast.success('Recibo enviado por correo.')
      load()
    } catch (e: any) {
      toast.error(e?.message || 'Error al enviar.')
    } finally {
      setSendingId(null)
    }
  }

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
          Los pagos en <strong>En revisión (manual)</strong> no coincidieron 100% con Gemini; use Aprobar (envía recibo) o Rechazar (se notifica con WhatsApp 424-4579934).
        </p>
      </Card>

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <p>Cargando...</p>
          ) : !data?.items?.length ? (
            <p className="text-gray-500">No hay registros.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2">Nombre</th>
                    <th className="text-left py-2">Cédula</th>
                    <th className="text-left py-2">Banco</th>
                    <th className="text-right py-2">Monto</th>
                    <th className="text-left py-2">Fecha pago</th>
                    <th className="text-left py-2">Nº operación</th>
                    <th className="text-left py-2">Fecha reporte</th>
                    <th className="text-left py-2">Estado</th>
                    <th className="text-left py-2">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((row: PagoReportadoItem) => (
                    <tr key={row.id} className="border-b">
                      <td className="py-2">{row.nombres} {row.apellidos}</td>
                      <td className="py-2">{row.cedula_display}</td>
                      <td className="py-2">{row.institucion_financiera}</td>
                      <td className="py-2 text-right">{row.monto} {row.moneda}</td>
                      <td className="py-2">{row.fecha_pago}</td>
                      <td className="py-2">{row.numero_operacion}</td>
                      <td className="py-2">{new Date(row.fecha_reporte).toLocaleString()}</td>
                      <td className="py-2">
                        <Badge variant={ESTADO_BADGE[row.estado]?.variant ?? 'outline'}>
                          {ESTADO_BADGE[row.estado]?.label ?? row.estado}
                        </Badge>
                      </td>
                      <td className="py-2">
                        <div className="flex flex-wrap gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => navigate(`/cobros/pagos-reportados/${row.id}`)}
                          >
                            Ver detalle
                          </Button>
                          <select
                            className="border rounded text-xs px-2 py-1"
                            value=""
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
                          <Button
                            variant="ghost"
                            size="sm"
                            title="Enviar recibo PDF por correo"
                            onClick={() => handleEnviarRecibo(row.id)}
                            disabled={sendingId === row.id}
                          >
                            {sendingId === row.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4" />}
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
