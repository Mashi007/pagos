import { useCallback, useEffect, useState } from 'react'

import {
  CheckCircle2,
  Download,
  Eye,
  Loader2,
  RefreshCw,
  Search,
  X,
  XCircle,
  FileText,
} from 'lucide-react'

import { toast } from 'sonner'

import { Button } from '../components/ui/button'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
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

import { FiniquitoRevisionDialog } from '../components/finiquito/FiniquitoRevisionDialog'

import {
  type FiniquitoCasoItem,
  finiquitoAdminListar,
  finiquitoAdminPatchEstado,
  finiquitoAdminRefreshMaterializado,
  type FiniquitoRefreshStats,
} from '../services/finiquitoService'
import { prestamoService } from '../services/prestamoService'

import { cn, formatDate } from '../utils'

function textoUltimoPago(iso: string | null | undefined): string {
  if (iso == null || String(iso).trim() === '') return '-'
  try {
    return formatDate(String(iso))
  } catch {
    return String(iso)
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

export function FiniquitoGestionPage() {
  const [cedulaInput, setCedulaInput] = useState('')
  const [cedulaBusqueda, setCedulaBusqueda] = useState('')
  const [itemsAreaTrabajo, setItemsAreaTrabajo] = useState<FiniquitoCasoItem[]>(
    []
  )
  const [dialogTerminadoCasoId, setDialogTerminadoCasoId] = useState<
    number | null
  >(null)
  const [itemsRechazados, setItemsRechazados] = useState<FiniquitoCasoItem[]>(
    []
  )
  const [itemsBandeja, setItemsBandeja] = useState<FiniquitoCasoItem[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [revisionOpen, setRevisionOpen] = useState(false)
  const [revisionCasoId, setRevisionCasoId] = useState<number | null>(null)
  const [
    descargandoEstadoCuentaPrestamoId,
    setDescargandoEstadoCuentaPrestamoId,
  ] = useState<number | null>(null)

  useEffect(() => {
    const t = window.setTimeout(
      () => setCedulaBusqueda(cedulaInput.trim()),
      DEBOUNCE_MS
    )
    return () => window.clearTimeout(t)
  }, [cedulaInput])

  const cargarListas = useCallback(async () => {
    setLoading(true)
    try {
      const [rTrabajo, rRech, rBandeja] = await Promise.all([
        finiquitoAdminListar(
          undefined,
          undefined,
          'ACEPTADO,EN_PROCESO,TERMINADO'
        ),
        finiquitoAdminListar('RECHAZADO'),
        finiquitoAdminListar('REVISION', cedulaBusqueda || undefined),
      ])
      setItemsAreaTrabajo(rTrabajo.items || [])
      setItemsRechazados(rRech.items || [])
      setItemsBandeja(rBandeja.items || [])
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al cargar')
    } finally {
      setLoading(false)
    }
  }, [cedulaBusqueda])

  useEffect(() => {
    cargarListas()
  }, [cargarListas])

  const onRefreshJob = async () => {
    setRefreshing(true)
    try {
      const r = await finiquitoAdminRefreshMaterializado()
      const { titulo, descripcion } = textoToastRefresco(r)
      toast.success(titulo, { description: descripcion })
      await cargarListas()
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
      toast.success('Estado actualizado')
      cargarListas()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error')
    }
  }

  const confirmarTerminado = async (contactoParaSiguientes: boolean) => {
    if (dialogTerminadoCasoId == null) return
    try {
      const r = await finiquitoAdminPatchEstado(
        dialogTerminadoCasoId,
        'TERMINADO',
        contactoParaSiguientes
      )
      if (!r.ok) {
        toast.error(r.error || 'No se pudo actualizar')
        return
      }
      setDialogTerminadoCasoId(null)
      toast.success('Caso marcado como terminado')
      cargarListas()
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error')
    }
  }

  const limpiarCedula = () => {
    setCedulaInput('')
    setCedulaBusqueda('')
  }

  const renderAcciones = (row: FiniquitoCasoItem) => (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <Button
        type="button"
        size="icon"
        variant="outline"
        className="h-8 w-8 border-slate-300"
        title="Ver préstamo, cuotas y pagos"
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
        disabled={descargandoEstadoCuentaPrestamoId === row.prestamo_id}
        onClick={() => descargarEstadoCuenta(row.prestamo_id)}
      >
        {descargandoEstadoCuentaPrestamoId === row.prestamo_id ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        ) : (
          <Download className="h-4 w-4" aria-hidden />
        )}
        <span className="sr-only">Descargar estado de cuenta PDF</span>
      </Button>
      <Select onValueChange={v => cambiarEstado(row.id, v)}>
        <SelectTrigger className="h-8 w-[150px] text-xs">
          <SelectValue placeholder="Estado..." />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="REVISION">Revisión</SelectItem>
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
        title="Ver préstamo, cuotas y pagos"
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
        disabled={descargandoEstadoCuentaPrestamoId === row.prestamo_id}
        onClick={() => descargarEstadoCuenta(row.prestamo_id)}
      >
        {descargandoEstadoCuentaPrestamoId === row.prestamo_id ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        ) : (
          <Download className="h-4 w-4" aria-hidden />
        )}
        <span className="sr-only">Descargar estado de cuenta PDF</span>
      </Button>
      {row.estado === 'ACEPTADO' ? (
        <Button
          type="button"
          size="sm"
          variant="secondary"
          className="h-8 text-xs"
          onClick={() => cambiarEstado(row.id, 'EN_PROCESO')}
        >
          En proceso
        </Button>
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
            onClick={() => setDialogTerminadoCasoId(row.id)}
          >
            Terminado
          </Button>
        </>
      ) : null}
    </div>
  )

  const renderTabla = (items: FiniquitoCasoItem[]) => (
    <div className="overflow-hidden rounded-md border border-slate-200">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-0 hover:bg-transparent">
              <TableHead className={thGestion}>ID caso</TableHead>
              <TableHead className={thGestion}>Cédula</TableHead>
              <TableHead className={thGestion}>Préstamo</TableHead>
              <TableHead className={cn(thGestion, 'whitespace-normal')}>
                Último pago
              </TableHead>
              <TableHead className={thGestion}>Estado</TableHead>
              <TableHead className={cn(thGestion, 'text-right')}>
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
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-medium uppercase text-slate-800">
                    {row.estado}
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
    </div>
  )

  const renderTablaAreaTrabajo = (items: FiniquitoCasoItem[]) => (
    <div className="overflow-hidden rounded-md border border-slate-200">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-0 hover:bg-transparent">
              <TableHead className={thGestion}>ID caso</TableHead>
              <TableHead className={thGestion}>Cédula</TableHead>
              <TableHead className={thGestion}>Préstamo</TableHead>
              <TableHead className={cn(thGestion, 'whitespace-normal')}>
                Último pago
              </TableHead>
              <TableHead className={cn(thGestion, 'min-w-[140px]')}>
                Contacto
              </TableHead>
              <TableHead className={thGestion}>Estado</TableHead>
              <TableHead className={cn(thGestion, 'text-right')}>
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
                      'rounded px-1.5 py-0.5 text-xs font-medium uppercase',
                      row.estado === 'ACEPTADO' &&
                        'bg-slate-100 text-slate-800',
                      row.estado === 'EN_PROCESO' &&
                        'bg-amber-100 text-amber-950',
                      row.estado === 'TERMINADO' &&
                        'bg-emerald-100 text-emerald-950'
                    )}
                  >
                    {row.estado.replace('_', ' ')}
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
    </div>
  )

  return (
    <div className="min-h-full bg-slate-100/80 pb-10 pt-4 md:pt-6">
      <div className="mx-auto max-w-7xl space-y-5 px-4 md:space-y-6 md:px-6">
        <ModulePageHeader
          icon={FileText}
          title="Finiquito · Gestión"
          description="Área de trabajo: flujo post-aprobación (en proceso, terminado). Bandeja central por cédula. Abajo: rechazados."
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
        />

        {/* Área de trabajo: aprobados */}
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
                  Aceptados, en proceso y terminados · {itemsAreaTrabajo.length}{' '}
                  {itemsAreaTrabajo.length === 1 ? 'registro' : 'registros'}
                </p>
              </div>
            </div>
          </div>
          <div className="bg-gradient-to-b from-emerald-50/50 to-white p-3 sm:p-4">
            {loading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-emerald-600/70" />
              </div>
            ) : itemsAreaTrabajo.length === 0 ? (
              <p className="rounded-lg border border-dashed border-emerald-200/80 bg-white/60 px-4 py-10 text-center text-sm text-slate-600">
                No hay casos en esta bandeja. Los aceptados aparecen aquí; use
                «En proceso» y luego «Terminado» para cerrar el flujo.
              </p>
            ) : (
              renderTablaAreaTrabajo(itemsAreaTrabajo)
            )}
          </div>
        </section>

        {/* Bandeja principal + filtro cédula */}
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
                    htmlFor="finiquito-filtro-cedula"
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
                      id="finiquito-filtro-cedula"
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
                  onClick={() => cargarListas()}
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
                Filtro activo:{' '}
                <span className="font-mono font-semibold text-[#1e3a5f]">
                  {cedulaBusqueda}
                </span>
              </p>
            ) : null}
          </div>
          <div className="p-3 sm:p-4">
            {loading ? (
              <div className="flex justify-center py-14">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
              </div>
            ) : itemsBandeja.length === 0 ? (
              <p className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50 px-4 py-10 text-center text-sm leading-relaxed text-slate-600">
                {cedulaBusqueda
                  ? 'Ningún caso en revisión coincide con esa cédula. Pruebe otra subcadena o limpie el filtro.'
                  : 'No hay casos en revisión. Use «Refrescar materializado» si acaba de cargar datos o revise préstamos saldados.'}
              </p>
            ) : (
              renderTabla(itemsBandeja)
            )}
          </div>
        </section>

        {/* Área de revisión: rechazados */}
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
                  Rechazados · {itemsRechazados.length}{' '}
                  {itemsRechazados.length === 1 ? 'registro' : 'registros'}
                </p>
              </div>
            </div>
          </div>
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
              renderTabla(itemsRechazados)
            )}
          </div>
        </section>
      </div>

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
        open={dialogTerminadoCasoId != null}
        onOpenChange={open => {
          if (!open) setDialogTerminadoCasoId(null)
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
              onClick={() => setDialogTerminadoCasoId(null)}
            >
              Cancelar
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => confirmarTerminado(false)}
            >
              No
            </Button>
            <Button
              type="button"
              className="bg-emerald-700 hover:bg-emerald-800"
              onClick={() => confirmarTerminado(true)}
            >
              Sí
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
