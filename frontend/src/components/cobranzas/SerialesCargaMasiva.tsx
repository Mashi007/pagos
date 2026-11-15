/**
 * Cobranzas → Seriales, carga masiva de 5 en 5.
 * Simula 5 cédulas, el usuario marca los préstamos a aprobar y «Aprobar y cargar»
 * registra solo esos (misma asignación que la simulación); luego simula las 5 siguientes.
 */
import { useMemo, useState } from 'react'
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Download,
  Loader2,
  Play,
  RotateCcw,
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '../ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { Badge } from '../ui/badge'
import { Input } from '../ui/input'
import {
  cobranzasSerialesService,
  type SerialDepositoIn,
  type SerialEstadoCedula,
  type SerialLoteResponse,
  type SerialPagoCreado,
  type SerialResultadoCedula,
} from '../../services/cobranzasSerialesService'
import {
  errMsg,
  leerCedulas,
  leerDepositos,
  type DepositoFila,
} from '../../utils/serialesExcel'

const TAM_LOTE = 5

const ESTADO_LABEL: Record<SerialEstadoCedula, string> = {
  COMPLETO: 'Completo',
  PARCIAL: 'Parcial',
  SIN_COINCIDENCIA: 'Sin coincidencia',
  SIN_ATRASO: 'Sin cuotas atrasadas',
  CEDULA_INVALIDA: 'Cédula inválida',
}

type Historial = SerialResultadoCedula & {
  resultado: 'CARGADA' | 'OMITIDA' | 'DESHECHA'
  lote: number
}

function money(n: number) {
  return n.toLocaleString('es-EC', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

function badgeEstado(estado: SerialEstadoCedula) {
  if (estado === 'COMPLETO')
    return (
      <Badge className="bg-emerald-600 hover:bg-emerald-600">
        {ESTADO_LABEL[estado]}
      </Badge>
    )
  if (estado === 'PARCIAL')
    return (
      <Badge className="bg-amber-500 hover:bg-amber-500">
        {ESTADO_LABEL[estado]}
      </Badge>
    )
  if (estado === 'SIN_COINCIDENCIA')
    return <Badge variant="destructive">{ESTADO_LABEL[estado]}</Badge>
  return <Badge variant="secondary">{ESTADO_LABEL[estado] || estado}</Badge>
}

const montoPagos = (pagos: SerialPagoCreado[]) =>
  pagos.reduce((s, p) => s + p.monto, 0)

function TablaPagos({ pagos }: { pagos: SerialPagoCreado[] }) {
  return (
    <div className="overflow-x-auto rounded-md border border-slate-200">
      <table className="w-full min-w-[640px] text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">Cuota</th>
            <th className="px-3 py-2 font-medium">Mes</th>
            <th className="px-3 py-2 font-medium">Fecha depósito</th>
            <th className="px-3 py-2 font-medium">Serial</th>
            <th className="px-3 py-2 text-right font-medium">Monto</th>
            <th className="px-3 py-2 text-right font-medium">Falta antes</th>
            <th className="px-3 py-2 font-medium">Otras opciones</th>
          </tr>
        </thead>
        <tbody>
          {pagos.map((p, i) => (
            <tr
              key={p.deposito_id}
              className={i % 2 === 0 ? 'bg-white' : 'bg-slate-50/70'}
            >
              <td className="px-3 py-2">
                <span className="font-semibold">#{p.cuota_numero}</span>
                <span className="ml-1 text-xs text-muted-foreground">
                  vence {p.cuota_vencimiento}
                </span>
              </td>
              <td className="px-3 py-2">{p.mes}</td>
              <td className="px-3 py-2">{p.fecha_deposito}</td>
              <td className="px-3 py-2 font-mono text-xs">{p.serial}</td>
              <td className="px-3 py-2 text-right font-semibold tabular-nums text-emerald-700">
                ${money(p.monto)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums text-slate-600">
                ${money(p.saldo_cuota_antes)}
              </td>
              <td className="px-3 py-2">
                {p.alternativas > 0 ? (
                  <span className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                    +{p.alternativas} en el mes
                  </span>
                ) : (
                  <span className="text-xs text-muted-foreground">única</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function SerialesCargaMasiva() {
  const [fileCedulas, setFileCedulas] = useState<File | null>(null)
  const [fileDepositos, setFileDepositos] = useState<File | null>(null)
  const [tolerancia, setTolerancia] = useState(20)
  const [maxMeses, setMaxMeses] = useState(2)
  const [cedulas, setCedulas] = useState<string[]>([])
  const [deps, setDeps] = useState<DepositoFila[]>([])
  const [lote, setLote] = useState(0)
  const [sim, setSim] = useState<SerialLoteResponse | null>(null)
  const [marcadas, setMarcadas] = useState<Record<number, boolean>>({})
  const [abiertas, setAbiertas] = useState<Record<number, boolean>>({})
  const [cargados, setCargados] = useState<number[]>([])
  const [enBd, setEnBd] = useState<number[]>([])
  const [enOtras, setEnOtras] = useState<number[]>([])
  const [historial, setHistorial] = useState<Historial[]>([])
  const [verHistorial, setVerHistorial] = useState(false)
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState<string | null>(null)

  const totalLotes = Math.ceil(cedulas.length / TAM_LOTE)
  const iniciado = cedulas.length > 0
  const terminado = iniciado && lote >= totalLotes

  const payloadDeps: SerialDepositoIn[] = useMemo(
    () =>
      deps.map(d => ({
        id: d.id,
        fecha: d.fecha,
        serial: d.serial,
        monto: d.monto,
      })),
    [deps]
  )

  const filaPorDeposito = useMemo(() => {
    const m = new Map<number, number>()
    for (const d of deps) m.set(d.id, d.filaExcel)
    return m
  }, [deps])

  const totales = useMemo(() => {
    const cargadas = historial.filter(h => h.resultado === 'CARGADA')
    return {
      cedulas: cargadas.length,
      omitidas: historial.filter(h => h.resultado === 'OMITIDA').length,
      pagos: cargadas.reduce((s, h) => s + h.pagos.length, 0),
      monto: cargadas.reduce((s, h) => s + montoPagos(h.pagos), 0),
    }
  }, [historial])

  const seleccionadas = (sim?.resultados || []).filter(
    (r, i) => marcadas[i] && r.pagos.length > 0
  )
  const montoSeleccion = seleccionadas.reduce(
    (s, r) => s + montoPagos(r.pagos),
    0
  )
  const pagosSeleccion = seleccionadas.reduce((s, r) => s + r.pagos.length, 0)

  function acumularDescartes(res: SerialLoteResponse) {
    setEnBd(prev => [...new Set([...prev, ...res.depositos_serial_en_bd])])
    setEnOtras(prev => [
      ...new Set([...prev, ...(res.depositos_en_otras_tablas || [])]),
    ])
  }

  async function simularLote(
    i: number,
    cargadosActuales: number[],
    lista = cedulas,
    depsPayload = payloadDeps
  ) {
    setLote(i)
    setSim(null)
    setMarcadas({})
    setAbiertas({})
    const total = Math.ceil(lista.length / TAM_LOTE)
    if (i >= total) {
      toast.success('Lista terminada.')
      return
    }
    const desde = i * TAM_LOTE
    const chunk = lista.slice(desde, desde + TAM_LOTE)
    setProgress(
      `Simulando lote ${i + 1} / ${total} · cédulas ${desde + 1}–${desde + chunk.length} de ${lista.length}…`
    )
    const res = await cobranzasSerialesService.procesarLote({
      cedulas: chunk,
      depositos: depsPayload,
      usados: cargadosActuales,
      simular: true,
      tolerancia_pct: tolerancia,
      max_meses_adelante: maxMeses,
    })
    acumularDescartes(res)
    setSim(res)
    const m: Record<number, boolean> = {}
    res.resultados.forEach((r, k) => {
      m[k] = r.pagos.length > 0
    })
    setMarcadas(m)
    setProgress(null)
  }

  async function iniciar() {
    if (!fileCedulas || !fileDepositos) {
      toast.error('Sube el Excel de cédulas y el Excel de depósitos.')
      return
    }
    if (
      historial.length &&
      !window.confirm(
        'Se reinicia la lista desde la primera cédula (lo ya cargado queda en BD). ¿Continuar?'
      )
    )
      return
    setRunning(true)
    try {
      setProgress('Leyendo archivos…')
      const lista = await leerCedulas(fileCedulas)
      const d = await leerDepositos(fileDepositos)
      const sinFecha = d.filter(
        x =>
          !/^\d{4}-\d{2}-\d{2}$/.test(x.fecha) &&
          !/^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$/.test(x.fecha)
      )
      if (sinFecha.length) {
        toast.warning(
          `${sinFecha.length} depósito(s) con fecha no reconocida (p. ej. fila ${sinFecha[0].filaExcel}: "${sinFecha[0].fecha}"); no se usarán.`
        )
      }
      const payload = d.map(x => ({
        id: x.id,
        fecha: x.fecha,
        serial: x.serial,
        monto: x.monto,
      }))
      setCedulas(lista)
      setDeps(d)
      setCargados([])
      setEnBd([])
      setEnOtras([])
      setHistorial([])
      await simularLote(0, [], lista, payload)
    } catch (err) {
      setProgress(null)
      toast.error(errMsg(err))
    } finally {
      setRunning(false)
    }
  }

  async function aprobar() {
    if (!sim) return
    const resultados = sim.resultados
    const elegidas = resultados.filter(
      (r, i) => marcadas[i] && r.pagos.length > 0
    )
    const omitidas = resultados.filter(
      (r, i) => !(marcadas[i] && r.pagos.length > 0)
    )
    setRunning(true)
    try {
      let nuevosCargados = cargados
      const nuevasFilas: Historial[] = []
      if (elegidas.length) {
        setProgress(
          `Cargando ${elegidas.length} préstamo(s) del lote ${lote + 1}…`
        )
        // Los depósitos que la simulación dio a las omitidas se excluyen para que
        // las aprobadas reciban exactamente lo simulado.
        const reservados = omitidas.flatMap(r =>
          r.pagos.map(p => p.deposito_id)
        )
        const res = await cobranzasSerialesService.procesarLote({
          cedulas: elegidas.map(r => r.cedula),
          depositos: payloadDeps,
          usados: [...cargados, ...reservados],
          simular: false,
          tolerancia_pct: tolerancia,
          max_meses_adelante: maxMeses,
        })
        acumularDescartes(res)
        nuevosCargados = [...cargados, ...res.depositos_usados]
        const distintas = res.resultados.filter((r, k) => {
          const a = r.pagos.map(p => p.deposito_id).join(',')
          const b = elegidas[k]?.pagos.map(p => p.deposito_id).join(',')
          return a !== b
        })
        if (distintas.length) {
          toast.warning(
            `${distintas.length} préstamo(s) quedaron con una asignación distinta a la simulada (cambió la BD); revisa el historial.`
          )
        }
        for (const r of res.resultados)
          nuevasFilas.push({ ...r, resultado: 'CARGADA', lote })
        toast.success(
          `Lote ${lote + 1}: ${res.pagos_creados} pago(s) cargados en ${res.resultados.length} préstamo(s).`
        )
      }
      for (const r of omitidas)
        nuevasFilas.push({
          ...r,
          pagos: [],
          resultado: 'OMITIDA',
          lote,
          detalle:
            r.pagos.length > 0
              ? 'No aprobada (omitida por el usuario)'
              : r.detalle,
        })
      setCargados(nuevosCargados)
      setHistorial(prev => [...prev, ...nuevasFilas])
      await simularLote(lote + 1, nuevosCargados)
    } catch (err) {
      setProgress(null)
      toast.error(errMsg(err))
    } finally {
      setRunning(false)
    }
  }

  async function deshacer(soloUltimoLote: boolean) {
    const ultimoLote = Math.max(
      -1,
      ...historial
        .filter(h => h.resultado === 'CARGADA' && h.pagos.length)
        .map(h => h.lote)
    )
    const objetivo = historial.filter(
      h =>
        h.resultado === 'CARGADA' &&
        h.pagos.length &&
        (!soloUltimoLote || h.lote === ultimoLote)
    )
    const ids = objetivo.flatMap(h =>
      h.pagos
        .map(p => p.pago_id)
        .filter((x): x is number => typeof x === 'number')
    )
    if (!ids.length) return
    const ok = window.confirm(
      `Se eliminarán ${ids.length} pago(s) de ${objetivo.length} préstamo(s)${soloUltimoLote ? ` (lote ${ultimoLote + 1})` : ''} y se recalcularán sus cuotas. ¿Continuar?`
    )
    if (!ok) return
    setRunning(true)
    let eliminados: number[] = []
    try {
      for (let i = 0; i < ids.length; i += 100) {
        setProgress(
          `Deshaciendo ${Math.min(i + 100, ids.length)} / ${ids.length}…`
        )
        const res = await cobranzasSerialesService.deshacer(
          ids.slice(i, i + 100)
        )
        eliminados = [...eliminados, ...res.eliminados]
      }
      const borrados = new Set(eliminados)
      const liberados = new Set(
        objetivo.flatMap(h =>
          h.pagos
            .filter(p => p.pago_id != null && borrados.has(p.pago_id))
            .map(p => p.deposito_id)
        )
      )
      setCargados(prev => prev.filter(id => !liberados.has(id)))
      setHistorial(prev =>
        prev.map(h =>
          objetivo.includes(h)
            ? { ...h, resultado: 'DESHECHA', detalle: 'Carga deshecha' }
            : h
        )
      )
      if (eliminados.length === ids.length) {
        toast.success(`${eliminados.length} pago(s) eliminados.`)
      } else {
        toast.warning(
          `Eliminados ${eliminados.length} de ${ids.length}; revisa los restantes.`
        )
      }
    } catch (err) {
      toast.error(
        `${errMsg(err)} (eliminados hasta ahora: ${eliminados.length})`
      )
    } finally {
      setProgress(null)
      setRunning(false)
    }
  }

  async function descargarHistorial() {
    const { createAndDownloadExcel } = await import('../../types/exceljs')
    const filas: Record<string, unknown>[] = []
    for (const h of historial) {
      const base = {
        Lote: h.lote + 1,
        Resultado: h.resultado,
        Cedula: h.cedula,
        Prestamo: h.prestamo_id ?? '',
        Estado: ESTADO_LABEL[h.estado] || h.estado,
        Cubiertas: `${h.cuotas_cubiertas}/${h.cuotas_atrasadas}`,
      }
      if (!h.pagos.length) {
        filas.push({ ...base, Detalle: h.detalle })
        continue
      }
      for (const p of h.pagos)
        filas.push({
          ...base,
          Cuota: p.cuota_numero,
          Vencimiento: p.cuota_vencimiento,
          'Falta antes': p.saldo_cuota_antes,
          Mes: p.mes,
          Deposito: p.fecha_deposito,
          Serial: p.serial,
          Monto: p.monto,
          'Fila deposito': filaPorDeposito.get(p.deposito_id) ?? '',
          'Pago ID': p.pago_id ?? '',
          Detalle: h.detalle,
        })
    }
    await createAndDownloadExcel(
      filas,
      'Seriales',
      'Cobranzas_Seriales_carga_masiva.xlsx'
    )
  }

  async function descargarNoUsados() {
    const { createAndDownloadExcel } = await import('../../types/exceljs')
    const usados = new Set(cargados)
    const bd = new Set(enBd)
    const otras = new Set(enOtras)
    const filas = deps
      .filter(d => !usados.has(d.id))
      .map(d => ({
        Fila: d.filaExcel,
        Deposito: d.fecha,
        Referencia: d.serial,
        Monto: d.monto,
        Motivo: bd.has(d.id)
          ? 'Serial ya registrado en BD'
          : otras.has(d.id)
            ? 'En pagos reportados / confirmados'
            : 'Sin asignar',
      }))
    await createAndDownloadExcel(
      filas,
      'No usados',
      'Cobranzas_Seriales_depositos_no_usados.xlsx'
    )
  }

  const hayCargas = historial.some(
    h => h.resultado === 'CARGADA' && h.pagos.length
  )
  const desde = lote * TAM_LOTE

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Archivos y opciones</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1">
              <p className="text-sm font-medium">1. Cédulas (columna A)</p>
              <Input
                type="file"
                accept=".xlsx"
                disabled={running}
                onChange={e => setFileCedulas(e.target.files?.[0] || null)}
              />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">
                2. Depósitos (A Deposito · B Referencia · C Monto)
              </p>
              <Input
                type="file"
                accept=".xlsx"
                disabled={running}
                onChange={e => setFileDepositos(e.target.files?.[0] || null)}
              />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">Tolerancia de monto (±%)</p>
              <Input
                type="number"
                min={0}
                max={50}
                value={tolerancia}
                disabled={running}
                className="max-w-[10rem]"
                onChange={e =>
                  setTolerancia(
                    Math.min(50, Math.max(0, Number(e.target.value) || 0))
                  )
                }
              />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">
                Meses de búsqueda después del vencimiento (0 = sin límite)
              </p>
              <Input
                type="number"
                min={0}
                max={24}
                value={maxMeses}
                disabled={running}
                className="max-w-[10rem]"
                onChange={e =>
                  setMaxMeses(
                    Math.min(
                      24,
                      Math.max(0, Math.trunc(Number(e.target.value) || 0))
                    )
                  )
                }
              />
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            Se simulan {TAM_LOTE} cédulas a la vez. Marcas los préstamos que
            apruebas y pulsas «Aprobar y cargar»: se registran solo esos (con la
            misma asignación simulada) y aparecen las {TAM_LOTE} siguientes. Un
            depósito por mes; cada cuota toma el más cercano a lo que le falta
            dentro de ±{tolerancia}%. Un serial cargado no se vuelve a usar.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={iniciar}
              disabled={running || !fileCedulas || !fileDepositos}
            >
              {running && !iniciado ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              {iniciado ? 'Reiniciar desde el principio' : 'Iniciar'}
            </Button>
            <Button
              variant="outline"
              onClick={descargarHistorial}
              disabled={running || !historial.length}
            >
              <Download className="mr-2 h-4 w-4" />
              Descargar historial
            </Button>
            <Button
              variant="outline"
              onClick={descargarNoUsados}
              disabled={running || !deps.length}
            >
              <Download className="mr-2 h-4 w-4" />
              Depósitos no usados
            </Button>
            {hayCargas ? (
              <>
                <Button
                  variant="outline"
                  className="border-red-300 text-red-700 hover:bg-red-50"
                  onClick={() => deshacer(true)}
                  disabled={running}
                >
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Deshacer último lote
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => deshacer(false)}
                  disabled={running}
                >
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Deshacer todo
                </Button>
              </>
            ) : null}
          </div>
          {iniciado ? (
            <div className="space-y-2">
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full bg-emerald-500 transition-all"
                  style={{
                    width: `${Math.min(100, (Math.min(lote, totalLotes) / Math.max(1, totalLotes)) * 100)}%`,
                  }}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">
                  Lote {Math.min(lote + 1, totalLotes)} / {totalLotes}
                </Badge>
                <Badge variant="outline">
                  Cédulas revisadas: {Math.min(desde, cedulas.length)} /{' '}
                  {cedulas.length}
                </Badge>
                <Badge className="bg-emerald-600 hover:bg-emerald-600">
                  Préstamos cargados: {totales.cedulas}
                </Badge>
                <Badge variant="secondary">
                  Pagos: {totales.pagos} · ${money(totales.monto)}
                </Badge>
                <Badge variant="secondary">Omitidas: {totales.omitidas}</Badge>
                <Badge variant="secondary">
                  Depósitos usados: {cargados.length} / {deps.length}
                </Badge>
              </div>
            </div>
          ) : null}
          {progress ? (
            <p className="flex items-center gap-2 text-sm font-medium">
              <Loader2 className="h-4 w-4 animate-spin" /> {progress}
            </p>
          ) : null}
        </CardContent>
      </Card>

      {iniciado && !terminado && !sim && !running ? (
        <Card>
          <CardContent className="flex flex-wrap items-center gap-3 py-4">
            <p className="text-sm">
              No se pudo simular el lote {lote + 1}. Puedes reintentar.
            </p>
            <Button
              variant="outline"
              onClick={async () => {
                setRunning(true)
                try {
                  await simularLote(lote, cargados)
                } catch (err) {
                  setProgress(null)
                  toast.error(errMsg(err))
                } finally {
                  setRunning(false)
                }
              }}
            >
              Reintentar lote {lote + 1}
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {terminado ? (
        <Card className="border-emerald-300 bg-emerald-50">
          <CardContent className="py-5 text-sm font-medium text-emerald-900">
            Lista terminada: {totales.cedulas} préstamo(s) cargados,{' '}
            {totales.pagos} pago(s) por ${money(totales.monto)}.{' '}
            {totales.omitidas} omitida(s). Descarga el historial.
          </CardContent>
        </Card>
      ) : null}

      {sim && !terminado ? (
        <Card className="border-amber-300">
          <CardHeader className="flex flex-col gap-2 space-y-0 md:flex-row md:items-center md:justify-between">
            <div>
              <CardTitle className="text-base">
                Simulación · lote {lote + 1} de {totalLotes} · cédulas{' '}
                {desde + 1}–{desde + sim.resultados.length}
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Nada se ha guardado. Marca los préstamos que apruebas.
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                disabled={running}
                onClick={() => {
                  const m: Record<number, boolean> = {}
                  sim.resultados.forEach((r, k) => {
                    m[k] = r.pagos.length > 0
                  })
                  setMarcadas(m)
                }}
              >
                Marcar todos
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={running}
                onClick={() => setMarcadas({})}
              >
                Ninguno
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {sim.resultados.map((r, k) => {
              const conPagos = r.pagos.length > 0
              const marcado = !!marcadas[k] && conPagos
              const abierta = !!abiertas[k]
              const alts = r.pagos.filter(p => p.alternativas > 0).length
              return (
                <div
                  key={`${k}-${r.cedula}`}
                  className={`rounded-md border ${
                    marcado
                      ? 'border-emerald-300 bg-emerald-50/40'
                      : 'border-slate-200 bg-white'
                  }`}
                >
                  <div className="flex items-start gap-3 px-3 py-3">
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4"
                      checked={marcado}
                      disabled={!conPagos || running}
                      onChange={e =>
                        setMarcadas(prev => ({
                          ...prev,
                          [k]: e.target.checked,
                        }))
                      }
                      aria-label={`Aprobar ${r.cedula}`}
                    />
                    <button
                      type="button"
                      className="flex min-w-0 flex-1 items-start gap-2 text-left"
                      onClick={() =>
                        setAbiertas(prev => ({ ...prev, [k]: !prev[k] }))
                      }
                      disabled={!conPagos}
                    >
                      <span className="mt-0.5 text-slate-500">
                        {conPagos ? (
                          abierta ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )
                        ) : null}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-sm font-semibold">
                            {r.cedula}
                          </span>
                          <span className="text-sm text-muted-foreground">
                            Préstamo {r.prestamo_id ?? '—'}
                          </span>
                          {badgeEstado(r.estado)}
                          {alts > 0 ? (
                            <Badge className="bg-amber-500 hover:bg-amber-500">
                              {alts} con opciones
                            </Badge>
                          ) : null}
                        </div>
                        <p className="mt-1 text-sm text-slate-700">
                          Cubiertas {r.cuotas_cubiertas}/{r.cuotas_atrasadas}
                          {conPagos
                            ? ` · ${r.pagos.length} pago(s) · $${money(montoPagos(r.pagos))}`
                            : ''}
                        </p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {r.detalle}
                        </p>
                      </div>
                    </button>
                  </div>
                  {abierta && conPagos ? (
                    <div className="border-t border-slate-100 px-3 py-3">
                      <TablaPagos pagos={r.pagos} />
                    </div>
                  ) : null}
                </div>
              )
            })}

            <div className="sticky bottom-3 z-10 mt-3 rounded-lg border border-emerald-300 bg-emerald-50 p-3 shadow-md">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <p className="text-sm font-medium text-emerald-900">
                  {seleccionadas.length
                    ? `Se cargarán ${seleccionadas.length} préstamo(s), ${pagosSeleccion} pago(s) por $${money(montoSeleccion)} y se aplicará la cascada.`
                    : 'Ningún préstamo marcado: se pasará a las siguientes cédulas sin cargar.'}
                </p>
                <Button
                  className="bg-emerald-600 hover:bg-emerald-700"
                  onClick={aprobar}
                  disabled={running}
                >
                  {running ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                  )}
                  {seleccionadas.length
                    ? `Aprobar y cargar (${seleccionadas.length})`
                    : 'Siguientes 5 sin cargar'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {historial.length ? (
        <Card>
          <CardHeader>
            <button
              type="button"
              className="flex items-center gap-2 text-left"
              onClick={() => setVerHistorial(v => !v)}
            >
              {verHistorial ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              <CardTitle className="text-base">
                Historial · {historial.length} cédula(s) revisadas
              </CardTitle>
            </button>
          </CardHeader>
          {verHistorial ? (
            <CardContent className="overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-3 py-2 font-medium">Lote</th>
                    <th className="px-3 py-2 font-medium">Cédula</th>
                    <th className="px-3 py-2 font-medium">Préstamo</th>
                    <th className="px-3 py-2 font-medium">Resultado</th>
                    <th className="px-3 py-2 text-right font-medium">Pagos</th>
                    <th className="px-3 py-2 text-right font-medium">Monto</th>
                    <th className="px-3 py-2 font-medium">Detalle</th>
                  </tr>
                </thead>
                <tbody>
                  {[...historial].reverse().map((h, i) => (
                    <tr
                      key={`${h.lote}-${h.cedula}-${i}`}
                      className={i % 2 === 0 ? 'bg-white' : 'bg-slate-50/70'}
                    >
                      <td className="px-3 py-2">{h.lote + 1}</td>
                      <td className="px-3 py-2 font-mono text-xs">
                        {h.cedula}
                      </td>
                      <td className="px-3 py-2">{h.prestamo_id ?? '—'}</td>
                      <td className="px-3 py-2">
                        {h.resultado === 'CARGADA' ? (
                          <Badge className="bg-emerald-600 hover:bg-emerald-600">
                            Cargada
                          </Badge>
                        ) : h.resultado === 'DESHECHA' ? (
                          <Badge variant="destructive">Deshecha</Badge>
                        ) : (
                          <Badge variant="secondary">Omitida</Badge>
                        )}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums">
                        {h.pagos.length}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums">
                        {h.pagos.length
                          ? `$${money(montoPagos(h.pagos))}`
                          : '—'}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {h.detalle}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          ) : null}
        </Card>
      ) : null}
    </div>
  )
}

export default SerialesCargaMasiva
