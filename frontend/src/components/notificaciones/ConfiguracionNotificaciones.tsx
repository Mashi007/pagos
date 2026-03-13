import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Settings, Mail, FileText, Clock, X, TestTube, CheckCircle } from 'lucide-react'
import { emailConfigService } from '../../services/notificacionService'
import { notificacionService, type NotificacionPlantilla } from '../../services/notificacionService'
import { getErrorDetail } from '../../types/errors'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { toast } from 'sonner'

const QUERY_KEY_ENVIOS = ['configuracion-notificaciones-envios'] as const
const QUERY_KEY_PLANTILLAS = ['notificaciones-plantillas', { solo_activas: false }] as const

/** Claves reservadas en la config (no son tipos de caso) */
const CLAVES_GLOBALES = ['modo_pruebas', 'email_pruebas', 'emails_pruebas'] as const

/** Tipo de configuración por criterio (habilitado, cco, plantilla opcional, programador) */
export type ConfigEnvioItem = {
  habilitado: boolean
  cco: string[]
  plantilla_id?: number | null
  programador?: string
  /** Incluir PDF anexo para este tipo. Por defecto true. */
  incluir_pdf_anexo?: boolean
  /** Incluir documentos PDF fijos para este tipo. Por defecto true. */
  incluir_adjuntos_fijos?: boolean
}

/** Respuesta de la API: config por tipo + modo_pruebas y email_pruebas (un solo objeto, sin duplicar) */
export type ConfigEnvioCompleta = Record<string, ConfigEnvioItem | boolean | string | string[]>

/** Criterios de notificación (tipo → label). Exportado para uso en Plantillas / vinculación PDF. */
export const CRITERIOS: { tipo: string; label: string; categoria: string; color: 'blue' | 'green' | 'orange' | 'red' | 'slate' }[] = [
  { tipo: 'PAGO_5_DIAS_ANTES', label: 'Faltan 5', categoria: 'Notificación previa', color: 'blue' },
  { tipo: 'PAGO_3_DIAS_ANTES', label: 'Faltan 3', categoria: 'Notificación previa', color: 'blue' },
  { tipo: 'PAGO_1_DIA_ANTES', label: 'Falta 1', categoria: 'Notificación previa', color: 'blue' },
  { tipo: 'PAGO_DIA_0', label: 'Hoy vence', categoria: 'Día de pago', color: 'green' },
  { tipo: 'PAGO_1_DIA_ATRASADO', label: '1 día de retraso', categoria: 'Retrasada', color: 'orange' },
  { tipo: 'PAGO_3_DIAS_ATRASADO', label: '3 días de retraso', categoria: 'Retrasada', color: 'orange' },
  { tipo: 'PAGO_5_DIAS_ATRASADO', label: '5 días atrasado', categoria: 'Retrasada', color: 'orange' },
  { tipo: 'PREJUDICIAL', label: 'Prejudicial', categoria: 'Prejudicial', color: 'red' },
  { tipo: 'MORA_90', label: '90+ días de mora (moroso)', categoria: 'Mora 90+', color: 'slate' },
  { tipo: 'COBRANZA', label: 'Carta de cobranza', categoria: 'Cobranza', color: 'red' },
]

const COLORES = {
  blue: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-900', accent: 'text-blue-600' },
  green: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-900', accent: 'text-emerald-600' },
  orange: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-900', accent: 'text-amber-600' },
  red: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-900', accent: 'text-red-600' },
  slate: { bg: 'bg-slate-50', border: 'border-slate-200', text: 'text-slate-900', accent: 'text-slate-600' },
} as const

const HORA_DEFAULT = '04:00'

function defaultEnvio(): ConfigEnvioItem {
  return { habilitado: true, cco: [], programador: HORA_DEFAULT }
}

/** Normaliza la respuesta de la API en estado listo para el componente (carga única y clara). */
function normalizeConfigFromApi(raw: ConfigEnvioCompleta | null): {
  modoPruebas: boolean
  emailsPruebas: [string, string]
  configEnvios: Record<string, ConfigEnvioItem>
} {
  const data = raw || {}
  const modoPruebas = data.modo_pruebas === true
  let emailsPruebas: [string, string] = ['', '']
  if (Array.isArray(data.emails_pruebas)) {
    emailsPruebas = [data.emails_pruebas[0] ?? '', data.emails_pruebas[1] ?? '']
  } else if (typeof data.email_pruebas === 'string') {
    emailsPruebas = [data.email_pruebas, '']
  }
  const sinGlobales = { ...data }
  CLAVES_GLOBALES.forEach((k) => delete sinGlobales[k])
  return { modoPruebas, emailsPruebas, configEnvios: sinGlobales as Record<string, ConfigEnvioItem> }
}

export function ConfiguracionNotificaciones() {
  const [configEnvios, setConfigEnvios] = useState<Record<string, ConfigEnvioItem>>({})
  const [modoPruebas, setModoPruebas] = useState(false)
  const [emailsPruebas, setEmailsPruebas] = useState<[string, string]>(['', ''])
  const [guardandoEnvios, setGuardandoEnvios] = useState(false)
  const [ultimoGuardado, setUltimoGuardado] = useState<Date | null>(null)
  const [plantillas, setPlantillas] = useState<NotificacionPlantilla[]>([])
  const [enviandoPruebaIndice, setEnviandoPruebaIndice] = useState<number | null>(null)
  const [enviandoMasivo, setEnviandoMasivo] = useState(false)
  const [smtpConfigurado, setSmtpConfigurado] = useState<boolean | null>(null)
  const guardandoRef = useRef(false)
  const queryClient = useQueryClient()

  const { data: dataEnvios, isLoading: loadingEnvios, isError: errorEnvios } = useQuery({
    queryKey: QUERY_KEY_ENVIOS,
    queryFn: () => emailConfigService.obtenerConfiguracionEnvios() as Promise<ConfigEnvioCompleta>,
    staleTime: 1 * 60 * 1000,
  })
  const { data: plantillasList, isLoading: loadingPlantillas } = useQuery({
    queryKey: QUERY_KEY_PLANTILLAS,
    queryFn: () => notificacionService.listarPlantillas(undefined, false),
    staleTime: 1 * 60 * 1000,
    placeholderData: [] as NotificacionPlantilla[],
  })

  const cargando = loadingEnvios || loadingPlantillas

  useEffect(() => {
    if (dataEnvios != null) {
      const { modoPruebas: mp, emailsPruebas: ep, configEnvios: ce } = normalizeConfigFromApi(dataEnvios)
      setModoPruebas(mp)
      setEmailsPruebas(ep)
      setConfigEnvios(ce)
    }
  }, [dataEnvios])
  useEffect(() => {
    if (plantillasList != null) setPlantillas(plantillasList)
  }, [plantillasList])
  useEffect(() => {
    if (errorEnvios) toast.error('Error al cargar la configuración de envíos')
  }, [errorEnvios])

  useEffect(() => {
    if (modoPruebas) {
      emailConfigService.verificarEstadoConfiguracionEmail()
        .then((r) => setSmtpConfigurado(r?.configurada ?? false))
        .catch(() => setSmtpConfigurado(false))
    } else {
      setSmtpConfigurado(null)
    }
  }, [modoPruebas])

  const getConfig = (tipo: string): ConfigEnvioItem => {
    const c = configEnvios[tipo]
    if (!c) return defaultEnvio()
    return {
      habilitado: c.habilitado !== false,
      cco: Array.isArray(c.cco) ? c.cco : [],
      plantilla_id: c.plantilla_id ?? null,
      programador: c.programador ?? HORA_DEFAULT,
      // PDF = Carta_Cobranza (pestaña 2). Por defecto no; marcar para incluir. Adj. = documentos subidos (pestaña 3).
      incluir_pdf_anexo: c.incluir_pdf_anexo === true,
      incluir_adjuntos_fijos: c.incluir_adjuntos_fijos !== false,
    }
  }

  const setConfig = (tipo: string, upd: Partial<ConfigEnvioItem>) => {
    setConfigEnvios((prev) => {
      const current = prev[tipo] || defaultEnvio()
      return { ...prev, [tipo]: { ...current, ...upd } }
    })
  }

  const toggleEnvio = (tipo: string) => {
    const c = getConfig(tipo)
    setConfig(tipo, { habilitado: !c.habilitado })
  }

  const actualizarCCO = (tipo: string, index: number, email: string) => {
    const c = getConfig(tipo)
    const nuevosCCO = [...c.cco]
    if (index < nuevosCCO.length) nuevosCCO[index] = email
    else nuevosCCO.push(email)
    setConfig(tipo, { cco: nuevosCCO.slice(0, 3) })
  }

  const eliminarCCO = (tipo: string, index: number) => {
    const c = getConfig(tipo)
    setConfig(tipo, { cco: c.cco.filter((_, i) => i !== index) })
  }

  const guardarConfiguracionEnvios = async () => {
    if (guardandoRef.current) return
    guardandoRef.current = true
    setGuardandoEnvios(true)
    try {
      const payload: ConfigEnvioCompleta = {
        ...configEnvios,
        modo_pruebas: modoPruebas,
        emails_pruebas: emailsPruebas.filter((e) => e?.trim()),
        email_pruebas: emailsPruebas[0]?.trim() || '',
      }
      CRITERIOS.forEach(({ tipo }) => {
        const c = getConfig(tipo)
        ;(payload as Record<string, ConfigEnvioItem>)[tipo] = {
          ...c,
          incluir_pdf_anexo: c.incluir_pdf_anexo === true,
          incluir_adjuntos_fijos: c.incluir_adjuntos_fijos !== false,
        }
      })
      await emailConfigService.actualizarConfiguracionEnvios(payload)
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY_ENVIOS })
      setUltimoGuardado(new Date())
      toast.success('Configuración de envíos guardada')
    } catch {
      toast.error('Error al guardar la configuración de envíos')
    } finally {
      setGuardandoEnvios(false)
      guardandoRef.current = false
    }
  }

  const enModoPrueba = modoPruebas
  const enModoProduccion = !modoPruebas

  const plantillasPorTipo = (tipo: string): NotificacionPlantilla[] =>
    plantillas.filter((p) => p.tipo === tipo)


  const esEmailValido = (e: string) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test((e || '').trim())

  /** En modo prueba el envío usa solo plantilla predeterminada (ejemplo) y envía a correo de pruebas 1 y 2. */
  const ASUNTO_PLANTILLA_PREDETERMINADA = 'Notificación de cobranza - RapiCredit (ejemplo)'
  const MENSAJE_PLANTILLA_PREDETERMINADA =
    'Este es un correo de ejemplo con la plantilla predeterminada. Se envía a los correos de pruebas 1 y 2 para verificar la configuración de notificaciones.'

  const handleEnviarNotificacionesPrueba = async () => {
    const destinos = [emailsPruebas[0]?.trim(), emailsPruebas[1]?.trim()].filter(Boolean) as string[]
    if (!modoPruebas || destinos.length === 0) {
      toast.error('Configura al menos un correo de pruebas para enviar.')
      return
    }
    const invalidos = destinos.filter((e) => !esEmailValido(e))
    if (invalidos.length > 0) {
      toast.error(`Correo(s) no válido(s): ${invalidos.join(', ')}. Usa formato usuario@dominio.com`)
      return
    }
    try {
      setEnviandoPruebaIndice(0)
      const estadoEmail = await emailConfigService.verificarEstadoConfiguracionEmail()
      if (!estadoEmail?.configurada) {
        const problemas = estadoEmail?.problemas?.join('. ') || 'servidor SMTP, usuario y contraseña'
        toast.error(
          `Configura el email SMTP antes de enviar pruebas: ${problemas} Ve a Configuración → Email.`,
          { duration: 6000 }
        )
        setEnviandoPruebaIndice(null)
        return
      }
      let enviados = 0
      for (let i = 0; i < destinos.length; i++) {
        setEnviandoPruebaIndice(i + 1)
        const resultado = await emailConfigService.probarConfiguracionEmail(
          destinos[i],
          ASUNTO_PLANTILLA_PREDETERMINADA,
          MENSAJE_PLANTILLA_PREDETERMINADA,
          undefined
        )
        if (resultado?.success || resultado?.mensaje?.includes('enviado')) enviados++
      }
      if (enviados === destinos.length) {
        toast.success(`Notificación de ejemplo enviada a ${destinos.length} correo(s) de pruebas.`)
      } else if (enviados > 0) {
        toast.warning(`Enviado a ${enviados} de ${destinos.length} correos de pruebas. Revisa los que fallaron.`)
      } else {
        toast.error('No se pudo enviar a ninguno de los correos de pruebas.')
      }
    } catch (error: unknown) {
      const detalle = getErrorDetail(error)
      const mensaje = detalle || (error as Error)?.message || 'Error al enviar el correo de prueba'
      toast.error(mensaje, { duration: 5000 })
    } finally {
      setEnviandoPruebaIndice(null)
    }
  }

  /** Envío masivo manual: mismo flujo que las 11PM pero en este momento; si modo prueba está activo, todos los correos van al correo de pruebas. Guarda la config antes de enviar para que el backend use los toggles actuales. */
  const handleEnviosMasivosPrueba = async () => {
    if (!modoPruebas) return
    try {
      setEnviandoMasivo(true)
      const payload: ConfigEnvioCompleta = {
        ...configEnvios,
        modo_pruebas: true,
        emails_pruebas: emailsPruebas.filter((e) => e?.trim()),
        email_pruebas: emailsPruebas[0]?.trim() || '',
      }
      await emailConfigService.actualizarConfiguracionEnvios(payload)
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY_ENVIOS })
      const res = await notificacionService.enviarTodasNotificaciones()
      if (res?.en_proceso && res?.mensaje) {
        toast.success(res.mensaje, { duration: 8000 })
      } else {
        const { enviados, fallidos, sin_email, omitidos_config } = res ?? {}
        if ((enviados ?? 0) + (fallidos ?? 0) + (sin_email ?? 0) === 0 && (omitidos_config ?? 0) > 0) {
          toast.warning(`Ningún envío: ${omitidos_config} omitidos (activa Envío en al menos una pestaña y vuelve a intentar).`)
        } else {
          toast.success(`Envíos masivos prueba: ${enviados ?? 0} enviados, ${fallidos ?? 0} fallidos, ${sin_email ?? 0} sin email.`)
        }
      }
    } catch (error: unknown) {
      const detalle = getErrorDetail(error)
      toast.error(detalle || 'Error al ejecutar envíos masivos.')
    } finally {
      setEnviandoMasivo(false)
    }
  }

  if (cargando) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="text-center text-gray-500">
          <Clock className="h-8 w-8 mx-auto animate-pulse mb-2 text-blue-500" />
          <p>Cargando configuración...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <Settings className="h-5 w-5 text-blue-600" />
            Configuración por caso
          </CardTitle>
          <CardDescription>
            Asigna una plantilla a cada pestaña, activa el envío y define si incluir PDF anexo (carta cobranza) y documentos PDF fijos. Los documentos fijos se asignan por pestaña en Configuración → Plantillas → Documentos PDF anexos.
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Modo Prueba / Producción: un solo bloque, sin duplicar config */}
      <Card className={enModoPrueba ? 'border-amber-300 bg-amber-50/50' : 'border-emerald-200 bg-emerald-50/30'}>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            {enModoPrueba ? (
              <>
                <TestTube className="h-4 w-4 text-amber-600" />
                Modo prueba
              </>
            ) : (
              <>
                <Mail className="h-4 w-4 text-emerald-600" />
                Modo producción
              </>
            )}
          </CardTitle>
          <CardDescription>
            {enModoPrueba
              ? 'Todos los envíos van al correo de pruebas. Puedes activar o desactivar cada caso (Envío) para elegir a qué pestañas enviar.'
              : 'Los emails se envían al correo de cada cliente según la opción Envío de cada caso.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {modoPruebas && smtpConfigurado === false && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
              <TestTube className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-800">SMTP no configurado</p>
                <p className="text-sm text-red-700 mt-1">
                  Para enviar correos de prueba, configura el servidor SMTP en{' '}
                  <Link to="/configuracion?tab=email" className="underline font-medium">Configuración → Email</Link>.
                </p>
              </div>
            </div>
          )}
          {/* Toggle Modo Prueba */}
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Prueba</span>
            <button
              type="button"
              role="switch"
              aria-checked={modoPruebas}
              onClick={() => setModoPruebas(!modoPruebas)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${
                modoPruebas ? 'bg-amber-500' : 'bg-emerald-600'
              }`}
            >
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow ${modoPruebas ? 'translate-x-5' : 'translate-x-1'}`} />
            </button>
            <span className="text-sm text-gray-600">{modoPruebas ? 'Activado (solo correo de pruebas)' : 'Desactivado (envío a clientes)'}</span>
          </div>

          {/* Correos de Prueba: hasta 2 que reciben notificaciones en modo prueba */}
          <div className="space-y-3">
            <p className="text-xs text-gray-500">Hasta 2 correos que recibirán las notificaciones en modo prueba.</p>
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700 whitespace-nowrap w-40">Correo pruebas 1</label>
              <Input
                type="email"
                placeholder="ejemplo@correo.com"
                value={emailsPruebas[0]}
                onChange={(e) => setEmailsPruebas((prev) => [e.target.value, prev[1]])}
                className="max-w-xs h-9 bg-white"
                maxLength={120}
              />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700 whitespace-nowrap w-40">Correo pruebas 2</label>
              <Input
                type="email"
                placeholder="ejemplo2@correo.com"
                value={emailsPruebas[1]}
                onChange={(e) => setEmailsPruebas((prev) => [prev[0], e.target.value])}
                className="max-w-xs h-9 bg-white"
                maxLength={120}
              />
            </div>
          </div>

          {/* En modo prueba: envío manual plantilla predeterminada + envíos masivos prueba */}
          {modoPruebas && (emailsPruebas[0]?.trim() || emailsPruebas[1]?.trim()) && (
            <div className="pt-4 border-t border-amber-200 space-y-3">
              <p className="text-sm text-gray-600">
                Envía un correo de ejemplo con la <strong>plantilla predeterminada</strong> a los correos de pruebas 1 y 2.
              </p>
              <Button
                onClick={handleEnviarNotificacionesPrueba}
                disabled={enviandoPruebaIndice !== null || smtpConfigurado === false}
                className="w-full bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 disabled:opacity-50 text-white font-semibold py-2 h-auto flex items-center justify-center gap-2 rounded-lg transition-all"
              >
                <Mail className="h-5 w-5" />
                {enviandoPruebaIndice !== null ? 'Enviando...' : 'Enviar notificaciones'}
              </Button>
              <p className="text-sm text-gray-600 mt-2">
                Envíos masivos: envía ahora un correo por cada cliente que requiera notificación; todos van al correo de pruebas (no a clientes).
              </p>
              <Button
                onClick={handleEnviosMasivosPrueba}
                disabled={enviandoMasivo || smtpConfigurado === false}
                variant="outline"
                className="w-full border-amber-400 text-amber-800 bg-amber-50 hover:bg-amber-100 disabled:opacity-50 font-semibold py-2 h-auto flex items-center justify-center gap-2 rounded-lg"
              >
                <Mail className="h-5 w-5" />
                {enviandoMasivo ? 'Enviando...' : 'Envíos masivos prueba'}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left py-3 px-4 font-semibold text-gray-700">Caso</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700">Plantilla</th>
              <th className="text-center py-3 px-4 font-semibold text-gray-700 w-20">Envío</th>
              <th className="text-center py-3 px-4 font-semibold text-gray-700 w-20" title="Incluir Carta_Cobranza.pdf (generada desde Configuración → Plantillas → Plantilla anexo PDF). Desmarca para usar solo tus PDFs subidos en Documentos PDF anexos." aria-label="Incluir carta cobranza PDF">PDF</th>
              <th className="text-center py-3 px-4 font-semibold text-gray-700 w-20" title="Incluir documentos PDF fijos asignados a esta pestaña (Configuración → Plantillas → Documentos PDF anexos)" aria-label="Incluir documentos PDF fijos de esta pestaña">Adj.</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700 w-32">Opciones</th>
            </tr>
          </thead>
          <tbody>
            {CRITERIOS.map(({ tipo, label, categoria, color }) => {
              const config = getConfig(tipo)
              const col = COLORES[color]
              const listaPlantillas = plantillasPorTipo(tipo)
              return (
                <tr key={tipo} className={`border-b border-gray-100 ${col.bg}`}>
                  <td className="py-3 px-4">
                    <span className={`font-medium ${col.text}`}>{label}</span>
                    <span className={`block text-xs ${col.accent} opacity-80`}>{categoria}</span>
                  </td>
                  <td className="py-3 px-4">
                    <Select
                      value={config.plantilla_id ? String(config.plantilla_id) : '__ninguna__'}
                      onValueChange={(v) => setConfig(tipo, { plantilla_id: v === '__ninguna__' ? null : parseInt(v, 10) })}
                      disabled={!config.habilitado}
                    >
                      <SelectTrigger className="w-full max-w-xs bg-white border-gray-200">
                        <SelectValue placeholder="Seleccionar" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__ninguna__">Texto por defecto</SelectItem>
                        {listaPlantillas.map((p) => (
                          <SelectItem key={p.id} value={String(p.id)}>{p.nombre || `#${p.id}`}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {listaPlantillas.length === 0 && (
                      <p className="text-xs text-gray-500 mt-1">Crea plantillas en <Link to="/configuracion?tab=plantillas" className="text-blue-600 hover:underline">Configuración → Plantillas</Link></p>
                    )}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <button
                      type="button"
                      onClick={() => toggleEnvio(tipo)}
                      title={config.habilitado ? 'Desactivar envío' : 'Activar envío'}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${
                        config.habilitado ? 'bg-blue-600' : 'bg-gray-300'
                      }`}
                    >
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow ${config.habilitado ? 'translate-x-5' : 'translate-x-1'}`} />
                    </button>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <input
                      type="checkbox"
                      checked={config.incluir_pdf_anexo === true}
                      onChange={() => setConfig(tipo, { incluir_pdf_anexo: !config.incluir_pdf_anexo })}
                      disabled={!config.habilitado}
                      title="Incluir Carta_Cobranza.pdf (Plantilla anexo PDF). Desmarca para enviar solo tus PDFs de Documentos PDF anexos."
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </td>
                  <td className="py-3 px-4 text-center">
                    <input
                      type="checkbox"
                      checked={config.incluir_adjuntos_fijos !== false}
                      onChange={() => setConfig(tipo, { incluir_adjuntos_fijos: !(config.incluir_adjuntos_fijos !== false) })}
                      disabled={!config.habilitado}
                      title="Incluir documentos PDF fijos (pestaña 3: Documentos PDF anexos)"
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </td>
                  <td className="py-3 px-4">
                    <details className="group">
                      <summary className="cursor-pointer text-blue-600 hover:text-blue-800 text-xs font-medium list-none">
                        Hora y CCO (1–3)
                      </summary>
                      <div className="mt-2 space-y-2 pl-0">
                        <label className="text-xs text-gray-500 block">Hora envío</label>
                        <Input
                          type="time"
                          value={config.programador || HORA_DEFAULT}
                          onChange={(e) => setConfig(tipo, { programador: e.target.value })}
                          disabled={!config.habilitado}
                          className="h-8 text-xs bg-white w-28"
                        />
                        <label className="text-xs text-gray-500 block pt-1">CCO (copia oculta)</label>
                        {[0, 1, 2].map((i) => (
                          <div key={i} className="flex gap-1 items-center">
                            <span className="text-xs text-gray-500 w-8">CCO {i + 1}</span>
                            <Input
                              type="email"
                              placeholder={`CCO ${i + 1}`}
                              value={config.cco[i] || ''}
                              onChange={(e) => actualizarCCO(tipo, i, e.target.value)}
                              className="h-8 text-xs flex-1 bg-white"
                              disabled={!config.habilitado}
                            />
                            {config.cco[i] && (
                              <Button type="button" variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={() => eliminarCCO(tipo, i)}>
                                <X className="h-3 w-3" />
                              </Button>
                            )}
                          </div>
                        ))}
                      </div>
                    </details>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

        <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
        <div className="flex items-center gap-3 text-sm text-gray-600">
          <Link to="/configuracion?tab=email" className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800">
            <Mail className="h-4 w-4" /> Email (SMTP)
          </Link>
          <Link to="/configuracion?tab=plantillas" className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800">
            <FileText className="h-4 w-4" /> Crear/editar plantillas
          </Link>
          {ultimoGuardado && (
            <span className="inline-flex items-center gap-1 text-emerald-600" title={`Guardado a las ${ultimoGuardado.toLocaleTimeString()}`}>
              <CheckCircle className="h-4 w-4" /> Guardado
            </span>
          )}
        </div>
        <Button onClick={guardarConfiguracionEnvios} disabled={guardandoEnvios} className="bg-blue-600 hover:bg-blue-700">
          {guardandoEnvios ? 'Guardando...' : 'Guardar'}
        </Button>
      </div>
    </div>
  )
}
