import { useState, useEffect, useRef } from 'react'

import { Link } from 'react-router-dom'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../../components/ui/card'

import {
  Settings,
  Mail,
  FileText,
  Clock,
  X,
  TestTube,
  CheckCircle,
  RefreshCw,
} from 'lucide-react'

import { emailConfigService } from '../../services/notificacionService'

import {
  notificacionService,
  type EnvioPruebaPaqueteResponse,
  type DiagnosticoPaquetePruebaResponse,
  type NotificacionPlantilla,
} from '../../services/notificacionService'

import { getErrorDetail } from '../../types/errors'

import { Button } from '../../components/ui/button'

import { Input } from '../../components/ui/input'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'

import { toast } from 'sonner'

import { NOTIFICACIONES_QUERY_KEYS } from '../../queries/notificaciones'

/** Claves reservadas en la config (no son tipos de caso) */

const CLAVES_GLOBALES = [
  'modo_pruebas',
  'email_pruebas',
  'emails_pruebas',
] as const

/** Tipo de configuración por criterio (habilitado, cco, plantilla opcional, programador) */

export type ConfigEnvioItem = {
  habilitado: boolean

  cco: string[]

  plantilla_id?: number | null

  programador?: string

  /** Incluir PDF anexo (pestaña 2: Plantilla anexo PDF). Si true, Carta_Cobranza.pdf se agrega OBLIGATORIAMENTE al email. */

  incluir_pdf_anexo?: boolean

  /** Incluir documentos PDF fijos (pestaña 3: Documentos PDF anexos). Si true, se agregan OBLIGATORIAMENTE al email. */

  incluir_adjuntos_fijos?: boolean
}

/** Respuesta de la API: config por tipo + modo_pruebas y email_pruebas (un solo objeto, sin duplicar) */

export type ConfigEnvioCompleta = Record<
  string,
  ConfigEnvioItem | boolean | string | string[]
>

/** Criterios de notificación (tipo → label). Exportado para uso en Plantillas / vinculación PDF. */

/**
 * Casos con envio por pestaña / lote (scheduler). COBRANZA no aplica: la carta PDF se arma
 * desde plantillas tipo COBRANZA vinculadas a estos casos, no hay fila de envío separada.
 */
export const CRITERIOS_ENVIO_PANEL: {
  tipo: string
  label: string
  categoria: string
  color: 'blue' | 'green' | 'orange' | 'red' | 'slate'
}[] = [
  {
    tipo: 'PAGO_1_DIA_ATRASADO',
    label: 'Día siguiente al vencimiento',
    categoria: 'Retrasada',
    color: 'orange',
  },

  {
    tipo: 'PAGO_3_DIAS_ATRASADO',
    label: '3 días de retraso',
    categoria: 'Retrasada',
    color: 'orange',
  },

  {
    tipo: 'PAGO_5_DIAS_ATRASADO',
    label: '5 días atrasado',
    categoria: 'Retrasada',
    color: 'orange',
  },

  {
    tipo: 'PREJUDICIAL',
    label: 'Prejudicial',
    categoria: 'Prejudicial',
    color: 'red',
  },
]

/** Etiquetas para vinculación PDF + compat; incluye COBRANZA (solo plantilla, sin fila envío). */
export const CRITERIOS_ETIQUETAS: {
  tipo: string
  label: string
  categoria: string
  color: 'blue' | 'green' | 'orange' | 'red' | 'slate'
}[] = [
  ...CRITERIOS_ENVIO_PANEL,
  {
    tipo: 'COBRANZA',
    label: 'Carta de cobranza (plantilla tipo cobranza)',
    categoria: 'Cobranza',
    color: 'red',
  },
]

/** @deprecated Usar CRITERIOS_ENVIO_PANEL o CRITERIOS_ETIQUETAS según contexto */
export const CRITERIOS = CRITERIOS_ETIQUETAS

const COLORES = {
  blue: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-900',
    accent: 'text-blue-600',
  },

  green: {
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    text: 'text-emerald-900',
    accent: 'text-emerald-600',
  },

  orange: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-900',
    accent: 'text-amber-600',
  },

  red: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-900',
    accent: 'text-red-600',
  },

  slate: {
    bg: 'bg-slate-50',
    border: 'border-slate-200',
    text: 'text-slate-900',
    accent: 'text-slate-600',
  },
} as const

const HORA_DEFAULT = '04:00'

function defaultEnvio(): ConfigEnvioItem {
  return {
    habilitado: true,
    cco: [],
    programador: HORA_DEFAULT,
    incluir_pdf_anexo: true,
    incluir_adjuntos_fijos: true,
  }
}

/** Normaliza la respuesta de la API en estado listo para el componente (carga única y clara). */

function normalizeConfigFromApi(raw: ConfigEnvioCompleta | null): {
  modoPruebas: boolean

  emailsPruebas: [string, string]

  configEnvios: Record<string, ConfigEnvioItem>
} {
  const data = raw || {}

  const modoPruebas =
    data.modo_pruebas === true ||
    data.modo_pruebas === 'true' ||
    String(data.modo_pruebas || '').toLowerCase() === 'true'

  let emailsPruebas: [string, string] = ['', '']

  if (Array.isArray(data.emails_pruebas)) {
    emailsPruebas = [data.emails_pruebas[0] ?? '', data.emails_pruebas[1] ?? '']
  } else if (typeof data.email_pruebas === 'string') {
    emailsPruebas = [data.email_pruebas, '']
  }

  const sinGlobales = { ...data }

  CLAVES_GLOBALES.forEach(k => delete sinGlobales[k])

  return {
    modoPruebas,
    emailsPruebas,
    configEnvios: sinGlobales as Record<string, ConfigEnvioItem>,
  }
}

export function ConfiguracionNotificaciones() {
  const [configEnvios, setConfigEnvios] = useState<
    Record<string, ConfigEnvioItem>
  >({})

  const [modoPruebas, setModoPruebas] = useState(false)

  const [emailsPruebas, setEmailsPruebas] = useState<[string, string]>(['', ''])

  const [guardandoEnvios, setGuardandoEnvios] = useState(false)

  const [ultimoGuardado, setUltimoGuardado] = useState<Date | null>(null)

  const [plantillas, setPlantillas] = useState<NotificacionPlantilla[]>([])

  const [enviandoPruebaIndice, setEnviandoPruebaIndice] = useState<
    number | null
  >(null)

  const [enviandoMasivo, setEnviandoMasivo] = useState(false)

  const [tipoPruebaPaquete, setTipoPruebaPaquete] = useState<string>(
    CRITERIOS_ENVIO_PANEL[0].tipo
  )

  const [diagnosticoPaquete, setDiagnosticoPaquete] =
    useState<DiagnosticoPaquetePruebaResponse | null>(null)

  const [diagnosticoCargando, setDiagnosticoCargando] = useState(false)

  const guardandoRef = useRef(false)

  const queryClient = useQueryClient()

  const {
    data: dataEnvios,
    isLoading: loadingEnvios,
    isError: errorEnvios,
  } = useQuery({
    queryKey: NOTIFICACIONES_QUERY_KEYS.envios,

    queryFn: () =>
      emailConfigService.obtenerConfiguracionEnvios() as Promise<ConfigEnvioCompleta>,

    staleTime: 1 * 60 * 1000,
  })

  const { data: plantillasList, isLoading: loadingPlantillas } = useQuery({
    queryKey: NOTIFICACIONES_QUERY_KEYS.plantillas,

    queryFn: () => notificacionService.listarPlantillas(undefined, false),

    staleTime: 1 * 60 * 1000,

    placeholderData: [] as NotificacionPlantilla[],
  })

  const {
    data: estadoEmailSmtp,
    isPending: cargandoEstadoSmtp,
    isError: errorEstadoSmtp,
  } = useQuery({
    queryKey: NOTIFICACIONES_QUERY_KEYS.emailEstado,

    queryFn: () => emailConfigService.verificarEstadoConfiguracionEmail(),

    enabled: modoPruebas,

    staleTime: 60 * 1000,

    refetchOnWindowFocus: false,

    refetchOnMount: false,
  })

  const {
    data: ultimoBatchResp,
    refetch: refetchUltimoBatch,
    isFetching: cargandoUltimoBatch,
  } = useQuery({
    queryKey: NOTIFICACIONES_QUERY_KEYS.envioBatchUltimo,

    queryFn: () => notificacionService.obtenerUltimoEnvioBatch(),

    staleTime: 20 * 1000,
  })

  /** null = pendiente o error de red (no aviso falso); false = SMTP incompleto; true = OK (v2 o legado). */

  const smtpConfigurado: boolean | null = !modoPruebas
    ? null
    : errorEstadoSmtp
      ? null
      : cargandoEstadoSmtp
        ? null
        : estadoEmailSmtp?.configurada === true
          ? true
          : false

  const cargando = loadingEnvios || loadingPlantillas

  useEffect(() => {
    if (dataEnvios != null) {
      const {
        modoPruebas: mp,
        emailsPruebas: ep,
        configEnvios: ce,
      } = normalizeConfigFromApi(dataEnvios)

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

  const getConfig = (tipo: string): ConfigEnvioItem => {
    const c = configEnvios[tipo]

    if (!c) return defaultEnvio()

    return {
      habilitado: c.habilitado !== false,

      cco: Array.isArray(c.cco) ? c.cco : [],

      plantilla_id: c.plantilla_id ?? null,

      programador: c.programador ?? HORA_DEFAULT,

      // PDF = Carta_Cobranza (pestaña 2). Por defecto sí (requerido con paquete estricto en backend).

      incluir_pdf_anexo: c.incluir_pdf_anexo !== false,

      incluir_adjuntos_fijos: c.incluir_adjuntos_fijos !== false,
    }
  }

  const setConfig = (tipo: string, upd: Partial<ConfigEnvioItem>) => {
    setConfigEnvios(prev => {
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

    if (modoPruebas && (emailsPruebas[0]?.trim() || emailsPruebas[1]?.trim())) {
      const mal = [emailsPruebas[0], emailsPruebas[1]]
        .map(e => (e || '').trim())
        .filter(e => e && !esEmailValido(e))
      if (mal.length > 0) {
        toast.error(
          `Correo(s) de prueba incompleto(s): ${mal.join(', ')}. Use formato nombre@dominio.com (con punto en el dominio, ej. .com).`
        )
        return
      }
    }

    guardandoRef.current = true

    setGuardandoEnvios(true)

    try {
      const payload: ConfigEnvioCompleta = {
        ...configEnvios,

        modo_pruebas: modoPruebas,

        emails_pruebas: emailsPruebas.filter(e => e?.trim()),

        email_pruebas: emailsPruebas[0]?.trim() || '',
      }

      CRITERIOS_ENVIO_PANEL.forEach(({ tipo }) => {
        const c = getConfig(tipo)

        ;(payload as Record<string, ConfigEnvioItem>)[tipo] = {
          ...c,

          incluir_pdf_anexo: c.incluir_pdf_anexo !== false,

          incluir_adjuntos_fijos: c.incluir_adjuntos_fijos !== false,
        }
      })

      await emailConfigService.actualizarConfiguracionEnvios(payload)

      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.envios,
      })

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
    plantillas.filter(p => p.tipo === tipo)

  const esEmailValido = (e: string) =>
    /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test((e || '').trim())

  /** En modo prueba el envío usa solo plantilla predeterminada (ejemplo) y envía a correo de pruebas 1 y 2. */

  const handleEnviarNotificacionesPrueba = async () => {
    const destinos = [
      emailsPruebas[0]?.trim(),
      emailsPruebas[1]?.trim(),
    ].filter(Boolean) as string[]

    if (!modoPruebas || destinos.length === 0) {
      toast.error('Configura al menos un correo de pruebas para enviar.')

      return
    }

    const invalidos = destinos.filter(e => !esEmailValido(e))

    if (invalidos.length > 0) {
      toast.error(
        `Correo(s) no valido(s): ${invalidos.join(', ')}. Usa formato usuario@dominio.com`
      )

      return
    }

    try {
      setEnviandoPruebaIndice(0)

      const estadoEmail =
        await emailConfigService.verificarEstadoConfiguracionEmail()

      if (!estadoEmail?.configurada) {
        const problemas =
          estadoEmail?.problemas?.join('. ') ||
          'servidor SMTP, usuario y contrasena'

        toast.error(
          `Configura el email SMTP antes de enviar pruebas: ${problemas} Ve a Configuracion > Email.`,

          { duration: 6000 }
        )

        setEnviandoPruebaIndice(null)

        return
      }

      const resultado: EnvioPruebaPaqueteResponse =
        await notificacionService.enviarPruebaPaqueteCompleta({
          tipo: tipoPruebaPaquete,
          destinos,
        })

      const enviados = resultado.enviados ?? 0
      const fallidos = resultado.fallidos ?? 0

      if (enviados > 0 && fallidos === 0) {
        toast.success(
          resultado.mensaje ||
            `Prueba enviada: plantilla + Carta PDF + PDFs fijos a ${destinos.length} correo(s).`
        )
      } else if (enviados > 0) {
        toast.warning(
          `Enviado con advertencias (fallidos=${fallidos}). Revise SMTP y adjuntos en pestañas 2 y 3.`
        )
      } else {
        const op = resultado.omitidos_paquete_incompleto ?? 0
        const oc = resultado.omitidos_config ?? 0
        let msg =
          resultado.mensaje ||
          'No se pudo enviar la prueba. Revise que exista un cliente en el criterio y que los PDFs esten configurados.'
        if (op > 0) {
          msg =
            'Paquete incompleto: falta Carta PDF valida y/o PDF fijo (pestana 3 o adjunto global). En Render use disco persistente. Emergencia: NOTIFICACIONES_PAQUETE_ESTRICTO=false.'
        } else if (oc > 0) {
          msg = `Ningun envio: active Envio en la pestana del caso (${oc} omitidos por configuracion).`
        }
        toast.error(msg, { duration: 10000 })
      }
    } catch (error: unknown) {
      const detalle = getErrorDetail(error)

      const mensaje =
        detalle ||
        (error as Error)?.message ||
        'Error al enviar el correo de prueba'

      toast.error(mensaje, { duration: 5000 })
    } finally {
      setEnviandoPruebaIndice(null)
    }
  }

  const handleDiagnosticoPaquete = async () => {
    try {
      setDiagnosticoCargando(true)
      const d =
        await notificacionService.diagnosticoPaquetePrueba(tipoPruebaPaquete)
      setDiagnosticoPaquete(d)
      if (d.ok && d.paquete_completo) {
        toast.success(
          'Diagnostico: paquete listo (plantilla + Carta PDF + PDFs fijos). Puede enviar la prueba con confianza.',
          { duration: 8000 }
        )
      } else {
        toast.warning(
          `Diagnostico: no listo (${d.motivo || d.paquete_motivo || 'revisar'}). Revise PDFs en pestanas 2 y 3 y volumen en Render. Opcional: NOTIFICACIONES_PAQUETE_RELAX_SOLO_PRUEBA_DESTINO=true solo para prueba forzada.`,
          { duration: 14000 }
        )
      }
    } catch (e: unknown) {
      const detalle = getErrorDetail(e)
      toast.error(detalle || 'Error al ejecutar diagnostico')
    } finally {
      setDiagnosticoCargando(false)
    }
  }

  const handleEnviosMasivosPrueba = async () => {
    if (!modoPruebas) return

    const primero = (emailsPruebas[0] || '').trim()
    if (!primero) {
      toast.error(
        'Indica al menos Correo pruebas 1 (destino del lote en modo prueba).'
      )
      return
    }
    if (!esEmailValido(primero)) {
      toast.error(
        `Correo pruebas 1 no válido: "${primero}". Debe incluir dominio con punto (ej. notificaciones@rapicreditca.com).`
      )
      return
    }
    const segundo = (emailsPruebas[1] || '').trim()
    if (segundo && !esEmailValido(segundo)) {
      toast.error(
        `Correo pruebas 2 no válido. Use formato usuario@dominio.com o déjelo vacío.`
      )
      return
    }

    try {
      setEnviandoMasivo(true)

      const payload: ConfigEnvioCompleta = {
        ...configEnvios,

        modo_pruebas: true,

        emails_pruebas: emailsPruebas.filter(e => e?.trim()),

        email_pruebas: emailsPruebas[0]?.trim() || '',
      }

      await emailConfigService.actualizarConfiguracionEnvios(payload)

      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.envios,
      })

      const res = await notificacionService.enviarTodasNotificaciones()

      if (res?.en_proceso && res?.mensaje) {
        await queryClient.invalidateQueries({
          queryKey: NOTIFICACIONES_QUERY_KEYS.envioBatchUltimo,
        })
        setTimeout(() => {
          void queryClient.invalidateQueries({
            queryKey: NOTIFICACIONES_QUERY_KEYS.envioBatchUltimo,
          })
        }, 8000)
        toast.success(
          `${res.mensaje} En unos segundos use Actualizar en Ultimo envio masivo para ver enviados y omitidos por paquete. Si enviados=0, revise PDFs en pestana 3 y disco persistente en Render.`,
          { duration: 14000 }
        )
      } else {
        const { enviados, fallidos, sin_email, omitidos_config } = res ?? {}

        if (
          (enviados ?? 0) + (fallidos ?? 0) + (sin_email ?? 0) === 0 &&
          (omitidos_config ?? 0) > 0
        ) {
          toast.warning(
            `Ningún envío: ${omitidos_config} omitidos (activa Envío en al menos una pestaña y vuelve a intentar).`
          )
        } else {
          toast.success(
            `Envíos masivos prueba: ${enviados ?? 0} enviados, ${fallidos ?? 0} fallidos, ${sin_email ?? 0} sin email.`
          )
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
          <Clock className="mx-auto mb-2 h-8 w-8 animate-pulse text-blue-500" />

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
            Cada correo al cliente (modo estricto) combina tres piezas: (1)
            plantilla de correo HTML con variables; (2) PDF de carta con
            variables (Carta_Cobranza.pdf); (3) PDFs fijos de anexos, siempre
            junto al PDF variable. Solo aparecen casos con envio por pestaña
            (retrasadas y prejudicial). Las plantillas tipo carta de cobranza
            (COBRANZA) se crean en Plantillas y se eligen aqui por caso. El
            backend exige plantilla activa, PDF variable valido y al menos un
            PDF fijo adicional (pestaña Documentos PDF anexos / adjunto global).
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Modo Prueba / Producción: un solo bloque, sin duplicar config */}

      <Card
        className={
          enModoPrueba
            ? 'border-amber-300 bg-amber-50/50'
            : 'border-emerald-200 bg-emerald-50/30'
        }
      >
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
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
            <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3">
              <TestTube className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />

              <div>
                <p className="text-sm font-medium text-red-800">
                  SMTP no configurado
                </p>

                <p className="mt-1 text-sm text-red-700">
                  Para enviar correos de prueba, configura el servidor SMTP en{' '}
                  <Link
                    to="/configuracion?tab=email"
                    className="font-medium underline"
                  >
                    Configuración → Email
                  </Link>
                  .
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
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white shadow ${modoPruebas ? 'translate-x-5' : 'translate-x-1'}`}
              />
            </button>

            <span className="text-sm text-gray-600">
              {modoPruebas
                ? 'Activado (solo correo de pruebas)'
                : 'Desactivado (envío a clientes)'}
            </span>
          </div>

          {/* Correos de Prueba: hasta 2 que reciben notificaciones en modo prueba */}

          <div className="space-y-3">
            <p className="text-xs text-gray-500">
              Hasta 2 correos que recibirán las notificaciones en modo prueba.
            </p>

            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-2">
              <label className="w-40 whitespace-nowrap text-sm font-medium text-gray-700">
                Correo pruebas 1
              </label>

              <div className="flex max-w-md flex-col gap-1">
                <Input
                  type="email"
                  placeholder="ejemplo@correo.com"
                  value={emailsPruebas[0]}
                  onChange={e =>
                    setEmailsPruebas(prev => [e.target.value, prev[1]])
                  }
                  className="h-9 max-w-xs bg-white"
                  maxLength={120}
                />
                {modoPruebas &&
                  emailsPruebas[0]?.trim() &&
                  !esEmailValido(emailsPruebas[0].trim()) && (
                    <p className="text-xs text-amber-800">
                      Falta un dominio válido (debe haber un punto después de @,
                      ej. .com). Sin eso el servidor no puede entregar el
                      correo.
                    </p>
                  )}
              </div>
            </div>

            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-2">
              <label className="w-40 whitespace-nowrap text-sm font-medium text-gray-700">
                Correo pruebas 2
              </label>

              <div className="flex max-w-md flex-col gap-1">
                <Input
                  type="email"
                  placeholder="ejemplo2@correo.com"
                  value={emailsPruebas[1]}
                  onChange={e =>
                    setEmailsPruebas(prev => [prev[0], e.target.value])
                  }
                  className="h-9 max-w-xs bg-white"
                  maxLength={120}
                />
                {modoPruebas &&
                  emailsPruebas[1]?.trim() &&
                  !esEmailValido(emailsPruebas[1].trim()) && (
                    <p className="text-xs text-amber-800">
                      Dominio incompleto; corrija o deje vacío.
                    </p>
                  )}
              </div>
            </div>

            {modoPruebas && (
              <p className="text-xs text-gray-600">
                Pestaña 1 = cuerpo HTML del correo; pestaña 2 = carta PDF;
                pestaña 3 = PDF fijo por caso (ej. «Día siguiente al venc.» →{' '}
                <code className="rounded bg-gray-100 px-1">dias_1_retraso</code>
                ). El panel solo enlaza plantilla y flags: el archivo de la
                pestaña 3 debe existir en el disco del servidor (si el hosting
                borra archivos al desplegar, vuelva a subir el PDF o use volumen
                persistente).
              </p>
            )}
          </div>

          {/* En modo prueba: envío manual plantilla predeterminada + envíos masivos prueba */}

          {modoPruebas &&
            (emailsPruebas[0]?.trim() || emailsPruebas[1]?.trim()) && (
              <div className="space-y-3 border-t border-amber-200 pt-4">
                <p className="text-sm text-gray-600">
                  Prueba con el mismo contenido que producción: cuerpo desde la
                  plantilla vinculada en la tabla (pestaña 1),{' '}
                  <strong>Carta_Cobranza.pdf</strong> (pestaña 2) y PDF(s) fijos
                  (pestaña 3). Elija el criterio de caso:
                </p>

                <div className="flex max-w-md flex-col gap-1">
                  <label className="text-xs font-medium text-gray-600">
                    Criterio (tipo de envío)
                  </label>
                  <Select
                    value={tipoPruebaPaquete}
                    onValueChange={v => setTipoPruebaPaquete(v)}
                  >
                    <SelectTrigger className="border-gray-200 bg-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CRITERIOS_ENVIO_PANEL.map(({ tipo, label }) => (
                        <SelectItem key={tipo} value={tipo}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void handleDiagnosticoPaquete()}
                  disabled={
                    diagnosticoCargando ||
                    enviandoPruebaIndice !== null ||
                    enviandoMasivo ||
                    smtpConfigurado === false
                  }
                  className="flex h-auto w-full items-center justify-center gap-2 rounded-lg py-2"
                >
                  {diagnosticoCargando
                    ? 'Diagnosticando...'
                    : 'Diagnosticar paquete (sin enviar correo)'}
                </Button>

                {diagnosticoPaquete && (
                  <pre className="mt-2 max-h-48 overflow-auto rounded border border-gray-200 bg-gray-50 p-2 text-left text-xs text-gray-800">
                    {JSON.stringify(diagnosticoPaquete, null, 2)}
                  </pre>
                )}

                <Button
                  onClick={handleEnviarNotificacionesPrueba}
                  disabled={
                    diagnosticoCargando ||
                    enviandoPruebaIndice !== null ||
                    smtpConfigurado === false
                  }
                  className="flex h-auto w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-green-500 to-emerald-600 py-2 font-semibold text-white transition-all hover:from-green-600 hover:to-emerald-700 disabled:opacity-50"
                >
                  <Mail className="h-5 w-5" />

                  {enviandoPruebaIndice !== null
                    ? 'Enviando...'
                    : 'Enviar notificaciones'}
                </Button>

                <p className="mt-2 text-sm text-gray-600">
                  Un correo de prueba a los destinos configurados arriba, con la
                  plantilla, la carta en PDF y los PDFs fijos del criterio
                  elegido (no recorre todos los clientes).
                </p>

                <Button
                  onClick={handleEnviosMasivosPrueba}
                  disabled={
                    enviandoMasivo ||
                    smtpConfigurado === false ||
                    diagnosticoCargando
                  }
                  variant="outline"
                  className="flex h-auto w-full items-center justify-center gap-2 rounded-lg border-amber-400 bg-amber-50 py-2 font-semibold text-amber-800 hover:bg-amber-100 disabled:opacity-50"
                >
                  <Mail className="h-5 w-5" />

                  {enviandoMasivo ? 'Enviando...' : 'Envíos masivos prueba'}
                </Button>

                <p className="mt-2 text-sm text-gray-600">
                  Envíos masivos: envía ahora un correo por cada cliente que
                  requiera notificación; todos van al correo de pruebas (no a
                  clientes).
                </p>
              </div>
            )}
        </CardContent>
      </Card>

      <Card className="border-slate-200">
        <CardHeader className="pb-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="text-base">Último envío masivo</CardTitle>

            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-1"
              disabled={cargandoUltimoBatch}
              onClick={() => void refetchUltimoBatch()}
            >
              <RefreshCw
                className={`h-4 w-4 ${cargandoUltimoBatch ? 'animate-spin' : ''}`}
              />
              Actualizar
            </Button>
          </div>

          <CardDescription className="text-xs">
            Resultado del último «Enviar todas» (API) o del programador 01:00
            (Caracas). Útil cuando la petición masiva responde 202 sin cuerpo.
          </CardDescription>
        </CardHeader>

        <CardContent className="text-sm">
          {(() => {
            const u = ultimoBatchResp?.ultimo as
              | Record<string, unknown>
              | null
              | undefined

            if (u == null) {
              return (
                <p className="text-gray-500">
                  Aún no hay ningún resultado guardado en el servidor.
                </p>
              )
            }

            if (u.omitido === true) {
              return (
                <p className="text-amber-800">
                  Omitido: {String(u.omitido_motivo ?? '-')} (
                  {String(u.origen ?? '')})
                </p>
              )
            }

            return (
              <dl className="grid gap-1 sm:grid-cols-2">
                <dt className="text-gray-500">Origen</dt>
                <dd>{String(u.origen ?? '-')}</dd>
                <dt className="text-gray-500">Fin (UTC)</dt>
                <dd className="break-all">{String(u.fin_utc ?? '-')}</dd>
                <dt className="text-gray-500">Enviados</dt>
                <dd>{String(u.enviados ?? 0)}</dd>
                <dt className="text-gray-500">Fallidos</dt>
                <dd>{String(u.fallidos ?? 0)}</dd>
                <dt className="text-gray-500">Sin email</dt>
                <dd>{String(u.sin_email ?? 0)}</dd>
                <dt className="text-gray-500">Omitidos config</dt>
                <dd>{String(u.omitidos_config ?? 0)}</dd>
                <dt className="text-gray-500">Omitidos paquete</dt>
                <dd>{String(u.omitidos_paquete_incompleto ?? 0)}</dd>
                <dt className="text-gray-500">WhatsApp OK / fallo</dt>
                <dd>
                  {String(u.enviados_whatsapp ?? 0)} /{' '}
                  {String(u.fallidos_whatsapp ?? 0)}
                </dd>
                {u.error ? (
                  <>
                    <dt className="text-gray-500">Error</dt>
                    <dd className="col-span-2 break-words text-red-700">
                      {String(u.error)}
                    </dd>
                  </>
                ) : null}
              </dl>
            )
          })()}
        </CardContent>
      </Card>

      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                Caso
              </th>

              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                Plantilla
              </th>

              <th className="w-20 px-4 py-3 text-center font-semibold text-gray-700">
                Envío
              </th>

              <th
                className="w-20 px-4 py-3 text-center font-semibold text-gray-700"
                title="Pestaña 2: Carta_Cobranza.pdf. Obligatorio para enviar (junto con plantilla email y PDF fijo). Desactivar impide el envío en modo estricto."
                aria-label="Incluir carta cobranza PDF"
              >
                PDF
              </th>

              <th
                className="w-20 px-4 py-3 text-center font-semibold text-gray-700"
                title="Pestaña 3: PDFs fijos por caso + global. Obligatorio para enviar (junto con plantilla y carta PDF)."
                aria-label="Incluir documentos PDF fijos de esta pestaña"
              >
                Adj.
              </th>

              <th className="w-32 px-4 py-3 text-left font-semibold text-gray-700">
                Opciones
              </th>
            </tr>
          </thead>

          <tbody>
            {CRITERIOS_ENVIO_PANEL.map(({ tipo, label, categoria, color }) => {
              const config = getConfig(tipo)

              const col = COLORES[color]

              const listaPlantillas = plantillasPorTipo(tipo)

              return (
                <tr key={tipo} className={`border-b border-gray-100 ${col.bg}`}>
                  <td className="px-4 py-3">
                    <span className={`font-medium ${col.text}`}>{label}</span>

                    <span className={`block text-xs ${col.accent} opacity-80`}>
                      {categoria}
                    </span>
                  </td>

                  <td className="px-4 py-3">
                    <Select
                      value={
                        config.plantilla_id
                          ? String(config.plantilla_id)
                          : '__ninguna__'
                      }
                      onValueChange={v =>
                        setConfig(tipo, {
                          plantilla_id:
                            v === '__ninguna__' ? null : parseInt(v, 10),
                        })
                      }
                      disabled={!config.habilitado}
                    >
                      <SelectTrigger className="w-full max-w-xs border-gray-200 bg-white">
                        <SelectValue placeholder="Seleccionar" />
                      </SelectTrigger>

                      <SelectContent>
                        <SelectItem value="__ninguna__">
                          Texto por defecto
                        </SelectItem>

                        {listaPlantillas.map(p => (
                          <SelectItem key={p.id} value={String(p.id)}>
                            {p.nombre || `#${p.id}`}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {listaPlantillas.length === 0 && (
                      <p className="mt-1 text-xs text-gray-500">
                        Crea plantillas en{' '}
                        <Link
                          to="/configuracion?tab=plantillas"
                          className="text-blue-600 hover:underline"
                        >
                          Configuración → Plantillas
                        </Link>
                      </p>
                    )}
                  </td>

                  <td className="px-4 py-3 text-center">
                    <button
                      type="button"
                      onClick={() => toggleEnvio(tipo)}
                      title={
                        config.habilitado ? 'Desactivar envío' : 'Activar envío'
                      }
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 ${
                        config.habilitado ? 'bg-blue-600' : 'bg-gray-300'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow ${config.habilitado ? 'translate-x-5' : 'translate-x-1'}`}
                      />
                    </button>
                  </td>

                  <td className="px-4 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={config.incluir_pdf_anexo !== false}
                      onChange={() =>
                        setConfig(tipo, {
                          incluir_pdf_anexo: !config.incluir_pdf_anexo,
                        })
                      }
                      disabled={!config.habilitado}
                      title="Carta_Cobranza.pdf (plantilla PDF cobranza). El servidor exige este PDF y un PDF fijo para enviar; debe estar activado."
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </td>

                  <td className="px-4 py-3 text-center">
                    <input
                      type="checkbox"
                      checked={config.incluir_adjuntos_fijos !== false}
                      onChange={() =>
                        setConfig(tipo, {
                          incluir_adjuntos_fijos: !(
                            config.incluir_adjuntos_fijos !== false
                          ),
                        })
                      }
                      disabled={!config.habilitado}
                      title="PDFs fijos (global + por caso). El servidor exige al menos un PDF fijo valido ademas de la carta; no desactivar."
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </td>

                  <td className="px-4 py-3">
                    <details className="group">
                      <summary className="cursor-pointer list-none text-xs font-medium text-blue-600 hover:text-blue-800">
                        Hora y CCO (1-3)
                      </summary>

                      <div className="mt-2 space-y-2 pl-0">
                        <label className="block text-xs text-gray-500">
                          Hora envío
                        </label>

                        <Input
                          type="time"
                          value={config.programador || HORA_DEFAULT}
                          onChange={e =>
                            setConfig(tipo, { programador: e.target.value })
                          }
                          disabled={!config.habilitado}
                          className="h-8 w-28 bg-white text-xs"
                        />

                        <label className="block pt-1 text-xs text-gray-500">
                          CCO (copia oculta)
                        </label>

                        {[0, 1, 2].map(i => (
                          <div key={i} className="flex items-center gap-1">
                            <span className="w-8 text-xs text-gray-500">
                              CCO {i + 1}
                            </span>

                            <Input
                              type="email"
                              placeholder={`CCO ${i + 1}`}
                              value={config.cco[i] || ''}
                              onChange={e =>
                                actualizarCCO(tipo, i, e.target.value)
                              }
                              className="h-8 flex-1 bg-white text-xs"
                              disabled={!config.habilitado}
                            />

                            {config.cco[i] && (
                              <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 shrink-0"
                                onClick={() => eliminarCCO(tipo, i)}
                              >
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
          <Link
            to="/configuracion?tab=email"
            className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800"
          >
            <Mail className="h-4 w-4" /> Email (SMTP)
          </Link>

          <Link
            to="/configuracion?tab=plantillas"
            className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800"
          >
            <FileText className="h-4 w-4" /> Crear/editar plantillas
          </Link>

          {ultimoGuardado && (
            <span
              className="inline-flex items-center gap-1 text-emerald-600"
              title={`Guardado a las ${ultimoGuardado.toLocaleTimeString()}`}
            >
              <CheckCircle className="h-4 w-4" /> Guardado
            </span>
          )}
        </div>

        <Button
          onClick={guardarConfiguracionEnvios}
          disabled={guardandoEnvios}
          className="bg-blue-600 hover:bg-blue-700"
        >
          {guardandoEnvios ? 'Guardando...' : 'Guardar'}
        </Button>
      </div>
    </div>
  )
}
