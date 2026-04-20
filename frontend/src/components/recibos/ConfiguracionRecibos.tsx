import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { Link } from 'react-router-dom'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  AlertTriangle,
  Clock,
  Eye,
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
import { Textarea } from '../ui/textarea'
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
import {
  emailConfigService,
  notificacionService,
} from '../../services/notificacionService'
import { NOTIFICACIONES_QUERY_KEYS } from '../../queries/notificaciones'
import { toast } from 'sonner'
import { getErrorMessage } from '../../types/errors'

export const RECIBOS_CONFIG_EMAIL_CUENTAS_QUERY_KEY = [
  'notificaciones',
  'recibos',
  'configEmailCuentas',
] as const

function normalizarBccRecibosParaGuardar(a: string, b: string): string[] {
  const out: string[] = []
  const seen = new Set<string>()
  for (const raw of [a, b]) {
    const t = String(raw ?? '').trim()
    if (!t || !t.includes('@')) continue
    const low = t.toLowerCase()
    if (seen.has(low)) continue
    seen.add(low)
    out.push(t)
    if (out.length >= 2) break
  }
  return out
}

function buildPutPayload(
  cur: EmailCuentasResponse,
  patch: {
    email_activo_recibos: string
    modo_pruebas_recibos: string
    recibos_cuenta: number
    recibos_bcc_emails: string[]
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
    recibos_bcc_emails: patch.recibos_bcc_emails,
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
  const [recibosBcc1, setRecibosBcc1] = useState('')
  const [recibosBcc2, setRecibosBcc2] = useState('')

  /** Plantilla en disco (texto); puede divergir del cuadro si el usuario edita sin traer del servidor. */
  const [editorHtml, setEditorHtml] = useState('')
  /**
   * HTML exacto de la parte text/html del SMTP (mismo pipeline que send_email: logo URL, saneado).
   * La vista previa del iframe usa solo esto, no el editor en vivo, para coincidir con el correo enviado.
   */
  const [htmlVistaSmtp, setHtmlVistaSmtp] = useState('')
  /** HTML procesado de la plantilla persistida (BD/archivo): misma fuente que job y envío real. */
  const [htmlVistaSmtpGuardada, setHtmlVistaSmtpGuardada] = useState('')
  const [vistaGuardadaCargando, setVistaGuardadaCargando] = useState(false)
  const [vistaGuardadaError, setVistaGuardadaError] = useState<string | null>(null)
  /** Último HTML crudo traído o guardado en servidor; sirve para detectar borrador sin persistir. */
  const [plantillaCrudaUltimaServidor, setPlantillaCrudaUltimaServidor] = useState('')
  const [plantillaCargando, setPlantillaCargando] = useState(false)
  const [plantillaError, setPlantillaError] = useState<string | null>(null)
  const [guardandoPlantillaCorreo, setGuardandoPlantillaCorreo] = useState(false)
  const previewSeq = useRef(0)

  const cargarVistaPreviaPlantillaGuardada = useCallback(async () => {
    setVistaGuardadaCargando(true)
    setVistaGuardadaError(null)
    try {
      const { html } = await notificacionService.obtenerPlantillaRecibosHtmlVistaEnvio()
      setHtmlVistaSmtpGuardada(String(html ?? '').trim())
    } catch (e) {
      setHtmlVistaSmtpGuardada('')
      setVistaGuardadaError(getErrorMessage(e))
    } finally {
      setVistaGuardadaCargando(false)
    }
  }, [])

  const cargarPlantillaDesdeServidor = useCallback(async () => {
    setPlantillaCargando(true)
    setPlantillaError(null)
    try {
      const raw = await notificacionService.obtenerPlantillaHtmlRecibos()
      setEditorHtml(raw)
      setPlantillaCrudaUltimaServidor(raw)
    } catch (e) {
      setPlantillaError(getErrorMessage(e))
    } finally {
      setPlantillaCargando(false)
    }
    void cargarVistaPreviaPlantillaGuardada()
  }, [cargarVistaPreviaPlantillaGuardada])

  useEffect(() => {
    void cargarPlantillaDesdeServidor()
  }, [cargarPlantillaDesdeServidor])

  /** Vista previa = mismo pipeline que send_email (POST), actualizado al pegar/editar con debounce. */
  useEffect(() => {
    const seq = ++previewSeq.current
    const ac = new AbortController()
    const t = window.setTimeout(() => {
      void (async () => {
        if (!editorHtml.trim()) {
          if (seq === previewSeq.current && !ac.signal.aborted) {
            setHtmlVistaSmtp('')
            setPlantillaError(null)
          }
          return
        }
        try {
          const { html } = await notificacionService.previsualizarPlantillaRecibosHtml(editorHtml, {
            signal: ac.signal,
          })
          if (seq === previewSeq.current && !ac.signal.aborted) {
            setHtmlVistaSmtp(html)
            setPlantillaError(null)
          }
        } catch (e: unknown) {
          if (ac.signal.aborted) return
          if (seq === previewSeq.current) {
            setPlantillaError(getErrorMessage(e))
          }
        }
      })()
    }, 400)
    return () => {
      ac.abort()
      window.clearTimeout(t)
    }
  }, [editorHtml])

  const hayCambiosPlantillaSinGuardar = useMemo(
    () => editorHtml !== plantillaCrudaUltimaServidor,
    [editorHtml, plantillaCrudaUltimaServidor]
  )

  useEffect(() => {
    if (!data) return
    setEmailActivoRecibos((data.email_activo_recibos ?? 'true') === 'true')
    setModoPruebasRecibos((data.modo_pruebas_recibos ?? 'false') === 'true')
    setCuentaRecibos(
      typeof data.asignacion?.recibos === 'number' ? data.asignacion.recibos : 3
    )
    const bcc = Array.isArray(data.recibos_bcc_emails) ? data.recibos_bcc_emails : []
    setRecibosBcc1(String(bcc[0] ?? '').trim())
    setRecibosBcc2(String(bcc[1] ?? '').trim())
  }, [data])

  useEffect(() => {
    if (emergencyResetSeq <= 0) return
    setGuardando(false)
    setProbando(false)
    setGuardandoPlantillaCorreo(false)
    setVistaGuardadaCargando(false)
  }, [emergencyResetSeq])

  const puedeCancelarEmergencia =
    guardando ||
    probando ||
    isFetching ||
    guardandoPlantillaCorreo ||
    plantillaCargando ||
    vistaGuardadaCargando

  const cancelarEmergenciaConfig = () => {
    setGuardando(false)
    setProbando(false)
    setGuardandoPlantillaCorreo(false)
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
          recibos_bcc_emails: normalizarBccRecibosParaGuardar(recibosBcc1, recibosBcc2),
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
    recibosBcc1,
    recibosBcc2,
    qc,
    refetch,
  ])

  const guardarPlantillaCorreoEnServidor = async () => {
    if (!editorHtml.trim()) {
      toast.warning('No hay HTML para guardar.')
      return
    }
    setGuardandoPlantillaCorreo(true)
    try {
      await notificacionService.guardarPlantillaRecibosHtml(editorHtml)
      toast.success(
        'Plantilla guardada en el servidor (BD). Prueba SMTP, envío manual y job usarán esta versión.'
      )
      await cargarPlantillaDesdeServidor()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setGuardandoPlantillaCorreo(false)
    }
  }

  const probarCorreo = async () => {
    const to = emailPrueba.trim()
    if (!to || !to.includes('@')) {
      toast.warning('Indique un correo de destino válido.')
      return
    }
    setProbando(true)
    try {
      const res = await emailConfigService.probarConfiguracionEmail(
        to,
        undefined,
        undefined,
        undefined,
        {
          servicio: 'recibos',
          tipo_tab: 'recibos',
          recibos_prueba_datos_reales: true,
          // Sin recibos_html_plantilla: el backend usa la misma plantilla que el job/envío masivo
          // (BD `recibos_plantilla_correo_html` o archivo). Evita divergencias editor ≠ guardado.
        },
        { timeout: 120_000 }
      )
      const ok = Boolean((res as { success?: boolean })?.success)
      const msg = String((res as { mensaje?: string })?.mensaje || '').trim()
      if (ok) {
        toast.success(
          msg ||
            'Muestra Recibos enviada: mismo HTML que el envío masivo (plantilla guardada) + PDF, primer cliente en ventana.'
        )
      } else {
        toast.error(msg || 'No se pudo enviar la muestra Recibos.')
      }
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

          <div className="space-y-3 rounded-lg border border-slate-200 bg-white/80 p-3">
            <p className="text-sm font-medium text-gray-800">Copia oculta (CCO) en envíos Recibos</p>
            <p className="text-xs text-gray-600">
              Opcional: hasta 2 correos que recibirán copia oculta de cada envío Recibos (mismo adjunto y
              cuerpo). Se guardan en la configuración de email y se aplican al enviar por SMTP.
            </p>
            <div className="grid max-w-xl gap-3 sm:grid-cols-2">
              <div className="flex flex-col gap-1">
                <label htmlFor="rec-bcc-1" className="text-xs font-medium text-gray-600">
                  CCO opción 1
                </label>
                <Input
                  id="rec-bcc-1"
                  type="email"
                  autoComplete="off"
                  placeholder="correo@ejemplo.com"
                  value={recibosBcc1}
                  onChange={e => setRecibosBcc1(e.target.value)}
                  className="h-9 bg-white"
                  maxLength={120}
                />
              </div>
              <div className="flex flex-col gap-1">
                <label htmlFor="rec-bcc-2" className="text-xs font-medium text-gray-600">
                  CCO opción 2
                </label>
                <Input
                  id="rec-bcc-2"
                  type="email"
                  autoComplete="off"
                  placeholder="correo@ejemplo.com"
                  value={recibosBcc2}
                  onChange={e => setRecibosBcc2(e.target.value)}
                  className="h-9 bg-white"
                  maxLength={120}
                />
              </div>
            </div>
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
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <CardTitle className="flex items-center gap-2 text-base">
                <Eye className="h-4 w-4 text-slate-600" aria-hidden />
                HTML del correo Recibos y vista previa
              </CardTitle>
              <CardDescription className="mt-1">
                Hay dos vistas: <strong>borrador</strong> (HTML del cuadro + pipeline SMTP) y{' '}
                <strong>plantilla guardada</strong> (lee BD/archivo en el servidor y aplica el mismo pipeline que
                el job). Así se ve exactamente el <code className="text-[11px]">text/html</code> que se enviará
                mientras edita sin guardar. <strong>Enviar prueba</strong>, envío manual y job solo usan la
                versión persistida; guarde con el botón verde antes de probar o ejecutar masivo.
              </CardDescription>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="shrink-0"
                disabled={vistaGuardadaCargando}
                onClick={() => void cargarVistaPreviaPlantillaGuardada()}
                title="Solo actualiza la vista de la plantilla persistida (no cambia el editor)"
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${vistaGuardadaCargando ? 'animate-spin' : ''}`}
                  aria-hidden
                />
                {vistaGuardadaCargando ? 'Actualizando vista envío…' : 'Actualizar vista envío'}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="shrink-0"
                disabled={plantillaCargando}
                onClick={() => void cargarPlantillaDesdeServidor()}
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${plantillaCargando ? 'animate-spin' : ''}`}
                  aria-hidden
                />
                {plantillaCargando ? 'Cargando…' : 'Traer del servidor'}
              </Button>
              <Button
                type="button"
                variant="default"
                size="sm"
                className="shrink-0 bg-emerald-700 text-white hover:bg-emerald-800"
                disabled={guardandoPlantillaCorreo || !editorHtml.trim()}
                onClick={() => void guardarPlantillaCorreoEnServidor()}
              >
                <Save className={`mr-2 h-4 w-4 ${guardandoPlantillaCorreo ? 'animate-pulse' : ''}`} aria-hidden />
                {guardandoPlantillaCorreo ? 'Guardando plantilla…' : 'Guardar plantilla'}
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="shrink-0 text-slate-600"
                disabled={!editorHtml.trim() && !htmlVistaSmtp.trim()}
                onClick={() => {
                  setEditorHtml('')
                  setHtmlVistaSmtp('')
                  setPlantillaError(null)
                }}
                title="Vacía el editor y la vista previa del borrador (la vista «envío» sigue mostrando lo guardado en servidor)"
              >
                Vaciar editor
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {plantillaError ? (
            <p className="text-sm text-red-700">{plantillaError}</p>
          ) : null}

          {hayCambiosPlantillaSinGuardar ? (
            <div
              className="flex flex-wrap items-start gap-2 rounded-md border border-amber-300 bg-amber-50/90 px-3 py-2 text-sm text-amber-950"
              role="status"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" aria-hidden />
              <p>
                Hay cambios en el editor <strong>sin guardar en el servidor</strong>. Job, envío masivo y
                «Enviar prueba» usan la plantilla persistida; la sección <strong>Plantilla guardada</strong>{' '}
                abajo muestra ese HTML. Guarde con el botón verde para alinear envíos con el borrador.
              </p>
            </div>
          ) : null}

          <div className="flex flex-col gap-2">
            <label htmlFor="recibos-html-editor" className="text-xs font-medium text-gray-700">
              HTML (borrador: la vista previa del cuadro usa este texto; job y prueba SMTP leen solo lo guardado)
            </label>
            <Textarea
              id="recibos-html-editor"
              spellCheck={false}
              value={editorHtml}
              onChange={e => setEditorHtml(e.target.value)}
              placeholder="Pulse «Traer del servidor» para cargar la misma versión que usa SMTP."
              className="min-h-[220px] max-h-[min(50vh,420px)] resize-y font-mono text-xs leading-relaxed"
            />
          </div>

          <div>
            <p className="mb-2 text-xs font-medium text-gray-600">
              Vista previa del borrador (mismo pipeline SMTP que la parte <code className="text-[11px]">text/html</code>)
            </p>
            {htmlVistaSmtp.trim() ? (
              <iframe
                title="Vista previa borrador Recibos: HTML del editor tras pipeline SMTP"
                sandbox="allow-same-origin allow-popups"
                className="h-[min(360px,50vh)] w-full max-w-full rounded-md border border-slate-200 bg-slate-100"
                srcDoc={htmlVistaSmtp}
              />
            ) : (
              <p className="rounded-md border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-gray-500">
                {plantillaCargando
                  ? 'Cargando plantilla del servidor…'
                  : 'Escriba HTML arriba o pulse «Traer del servidor». La vista previa del borrador aparece al poco tiempo.'}
              </p>
            )}
          </div>

          <div className="border-t border-slate-200 pt-4">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-medium text-gray-800">
                Plantilla guardada en servidor (misma fuente que job y envío real)
              </p>
            </div>
            {vistaGuardadaError ? (
              <p className="mb-2 text-sm text-red-700">{vistaGuardadaError}</p>
            ) : null}
            {htmlVistaSmtpGuardada.trim() ? (
              <iframe
                title="Vista previa plantilla Recibos persistida: mismo HTML text/html que envían job y clientes"
                sandbox="allow-same-origin allow-popups"
                className="h-[min(360px,50vh)] w-full max-w-full rounded-md border border-emerald-200/80 bg-slate-100"
                srcDoc={htmlVistaSmtpGuardada}
              />
            ) : (
              <p className="rounded-md border border-dashed border-emerald-200/70 bg-emerald-50/40 px-4 py-6 text-center text-sm text-gray-600">
                {vistaGuardadaCargando
                  ? 'Generando vista desde la plantilla persistida en el servidor…'
                  : 'Pulse «Actualizar vista envío» o «Traer del servidor» para cargar la vista de lo guardado en BD (o archivo por defecto).'}
              </p>
            )}
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
            Un solo correo de muestra: plantilla HTML <strong>ya guardada</strong> (misma que el envío masivo)
            más PDF de estado de cuenta del primer cliente válido en la ventana (Caracas). Destino: solo el
            correo que indique abajo. CCO según Recibos. Guarde la plantilla antes si acaba de editarla.
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
