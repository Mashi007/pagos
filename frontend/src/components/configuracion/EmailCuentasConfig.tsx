/**









 * Configuración de 4 cuentas de correo con asignación por servicio.









 * Cuenta 1 = Cobros, 2 = Estado de cuenta, 3 y 4 = Notificaciones (por pestaña).









 */

import { useState, useEffect } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import { Mail, Save, AlertCircle, CheckCircle } from 'lucide-react'

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
  NOTIF_TABS,
  type EmailCuentasResponse,
  type CuentaEmailItem,
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

export function EmailCuentasConfig() {
  const queryClient = useQueryClient()

  const [data, setData] = useState<EmailCuentasResponse | null>(null)

  const [loading, setLoading] = useState(true)

  const [saving, setSaving] = useState(false)

  const [sendingTest, setSendingTest] = useState(false)

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

      setAsignacion({ ...tab })
    } catch (e) {
      console.error(e)

      toast.error('Error cargando configuración de cuentas')

      setData({
        version: 2,

        cuentas: Array.from({ length: CUENTAS_COUNT }, emptyCuenta),

        asignacion: { cobros: 1, estado_cuenta: 2, notificaciones_tab: {}, recibos: 3 },
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
  }

  const setServicioActivo = (
    key: keyof EmailCuentasResponse,
    value: string
  ) => {
    if (!data) return

    setData({ ...data, [key]: value })
  }

  const SERVICIOS_DISPONIBLES: {
    key: keyof EmailCuentasResponse
    label: string
    cuenta: number
  }[] = [
    {
      key: 'email_activo_cobros',
      label: 'Cobros (formulario público, recibos)',
      cuenta: 1,
    },

    {
      key: 'email_activo_estado_cuenta',
      label: 'Estado de cuenta (código y envío PDF)',
      cuenta: 2,
    },

    {
      key: 'email_activo_finiquito',
      label: 'Finiquito (código OTP portal colaborador)',
      cuenta: 2,
    },

    {
      key: 'email_activo_notificaciones',
      label: 'Notificaciones (plantillas a clientes)',
      cuenta: 3,
    },

    {
      key: 'email_activo_recibos',
      label: 'Recibos (estado de cuenta tras conciliación, job diario 15:00 Caracas)',
      cuenta: 3,
    },
  ]

  const handleSave = async () => {
    if (!data) return

    setSaving(true)

    try {
      const cuentas = data.cuentas.slice(0, CUENTAS_COUNT)

      while (cuentas.length < CUENTAS_COUNT) cuentas.push(emptyCuenta())

      await emailCuentasApi.put({
        cuentas,

        asignacion: {
          cobros: data.asignacion?.cobros ?? 1,

          estado_cuenta: data.asignacion?.estado_cuenta ?? 2,

          notificaciones_tab: asignacion,

          recibos: data.asignacion?.recibos ?? 3,
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
      })

      toast.success('Configuración de 4 cuentas guardada')

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
            Servicios disponibles
          </CardTitle>

          <CardDescription>
            La configuración se guarda en la base de datos (tabla{' '}
            <code className="rounded bg-muted px-1 text-xs">configuracion</code>
            , clave{' '}
            <code className="rounded bg-muted px-1 text-xs">email_config</code>
            ): sobrevive reinicios y despliegues. Las contraseñas SMTP/IMAP se
            guardan cifradas cuando el servidor define clave de cifrado.{' '}
            <span className="block pt-2 text-foreground/90">
              Active o desactive el envío por servicio (cuenta 1, 2 o 3/4).
              Cobros: recibo al aprobar y &quot;Enviar recibo&quot;. Rechazo de
              pagos reportados: Notificaciones (cuenta 3/4).
            </span>
          </CardDescription>
        </CardHeader>

        <CardContent>
          <div className="mb-4 flex flex-col justify-between gap-2 rounded border border-primary/25 bg-muted/30 p-3 sm:flex-row sm:items-center">
            <div>
              <p className="text-sm font-medium">
                Correo electrónico (maestro)
              </p>

              <p className="text-xs text-muted-foreground">
                Si está inactivo, no se envía ningún e-mail (anula los
                interruptores de abajo).
              </p>
            </div>

            <label className="relative inline-flex cursor-pointer items-center">
              <input
                type="checkbox"
                checked={(data?.email_activo ?? 'true') === 'true'}
                onChange={e =>
                  setServicioActivo(
                    'email_activo',
                    e.target.checked ? 'true' : 'false'
                  )
                }
                className="peer sr-only"
              />

              <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-blue-600 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none dark:border-gray-600 dark:bg-gray-700" />

              <span className="ml-2 text-sm">
                {(data?.email_activo ?? 'true') === 'true'
                  ? 'Activo'
                  : 'Inactivo'}
              </span>
            </label>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {SERVICIOS_DISPONIBLES.map(({ key, label, cuenta }) => (
              <div
                key={key}
                className="flex items-center justify-between rounded border p-3"
              >
                <div>
                  <p className="text-sm font-medium">{label}</p>

                  <p className="text-xs text-muted-foreground">
                    Cuenta {cuenta}
                  </p>
                </div>

                <label className="relative inline-flex cursor-pointer items-center">
                  <input
                    type="checkbox"
                    checked={(data?.[key] ?? 'true') === 'true'}
                    onChange={e =>
                      setServicioActivo(
                        key,
                        e.target.checked ? 'true' : 'false'
                      )
                    }
                    className="peer sr-only"
                  />

                  <div className="peer h-6 w-11 rounded-full bg-gray-200 after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:bg-blue-600 peer-checked:after:translate-x-full peer-checked:after:border-white peer-focus:outline-none dark:border-gray-600 dark:bg-gray-700" />

                  <span className="ml-2 text-sm">
                    {(data?.[key] ?? 'true') === 'true' ? 'Activo' : 'Inactivo'}
                  </span>
                </label>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="border-amber-200 bg-amber-50/50 dark:bg-amber-950/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            Modo pruebas y correo de pruebas
          </CardTitle>

          <CardDescription>
            Si "Modo pruebas" está activo, todos los envíos se redirigen al
            correo indicado. El correo de pruebas es obligatorio cuando el modo
            pruebas está activado.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded border p-3">
            <span className="text-sm font-medium">
              Modo pruebas (redirigir envíos al correo de pruebas)
            </span>

            <label className="relative inline-flex cursor-pointer items-center">
              <input
                type="checkbox"
                checked={(data?.modo_pruebas ?? 'true') === 'true'}
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
                {(data?.modo_pruebas ?? 'true') === 'true'
                  ? 'Activo'
                  : 'Inactivo'}
              </span>
            </label>
          </div>
          <div>
            <Label>
              Correo de pruebas (obligatorio si modo pruebas está activo)
            </Label>

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
          <div className="space-y-2 border-t border-amber-200/80 pt-3">
            <p className="text-xs font-medium text-amber-900/90">
              Modo prueba: PDF de estado de cuenta (cuenta 2)
            </p>
            <p className="text-xs text-muted-foreground">
              Si activa esta opción, los envíos de estado de cuenta pueden ir al
              correo de pruebas. El código OTP del portal Finiquito siempre se
              envía al correo del colaborador registrado (no se redirige a
              pruebas).
            </p>
            <label className="flex items-center justify-between gap-2 rounded border border-amber-100 bg-white/60 p-2">
              <span className="text-sm">Estado de cuenta (PDF) → pruebas</span>
              <input
                type="checkbox"
                checked={
                  (data?.modo_pruebas_estado_cuenta ?? 'false') === 'true'
                }
                onChange={e =>
                  setData(
                    data
                      ? {
                          ...data,
                          modo_pruebas_estado_cuenta: e.target.checked
                            ? 'true'
                            : 'false',
                        }
                      : data
                  )
                }
                className="rounded border-gray-300"
              />
            </label>
            <label className="flex items-center justify-between gap-2 rounded border border-amber-100 bg-white/60 p-2">
              <span className="text-sm">Recibos (post-conciliación) → pruebas</span>
              <input
                type="checkbox"
                checked={(data?.modo_pruebas_recibos ?? 'false') === 'true'}
                onChange={e =>
                  setData(
                    data
                      ? {
                          ...data,
                          modo_pruebas_recibos: e.target.checked
                            ? 'true'
                            : 'false',
                        }
                      : data
                  )
                }
                className="rounded border-gray-300"
              />
            </label>
          </div>
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
            Configure hasta 4 cuentas. Cada servicio usa una cuenta:{' '}
            <strong>Cuenta 1</strong> = Cobros (formulario público, recibos al
            aprobar pagos reportados),
            <strong> Cuenta 2</strong> = Estado de cuenta,{' '}
            <strong>Cuentas 3 y 4</strong> = Notificaciones (puede elegir por
            pestaña; también rechazo de pagos reportados).{' '}
            <span className="block pt-2 text-amber-900 dark:text-amber-200">
              Gmail con verificación en dos pasos: en SMTP debe usar una{' '}
              <strong>contraseña de aplicación</strong> (16 caracteres) desde
              Seguridad de la cuenta de Google, no la contraseña habitual.
            </span>
          </CardDescription>
        </CardHeader>
      </Card>

      {[0, 1, 2, 3].map(i => (
        <Card key={i}>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              Cuenta {i + 1} - {SERVICIO_POR_CUENTA[i + 1] ?? `Cuenta ${i + 1}`}
            </CardTitle>

            <CardDescription>
              {i === 0 &&
                'Usada en: Cobros (reporte público, recibo al aprobar y envío manual de recibo).'}

              {i === 1 &&
                'Usada en: rapicredit-estadocuenta (consulta y envío de PDF).'}

              {(i === 2 || i === 3) &&
                `Usada en: Notificaciones (pestañas que elija como "Cuenta ${i + 1}" abajo).`}
            </CardDescription>
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
                <Label>Contraseña</Label>

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
                  placeholder="***"
                  autoComplete="off"
                />
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

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Asignación: Recibos</CardTitle>
          <CardDescription>
            Correos automáticos con PDF de estado de cuenta (servicio <code>recibos</code>). Por
            defecto Cuenta 3; puede usar la misma cuenta que Notificaciones o la de Estado de cuenta.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex max-w-md flex-col gap-2">
            <Label htmlFor="asig-recibos-cuenta">Cuenta SMTP para Recibos</Label>
            <select
              id="asig-recibos-cuenta"
              className="flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm"
              value={data?.asignacion?.recibos ?? 3}
              onChange={e => {
                const v = Number(e.target.value)
                setData(d =>
                  d
                    ? {
                        ...d,
                        asignacion: {
                          cobros: d.asignacion?.cobros ?? 1,
                          estado_cuenta: d.asignacion?.estado_cuenta ?? 2,
                          notificaciones_tab: {
                            ...(d.asignacion?.notificaciones_tab ?? {}),
                          },
                          recibos: v,
                        },
                      }
                    : d
                )
              }}
            >
              <option value={1}>Cuenta 1</option>
              <option value={2}>Cuenta 2</option>
              <option value={3}>Cuenta 3</option>
              <option value={4}>Cuenta 4</option>
            </select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <AlertCircle className="h-4 w-4" />
            Asignación Notificaciones: qué cuenta usa cada caso de envío
          </CardTitle>

          <CardDescription>
            Elija para cada tipo de notificación (mora, prejudicial, etc.) si
            usa <strong>Cuenta 3</strong> o <strong>Cuenta 4</strong> (servidor
            SMTP y credenciales). El caso{' '}
            <strong>2 días antes (cuota pendiente)</strong> usa como remitente
            visible{' '}
            <code className="rounded bg-muted px-1 text-xs">
              recuerda@rapicreditca.com
            </code>{' '}
            en el backend; la cuenta aquí solo define con qué buzón se conecta
            el servidor. En Google Workspace, autorice la dirección recuerda@
            como alias Enviar correo como del usuario SMTP de esa cuenta.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            {NOTIF_TABS.map(({ id, label }) => (
              <div
                key={id}
                className="flex items-center justify-between rounded border p-3"
              >
                <span className="text-sm font-medium">{label}</span>

                <select
                  className="rounded border bg-background px-2 py-1 text-sm"
                  value={asignacion[id] ?? 3}
                  onChange={e => setNotifTabCuenta(id, Number(e.target.value))}
                >
                  <option value={3}>Cuenta 3</option>

                  <option value={4}>Cuenta 4</option>
                </select>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={saving}>
          <Save className="mr-2 h-4 w-4" />

          {saving ? 'Guardando...' : 'Guardar configuración de 4 cuentas'}
        </Button>
      </div>
    </div>
  )
}
