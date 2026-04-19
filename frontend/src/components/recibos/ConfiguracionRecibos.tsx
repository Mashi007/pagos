import { useCallback, useEffect, useState } from 'react'

import { Link } from 'react-router-dom'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import { Mail, RefreshCw, Save, Settings } from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'

import {
  emailCuentasApi,
  type EmailCuentasResponse,
} from '../../services/emailCuentasApi'
import { emailConfigService } from '../../services/notificacionService'
import { NOTIFICACIONES_QUERY_KEYS } from '../../queries/notificaciones'
import { toast } from 'sonner'
import { getErrorMessage } from '../../types/errors'

const QUERY_KEY = ['notificaciones', 'recibos', 'configEmailCuentas'] as const

function buildPutPayload(
  cur: EmailCuentasResponse,
  patch: {
    email_activo_recibos: string
    modo_pruebas_recibos: string
    recibos_cuenta: number
  }
) {
  const a = cur.asignacion ?? { cobros: 1, estado_cuenta: 2, notificaciones_tab: {} }
  return {
    cuentas: cur.cuentas,
    asignacion: {
      cobros: a.cobros ?? 1,
      estado_cuenta: a.estado_cuenta ?? 2,
      notificaciones_tab: { ...(a.notificaciones_tab ?? {}) },
      recibos: patch.recibos_cuenta,
    },
    modo_pruebas: cur.modo_pruebas,
    email_pruebas: cur.email_pruebas,
    emails_pruebas: cur.emails_pruebas,
    email_activo: cur.email_activo,
    email_activo_notificaciones: cur.email_activo_notificaciones,
    email_activo_informe_pagos: cur.email_activo_informe_pagos,
    email_activo_estado_cuenta: cur.email_activo_estado_cuenta,
    email_activo_finiquito: cur.email_activo_finiquito,
    email_activo_cobros: cur.email_activo_cobros,
    email_activo_campanas: cur.email_activo_campanas,
    email_activo_tickets: cur.email_activo_tickets,
    email_activo_recibos: patch.email_activo_recibos,
    modo_pruebas_notificaciones: cur.modo_pruebas_notificaciones,
    modo_pruebas_informe_pagos: cur.modo_pruebas_informe_pagos,
    modo_pruebas_estado_cuenta: cur.modo_pruebas_estado_cuenta,
    modo_pruebas_finiquito: cur.modo_pruebas_finiquito,
    modo_pruebas_cobros: cur.modo_pruebas_cobros,
    modo_pruebas_campanas: cur.modo_pruebas_campanas,
    modo_pruebas_tickets: cur.modo_pruebas_tickets,
    modo_pruebas_recibos: patch.modo_pruebas_recibos,
    tickets_notify_emails: cur.tickets_notify_emails,
  }
}

export function ConfiguracionRecibos() {
  const qc = useQueryClient()
  const { data, isFetching, refetch, isError, error } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => emailCuentasApi.get(),
  })

  const [emailActivoRecibos, setEmailActivoRecibos] = useState(true)
  const [modoPruebasRecibos, setModoPruebasRecibos] = useState(false)
  const [cuentaRecibos, setCuentaRecibos] = useState(3)
  const [guardando, setGuardando] = useState(false)
  const [emailPrueba, setEmailPrueba] = useState('')
  const [probando, setProbando] = useState(false)

  useEffect(() => {
    if (!data) return
    setEmailActivoRecibos((data.email_activo_recibos ?? 'true') === 'true')
    setModoPruebasRecibos((data.modo_pruebas_recibos ?? 'false') === 'true')
    setCuentaRecibos(
      typeof data.asignacion?.recibos === 'number' ? data.asignacion.recibos : 3
    )
  }, [data])

  const guardar = useCallback(async () => {
    if (!data) {
      toast.error('Cargue la configuración antes de guardar.')
      return
    }
    setGuardando(true)
    try {
      await emailCuentasApi.put(
        buildPutPayload(data, {
          email_activo_recibos: emailActivoRecibos ? 'true' : 'false',
          modo_pruebas_recibos: modoPruebasRecibos ? 'true' : 'false',
          recibos_cuenta: cuentaRecibos,
        })
      )
      toast.success('Configuración de Recibos guardada')
      await qc.invalidateQueries({ queryKey: NOTIFICACIONES_QUERY_KEYS.emailEstado })
      await refetch()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setGuardando(false)
    }
  }, [
    cuentaRecibos,
    data,
    emailActivoRecibos,
    modoPruebasRecibos,
    qc,
    refetch,
  ])

  const probarCorreo = async () => {
    const to = emailPrueba.trim()
    if (!to || !to.includes('@')) {
      toast.warning('Indique un correo de destino válido.')
      return
    }
    setProbando(true)
    try {
      await emailConfigService.probarConfiguracionEmail(
        to,
        'Prueba SMTP — Recibos (RapiCredit)',
        'Si recibe este mensaje, la cuenta asignada al servicio «recibos» envía correctamente.',
        undefined,
        { servicio: 'recibos', tipo_tab: 'recibos' }
      )
      toast.success('Correo de prueba enviado (servicio recibos).')
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setProbando(false)
    }
  }

  if (isError) {
    return (
      <Card>
        <CardContent className="pt-6 text-sm text-red-700">
          No se pudo cargar la configuración de email: {getErrorMessage(error)}
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Settings className="h-5 w-5" />
            Alcance del submódulo Recibos
          </CardTitle>
          <CardDescription>
            Misma persistencia que en{' '}
            <Link
              className="font-medium text-blue-600 underline"
              to="/configuracion?tab=email"
            >
              Configuración → Email (4 cuentas)
            </Link>
            : clave <code className="rounded bg-muted px-1 text-xs">email_config</code>. Aquí solo
            se ajustan interruptores y la cuenta SMTP del servicio <strong>recibos</strong>; credenciales
            y el resto de servicios se editan en la pantalla global.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-700">
          <p>
            Tras pagos <strong>conciliados</strong> y <code>fecha_registro</code> en franja Caracas, se
            envía el <strong>estado de cuenta</strong> (PDF del portal) a los correos del cliente. No
            usa plantillas de mora ni carta de cobranza.
          </p>
          <p>
            Programación: <strong>11:05</strong>, <strong>17:05</strong> y <strong>23:55</strong>{' '}
            (America/Caracas) si <code>ENABLE_AUTOMATIC_SCHEDULED_JOBS</code> y{' '}
            <code>ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS</code> están activos en el servidor.
          </p>
          <p>
            Remitente visible: variable <code>RECIBOS_FROM_EMAIL</code> en el backend (por defecto{' '}
            <code>notificacion@rapicreditca.com</code>).
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Envío por servicio «recibos»</CardTitle>
          <CardDescription>
            Si el correo maestro está apagado en Configuración global, no se envía ningún e-mail.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isFetching && !data ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : null}
          <div className="flex flex-col justify-between gap-2 rounded border p-3 sm:flex-row sm:items-center">
            <div>
              <p className="text-sm font-medium">Recibos: envío activo</p>
              <p className="text-xs text-muted-foreground">
                Desactivar evita SMTP y tabla de idempotencia (comportamiento actual del job).
              </p>
            </div>
            <label className="relative inline-flex cursor-pointer items-center">
              <input
                type="checkbox"
                className="peer sr-only"
                checked={emailActivoRecibos}
                onChange={e => setEmailActivoRecibos(e.target.checked)}
                disabled={!data}
              />
              <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-blue-600 peer-checked:after:translate-x-full peer-checked:after:border-white" />
              <span className="ml-2 text-sm">{emailActivoRecibos ? 'Activo' : 'Inactivo'}</span>
            </label>
          </div>

          <div className="flex flex-col justify-between gap-2 rounded border border-amber-100 bg-amber-50/40 p-3 sm:flex-row sm:items-center">
            <div>
              <p className="text-sm font-medium">Modo pruebas solo para Recibos</p>
              <p className="text-xs text-muted-foreground">
                Si está activo y hay correo(s) de prueba en la config global, los envíos de Recibos se
                redirigen (salvo envío manual con destinos respetados en otros módulos).
              </p>
            </div>
            <label className="relative inline-flex cursor-pointer items-center">
              <input
                type="checkbox"
                className="peer sr-only"
                checked={modoPruebasRecibos}
                onChange={e => setModoPruebasRecibos(e.target.checked)}
                disabled={!data}
              />
              <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-amber-600 peer-checked:after:translate-x-full peer-checked:after:border-white" />
              <span className="ml-2 text-sm">{modoPruebasRecibos ? 'Activo' : 'Inactivo'}</span>
            </label>
          </div>

          <div className="space-y-2">
            <Label htmlFor="rec-cuenta">Cuenta SMTP (1–4) para Recibos</Label>
            <select
              id="rec-cuenta"
              className="flex h-10 max-w-xs rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={cuentaRecibos}
              onChange={e => setCuentaRecibos(Number(e.target.value))}
              disabled={!data}
            >
              <option value={1}>Cuenta 1 (Cobros)</option>
              <option value={2}>Cuenta 2 (Estado de cuenta)</option>
              <option value={3}>Cuenta 3 (Notificaciones)</option>
              <option value={4}>Cuenta 4 (Notificaciones)</option>
            </select>
          </div>

          <div className="flex flex-wrap gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => void refetch()} disabled={isFetching}>
              <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
              Recargar
            </Button>
            <Button type="button" onClick={() => void guardar()} disabled={guardando || !data}>
              <Save className="mr-2 h-4 w-4" />
              {guardando ? 'Guardando…' : 'Guardar'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Mail className="h-5 w-5" />
            Probar SMTP (servicio recibos)
          </CardTitle>
          <CardDescription>
            Usa la misma ruta que Configuración → Email → Probar, con{' '}
            <code className="rounded bg-muted px-1 text-xs">servicio=recibos</code>.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="min-w-[220px] flex-1 space-y-2">
            <Label htmlFor="rec-mail-prueba">Correo destino</Label>
            <Input
              id="rec-mail-prueba"
              type="email"
              placeholder="destino@ejemplo.com"
              value={emailPrueba}
              onChange={e => setEmailPrueba(e.target.value)}
            />
          </div>
          <Button type="button" variant="secondary" disabled={probando} onClick={() => void probarCorreo()}>
            {probando ? 'Enviando…' : 'Enviar prueba'}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
