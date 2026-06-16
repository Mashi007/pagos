import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
  type RefObject,
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
  Pencil,
  RefreshCw,
  Search,
  Trash2,
  RotateCcw,
  X,
} from 'lucide-react'

import { toast } from 'sonner'

import { Button } from '../components/ui/button'

import { FiniquitoWorkspaceShell } from '../components/finiquito/FiniquitoWorkspaceShell'
import { FiniquitoRevisionDialog } from '../components/finiquito/FiniquitoRevisionDialog'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
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
  finiquitoAdminEliminarCaso,
  finiquitoAdminLiberarProcesosNormales,
  finiquitoAdminListar,
  finiquitoAdminListarTerminados,
  finiquitoAdminPasarATrabajo,
  finiquitoAdminPatchEstado,
  finiquitoAdminRefreshMaterializado,
  finiquitoAdminResumenEstado,
  finiquitoAdminResumenTerminadosDiario,
  type FiniquitoRefreshStats,
  type FiniquitoResumenEstado,
  type FiniquitoTerminadoItem,
  type FiniquitoTerminadosDia,
  FINIQUITO_HORAS_NUEVOS_REVISION_DEFAULT,
  FINIQUITO_TERMINADOS_RESUMEN_DIAS_DEFAULT,
} from '../services/finiquitoService'
import { descargarTerminadosExcel } from '../utils/finiquitoTerminadosExcelExport'
import {
  invalidateFiniquitoTerminadosCache,
  minutosDesdeCache,
  readFiniquitoTerminadosCache,
  writeFiniquitoTerminadosCache,
} from '../utils/finiquitoTerminadosCache'
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

/** Ciclo finiquito desde entrada a bandeja (dia 1 = alta del caso). */
const PLAZO_CICLO_DIAS = 30
/** Dias 1-2 en bandeja; desde dia 3 = atrasado si sigue en REVISION. */
const BANDEJA_DIA_ATRASADO = 3
/** Fase area revision: hasta 5 dias; dia 6 = atrasado. */
const AREA_REVISION_DIAS_MAX = 5
/** Fase revision contable: hasta 5 dias; dia 6 = atrasado. */
const AREA_REVISION_CONTABLE_DIAS_MAX = 5

/** Nomenclatura tiempo limite: F1 bandeja, F2 revision, F2C contable, F3 trabajo. */
const FASE_TIEMPO_BANDEJA = 'F1'
const FASE_TIEMPO_REVISION = 'F2'
const FASE_TIEMPO_CONTABLE = 'F2C'
const FASE_TIEMPO_TRABAJO = 'F3'

function parseIsoDate(iso: string | null | undefined): Date | null {
  if (iso == null || String(iso).trim() === '') return null
  const d = new Date(`${String(iso).slice(0, 10)}T00:00:00`)
  return Number.isNaN(d.getTime()) ? null : d
}

function hoyMedianoche(): Date {
  const hoy = new Date()
  hoy.setHours(0, 0, 0, 0)
  return hoy
}

function diasDesdeIsoDate(iso: string | null | undefined) {
  const d = parseIsoDate(iso)
  if (d == null) return null
  return Math.floor((hoyMedianoche().getTime() - d.getTime()) / 86_400_000)
}

function sumarDiasCalendario(iso: string, dias: number): string {
  const d = parseIsoDate(iso)
  if (d == null) return iso
  const out = new Date(d.getTime())
  out.setDate(out.getDate() + dias)
  return out.toISOString().slice(0, 10)
}

function maxIsoDate(a: string | null | undefined, b: string | null | undefined) {
  const da = parseIsoDate(a)
  const db = parseIsoDate(b)
  if (da == null) return b ?? null
  if (db == null) return a ?? null
  return da.getTime() >= db.getTime() ? a! : b!
}

/** Alta en finiquito (entrada a bandeja principal). */
function anchorCiclo(caso: FiniquitoCasoItem): string | null {
  return caso.creado_en ?? caso.fecha_liquidado ?? null
}

function diaOperativoCiclo(caso: FiniquitoCasoItem): number | null {
  const dias = diasDesdeIsoDate(anchorCiclo(caso))
  if (dias == null) return null
  return dias + 1
}

function finCicloIso(caso: FiniquitoCasoItem): string | null {
  const anchor = anchorCiclo(caso)
  if (anchor == null) return caso.finiquito_tramite_fecha_limite ?? null
  return sumarDiasCalendario(anchor.slice(0, 10), PLAZO_CICLO_DIAS - 1)
}

function diasRestantesHastaFinCiclo(caso: FiniquitoCasoItem): number | null {
  const fin = finCicloIso(caso)
  if (fin == null) return null
  const dFin = parseIsoDate(fin)
  if (dFin == null) return null
  return Math.floor((dFin.getTime() - hoyMedianoche().getTime()) / 86_400_000)
}

function bandejaAtrasado(caso: FiniquitoCasoItem): boolean {
  if (caso.estado !== 'REVISION') return false
  const dia = diaOperativoCiclo(caso)
  return dia != null && dia >= BANDEJA_DIA_ATRASADO
}

function inicioFaseAreaRevision(caso: FiniquitoCasoItem): string | null {
  const anchor = anchorCiclo(caso)
  if (anchor == null) return caso.fecha_entrada_aceptado ?? null
  const dia3 = sumarDiasCalendario(anchor.slice(0, 10), BANDEJA_DIA_ATRASADO - 1)
  return maxIsoDate(dia3, caso.fecha_entrada_aceptado)
}

function areaRevisionAtrasado(caso: FiniquitoCasoItem): boolean {
  if (caso.estado !== 'ACEPTADO') return false
  const dias = diasDesdeIsoDate(inicioFaseAreaRevision(caso))
  return dias != null && dias >= AREA_REVISION_DIAS_MAX
}

function inicioFaseRevisionContable(caso: FiniquitoCasoItem): string | null {
  return caso.fecha_entrada_revision_contable ?? null
}

function revisionContableAtrasado(caso: FiniquitoCasoItem): boolean {
  if (caso.estado !== 'REVISION_CONTABLE') return false
  const dias = diasDesdeIsoDate(inicioFaseRevisionContable(caso))
  return dias != null && dias >= AREA_REVISION_CONTABLE_DIAS_MAX
}

function casoAtrasado(caso: FiniquitoCasoItem): boolean {
  return (
    bandejaAtrasado(caso) ||
    areaRevisionAtrasado(caso) ||
    revisionContableAtrasado(caso)
  )
}

function diasRestantesBandeja(caso: FiniquitoCasoItem): number | null {
  if (caso.estado !== 'REVISION') return null
  const dia = diaOperativoCiclo(caso)
  if (dia == null) return null
  if (dia >= BANDEJA_DIA_ATRASADO) return 0
  return BANDEJA_DIA_ATRASADO - dia
}

function diasRestantesAreaRevision(caso: FiniquitoCasoItem): number | null {
  if (caso.estado !== 'ACEPTADO') return null
  const dias = diasDesdeIsoDate(inicioFaseAreaRevision(caso))
  if (dias == null) return null
  if (dias >= AREA_REVISION_DIAS_MAX) return 0
  return AREA_REVISION_DIAS_MAX - dias
}

function diasRestantesRevisionContable(caso: FiniquitoCasoItem): number | null {
  if (caso.estado !== 'REVISION_CONTABLE') return null
  const dias = diasDesdeIsoDate(inicioFaseRevisionContable(caso))
  if (dias == null) return null
  if (dias >= AREA_REVISION_CONTABLE_DIAS_MAX) return 0
  return AREA_REVISION_CONTABLE_DIAS_MAX - dias
}

function diasRestantesAreaTrabajo(caso: FiniquitoCasoItem): number | null {
  if (caso.estado !== 'EN_PROCESO') return null
  return diasRestantesHastaFinCiclo(caso)
}

function formatoTiempoFase(
  fase: string,
  restantes: number | null,
  total: number,
  etiquetaVencido: string
): string {
  if (restantes == null) return '-'
  if (restantes <= 0) return `${fase} - ${etiquetaVencido}`
  return `${fase} - ${restantes} de ${total} días`
}

function textoTiempoLimiteBandeja(caso: FiniquitoCasoItem): string {
  if (bandejaAtrasado(caso)) return `${FASE_TIEMPO_BANDEJA} - Atrasado`
  return formatoTiempoFase(
    FASE_TIEMPO_BANDEJA,
    diasRestantesBandeja(caso),
    BANDEJA_DIA_ATRASADO,
    'Atrasado'
  )
}

function textoTiempoLimiteAreaRevision(caso: FiniquitoCasoItem): string {
  if (areaRevisionAtrasado(caso)) return `${FASE_TIEMPO_REVISION} - Atrasado`
  return formatoTiempoFase(
    FASE_TIEMPO_REVISION,
    diasRestantesAreaRevision(caso),
    AREA_REVISION_DIAS_MAX,
    'Atrasado'
  )
}

function textoTiempoLimiteRevisionContable(caso: FiniquitoCasoItem): string {
  if (revisionContableAtrasado(caso)) {
    return `${FASE_TIEMPO_CONTABLE} - Atrasado`
  }
  return formatoTiempoFase(
    FASE_TIEMPO_CONTABLE,
    diasRestantesRevisionContable(caso),
    AREA_REVISION_CONTABLE_DIAS_MAX,
    'Atrasado'
  )
}

function totalDiasFaseTrabajo(caso: FiniquitoCasoItem): number | null {
  const restantes = diasRestantesAreaTrabajo(caso)
  if (restantes == null) return null
  const desdeEntrada = diasDesdeIsoDate(caso.fecha_entrada_en_proceso)
  if (desdeEntrada == null) return Math.max(restantes, 1)
  return Math.max(desdeEntrada + restantes, 1)
}

function textoTiempoLimiteAreaTrabajo(caso: FiniquitoCasoItem): string {
  const restantes = diasRestantesAreaTrabajo(caso)
  const total = totalDiasFaseTrabajo(caso)
  if (restantes == null || total == null) return '-'
  return formatoTiempoFase(
    FASE_TIEMPO_TRABAJO,
    restantes,
    total,
    'Vencido'
  )
}

type ModoTiempoTabla = 'bandeja' | 'revision' | 'contable'

function tiempoLimiteTabla(
  row: FiniquitoCasoItem,
  modoTiempo: ModoTiempoTabla
): { atrasado: boolean; diasRest: number | null; texto: string } {
  if (modoTiempo === 'bandeja') {
    return {
      atrasado: bandejaAtrasado(row),
      diasRest: diasRestantesBandeja(row),
      texto: textoTiempoLimiteBandeja(row),
    }
  }
  if (modoTiempo === 'contable') {
    return {
      atrasado: revisionContableAtrasado(row),
      diasRest: diasRestantesRevisionContable(row),
      texto: textoTiempoLimiteRevisionContable(row),
    }
  }
  return {
    atrasado: areaRevisionAtrasado(row),
    diasRest: diasRestantesAreaRevision(row),
    texto: textoTiempoLimiteAreaRevision(row),
  }
}

function claseTiempoLimite(
  dias: number | null,
  atrasado: boolean
): string {
  if (atrasado || (dias != null && dias <= 0)) {
    return 'bg-red-100 text-red-950'
  }
  if (dias != null && dias <= 2) return 'bg-amber-100 text-amber-950'
  return 'bg-emerald-100 text-emerald-950'
}

function estadoEtiquetaVisible(caso: FiniquitoCasoItem): string {
  if (casoAtrasado(caso)) return 'Atrasado'
  const map: Record<string, string> = {
    REVISION: 'Revision',
    ACEPTADO: 'Validado',
    REVISION_CONTABLE: 'Revision contable',
    RECHAZADO: 'Rechazado',
    EN_PROCESO: 'En proceso',
    TERMINADO: 'Terminado',
  }
  return map[caso.estado] ?? caso.estado.replace(/_/g, ' ')
}

function estadoBadgeClassName(caso: FiniquitoCasoItem): string {
  if (casoAtrasado(caso)) return 'bg-red-100 text-red-950'
  switch (caso.estado) {
    case 'REVISION':
      return 'bg-sky-100 text-sky-950'
    case 'ACEPTADO':
      return 'bg-amber-100 text-amber-950'
    case 'REVISION_CONTABLE':
      return 'bg-indigo-100 text-indigo-950'
    case 'RECHAZADO':
      return 'bg-rose-100 text-rose-950'
    case 'EN_PROCESO':
      return 'bg-emerald-100 text-emerald-950'
    case 'TERMINADO':
      return 'bg-violet-100 text-violet-950'
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
const AUTO_REFRESH_POLL_MS = 60_000

/** Tope visual del gráfico diario de terminados (outliers no comprimen el resto). */
const TERMINADOS_GRAFICO_ESCALA_MAX = 25
/** Altura visible de cada columna del gráfico diario (barra + número). */
const GRAFICO_DIA_ALTURA_BARRA_MAX = 72
const GRAFICO_DIA_COLOR_INGRESAN = '#f5b896'
const GRAFICO_DIA_COLOR_INGRESAN_VACIO = '#fde9d8'
const GRAFICO_DIA_COLOR_INGRESAN_ETIQUETA = '#c48655'

/** Coincide con backend `_ADMIN_CASOS_MAX_LIMIT` para bandejas pequeñas. */
const FETCH_LIMIT = 2000
const BANDEJA_PRINCIPAL_FETCH_LIMIT = 100

type FiniquitoAreaId = 'bandeja' | 'revision' | 'contable' | 'trabajo' | 'terminados'

const AREAS_CARGADAS_INICIAL: Record<FiniquitoAreaId, boolean> = {
  bandeja: false,
  revision: false,
  contable: false,
  trabajo: false,
  terminados: false,
}

const AREAS_LOADING_INICIAL: Record<FiniquitoAreaId, boolean> = {
  bandeja: false,
  revision: false,
  contable: false,
  trabajo: false,
  terminados: false,
}

function buildResumenDigest(snapshot: FiniquitoResumenEstado): string {
  return [
    snapshot.total,
    snapshot.revision,
    snapshot.aceptado,
    snapshot.revision_contable ?? 0,
    snapshot.rechazado,
    snapshot.en_proceso,
    snapshot.terminado,
    snapshot.max_ultimo_refresh_utc ?? '',
    snapshot.max_creado_en_utc ?? '',
  ].join('|')
}

function textoUbicacionOtrasAreasFiniquito(
  resumen: FiniquitoResumenEstado
): string | null {
  const partes: string[] = []
  if (resumen.aceptado > 0) {
    partes.push(`${resumen.aceptado} en área de revisión`)
  }
  if ((resumen.revision_contable ?? 0) > 0) {
    partes.push(`${resumen.revision_contable} en revisión contable`)
  }
  if (resumen.en_proceso > 0) {
    partes.push(`${resumen.en_proceso} en área de trabajo`)
  }
  if (resumen.terminado > 0) {
    partes.push(`${resumen.terminado} terminado(s)`)
  }
  if (resumen.rechazado > 0) {
    partes.push(`${resumen.rechazado} rechazado(s)`)
  }
  if (partes.length === 0) return null
  return partes.join(' · ')
}

function casoCoincideCedula(caso: FiniquitoCasoItem, filtro: string): boolean {
  const f = filtro.trim().toLowerCase()
  if (!f) return true
  return String(caso.cedula || '')
    .toLowerCase()
    .includes(f)
}

/** Para ordenar área de revisión: sin fecha al final. */
function timestampUltimoPago(iso: string | null | undefined): number {
  if (iso == null || String(iso).trim() === '') return Number.POSITIVE_INFINITY
  const t = Date.parse(String(iso))
  return Number.isNaN(t) ? Number.POSITIVE_INFINITY : t
}

function ordenarCasosPorUltimoPagoAsc(
  items: FiniquitoCasoItem[]
): FiniquitoCasoItem[] {
  return [...items].sort(
    (a, b) =>
      timestampUltimoPago(a.ultima_fecha_pago) -
      timestampUltimoPago(b.ultima_fecha_pago)
  )
}

type SeleccionFilasTabla = {
  selectedIds: Set<number>
  onToggleRow: (id: number, checked: boolean) => void
  onToggleAll: (checked: boolean) => void
  disabled: boolean
  todosSeleccionados: boolean
  algunSeleccionado: boolean
  estadoRequerido: string
  ariaSeleccionarTodos: string
}

type FiniquitoCedulaFiltroInlineProps = {
  id: string
  value: string
  onChange: (value: string) => void
  onClear: () => void
  placeholder?: string
  labelClassName?: string
  inputClassName?: string
  searchIconClassName?: string
  clearButtonClassName?: string
  ariaClear?: string
}

function FiniquitoCedulaFiltroInline({
  id,
  value,
  onChange,
  onClear,
  placeholder = 'Ej. V12345678',
  labelClassName = 'text-slate-700',
  inputClassName = 'border-slate-300 bg-white',
  searchIconClassName = 'text-slate-400',
  clearButtonClassName = 'text-slate-500 hover:bg-slate-100 hover:text-slate-800',
  ariaClear = 'Limpiar filtro',
}: FiniquitoCedulaFiltroInlineProps) {
  return (
    <div className="flex min-w-0 flex-1 items-center gap-2 sm:max-w-xs lg:max-w-[14rem] xl:max-w-xs">
      <Label
        htmlFor={id}
        className={cn('shrink-0 text-xs font-semibold', labelClassName)}
      >
        Filtro
      </Label>
      <div className="relative min-w-0 flex-1">
        <Search
          className={cn(
            'pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2',
            searchIconClassName
          )}
          aria-hidden
        />
        <Input
          id={id}
          type="search"
          autoComplete="off"
          placeholder={placeholder}
          value={value}
          onChange={e => onChange(e.target.value)}
          className={cn('h-9 w-full pl-8 pr-8 font-mono text-sm', inputClassName)}
        />
        {value ? (
          <button
            type="button"
            className={cn(
              'absolute right-1.5 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md',
              clearButtonClassName
            )}
            onClick={onClear}
            title="Limpiar filtro"
            aria-label={ariaClear}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        ) : null}
      </div>
    </div>
  )
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
  const { canTrasladarFiniquitoBandejas } = usePermissions()

  const [cedulaInput, setCedulaInput] = useState('')
  const [cedulaBusqueda, setCedulaBusqueda] = useState('')
  const [cedulaRevisionInput, setCedulaRevisionInput] = useState('')
  const [cedulaRevisionBusqueda, setCedulaRevisionBusqueda] = useState('')
  const [cedulaContableInput, setCedulaContableInput] = useState('')
  const [cedulaContableBusqueda, setCedulaContableBusqueda] = useState('')
  const [cedulaTrabajoInput, setCedulaTrabajoInput] = useState('')
  const [cedulaTrabajoBusqueda, setCedulaTrabajoBusqueda] = useState('')
  const [itemsAreaRevision, setItemsAreaRevision] = useState<FiniquitoCasoItem[]>(
    []
  )
  const [totalAreaRevision, setTotalAreaRevision] = useState(0)
  const [itemsAreaRevisionContable, setItemsAreaRevisionContable] = useState<
    FiniquitoCasoItem[]
  >([])
  const [totalAreaRevisionContable, setTotalAreaRevisionContable] = useState(0)
  const [itemsAreaTrabajo, setItemsAreaTrabajo] = useState<FiniquitoCasoItem[]>(
    []
  )
  const [totalAreaTrabajo, setTotalAreaTrabajo] = useState(0)
  const [dialogTerminado, setDialogTerminado] = useState<{
    casoId: number
  } | null>(null)
  const [itemsBandeja, setItemsBandeja] = useState<FiniquitoCasoItem[]>([])
  const [totalBandeja, setTotalBandeja] = useState(0)
  const [selectedBandejaIds, setSelectedBandejaIds] = useState<Set<number>>(
    () => new Set()
  )
  const [validandoBandejaLote, setValidandoBandejaLote] = useState(false)
  const [selectedRevisionIds, setSelectedRevisionIds] = useState<Set<number>>(
    () => new Set()
  )
  const [pasandoRevisionLote, setPasandoRevisionLote] = useState(false)
  const [selectedContableIds, setSelectedContableIds] = useState<Set<number>>(
    () => new Set()
  )
  const [pasandoContableLote, setPasandoContableLote] = useState(false)
  const [resumenEstado, setResumenEstado] = useState<FiniquitoResumenEstado | null>(
    null
  )
  const [resumenBandejaPorCedula, setResumenBandejaPorCedula] =
    useState<FiniquitoResumenEstado | null>(null)
  const [cargandoResumenBandejaPorCedula, setCargandoResumenBandejaPorCedula] =
    useState(false)
  const [loadingResumen, setLoadingResumen] = useState(true)
  const [areasCargadas, setAreasCargadas] = useState(AREAS_CARGADAS_INICIAL)
  const [areasLoading, setAreasLoading] = useState(AREAS_LOADING_INICIAL)
  const areasCargadasRef = useRef(areasCargadas)
  const revisionSectionRef = useRef<HTMLElement>(null)
  const contableSectionRef = useRef<HTMLElement>(null)
  const trabajoSectionRef = useRef<HTMLElement>(null)
  const terminadosSectionRef = useRef<HTMLElement>(null)
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
  const [pendingEliminarCasoId, setPendingEliminarCasoId] = useState<
    number | null
  >(null)
  const [pendingLiberarCaso, setPendingLiberarCaso] =
    useState<FiniquitoCasoItem | null>(null)
  const [revisionDialogCasoId, setRevisionDialogCasoId] = useState<
    number | null
  >(null)
  const [pendingVistoRow, setPendingVistoRow] = useState<FiniquitoCasoItem | null>(
    null
  )
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
  const [resumenDias, setResumenDias] = useState<FiniquitoTerminadosDia[]>([])
  const [totalTerminadosEnVentana, setTotalTerminadosEnVentana] = useState(0)
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
  const [terminadosFetchedAt, setTerminadosFetchedAt] = useState<number | null>(
    null
  )
  const [, setTerminadosRelojUi] = useState(0)
  const resumenDigestRef = useRef<string | null>(null)
  const refreshingRef = useRef(false)
  const bandejaFetchGenRef = useRef(0)
  const revisionFetchGenRef = useRef(0)
  const contableFetchGenRef = useRef(0)
  const trabajoFetchGenRef = useRef(0)
  const terminadosFetchGenRef = useRef(0)
  const terminadosGraficoScrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const t = window.setTimeout(
      () => setCedulaBusqueda(cedulaInput.trim()),
      DEBOUNCE_MS
    )
    return () => window.clearTimeout(t)
  }, [cedulaInput])

  useEffect(() => {
    const t = window.setTimeout(
      () => setCedulaRevisionBusqueda(cedulaRevisionInput.trim()),
      DEBOUNCE_MS
    )
    return () => window.clearTimeout(t)
  }, [cedulaRevisionInput])

  useEffect(() => {
    const t = window.setTimeout(
      () => setCedulaContableBusqueda(cedulaContableInput.trim()),
      DEBOUNCE_MS
    )
    return () => window.clearTimeout(t)
  }, [cedulaContableInput])

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

  useEffect(() => {
    areasCargadasRef.current = areasCargadas
  }, [areasCargadas])

  const marcarAreaCargada = useCallback((area: FiniquitoAreaId) => {
    setAreasCargadas(prev =>
      prev[area] ? prev : { ...prev, [area]: true }
    )
  }, [])

  const setAreaLoadingFlag = useCallback(
    (area: FiniquitoAreaId, value: boolean) => {
      setAreasLoading(prev =>
        prev[area] === value ? prev : { ...prev, [area]: value }
      )
    },
    []
  )

  const cargarResumenKpis = useCallback(async (opts?: { silent?: boolean }) => {
    const silent = opts?.silent === true
    if (!silent) setLoadingResumen(true)
    try {
      const snapshot = await finiquitoAdminResumenEstado()
      setResumenEstado(snapshot)
      resumenDigestRef.current = buildResumenDigest(snapshot)
    } catch {
      if (!silent) {
        toast.error('No se pudo cargar el resumen de finiquitos')
      }
    } finally {
      if (!silent) setLoadingResumen(false)
    }
  }, [])

  const cargarBandeja = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = opts?.silent === true
      const gen = ++bandejaFetchGenRef.current
      const cedulaFiltro = cedulaBusqueda
      if (!silent) setAreaLoadingFlag('bandeja', true)
      try {
        const [rBandeja, rNuevos] = await Promise.all([
          finiquitoAdminListar(
            'REVISION',
            cedulaFiltro || undefined,
            undefined,
            {
              limit: BANDEJA_PRINCIPAL_FETCH_LIMIT,
              offset: 0,
            }
          ),
          finiquitoAdminConteoRevisionNuevos(
            cedulaFiltro || undefined,
            FINIQUITO_HORAS_NUEVOS_REVISION_DEFAULT
          ),
        ])
        if (gen !== bandejaFetchGenRef.current) return
        setItemsBandeja(rBandeja.items || [])
        setTotalBandeja(rBandeja.total ?? (rBandeja.items || []).length)
        setKpiNuevosRevision({
          total: rNuevos.total ?? 0,
          ventana_horas:
            rNuevos.ventana_horas ?? FINIQUITO_HORAS_NUEVOS_REVISION_DEFAULT,
        })
        marcarAreaCargada('bandeja')
      } catch (e: unknown) {
        if (gen !== bandejaFetchGenRef.current) return
        if (!silent) {
          toast.error(e instanceof Error ? e.message : 'Error al cargar bandeja')
        }
      } finally {
        if (gen === bandejaFetchGenRef.current && !silent) {
          setAreaLoadingFlag('bandeja', false)
        }
      }
    },
    [cedulaBusqueda, marcarAreaCargada, setAreaLoadingFlag]
  )

  const cargarAreaRevision = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = opts?.silent === true
      const gen = ++revisionFetchGenRef.current
      const cedulaFiltro = cedulaRevisionBusqueda
      if (!silent) setAreaLoadingFlag('revision', true)
      try {
        const rRevision = await finiquitoAdminListar(
          'ACEPTADO',
          cedulaFiltro || undefined,
          undefined,
          { limit: FETCH_LIMIT, offset: 0 }
        )
        if (gen !== revisionFetchGenRef.current) return
        setItemsAreaRevision(rRevision.items || [])
        setTotalAreaRevision(
          rRevision.total ?? (rRevision.items || []).length
        )
        marcarAreaCargada('revision')
      } catch (e: unknown) {
        if (gen !== revisionFetchGenRef.current) return
        if (!silent) {
          toast.error(
            e instanceof Error ? e.message : 'Error al cargar área de revisión'
          )
        }
      } finally {
        if (gen === revisionFetchGenRef.current && !silent) {
          setAreaLoadingFlag('revision', false)
        }
      }
    },
    [cedulaRevisionBusqueda, marcarAreaCargada, setAreaLoadingFlag]
  )

  const cargarAreaRevisionContable = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = opts?.silent === true
      const gen = ++contableFetchGenRef.current
      const cedulaFiltro = cedulaContableBusqueda
      if (!silent) setAreaLoadingFlag('contable', true)
      try {
        const rContable = await finiquitoAdminListar(
          'REVISION_CONTABLE',
          cedulaFiltro || undefined,
          undefined,
          { limit: FETCH_LIMIT, offset: 0 }
        )
        if (gen !== contableFetchGenRef.current) return
        setItemsAreaRevisionContable(rContable.items || [])
        setTotalAreaRevisionContable(
          rContable.total ?? (rContable.items || []).length
        )
        marcarAreaCargada('contable')
      } catch (e: unknown) {
        if (gen !== contableFetchGenRef.current) return
        if (!silent) {
          toast.error(
            e instanceof Error ? e.message : 'Error al cargar revision contable'
          )
        }
      } finally {
        if (gen === contableFetchGenRef.current && !silent) {
          setAreaLoadingFlag('contable', false)
        }
      }
    },
    [cedulaContableBusqueda, marcarAreaCargada, setAreaLoadingFlag]
  )

  const cargarAreaTrabajo = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = opts?.silent === true
      const gen = ++trabajoFetchGenRef.current
      const cedulaFiltro = cedulaTrabajoBusqueda
      if (!silent) setAreaLoadingFlag('trabajo', true)
      try {
        const rTrabajo = await finiquitoAdminListar(
          'EN_PROCESO',
          cedulaFiltro || undefined,
          undefined,
          { limit: FETCH_LIMIT, offset: 0 }
        )
        if (gen !== trabajoFetchGenRef.current) return
        setItemsAreaTrabajo(rTrabajo.items || [])
        setTotalAreaTrabajo(rTrabajo.total ?? (rTrabajo.items || []).length)
        marcarAreaCargada('trabajo')
      } catch (e: unknown) {
        if (gen !== trabajoFetchGenRef.current) return
        if (!silent) {
          toast.error(
            e instanceof Error ? e.message : 'Error al cargar área de trabajo'
          )
        }
      } finally {
        if (gen === trabajoFetchGenRef.current && !silent) {
          setAreaLoadingFlag('trabajo', false)
        }
      }
    },
    [cedulaTrabajoBusqueda, marcarAreaCargada, setAreaLoadingFlag]
  )

  const cargarTerminados = useCallback(
    async (opts?: { silent?: boolean; force?: boolean }) => {
      const silent = opts?.silent === true
      const force = opts?.force === true
      const gen = ++terminadosFetchGenRef.current
      const cedulaFiltro = cedulaTerminadosBusqueda

      const aplicarPayload = (
        items: FiniquitoTerminadoItem[],
        total: number,
        dias: FiniquitoTerminadosDia[],
        totalEnVentana: number,
        totalResumen: number,
        fetchedAt: number
      ) => {
        setItemsTerminados(items)
        setTotalTerminados(total)
        setResumenDias(dias)
        setTotalTerminadosEnVentana(totalEnVentana)
        setTotalTerminadosResumen(totalResumen)
        setTerminadosFetchedAt(fetchedAt)
        marcarAreaCargada('terminados')
      }

      if (!force) {
        const cached = readFiniquitoTerminadosCache(
          cedulaFiltro,
          FINIQUITO_TERMINADOS_RESUMEN_DIAS_DEFAULT
        )
        if (cached) {
          aplicarPayload(
            cached.items,
            cached.totalTerminados,
            cached.resumenDias,
            cached.totalEnVentana,
            cached.totalTerminadosResumen,
            cached.fetchedAt
          )
          const cacheAgeMs = Date.now() - cached.fetchedAt
          if (cacheAgeMs >= AUTO_REFRESH_POLL_MS) {
            void (async () => {
              try {
                const [rTerm, rSem] = await Promise.all([
                  finiquitoAdminListarTerminados(cedulaFiltro || undefined, {
                    limit: FETCH_LIMIT,
                    offset: 0,
                  }),
                  finiquitoAdminResumenTerminadosDiario(
                    cedulaFiltro || undefined,
                    FINIQUITO_TERMINADOS_RESUMEN_DIAS_DEFAULT
                  ),
                ])
                if (gen !== terminadosFetchGenRef.current) return
                const fetchedAt = Date.now()
                const items = rTerm.items || []
                const total = rTerm.total ?? items.length
                const dias = rSem.dias || []
                aplicarPayload(
                  items,
                  total,
                  dias,
                  rSem.total_en_ventana ?? 0,
                  rSem.total_terminados ?? 0,
                  fetchedAt
                )
                writeFiniquitoTerminadosCache({
                  fetchedAt,
                  cedula: cedulaFiltro,
                  dias: FINIQUITO_TERMINADOS_RESUMEN_DIAS_DEFAULT,
                  items,
                  totalTerminados: total,
                  resumenDias: dias,
                  totalEnVentana: rSem.total_en_ventana ?? 0,
                  totalTerminadosResumen: rSem.total_terminados ?? 0,
                })
              } catch {
                // Revalidacion en segundo plano: no interrumpir la UI.
              }
            })()
          }
          return
        }
      }

      if (!silent) setAreaLoadingFlag('terminados', true)
      try {
        const [rTerm, rSem] = await Promise.all([
          finiquitoAdminListarTerminados(cedulaFiltro || undefined, {
            limit: FETCH_LIMIT,
            offset: 0,
          }),
          finiquitoAdminResumenTerminadosDiario(
            cedulaFiltro || undefined,
            FINIQUITO_TERMINADOS_RESUMEN_DIAS_DEFAULT
          ),
        ])
        if (gen !== terminadosFetchGenRef.current) return
        const fetchedAt = Date.now()
        const items = rTerm.items || []
        const total = rTerm.total ?? items.length
        const dias = rSem.dias || []
        aplicarPayload(
          items,
          total,
          dias,
          rSem.total_en_ventana ?? 0,
          rSem.total_terminados ?? 0,
          fetchedAt
        )
        writeFiniquitoTerminadosCache({
          fetchedAt,
          cedula: cedulaFiltro,
          dias: FINIQUITO_TERMINADOS_RESUMEN_DIAS_DEFAULT,
          items,
          totalTerminados: total,
          resumenDias: dias,
          totalEnVentana: rSem.total_en_ventana ?? 0,
          totalTerminadosResumen: rSem.total_terminados ?? 0,
        })
      } catch (e: unknown) {
        if (gen !== terminadosFetchGenRef.current) return
        if (!silent) {
          toast.error(
            e instanceof Error ? e.message : 'Error al cargar terminados'
          )
        }
      } finally {
        if (gen === terminadosFetchGenRef.current && !silent) {
          setAreaLoadingFlag('terminados', false)
        }
      }
    },
    [cedulaTerminadosBusqueda, marcarAreaCargada, setAreaLoadingFlag]
  )

  /** Recarga solo las áreas que el usuario ya abrió (polling / tras acciones). */
  const cargarAreasVisibles = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = opts?.silent === true
      const cargadas = areasCargadasRef.current
      const tasks: Promise<void>[] = [cargarResumenKpis({ silent: true })]
      if (cargadas.bandeja) tasks.push(cargarBandeja({ silent: true }))
      if (cargadas.revision) tasks.push(cargarAreaRevision({ silent: true }))
      if (cargadas.contable) tasks.push(cargarAreaRevisionContable({ silent: true }))
      if (cargadas.trabajo) tasks.push(cargarAreaTrabajo({ silent: true }))
      if (cargadas.terminados) {
        tasks.push(cargarTerminados({ silent: true, force: silent }))
      }
      await Promise.all(tasks)
    },
    [
      cargarAreaRevision,
      cargarAreaRevisionContable,
      cargarAreaTrabajo,
      cargarBandeja,
      cargarResumenKpis,
      cargarTerminados,
    ]
  )

  const itemsBandejaVisibles = useMemo(
    () =>
      itemsBandeja.filter(row => casoCoincideCedula(row, cedulaBusqueda)),
    [itemsBandeja, cedulaBusqueda]
  )

  const itemsAreaRevisionVisibles = useMemo(
    () =>
      ordenarCasosPorUltimoPagoAsc(
        itemsAreaRevision.filter(row =>
          casoCoincideCedula(row, cedulaRevisionBusqueda)
        )
      ),
    [itemsAreaRevision, cedulaRevisionBusqueda]
  )

  const itemsAreaRevisionContableVisibles = useMemo(
    () =>
      ordenarCasosPorUltimoPagoAsc(
        itemsAreaRevisionContable.filter(row =>
          casoCoincideCedula(row, cedulaContableBusqueda)
        )
      ),
    [itemsAreaRevisionContable, cedulaContableBusqueda]
  )

  const itemsAreaTrabajoVisibles = useMemo(
    () =>
      itemsAreaTrabajo.filter(row =>
        casoCoincideCedula(row, cedulaTrabajoBusqueda)
      ),
    [itemsAreaTrabajo, cedulaTrabajoBusqueda]
  )

  const itemsTerminadosFiltrados = useMemo(
    () =>
      itemsTerminados.filter(row =>
        terminadoCoincideFiltrosTabla(row, filtrosTerminados)
      ),
    [itemsTerminados, filtrosTerminados]
  )

  const escalaMaxTerminadosGrafico = useMemo(() => {
    const vals = resumenDias
      .flatMap(d => [d.cantidad, d.cantidad_ingresos ?? 0])
      .filter(c => c > 0)
    const dataMax = vals.length ? Math.max(...vals) : 0
    return Math.min(
      TERMINADOS_GRAFICO_ESCALA_MAX,
      Math.max(1, dataMax)
    )
  }, [resumenDias])

  const alturaBarraGraficoDiario = (cantidad: number) => {
    if (cantidad <= 0) return 4
    const paraEscala = Math.min(cantidad, TERMINADOS_GRAFICO_ESCALA_MAX)
    return Math.max(
      4,
      Math.round(
        (paraEscala / escalaMaxTerminadosGrafico) * GRAFICO_DIA_ALTURA_BARRA_MAX
      )
    )
  }

  const renderColumnaBarraGraficoDiario = (
    valor: number,
    opts: {
      barClass: string
      barEmptyClass: string
      labelClass: string
      barStyle?: CSSProperties
      barEmptyStyle?: CSSProperties
      labelStyle?: CSSProperties
    }
  ) => {
    const fuera = valor > TERMINADOS_GRAFICO_ESCALA_MAX
    const barH = alturaBarraGraficoDiario(valor)
    return (
      <div
        className="relative flex w-3.5 shrink-0 flex-col items-center justify-end"
        style={{ height: GRAFICO_DIA_ALTURA_BARRA_MAX + 12 }}
      >
        <span
          className={cn(
            'absolute left-1/2 z-[1] -translate-x-1/2 whitespace-nowrap text-[8px] font-semibold tabular-nums leading-none',
            opts.labelClass,
            fuera && 'text-amber-900'
          )}
          style={{ bottom: barH + 2, ...opts.labelStyle }}
        >
          {valor}
        </span>
        <div
          className={cn(
            'w-3 rounded-t-sm transition-all',
            valor > 0 ? opts.barClass : opts.barEmptyClass,
            fuera && 'ring-1 ring-amber-400/90'
          )}
          style={{
            height: barH,
            ...(valor > 0 ? opts.barStyle : opts.barEmptyStyle),
          }}
        />
      </div>
    )
  }

  /** Mueve filas locales al instante con el caso devuelto por PATCH (antes del refetch). */
  const incorporarCasoActualizado = useCallback(
    (caso: FiniquitoCasoItem) => {
      const debeAreaRevision =
        caso.estado === 'ACEPTADO' &&
        casoCoincideCedula(caso, cedulaRevisionBusqueda)
      const debeAreaContable =
        caso.estado === 'REVISION_CONTABLE' &&
        casoCoincideCedula(caso, cedulaContableBusqueda)
      const debeAreaTrabajo =
        caso.estado === 'EN_PROCESO' &&
        casoCoincideCedula(caso, cedulaTrabajoBusqueda)
      const debeBandeja =
        caso.estado === 'REVISION' && casoCoincideCedula(caso, cedulaBusqueda)
      const estabaAreaRevision = itemsAreaRevision.some(r => r.id === caso.id)
      const estabaAreaContable = itemsAreaRevisionContable.some(
        r => r.id === caso.id
      )
      const estabaAreaTrabajo = itemsAreaTrabajo.some(r => r.id === caso.id)
      const estabaBandeja = itemsBandeja.some(r => r.id === caso.id)

      setItemsAreaRevision(prev =>
        reconciliarCasoEnLista(prev, caso, debeAreaRevision)
      )
      setTotalAreaRevision(prev =>
        totalTrasMovimiento(prev, estabaAreaRevision, debeAreaRevision)
      )
      setItemsAreaRevisionContable(prev =>
        reconciliarCasoEnLista(prev, caso, debeAreaContable)
      )
      setTotalAreaRevisionContable(prev =>
        totalTrasMovimiento(prev, estabaAreaContable, debeAreaContable)
      )
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
    },
    [
      cedulaBusqueda,
      cedulaRevisionBusqueda,
      cedulaContableBusqueda,
      cedulaTrabajoBusqueda,
      itemsAreaRevision,
      itemsAreaRevisionContable,
      itemsAreaTrabajo,
      itemsBandeja,
    ]
  )

  useEffect(() => {
    void cargarResumenKpis()
  }, [cargarResumenKpis])

  useEffect(() => {
    if (!areasCargadas.terminados) return
    const id = window.setInterval(() => {
      setTerminadosRelojUi(t => t + 1)
    }, 30_000)
    return () => window.clearInterval(id)
  }, [areasCargadas.terminados])

  useEffect(() => {
    void cargarBandeja()
  }, [cedulaBusqueda, cargarBandeja])

  useEffect(() => {
    const cedula = cedulaBusqueda.trim()
    if (!cedula) {
      setResumenBandejaPorCedula(null)
      setCargandoResumenBandejaPorCedula(false)
      return
    }
    if (areasLoading.bandeja || itemsBandejaVisibles.length > 0) {
      setResumenBandejaPorCedula(null)
      setCargandoResumenBandejaPorCedula(false)
      return
    }

    let cancelled = false
    setCargandoResumenBandejaPorCedula(true)
    void finiquitoAdminResumenEstado(cedula)
      .then(snapshot => {
        if (!cancelled) setResumenBandejaPorCedula(snapshot)
      })
      .catch(() => {
        if (!cancelled) setResumenBandejaPorCedula(null)
      })
      .finally(() => {
        if (!cancelled) setCargandoResumenBandejaPorCedula(false)
      })

    return () => {
      cancelled = true
    }
  }, [cedulaBusqueda, itemsBandejaVisibles.length, areasLoading.bandeja])

  useEffect(() => {
    if (!areasCargadas.revision) return
    void cargarAreaRevision()
  }, [areasCargadas.revision, cedulaRevisionBusqueda, cargarAreaRevision])

  useEffect(() => {
    if (!areasCargadas.contable) return
    void cargarAreaRevisionContable()
  }, [areasCargadas.contable, cedulaContableBusqueda, cargarAreaRevisionContable])

  useEffect(() => {
    if (!areasCargadas.trabajo) return
    void cargarAreaTrabajo()
  }, [areasCargadas.trabajo, cedulaTrabajoBusqueda, cargarAreaTrabajo])

  useEffect(() => {
    if (!areasCargadas.terminados) return
    void cargarTerminados()
  }, [areasCargadas.terminados, cedulaTerminadosBusqueda, cargarTerminados])

  /** Al cargar o actualizar datos, el scroll queda al final (Hoy / Ayer visibles). */
  useEffect(() => {
    const el = terminadosGraficoScrollRef.current
    if (!el || resumenDias.length === 0) return
    const scrollAlFinal = () => {
      el.scrollLeft = el.scrollWidth
    }
    scrollAlFinal()
    const raf = requestAnimationFrame(scrollAlFinal)
    return () => cancelAnimationFrame(raf)
  }, [resumenDias, cedulaTerminadosBusqueda])

  useEffect(() => {
    const secciones: {
      ref: RefObject<HTMLElement | null>
      area: FiniquitoAreaId
      cargar: () => void
    }[] = [
      {
        ref: revisionSectionRef,
        area: 'revision',
        cargar: () => void cargarAreaRevision(),
      },
      {
        ref: contableSectionRef,
        area: 'contable',
        cargar: () => void cargarAreaRevisionContable(),
      },
      {
        ref: trabajoSectionRef,
        area: 'trabajo',
        cargar: () => void cargarAreaTrabajo(),
      },
      {
        ref: terminadosSectionRef,
        area: 'terminados',
        cargar: () => void cargarTerminados(),
      },
    ]

    const observer = new IntersectionObserver(
      entries => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          const match = secciones.find(s => s.ref.current === entry.target)
          if (!match) continue
          if (areasCargadasRef.current[match.area]) continue
          match.cargar()
        }
      },
      { root: null, rootMargin: '160px 0px', threshold: 0.01 }
    )

    for (const s of secciones) {
      if (s.ref.current) observer.observe(s.ref.current)
    }

    return () => observer.disconnect()
  }, [cargarAreaRevision, cargarAreaRevisionContable, cargarAreaTrabajo, cargarTerminados])

  useEffect(() => {
    refreshingRef.current = refreshing
  }, [refreshing])

  /** KPIs sticky: resumen-estado cada 1 min (independiente del grafico). */
  useEffect(() => {
    const tickResumen = async () => {
      if (document.hidden || refreshingRef.current) return
      try {
        const snapshot = await finiquitoAdminResumenEstado()
        const digest = buildResumenDigest(snapshot)
        setResumenEstado(snapshot)
        const digestChanged =
          resumenDigestRef.current != null &&
          digest !== resumenDigestRef.current
        resumenDigestRef.current = digest
        if (digestChanged) {
          invalidateFiniquitoTerminadosCache()
          void invalidatePrestamosQueries(queryClient)
          await cargarAreasVisibles({ silent: true })
        }
      } catch {
        // Polling silencioso: no interrumpir la gestion por fallos transitorios.
      }
    }

    const intervalId = window.setInterval(() => {
      void tickResumen()
    }, AUTO_REFRESH_POLL_MS)
    void tickResumen()
    return () => window.clearInterval(intervalId)
  }, [cargarAreasVisibles, queryClient])

  /** Grafico Terminados / Ingresan: refresh cada 1 min sin depender del resumen KPI. */
  useEffect(() => {
    if (!areasCargadas.terminados) return

    const tickGrafico = () => {
      if (document.hidden || refreshingRef.current) return
      void cargarTerminados({ silent: true, force: true })
    }

    const intervalId = window.setInterval(tickGrafico, AUTO_REFRESH_POLL_MS)
    tickGrafico()
    return () => window.clearInterval(intervalId)
  }, [areasCargadas.terminados, cargarTerminados, cedulaTerminadosBusqueda])

  const onRefreshJob = async () => {
    setRefreshing(true)
    try {
      const r = await finiquitoAdminRefreshMaterializado()
      const { titulo, descripcion } = textoToastRefresco(r)
      toast.success(titulo, { description: descripcion })
      void invalidatePrestamosQueries(queryClient)
      await cargarAreasVisibles({ silent: true })
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
    const row =
      itemsBandeja.find(r => r.id === id) ??
      itemsAreaRevision.find(r => r.id === id) ??
      itemsAreaRevisionContable.find(r => r.id === id) ??
      itemsAreaTrabajo.find(r => r.id === id)
    if (
      !canTrasladarFiniquitoBandejas &&
      row &&
      ((estado === 'ACEPTADO' && row.estado === 'REVISION') ||
        (estado === 'REVISION_CONTABLE' && row.estado === 'ACEPTADO'))
    ) {
      toast.error(
        'Solo administradores pueden trasladar casos entre bandeja principal, area de revision, revision contable y area de trabajo.'
      )
      return
    }
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
      if (estado === 'ACEPTADO') {
        toast.success('Caso validado: pasa al area de revision')
      } else if (estado === 'REVISION_CONTABLE') {
        toast.success('Caso en revision contable')
      } else if (estado === 'EN_PROCESO') {
        toast.success('Caso en area de trabajo')
      } else if (estado === 'REVISION') {
        toast.success('Caso devuelto a bandeja principal')
      } else {
        toast.success('Estado actualizado')
      }
      void invalidatePrestamosQueries(queryClient)
      await cargarAreasVisibles({ silent: true })
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error')
    } finally {
      setPendingEstadoCasoId(null)
    }
  }

  const confirmarRechazo = async () => {
    if (pendingRechazoCasoId == null) return
    const id = pendingRechazoCasoId
    setPendingRechazoCasoId(null)
    await cambiarEstado(id, 'RECHAZADO')
  }

  const confirmarLiberarProcesosNormales = async () => {
    if (pendingLiberarCaso == null) return
    const row = pendingLiberarCaso
    setPendingLiberarCaso(null)
    if (pendingEstadoCasoId != null) return
    setPendingEstadoCasoId(row.id)
    try {
      const r = await finiquitoAdminLiberarProcesosNormales(row.id)
      if (!r.ok) {
        toast.error(r.error || 'No se pudo liberar el préstamo')
        return
      }
      setItemsBandeja(prev => prev.filter(c => c.id !== row.id))
      setTotalBandeja(prev => Math.max(0, prev - 1))
      setItemsAreaRevision(prev => prev.filter(c => c.id !== row.id))
      setTotalAreaRevision(prev => Math.max(0, prev - 1))
      setItemsAreaRevisionContable(prev => prev.filter(c => c.id !== row.id))
      setTotalAreaRevisionContable(prev => Math.max(0, prev - 1))
      toast.success(
        r.mensaje ||
          `Préstamo #${r.prestamo_id ?? row.prestamo_id} en procesos normales (cartera).`
      )
      void invalidatePrestamosQueries(queryClient)
      await cargarResumenKpis({ silent: true })
      await cargarAreasVisibles({ silent: true })
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al liberar')
    } finally {
      setPendingEstadoCasoId(null)
    }
  }

  const confirmarEliminar = async () => {
    if (pendingEliminarCasoId == null) return
    const id = pendingEliminarCasoId
    setPendingEliminarCasoId(null)
    if (pendingEstadoCasoId != null) return
    setPendingEstadoCasoId(id)
    try {
      const r = await finiquitoAdminEliminarCaso(id)
      if (!r.ok) {
        toast.error(r.error || 'No se pudo eliminar')
        return
      }
      setItemsBandeja(prev => prev.filter(row => row.id !== id))
      setTotalBandeja(prev => Math.max(0, prev - 1))
      toast.success('Caso eliminado de la bandeja')
      void invalidatePrestamosQueries(queryClient)
      await cargarAreasVisibles({ silent: true })
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al eliminar')
    } finally {
      setPendingEstadoCasoId(null)
    }
  }

  const confirmarTerminado = async (contactoParaSiguientes?: boolean) => {
    if (dialogTerminado == null) return
    const { casoId } = dialogTerminado
    if (contactoParaSiguientes === undefined) {
      return
    }
    if (pendingEstadoCasoId != null) return
    setPendingEstadoCasoId(casoId)
    try {
      const r = await finiquitoAdminPatchEstado(
        casoId,
        'TERMINADO',
        contactoParaSiguientes
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
      invalidateFiniquitoTerminadosCache()
      void invalidatePrestamosQueries(queryClient)
      await cargarTerminados({ silent: true, force: true })
      await cargarAreasVisibles({ silent: true })
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

  const limpiarCedulaRevision = () => {
    setCedulaRevisionInput('')
    setCedulaRevisionBusqueda('')
  }

  const limpiarCedulaContable = () => {
    setCedulaContableInput('')
    setCedulaContableBusqueda('')
  }

  const limpiarCedulaTrabajo = () => {
    setCedulaTrabajoInput('')
    setCedulaTrabajoBusqueda('')
  }

  const limpiarCedulaTerminados = () => {
    setCedulaTerminadosInput('')
    setCedulaTerminadosBusqueda('')
  }

  const buscarCedulaEnTerminados = (cedula: string) => {
    const c = cedula.trim()
    if (!c) return
    setCedulaTerminadosInput(c)
    setCedulaTerminadosBusqueda(c)
    void cargarTerminados()
    window.setTimeout(() => {
      terminadosSectionRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      })
    }, 80)
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
    pendingEstadoCasoId === casoId ||
    validandoBandejaLote ||
    pasandoRevisionLote

  useEffect(() => {
    setSelectedBandejaIds(prev => {
      if (prev.size === 0) return prev
      const visibles = new Set(itemsBandejaVisibles.map(r => r.id))
      const next = new Set(Array.from(prev).filter(id => visibles.has(id)))
      return next.size === prev.size ? prev : next
    })
  }, [itemsBandejaVisibles])

  useEffect(() => {
    setSelectedRevisionIds(prev => {
      if (prev.size === 0) return prev
      const visibles = new Set(itemsAreaRevisionVisibles.map(r => r.id))
      const next = new Set(Array.from(prev).filter(id => visibles.has(id)))
      return next.size === prev.size ? prev : next
    })
  }, [itemsAreaRevisionVisibles])

  const idsBandejaSeleccionables = useMemo(
    () =>
      itemsBandejaVisibles
        .filter(r => (r.estado || '').toUpperCase() === 'REVISION')
        .map(r => r.id),
    [itemsBandejaVisibles]
  )

  const todosBandejaSeleccionados =
    idsBandejaSeleccionables.length > 0 &&
    idsBandejaSeleccionables.every(id => selectedBandejaIds.has(id))

  const algunBandejaSeleccionado =
    !todosBandejaSeleccionados &&
    idsBandejaSeleccionables.some(id => selectedBandejaIds.has(id))

  const idsRevisionSeleccionables = useMemo(
    () =>
      itemsAreaRevisionVisibles
        .filter(r => (r.estado || '').toUpperCase() === 'ACEPTADO')
        .map(r => r.id),
    [itemsAreaRevisionVisibles]
  )

  const todosRevisionSeleccionados =
    idsRevisionSeleccionables.length > 0 &&
    idsRevisionSeleccionables.every(id => selectedRevisionIds.has(id))

  const algunRevisionSeleccionado =
    !todosRevisionSeleccionados &&
    idsRevisionSeleccionables.some(id => selectedRevisionIds.has(id))

  const idsContableSeleccionables = useMemo(
    () =>
      itemsAreaRevisionContableVisibles
        .filter(r => (r.estado || '').toUpperCase() === 'REVISION_CONTABLE')
        .map(r => r.id),
    [itemsAreaRevisionContableVisibles]
  )

  const todosContableSeleccionados =
    idsContableSeleccionables.length > 0 &&
    idsContableSeleccionables.every(id => selectedContableIds.has(id))

  const algunContableSeleccionado =
    !todosContableSeleccionados &&
    idsContableSeleccionables.some(id => selectedContableIds.has(id))

  const validarBandejaEnLote = async () => {
    if (!canTrasladarFiniquitoBandejas || validandoBandejaLote) return
    const ids = idsBandejaSeleccionables.filter(id => selectedBandejaIds.has(id))
    if (ids.length === 0) {
      toast.message('Seleccione al menos un caso en la bandeja principal.')
      return
    }
    const confirmado = window.confirm(
      `¿Validar ${ids.length} caso(s)? Pasarán al área de revisión (no procesa datos ni concilia).`
    )
    if (!confirmado) return

    setValidandoBandejaLote(true)
    let ok = 0
    let fail = 0
    const errores: string[] = []
    try {
      for (const id of ids) {
        try {
          const r = await finiquitoAdminPatchEstado(id, 'ACEPTADO')
          if (r.ok && r.caso) {
            incorporarCasoActualizado(r.caso)
            ok += 1
          } else {
            fail += 1
            errores.push(`Caso ${id}: ${r.error || 'no se pudo validar'}`)
          }
        } catch (e: unknown) {
          fail += 1
          errores.push(
            `Caso ${id}: ${e instanceof Error ? e.message : 'error de red'}`
          )
        }
      }
      setSelectedBandejaIds(new Set())
      void invalidatePrestamosQueries(queryClient)
      await cargarAreasVisibles({ silent: true })
      if (fail === 0) {
        toast.success(
          `${ok} caso(s) validados: pasan al área de revisión.`
        )
      } else if (ok > 0) {
        toast.warning(
          `${ok} validados, ${fail} con error. ${errores.slice(0, 2).join(' · ')}`
        )
      } else {
        toast.error(
          errores.slice(0, 3).join(' · ') || 'No se pudo validar ningún caso.'
        )
      }
    } finally {
      setValidandoBandejaLote(false)
    }
  }

  const pasarRevisionContableEnLote = async () => {
    if (!canTrasladarFiniquitoBandejas || pasandoRevisionLote) return
    const ids = idsRevisionSeleccionables.filter(id =>
      selectedRevisionIds.has(id)
    )
    if (ids.length === 0) {
      toast.message('Seleccione al menos un caso en el area de revision.')
      return
    }
    const confirmado = window.confirm(
      `¿Pasar ${ids.length} caso(s) a revision contable?`
    )
    if (!confirmado) return

    setPasandoRevisionLote(true)
    let ok = 0
    let fail = 0
    const errores: string[] = []
    try {
      for (const id of ids) {
        try {
          const r = await finiquitoAdminPatchEstado(id, 'REVISION_CONTABLE')
          if (r.ok && r.caso) {
            incorporarCasoActualizado(r.caso)
            ok += 1
          } else {
            fail += 1
            errores.push(
              `Caso ${id}: ${r.error || 'no se pudo pasar a revision contable'}`
            )
          }
        } catch (e: unknown) {
          fail += 1
          errores.push(
            `Caso ${id}: ${e instanceof Error ? e.message : 'error de red'}`
          )
        }
      }
      setSelectedRevisionIds(new Set())
      void invalidatePrestamosQueries(queryClient)
      await cargarAreasVisibles({ silent: true })
      if (fail === 0) {
        toast.success(`${ok} caso(s) en revision contable.`)
      } else if (ok > 0) {
        toast.warning(
          `${ok} movidos, ${fail} con error. ${errores.slice(0, 2).join(' · ')}`
        )
      } else {
        toast.error(
          errores.slice(0, 3).join(' · ') ||
            'No se pudo pasar ningun caso a revision contable.'
        )
      }
    } finally {
      setPasandoRevisionLote(false)
    }
  }

  const pasarContableATrabajoEnLote = async () => {
    if (pasandoContableLote) return
    const ids = idsContableSeleccionables.filter(id =>
      selectedContableIds.has(id)
    )
    if (ids.length === 0) {
      toast.message('Seleccione al menos un caso en revision contable.')
      return
    }
    const confirmado = window.confirm(
      `¿Pasar ${ids.length} caso(s) al area de trabajo? Cierra conciliacion pendiente y mueve cada caso a En proceso.`
    )
    if (!confirmado) return

    setPasandoContableLote(true)
    let ok = 0
    let fail = 0
    const errores: string[] = []
    try {
      for (const id of ids) {
        try {
          const r = await finiquitoAdminPasarATrabajo(id)
          if (r.ok && r.caso) {
            incorporarCasoActualizado(r.caso)
            ok += 1
          } else {
            fail += 1
            errores.push(
              `Caso ${id}: ${r.error || 'no se pudo pasar al area de trabajo'}`
            )
          }
        } catch (e: unknown) {
          fail += 1
          errores.push(
            `Caso ${id}: ${e instanceof Error ? e.message : 'error de red'}`
          )
        }
      }
      setSelectedContableIds(new Set())
      void invalidatePrestamosQueries(queryClient)
      await cargarAreasVisibles({ silent: true })
      if (fail === 0) {
        toast.success(`${ok} caso(s) en area de trabajo.`)
      } else if (ok > 0) {
        toast.warning(
          `${ok} movidos, ${fail} con error. ${errores.slice(0, 2).join(' · ')}`
        )
      } else {
        toast.error(
          errores.slice(0, 3).join(' · ') ||
            'No se pudo pasar ningun caso al area de trabajo.'
        )
      }
    } finally {
      setPasandoContableLote(false)
    }
  }

  const abrirRevisionManualPrestamo = (
    prestamoId: number,
    finiquitoCasoId?: number
  ) => {
    navigate(`/revision-manual/editar/${prestamoId}`, {
      state: {
        returnTo: `${location.pathname}${location.search}`,
        finiquitoCasoId: finiquitoCasoId ?? undefined,
      },
    })
  }

  const pasarATrabajo = async (casoId: number) => {
    if (pendingEstadoCasoId != null) return
    setPendingEstadoCasoId(casoId)
    try {
      const r = await finiquitoAdminPasarATrabajo(casoId)
      if (!r.ok) {
        toast.error(r.error || 'No se pudo pasar a area de trabajo')
        return
      }
      if (r.caso) {
        incorporarCasoActualizado(r.caso)
      }
      toast.success('Caso en area de trabajo')
      void invalidatePrestamosQueries(queryClient)
      await cargarAreasVisibles({ silent: true })
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error')
    } finally {
      setPendingEstadoCasoId(null)
    }
  }

  const solicitarVistoRevisionManual = (row: FiniquitoCasoItem) => {
    if (pendingEstadoCasoId != null) return
    setPendingVistoRow(row)
  }

  const confirmarVistoRevisionManual = () => {
    if (pendingVistoRow == null) return
    const row = pendingVistoRow
    setPendingVistoRow(null)
    abrirRevisionManualPrestamo(row.prestamo_id, row.id)
  }

  const botonesFilaOperativos = (row: FiniquitoCasoItem) => (
    <>
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-8 w-8 border-slate-300"
        title="Revision manual del prestamo"
        aria-label={`Revision manual del prestamo ${row.prestamo_id}`}
        onClick={() =>
          abrirRevisionManualPrestamo(
            row.prestamo_id,
            row.estado === 'ACEPTADO' || row.estado === 'REVISION_CONTABLE'
              ? row.id
              : undefined
          )
        }
      >
        <Eye className="h-4 w-4" aria-hidden />
      </Button>
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-8 w-8 border-slate-300"
        title="Edicion y datos del caso"
        aria-label={`Edicion del caso ${row.id}`}
        onClick={() => setRevisionDialogCasoId(row.id)}
      >
        <Pencil className="h-4 w-4" aria-hidden />
      </Button>
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-8 w-8 border-slate-300"
        title="Escaneo: estado de cuenta PDF"
        aria-label={`Escaneo PDF del prestamo ${row.prestamo_id}`}
        disabled={descargandoEstadoCuentaPrestamoId === row.prestamo_id}
        onClick={() => descargarEstadoCuenta(row.prestamo_id)}
      >
        {descargandoEstadoCuentaPrestamoId === row.prestamo_id ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        ) : (
          <Download className="h-4 w-4" aria-hidden />
        )}
      </Button>
    </>
  )

  const botonProcesosNormales = (row: FiniquitoCasoItem) => (
    <Button
      type="button"
      size="sm"
      variant="outline"
      className="h-8 gap-1 border-sky-600 text-xs text-sky-950 hover:bg-sky-50"
      title="Quitar de finiquito y continuar en cartera (pagos, cuotas)"
      disabled={casoTieneAccionPendiente(row.id)}
      onClick={() => setPendingLiberarCaso(row)}
    >
      <RotateCcw className="h-3.5 w-3.5 shrink-0" aria-hidden />
      Procesos normales
    </Button>
  )

  const renderAcciones = (row: FiniquitoCasoItem) => (
    <div className="flex flex-wrap items-center justify-end gap-2">
      {botonesFilaOperativos(row)}
      <Button
        type="button"
        size="sm"
        className="h-8 bg-emerald-700 text-xs hover:bg-emerald-800"
        disabled={casoTieneAccionPendiente(row.id)}
        onClick={() => void cambiarEstado(row.id, 'ACEPTADO')}
      >
        Validar
      </Button>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-8 border-rose-300 text-xs text-rose-900"
        disabled={casoTieneAccionPendiente(row.id)}
        onClick={() => setPendingRechazoCasoId(row.id)}
      >
        Rechazar
      </Button>
      {botonProcesosNormales(row)}
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-8 w-8 border-slate-300 text-rose-800"
        title="Eliminar caso de la bandeja"
        aria-label={`Eliminar caso ${row.id}`}
        disabled={casoTieneAccionPendiente(row.id)}
        onClick={() => setPendingEliminarCasoId(row.id)}
      >
        <Trash2 className="h-4 w-4" aria-hidden />
      </Button>
    </div>
  )

  const renderAccionesAreaRevision = (row: FiniquitoCasoItem) => {
    return (
      <div className="flex flex-wrap items-center justify-end gap-2">
        {botonesFilaOperativos(row)}
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 gap-1 border-emerald-600 text-xs text-emerald-900 hover:bg-emerald-50"
          title="Cierra conciliacion pendiente y pasa el caso al area de trabajo (sin revision contable)"
          aria-label={`Pasar caso ${row.id} al area de trabajo`}
          disabled={casoTieneAccionPendiente(row.id)}
          onClick={() => void pasarATrabajo(row.id)}
        >
          <X className="h-3.5 w-3.5 shrink-0" aria-hidden />
          Area trabajo
        </Button>
        <Button
          type="button"
          size="sm"
          className="h-8 gap-1 bg-emerald-700 text-xs hover:bg-emerald-800"
          disabled={casoTieneAccionPendiente(row.id)}
          title="Abrir revisión manual y usar Conciliar (mismo flujo que revisión manual estándar)"
          onClick={() => solicitarVistoRevisionManual(row)}
        >
          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
          Visto
        </Button>
        {botonProcesosNormales(row)}
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 gap-1 border-indigo-600 text-xs text-indigo-900 hover:bg-indigo-50"
          title="Pasa el caso a revision contable"
          aria-label={`Pasar caso ${row.id} a revision contable`}
          disabled={casoTieneAccionPendiente(row.id)}
          onClick={() => void cambiarEstado(row.id, 'REVISION_CONTABLE')}
        >
          Revision contable
        </Button>
      </div>
    )
  }

  const renderAccionesRevisionContable = (row: FiniquitoCasoItem) => (
    <div className="flex flex-wrap items-center justify-end gap-2">
      {botonesFilaOperativos(row)}
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-8 gap-1 border-emerald-600 text-xs text-emerald-900 hover:bg-emerald-50"
        title="Cierra conciliacion pendiente y pasa el caso al area de trabajo"
        aria-label={`Pasar caso ${row.id} al area de trabajo`}
        disabled={casoTieneAccionPendiente(row.id)}
        onClick={() => void pasarATrabajo(row.id)}
      >
        <X className="h-3.5 w-3.5 shrink-0" aria-hidden />
        Area trabajo
      </Button>
      {botonProcesosNormales(row)}
    </div>
  )

  const renderAccionesAreaTrabajo = (row: FiniquitoCasoItem) => (
    <div className="flex flex-wrap items-center justify-end gap-2">
      {botonesFilaOperativos(row)}
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-8 border-slate-300 text-xs"
        disabled={casoTieneAccionPendiente(row.id)}
        onClick={() => void cambiarEstado(row.id, 'ACEPTADO')}
      >
        Volver a validacion
      </Button>
      <Button
        type="button"
        size="sm"
        className="h-8 bg-emerald-700 text-xs hover:bg-emerald-800"
        disabled={casoTieneAccionPendiente(row.id)}
        onClick={() => setDialogTerminado({ casoId: row.id })}
      >
        Terminado
      </Button>
    </div>
  )

  const renderTabla = (
    items: FiniquitoCasoItem[],
    renderAccionesFila: (row: FiniquitoCasoItem) => ReactNode = renderAcciones,
    modoTiempo: ModoTiempoTabla = 'bandeja',
    seleccionFilas?: SeleccionFilasTabla
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
            {seleccionFilas ? (
              <TableHead className={cn(thGestion, 'w-10 text-center')} scope="col">
                <input
                  type="checkbox"
                  aria-label={seleccionFilas.ariaSeleccionarTodos}
                  className="h-4 w-4 rounded border-slate-300"
                  checked={seleccionFilas.todosSeleccionados}
                  ref={el => {
                    if (el) {
                      el.indeterminate = seleccionFilas.algunSeleccionado
                    }
                  }}
                  disabled={seleccionFilas.disabled}
                  onChange={e => seleccionFilas.onToggleAll(e.target.checked)}
                />
              </TableHead>
            ) : null}
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
              title={
                modoTiempo !== 'bandeja'
                  ? 'Ordenado de fecha más antigua a la más reciente'
                  : undefined
              }
            >
              Último pago
              {modoTiempo !== 'bandeja' ? (
                <span className="mt-0.5 block text-[9px] font-normal normal-case text-slate-300">
                  ↑ antiguo · reciente ↓
                </span>
              ) : null}
            </TableHead>
            <TableHead
              className={cn(
                thGestion,
                'max-w-[9rem] whitespace-normal leading-tight'
              )}
              scope="col"
              title={
                modoTiempo === 'bandeja'
                  ? `${FASE_TIEMPO_BANDEJA}: dias restantes de ${BANDEJA_DIA_ATRASADO} en bandeja (atrasado desde dia ${BANDEJA_DIA_ATRASADO} del ciclo)`
                  : modoTiempo === 'contable'
                    ? `${FASE_TIEMPO_CONTABLE}: dias restantes de ${AREA_REVISION_CONTABLE_DIAS_MAX} en revision contable`
                    : `${FASE_TIEMPO_REVISION}: dias restantes de ${AREA_REVISION_DIAS_MAX} en area de revision`
              }
            >
              Tiempo limite
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
          {items.map((row, idx) => {
            const { atrasado, diasRest, texto: textoTiempo } =
              tiempoLimiteTabla(row, modoTiempo)
            const puedeSeleccionar =
              seleccionFilas &&
              (row.estado || '').toUpperCase() ===
                seleccionFilas.estadoRequerido
            return (
            <TableRow key={row.id} className={idx % 2 === 0 ? trEven : trOdd}>
              {seleccionFilas ? (
                <TableCell className={cn(tdGestion, 'text-center')}>
                  <input
                    type="checkbox"
                    aria-label={`Seleccionar caso ${row.id}`}
                    className="h-4 w-4 rounded border-slate-300"
                    checked={seleccionFilas.selectedIds.has(row.id)}
                    disabled={seleccionFilas.disabled || !puedeSeleccionar}
                    onChange={e =>
                      seleccionFilas.onToggleRow(row.id, e.target.checked)
                    }
                  />
                </TableCell>
              ) : null}
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
                    : 'Sin pagos con prestamo vinculado'
                }
              >
                {textoUltimoPago(row.ultima_fecha_pago)}
              </TableCell>
              <TableCell className={cn(tdGestion, 'whitespace-nowrap')}>
                <span
                  className={cn(
                    'rounded px-1.5 py-0.5 text-xs font-medium',
                    claseTiempoLimite(diasRest, atrasado)
                  )}
                >
                  {textoTiempo}
                </span>
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
          )})}
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
              title={`${FASE_TIEMPO_TRABAJO}: dias restantes de la fase hasta el dia ${PLAZO_CICLO_DIAS} del ciclo`}
            >
              Tiempo limite
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
                  row.fecha_entrada_en_proceso
                    ? `Desde EN_PROCESO: ${row.fecha_entrada_en_proceso}`
                    : row.finiquito_tramite_fecha_limite
                      ? `Limite: ${row.finiquito_tramite_fecha_limite}`
                      : 'Sin fecha de inicio en area de trabajo'
                }
              >
                <span
                  className={cn(
                    'rounded px-1.5 py-0.5 text-xs font-medium',
                    claseTiempoLimite(
                      diasRestantesAreaTrabajo(row),
                      (diasRestantesAreaTrabajo(row) ?? 1) <= 0
                    )
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

  const kpiCargando = loadingResumen && resumenEstado == null
  const displayTotalBandeja = cedulaBusqueda
    ? totalBandeja
    : (resumenEstado?.revision ?? totalBandeja)
  const displayTotalRevision = cedulaRevisionBusqueda
    ? totalAreaRevision
    : (resumenEstado?.aceptado ?? totalAreaRevision)
  const displayTotalContable = cedulaContableBusqueda
    ? totalAreaRevisionContable
    : (resumenEstado?.revision_contable ?? totalAreaRevisionContable)
  const displayTotalTrabajo = cedulaTrabajoBusqueda
    ? totalAreaTrabajo
    : (resumenEstado?.en_proceso ?? totalAreaTrabajo)
  const algunaAreaCargando = Object.values(areasLoading).some(Boolean)

  const renderContenidoAreaPendiente = (
    area: FiniquitoAreaId,
    etiqueta: string,
    cargar: () => void
  ) => (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-slate-200 bg-slate-50/60 px-4 py-12 text-center">
      <p className="max-w-md text-sm text-slate-600">
        <strong>{etiqueta}</strong> se carga al llegar a esta sección para
        agilizar la apertura de la página.
      </p>
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="border-slate-300"
        disabled={areasLoading[area]}
        onClick={() => void cargar()}
      >
        {areasLoading[area] ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
            Cargando…
          </>
        ) : (
          'Cargar ahora'
        )}
      </Button>
    </div>
  )

  return (
    <FiniquitoWorkspaceShell
      description={`Ciclo ${PLAZO_CICLO_DIAS} dias: bandeja (dias 1-2, atrasado desde dia ${BANDEJA_DIA_ATRASADO}) → area revision (hasta ${AREA_REVISION_DIAS_MAX}d) → area de trabajo (hasta dia ${PLAZO_CICLO_DIAS}).`}
      actions={
        <Button
          size="sm"
          variant="outline"
          disabled={refreshing || algunaAreaCargando}
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
      toolbar={
        <div aria-label="Indicadores finiquito">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <Card className="border-slate-200 shadow-sm">
            <CardContent className="flex min-h-[5.5rem] flex-col justify-start gap-1 p-4">
              <p className="text-[11px] font-semibold uppercase leading-tight tracking-wide text-slate-500">
                Bandeja (Revision)
              </p>
              <p className="text-2xl font-bold leading-none tabular-nums text-[#1e3a5f]">
                {kpiCargando ? '-' : displayTotalBandeja}
              </p>
              <p className="text-xs leading-snug text-slate-500">
                Dias 1-2 · atrasado desde dia {BANDEJA_DIA_ATRASADO}
                {cedulaBusqueda ? ' (filtro cedula)' : ''}
              </p>
            </CardContent>
          </Card>
          <Card
            className={cn(
              'border-slate-200 shadow-sm',
              !kpiCargando &&
                (kpiNuevosRevision?.total ?? 0) > 0 &&
                'border-amber-300/90 bg-amber-50/40 ring-1 ring-amber-200/80'
            )}
          >
            <CardContent className="flex min-h-[5.5rem] flex-col justify-start gap-1 p-4">
              <div className="flex items-center gap-1.5">
                <Bell
                  className={cn(
                    'h-3.5 w-3.5 shrink-0',
                    !kpiCargando && (kpiNuevosRevision?.total ?? 0) > 0
                      ? 'text-amber-700'
                      : 'text-slate-400'
                  )}
                  aria-hidden
                />
                <p className="text-[11px] font-semibold uppercase leading-tight tracking-wide text-slate-500">
                  Nuevos en bandeja
                </p>
              </div>
              <p
                className={cn(
                  'text-2xl font-bold leading-none tabular-nums',
                  !kpiCargando && (kpiNuevosRevision?.total ?? 0) > 0
                    ? 'text-amber-950'
                    : 'text-slate-800'
                )}
              >
                {areasLoading.bandeja && kpiNuevosRevision == null
                  ? '-'
                  : (kpiNuevosRevision?.total ?? 0)}
              </p>
              <p className="text-xs leading-snug text-slate-500">
                Creados hace ≤{' '}
                {kpiNuevosRevision?.ventana_horas ??
                  FINIQUITO_HORAS_NUEVOS_REVISION_DEFAULT}{' '}
                h (UTC)
              </p>
            </CardContent>
          </Card>
          <Card className="border-slate-200 shadow-sm">
            <CardContent className="flex min-h-[5.5rem] flex-col justify-start gap-1 p-4">
              <p className="text-[11px] font-semibold uppercase leading-tight tracking-wide text-slate-500">
                Area de revision
              </p>
              <p className="text-2xl font-bold leading-none tabular-nums text-amber-900">
                {kpiCargando ? '-' : displayTotalRevision}
              </p>
              <p className="text-xs leading-snug text-slate-500">
                Hasta {AREA_REVISION_DIAS_MAX}d · atrasado dia 6 de fase
                {cedulaRevisionBusqueda ? ' (filtro cedula)' : ''}
              </p>
            </CardContent>
          </Card>
          <Card className="border-indigo-200/80 shadow-sm ring-1 ring-indigo-100/60">
            <CardContent className="flex min-h-[5.5rem] flex-col justify-start gap-1 p-4">
              <p className="text-[11px] font-semibold uppercase leading-tight tracking-wide text-slate-500">
                Revision contable
              </p>
              <p className="text-2xl font-bold leading-none tabular-nums text-indigo-900">
                {kpiCargando ? '-' : displayTotalContable}
              </p>
              <p className="text-xs leading-snug text-slate-500">
                Hasta {AREA_REVISION_CONTABLE_DIAS_MAX}d · atrasado dia 6 de fase
                {cedulaContableBusqueda ? ' (filtro cedula)' : ''}
              </p>
            </CardContent>
          </Card>
          <Card className="border-slate-200 shadow-sm">
            <CardContent className="flex min-h-[5.5rem] flex-col justify-start gap-1 p-4">
              <p className="text-[11px] font-semibold uppercase leading-tight tracking-wide text-slate-500">
                Area de trabajo
              </p>
              <p className="text-2xl font-bold leading-none tabular-nums text-emerald-900">
                {kpiCargando ? '-' : displayTotalTrabajo}
              </p>
              <p className="text-xs leading-snug text-slate-500">
                Hasta dia {PLAZO_CICLO_DIAS} del ciclo
                {cedulaTrabajoBusqueda ? ' (filtro cedula)' : ''}
              </p>
            </CardContent>
          </Card>
        </div>
        </div>
      }
    >
      <div className="space-y-5 md:space-y-6">
      <section
        className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-md"
        aria-labelledby="finiquito-bandeja-titulo"
      >
        <div className="border-b border-slate-200 bg-slate-50/90 px-4 py-3 sm:px-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:flex-wrap lg:items-center lg:justify-between">
            <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
              <h2
                id="finiquito-bandeja-titulo"
                className="shrink-0 text-base font-bold text-[#1e3a5f]"
              >
                Bandeja principal
              </h2>
              <FiniquitoCedulaFiltroInline
                id="finiquito-filtro-cedula-bandeja"
                value={cedulaInput}
                onChange={setCedulaInput}
                onClear={limpiarCedula}
                placeholder="Ej. V12345678 o parte del número"
                ariaClear="Limpiar filtro de cédula"
              />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {canTrasladarFiniquitoBandejas ? (
                <Button
                  type="button"
                  size="sm"
                  className="h-9 shrink-0 bg-emerald-700 hover:bg-emerald-800"
                  disabled={
                    areasLoading.bandeja ||
                    validandoBandejaLote ||
                    selectedBandejaIds.size === 0
                  }
                  onClick={() => void validarBandejaEnLote()}
                >
                  {validandoBandejaLote ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    `Validar seleccionados (${selectedBandejaIds.size})`
                  )}
                </Button>
              ) : null}
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-9 shrink-0 border-slate-300"
                disabled={areasLoading.bandeja || validandoBandejaLote}
                onClick={() => void cargarBandeja()}
              >
                {areasLoading.bandeja ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Recargar'
                )}
              </Button>
            </div>
          </div>
        </div>
        <div>
          <div className="p-3 sm:p-4">
            {areasLoading.bandeja && itemsBandejaVisibles.length === 0 ? (
              <div className="flex justify-center py-14">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
              </div>
            ) : itemsBandejaVisibles.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50 px-4 py-10 text-center text-sm leading-relaxed text-slate-600">
                {cedulaBusqueda ? (
                  <>
                    <p>
                      Ningún caso en <strong>Revisión</strong> (bandeja principal)
                      coincide con esa cédula.
                    </p>
                    <p className="mt-2 text-xs text-slate-500">
                      La bandeja solo muestra créditos recién ingresados a finiquito.
                      Si en Préstamos figura <strong>Liquidado / Terminado</strong>,
                      el caso ya cerró el flujo y está en{' '}
                      <strong>Casos terminados</strong> (más abajo), no aquí.
                    </p>
                    {cargandoResumenBandejaPorCedula ? (
                      <p className="mt-3 flex items-center justify-center gap-2 text-xs text-slate-500">
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                        Buscando en otras áreas…
                      </p>
                    ) : resumenBandejaPorCedula ? (
                      <>
                        {textoUbicacionOtrasAreasFiniquito(
                          resumenBandejaPorCedula
                        ) ? (
                          <p className="mt-3 text-xs font-medium text-[#1e3a5f]">
                            Para{' '}
                            <span className="font-mono">{cedulaBusqueda}</span>:{' '}
                            {textoUbicacionOtrasAreasFiniquito(
                              resumenBandejaPorCedula
                            )}
                            .
                          </p>
                        ) : (
                          <p className="mt-3 text-xs text-amber-900">
                            No hay casos finiquito materializados para esta cédula.
                            Use «Refrescar materializado» si el préstamo está
                            LIQUIDADO y las cuotas cuadran con el financiamiento.
                          </p>
                        )}
                        {resumenBandejaPorCedula.terminado > 0 ? (
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="mt-4 border-slate-300"
                            onClick={() => buscarCedulaEnTerminados(cedulaBusqueda)}
                          >
                            Ver en Casos terminados
                          </Button>
                        ) : null}
                      </>
                    ) : null}
                  </>
                ) : (
                  'No hay casos en Revision. Use «Refrescar materializado» para traer prestamos LIQUIDADO elegibles.'
                )}
              </div>
            ) : (
              <>
                {renderTabla(
                  itemsBandejaVisibles,
                  renderAcciones,
                  'bandeja',
                  canTrasladarFiniquitoBandejas
                    ? {
                        selectedIds: selectedBandejaIds,
                        onToggleRow: (id, checked) => {
                          setSelectedBandejaIds(prev => {
                            const next = new Set(prev)
                            if (checked) next.add(id)
                            else next.delete(id)
                            return next
                          })
                        },
                        onToggleAll: checked => {
                          setSelectedBandejaIds(() => {
                            if (!checked) return new Set()
                            return new Set(idsBandejaSeleccionables)
                          })
                        },
                        disabled:
                          validandoBandejaLote || pendingEstadoCasoId != null,
                        todosSeleccionados: todosBandejaSeleccionados,
                        algunSeleccionado: algunBandejaSeleccionado,
                        estadoRequerido: 'REVISION',
                        ariaSeleccionarTodos:
                          'Seleccionar todos los casos visibles en bandeja',
                      }
                    : undefined
                )}
                <FiniquitoTablaScrollHint
                  total={totalBandeja}
                  cargados={itemsBandejaVisibles.length}
                  limit={BANDEJA_PRINCIPAL_FETCH_LIMIT}
                />
              </>
            )}
          </div>
        </div>
      </section>
      <section
        ref={revisionSectionRef}
        className={cn(
          'overflow-hidden rounded-2xl border-2 border-dashed border-amber-400/85',
          'bg-amber-50/40 shadow-inner'
        )}
        aria-labelledby="finiquito-area-revision-titulo"
      >
        <div className="border-b border-amber-200/90 bg-amber-100/95 px-4 py-3 sm:px-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:flex-wrap lg:items-center lg:justify-between">
            <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-center sm:gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-amber-300/90 bg-amber-50 shadow-sm">
                <CheckCircle2 className="h-4 w-4 text-amber-800" aria-hidden />
              </span>
              <h2
                id="finiquito-area-revision-titulo"
                className="shrink-0 text-sm font-bold tracking-tight text-amber-950 sm:text-base"
              >
                Area de revision
              </h2>
              <FiniquitoCedulaFiltroInline
                id="finiquito-filtro-cedula-revision"
                value={cedulaRevisionInput}
                onChange={setCedulaRevisionInput}
                onClear={limpiarCedulaRevision}
                placeholder="Ej. V17037221 o parte del número"
                labelClassName="text-amber-950"
                inputClassName="border-amber-200 bg-white"
                searchIconClassName="text-amber-700/70"
                clearButtonClassName="text-amber-800 hover:bg-amber-100"
                ariaClear="Limpiar filtro de cédula en área de revisión"
              />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {canTrasladarFiniquitoBandejas ? (
                <Button
                  type="button"
                  size="sm"
                  className="h-9 shrink-0 border-indigo-700 bg-indigo-700 hover:bg-indigo-800"
                  disabled={
                    areasLoading.revision ||
                    pasandoRevisionLote ||
                    selectedRevisionIds.size === 0
                  }
                  onClick={() => void pasarRevisionContableEnLote()}
                >
                  {pasandoRevisionLote ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    `Revision contable seleccionados (${selectedRevisionIds.size})`
                  )}
                </Button>
              ) : null}
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-9 shrink-0 border-amber-300 bg-white"
                disabled={
                  areasLoading.revision ||
                  pasandoRevisionLote ||
                  validandoBandejaLote
                }
                onClick={() => void cargarAreaRevision()}
              >
                {areasLoading.revision ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Recargar'
                )}
              </Button>
            </div>
          </div>
        </div>
        <div>
          <div className="p-3 sm:p-4">
            {!areasCargadas.revision ? (
              renderContenidoAreaPendiente(
                'revision',
                'Área de revisión',
                () => void cargarAreaRevision()
              )
            ) : areasLoading.revision && itemsAreaRevisionVisibles.length === 0 ? (
              <div className="flex justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-amber-600/70" />
              </div>
            ) : itemsAreaRevisionVisibles.length === 0 ? (
              <p className="rounded-lg border border-dashed border-amber-200/90 bg-white/50 px-4 py-10 text-center text-sm text-amber-950/85">
                {cedulaRevisionBusqueda
                  ? 'Ningún caso en el área de revisión coincide con esa cédula.'
                  : 'No hay casos validados pendientes. Al pulsar Validar en la bandeja principal aparecen aqui.'}
              </p>
            ) : (
              <>
                {renderTabla(
                  itemsAreaRevisionVisibles,
                  renderAccionesAreaRevision,
                  'revision',
                  canTrasladarFiniquitoBandejas
                    ? {
                        selectedIds: selectedRevisionIds,
                        onToggleRow: (id, checked) => {
                          setSelectedRevisionIds(prev => {
                            const next = new Set(prev)
                            if (checked) next.add(id)
                            else next.delete(id)
                            return next
                          })
                        },
                        onToggleAll: checked => {
                          setSelectedRevisionIds(() => {
                            if (!checked) return new Set()
                            return new Set(idsRevisionSeleccionables)
                          })
                        },
                        disabled:
                          pasandoRevisionLote || pendingEstadoCasoId != null,
                        todosSeleccionados: todosRevisionSeleccionados,
                        algunSeleccionado: algunRevisionSeleccionado,
                        estadoRequerido: 'ACEPTADO',
                        ariaSeleccionarTodos:
                          'Seleccionar todos los casos visibles en área de revisión',
                      }
                    : undefined
                )}
                <FiniquitoTablaScrollHint
                  total={totalAreaRevision}
                  cargados={itemsAreaRevisionVisibles.length}
                />
              </>
            )}
          </div>
        </div>
      </section>
      <section
        ref={contableSectionRef}
        className={cn(
          'overflow-hidden rounded-2xl border border-indigo-200/90 bg-white shadow-md',
          'ring-1 ring-indigo-100/80'
        )}
        aria-labelledby="finiquito-revision-contable-titulo"
      >
        <div className="border-b border-indigo-200/90 bg-indigo-100/95 px-4 py-3 sm:px-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:flex-wrap lg:items-center lg:justify-between">
            <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-center sm:gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-indigo-300/90 bg-indigo-50 shadow-sm">
                <CheckCircle2 className="h-4 w-4 text-indigo-800" aria-hidden />
              </span>
              <h2
                id="finiquito-revision-contable-titulo"
                className="shrink-0 text-sm font-bold tracking-tight text-indigo-950 sm:text-base"
              >
                Revision contable
              </h2>
              <FiniquitoCedulaFiltroInline
                id="finiquito-filtro-cedula-contable"
                value={cedulaContableInput}
                onChange={setCedulaContableInput}
                onClear={limpiarCedulaContable}
                placeholder="Ej. V17037221 o parte del numero"
                labelClassName="text-indigo-950"
                inputClassName="border-indigo-200 bg-white"
                searchIconClassName="text-indigo-700/70"
                clearButtonClassName="text-indigo-800 hover:bg-indigo-100"
                ariaClear="Limpiar filtro de cedula en revision contable"
              />
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                size="sm"
                className="h-9 shrink-0 border-emerald-700 bg-emerald-700 hover:bg-emerald-800"
                disabled={
                  areasLoading.contable ||
                  pasandoContableLote ||
                  selectedContableIds.size === 0
                }
                onClick={() => void pasarContableATrabajoEnLote()}
              >
                {pasandoContableLote ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  `Area trabajo seleccionados (${selectedContableIds.size})`
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-9 shrink-0 border-indigo-300 bg-white"
                disabled={
                  areasLoading.contable ||
                  pasandoContableLote ||
                  pasandoRevisionLote
                }
                onClick={() => void cargarAreaRevisionContable()}
              >
                {areasLoading.contable ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Recargar'
                )}
              </Button>
            </div>
          </div>
        </div>
        <div>
          <div className="p-3 sm:p-4">
            {!areasCargadas.contable ? (
              renderContenidoAreaPendiente(
                'contable',
                'Revision contable',
                () => void cargarAreaRevisionContable()
              )
            ) : areasLoading.contable &&
              itemsAreaRevisionContableVisibles.length === 0 ? (
              <div className="flex justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600/70" />
              </div>
            ) : itemsAreaRevisionContableVisibles.length === 0 ? (
              <p className="rounded-lg border border-dashed border-indigo-200/90 bg-white/50 px-4 py-10 text-center text-sm text-indigo-950/85">
                {cedulaContableBusqueda
                  ? 'Ningun caso en revision contable coincide con esa cedula.'
                  : 'No hay casos en revision contable. Trasladelos desde el area de revision con «Revision contable».'}
              </p>
            ) : (
              <>
                {renderTabla(
                  itemsAreaRevisionContableVisibles,
                  renderAccionesRevisionContable,
                  'contable',
                  {
                    selectedIds: selectedContableIds,
                    onToggleRow: (id, checked) => {
                      setSelectedContableIds(prev => {
                        const next = new Set(prev)
                        if (checked) next.add(id)
                        else next.delete(id)
                        return next
                      })
                    },
                    onToggleAll: checked => {
                      setSelectedContableIds(() => {
                        if (!checked) return new Set()
                        return new Set(idsContableSeleccionables)
                      })
                    },
                    disabled:
                      pasandoContableLote || pendingEstadoCasoId != null,
                    todosSeleccionados: todosContableSeleccionados,
                    algunSeleccionado: algunContableSeleccionado,
                    estadoRequerido: 'REVISION_CONTABLE',
                    ariaSeleccionarTodos:
                      'Seleccionar todos los casos visibles en revision contable',
                  }
                )}
                <FiniquitoTablaScrollHint
                  total={totalAreaRevisionContable}
                  cargados={itemsAreaRevisionContableVisibles.length}
                />
              </>
            )}
          </div>
        </div>
      </section>
      <section
        ref={trabajoSectionRef}
        className={cn(
          'overflow-hidden rounded-2xl border border-emerald-200/90 bg-white shadow-md',
          'ring-1 ring-emerald-100/80'
        )}
        aria-labelledby="finiquito-area-trabajo-titulo"
      >
        <div className="border-b border-emerald-200/80 bg-gradient-to-r from-emerald-800 to-emerald-600 px-4 py-3 text-white sm:px-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:flex-wrap lg:items-center lg:justify-between">
            <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-center sm:gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white/15 shadow-inner">
                <CheckCircle2 className="h-4 w-4" aria-hidden />
              </span>
              <h2
                id="finiquito-area-trabajo-titulo"
                className="shrink-0 text-sm font-bold tracking-tight sm:text-base"
              >
                Área de trabajo
              </h2>
              <FiniquitoCedulaFiltroInline
                id="finiquito-filtro-cedula-trabajo"
                value={cedulaTrabajoInput}
                onChange={setCedulaTrabajoInput}
                onClear={limpiarCedulaTrabajo}
                placeholder="Ej. V12345678 o parte del número"
                labelClassName="text-emerald-50"
                inputClassName="border-emerald-200/80 bg-white text-slate-900"
                searchIconClassName="text-slate-400"
                clearButtonClassName="text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                ariaClear="Limpiar filtro de cédula en área de trabajo"
              />
            </div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="h-9 shrink-0 border-white/30 bg-white/15 text-white hover:bg-white/25"
              disabled={areasLoading.trabajo}
              onClick={() => void cargarAreaTrabajo()}
            >
              {areasLoading.trabajo ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Recargar'
              )}
            </Button>
          </div>
        </div>
        <div className="bg-gradient-to-b from-emerald-50/50 to-white">
          <div className="p-3 sm:p-4">
            {!areasCargadas.trabajo ? (
              renderContenidoAreaPendiente(
                'trabajo',
                'Área de trabajo',
                () => void cargarAreaTrabajo()
              )
            ) : areasLoading.trabajo && itemsAreaTrabajoVisibles.length === 0 ? (
              <div className="flex justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-emerald-600/70" />
              </div>
            ) : itemsAreaTrabajoVisibles.length === 0 ? (
              <p className="rounded-lg border border-dashed border-emerald-200/80 bg-white/60 px-4 py-10 text-center text-sm text-slate-600">
                {cedulaTrabajoBusqueda ? (
                  <>
                    Ningún caso en el área de trabajo coincide con esa cédula.
                    Pruebe otra subcadena o limpie el filtro.
                  </>
                ) : (
                  <>
                    No hay casos en area de trabajo. Paselos desde revision
                    contable con «Area trabajo».
                  </>
                )}
              </p>
            ) : (
              <>
                {renderTablaAreaTrabajo(itemsAreaTrabajoVisibles)}
                <FiniquitoTablaScrollHint
                  total={totalAreaTrabajo}
                  cargados={itemsAreaTrabajoVisibles.length}
                />
              </>
            )}
          </div>
        </div>
      </section>
      <section
        ref={terminadosSectionRef}
        className={cn(
          'overflow-hidden rounded-2xl border border-violet-200/90 bg-white shadow-md',
          'ring-1 ring-violet-100/80'
        )}
        aria-labelledby="finiquito-terminados-titulo"
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-violet-200/80 bg-gradient-to-r from-violet-900 to-violet-600 px-4 py-3 text-white sm:px-5">
          <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-center sm:gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-white/15 shadow-inner">
              <CheckCircle2 className="h-4 w-4" aria-hidden />
            </span>
            <h2
              id="finiquito-terminados-titulo"
              className="shrink-0 text-sm font-bold tracking-tight sm:text-base"
            >
              Casos terminados
            </h2>
            <FiniquitoCedulaFiltroInline
              id="finiquito-filtro-cedula-terminados"
              value={cedulaTerminadosInput}
              onChange={setCedulaTerminadosInput}
              onClear={limpiarCedulaTerminados}
              placeholder="Ej. V12345678"
              labelClassName="text-violet-50"
              inputClassName="border-violet-200/80 bg-white text-slate-900"
              searchIconClassName="text-slate-400"
              clearButtonClassName="text-slate-500 hover:bg-slate-100 hover:text-slate-800"
              ariaClear="Limpiar filtro de cédula en terminados"
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {areasCargadas.terminados ? (
              <Button
                type="button"
                size="sm"
                variant="secondary"
                className="h-9 shrink-0 border-white/30 bg-white/15 text-white hover:bg-white/25"
                disabled={areasLoading.terminados}
                onClick={() =>
                  void cargarTerminados({ force: true, silent: false })
                }
              >
                {areasLoading.terminados ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Recargar'
                )}
              </Button>
            ) : null}
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
        </div>
        <div className="border-b border-violet-200/70 bg-violet-50/40 px-4 py-3 sm:px-5">
          {!areasCargadas.terminados ? (
            <p className="mt-4 rounded-lg border border-dashed border-violet-200/90 bg-white/60 px-4 py-6 text-center text-sm text-slate-600">
              Baje hasta el listado o pulse «Cargar ahora» para traer el gráfico
              diario y los terminados.
            </p>
          ) : areasLoading.terminados && resumenDias.length === 0 ? (
            <p className="mt-4 rounded-lg border border-dashed border-violet-200/90 bg-white/60 px-4 py-6 text-center text-sm text-slate-600">
              Cargando resumen…
            </p>
          ) : (
            <>
              <div className="mb-2 flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
                <div className="flex flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-slate-600">
                    <span
                      className="inline-flex items-center gap-1.5"
                      title="Casos que pasaron al area de trabajo (EN_PROCESO) ese dia, calendario Caracas"
                    >
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-sm"
                        style={{ backgroundColor: GRAFICO_DIA_COLOR_INGRESAN }}
                        aria-hidden
                      />
                      Ingresan · area trabajo
                    </span>
                    <span
                      className="inline-flex items-center gap-1.5"
                      title="Casos marcados Terminado ese dia, calendario Caracas"
                    >
                      <span
                        className="inline-block h-2.5 w-2.5 rounded-sm bg-violet-600"
                        aria-hidden
                      />
                      Terminan
                    </span>
                  </div>
                  <p className="text-[10px] leading-snug text-slate-500">
                    Flujo diario: entradas a area de trabajo vs cierres Terminado
                    (fecha Caracas).
                  </p>
                </div>
                {terminadosFetchedAt != null ? (
                  <p className="text-[10px] text-slate-500">
                    {minutosDesdeCache(terminadosFetchedAt) === 0
                      ? 'Actualizado hace un momento'
                      : `Actualizado hace ${minutosDesdeCache(terminadosFetchedAt)} min`}{' '}
                    · auto cada 1 min
                  </p>
                ) : null}
              </div>
              <div
                ref={terminadosGraficoScrollRef}
                className="mt-1 flex items-end gap-1 overflow-x-auto pb-2 pt-1 scroll-smooth"
                role="img"
                aria-label="Grafico diario: entradas al area de trabajo y cierres Terminado (vista inicial: Hoy)"
              >
                <BarChart3
                  className="mb-6 h-5 w-5 shrink-0 text-violet-700"
                  aria-hidden
                />
                {resumenDias.map(d => {
                  const esHoy = d.etiqueta === 'Hoy'
                  const esAyer = d.etiqueta === 'Ayer'
                  const ingresos = d.cantidad_ingresos ?? 0
                  const terminados = d.cantidad
                  return (
                    <div
                      key={d.fecha}
                      className={cn(
                        'flex min-w-[2.75rem] flex-col items-center gap-1 rounded-t-md px-0.5',
                        esHoy && 'bg-violet-100/80 ring-1 ring-violet-400/70'
                      )}
                      title={`${d.etiqueta} (${d.fecha}): ${ingresos} entrada(s) a area de trabajo, ${terminados} terminado(s)`}
                    >
                      <div className="flex items-end justify-center gap-0.5">
                        {renderColumnaBarraGraficoDiario(ingresos, {
                          barClass: '',
                          barEmptyClass: '',
                          labelClass: '',
                          barStyle: { backgroundColor: GRAFICO_DIA_COLOR_INGRESAN },
                          barEmptyStyle: {
                            backgroundColor: GRAFICO_DIA_COLOR_INGRESAN_VACIO,
                          },
                          labelStyle: { color: GRAFICO_DIA_COLOR_INGRESAN_ETIQUETA },
                        })}
                        {renderColumnaBarraGraficoDiario(terminados, {
                          barClass: esHoy ? 'bg-violet-700' : 'bg-violet-500/90',
                          barEmptyClass: esHoy
                            ? 'bg-violet-300/80'
                            : 'bg-violet-200/60',
                          labelClass: esHoy
                            ? 'text-violet-950'
                            : 'text-violet-900',
                        })}
                      </div>
                      <span
                        className={cn(
                          'max-w-[2.75rem] text-center text-[8px] leading-tight text-slate-600',
                          esHoy && 'font-bold text-violet-900',
                          esAyer && 'font-semibold text-violet-800'
                        )}
                      >
                        {d.etiqueta}
                      </span>
                    </div>
                  )
                })}
              </div>
            </>
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
          {!areasCargadas.terminados ? (
            renderContenidoAreaPendiente(
              'terminados',
              'Casos terminados',
              () => void cargarTerminados()
            )
          ) : areasLoading.terminados && itemsTerminados.length === 0 ? (
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
      </div>
      <Dialog
        open={dialogTerminado != null}
        onOpenChange={open => {
          if (!open) setDialogTerminado(null)
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Marcar como terminado</DialogTitle>
            <DialogDescription className="text-base text-slate-800">
              ¿Usted ha contactado al cliente para pasos siguientes?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setDialogTerminado(null)}
            >
              Cancelar
            </Button>
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
              Si
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={pendingVistoRow != null}
        onOpenChange={open => {
          if (!open) setPendingVistoRow(null)
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Abrir revisión para conciliar</DialogTitle>
            <DialogDescription className="space-y-2 text-base text-slate-800">
              <span className="block">
                Préstamo <strong>{pendingVistoRow?.prestamo_id ?? '—'}</strong>:
                se abrirá revisión manual. La conciliación se hace solo con el
                botón <strong>Conciliar</strong> (ABONOS, comprobantes, OCR y
                cascada), igual que en cualquier revisión manual.
              </span>
              <span className="block text-sm text-slate-600">
                No hay pasos intermedios de reserva Visto ni «Recrear OCR» por
                separado.
              </span>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setPendingVistoRow(null)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              className="bg-emerald-700 hover:bg-emerald-800"
              disabled={pendingEstadoCasoId != null}
              onClick={confirmarVistoRevisionManual}
            >
              Abrir revisión manual
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={pendingLiberarCaso != null}
        onOpenChange={open => {
          if (!open) setPendingLiberarCaso(null)
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Volver a procesos normales</DialogTitle>
            <DialogDescription className="space-y-2 text-base text-slate-800">
              <span className="block">
                Préstamo{' '}
                <strong>#{pendingLiberarCaso?.prestamo_id ?? '—'}</strong> (caso{' '}
                {pendingLiberarCaso?.id ?? '—'}) saldrá del flujo finiquito.
              </span>
              <span className="block">
                Use esto cuando <strong>Conciliar</strong> confirme que el crédito{' '}
                <strong>no está liquidado</strong>: el préstamo vuelve a cartera
                operativa (pagos, cuotas, revisión manual habitual).
              </span>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setPendingLiberarCaso(null)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              className="bg-sky-700 hover:bg-sky-800"
              disabled={pendingEstadoCasoId != null}
              onClick={() => void confirmarLiberarProcesosNormales()}
            >
              Procesos normales
            </Button>
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
              ¿Confirma <strong>rechazar</strong> este caso? Dejara de mostrarse
              en las bandejas activas.
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

      <Dialog
        open={pendingEliminarCasoId != null}
        onOpenChange={open => {
          if (!open) setPendingEliminarCasoId(null)
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Eliminar caso</DialogTitle>
            <DialogDescription className="text-base text-slate-800">
              Quita el caso de finiquito (solo en Revision). El prestamo sigue
              LIQUIDADO; puede volver con «Refrescar materializado» si aplica.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              onClick={() => setPendingEliminarCasoId(null)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => void confirmarEliminar()}
            >
              Eliminar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <FiniquitoRevisionDialog
        open={revisionDialogCasoId != null}
        casoId={revisionDialogCasoId ?? 0}
        onOpenChange={open => {
          if (!open) setRevisionDialogCasoId(null)
        }}
      />
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
