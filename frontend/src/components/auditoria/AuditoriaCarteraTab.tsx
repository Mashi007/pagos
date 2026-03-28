import { useCallback, useEffect, useMemo, useState } from 'react'

import { Check, Loader2, RefreshCw } from 'lucide-react'

import { Button } from '../ui/button'

import { Card, CardContent } from '../ui/card'

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
  auditoriaService,
  PrestamoCarteraChequeo,
} from '../../services/auditoriaService'

import { toast } from 'sonner'

import { Link } from 'react-router-dom'

function controlDismissKey(prestamoId: number, codigo: string) {
  return `${prestamoId}:${codigo}`
}

function normalizarCedulaBusqueda(valor: string) {
  return valor.trim().toUpperCase().replace(/\s+/g, '')
}

export function AuditoriaCarteraTab() {
  const [loading, setLoading] = useState(true)

  const [running, setRunning] = useState(false)

  const [items, setItems] = useState<PrestamoCarteraChequeo[]>([])

  const [resumen, setResumen] = useState<Record<string, unknown> | null>(null)

  /** Controles ocultados con OK en esta sesion; se limpia al Recargar / Ejecutar auditoria. */
  const [dismissed, setDismissed] = useState<Record<string, true>>({})

  const [cedulaFiltro, setCedulaFiltro] = useState('')

  const cargar = useCallback(async () => {
    try {
      setLoading(true)

      const cheq = await auditoriaService.listarCarteraChequeos()

      setItems(cheq.items || [])

      setResumen((cheq.resumen as Record<string, unknown>) || {})

      setDismissed({})

      setCedulaFiltro('')
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

      toast.success('Auditoria ejecutada y metadatos actualizados')
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

  const displayRows = useMemo(() => {
    if (!cedulaFiltroNorm) return visibleRows
    return visibleRows.filter(row => {
      const c = normalizarCedulaBusqueda(row.cedula || '')
      return c.includes(cedulaFiltroNorm)
    })
  }, [visibleRows, cedulaFiltroNorm])

  const marcarControlOk = (prestamoId: number, codigo: string) => {
    const k = controlDismissKey(prestamoId, codigo)
    setDismissed(prev => ({ ...prev, [k]: true }))
  }

  const hayAlertas = items.length > 0

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

        {hayAlertas && !loading ? (
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
                Ningun prestamo visible coincide con la cedula indicada. Pruebe
                otro fragmento o deje el filtro vacio para ver todos.
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
                        {row.controles.map(c => (
                          <TableRow key={`${row.prestamo_id}-${c.codigo}`}>
                            <TableCell className="align-top text-sm font-medium">
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
                        ))}
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
