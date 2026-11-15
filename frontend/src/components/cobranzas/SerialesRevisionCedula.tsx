/**
 * Cobranzas → Seriales, revisión manual por cédula.
 * Izquierda: cuotas del préstamo más atrasado (con la cascada simulada de lo marcado).
 * Derecha: por cada cuota atrasada, los depósitos de los N meses posteriores a su
 * vencimiento dentro de ±tolerancia del monto de la cuota. Un depósito por mes.
 * «Procesar» registra los marcados (cascada desde la cuota más antigua) y pasa a la siguiente.
 */
import { useMemo, useState } from 'react'
import { Download, Loader2, Play, RotateCcw } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '../ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { Input } from '../ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table'
import {
  cobranzasSerialesService,
  type SerialCandidato,
  type SerialRevisionResponse,
} from '../../services/cobranzasSerialesService'
import {
  errMsg,
  leerCedulas,
  leerDepositos,
  type DepositoFila,
} from '../../utils/serialesExcel'

type Historial = {
  cedula: string
  prestamo_id: number | null
  resultado: 'CARGADA' | 'SIN_PAGOS' | 'ERROR' | 'DESHECHA'
  pagos: {
    pago_id: number
    deposito_id: number
    fecha: string
    serial: string
    monto: number
  }[]
  detalle: string
}

const money = (n: number) =>
  n.toLocaleString('es-EC', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })

export function SerialesRevisionCedula() {
  const [fileCedulas, setFileCedulas] = useState<File | null>(null)
  const [fileDepositos, setFileDepositos] = useState<File | null>(null)
  const [tolerancia, setTolerancia] = useState(30)
  const [meses, setMeses] = useState(3)
  const [cedulas, setCedulas] = useState<string[]>([])
  const [deps, setDeps] = useState<DepositoFila[]>([])
  const [idx, setIdx] = useState(0)
  const [revision, setRevision] = useState<SerialRevisionResponse | null>(null)
  const [seleccion, setSeleccion] = useState<Record<string, number>>({})
  const [usados, setUsados] = useState<number[]>([])
  const [historial, setHistorial] = useState<Historial[]>([])
  const [cargando, setCargando] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const ocupado = cargando || guardando
  const terminado = cedulas.length > 0 && idx >= cedulas.length

  const depPorId = useMemo(() => {
    const m = new Map<number, DepositoFila>()
    for (const d of deps) m.set(d.id, d)
    return m
  }, [deps])

  const candPorId = useMemo(() => {
    const m = new Map<number, SerialCandidato & { clave: string }>()
    for (const b of revision?.bloques || [])
      for (const mb of b.meses)
        for (const c of mb.candidatos)
          m.set(c.deposito_id, { ...c, clave: mb.clave })
    return m
  }, [revision])

  const marcados = useMemo(
    () =>
      Object.values(seleccion)
        .map(id => candPorId.get(id))
        .filter((x): x is SerialCandidato & { clave: string } => !!x)
        .sort(
          (a, b) =>
            a.fecha.localeCompare(b.fecha) || a.deposito_id - b.deposito_id
        ),
    [seleccion, candPorId]
  )

  const simulacion = useMemo(() => {
    const cuotas = revision?.cuotas || []
    const aplica = new Map<number, number>()
    const falta = new Map(cuotas.map(c => [c.id, c.falta]))
    let sobrante = 0
    for (const d of marcados) {
      let resto = d.monto
      for (const c of cuotas) {
        if (resto <= 0.0001) break
        const f = falta.get(c.id) || 0
        if (f <= 0.0001) continue
        const a = Math.min(f, resto)
        falta.set(c.id, f - a)
        aplica.set(c.id, (aplica.get(c.id) || 0) + a)
        resto -= a
      }
      sobrante += Math.max(0, resto)
    }
    const total = marcados.reduce((s, d) => s + d.monto, 0)
    const faltaAtrasadas = cuotas
      .filter(c => c.atrasada)
      .reduce((s, c) => s + c.falta, 0)
    const cubiertas = cuotas.filter(
      c => c.atrasada && (falta.get(c.id) || 0) <= 0.01
    ).length
    return { aplica, falta, sobrante, total, faltaAtrasadas, cubiertas }
  }, [revision, marcados])

  async function cargar(
    i: number,
    usadosActuales: number[],
    lista = cedulas,
    depsLista = deps
  ) {
    if (i >= lista.length) {
      setIdx(i)
      setRevision(null)
      setSeleccion({})
      return
    }
    setCargando(true)
    setIdx(i)
    try {
      const usadosSet = new Set(usadosActuales)
      const res = await cobranzasSerialesService.revisionCedula({
        cedula: lista[i],
        depositos: depsLista
          .filter(d => !usadosSet.has(d.id))
          .map(d => ({
            id: d.id,
            fecha: d.fecha,
            serial: d.serial,
            monto: d.monto,
          })),
        usados: usadosActuales,
        seriales_tomados: depsLista
          .filter(d => usadosSet.has(d.id))
          .map(d => d.serial),
        tolerancia_pct: tolerancia,
        meses_despues: meses,
      })
      setRevision(res)
      const sel: Record<string, number> = {}
      const clavePorDep = new Map<number, string>()
      for (const b of res.bloques)
        for (const mb of b.meses)
          for (const c of mb.candidatos)
            clavePorDep.set(c.deposito_id, mb.clave)
      for (const id of res.sugeridos) {
        const k = clavePorDep.get(id)
        if (k && sel[k] === undefined) sel[k] = id
      }
      setSeleccion(sel)
    } catch (err) {
      setRevision(null)
      setSeleccion({})
      toast.error(errMsg(err))
    } finally {
      setCargando(false)
    }
  }

  async function iniciar() {
    if (!fileCedulas || !fileDepositos) {
      toast.error('Sube el Excel de cédulas y el Excel de depósitos.')
      return
    }
    setCargando(true)
    try {
      const lista = await leerCedulas(fileCedulas)
      const d = await leerDepositos(fileDepositos)
      setCedulas(lista)
      setDeps(d)
      setUsados([])
      setHistorial([])
      toast.success(
        `${lista.length} cédula(s) y ${d.length} depósito(s) leídos.`
      )
      await cargar(0, [], lista, d)
    } catch (err) {
      setCargando(false)
      toast.error(errMsg(err))
    }
  }

  /** Un depósito por mes y un serial una sola vez. */
  function alternar(clave: string, depositoId: number) {
    setSeleccion(prev => {
      const next = { ...prev }
      if (next[clave] === depositoId) {
        delete next[clave]
        return next
      }
      const serial = candPorId.get(depositoId)?.serial
      for (const [k, id] of Object.entries(next)) {
        if (serial && candPorId.get(id)?.serial === serial) delete next[k]
      }
      next[clave] = depositoId
      return next
    })
  }

  async function procesar() {
    if (!revision) return
    const cedula = cedulas[idx]
    if (!marcados.length || !revision.prestamo_id) {
      setHistorial(h => [
        ...h,
        {
          cedula,
          prestamo_id: revision.prestamo_id,
          resultado: 'SIN_PAGOS',
          pagos: [],
          detalle: revision.prestamo_id
            ? 'Sin depósitos marcados'
            : revision.detalle,
        },
      ])
      await cargar(idx + 1, usados)
      return
    }
    setGuardando(true)
    try {
      const res = await cobranzasSerialesService.guardarCedula({
        cedula,
        prestamo_id: revision.prestamo_id,
        depositos: marcados.map(m => {
          const d = depPorId.get(m.deposito_id)
          return {
            id: m.deposito_id,
            fecha: d?.fecha ?? m.fecha,
            serial: d?.serial ?? m.serial,
            monto: d?.monto ?? String(m.monto),
          }
        }),
      })
      const nuevosUsados = [...usados, ...res.pagos.map(p => p.deposito_id)]
      setUsados(nuevosUsados)
      setHistorial(h => [
        ...h,
        {
          cedula,
          prestamo_id: res.prestamo_id,
          resultado: res.error ? 'ERROR' : 'CARGADA',
          pagos: res.pagos.map(p => ({
            pago_id: p.pago_id,
            deposito_id: p.deposito_id,
            fecha: p.fecha,
            serial: p.serial,
            monto: p.monto,
          })),
          detalle: res.error || `${res.pagos.length} pago(s) cargado(s)`,
        },
      ])
      if (res.error) {
        toast.error(
          `${res.error}. Cargados ${res.pagos.length}; revisa esta cédula.`
        )
        await cargar(idx, nuevosUsados)
      } else {
        toast.success(
          `${cedula}: ${res.pagos.length} pago(s) cargado(s) con cascada.`
        )
        await cargar(idx + 1, nuevosUsados)
      }
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setGuardando(false)
    }
  }

  async function deshacerUltima() {
    const i = [...historial]
      .reverse()
      .findIndex(h => h.resultado !== 'DESHECHA' && h.pagos.length)
    if (i < 0) return
    const pos = historial.length - 1 - i
    const h = historial[pos]
    if (
      !window.confirm(
        `Se eliminarán ${h.pagos.length} pago(s) de la cédula ${h.cedula} y se recalcularán sus cuotas. ¿Continuar?`
      )
    )
      return
    setGuardando(true)
    try {
      const res = await cobranzasSerialesService.deshacer(
        h.pagos.map(p => p.pago_id)
      )
      const borrados = new Set(res.eliminados)
      const liberados = new Set(
        h.pagos.filter(p => borrados.has(p.pago_id)).map(p => p.deposito_id)
      )
      const nuevosUsados = usados.filter(id => !liberados.has(id))
      setUsados(nuevosUsados)
      setHistorial(prev =>
        prev.map((x, k) =>
          k === pos
            ? {
                ...x,
                resultado: 'DESHECHA',
                detalle: `Deshecha (${res.eliminados.length} pago(s) eliminados)`,
              }
            : x
        )
      )
      if (res.errores.length || res.omitidos.length) {
        toast.warning(
          `Eliminados ${res.eliminados.length}; con problema ${res.errores.length + res.omitidos.length}.`
        )
      } else {
        toast.success(`Cédula ${h.cedula} deshecha.`)
      }
      const vuelta = cedulas.indexOf(h.cedula)
      await cargar(vuelta >= 0 ? vuelta : idx, nuevosUsados)
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setGuardando(false)
    }
  }

  async function descargarResumen() {
    const { createAndDownloadExcel } = await import('../../types/exceljs')
    const filas: Record<string, unknown>[] = []
    for (const h of historial) {
      if (!h.pagos.length) {
        filas.push({
          Cedula: h.cedula,
          Prestamo: h.prestamo_id ?? '',
          Resultado: h.resultado,
          Fecha: '',
          Serial: '',
          Monto: '',
          'Pago ID': '',
          Detalle: h.detalle,
        })
        continue
      }
      for (const p of h.pagos)
        filas.push({
          Cedula: h.cedula,
          Prestamo: h.prestamo_id ?? '',
          Resultado: h.resultado,
          Fecha: p.fecha,
          Serial: p.serial,
          Monto: p.monto,
          'Pago ID': p.pago_id,
          Detalle: h.detalle,
        })
    }
    await createAndDownloadExcel(
      filas,
      'Revision',
      'Cobranzas_Seriales_revision.xlsx'
    )
  }

  const cargadas = historial.filter(h => h.resultado === 'CARGADA').length
  const pagosCargados = historial
    .filter(h => h.resultado !== 'DESHECHA')
    .reduce((s, h) => s + h.pagos.length, 0)
  const puedeDeshacer = historial.some(
    h => h.resultado !== 'DESHECHA' && h.pagos.length
  )

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Archivos y opciones</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="space-y-1 md:col-span-2">
              <p className="text-sm font-medium">1. Cédulas (columna A)</p>
              <Input
                type="file"
                accept=".xlsx"
                disabled={ocupado}
                onChange={e => setFileCedulas(e.target.files?.[0] || null)}
              />
            </div>
            <div className="space-y-1 md:col-span-2">
              <p className="text-sm font-medium">
                2. Depósitos (A Deposito · B Referencia · C Monto)
              </p>
              <Input
                type="file"
                accept=".xlsx"
                disabled={ocupado}
                onChange={e => setFileDepositos(e.target.files?.[0] || null)}
              />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">
                Tolerancia sobre la cuota (±%)
              </p>
              <Input
                type="number"
                min={0}
                max={50}
                value={tolerancia}
                disabled={ocupado}
                onChange={e =>
                  setTolerancia(
                    Math.min(50, Math.max(0, Number(e.target.value) || 0))
                  )
                }
              />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">
                Meses después del vencimiento
              </p>
              <Input
                type="number"
                min={1}
                max={12}
                value={meses}
                disabled={ocupado}
                onChange={e =>
                  setMeses(
                    Math.min(
                      12,
                      Math.max(1, Math.trunc(Number(e.target.value) || 1))
                    )
                  )
                }
              />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={iniciar}
              disabled={ocupado || !fileCedulas || !fileDepositos}
            >
              {cargando && !cedulas.length ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Iniciar revisión
            </Button>
            {cedulas.length > 0 && !terminado ? (
              <Button
                variant="outline"
                onClick={() => cargar(idx, usados)}
                disabled={ocupado}
              >
                Recalcular con tolerancia / meses
              </Button>
            ) : null}
            <Button
              variant="outline"
              onClick={descargarResumen}
              disabled={ocupado || !historial.length}
            >
              <Download className="mr-2 h-4 w-4" />
              Descargar resumen
            </Button>
            {puedeDeshacer ? (
              <Button
                variant="destructive"
                onClick={deshacerUltima}
                disabled={ocupado}
              >
                <RotateCcw className="mr-2 h-4 w-4" />
                Deshacer última cédula
              </Button>
            ) : null}
          </div>
          {cedulas.length ? (
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">
                Cédula {Math.min(idx + 1, cedulas.length)} / {cedulas.length}
              </Badge>
              <Badge className="bg-emerald-600 hover:bg-emerald-600">
                Cédulas cargadas: {cargadas}
              </Badge>
              <Badge variant="secondary">Pagos cargados: {pagosCargados}</Badge>
              <Badge variant="secondary">
                Depósitos usados: {usados.length} / {deps.length}
              </Badge>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {terminado ? (
        <Card>
          <CardContent className="py-6 text-sm font-medium">
            Lista terminada: {cargadas} cédula(s) con carga, {pagosCargados}{' '}
            pago(s). Descarga el resumen.
          </CardContent>
        </Card>
      ) : null}

      {cargando && cedulas.length ? (
        <p className="flex items-center gap-2 text-sm">
          <Loader2 className="h-4 w-4 animate-spin" /> Cargando cédula…
        </p>
      ) : null}

      {revision && !cargando && !terminado ? (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-base font-semibold">
              {revision.cedula}
              {revision.cliente ? ` · ${revision.cliente}` : ''}
              {revision.prestamo_id
                ? ` · Préstamo ${revision.prestamo_id}`
                : ''}
            </p>
            {revision.estado !== 'CON_CANDIDATOS' ? (
              <Badge variant="secondary">{revision.detalle}</Badge>
            ) : null}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Cuotas (simulación con lo marcado)
                </CardTitle>
              </CardHeader>
              <CardContent className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>#</TableHead>
                      <TableHead>Vence</TableHead>
                      <TableHead className="text-right">Monto</TableHead>
                      <TableHead className="text-right">Pagado</TableHead>
                      <TableHead className="text-right">Falta</TableHead>
                      <TableHead className="text-right">Aplica</TableHead>
                      <TableHead className="text-right">Queda</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {revision.cuotas.map(c => {
                      const aplica = simulacion.aplica.get(c.id) || 0
                      const queda = simulacion.falta.get(c.id) ?? c.falta
                      const cubierta = c.falta > 0.01 && queda <= 0.01
                      return (
                        <TableRow
                          key={c.id}
                          className={
                            cubierta
                              ? 'bg-emerald-50'
                              : c.atrasada
                                ? 'bg-red-50'
                                : undefined
                          }
                        >
                          <TableCell className="text-sm">{c.numero}</TableCell>
                          <TableCell className="text-sm">
                            {c.vencimiento}
                          </TableCell>
                          <TableCell className="text-right text-sm">
                            {money(c.monto)}
                          </TableCell>
                          <TableCell className="text-right text-sm">
                            {money(c.pagado)}
                          </TableCell>
                          <TableCell className="text-right text-sm">
                            {money(c.falta)}
                          </TableCell>
                          <TableCell className="text-right text-sm font-medium text-emerald-700">
                            {aplica > 0 ? money(aplica) : ''}
                          </TableCell>
                          <TableCell className="text-right text-sm">
                            {c.falta > 0.01 ? money(queda) : '—'}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
                <div className="mt-3 flex flex-wrap gap-2 text-sm">
                  <Badge variant="outline">
                    Marcado: ${money(simulacion.total)}
                  </Badge>
                  <Badge variant="outline">
                    Falta atrasadas: ${money(simulacion.faltaAtrasadas)}
                  </Badge>
                  <Badge variant="outline">
                    Atrasadas cubiertas: {simulacion.cubiertas} /{' '}
                    {revision.cuotas.filter(c => c.atrasada).length}
                  </Badge>
                  {simulacion.sobrante > 0.01 ? (
                    <Badge className="bg-amber-500 hover:bg-amber-500">
                      Sobrante sin cuota: ${money(simulacion.sobrante)}
                    </Badge>
                  ) : null}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  Depósitos por mes (±{tolerancia}% de la cuota · un depósito
                  por mes)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {!revision.bloques.length ? (
                  <p className="text-sm text-muted-foreground">
                    Sin cuotas atrasadas.
                  </p>
                ) : null}
                {revision.bloques.map(b => (
                  <div key={b.cuota_id} className="rounded-md border p-3">
                    <p className="mb-2 text-sm font-semibold">
                      Cuota #{b.cuota_numero} · vence {b.vencimiento} · $
                      {money(b.monto)}
                    </p>
                    <div className="space-y-2">
                      {b.meses.map(mb => {
                        const elegido = seleccion[mb.clave]
                        const elegidoAqui = mb.candidatos.some(
                          c => c.deposito_id === elegido
                        )
                        return (
                          <div key={mb.clave}>
                            <p className="text-xs font-medium text-muted-foreground">
                              {mb.mes}
                              {elegido !== undefined && !elegidoAqui
                                ? ' · mes ya usado con otro depósito'
                                : ''}
                            </p>
                            {mb.candidatos.length ? (
                              mb.candidatos.map(c => {
                                const marcado = elegido === c.deposito_id
                                const dif = b.monto
                                  ? ((c.monto - b.monto) / b.monto) * 100
                                  : 0
                                return (
                                  <label
                                    key={c.deposito_id}
                                    className={`flex cursor-pointer items-center gap-2 rounded px-2 py-1 font-mono text-xs ${
                                      marcado
                                        ? 'bg-emerald-100'
                                        : 'hover:bg-muted'
                                    }`}
                                  >
                                    <input
                                      type="checkbox"
                                      checked={marcado}
                                      disabled={ocupado}
                                      onChange={() =>
                                        alternar(mb.clave, c.deposito_id)
                                      }
                                    />
                                    <span>{c.fecha}</span>
                                    <span>{c.serial}</span>
                                    <span className="ml-auto">
                                      ${money(c.monto)}
                                    </span>
                                    <span className="w-14 text-right text-muted-foreground">
                                      {dif >= 0 ? '+' : ''}
                                      {dif.toFixed(0)}%
                                    </span>
                                  </label>
                                )
                              })
                            ) : (
                              <p className="px-2 text-xs text-muted-foreground">
                                —
                              </p>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button
              className="bg-emerald-600 hover:bg-emerald-700"
              onClick={procesar}
              disabled={ocupado}
            >
              {guardando ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              {marcados.length && revision.prestamo_id
                ? `Procesar ${marcados.length} depósito(s) y siguiente`
                : 'Siguiente sin cargar'}
            </Button>
            <span className="text-xs text-muted-foreground">
              Se registra serial, fecha y monto (Mercantil, USD, imagen en
              blanco) y la cascada aplica desde la cuota pendiente más antigua.
            </span>
          </div>
        </>
      ) : null}
    </div>
  )
}

export default SerialesRevisionCedula
