import { useCallback, useEffect, useMemo, useState } from 'react'

import { Check, Loader2, RefreshCw } from 'lucide-react'

import { Button } from '../ui/button'

import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

import { Input } from '../ui/input'

import { Label } from '../ui/label'

import { Badge } from '../ui/badge'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'

import {
  auditoriaService,
  PrestamoCarteraChequeo,
} from '../../services/auditoriaService'

import { useSimpleAuth } from '../../store/simpleAuthStore'

import { toast } from 'sonner'

import { Link } from 'react-router-dom'

import {
  AUDITORIA_CARTERA_CONTROLES_CATALOGO,
  numeroControlAuditoriaCartera,
} from './auditoriaCarteraControlesCatalogo'

function controlDismissKey(prestamoId: number, codigo: string) {
  return `${prestamoId}:${codigo}`
}

function normalizarCedulaBusqueda(valor: string) {
  return valor.trim().toUpperCase().replace(/\s+/g, '')
}

const COD_DESAJUSTE_PAGOS = 'total_pagado_vs_aplicado_cuotas'

export function AuditoriaCarteraTab() {
  const { user } = useSimpleAuth()

  const esAdmin = (user?.rol || 'operativo') === 'administrador'

  const [loading, setLoading] = useState(true)

  const [running, setRunning] = useState(false)

  const [corrigiendo, setCorrigiendo] = useState(false)

  const [items, setItems] = useState<PrestamoCarteraChequeo[]>([])

  const [resumen, setResumen] = useState<Record<string, unknown> | null>(null)

  /** Controles ocultados con OK en esta sesion; se limpia al Recargar / Ejecutar auditoria. */
  const [dismissed, setDismissed] = useState<Record<string, true>>({})

  const [cedulaFiltro, setCedulaFiltro] = useState('')

  /** '' = todos los controles; si no, solo prestamos con alerta SI en ese codigo. */
  const [filtroControlCodigo, setFiltroControlCodigo] = useState('')

  const cargar = useCallback(async () => {
    try {
      setLoading(true)

      const cheq = await auditoriaService.listarCarteraChequeos()

      setItems(cheq.items || [])

      setResumen((cheq.resumen as Record<string, unknown>) || {})

      setDismissed({})

      setCedulaFiltro('')

      setFiltroControlCodigo('')
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al cargar auditoria de cartera'

      toast.error(msg)

      setItems([])

      setResumen(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    cargar()
  }, [cargar])

  const ejecutarAhora = async () => {
    try {
      setRunning(true)

      const cheq = await auditoriaService.ejecutarCartera()

      setItems(cheq.items || [])

      setResumen((cheq.resumen as Record<string, unknown>) || {})

      setDismissed({})

      setCedulaFiltro('')

      setFiltroControlCodigo('')

      const s = cheq.sincronizar_estado_cuotas
      const extra =
        s && typeof s.estados_actualizados === 'number'
          ? ` Estados de cuota alineados: ${s.estados_actualizados} fila(s).`
          : ''
      toast.success(`Auditoria ejecutada y metadatos actualizados.${extra}`)
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al ejecutar auditoria'

      toast.error(msg)
    } finally {
      setRunning(false)
    }
  }

  const visibleRows = useMemo(() => {
    return items
      .map(row => ({
        ...row,
        controles: row.controles.filter(
          c => !dismissed[controlDismissKey(row.prestamo_id, c.codigo)]
        ),
      }))
      .filter(row => row.controles.length > 0)
  }, [items, dismissed])

  const cedulaFiltroNorm = normalizarCedulaBusqueda(cedulaFiltro)

  const conteosPorControlCodigo = useMemo(() => {
    const m: Record<string, number> = {}
    for (const row of visibleRows) {
      for (const c of row.controles) {
        const k = c.codigo
        m[k] = (m[k] || 0) + 1
      }
    }
    return m
  }, [visibleRows])

  const filasTrasCedula = useMemo(() => {
    if (!cedulaFiltroNorm) return visibleRows
    return visibleRows.filter(row => {
      const c = normalizarCedulaBusqueda(row.cedula || '')
      return c.includes(cedulaFiltroNorm)
    })
  }, [visibleRows, cedulaFiltroNorm])

  const displayRows = useMemo(() => {
    if (!filtroControlCodigo) return filasTrasCedula
    return filasTrasCedula
      .filter(row => row.controles.some(c => c.codigo === filtroControlCodigo))
      .map(row => ({
        ...row,
        controles: row.controles.filter(c => c.codigo === filtroControlCodigo),
      }))
  }, [filasTrasCedula, filtroControlCodigo])

  const marcarControlOk = (prestamoId: number, codigo: string) => {
    const k = controlDismissKey(prestamoId, codigo)
    setDismissed(prev => ({ ...prev, [k]: true }))
  }

  const hayAlertas = items.length > 0

  const hayDesajustePagosVsAplicado = useMemo(() => {
    return items.some(row =>
      row.controles.some(c => c.codigo === COD_DESAJUSTE_PAGOS)
    )
  }, [items])

  const corregirDesajustePagos = async () => {
    try {
      setCorrigiendo(true)
      const res = await auditoriaService.corregirCartera({
        sincronizar_estados: true,
        reaplicar_cascada_desajuste_pagos: true,
        max_reaplicaciones: 100,
      })
      setItems(res.items || [])
      setResumen((res.resumen as Record<string, unknown>) || {})
      setDismissed({})
      setCedulaFiltro('')
      setFiltroControlCodigo('')
      const ok = (res.reaplicar_cascada || []).filter(
        (x: Record<string, unknown>) => x.ok === true
      ).length
      const fail = (res.reaplicar_cascada || []).length - ok
      const sync = res.sincronizar_estado_cuotas
      toast.success(
        `Correccion: cascada ${ok} prestamo(s) OK${fail ? `, ${fail} con error` : ''}.` +
          (sync && typeof sync.estados_actualizados === 'number'
            ? ` Estados sincronizados: ${sync.estados_actualizados}.`
            : '')
      )
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al corregir cartera'
      toast.error(msg)
    } finally {
      setCorrigiendo(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="outline"
          size="sm"
          onClick={() => cargar()}
          disabled={loading}
        >
          {loading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Recargar
        </Button>

        <Button size="sm" onClick={ejecutarAhora} disabled={running || loading}>
          {running ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Ejecutar ahora y guardar meta
        </Button>

        {esAdmin && hayDesajustePagosVsAplicado && !loading ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => void corregirDesajustePagos()}
            disabled={corrigiendo || running || loading}
            title="Reaplica pagos en cascada en prestamos con alerta de suma pagos vs cuota_pagos, luego sincroniza estados de cuota."
          >
            {corrigiendo ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Corregir desajuste pagos (cascada)
          </Button>
        ) : null}

        {hayAlertas && !loading ? (
          <>
            <div className="flex w-full min-w-[200px] max-w-sm flex-col gap-1 sm:w-auto">
              <Label
                htmlFor="auditoria-cedula-filtro"
                className="text-xs text-gray-600"
              >
                Filtrar por cedula
              </Label>

              <Input
                id="auditoria-cedula-filtro"
                type="search"
                placeholder="Ej. V12345678"
                value={cedulaFiltro}
                onChange={e => setCedulaFiltro(e.target.value)}
                autoComplete="off"
                className="h-9"
              />
            </div>

            <div className="flex w-full min-w-[240px] max-w-xl flex-col gap-1 sm:w-auto">
              <Label
                htmlFor="auditoria-control-filtro"
                className="text-xs text-gray-600"
              >
                Filtrar por control
              </Label>

              <Select
                value={filtroControlCodigo || '__todos__'}
                onValueChange={v =>
                  setFiltroControlCodigo(v === '__todos__' ? '' : v)
                }
              >
                <SelectTrigger
                  id="auditoria-control-filtro"
                  className="h-9 w-full"
                >
                  <SelectValue placeholder="Todos los controles" />
                </SelectTrigger>

                <SelectContent>
                  <SelectItem value="__todos__">
                    Todos los controles (cualquier alerta)
                  </SelectItem>

                  {AUDITORIA_CARTERA_CONTROLES_CATALOGO.map(def => {
                    const cnt = conteosPorControlCodigo[def.codigo] ?? 0

                    return (
                      <SelectItem
                        key={def.codigo}
                        value={def.codigo}
                        title={def.titulo}
                      >
                        <span className="font-mono text-xs text-muted-foreground">
                          {def.n}.
                        </span>{' '}
                        {def.titulo}
                        {cnt > 0 ? (
                          <span className="text-muted-foreground">
                            {' '}
                            ({cnt})
                          </span>
                        ) : (
                          <span className="text-muted-foreground"> (0)</span>
                        )}
                      </SelectItem>
                    )
                  })}
                </SelectContent>
              </Select>
            </div>
          </>
        ) : null}

        {hayAlertas && resumen ? (
          <span className="text-sm text-gray-600">
            Evaluados:{' '}
            <strong>{String(resumen.prestamos_evaluados ?? '-')}</strong>
            {' · '}
            Con alerta:{' '}
            <strong>{String(resumen.prestamos_con_alerta ?? '-')}</strong>
            {' · '}
            Listados:{' '}
            <strong>
              {String(resumen.prestamos_listados ?? items.length)}
            </strong>
            {resumen.fecha_referencia ? (
              <>
                {' · '}
                Fecha referencia (Caracas):{' '}
                <strong className="font-mono">
                  {String(resumen.fecha_referencia)}
                </strong>
              </>
            ) : null}
          </span>
        ) : null}
      </div>

      {hayAlertas && !loading ? (
        <Card className="border-slate-200 bg-slate-50/80">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-slate-800">
              Controles numerados (mismo orden que la auditoria en servidor)
            </CardTitle>
          </CardHeader>

          <CardContent>
            <p className="mb-3 text-xs text-slate-600">
              Use el desplegable <strong>Filtrar por control</strong> arriba: al
              elegir el control N, solo verá los préstamos que tienen alerta{' '}
              <strong>SI</strong> en esa regla. Con <strong>Todos</strong> se
              muestran todas las alertas de cada préstamo.
            </p>

            <ol className="list-decimal space-y-1.5 pl-5 text-sm text-slate-800">
              {AUDITORIA_CARTERA_CONTROLES_CATALOGO.map(def => (
                <li key={def.codigo}>
                  <span className="font-medium">{def.titulo}</span>
                  {conteosPorControlCodigo[def.codigo] ? (
                    <span className="text-muted-foreground">
                      {' '}
                      - {conteosPorControlCodigo[def.codigo]} préstamo(s) con
                      esta alerta en vista actual
                    </span>
                  ) : (
                    <span className="text-muted-foreground">
                      {' '}
                      - sin casos en vista actual
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      ) : null}

      {loading ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center py-12 text-gray-500">
              <Loader2 className="mr-2 h-6 w-6 animate-spin" />
              Analizando cartera...
            </div>
          </CardContent>
        </Card>
      ) : !hayAlertas ? (
        <p className="py-6 text-center text-sm text-gray-600">
          No hay prestamos con controles en SI segun estos criterios. La cartera
          esta alineada con lo que aqui se revisa, o no hay prestamos
          APROBADO/LIQUIDADO.
        </p>
      ) : (
        <Card>
          <CardContent className="pt-6">
            {visibleRows.length === 0 ? (
              <p className="py-8 text-center text-gray-600">
                Oculto todos los controles con <strong>OK</strong> en esta
                sesion. Pulse <strong>Recargar</strong> o{' '}
                <strong>Ejecutar ahora</strong> para volver a evaluar desde la
                base de datos; lo que siga en alerta volvera a mostrarse.
              </p>
            ) : displayRows.length === 0 ? (
              <p className="py-8 text-center text-gray-600">
                {filtroControlCodigo && filasTrasCedula.length > 0 ? (
                  <>
                    Ningun prestamo cumple el{' '}
                    <strong>control seleccionado</strong> en esta vista (puede
                    haberlo ocultado con <strong>OK</strong> o no hay casos).
                    Pruebe <strong>Todos los controles</strong> u otro numero.
                  </>
                ) : (
                  <>
                    Ningun prestamo visible coincide con la cedula indicada.
                    Pruebe otro fragmento o deje el filtro vacio para ver todos.
                  </>
                )}
              </p>
            ) : (
              <div className="space-y-8">
                {displayRows.map(row => (
                  <div
                    key={row.prestamo_id}
                    className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
                  >
                    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <div className="text-lg font-semibold text-slate-900">
                          Prestamo #{row.prestamo_id}{' '}
                          <span className="text-slate-500">
                            · {row.nombres}
                          </span>
                        </div>

                        <div className="text-sm text-slate-600">
                          Cedula:{' '}
                          <span className="font-mono">{row.cedula}</span>
                          {' · '}
                          Estado:{' '}
                          <Badge variant="secondary">
                            {row.estado_prestamo}
                          </Badge>
                          {' · '}
                          <Link
                            className="text-blue-600 underline"
                            to={`/prestamos?prestamo_id=${row.prestamo_id}`}
                          >
                            Abrir prestamo
                          </Link>
                        </div>
                      </div>
                    </div>

                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[280px]">
                            Control (alerta SI)
                          </TableHead>

                          <TableHead>Detalle</TableHead>

                          <TableHead className="w-[100px] text-right">
                            Accion
                          </TableHead>
                        </TableRow>
                      </TableHeader>

                      <TableBody>
                        {row.controles.map(c => {
                          const numCtrl = numeroControlAuditoriaCartera(
                            c.codigo
                          )

                          return (
                            <TableRow key={`${row.prestamo_id}-${c.codigo}`}>
                              <TableCell className="align-top text-sm font-medium">
                                {numCtrl != null ? (
                                  <span
                                    className="mr-2 inline-flex h-5 min-w-[1.35rem] items-center justify-center rounded-md border border-slate-200 bg-slate-50 px-1 font-mono text-xs text-slate-700"
                                    title={`Control ${numCtrl}`}
                                  >
                                    {numCtrl}
                                  </span>
                                ) : null}
                                {c.titulo}
                              </TableCell>

                              <TableCell className="align-top text-sm text-slate-700">
                                {c.detalle || '-'}
                              </TableCell>

                              <TableCell className="text-right align-top">
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  className="gap-1"
                                  aria-label={`Marcar como revisado y ocultar: ${c.titulo}`}
                                  onClick={() =>
                                    marcarControlOk(row.prestamo_id, c.codigo)
                                  }
                                >
                                  <Check className="h-3.5 w-3.5" />
                                  OK
                                </Button>
                              </TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
