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

function esEncabezado(row: unknown[]): boolean {
  const t = row
    .slice(0, 4)
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
    t.includes('si/no')
  )
}

type FilaParsed = {
  deposito: unknown
  serial: string
  monto: unknown
}

async function leerFilasExcel(file: File): Promise<{
  filas: FilaParsed[]
  headerRow: unknown[] | null
}> {
  const { readExcelToJSON } = await import('../types/exceljs')
  const matrix = (await readExcelToJSON(file)) as unknown[][]
  if (!matrix?.length) {
    throw new Error('El Excel está vacío.')
  }
  let start = 0
  let headerRow: unknown[] | null = null
  if (esEncabezado(matrix[0] || [])) {
    headerRow = matrix[0]
    start = 1
  }
  const filas: FilaParsed[] = []
  for (let i = start; i < matrix.length; i++) {
    const row = matrix[i] || []
    const a = row[0]
    const b = row[1]
    const c = row[2]
    if (
      (a == null || String(a).trim() === '') &&
      (b == null || String(b).trim() === '') &&
      (c == null || String(c).trim() === '')
    ) {
      continue
    }
    filas.push({ deposito: a, serial: celdaASerial(b), monto: c })
  }
  if (filas.length > 20000) {
    throw new Error('Máximo 20000 filas de datos por archivo.')
  }
  return { filas, headerRow }
}

async function descargarExcelConSiNo(
  filas: FilaParsed[],
  resultados: string[],
  headerRow: unknown[] | null
): Promise<void> {
  const { createAndDownloadExcel } = await import('../types/exceljs')
  const colA = String(headerRow?.[0] ?? 'Deposito') || 'Deposito'
  const colB = String(headerRow?.[1] ?? 'Referencia') || 'Referencia'
  const colC = String(headerRow?.[2] ?? 'Monto') || 'Monto'
  const data = filas.map((f, idx) => ({
    [colA]: f.deposito ?? '',
    [colB]: f.serial,
    [colC]: f.monto ?? '',
    'SI/NO': resultados[idx] || 'no',
  }))
  await createAndDownloadExcel(
    data,
    'Seriales',
    'Auditoria_Seriales_SI_NO.xlsx'
  )
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
      const { filas, headerRow } = await leerFilasExcel(file)
      if (!filas.length) {
        throw new Error('No hay filas de datos en el Excel.')
      }

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
      await descargarExcelConSiNo(filas, resultados, headerRow)
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
              accept=".xlsx,.xls"
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
