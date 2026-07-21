/**









 * Configuración de 4 cuentas de correo con asignación por servicio.









 * Cuenta 1 = Cobros, 2 = Estado de cuenta, 3 y 4 = Notificaciones (por pestaña).









 */

import { useState, useEffect } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { Mail, Save, AlertCircle, CheckCircle, Key } from 'lucide-react'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '../ui/card'

import { Button } from '../ui/button'

import { Input } from '../ui/input'

import { Label } from '../ui/label'

import { toast } from 'sonner'

import {
  emailCuentasApi,
  SERVICIO_POR_CUENTA,
  PANEL_SERVICIOS_EMAIL,
  ASIGNACION_NOTIF_GRUPOS,
  ASIGNACION_NOTIF_DEFAULTS,
  CUENTA_OPCIONES_ASIGNACION,
  type EmailCuentasResponse,
  type CuentaEmailItem,
  type AsignacionServicioKey,
} from '../../services/emailCuentasApi'

import { NOTIFICACIONES_QUERY_KEYS } from '../../queries/notificaciones'

const CUENTAS_COUNT = 4

const emptyCuenta = (): CuentaEmailItem => ({
  smtp_host: 'smtp.gmail.com',
  smtp_port: '587',
  smtp_user: '',
  smtp_password: '',
  from_email: '',
  from_name: 'RapiCredit',
  smtp_use_tls: 'true',
  imap_host: '',
  imap_port: '993',
  imap_user: '',
  imap_password: '',
  imap_use_ssl: 'true',
})

function mergeAsignacionTabs(
  tab: Record<string, number> | undefined
): Record<string, number> {
  return { ...ASIGNACION_NOTIF_DEFAULTS, ...(tab ?? {}) }
}

function SelectCuentaAsignacion({
  id,
  value,
  onChange,
  className = 'rounded border bg-background px-2 py-1 text-sm',
}: {
  id?: string
  value: number
  onChange: (v: number) => void
  className?: string
}) {
  return (
    <select
      id={id}
      className={className}
      value={value}
      onChange={e => onChange(Number(e.target.value))}
    >
      {CUENTA_OPCIONES_ASIGNACION.map(o => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  )
}

function CuentaClaveIndicador({
  guardada,
  pendiente,
  smtpUser,
}: {
  guardada?: boolean
  pendiente: boolean
  smtpUser?: string
}) {
  if (pendiente) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-900 dark:bg-blue-950 dark:text-blue-100">
        <Key className="h-3 w-3 shrink-0" aria-hidden />
        Clave nueva (pendiente de guardar)
      </span>
    )
  }
  if (guardada) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100">
        <CheckCircle className="h-3 w-3 shrink-0" aria-hidden />
        Clave SMTP guardada
      </span>
    )
  }
  if ((smtpUser ?? '').trim()) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-950 dark:bg-amber-950 dark:text-amber-100">
        <AlertCircle className="h-3 w-3 shrink-0" aria-hidden />
        Sin clave SMTP (requerida para enviar)
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
      Cuenta sin configurar
    </span>
  )
}

function cuentaTieneClavePendiente(cuenta: CuentaEmailItem | undefined): boolean {
  const pwd = cuenta?.smtp_password
  return Boolean(pwd && pwd !== '***' && pwd.trim().length > 0)
}

export function EmailCuentasConfig() {
  const queryClient = useQueryClient()

  const [data, setData] = useState<EmailCuentasResponse | null>(null)

  const [loading, setLoading] = useState(true)

  const [saving, setSaving] = useState(false)

  const [sendingTest, setSendingTest] = useState(false)

  const [testingSmtp, setTestingSmtp] = useState<Record<number, boolean>>({})

  const [smtpTestOk, setSmtpTestOk] = useState<Record<number, boolean>>({})

  const [asignacion, setAsignacion] = useState<Record<string, number>>({})

  useEffect(() => {
    load()
  }, [])

  const load = async () => {
    setLoading(true)

    try {
      const res = await emailCuentasApi.get()

      setData(res)

      const tab = res.asignacion?.notificaciones_tab ?? {}

      setAsignacion(mergeAsignacionTabs(tab))
    } catch (e) {
      console.error(e)

      toast.error('Error cargando configuración de cuentas')

      setData({
        version: 2,

        cuentas: Array.from({ length: CUENTAS_COUNT }, emptyCuenta),

        asignacion: {
          cobros: 1,
          estado_cuenta: 2,
          notificaciones_tab: {},
          recibos: 1,
        },
      })

      setAsignacion({})
    } finally {
      setLoading(false)
    }
  }

  const updateCuenta = (
    index: number,
    field: keyof CuentaEmailItem,
    value: string
  ) => {
    if (!data) return

    const next = [...data.cuentas]

    if (!next[index]) next[index] = emptyCuenta()

    next[index] = { ...next[index], [field]: value }

    if (field === 'smtp_user' && !next[index].from_email?.trim())
      next[index].from_email = value

    setData({ ...data, cuentas: next })
  }

  const setNotifTabCuenta = (tabId: string, cuenta: number) => {
    setAsignacion(prev => ({ ...prev, [tabId]: cuenta }))
    if (!data) return
    setData({
      ...data,
      asignacion: {
        cobros: data.asignacion?.cobros ?? 1,
        estado_cuenta: data.asignacion?.estado_cuenta ?? 2,
        recibos: data.asignacion?.recibos ?? 1,
        notificaciones_tab: {
          ...(data.asignacion?.notificaciones_tab ?? {}),
          [tabId]: cuenta,
        },
      },
    })
  }

  const setServicioCuenta = (key: AsignacionServicioKey, cuenta: number) => {
    if (!data) return
    setData({
      ...data,
      asignacion: {
        cobros: data.asignacion?.cobros ?? 1,
        estado_cuenta: data.asignacion?.estado_cuenta ?? 2,
        recibos: data.asignacion?.recibos ?? 1,
        notificaciones_tab: {
          ...(data.asignacion?.notificaciones_tab ?? {}),
        },
        [key]: cuenta,
      },
    })
  }

  const setServicioActivo = (
    key: keyof EmailCuentasResponse,
    value: string
  ) => {
    if (!data) return

    setData({ ...data, [key]: value })
  }

  const setModoPruebasServicio = (
    key: keyof EmailCuentasResponse,
    checked: boolean
  ) => {
    if (!data) return
    setData({ ...data, [key]: checked ? 'true' : 'false' })
  }

  const probarConexionCuenta = async (index: number) => {
    if (!data) return
    const c = data.cuentas[index] ?? emptyCuenta()
    setTestingSmtp(prev => ({ ...prev, [index]: true }))
    try {
      const res = await emailCuentasApi.probarSmtpCuenta({
        cuenta: index + 1,
        smtp_host: c.smtp_host,
        smtp_port: c.smtp_port,
        smtp_user: c.smtp_user,
        smtp_password:
          c.smtp_password && c.smtp_password !== '***'
            ? c.smtp_password
            : undefined,
        smtp_use_tls: c.smtp_use_tls,
      })
      setSmtpTestOk(prev => ({ ...prev, [index]: res.success }))
      if (res.success) {
        toast.success(`Cuenta ${index + 1}: ${res.mensaje}`)
      } else {
        toast.error(`Cuenta ${index + 1}: ${res.mensaje}`)
      }
    } catch (e: unknown) {
      setSmtpTestOk(prev => ({ ...prev, [index]: false }))
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (e as Error)?.message ??
        'Error al probar SMTP'
      toast.error(`Cuenta ${index + 1}: ${String(msg)}`)
    } finally {
      setTestingSmtp(prev => ({ ...prev, [index]: false }))
    }
  }

  const etiquetaCuenta = (n: number) =>
    CUENTA_OPCIONES_ASIGNACION.find(o => o.value === n)?.label ?? `Cuenta ${n}`

  const cuentaAsignadaServicio = (
    row: (typeof PANEL_SERVICIOS_EMAIL)[number]
  ): number | null => {
    if ('sinSelectorCuenta' in row && row.sinSelectorCuenta) return null
    if ('asignacionDesde' in row && row.asignacionDesde) {
      return data?.asignacion?.[row.asignacionDesde] ?? row.defaultCuenta ?? 2
    }
    if ('asignacionKey' in row && row.asignacionKey) {
      return data?.asignacion?.[row.asignacionKey] ?? row.defaultCuenta ?? 1
    }
    return null
  }

  const ToggleActivo = ({
    checked,
    onChange,
    id,
  }: {
    checked: boolean
    onChange: (v: boolean) => void
    id?: string
  }) => (
    <label className="relative inline-flex cursor-pointer items-center">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        className="peer sr-only"
      />
      <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-blue-600 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none dark:border-gray-600 dark:bg-gray-700" />
      <span className="ml-2 text-xs sm:text-sm">
        {checked ? 'Activo' : 'Inactivo'}
      </span>
    </label>
  )

  const handleSave = async () => {
    if (!data) return

    setSaving(true)

    try {
      const cuentas = data.cuentas.slice(0, CUENTAS_COUNT).map(c => {
        const {
          smtp_password_guardada: _sg,
          imap_password_guardada: _ig,
          ...rest
        } = c
        return rest
      })

      while (cuentas.length < CUENTAS_COUNT) cuentas.push(emptyCuenta())

      const payloadPut = {
        cuentas,
        asignacion: {
          cobros: data.asignacion?.cobros ?? 1,
          estado_cuenta: data.asignacion?.estado_cuenta ?? 2,
          notificaciones_tab: { ...asignacion },
          recibos: data.asignacion?.recibos ?? 1,
        },
        modo_pruebas: data.modo_pruebas,
        email_pruebas: data.email_pruebas,
        emails_pruebas: data.emails_pruebas,
        email_activo: data.email_activo,
        email_activo_notificaciones: data.email_activo_notificaciones,
        email_activo_informe_pagos: data.email_activo_informe_pagos,
        email_activo_estado_cuenta: data.email_activo_estado_cuenta,
        email_activo_finiquito: data.email_activo_finiquito,
        email_activo_cobros: data.email_activo_cobros,
        email_activo_campanas: data.email_activo_campanas,
        email_activo_tickets: data.email_activo_tickets,
        email_activo_recibos: data.email_activo_recibos,
        modo_pruebas_notificaciones: data.modo_pruebas_notificaciones,
        modo_pruebas_informe_pagos: data.modo_pruebas_informe_pagos,
        modo_pruebas_estado_cuenta: data.modo_pruebas_estado_cuenta,
        modo_pruebas_finiquito: data.modo_pruebas_finiquito,
        modo_pruebas_cobros: data.modo_pruebas_cobros,
        modo_pruebas_campanas: data.modo_pruebas_campanas,
        modo_pruebas_tickets: data.modo_pruebas_tickets,
        modo_pruebas_recibos: data.modo_pruebas_recibos,
        tickets_notify_emails: data.tickets_notify_emails,
        recibos_bcc_emails: Array.isArray(data.recibos_bcc_emails)
          ? data.recibos_bcc_emails
          : [],
      }

      const resPut = await emailCuentasApi.put(payloadPut)
      const verifs = resPut.smtp_verificaciones

      if (resPut.asignacion?.notificaciones_tab) {
        const savedAsig = resPut.asignacion
        setAsignacion(mergeAsignacionTabs(savedAsig.notificaciones_tab))
        setData(prev =>
          prev
            ? {
                ...prev,
                asignacion: {
                  cobros: savedAsig.cobros ?? prev.asignacion?.cobros ?? 1,
                  estado_cuenta:
                    savedAsig.estado_cuenta ?? prev.asignacion?.estado_cuenta ?? 2,
                  recibos: savedAsig.recibos ?? prev.asignacion?.recibos ?? 1,
                  notificaciones_tab: savedAsig.notificaciones_tab,
                },
              }
            : prev
        )
      }

      if (verifs?.length) {
        const okN = verifs.filter(v => v.ok).map(v => v.cuenta)
        const okMap: Record<number, boolean> = {}
        verifs.forEach(v => {
          okMap[v.cuenta - 1] = v.ok
        })
        setSmtpTestOk(prev => ({ ...prev, ...okMap }))
        toast.success(
          `Clave verificada por SMTP en cuenta(s): ${okN.join(', ')}`
        )
      } else {
        toast.success('Configuración de 4 cuentas guardada')
      }

      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.emailEstado,
      })

      await load()
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (e as Error)?.message ??
        'Error al guardar'

      toast.error(String(msg))
    } finally {
      setSaving(false)
    }
  }

  const handleEnviarPrueba = async () => {
    setSendingTest(true)

    try {
      const res = await emailCuentasApi.enviarPrueba()

      if (res.success) {
        const cuentasOk = [
          ...new Set((res.enviados || []).map(e => e.cuenta)),
        ].sort((a, b) => a - b)

        const lineasDetalle = (res.enviados || [])
          .map(e => `Cuenta ${e.cuenta} -> ${e.email}`)
          .join('\n')

        toast.success(
          `SMTP acepto el envio (${res.enviados?.length ?? 0} aceptado(s) por el servidor)`,
          {
            description: [
              cuentasOk.length
                ? `Cuentas probadas: ${cuentasOk.join(', ')}.`
                : '',
              res.mensaje,
              res.nota_smtp,
              lineasDetalle ? `Detalle por cuenta:\n${lineasDetalle}` : '',
            ]
              .filter(Boolean)
              .join('\n'),
            duration: 14000,
          }
        )
      } else {
        const errMsg = res.errores?.length
          ? res.errores.map(e => `Cuenta ${e.cuenta}: ${e.mensaje}`).join('; ')
          : res.mensaje

        toast.warning(errMsg || res.mensaje)
      }
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ??
        (e as Error)?.message ??
        'Error al enviar prueba'

      toast.error(String(msg))
    } finally {
      setSendingTest(false)
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          Cargando configuración de cuentas...
        </CardContent>
      </Card>
    )
  }

  const cuentas =
    data?.cuentas ?? Array.from({ length: CUENTAS_COUNT }, emptyCuenta)

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <CheckCircle className="h-4 w-4" />
            Panel de servicios (activo, cuenta SMTP, modo pruebas)
          </CardTitle>

          <CardDescription>
            Un solo lugar para encender cada servicio, elegir qué cuenta SMTP usa
            y si redirige al correo de pruebas. Los casos de Notificaciones
            eligen cuenta en la tabla inferior.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="flex flex-col justify-between gap-2 rounded border border-primary/25 bg-muted/30 p-3 sm:flex-row sm:items-center">
            <div>
              <p className="text-sm font-medium">Correo electrónico (maestro)</p>
              <p className="text-xs text-muted-foreground">
                Si está inactivo, ningún servicio envía correo.
              </p>
            </div>
            <ToggleActivo
              checked={(data?.email_activo ?? 'true') === 'true'}
              onChange={v =>
                setServicioActivo('email_activo', v ? 'true' : 'false')
              }
            />
          </div>

          <div className="overflow-x-auto rounded border">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="p-3 font-medium">Servicio</th>
                  <th className="p-3 font-medium">Activo</th>
                  <th className="p-3 font-medium">Cuenta SMTP</th>
                  <th className="p-3 font-medium">→ Pruebas</th>
                </tr>
              </thead>
              <tbody>
                {PANEL_SERVICIOS_EMAIL.map(row => {
                  const cuentaN = cuentaAsignadaServicio(row)
                  return (
                    <tr key={row.id} className="border-b last:border-0">
                      <td className="p-3 align-middle font-medium">{row.label}</td>
                      <td className="p-3 align-middle">
                        <ToggleActivo
                          checked={(data?.[row.activoKey] ?? 'true') === 'true'}
                          onChange={v =>
                            setServicioActivo(row.activoKey, v ? 'true' : 'false')
                          }
                        />
                      </td>
                      <td className="p-3 align-middle">
                        {'sinSelectorCuenta' in row && row.sinSelectorCuenta ? (
                          <span className="text-xs text-muted-foreground">
                            Por caso (tabla abajo)
                          </span>
                        ) : 'asignacionDesde' in row && row.asignacionDesde ? (
                          <span className="text-xs text-muted-foreground">
                            Igual que Estado de cuenta (
                            {etiquetaCuenta(cuentaN ?? row.defaultCuenta ?? 2)})
                          </span>
                        ) : 'asignacionKey' in row ? (
                          <SelectCuentaAsignacion
                            id={`panel-cuenta-${row.id}`}
                            value={
                              data?.asignacion?.[row.asignacionKey] ??
                              row.defaultCuenta ??
                              1
                            }
                            onChange={v =>
                              setServicioCuenta(row.asignacionKey, v)
                            }
                          />
                        ) : null}
                      </td>
                      <td className="p-3 align-middle">
                        <label className="inline-flex cursor-pointer items-center gap-2">
                          <input
                            type="checkbox"
                            checked={
                              (data?.[row.modoPruebasKey] ?? 'false') === 'true'
                            }
                            onChange={e =>
                              setModoPruebasServicio(
                                row.modoPruebasKey,
                                e.target.checked
                              )
                            }
                            className="rounded border-gray-300"
                          />
                          <span className="text-xs">
                            {(data?.[row.modoPruebasKey] ?? 'false') === 'true'
                              ? 'Sí'
                              : 'No'}
                          </span>
                        </label>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card className="border-amber-200 bg-amber-50/50 dark:bg-amber-950/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            Modo pruebas y correo de pruebas
          </CardTitle>

          <CardDescription>
            Modo pruebas global redirige envíos al correo indicado (si el
            servicio también tiene «→ Pruebas» activo en el panel de arriba).
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded border p-3">
            <span className="text-sm font-medium">
              Modo pruebas global (redirigir al correo de pruebas)
            </span>

            <label className="relative inline-flex cursor-pointer items-center">
              <input
                type="checkbox"
                checked={(data?.modo_pruebas ?? 'false') === 'true'}
                onChange={e =>
                  setData(
                    data
                      ? {
                          ...data,
                          modo_pruebas: e.target.checked ? 'true' : 'false',
                        }
                      : data
                  )
                }
                className="peer sr-only"
              />

              <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-amber-600 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none dark:border-gray-600 dark:bg-gray-700" />

              <span className="ml-2 text-sm">
                {(data?.modo_pruebas ?? 'false') === 'true'
                  ? 'Activo'
                  : 'Inactivo'}
              </span>
            </label>
          </div>
          <div>
            <Label>Correo de pruebas</Label>

            <Input
              type="email"
              value={data?.email_pruebas ?? ''}
              onChange={e =>
                setData(
                  data ? { ...data, email_pruebas: e.target.value } : data
                )
              }
              placeholder="ejemplo@correo.com"
              className="mt-1"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            El OTP de Finiquito no se redirige: siempre llega al correo del
            colaborador.
          </p>
          <div className="flex justify-end pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={handleEnviarPrueba}
              disabled={sendingTest || !(data?.email_pruebas ?? '').trim()}
            >
              <Mail className="mr-2 h-4 w-4" />

              {sendingTest
                ? 'Enviando...'
                : 'Enviar prueba a todos los correos registrados'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Mail className="h-5 w-5" />
            Cuentas de correo por servicio
          </CardTitle>

            <CardDescription>
            Configure hasta 4 cuentas SMTP. Asigne abajo qué buzón usa cada
            módulo del menú Notificaciones y cada servicio (Cobros, Estado de
            cuenta, Recibos). En Gmail con 2FA use contraseña de aplicación.
          </CardDescription>
          <div className="mt-3 flex flex-wrap gap-2">
            {cuentas.slice(0, CUENTAS_COUNT).map((c, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 rounded-md border border-blue-200/60 bg-white/70 px-2 py-1 text-xs dark:bg-slate-900/40"
              >
                <span className="font-medium text-blue-900 dark:text-blue-100">
                  Cuenta {idx + 1}
                </span>
                <CuentaClaveIndicador
                  guardada={c.smtp_password_guardada}
                  pendiente={cuentaTieneClavePendiente(c)}
                  smtpUser={c.smtp_user}
                />
              </div>
            ))}
          </div>
        </CardHeader>
      </Card>

      {[0, 1, 2, 3].map(i => (
        <Card key={i}>
          <CardHeader className="pb-2">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <CardTitle className="text-base">
                  Cuenta {i + 1} - {SERVICIO_POR_CUENTA[i + 1] ?? `Cuenta ${i + 1}`}
                </CardTitle>

                <CardDescription className="mt-1">
                  {i === 0 && `SMTP: ${SERVICIO_POR_CUENTA[1]}`}
                  {i === 1 && `SMTP: ${SERVICIO_POR_CUENTA[2]}`}
                  {i === 2 && `SMTP: ${SERVICIO_POR_CUENTA[3]}`}
                  {i === 3 && `SMTP: ${SERVICIO_POR_CUENTA[4]}`}
                </CardDescription>
              </div>
              <CuentaClaveIndicador
                guardada={cuentas[i]?.smtp_password_guardada}
                pendiente={cuentaTieneClavePendiente(cuentas[i])}
                smtpUser={cuentas[i]?.smtp_user}
              />
              {smtpTestOk[i] === true ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-900">
                  SMTP verificado
                </span>
              ) : null}
              {smtpTestOk[i] === false ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-900">
                  SMTP falló
                </span>
              ) : null}
            </div>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="grid gap-2 sm:grid-cols-2">
              <div>
                <Label>Servidor SMTP</Label>

                <Input
                  value={cuentas[i]?.smtp_host ?? ''}
                  onChange={e => updateCuenta(i, 'smtp_host', e.target.value)}
                  placeholder="smtp.gmail.com"
                />
              </div>

              <div>
                <Label>Puerto SMTP</Label>

                <Input
                  type="text"
                  value={cuentas[i]?.smtp_port ?? '587'}
                  onChange={e => updateCuenta(i, 'smtp_port', e.target.value)}
                  placeholder="587"
                />
              </div>

              <div>
                <Label>Usuario / Email</Label>

                <Input
                  type="email"
                  value={cuentas[i]?.smtp_user ?? ''}
                  onChange={e => updateCuenta(i, 'smtp_user', e.target.value)}
                  placeholder="correo@ejemplo.com"
                />
              </div>

              <div>
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <Label>Contraseña SMTP</Label>
                  <CuentaClaveIndicador
                    guardada={cuentas[i]?.smtp_password_guardada}
                    pendiente={cuentaTieneClavePendiente(cuentas[i])}
                    smtpUser={cuentas[i]?.smtp_user}
                  />
                </div>

                <Input
                  type="password"
                  value={
                    cuentas[i]?.smtp_password &&
                    (cuentas[i].smtp_password as string) !== '***'
                      ? (cuentas[i].smtp_password as string)
                      : ''
                  }
                  onChange={e =>
                    updateCuenta(i, 'smtp_password', e.target.value)
                  }
                  placeholder={
                    cuentas[i]?.smtp_password_guardada
                      ? 'Dejar vacío para conservar la clave guardada'
                      : 'Contraseña de aplicación Gmail'
                  }
                  autoComplete="off"
                />
                {cuentas[i]?.smtp_password_guardada &&
                !cuentaTieneClavePendiente(cuentas[i]) ? (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Hay una clave guardada en el servidor. Escriba aquí solo si
                    desea cambiarla.
                  </p>
                ) : null}
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={testingSmtp[i] || !(cuentas[i]?.smtp_user ?? '').trim()}
                    onClick={() => probarConexionCuenta(i)}
                  >
                    {testingSmtp[i] ? 'Comprobando…' : 'Probar conexión SMTP'}
                  </Button>
                  <span className="self-center text-xs text-muted-foreground">
                    Login al servidor (sin enviar correo). Al guardar una clave
                    nueva también se verifica automáticamente.
                  </span>
                </div>
              </div>

              <div>
                <Label>Remitente (From)</Label>

                <Input
                  type="email"
                  value={cuentas[i]?.from_email ?? ''}
                  onChange={e => updateCuenta(i, 'from_email', e.target.value)}
                  placeholder="correo@ejemplo.com"
                />
              </div>

              <div>
                <Label>Nombre remitente</Label>

                <Input
                  value={cuentas[i]?.from_name ?? 'RapiCredit'}
                  onChange={e => updateCuenta(i, 'from_name', e.target.value)}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      ))}

      {ASIGNACION_NOTIF_GRUPOS.map(grupo => (
        <Card key={grupo.titulo}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertCircle className="h-4 w-4" />
              {grupo.titulo}
            </CardTitle>
            <CardDescription>{grupo.descripcion}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2">
              {grupo.items.map(({ id, label, defaultCuenta }) => (
                <div
                  key={id}
                  className="flex items-center justify-between rounded border p-3"
                >
                  <span className="pr-2 text-sm font-medium">{label}</span>
                  <SelectCuentaAsignacion
                    id={`asig-notif-${id}`}
                    value={asignacion[id] ?? defaultCuenta}
                    onChange={v => setNotifTabCuenta(id, v)}
                  />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={saving}>
          <Save className="mr-2 h-4 w-4" />

          {saving ? 'Guardando...' : 'Guardar configuración de 4 cuentas'}
        </Button>
      </div>
    </div>
  )
}
