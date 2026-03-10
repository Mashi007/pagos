/**
 * Detalle de un pago reportado: datos, comprobante (enlace), Aprobar / Rechazar, historial.
 */
import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  getPagoReportadoDetalle,
  aprobarPagoReportado,
  rechazarPagoReportado,
  enviarReciboManual,
  openComprobanteInNewTab,
  openReciboPdfInNewTab,
  type PagoReportadoDetalleResponse,
} from '../services/cobrosService'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import toast from 'react-hot-toast'
import { FileImage, FileText, Mail, Loader2 } from 'lucide-react'

const ESTADO_BADGE: Record<string, string> = {
  pendiente: 'Pendiente 🟡',
  en_revision: 'En revisión 🟠',
  aprobado: 'Aprobado 🟢',
  rechazado: 'Rechazado 🔴',
}

export default function CobrosDetallePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [detalle, setDetalle] = useState<PagoReportadoDetalleResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [accion, setAccion] = useState<'idle' | 'aprobar' | 'rechazar'>('idle')
  const [motivoRechazo, setMotivoRechazo] = useState('')
  const [sendingRecibo, setSendingRecibo] = useState(false)

  const load = async () => {
    if (!id) return
    setLoading(true)
    try {
      const res = await getPagoReportadoDetalle(Number(id))
      setDetalle(res)
    } catch (e: any) {
      toast.error(e?.message || 'Error al cargar.')
      navigate('/cobros/pagos-reportados')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [id])

  const handleAprobar = async () => {
    if (!id) return
    setAccion('aprobar')
    try {
      await aprobarPagoReportado(Number(id))
      toast.success('Pago aprobado y recibo enviado por correo.')
      setAccion('idle')
      load()
    } catch (e: any) {
      toast.error(e?.message || 'Error al aprobar.')
      setAccion('idle')
    }
  }

  const handleEnviarRecibo = async () => {
    if (!id) return
    setSendingRecibo(true)
    try {
      await enviarReciboManual(Number(id))
      toast.success('Recibo enviado por correo.')
      load()
    } catch (e: any) {
      toast.error(e?.message || 'Error al enviar.')
    } finally {
      setSendingRecibo(false)
    }
  }

  const handleRechazar = async () => {
    if (!id || !motivoRechazo.trim()) {
      toast.error('El motivo de rechazo es obligatorio.')
      return
    }
    setAccion('rechazar')
    try {
      await rechazarPagoReportado(Number(id), motivoRechazo.trim())
      toast.success('Pago rechazado y cliente notificado.')
      setAccion('idle')
      setMotivoRechazo('')
      load()
    } catch (e: any) {
      toast.error(e?.message || 'Error al rechazar.')
      setAccion('idle')
    }
  }

  if (loading || !detalle) {
    return <div className="p-6">Cargando...</div>
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => navigate('/cobros/pagos-reportados')}>
          ← Volver
        </Button>
        <Badge variant="outline">{ESTADO_BADGE[detalle.estado] ?? detalle.estado}</Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Detalle del reporte #{detalle.referencia_interna}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p><strong>Nombre:</strong> {detalle.nombres} {detalle.apellidos}</p>
          <p><strong>Cédula:</strong> {detalle.tipo_cedula}-{detalle.numero_cedula}</p>
          <p><strong>Fecha de pago:</strong> {detalle.fecha_pago}</p>
          <p><strong>Institución:</strong> {detalle.institucion_financiera}</p>
          <p><strong>Número de operación:</strong> {detalle.numero_operacion}</p>
          <p><strong>Monto:</strong> {detalle.monto} {detalle.moneda}</p>
          {detalle.observacion && <p><strong>Observación:</strong> {detalle.observacion}</p>}
          <p><strong>Correo enviado a:</strong> {detalle.correo_enviado_a ?? '—'}</p>
          <div className="flex flex-wrap gap-2 mt-2">
            {detalle.tiene_comprobante && (
              <Button variant="outline" size="sm" onClick={() => id && openComprobanteInNewTab(Number(id))}>
                <FileImage className="h-4 w-4 mr-1" /> Ver comprobante
              </Button>
            )}
            {detalle.tiene_recibo_pdf && (
              <Button variant="outline" size="sm" onClick={() => id && openReciboPdfInNewTab(Number(id))}>
                <FileText className="h-4 w-4 mr-1" /> Ver recibo PDF
              </Button>
            )}
            {detalle.correo_enviado_a && (
              <Button variant="outline" size="sm" onClick={handleEnviarRecibo} disabled={sendingRecibo}>
                {sendingRecibo ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Mail className="h-4 w-4 mr-1" />}
                Enviar recibo por correo
              </Button>
            )}
          </div>
          {detalle.gemini_comentario && (
            <p><strong>Gemini:</strong> {detalle.gemini_comentario}</p>
          )}
        </CardContent>
      </Card>

      {detalle.estado !== 'aprobado' && detalle.estado !== 'rechazado' && (
        <Card>
          <CardHeader>
            <CardTitle>
              {detalle.estado === 'en_revision' ? 'Revisión manual' : 'Acciones'}
            </CardTitle>
            {detalle.estado === 'en_revision' && (
              <p className="text-sm text-muted-foreground mt-1">
                No coincidió 100% con la revisión automática (Gemini). Use los mismos botones: Aprobar (envía recibo) o Rechazar (se notifica al cliente con WhatsApp 424-4579934).
              </p>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Button
                onClick={handleAprobar}
                disabled={accion !== 'idle'}
              >
                {accion === 'aprobar' ? 'Procesando...' : 'Aprobar'}
              </Button>
              <Button
                variant="destructive"
                onClick={() => setAccion('rechazar')}
                disabled={accion !== 'idle'}
              >
                Rechazar
              </Button>
            </div>
            {accion === 'rechazar' && (
              <div className="space-y-2">
                <label className="block text-sm font-medium">Motivo de rechazo (obligatorio)</label>
                <textarea
                  className="w-full border rounded-md px-3 py-2 min-h-[80px]"
                  value={motivoRechazo}
                  onChange={(e) => setMotivoRechazo(e.target.value)}
                  placeholder="Indique el motivo..."
                />
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setAccion('idle')}>Cancelar</Button>
                  <Button size="sm" variant="destructive" onClick={handleRechazar} disabled={!motivoRechazo.trim()}>
                    Confirmar rechazo
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {detalle.historial?.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Historial de cambios</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {detalle.historial.map((h, i) => (
                <li key={i} className="border-b pb-2">
                  {h.estado_anterior} → {h.estado_nuevo}
                  {h.usuario_email && ` por ${h.usuario_email}`}
                  {h.created_at && ` (${new Date(h.created_at).toLocaleString()})`}
                  {h.motivo && <p className="text-gray-600 mt-1">Motivo: {h.motivo}</p>}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
