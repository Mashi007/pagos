import { useState, useEffect, useRef, useMemo } from 'react'

import { Link, useSearchParams } from 'react-router-dom'

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

import { isRequestCanceled } from '../../utils/requestCanceled'

import { Button } from '../../components/ui/button'

import { Input } from '../../components/ui/input'

import { Textarea } from '../../components/ui/textarea'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select'

import { toast } from 'sonner'

import { NOTIFICACIONES_QUERY_KEYS } from '../../queries/notificaciones'

import { invalidateListasNotificacionesMora } from '../../constants/queryKeys'

import { hrefPlantillasConContexto } from '../../constants/notifPlantillaServicioContexto'

import { DocumentosPdfAnexos } from './DocumentosPdfAnexos'

/** Claves reservadas en la config (no son tipos de caso) */

const CLAVES_GLOBALES = [
  'modo_pruebas',
  'email_pruebas',
  'emails_pruebas',
] as const

const CCO_MAX = 3

/** Separa correos por coma, punto y coma o salto de linea (Enter; maximo CCO_MAX). */
function parsearCorreosCco(texto: string): string[] {
  return texto
    .split(/[\n,;]+/)
    .map(s => s.trim())
    .filter(Boolean)
    .slice(0, CCO_MAX)
}

/** Tipo de configuración por criterio (habilitado, cco, plantilla; programador solo persistido por compatibilidad) */

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

export type CampanaMasivaConfig = {
  id: string
  nombre: string
  habilitado: boolean
  plantilla_id?: number | null
  programador?: string
  dias_semana: number[]
  cco: string[]
}

/** Respuesta de la API: config por tipo + modo_pruebas y email_pruebas (un solo objeto, sin duplicar) */

export type ConfigEnvioCompleta = Record<
  string,
  ConfigEnvioItem | CampanaMasivaConfig[] | boolean | string | string[]
>

/** Criterios de notificación (tipo → label). Exportado para uso en Plantillas / vinculación PDF. */

type CriterioEnvioRow = {
  tipo: string
  label: string
  categoria: string
  color: 'blue' | 'green' | 'orange' | 'red' | 'slate'
}

/**
 * Tabla de envíos: una fila por caso (CCO por fila). Envíos solo manuales.
 * Alineado con los tipos que usa el backend (notificaciones_tabs).
 */
export const CRITERIOS_ENVIO_TABLA: CriterioEnvioRow[] = [
  {
    tipo: 'PAGO_5_DIAS_ANTES',
    label: 'Faltan 5 días al vencimiento',
    categoria: 'Por vencer',
    color: 'blue',
  },
  {
    tipo: 'PAGO_3_DIAS_ANTES',
    label: 'Faltan 3 días al vencimiento',
    categoria: 'Por vencer',
    color: 'blue',
  },
  {
    tipo: 'PAGO_1_DIA_ANTES',
    label: 'Falta 1 día al vencimiento',
    categoria: 'Por vencer',
    color: 'blue',
  },
  {
    tipo: 'PAGO_2_DIAS_ANTES_PENDIENTE',
    label: '2 días antes (pendiente, vence en 2 días)',
    categoria: 'Por vencer',
    color: 'blue',
  },
  {
    tipo: 'PAGO_DIA_0',
    label: 'Vence hoy',
    categoria: 'Día de pago',
    color: 'green',
  },
  {
    tipo: 'PAGO_1_DIA_ATRASADO',
    label: 'Día siguiente al vencimiento',
    categoria: 'Retrasada',
    color: 'orange',
  },
  {
    tipo: 'PAGO_10_DIAS_ATRASADO',
    label: '10 días de retraso',
    categoria: 'Retrasada',
    color: 'orange',
  },
  {
    tipo: 'PREJUDICIAL',
    label: 'Prejudicial',
    categoria: 'Prejudicial',
    color: 'red',
  },
  {
    tipo: 'MASIVOS',
    label: 'Comunicaciones masivas',
    categoria: 'Comunicaciones',
    color: 'slate',
  },
]

const CONFIG_ENVIO_SECCIONES = [
  {
    id: 'por-vencer' as const,
    label: 'Por vencer',
    categorias: ['Por vencer'],
  },
  {
    id: 'dia-pago' as const,
    label: 'Día de pago',
    categorias: ['Día de pago'],
  },
  { id: 'retrasada' as const, label: 'Retrasada', categorias: ['Retrasada'] },
  {
    id: 'prejudicial' as const,
    label: 'Prejudicial',
    categorias: ['Prejudicial'],
  },
  {
    id: 'comunicaciones' as const,
    label: 'Comunicaciones',
    categorias: ['Comunicaciones'],
  },
]

type ConfigEnvioSeccionId = (typeof CONFIG_ENVIO_SECCIONES)[number]['id']

function esConfigEnvioSeccionId(v: string | null): v is ConfigEnvioSeccionId {
  return CONFIG_ENVIO_SECCIONES.some(s => s.id === v)
}

/**
 * Subconjunto para prueba de paquete (cuotas en mora / prejudicial con datos típicos en BD).
 */
export const CRITERIOS_ENVIO_PANEL: CriterioEnvioRow[] = [
  {
    tipo: 'PAGO_2_DIAS_ANTES_PENDIENTE',
    label: '2 días antes (pendiente, vence en 2 días)',
    categoria: 'Por vencer',
    color: 'blue',
  },
  {
    tipo: 'PAGO_1_DIA_ATRASADO',
    label: 'Día siguiente al vencimiento',
    categoria: 'Retrasada',
    color: 'orange',
  },
  {
    tipo: 'PAGO_10_DIAS_ATRASADO',
    label: '10 días de retraso',
    categoria: 'Retrasada',
    color: 'orange',
  },
  {
    tipo: 'PREJUDICIAL',
    label: 'Prejudicial',
    categoria: 'Prejudicial',
    color: 'red',
  },
  {
    tipo: 'MASIVOS',
    label: 'Comunicaciones masivas',
    categoria: 'Comunicaciones',
    color: 'slate',
  },
]

/** Etiquetas para vinculación PDF + compat; incluye COBRANZA (solo plantilla, sin fila envío). */
export const CRITERIOS_ETIQUETAS: CriterioEnvioRow[] = [
  ...CRITERIOS_ENVIO_TABLA,
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
const HORA_DEFAULT_MASIVOS = '03:00'

/** Toast fijo mientras corre POST /notificaciones/enviar-caso-manual (lote largo). */
const TOAST_ID_ENVIO_CASO_MANUAL = 'envio-caso-manual'

function defaultEnvio(): ConfigEnvioItem {
  return {
    habilitado: true,
    cco: [],
    programador: HORA_DEFAULT_MASIVOS,
    incluir_pdf_anexo: true,
    incluir_adjuntos_fijos: true,
  }
}

/** Normaliza la respuesta de la API en estado listo para el componente (carga única y clara). */

function normalizeConfigFromApi(raw: ConfigEnvioCompleta | null): {
  modoPruebas: boolean

  emailsPruebas: [string, string]

  configEnvios: Record<string, ConfigEnvioItem>

  campanasMasivos: CampanaMasivaConfig[]
} {
  const data = raw || {}

  const modoPruebas =
    data.modo_pruebas === true ||
    data.modo_pruebas === 'true' ||
    String(data.modo_pruebas || '').toLowerCase() === 'true'

  let emailsPruebas: [string, string] = ['', '']

  if (Array.isArray(data.emails_pruebas)) {
    emailsPruebas = [
      String(data.emails_pruebas[0] ?? ''),
      String(data.emails_pruebas[1] ?? ''),
    ]
  } else if (typeof data.email_pruebas === 'string') {
    emailsPruebas = [data.email_pruebas, '']
  }

  const tiposCasoEnvio = new Set(CRITERIOS_ENVIO_TABLA.map(r => r.tipo))
  const configEnvios: Record<string, ConfigEnvioItem> = {}
  for (const tipo of tiposCasoEnvio) {
    const v = (data as Record<string, unknown>)[tipo]
    if (v != null && typeof v === 'object' && !Array.isArray(v)) {
      configEnvios[tipo] = v as ConfigEnvioItem
    }
  }

  const rawCampanas = Array.isArray(
    (data as Record<string, unknown>).masivos_campanas
  )
    ? ((data as Record<string, unknown>).masivos_campanas as Array<
        Record<string, unknown>
      >)
    : []

  const campanasMasivos: CampanaMasivaConfig[] = rawCampanas.map((c, idx) => {
    const diasRaw = Array.isArray(c?.dias_semana) ? c.dias_semana : []
    const dias = diasRaw
      .map(d => Number(d))
      .filter(d => Number.isInteger(d) && d >= 0 && d <= 6)
    const ccoRaw = Array.isArray(c?.cco) ? c.cco : []
    const cco = ccoRaw.map(v => String(v || '').trim()).filter(Boolean)
    return {
      id: String(c?.id || `campana-${idx + 1}`),
      nombre: String(c?.nombre || `Campana ${idx + 1}`),
      habilitado: c?.habilitado !== false,
      plantilla_id:
        typeof c?.plantilla_id === 'number'
          ? c.plantilla_id
          : c?.plantilla_id != null && String(c.plantilla_id).trim() !== ''
            ? Number(c.plantilla_id)
            : null,
      programador: String(c?.programador || HORA_DEFAULT_MASIVOS),
      dias_semana: Array.from(new Set(dias)).sort((a, b) => a - b),
      cco,
    }
  })

  return {
    modoPruebas,
    emailsPruebas,
    configEnvios,
    campanasMasivos,
  }
}

/** Vista completa (grupos por sección) o solo la fila de un módulo de notificaciones. */
export type ConfiguracionNotificacionesAlcance =
  | 'completo'
  | 'solo_pago_1_dia'
  | 'solo_pago_2_dias_antes_pendiente'
  | 'solo_pago_10_dias_atrasado'
  | 'solo_prejudicial'

/** Tipos de caso cuyas filas de envío pertenecen a un submódulo de Notificaciones (guardado parcial). */
function tiposCasoNotificacionParaAlcance(
  alcance: ConfiguracionNotificacionesAlcance
): string[] {
  switch (alcance) {
    case 'solo_pago_1_dia':
      return ['PAGO_1_DIA_ATRASADO']
    case 'solo_pago_2_dias_antes_pendiente':
      return ['PAGO_2_DIAS_ANTES_PENDIENTE']
    case 'solo_pago_10_dias_atrasado':
      return ['PAGO_10_DIAS_ATRASADO']
    case 'solo_prejudicial':
      return ['PREJUDICIAL']
    default:
      return CRITERIOS_ENVIO_TABLA.map(r => r.tipo)
  }
}

type ConfiguracionNotificacionesProps = {
  alcance?: ConfiguracionNotificacionesAlcance
}

export function ConfiguracionNotificaciones({
  alcance = 'completo',
}: ConfiguracionNotificacionesProps) {
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

  const criteriosPanelFiltrados = useMemo(() => {
    if (alcance === 'solo_pago_1_dia') {
      return CRITERIOS_ENVIO_PANEL.filter(c => c.tipo === 'PAGO_1_DIA_ATRASADO')
    }
    if (alcance === 'solo_pago_2_dias_antes_pendiente') {
      return CRITERIOS_ENVIO_PANEL.filter(
        c => c.tipo === 'PAGO_2_DIAS_ANTES_PENDIENTE'
      )
    }
    if (alcance === 'solo_pago_10_dias_atrasado') {
      return CRITERIOS_ENVIO_PANEL.filter(
        c => c.tipo === 'PAGO_10_DIAS_ATRASADO'
      )
    }
    if (alcance === 'solo_prejudicial') {
      return CRITERIOS_ENVIO_PANEL.filter(c => c.tipo === 'PREJUDICIAL')
    }
    return CRITERIOS_ENVIO_PANEL
  }, [alcance])

  const hrefPlantillasDesdeAlcance = useMemo(() => {
    if (alcance === 'solo_pago_1_dia') {
      return hrefPlantillasConContexto('PAGO_1_DIA_ATRASADO')
    }
    if (alcance === 'solo_pago_2_dias_antes_pendiente') {
      return hrefPlantillasConContexto('PAGO_2_DIAS_ANTES_PENDIENTE')
    }
    if (alcance === 'solo_pago_10_dias_atrasado') {
      return hrefPlantillasConContexto('PAGO_10_DIAS_ATRASADO')
    }
    if (alcance === 'solo_prejudicial') {
      return hrefPlantillasConContexto('PREJUDICIAL')
    }
    return '/configuracion?tab=plantillas'
  }, [alcance])

  /** Clave tipo_caso de adjuntos fijos (pestaña 3) alineada con el submenú de Notificaciones. */
  const casoAdjuntoPdfParaAlcance = useMemo((): string | null => {
    switch (alcance) {
      case 'solo_pago_1_dia':
        return 'dias_1_retraso'
      case 'solo_pago_2_dias_antes_pendiente':
        return 'd_2_antes_vencimiento'
      case 'solo_pago_10_dias_atrasado':
        return 'dias_10_retraso'
      case 'solo_prejudicial':
        return 'prejudicial'
      default:
        return null
    }
  }, [alcance])

  const [tipoPruebaPaquete, setTipoPruebaPaquete] = useState<string>(
    () => criteriosPanelFiltrados[0]?.tipo ?? CRITERIOS_ENVIO_PANEL[0].tipo
  )

  useEffect(() => {
    const allowed = new Set(criteriosPanelFiltrados.map(c => c.tipo))
    if (!allowed.has(tipoPruebaPaquete) && criteriosPanelFiltrados[0]) {
      setTipoPruebaPaquete(criteriosPanelFiltrados[0].tipo)
    }
  }, [criteriosPanelFiltrados, tipoPruebaPaquete])

  const [diagnosticoPaquete, setDiagnosticoPaquete] =
    useState<DiagnosticoPaquetePruebaResponse | null>(null)

  const [diagnosticoCargando, setDiagnosticoCargando] = useState(false)

  const [enviandoCasoTipo, setEnviandoCasoTipo] = useState<string | null>(null)

  const [campanasMasivos, setCampanasMasivos] = useState<CampanaMasivaConfig[]>(
    []
  )

  /**
   * Texto libre del textarea CCO (incluye saltos con Enter). Sin esto, al parsear se pierden
   * lineas vacias y el valor controlado colapsa: Enter no permitia escribir el siguiente correo.
   */
  const [ccoDraftPorTipo, setCcoDraftPorTipo] = useState<
    Record<string, string>
  >({})

  const [ccoDraftPorCampanaId, setCcoDraftPorCampanaId] = useState<
    Record<string, string>
  >({})

  const envioConfigAbortRef = useRef<AbortController | null>(null)

  const beginEnvioConfigAbortable = () => {
    envioConfigAbortRef.current?.abort()
    const c = new AbortController()
    envioConfigAbortRef.current = c
    return c
  }

  const cancelarEnvioConfigEmergencia = () => {
    envioConfigAbortRef.current?.abort()
    envioConfigAbortRef.current = null
    setEnviandoCasoTipo(null)
    setEnviandoPruebaIndice(null)
    setEnviandoMasivo(false)
    setDiagnosticoCargando(false)
    setGuardandoEnvios(false)
    guardandoRef.current = false
    toast.dismiss(TOAST_ID_ENVIO_CASO_MANUAL)
    toast.warning(
      'Cancelación: petición cortada en el navegador (o desbloqueo tras Guardar). ' +
        'Compruebe en Red (F12) si el PUT aún estaba en curso; si hace falta, vuelva a Guardar.'
    )
  }

  const hayEnvioConfigEnCurso =
    enviandoCasoTipo !== null || enviandoMasivo || enviandoPruebaIndice !== null

  /** Incluye Guardar en curso para poder desbloquear la UI si el estado queda colgado. */
  const puedeCancelarEmergenciaConfig =
    hayEnvioConfigEnCurso || guardandoEnvios || diagnosticoCargando

  const guardandoRef = useRef(false)

  /**
   * Evita que un refetch de GET .../notificaciones/envios (otra pestaña del navegador,
   * foco de ventana, invalidacion) pise cambios locales sin guardar. Cada fila/caso
   * sigue teniendo su propia clave en configEnvios; esto no mezcla plantillas entre casos.
   */
  const enviosLocalDirtyRef = useRef(false)

  const markEnviosLocalDirty = () => {
    enviosLocalDirtyRef.current = true
  }

  const queryClient = useQueryClient()

  const [searchParams, setSearchParams] = useSearchParams()

  const cfgParam = searchParams.get('cfg')

  const seccionConfigId: ConfigEnvioSeccionId = esConfigEnvioSeccionId(cfgParam)
    ? cfgParam
    : 'retrasada'

  useEffect(() => {
    if (cfgParam != null && !esConfigEnvioSeccionId(cfgParam)) {
      setSearchParams(
        p => {
          const n = new URLSearchParams(p)
          n.delete('cfg')
          return n
        },
        { replace: true }
      )
    }
  }, [cfgParam, setSearchParams])

  const setSeccionConfig = (id: ConfigEnvioSeccionId) => {
    setSearchParams(
      p => {
        const n = new URLSearchParams(p)
        if (id === 'retrasada') n.delete('cfg')
        else n.set('cfg', id)
        return n
      },
      { replace: true }
    )
  }

  const filasEnvioPorSeccion = useMemo(() => {
    if (alcance === 'solo_pago_1_dia') {
      return CRITERIOS_ENVIO_TABLA.filter(r => r.tipo === 'PAGO_1_DIA_ATRASADO')
    }
    if (alcance === 'solo_pago_2_dias_antes_pendiente') {
      return CRITERIOS_ENVIO_TABLA.filter(
        r => r.tipo === 'PAGO_2_DIAS_ANTES_PENDIENTE'
      )
    }
    if (alcance === 'solo_pago_10_dias_atrasado') {
      return CRITERIOS_ENVIO_TABLA.filter(
        r => r.tipo === 'PAGO_10_DIAS_ATRASADO'
      )
    }
    if (alcance === 'solo_prejudicial') {
      return CRITERIOS_ENVIO_TABLA.filter(r => r.tipo === 'PREJUDICIAL')
    }
    const cats = new Set(
      CONFIG_ENVIO_SECCIONES.find(s => s.id === seccionConfigId)?.categorias ??
        []
    )
    return CRITERIOS_ENVIO_TABLA.filter(row => cats.has(row.categoria))
  }, [alcance, seccionConfigId])

  const alcanceReducido = alcance !== 'completo'

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

    refetchOnMount: 'always',
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
    if (dataEnvios == null) return
    if (enviosLocalDirtyRef.current) return
    const {
      modoPruebas: mp,
      emailsPruebas: ep,
      configEnvios: ce,
      campanasMasivos: cm,
    } = normalizeConfigFromApi(dataEnvios)

    setModoPruebas(mp)

    setEmailsPruebas(ep)

    setConfigEnvios(ce)
    setCampanasMasivos(cm)
    setCcoDraftPorTipo({})
    setCcoDraftPorCampanaId({})
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

    const row: ConfigEnvioItem = {
      habilitado: c.habilitado !== false,

      cco: Array.isArray(c.cco) ? c.cco : [],

      plantilla_id: c.plantilla_id ?? null,

      programador: c.programador ?? HORA_DEFAULT,

      // PDF = Carta_Cobranza (pestaña 2). Por defecto sí (requerido con paquete estricto en backend).

      incluir_pdf_anexo: c.incluir_pdf_anexo !== false,

      incluir_adjuntos_fijos: c.incluir_adjuntos_fijos !== false,
    }

    // Masivos: nunca carta PDF de cobranza (comunicación general; evita Carta_Cobranza.pdf por error).
    if (tipo === 'MASIVOS') {
      return { ...row, incluir_pdf_anexo: false }
    }

    return row
  }

  const setConfig = (tipo: string, upd: Partial<ConfigEnvioItem>) => {
    markEnviosLocalDirty()
    setConfigEnvios(prev => {
      const current = prev[tipo] || defaultEnvio()

      return { ...prev, [tipo]: { ...current, ...upd } }
    })
  }

  const toggleEnvio = (tipo: string) => {
    const c = getConfig(tipo)

    setConfig(tipo, { habilitado: !c.habilitado })
  }

  const setCcoDesdeTexto = (tipo: string, texto: string) => {
    setCcoDraftPorTipo(prev => ({ ...prev, [tipo]: texto }))
    setConfig(tipo, { cco: parsearCorreosCco(texto) })
  }

  const valorTextareaCcoTipo = (tipo: string) => {
    const borrador = ccoDraftPorTipo[tipo]
    if (borrador !== undefined) return borrador
    return getConfig(tipo).cco.filter(Boolean).join('\n')
  }

  const eliminarCCO = (tipo: string, index: number) => {
    const c = getConfig(tipo)
    const next = c.cco.filter((_, i) => i !== index)
    setCcoDraftPorTipo(prev => ({ ...prev, [tipo]: next.join('\n') }))
    setConfig(tipo, { cco: next })
  }

  const agregarCampanaMasiva = () => {
    markEnviosLocalDirty()
    setCampanasMasivos(prev => [
      ...prev,
      {
        id: `campana-${Date.now()}`,
        nombre: `Campana ${prev.length + 1}`,
        habilitado: true,
        plantilla_id: null,
        programador: HORA_DEFAULT_MASIVOS,
        dias_semana: [0],
        cco: [],
      },
    ])
  }

  const actualizarCampanaMasiva = (
    id: string,
    patch: Partial<CampanaMasivaConfig>
  ) => {
    markEnviosLocalDirty()
    setCampanasMasivos(prev =>
      prev.map(c => (c.id === id ? { ...c, ...patch } : c))
    )
  }

  const eliminarCampanaMasiva = (id: string) => {
    markEnviosLocalDirty()
    setCampanasMasivos(prev => prev.filter(c => c.id !== id))
    setCcoDraftPorCampanaId(prev => {
      if (!(id in prev)) return prev
      const n = { ...prev }
      delete n[id]
      return n
    })
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
      const tiposPersistir = tiposCasoNotificacionParaAlcance(alcance)
      const payload: ConfigEnvioCompleta = {} as ConfigEnvioCompleta

      if (alcanceReducido) {
        // PUT parcial: solo filas de este submódulo + modo prueba (global en BD).
        // No se envían otros criterios ni masivos_campanas: el servidor hace merge y no los pisa.
        ;(payload as Record<string, unknown>).modo_pruebas = modoPruebas
        ;(payload as Record<string, unknown>).emails_pruebas =
          emailsPruebas.filter(e => e?.trim())
        ;(payload as Record<string, unknown>).email_pruebas =
          emailsPruebas[0]?.trim() || ''

        for (const tipo of tiposPersistir) {
          const c = getConfig(tipo)
          ;(payload as Record<string, ConfigEnvioItem>)[tipo] = {
            ...c,
            incluir_pdf_anexo:
              tipo === 'MASIVOS' ? false : c.incluir_pdf_anexo !== false,
            incluir_adjuntos_fijos: c.incluir_adjuntos_fijos !== false,
          }
        }
      } else {
        // Guardado completo: solo claves de producto conocidas (sin reenviar JSON legado ni
        // mezclar masivos/cron dentro del mismo objeto que las filas por tipo).
        const p = payload as Record<string, unknown>
        p.modo_pruebas = modoPruebas
        p.emails_pruebas = emailsPruebas.filter(e => e?.trim())
        p.email_pruebas = emailsPruebas[0]?.trim() || ''
        p.masivos_campanas = campanasMasivos.map(c => ({
          id: c.id,
          nombre: c.nombre,
          habilitado: c.habilitado,
          plantilla_id: c.plantilla_id ?? null,
          programador: c.programador || HORA_DEFAULT_MASIVOS,
          dias_semana: Array.from(new Set(c.dias_semana || [])).sort(
            (a, b) => a - b
          ),
          cco: (c.cco || []).map(e => String(e || '').trim()).filter(Boolean),
        }))

        for (const { tipo } of CRITERIOS_ENVIO_TABLA) {
          const c = getConfig(tipo)
          p[tipo] = {
            ...c,
            incluir_pdf_anexo:
              tipo === 'MASIVOS' ? false : c.incluir_pdf_anexo !== false,
            incluir_adjuntos_fijos: c.incluir_adjuntos_fijos !== false,
          }
        }
      }

      await emailConfigService.actualizarConfiguracionEnvios(payload)

      enviosLocalDirtyRef.current = false

      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.envios,
      })

      setUltimoGuardado(new Date())

      toast.success(
        alcanceReducido
          ? `Guardado: solo ${tiposPersistir.join(', ')} y modo prueba (global). Otros criterios y campañas masivas no se modificaron.`
          : 'Configuración de envíos guardada'
      )
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

  const handleEnviarCasoManual = async (tipo: string, etiquetaCaso: string) => {
    if (enviosLocalDirtyRef.current) {
      toast.error(
        'Hay cambios sin guardar en esta pantalla. Pulse Guardar antes de enviar: el servidor solo usa la configuración ya persistida.',
        { duration: 8000 }
      )
      return
    }
    if (modoPruebas) {
      const primero = (emailsPruebas[0] || '').trim()
      if (!primero || !esEmailValido(primero)) {
        toast.error(
          'Configure Correo pruebas 1 válido antes de enviar este caso.'
        )
        return
      }
      const estadoEmail =
        await emailConfigService.verificarEstadoConfiguracionEmail()
      if (!estadoEmail?.configurada) {
        const problemas =
          estadoEmail?.problemas?.join('. ') ||
          'servidor SMTP, usuario y contrasena'
        toast.error(
          `Configura el email SMTP antes de enviar este caso: ${problemas} Ve a Configuracion > Email.`,
          { duration: 6000 }
        )
        return
      }
      void queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.emailEstado,
      })
    } else {
      const ok = window.confirm(
        `¿Enviar ahora el caso «${etiquetaCaso}» a los correos de los clientes en lista? ` +
          'Se usa la configuración ya guardada en el servidor (plantilla, CCO, PDFs).'
      )
      if (!ok) return
    }

    const ac = beginEnvioConfigAbortable()
    try {
      setEnviandoCasoTipo(tipo)
      toast.loading(
        `Enviando «${etiquetaCaso}»… El servidor recorre la lista (un correo por cliente); ` +
          'puede tardar varios minutos. En Red (F12): el POST a notificaciones/enviar-caso-manual ' +
          'permanece pendiente hasta que termine todo el lote.',
        { id: TOAST_ID_ENVIO_CASO_MANUAL, duration: Infinity }
      )
      const res = await notificacionService.enviarCasoManual(tipo, {
        signal: ac.signal,
      })
      toast.dismiss(TOAST_ID_ENVIO_CASO_MANUAL)
      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.envioBatchUltimo,
      })
      await invalidateListasNotificacionesMora(queryClient)
      const lista = res.total_en_lista ?? 0
      const env = res.enviados ?? 0
      const fall = res.fallidos ?? 0
      const sin = res.sin_email ?? 0
      const omPkg = res.omitidos_paquete_incompleto ?? 0
      toast.success(
        `${res.mensaje || 'Listo.'} Lista: ${lista}. Enviados: ${env}, fallidos: ${fall}, sin email: ${sin}. ` +
          (omPkg > 0
            ? `Omitidos paquete: ${omPkg} (revise plantilla y PDFs).`
            : '')
      )
    } catch (error: unknown) {
      toast.dismiss(TOAST_ID_ENVIO_CASO_MANUAL)
      if (isRequestCanceled(error)) {
        toast.info('Envío cancelado en el navegador.')
        return
      }
      toast.error(getErrorDetail(error) || 'Error al enviar este caso.')
    } finally {
      if (envioConfigAbortRef.current === ac) {
        envioConfigAbortRef.current = null
      }
      setEnviandoCasoTipo(null)
    }
  }

  /** Prueba de paquete (mora/prejudicial): un correo por criterio con plantilla guardada en BD. Masivos usa otro boton. */

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

    const ac = beginEnvioConfigAbortable()
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

        if (envioConfigAbortRef.current === ac) {
          envioConfigAbortRef.current = null
        }
        setEnviandoPruebaIndice(null)

        return
      }

      const resultado: EnvioPruebaPaqueteResponse =
        await notificacionService.enviarPruebaPaqueteCompleta({
          tipo: tipoPruebaPaquete,
          destinos,
          signal: ac.signal,
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
      if (isRequestCanceled(error)) {
        toast.info('Prueba cancelada en el navegador.')
        return
      }
      const detalle = getErrorDetail(error)

      const mensaje =
        detalle ||
        (error as Error)?.message ||
        'Error al enviar el correo de prueba'

      toast.error(mensaje, { duration: 5000 })
    } finally {
      if (envioConfigAbortRef.current === ac) {
        envioConfigAbortRef.current = null
      }
      setEnviandoPruebaIndice(null)
    }
  }

  const handleDiagnosticoPaquete = async () => {
    try {
      setDiagnosticoCargando(true)
      const d =
        await notificacionService.diagnosticoPaquetePrueba(tipoPruebaPaquete)
      setDiagnosticoPaquete(d)
      const esDosDiasAntes = tipoPruebaPaquete === 'PAGO_2_DIAS_ANTES_PENDIENTE'
      if (d.ok && d.paquete_completo) {
        toast.success(
          esDosDiasAntes
            ? 'Diagnostico: listo para 2 dias antes (correo). PDFs en pestanas 2 y 3 son opcionales segun la fila de envio.'
            : 'Diagnostico: paquete listo (plantilla + Carta PDF + PDFs fijos). Puede enviar la prueba con confianza.',
          { duration: 8000 }
        )
      } else {
        const guiaFalla = esDosDiasAntes
          ? ' Revise SMTP, destinos de prueba y que exista un item de ejemplo en BD. No se exige plantilla guardada ni Carta PDF para este criterio.'
          : ' Revise PDFs en pestanas 2 y 3 y volumen en Render. Opcional: NOTIFICACIONES_PAQUETE_RELAX_SOLO_PRUEBA_DESTINO=true solo para prueba forzada.'
        toast.warning(
          `Diagnostico: no listo (${d.motivo || d.paquete_motivo || 'revisar'}).${guiaFalla}`,
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

    const ac = beginEnvioConfigAbortable()
    try {
      setEnviandoMasivo(true)

      const payload: ConfigEnvioCompleta = {
        ...configEnvios,

        modo_pruebas: true,

        emails_pruebas: emailsPruebas.filter(e => e?.trim()),

        email_pruebas: emailsPruebas[0]?.trim() || '',

        masivos_campanas: campanasMasivos.map(c => ({
          id: c.id,
          nombre: c.nombre,
          habilitado: c.habilitado,
          plantilla_id: c.plantilla_id ?? null,
          programador: c.programador || HORA_DEFAULT_MASIVOS,
          dias_semana: Array.from(new Set(c.dias_semana || [])).sort(
            (a, b) => a - b
          ),
          cco: (c.cco || []).map(e => String(e || '').trim()).filter(Boolean),
        })),
      }

      await emailConfigService.actualizarConfiguracionEnvios(payload, {
        signal: ac.signal,
      })

      await queryClient.invalidateQueries({
        queryKey: NOTIFICACIONES_QUERY_KEYS.envios,
      })

      const res = await notificacionService.enviarNotificacionesMasivos({
        signal: ac.signal,
      })

      const enviados = res?.enviados ?? 0
      const fallidos = res?.fallidos ?? 0
      const sinEmail = res?.sin_email ?? 0
      const omitidos =
        (res as { omitidos_config?: number })?.omitidos_config ?? 0

      if (enviados + fallidos + sinEmail === 0 && omitidos > 0) {
        toast.warning(
          `Ningún envío masivo: ${omitidos} omitidos por configuración o paquete. Revise la fila MASIVOS y campañas.`
        )
      } else {
        toast.success(
          `Prueba solo MASIVOS: ${enviados} enviados, ${fallidos} fallidos, ${sinEmail} sin email. No se ejecutaron mora/prejudicial ni otros casos.`
        )
      }
    } catch (error: unknown) {
      if (isRequestCanceled(error)) {
        toast.info('Envío masivos cancelado en el navegador.')
        return
      }
      const detalle = getErrorDetail(error)

      toast.error(detalle || 'Error al ejecutar envíos masivos.')
    } finally {
      if (envioConfigAbortRef.current === ac) {
        envioConfigAbortRef.current = null
      }
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
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-red-200 bg-red-50/90 px-3 py-2">
        <p className="max-w-xl text-sm text-red-900">
          <strong>Emergencia:</strong> cancela envío/prueba en curso o
          desbloquea si Guardar dejó el formulario colgado (revise en Red si el
          PUT siguió).
        </p>

        <Button
          type="button"
          variant="outline"
          size="sm"
          className="shrink-0 border-red-400 text-red-800 hover:bg-red-100"
          disabled={!puedeCancelarEmergenciaConfig}
          onClick={cancelarEnvioConfigEmergencia}
          title="Interrumpe POST de envío/prueba/masivos o restablece estado tras Guardar atascado."
        >
          <X className="mr-2 h-4 w-4" />
          Cancelar
        </Button>
      </div>

      <Card className="border-slate-200 bg-slate-50/40">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-xl">
            <Settings className="h-5 w-5 text-blue-600" />
            Configuración por caso
          </CardTitle>

          <CardDescription>
            {alcance === 'solo_prejudicial' ? (
              <>
                Configuración solo para el listado{' '}
                <strong>Prejudicial (5+ cuotas)</strong> (caso{' '}
                <strong>PREJUDICIAL</strong>
                ): plantilla, envío, PDF y adjuntos de ese criterio. Las
                plantillas COBRANZA se crean en Plantillas. El backend exige
                plantilla activa, PDF variable válido y al menos un PDF fijo
                adicional.
              </>
            ) : alcance === 'solo_pago_2_dias_antes_pendiente' ? (
              <>
                Configuración solo para <strong>2 días antes</strong> (caso{' '}
                <strong>PAGO_2_DIAS_ANTES_PENDIENTE</strong>): cuotas en estado
                PENDIENTE con vencimiento dentro de 2 días; plantilla, envío,
                PDF y adjuntos del caso{' '}
                <code className="rounded bg-gray-100 px-1">
                  d_2_antes_vencimiento
                </code>
                .
              </>
            ) : alcance === 'solo_pago_1_dia' ? (
              <>
                Configuración solo para{' '}
                <strong>día siguiente al vencimiento</strong> (caso{' '}
                <strong>PAGO_1_DIA_ATRASADO</strong>): plantilla, envío, PDF y
                adjuntos. Plantillas en Plantillas; PDFs fijos según adjuntos
                del caso.
              </>
            ) : alcance === 'solo_pago_10_dias_atrasado' ? (
              <>
                Configuración solo para <strong>10 días de atraso</strong> (caso{' '}
                <strong>PAGO_10_DIAS_ATRASADO</strong>): cuotas pendientes cuya
                fecha de vencimiento está exactamente a 10 días calendario en el
                pasado respecto de la fecha de referencia (Caracas); el préstamo
                debe tener entre 2 y 3 cuotas en mora (inclusive); con 1 o con 4
                o más no aplican. Incluye plantilla, envío, PDF y adjuntos del
                caso{' '}
                <code className="rounded bg-gray-100 px-1">
                  dias_10_retraso
                </code>
                . Al pulsar Guardar solo se persisten esta fila y el bloque
                global de modo prueba (no se modifican otros criterios ni
                campañas masivas). El envío de correos de este criterio es solo
                manual desde la pestaña de listado del submódulo (no entra en
                «enviar todas» ni en el POST agregado legacy de retrasadas).
              </>
            ) : (
              <>
                Cada correo al cliente (modo estricto) combina tres piezas: (1)
                plantilla de correo HTML con variables; (2) PDF de carta con
                variables (Carta_Cobranza.pdf); (3) PDFs fijos de anexos,
                siempre junto al PDF variable. Aquí se configuran los casos de
                envío (por vencer, día de pago, retrasadas, prejudicial,
                comunicaciones masivas). Las plantillas tipo carta de cobranza
                (COBRANZA) se crean en Plantillas y se eligen aqui por caso. El
                backend exige plantilla activa, PDF variable valido y al menos
                un PDF fijo adicional (sección Documentos PDF anexos / adjunto
                global).
              </>
            )}
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
              ? 'Todos los envíos van al correo de pruebas. Puedes activar o desactivar cada caso (Envío) para elegir a qué tipos de notificación aplicar la prueba.'
              : 'Los emails se envían al correo de cada cliente según la opción Envío de cada caso.'}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {alcanceReducido && (
            <div className="rounded-lg border border-amber-200 bg-amber-50/80 p-3 text-xs text-amber-900">
              <strong className="font-semibold">
                Alcance de esta pantalla:
              </strong>{' '}
              al pulsar Guardar solo se persisten las filas de este criterio (
              {tiposCasoNotificacionParaAlcance(alcance).join(', ')}). El modo
              prueba/producción y los correos de prueba son <em>globales</em> en
              la base de datos (afectan a todos los criterios al enviar). Las
              campañas masivas y el resto de casos no se modifican desde aquí.
            </div>
          )}

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

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Prueba</span>

            <button
              type="button"
              role="switch"
              aria-checked={modoPruebas}
              onClick={() => {
                markEnviosLocalDirty()
                setModoPruebas(!modoPruebas)
              }}
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
                  onChange={e => {
                    markEnviosLocalDirty()
                    setEmailsPruebas(prev => [e.target.value, prev[1]])
                  }}
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
                  onChange={e => {
                    markEnviosLocalDirty()
                    setEmailsPruebas(prev => [prev[0], e.target.value])
                  }}
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
                {alcance === 'solo_prejudicial' ? (
                  <>
                    Pestaña 1 = cuerpo HTML; pestaña 2 = carta PDF; pestaña 3 =
                    PDF fijo del caso prejudicial (
                    <code className="rounded bg-gray-100 px-1">
                      prejudicial
                    </code>
                    ), subido abajo o en Plantillas; se guarda en base de datos.
                  </>
                ) : alcance === 'solo_pago_2_dias_antes_pendiente' ? (
                  <>
                    Pestaña 1 = cuerpo HTML; pestaña 2 = carta PDF; pestaña 3 =
                    PDF fijo (
                    <code className="rounded bg-gray-100 px-1">
                      d_2_antes_vencimiento
                    </code>
                    ).
                  </>
                ) : alcance === 'solo_pago_1_dia' ? (
                  <>
                    Pestaña 1 = cuerpo HTML; pestaña 2 = carta PDF; pestaña 3 =
                    PDF fijo (
                    <code className="rounded bg-gray-100 px-1">
                      dias_1_retraso
                    </code>
                    ), subido abajo o en Plantillas; se guarda en base de datos.
                  </>
                ) : alcance === 'solo_pago_10_dias_atrasado' ? (
                  <>
                    Pestaña 1 = cuerpo HTML; pestaña 2 = carta PDF; pestaña 3 =
                    PDF fijo (
                    <code className="rounded bg-gray-100 px-1">
                      dias_10_retraso
                    </code>
                    ), subido abajo o en Plantillas; se guarda en base de datos.
                  </>
                ) : (
                  <>
                    Pestaña 1 = cuerpo HTML del correo; pestaña 2 = carta PDF;
                    pestaña 3 = PDF fijo por caso (ej. «Día siguiente al venc.»
                    →{' '}
                    <code className="rounded bg-gray-100 px-1">
                      dias_1_retraso
                    </code>
                    ). El panel solo enlaza plantilla y flags: el archivo de la
                    pestaña 3 debe existir en el disco del servidor (si el
                    hosting borra archivos al desplegar, vuelva a subir el PDF o
                    use volumen persistente).
                  </>
                )}
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
                      {criteriosPanelFiltrados.map(({ tipo, label }) => (
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
                    enviandoMasivo
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
                    diagnosticoCargando || enviandoPruebaIndice !== null
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

                {!alcanceReducido && (
                  <>
                    <Button
                      onClick={handleEnviosMasivosPrueba}
                      disabled={enviandoMasivo || diagnosticoCargando}
                      variant="outline"
                      className="flex h-auto w-full items-center justify-center gap-2 rounded-lg border-amber-400 bg-amber-50 py-2 font-semibold text-amber-800 hover:bg-amber-100 disabled:opacity-50"
                    >
                      <Mail className="h-5 w-5" />

                      {enviandoMasivo ? 'Enviando...' : 'Envíos masivos prueba'}
                    </Button>

                    <p className="mt-2 text-sm text-gray-600">
                      Solo caso MASIVOS: un correo por contacto de la lista
                      masiva (campañas en Comunicaciones). No ejecuta día
                      siguiente al vencimiento, prejudicial, 2 días antes ni
                      retrasadas. En modo prueba los destinos reales se
                      redirigen al correo de pruebas. Guarde antes si cambió
                      plantillas o campañas.
                    </p>
                  </>
                )}
              </div>
            )}
        </CardContent>
      </Card>

      {!alcanceReducido && (
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
              Resultado del último lote grande (p. ej. «Enviar todas» en segundo
              plano) o de «Enviar este caso ahora» por fila. El submódulo 2 días
              antes no entra en «Enviar todas». Útil cuando una petición
              responde 202 sin cuerpo.
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
      )}

      {!alcanceReducido && (
        <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
          <p className="mb-2 text-xs font-medium text-slate-600">
            Grupo de configuración: solo se listan filas y acciones de este
            bloque. Campañas masivas aparecen únicamente en «Comunicaciones».
          </p>
          <nav className="flex flex-wrap gap-1" aria-label="Grupos de envío">
            {CONFIG_ENVIO_SECCIONES.map(sec => (
              <button
                key={sec.id}
                type="button"
                onClick={() => setSeccionConfig(sec.id)}
                className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  seccionConfigId === sec.id
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {sec.label}
              </button>
            ))}
          </nav>
        </div>
      )}

      {seccionConfigId === 'comunicaciones' && !alcanceReducido ? (
        <Card className="border-slate-200 bg-slate-50/40">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Mail className="h-4 w-4 text-slate-600" />
              Campanas masivas
            </CardTitle>
            <CardDescription>
              Varias campañas con plantilla y CCO para comunicaciones masivas
              (caso MASIVOS). El envío es manual desde aquí (Enviar campañas
              activas ahora o botones por campaña). Si una campaña deja la
              plantilla en «Texto por defecto», se usa la plantilla de la fila
              «Comunicaciones masivas» de la tabla de arriba (guardada en el
              servidor).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={agregarCampanaMasiva}
              >
                Agregar campana
              </Button>
              <Button
                type="button"
                variant="secondary"
                onClick={() =>
                  void handleEnviarCasoManual('MASIVOS', 'campanas masivas')
                }
                disabled={enviandoCasoTipo !== null || enviandoMasivo}
              >
                {enviandoCasoTipo === 'MASIVOS'
                  ? 'Enviando campanas...'
                  : 'Enviar campanas activas ahora'}
              </Button>
            </div>

            {campanasMasivos.length === 0 ? (
              <p className="text-sm text-gray-500">
                No hay campanas configuradas. Agrega al menos una para campañas
                de comunicaciones masivas.
              </p>
            ) : (
              <div className="space-y-3">
                {campanasMasivos.map(camp => {
                  const listaPlantillas = plantillasPorTipo('MASIVOS')
                  return (
                    <div
                      key={camp.id}
                      className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                    >
                      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                        <Input
                          value={camp.nombre}
                          onChange={e =>
                            actualizarCampanaMasiva(camp.id, {
                              nombre: e.target.value,
                            })
                          }
                          className="h-9 w-full max-w-md bg-white"
                          placeholder="Nombre de campana"
                        />
                        <div className="flex flex-wrap items-center gap-2">
                          <label className="text-xs text-gray-600">
                            Activa
                          </label>
                          <input
                            type="checkbox"
                            checked={camp.habilitado}
                            onChange={e =>
                              actualizarCampanaMasiva(camp.id, {
                                habilitado: e.target.checked,
                              })
                            }
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => eliminarCampanaMasiva(camp.id)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      <div className="grid gap-4 md:grid-cols-2">
                        <div>
                          <label className="mb-1 block text-xs font-medium text-gray-600">
                            Plantilla
                          </label>
                          <Select
                            key={`plantilla-select-masivos-${camp.id}-${camp.plantilla_id ?? 'none'}`}
                            value={
                              camp.plantilla_id
                                ? String(camp.plantilla_id)
                                : '__ninguna__'
                            }
                            onValueChange={v =>
                              actualizarCampanaMasiva(camp.id, {
                                plantilla_id:
                                  v === '__ninguna__' ? null : parseInt(v, 10),
                              })
                            }
                          >
                            <SelectTrigger className="h-9 bg-white">
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
                        </div>

                        <div>
                          <label className="mb-1 block text-xs font-medium text-gray-600">
                            CCO (coma, ;, Enter)
                          </label>
                          <Textarea
                            value={
                              ccoDraftPorCampanaId[camp.id] !== undefined
                                ? ccoDraftPorCampanaId[camp.id]
                                : (camp.cco || []).join('\n')
                            }
                            onChange={e => {
                              const v = e.target.value
                              setCcoDraftPorCampanaId(prev => ({
                                ...prev,
                                [camp.id]: v,
                              }))
                              actualizarCampanaMasiva(camp.id, {
                                cco: parsearCorreosCco(v),
                              })
                            }}
                            rows={3}
                            className="bg-white"
                          />
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

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
                title="Sección Documentos PDF anexos: PDFs fijos por caso + global. Obligatorio para enviar (junto con plantilla y carta PDF)."
                aria-label="Incluir documentos PDF fijos de este caso"
              >
                Adj.
              </th>

              <th className="min-w-[280px] px-4 py-3 text-left font-semibold text-gray-700">
                Opciones
              </th>
            </tr>
          </thead>

          <tbody>
            {filasEnvioPorSeccion.map(({ tipo, label, categoria, color }) => {
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
                      key={`plantilla-select-${tipo}-${config.plantilla_id ?? 'none'}`}
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
                          to={hrefPlantillasConContexto(tipo)}
                          className="text-blue-600 hover:underline"
                        >
                          Configuración → Plantillas
                        </Link>{' '}
                        (caso {tipo}).
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
                      disabled={!config.habilitado || tipo === 'MASIVOS'}
                      title={
                        tipo === 'MASIVOS'
                          ? 'No aplica: comunicaciones masivas no adjuntan Carta_Cobranza.pdf'
                          : 'Carta_Cobranza.pdf (plantilla PDF cobranza). El servidor exige este PDF y un PDF fijo para enviar; debe estar activado.'
                      }
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
                    <div className="mb-3 space-y-1.5">
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        className="h-auto w-full gap-1.5 py-2 text-xs sm:max-w-[220px]"
                        disabled={
                          enviandoCasoTipo !== null ||
                          enviandoMasivo ||
                          diagnosticoCargando ||
                          enviandoPruebaIndice !== null
                        }
                        title={
                          enviandoCasoTipo !== null
                            ? 'Hay otro envío de caso en curso.'
                            : enviandoMasivo
                              ? 'Hay un envío masivos de prueba en curso.'
                              : diagnosticoCargando
                                ? 'Diagnóstico de paquete en curso.'
                                : enviandoPruebaIndice !== null
                                  ? 'Envío de notificación de prueba en curso.'
                                  : 'Enviar solo este criterio (POST sincrono). Si acaba de guardar y el botón no respondía, use Emergencia arriba solo si Guardar quedó colgado.'
                        }
                        onClick={() => void handleEnviarCasoManual(tipo, label)}
                      >
                        <Mail className="h-3.5 w-3.5 shrink-0" />

                        {enviandoCasoTipo === tipo
                          ? 'Enviando...'
                          : 'Enviar este caso ahora'}
                      </Button>

                      <p className="max-w-md text-[11px] leading-snug text-gray-500">
                        Solo este criterio (esta fila): un POST sincrono, sin
                        programar otros casos ni mezclar plantillas de otras
                        filas. Lista = misma regla de BD que la pestaña
                        correspondiente. Usa la config <strong>guardada</strong>{' '}
                        (pulse Guardar si cambió plantilla o CCO).
                        {modoPruebas
                          ? ' Modo prueba: destino = correo(s) de pruebas.'
                          : ' Producción: un correo por cliente con email.'}{' '}
                        Mientras dura el envío: el botón muestra «Enviando…»,
                        hay un aviso fijo arriba y en Red el POST{' '}
                        <code className="rounded bg-gray-100 px-0.5">
                          .../enviar-caso-manual
                        </code>{' '}
                        queda en curso hasta el final. En logs del servidor verá{' '}
                        <code className="rounded bg-gray-100 px-0.5">
                          [SMTP_ENVIO]
                        </code>{' '}
                        y{' '}
                        <code className="rounded bg-gray-100 px-0.5">
                          [notif_envio_email]
                        </code>
                        .
                      </p>
                    </div>

                    <details className="group">
                      <summary className="cursor-pointer list-none text-xs font-medium text-blue-600 hover:text-blue-800">
                        CCO (hasta {CCO_MAX})
                      </summary>

                      <div className="mt-2 min-w-[260px] space-y-3 pl-0">
                        <div className="rounded-lg border border-gray-200 bg-slate-50/80 p-3">
                          <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-gray-700">
                            <Mail className="h-3.5 w-3.5 text-blue-600" />
                            CCO (copia oculta)
                          </div>

                          <p className="mb-2 text-xs text-gray-500">
                            Pegue varios correos aquí:{' '}
                            <strong>uno por línea</strong> (pulse{' '}
                            <strong>Enter</strong> para pasar al siguiente), o
                            separados por <strong>coma</strong> o{' '}
                            <strong>punto y coma</strong>. Máximo {CCO_MAX}. El
                            servidor solo usa direcciones con formato completo (
                            <code className="rounded bg-white px-0.5">@</code> y
                            dominio). En modo pruebas el destino principal es el
                            de pruebas; CCO sigue aplicando.
                          </p>

                          <Textarea
                            value={valorTextareaCcoTipo(tipo)}
                            onChange={e =>
                              setCcoDesdeTexto(tipo, e.target.value)
                            }
                            disabled={!config.habilitado}
                            placeholder={
                              'ejemplo@empresa.com\notro@empresa.com'
                            }
                            rows={4}
                            autoComplete="off"
                            spellCheck={false}
                            className="resize-y bg-white text-sm leading-relaxed placeholder:text-gray-400"
                            aria-label="Correos en copia oculta"
                          />

                          {config.cco.some(Boolean) && (
                            <div className="mt-2">
                              <p className="mb-1 text-[11px] font-medium uppercase tracking-wide text-gray-500">
                                Activos (pulse la X para quitar)
                              </p>

                              <ul className="flex flex-col gap-1.5">
                                {config.cco.map(
                                  (email, idx) =>
                                    email?.trim() && (
                                      <li
                                        key={`${tipo}-cco-${idx}-${email}`}
                                        className="flex items-center gap-2"
                                      >
                                        <span
                                          className={`inline-flex min-h-9 max-w-full flex-1 items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs ${
                                            esEmailValido(email)
                                              ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                                              : 'border-amber-300 bg-amber-50 text-amber-950'
                                          }`}
                                        >
                                          <Mail className="h-3.5 w-3.5 shrink-0 opacity-70" />

                                          <span
                                            className="min-w-0 flex-1 break-all font-medium"
                                            title={email.trim()}
                                          >
                                            {email.trim()}
                                          </span>

                                          {!esEmailValido(email) && (
                                            <span className="shrink-0 text-[10px] text-amber-800">
                                              Revisar formato
                                            </span>
                                          )}
                                        </span>

                                        <Button
                                          type="button"
                                          variant="outline"
                                          size="sm"
                                          className="h-9 shrink-0 px-2 text-red-700 hover:bg-red-50"
                                          disabled={!config.habilitado}
                                          onClick={() => eliminarCCO(tipo, idx)}
                                          title="Quitar este correo"
                                        >
                                          <X className="h-4 w-4" />
                                        </Button>
                                      </li>
                                    )
                                )}
                              </ul>
                            </div>
                          )}
                        </div>
                      </div>
                    </details>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {casoAdjuntoPdfParaAlcance && (
        <DocumentosPdfAnexos casoDestinoFijo={casoAdjuntoPdfParaAlcance} />
      )}

      <div className="flex flex-wrap items-center justify-between gap-4 pt-2">
        <div className="flex items-center gap-3 text-sm text-gray-600">
          <Link
            to="/configuracion?tab=email"
            className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800"
          >
            <Mail className="h-4 w-4" /> Email (SMTP)
          </Link>

          <Link
            to={hrefPlantillasDesdeAlcance}
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
