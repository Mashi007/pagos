import { useEffect, useState } from 'react'

import { Calendar, Loader2 } from 'lucide-react'

import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'

import { cn, formatCurrency, formatDate } from '../../utils'

import {
  finiquitoAdminRevisionDatos,
  finiquitoRevisionDatos,
  type FiniquitoRevisionDatosResponse,
} from '../../services/finiquitoService'

/** Contenedor del área de datos bajo pestañas (flex consume alto del modal). */
const PANEL_SCROLL =
  'flex min-h-0 flex-1 flex-col overflow-hidden sm:min-h-[min(58vh,520px)]'

/** Tabla densa tipo back-office; cabecera oscura fija al hacer scroll. */
const TABLE_SHELL =
  'min-h-0 flex-1 overflow-auto rounded-md border border-slate-300 bg-white shadow-sm'

const thFin =
  'h-7 whitespace-nowrap bg-slate-800 px-2 py-0.5 text-left text-[11px] font-semibold uppercase tracking-wide text-white'

const tdFin = 'px-2 py-1 align-middle text-[11px] text-slate-900 tabular-nums'

const trFinEven = 'border-b border-slate-200 bg-white hover:bg-slate-100/90'

const trFinOdd =
  'border-b border-slate-200 bg-slate-50/90 hover:bg-slate-100/90'

/**
 * Pestaña Descripción: solo los bloques acordados (resumen visual 1 + cédula + ID préstamo).
 * Orden: cédula, ID préstamo, luego el resto como en la referencia de negocio.
 */
const DESCRIPCION_CAMPOS_ORDEN = [
  'cedula',
  'id',
  'analista',
  'cliente_id',
  'cuota_periodo',
  'fecha_aprobacion',
  'fecha_registro',
  'modalidad_pago',
  'nombres',
  'producto',
  'total_financiamiento',
] as const

const PRESTAMO_CAMPO_LABEL: Record<string, string> = {
  id: 'ID préstamo',
  cliente_id: 'ID cliente',
  cedula: 'Cédula',
  nombres: 'Nombres',
  total_financiamiento: 'Total financiamiento',
  fecha_requerimiento: 'Fecha requerimiento',
  modalidad_pago: 'Modalidad de pago',
  numero_cuotas: 'Número de cuotas',
  cuota_periodo: 'Cuota / periodo',
  tasa_interes: 'Tasa interés',
  fecha_base_calculo: 'Fecha base cálculo',
  producto: 'Producto',
  estado: 'Estado préstamo',
  fecha_liquidado: 'Fecha liquidado',
  usuario_proponente: 'Usuario proponente',
  usuario_aprobador: 'Usuario aprobador',
  observaciones: 'Observaciones',
  fecha_registro: 'Fecha registro',
  fecha_aprobacion: 'Fecha aprobación',
  fecha_actualizacion: 'Fecha actualización',
  concesionario: 'Concesionario',
  analista: 'Analista',
  modelo_vehiculo: 'Modelo vehículo',
  usuario_autoriza: 'Usuario autoriza',
  valor_activo: 'Valor activo',
  requiere_revision: 'Requiere revisión',
  concesionario_id: 'ID concesionario',
  analista_id: 'ID analista',
  modelo_vehiculo_id: 'ID modelo vehículo',
}

function modalidadLabel(v: unknown): string {
  const s = String(v || '')
  if (s === 'MENSUAL') return 'Mensual'
  if (s === 'QUINCENAL') return 'Quincenal'
  if (s === 'SEMANAL') return 'Semanal'
  return s || '-'
}

function estadoPrestamoBadgeClass(estado: string): string {
  const e = (estado || '').toUpperCase()
  if (e === 'APROBADO') return 'bg-green-100 text-green-800'
  if (e === 'LIQUIDADO') return 'bg-emerald-100 text-emerald-900'
  if (e === 'EN_REVISION') return 'bg-yellow-100 text-yellow-800'
  if (e === 'RECHAZADO') return 'bg-red-100 text-red-800'
  if (e === 'EVALUADO') return 'bg-blue-100 text-blue-800'
  return 'bg-gray-100 text-gray-800'
}

function estadoPrestamoLabel(estado: string): string {
  const e = (estado || '').toUpperCase()
  if (e === 'APROBADO') return 'Aprobado'
  if (e === 'LIQUIDADO') return 'Liquidado'
  if (e === 'EN_REVISION') return 'En Revisión'
  if (e === 'RECHAZADO') return 'Rechazado'
  if (e === 'EVALUADO') return 'Evaluado'
  if (e === 'DRAFT') return 'Borrador'
  return estado || '-'
}

function formatearValorPrestamoCampo(key: string, val: unknown): string {
  if (val === null || val === undefined) return '-'
  if (key === 'modalidad_pago') return modalidadLabel(val)
  if (key === 'requiere_revision') return val ? 'Sí' : 'No'
  if (
    key === 'total_financiamiento' ||
    key === 'cuota_periodo' ||
    key === 'tasa_interes' ||
    key === 'valor_activo'
  ) {
    const n = Number(val)
    return Number.isFinite(n) ? formatCurrency(n) : String(val)
  }
  if (
    key.includes('fecha') ||
    key === 'fecha_registro' ||
    key === 'fecha_aprobacion' ||
    key === 'fecha_actualizacion'
  ) {
    const s = String(val)
    if (!s) return '-'
    try {
      return formatDate(s)
    } catch {
      return s
    }
  }
  return String(val)
}

type Props = {
  open: boolean
  casoId: number | null
  onOpenChange: (open: boolean) => void
  mode?: 'public' | 'admin'
}

export function FiniquitoRevisionDialog({
  open,
  casoId,
  onOpenChange,
  mode = 'public',
}: Props) {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<FiniquitoRevisionDatosResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tabRevision, setTabRevision] = useState('descripcion')

  useEffect(() => {
    if (!open || casoId == null) {
      setData(null)
      setError(null)
      setTabRevision('descripcion')
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    const promise =
      mode === 'admin'
        ? finiquitoAdminRevisionDatos(casoId)
        : finiquitoRevisionDatos(casoId)
    promise
      .then(res => {
        if (!cancelled) setData(res)
      })
      .catch(e => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : 'Error al cargar revision')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, casoId, mode])

  const prestamosItems = data?.prestamos?.prestamos ?? []
  const pagosItems = data?.pagos?.pagos ?? []
  const cuotasItems = data?.cuotas_caso ?? []
  const prestamoCaso = data?.prestamo_caso
  const cedulaDescripcion = (
    (data?.cedula ?? prestamoCaso?.cedula ?? '') as string
  ).trim()

  const pagosTotal = data?.pagos?.total ?? 0
  const pagosPerPage = data?.pagos?.per_page ?? 100

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className={cn(
          'flex !h-[92vh] !max-h-[92vh] w-[min(96rem,calc(100vw-0.75rem))] !max-w-[min(96rem,calc(100vw-0.75rem))] flex-col gap-0 overflow-hidden !p-0 shadow-xl',
          'rounded-lg border border-slate-300 bg-white'
        )}
      >
        <DialogHeader className="mb-0 shrink-0 border-b border-slate-300 bg-gradient-to-r from-slate-100 to-slate-50 px-4 py-2.5 sm:px-5">
          <DialogTitle className="text-left text-base font-bold tracking-tight text-[#1e3a5f]">
            Detalle del caso - préstamo, cuotas, movimientos
          </DialogTitle>
          <DialogDescription className="text-left text-xs leading-relaxed text-slate-800">
            <span className="font-mono font-semibold text-slate-900">
              {data?.cedula ?? '…'}
            </span>
            {data?.prestamo_id_finiquito != null && (
              <>
                {' '}
                <span className="text-slate-500">|</span> Crédito{' '}
                <span className="font-mono font-semibold text-slate-900">
                  #{data.prestamo_id_finiquito}
                </span>
              </>
            )}
            <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-900">
              Solo lectura
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-slate-100/60 px-2 pb-2 pt-1.5 sm:px-3">
          {loading && (
            <div className="flex flex-1 items-center justify-center py-12">
              <Loader2 className="h-9 w-9 animate-spin text-slate-500" />
            </div>
          )}
          {!loading && error && (
            <div className="m-2 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-900">
              {error}
            </div>
          )}
          {!loading && !error && data && (
            <Tabs
              value={tabRevision}
              onValueChange={setTabRevision}
              className="flex min-h-0 flex-1 flex-col"
            >
              <TabsList className="mb-1.5 h-auto shrink-0 flex-wrap justify-start gap-0.5 rounded-md border border-slate-300 bg-slate-200/90 p-0.5 sm:h-9 sm:flex-nowrap">
                <TabsTrigger
                  value="descripcion"
                  className="rounded px-2.5 py-1 text-xs font-semibold"
                >
                  Descripción
                </TabsTrigger>
                <TabsTrigger
                  value="prestamos"
                  className="rounded px-2.5 py-1 text-xs font-semibold"
                >
                  Resumen Préstamo
                </TabsTrigger>
                <TabsTrigger
                  value="cuotas"
                  className="rounded px-2.5 py-1 text-xs font-semibold"
                >
                  Cuotas
                </TabsTrigger>
                <TabsTrigger
                  value="pagos"
                  className="rounded px-2.5 py-1 text-xs font-semibold"
                >
                  Pagos
                </TabsTrigger>
              </TabsList>

              <TabsContent
                value="descripcion"
                className="mt-0 flex min-h-0 flex-1 flex-col overflow-hidden focus-visible:outline-none"
              >
                <div
                  className={cn(
                    PANEL_SCROLL,
                    'rounded-md border border-slate-300 bg-white p-3'
                  )}
                >
                  {!prestamoCaso && !cedulaDescripcion ? (
                    <p className="text-xs text-slate-600">
                      No hay préstamo asociado a este caso.
                    </p>
                  ) : (
                    <div className="grid min-h-0 auto-rows-min grid-cols-1 gap-x-6 gap-y-2 overflow-y-auto text-xs sm:grid-cols-2 lg:grid-cols-3">
                      {DESCRIPCION_CAMPOS_ORDEN.map(key => {
                        const raw =
                          key === 'cedula'
                            ? cedulaDescripcion || null
                            : prestamoCaso
                              ? prestamoCaso[key as string]
                              : undefined
                        const label = PRESTAMO_CAMPO_LABEL[key] ?? key
                        const empty =
                          raw === null ||
                          raw === undefined ||
                          (typeof raw === 'string' && raw.trim() === '')
                        if (key !== 'cedula' && !prestamoCaso) {
                          return null
                        }
                        return (
                          <div
                            key={key}
                            className="flex flex-col border-b border-slate-200/80 pb-2 sm:border-0 sm:pb-0"
                          >
                            <span className="text-[10px] font-bold uppercase tracking-wide text-slate-500">
                              {label}
                            </span>
                            <span
                              className={cn(
                                'mt-0.5 break-words font-medium text-slate-900',
                                (key === 'cedula' || key === 'id') &&
                                  'font-mono text-sm'
                              )}
                            >
                              {empty
                                ? '-'
                                : formatearValorPrestamoCampo(key, raw)}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </TabsContent>

              <TabsContent
                value="prestamos"
                className="mt-0 flex min-h-0 flex-1 flex-col overflow-hidden focus-visible:outline-none"
              >
                <div className={TABLE_SHELL}>
                  <Table className="text-xs">
                    <TableHeader className="sticky top-0 z-20 shadow-sm">
                      <TableRow className="border-0 hover:bg-transparent">
                        <TableHead className={thFin}>Cliente</TableHead>
                        <TableHead className={thFin}>Cédula</TableHead>
                        <TableHead className={thFin}>Monto</TableHead>
                        <TableHead className={thFin}>Modal.</TableHead>
                        <TableHead className={thFin}>Nº cuot.</TableHead>
                        <TableHead className={thFin}>Estado</TableHead>
                        <TableHead className={thFin}>Aprob.</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {prestamosItems.length === 0 ? (
                        <TableRow>
                          <TableCell
                            colSpan={7}
                            className={cn(tdFin, 'text-center text-slate-500')}
                          >
                            Sin préstamos para esta cédula.
                          </TableCell>
                        </TableRow>
                      ) : (
                        prestamosItems.map(
                          (p: Record<string, unknown>, idx) => (
                            <TableRow
                              key={`p-${String(p.id)}`}
                              className={idx % 2 === 0 ? trFinEven : trFinOdd}
                            >
                              <TableCell
                                className={cn(
                                  tdFin,
                                  'max-w-[140px] font-medium'
                                )}
                              >
                                {String(
                                  p.nombres ??
                                    p.nombre_cliente ??
                                    `Cliente #${p.cliente_id ?? '-'}`
                                )}
                              </TableCell>
                              <TableCell
                                className={cn(tdFin, 'font-mono text-[10px]')}
                              >
                                {String(p.cedula ?? p.cedula_cliente ?? '-')}
                              </TableCell>
                              <TableCell className={tdFin}>
                                <span className="font-semibold text-emerald-800">
                                  {formatCurrency(
                                    Number(p.total_financiamiento ?? 0)
                                  )}
                                </span>
                              </TableCell>
                              <TableCell className={tdFin}>
                                {modalidadLabel(p.modalidad_pago)}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {p.numero_cuotas != null
                                  ? String(p.numero_cuotas)
                                  : '-'}
                              </TableCell>
                              <TableCell className={tdFin}>
                                <Badge
                                  className={cn(
                                    'border-0 text-[10px]',
                                    estadoPrestamoBadgeClass(
                                      String(p.estado ?? '')
                                    )
                                  )}
                                >
                                  {estadoPrestamoLabel(String(p.estado ?? ''))}
                                </Badge>
                              </TableCell>
                              <TableCell
                                className={cn(tdFin, 'whitespace-nowrap')}
                              >
                                {p.fecha_aprobacion ? (
                                  <span className="inline-flex items-center gap-0.5">
                                    <Calendar
                                      className="h-3 w-3 text-slate-500"
                                      aria-hidden
                                    />
                                    {formatDate(String(p.fecha_aprobacion))}
                                  </span>
                                ) : (
                                  '-'
                                )}
                              </TableCell>
                            </TableRow>
                          )
                        )
                      )}
                    </TableBody>
                  </Table>
                </div>
              </TabsContent>

              <TabsContent
                value="cuotas"
                className="mt-0 flex min-h-0 flex-1 flex-col overflow-hidden focus-visible:outline-none"
              >
                <div className="mb-1 flex shrink-0 items-center justify-between gap-2 rounded-t-md border border-b-0 border-slate-300 bg-slate-800 px-2 py-1">
                  <span className="text-[11px] font-semibold uppercase tracking-wide text-white">
                    Plan de cuotas
                  </span>
                  <span className="font-mono text-[11px] text-slate-200">
                    {cuotasItems.length} filas - desplazamiento vertical
                  </span>
                </div>
                <div className={TABLE_SHELL}>
                  <Table className="text-xs">
                    <TableHeader className="sticky top-0 z-20 shadow-sm">
                      <TableRow className="border-0 hover:bg-transparent">
                        <TableHead className={thFin}>Nº</TableHead>
                        <TableHead className={thFin}>Venc.</TableHead>
                        <TableHead className={thFin}>F. pago</TableHead>
                        <TableHead className={thFin}>Cuota</TableHead>
                        <TableHead className={thFin}>Capital</TableHead>
                        <TableHead className={thFin}>Int.</TableHead>
                        <TableHead className={thFin}>Pagado</TableHead>
                        <TableHead className={thFin}>Saldo cap.</TableHead>
                        <TableHead className={thFin}>Estado</TableHead>
                        <TableHead className={thFin}>Mora</TableHead>
                        <TableHead className={thFin}>Pago</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {cuotasItems.length === 0 ? (
                        <TableRow>
                          <TableCell
                            colSpan={11}
                            className={cn(tdFin, 'text-center text-slate-500')}
                          >
                            Sin cuotas para el préstamo del caso.
                          </TableCell>
                        </TableRow>
                      ) : (
                        cuotasItems.map((c: Record<string, unknown>, idx) => (
                          <TableRow
                            key={`cu-${String(c.id)}`}
                            className={idx % 2 === 0 ? trFinEven : trFinOdd}
                          >
                            <TableCell
                              className={cn(
                                tdFin,
                                'font-semibold text-slate-800'
                              )}
                            >
                              {String(c.numero_cuota ?? '')}
                            </TableCell>
                            <TableCell
                              className={cn(tdFin, 'whitespace-nowrap')}
                            >
                              {c.fecha_vencimiento
                                ? formatDate(String(c.fecha_vencimiento))
                                : '-'}
                            </TableCell>
                            <TableCell
                              className={cn(tdFin, 'whitespace-nowrap')}
                            >
                              {c.fecha_pago
                                ? formatDate(String(c.fecha_pago))
                                : '-'}
                            </TableCell>
                            <TableCell className={tdFin}>
                              {formatCurrency(Number(c.monto_cuota ?? 0))}
                            </TableCell>
                            <TableCell className={tdFin}>
                              {formatCurrency(Number(c.monto_capital ?? 0))}
                            </TableCell>
                            <TableCell className={tdFin}>
                              {formatCurrency(Number(c.monto_interes ?? 0))}
                            </TableCell>
                            <TableCell className={tdFin}>
                              {formatCurrency(Number(c.total_pagado ?? 0))}
                            </TableCell>
                            <TableCell className={tdFin}>
                              {formatCurrency(
                                Number(c.saldo_capital_final ?? 0)
                              )}
                            </TableCell>
                            <TableCell
                              className={cn(
                                tdFin,
                                'font-medium uppercase text-slate-800'
                              )}
                            >
                              {String(c.estado ?? '')}
                            </TableCell>
                            <TableCell className={tdFin}>
                              {c.dias_mora != null
                                ? String(c.dias_mora)
                                : c.dias_morosidad != null
                                  ? String(c.dias_morosidad)
                                  : '-'}
                            </TableCell>
                            <TableCell
                              className={cn(tdFin, 'font-mono text-[10px]')}
                            >
                              {c.pago_id != null ? String(c.pago_id) : '-'}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </TabsContent>

              <TabsContent
                value="pagos"
                className="mt-0 flex min-h-0 flex-1 flex-col overflow-hidden focus-visible:outline-none"
              >
                <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border border-slate-300 bg-white shadow-sm">
                  <div className="min-h-0 flex-1 overflow-auto">
                    <Table className="text-xs">
                      <TableHeader className="sticky top-0 z-20 shadow-sm">
                        <TableRow className="border-0 hover:bg-transparent">
                          <TableHead className={thFin}>ID</TableHead>
                          <TableHead className={thFin}>Cédula</TableHead>
                          <TableHead className={thFin}>Créd.</TableHead>
                          <TableHead className={thFin}>Est.</TableHead>
                          <TableHead className={thFin}>Notas</TableHead>
                          <TableHead className={thFin}>Monto</TableHead>
                          <TableHead className={thFin}>Fecha</TableHead>
                          <TableHead className={thFin}>Doc.</TableHead>
                          <TableHead className={thFin}>Conc.</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {pagosItems.length === 0 ? (
                          <TableRow>
                            <TableCell
                              colSpan={9}
                              className={cn(
                                tdFin,
                                'text-center text-slate-500'
                              )}
                            >
                              Sin pagos en esta página.
                            </TableCell>
                          </TableRow>
                        ) : (
                          pagosItems.map((p: Record<string, unknown>, idx) => (
                            <TableRow
                              key={`pay-${String(p.id)}`}
                              className={idx % 2 === 0 ? trFinEven : trFinOdd}
                            >
                              <TableCell
                                className={cn(tdFin, 'font-mono text-[10px]')}
                              >
                                {String(p.id ?? '')}
                              </TableCell>
                              <TableCell
                                className={cn(tdFin, 'font-mono text-[10px]')}
                              >
                                {String(p.cedula_cliente ?? '')}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {p.prestamo_id != null
                                  ? String(p.prestamo_id)
                                  : '-'}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {String(p.estado ?? '')}
                              </TableCell>
                              <TableCell
                                className={cn(
                                  tdFin,
                                  'max-w-[160px] truncate text-left'
                                )}
                                title={String(p.notas ?? '')}
                              >
                                {p.notas != null &&
                                String(p.notas).trim() !== ''
                                  ? String(p.notas)
                                  : '-'}
                              </TableCell>
                              <TableCell className={cn(tdFin, 'font-semibold')}>
                                {formatCurrency(Number(p.monto_pagado ?? 0))}
                              </TableCell>
                              <TableCell
                                className={cn(tdFin, 'whitespace-nowrap')}
                              >
                                {p.fecha_pago
                                  ? formatDate(String(p.fecha_pago))
                                  : '-'}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {String(p.numero_documento ?? '')}
                              </TableCell>
                              <TableCell className={tdFin}>
                                {p.conciliado ? 'Sí' : 'No'}
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </div>
                  {pagosTotal > pagosPerPage && (
                    <p className="shrink-0 border-t border-slate-300 bg-slate-100 px-2 py-1.5 text-[10px] text-slate-700">
                      Total {pagosTotal} pagos; vista limitada a {pagosPerPage}.
                      Histórico completo en módulo Pagos.
                    </p>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          )}
        </div>

        <div className="flex shrink-0 justify-end border-t border-slate-300 bg-slate-100 px-4 py-2 sm:px-5">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="border-slate-400 font-semibold text-[#1e3a5f]"
            onClick={() => onOpenChange(false)}
          >
            Cerrar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
