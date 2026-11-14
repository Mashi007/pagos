/**
 * Auditoría → Pagos / Seriales
 * Sube Excel (Deposito | Referencia | Monto | SI/NO) y marca si/no
 * comparando la columna B contra pagos.numero_documento / referencia_pago.
 * Procesa por lotes de 200 filas para no colapsar con ~1000+ filas.
 */
import { useMemo, useState } from 'react'
import { Download, FileSpreadsheet, Loader2, Upload } from 'lucide-react'
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
  auditoriaService,
  type SerialesVerificarItem,
  type SerialesVerificarResponse,
} from '../services/auditoriaService'

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
    .map(c => String(c ?? '').trim().toLowerCase())
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
  filaExcel: number
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
    filas.push({
      filaExcel: i + 1,
      deposito: a,
      serial: celdaASerial(b),
      monto: c,
    })
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
  await createAndDownloadExcel(data, 'Seriales', 'Auditoria_Seriales_SI_NO.xlsx')
}

export function AuditoriaSerialesPage() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [progress, setProgress] = useState<string | null>(null)
  const [result, setResult] = useState<SerialesVerificarResponse | null>(null)
  const [filasCache, setFilasCache] = useState<FilaParsed[] | null>(null)
  const [headerCache, setHeaderCache] = useState<unknown[] | null>(null)
  const [resultadosCache, setResultadosCache] = useState<string[] | null>(null)

  const preview = useMemo(() => {
    if (!result?.items?.length) return []
    return result.items.slice(0, 200)
  }, [result])

  async function procesarPorLotes(opts: {
    descargar: boolean
  }): Promise<void> {
    if (!file) {
      toast.error('Selecciona un Excel con Referencia en la columna B.')
      return
    }

    setProgress('Leyendo Excel…')
    const { filas, headerRow } = await leerFilasExcel(file)
    if (!filas.length) {
      throw new Error('No hay filas de datos en el Excel.')
    }

    const total = filas.length
    const lotesTotal = Math.max(1, Math.ceil(total / LOTE_FILAS))
    const items: SerialesVerificarItem[] = []
    const resultados: string[] = []
    let nSi = 0
    let nNo = 0
    let nVacios = 0

    for (let li = 0; li < lotesTotal; li++) {
      const from = li * LOTE_FILAS
      const chunk = filas.slice(from, from + LOTE_FILAS)
      setProgress(
        `Lote ${li + 1} / ${lotesTotal} · filas ${from + 1}–${from + chunk.length} de ${total}`
      )
      const seriales = chunk.map(f => f.serial)
      const lote = await auditoriaService.consultarSerialesLote(seriales)
      for (let j = 0; j < chunk.length; j++) {
        const it = lote.items[j]
        const resultado = (it?.resultado || 'no') as string
        resultados.push(resultado)
        if (resultado === 'si') nSi += 1
        else nNo += 1
        if (!chunk[j].serial) nVacios += 1
        items.push({
          fila: chunk[j].filaExcel,
          serial_archivo: chunk[j].serial,
          serial_norm: it?.serial_norm ?? null,
          resultado,
          en_bd: resultado === 'si',
        })
      }
    }

    const aggregated: SerialesVerificarResponse = {
      total_filas: items.length,
      encontrados_si: nSi,
      no_encontrados_no: nNo,
      seriales_vacios: nVacios,
      items,
    }
    setResult(aggregated)
    setFilasCache(filas)
    setHeaderCache(headerRow)
    setResultadosCache(resultados)

    if (opts.descargar) {
      setProgress('Generando Excel…')
      await descargarExcelConSiNo(filas, resultados, headerRow)
    }
    setProgress(null)
    toast.success(
      `Verificados ${aggregated.total_filas} en ${lotesTotal} lote(s): ${nSi} si, ${nNo} no.`
    )
  }

  async function verificar() {
    setLoading(true)
    setProgress(null)
    try {
      await procesarPorLotes({ descargar: false })
    } catch (err) {
      setProgress(null)
      toast.error(errMsg(err))
    } finally {
      setLoading(false)
    }
  }

  async function descargar() {
    setExporting(true)
    setProgress(null)
    try {
      if (filasCache && resultadosCache && resultadosCache.length === filasCache.length) {
        setProgress('Generando Excel…')
        await descargarExcelConSiNo(filasCache, resultadosCache, headerCache)
        setProgress(null)
        toast.success('Excel descargado con columna D (si/no).')
      } else {
        await procesarPorLotes({ descargar: true })
      }
    } catch (err) {
      setProgress(null)
      toast.error(errMsg(err))
    } finally {
      setExporting(false)
    }
  }

  function badgeResultado(row: SerialesVerificarItem) {
    if (row.resultado === 'si') {
      return (
        <Badge className="bg-emerald-600 hover:bg-emerald-600">si</Badge>
      )
    }
    return <Badge variant="destructive">no</Badge>
  }

  const busy = loading || exporting

  return (
    <div className="space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Pagos"
        description="Sube un Excel (Deposito | Referencia | Monto | SI/NO). Se compara la columna B (Referencia) contra numero_documento y referencia_pago en la tabla pagos. Procesa de 200 en 200 para archivos de ~1000 filas. La columna D queda en si (registrado) o no (no encontrado)."
        icon={FileSpreadsheet}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Subir Excel de seriales</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Formato: A Deposito, B Referencia, C Monto, D SI/NO. Con ~1000 filas
            el sistema parte la lista en lotes de {LOTE_FILAS} y consulta la BD
            por bloques para no saturar el servidor.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Input
              type="file"
              accept=".xlsx,.xls"
              onChange={e => {
                setFile(e.target.files?.[0] || null)
                setResult(null)
                setFilasCache(null)
                setHeaderCache(null)
                setResultadosCache(null)
                setProgress(null)
              }}
              className="max-w-md"
              disabled={busy}
            />
            <div className="flex flex-wrap gap-2">
              <Button onClick={verificar} disabled={busy || !file}>
                {loading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                Verificar
              </Button>
              <Button
                variant="outline"
                onClick={descargar}
                disabled={busy || !file}
              >
                {exporting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Download className="mr-2 h-4 w-4" />
                )}
                Descargar Excel
              </Button>
            </div>
          </div>
          {file ? (
            <p className="text-xs text-muted-foreground">Archivo: {file.name}</p>
          ) : null}
          {progress ? (
            <p className="text-sm font-medium text-foreground">{progress}</p>
          ) : null}
        </CardContent>
      </Card>

      {result ? (
        <>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">Filas: {result.total_filas}</Badge>
            <Badge className="bg-emerald-600 hover:bg-emerald-600">
              si: {result.encontrados_si}
            </Badge>
            <Badge variant="destructive">no: {result.no_encontrados_no}</Badge>
            {result.seriales_vacios > 0 ? (
              <Badge variant="secondary">
                serial vacío: {result.seriales_vacios}
              </Badge>
            ) : null}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Resultado
                {result.items.length > preview.length
                  ? ` (primeras ${preview.length} de ${result.items.length})`
                  : ''}
              </CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fila</TableHead>
                    <TableHead>Referencia</TableHead>
                    <TableHead>Normalizado</TableHead>
                    <TableHead>SI/NO</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.map(row => (
                    <TableRow key={`${row.fila}-${row.serial_archivo}`}>
                      <TableCell className="text-sm">{row.fila}</TableCell>
                      <TableCell className="font-mono text-sm">
                        {row.serial_archivo || '—'}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {row.serial_norm || '—'}
                      </TableCell>
                      <TableCell>{badgeResultado(row)}</TableCell>
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

export default AuditoriaSerialesPage
