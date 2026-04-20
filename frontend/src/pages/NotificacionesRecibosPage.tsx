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
} from '../services/notificacionService'
import { apiClient } from '../services/api'
import { pathApiComprobanteImagenDesdeHref } from '../utils/comprobanteImagenAuth'
import { prestamoService } from '../services/prestamoService'
import { toast } from 'sonner'
import { getErrorMessage } from '../types/errors'
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

/** Día calendario America/Caracas en YYYY-MM-DD (alineado al backend). */
function fechaHoyIsoCaracas(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Caracas',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
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

  const listadoKey = useMemo(
    () => ['notificaciones', 'recibos', 'listado', fechaCaracas || 'hoy'],
    [fechaCaracas]
  )

  const { data, isFetching, refetch } = useQuery({
    queryKey: listadoKey,
    queryFn: () =>
      notificacionService.listarRecibosConciliacion({
        fecha_caracas: fechaCaracas.trim() || undefined,
      }),
    enabled: activeTab === 'listado',
  })

  const totalPagosListado = data?.total_pagos ?? 0
  const list: ReciboConciliacionFila[] = data?.pagos ?? []
  const kpiEnviados = data?.kpis?.correos_enviados ?? 0
  const kpiRebotados = data?.kpis?.correos_rebotados ?? 0

  useEffect(() => {
    setFiltroCedula('')
    setSortCol(null)
    setSortDir('asc')
  }, [fechaCaracas])

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
          Listado y ejecución
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
        'No hay pagos en la ventana para la fecha indicada: no se envía correo a nadie. Actualice el listado o cambie fecha/franja.'
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
    try {
      const out = await notificacionService.ejecutarRecibosEnvio({
        fecha_caracas: fechaCaracasTrim || undefined,
        solo_simular: false,
        forzar_envio_fecha_pasada: false,
      })
      if (out.sin_casos_en_ventana === true) {
        toast('Sin casos en la ventana: no se envió ningún correo.')
        void refetch()
        return
      }
      const resumen = `enviados=${String(out.enviados)} fallidos=${String(out.fallidos)} cedulas=${String(out.cedulas_distintas)}`
      toast.success(`Envío manual: ${resumen}`)
      void refetch()
    } catch (e) {
      toast.error(getErrorMessage(e))
    }
  }

  const ejecutarLotePasadoReal = async () => {
    if (data !== undefined && totalPagosListado === 0) {
      toast.warning(
        'No hay pagos en la ventana para la fecha indicada: no se envía correo a nadie. Actualice el listado o cambie fecha/franja.'
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
      `¿Enviar correo REAL de Recibos?\n\nDía de corte (Caracas): ${fechaCaracasTrim}\nVentana: 24 h hasta las 15:00 de ese día.\n\n` +
        'Se respeta idempotencia (recibos_email_envio por cédula y día). Los destinatarios son los del cliente.'
    )
    if (!ok) return
    try {
      const out = await notificacionService.ejecutarRecibosEnvio({
        fecha_caracas: fechaCaracasTrim,
        solo_simular: false,
        forzar_envio_fecha_pasada: true,
      })
      if (out.sin_casos_en_ventana === true) {
        toast('Sin casos en la ventana: no se envió ningún correo.')
        void refetch()
        return
      }
      const resumen = `enviados=${String(out.enviados)} fallidos=${String(out.fallidos)} cedulas=${String(out.cedulas_distintas)}`
      toast.success(`Lote pasado: ${resumen}`)
      void refetch()
    } catch (e) {
      toast.error(getErrorMessage(e))
    }
  }

  const esFechaPasadaReal = Boolean(fechaCaracasTrim && fechaCaracasTrim < hoyCaracasIso)

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
              <CardTitle>Vista previa y ejecución</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="max-w-md space-y-2">
                <Label htmlFor="fecha-rec">Día de corte Caracas (YYYY-MM-DD)</Label>
                <Input
                  id="fecha-rec"
                  placeholder="Vacío = hoy — ventana: 24 h hasta las 15:00 de ese día"
                  value={fechaCaracas}
                  title="Define el fin de la ventana (15:00 Caracas de ese día); el inicio es 24 h antes."
                  onChange={e => setFechaCaracas(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Hoy (Caracas): <span className="font-mono">{hoyCaracasIso}</span>
                </p>
              </div>
              <p className="text-sm text-muted-foreground">
                El envío manual usa SMTP real a los correos del cliente (misma lógica que el job del día
                en curso). Respete modo pruebas / correo activo en Configuración Recibos.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void refetch()}
                  disabled={isFetching}
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
                    (data !== undefined && totalPagosListado === 0) ||
                    esFechaPasadaReal
                  }
                  title={
                    esFechaPasadaReal
                      ? 'Use «Enviar lote pasado (real)» para envío SMTP de una fecha anterior a hoy.'
                      : undefined
                  }
                >
                  <Mail className="mr-2 h-4 w-4" />
                  Envío manual
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  className="border-amber-300 bg-amber-50 text-amber-950 hover:bg-amber-100"
                  onClick={() => void ejecutarLotePasadoReal()}
                  disabled={
                    isFetching ||
                    (data !== undefined && totalPagosListado === 0) ||
                    !fechaCaracasTrim ||
                    fechaCaracasTrim >= hoyCaracasIso
                  }
                  title="SMTP real para la fecha y franja seleccionadas (día anterior a hoy en Caracas)."
                >
                  <Mail className="mr-2 h-4 w-4" />
                  Enviar lote pasado (real)
                </Button>
              </div>

              {data ? (
                <p className="text-sm text-muted-foreground">
                  <strong>Fecha:</strong> {data.fecha_dia} · <strong>Franja:</strong> {data.slot} ·{' '}
                  <strong>Pagos:</strong> {data.total_pagos} · <strong>Cédulas distintas:</strong>{' '}
                  {data.cedulas_distintas}
                </p>
              ) : null}

              <div className="mb-2 grid grid-cols-2 gap-4 sm:grid-cols-2">
                <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 p-4">
                  <Mail className="h-8 w-8 text-green-600" aria-hidden />
                  <div>
                    <p className="text-2xl font-bold text-green-800">{kpiEnviados}</p>
                    <p className="text-xs font-medium text-green-700">Correos enviados</p>
                    <p className="mt-1 text-[11px] text-green-700/90">
                      Histórico Recibos (tipo_tab <code className="text-[10px]">recibos</code> en BD)
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4">
                  <AlertTriangle className="h-8 w-8 text-red-600" aria-hidden />
                  <div>
                    <p className="text-2xl font-bold text-red-800">{kpiRebotados}</p>
                    <p className="text-xs font-medium text-red-700">Correos rebotados</p>
                    <p className="mt-1 text-[11px] text-red-700/90">
                      Envíos con fallo SMTP u error de entrega en Recibos
                    </p>
                  </div>
                </div>
              </div>

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
                        listaFiltradaCedula.map(row => (
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
              </Fragment>
            </CardContent>
          </Card>
        </>
      </div>
    </div>
  )
}
