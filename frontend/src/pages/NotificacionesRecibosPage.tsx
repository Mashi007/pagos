import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  Fragment,
  type MouseEvent,
} from 'react'

import { useSearchParams } from 'react-router-dom'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  AlertTriangle,
  Download,
  Eye,
  FileText,
  LayoutList,
  Loader2,
  Mail,
  RefreshCw,
  Settings,
  TestTube,
  X,
} from 'lucide-react'

import { Button } from '../components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import {
  ConfiguracionRecibos,
  RECIBOS_CONFIG_EMAIL_CUENTAS_QUERY_KEY,
} from '../components/recibos/ConfiguracionRecibos'
import {
  notificacionService,
  type ReciboConciliacionFila,
  type RecibosEjecutarEnvioResponse,
} from '../services/notificacionService'
import { apiClient } from '../services/api'
import { pathApiComprobanteImagenDesdeHref } from '../utils/comprobanteImagenAuth'
import { prestamoService } from '../services/prestamoService'
import { NOTIFICACIONES_RECIBOS_LISTADO_QUERY_KEY_PREFIX } from '../constants/queryKeys'
import { toast } from 'sonner'
import { getErrorMessage, isAxiosError } from '../types/errors'
import {
  SortArrowsCuotas,
  filaCoincideFiltroCedulaNotif,
  type NotificacionesCuotasSortCol,
} from './notificaciones/notificacionesPageCells'
import {
  cuotasAtrasadasSortValue,
  fechaVencSortValue,
  numericTotalPendienteSort,
} from './notificaciones/notificacionesListSort'

function hrefComprobanteRecibo(row: ReciboConciliacionFila): string {
  return (
    String(row.link_comprobante ?? '').trim() ||
    String(row.documento_ruta ?? '').trim()
  )
}

function pareceUrlImagenComprobante(u: string): boolean {
  if (!u) return false
  const low = u.toLowerCase()
  if (/\/comprobante-imagen\//i.test(u) || low.includes('/pagos/comprobante-imagen/')) {
    return true
  }
  const path = u.split('?')[0].toLowerCase()
  if (/\.(jpe?g|png|gif|webp)$/i.test(path)) return true
  return low.includes('googleusercontent')
}

const fmtMontoPagadoRecibo = new Intl.NumberFormat('es-VE', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

function textoMontoPagadoRecibo(n: number | undefined | null): string {
  const v = Number(n)
  if (!Number.isFinite(v)) return '-'
  return fmtMontoPagadoRecibo.format(v)
}

function textoFechaRegistroListado(s: string | null | undefined): string {
  const t = String(s ?? '').trim()
  if (!t) return '-'
  return t.length >= 16 ? t.slice(0, 16).replace('T', ' ') : t
}

function mensajeRecibosRespuestaError(codigo: string): string {
  switch (codigo) {
    case 'email_activo_recibos_desactivado':
      return 'Recibos está desactivado en Configuración > Correo (servicio recibos). Actívelo para envío real o use «Simular» (con modo pruebas puede enviarse muestra SMTP).'
    case 'envio_real_solo_fecha_recepcion_hoy_caracas':
      return 'El envío real solo aplica al día de hoy en Caracas, salvo «Enviar lote pasado (real)» con confirmación.'
    default:
      return codigo ? `Respuesta del servidor: ${codigo}` : 'Error al ejecutar Recibos.'
  }
}

function respuestaRecibosTieneErrorNegocio(out: RecibosEjecutarEnvioResponse): boolean {
  return typeof out.error === 'string' && out.error.trim().length > 0
}

function CeldaFotografiaPagoRecibo({ row }: { row: ReciboConciliacionFila }) {
  const href = hrefComprobanteRecibo(row)
  const [thumbOk, setThumbOk] = useState(true)
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [blobCargando, setBlobCargando] = useState(false)
  const [blobError, setBlobError] = useState(false)

  const pathAuth = href ? pathApiComprobanteImagenDesdeHref(href) : null
  const requiereAuth = Boolean(pathAuth)

  useEffect(() => {
    if (!href || !pathAuth) {
      setBlobUrl(u => {
        if (u) URL.revokeObjectURL(u)
        return null
      })
      setBlobCargando(false)
      setBlobError(false)
      return
    }
    let cancelado = false
    ;(async () => {
      try {
        setBlobCargando(true)
        setBlobError(false)
        const blob = await apiClient.getBlob(pathAuth)
        if (cancelado) return
        const objectUrl = URL.createObjectURL(blob)
        setBlobUrl(prev => {
          if (prev) URL.revokeObjectURL(prev)
          return objectUrl
        })
      } catch {
        if (!cancelado) {
          setBlobError(true)
          setThumbOk(false)
        }
      } finally {
        if (!cancelado) setBlobCargando(false)
      }
    })()
    return () => {
      cancelado = true
      setBlobUrl(u => {
        if (u) URL.revokeObjectURL(u)
        return null
      })
    }
  }, [href, pathAuth])

  if (!href) {
    return <span className="text-sm text-gray-400">-</span>
  }

  const abrirEnNuevaPestana = async (e: MouseEvent<HTMLAnchorElement>) => {
    if (!requiereAuth || !pathAuth) return
    e.preventDefault()
    try {
      const blob = await apiClient.getBlob(pathAuth)
      const url = URL.createObjectURL(blob)
      const w = window.open(url, '_blank', 'noopener,noreferrer')
      if (!w) {
        URL.revokeObjectURL(url)
      } else {
        window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
      }
    } catch {
      /* ya hay miniatura / estado; abrir pestaña sin blob falla silenciosamente */
    }
  }

  const imgSrc = requiereAuth ? blobUrl : href
  const probarMiniatura =
    pareceUrlImagenComprobante(href) &&
    thumbOk &&
    (!requiereAuth || (blobUrl && !blobError))

  return (
    <a
      href={requiereAuth ? '#' : href}
      target={requiereAuth ? undefined : '_blank'}
      rel={requiereAuth ? undefined : 'noopener noreferrer'}
      onClick={requiereAuth ? abrirEnNuevaPestana : undefined}
      className="inline-flex max-w-[14rem] items-center gap-2 text-violet-700 hover:text-violet-900"
      title={
        String(row.documento_nombre ?? '').trim() ||
        'Abrir fotografía o comprobante de pago'
      }
    >
      {blobCargando && requiereAuth ? (
        <span className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded border border-gray-200 bg-slate-50">
          <Loader2 className="h-5 w-5 animate-spin text-slate-500" aria-hidden />
        </span>
      ) : probarMiniatura && imgSrc ? (
        <img
          src={imgSrc}
          alt=""
          className="h-12 w-12 shrink-0 rounded border border-gray-200 bg-white object-cover"
          onError={() => setThumbOk(false)}
        />
      ) : (
        <span className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded border border-gray-200 bg-slate-50">
          <Eye className="h-6 w-6 text-slate-500" aria-hidden />
        </span>
      )}
      <span className="text-xs font-medium">Abrir</span>
    </a>
  )
}

type TabId = 'listado' | 'configuracion'

const RECIBOS_LISTADO_PAGE_SIZE = 10

/** Hasta ``maxButtons`` números de página centrados alrededor de ``current`` (ej. 1–5 en página 1 de 14). */
function numerosPaginaVisibles(
  current: number,
  total: number,
  maxButtons = 5
): number[] {
  if (total <= 0) return []
  if (total <= maxButtons) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }
  let start = Math.max(1, current - Math.floor(maxButtons / 2))
  let end = start + maxButtons - 1
  if (end > total) {
    end = total
    start = Math.max(1, end - maxButtons + 1)
  }
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
}

/** Día calendario America/Caracas en YYYY-MM-DD (alineado al backend). */
function fechaHoyIsoCaracas(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Caracas',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

/** ``creado_en`` de ``recibos_email_envio`` (ISO) mostrado en Caracas. */
function fmtInstanteRegistroRecibosCaracas(isoUtc: string): string {
  const t = String(isoUtc || '').trim()
  if (!t) return '—'
  const ms = Date.parse(t)
  if (Number.isNaN(ms)) return t
  return new Intl.DateTimeFormat('es-VE', {
    timeZone: 'America/Caracas',
    dateStyle: 'short',
    timeStyle: 'medium',
  }).format(new Date(ms))
}

/** Rótulo legible para cada lote (orden cronológico del backend). */
function etiquetaOrdinalEnvioRecibos(n: number): string {
  if (!Number.isFinite(n) || n < 1) return `Envío ${String(n)}`
  if (n === 2) return '2.o envío'
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return `${n}.er envío`
  if (mod10 === 3 && mod100 !== 13) return `${n}.er envío`
  return `${n}.º envío`
}

export default function NotificacionesRecibosPage() {
  const qc = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [recibosCfgResetSeq, setRecibosCfgResetSeq] = useState(0)
  const tabRaw = (searchParams.get('tab') || '').trim().toLowerCase()
  const activeTab: TabId = tabRaw === 'configuracion' ? 'configuracion' : 'listado'

  const setActiveTab = useCallback(
    (id: TabId) => {
      setSearchParams(
        p => {
          const n = new URLSearchParams(p)
          if (id === 'listado') n.delete('tab')
          else n.set('tab', 'configuracion')
          return n
        },
        { replace: true }
      )
    },
    [setSearchParams]
  )

  useEffect(() => {
    const prev = document.title
    document.title = 'Recibos | Notificaciones | RapiCredit'
    return () => {
      document.title = prev
    }
  }, [])

  const [fechaCaracas, setFechaCaracas] = useState('')
  const [filtroCedula, setFiltroCedula] = useState('')
  const [sortCol, setSortCol] = useState<NotificacionesCuotasSortCol | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [descargandoEstadoCuentaId, setDescargandoEstadoCuentaId] = useState<
    number | null
  >(null)
  const [paginaRecibosListado, setPaginaRecibosListado] = useState(1)
  const [envioManualEnCurso, setEnvioManualEnCurso] = useState(false)
  const [envioLotePasadoEnCurso, setEnvioLotePasadoEnCurso] = useState(false)
  const [simulacionEnCurso, setSimulacionEnCurso] = useState(false)

  const listadoKey = useMemo(
    () => [...NOTIFICACIONES_RECIBOS_LISTADO_QUERY_KEY_PREFIX, fechaCaracas || 'hoy'],
    [fechaCaracas]
  )

  const {
    data,
    isFetching,
    isError,
    isPlaceholderData,
    error: listadoError,
    refetch,
  } = useQuery({
    queryKey: listadoKey,
    queryFn: () =>
      notificacionService.listarRecibosConciliacion({
        fecha_caracas: fechaCaracas.trim() || undefined,
      }),
    enabled: activeTab === 'listado',
    placeholderData: previousData => previousData,
    retry: (failureCount, err) => {
      if (isAxiosError(err)) {
        const s = err.response?.status
        if (typeof s === 'number' && s >= 400 && s < 500) return false
      }
      return failureCount < 2
    },
  })

  const totalPagosListado = data?.total_pagos ?? 0
  const list: ReciboConciliacionFila[] = data?.pagos ?? []
  const kpiEnviados = data?.kpis?.correos_enviados ?? 0
  const kpiRebotados = data?.kpis?.correos_rebotados ?? 0
  const kpiRegDia = data?.kpis?.cedulas_registradas_envio_dia ?? 0
  const kpiCedVentana = data?.kpis?.cedulas_en_ventana_total ?? 0
  const kpiPagosVentana = data?.kpis?.pagos_en_ventana_total ?? 0
  const kpiRegistrosTotal = data?.kpis?.registros_envio_dia_total ?? 0
  const olasEnvio = data?.kpis?.olas_envio_recibos_dia ?? []

  useEffect(() => {
    setFiltroCedula('')
    setSortCol(null)
    setSortDir('asc')
    setPaginaRecibosListado(1)
  }, [fechaCaracas])

  useEffect(() => {
    setPaginaRecibosListado(1)
  }, [filtroCedula, sortCol, sortDir])

  const aplicarOrdenAsc = useCallback((c: NotificacionesCuotasSortCol) => {
    setSortCol(c)
    setSortDir('asc')
  }, [])

  const aplicarOrdenDesc = useCallback((c: NotificacionesCuotasSortCol) => {
    setSortCol(c)
    setSortDir('desc')
  }, [])

  const sortedList = useMemo(() => {
    if (!sortCol || list.length === 0) return list

    const cmp = (a: ReciboConciliacionFila, b: ReciboConciliacionFila): number => {
      switch (sortCol) {
        case 'nombre':
          return String(a.nombre ?? '').localeCompare(String(b.nombre ?? ''), 'es', {
            sensitivity: 'base',
          })
        case 'cedula':
          return String(a.cedula ?? '').localeCompare(String(b.cedula ?? ''), 'es', {
            sensitivity: 'base',
          })
        case 'fecha_registro':
          return String(a.fecha_registro ?? '').localeCompare(
            String(b.fecha_registro ?? '')
          )
        case 'monto_pagado': {
          const ma = Number(a.monto_pagado)
          const mb = Number(b.monto_pagado)
          const va = Number.isFinite(ma) ? ma : 0
          const vb = Number.isFinite(mb) ? mb : 0
          return va - vb
        }
        case 'numero_cuota': {
          const na = a.numero_cuota
          const nb = b.numero_cuota
          const va =
            na == null || Number.isNaN(Number(na))
              ? Number.POSITIVE_INFINITY
              : Number(na)
          const vb =
            nb == null || Number.isNaN(Number(nb))
              ? Number.POSITIVE_INFINITY
              : Number(nb)
          return va - vb
        }
        case 'fecha_vencimiento':
          return (
            fechaVencSortValue(a.fecha_vencimiento) -
            fechaVencSortValue(b.fecha_vencimiento)
          )
        case 'cuotas_atrasadas':
          return cuotasAtrasadasSortValue(a) - cuotasAtrasadasSortValue(b)
        case 'total_pendiente': {
          const va = numericTotalPendienteSort(a)
          const vb = numericTotalPendienteSort(b)
          const na = va == null ? Number.POSITIVE_INFINITY : va
          const nb = vb == null ? Number.POSITIVE_INFINITY : vb
          return na - nb
        }
        default:
          return 0
      }
    }

    const out = [...list]
    out.sort((a, b) => {
      const p = sortDir === 'asc' ? cmp(a, b) : -cmp(a, b)
      if (p !== 0) return p
      return a.pago_id - b.pago_id
    })
    return out
  }, [list, sortCol, sortDir])

  const listaFiltradaCedula = useMemo(() => {
    const q = filtroCedula.trim()
    if (!q) return sortedList
    return sortedList.filter(row => filaCoincideFiltroCedulaNotif(row, q))
  }, [sortedList, filtroCedula])

  const totalFilasListado = listaFiltradaCedula.length
  const totalPaginasListado = Math.max(1, Math.ceil(totalFilasListado / RECIBOS_LISTADO_PAGE_SIZE))

  useEffect(() => {
    if (paginaRecibosListado > totalPaginasListado) {
      setPaginaRecibosListado(totalPaginasListado)
    }
  }, [paginaRecibosListado, totalPaginasListado])

  const filasPaginaRecibos = useMemo(() => {
    const start = (paginaRecibosListado - 1) * RECIBOS_LISTADO_PAGE_SIZE
    return listaFiltradaCedula.slice(start, start + RECIBOS_LISTADO_PAGE_SIZE)
  }, [listaFiltradaCedula, paginaRecibosListado])

  const numerosPaginaRecibos = useMemo(
    () => numerosPaginaVisibles(paginaRecibosListado, totalPaginasListado, 5),
    [paginaRecibosListado, totalPaginasListado]
  )

  const handleDescargarEstadoCuentaPdf = async (prestamoId: number) => {
    setDescargandoEstadoCuentaId(prestamoId)
    try {
      await prestamoService.descargarEstadoCuentaPDF(prestamoId)
      toast.success('Estado de cuenta PDF descargado exitosamente')
    } catch (e) {
      console.error(e)
      toast.error('Error al exportar estado de cuenta PDF')
    } finally {
      setDescargandoEstadoCuentaId(null)
    }
  }

  const estadoCuentaPdfCell = (prestamoId: number | undefined) => {
    if (prestamoId == null) {
      return (
        <span className="text-xs text-gray-400" title="Sin id de préstamo">
          -
        </span>
      )
    }
    return (
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-9 w-9 shrink-0 text-blue-600 hover:bg-blue-50 hover:text-blue-800"
        disabled={descargandoEstadoCuentaId === prestamoId}
        onClick={() => void handleDescargarEstadoCuentaPdf(prestamoId)}
        title="Exportar estado de cuenta en PDF (mismo que en tabla de amortización)"
        aria-label="Exportar estado de cuenta en PDF"
      >
        <Download
          className={`h-4 w-4 ${
            descargandoEstadoCuentaId === prestamoId ? 'animate-pulse' : ''
          }`}
          aria-hidden
        />
      </Button>
    )
  }

  const tabNav = (
    <div className="border-b border-gray-200">
      <nav
        role="tablist"
        aria-label="Recibos: listado y configuración"
        className="flex flex-wrap gap-2"
      >
        <button
          type="button"
          role="tab"
          id="recibos-cfg-tab-listado"
          aria-selected={activeTab === 'listado'}
          aria-controls="recibos-cfg-panel-listado"
          onClick={() => setActiveTab('listado')}
          className={`flex items-center gap-2 rounded-t px-3 py-2 text-sm font-medium ${
            activeTab === 'listado'
              ? 'border border-b-0 border-gray-200 bg-white text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <LayoutList className="h-4 w-4" aria-hidden />
          Listado y envío
        </button>
        <button
          type="button"
          role="tab"
          id="recibos-cfg-tab-configuracion"
          aria-selected={activeTab === 'configuracion'}
          aria-controls="recibos-cfg-panel-config"
          onClick={() => setActiveTab('configuracion')}
          className={`flex items-center gap-2 rounded-t px-3 py-2 text-sm font-medium ${
            activeTab === 'configuracion'
              ? 'border border-b-0 border-gray-200 bg-white text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Settings className="h-4 w-4" aria-hidden />
          Configuración
        </button>
      </nav>
    </div>
  )

  if (activeTab === 'configuracion') {
    return (
      <div className="space-y-6">
        <ModulePageHeader
          icon={FileText}
          title="Recibos"
          description="Correo con PDF de estado de cuenta tras pagos conciliados (tabla pagos, vínculo cuotas). Zona America/Caracas."
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  void qc.invalidateQueries({
                    queryKey: [...RECIBOS_CONFIG_EMAIL_CUENTAS_QUERY_KEY],
                  })
                }}
              >
                <RefreshCw className="mr-2 h-4 w-4" aria-hidden />
                Actualización manual
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                className="border-red-400 text-red-800 hover:bg-red-50"
                onClick={() => setRecibosCfgResetSeq(s => s + 1)}
                title="Restablece la interfaz si Guardar o Prueba queda colgado (no cancela el servidor)."
              >
                <X className="mr-2 h-4 w-4" aria-hidden />
                Cancelar
              </Button>
            </div>
          }
        />

        {tabNav}

        <div
          role="tabpanel"
          id="recibos-cfg-panel-config"
          aria-labelledby="recibos-cfg-tab-configuracion"
        >
          <ConfiguracionRecibos emergencyResetSeq={recibosCfgResetSeq} />
        </div>
      </div>
    )
  }

  const hoyCaracasIso = fechaHoyIsoCaracas()
  const fechaCaracasTrim = fechaCaracas.trim()

  const ejecutar = async () => {
    if (data !== undefined && totalPagosListado === 0) {
      toast.warning(
        'No hay pagos en la ventana para la fecha indicada: no se envía correo a nadie. Actualice el listado o cambie la fecha (ventana 00:00–23:45 Caracas).'
      )
      return
    }
    if (fechaCaracasTrim && fechaCaracasTrim > hoyCaracasIso) {
      toast.error('No se permite envío real para una fecha futura (Caracas).')
      return
    }
    if (fechaCaracasTrim && fechaCaracasTrim < hoyCaracasIso) {
      toast.warning(
        'Para un día pasado use «Enviar lote pasado (real)» (confirmación explícita).'
      )
      return
    }
    setEnvioManualEnCurso(true)
    try {
      const out = await notificacionService.ejecutarRecibosEnvio({
        fecha_caracas: fechaCaracasTrim || undefined,
        solo_simular: false,
        forzar_envio_fecha_pasada: false,
      })
      if (respuestaRecibosTieneErrorNegocio(out)) {
        toast.error(mensajeRecibosRespuestaError(String(out.error)))
        await refetch()
        return
      }
      if (out.sin_casos_en_ventana === true) {
        toast('Sin casos en la ventana: no se envió ningún correo.')
        await refetch()
        return
      }
      const resumen = `enviados=${String(out.enviados)} fallidos=${String(out.fallidos)} cedulas=${String(out.cedulas_distintas)}`
      toast.success(`Envío manual: ${resumen}`)
      await refetch()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setEnvioManualEnCurso(false)
    }
  }

  const ejecutarLotePasadoReal = async () => {
    if (data !== undefined && totalPagosListado === 0) {
      toast.warning(
        'No hay pagos en la ventana para la fecha indicada: no se envía correo a nadie. Actualice el listado o cambie la fecha (ventana 00:00–23:45 Caracas).'
      )
      return
    }
    if (!fechaCaracasTrim) {
      toast.warning('Indique la fecha Caracas (YYYY-MM-DD) del lote pasado.')
      return
    }
    if (fechaCaracasTrim >= hoyCaracasIso) {
      toast.warning('El envío manual de lote pasado solo aplica a fechas anteriores a hoy (Caracas).')
      return
    }
    const ok = window.confirm(
      `¿Enviar correo REAL de Recibos?\n\nDía de corte (Caracas): ${fechaCaracasTrim}\nVentana: fecha_registro ese día 00:00–23:45 (America/Caracas).\n\n` +
        'Se respeta idempotencia (recibos_email_envio por cédula y día). Los destinatarios son los del cliente.'
    )
    if (!ok) return
    setEnvioLotePasadoEnCurso(true)
    try {
      const out = await notificacionService.ejecutarRecibosEnvio({
        fecha_caracas: fechaCaracasTrim,
        solo_simular: false,
        forzar_envio_fecha_pasada: true,
      })
      if (respuestaRecibosTieneErrorNegocio(out)) {
        toast.error(mensajeRecibosRespuestaError(String(out.error)))
        await refetch()
        return
      }
      if (out.sin_casos_en_ventana === true) {
        toast('Sin casos en la ventana: no se envió ningún correo.')
        await refetch()
        return
      }
      const resumen = `enviados=${String(out.enviados)} fallidos=${String(out.fallidos)} cedulas=${String(out.cedulas_distintas)}`
      toast.success(`Lote pasado: ${resumen}`)
      await refetch()
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setEnvioLotePasadoEnCurso(false)
    }
  }

  const simularEnvio = async () => {
    setSimulacionEnCurso(true)
    try {
      const out = await notificacionService.ejecutarRecibosEnvio({
        fecha_caracas: fechaCaracasTrim || undefined,
        solo_simular: true,
        forzar_envio_fecha_pasada: false,
      })
      if (respuestaRecibosTieneErrorNegocio(out)) {
        toast.error(mensajeRecibosRespuestaError(String(out.error)))
        return
      }
      if (out.sin_casos_en_ventana === true) {
        toast(
          'Simulación: sin casos en la ventana (ningún pago en la franja o ninguna cédula procesable).'
        )
        return
      }
      toast.success(
        `Simulación: ${String(out.cedulas_distintas)} cédula(s), ${String(out.pagos_en_ventana)} pago(s) en ventana. No se escribe recibos_email_envio; con modo pruebas activo puede enviarse muestra SMTP por cédula.`
      )
    } catch (e) {
      toast.error(getErrorMessage(e))
    } finally {
      setSimulacionEnCurso(false)
    }
  }

  const esFechaPasadaReal = Boolean(fechaCaracasTrim && fechaCaracasTrim < hoyCaracasIso)
  const accionRecibosEnCurso =
    envioManualEnCurso || envioLotePasadoEnCurso || simulacionEnCurso

  return (
    <div className="space-y-6">
      <ModulePageHeader
        icon={FileText}
        title="Recibos"
        description="Correo con PDF de estado de cuenta tras pagos conciliados (tabla pagos, vínculo cuotas). Zona America/Caracas."
      />

      {tabNav}

      <div role="tabpanel" id="recibos-cfg-panel-listado" aria-labelledby="recibos-cfg-tab-listado">
        <>
          <Card>
            <CardHeader>
              <CardTitle>Pendientes de envío</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="max-w-md space-y-2">
                <Label htmlFor="fecha-rec">Día de corte Caracas</Label>
                <Input
                  id="fecha-rec"
                  type="date"
                  className="max-w-[11.5rem]"
                  value={fechaCaracas}
                  title="Pagos con fecha_registro ese día en America/Caracas, 00:00–23:45 inclusive. Vacío = hoy."
                  onChange={e => setFechaCaracas(e.target.value)}
                  disabled={accionRecibosEnCurso}
                  helperText="Vacío = hoy. Ventana: 00:00–23:45 Caracas del día elegido."
                />
                <p className="text-xs text-muted-foreground">
                  Hoy (Caracas): <span className="font-mono">{hoyCaracasIso}</span>
                </p>
                <details className="rounded-md border border-slate-200 bg-slate-50/80 px-3 py-2 text-xs text-slate-700">
                  <summary className="cursor-pointer font-medium text-slate-900">
                    Ayuda: listado, ventana y envíos
                  </summary>
                  <div className="mt-2 space-y-2 leading-relaxed">
                    <p>
                      El listado muestra pagos pendientes de Recibos para el día de corte (aún sin registro
                      en <code className="text-[11px]">recibos_email_envio</code> para ese día).
                    </p>
                    <p>
                      <strong>Envío manual</strong> es SMTP real para <strong>hoy</strong> Caracas o fecha
                      vacía. Para un día anterior use <strong>Enviar lote pasado (real)</strong> (confirmación).
                    </p>
                    <p>
                      <strong>Simular</strong> recorre la misma lógica sin persistir envíos; con modo pruebas
                      en Configuración &gt; Correo puede enviarse muestra SMTP por cédula.
                    </p>
                    <p>
                      Los KPIs de <strong>envíos por lote</strong> listan cada ejecución manual que registró
                      filas en <code className="text-[11px]">recibos_email_envio</code> para el día de corte
                      elegido (misma ventana de <strong>fecha de registro</strong> 00:00–23:45 Caracas). Otro
                      día de corte en el calendario empieza la serie de nuevo.
                    </p>
                  </div>
                </details>
              </div>

              {isError ? (
                <div
                  className="flex flex-col gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-950 sm:flex-row sm:items-center sm:justify-between"
                  role="alert"
                >
                  <span>
                    No se pudo cargar el listado: {getErrorMessage(listadoError)}
                    {isPlaceholderData ? (
                      <>
                        {' '}
                        <span className="block pt-1 text-xs font-normal text-red-900/90">
                          La tabla debajo puede corresponder a la última fecha cargada con éxito;
                          corrija el día de corte o pulse Reintentar.
                        </span>
                      </>
                    ) : null}
                  </span>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="shrink-0 border-red-300 bg-white text-red-900 hover:bg-red-100"
                    onClick={() => void refetch()}
                  >
                    Reintentar
                  </Button>
                </div>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void refetch()}
                  disabled={isFetching || accionRecibosEnCurso}
                >
                  <RefreshCw
                    className={`mr-2 h-4 w-4 ${isFetching ? 'animate-spin' : ''}`}
                  />
                  Actualizar listado
                </Button>
                <Button
                  type="button"
                  onClick={() => void ejecutar()}
                  disabled={
                    isFetching ||
                    isError ||
                    accionRecibosEnCurso ||
                    (data !== undefined && totalPagosListado === 0)
                  }
                  aria-busy={envioManualEnCurso}
                  title={
                    data !== undefined && totalPagosListado === 0
                      ? 'No hay pagos pendientes en esta ventana para la fecha indicada.'
                      : esFechaPasadaReal
                        ? 'Para SMTP real con fecha anterior a hoy use «Enviar lote pasado (real)» (confirmación). Este botón solo envía el día de hoy (o fecha vacía = hoy).'
                        : envioManualEnCurso
                          ? 'Enviando correos y actualizando listado…'
                          : undefined
                  }
                >
                  {envioManualEnCurso ? (
                    <Loader2 className="mr-2 h-4 w-4 shrink-0 animate-spin" aria-hidden />
                  ) : (
                    <Mail className="mr-2 h-4 w-4 shrink-0" aria-hidden />
                  )}
                  {envioManualEnCurso ? 'Enviando…' : 'Envío manual'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void simularEnvio()}
                  disabled={isFetching || isError || accionRecibosEnCurso}
                  aria-busy={simulacionEnCurso}
                  title="Misma lógica que el envío real sin registrar recibos_email_envio. Permite cualquier fecha válida; con modo pruebas puede enviarse muestra SMTP."
                >
                  {simulacionEnCurso ? (
                    <Loader2 className="mr-2 h-4 w-4 shrink-0 animate-spin" aria-hidden />
                  ) : (
                    <TestTube className="mr-2 h-4 w-4 shrink-0" aria-hidden />
                  )}
                  {simulacionEnCurso ? 'Simulando…' : 'Simular'}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  className="border-amber-300 bg-amber-50 text-amber-950 hover:bg-amber-100"
                  onClick={() => void ejecutarLotePasadoReal()}
                  disabled={
                    isFetching ||
                    isError ||
                    accionRecibosEnCurso ||
                    (data !== undefined && totalPagosListado === 0) ||
                    !fechaCaracasTrim ||
                    fechaCaracasTrim >= hoyCaracasIso
                  }
                  aria-busy={envioLotePasadoEnCurso}
                  title={
                    envioLotePasadoEnCurso
                      ? 'Enviando lote y actualizando listado…'
                      : 'SMTP real para la fecha y franja seleccionadas (día anterior a hoy en Caracas).'
                  }
                >
                  {envioLotePasadoEnCurso ? (
                    <Loader2 className="mr-2 h-4 w-4 shrink-0 animate-spin" aria-hidden />
                  ) : (
                    <Mail className="mr-2 h-4 w-4 shrink-0" aria-hidden />
                  )}
                  {envioLotePasadoEnCurso ? 'Enviando lote…' : 'Enviar lote pasado (real)'}
                </Button>
              </div>

              {accionRecibosEnCurso ? (
                <p
                  className="flex items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-950"
                  role="status"
                  aria-live="polite"
                >
                  <Loader2 className="h-4 w-4 shrink-0 animate-spin text-blue-700" aria-hidden />
                  <span>
                    {envioManualEnCurso
                      ? 'Ejecutando envío manual Recibos (SMTP + registro en BD). Luego se actualiza el listado…'
                      : envioLotePasadoEnCurso
                        ? 'Ejecutando envío de lote pasado Recibos. Luego se actualiza el listado…'
                        : 'Ejecutando simulación Recibos (sin persistir envíos en BD)…'}
                  </span>
                </p>
              ) : null}

              {esFechaPasadaReal && totalPagosListado > 0 ? (
                <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                  La fecha indicada es <strong>anterior a hoy</strong> (Caracas). Para enviar correos
                  reales de ese día use <strong>«Enviar lote pasado (real)»</strong> (confirmación).{' '}
                  «Envío manual» solo corresponde al día de hoy o fecha vacía.
                </p>
              ) : null}

              {data !== undefined && totalPagosListado === 0 && !isFetching ? (
                <p className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                  No hay pagos pendientes en la ventana para esta fecha: «Envío manual» permanece
                  deshabilitado hasta que el listado muestre al menos un pago.
                </p>
              ) : null}

              {data ? (
                <p className="text-sm text-muted-foreground">
                  <strong>Fecha:</strong> {data.fecha_dia} · <strong>Id. ventana (BD):</strong> {data.slot} ·{' '}
                  <strong>Pagos pendientes:</strong> {data.total_pagos} · <strong>Cédulas distintas:</strong>{' '}
                  {data.cedulas_distintas}
                </p>
              ) : null}

              <div className="mb-2 space-y-4">
                <div className="rounded-lg border border-indigo-200 bg-indigo-50/90 p-4">
                  <div className="mb-3 flex flex-wrap items-start gap-2">
                    <Mail className="mt-0.5 h-6 w-6 shrink-0 text-indigo-600" aria-hidden />
                    <div>
                      <p className="text-sm font-semibold text-indigo-950">
                        Envíos por ejecución (día de corte {data?.fecha_dia ?? '—'})
                      </p>
                      <p className="mt-1 text-[11px] leading-snug text-indigo-900/90">
                        Cada ítem es un lote registrado en <code className="text-[10px]">recibos_email_envio</code>{' '}
                        al completar un envío manual: 1.er envío, 2.o envío, … según el instante de registro
                        en BD (un commit por ejecución, PostgreSQL). La ventana sigue siendo la de{' '}
                        <strong>fecha de registro</strong> 00:00–23:45 Caracas de ese día.
                      </p>
                    </div>
                  </div>
                  {olasEnvio.length === 0 ? (
                    <p className="text-sm text-indigo-900/80">
                      Sin envíos registrados aún para este día de corte.
                    </p>
                  ) : (
                    <ul
                      className="divide-y divide-indigo-100/90 text-sm text-indigo-950"
                      role="list"
                      aria-label="Envíos por lote en orden cronológico"
                    >
                      {olasEnvio.map(o => (
                        <li
                          key={`ola-${o.orden}-${o.creado_en}`}
                          className="flex flex-col gap-1 py-2.5 first:pt-0 last:pb-0 sm:flex-row sm:items-baseline sm:justify-between sm:gap-6"
                        >
                          <span className="shrink-0 font-semibold text-indigo-950">
                            {etiquetaOrdinalEnvioRecibos(o.orden)}
                          </span>
                          <span className="min-w-0 text-indigo-900 sm:text-right">
                            <span className="tabular-nums font-semibold text-indigo-950">
                              {o.correos_registrados_lote ?? 0}
                            </span>{' '}
                            correo(s) registrado(s){' '}
                            <span className="text-indigo-700/85">·</span>{' '}
                            <span className="text-indigo-800/90">
                              {fmtInstanteRegistroRecibosCaracas(o.creado_en)} (Caracas)
                            </span>
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                  <p className="mt-3 border-t border-indigo-200/80 pt-2 text-xs text-indigo-900/90">
                    <span className="font-medium">Resumen día de corte:</span>{' '}
                    <span className="tabular-nums font-semibold">{kpiRegistrosTotal}</span> filas en BD
                    (suma de lotes){' '}
                    <span className="text-indigo-800/80">·</span>{' '}
                    <span className="tabular-nums font-semibold">{kpiRegDia}</span> cédulas distintas con
                    registro / <span className="tabular-nums font-semibold">{kpiCedVentana}</span> cédulas
                    distintas en ventana de pagos
                  </p>
                </div>
                <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <LayoutList className="h-8 w-8 shrink-0 text-slate-600" aria-hidden />
                  <div className="min-w-0">
                    <p className="text-2xl font-bold tabular-nums text-slate-900">
                      {kpiPagosVentana}
                      <span className="text-lg font-semibold text-slate-600">
                        {' '}
                        · {totalPagosListado} pend.
                      </span>
                    </p>
                    <p className="text-xs font-medium text-slate-800">Pagos en ventana (00:00–23:45)</p>
                    <p className="mt-1 text-[11px] leading-snug text-slate-600">
                      Total pagos con <strong>fecha de registro</strong> en la franja vs. pendientes de envío
                      Recibos en la tabla.
                    </p>
                  </div>
                </div>
              </div>
              <p className="mb-2 text-center text-xs text-muted-foreground">
                Histórico global Recibos (todos los días):{' '}
                <span className="font-semibold tabular-nums text-foreground">{kpiEnviados}</span> envíos
                exitosos ·{' '}
                <span className="font-semibold tabular-nums text-foreground">{kpiRebotados}</span> fallidos
                en <code className="text-[10px]">envios_notificacion</code>.
              </p>

              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div className="max-w-md flex-1 space-y-2">
                  <Label htmlFor="filtro-ced-rec">Filtrar por cédula</Label>
                  <Input
                    id="filtro-ced-rec"
                    placeholder="Ej. V12345678 o dígitos"
                    value={filtroCedula}
                    onChange={e => setFiltroCedula(e.target.value)}
                  />
                </div>
                {filtroCedula.trim() && list.length > 0 ? (
                  <p className="text-xs text-muted-foreground sm:ml-auto">
                    Mostrando{' '}
                    <span className="font-semibold tabular-nums text-foreground">
                      {listaFiltradaCedula.length}
                    </span>{' '}
                    de <span className="tabular-nums">{list.length}</span> filas
                  </p>
                ) : null}
              </div>

              {isFetching && !data ? (
                <div className="flex items-center gap-2 rounded border border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-700">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>Cargando datos…</span>
                </div>
              ) : null}

              <Fragment>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[600px] text-sm">
                    <thead>
                      <tr className="border-b bg-gray-50">
                        <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                          <div className="inline-flex items-center gap-1">
                            <span>Nombre</span>
                            <SortArrowsCuotas
                              column="nombre"
                              labelAsc="Orden ascendente: nombre"
                              labelDesc="Orden descendente: nombre"
                              sortCol={sortCol}
                              sortDir={sortDir}
                              onAsc={aplicarOrdenAsc}
                              onDesc={aplicarOrdenDesc}
                            />
                          </div>
                        </th>
                        <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                          <div className="inline-flex items-center gap-1">
                            <span>Cédula</span>
                            <SortArrowsCuotas
                              column="cedula"
                              labelAsc="Orden ascendente: cédula"
                              labelDesc="Orden descendente: cédula"
                              sortCol={sortCol}
                              sortDir={sortDir}
                              onAsc={aplicarOrdenAsc}
                              onDesc={aplicarOrdenDesc}
                            />
                          </div>
                        </th>
                        <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                          <div className="inline-flex items-center gap-1">
                            <span>Fecha de registro</span>
                            <SortArrowsCuotas
                              column="fecha_registro"
                              labelAsc="Orden ascendente: fecha de registro"
                              labelDesc="Orden descendente: fecha de registro"
                              sortCol={sortCol}
                              sortDir={sortDir}
                              onAsc={aplicarOrdenAsc}
                              onDesc={aplicarOrdenDesc}
                            />
                          </div>
                        </th>
                        <th className="whitespace-nowrap px-3 py-2 text-right font-semibold">
                          <div className="inline-flex items-center justify-end gap-1">
                            <span>Monto pagado</span>
                            <SortArrowsCuotas
                              column="monto_pagado"
                              labelAsc="Orden ascendente: monto pagado"
                              labelDesc="Orden descendente: monto pagado"
                              sortCol={sortCol}
                              sortDir={sortDir}
                              onAsc={aplicarOrdenAsc}
                              onDesc={aplicarOrdenDesc}
                            />
                          </div>
                        </th>
                        <th className="min-w-[10rem] px-3 py-2 text-left font-semibold">
                          Fotografía de pago
                        </th>
                        <th className="w-14 whitespace-nowrap px-2 py-2 text-center font-semibold">
                          <span title="Descargar PDF de estado de cuenta">Estado de cuenta</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {listaFiltradaCedula.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="py-8 text-center text-gray-500">
                            <span className="block font-medium text-gray-600">
                              {list.length === 0
                                ? 'Ningún registro en este criterio.'
                                : 'Ninguna fila coincide con la cédula indicada.'}
                            </span>
                          </td>
                        </tr>
                      ) : (
                        filasPaginaRecibos.map(row => (
                          <tr
                            key={`rec-${row.pago_id}`}
                            className="border-b border-gray-200 bg-white hover:bg-gray-50"
                          >
                            <td className="px-3 py-3 font-medium">{row.nombre}</td>
                            <td className="px-3 py-3">{row.cedula}</td>
                            <td className="px-3 py-3 tabular-nums text-gray-800">
                              {textoFechaRegistroListado(row.fecha_registro)}
                            </td>
                            <td className="px-3 py-3 text-right font-medium tabular-nums text-gray-900">
                              {textoMontoPagadoRecibo(row.monto_pagado)}
                            </td>
                            <td className="px-3 py-3 align-middle">
                              <CeldaFotografiaPagoRecibo row={row} />
                            </td>
                            <td className="px-2 py-3 text-center align-middle">
                              {estadoCuentaPdfCell(row.prestamo_id)}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>

                {totalFilasListado > 0 ? (
                  <nav
                    className="mt-6 flex flex-col items-center gap-3"
                    aria-label="Paginación del listado Recibos"
                  >
                    <div className="flex flex-wrap items-center justify-center gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="rounded-md border-gray-300"
                        disabled={paginaRecibosListado <= 1}
                        onClick={() => setPaginaRecibosListado(p => Math.max(1, p - 1))}
                      >
                        ← Anterior
                      </Button>
                      {numerosPaginaRecibos.map(n => (
                        <Button
                          key={`rec-pag-${n}`}
                          type="button"
                          variant="outline"
                          size="sm"
                          className={
                            n === paginaRecibosListado
                              ? 'min-w-[2.25rem] rounded-md border-blue-600 bg-blue-600 text-white shadow-none hover:bg-blue-700 hover:text-white'
                              : 'min-w-[2.25rem] rounded-md border-gray-300 bg-white text-gray-900 hover:bg-gray-50'
                          }
                          aria-current={n === paginaRecibosListado ? 'page' : undefined}
                          onClick={() => setPaginaRecibosListado(n)}
                        >
                          {n}
                        </Button>
                      ))}
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="rounded-md border-gray-300"
                        disabled={paginaRecibosListado >= totalPaginasListado}
                        onClick={() =>
                          setPaginaRecibosListado(p => Math.min(totalPaginasListado, p + 1))
                        }
                      >
                        Siguiente →
                      </Button>
                    </div>
                    <p className="text-center text-sm text-muted-foreground">
                      Página {paginaRecibosListado} de {totalPaginasListado}
                    </p>
                  </nav>
                ) : null}
              </Fragment>
            </CardContent>
          </Card>
        </>
      </div>
    </div>
  )
}
