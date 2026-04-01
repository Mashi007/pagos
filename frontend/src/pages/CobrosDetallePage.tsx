/**





 * Detalle de un pago reportado: datos, comprobante (enlace), Aprobar / Rechazar, historial.





 * Al aprobar se invalidan cuotas y préstamos para que la tabla de amortización se actualice al ir a Préstamos.





 */

import React, { useState, useEffect } from 'react'

import { useParams, useNavigate } from 'react-router-dom'

import { useQueryClient } from '@tanstack/react-query'

import { invalidateListasNotificacionesMora } from '../constants/queryKeys'

import {
  getPagoReportadoDetalle,
  aprobarPagoReportado,
  rechazarPagoReportado,
  enviarReciboManual,
  openComprobanteInNewTab,
  openReciboPdfInNewTab,
  type PagoReportadoDetalleResponse,
  type CambiarEstadoPagoResponse,
  etiquetaCanalReportado,
} from '../services/cobrosService'

import { Button } from '../components/ui/button'

import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

import { Badge } from '../components/ui/badge'

import toast from 'react-hot-toast'

import { Eye, FileText, Mail, Loader2, Edit } from 'lucide-react'

function toastAfterRechazoDetalle(data: CambiarEstadoPagoResponse) {
  const msg = data.mensaje ?? 'Pago rechazado.'
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

const ESTADO_BADGE: Record<string, string> = {
  pendiente: 'Pendiente 🟡',

  en_revision: 'En revisión 🟠',

  aprobado: 'Aprobado 🟢',

  rechazado: 'Rechazado 🔴',

  importado: 'Importado a Pagos 🟢',
}

const MENSAJE_RECHAZO_POR_DEFECTO = `Buenas tardes











La imagen no se aprecia detalles, agradezco enviar una imagen sin recortar a cobranza@rapicreditca.com











Gracias











Angélica Fuentes`

export default function CobrosDetallePage() {
  const { id } = useParams<{ id: string }>()

  const navigate = useNavigate()

  const queryClient = useQueryClient()

  const [detalle, setDetalle] = useState<PagoReportadoDetalleResponse | null>(
    null
  )

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
      const res = await aprobarPagoReportado(Number(id))

      toast.success(res.mensaje || 'Pago aprobado.')

      setAccion('idle')

      load()

      // El backend crea el pago en pagos, lo concilia y aplica a cuotas en cascada.
      // Invalidar para que prestamos, cuotas y notificaciones de mora se actualicen.
      queryClient.invalidateQueries({ queryKey: ['pagos'] })
      queryClient.invalidateQueries({ queryKey: ['cuotas-prestamo'] })
      queryClient.invalidateQueries({ queryKey: ['prestamos'] })
      void invalidateListasNotificacionesMora(queryClient)
    } catch (e: any) {
      const detail =
        e?.response?.data?.detail ||
        e?.response?.data?.message ||
        e?.message ||
        'Error al aprobar.'
      toast.error(detail)

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
      const data = await rechazarPagoReportado(Number(id), motivoRechazo.trim())

      toastAfterRechazoDetalle(data)

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
    <div className="max-w-4xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={() => navigate('/cobros/pagos-reportados')}
        >
          ← Volver
        </Button>

        <Badge variant="outline">
          {ESTADO_BADGE[detalle.estado] ?? detalle.estado}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>
            Detalle del reporte{' '}
            {detalle.referencia_interna?.startsWith('#')
              ? detalle.referencia_interna
              : `#${detalle.referencia_interna}`}
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-2 text-sm">
          <p className="text-xs text-muted-foreground">
            <strong>Origen:</strong>{' '}
            {etiquetaCanalReportado(detalle.canal_ingreso)}
            <span className="ml-1">
              (Infopagos y formulario publico usan la misma cola y validadores.)
            </span>
          </p>

          <p>
            <strong>Nombre:</strong> {detalle.nombres} {detalle.apellidos}
          </p>

          <p>
            <strong>Cédula:</strong> {detalle.tipo_cedula}
            {detalle.numero_cedula}
          </p>

          <p>
            <strong>Fecha de pago:</strong> {detalle.fecha_pago}
          </p>

          <p>
            <strong>Institución:</strong> {detalle.institucion_financiera}
          </p>

          <p>
            <strong>Número de operación:</strong> {detalle.numero_operacion}
          </p>

          <p>
            <strong>Monto:</strong> {detalle.monto} {detalle.moneda}
            {detalle.moneda === 'BS' && detalle.equivalente_usd != null && (
              <span className="ml-2 text-emerald-700">
                {'≈ '}
                {detalle.equivalente_usd.toLocaleString('es-VE', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}{' '}
                USD
                {detalle.tasa_cambio_bs_usd != null && (
                  <span className="ml-1 text-xs text-muted-foreground">
                    (tasa:{' '}
                    {detalle.tasa_cambio_bs_usd.toLocaleString('es-VE')}{' '}
                    Bs/USD)
                  </span>
                )}
              </span>
            )}
            {detalle.moneda === 'BS' && detalle.equivalente_usd == null && (
              <span
                className="ml-2 text-xs font-semibold text-amber-600"
                title="No hay tasa registrada para la fecha de pago. Debe registrarla en Pagos antes de aprobar."
              >
                (sin tasa registrada para esta fecha — no se puede aprobar hasta registrar la tasa)
              </span>
            )}
          </p>

          {detalle.observacion && (
            <p>
              <strong>Observación:</strong> {detalle.observacion}
            </p>
          )}

          <p>
            <strong>Correo enviado a:</strong> {detalle.correo_enviado_a ?? '-'}
          </p>

          <div className="mt-2 flex flex-wrap gap-2">
            {detalle.tiene_comprobante && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => id && openComprobanteInNewTab(Number(id))}
              >
                <Eye className="mr-1 h-4 w-4" /> Ver comprobante
              </Button>
            )}

            {(detalle.estado === 'pendiente' ||
              detalle.estado === 'en_revision' ||
              detalle.estado === 'rechazado') && (
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  id && navigate(`/cobros/pagos-reportados/${id}/editar`)
                }
              >
                <Edit className="mr-1 h-4 w-4" /> Editar datos
              </Button>
            )}

            {detalle.tiene_recibo_pdf && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => id && openReciboPdfInNewTab(Number(id))}
                className="border-red-200 text-red-600 hover:bg-red-50 hover:text-red-800"
              >
                <FileText className="mr-1 h-4 w-4" /> Ver recibo PDF
              </Button>
            )}

            {detalle.correo_enviado_a && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleEnviarRecibo}
                disabled={sendingRecibo}
              >
                {sendingRecibo ? (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                ) : (
                  <Mail className="mr-1 h-4 w-4" />
                )}
                Enviar recibo por correo
              </Button>
            )}
          </div>

          {detalle.gemini_comentario && (
            <p>
              <strong>Gemini:</strong> {detalle.gemini_comentario}
            </p>
          )}
        </CardContent>
      </Card>

      {detalle.estado !== 'aprobado' &&
        detalle.estado !== 'rechazado' &&
        detalle.estado !== 'importado' && (
          <Card>
            <CardHeader>
              <CardTitle>
                {detalle.estado === 'en_revision'
                  ? 'Revisión manual'
                  : 'Acciones'}
              </CardTitle>

              {detalle.estado === 'en_revision' && (
                <p className="mt-1 text-sm text-muted-foreground">
                  No coincidió 100% con la revisión automática (Gemini). Use los
                  mismos botones: Aprobar (envía recibo) o Rechazar (se notifica
                  al cliente por correo electrónico).
                </p>
              )}

              <p className="text-sm text-muted-foreground">
                Al rechazar se envía un correo al cliente desde{' '}
                <strong>notificaciones@rapicreditca.com</strong> con el motivo
                de rechazo y el comprobante adjunto (misma pantalla).
              </p>
            </CardHeader>

            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Button onClick={handleAprobar} disabled={accion !== 'idle'}>
                  {accion === 'aprobar' ? 'Procesando...' : 'Aprobar'}
                </Button>

                <Button
                  variant="destructive"
                  onClick={() => {
                    setMotivoRechazo(MENSAJE_RECHAZO_POR_DEFECTO)

                    setAccion('rechazar')
                  }}
                  disabled={accion !== 'idle'}
                >
                  Rechazar
                </Button>
              </div>

              {accion === 'rechazar' && (
                <div className="space-y-2">
                  <label className="block text-sm font-medium">
                    Motivo de rechazo (obligatorio)
                  </label>

                  <textarea
                    className="min-h-[80px] w-full rounded-md border px-3 py-2"
                    value={motivoRechazo}
                    onChange={e => setMotivoRechazo(e.target.value)}
                    placeholder="Indique el motivo..."
                  />

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setAccion('idle')}
                    >
                      Cancelar
                    </Button>

                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={handleRechazar}
                      disabled={!motivoRechazo.trim()}
                    >
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
                  {h.created_at &&
                    ` (${new Date(h.created_at).toLocaleString()})`}
                  {h.motivo && (
                    <p className="mt-1 text-gray-600">Motivo: {h.motivo}</p>
                  )}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
