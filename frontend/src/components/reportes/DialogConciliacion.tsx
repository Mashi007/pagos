import { useState, useCallback } from 'react'
import { Loader2, Upload, Download, X } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'
import { Button } from '../ui/button'
import { getErrorMessage, getErrorDetail } from '../../types/errors'
import { reporteService } from '../../services/reporteService'
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

  const validar = useCallback((filasToValidate: FilaConciliacion[]) => {
    const err: string[] = []
    filasToValidate.forEach((f, i) => {
      if (!validarCedula(f.cedula)) err.push(`Fila ${i + 1}: cédula inválida`)
      if (!validarNumero(f.total_financiamiento)) err.push(`Fila ${i + 1}: total financiamiento debe ser un número >= 0`)
      if (!validarNumero(f.total_abonos)) err.push(`Fila ${i + 1}: total abonos debe ser un número >= 0`)
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
              toast.error('El Excel debe tener al menos encabezado y una fila. Columnas: A=Cédula, B=Total financiamiento, C=Total abonos.')
              return
            }
            const headers = (json[0] as unknown[]) as (string | number)[]
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
          toast.error('Error al leer el Excel. Asegúrese de que sea .xlsx y que la columna A sea cédula, B total financiamiento, C total abonos.')
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
      onOpenChange(false)
      setFilas([])
    } catch (error: unknown) {
      const msg = getErrorDetail(error) || getErrorMessage(error) || 'Error al guardar'
      const detail = (error as { response?: { data?: { detail?: { errores?: string[] } } } })?.response?.data?.detail
      if (detail?.errores?.length) {
        setErrores(detail.errores)
        toast.error(detail.mensaje || 'Errores de validación')
      } else {
        toast.error(msg)
      }
    } finally {
      setGuardando(false)
    }
  }

  const handleDescargar = async () => {
    setDescargando(true)
    try {
      const blob = await reporteService.exportarReporteConciliacion()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `reporte_conciliacion_${new Date().toISOString().split('T')[0]}.xlsx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
      toast.success('Reporte descargado. Los datos temporales se han eliminado.')
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
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>Reporte Conciliación</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 overflow-auto">
          <p className="text-sm text-muted-foreground">
            Cargue un Excel con columnas: A = Cédula, B = Total financiamiento, C = Total abonos. Opcionales: columnas 5 y 6 para E y F.
            Corrija errores en la tabla y pulse Guardar e integrar. Luego puede descargar el reporte completo.
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
            <Button
              type="button"
              onClick={handleDescargar}
              disabled={descargando}
            >
              {descargando ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Download className="h-4 w-4 mr-2" />}
              Descargar reporte Excel
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
                    <th className="p-2 text-left">Cédula (A)</th>
                    <th className="p-2 text-right">Total fin. (B)</th>
                    <th className="p-2 text-right">Total abonos (C)</th>
                  </tr>
                </thead>
                <tbody>
                  {filas.map((f, i) => (
                    <tr key={i}>
                      <td className="p-2">{f.cedula}</td>
                      <td className="p-2 text-right">{Number(f.total_financiamiento)}</td>
                      <td className="p-2 text-right">{Number(f.total_abonos)}</td>
                    </tr>
                  ))}
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
        </div>
      </DialogContent>
    </Dialog>
  )
}
