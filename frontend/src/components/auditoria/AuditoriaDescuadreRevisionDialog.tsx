import { useCallback, useEffect, useState, type ReactNode } from 'react'

import { ChevronRight, Edit, Loader2, RefreshCw, Trash2, Wrench } from 'lucide-react'

import { toast } from 'sonner'

import { Link } from 'react-router-dom'

import { auditoriaService, type RevisionDescuadrePagosCuotasResponse } from '../../services/auditoriaService'

import { pagoService } from '../../services/pagoService'

import { prestamoService } from '../../services/prestamoService'

import { Badge } from '../ui/badge'

import { Button } from '../ui/button'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'

import { Input } from '../ui/input'

import { Label } from '../ui/label'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table'

type Props = {
  open: boolean

  onOpenChange: (open: boolean) => void

  prestamoId: number | null

  esAdmin: boolean

  onRefreshLista?: () => void
}

function parseUsd(s: string): number {
  const n = Number(String(s).replace(',', '.'))
  return Number.isFinite(n) ? n : 0
}

function SemaforoCuadre({ semaforo }: { semaforo: string }) {
  const s = (semaforo || '').toLowerCase()
  const verde = s === 'verde'
  const amarillo = s === 'amarillo'
  const rojo = s === 'rojo' || (!verde && !amarillo)
  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Semaforo</span>
      <div className="flex items-center gap-2" title="Semaforo de cuadre contable">
        <span
          className={`h-4 w-4 rounded-full border-2 shadow-sm ${
            rojo ? 'border-red-700 bg-red-500' : 'border-slate-300 bg-slate-200'
          }`}
          aria-label="Rojo: descuadre o aplicaciones pendientes"
        />
        <span
          className={`h-4 w-4 rounded-full border-2 shadow-sm ${
            amarillo ? 'border-amber-600 bg-amber-400' : 'border-slate-300 bg-slate-200'
          }`}
          aria-label="Amarillo: montos cuadran pero falta cierre administrativo"
        />
        <span
          className={`h-4 w-4 rounded-full border-2 shadow-sm ${
            verde ? 'border-emerald-700 bg-emerald-500' : 'border-slate-300 bg-slate-200'
          }`}
          aria-label="Verde: cuadre y aplicaciones dentro de tolerancia"
        />
      </div>
      <div className="text-sm text-slate-700">
        {verde ? (
          <span className="font-medium text-emerald-800">Verde — cuadre motor OK</span>
        ) : amarillo ? (
          <span className="font-medium text-amber-900">
            Amarillo — numeros OK; falta fecha liquidacion u otro cierre admin
          </span>
        ) : (
          <span className="font-medium text-red-800">
            Rojo — descuadre o saldo sin aplicar &gt; 0,02 USD en pago operativo
          </span>
        )}
      </div>
    </div>
  )
}

type SeccionId = 'pagos' | 'cuotas'

function TarjetaExpandibleBd({
  id,
  titulo,
  descripcion,
  resumenColapsado,
  expandido,
  onToggle,
  ninos,
}: {
  id: SeccionId
  titulo: string
  descripcion: string
  resumenColapsado: ReactNode
  expandido: boolean
  onToggle: () => void
  ninos: ReactNode
}) {
  return (
    <Card className="overflow-hidden border-slate-200 shadow-sm">
      <button
        type="button"
        className="flex w-full items-start gap-3 p-4 text-left transition-colors hover:bg-slate-50/90"
        onClick={onToggle}
        aria-expanded={expandido}
        aria-controls={`bd-seccion-${id}`}
      >
        <ChevronRight
          className={`mt-0.5 h-5 w-5 shrink-0 text-slate-500 transition-transform ${
            expandido ? 'rotate-90' : ''
          }`}
        />
        <div className="min-w-0 flex-1 space-y-1">
          <CardTitle className="text-base leading-snug">{titulo}</CardTitle>
          <CardDescription className="text-xs leading-relaxed">{descripcion}</CardDescription>
          {!expandido ? (
            <div className="rounded-md border border-dashed border-slate-200 bg-white/80 px-3 py-2 text-sm text-slate-800">
              {resumenColapsado}
            </div>
          ) : null}
        </div>
      </button>
      {expandido ? (
        <CardContent id={`bd-seccion-${id}`} className="border-t border-slate-100 px-4 pb-4 pt-0">
          {ninos}
        </CardContent>
      ) : null}
    </Card>
  )
}

export function AuditoriaDescuadreRevisionDialog({
  open,
  onOpenChange,
  prestamoId,
  esAdmin,
  onRefreshLista,
}: Props) {
  const [cargando, setCargando] = useState(false)

  const [data, setData] = useState<RevisionDescuadrePagosCuotasResponse | null>(null)

  const [cascadaBusy, setCascadaBusy] = useState(false)

  const [aplicarBusy, setAplicarBusy] = useState<number | null>(null)

  const [deleteBusy, setDeleteBusy] = useState<number | null>(null)

  const [editOpen, setEditOpen] = useState(false)

  const [editPagoId, setEditPagoId] = useState<number | null>(null)

  const [editMonto, setEditMonto] = useState('')

  const [editDoc, setEditDoc] = useState('')

  const [editConciliado, setEditConciliado] = useState(false)

  const [editGuardando, setEditGuardando] = useState(false)

  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null)

  const [expPagos, setExpPagos] = useState(false)

  const [expCuotas, setExpCuotas] = useState(false)

  const cargar = useCallback(async () => {
    if (prestamoId == null || !open) return
    setCargando(true)
    try {
      const r = await auditoriaService.obtenerRevisionDescuadrePagosCuotas(prestamoId)
      setData(r)
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (e as Error)?.message ||
        'No se pudo cargar la revision'
      toast.error(String(msg))
      setData(null)
    } finally {
      setCargando(false)
    }
  }, [open, prestamoId])

  useEffect(() => {
    void cargar()
  }, [cargar])

  const cerrarTodo = useCallback(() => {
    setEditOpen(false)

    setEditPagoId(null)

    setPendingDeleteId(null)

    onOpenChange(false)
  }, [onOpenChange])

  const reaplicarCascada = useCallback(async () => {
    if (prestamoId == null || !esAdmin) return
    setCascadaBusy(true)
    try {
      await prestamoService.reaplicarCascadaAplicacion(prestamoId)
      toast.success(`Cascada reaplicada en prestamo ${prestamoId}`)
      onRefreshLista?.()
      await cargar()
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (e as Error)?.message ||
        'Error al reaplicar cascada'
      toast.error(String(msg))
    } finally {
      setCascadaBusy(false)
    }
  }, [prestamoId, esAdmin, onRefreshLista, cargar])

  const aplicarCuotasPago = useCallback(
    async (pagoId: number) => {
      if (!esAdmin) return
      setAplicarBusy(pagoId)
      try {
        const out = await pagoService.aplicarPagoACuotas(pagoId)
        toast.success(out.message || 'Aplicacion a cuotas ejecutada')
        onRefreshLista?.()
        await cargar()
      } catch (e: unknown) {
        const msg =
          (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          (e as Error)?.message ||
          'Error al aplicar a cuotas'
        toast.error(String(msg))
      } finally {
        setAplicarBusy(null)
      }
    },
    [esAdmin, onRefreshLista, cargar]
  )

  const eliminarPago = useCallback(
    async (pagoId: number) => {
      if (!esAdmin) return
      setDeleteBusy(pagoId)
      try {
        await pagoService.deletePago(pagoId)
        toast.success(`Pago ${pagoId} eliminado`)
        setPendingDeleteId(null)
        onRefreshLista?.()
        await cargar()
      } catch (e: unknown) {
        const msg =
          (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          (e as Error)?.message ||
          'Error al eliminar pago'
        toast.error(String(msg))
      } finally {
        setDeleteBusy(null)
      }
    },
    [esAdmin, onRefreshLista, cargar]
  )

  const abrirEditar = useCallback(
    (row: RevisionDescuadrePagosCuotasResponse['pagos'][number]) => {
      setEditPagoId(row.pago_id)

      setEditMonto(String(parseUsd(row.monto_pagado)))

      setEditDoc(row.numero_documento || '')

      setEditConciliado(!!row.conciliado)

      setEditOpen(true)
    },
    []
  )

  const guardarEdicion = useCallback(async () => {
    if (!esAdmin || editPagoId == null) return
    const m = Number(editMonto.replace(',', '.'))
    if (!Number.isFinite(m)) {
      toast.error('Monto invalido')
      return
    }
    setEditGuardando(true)
    try {
      await pagoService.updatePago(editPagoId, {
        monto_pagado: m,
        numero_documento: editDoc,
        conciliado: editConciliado,
      })
      toast.success('Pago actualizado')
      setEditOpen(false)

      setEditPagoId(null)

      onRefreshLista?.()

      await cargar()
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (e as Error)?.message ||
        'Error al guardar'
      toast.error(String(msg))
    } finally {
      setEditGuardando(false)
    }
  }, [
    esAdmin,
    editPagoId,
    editMonto,
    editDoc,
    editConciliado,
    onRefreshLista,
    cargar,
  ])

  const titulo =
    prestamoId != null
      ? `Revision cuadre pagos vs cuotas · Prestamo #${prestamoId}`
      : 'Revision cuadre pagos vs cuotas'

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[min(94vh,920px)] max-w-6xl overflow-hidden overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex flex-wrap items-center gap-2">
              <Wrench className="h-5 w-5 text-slate-600" />
              {titulo}
            </DialogTitle>
          </DialogHeader>

          {prestamoId != null ? (
            <p className="text-sm text-slate-600">
              <Link className="text-blue-600 underline" to={`/prestamos?prestamo_id=${prestamoId}`}>
                Abrir ficha del prestamo
              </Link>
              {' · '}
              <Link className="text-blue-600 underline" to="/pagos/pagos">
                Ir a modulo Pagos
              </Link>
            </p>
          ) : null}

          {cargando && !data ? (
            <div className="flex items-center gap-2 py-10 text-slate-600">
              <Loader2 className="h-5 w-5 animate-spin" />
              Cargando datos...
            </div>
          ) : data ? (
            <div className="space-y-4">
              <div className="grid gap-4 lg:grid-cols-3">
                <Card className="border-slate-200 shadow-sm">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base">Prestamo (BD)</CardTitle>
                    <CardDescription>Identidad y estructura del credito en base de datos</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <div>
                      <span className="text-xs text-slate-500">Titular</span>
                      <p className="font-medium text-slate-900">{data.prestamo_nombres || '—'}</p>
                      <p className="font-mono text-xs text-slate-600">{data.prestamo_cedula || '—'}</p>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="rounded-md bg-slate-50 p-2">
                        <div className="text-[10px] uppercase text-slate-500">Financiamiento</div>
                        <div className="font-mono text-sm tabular-nums">
                          {data.total_financiamiento_usd ?? '—'} USD
                        </div>
                      </div>
                      <div className="rounded-md bg-slate-50 p-2">
                        <div className="text-[10px] uppercase text-slate-500">Cuotas config.</div>
                        <div className="font-mono text-sm tabular-nums">{data.numero_cuotas_config ?? '—'}</div>
                      </div>
                      <div className="rounded-md bg-slate-50 p-2">
                        <div className="text-[10px] uppercase text-slate-500">Suma monto cuotas</div>
                        <div className="font-mono text-sm tabular-nums">{data.sum_monto_cuotas_usd ?? '—'}</div>
                      </div>
                      <div className="rounded-md bg-slate-50 p-2">
                        <div className="text-[10px] uppercase text-slate-500">Suma total_pagado (col.)</div>
                        <div className="font-mono text-sm tabular-nums">
                          {data.sum_total_pagado_column_cuotas_usd ?? '—'}
                        </div>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-2">
                      <Badge variant="secondary">{data.estado_prestamo}</Badge>
                      <span className="text-xs text-slate-600">
                        Liquidado:{' '}
                        <span className="font-mono">{data.fecha_liquidado || 'sin fecha'}</span>
                      </span>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-slate-200 shadow-sm lg:col-span-2">
                  <CardHeader className="space-y-3 pb-2">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <CardTitle className="text-base">Cuadre motor (BD)</CardTitle>
                        <CardDescription>
                          Pagos operativos (excl. anulados/reversados/duplicados declarados) frente a suma de{' '}
                          <code className="rounded bg-slate-100 px-1 text-[10px]">cuota_pagos</code> vía pagos
                          operativos
                        </CardDescription>
                      </div>
                      <SemaforoCuadre semaforo={data.semaforo_cuadre} />
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                      <div className="rounded-lg border border-slate-200 bg-gradient-to-br from-white to-slate-50/80 p-3">
                        <div className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
                          Pagos operativos
                        </div>
                        <div className="font-mono text-xl tabular-nums text-slate-900">
                          {data.sum_pagos_operativos_usd}
                        </div>
                        <div className="mt-1 text-[11px] text-slate-500">USD · misma regla que auditoria cartera</div>
                      </div>
                      <div className="rounded-lg border border-slate-200 bg-gradient-to-br from-white to-slate-50/80 p-3">
                        <div className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
                          Aplicado cuotas
                        </div>
                        <div className="font-mono text-xl tabular-nums text-slate-900">
                          {data.sum_aplicado_cuotas_usd}
                        </div>
                        <div className="mt-1 text-[11px] text-slate-500">USD · desde cuota_pagos</div>
                      </div>
                      <div className="rounded-lg border border-orange-200 bg-orange-50/60 p-3">
                        <div className="text-[10px] font-medium uppercase tracking-wide text-orange-900">
                          Diferencia
                        </div>
                        <div className="font-mono text-xl tabular-nums text-orange-900">{data.diff_usd}</div>
                        <div className="mt-1 text-[11px] text-orange-800/90">
                          Tol. {data.tolerancia_usd} USD · si mayor, revisar BS/USD, duplicados o aplicacion
                        </div>
                      </div>
                      <div className="rounded-lg border border-slate-200 bg-white p-3">
                        <div className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
                          Conteos BD
                        </div>
                        <ul className="mt-1 space-y-1 text-[11px] leading-snug text-slate-700">
                          <li>
                            Pagos en prestamo: <strong>{data.n_pagos_en_bd ?? data.pagos.length}</strong>
                          </li>
                          <li>
                            Operativos cartera: <strong>{data.n_pagos_operativos_cartera ?? '—'}</strong>
                          </li>
                          <li>
                            Operativos saldo &gt; tol:{' '}
                            <strong className="text-orange-800">
                              {data.n_pagos_operativos_saldo_fuera_tol ?? '—'}
                            </strong>
                          </li>
                          <li>
                            Cuotas en BD: <strong>{data.n_cuotas_en_bd ?? data.cuotas.length}</strong>
                          </li>
                        </ul>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Criterios para decidir</CardTitle>
                  <CardDescription>Resumen calculado con los mismos datos que la tabla expandible</CardDescription>
                </CardHeader>
                <CardContent className="grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
                  <p className="rounded-md border border-slate-100 bg-slate-50/80 p-3">
                    Si <strong>diferencia</strong> es alta y <strong>suma total_pagado en cuotas</strong> se aleja del
                    aplicado vía <code className="text-xs">cuota_pagos</code>, priorice revisar filas de pago (BS mal
                    como USD, duplicados, estados no excluidos).
                  </p>
                  <p className="rounded-md border border-slate-100 bg-slate-50/80 p-3">
                    Si <strong>financiamiento</strong> y <strong>suma monto cuotas</strong> no alinean, el problema
                    puede estar en la tabla <code className="text-xs">cuotas</code> o en configuracion del prestamo,
                    no solo en pagos.
                  </p>
                </CardContent>
              </Card>

              {!esAdmin ? (
                <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                  Modo lectura: solo administradores pueden editar, eliminar o aplicar cuotas desde esta
                  herramienta.
                </p>
              ) : null}

              <Card className="border-slate-200 shadow-sm">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Herramientas</CardTitle>
                  <CardDescription>Acciones sobre el prestamo completo o recarga desde BD</CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={!esAdmin || cascadaBusy || prestamoId == null}
                    onClick={() => void reaplicarCascada()}
                  >
                    {cascadaBusy ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="mr-2 h-4 w-4" />
                    )}
                    Reaplicar cascada (todo el prestamo)
                  </Button>
                  <Button type="button" variant="outline" disabled={cargando} onClick={() => void cargar()}>
                    Recargar desde BD
                  </Button>
                </CardContent>
              </Card>

              <TarjetaExpandibleBd
                id="pagos"
                titulo="Pagos del prestamo (tabla completa)"
                descripcion="Cada fila es un registro en pagos; montos y aplicacion vienen de la BD. Pulse la tarjeta para ampliar."
                expandido={expPagos}
                onToggle={() => setExpPagos(v => !v)}
                resumenColapsado={
                  <span>
                    <strong>{data.pagos.length}</strong> filas en BD ·{' '}
                    <strong>{data.n_pagos_operativos_cartera ?? '—'}</strong> cuentan como operativos cartera ·{' '}
                    <strong className="text-orange-800">
                      {data.n_pagos_operativos_saldo_fuera_tol ?? '—'}
                    </strong>{' '}
                    con saldo sin aplicar &gt; tolerancia
                  </span>
                }
                ninos={
                  <div className="max-h-[min(52vh,520px)] overflow-auto rounded-md border border-slate-200">
                    <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[72px]">ID</TableHead>
                        <TableHead>Op.</TableHead>
                        <TableHead>Fecha</TableHead>
                        <TableHead className="text-right">Monto</TableHead>
                        <TableHead className="text-right">Aplicado</TableHead>
                        <TableHead className="text-right">Saldo</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead>Documento</TableHead>
                        <TableHead className="text-right">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.pagos.map(p => (
                        <TableRow key={p.pago_id}>
                          <TableCell className="font-mono text-xs">{p.pago_id}</TableCell>
                          <TableCell>
                            {p.cuenta_operativo_cartera ? (
                              <Badge className="bg-emerald-700">Si</Badge>
                            ) : (
                              <Badge variant="outline">No</Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-xs">{p.fecha_pago ?? '—'}</TableCell>
                          <TableCell className="text-right font-mono text-xs">{p.monto_pagado}</TableCell>
                          <TableCell className="text-right font-mono text-xs">{p.sum_aplicado_cuotas}</TableCell>
                          <TableCell className="text-right font-mono text-xs">{p.saldo_sin_aplicar_usd}</TableCell>
                          <TableCell className="max-w-[100px] truncate text-xs" title={p.estado}>
                            {p.estado || '—'}
                          </TableCell>
                          <TableCell className="max-w-[160px] truncate text-xs" title={p.numero_documento}>
                            {p.numero_documento || '—'}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex flex-col items-end gap-1">
                              {esAdmin ? (
                                <>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="outline"
                                    className="h-7 gap-1 px-2"
                                    onClick={() => abrirEditar(p)}
                                  >
                                    <Edit className="h-3 w-3" />
                                    Editar
                                  </Button>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant="secondary"
                                    className="h-7 px-2"
                                    disabled={
                                      aplicarBusy === p.pago_id ||
                                      !p.cuenta_operativo_cartera ||
                                      parseUsd(p.monto_pagado) <= 0
                                    }
                                    onClick={() => void aplicarCuotasPago(p.pago_id)}
                                  >
                                    {aplicarBusy === p.pago_id ? (
                                      <Loader2 className="h-3 w-3 animate-spin" />
                                    ) : (
                                      'Aplicar cuotas'
                                    )}
                                  </Button>
                                  {pendingDeleteId === p.pago_id ? (
                                    <div className="flex gap-1">
                                      <Button
                                        type="button"
                                        size="sm"
                                        variant="destructive"
                                        className="h-7 px-2 text-xs"
                                        disabled={deleteBusy === p.pago_id}
                                        onClick={() => void eliminarPago(p.pago_id)}
                                      >
                                        {deleteBusy === p.pago_id ? (
                                          <Loader2 className="h-3 w-3 animate-spin" />
                                        ) : (
                                          'Confirmar'
                                        )}
                                      </Button>
                                      <Button
                                        type="button"
                                        size="sm"
                                        variant="ghost"
                                        className="h-7 px-2 text-xs"
                                        onClick={() => setPendingDeleteId(null)}
                                      >
                                        Cancelar
                                      </Button>
                                    </div>
                                  ) : (
                                    <Button
                                      type="button"
                                      size="sm"
                                      variant="ghost"
                                      className="h-7 gap-1 px-2 text-red-700 hover:bg-red-50"
                                      onClick={() => setPendingDeleteId(p.pago_id)}
                                    >
                                      <Trash2 className="h-3 w-3" />
                                      Eliminar
                                    </Button>
                                  )}
                                </>
                              ) : (
                                <span className="text-xs text-slate-400">—</span>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  </div>
                }
              />

              <TarjetaExpandibleBd
                id="cuotas"
                titulo="Cuotas del prestamo (tabla completa)"
                descripcion="Filas de cuotas en BD: monto_cuota, total_pagado acumulado en columna y estado. Ampliar para revisar contra pagos."
                expandido={expCuotas}
                onToggle={() => setExpCuotas(v => !v)}
                resumenColapsado={
                  <span>
                    <strong>{data.cuotas.length}</strong> cuotas en BD · suma montos{' '}
                    <span className="font-mono">{data.sum_monto_cuotas_usd ?? '—'}</span> · suma total_pagado (col.){' '}
                    <span className="font-mono">{data.sum_total_pagado_column_cuotas_usd ?? '—'}</span>
                  </span>
                }
                ninos={
                  <div className="max-h-[min(44vh,440px)] overflow-auto rounded-md border border-slate-200">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[72px]">Cuota</TableHead>
                          <TableHead className="w-[72px]">Nº</TableHead>
                          <TableHead className="text-right">Monto</TableHead>
                          <TableHead className="text-right">Total pagado</TableHead>
                          <TableHead>Estado</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {data.cuotas.map(c => (
                          <TableRow key={c.cuota_id}>
                            <TableCell className="font-mono text-xs">{c.cuota_id}</TableCell>
                            <TableCell className="text-xs">{c.numero_cuota}</TableCell>
                            <TableCell className="text-right font-mono text-xs">{c.monto_cuota}</TableCell>
                            <TableCell className="text-right font-mono text-xs">{c.total_pagado}</TableCell>
                            <TableCell className="text-xs">{c.estado}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                }
              />
            </div>
          ) : (
            <p className="py-6 text-sm text-slate-600">Sin datos.</p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => cerrarTodo()}>
              Cerrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Editar pago #{editPagoId}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 py-2">
            <div>
              <Label htmlFor="aud-desc-monto">Monto pagado (USD)</Label>
              <Input
                id="aud-desc-monto"
                value={editMonto}
                onChange={e => setEditMonto(e.target.value)}
                inputMode="decimal"
              />
            </div>
            <div>
              <Label htmlFor="aud-desc-doc">Numero documento</Label>
              <Input id="aud-desc-doc" value={editDoc} onChange={e => setEditDoc(e.target.value)} />
            </div>
            <div className="flex items-center gap-2">
              <input
                id="aud-desc-conc"
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300"
                checked={editConciliado}
                onChange={e => setEditConciliado(e.target.checked)}
              />
              <Label htmlFor="aud-desc-conc" className="cursor-pointer text-sm font-normal">
                Conciliado
              </Label>
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button type="button" variant="outline" onClick={() => setEditOpen(false)}>
              Cancelar
            </Button>
            <Button type="button" disabled={editGuardando} onClick={() => void guardarEdicion()}>
              {editGuardando ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
