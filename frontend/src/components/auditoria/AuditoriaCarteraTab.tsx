import { useCallback, useEffect, useState } from 'react'

import { AlertTriangle, Loader2, RefreshCw } from 'lucide-react'

import { Button } from '../ui/button'

import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

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

export function AuditoriaCarteraTab() {
  const [loading, setLoading] = useState(true)

  const [running, setRunning] = useState(false)

  const [items, setItems] = useState<PrestamoCarteraChequeo[]>([])

  const [resumen, setResumen] = useState<Record<string, unknown> | null>(null)

  const [meta, setMeta] = useState<Record<string, unknown> | null>(null)

  const [soloAlertas, setSoloAlertas] = useState(true)

  const cargar = useCallback(async () => {
    try {
      setLoading(true)

      const [cheq, m] = await Promise.all([
        auditoriaService.listarCarteraChequeos(soloAlertas),

        auditoriaService.metaCartera(),
      ])

      setItems(cheq.items || [])

      setResumen((cheq.resumen as Record<string, unknown>) || {})

      setMeta(m || {})
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'Error al cargar auditoria de cartera'

      toast.error(msg)

      setItems([])

      setResumen(null)

      setMeta(null)
    } finally {
      setLoading(false)
    }
  }, [soloAlertas])

  useEffect(() => {
    cargar()
  }, [cargar])

  const ejecutarAhora = async () => {
    try {
      setRunning(true)

      const cheq = await auditoriaService.ejecutarCartera(soloAlertas)

      setItems(cheq.items || [])

      setResumen((cheq.resumen as Record<string, unknown>) || {})

      setMeta((cheq.meta_ultima_corrida as Record<string, unknown>) || {})

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

  const ultima =
    (meta?.ultima_ejecucion_utc as string | undefined) ||
    (meta?.ultima_ejecucion as string | undefined)

  return (
    <div className="space-y-6">
      <Card className="border-amber-200 bg-amber-50/60">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base text-amber-950">
            <AlertTriangle className="h-5 w-5 text-amber-700" />
            Como leer esta auditoria
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-2 text-sm text-amber-950/90">
          <p>
            Los controles se calculan en tiempo real desde las tablas de la base
            de datos (prestamos, clientes, cuotas, pagos, cuota_pagos). Cada
            control muestra <strong>SI</strong> o <strong>NO</strong>:{' '}
            <strong>SI</strong> significa que hay una posible inconsistencia o
            riesgo y conviene revision humana; no es una sentencia juridica ni
            contable.
          </p>

          <p>
            A las <strong>03:00</strong> (America/Caracas) el servidor vuelve a
            evaluar toda la cartera y guarda la fecha de la ultima corrida. Si
            corrige los datos en la BD, al recargar desapareceran las alertas;
            si el problema persiste, el prestamo seguira apareciendo.
          </p>

          {ultima ? (
            <p className="text-xs text-amber-900/80">
              Ultima corrida automatica registrada (UTC):{' '}
              <span className="font-mono">{ultima}</span>
            </p>
          ) : (
            <p className="text-xs text-amber-900/80">
              Aun no hay registro de corrida automatica; use &quot;Ejecutar
              ahora&quot; o espere el job nocturno.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant={soloAlertas ? 'default' : 'outline'}
          size="sm"
          onClick={() => setSoloAlertas(true)}
        >
          Solo con alertas
        </Button>

        <Button
          variant={!soloAlertas ? 'default' : 'outline'}
          size="sm"
          onClick={() => setSoloAlertas(false)}
        >
          Todos los prestamos (puede ser lento)
        </Button>

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

        {resumen ? (
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
          </span>
        ) : null}
      </div>

      <Card>
        <CardContent className="pt-6">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-gray-500">
              <Loader2 className="mr-2 h-6 w-6 animate-spin" />
              Analizando cartera...
            </div>
          ) : items.length === 0 ? (
            <p className="py-8 text-center text-gray-600">
              No hay filas que mostrar con el filtro actual. Si eligio solo
              alertas, la cartera esta consistente con estos controles.
            </p>
          ) : (
            <div className="space-y-8">
              {items.map(row => (
                <div
                  key={row.prestamo_id}
                  className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-lg font-semibold text-slate-900">
                        Prestamo #{row.prestamo_id}{' '}
                        <span className="text-slate-500">· {row.nombres}</span>
                      </div>

                      <div className="text-sm text-slate-600">
                        Cedula: <span className="font-mono">{row.cedula}</span>
                        {' · '}
                        Estado:{' '}
                        <Badge variant="secondary">{row.estado_prestamo}</Badge>
                        {' · '}
                        <Link
                          className="text-blue-600 underline"
                          to="/prestamos"
                        >
                          Ir a prestamos
                        </Link>
                      </div>
                    </div>
                  </div>

                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-[240px]">Control</TableHead>

                        <TableHead className="w-[100px] text-center">
                          Alerta
                        </TableHead>

                        <TableHead>Detalle</TableHead>
                      </TableRow>
                    </TableHeader>

                    <TableBody>
                      {row.controles.map(c => (
                        <TableRow key={`${row.prestamo_id}-${c.codigo}`}>
                          <TableCell className="align-top text-sm font-medium">
                            {c.titulo}
                          </TableCell>

                          <TableCell className="text-center align-top">
                            <Badge
                              className={
                                c.alerta === 'SI'
                                  ? 'bg-red-600 hover:bg-red-600'
                                  : 'bg-emerald-600 hover:bg-emerald-600'
                              }
                            >
                              {c.alerta}
                            </Badge>
                          </TableCell>

                          <TableCell className="align-top text-sm text-slate-700">
                            {c.detalle || '-'}
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
    </div>
  )
}
