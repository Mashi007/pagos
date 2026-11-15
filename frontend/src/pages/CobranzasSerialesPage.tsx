/**
 * Cobranzas → Seriales (solo itmaster@).
 * Archivo 1: cédulas (columna A). Archivo 2: depósitos (Deposito | Referencia | Monto).
 * Por cada cédula (orden del archivo, lotes de 20) toma el préstamo con la cuota
 * atrasada más antigua. Un depósito por mes: cada cuota busca desde el mes de su
 * vencimiento el depósito más cercano a lo que le falta (±20%); si el mes no tiene,
 * sigue con el siguiente. Banco Mercantil, USD, comprobante en blanco; cascada normal.
 */
import { useMemo, useState } from 'react'
import { Download, FileSpreadsheet, Loader2, Play } from 'lucide-react'
import { toast } from 'sonner'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Input } from '../components/ui/input'
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

const LOTE_PRESTAMOS = 20

function errMsg(err: unknown): string {
  const e = err as {
    response?: { data?: { detail?: string } }
    message?: string
  }
  const d = e?.response?.data?.detail
  if (typeof d === 'string' && d.trim()) return d
  return e?.message || 'Error'
}

function celdaTexto(val: unknown): string {
  if (val == null || val === '') return ''
  if (typeof val === 'number' && Number.isFinite(val)) {
    if (Number.isInteger(val)) return String(val)
    return String(val)
  }
  if (val instanceof Date) return fechaIsoUtc(val)
  const s = String(val).trim()
  if (/^\d+\.0+$/.test(s)) return s.split('.', 1)[0]
  return s
}

async function leerMatriz(file: File): Promise<unknown[][]> {
  const { readExcelToJSON } = await import('../types/exceljs')
  const matrix = (await readExcelToJSON(file)) as unknown[][]
  if (!matrix?.length) throw new Error(`El archivo ${file.name} está vacío.`)
  return matrix
}

async function leerCedulas(file: File): Promise<string[]> {
  const matrix = await leerMatriz(file)
  const out: string[] = []
  for (const row of matrix) {
    const v = celdaTexto(row?.[0])
    if (!v) continue
    if (!/\d{5,}/.test(v)) continue
    out.push(v)
  }
  if (!out.length) throw new Error('No se encontraron cédulas en la columna A.')
  return out
}

function esEncabezadoDepositos(row: unknown[]): boolean {
  const t = row
    .slice(0, 3)
    .map(c =>
      String(c ?? '')
        .trim()
        .toLowerCase()
    )
    .join(' ')
  return (
    t.includes('referencia') ||
    t.includes('serial') ||
    t.includes('deposito') ||
    t.includes('depósito') ||
    t.includes('monto')
  )
}

type DepositoFila = SerialDepositoIn & { filaExcel: number }

type CeldaExcel = { value: unknown; text?: unknown; numFmt?: unknown }

/** Valor atómico de la celda (fórmula → resultado, richText/hyperlink → texto). */
function valorCelda(cell: CeldaExcel): unknown {
  const v = cell.value
  if (v != null && typeof v === 'object' && !(v instanceof Date)) {
    const o = v as {
      result?: unknown
      richText?: { text?: string }[]
      text?: unknown
    }
    if ('result' in o) return o.result
    if (Array.isArray(o.richText))
      return o.richText.map(x => x?.text ?? '').join('')
    if ('text' in o) return o.text
  }
  return v
}

/** ExcelJS entrega fechas como medianoche UTC: usar componentes UTC (sin corrimiento de día). */
function fechaIsoUtc(d: Date): string {
  const y = d.getUTCFullYear()
  const m = String(d.getUTCMonth() + 1).padStart(2, '0')
  const day = String(d.getUTCDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function fechaDeCelda(cell: CeldaExcel): string {
  const v = valorCelda(cell)
  if (v instanceof Date) return fechaIsoUtc(v)
  if (typeof v === 'number' && Number.isFinite(v) && v > 20000 && v < 80000) {
    return fechaIsoUtc(new Date(Math.round((v - 25569) * 86400000)))
  }
  return celdaTexto(v)
}

function serialDeCelda(cell: CeldaExcel): string {
  const v = valorCelda(cell)
  if (typeof v === 'number' && Number.isFinite(v) && Math.abs(v) >= 1e10) {
    const t = String(cell.text ?? '').replace(/\s+/g, '')
    if (/^\d{10,25}$/.test(t)) return t
    return BigInt(Math.round(v)).toString()
  }
  return celdaTexto(v)
}

type HojaExcel = {
  eachRow: (
    cb: (row: { getCell: (c: number) => CeldaExcel }, n: number) => void
  ) => void
}

async function leerDepositos(file: File): Promise<DepositoFila[]> {
  const { importExcelJS } = await import('../types/exceljs')
  const { Workbook } = await importExcelJS()
  const libro = new Workbook()
  await libro.xlsx.load(await file.arrayBuffer())
  const hoja = (libro.getWorksheet(1) || libro.worksheets[0]) as
    | HojaExcel
    | undefined
  if (!hoja) throw new Error(`El archivo ${file.name} no tiene hojas.`)

  const out: DepositoFila[] = []
  let primera = true
  hoja.eachRow((row, rowNumber) => {
    const a = row.getCell(1)
    const b = row.getCell(2)
    const c = row.getCell(3)
    if (primera) {
      primera = false
      const textos = [a, b, c].map(x => String(valorCelda(x) ?? ''))
      if (esEncabezadoDepositos(textos)) return
    }
    const fecha = fechaDeCelda(a)
    const serial = serialDeCelda(b)
    const monto = celdaTexto(valorCelda(c))
    if (!fecha && !serial && !monto) return
    out.push({ id: out.length, filaExcel: rowNumber, fecha, serial, monto })
  })
  if (!out.length) throw new Error('No hay filas de depósitos.')
  if (out.length > 20000) throw new Error('Máximo 20000 depósitos por archivo.')
  return out
}

const ESTADO_LABEL: Record<SerialEstadoCedula, string> = {
  COMPLETO: 'Completo',
  PARCIAL: 'Parcial',
  SIN_COINCIDENCIA: 'Sin coincidencia',
  SIN_ATRASO: 'Sin cuotas atrasadas',
  CEDULA_INVALIDA: 'Cédula inválida',
}

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

export function CobranzasSerialesPage() {
  const [fileCedulas, setFileCedulas] = useState<File | null>(null)
  const [fileDepositos, setFileDepositos] = useState<File | null>(null)
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState<string | null>(null)
  const [resultados, setResultados] = useState<SerialResultadoCedula[]>([])
  const [depositos, setDepositos] = useState<DepositoFila[]>([])
  const [usados, setUsados] = useState<number[]>([])
  const [serialEnBd, setSerialEnBd] = useState<number[]>([])

  const resumen = useMemo(() => {
    const r = {
      COMPLETO: 0,
      PARCIAL: 0,
      SIN_COINCIDENCIA: 0,
      SIN_ATRASO: 0,
      CEDULA_INVALIDA: 0,
    }
    let pagos = 0
    for (const x of resultados) {
      if (x.estado in r) r[x.estado as SerialEstadoCedula] += 1
      pagos += x.pagos.length
    }
    return { ...r, pagos }
  }, [resultados])

  const filaPorDeposito = useMemo(() => {
    const m = new Map<number, number>()
    for (const d of depositos) m.set(d.id, d.filaExcel)
    return m
  }, [depositos])

  async function procesar() {
    if (!fileCedulas || !fileDepositos) {
      toast.error('Sube el Excel de cédulas y el Excel de depósitos.')
      return
    }
    setRunning(true)
    setResultados([])
    setUsados([])
    setSerialEnBd([])
    try {
      setProgress('Leyendo archivos…')
      const cedulas = await leerCedulas(fileCedulas)
      const deps = await leerDepositos(fileDepositos)
      setDepositos(deps)
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

      const ok = window.confirm(
        `Se procesarán ${cedulas.length} cédula(s) contra ${deps.length} depósito(s) en lotes de ${LOTE_PRESTAMOS}.\n` +
          'Los pagos se registran en BD (Mercantil, USD, comprobante en blanco) y se aplica cascada. ¿Continuar?'
      )
      if (!ok) {
        setProgress(null)
        return
      }

      const payloadDeps: SerialDepositoIn[] = deps.map(d => ({
        id: d.id,
        fecha: d.fecha,
        serial: d.serial,
        monto: d.monto,
      }))
      const lotes = Math.ceil(cedulas.length / LOTE_PRESTAMOS)
      let usadosAcum: number[] = []
      const enBdAcum = new Set<number>()
      const acumulado: SerialResultadoCedula[] = []

      for (let li = 0; li < lotes; li++) {
        const chunk = cedulas.slice(
          li * LOTE_PRESTAMOS,
          (li + 1) * LOTE_PRESTAMOS
        )
        setProgress(
          `Lote ${li + 1} / ${lotes} · cédulas ${li * LOTE_PRESTAMOS + 1}–${li * LOTE_PRESTAMOS + chunk.length} de ${cedulas.length} · depósitos usados: ${usadosAcum.length}`
        )
        const res = await cobranzasSerialesService.procesarLote({
          cedulas: chunk,
          depositos: payloadDeps,
          usados: usadosAcum,
        })
        usadosAcum = [...usadosAcum, ...res.depositos_usados]
        for (const id of res.depositos_serial_en_bd) enBdAcum.add(id)
        acumulado.push(...res.resultados)
        setResultados([...acumulado])
        setUsados([...usadosAcum])
        setSerialEnBd([...enBdAcum])
      }
      setProgress(null)
      toast.success(
        `Listo: ${acumulado.length} cédula(s), ${usadosAcum.length} pago(s) registrados.`
      )
    } catch (err) {
      setProgress(null)
      toast.error(
        `${errMsg(err)} (lo ya registrado en lotes anteriores queda guardado)`
      )
    } finally {
      setRunning(false)
    }
  }

  async function descargar() {
    const { createAndDownloadExcel } = await import('../types/exceljs')
    const filasResultado: Record<string, unknown>[] = []
    for (const r of resultados) {
      if (!r.pagos.length) {
        filasResultado.push({
          Cedula: r.cedula,
          Prestamo: r.prestamo_id ?? '',
          Estado: ESTADO_LABEL[r.estado] || r.estado,
          Cuota: '',
          Vencimiento: '',
          Deposito: '',
          Serial: '',
          Monto: '',
          'Fila deposito': '',
          'Pago ID': '',
          Detalle: r.detalle,
        })
        continue
      }
      for (const p of r.pagos) {
        filasResultado.push({
          Cedula: r.cedula,
          Prestamo: r.prestamo_id ?? '',
          Estado: ESTADO_LABEL[r.estado] || r.estado,
          Cuota: p.cuota_numero,
          Vencimiento: p.cuota_vencimiento,
          Deposito: p.fecha_deposito,
          Serial: p.serial,
          Monto: p.monto,
          'Fila deposito': filaPorDeposito.get(p.deposito_id) ?? '',
          'Pago ID': p.pago_id,
          Detalle: r.detalle,
        })
      }
    }
    await createAndDownloadExcel(
      filasResultado,
      'Seriales',
      'Cobranzas_Seriales_resultado.xlsx'
    )
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Seriales"
        description="Carga depósitos Mercantil a préstamos con cuotas atrasadas de la lista de cédulas. Un depósito por mes: cada cuota toma, desde el mes de su vencimiento, el depósito más cercano a lo que le falta dentro de ±20%. Cada depósito se usa una sola vez; un serial ya registrado en BD se omite."
        icon={FileSpreadsheet}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Archivos</CardTitle>
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
          </div>
          <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
            <li>
              Un solo préstamo por cédula: el de la cuota atrasada más antigua.
            </li>
            <li>
              Un depósito por mes y por préstamo. Cada cuota busca en el mes de
              su vencimiento el depósito más cercano a lo que le falta, dentro
              de ±20% (empate: fecha más antigua). Si ese mes no tiene, pasa al
              mes siguiente.
            </li>
            <li>
              Lo que falta o sobra lo ajusta la cascada (cuota 110 con depósito
              100: los 10 los cubre el siguiente depósito).
            </li>
            <li>
              Termina cuando se acaban las cuotas atrasadas o los meses del
              archivo de depósitos. Lotes de {LOTE_PRESTAMOS} préstamos.
            </li>
          </ul>
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={procesar}
              disabled={running || !fileCedulas || !fileDepositos}
            >
              {running ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Procesar
            </Button>
            <Button
              variant="outline"
              onClick={descargar}
              disabled={running || !resultados.length}
            >
              <Download className="mr-2 h-4 w-4" />
              Descargar resultado
            </Button>
          </div>
          {progress ? <p className="text-sm font-medium">{progress}</p> : null}
        </CardContent>
      </Card>

      {resultados.length ? (
        <>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">Cédulas: {resultados.length}</Badge>
            <Badge className="bg-emerald-600 hover:bg-emerald-600">
              Pagos registrados: {resumen.pagos}
            </Badge>
            <Badge variant="outline">Completo: {resumen.COMPLETO}</Badge>
            <Badge variant="outline">Parcial: {resumen.PARCIAL}</Badge>
            <Badge variant="outline">
              Sin coincidencia: {resumen.SIN_COINCIDENCIA}
            </Badge>
            <Badge variant="outline">Sin atraso: {resumen.SIN_ATRASO}</Badge>
            <Badge variant="outline">
              Cédula inválida: {resumen.CEDULA_INVALIDA}
            </Badge>
            <Badge variant="secondary">
              Depósitos usados: {usados.length} / {depositos.length}
            </Badge>
            {serialEnBd.length ? (
              <Badge variant="secondary">
                Serial ya en BD (omitidos): {serialEnBd.length}
              </Badge>
            ) : null}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Resultado por cédula</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Cédula</TableHead>
                    <TableHead>Préstamo</TableHead>
                    <TableHead>Cubiertas</TableHead>
                    <TableHead>Pagos</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Detalle</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {resultados.map((r, idx) => (
                    <TableRow key={`${idx}-${r.cedula}`}>
                      <TableCell className="font-mono text-sm">
                        {r.cedula}
                      </TableCell>
                      <TableCell className="text-sm">
                        {r.prestamo_id ?? '—'}
                      </TableCell>
                      <TableCell className="text-sm">
                        {r.cuotas_cubiertas} / {r.cuotas_atrasadas}
                      </TableCell>
                      <TableCell className="text-xs">
                        {r.pagos.length
                          ? r.pagos.map(p => (
                              <div key={p.pago_id} className="font-mono">
                                #{p.cuota_numero} · {p.mes} · {p.fecha_deposito}{' '}
                                · {p.serial} · {p.monto.toFixed(2)}
                              </div>
                            ))
                          : '—'}
                      </TableCell>
                      <TableCell>{badgeEstado(r.estado)}</TableCell>
                      <TableCell className="max-w-md text-xs text-muted-foreground">
                        {r.detalle}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  )
}

export default CobranzasSerialesPage
