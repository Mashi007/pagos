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
  finiquitoRevisionDatos,
  type FiniquitoRevisionDatosResponse,
} from '../../services/finiquitoService'

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
  if (e === 'EN_REVISION') return 'bg-yellow-100 text-yellow-800'
  if (e === 'RECHAZADO') return 'bg-red-100 text-red-800'
  if (e === 'EVALUADO') return 'bg-blue-100 text-blue-800'
  return 'bg-gray-100 text-gray-800'
}

function estadoPrestamoLabel(estado: string): string {
  const e = (estado || '').toUpperCase()
  if (e === 'APROBADO') return 'Aprobado'
  if (e === 'EN_REVISION') return 'En Revisión'
  if (e === 'RECHAZADO') return 'Rechazado'
  if (e === 'EVALUADO') return 'Evaluado'
  if (e === 'DRAFT') return 'Borrador'
  return estado || '-'
}

type Props = {
  open: boolean
  casoId: number | null
  onOpenChange: (open: boolean) => void
}

/**
 * Vista de revision: mismos listados que /prestamos y /pagos filtrados por cedula del caso
 * (API GET /finiquito/public/revision-datos/:caso_id).
 */
export function FiniquitoRevisionDialog({ open, casoId, onOpenChange }: Props) {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<FiniquitoRevisionDatosResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tabRevision, setTabRevision] = useState('prestamos')

  useEffect(() => {
    if (!open || casoId == null) {
      setData(null)
      setError(null)
      setTabRevision('prestamos')
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    finiquitoRevisionDatos(casoId)
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
  }, [open, casoId])

  const prestamosItems = data?.prestamos?.prestamos ?? []
  const pagosItems = data?.pagos?.pagos ?? []

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90vh] max-w-[min(96rem,calc(100vw-2rem))] flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="shrink-0 border-b px-4 py-3 sm:px-6">
          <DialogTitle className="text-left text-lg text-[#1e3a5f]">
            Revision de caso - misma informacion que Préstamos y Pagos
          </DialogTitle>
          <DialogDescription className="text-left text-sm">
            Cédula:{' '}
            <span className="font-semibold text-slate-800">
              {data?.cedula ?? '…'}
            </span>
            . Listados alineados con las pantallas internas del sistema (solo
            lectura).
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
              <TabsList className="mb-2 w-full justify-start sm:w-auto">
                <TabsTrigger value="prestamos">
                  Préstamos ({data.prestamos?.total ?? prestamosItems.length})
                </TabsTrigger>
                <TabsTrigger value="pagos">
                  Pagos ({data.pagos?.total ?? pagosItems.length})
                </TabsTrigger>
              </TabsList>

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
                className="mt-0 min-h-0 flex-1 overflow-auto rounded-md border border-slate-200"
              >
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
                          Sin pagos conciliados para esta cédula (mismo filtro
                          por defecto que /pagos: conciliado = sí).
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
