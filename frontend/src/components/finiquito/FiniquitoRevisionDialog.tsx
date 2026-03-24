import { useEffect, useState } from 'react'

import { Calendar, DollarSign, Loader2 } from 'lucide-react'

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

import { formatCurrency, formatDate } from '../../utils'

import {
  finiquitoAdminRevisionDatos,
  finiquitoRevisionDatos,
  type FiniquitoRevisionDatosResponse,
} from '../../services/finiquitoService'

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
  /** public = token finiquito; admin = sesión del panel */
  mode?: 'public' | 'admin'
}

/**
 * Detalle del caso finiquito: préstamo del crédito, plan de cuotas, préstamos
 * y pagos por cédula (API revision-datos).
 */
export function FiniquitoRevisionDialog({
  open,
  casoId,
  onOpenChange,
  mode = 'public',
}: Props) {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<FiniquitoRevisionDatosResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tabRevision, setTabRevision] = useState('prestamo-caso')

  useEffect(() => {
    if (!open || casoId == null) {
      setData(null)
      setError(null)
      setTabRevision('prestamo-caso')
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
  const prestamoCamposOrdenados = prestamoCaso
    ? Object.keys(prestamoCaso).sort((a, b) => a.localeCompare(b))
    : []

  const pagosTotal = data?.pagos?.total ?? 0
  const pagosPerPage = data?.pagos?.per_page ?? 100

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90vh] max-w-[min(96rem,calc(100vw-2rem))] flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="shrink-0 border-b px-4 py-3 sm:px-6">
          <DialogTitle className="text-left text-lg text-[#1e3a5f]">
            Detalle del caso - préstamo, cuotas, préstamos y pagos
          </DialogTitle>
          <DialogDescription className="text-left text-sm">
            Cédula:{' '}
            <span className="font-semibold text-slate-800">
              {data?.cedula ?? '…'}
            </span>
            {data?.prestamo_id_finiquito != null && (
              <>
                {' '}
                · Préstamo caso:{' '}
                <span className="font-semibold text-slate-800">
                  #{data.prestamo_id_finiquito}
                </span>
              </>
            )}
            . Solo lectura.
          </DialogDescription>
        </DialogHeader>

        <div className="min-h-0 flex-1 overflow-hidden px-2 pb-3 pt-2 sm:px-4">
          {loading && (
            <div className="flex justify-center py-16">
              <Loader2 className="h-10 w-10 animate-spin text-slate-400" />
            </div>
          )}
          {!loading && error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
              {error}
            </div>
          )}
          {!loading && !error && data && (
            <Tabs
              value={tabRevision}
              onValueChange={setTabRevision}
              className="flex h-full min-h-0 flex-col"
            >
              <TabsList className="mb-2 flex h-auto w-full flex-wrap justify-start gap-1 sm:w-auto">
                <TabsTrigger value="prestamo-caso">
                  Préstamo (crédito)
                </TabsTrigger>
                <TabsTrigger value="cuotas">
                  Cuotas ({cuotasItems.length})
                </TabsTrigger>
                <TabsTrigger value="prestamos">
                  Préstamos cédula (
                  {data.prestamos?.total ?? prestamosItems.length})
                </TabsTrigger>
                <TabsTrigger value="pagos">
                  Pagos cédula ({data.pagos?.total ?? pagosItems.length})
                </TabsTrigger>
              </TabsList>

              <TabsContent
                value="prestamo-caso"
                className="mt-0 min-h-0 flex-1 overflow-auto rounded-md border border-slate-200 p-3 sm:p-4"
              >
                {!prestamoCaso ? (
                  <p className="text-sm text-slate-500">
                    No hay préstamo asociado a este caso.
                  </p>
                ) : (
                  <div className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
                    {prestamoCamposOrdenados.map(key => {
                      const raw = prestamoCaso[key]
                      const label = PRESTAMO_CAMPO_LABEL[key] ?? key
                      const isEstado = key === 'estado'
                      return (
                        <div
                          key={key}
                          className="flex flex-col border-b border-slate-100 pb-2 sm:border-0"
                        >
                          <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            {label}
                          </span>
                          {isEstado ? (
                            <Badge
                              className={`mt-1 w-fit border-0 ${estadoPrestamoBadgeClass(String(raw ?? ''))}`}
                            >
                              {estadoPrestamoLabel(String(raw ?? ''))}
                            </Badge>
                          ) : (
                            <span className="mt-0.5 break-words text-slate-900">
                              {formatearValorPrestamoCampo(key, raw)}
                            </span>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </TabsContent>

              <TabsContent
                value="cuotas"
                className="mt-0 min-h-0 flex-1 overflow-auto rounded-md border border-slate-200"
              >
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-50">
                      <TableHead className="whitespace-nowrap">Nº</TableHead>
                      <TableHead className="whitespace-nowrap">
                        Vencimiento
                      </TableHead>
                      <TableHead className="whitespace-nowrap">
                        Fecha pago
                      </TableHead>
                      <TableHead className="whitespace-nowrap">
                        Monto cuota
                      </TableHead>
                      <TableHead className="whitespace-nowrap">
                        Capital
                      </TableHead>
                      <TableHead className="whitespace-nowrap">
                        Interés
                      </TableHead>
                      <TableHead className="whitespace-nowrap">
                        Pagado cuota
                      </TableHead>
                      <TableHead className="whitespace-nowrap">
                        Saldo cap. final
                      </TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead className="whitespace-nowrap">Mora</TableHead>
                      <TableHead className="whitespace-nowrap">
                        Pago ID
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {cuotasItems.length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={11}
                          className="text-center text-slate-500"
                        >
                          Sin cuotas para el préstamo del caso.
                        </TableCell>
                      </TableRow>
                    ) : (
                      cuotasItems.map((c: Record<string, unknown>) => (
                        <TableRow key={`cu-${String(c.id)}`}>
                          <TableCell className="font-medium">
                            {String(c.numero_cuota ?? '')}
                          </TableCell>
                          <TableCell className="whitespace-nowrap text-sm">
                            {c.fecha_vencimiento
                              ? formatDate(String(c.fecha_vencimiento))
                              : '-'}
                          </TableCell>
                          <TableCell className="whitespace-nowrap text-sm">
                            {c.fecha_pago
                              ? formatDate(String(c.fecha_pago))
                              : '-'}
                          </TableCell>
                          <TableCell className="whitespace-nowrap text-sm">
                            {formatCurrency(Number(c.monto_cuota ?? 0))}
                          </TableCell>
                          <TableCell className="whitespace-nowrap text-sm">
                            {formatCurrency(Number(c.monto_capital ?? 0))}
                          </TableCell>
                          <TableCell className="whitespace-nowrap text-sm">
                            {formatCurrency(Number(c.monto_interes ?? 0))}
                          </TableCell>
                          <TableCell className="whitespace-nowrap text-sm">
                            {formatCurrency(Number(c.total_pagado ?? 0))}
                          </TableCell>
                          <TableCell className="whitespace-nowrap text-sm">
                            {formatCurrency(Number(c.saldo_capital_final ?? 0))}
                          </TableCell>
                          <TableCell className="text-sm">
                            {String(c.estado ?? '')}
                          </TableCell>
                          <TableCell className="text-sm">
                            {c.dias_mora != null
                              ? String(c.dias_mora)
                              : c.dias_morosidad != null
                                ? String(c.dias_morosidad)
                                : '-'}
                          </TableCell>
                          <TableCell className="font-mono text-xs">
                            {c.pago_id != null ? String(c.pago_id) : '-'}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TabsContent>

              <TabsContent
                value="prestamos"
                className="mt-0 min-h-0 flex-1 overflow-auto rounded-md border border-slate-200"
              >
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-50">
                      <TableHead>Cliente</TableHead>
                      <TableHead>Cédula</TableHead>
                      <TableHead>Monto</TableHead>
                      <TableHead>Modalidad</TableHead>
                      <TableHead>Cuotas</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead className="whitespace-nowrap">
                        Fecha aprob.
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {prestamosItems.length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={7}
                          className="text-center text-slate-500"
                        >
                          Sin préstamos para esta cédula (mismo criterio que
                          /prestamos).
                        </TableCell>
                      </TableRow>
                    ) : (
                      prestamosItems.map((p: Record<string, unknown>) => (
                        <TableRow key={`p-${String(p.id)}`}>
                          <TableCell className="font-medium">
                            {String(
                              p.nombres ??
                                p.nombre_cliente ??
                                `Cliente #${p.cliente_id ?? '-'}`
                            )}
                          </TableCell>
                          <TableCell>
                            {String(p.cedula ?? p.cedula_cliente ?? '-')}
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <DollarSign className="h-4 w-4 shrink-0 text-green-600" />
                              <span className="font-semibold text-green-700">
                                {formatCurrency(
                                  Number(p.total_financiamiento ?? 0)
                                )}
                              </span>
                            </div>
                          </TableCell>
                          <TableCell>
                            {modalidadLabel(p.modalidad_pago)}
                          </TableCell>
                          <TableCell>
                            {p.numero_cuotas != null
                              ? String(p.numero_cuotas)
                              : '-'}
                          </TableCell>
                          <TableCell>
                            <Badge
                              className={estadoPrestamoBadgeClass(
                                String(p.estado ?? '')
                              )}
                            >
                              {estadoPrestamoLabel(String(p.estado ?? ''))}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1 text-sm text-gray-600">
                              <Calendar className="h-4 w-4 shrink-0" />
                              {p.fecha_aprobacion
                                ? formatDate(String(p.fecha_aprobacion))
                                : '-'}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TabsContent>

              <TabsContent
                value="pagos"
                className="mt-0 flex min-h-0 flex-1 flex-col overflow-hidden rounded-md border border-slate-200"
              >
                <div className="min-h-0 flex-1 overflow-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-slate-50">
                        <TableHead>ID</TableHead>
                        <TableHead>Cédula</TableHead>
                        <TableHead>Crédito</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead className="max-w-[200px]">
                          Observaciones
                        </TableHead>
                        <TableHead>Monto</TableHead>
                        <TableHead>Fecha</TableHead>
                        <TableHead>Nº Doc.</TableHead>
                        <TableHead>Conciliado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {pagosItems.length === 0 ? (
                        <TableRow>
                          <TableCell
                            colSpan={9}
                            className="text-center text-slate-500"
                          >
                            Sin pagos registrados para esta cédula en la primera
                            página del listado.
                          </TableCell>
                        </TableRow>
                      ) : (
                        pagosItems.map((p: Record<string, unknown>) => (
                          <TableRow key={`pay-${String(p.id)}`}>
                            <TableCell className="font-mono text-xs">
                              {String(p.id ?? '')}
                            </TableCell>
                            <TableCell>
                              {String(p.cedula_cliente ?? '')}
                            </TableCell>
                            <TableCell>
                              {p.prestamo_id != null
                                ? String(p.prestamo_id)
                                : '-'}
                            </TableCell>
                            <TableCell>{String(p.estado ?? '')}</TableCell>
                            <TableCell
                              className="max-w-[200px] truncate text-sm"
                              title={String(p.notas ?? '')}
                            >
                              {p.notas != null && String(p.notas).trim() !== ''
                                ? String(p.notas)
                                : '-'}
                            </TableCell>
                            <TableCell>
                              {formatCurrency(Number(p.monto_pagado ?? 0))}
                            </TableCell>
                            <TableCell>
                              {p.fecha_pago
                                ? formatDate(String(p.fecha_pago))
                                : '-'}
                            </TableCell>
                            <TableCell className="text-sm">
                              {String(p.numero_documento ?? '')}
                            </TableCell>
                            <TableCell>{p.conciliado ? 'Sí' : 'No'}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
                {pagosTotal > pagosPerPage && (
                  <p className="shrink-0 border-t bg-slate-50 px-3 py-2 text-xs text-slate-600">
                    Hay {pagosTotal} pagos en total para esta cédula; aquí se
                    muestran hasta {pagosPerPage} (primera página). Para el
                    histórico completo use el módulo Pagos en el sistema
                    interno.
                  </p>
                )}
              </TabsContent>
            </Tabs>
          )}
        </div>

        <div className="flex shrink-0 justify-end border-t px-4 py-3 sm:px-6">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cerrar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
