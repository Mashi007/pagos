import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  Fragment,
} from 'react'

import { useSearchParams } from 'react-router-dom'

import { useQuery, useQueryClient } from '@tanstack/react-query'

import {
  AlertTriangle,
  Download,
  FileText,
  LayoutList,
  Mail,
  RefreshCw,
  Settings,
  X,
} from 'lucide-react'

import { Button } from '../components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
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
  type ClienteRetrasadoItem,
  type ReciboConciliacionFila,
} from '../services/notificacionService'
import { prestamoService } from '../services/prestamoService'
import { toast } from 'sonner'
import { getErrorMessage } from '../types/errors'
import {
  CompararAbonosDriveCuotasCell,
  RevisionManualNotifCell,
  SortArrowsCuotas,
  filaCoincideFiltroCedulaNotif,
  type NotificacionesCuotasSortCol,
} from './notificaciones/notificacionesPageCells'
import {
  cuotasAtrasadasSortValue,
  fechaVencSortValue,
  numericTotalPendienteSort,
  textoNumeroCreditoNotif,
  textoTotalPendientePagar,
} from './notificaciones/notificacionesListSort'

type Slot = 'manana' | 'tarde' | 'noche'

type TabId = 'listado' | 'configuracion'

const SLOT_LABEL: Record<Slot, string> = {
  manana: 'Mañana (01:00–11:00) → envío programado 11:05',
  tarde: 'Tarde (11:01–17:00) → envío programado 17:05',
  noche: 'Noche (17:01–23:45) → envío programado 23:55',
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

  const [slot, setSlot] = useState<Slot>('manana')
  const [fechaCaracas, setFechaCaracas] = useState('')
  const [soloSimular, setSoloSimular] = useState(true)
  const [filtroCedula, setFiltroCedula] = useState('')
  const [sortCol, setSortCol] = useState<NotificacionesCuotasSortCol | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')
  const [descargandoEstadoCuentaId, setDescargandoEstadoCuentaId] = useState<
    number | null
  >(null)

  const listadoKey = useMemo(
    () => ['notificaciones', 'recibos', 'listado', slot, fechaCaracas || 'hoy'],
    [slot, fechaCaracas]
  )

  const { data, isFetching, refetch } = useQuery({
    queryKey: listadoKey,
    queryFn: () =>
      notificacionService.listarRecibosConciliacion({
        slot,
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
  }, [slot, fechaCaracas])

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

    const cmp = (a: ClienteRetrasadoItem, b: ClienteRetrasadoItem): number => {
      switch (sortCol) {
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
      return String(a.cliente_id).localeCompare(String(b.cliente_id))
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

  const ejecutar = async () => {
    if (!soloSimular && data !== undefined && totalPagosListado === 0) {
      toast.warning(
        'No hay pagos en la ventana para la fecha indicada: no se envía correo a nadie. Actualice el listado o cambie fecha/franja.'
      )
      return
    }
    try {
      const out = await notificacionService.ejecutarRecibosEnvio({
        slot,
        fecha_caracas:
          soloSimular && fechaCaracas.trim() ? fechaCaracas.trim() : undefined,
        solo_simular: soloSimular,
      })
      if (out.sin_casos_en_ventana === true) {
        toast('Sin casos en la ventana: no se envió ningún correo.')
        void refetch()
        return
      }
      const resumen = `enviados=${String(out.enviados)} fallidos=${String(out.fallidos)} cedulas=${String(out.cedulas_distintas)}`
      toast.success(
        soloSimular ? `Simulación: ${resumen}` : `Ejecución: ${resumen}`
      )
      void refetch()
    } catch (e) {
      toast.error(getErrorMessage(e))
    }
  }

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
              <CardTitle>Criterio en base de datos</CardTitle>
              <CardDescription>
                Se listan filas de <strong>pagos</strong> con <code>conciliado=true</code>,{' '}
                <code>estado=PAGADO</code> y <code>fecha_registro</code> en la ventana indicada. Deben
                estar aplicadas a cuotas (<code>cuotas.pago_id</code> o <code>cuota_pagos</code>). La
                cédula del pago determina el cliente; el PDF es el mismo flujo que el portal (
                <code>obtener_datos_estado_cuenta_cliente</code>).
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 text-sm text-slate-700">
              <p>{SLOT_LABEL[slot]}</p>
              <p>
                Remitente From: variable de entorno <code>RECIBOS_FROM_EMAIL</code> (por defecto{' '}
                <code>notificacion@rapicreditca.com</code>). Cuenta SMTP según pestaña Configuración
                (asignación <code>recibos</code>).
              </p>
              <p>
                Jobs automáticos: <code>ENABLE_AUTOMATIC_SCHEDULED_JOBS</code> y{' '}
                <code>ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS</code> en el servidor.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Vista previa y ejecución</CardTitle>
              <CardDescription>
                Franja y fecha opcional para listado y simulación. El envío real solo usa hoy (Caracas),
                igual que el job programado según fecha de recepción (<code>fecha_registro</code>); no
                envía lotes de otro día. «Solo simular» no envía correos ni escribe idempotencia.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="slot-rec">Franja</Label>
                  <select
                    id="slot-rec"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={slot}
                    onChange={e => setSlot(e.target.value as Slot)}
                  >
                    <option value="manana">Mañana (01:00–11:00)</option>
                    <option value="tarde">Tarde (11:01–17:00)</option>
                    <option value="noche">Noche (17:01–23:45)</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="fecha-rec">Fecha Caracas (YYYY-MM-DD)</Label>
                  <Input
                    id="fecha-rec"
                    placeholder="Vacío = hoy"
                    value={fechaCaracas}
                    disabled={!soloSimular}
                    title={
                      soloSimular
                        ? 'Opcional: otra fecha para listar o simular'
                        : 'El envío real solo acepta hoy Caracas; active simulación para otra fecha'
                    }
                    onChange={e => setFechaCaracas(e.target.value)}
                  />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={soloSimular}
                  onChange={e => {
                    const v = e.target.checked
                    setSoloSimular(v)
                    if (!v) setFechaCaracas('')
                  }}
                />
                Solo simular (sin SMTP ni tabla recibos_email_envio)
              </label>
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
                    (!soloSimular && data !== undefined && totalPagosListado === 0)
                  }
                >
                  <Mail className="mr-2 h-4 w-4" />
                  {soloSimular ? 'Simular envío' : 'Ejecutar envío'}
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
                  <table className="w-full min-w-[640px] text-sm">
                    <thead>
                      <tr className="border-b bg-gray-50">
                        <th className="whitespace-nowrap px-3 py-2 text-left text-xs font-semibold leading-tight">
                          Número de
                          <br />
                          crédito
                        </th>
                        <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                          Nombre
                        </th>
                        <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                          Cédula
                        </th>
                        <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                          <div className="inline-flex items-center gap-1">
                            <span>Nº cuota</span>
                            <SortArrowsCuotas
                              column="numero_cuota"
                              labelAsc="Orden ascendente: Nº cuota"
                              labelDesc="Orden descendente: Nº cuota"
                              sortCol={sortCol}
                              sortDir={sortDir}
                              onAsc={aplicarOrdenAsc}
                              onDesc={aplicarOrdenDesc}
                            />
                          </div>
                        </th>
                        <th className="whitespace-nowrap px-3 py-2 text-left font-semibold">
                          <div className="inline-flex items-center gap-1">
                            <span>Fecha venc.</span>
                            <SortArrowsCuotas
                              column="fecha_vencimiento"
                              labelAsc="Orden ascendente: fecha de vencimiento"
                              labelDesc="Orden descendente: fecha de vencimiento"
                              sortCol={sortCol}
                              sortDir={sortDir}
                              onAsc={aplicarOrdenAsc}
                              onDesc={aplicarOrdenDesc}
                            />
                          </div>
                        </th>
                        <th className="whitespace-nowrap px-3 py-2 text-right font-semibold">
                          <div className="inline-flex w-full items-center justify-end gap-1">
                            <span>Cuotas atrasadas</span>
                            <SortArrowsCuotas
                              column="cuotas_atrasadas"
                              labelAsc="Orden ascendente: cuotas atrasadas"
                              labelDesc="Orden descendente: cuotas atrasadas"
                              sortCol={sortCol}
                              sortDir={sortDir}
                              onAsc={aplicarOrdenAsc}
                              onDesc={aplicarOrdenDesc}
                            />
                          </div>
                        </th>
                        <th className="max-w-[12rem] whitespace-normal px-3 py-2 text-right font-semibold leading-tight">
                          <div className="inline-flex items-start justify-end gap-1">
                            <span>
                              TOTAL PENDIENTE
                              <br />A PAGAR
                            </span>
                            <SortArrowsCuotas
                              column="total_pendiente"
                              labelAsc="Orden ascendente: total pendiente"
                              labelDesc="Orden descendente: total pendiente"
                              sortCol={sortCol}
                              sortDir={sortDir}
                              onAsc={aplicarOrdenAsc}
                              onDesc={aplicarOrdenDesc}
                            />
                          </div>
                        </th>
                        <th
                          className="min-w-[5.5rem] px-1 py-2 text-center text-xs font-semibold leading-tight"
                          scope="col"
                        >
                          Revisión
                          <br />
                          manual
                        </th>
                        <th className="w-14 whitespace-nowrap px-2 py-2 text-center font-semibold">
                          <span title="Descargar PDF de estado de cuenta">Estado de cuenta</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {listaFiltradaCedula.length === 0 ? (
                        <tr>
                          <td colSpan={8} className="py-8 text-center text-gray-500">
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
                            key={`rec-${row.pago_id}-${row.prestamo_id ?? 'np'}-${row.numero_cuota ?? 'nc'}`}
                            className="border-b hover:bg-gray-50"
                          >
                            <td className="px-3 py-2 font-medium tabular-nums">
                              {textoNumeroCreditoNotif(row)}
                            </td>
                            <td className="px-3 py-2 font-medium">{row.nombre}</td>
                            <td className="px-3 py-2">{row.cedula}</td>
                            <td className="px-3 py-2">{row.numero_cuota ?? '-'}</td>
                            <td className="px-3 py-2">{row.fecha_vencimiento ?? '-'}</td>
                            <td className="px-3 py-2 text-right font-medium text-red-600">
                              {row.cuotas_atrasadas ?? row.total_cuotas_atrasadas ?? '-'}
                            </td>
                            <td className="px-3 py-2 text-right">
                              {textoTotalPendientePagar(row)}
                            </td>
                            <td className="px-1 py-2 text-center align-middle">
                              <div className="flex flex-wrap items-center justify-center gap-1">
                                <RevisionManualNotifCell row={row} />
                                <CompararAbonosDriveCuotasCell row={row} />
                              </div>
                            </td>
                            <td className="px-2 py-2 text-center align-middle">
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
