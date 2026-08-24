/**
 * Auditoría → Conciliacion_finiquitos
 * Sube Excel de cédulas (archivo finiquitos) y muestra el estado real en el sistema.
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
  type ConciliacionFiniquitosItem,
  type ConciliacionFiniquitosResponse,
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

export function ConciliacionFiniquitosPage() {
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [result, setResult] = useState<ConciliacionFiniquitosResponse | null>(
    null
  )

  const resumenChips = useMemo(() => {
    if (!result?.por_estado_sistema) return []
    return Object.entries(result.por_estado_sistema)
  }, [result])

  async function comparar() {
    if (!file) {
      toast.error('Selecciona un Excel con cédulas en la columna A.')
      return
    }
    setLoading(true)
    try {
      const data = await auditoriaService.compararConciliacionFiniquitos(file)
      setResult(data)
      toast.success(
        `Comparadas ${data.total_cedulas_archivo} cédulas (${data.encontradas} en sistema, ${data.no_encontradas} no encontradas).`
      )
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setLoading(false)
    }
  }

  async function exportar() {
    if (!file) {
      toast.error('Selecciona un Excel con cédulas en la columna A.')
      return
    }
    setExporting(true)
    try {
      await auditoriaService.exportarConciliacionFiniquitos(file)
      toast.success('Excel de resultado descargado.')
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setExporting(false)
    }
  }

  function badgeEstado(row: ConciliacionFiniquitosItem) {
    const est = row.estado_sistema || '—'
    if (!row.en_sistema || est === 'NO_ENCONTRADA') {
      return <Badge variant="destructive">{est}</Badge>
    }
    if (est.toUpperCase() === 'LIQUIDADO') {
      return <Badge className="bg-emerald-600 hover:bg-emerald-600">{est}</Badge>
    }
    if (est.toUpperCase() === 'DESISTIMIENTO') {
      return <Badge variant="secondary">{est}</Badge>
    }
    return <Badge variant="outline">{est}</Badge>
  }

  return (
    <div className="space-y-6 p-4 md:p-6">
      <ModulePageHeader
        title="Conciliacion_finiquitos"
        description="Sube el Excel de cédulas que tienes como finiquitos en archivo y compara el estado de cada una en el sistema (estado del préstamo en BD)."
        icon={FileSpreadsheet}
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Subir lista de cédulas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Formato: columna A con cédulas (puede tener encabezado). Una fila por
            cédula. El resultado muestra el estado del préstamo en el sistema; si
            hay caso finiquito, también su estado de gestión.
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
              <Button onClick={comparar} disabled={loading || !file}>
                {loading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                Comparar
              </Button>
              <Button
                variant="outline"
                onClick={exportar}
                disabled={exporting || !file}
              >
                {exporting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Download className="mr-2 h-4 w-4" />
                )}
                Descargar resultado
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
            <Badge variant="outline">
              Archivo: {result.total_cedulas_archivo}
            </Badge>
            <Badge variant="outline">En sistema: {result.encontradas}</Badge>
            <Badge variant="outline">
              No encontradas: {result.no_encontradas}
            </Badge>
            <Badge variant="outline">
              Filas: {result.total_filas_resultado}
            </Badge>
            {resumenChips.map(([est, n]) => (
              <Badge key={est} variant="secondary">
                {est}: {n}
              </Badge>
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Resultado</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Cédula archivo</TableHead>
                    <TableHead>Estado sistema</TableHead>
                    <TableHead>Gestión finiquito</TableHead>
                    <TableHead>Caso finiquito</TableHead>
                    <TableHead>Préstamo</TableHead>
                    <TableHead>Nombre</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.items.map((row, idx) => (
                    <TableRow key={`${row.cedula_archivo}-${row.prestamo_id ?? 'x'}-${idx}`}>
                      <TableCell className="font-mono text-sm">
                        {row.cedula_archivo}
                      </TableCell>
                      <TableCell>{badgeEstado(row)}</TableCell>
                      <TableCell className="text-sm">
                        {row.estado_gestion_finiquito || '—'}
                      </TableCell>
                      <TableCell className="text-sm">
                        {row.estado_caso_finiquito || '—'}
                      </TableCell>
                      <TableCell className="text-sm">
                        {row.prestamo_id != null ? `#${row.prestamo_id}` : '—'}
                      </TableCell>
                      <TableCell className="text-sm">
                        {row.nombres || '—'}
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

export default ConciliacionFiniquitosPage
