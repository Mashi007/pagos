import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, X, Car, DollarSign, Calendar, FileText } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Textarea } from '../../components/ui/textarea'
import { Badge } from '../../components/ui/badge'

interface PrestamoExistente {
  id: number
  modelo_vehiculo: string
  total_financiamiento: number
  saldo_pendiente: number
  cuotas_en_mora: number
  estado: string
  fecha_registro: string | null
}

interface ModalValidacionPrestamoExistenteProps {
  prestamos: PrestamoExistente[]
  totalSaldo: number
  totalCuotasMora: number
  onConfirm: (justificacion: string) => void
  onCancel: () => void
}

export function ModalValidacionPrestamoExistente({
  prestamos,
  totalSaldo,
  totalCuotasMora,
  onConfirm,
  onCancel,
}: ModalValidacionPrestamoExistenteProps) {
  const [justificacion, setJustificacion] = useState('')
  const [error, setError] = useState('')

  const handleConfirm = () => {
    if (!justificacion.trim()) {
      setError('Debe ingresar una justificaciÃ³n para continuar')
      return
    }

    if (justificacion.trim().length < 10) {
      setError('La justificaciÃ³n debe tener al menos 10 caracteres')
      return
    }

    onConfirm(justificacion.trim())
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('es-EC', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount)
  }

  const getEstadoBadge = (estado: string) => {
    const estados: Record<string, { label: string; className: string }> = {
      DRAFT: { label: 'Borrador', className: 'bg-gray-500' },
      EN_REVISION: { label: 'En RevisiÃ³n', className: 'bg-yellow-500' },
      APROBADO: { label: 'Aprobado', className: 'bg-green-500' },
      RECHAZADO: { label: 'Rechazado', className: 'bg-red-500' },
    }
    const estadoInfo = estados[estado] || { label: estado, className: 'bg-gray-500' }
    return (
      <Badge className={estadoInfo.className}>{estadoInfo.label}</Badge>
    )
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            // Solo cerrar si se hace clic fuera del modal
            onCancel()
          }
        }}
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="sticky top-0 bg-white border-b p-6 flex items-center justify-between z-10">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 rounded-full">
                <AlertTriangle className="h-6 w-6 text-yellow-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  Cliente ya tiene crÃ©dito(s) existente(s)
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  Se requiere justificaciÃ³n para crear un nuevo prÃ©stamo
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onCancel}
              className="h-8 w-8 p-0"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Resumen General */}
            <Card className="border-yellow-200 bg-yellow-50">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <DollarSign className="h-5 w-5" />
                  Resumen General
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Total PrÃ©stamos</p>
                    <p className="text-2xl font-bold">{prestamos.length}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Saldo Total Pendiente</p>
                    <p className="text-2xl font-bold text-red-600">
                      {formatCurrency(totalSaldo)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Cuotas en Mora</p>
                    <p className="text-2xl font-bold text-orange-600">
                      {totalCuotasMora}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Detalles de PrÃ©stamos */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Detalles de PrÃ©stamos Existentes</h3>
              <div className="space-y-4">
                {prestamos.map((prestamo, index) => (
                  <Card key={prestamo.id} className="border-l-4 border-l-blue-500">
                    <CardContent className="p-4">
                      <div className="grid grid-cols-4 gap-4">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <Car className="h-4 w-4 text-gray-500" />
                            <p className="text-xs text-gray-600">VehÃ­culo</p>
                          </div>
                          <p className="font-semibold">{prestamo.modelo_vehiculo || 'N/A'}</p>
                        </div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <DollarSign className="h-4 w-4 text-gray-500" />
                            <p className="text-xs text-gray-600">Total Financiamiento</p>
                          </div>
                          <p className="font-semibold">
                            {formatCurrency(prestamo.total_financiamiento)}
                          </p>
                        </div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <Calendar className="h-4 w-4 text-gray-500" />
                            <p className="text-xs text-gray-600">Saldo Pendiente</p>
                          </div>
                          <p className="font-semibold text-red-600">
                            {formatCurrency(prestamo.saldo_pendiente)}
                          </p>
                        </div>
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <AlertTriangle className="h-4 w-4 text-gray-500" />
                            <p className="text-xs text-gray-600">Estado / Cuotas Mora</p>
                          </div>
                          <div className="flex items-center gap-2">
                            {getEstadoBadge(prestamo.estado)}
                            {prestamo.cuotas_en_mora > 0 && (
                              <span className="text-xs text-orange-600 font-semibold">
                                {prestamo.cuotas_en_mora} en mora
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>

            {/* Campo de JustificaciÃ³n */}
            <Card className="border-blue-200">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  JustificaciÃ³n para Nuevo PrÃ©stamo
                  <span className="text-red-500">*</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  placeholder="Ingrese una justificaciÃ³n detallada de por quÃ© se estÃ¡ creando un nuevo prÃ©stamo cuando el cliente ya tiene crÃ©dito(s) existente(s). (MÃ­nimo 10 caracteres)"
                  value={justificacion}
                  onChange={(e) => {
                    setJustificacion(e.target.value)
                    setError('')
                  }}
                  rows={5}
                  className={error ? 'border-red-500' : ''}
                />
                {error && (
                  <p className="text-sm text-red-600">{error}</p>
                )}
                <p className="text-xs text-gray-500">
                  Esta justificaciÃ³n serÃ¡ guardada junto con el prÃ©stamo y quedarÃ¡ registrada como parte de la auditorÃ­a.
                </p>
              </CardContent>
            </Card>

            {/* Buttons */}
            <div className="flex justify-end gap-3 pt-4 border-t">
              <Button variant="outline" onClick={onCancel}>
                Cancelar
              </Button>
              <Button
                onClick={handleConfirm}
                className="bg-blue-600 hover:bg-blue-700"
                disabled={!justificacion.trim() || justificacion.trim().length < 10}
              >
                Autorizar y Continuar
              </Button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

