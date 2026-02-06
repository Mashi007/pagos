import { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { X, Calendar, DollarSign, CheckCircle2 } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { prestamoService } from '../../services/prestamoService'

const DECLARACION_FIJA =
  'Al aprobar, usted asegura que el cliente cumple las políticas de RapiCredit y que su riesgo está dentro de parámetros normales.'

interface AprobarPrestamoManualModalProps {
  prestamo: any
  onClose: () => void
  onSuccess: () => void
}

export function AprobarPrestamoManualModal({ prestamo, onClose, onSuccess }: AprobarPrestamoManualModalProps) {
  const [fechaAprobacion, setFechaAprobacion] = useState<string>(
    new Date().toISOString().split('T')[0]
  )
  const [documentosAnalizados, setDocumentosAnalizados] = useState(false)
  const [aceptaDeclaracion, setAceptaDeclaracion] = useState(false)
  const [totalFinanciamiento, setTotalFinanciamiento] = useState<number>(
    Number(prestamo.total_financiamiento) || 0
  )
  const [numeroCuotas, setNumeroCuotas] = useState<number>(
    Number(prestamo.numero_cuotas) || 12
  )
  const [modalidadPago, setModalidadPago] = useState<string>(
    prestamo.modalidad_pago || 'MENSUAL'
  )
  const [cuotaPeriodo, setCuotaPeriodo] = useState<number>(
    Number(prestamo.cuota_periodo) || 0
  )
  const [tasaInteres, setTasaInteres] = useState<number>(
    prestamo.tasa_interes != null ? Number(prestamo.tasa_interes) : 0
  )
  const [observaciones, setObservaciones] = useState<string>(
    prestamo.observaciones || ''
  )
  const [isLoading, setIsLoading] = useState(false)

  // Calcular cuota por periodo automáticamente: monto, número de cuotas, modalidad y tasa
  const cuotaCalculada = useMemo(() => {
    if (!totalFinanciamiento || totalFinanciamiento <= 0 || !numeroCuotas || numeroCuotas <= 0) return 0
    const P = totalFinanciamiento
    const n = numeroCuotas
    const periodosPorAnio = modalidadPago === 'MENSUAL' ? 12 : modalidadPago === 'QUINCENAL' ? 24 : 52
    const tasaAnual = tasaInteres ?? 0
    const r = tasaAnual / 100 / periodosPorAnio
    if (r <= 0) return Math.round((P / n) * 100) / 100
    const factor = Math.pow(1 + r, n)
    const cuota = P * (r * factor) / (factor - 1)
    return Math.round(cuota * 100) / 100
  }, [totalFinanciamiento, numeroCuotas, modalidadPago, tasaInteres])

  useEffect(() => {
    setCuotaPeriodo(cuotaCalculada)
  }, [cuotaCalculada])

  const canSubmit =
    fechaAprobacion &&
    documentosAnalizados &&
    aceptaDeclaracion &&
    totalFinanciamiento > 0 &&
    numeroCuotas > 0

  const handleAprobar = async () => {
    if (!canSubmit) return
    setIsLoading(true)
    try {
      await prestamoService.aprobarManual(prestamo.id, {
        fecha_aprobacion: fechaAprobacion,
        acepta_declaracion: true,
        documentos_analizados: true,
        total_financiamiento: totalFinanciamiento,
        numero_cuotas: numeroCuotas,
        modalidad_pago: modalidadPago,
        cuota_periodo: cuotaPeriodo,
        tasa_interes: tasaInteres,
        observaciones: observaciones || undefined,
      })
      toast.success('Préstamo aprobado correctamente. Tabla de amortización generada.')
      onSuccess()
      onClose()
    } catch (error: any) {
      const msg = error.response?.data?.detail || error.message
      toast.error(typeof msg === 'string' ? msg : 'Error al aprobar el préstamo')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <Card>
          <CardHeader className="bg-gradient-to-r from-green-600 to-green-700 text-white">
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5" />
                Aprobar préstamo (riesgo manual) - #{prestamo.id}
              </CardTitle>
              <Button variant="ghost" size="sm" onClick={onClose} className="text-white hover:bg-green-800">
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>

          <CardContent className="p-6 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-700">Monto financiamiento *</label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="number"
                    min={0}
                    step={0.01}
                    value={totalFinanciamiento || ''}
                    onChange={(e) => setTotalFinanciamiento(Number(e.target.value) || 0)}
                    className="pl-10"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Número de cuotas *</label>
                <Input
                  type="number"
                  min={1}
                  value={numeroCuotas || ''}
                  onChange={(e) => setNumeroCuotas(Number(e.target.value) || 0)}
                />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Modalidad de pago</label>
                <Select value={modalidadPago} onValueChange={setModalidadPago}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MENSUAL">Mensual</SelectItem>
                    <SelectItem value="QUINCENAL">Quincenal</SelectItem>
                    <SelectItem value="SEMANAL">Semanal</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Cuota por periodo</label>
                <Input
                  type="number"
                  min={0}
                  step={0.01}
                  value={cuotaPeriodo || ''}
                  readOnly
                  className="bg-gray-50"
                />
                <p className="text-xs text-gray-500 mt-1">Calculada según monto, número de cuotas, modalidad y tasa de interés.</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Tasa de interés (%)</label>
                <Input
                  type="number"
                  min={0}
                  max={100}
                  step={0.1}
                  value={tasaInteres ?? ''}
                  onChange={(e) => setTasaInteres(Number(e.target.value) ?? 0)}
                />
                <p className="text-xs text-gray-500 mt-1">Por defecto 0. Al cambiar, la cuota por periodo se actualiza automáticamente.</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700">Fecha de aprobación *</label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <Input
                    type="date"
                    value={fechaAprobacion}
                    onChange={(e) => setFechaAprobacion(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">Base para la tabla de amortización.</p>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">Observaciones</label>
              <Textarea
                value={observaciones}
                onChange={(e) => setObservaciones(e.target.value)}
                placeholder="Opcional"
                rows={2}
              />
            </div>

            <div className="space-y-4 border-t pt-4">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={documentosAnalizados}
                  onChange={(e) => setDocumentosAnalizados(e.target.checked)}
                  className="mt-1"
                />
                <span className="text-sm">
                  Confirmo que se analizaron los documentos del cliente.
                </span>
              </label>
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={aceptaDeclaracion}
                  onChange={(e) => setAceptaDeclaracion(e.target.checked)}
                  className="mt-1"
                />
                <span className="text-sm">{DECLARACION_FIJA}</span>
              </label>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button
                type="button"
                className="bg-green-600 hover:bg-green-700 text-white disabled:opacity-50"
                onClick={handleAprobar}
                disabled={!canSubmit || isLoading}
              >
                {isLoading ? 'Guardando...' : 'Guardar y aprobar'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </motion.div>
  )
}
