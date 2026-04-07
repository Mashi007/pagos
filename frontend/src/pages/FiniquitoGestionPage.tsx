import { useCallback, useEffect, useState } from 'react'

import { useQueryClient } from '@tanstack/react-query'

import {
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
import { Textarea } from '../components/ui/textarea'
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

import { FiniquitoRevisionDialog } from '../components/finiquito/FiniquitoRevisionDialog'

import {
  type FiniquitoCasoItem,
  finiquitoAdminConteoRevisionNuevos,
  finiquitoAdminListar,
  finiquitoAdminPatchEstado,
  finiquitoAdminRefreshMaterializado,
  type FiniquitoRefreshStats,
  FINIQUITO_HORAS_NUEVOS_REVISION_DEFAULT,
} from '../services/finiquitoService'
import { prestamoService } from '../services/prestamoService'

import { cn, formatDate } from '../utils'
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

/** YYYY-MM-DD desde ISO o fecha parseable (comparar con corte migracion). */
function parseIsoDateOnly(iso: string | null | undefined): string | null {
  if (iso == null || String(iso).trim() === '') return null
  const s = String(iso).trim()
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (m) return `${m[1]}-${m[2]}-${m[3]}`
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return null
  const y = d.getFullYear()
  const mo = String(d.getMonth() + 1).padStart(2, '0')
  const da = String(d.getDate()).padStart(2, '0')
  return `${y}-${mo}-${da}`
}

const FECHA_CORTE_ANTIGUO = '2026-01-01'

const MIN_NOTA_ANTIGUO = 15

/** True si hace falta nota: sin fecha, o ultimo pago estrictamente despues del 01/01/2026. */
function requiereNotaJustificativaAntiguo(
  ultimaFechaPagoIso: string | null | undefined
): boolean {
  const day = parseIsoDateOnly(ultimaFechaPagoIso)
  if (day == null) return true
  return day > FECHA_CORTE_ANTIGUO
}

function estadoEtiquetaVisible(estado: string): string {
  const map: Record<string, string> = {
    REVISION: 'Revisión',
    ACEPTADO: 'Aceptado',
    RECHAZADO: 'Rechazado',
    EN_PROCESO: 'En proceso',
    TERMINADO: 'Terminado',
    ANTIGUO: 'Antiguo',
  }
  return map[estado] ?? estado.replace(/_/g, ' ')
}

function estadoBadgeClassName(estado: string): string {
  switch (estado) {
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
    case 'ANTIGUO':
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
        ? 'Insertados 0 es normal si esos préstamos ya estaban en finiquito. Los saldados suelen verse en la bandeja Revisión (no en Rechazados).'
        : `Quitados del listado (ya no califican): ${eli}. Revise el filtro de bandeja si no ve filas.`,
  }
}

const DEBOUNCE_MS = 420

/** Coincide con backend `_ADMIN_CASOS_MAX_LIMIT` (listar sin paginar en UI). */
const FETCH_LIMIT = 2000

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
}: {
  total: number
  cargados: number
}) {
  if (cargados === 0) return null
  const truncado = total > FETCH_LIMIT && cargados === FETCH_LIMIT
  return (
    <p className="mt-2 text-center text-[11px] leading-snug text-slate-500">
      {cargados === total
        ? `${total} caso(s).`
        : `${cargados} en pantalla de ${total} totales.`}
      {truncado ? (
        <>
          {' '}
          <span className="font-medium text-amber-900">
            Listado acotado a {FETCH_LIMIT} (límite API).
          </span>
        </>
      ) : null}{' '}
      Desplácese dentro de la tabla para ver más filas (~10 visibles a la vez).
    </p>
  )
}

function FiniquitoGestionPageInner() {
  const queryClient = useQueryClient()

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
  const [revisionOpen, setRevisionOpen] = useState(false)
  const [revisionCasoId, setRevisionCasoId] = useState<number | null>(null)
  const [
    descargandoEstadoCuentaPrestamoId,
    setDescargandoEstadoCuentaPrestamoId,
  ] = useState<number | null>(null)
  const [pendingRechazoCasoId, setPendingRechazoCasoId] = useState<
    number | null
  >(null)
  const [dialogAntiguoRow, setDialogAntiguoRow] =
    useState<FiniquitoCasoItem | null>(null)
  const [antiguoNota, setAntiguoNota] = useState('')
  const [antiguoSubmitting, setAntiguoSubmitting] = useState(false)
  const [kpiNuevosRevision, setKpiNuevosRevision] = useState<{
    total: number
    ventana_horas: number
  } | null>(null)

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

  const cargarListas = useCallback(
    async (opts?: { silent?: boolean }) => {
      const silent = opts?.silent === true
      if (!silent) {
        setLoading(true)
      }
      try {
        const [rTrabajo, rRech, rBandeja, rNuevos] = await Promise.all([
          finiquitoAdminListar(
            undefined,
            cedulaTrabajoBusqueda || undefined,
            'ACEPTADO,EN_PROCESO,TERMINADO',
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
              limit: FETCH_LIMIT,
              offset: 0,
            }
          ),
          finiquitoAdminConteoRevisionNuevos(
            cedulaBusqueda || undefined,
            FINIQUITO_HORAS_NUEVOS_REVISION_DEFAULT
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
      } catch (e: unknown) {
        setKpiNuevosRevision(null)
        toast.error(e instanceof Error ? e.message : 'Error al cargar')
      } finally {
        if (!silent) {
          setLoading(false)
        }
      }
    },
    [cedulaBusqueda, cedulaTrabajoBusqueda]
  )

  /** Actualiza filas locales al instante con el caso devuelto por PATCH (antes del refetch). */
  const incorporarCasoActualizado = useCallback((caso: FiniquitoCasoItem) => {
    const enAreaTrabajo = ['ACEPTADO', 'EN_PROCESO', 'TERMINADO'].includes(
      caso.estado
    )
    setItemsAreaTrabajo(prev => {
      if (!prev.some(r => r.id === caso.id)) return prev
      if (!enAreaTrabajo) {
        return prev.filter(r => r.id !== caso.id)
      }
      return prev.map(r => (r.id === caso.id ? { ...r, ...caso } : r))
    })
    setItemsBandeja(prev => {
      if (!prev.some(r => r.id === caso.id)) return prev
      if (caso.estado !== 'REVISION') {
        return prev.filter(r => r.id !== caso.id)
      }
      return prev.map(r => (r.id === caso.id ? { ...r, ...caso } : r))
    })
    setItemsRechazados(prev =>
      prev.some(r => r.id === caso.id)
        ? prev.map(r => (r.id === caso.id ? { ...r, ...caso } : r))
        : prev
    )
  }, [])

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
        toast.success('En proceso', {
          description:
            'Se envió aviso a operaciones y cobranza (si el correo del servidor está configurado).',
        })
      } else if (estado === 'REVISION') {
        toast.success('Caso en bandeja principal (Revisión)')
      } else {
        toast.success('Estado actualizado')
      }
      void invalidatePrestamosQueries(queryClient)
      await cargarListas({ silent: true })
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error')
    }
  }

  const onSeleccionarEstadoBandeja = (row: FiniquitoCasoItem, v: string) => {
    if (v === 'RECHAZADO') {
      setPendingRechazoCasoId(row.id)
      return
    }
    if (v === 'ANTIGUO') {
      setDialogAntiguoRow(row)
      setAntiguoNota('')
      return
    }
    void cambiarEstado(row.id, v)
  }

  const confirmarAntiguo = async () => {
    if (dialogAntiguoRow == null) return
    const req = requiereNotaJustificativaAntiguo(
      dialogAntiguoRow.ultima_fecha_pago
    )
    const nota = antiguoNota.trim()
    if (req && nota.length < MIN_NOTA_ANTIGUO) {
      toast.error(
        `Nota justificativa obligatoria (minimo ${MIN_NOTA_ANTIGUO} caracteres) si la ultima fecha de pago es posterior al 01/01/2026 o no consta.`
      )
      return
    }
    setAntiguoSubmitting(true)
    try {
      const r = await finiquitoAdminPatchEstado(
        dialogAntiguoRow.id,
        'ANTIGUO',
        undefined,
        nota.length > 0 ? nota : undefined
      )
      if (!r.ok) {
        toast.error(r.error || 'No se pudo actualizar')
        return
      }
      setDialogAntiguoRow(null)
      setAntiguoNota('')
      toast.success('Caso marcado como Antiguo')
      if (r.caso) {
        incorporarCasoActualizado(r.caso)
      }
      void invalidatePrestamosQueries(queryClient)
      await cargarListas({ silent: true })
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error')
    } finally {
      setAntiguoSubmitting(false)
    }
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

  const renderAcciones = (row: FiniquitoCasoItem) => (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-8 w-8 border-slate-300"
        title="Ver préstamo, cuotas y pagos"
        aria-label={`Ver préstamo, cuotas y pagos del caso ${row.id}`}
        onClick={() => {
          setRevisionCasoId(row.id)
          setRevisionOpen(true)
        }}
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
        onValueChange={v => onSeleccionarEstadoBandeja(row, v)}
      >
        <SelectTrigger
          className="h-8 min-w-[158px] max-w-[200px] text-xs"
          aria-label={`Cambiar estado del caso ${row.id}`}
        >
          <SelectValue placeholder="Estado..." />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="REVISION">Revisión</SelectItem>
          <SelectItem value="ACEPTADO">Aceptado</SelectItem>
          <SelectItem value="RECHAZADO">Rechazado</SelectItem>
          <SelectItem value="ANTIGUO">Antiguo</SelectItem>
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
        title="Ver préstamo, cuotas y pagos"
        aria-label={`Ver préstamo, cuotas y pagos del caso ${row.id}`}
        onClick={() => {
          setRevisionCasoId(row.id)
          setRevisionOpen(true)
        }}
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
            onClick={() => cambiarEstado(row.id, 'ACEPTADO')}
          >
            Volver a aceptado
          </Button>
          <Button
            type="button"
            size="sm"
            className="h-8 bg-emerald-700 text-xs hover:bg-emerald-800"
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

  const renderTabla = (items: FiniquitoCasoItem[]) => (
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
                    estadoBadgeClassName(row.estado)
                  )}
                >
                  {estadoEtiquetaVisible(row.estado)}
                </span>
              </TableCell>
              <TableCell className={cn(tdGestion, 'text-right')}>
                {renderAcciones(row)}
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
                'max-w-[10.5rem] whitespace-normal leading-tight'
              )}
              scope="col"
              title="Fecha estimada de terminación del proceso de finiquito (15 días laborales desde En proceso)"
            >
              Fecha estimada de terminación del proceso de finiquito
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
                  row.finiquito_tramite_fecha_limite
                    ? 'Plazo calculado al marcar En proceso (días laborales)'
                    : undefined
                }
              >
                {row.finiquito_tramite_fecha_limite
                  ? formatDate(String(row.finiquito_tramite_fecha_limite))
                  : '-'}
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
                  {estadoEtiquetaVisible(row.estado)}
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
      description="Solo entran créditos LIQUIDADO con cuotas cubiertas (= financiamiento). Área de trabajo: en proceso y terminado. Bandeja central por cédula. Abajo: rechazados."
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
              Revisión (bandeja)
            </p>
            <p className="text-2xl font-bold tabular-nums text-[#1e3a5f]">
              {loading ? '-' : totalBandeja}
            </p>
            <p className="text-xs text-slate-500">
              Total en estado Revisión
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
                Nuevos en revisión
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
              Aceptado / En proceso / Terminado
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
              Casos rechazados en el portal
            </p>
          </CardContent>
        </Card>
      </div>

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
                Aceptados, en proceso y terminados · {totalAreaTrabajo}{' '}
                {subtituloTrabajo}
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
                    puede usar «En proceso» (aviso a operaciones/cobranza) o
                    «Terminado» para dejar el caso en pasivo.
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
                Casos en <strong>revisión</strong>. Escriba parte de la cédula
                para acotar (espera ~{DEBOUNCE_MS / 1000} s tras dejar de
                escribir).
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
                  ? 'Ningún caso en revisión coincide con esa cédula. Pruebe otra subcadena o limpie el filtro.'
                  : 'No hay casos en revisión. Use «Refrescar materializado» tras marcar préstamos como LIQUIDADO y cuadrar cuotas.'}
              </p>
            ) : (
              <>
                {renderTabla(itemsBandeja)}
                <FiniquitoTablaScrollHint
                  total={totalBandeja}
                  cargados={itemsBandeja.length}
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
                {renderTabla(itemsRechazados)}
                <FiniquitoTablaScrollHint
                  total={totalRechazados}
                  cargados={itemsRechazados.length}
                />
              </>
            )}
          </div>
        </div>
      </section>

      <FiniquitoRevisionDialog
        open={revisionOpen}
        casoId={revisionCasoId}
        mode="admin"
        onOpenChange={open => {
          setRevisionOpen(open)
          if (!open) setRevisionCasoId(null)
        }}
      />

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
        open={dialogAntiguoRow != null}
        onOpenChange={open => {
          if (!open) {
            setDialogAntiguoRow(null)
            setAntiguoNota('')
          }
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Marcar como Antiguo</DialogTitle>
            <DialogDescription className="space-y-2 text-left text-sm text-slate-700">
              <span className="block">
                Indica que el finiquito ya se gestionó antes de migrar a este
                sistema. Queda registrado en el historial de estados.
              </span>
              {dialogAntiguoRow ? (
                <>
                  <span className="block">
                    Última fecha de pago (referencia):{' '}
                    <strong>
                      {textoUltimoPago(dialogAntiguoRow.ultima_fecha_pago)}
                    </strong>
                  </span>
                  {requiereNotaJustificativaAntiguo(
                    dialogAntiguoRow.ultima_fecha_pago
                  ) ? (
                    <span className="block font-medium text-amber-900">
                      Obligatorio: nota justificativa (mín. {MIN_NOTA_ANTIGUO}{' '}
                      caracteres) porque la fecha es posterior al 01/01/2026 o
                      no consta.
                    </span>
                  ) : (
                    <span className="block text-slate-600">
                      No exige nota (último pago en o antes del 01/01/2026).
                      Puede añadir una nota opcional para auditoría.
                    </span>
                  )}
                </>
              ) : null}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="finiquito-antiguo-nota">Nota</Label>
            <Textarea
              id="finiquito-antiguo-nota"
              value={antiguoNota}
              onChange={e => setAntiguoNota(e.target.value)}
              rows={4}
              placeholder="Referencia interna, acuerdo, expediente..."
              className="resize-y"
            />
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              disabled={antiguoSubmitting}
              onClick={() => {
                setDialogAntiguoRow(null)
                setAntiguoNota('')
              }}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              className="bg-violet-700 hover:bg-violet-800"
              disabled={antiguoSubmitting}
              onClick={() => void confirmarAntiguo()}
            >
              {antiguoSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Guardando...
                </>
              ) : (
                'Confirmar Antiguo'
              )}
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
