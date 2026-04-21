import { useCallback, useEffect, useMemo, useState } from 'react'

import { Copy, Loader2, RefreshCw, Search, Shield, Wrench } from 'lucide-react'

import { Link } from 'react-router-dom'

import { toast } from 'sonner'
import { useSimpleAuth } from '../../store/simpleAuthStore'
import { isAdminRole } from '../../utils/rol'
import { AuditoriaDescuadreRevisionDialog } from './AuditoriaDescuadreRevisionDialog'

import { AlertDescription, AlertWithIcon } from '../ui/alert'

import { Badge } from '../ui/badge'

import { Button } from '../ui/button'

import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

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

import {
  auditoriaService,
  type AuditoriaLiquidadosIntensivaResponse,
  type DocSimilarPrestamoTarjetaItem,
  type PrestamoCarteraChequeo,
} from '../../services/auditoriaService'

const PAGE_SIZE = 25

const MEJORES_PRACTICAS_LIQUIDADOS: readonly string[] = [
  'Verifique siempre la tarjeta «Cobertura de pagos»: el motor usa solo pagos **operativos cartera**; las filas excluidas por estado (anulado, reversado, duplicado declarado, etc.) no entran al cuadre ni a heurísticas de documento, pero siguen en BD y pueden ocultar dinero si el estado está mal.',
  'Antes de aceptar un cierre (LIQUIDADO), cuadrar en USD la suma de pagos operativos frente a la suma aplicada en cuota_pagos (tolerancia operativa 0,02 USD), excluyendo anulados, reversados y duplicados declarados.',
  'Mantener fecha_liquidado poblada cuando el estado sea LIQUIDADO: es el ancla contable del cierre en cartera y evita listados ambiguos frente a finiquito.',
  'Respetar la regla de materialización de finiquito_casos (suma exacta de total_pagado en cuotas = total_financiamiento): si no aparece el caso, revisar redondeos por cuota y ejecutar el refresco puntual o el job programado.',
  'Exigir comprobantes con huella y documento canónico (doc_canon_numero) consistente: duplicados en el mismo préstamo suelen ser doble captura; la sección de similitud (≥70 %) ayuda a detectar variantes tipográficas — no sustituye el control de duplicado exacto por canon.',
  'Si existe saldo sin aplicar a cuotas en un préstamo liquidado, tratarlo como incidente prioritario: bloquea la reconciliación del capital y puede generar colisiones de documento con otros préstamos.',
  'Registrar excepciones en la bitácora de cartera solo cuando el motor marque un falso positivo documentado; en LIQUIDADO los descuadres de totales no son “ruido”, son riesgo de estado financiero incorrecto.',
]

function numOr0(v: unknown): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : 0
}

function pctSimilitud(ratio: number): string {
  if (typeof ratio !== 'number' || !Number.isFinite(ratio)) return '—'
  return `${(ratio * 100).toFixed(1)} %`
}

function TarjetaDocSimilaresPrestamo({
  item,
  maxPagosPairwise,
}: {
  item: DocSimilarPrestamoTarjetaItem

  maxPagosPairwise: number
}) {
  return (
    <Card className="border-amber-200/80 bg-amber-50/30">
      <CardHeader className="py-3">
        <CardTitle className="text-sm font-medium">
          <Link className="font-mono text-blue-700 underline" to={`/prestamos?prestamo_id=${item.prestamo_id}`}>
            Préstamo #{item.prestamo_id}
          </Link>
          <span className="ml-2 font-normal text-muted-foreground">
            — {item.nombres} <span className="text-xs">({item.cedula})</span>
          </span>
        </CardTitle>
        {item.pares_truncados ? (
          <p className="text-xs text-amber-900">
            Comparación pareja limitada a los primeros{' '}
            <span className="font-mono tabular-nums">{maxPagosPairwise}</span> pagos con documento; este préstamo
            tiene <span className="font-mono tabular-nums">{item.n_pagos_con_documento ?? '—'}</span> en total.
          </p>
        ) : null}
      </CardHeader>
      <CardContent className="overflow-x-auto pt-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[88px]">Similitud</TableHead>
              <TableHead>Pago A</TableHead>
              <TableHead>Documento A</TableHead>
              <TableHead>Canon A</TableHead>
              <TableHead>Pago B</TableHead>
              <TableHead>Documento B</TableHead>
              <TableHead>Canon B</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {item.pares.map((p, idx) => (
              <TableRow key={`${p.pago_id_a}-${p.pago_id_b}-${idx}`}>
                <TableCell className="font-mono text-xs tabular-nums">{pctSimilitud(p.similitud)}</TableCell>
                <TableCell className="font-mono text-xs">#{p.pago_id_a}</TableCell>
                <TableCell className="max-w-[200px] font-mono text-xs break-all">{p.numero_documento_a}</TableCell>
                <TableCell className="max-w-[120px] font-mono text-[11px] text-muted-foreground break-all">
                  {p.doc_canon_numero_a || '—'}
                </TableCell>
                <TableCell className="font-mono text-xs">#{p.pago_id_b}</TableCell>
                <TableCell className="max-w-[200px] font-mono text-xs break-all">{p.numero_documento_b}</TableCell>
                <TableCell className="max-w-[120px] font-mono text-[11px] text-muted-foreground break-all">
                  {p.doc_canon_numero_b || '—'}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function ControlesCelda({ row }: { row: PrestamoCarteraChequeo }) {
  return (
    <div className="flex flex-col gap-1">
      {row.controles.map((c) => (
        <div key={c.codigo} className="rounded-md border border-orange-200 bg-orange-50/60 p-2 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="font-mono text-[10px]">
              {c.codigo}
            </Badge>
            <span className="font-medium text-gray-800">{c.titulo}</span>
          </div>
          {c.detalle ? (
            <p className="mt-1 text-[11px] leading-snug text-gray-600">{c.detalle}</p>
          ) : null}
        </div>
      ))}
    </div>
  )
}

export function AuditoriaLiquidadosIntensivaTab() {
  const { user } = useSimpleAuth()
  const esAdmin = isAdminRole(user?.rol)
  const [loading, setLoading] = useState(false)

  const [error, setError] = useState<string | null>(null)

  const [data, setData] = useState<AuditoriaLiquidadosIntensivaResponse | null>(null)

  const [cedula, setCedula] = useState('')

  const [prestamoIdRaw, setPrestamoIdRaw] = useState('')

  const [page, setPage] = useState(1)

  const [umbralSimDoc, setUmbralSimDoc] = useState('0.7')
  const [descRevisionOpen, setDescRevisionOpen] = useState(false)
  const [descRevisionPid, setDescRevisionPid] = useState<number | null>(null)

  const umbralSimNum = useMemo(() => {
    const n = Number(String(umbralSimDoc).replace(',', '.'))
    if (!Number.isFinite(n)) return 0.7
    return Math.min(1, Math.max(0.5, n))
  }, [umbralSimDoc])

  const prestamoId = useMemo(() => {
    const t = prestamoIdRaw.trim()
    if (!t) return undefined
    const n = Number(t)
    return Number.isFinite(n) && n >= 1 ? n : undefined
  }, [prestamoIdRaw])

  const cargar = useCallback(async () => {
    try {
      setLoading(true)

      setError(null)

      const skip = (page - 1) * PAGE_SIZE

      const res = await auditoriaService.obtenerAuditoriaLiquidadosIntensiva({
        skip,

        limit: PAGE_SIZE,

        cedula: cedula.trim() || undefined,

        prestamo_id: prestamoId,

        excluir_marcar_ok: false,

        umbral_similitud_documento: umbralSimNum,
      })

      setData(res)
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (e as Error)?.message ||
        'Error al cargar auditoria intensiva de liquidados'

      setError(String(msg))

      toast.error(String(msg))
    } finally {
      setLoading(false)
    }
  }, [cedula, page, prestamoId, umbralSimNum])

  useEffect(() => {
    void cargar()
  }, [cargar])

  const carteraItems = data?.cartera.items ?? []

  const cierreItems = data?.cierre.items ?? []

  const rCar = data?.cartera.resumen ?? {}

  const rCie = data?.cierre.resumen ?? {}

  const docSim = data?.documentos_similares

  const rSim = docSim?.resumen ?? {}

  const docSimItems = docSim?.items ?? []

  const maxPagosPairwise = numOr0(rSim.max_pagos_analizados_por_prestamo) || 100

  const cov = data?.cobertura_pagos

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Shield className="h-5 w-5 text-purple-600" />
            Auditoria intensiva — prestamos LIQUIDADO
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Cruza el motor de cartera (solo universo LIQUIDADO) con hallazgos de cierre: fecha de liquidación,
            fila en finiquito_casos, alineación de snapshot y riesgos de documento duplicado o pendiente de
            aplicación frente a otro préstamo. Además lista pares de pagos con{' '}
            <span className="font-medium">numero_documento</span> muy parecido (similitud configurable) dentro del
            mismo préstamo, como pista de posible doble captura.
          </p>

          <div className="flex flex-col gap-3 md:flex-row md:items-end">
            <div className="grid flex-1 gap-2 md:grid-cols-3">
              <div>
                <Label htmlFor="liq-cedula">Cedula (fragmento)</Label>
                <Input
                  id="liq-cedula"
                  value={cedula}
                  onChange={(e) => {
                    setCedula(e.target.value)

                    setPage(1)
                  }}
                  placeholder="Ej. 12345"
                />
              </div>
              <div>
                <Label htmlFor="liq-pid">Prestamo ID</Label>
                <Input
                  id="liq-pid"
                  value={prestamoIdRaw}
                  onChange={(e) => {
                    setPrestamoIdRaw(e.target.value)

                    setPage(1)
                  }}
                  placeholder="Opcional"
                  inputMode="numeric"
                />
              </div>
              <div>
                <Label htmlFor="liq-sim">Umbral similitud documento</Label>
                <Input
                  id="liq-sim"
                  value={umbralSimDoc}
                  onChange={(e) => {
                    setUmbralSimDoc(e.target.value)

                    setPage(1)
                  }}
                  placeholder="0.7 = 70%"
                  inputMode="decimal"
                />
                <p className="mt-1 text-[11px] text-muted-foreground">Rango en servidor: 0,5 a 1,0 (difflib).</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="secondary" onClick={() => void cargar()} disabled={loading}>
                {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
                Buscar
              </Button>
              <Button type="button" variant="outline" onClick={() => void cargar()} disabled={loading}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Refrescar
              </Button>
            </div>
          </div>

          {error ? (
            <AlertWithIcon variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </AlertWithIcon>
          ) : null}

          {cov ? (
            <div className="rounded-md border border-slate-200 bg-slate-50/80 p-4 text-sm">
              <p className="font-semibold text-slate-900">Cobertura de pagos (completitud, mismo filtro)</p>
              <p className="mt-2 grid gap-1 text-muted-foreground sm:grid-cols-2 lg:grid-cols-3">
                <span>
                  Préstamos con ≥1 fila de pago:{' '}
                  <span className="font-mono tabular-nums text-slate-900">
                    {numOr0(cov.n_prestamos_distintos_con_algun_pago)}
                  </span>
                </span>
                <span>
                  Filas de pago (todas):{' '}
                  <span className="font-mono tabular-nums text-slate-900">{numOr0(cov.n_pagos_total_filas)}</span>
                </span>
                <span>
                  Operativos cartera:{' '}
                  <span className="font-mono tabular-nums text-emerald-800">
                    {numOr0(cov.n_pagos_operativos_cartera)}
                  </span>
                </span>
                <span>
                  Excluidos del motor:{' '}
                  <span className="font-mono tabular-nums text-amber-900">
                    {numOr0(cov.n_pagos_excluidos_cartera)}
                  </span>
                </span>
                <span>
                  Operativos sin N° documento:{' '}
                  <span className="font-mono tabular-nums text-orange-900">
                    {numOr0(cov.n_pagos_operativos_sin_numero_documento)}
                  </span>
                </span>
                <span>
                  LIQUIDADO sin ningún pago:{' '}
                  <span className="font-mono tabular-nums text-red-800">
                    {numOr0(cov.n_prestamos_liquidados_sin_ningun_pago)}
                  </span>
                </span>
                <span className="sm:col-span-2 lg:col-span-3">
                  Préstamos donde todos los pagos están excluidos:{' '}
                  <span className="font-mono tabular-nums text-red-800">
                    {numOr0(cov.n_prestamos_con_pagos_todos_excluidos_cartera)}
                  </span>
                </span>
              </p>
              <p className="mt-3 text-xs leading-relaxed text-slate-600">
                <span className="font-medium text-slate-800">Regla operativo:</span> {cov.regla_exclusion_operativo_resumen}
              </p>
              <p className="mt-2 text-xs leading-relaxed text-slate-600">{cov.nota_completitud_auditoria}</p>
            </div>
          ) : null}

          <div className="grid gap-3 text-sm md:grid-cols-3">
            <div className="rounded-md border bg-muted/30 p-3">
              <p className="font-medium text-gray-800">Cartera (LIQUIDADO)</p>
              <p className="mt-1 text-muted-foreground">
                Evaluados:{' '}
                <span className="font-mono tabular-nums">{numOr0(rCar.prestamos_evaluados)}</span> — Con
                alerta motor:{' '}
                <span className="font-mono tabular-nums text-orange-700">
                  {numOr0(rCar.prestamos_con_alerta)}
                </span>{' '}
                — En esta pagina:{' '}
                <span className="font-mono tabular-nums">{carteraItems.length}</span>
              </p>
            </div>
            <div className="rounded-md border bg-muted/30 p-3">
              <p className="font-medium text-gray-800">Cierre / finiquito / documentos</p>
              <p className="mt-1 text-muted-foreground">
                Prestamos con hallazgo (filtrado):{' '}
                <span className="font-mono tabular-nums">
                  {numOr0(rCie.prestamos_con_hallazgo_cierre)}
                </span>{' '}
                — Hallazgos totales:{' '}
                <span className="font-mono tabular-nums text-orange-700">
                  {numOr0(rCie.hallazgos_totales)}
                </span>{' '}
                — En esta pagina:{' '}
                <span className="font-mono tabular-nums">{cierreItems.length}</span>
              </p>
            </div>
            <div className="rounded-md border bg-muted/30 p-3">
              <p className="font-medium text-gray-800">Documentos similares (mismo préstamo)</p>
              <p className="mt-1 text-muted-foreground">
                Umbral aplicado:{' '}
                <span className="font-mono tabular-nums">{pctSimilitud(Number(rSim.umbral_similitud) || umbralSimNum)}</span>{' '}
                — Préstamos con pares:{' '}
                <span className="font-mono tabular-nums text-amber-800">
                  {numOr0(rSim.prestamos_con_pares_similares)}
                </span>{' '}
                — Pares listados:{' '}
                <span className="font-mono tabular-nums">{numOr0(rSim.total_pares_listados)}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between gap-2">
            <Button type="button" variant="outline" size="sm" disabled={loading || page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
              Anterior
            </Button>
            <span className="text-sm text-muted-foreground">Pagina {page}</span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={loading || (carteraItems.length < PAGE_SIZE && cierreItems.length < PAGE_SIZE)}
              onClick={() => setPage((p) => p + 1)}
            >
              Siguiente
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">1) Motor de cartera (solo LIQUIDADO)</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {carteraItems.length === 0 && !loading ? (
            <p className="text-sm text-muted-foreground">Sin alertas del motor en esta pagina.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Prestamo</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Controles en SI</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {carteraItems.map((row) => (
                  <TableRow key={row.prestamo_id}>
                    <TableCell className="align-top">
                      <Link className="font-mono text-blue-700 underline" to={`/prestamos?prestamo_id=${row.prestamo_id}`}>
                        #{row.prestamo_id}
                      </Link>
                      <div className="text-xs text-muted-foreground">{row.estado_prestamo}</div>
                      <div className="mt-2">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-8 gap-1"
                            title="Abrir interfaz rápida para revisar, editar o eliminar pagos del préstamo"
                            onClick={() => {
                              setDescRevisionPid(row.prestamo_id)
                              setDescRevisionOpen(true)
                            }}
                          >
                            <Wrench className="h-3.5 w-3.5" />
                            Resolver rapido
                          </Button>
                          <Button asChild type="button" variant="secondary" size="sm" className="h-8 gap-1">
                            <Link
                              to={`/pagos/pagos?prestamo_id=${row.prestamo_id}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              title="Abrir Pagos filtrado por préstamo en una pestaña nueva"
                            >
                              Ir a Pagos
                            </Link>
                          </Button>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="align-top text-sm">
                      <div className="font-medium">{row.nombres}</div>
                      <div className="text-muted-foreground">{row.cedula}</div>
                    </TableCell>
                    <TableCell className="max-w-xl">
                      <ControlesCelda row={row} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">2) Hallazgos de cierre (contable / finiquito / documentos)</CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {cierreItems.length === 0 && !loading ? (
            <p className="text-sm text-muted-foreground">Sin hallazgos de cierre en esta pagina.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Prestamo</TableHead>
                  <TableHead>Cliente</TableHead>
                  <TableHead>Hallazgos</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {cierreItems.map((row) => (
                  <TableRow key={`c-${row.prestamo_id}`}>
                    <TableCell className="align-top">
                      <Link className="font-mono text-blue-700 underline" to={`/prestamos?prestamo_id=${row.prestamo_id}`}>
                        #{row.prestamo_id}
                      </Link>
                      <div className="mt-2">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-8 gap-1"
                            title="Abrir interfaz rápida para corregir inconformidades de este préstamo"
                            onClick={() => {
                              setDescRevisionPid(row.prestamo_id)
                              setDescRevisionOpen(true)
                            }}
                          >
                            <Wrench className="h-3.5 w-3.5" />
                            Resolver rapido
                          </Button>
                          <Button asChild type="button" variant="secondary" size="sm" className="h-8 gap-1">
                            <Link
                              to={`/pagos/pagos?prestamo_id=${row.prestamo_id}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              title="Abrir Pagos filtrado por préstamo en una pestaña nueva"
                            >
                              Ir a Pagos
                            </Link>
                          </Button>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="align-top text-sm">
                      <div className="font-medium">{row.nombres}</div>
                      <div className="text-muted-foreground">{row.cedula}</div>
                    </TableCell>
                    <TableCell className="max-w-xl">
                      <ControlesCelda row={row} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Copy className="h-4 w-4 text-amber-700" />
            3) Documentos similares (posible duplicado / variante)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Pagos operativos del mismo préstamo LIQUIDADO cuyo <span className="font-medium">numero_documento</span>{' '}
            alcanza al menos el umbral de similitud (secuencia normalizada). Revise montos, fechas y canon antes de
            concluir: alta similitud sugiere la misma operación capturada dos veces, pero no lo prueba.
          </p>
          {typeof rSim.metodo === 'string' ? (
            <p className="text-xs text-muted-foreground">
              <span className="font-medium">Método:</span> {rSim.metodo}
            </p>
          ) : null}
          {!loading && docSimItems.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Sin pares por encima del umbral en el filtro actual (cédula / préstamo / universo consultado).
            </p>
          ) : (
            <div className="space-y-3">
              {docSimItems.map((it) => (
                <TarjetaDocSimilaresPrestamo key={it.prestamo_id} item={it} maxPagosPairwise={maxPagosPairwise} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Buenas practicas para el modulo (prestamos, pagos, cuotas)</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-2 pl-5 text-sm text-gray-700">
            {MEJORES_PRACTICAS_LIQUIDADOS.map((t, idx) => (
              <li key={idx}>{t}</li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <AuditoriaDescuadreRevisionDialog
        open={descRevisionOpen}
        onOpenChange={(open) => {
          setDescRevisionOpen(open)
          if (!open) setDescRevisionPid(null)
        }}
        prestamoId={descRevisionPid}
        esAdmin={esAdmin}
        onRefreshLista={() => {
          void cargar()
        }}
      />
    </div>
  )
}
