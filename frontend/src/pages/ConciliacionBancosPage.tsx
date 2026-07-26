import { useMemo, useState } from 'react'
import { Building2, Check, Download, Loader2, Upload } from 'lucide-react'
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
  CONCILIACION_BANCOS_CATEGORIAS,
  ConciliacionBancosBancoCategoria,
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
  const [bancosSel, setBancosSel] = useState<
    ConciliacionBancosBancoCategoria[]
  >([])
  const [filtroNovedad, setFiltroNovedad] = useState<string[]>([])

  const toggleBanco = (b: ConciliacionBancosBancoCategoria) => {
    setBancosSel(prev =>
      prev.includes(b) ? prev.filter(x => x !== b) : [...prev, b]
    )
  }

  const toggleNovedad = (tipo: string) => {
    setFiltroNovedad(prev =>
      prev.includes(tipo) ? prev.filter(x => x !== tipo) : [...prev, tipo]
    )
  }

  const pendientes = useMemo(
    () => items.filter(i => i.decision === 'PENDIENTE').length,
    [items]
  )

  const itemsFiltrados = useMemo(() => {
    if (filtroNovedad.length === 0) return items
    return items.filter(i => filtroNovedad.includes(i.tipo_novedad))
  }, [items, filtroNovedad])

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
      setFiltroNovedad([])
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
    if (bancosSel.length === 0) {
      toast.error('Seleccione al menos un banco del filtro')
      return
    }
    setLoading(true)
    try {
      const cmp = await conciliacionBancosService.comparar(lote.id, bancosSel)
      setStats(cmp.stats || null)
      setFiltroNovedad([])
      await refreshResultados(lote.id)
      toast.success(
        `Comparacion lista (bancos: ${bancosSel.join(', ')}). Pagos universo: ${cmp.pagos_universo ?? '-'}.`
      )
    } catch (err) {
      toast.error(errMsg(err))
    } finally {
      setLoading(false)
    }
  }

  /** Fuente + visto = confirmar: Ref.BD mantiene; Ref.Banco graba (cascada si aplica). */
  const handleConfirmar = async (row: ConciliacionBancosResultado) => {
    const fuente = fuentePorFila[row.id] || 'BANCO'
    setRowBusy(row.id)
    try {
      // Sin pago vinculado no hay que grabar/mantener paquete: solo cierra como revisado
      if (
        !row.pago_id ||
        row.tipo_novedad === 'SIN_BD' ||
        row.tipo_novedad === 'SIN_TASA'
      ) {
        await conciliacionBancosService.decidir(row.id, { decision: 'VISTO' })
        toast.message('Marcado como revisado (sin pago BD para aplicar)')
        if (lote) await refreshResultados(lote.id)
        return
      }
      const r = await conciliacionBancosService.decidir(row.id, {
        decision: 'CORREGIR',
        fuente_elegida: fuente,
      })
      if (fuente === 'BANCO' && r.cambio) {
        toast.success('Confirmado Ref. Banco: datos actualizados')
      } else if (fuente === 'BANCO') {
        toast.message('Confirmado Ref. Banco: ya coincidia con BD')
      } else {
        toast.message('Confirmado Ref. BD: se mantienen los datos')
      }
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
        description="Compara el Excel del banco (fecha, referencia, monto) con pagos.numero_documento (OCR). Solo admin: elija fuente (Ref. Banco o Ref. BD) y confirme con el visto."
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

          <div>
            <label className="mb-2 block text-sm font-medium">
              Filtro banco BD (seleccion multiple)
            </label>
            <div className="flex flex-wrap gap-3">
              {CONCILIACION_BANCOS_CATEGORIAS.map(b => (
                <label
                  key={b}
                  className="flex cursor-pointer items-center gap-2 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={bancosSel.includes(b)}
                    onChange={() => toggleBanco(b)}
                  />
                  {b}
                </label>
              ))}
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Solo se comparan pagos BD de los bancos marcados (segun
              institucion_bancaria).
            </p>
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
              disabled={loading || !lote || bancosSel.length === 0}
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
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                {Object.entries(stats).map(([k, v]) => {
                  const activo = filtroNovedad.includes(k)
                  return (
                    <button
                      key={k}
                      type="button"
                      onClick={() => toggleNovedad(k)}
                      title={
                        activo
                          ? 'Quitar filtro'
                          : 'Filtrar tabla por esta novedad'
                      }
                      className="rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <Badge
                        variant="outline"
                        className={
                          activo
                            ? 'cursor-pointer border-blue-600 bg-blue-600 text-white hover:bg-blue-700'
                            : 'cursor-pointer hover:border-blue-400 hover:bg-blue-50'
                        }
                      >
                        {k}: {v}
                      </Badge>
                    </button>
                  )
                })}
                {filtroNovedad.length > 0 && (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => setFiltroNovedad([])}
                  >
                    Ver todos
                  </Button>
                )}
              </div>
              <p className="text-xs text-gray-500">
                Clic en un chip para filtrar la tabla (puede marcar varios).
                {filtroNovedad.length > 0
                  ? ` Mostrando ${itemsFiltrados.length} de ${items.length}.`
                  : ''}
              </p>
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
                <TableHead>Cedula</TableHead>
                <TableHead>Prestamo</TableHead>
                <TableHead>Banco BD</TableHead>
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
                    colSpan={11}
                    className="py-8 text-center text-gray-500"
                  >
                    Sin resultados. Suba Excel y pulse Conciliar.
                  </TableCell>
                </TableRow>
              ) : itemsFiltrados.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={11}
                    className="py-8 text-center text-gray-500"
                  >
                    No hay filas para el filtro de novedad seleccionado.{' '}
                    <button
                      type="button"
                      className="text-blue-600 underline"
                      onClick={() => setFiltroNovedad([])}
                    >
                      Ver todos
                    </button>
                  </TableCell>
                </TableRow>
              ) : (
                itemsFiltrados.map(row => {
                  const busy = rowBusy === row.id
                  const locked =
                    row.aplicado ||
                    row.decision === 'VISTO' ||
                    row.decision === 'OMITIR' ||
                    (row.decision === 'CORREGIR' && row.aplicado)
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
                      <TableCell className="whitespace-nowrap text-xs">
                        {row.cedula || '-'}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs">
                        {row.prestamo_id != null ? `#${row.prestamo_id}` : '-'}
                      </TableCell>
                      <TableCell className="text-xs">
                        {row.institucion_categoria || '-'}
                        {row.institucion_bancaria ? (
                          <div className="max-w-[120px] truncate text-[11px] text-gray-500">
                            {row.institucion_bancaria}
                          </div>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-xs">
                        Banco: {row.fecha_banco || '-'}
                        <br />
                        RapiC: {row.fecha_bd || '-'}
                      </TableCell>
                      <TableCell className="text-xs">
                        Banco: {row.monto_banco ?? '-'}
                        <br />
                        RapiC: {row.monto_bd ?? '-'}
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
                            title={
                              (fuentePorFila[row.id] || 'BANCO') === 'BANCO'
                                ? 'Confirmar: grabar paquete Ref. Banco'
                                : 'Confirmar: mantener paquete Ref. BD'
                            }
                            disabled={locked || busy}
                            onClick={() => handleConfirmar(row)}
                          >
                            {busy ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Check className="h-4 w-4 text-green-600" />
                            )}
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
