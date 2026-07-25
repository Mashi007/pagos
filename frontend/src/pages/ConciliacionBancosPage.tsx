import { useMemo, useState } from 'react'
import { Building2, Check, Download, Loader2, Upload, X } from 'lucide-react'
import { toast } from 'sonner'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'
import {
  ConciliacionBancosLote,
  ConciliacionBancosMoneda,
  ConciliacionBancosResultado,
  conciliacionBancosService,
} from '../services/conciliacionBancosService'

function hoyISO(): string {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function errMsg(err: unknown): string {
  const e = err as {
    response?: { data?: { detail?: string } }
    message?: string
  }
  return e?.response?.data?.detail || e?.message || 'Error'
}

export default function ConciliacionBancosPage() {
  const [moneda, setMoneda] = useState<ConciliacionBancosMoneda>('USD')
  const [fechaDesde, setFechaDesde] = useState(hoyISO())
  const [fechaHasta, setFechaHasta] = useState(hoyISO())
  const [file, setFile] = useState<File | null>(null)
  const [lote, setLote] = useState<ConciliacionBancosLote | null>(null)
  const [items, setItems] = useState<ConciliacionBancosResultado[]>([])
  const [stats, setStats] = useState<Record<string, number> | null>(null)
  const [loading, setLoading] = useState(false)
  const [rowBusy, setRowBusy] = useState<number | null>(null)
  const [fuentePorFila, setFuentePorFila] = useState<
    Record<number, 'BD' | 'BANCO'>
  >({})

  const pendientes = useMemo(
    () => items.filter(i => i.decision === 'PENDIENTE').length,
    [items]
  )

  const refreshResultados = async (loteId: number) => {
    const res = await conciliacionBancosService.listarResultados(loteId)
    setItems(res.items || [])
  }

  const handleCargar = async () => {
    if (!file) {
      toast.error('Seleccione el Excel (Fecha, Referencia, Monto)')
      return
    }
    setLoading(true)
    try {
      const res = await conciliacionBancosService.crearLote({
        file,
        moneda_carga: moneda,
        fecha_desde: fechaDesde,
        fecha_hasta: fechaHasta,
      })
      setLote(res.lote)
      setItems([])
      setStats(null)
      toast.success(`Lote #${res.lote.id} cargado (${moneda})`)
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setLoading(false)
    }
  }

  const handleConciliar = async () => {
    if (!lote) {
      toast.error('Cargue un Excel primero')
      return
    }
    setLoading(true)
    try {
      const cmp = await conciliacionBancosService.comparar(lote.id)
      setStats(cmp.stats || null)
      await refreshResultados(lote.id)
      toast.success('Comparacion lista. Revise fila a fila (visto o X).')
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setLoading(false)
    }
  }

  const handleVisto = async (id: number) => {
    setRowBusy(id)
    try {
      await conciliacionBancosService.decidir(id, { decision: 'VISTO' })
      if (lote) await refreshResultados(lote.id)
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setRowBusy(null)
    }
  }

  const handleCorregir = async (id: number) => {
    const fuente = fuentePorFila[id] || 'BANCO'
    setRowBusy(id)
    try {
      const r = await conciliacionBancosService.decidir(id, {
        decision: 'CORREGIR',
        fuente_elegida: fuente,
      })
      if (r.cambio)
        toast.success('Actualizado y cascada aplicada si correspondia')
      else toast.message('Sin cambios (paquete coincidente o se mantuvo BD)')
      if (lote) await refreshResultados(lote.id)
    } catch (err) {
      toast.error(errMsg(err))
      if (lote) await refreshResultados(lote.id)
    } finally {
      setRowBusy(null)
    }
  }

  const handleExport = async () => {
    if (!lote) return
    try {
      await conciliacionBancosService.descargarExcel(lote.id)
    } catch (err) {
      toast.error(errMsg(err))
    }
  }

  return (
    <div className="space-y-6">
      <ModulePageHeader
        icon={Building2}
        title="Conciliacion Bancos"
        description="Compara el Excel del banco (fecha, referencia, monto) con pagos.numero_documento (OCR). Solo admin: nada se aplica hasta Visto o X por fila."
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">1) Preparar carga</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant={moneda === 'USD' ? 'default' : 'outline'}
              onClick={() => setMoneda('USD')}
            >
              Carga USD
            </Button>
            <Button
              type="button"
              variant={moneda === 'BS' ? 'default' : 'outline'}
              onClick={() => setMoneda('BS')}
            >
              Carga Bs
            </Button>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm font-medium">
                Fecha desde
              </label>
              <Input
                type="date"
                value={fechaDesde}
                onChange={e => setFechaDesde(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">
                Fecha hasta
              </label>
              <Input
                type="date"
                value={fechaHasta}
                onChange={e => setFechaHasta(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">
                Excel (A Fecha, B Referencia, C Monto)
              </label>
              <Input
                type="file"
                accept=".xlsx,.xls"
                onChange={e => setFile(e.target.files?.[0] || null)}
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button onClick={handleCargar} disabled={loading || !file}>
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Upload className="mr-2 h-4 w-4" />
              )}
              Subir Excel
            </Button>
            <Button
              onClick={handleConciliar}
              disabled={loading || !lote}
              className="bg-blue-600 hover:bg-blue-700"
            >
              Conciliar
            </Button>
            <Button
              variant="outline"
              onClick={handleExport}
              disabled={!lote || items.length === 0}
            >
              <Download className="mr-2 h-4 w-4" />
              Reporte Excel
            </Button>
          </div>

          {lote && (
            <p className="text-sm text-gray-600">
              Lote #{lote.id} · {lote.archivo_nombre} · {lote.moneda_carga} ·{' '}
              {lote.fecha_desde} → {lote.fecha_hasta} · estado {lote.estado}
              {stats ? ` · pendientes decision: ${pendientes}` : null}
            </p>
          )}

          {stats && (
            <div className="flex flex-wrap gap-2">
              {Object.entries(stats).map(([k, v]) => (
                <Badge key={k} variant="outline">
                  {k}: {v}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            2) Resultados (referencia banco · similitud · decision)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Ref. banco</TableHead>
                <TableHead>Similitud</TableHead>
                <TableHead>Ref. BD (OCR)</TableHead>
                <TableHead>Fechas</TableHead>
                <TableHead>Montos USD</TableHead>
                <TableHead>Novedad</TableHead>
                <TableHead>Fuente</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={8}
                    className="py-8 text-center text-gray-500"
                  >
                    Sin resultados. Suba Excel y pulse Conciliar.
                  </TableCell>
                </TableRow>
              ) : (
                items.map(row => {
                  const busy = rowBusy === row.id
                  const locked =
                    row.aplicado ||
                    row.decision === 'VISTO' ||
                    row.decision === 'OMITIR'
                  return (
                    <TableRow key={row.id}>
                      <TableCell className="max-w-[160px] truncate font-mono text-xs">
                        {row.referencia_banco || '-'}
                      </TableCell>
                      <TableCell>
                        {row.similitud_pct != null
                          ? `${row.similitud_pct}%`
                          : '-'}
                      </TableCell>
                      <TableCell className="max-w-[160px] truncate font-mono text-xs">
                        {row.referencia_bd || '-'}
                      </TableCell>
                      <TableCell className="text-xs">
                        B: {row.fecha_banco || '-'}
                        <br />
                        BD: {row.fecha_bd || '-'}
                      </TableCell>
                      <TableCell className="text-xs">
                        B: {row.monto_banco ?? '-'}
                        <br />
                        BD: {row.monto_bd ?? '-'}
                      </TableCell>
                      <TableCell>
                        <Badge
                          className={
                            row.tipo_novedad === 'MATCH_EXACTO'
                              ? 'bg-green-600'
                              : row.tipo_novedad === 'SIN_BD'
                                ? 'bg-amber-600'
                                : row.tipo_novedad === 'AMBIGUO'
                                  ? 'bg-red-600'
                                  : 'bg-gray-600'
                          }
                        >
                          {row.tipo_novedad}
                        </Badge>
                        <div className="mt-1 text-xs text-gray-500">
                          {row.decision}
                          {row.aplicado ? ' · aplicado' : ''}
                        </div>
                      </TableCell>
                      <TableCell>
                        <select
                          className="rounded border px-2 py-1 text-xs"
                          disabled={locked || busy}
                          value={fuentePorFila[row.id] || 'BANCO'}
                          onChange={e =>
                            setFuentePorFila(prev => ({
                              ...prev,
                              [row.id]: e.target.value as 'BD' | 'BANCO',
                            }))
                          }
                        >
                          <option value="BANCO">Ref. Banco</option>
                          <option value="BD">Ref. BD</option>
                        </select>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            title="Visto: sin cambios"
                            disabled={locked || busy}
                            onClick={() => handleVisto(row.id)}
                          >
                            {busy ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Check className="h-4 w-4 text-green-600" />
                            )}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            title="X: corregir con fuente elegida"
                            disabled={
                              locked ||
                              busy ||
                              !row.pago_id ||
                              row.tipo_novedad === 'SIN_BD' ||
                              row.tipo_novedad === 'SIN_TASA'
                            }
                            onClick={() => handleCorregir(row.id)}
                          >
                            <X className="h-4 w-4 text-red-600" />
                          </Button>
                        </div>
                        {row.detalle_aplicacion && (
                          <p className="mt-1 max-w-[220px] text-[11px] text-gray-500">
                            {row.detalle_aplicacion}
                          </p>
                        )}
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
