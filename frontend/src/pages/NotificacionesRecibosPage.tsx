import { useEffect, useMemo, useState } from 'react'

import { useQuery } from '@tanstack/react-query'

import { Receipt, RefreshCw, Send } from 'lucide-react'

import { Button } from '../components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { notificacionService } from '../services/notificacionService'
import { toast } from 'sonner'
import { getErrorMessage } from '../types/errors'

type Slot = 'manana' | 'tarde' | 'noche'

const SLOT_LABEL: Record<Slot, string> = {
  manana: 'Mañana (01:00–11:00) → envío programado 11:05',
  tarde: 'Tarde (11:01–17:00) → envío programado 17:05',
  noche: 'Noche (17:01–23:45) → envío programado 23:55',
}

export default function NotificacionesRecibosPage() {
  useEffect(() => {
    const prev = document.title
    document.title = 'Recibos | Notificaciones | RapiCredit'
    return () => {
      document.title = prev
    }
  }, [])

  const [slot, setSlot] = useState<Slot>('manana')
  const [fechaCaracas, setFechaCaracas] = useState('')
  const [soloSimular, setSoloSimular] = useState(true)

  const listadoKey = useMemo(
    () => ['notificaciones', 'recibos', 'listado', slot, fechaCaracas || 'hoy'],
    [slot, fechaCaracas]
  )

  const { data, isFetching, refetch } = useQuery({
    queryKey: listadoKey,
    queryFn: () =>
      notificacionService.listarRecibosConciliacion({
        slot,
        fecha_caracas: fechaCaracas.trim() || undefined,
      }),
  })

  const totalPagosListado = data?.total_pagos ?? 0

  const ejecutar = async () => {
    if (!soloSimular && data !== undefined && totalPagosListado === 0) {
      toast.warning(
        'No hay pagos en la ventana para la fecha indicada: no se envía correo a nadie. Actualice el listado o cambie fecha/franja.'
      )
      return
    }
    try {
      const out = await notificacionService.ejecutarRecibosEnvio({
        slot,
        fecha_caracas: fechaCaracas.trim() || undefined,
        solo_simular: soloSimular,
      })
      if (out.sin_casos_en_ventana === true) {
        toast('Sin casos en la ventana: no se envió ningún correo.')
        void refetch()
        return
      }
      const resumen = `enviados=${String(out.enviados)} fallidos=${String(out.fallidos)} cedulas=${String(out.cedulas_distintas)}`
      toast.success(
        soloSimular
          ? `Simulación: ${resumen}`
          : `Ejecución: ${resumen}`
      )
      void refetch()
    } catch (e) {
      toast.error(getErrorMessage(e))
    }
  }

  return (
    <div className="space-y-6">
      <ModulePageHeader
        icon={Receipt}
        title="Recibos"
        description="Correo con PDF de estado de cuenta tras pagos conciliados (tabla pagos, vínculo cuotas). Zona America/Caracas."
      />

      <Card>
        <CardHeader>
          <CardTitle>Criterio en base de datos</CardTitle>
          <CardDescription>
            Se listan filas de <strong>pagos</strong> con <code>conciliado=true</code>,{' '}
            <code>estado=PAGADO</code> y <code>fecha_registro</code> en la ventana indicada. Deben
            estar aplicadas a cuotas (<code>cuotas.pago_id</code> o <code>cuota_pagos</code>). La
            cédula del pago determina el cliente; el PDF es el mismo flujo que el portal (
            <code>obtener_datos_estado_cuenta_cliente</code>).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-slate-700">
          <p>{SLOT_LABEL[slot]}</p>
          <p>
            Remitente From: variable de entorno <code>RECIBOS_FROM_EMAIL</code> (por defecto{' '}
            <code>notificacion@rapicreditca.com</code>). Cuenta SMTP según Configuración &gt; Email
            (asignación <code>recibos</code> → índice de cuenta, por defecto 3).
          </p>
          <p>
            Jobs automáticos: <code>ENABLE_AUTOMATIC_SCHEDULED_JOBS</code> y{' '}
            <code>ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS</code> en el servidor.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Vista previa y ejecución</CardTitle>
          <CardDescription>
            Elija franja y fecha de referencia (opcional). «Solo simular» no envía correos ni escribe
            idempotencia.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="slot-rec">Franja</Label>
              <select
                id="slot-rec"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={slot}
                onChange={e => setSlot(e.target.value as Slot)}
              >
                <option value="manana">Mañana (01:00–11:00)</option>
                <option value="tarde">Tarde (11:01–17:00)</option>
                <option value="noche">Noche (17:01–23:45)</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="fecha-rec">Fecha Caracas (YYYY-MM-DD)</Label>
              <Input
                id="fecha-rec"
                placeholder="Vacío = hoy"
                value={fechaCaracas}
                onChange={e => setFechaCaracas(e.target.value)}
              />
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={soloSimular}
              onChange={e => setSoloSimular(e.target.checked)}
            />
            Solo simular (sin SMTP ni tabla recibos_email_envio)
          </label>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" onClick={() => void refetch()} disabled={isFetching}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Actualizar listado
            </Button>
            <Button
              type="button"
              onClick={() => void ejecutar()}
              disabled={
                isFetching ||
                (!soloSimular && data !== undefined && totalPagosListado === 0)
              }
            >
              <Send className="mr-2 h-4 w-4" />
              {soloSimular ? 'Simular envío' : 'Ejecutar envío'}
            </Button>
          </div>
          {data && (
            <div className="rounded-md border bg-slate-50 p-3 text-sm">
              <p>
                <strong>Fecha:</strong> {data.fecha_dia} · <strong>Franja:</strong> {data.slot} ·{' '}
                <strong>Pagos:</strong> {data.total_pagos} · <strong>Cédulas distintas:</strong>{' '}
                {data.cedulas_distintas}
              </p>
              <div className="mt-2 max-h-64 overflow-auto font-mono text-xs">
                {(data.pagos || []).slice(0, 80).map(p => (
                  <div key={p.pago_id}>
                    #{p.pago_id} {p.cedula} · {p.fecha_registro} · {p.monto_pagado} USD
                  </div>
                ))}
                {(data.pagos || []).length > 80 ? <p>…</p> : null}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
