/** Lectura de los Excel de Cobranzas → Seriales (cédulas y depósitos). */
import type { SerialDepositoIn } from '../services/cobranzasSerialesService'

export function errMsg(err: unknown): string {
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

export async function leerCedulas(file: File): Promise<string[]> {
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

export type DepositoFila = SerialDepositoIn & { filaExcel: number }

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
export function fechaIsoUtc(d: Date): string {
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

export async function leerDepositos(file: File): Promise<DepositoFila[]> {
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
