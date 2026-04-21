import { useCallback, useEffect, useMemo, useState } from 'react'

import { Loader2, RefreshCw, Search, Shield } from 'lucide-react'

import { Link } from 'react-router-dom'

import { toast } from 'sonner'

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
  type PrestamoCarteraChequeo,
} from '../../services/auditoriaService'

const PAGE_SIZE = 25

const MEJORES_PRACTICAS_LIQUIDADOS: readonly string[] = [
  'Antes de aceptar un cierre (LIQUIDADO), cuadrar en USD la suma de pagos operativos frente a la suma aplicada en cuota_pagos (tolerancia operativa 0,02 USD), excluyendo anulados, reversados y duplicados declarados.',
  'Mantener fecha_liquidado poblada cuando el estado sea LIQUIDADO: es el ancla contable del cierre en cartera y evita listados ambiguos frente a finiquito.',
  'Respetar la regla de materialización de finiquito_casos (suma exacta de total_pagado en cuotas = total_financiamiento): si no aparece el caso, revisar redondeos por cuota y ejecutar el refresco puntual o el job programado.',
  'Exigir comprobantes con huella y documento canónico (doc_canon_numero) consistente: duplicados en el mismo préstamo suelen ser doble captura; si es recibo partido, usar la convención operativa de sufijos y el flujo de “visto” donde aplique.',
  'Si existe saldo sin aplicar a cuotas en un préstamo liquidado, tratarlo como incidente prioritario: bloquea la reconciliación del capital y puede generar colisiones de documento con otros préstamos.',
  'Registrar excepciones en la bitácora de cartera solo cuando el motor marque un falso positivo documentado; en LIQUIDADO los descuadres de totales no son “ruido”, son riesgo de estado financiero incorrecto.',
]

function numOr0(v: unknown): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : 0
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
  const [loading, setLoading] = useState(false)

  const [error, setError] = useState<string | null>(null)

  const [data, setData] = useState<AuditoriaLiquidadosIntensivaResponse | null>(null)

  const [cedula, setCedula] = useState('')

  const [prestamoIdRaw, setPrestamoIdRaw] = useState('')

  const [page, setPage] = useState(1)

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
  }, [cedula, page, prestamoId])

  useEffect(() => {
    void cargar()
  }, [cargar])

  const carteraItems = data?.cartera.items ?? []

  const cierreItems = data?.cierre.items ?? []

  const rCar = data?.cartera.resumen ?? {}

  const rCie = data?.cierre.resumen ?? {}

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
            aplicación frente a otro préstamo.
          </p>

          <div className="flex flex-col gap-3 md:flex-row md:items-end">
            <div className="grid flex-1 gap-2 md:grid-cols-2">
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

          <div className="grid gap-3 text-sm md:grid-cols-2">
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
    </div>
  )
}
