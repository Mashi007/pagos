import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'

import {
  BarChart3,
  Bell,
  CheckCircle2,
  Download,
  Eye,
  Loader2,
  Lock,
  RefreshCw,
  Search,
  X,
  XCircle,
} from 'lucide-react'

import { toast } from 'sonner'

import { Button } from '../components/ui/button'

import { FiniquitoWorkspaceShell } from '../components/finiquito/FiniquitoWorkspaceShell'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog'

import {
  type FiniquitoCasoItem,
  finiquitoAdminConteoRevisionNuevos,
  finiquitoAdminListar,
  finiquitoAdminListarTerminados,
  finiquitoAdminPatchEstado,
  finiquitoAdminRefreshMaterializado,
  finiquitoAdminResumenTerminadosSemanal,
  type FiniquitoRefreshStats,
  type FiniquitoTerminadoItem,
  FINIQUITO_HORAS_NUEVOS_REVISION_DEFAULT,
} from '../services/finiquitoService'
import { descargarTerminadosExcel } from '../utils/finiquitoTerminadosExcelExport'
import { prestamoService } from '../services/prestamoService'

import { cn, formatCurrency, formatDate } from '../utils'
import { invalidatePrestamosQueries } from '../hooks/usePrestamos'
import { usePermissions } from '../hooks/usePermissions'
import { Card, CardContent } from '../components/ui/card'

function textoUltimoPago(iso: string | null | undefined): string {
  if (iso == null || String(iso).trim() === '') return '-'
  try {
    return formatDate(String(iso))
  } catch {
    return String(iso)
  }
}

const DIAS_REVISION_SIN_ATRASO = 3
const DIAS_LIMITE_AREA_TRABAJO = 30

function diasDesdeFechaLiquidado(fechaLiquidado: string | null | undefined) {
  if (fechaLiquidado == null || String(fechaLiquidado).trim() === '') {
    return null
  }
  const d = new Date(`${String(fechaLiquidado).slice(0, 10)}T00:00:00`)
  if (Number.isNaN(d.getTime())) return null
  const hoy = new Date()
  hoy.setHours(0, 0, 0, 0)
  return Math.floor((hoy.getTime() - d.getTime()) / 86_400_000)
}

function casoRevisionAtrasado(caso: FiniquitoCasoItem): boolean {
  if (caso.estado !== 'REVISION') return false
  const dias = diasDesdeFechaLiquidado(caso.fecha_liquidado)
  return dias != null && dias > DIAS_REVISION_SIN_ATRASO
}

function diasRestantesAreaTrabajo(caso: FiniquitoCasoItem): number | null {
  const diasTranscurridos = diasDesdeFechaLiquidado(caso.ultima_fecha_pago)
  if (diasTranscurridos == null) return null
  return DIAS_LIMITE_AREA_TRABAJO - diasTranscurridos
}

function textoTiempoLimiteAreaTrabajo(caso: FiniquitoCasoItem): string {
  const dias = diasRestantesAreaTrabajo(caso)
  if (dias == null) return '-'
  if (dias <= 0) return 'Atrasado'
  return `${dias} ${dias === 1 ? 'día' : 'días'}`
}

function tiempoLimiteAreaTrabajoClassName(caso: FiniquitoCasoItem): string {
  const dias = diasRestantesAreaTrabajo(caso)
  if (dias == null) return 'bg-slate-100 text-slate-700'
  if (dias <= 0) return 'bg-red-100 text-red-950'
  if (dias <= 3) return 'bg-amber-100 text-amber-950'
  return 'bg-emerald-100 text-emerald-950'
}

function estadoEtiquetaVisible(caso: FiniquitoCasoItem): string {
  const estado = caso.estado
  if (casoRevisionAtrasado(caso)) return 'Atrasado'
  const map: Record<string, string> = {
    REVISION: 'Revisión',
    ACEPTADO: 'Aceptado',
    RECHAZADO: 'Rechazado',
    EN_PROCESO: 'En proceso',
    TERMINADO: 'Terminado',
  }
  return map[estado] ?? estado.replace(/_/g, ' ')
}

function estadoBadgeClassName(caso: FiniquitoCasoItem): string {
  if (casoRevisionAtrasado(caso)) return 'bg-red-100 text-red-950'
  switch (caso.estado) {
    case 'REVISION':
      return 'bg-sky-100 text-sky-950'
    case 'ACEPTADO':
      return 'bg-slate-100 text-slate-800'
    case 'RECHAZADO':
      return 'bg-rose-100 text-rose-950'
    case 'EN_PROCESO':
      return 'bg-amber-100 text-amber-950'
    case 'TERMINADO':
      return 'bg-emerald-100 text-emerald-950'
    default:
      return 'bg-slate-100 text-slate-800'
  }
}

const thGestion =
  'h-9 whitespace-nowrap bg-slate-800 px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-white'

const tdGestion = 'px-3 py-2.5 align-middle text-sm text-slate-900'

const trEven = 'border-b border-slate-200 bg-white hover:bg-slate-50/90'

const trOdd = 'border-b border-slate-200 bg-slate-50/80 hover:bg-slate-100/80'

function textoToastRefresco(r: FiniquitoRefreshStats): {
  titulo: string
  descripcion: string
} {
  const ins = r.insertados ?? 0
  const act = r.actualizados ?? 0
  const eli = r.eliminados ?? 0
  const elg = r.elegibles ?? 0
  return {
    titulo: `Refresco: ${elg} elegibles · ${ins} nuevos · ${act} actualizados`,
    descripcion:
      ins === 0 && elg > 0
        ? 'Insertados 0 es normal si esos préstamos ya estaban en finiquito. Los saldados se muestran en la bandeja principal.'
        : `Quitados del listado (ya no califican): ${eli}. Revise el filtro de bandeja si no ve filas.`,
  }
}

const DEBOUNCE_MS = 420

/** Coincide con backend `_ADMIN_CASOS_MAX_LIMIT` para bandejas pequeñas. */
const FETCH_LIMIT = 2000
const BANDEJA_PRINCIPAL_FETCH_LIMIT = 100

function casoCoincideCedula(caso: FiniquitoCasoItem, filtro: string): boolean {
  const f = filtro.trim().toLowerCase()
  if (!f) return true
  return String(caso.cedula || '')
    .toLowerCase()
    .includes(f)
}

function textoFechaTabla(iso: string | null | undefined): string {
  if (iso == null || String(iso).trim() === '') return '-'
  try {
    return formatDate(String(iso))
  } catch {
    return String(iso)
  }
}

type FiltrosTerminadosTabla = {
  nombre: string
  total: string
  fechaAprobacion: string
  fechaTerminoPago: string
  fechaTerminado: string
}

function terminadoCoincideFiltroTexto(
  valor: string,
  filtro: string
): boolean {
  const f = filtro.trim().toLowerCase()
  if (!f) return true
  return valor.toLowerCase().includes(f)
}

function terminadoCoincideFiltroFecha(
  iso: string | null | undefined,
  filtro: string
): boolean {
  const f = filtro.trim().toLowerCase()
  if (!f) return true
  if (iso == null || String(iso).trim() === '') return false
  const raw = String(iso).toLowerCase()
  const legible = textoFechaTabla(iso).toLowerCase()
  return raw.includes(f) || legible.includes(f)
}

function terminadoCoincideFiltrosTabla(
  row: FiniquitoTerminadoItem,
  filtros: FiltrosTerminadosTabla
): boolean {
  if (!terminadoCoincideFiltroTexto(row.nombre, filtros.nombre)) return false
  const t = filtros.total.trim().toLowerCase()
  if (t) {
    const raw = String(row.total_financiamiento).toLowerCase()
    const fmt = formatCurrency(Number(row.total_financiamiento)).toLowerCase()
    if (!raw.includes(t) && !fmt.includes(t)) return false
  }
  if (
    !terminadoCoincideFiltroFecha(
      row.fecha_aprobacion,
      filtros.fechaAprobacion
    )
  ) {
    return false
  }
  if (
    !terminadoCoincideFiltroFecha(
      row.fecha_termino_pago,
      filtros.fechaTerminoPago
    )
  ) {
    return false
  }
  if (
    !terminadoCoincideFiltroFecha(row.fecha_terminado, filtros.fechaTerminado)
  ) {
    return false
  }
  return true
}

function reconciliarCasoEnLista(
  prev: FiniquitoCasoItem[],
  caso: FiniquitoCasoItem,
  debeEstar: boolean
): FiniquitoCasoItem[] {
  const idx = prev.findIndex(r => r.id === caso.id)
  if (!debeEstar) {
    return idx >= 0 ? prev.filter(r => r.id !== caso.id) : prev
  }
  if (idx >= 0) {
    return prev.map((r, i) => (i === idx ? { ...r, ...caso } : r))
  }
  return [caso, ...prev].slice(0, FETCH_LIMIT)
}

function totalTrasMovimiento(
  total: number,
  estaba: boolean,
  debeEstar: boolean
): number {
  if (estaba === debeEstar) return total
  return debeEstar ? total + 1 : Math.max(0, total - 1)
}

/**
 * Altura máxima del cuerpo de la tabla: ~10 filas en primer plano; el resto con scroll.
 * Área de trabajo usa filas más altas (contacto): un poco más de alto.
 */
const TABLA_SCROLL_MAX_H_COMPACTO = 'max-h-[min(26rem,46vh)]'
const TABLA_SCROLL_MAX_H_AREA_TRABAJO = 'max-h-[min(34rem,52vh)]'

const theadStickyClass =
  'sticky top-0 z-20 border-b border-slate-700 bg-slate-800 shadow-sm [&_tr]:border-slate-700'

function FiniquitoTablaScrollHint({
  total,
  cargados,
  limit = FETCH_LIMIT,
}: {
  total: number
  cargados: number
  limit?: number
}) {
  if (cargados === 0) return null
  const truncado = total > limit && cargados === limit
  return (
    <p className="mt-2 text-center text-[11px] leading-snug text-slate-500">
      {cargados === total
        ? `${total} caso(s).`
        : `${cargados} en pantalla de ${total} totales.`}
      {truncado ? (
        <>
          {' '}
          <span className="font-medium text-amber-900">
            Listado acotado a {limit}; use el filtro por cédula para ubicar
            casos fuera de esta primera carga.
          </span>
        </>
      ) : null}{' '}
      Desplácese dentro de la tabla para ver más filas (~10 visibles a la vez).
    </p>
  )
}

function FiniquitoGestionPageInner() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const location = useLocation()

  const [cedulaInput, setCedulaInput] = useState('')
  const [cedulaBusqueda, setCedulaBusqueda] = useState('')
  const [cedulaTrabajoInput, setCedulaTrabajoInput] = useState('')
  const [cedulaTrabajoBusqueda, setCedulaTrabajoBusqueda] = useState('')
  const [itemsAreaTrabajo, setItemsAreaTrabajo] = useState<FiniquitoCasoItem[]>(
    []
  )
  const [totalAreaTrabajo, setTotalAreaTrabajo] = useState(0)
  const [dialogTerminado, setDialogTerminado] = useState<{
    casoId: number
    /** Si true, exige Si/No (contacto para pasos siguientes); si false, Terminado directo desde Aceptado. */
    preguntarContactoCliente: boolean
  } | null>(null)
  const [itemsRechazados, setItemsRechazados] = useState<FiniquitoCasoItem[]>(
    []
  )
  const [totalRechazados, setTotalRechazados] = useState(0)
  const [itemsBandeja, setItemsBandeja] = useState<FiniquitoCasoItem[]>([])
  const [totalBandeja, setTotalBandeja] = useState(0)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [pendingEstadoCasoId, setPendingEstadoCasoId] = useState<number | null>(
    null
  )
  const [
    descargandoEstadoCuentaPrestamoId,
    setDescargandoEstadoCuentaPrestamoId,
  ] = useState<number | null>(null)
  const [pendingRechazoCasoId, setPendingRechazoCasoId] = useState<
    number | null
  >(null)
  const [kpiNuevosRevision, setKpiNuevosRevision] = useState<{
    total: number
    ventana_horas: number
  } | null>(null)
  const [cedulaTerminadosInput, setCedulaTerminadosInput] = useState('')
  const [cedulaTerminadosBusqueda, setCedulaTerminadosBusqueda] = useState('')
  const [itemsTerminados, setItemsTerminados] = useState<FiniquitoTerminadoItem[]>(
    []
  )
  const [totalTerminados, setTotalTerminados] = useState(0)
  const [resumenSemanas, setResumenSemanas] = useState<
    { semana: string; etiqueta: string; cantidad: number }[]
  >([])
  const [totalTerminadosResumen, setTotalTerminadosResumen] = useState(0)
  const [filtrosTerminados, setFiltrosTerminados] =
    useState<FiltrosTerminadosTabla>({
      nombre: '',
      total: '',
      fechaAprobacion: '',
      fechaTerminoPago: '',
      fechaTerminado: '',
    })
  const [descargandoTerminadosExcel, setDescargandoTerminadosExcel] =
    useState(false)

  useEffect(() => {
    const t = window.setTimeout(
      () => setCedulaBusqueda(cedulaInput.trim()),
      DEBOUNCE_MS
    )
    return () => window.clearTimeout(t)
  }, [cedulaInput])

  useEffect(() => {
    const t = window.setTimeout(
      () => setCedulaTrabajoBusqueda(cedulaTrabajoInput.trim()),
      DEBOUNCE_MS
    )
    return () => window.clearTimeout(t)
  }, [cedulaTrabajoInput])

  useEffect(() => {
    const t = window.setTimeout(
      () => setCedulaTerminadosBusqueda(cedulaTerminadosInput.trim()),
      DEBOUNCE_MS
    )
    return () => window.clearTimeout(t)
  }, [cedulaTerminadosInput])

  const cargarListas = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = opts?.silent === true
      if (!silent) {
        setLoading(true)
      }
      try {
        const [rTrabajo, rRech, rBandeja, rNuevos, rTerm, rSem] =
          await Promise.all([
            finiquitoAdminListar(
              undefined,
              cedulaTrabajoBusqueda || undefined,
              'ACEPTADO,EN_PROCESO',
              { limit: FETCH_LIMIT, offset: 0 }
            ),
            finiquitoAdminListar('RECHAZADO', undefined, undefined, {
              limit: FETCH_LIMIT,
              offset: 0,
            }),
            finiquitoAdminListar(
              'REVISION',
              cedulaBusqueda || undefined,
              undefined,
              {
                limit: BANDEJA_PRINCIPAL_FETCH_LIMIT,
                offset: 0,
              }
            ),
            finiquitoAdminConteoRevisionNuevos(
              cedulaBusqueda || undefined,
              FINIQUITO_HORAS_NUEVOS_REVISION_DEFAULT
            ),
            finiquitoAdminListarTerminados(cedulaTerminadosBusqueda || undefined, {
              limit: FETCH_LIMIT,
              offset: 0,
            }),
            finiquitoAdminResumenTerminadosSemanal(
              cedulaTerminadosBusqueda || undefined
            ),
          ])
        setItemsAreaTrabajo(rTrabajo.items || [])
        setTotalAreaTrabajo(rTrabajo.total ?? (rTrabajo.items || []).length)
        setItemsRechazados(rRech.items || [])
        setTotalRechazados(rRech.total ?? (rRech.items || []).length)
        setItemsBandeja(rBandeja.items || [])
        setTotalBandeja(rBandeja.total ?? (rBandeja.items || []).length)
        setKpiNuevosRevision({
          total: rNuevos.total ?? 0,
          ventana_horas:
            rNuevos.ventana_horas ?? FINIQUITO_HORAS_NUEVOS_REVISION_DEFAULT,
        })
        setItemsTerminados(rTerm.items || [])
        setTotalTerminados(rTerm.total ?? (rTerm.items || []).length)
        setResumenSemanas(rSem.semanas || [])
        setTotalTerminadosResumen(rSem.total_terminados ?? 0)
      } catch (e: unknown) {
        setKpiNuevosRevision(null)
        setItemsTerminados([])
        setTotalTerminados(0)
        setResumenSemanas([])
        setTotalTerminadosResumen(0)
        toast.error(e instanceof Error ? e.message : 'Error al cargar')
      } finally {
        if (!silent) {
          setLoading(false)
        }
      }
    },
    [cedulaBusqueda, cedulaTrabajoBusqueda, cedulaTerminadosBusqueda]
  )

  const itemsTerminadosFiltrados = useMemo(
    () =>
      itemsTerminados.filter(row =>
        terminadoCoincideFiltrosTabla(row, filtrosTerminados)
      ),
    [itemsTerminados, filtrosTerminados]
  )

  const maxSemanaCantidad = useMemo(() => {
    const vals = resumenSemanas.map(s => s.cantidad)
    return Math.max(1, ...vals, 0)
  }, [resumenSemanas])

  /** Mueve filas locales al instante con el caso devuelto por PATCH (antes del refetch). */
  const incorporarCasoActualizado = useCallback(
    (caso: FiniquitoCasoItem) => {
      const debeAreaTrabajo =
        ['ACEPTADO', 'EN_PROCESO'].includes(caso.estado) &&
        casoCoincideCedula(caso, cedulaTrabajoBusqueda)
      const debeBandeja =
        caso.estado === 'REVISION' && casoCoincideCedula(caso, cedulaBusqueda)
      const debeRechazados = caso.estado === 'RECHAZADO'

      const estabaAreaTrabajo = itemsAreaTrabajo.some(r => r.id === caso.id)
      const estabaBandeja = itemsBandeja.some(r => r.id === caso.id)
      const estabaRechazados = itemsRechazados.some(r => r.id === caso.id)

      setItemsAreaTrabajo(prev =>
        reconciliarCasoEnLista(prev, caso, debeAreaTrabajo)
      )
      setTotalAreaTrabajo(prev =>
        totalTrasMovimiento(prev, estabaAreaTrabajo, debeAreaTrabajo)
      )
      setItemsBandeja(prev => reconciliarCasoEnLista(prev, caso, debeBandeja))
      setTotalBandeja(prev =>
        totalTrasMovimiento(prev, estabaBandeja, debeBandeja)
      )
      setItemsRechazados(prev =>
        reconciliarCasoEnLista(prev, caso, debeRechazados)
      )
      setTotalRechazados(prev =>
        totalTrasMovimiento(prev, estabaRechazados, debeRechazados)
      )
    },
    [
      cedulaBusqueda,
      cedulaTrabajoBusqueda,
      itemsAreaTrabajo,
      itemsBandeja,
      itemsRechazados,
    ]
  )

  useEffect(() => {
    void cargarListas()
  }, [cargarListas])

  const onRefreshJob = async () => {
    setRefreshing(true)
    try {
      const r = await finiquitoAdminRefreshMaterializado()
      const { titulo, descripcion } = textoToastRefresco(r)
      toast.success(titulo, { description: descripcion })
      void invalidatePrestamosQueries(queryClient)
      await cargarListas({ silent: true })
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al refrescar')
    } finally {
      setRefreshing(false)
    }
  }

  const descargarEstadoCuenta = async (prestamoId: number) => {
    setDescargandoEstadoCuentaPrestamoId(prestamoId)
    try {
      await prestamoService.descargarEstadoCuentaPDF(prestamoId)
      toast.success('Estado de cuenta descargado')
    } catch (e: unknown) {
      toast.error(
        e instanceof Error ? e.message : 'Error al descargar estado de cuenta'
      )
    } finally {
      setDescargandoEstadoCuentaPrestamoId(null)
    }
  }

  const cambiarEstado = async (id: number, estado: string) => {
    if (pendingEstadoCasoId != null) return
    setPendingEstadoCasoId(id)
    try {
      const r = await finiquitoAdminPatchEstado(id, estado)
      if (!r.ok) {
        toast.error(r.error || 'No se pudo actualizar')
        return
      }
      if (r.caso) {
        incorporarCasoActualizado(r.caso)
      }
      if (estado === 'EN_PROCESO') {
        toast.success('En proceso')
      } else if (estado === 'REVISION') {
        toast.success('Caso en bandeja principal (Atrasado)')
      } else {
        toast.success('Estado actualizado')
      }
      void invalidatePrestamosQueries(queryClient)
      await cargarListas({ silent: true })
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error')
    } finally {
      setPendingEstadoCasoId(null)
    }
  }

  const onSeleccionarEstadoBandeja = (row: FiniquitoCasoItem, v: string) => {
    if (v === 'RECHAZADO') {
      setPendingRechazoCasoId(row.id)
      return
    }
    void cambiarEstado(row.id, v)
  }

  const confirmarRechazo = async () => {
    if (pendingRechazoCasoId == null) return
    const id = pendingRechazoCasoId
    setPendingRechazoCasoId(null)
    await cambiarEstado(id, 'RECHAZADO')
  }

  const confirmarTerminado = async (contactoParaSiguientes?: boolean) => {
    if (dialogTerminado == null) return
    const { casoId, preguntarContactoCliente } = dialogTerminado
    if (preguntarContactoCliente && contactoParaSiguientes === undefined) {
      return
    }
    if (pendingEstadoCasoId != null) return
    setPendingEstadoCasoId(casoId)
    try {
      const r = await finiquitoAdminPatchEstado(
        casoId,
        'TERMINADO',
        preguntarContactoCliente ? contactoParaSiguientes : undefined
      )
      if (!r.ok) {
        toast.error(r.error || 'No se pudo actualizar')
        return
      }
      setDialogTerminado(null)
      toast.success('Caso marcado como terminado')
      if (r.caso) {
        incorporarCasoActualizado(r.caso)
      }
      void invalidatePrestamosQueries(queryClient)
      await cargarListas({ silent: true })
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error')
    } finally {
      setPendingEstadoCasoId(null)
    }
  }

  const limpiarCedula = () => {
    setCedulaInput('')
    setCedulaBusqueda('')
  }

  const limpiarCedulaTrabajo = () => {
    setCedulaTrabajoInput('')
    setCedulaTrabajoBusqueda('')
  }

  const limpiarCedulaTerminados = () => {
    setCedulaTerminadosInput('')
    setCedulaTerminadosBusqueda('')
  }

  const limpiarFiltrosTerminadosTabla = () => {
    setFiltrosTerminados({
      nombre: '',
      total: '',
      fechaAprobacion: '',
      fechaTerminoPago: '',
      fechaTerminado: '',
    })
  }

  const exportarTerminadosExcel = async () => {
    if (!itemsTerminadosFiltrados.length) {
      toast.error('No hay filas para exportar con los filtros actuales')
      return
    }
    setDescargandoTerminadosExcel(true)
    try {
      await descargarTerminadosExcel(itemsTerminadosFiltrados, {
        cedulaFiltro: cedulaTerminadosBusqueda || 'todos',
      })
      toast.success('Excel de terminados descargado')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al exportar Excel')
    } finally {
      setDescargandoTerminadosExcel(false)
    }
  }

  const casoTieneAccionPendiente = (casoId: number) =>
    pendingEstadoCasoId === casoId

  const abrirRevisionManualPrestamo = (prestamoId: number) => {
    navigate(`/revision-manual/editar/${prestamoId}`, {
      state: { returnTo: `${location.pathname}${location.search}` },
    })
  }

  const renderAcciones = (row: FiniquitoCasoItem) => (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-8 w-8 border-slate-300"
        title="Abrir revisión manual del préstamo"
        aria-label={`Abrir revisión manual del préstamo ${row.prestamo_id}`}
        onClick={() => abrirRevisionManualPrestamo(row.prestamo_id)}
      >
        <Eye className="h-4 w-4" aria-hidden />
      </Button>
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-8 w-8 border-slate-300"
        title="Descargar estado de cuenta (PDF)"
        aria-label={`Descargar estado de cuenta PDF del préstamo ${row.prestamo_id}`}
        disabled={descargandoEstadoCuentaPrestamoId === row.prestamo_id}
        onClick={() => descargarEstadoCuenta(row.prestamo_id)}
      >
        {descargandoEstadoCuentaPrestamoId === row.prestamo_id ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        ) : (
          <Download className="h-4 w-4" aria-hidden />
        )}
      </Button>
      <Select
        key={`estado-sel-${row.id}-${row.estado}`}
        value={row.estado === 'REVISION' ? 'REVISION' : undefined}
        disabled={casoTieneAccionPendiente(row.id)}
        onValueChange={v => onSeleccionarEstadoBandeja(row, v)}
      >
        <SelectTrigger
          className={cn(
            'h-8 min-w-[158px] max-w-[200px] text-xs',
            casoRevisionAtrasado(row)
              ? 'border-red-200 bg-red-50 text-red-900'
              : row.estado === 'REVISION' &&
                  'border-sky-200 bg-sky-50 text-sky-900'
          )}
          aria-label={`Cambiar estado del caso ${row.id}`}
        >
          <SelectValue placeholder="Estado..." />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="REVISION" disabled>
            {casoRevisionAtrasado(row) ? 'Atrasado' : 'Revisión'}
          </SelectItem>
          <SelectItem value="ACEPTADO">Aceptado</SelectItem>
          <SelectItem value="RECHAZADO">Rechazado</SelectItem>
        </SelectContent>
      </Select>
    </div>
  )

  const renderAccionesAreaTrabajo = (row: FiniquitoCasoItem) => (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-8 w-8 border-slate-300"
        title="Abrir revisión manual del préstamo"
        aria-label={`Abrir revisión manual del préstamo ${row.prestamo_id}`}
        onClick={() => abrirRevisionManualPrestamo(row.prestamo_id)}
      >
        <Eye className="h-4 w-4" aria-hidden />
      </Button>
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-8 w-8 border-slate-300"
        title="Descargar estado de cuenta (PDF)"
        aria-label={`Descargar estado de cuenta PDF del préstamo ${row.prestamo_id}`}
        disabled={descargandoEstadoCuentaPrestamoId === row.prestamo_id}
        onClick={() => descargarEstadoCuenta(row.prestamo_id)}
      >
        {descargandoEstadoCuentaPrestamoId === row.prestamo_id ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        ) : (
          <Download className="h-4 w-4" aria-hidden />
        )}
      </Button>
      {row.estado === 'ACEPTADO' || row.estado === 'EN_PROCESO' ? (
        <>
          <Select
            key={`proceso-revision-${row.id}-${row.estado}`}
            disabled={casoTieneAccionPendiente(row.id)}
            value={row.estado === 'EN_PROCESO' ? 'EN_PROCESO' : undefined}
            onValueChange={v => {
              if (v === 'REVISION') {
                void cambiarEstado(row.id, 'REVISION')
                return
              }
              if (v === 'EN_PROCESO') {
                if (row.estado === 'EN_PROCESO') return
                void cambiarEstado(row.id, 'EN_PROCESO')
              }
            }}
          >
            <SelectTrigger
              className="h-8 min-w-[168px] max-w-[200px] text-xs"
              aria-label={`En proceso o revisión, caso ${row.id}`}
            >
              <SelectValue placeholder="En proceso / Revisión" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="EN_PROCESO">En proceso</SelectItem>
              <SelectItem value="REVISION">Revisión</SelectItem>
            </SelectContent>
          </Select>
          {row.estado === 'ACEPTADO' ? (
            <Button
              type="button"
              size="sm"
              className="h-8 bg-emerald-700 text-xs hover:bg-emerald-800"
              disabled={casoTieneAccionPendiente(row.id)}
              onClick={() =>
                setDialogTerminado({
                  casoId: row.id,
                  preguntarContactoCliente: false,
                })
              }
            >
              Terminado
            </Button>
          ) : null}
        </>
      ) : null}
      {row.estado === 'EN_PROCESO' ? (
        <>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-8 border-slate-300 text-xs"
            disabled={casoTieneAccionPendiente(row.id)}
            onClick={() => cambiarEstado(row.id, 'ACEPTADO')}
          >
            Volver a aceptado
          </Button>
          <Button
            type="button"
            size="sm"
            className="h-8 bg-emerald-700 text-xs hover:bg-emerald-800"
            disabled={casoTieneAccionPendiente(row.id)}
            onClick={() =>
              setDialogTerminado({
                casoId: row.id,
                preguntarContactoCliente: true,
              })
            }
          >
            Terminado
          </Button>
        </>
      ) : null}
      {row.estado === 'TERMINADO' ? (
        <Select
          key={`solo-revision-${row.id}`}
          disabled={casoTieneAccionPendiente(row.id)}
          onValueChange={v => {
            if (v === 'REVISION') void cambiarEstado(row.id, 'REVISION')
          }}
        >
          <SelectTrigger
            className="h-8 min-w-[168px] max-w-[200px] text-xs"
            aria-label={`Volver a bandeja principal, caso ${row.id}`}
          >
            <SelectValue placeholder="Volver a Revisión…" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="REVISION">
              Revisión (bandeja principal)
            </SelectItem>
          </SelectContent>
        </Select>
      ) : null}
    </div>
  )

  const renderAccionesRechazado = (row: FiniquitoCasoItem) => (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-8 w-8 border-slate-300"
        title="Abrir revisión manual del préstamo"
        aria-label={`Abrir revisión manual del préstamo ${row.prestamo_id}`}
        onClick={() => abrirRevisionManualPrestamo(row.prestamo_id)}
      >
        <Eye className="h-4 w-4" aria-hidden />
      </Button>
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-8 w-8 border-slate-300"
        title="Descargar estado de cuenta (PDF)"
        aria-label={`Descargar estado de cuenta PDF del préstamo ${row.prestamo_id}`}
        disabled={descargandoEstadoCuentaPrestamoId === row.prestamo_id}
        onClick={() => descargarEstadoCuenta(row.prestamo_id)}
      >
        {descargandoEstadoCuentaPrestamoId === row.prestamo_id ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        ) : (
          <Download className="h-4 w-4" aria-hidden />
        )}
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-8 border-slate-300 text-xs"
        disabled={casoTieneAccionPendiente(row.id)}
        onClick={() => cambiarEstado(row.id, 'REVISION')}
      >
        Volver a revisión
      </Button>
    </div>
  )

  const renderTabla = (
    items: FiniquitoCasoItem[],
    renderAccionesFila: (row: FiniquitoCasoItem) => ReactNode = renderAcciones
  ) => (
    <div
      className={cn(
        TABLA_SCROLL_MAX_H_COMPACTO,
        'overflow-x-auto overflow-y-auto overscroll-y-contain rounded-md border border-slate-200'
      )}
    >
      <Table
        containerClassName="overflow-visible"
        className="border-separate border-spacing-0"
      >
        <TableHeader className={theadStickyClass}>
          <TableRow className="border-0 hover:bg-transparent">
            <TableHead className={thGestion} scope="col">
              ID caso
            </TableHead>
            <TableHead className={thGestion} scope="col">
              Cédula
            </TableHead>
            <TableHead className={thGestion} scope="col">
              Préstamo
            </TableHead>
            <TableHead
              className={cn(thGestion, 'whitespace-normal')}
              scope="col"
            >
              Último pago
            </TableHead>
            <TableHead className={thGestion} scope="col">
              Estado
            </TableHead>
            <TableHead className={cn(thGestion, 'text-right')} scope="col">
              Acciones
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((row, idx) => (
            <TableRow key={row.id} className={idx % 2 === 0 ? trEven : trOdd}>
              <TableCell className={cn(tdGestion, 'font-mono text-xs')}>
                {row.id}
              </TableCell>
              <TableCell className={cn(tdGestion, 'font-mono text-xs')}>
                {row.cedula}
              </TableCell>
              <TableCell className={cn(tdGestion, 'tabular-nums')}>
                {row.prestamo_id}
              </TableCell>
              <TableCell
                className={cn(tdGestion, 'whitespace-nowrap text-slate-800')}
                title={
                  row.ultima_fecha_pago
                    ? `Desde pagos: ${row.ultima_fecha_pago}`
                    : 'Sin pagos con préstamo vinculado'
                }
              >
                {textoUltimoPago(row.ultima_fecha_pago)}
              </TableCell>
              <TableCell className={tdGestion}>
                <span
                  className={cn(
                    'rounded px-1.5 py-0.5 text-xs font-medium',
                    estadoBadgeClassName(row)
                  )}
                >
                  {estadoEtiquetaVisible(row)}
                </span>
              </TableCell>
              <TableCell className={cn(tdGestion, 'text-right')}>
                {renderAccionesFila(row)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )

  const renderTablaAreaTrabajo = (items: FiniquitoCasoItem[]) => (
    <div
      className={cn(
        TABLA_SCROLL_MAX_H_AREA_TRABAJO,
        'overflow-x-auto overflow-y-auto overscroll-y-contain rounded-md border border-slate-200'
      )}
    >
      <Table
        containerClassName="overflow-visible"
        className="border-separate border-spacing-0"
      >
        <TableHeader className={theadStickyClass}>
          <TableRow className="border-0 hover:bg-transparent">
            <TableHead className={thGestion} scope="col">
              ID caso
            </TableHead>
            <TableHead className={thGestion} scope="col">
              Cédula
            </TableHead>
            <TableHead className={thGestion} scope="col">
              Préstamo
            </TableHead>
            <TableHead
              className={cn(thGestion, 'whitespace-normal')}
              scope="col"
            >
              Último pago
            </TableHead>
            <TableHead
              className={cn(
                thGestion,
                'max-w-[9rem] whitespace-normal leading-tight'
              )}
              scope="col"
              title="Tiempo límite: cuenta regresiva de 30 días desde la liquidación o último pago"
            >
              Tiempo límite
            </TableHead>
            <TableHead className={cn(thGestion, 'min-w-[140px]')} scope="col">
              Contacto
            </TableHead>
            <TableHead className={thGestion} scope="col">
              Estado
            </TableHead>
            <TableHead className={cn(thGestion, 'text-right')} scope="col">
              Acciones
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((row, idx) => (
            <TableRow key={row.id} className={idx % 2 === 0 ? trEven : trOdd}>
              <TableCell className={cn(tdGestion, 'font-mono text-xs')}>
                {row.id}
              </TableCell>
              <TableCell className={cn(tdGestion, 'font-mono text-xs')}>
                {row.cedula}
              </TableCell>
              <TableCell className={cn(tdGestion, 'tabular-nums')}>
                {row.prestamo_id}
              </TableCell>
              <TableCell
                className={cn(tdGestion, 'whitespace-nowrap text-slate-800')}
                title={
                  row.ultima_fecha_pago
                    ? `Desde pagos: ${row.ultima_fecha_pago}`
                    : 'Sin pagos con préstamo vinculado'
                }
              >
                {textoUltimoPago(row.ultima_fecha_pago)}
              </TableCell>
              <TableCell
                className={cn(tdGestion, 'whitespace-nowrap text-slate-800')}
                title={
                  row.ultima_fecha_pago
                    ? `Cuenta regresiva de 30 días desde último pago: ${row.ultima_fecha_pago}`
                    : 'Sin último pago'
                }
              >
                <span
                  className={cn(
                    'rounded px-1.5 py-0.5 text-xs font-medium',
                    tiempoLimiteAreaTrabajoClassName(row)
                  )}
                >
                  {textoTiempoLimiteAreaTrabajo(row)}
                </span>
              </TableCell>
              <TableCell className={cn(tdGestion, 'max-w-[200px]')}>
                <div className="space-y-0.5 text-xs leading-snug text-slate-800">
                  <div className="font-medium">
                    {row.cliente_nombres?.trim() || '-'}
                  </div>
                  <div className="break-all text-slate-600">
                    {row.cliente_email?.trim() || '-'}
                  </div>
                  <div className="font-mono text-slate-700">
                    {row.cliente_telefono?.trim() || '-'}
                  </div>
                  {row.estado === 'TERMINADO' &&
                  row.contacto_para_siguientes !== undefined &&
                  row.contacto_para_siguientes !== null ? (
                    <div className="pt-1 text-[11px] text-slate-500">
                      Contactó para siguientes:{' '}
                      <span className="font-semibold text-slate-700">
                        {row.contacto_para_siguientes ? 'Sí' : 'No'}
                      </span>
                    </div>
                  ) : null}
                </div>
              </TableCell>
              <TableCell className={tdGestion}>
                <span
                  className={cn(
                    'rounded px-1.5 py-0.5 text-xs font-medium',
                    row.estado === 'ACEPTADO' && 'bg-slate-100 text-slate-800',
                    row.estado === 'EN_PROCESO' &&
                      'bg-amber-100 text-amber-950',
                    row.estado === 'TERMINADO' &&
                      'bg-emerald-100 text-emerald-950'
                  )}
                >
                  {estadoEtiquetaVisible(row)}
                </span>
              </TableCell>
              <TableCell className={cn(tdGestion, 'text-right')}>
                {renderAccionesAreaTrabajo(row)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )

  const subtituloTrabajo = totalAreaTrabajo === 1 ? 'registro' : 'registros'
  const subtituloRech = totalRechazados === 1 ? 'registro' : 'registros'

  return (
    <FiniquitoWorkspaceShell
      description="Los créditos LIQUIDADO con cuotas cubiertas (= financiamiento) entran automáticamente a la bandeja principal. Desde acciones se aceptan para pasar al área de trabajo o se rechazan al área de revisión."
      actions={
        <Button
          size="sm"
          variant="outline"
          disabled={refreshing || loading}
          onClick={onRefreshJob}
          className="shrink-0 gap-2"
        >
          {refreshing ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" aria-hidden />
          )}
          Refrescar materializado
        </Button>
      }
    >
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="space-y-1 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Atrasados (bandeja)
            </p>
            <p className="text-2xl font-bold tabular-nums text-[#1e3a5f]">
              {loading ? '-' : totalBandeja}
            </p>
            <p className="text-xs text-slate-500">
              Pendientes sin aceptar/rechazar
              {cedulaBusqueda ? ' (filtro cédula)' : ''}
            </p>
          </CardContent>
        </Card>
        <Card
          className={cn(
            'border-slate-200 shadow-sm',
            !loading &&
              (kpiNuevosRevision?.total ?? 0) > 0 &&
              'border-amber-300/90 bg-amber-50/40 ring-1 ring-amber-200/80'
          )}
        >
          <CardContent className="space-y-1 p-4">
            <div className="flex items-center gap-1.5">
              <Bell
                className={cn(
                  'h-3.5 w-3.5 shrink-0',
                  !loading && (kpiNuevosRevision?.total ?? 0) > 0
                    ? 'text-amber-700'
                    : 'text-slate-400'
                )}
                aria-hidden
              />
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Nuevos en bandeja
              </p>
            </div>
            <p
              className={cn(
                'text-2xl font-bold tabular-nums',
                !loading && (kpiNuevosRevision?.total ?? 0) > 0
                  ? 'text-amber-950'
                  : 'text-slate-800'
              )}
            >
              {loading ? '-' : (kpiNuevosRevision?.total ?? 0)}
            </p>
            <p className="text-xs text-slate-500">
              Creados hace ≤{' '}
              {kpiNuevosRevision?.ventana_horas ??
                FINIQUITO_HORAS_NUEVOS_REVISION_DEFAULT}{' '}
              h (UTC)
            </p>
          </CardContent>
        </Card>
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="space-y-1 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Área de trabajo
            </p>
            <p className="text-2xl font-bold tabular-nums text-emerald-900">
              {loading ? '-' : totalAreaTrabajo}
            </p>
            <p className="text-xs text-slate-500">
              Aceptado / En proceso
              {cedulaTrabajoBusqueda ? ' (filtro cédula)' : ''}
            </p>
          </CardContent>
        </Card>
        <Card className="border-slate-200 shadow-sm">
          <CardContent className="space-y-1 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Rechazados
            </p>
            <p className="text-2xl font-bold tabular-nums text-rose-900">
              {loading ? '-' : totalRechazados}
            </p>
            <p className="text-xs text-slate-500">
              Casos rechazados desde bandeja principal
            </p>
          </CardContent>
        </Card>
      </div>

      <section
        className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-md"
        aria-labelledby="finiquito-bandeja-titulo"
      >
        <div className="border-b border-slate-200 bg-slate-50/90 px-4 py-4 sm:px-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-1">
              <h2
                id="finiquito-bandeja-titulo"
                className="text-base font-bold text-[#1e3a5f]"
              >
                Bandeja principal
              </h2>
              <p className="text-xs text-slate-600 sm:text-sm">
                Casos <strong>atrasados</strong> pendientes de aceptar o
                rechazar. Escriba parte de la cédula para acotar (espera ~
                {DEBOUNCE_MS / 1000} s tras dejar de escribir).
              </p>
            </div>
            <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-end lg:w-auto lg:min-w-[320px]">
              <div className="min-w-0 flex-1 space-y-1.5">
                <Label
                  htmlFor="finiquito-filtro-cedula-bandeja"
                  className="text-xs font-semibold text-slate-700"
                >
                  Filtrar por cédula
                </Label>
                <div className="relative">
                  <Search
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                    aria-hidden
                  />
                  <Input
                    id="finiquito-filtro-cedula-bandeja"
                    type="search"
                    autoComplete="off"
                    placeholder="Ej. V12345678 o parte del número"
                    value={cedulaInput}
                    onChange={e => setCedulaInput(e.target.value)}
                    className="h-10 border-slate-300 pl-9 pr-10 font-mono text-sm"
                  />
                  {cedulaInput ? (
                    <button
                      type="button"
                      className="absolute right-2 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                      onClick={limpiarCedula}
                      title="Limpiar filtro"
                      aria-label="Limpiar filtro de cédula"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  ) : null}
                </div>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-10 shrink-0 border-slate-300"
                disabled={loading}
                onClick={() => void cargarListas()}
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Recargar'
                )}
              </Button>
            </div>
          </div>
          {cedulaBusqueda ? (
            <p className="mt-3 text-xs text-slate-600">
              Filtro activo (bandeja principal):{' '}
              <span className="font-mono font-semibold text-[#1e3a5f]">
                {cedulaBusqueda}
              </span>
            </p>
          ) : null}
        </div>
        <div>
          <div className="p-3 sm:p-4">
            {loading ? (
              <div className="flex justify-center py-14">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
              </div>
            ) : itemsBandeja.length === 0 ? (
              <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50 px-4 py-10 text-center text-sm leading-relaxed text-slate-600">
                {cedulaBusqueda
                  ? 'Ningún caso atrasado coincide con esa cédula. Pruebe otra subcadena o limpie el filtro.'
                  : 'No hay casos atrasados. Use «Refrescar materializado» para traer préstamos LIQUIDADO con cuotas cubiertas a la bandeja principal.'}
              </p>
            ) : (
              <>
                {renderTabla(itemsBandeja)}
                <FiniquitoTablaScrollHint
                  total={totalBandeja}
                  cargados={itemsBandeja.length}
                  limit={BANDEJA_PRINCIPAL_FETCH_LIMIT}
                />
              </>
            )}
          </div>
        </div>
      </section>
      <section
        className={cn(
          'overflow-hidden rounded-2xl border-2 border-dashed border-amber-400/85',
          'bg-amber-50/40 shadow-inner'
        )}
        aria-labelledby="finiquito-area-revision-titulo"
      >
        <div className="border-b border-amber-200/90 bg-amber-100/95 px-4 py-3.5 sm:px-5">
          <div className="flex flex-wrap items-center gap-3 text-amber-950">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-amber-300/90 bg-amber-50 shadow-sm">
              <XCircle className="h-5 w-5 text-amber-800" aria-hidden />
            </span>
            <div>
              <h2
                id="finiquito-area-revision-titulo"
                className="text-sm font-bold tracking-tight sm:text-base"
              >
                Área de revisión
              </h2>
              <p className="text-xs text-amber-900/85">
                Rechazados · {totalRechazados} {subtituloRech}
              </p>
            </div>
          </div>
        </div>
        <div>
          <div className="p-3 sm:p-4">
            {loading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-amber-600/70" />
              </div>
            ) : itemsRechazados.length === 0 ? (
              <p className="rounded-lg border border-dashed border-amber-200/90 bg-white/50 px-4 py-10 text-center text-sm text-amber-950/85">
                No hay casos rechazados. Aparecerán aquí al pasar un caso a
                «Rechazado».
              </p>
            ) : (
              <>
                {renderTabla(itemsRechazados, renderAccionesRechazado)}
                <FiniquitoTablaScrollHint
                  total={totalRechazados}
                  cargados={itemsRechazados.length}
                />
              </>
            )}
          </div>
        </div>
      </section>
      <section
        className={cn(
          'overflow-hidden rounded-2xl border border-emerald-200/90 bg-white shadow-md',
          'ring-1 ring-emerald-100/80'
        )}
        aria-labelledby="finiquito-area-trabajo-titulo"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-emerald-200/80 bg-gradient-to-r from-emerald-800 to-emerald-600 px-4 py-3.5 text-white sm:px-5">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/15 shadow-inner">
              <CheckCircle2 className="h-5 w-5" aria-hidden />
            </span>
            <div>
              <h2
                id="finiquito-area-trabajo-titulo"
                className="text-sm font-bold tracking-tight sm:text-base"
              >
                Área de trabajo
              </h2>
              <p className="text-xs text-emerald-100">
                Aceptados y en proceso · {totalAreaTrabajo} {subtituloTrabajo}
              </p>
            </div>
          </div>
        </div>
        <div className="border-b border-emerald-200/70 bg-emerald-50/30 px-4 py-3.5 sm:px-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <p className="max-w-xl text-xs text-slate-600">
              Escriba parte de la cédula para acotar el área de trabajo (espera
              ~{DEBOUNCE_MS / 1000} s tras dejar de escribir). Independiente del
              filtro de la bandeja principal.
            </p>
            <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-end lg:w-auto lg:min-w-[320px]">
              <div className="min-w-0 flex-1 space-y-1.5">
                <Label
                  htmlFor="finiquito-filtro-cedula-trabajo"
                  className="text-xs font-semibold text-slate-700"
                >
                  Filtrar por cédula
                </Label>
                <div className="relative">
                  <Search
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                    aria-hidden
                  />
                  <Input
                    id="finiquito-filtro-cedula-trabajo"
                    type="search"
                    autoComplete="off"
                    placeholder="Ej. V12345678 o parte del número"
                    value={cedulaTrabajoInput}
                    onChange={e => setCedulaTrabajoInput(e.target.value)}
                    className="h-10 border-slate-300 bg-white pl-9 pr-10 font-mono text-sm"
                  />
                  {cedulaTrabajoInput ? (
                    <button
                      type="button"
                      className="absolute right-2 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                      onClick={limpiarCedulaTrabajo}
                      title="Limpiar filtro"
                      aria-label="Limpiar filtro de cédula en área de trabajo"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  ) : null}
                </div>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-10 shrink-0 border-slate-300 bg-white"
                disabled={loading}
                onClick={() => void cargarListas()}
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Recargar'
                )}
              </Button>
            </div>
          </div>
          {cedulaTrabajoBusqueda ? (
            <p className="mt-3 text-xs text-slate-600">
              Filtro activo (área de trabajo):{' '}
              <span className="font-mono font-semibold text-emerald-900">
                {cedulaTrabajoBusqueda}
              </span>
            </p>
          ) : null}
        </div>
        <div className="bg-gradient-to-b from-emerald-50/50 to-white">
          <div className="p-3 sm:p-4">
            {loading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-emerald-600/70" />
              </div>
            ) : itemsAreaTrabajo.length === 0 ? (
              <p className="rounded-lg border border-dashed border-emerald-200/80 bg-white/60 px-4 py-10 text-center text-sm text-slate-600">
                {cedulaTrabajoBusqueda ? (
                  <>
                    Ningún caso en el área de trabajo coincide con esa cédula.
                    Pruebe otra subcadena o limpie el filtro.
                  </>
                ) : (
                  <>
                    No hay casos en esta bandeja. Los aceptados aparecen aquí;
                    puede usar «En proceso» o «Terminado» para dejar el caso en
                    pasivo y sacarlo de la pantalla operativa.
                  </>
                )}
              </p>
            ) : (
              <>
                {renderTablaAreaTrabajo(itemsAreaTrabajo)}
                <FiniquitoTablaScrollHint
                  total={totalAreaTrabajo}
                  cargados={itemsAreaTrabajo.length}
                />
              </>
            )}
          </div>
        </div>
      </section>
      <section
        className={cn(
          'overflow-hidden rounded-2xl border border-violet-200/90 bg-white shadow-md',
          'ring-1 ring-violet-100/80'
        )}
        aria-labelledby="finiquito-terminados-titulo"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-violet-200/80 bg-gradient-to-r from-violet-900 to-violet-600 px-4 py-3.5 text-white sm:px-5">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/15 shadow-inner">
              <CheckCircle2 className="h-5 w-5" aria-hidden />
            </span>
            <div>
              <h2
                id="finiquito-terminados-titulo"
                className="text-sm font-bold tracking-tight sm:text-base"
              >
                Casos terminados
              </h2>
              <p className="text-xs text-violet-100">
                Pasivos tras marcar Terminado · {totalTerminadosResumen} en total
                {cedulaTerminadosBusqueda
                  ? ` (filtro cédula: ${cedulaTerminadosBusqueda})`
                  : ''}
              </p>
            </div>
          </div>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="h-9 shrink-0 border-white/30 bg-white/15 text-white hover:bg-white/25"
            disabled={
              descargandoTerminadosExcel || itemsTerminadosFiltrados.length === 0
            }
            onClick={() => void exportarTerminadosExcel()}
          >
            {descargandoTerminadosExcel ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
            ) : (
              <Download className="mr-2 h-4 w-4" aria-hidden />
            )}
            Descargar Excel
          </Button>
        </div>
        <div className="border-b border-violet-200/70 bg-violet-50/40 px-4 py-4 sm:px-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <p className="max-w-xl text-xs text-slate-600">
              Resumen por semana ISO (fecha en que se marcó Terminado). Use el
              filtro de cédula para acotar el gráfico y el listado (~
              {DEBOUNCE_MS / 1000} s de espera).
            </p>
            <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-end lg:w-auto lg:min-w-[320px]">
              <div className="min-w-0 flex-1 space-y-1.5">
                <Label
                  htmlFor="finiquito-filtro-cedula-terminados"
                  className="text-xs font-semibold text-slate-700"
                >
                  Buscar por cédula
                </Label>
                <div className="relative">
                  <Search
                    className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
                    aria-hidden
                  />
                  <Input
                    id="finiquito-filtro-cedula-terminados"
                    type="search"
                    autoComplete="off"
                    placeholder="Ej. V12345678"
                    value={cedulaTerminadosInput}
                    onChange={e => setCedulaTerminadosInput(e.target.value)}
                    className="h-10 border-slate-300 bg-white pl-9 pr-10 font-mono text-sm"
                  />
                  {cedulaTerminadosInput ? (
                    <button
                      type="button"
                      className="absolute right-2 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                      onClick={limpiarCedulaTerminados}
                      title="Limpiar filtro"
                      aria-label="Limpiar filtro de cédula en terminados"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  ) : null}
                </div>
              </div>
            </div>
          </div>
          {resumenSemanas.length === 0 ? (
            <p className="mt-4 rounded-lg border border-dashed border-violet-200/90 bg-white/60 px-4 py-6 text-center text-sm text-slate-600">
              {loading
                ? 'Cargando resumen…'
                : 'Sin casos terminados en el periodo mostrado.'}
            </p>
          ) : (
            <div
              className="mt-4 flex items-end gap-2 overflow-x-auto pb-2 pt-1"
              role="img"
              aria-label="Gráfico de casos terminados por semana"
            >
              <BarChart3
                className="mb-6 h-5 w-5 shrink-0 text-violet-700"
                aria-hidden
              />
              {resumenSemanas.map(s => (
                <div
                  key={s.semana}
                  className="flex min-w-[3.25rem] flex-col items-center gap-1"
                  title={`${s.etiqueta}: ${s.cantidad} caso(s)`}
                >
                  <span className="text-[10px] font-semibold tabular-nums text-violet-900">
                    {s.cantidad}
                  </span>
                  <div
                    className="w-10 rounded-t-md bg-violet-500/90 transition-all"
                    style={{
                      height: `${Math.max(12, Math.round((s.cantidad / maxSemanaCantidad) * 120))}px`,
                    }}
                  />
                  <span className="max-w-[4.5rem] text-center text-[9px] leading-tight text-slate-600">
                    {s.etiqueta}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="border-b border-violet-100 bg-slate-50/80 px-3 py-3 sm:px-4">
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            <Input
              placeholder="Filtrar nombre"
              value={filtrosTerminados.nombre}
              onChange={e =>
                setFiltrosTerminados(prev => ({
                  ...prev,
                  nombre: e.target.value,
                }))
              }
              className="h-9 bg-white text-sm"
              aria-label="Filtrar por nombre"
            />
            <Input
              placeholder="Filtrar total financ."
              value={filtrosTerminados.total}
              onChange={e =>
                setFiltrosTerminados(prev => ({
                  ...prev,
                  total: e.target.value,
                }))
              }
              className="h-9 bg-white text-sm"
              aria-label="Filtrar por total de financiamiento"
            />
            <Input
              placeholder="Filtrar fecha aprobación"
              value={filtrosTerminados.fechaAprobacion}
              onChange={e =>
                setFiltrosTerminados(prev => ({
                  ...prev,
                  fechaAprobacion: e.target.value,
                }))
              }
              className="h-9 bg-white text-sm"
              aria-label="Filtrar por fecha de aprobación"
            />
            <Input
              placeholder="Filtrar último pago"
              value={filtrosTerminados.fechaTerminoPago}
              onChange={e =>
                setFiltrosTerminados(prev => ({
                  ...prev,
                  fechaTerminoPago: e.target.value,
                }))
              }
              className="h-9 bg-white text-sm"
              aria-label="Filtrar por fecha de término de pago"
            />
            <Input
              placeholder="Filtrar fecha terminado"
              value={filtrosTerminados.fechaTerminado}
              onChange={e =>
                setFiltrosTerminados(prev => ({
                  ...prev,
                  fechaTerminado: e.target.value,
                }))
              }
              className="h-9 bg-white text-sm"
              aria-label="Filtrar por fecha en que se marcó terminado"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-9 border-slate-300 bg-white text-xs"
              onClick={limpiarFiltrosTerminadosTabla}
            >
              Limpiar filtros tabla
            </Button>
          </div>
        </div>
        <div className="bg-gradient-to-b from-violet-50/40 to-white p-3 sm:p-4">
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-violet-600/70" />
            </div>
          ) : itemsTerminadosFiltrados.length === 0 ? (
            <p className="rounded-lg border border-dashed border-violet-200/80 bg-white/60 px-4 py-10 text-center text-sm text-slate-600">
              {itemsTerminados.length === 0
                ? 'No hay casos terminados. Aparecerán aquí al confirmar Terminado en el área de trabajo.'
                : 'Ningún caso coincide con los filtros de la tabla.'}
            </p>
          ) : (
            <>
              <div
                className={cn(
                  'overflow-auto rounded-lg border border-slate-200',
                  TABLA_SCROLL_MAX_H_COMPACTO
                )}
              >
                <Table>
                  <TableHeader className={theadStickyClass}>
                    <TableRow>
                      <TableHead className={thGestion}>Cédula</TableHead>
                      <TableHead className={thGestion}>Nombre</TableHead>
                      <TableHead className={thGestion}>
                        Total financ.
                      </TableHead>
                      <TableHead className={thGestion}>
                        Fecha aprobación
                      </TableHead>
                      <TableHead className={thGestion}>
                        Último pago
                      </TableHead>
                      <TableHead className={thGestion}>
                        Fecha terminado
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {itemsTerminadosFiltrados.map((row, idx) => (
                      <TableRow
                        key={row.id}
                        className={idx % 2 === 0 ? trEven : trOdd}
                      >
                        <TableCell
                          className={cn(tdGestion, 'font-mono text-xs')}
                        >
                          {row.cedula}
                        </TableCell>
                        <TableCell className={tdGestion}>
                          {row.nombre || '-'}
                        </TableCell>
                        <TableCell className={cn(tdGestion, 'tabular-nums')}>
                          {formatCurrency(Number(row.total_financiamiento))}
                        </TableCell>
                        <TableCell className={tdGestion}>
                          {textoFechaTabla(row.fecha_aprobacion)}
                        </TableCell>
                        <TableCell className={tdGestion}>
                          {textoFechaTabla(row.fecha_termino_pago)}
                        </TableCell>
                        <TableCell className={tdGestion}>
                          {textoFechaTabla(row.fecha_terminado)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <FiniquitoTablaScrollHint
                total={totalTerminados}
                cargados={itemsTerminadosFiltrados.length}
              />
              {itemsTerminadosFiltrados.length !== itemsTerminados.length ? (
                <p className="mt-2 text-center text-[11px] text-slate-500">
                  Mostrando {itemsTerminadosFiltrados.length} de{' '}
                  {itemsTerminados.length} filas cargadas (filtros de tabla).
                </p>
              ) : null}
            </>
          )}
        </div>
      </section>
      <Dialog
        open={dialogTerminado != null}
        onOpenChange={open => {
          if (!open) setDialogTerminado(null)
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Marcar como terminado</DialogTitle>
            {dialogTerminado?.preguntarContactoCliente ? (
              <DialogDescription className="text-base text-slate-800">
                ¿Usted ha contactado al cliente para pasos siguientes?
              </DialogDescription>
            ) : (
              <DialogDescription className="text-base text-slate-800">
                El caso pasará a <strong>Terminado</strong> (pasivo). Solo un
                administrador puede cambiar el estado después.
              </DialogDescription>
            )}
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setDialogTerminado(null)}
            >
              Cancelar
            </Button>
            {dialogTerminado?.preguntarContactoCliente ? (
              <>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => void confirmarTerminado(false)}
                >
                  No
                </Button>
                <Button
                  type="button"
                  className="bg-emerald-700 hover:bg-emerald-800"
                  onClick={() => void confirmarTerminado(true)}
                >
                  Sí
                </Button>
              </>
            ) : (
              <Button
                type="button"
                className="bg-emerald-700 hover:bg-emerald-800"
                onClick={() => void confirmarTerminado()}
              >
                Confirmar
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={pendingRechazoCasoId != null}
        onOpenChange={open => {
          if (!open) setPendingRechazoCasoId(null)
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Rechazar caso</DialogTitle>
            <DialogDescription className="text-base text-slate-800">
              ¿Confirma pasar este caso a <strong>Rechazado</strong>? Podrá
              revertirlo desde el área de revisión cambiando el estado.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setPendingRechazoCasoId(null)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => void confirmarRechazo()}
            >
              Rechazar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </FiniquitoWorkspaceShell>
  )
}

export function FiniquitoGestionPage() {
  const { isFiniquitador } = usePermissions()

  if (!isFiniquitador) {
    return (
      <div className="mx-auto max-w-3xl space-y-8 py-12">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Lock className="h-5 w-5 text-red-600" />
              <div>
                <p className="font-semibold text-red-800">Acceso Restringido</p>
                <p className="mt-1 text-sm text-red-700">
                  No tienes permisos para acceder a la gestión de finiquitos.
                  Contacta al administrador.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return <FiniquitoGestionPageInner />
}
