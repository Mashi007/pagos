import { useCallback, useEffect, useState } from 'react'

import { Loader2, Pencil, RefreshCw, Trash2, Wrench } from 'lucide-react'

import { toast } from 'sonner'

import { Link } from 'react-router-dom'

import { auditoriaService, type RevisionDescuadrePagosCuotasResponse } from '../../services/auditoriaService'

import { pagoService } from '../../services/pagoService'

import { prestamoService } from '../../services/prestamoService'

import { Badge } from '../ui/badge'

import { Button } from '../ui/button'

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
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/80 px-4 py-3">
      <span className="text-sm font-medium text-slate-700">Cuadre motor</span>
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
      <div className="text-sm text-slate-600">
        {verde ? (
          <span className="font-medium text-emerald-800">Verde — auditado en cuadre (motor)</span>
        ) : amarillo ? (
          <span className="font-medium text-amber-900">
            Amarillo — totales dentro de tolerancia; revise fecha de liquidacion u otros controles
          </span>
        ) : (
          <span className="font-medium text-red-800">
            Rojo — descuadre o pagos operativos con saldo sin aplicar (&gt; 0,02 USD)
          </span>
        )}
      </div>
    </div>
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

  const [editEstado, setEditEstado] = useState('')

  const [editDoc, setEditDoc] = useState('')

  const [editConciliado, setEditConciliado] = useState(false)

  const [editGuardando, setEditGuardando] = useState(false)

  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null)

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

      setEditEstado(row.estado || '')

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
        estado: editEstado || undefined,
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
    editEstado,
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
        <DialogContent className="max-h-[min(92vh,900px)] max-w-5xl overflow-hidden overflow-y-auto">
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
              <SemaforoCuadre semaforo={data.semaforo_cuadre} />

              <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-md border bg-white p-3 shadow-sm">
                  <div className="text-xs text-slate-500">Suma pagos operativos (USD)</div>
                  <div className="font-mono text-lg tabular-nums">{data.sum_pagos_operativos_usd}</div>
                </div>
                <div className="rounded-md border bg-white p-3 shadow-sm">
                  <div className="text-xs text-slate-500">Aplicado a cuotas (USD)</div>
                  <div className="font-mono text-lg tabular-nums">{data.sum_aplicado_cuotas_usd}</div>
                </div>
                <div className="rounded-md border bg-white p-3 shadow-sm">
                  <div className="text-xs text-slate-500">Diferencia (USD)</div>
                  <div className="font-mono text-lg tabular-nums text-orange-700">{data.diff_usd}</div>
                </div>
                <div className="rounded-md border bg-white p-3 shadow-sm">
                  <div className="text-xs text-slate-500">Estado / fecha liquidacion</div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="secondary">{data.estado_prestamo}</Badge>
                    <span className="font-mono text-xs text-slate-600">
                      {data.fecha_liquidado || '—'}
                    </span>
                  </div>
                </div>
              </div>

              {!esAdmin ? (
                <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                  Modo lectura: solo administradores pueden editar, eliminar o aplicar cuotas desde esta
                  herramienta.
                </p>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={!esAdmin || cascadaBusy || prestamoId == null}
                  onClick={() => void reaplicarCascada()}
                >
                  {cascadaBusy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                  Reaplicar cascada (todo el prestamo)
                </Button>
                <Button type="button" variant="outline" disabled={cargando} onClick={() => void cargar()}>
                  Recargar datos
                </Button>
              </div>

              <div>
                <h3 className="mb-2 text-sm font-semibold text-slate-800">Pagos del prestamo</h3>
                <div className="max-h-[38vh] overflow-auto rounded-md border">
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
                                    <Pencil className="h-3 w-3" />
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
              </div>

              <div>
                <h3 className="mb-2 text-sm font-semibold text-slate-800">Cuotas</h3>
                <div className="max-h-[28vh] overflow-auto rounded-md border">
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
              </div>
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
              <Label htmlFor="aud-desc-estado">Estado (texto en BD)</Label>
              <Input
                id="aud-desc-estado"
                value={editEstado}
                onChange={e => setEditEstado(e.target.value)}
                placeholder="Ej. ACTIVO, ANULADO_IMPORT..."
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
