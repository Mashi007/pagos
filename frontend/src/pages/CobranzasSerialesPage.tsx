/**
 * Cobranzas → Seriales (solo itmaster@). Pestaña «Revisión por cédula»
 * (SerialesRevisionCedula) y pestaña «Carga masiva» (abajo).
 * Archivo 1: cédulas (columna A). Archivo 2: depósitos (Deposito | Referencia | Monto).
 * Por cada cédula (orden del archivo, lotes de 20) toma el préstamo con la cuota
 * atrasada más antigua. Un depósito por mes: cada cuota busca desde el mes de su
 * vencimiento el depósito más cercano a lo que le falta (±20%); si el mes no tiene,
 * sigue con el siguiente. Banco Mercantil, USD, comprobante en blanco; cascada normal.
 */
import { useMemo, useState } from 'react'
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Download,
  FileSpreadsheet,
  Eye,
  Loader2,
  RotateCcw,
} from 'lucide-react'
import { toast } from 'sonner'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Input } from '../components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { SerialesRevisionCedula } from '../components/cobranzas/SerialesRevisionCedula'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'
import {
  cobranzasSerialesService,
  type SerialDepositoIn,
  type SerialEstadoCedula,
  type SerialResultadoCedula,
} from '../services/cobranzasSerialesService'
import {
  errMsg,
  leerCedulas,
  leerDepositos,
  type DepositoFila,
} from '../utils/serialesExcel'

const LOTE_PRESTAMOS = 20

const ESTADO_LABEL: Record<SerialEstadoCedula, string> = {
  COMPLETO: 'Completo',
  PARCIAL: 'Parcial',
  SIN_COINCIDENCIA: 'Sin coincidencia',
  SIN_ATRASO: 'Sin cuotas atrasadas',
  CEDULA_INVALIDA: 'Cédula inválida',
}

function moneyFmt(n: number) {
  return n.toLocaleString('es-EC', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

type FiltroResultado = 'TODAS' | SerialEstadoCedula | 'CON_ALTERNATIVAS'

function badgeEstado(estado: SerialEstadoCedula) {
  if (estado === 'COMPLETO') {
    return (
      <Badge className="bg-emerald-600 hover:bg-emerald-600">
        {ESTADO_LABEL[estado]}
      </Badge>
    )
  }
  if (estado === 'PARCIAL') {
    return (
      <Badge className="bg-amber-500 hover:bg-amber-500">
        {ESTADO_LABEL[estado]}
      </Badge>
    )
  }
  if (estado === 'SIN_COINCIDENCIA') {
    return <Badge variant="destructive">{ESTADO_LABEL[estado]}</Badge>
  }
  return <Badge variant="secondary">{ESTADO_LABEL[estado] || estado}</Badge>
}

type Modo = 'simulacion' | 'real' | null

function firmaArchivo(f: File | null): string {
  return f ? `${f.name}|${f.size}|${f.lastModified}` : ''
}

export function CobranzasSerialesPage() {
  const [tab, setTab] = useState('revision')
  const [fileCedulas, setFileCedulas] = useState<File | null>(null)
  const [fileDepositos, setFileDepositos] = useState<File | null>(null)
  const [tolerancia, setTolerancia] = useState(20)
  const [maxMeses, setMaxMeses] = useState(2)
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState<string | null>(null)
  const [resultados, setResultados] = useState<SerialResultadoCedula[]>([])
  const [depositos, setDepositos] = useState<DepositoFila[]>([])
  const [usados, setUsados] = useState<number[]>([])
  const [serialEnBd, setSerialEnBd] = useState<number[]>([])
  const [enOtras, setEnOtras] = useState<number[]>([])
  const [modo, setModo] = useState<Modo>(null)
  const [firmaSimulada, setFirmaSimulada] = useState<string | null>(null)
  const [deshecho, setDeshecho] = useState(false)
  const [filtro, setFiltro] = useState<FiltroResultado>('TODAS')
  const [abiertas, setAbiertas] = useState<Record<string, boolean>>({})

  const firmaActual = `${firmaArchivo(fileCedulas)}#${firmaArchivo(fileDepositos)}#${tolerancia}#${maxMeses}`
  const puedeConfirmar =
    modo === 'simulacion' && firmaSimulada === firmaActual && !running

  const resumen = useMemo(() => {
    const r = {
      COMPLETO: 0,
      PARCIAL: 0,
      SIN_COINCIDENCIA: 0,
      SIN_ATRASO: 0,
      CEDULA_INVALIDA: 0,
    }
    let pagos = 0
    let conAlternativas = 0
    let monto = 0
    for (const x of resultados) {
      if (x.estado in r) r[x.estado as SerialEstadoCedula] += 1
      pagos += x.pagos.length
      conAlternativas += x.pagos.filter(p => p.alternativas > 0).length
      monto += x.pagos.reduce((s, p) => s + p.monto, 0)
    }
    return { ...r, pagos, conAlternativas, monto }
  }, [resultados])

  const resultadosFiltrados = useMemo(() => {
    if (filtro === 'TODAS') return resultados
    if (filtro === 'CON_ALTERNATIVAS')
      return resultados.filter(r => r.pagos.some(p => p.alternativas > 0))
    return resultados.filter(r => r.estado === filtro)
  }, [resultados, filtro])

  const filaPorDeposito = useMemo(() => {
    const m = new Map<number, number>()
    for (const d of depositos) m.set(d.id, d.filaExcel)
    return m
  }, [depositos])

  const pagoIdsReales = useMemo(
    () =>
      modo === 'real'
        ? resultados.flatMap(r =>
            r.pagos
              .map(p => p.pago_id)
              .filter((x): x is number => typeof x === 'number')
          )
        : [],
    [modo, resultados]
  )

  async function ejecutar(simular: boolean) {
    if (!fileCedulas || !fileDepositos) {
      toast.error('Sube el Excel de cédulas y el Excel de depósitos.')
      return
    }
    setRunning(true)
    try {
      setProgress('Leyendo archivos…')
      const cedulas = await leerCedulas(fileCedulas)
      const deps = await leerDepositos(fileDepositos)
      const sinFecha = deps.filter(
        d =>
          !/^\d{4}-\d{2}-\d{2}$/.test(d.fecha) &&
          !/^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$/.test(d.fecha)
      )
      if (sinFecha.length) {
        toast.warning(
          `${sinFecha.length} depósito(s) con fecha no reconocida (p. ej. fila ${sinFecha[0].filaExcel}: "${sinFecha[0].fecha}"); no se usarán.`
        )
      }

      if (!simular) {
        const ok = window.confirm(
          `Se registrarán en BD los pagos de ${cedulas.length} cédula(s) contra ${deps.length} depósito(s), en lotes de ${LOTE_PRESTAMOS}.\n` +
            'Mercantil, USD, comprobante en blanco y cascada. ¿Continuar?'
        )
        if (!ok) {
          setProgress(null)
          return
        }
      }

      setDepositos(deps)
      setResultados([])
      setUsados([])
      setSerialEnBd([])
      setEnOtras([])
      setDeshecho(false)
      setAbiertas({})
      setFiltro('TODAS')
      setModo(simular ? 'simulacion' : 'real')
      if (!simular) setFirmaSimulada(null)

      const payloadDeps: SerialDepositoIn[] = deps.map(d => ({
        id: d.id,
        fecha: d.fecha,
        serial: d.serial,
        monto: d.monto,
      }))
      const lotes = Math.ceil(cedulas.length / LOTE_PRESTAMOS)
      let usadosAcum: number[] = []
      const enBdAcum = new Set<number>()
      const otrasAcum = new Set<number>()
      const acumulado: SerialResultadoCedula[] = []
      const etiqueta = simular ? 'Simulando' : 'Cargando'

      for (let li = 0; li < lotes; li++) {
        const desde = li * LOTE_PRESTAMOS
        const chunk = cedulas.slice(desde, desde + LOTE_PRESTAMOS)
        setProgress(
          `${etiqueta} lote ${li + 1} / ${lotes} · cédulas ${desde + 1}–${desde + chunk.length} de ${cedulas.length} · depósitos asignados: ${usadosAcum.length}`
        )
        const res = await cobranzasSerialesService.procesarLote({
          cedulas: chunk,
          depositos: payloadDeps,
          usados: usadosAcum,
          simular,
          tolerancia_pct: tolerancia,
          max_meses_adelante: maxMeses,
        })
        usadosAcum = [...usadosAcum, ...res.depositos_usados]
        for (const id of res.depositos_serial_en_bd) enBdAcum.add(id)
        for (const id of res.depositos_en_otras_tablas || []) otrasAcum.add(id)
        acumulado.push(...res.resultados)
        setResultados([...acumulado])
        setUsados([...usadosAcum])
        setSerialEnBd([...enBdAcum])
        setEnOtras([...otrasAcum])
      }
      setProgress(null)
      if (simular) {
        setFirmaSimulada(firmaActual)
        toast.success(
          `Simulación lista: ${usadosAcum.length} pago(s) propuestos para ${acumulado.length} cédula(s). Nada se guardó; revisa y pulsa «Confirmar y cargar».`
        )
      } else {
        toast.success(
          `Listo: ${acumulado.length} cédula(s), ${usadosAcum.length} pago(s) registrados.`
        )
      }
    } catch (err) {
      setProgress(null)
      toast.error(
        simular
          ? errMsg(err)
          : `${errMsg(err)} (lo ya registrado en lotes anteriores queda guardado)`
      )
    } finally {
      setRunning(false)
    }
  }

  async function deshacer() {
    if (!pagoIdsReales.length) return
    const ok = window.confirm(
      `Se eliminarán ${pagoIdsReales.length} pago(s) cargados en esta corrida y se recalcularán las cuotas de los préstamos. ¿Continuar?`
    )
    if (!ok) return
    setRunning(true)
    let eliminados = 0
    const fallos: string[] = []
    try {
      const TAM = 100
      for (let i = 0; i < pagoIdsReales.length; i += TAM) {
        setProgress(
          `Deshaciendo ${Math.min(i + TAM, pagoIdsReales.length)} / ${pagoIdsReales.length}…`
        )
        const res = await cobranzasSerialesService.deshacer(
          pagoIdsReales.slice(i, i + TAM)
        )
        eliminados += res.eliminados.length
        for (const e of res.errores) fallos.push(`#${e.pago_id}: ${e.error}`)
        for (const o of res.omitidos) fallos.push(`#${o.pago_id}: ${o.motivo}`)
      }
      setDeshecho(true)
      if (fallos.length) {
        toast.warning(
          `Eliminados ${eliminados}; ${fallos.length} con problema (p. ej. ${fallos[0]}).`
        )
      } else {
        toast.success(`Carga deshecha: ${eliminados} pago(s) eliminados.`)
      }
    } catch (err) {
      toast.error(`${errMsg(err)} (eliminados hasta ahora: ${eliminados})`)
    } finally {
      setProgress(null)
      setRunning(false)
    }
  }

  async function descargar() {
    const { createAndDownloadExcel } = await import('../types/exceljs')
    const tipo = modo === 'simulacion' ? 'SIMULACION' : 'CARGADO'
    const filasResultado: Record<string, unknown>[] = []
    for (const r of resultados) {
      const base = {
        Tipo: tipo,
        Cedula: r.cedula,
        Prestamo: r.prestamo_id ?? '',
        Estado: ESTADO_LABEL[r.estado] || r.estado,
        Cubiertas: `${r.cuotas_cubiertas}/${r.cuotas_atrasadas}`,
      }
      if (!r.pagos.length) {
        filasResultado.push({
          ...base,
          Cuota: '',
          Vencimiento: '',
          'Falta antes': '',
          Mes: '',
          Deposito: '',
          Serial: '',
          Monto: '',
          Alternativas: '',
          'Fila deposito': '',
          'Pago ID': '',
          Detalle: r.detalle,
        })
        continue
      }
      for (const p of r.pagos) {
        filasResultado.push({
          ...base,
          Cuota: p.cuota_numero,
          Vencimiento: p.cuota_vencimiento,
          'Falta antes': p.saldo_cuota_antes,
          Mes: p.mes,
          Deposito: p.fecha_deposito,
          Serial: p.serial,
          Monto: p.monto,
          Alternativas: p.alternativas,
          'Fila deposito': filaPorDeposito.get(p.deposito_id) ?? '',
          'Pago ID': p.pago_id ?? '',
          Detalle: r.detalle,
        })
      }
    }
    await createAndDownloadExcel(
      filasResultado,
      'Seriales',
      modo === 'simulacion'
        ? 'Cobranzas_Seriales_SIMULACION.xlsx'
        : 'Cobranzas_Seriales_resultado.xlsx'
    )
  }

  async function descargarNoUsados() {
    const { createAndDownloadExcel } = await import('../types/exceljs')
    const usadosSet = new Set(usados)
    const enBdSet = new Set(serialEnBd)
    const otrasSet = new Set(enOtras)
    const filas = depositos
      .filter(d => !usadosSet.has(d.id))
      .map(d => ({
        Fila: d.filaExcel,
        Deposito: d.fecha,
        Referencia: d.serial,
        Monto: d.monto,
        Motivo: enBdSet.has(d.id)
          ? 'Serial ya registrado en BD'
          : otrasSet.has(d.id)
            ? 'En pagos reportados / confirmados'
            : 'Sin asignar',
      }))
    if (!filas.length) {
      toast.info('Todos los depósitos fueron asignados.')
      return
    }
    await createAndDownloadExcel(
      filas,
      'No usados',
      'Cobranzas_Seriales_depositos_no_usados.xlsx'
    )
  }

  const libres = depositos.length - usados.length

  return (
    <div className="space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Seriales"
        description="Carga depósitos Mercantil a préstamos con cuotas atrasadas. Revisión por cédula: eliges a mano los depósitos de cada mes. Carga masiva: asignación automática con simulación previa."
        icon={FileSpreadsheet}
      />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="revision">Revisión por cédula</TabsTrigger>
          <TabsTrigger value="masiva">Carga masiva</TabsTrigger>
        </TabsList>
        <TabsContent value="revision" forceMount className="mt-4">
          <SerialesRevisionCedula />
        </TabsContent>
        <TabsContent value="masiva" forceMount className="mt-4 space-y-6">
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
                    onChange={e =>
                      setFileDepositos(e.target.files?.[0] || null)
                    }
                  />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium">
                    Tolerancia de monto (±%)
                  </p>
                  <Input
                    type="number"
                    min={0}
                    max={50}
                    step={1}
                    value={tolerancia}
                    disabled={running}
                    onChange={e =>
                      setTolerancia(
                        Math.min(50, Math.max(0, Number(e.target.value) || 0))
                      )
                    }
                    className="max-w-[10rem]"
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
                    step={1}
                    value={maxMeses}
                    disabled={running}
                    onChange={e =>
                      setMaxMeses(
                        Math.min(
                          24,
                          Math.max(0, Math.trunc(Number(e.target.value) || 0))
                        )
                      )
                    }
                    className="max-w-[10rem]"
                  />
                </div>
              </div>
              <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                <li>
                  Un solo préstamo por cédula: el de la cuota atrasada más
                  antigua.
                </li>
                <li>
                  Un depósito por mes y por préstamo. Cada cuota busca en el mes
                  de su vencimiento el depósito más cercano a lo que le falta
                  (exacto primero), dentro de ±{tolerancia}% (empate: fecha más
                  antigua). Si ese mes no tiene, pasa al siguiente, hasta{' '}
                  {maxMeses > 0
                    ? `${maxMeses} mes(es) después del vencimiento`
                    : 'el último mes del archivo'}
                  ; si no encuentra, se detiene ese préstamo.
                </li>
                <li>
                  Lo que falta o sobra lo ajusta la cascada (cuota 110 con
                  depósito 100: los 10 los cubre el siguiente depósito).
                </li>
                <li>
                  Se omiten seriales ya registrados en pagos, pagos con errores,
                  pagos reportados pendientes y pagos confirmados activos.
                </li>
              </ul>
              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={() => ejecutar(true)}
                  disabled={running || !fileCedulas || !fileDepositos}
                >
                  {running && modo !== 'real' ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Eye className="mr-2 h-4 w-4" />
                  )}
                  1. Simular (no guarda)
                </Button>
                <Button
                  variant="default"
                  className="bg-emerald-600 hover:bg-emerald-700"
                  onClick={() => ejecutar(false)}
                  disabled={!puedeConfirmar}
                  title={
                    puedeConfirmar
                      ? ''
                      : 'Primero simula con los mismos archivos y opciones'
                  }
                >
                  <CheckCircle2 className="mr-2 h-4 w-4" />
                  2. Aprobar y cargar
                </Button>
                <Button
                  variant="outline"
                  onClick={descargar}
                  disabled={running || !resultados.length}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Descargar resultado
                </Button>
                <Button
                  variant="outline"
                  onClick={descargarNoUsados}
                  disabled={running || !depositos.length || !resultados.length}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Depósitos no usados
                </Button>
                {modo === 'real' && pagoIdsReales.length > 0 && !deshecho ? (
                  <Button
                    variant="destructive"
                    onClick={deshacer}
                    disabled={running}
                  >
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Deshacer esta carga
                  </Button>
                ) : null}
              </div>
              {modo === 'simulacion' && resultados.length && !running ? (
                <p className="text-sm text-muted-foreground">
                  Paso 1 listo. Abajo puedes revisar cédula por cédula y aprobar
                  la carga.
                </p>
              ) : null}
              {deshecho ? (
                <p className="text-sm font-medium text-red-700">
                  Esta carga fue deshecha.
                </p>
              ) : null}
              {progress ? (
                <p className="text-sm font-medium">{progress}</p>
              ) : null}
            </CardContent>
          </Card>

          {resultados.length ? (
            <>
              {modo === 'simulacion' && !running ? (
                <Card className="border-amber-300 bg-amber-50">
                  <CardContent className="flex flex-col gap-3 py-4 md:flex-row md:items-center md:justify-between">
                    <div className="space-y-1">
                      <p className="text-sm font-semibold text-amber-900">
                        Simulación lista — nada se ha guardado
                      </p>
                      <p className="text-sm text-amber-900/80">
                        {resumen.pagos} pago(s) propuestos · $
                        {moneyFmt(resumen.monto)} · {resumen.COMPLETO}{' '}
                        completo(s) · {resumen.PARCIAL} parcial(es)
                        {resumen.SIN_COINCIDENCIA
                          ? ` · ${resumen.SIN_COINCIDENCIA} sin coincidencia`
                          : ''}
                        {resumen.conAlternativas
                          ? ` · ${resumen.conAlternativas} con otras opciones`
                          : ''}
                        . Revisa el listado y aprueba para cargar en BD.
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="outline"
                        onClick={descargar}
                        disabled={running}
                      >
                        <Download className="mr-2 h-4 w-4" />
                        Descargar simulación
                      </Button>
                      <Button
                        className="bg-emerald-600 hover:bg-emerald-700"
                        onClick={() => ejecutar(false)}
                        disabled={!puedeConfirmar}
                      >
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Aprobar y cargar {resumen.pagos} pago(s)
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <Badge
                  variant={modo === 'simulacion' ? 'secondary' : 'default'}
                >
                  {modo === 'simulacion' ? 'SIMULACIÓN' : 'CARGADO'}
                </Badge>
                <Badge variant="outline">Cédulas: {resultados.length}</Badge>
                <Badge className="bg-emerald-600 hover:bg-emerald-600">
                  {modo === 'simulacion'
                    ? 'Pagos propuestos'
                    : 'Pagos registrados'}
                  : {resumen.pagos}
                </Badge>
                <Badge variant="outline">
                  Monto: ${moneyFmt(resumen.monto)}
                </Badge>
                {(
                  [
                    ['TODAS', `Todas (${resultados.length})`],
                    ['COMPLETO', `Completo (${resumen.COMPLETO})`],
                    ['PARCIAL', `Parcial (${resumen.PARCIAL})`],
                    [
                      'SIN_COINCIDENCIA',
                      `Sin coincidencia (${resumen.SIN_COINCIDENCIA})`,
                    ],
                    ['SIN_ATRASO', `Sin atraso (${resumen.SIN_ATRASO})`],
                    [
                      'CEDULA_INVALIDA',
                      `Inválida (${resumen.CEDULA_INVALIDA})`,
                    ],
                    [
                      'CON_ALTERNATIVAS',
                      `Con opciones (${resumen.conAlternativas})`,
                    ],
                  ] as [FiltroResultado, string][]
                ).map(([k, label]) => (
                  <button
                    key={k}
                    type="button"
                    onClick={() => setFiltro(k)}
                    className={`rounded-full border px-2.5 py-0.5 text-xs ${
                      filtro === k
                        ? 'border-slate-900 bg-slate-900 text-white'
                        : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">
                  Depósitos asignados: {usados.length} / {depositos.length}
                </Badge>
                <Badge variant="secondary">Libres: {libres}</Badge>
                <Badge variant="secondary">
                  Serial ya en BD: {serialEnBd.length}
                </Badge>
                <Badge variant="secondary">
                  En reportados / confirmados: {enOtras.length}
                </Badge>
              </div>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0">
                  <CardTitle className="text-base">
                    {modo === 'simulacion'
                      ? 'Revisión de la simulación'
                      : 'Resultado cargado'}{' '}
                    · {resultadosFiltrados.length} fila(s)
                  </CardTitle>
                  {modo === 'simulacion' && resultadosFiltrados.length ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        const all = Object.fromEntries(
                          resultadosFiltrados.map((r, i) => [
                            `${i}-${r.cedula}`,
                            true,
                          ])
                        )
                        const abierto = resultadosFiltrados.every(
                          (r, i) => abiertas[`${i}-${r.cedula}`]
                        )
                        setAbiertas(abierto ? {} : all)
                      }}
                    >
                      {resultadosFiltrados.every(
                        (r, i) => abiertas[`${i}-${r.cedula}`]
                      )
                        ? 'Contraer todas'
                        : 'Expandir todas'}
                    </Button>
                  ) : null}
                </CardHeader>
                <CardContent className="space-y-2">
                  {resultadosFiltrados.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      Ninguna cédula en este filtro.
                    </p>
                  ) : null}
                  {resultadosFiltrados.map((r, idx) => {
                    const key = `${idx}-${r.cedula}`
                    const abierta = !!abiertas[key]
                    const monto = r.pagos.reduce((s, p) => s + p.monto, 0)
                    const alts = r.pagos.filter(p => p.alternativas > 0).length
                    return (
                      <div
                        key={key}
                        className="rounded-md border border-slate-200 bg-white"
                      >
                        <button
                          type="button"
                          className="flex w-full items-start gap-3 px-3 py-3 text-left hover:bg-slate-50"
                          onClick={() =>
                            setAbiertas(prev => ({
                              ...prev,
                              [key]: !prev[key],
                            }))
                          }
                        >
                          <span className="mt-0.5 text-slate-500">
                            {abierta ? (
                              <ChevronDown className="h-4 w-4" />
                            ) : (
                              <ChevronRight className="h-4 w-4" />
                            )}
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
                              Cubiertas {r.cuotas_cubiertas}/
                              {r.cuotas_atrasadas}
                              {r.pagos.length
                                ? ` · ${r.pagos.length} pago(s) · $${moneyFmt(monto)}`
                                : ' · sin pagos'}
                            </p>
                            {!abierta && r.detalle ? (
                              <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
                                {r.detalle}
                              </p>
                            ) : null}
                          </div>
                        </button>
                        {abierta ? (
                          <div className="border-t border-slate-100 px-3 py-3">
                            <p className="mb-2 text-xs text-muted-foreground">
                              {r.detalle}
                            </p>
                            {r.pagos.length ? (
                              <div className="overflow-x-auto">
                                <Table>
                                  <TableHeader>
                                    <TableRow>
                                      <TableHead>Cuota</TableHead>
                                      <TableHead>Mes</TableHead>
                                      <TableHead>Depósito</TableHead>
                                      <TableHead>Serial</TableHead>
                                      <TableHead className="text-right">
                                        Monto
                                      </TableHead>
                                      <TableHead className="text-right">
                                        Falta antes
                                      </TableHead>
                                      <TableHead>Opciones</TableHead>
                                    </TableRow>
                                  </TableHeader>
                                  <TableBody>
                                    {r.pagos.map(p => (
                                      <TableRow key={p.deposito_id}>
                                        <TableCell className="text-sm">
                                          #{p.cuota_numero}
                                          <span className="ml-1 text-xs text-muted-foreground">
                                            {p.cuota_vencimiento}
                                          </span>
                                        </TableCell>
                                        <TableCell className="text-sm">
                                          {p.mes}
                                        </TableCell>
                                        <TableCell className="text-sm">
                                          {p.fecha_deposito}
                                        </TableCell>
                                        <TableCell className="font-mono text-xs">
                                          {p.serial}
                                        </TableCell>
                                        <TableCell className="text-right text-sm">
                                          ${moneyFmt(p.monto)}
                                        </TableCell>
                                        <TableCell className="text-right text-sm">
                                          ${moneyFmt(p.saldo_cuota_antes)}
                                        </TableCell>
                                        <TableCell className="text-sm">
                                          {p.alternativas > 0 ? (
                                            <span className="text-amber-700">
                                              +{p.alternativas}
                                            </span>
                                          ) : (
                                            '—'
                                          )}
                                        </TableCell>
                                      </TableRow>
                                    ))}
                                  </TableBody>
                                </Table>
                              </div>
                            ) : (
                              <p className="text-sm text-muted-foreground">
                                Sin depósitos asignados.
                              </p>
                            )}
                          </div>
                        ) : null}
                      </div>
                    )
                  })}
                </CardContent>
              </Card>

              {modo === 'simulacion' && !running && puedeConfirmar ? (
                <div className="sticky bottom-3 z-10 rounded-lg border border-emerald-300 bg-emerald-50 p-3 shadow-md">
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <p className="text-sm font-medium text-emerald-900">
                      ¿Aprobar esta simulación? Se cargarán {resumen.pagos}{' '}
                      pago(s) por ${moneyFmt(resumen.monto)} y se aplicará la
                      cascada.
                    </p>
                    <Button
                      className="bg-emerald-600 hover:bg-emerald-700"
                      onClick={() => ejecutar(false)}
                      disabled={!puedeConfirmar}
                    >
                      <CheckCircle2 className="mr-2 h-4 w-4" />
                      Aprobar y cargar
                    </Button>
                  </div>
                </div>
              ) : null}
            </>
          ) : null}
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default CobranzasSerialesPage
