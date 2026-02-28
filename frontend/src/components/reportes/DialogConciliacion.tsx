import { useState, useCallback } from 'react'
import { Loader2, Upload, Download, X, Eye } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'
import { Button } from '../ui/button'
import { getErrorMessage, getErrorDetail } from '../../types/errors'
import { reporteService, ResumenConciliacion } from '../../services/reporteService'
import { toast } from 'sonner'

export interface FilaConciliacion {
  cedula: string
  total_financiamiento: number
  total_abonos: number
  columna_e?: string
  columna_f?: string
}

const CEDULA_REGEX = /^[A-Za-z0-9\-]{5,20}$/

function validarCedula(cedula: string): boolean {
  const s = (cedula ?? '').trim()
  return s.length >= 5 && CEDULA_REGEX.test(s)
}

function validarNumero(val: unknown): boolean {
  if (val === null || val === undefined) return false
  const n = Number(val)
  return !Number.isNaN(n) && n >= 0
}

interface DialogConciliacionProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onGuardar?: () => void
}

export function DialogConciliacion({ open, onOpenChange, onGuardar }: DialogConciliacionProps) {
  const [filas, setFilas] = useState<FilaConciliacion[]>([])
  const [guardando, setGuardando] = useState(false)
  const [descargando, setDescargando] = useState(false)
  const [errores, setErrores] = useState<string[]>([])
  const [resumen, setResumen] = useState<ResumenConciliacion | null>(null)
  const [cargandoResumen, setCargandoResumen] = useState(false)
  const [filtroFechaInicio, setFiltroFechaInicio] = useState('')
  const [filtroFechaFin, setFiltroFechaFin] = useState('')
  const [filtroCedulas, setFiltroCedulas] = useState('')
  const [formatoDescarga, setFormatoDescarga] = useState<'excel' | 'pdf'>('excel')
  const [tab, setTab] = useState<'carga' | 'resumen'>('carga')

  const validar = useCallback((filasToValidate: FilaConciliacion[]) => {
    const err: string[] = []
    filasToValidate.forEach((f, i) => {
      if (!validarCedula(f.cedula)) err.push(`Fila ${i + 1}: cedula invalida`)
      if (!validarNumero(f.total_financiamiento)) err.push(`Fila ${i + 1}: total financiamiento debe ser un numero >= 0`)
      if (!validarNumero(f.total_abonos)) err.push(`Fila ${i + 1}: total abonos debe ser un numero >= 0`)
    })
    setErrores(err)
    return err.length === 0
  }, [])

  const handleFile = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = () => {
        try {
          const data = reader.result as ArrayBuffer
          const uint = new Uint8Array(data)
          import('xlsx').then((XLSX) => {
            const wb = XLSX.read(uint, { type: 'array' })
            const sh = wb.Sheets[wb.SheetNames[0]]
            const json: unknown[] = XLSX.utils.sheet_to_json(sh, { header: 1 })
            if (json.length < 2) {
              toast.error('El Excel debe tener al menos encabezado y una fila. Columnas: A=Cedula, B=Total financiamiento, C=Total abonos.')
              return
            }
            const rows: FilaConciliacion[] = []
            for (let i = 1; i < json.length; i++) {
              const row = (json[i] as unknown[]) as (string | number)[]
              const cedula = String(row[0] ?? '').trim()
              if (!cedula) continue
              const tf = row[1] ?? 0
              const ta = row[2] ?? 0
              const colE = row[4] != null ? String(row[4]) : ''
              const colF = row[5] != null ? String(row[5]) : ''
              rows.push({
                cedula,
                total_financiamiento: Number(tf) || 0,
                total_abonos: Number(ta) || 0,
                columna_e: colE || undefined,
                columna_f: colF || undefined,
              })
            }
            setFilas(rows)
            validar(rows)
            toast.success(`Se cargaron ${rows.length} filas. Revise y guarde.`)
          })
        } catch (err) {
          console.error(err)
          toast.error('Error al leer el Excel. Asegurese de que sea .xlsx y que la columna A sea cedula, B total financiamiento, C total abonos.')
        }
      }
      reader.readAsArrayBuffer(file)
      e.target.value = ''
    },
    [validar]
  )

  const handleGuardar = async () => {
    if (!validar(filas)) {
      toast.error('Corrija los errores antes de guardar')
      return
    }
    setGuardando(true)
    try {
      await reporteService.cargarConciliacion(filas)
      toast.success('Datos guardados correctamente. Puede descargar el reporte.')
      onGuardar?.()
      setTab('resumen')
      setFilas([])
    } catch (error: unknown) {
      const msg = getErrorDetail(error) || getErrorMessage(error) || 'Error al guardar'
      const detailData = (error as any)?.response?.data?.detail
      const erroresLista = detailData?.errores || []
      const mensaje = detailData?.mensaje || ''
      if (erroresLista && erroresLista.length > 0) {
        setErrores(erroresLista)
        toast.error(mensaje || 'Errores de validacion')
      } else {
        toast.error(msg)
      }
    } finally {
      setGuardando(false)
    }
  }

  const handleCargarResumen = async () => {
    setCargandoResumen(true)
    try {
      const res = await reporteService.obtenerResumenConciliacion(
        filtroFechaInicio || undefined,
        filtroFechaFin || undefined
      )
      setResumen(res)
      toast.success('Resumen cargado')
    } catch (err) {
      toast.error('Error al cargar resumen')
    } finally {
      setCargandoResumen(false)
    }
  }

  const handleDescargar = async () => {
    setDescargando(true)
    try {
      const blob = await reporteService.exportarReporteConciliacion(
        filtroFechaInicio || undefined,
        filtroFechaFin || undefined,
        filtroCedulas ? filtroCedulas.split(',').map(c => c.trim()) : undefined
      )
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `reporte_conciliacion_${new Date().toISOString().split('T')[0]}.${formatoDescarga === 'excel' ? 'xlsx' : 'pdf'}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      toast.success(`Reporte descargado en ${formatoDescarga.toUpperCase()}. Los datos temporales se han eliminado.`)
      onOpenChange(false)
    } catch (error: unknown) {
      toast.error(getErrorDetail(error) || getErrorMessage(error) || 'Error al descargar')
    } finally {
      setDescargando(false)
    }
  }

  const puedeGuardar = filas.length > 0 && errores.length === 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Reporte Conciliacion</DialogTitle>
        </DialogHeader>
        
        {/* Tabs */}
        <div className="flex gap-2 border-b">
          <button
            onClick={() => setTab('carga')}
            className={`px-4 py-2 ${tab === 'carga' ? 'border-b-2 border-blue-500 font-semibold' : 'text-gray-500'}`}
          >
            Cargar Datos
          </button>
          <button
            onClick={() => setTab('resumen')}
            className={`px-4 py-2 ${tab === 'resumen' ? 'border-b-2 border-blue-500 font-semibold' : 'text-gray-500'}`}
          >
            Resumen & Descarga
          </button>
        </div>

        <div className="space-y-4 overflow-auto">
          {/* Tab Carga */}
          {tab === 'carga' && (
            <>
              <p className="text-sm text-muted-foreground">
                Cargue un Excel con columnas: A = Cedula, B = Total financiamiento, C = Total abonos. Opcionales: columnas 5 y 6 para E y F.
                Corrija errores en la tabla y pulse Guardar e integrar.
              </p>
              <div className="flex flex-wrap gap-2">
                <input
                  id="conciliacion-file"
                  type="file"
                  accept=".xlsx,.xls"
                  className="hidden"
                  onChange={handleFile}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => document.getElementById('conciliacion-file')?.click()}
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Cargar Excel
                </Button>
              </div>
              {errores.length > 0 && (
                <ul className="text-sm text-red-600 list-disc pl-4">
                  {errores.map((e, i) => (
                    <li key={i}>{e}</li>
                  ))}
                </ul>
              )}
              {filas.length > 0 && (
                <div className="border rounded overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-muted">
                        <th className="p-2 text-left">Cedula (A)</th>
                        <th className="p-2 text-right">Total fin. (B)</th>
                        <th className="p-2 text-right">Total abonos (C)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filas.slice(0, 10).map((f, i) => (
                        <tr key={i}>
                          <td className="p-2">{f.cedula}</td>
                          <td className="p-2 text-right">{Number(f.total_financiamiento)}</td>
                          <td className="p-2 text-right">{Number(f.total_abonos)}</td>
                        </tr>
                      ))}
                      {filas.length > 10 && (
                        <tr>
                          <td colSpan={3} className="p-2 text-center text-gray-500">
                            ... y {filas.length - 10} filas mas
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Cerrar
                </Button>
                <Button onClick={handleGuardar} disabled={!puedeGuardar || guardando}>
                  {guardando && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                  Guardar e integrar
                </Button>
              </div>
            </>
          )}

          {/* Tab Resumen */}
          {tab === 'resumen' && (
            <>
              <p className="text-sm text-muted-foreground">
                Ver resumen de conciliacion o descargar reporte en Excel/PDF con filtros opcionales.
              </p>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">Fecha Inicio</label>
                  <input
                    type="date"
                    value={filtroFechaInicio}
                    onChange={(e) => setFiltroFechaInicio(e.target.value)}
                    className="w-full px-2 py-1 border rounded text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Fecha Fin</label>
                  <input
                    type="date"
                    value={filtroFechaFin}
                    onChange={(e) => setFiltroFechaFin(e.target.value)}
                    className="w-full px-2 py-1 border rounded text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium">Cedulas (separadas por coma)</label>
                <input
                  type="text"
                  placeholder="V12345678, E98765432"
                  value={filtroCedulas}
                  onChange={(e) => setFiltroCedulas(e.target.value)}
                  className="w-full px-2 py-1 border rounded text-sm"
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <Button
                  onClick={handleCargarResumen}
                  disabled={cargandoResumen}
                  variant="outline"
                >
                  {cargandoResumen && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                  <Eye className="h-4 w-4 mr-2" />
                  Ver Resumen
                </Button>
              </div>

              {resumen && (
                <div className="bg-blue-50 border border-blue-200 rounded p-4">
                  <h4 className="font-semibold mb-3">Resumen</h4>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-gray-600">Total Filas:</span>
                      <p className="font-semibold">{resumen.total_filas}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Filas Procesadas:</span>
                      <p className="font-semibold">{resumen.filas_procesadas}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Total Financiamiento:</span>
                      <p className="font-semibold">${resumen.monto_total_financiamiento.toLocaleString('es-ES')}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Total Abonos:</span>
                      <p className="font-semibold text-green-600">${resumen.monto_total_abonos.toLocaleString('es-ES')}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Diferencia Total:</span>
                      <p className={`font-semibold ${resumen.diferencia_total < 0 ? 'text-red-600' : 'text-green-600'}`}>
                        ${resumen.diferencia_total.toLocaleString('es-ES')}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-600">Cédulas Únicas:</span>
                      <p className="font-semibold">{resumen.cedulas_unicas}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Filas con Discrepancia:</span>
                      <p className={`font-semibold ${resumen.filas_con_discrepancia > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                        {resumen.filas_con_discrepancia}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div>
                <label className="text-sm font-medium">Formato Descarga</label>
                <select
                  value={formatoDescarga}
                  onChange={(e) => setFormatoDescarga(e.target.value as 'excel' | 'pdf')}
                  className="w-full px-2 py-1 border rounded text-sm"
                >
                  <option value="excel">Excel (.xlsx)</option>
                  <option value="pdf">PDF (.pdf)</option>
                </select>
              </div>

              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => onOpenChange(false)}>
                  Cerrar
                </Button>
                <Button onClick={handleDescargar} disabled={descargando}>
                  {descargando ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Download className="h-4 w-4 mr-2" />}
                  Descargar {formatoDescarga.toUpperCase()}
                </Button>
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
