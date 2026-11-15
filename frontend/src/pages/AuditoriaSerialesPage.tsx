/**
 * Auditoría → Pagos / Seriales
 * Sube Excel (Deposito | Referencia | Monto | SI/NO), consulta la columna B
 * contra pagos.numero_documento / referencia_pago por lotes y descarga el
 * Excel completo con la columna D en si/no. En pantalla solo totales.
 */
import { useState } from 'react'
import { Download, FileSpreadsheet, Loader2 } from 'lucide-react'
import { toast } from 'sonner'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { auditoriaService } from '../services/auditoriaService'

/** Filas de datos por request al backend. */
const LOTE_FILAS = 200

function errMsg(err: unknown): string {
  const e = err as {
    response?: { data?: { detail?: string } }
    message?: string
  }
  const d = e?.response?.data?.detail
  if (typeof d === 'string' && d.trim()) return d
  return e?.message || 'Error'
}

function celdaASerial(val: unknown): string {
  if (val == null || val === '') return ''
  if (typeof val === 'number' && Number.isFinite(val)) {
    if (Number.isInteger(val) || val === Math.trunc(val)) {
      return String(Math.trunc(val))
    }
    return String(val)
  }
  const s = String(val).trim()
  if (/^\d+\.0+$/.test(s)) return s.split('.', 1)[0]
  return s
}

type CeldaExcel = { value: unknown; text?: unknown }

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

function serialDeCelda(cell: CeldaExcel): string {
  const v = valorCelda(cell)
  if (typeof v === 'number' && Number.isFinite(v) && Math.abs(v) >= 1e10) {
    const t = String(cell.text ?? '').replace(/\s+/g, '')
    if (/^\d{10,25}$/.test(t)) return t
    return BigInt(Math.round(v)).toString()
  }
  return celdaASerial(v)
}

function celdaVacia(cell: CeldaExcel): boolean {
  const v = valorCelda(cell)
  return v == null || String(v).trim() === ''
}

function esEncabezado(textos: string[]): boolean {
  const t = textos.join(' ').toLowerCase()
  return (
    t.includes('referencia') ||
    t.includes('serial') ||
    t.includes('deposito') ||
    t.includes('depósito') ||
    t.includes('si/no')
  )
}

type FilaParsed = { rowNumber: number; serial: string }

type HojaExcel = {
  eachRow: (cb: (row: FilaExcel, rowNumber: number) => void) => void
  getRow: (n: number) => FilaExcel
}
type FilaExcel = { getCell: (c: number) => CeldaExcel & { value: unknown } }
type LibroExcel = {
  worksheets: HojaExcel[]
  getWorksheet: (i: number) => HojaExcel | undefined
  xlsx: {
    load: (b: ArrayBuffer) => Promise<unknown>
    writeBuffer: () => Promise<ArrayBuffer>
  }
}

/** Abre el Excel original; se reutiliza para descargar sin tocar fechas ni formato. */
async function leerFilasExcel(file: File): Promise<{
  libro: LibroExcel
  hoja: HojaExcel
  filas: FilaParsed[]
  headerRowNumber: number | null
}> {
  const { importExcelJS } = await import('../types/exceljs')
  const { Workbook } = await importExcelJS()
  const libro = new Workbook() as LibroExcel
  await libro.xlsx.load(await file.arrayBuffer())
  const hoja = libro.getWorksheet(1) || libro.worksheets[0]
  if (!hoja) throw new Error('El Excel no tiene hojas.')

  const filas: FilaParsed[] = []
  let headerRowNumber: number | null = null
  let primera = true
  hoja.eachRow((row, rowNumber) => {
    const a = row.getCell(1)
    const b = row.getCell(2)
    const c = row.getCell(3)
    if (primera) {
      primera = false
      const textos = [1, 2, 3, 4].map(i =>
        String(valorCelda(row.getCell(i)) ?? '').trim()
      )
      if (esEncabezado(textos)) {
        headerRowNumber = rowNumber
        return
      }
    }
    if (celdaVacia(a) && celdaVacia(b) && celdaVacia(c)) return
    filas.push({ rowNumber, serial: serialDeCelda(b) })
  })
  if (!filas.length) throw new Error('No hay filas de datos en el Excel.')
  if (filas.length > 20000) {
    throw new Error('Máximo 20000 filas de datos por archivo.')
  }
  return { libro, hoja, filas, headerRowNumber }
}

/** Escribe si/no en la columna D del mismo archivo; el resto de celdas queda igual. */
async function descargarExcelConSiNo(
  libro: LibroExcel,
  hoja: HojaExcel,
  filas: FilaParsed[],
  resultados: string[],
  headerRowNumber: number | null,
  nombreOriginal: string
): Promise<void> {
  if (headerRowNumber != null) {
    const h = hoja.getRow(headerRowNumber).getCell(4)
    if (celdaVacia(h)) h.value = 'SI/NO'
  }
  filas.forEach((f, idx) => {
    hoja.getRow(f.rowNumber).getCell(4).value = resultados[idx] || 'no'
  })
  const buffer = await libro.xlsx.writeBuffer()
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const base = nombreOriginal.replace(/\.xlsx?$/i, '') || 'Auditoria_Seriales'
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${base}_SI_NO.xlsx`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

type Resumen = { total: number; si: number; no: number }

export function AuditoriaSerialesPage() {
  const [file, setFile] = useState<File | null>(null)
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState<string | null>(null)
  const [resumen, setResumen] = useState<Resumen | null>(null)

  async function procesarYDescargar() {
    if (!file) {
      toast.error('Selecciona un Excel con Referencia en la columna B.')
      return
    }
    setRunning(true)
    setResumen(null)
    try {
      setProgress('Leyendo Excel…')
      const { libro, hoja, filas, headerRowNumber } = await leerFilasExcel(file)

      const total = filas.length
      const lotesTotal = Math.ceil(total / LOTE_FILAS)
      const resultados: string[] = []
      let nSi = 0

      for (let li = 0; li < lotesTotal; li++) {
        const from = li * LOTE_FILAS
        const chunk = filas.slice(from, from + LOTE_FILAS)
        setProgress(
          `Lote ${li + 1} / ${lotesTotal} · filas ${from + 1}–${from + chunk.length} de ${total}`
        )
        const lote = await auditoriaService.consultarSerialesLote(
          chunk.map(f => f.serial)
        )
        for (let j = 0; j < chunk.length; j++) {
          const r = lote.items[j]?.resultado === 'si' ? 'si' : 'no'
          resultados.push(r)
          if (r === 'si') nSi += 1
        }
      }

      if (resultados.length !== total) {
        throw new Error(
          `Procesadas ${resultados.length} de ${total} filas; no se descarga incompleto.`
        )
      }

      setResumen({ total, si: nSi, no: total - nSi })
      setProgress('Generando Excel…')
      await descargarExcelConSiNo(
        libro,
        hoja,
        filas,
        resultados,
        headerRowNumber,
        file.name
      )
      setProgress(null)
      toast.success(
        `Excel descargado: ${total} filas (${nSi} si, ${total - nSi} no).`
      )
    } catch (err) {
      setProgress(null)
      toast.error(errMsg(err))
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Pagos"
        description="Sube un Excel (Deposito | Referencia | Monto | SI/NO). Se compara la columna B contra numero_documento y referencia_pago en pagos, por lotes, y se descarga el Excel completo con la columna D en si o no."
        icon={FileSpreadsheet}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Subir Excel de seriales</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Input
              type="file"
              accept=".xlsx"
              onChange={e => {
                setFile(e.target.files?.[0] || null)
                setResumen(null)
                setProgress(null)
              }}
              className="max-w-md"
              disabled={running}
            />
            <Button onClick={procesarYDescargar} disabled={running || !file}>
              {running ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              Procesar y descargar Excel
            </Button>
          </div>
          {progress ? (
            <p className="text-sm font-medium text-foreground">{progress}</p>
          ) : null}
        </CardContent>
      </Card>

      {resumen ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Resumen</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="rounded-lg border p-4">
                <p className="text-sm text-muted-foreground">Total filas</p>
                <p className="text-2xl font-semibold">{resumen.total}</p>
              </div>
              <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-4">
                <p className="text-sm text-emerald-800">Total SI</p>
                <p className="text-2xl font-semibold text-emerald-700">
                  {resumen.si}
                </p>
              </div>
              <div className="rounded-lg border border-red-300 bg-red-50 p-4">
                <p className="text-sm text-red-800">Total NO</p>
                <p className="text-2xl font-semibold text-red-700">
                  {resumen.no}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}

export default AuditoriaSerialesPage
