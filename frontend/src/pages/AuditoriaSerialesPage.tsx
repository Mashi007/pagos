/**
 * Auditoría → Pagos / Seriales
 * Sube Excel (Deposito | Referencia | Monto | SI/NO) y marca si/no
 * comparando la columna B contra pagos.numero_documento / referencia_pago.
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

function errMsg(err: unknown): string {
  const e = err as {
    response?: { data?: { detail?: string } }
    message?: string
  }
  const d = e?.response?.data?.detail
  if (typeof d === 'string' && d.trim()) return d
  return e?.message || 'Error'
}

export function AuditoriaSerialesPage() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [result, setResult] = useState<SerialesVerificarResponse | null>(null)

  const preview = useMemo(() => {
    if (!result?.items?.length) return []
    return result.items.slice(0, 200)
  }, [result])

  async function verificar() {
    if (!file) {
      toast.error('Selecciona un Excel con Referencia en la columna B.')
      return
    }
    setLoading(true)
    try {
      const data = await auditoriaService.verificarSerialesExcel(file)
      setResult(data)
      toast.success(
        `Verificados ${data.total_filas}: ${data.encontrados_si} si, ${data.no_encontrados_no} no.`
      )
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setLoading(false)
    }
  }

  async function descargar() {
    if (!file) {
      toast.error('Selecciona un Excel con Referencia en la columna B.')
      return
    }
    setExporting(true)
    try {
      await auditoriaService.exportarSerialesExcel(file)
      toast.success('Excel descargado con columna D (si/no).')
    } catch (err) {
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

  return (
    <div className="space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Pagos"
        description="Sube un Excel (Deposito | Referencia | Monto | SI/NO). Se compara la columna B (Referencia) contra numero_documento y referencia_pago en la tabla pagos. La columna D queda en si (registrado) o no (no encontrado), sin importar el estado del pago."
        icon={FileSpreadsheet}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Subir Excel de seriales</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Formato esperado: columna A Deposito, B Referencia (serial), C Monto,
            D SI/NO (se rellena). Solo importa que coincida el serial
            normalizado (espacios, prefijos BNC/, sufijos _A#### / §CD:).
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Input
              type="file"
              accept=".xlsx,.xls"
              onChange={e => {
                setFile(e.target.files?.[0] || null)
                setResult(null)
              }}
              className="max-w-md"
            />
            <div className="flex flex-wrap gap-2">
              <Button onClick={verificar} disabled={loading || !file}>
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
                disabled={exporting || !file}
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
