import { useCallback, useEffect, useState } from 'react'

import { Link } from 'react-router-dom'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  Clock,
  Mail,
  RefreshCw,
  Save,
  Settings,
  TestTube,
  X,
} from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

import {
  emailCuentasApi,
  type EmailCuentasResponse,
} from '../../services/emailCuentasApi'
import { emailConfigService } from '../../services/notificacionService'
import { NOTIFICACIONES_QUERY_KEYS } from '../../queries/notificaciones'
import { toast } from 'sonner'
import { getErrorMessage } from '../../types/errors'

export const RECIBOS_CONFIG_EMAIL_CUENTAS_QUERY_KEY = [
  'notificaciones',
  'recibos',
  'configEmailCuentas',
] as const

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

type Props = {
  /** Incrementar desde la página (botón Cancelar) para limpiar estado local de operaciones. */
  emergencyResetSeq?: number
}

function SwitchPill({
  checked,
  disabled,
  onToggle,
  onClass,
  offClass,
}: {
  checked: boolean
  disabled?: boolean
  onToggle: () => void
  onClass: string
  offClass: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => {
        if (disabled) return
        onToggle()
      }}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 disabled:opacity-50 ${
        checked ? onClass : offClass
      }`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow ${
          checked ? 'translate-x-5' : 'translate-x-1'
        }`}
      />
    </button>
  )
}

export function ConfiguracionRecibos({ emergencyResetSeq = 0 }: Props) {
  const qc = useQueryClient()
  const { data, isFetching, refetch, isError, error, isPending } = useQuery({
    queryKey: RECIBOS_CONFIG_EMAIL_CUENTAS_QUERY_KEY,
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

  useEffect(() => {
    if (emergencyResetSeq <= 0) return
    setGuardando(false)
    setProbando(false)
  }, [emergencyResetSeq])

  const puedeCancelarEmergencia = guardando || probando || isFetching

  const cancelarEmergenciaConfig = () => {
    setGuardando(false)
    setProbando(false)
    toast.info('Operación en pantalla restablecida. Si un envío sigue en el servidor, espere unos segundos.')
  }

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
      toast.success('Configuración guardada')
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

  const enModoPruebasRecibos = modoPruebasRecibos

  if (isPending && !data) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center text-gray-500">
          <Clock className="mx-auto mb-2 h-8 w-8 animate-pulse text-blue-500" aria-hidden />

          <p>Cargando configuración...</p>
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <Card className="border-red-200 bg-red-50/40">
          <CardContent className="pt-6 text-sm text-red-800">
            No se pudo cargar la configuración de email: {getErrorMessage(error)}
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-red-200 bg-red-50/90 px-3 py-2">
        <p className="max-w-xl text-sm text-red-900">
          <strong>Emergencia:</strong> cancela guardado o prueba en curso o desbloquea si el formulario
          quedó colgado (revise en red si el PUT siguió).
        </p>

        <Button
          type="button"
          variant="outline"
          size="sm"
          className="shrink-0 border-red-400 text-red-800 hover:bg-red-100"
          disabled={!puedeCancelarEmergencia}
          onClick={cancelarEmergenciaConfig}
          title="Restablece estado local de Guardar / Enviar prueba y deja de mostrar carga en esta pantalla."
        >
          <X className="mr-2 h-4 w-4" aria-hidden />
          Cancelar
        </Button>
      </div>

      <Card className="border-slate-200 bg-slate-50/40">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-xl">
            <Settings className="h-5 w-5 text-blue-600" aria-hidden />
            Configuración Recibos
          </CardTitle>

          <CardDescription>
            Ajustes del servicio <strong>recibos</strong> en la misma persistencia que{' '}
            <Link
              to="/configuracion?tab=email"
              className="font-medium text-blue-600 underline underline-offset-2"
            >
              Configuración → Email (4 cuentas)
            </Link>
            . El modo prueba y los envíos de Recibos no toman el JSON de Notificaciones → Envíos; solo sus
            propias claves y el correo maestro global.
          </CardDescription>
        </CardHeader>
      </Card>

      <Card
        className={
          enModoPruebasRecibos
            ? 'border-amber-300 bg-amber-50/50'
            : emailActivoRecibos
              ? 'border-emerald-200 bg-emerald-50/30'
              : 'border-slate-200 bg-slate-50/40'
        }
      >
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            {enModoPruebasRecibos ? (
              <>
                <TestTube className="h-4 w-4 text-amber-600" aria-hidden />
                Modo prueba (solo Recibos)
              </>
            ) : emailActivoRecibos ? (
              <>
                <Mail className="h-4 w-4 text-emerald-600" aria-hidden />
                Envío activo
              </>
            ) : (
              <>
                <Settings className="h-4 w-4 text-slate-600" aria-hidden />
                Envío inactivo
              </>
            )}
          </CardTitle>

          <CardDescription>
            {enModoPruebasRecibos
              ? 'Modo prueba de Recibos solo usa el interruptor «modo pruebas recibos» y los correos definidos en Configuración → Email; no lee Notificaciones → Envíos.'
              : emailActivoRecibos
                ? 'Los envíos de Recibos dependen de su propio interruptor y del correo maestro global; no usan plantillas ni modo prueba del módulo Notificaciones.'
                : 'Con envío inactivo para Recibos, el job y la ejecución manual no envían correos de este servicio (independiente de otros servicios).'}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Recibos: envío</span>

            <SwitchPill
              checked={emailActivoRecibos}
              disabled={!data}
              onToggle={() => setEmailActivoRecibos(p => !p)}
              onClass="bg-emerald-600"
              offClass="bg-gray-300"
            />

            <span className="text-sm text-gray-600">
              {emailActivoRecibos ? 'Activado' : 'Desactivado'}
            </span>
          </div>

          <div className="rounded-lg border border-amber-200 bg-amber-50/80 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-gray-800">Modo prueba (Recibos)</span>

              <SwitchPill
                checked={modoPruebasRecibos}
                disabled={!data}
                onToggle={() => setModoPruebasRecibos(p => !p)}
                onClass="bg-amber-500"
                offClass="bg-gray-300"
              />

              <span className="text-sm text-gray-600">
                {modoPruebasRecibos ? 'Activado' : 'Desactivado'}
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-2">
            <label
              htmlFor="rec-cuenta-sel"
              className="w-40 shrink-0 whitespace-nowrap text-sm font-medium text-gray-700"
            >
              Cuenta SMTP (1–4)
            </label>

            <Select
              value={String(cuentaRecibos)}
              onValueChange={v => setCuentaRecibos(Number(v))}
              disabled={!data}
            >
              <SelectTrigger
                id="rec-cuenta-sel"
                className="h-9 max-w-xs border-gray-200 bg-white"
              >
                <SelectValue placeholder="Cuenta" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">Cuenta 1 (Cobros)</SelectItem>
                <SelectItem value="2">Cuenta 2 (Estado de cuenta)</SelectItem>
                <SelectItem value="3">Cuenta 3 (Notificaciones)</SelectItem>
                <SelectItem value="4">Cuenta 4 (Notificaciones)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-wrap gap-2 border-t border-gray-200/80 pt-4">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void refetch()}
              disabled={isFetching}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} aria-hidden />
              Recargar
            </Button>

            <Button
              type="button"
              size="sm"
              className="bg-blue-600 text-white hover:bg-blue-700"
              onClick={() => void guardar()}
              disabled={guardando || !data}
            >
              <Save className="mr-2 h-4 w-4" aria-hidden />
              {guardando ? 'Guardando…' : 'Guardar'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-slate-200 bg-white">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Mail className="h-4 w-4 text-blue-600" aria-hidden />
            Probar SMTP (servicio recibos)
          </CardTitle>

          <CardDescription>
            Misma acción que en Configuración global → Probar, con servicio{' '}
            <code className="rounded bg-gray-100 px-1 text-xs">recibos</code>.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-3">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:gap-3">
            <div className="flex max-w-md flex-1 flex-col gap-1">
              <label
                htmlFor="rec-mail-prueba"
                className="text-xs font-medium text-gray-600"
              >
                Correo destino
              </label>

              <Input
                id="rec-mail-prueba"
                type="email"
                placeholder="ejemplo@correo.com"
                value={emailPrueba}
                onChange={e => setEmailPrueba(e.target.value)}
                className="h-9 max-w-md bg-white"
                maxLength={120}
              />
            </div>

            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={probando}
              onClick={() => void probarCorreo()}
            >
              {probando ? 'Enviando…' : 'Enviar prueba'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
