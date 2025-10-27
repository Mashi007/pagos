import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Eye, Calendar, DollarSign, User, Building } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Prestamo } from '@/types'
import { formatDate } from '@/utils'
import { TablaAmortizacionPrestamo } from './TablaAmortizacionPrestamo'
import { usePrestamo } from '@/hooks/usePrestamos'

interface PrestamoDetalleModalProps {
  prestamo: Prestamo
  onClose: () => void
}

export function PrestamoDetalleModal({ prestamo: prestamoInitial, onClose }: PrestamoDetalleModalProps) {
  const [activeTab, setActiveTab] = useState<'detalles' | 'amortizacion' | 'auditoria'>('detalles')
  
  // Recargar datos completos del préstamo
  const { data: prestamo, isLoading } = usePrestamo(prestamoInitial.id)

  if (isLoading) {
    return (
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={(e) => e.target === e.currentTarget && onClose()}
        >
          <div className="text-center bg-white p-8 rounded-lg">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Cargando detalles del préstamo...</p>
          </div>
        </motion.div>
      </AnimatePresence>
    )
  }

  const prestamoData = prestamo || prestamoInitial

  const getEstadoBadge = (estado: string) => {
    const badges = {
      DRAFT: 'bg-gray-100 text-gray-800 border-gray-300',
      EN_REVISION: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      APROBADO: 'bg-green-100 text-green-800 border-green-300',
      RECHAZADO: 'bg-red-100 text-red-800 border-red-300',
    }
    return badges[estado as keyof typeof badges] || badges.DRAFT
  }

  const getEstadoLabel = (estado: string) => {
    const labels: Record<string, string> = {
      DRAFT: 'Borrador',
      EN_REVISION: 'En Revisión',
      APROBADO: 'Aprobado',
      RECHAZADO: 'Rechazado',
    }
    return labels[estado] || estado
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <motion.div
          initial={{ scale: 0.95, y: 20 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 20 }}
          className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="sticky top-0 bg-white border-b p-4 flex justify-between items-center z-10">
            <div>
              <h2 className="text-2xl font-bold">Detalles del Préstamo #{prestamoData.id}</h2>
              <p className="text-sm text-gray-600">Cliente: {prestamoData.nombres}</p>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Tabs */}
          <div className="border-b px-4">
            <div className="flex gap-4">
              <button
                onClick={() => setActiveTab('detalles')}
                className={`py-3 px-4 border-b-2 transition-colors ${
                  activeTab === 'detalles'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                Detalles
              </button>
              <button
                onClick={() => setActiveTab('amortizacion')}
                className={`py-3 px-4 border-b-2 transition-colors ${
                  activeTab === 'amortizacion'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                Tabla de Amortización
              </button>
              <button
                onClick={() => setActiveTab('auditoria')}
                className={`py-3 px-4 border-b-2 transition-colors ${
                  activeTab === 'auditoria'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                Auditoría
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {activeTab === 'detalles' && (
              <div className="space-y-6">
                {/* Estado */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Badge className={getEstadoBadge(prestamoData.estado)}>
                        {getEstadoLabel(prestamoData.estado)}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                </Card>

                {/* Información del Cliente */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <User className="h-5 w-5" />
                      Información del Cliente
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">Cédula</label>
                      <p className="font-medium">{prestamoData.cedula}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Nombres</label>
                      <p className="font-medium">{prestamoData.nombres}</p>
                    </div>
                  </CardContent>
                </Card>

                {/* Información del Préstamo */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <DollarSign className="h-5 w-5" />
                      Información del Préstamo
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">Total de Financiamiento</label>
                      <p className="text-2xl font-bold text-green-600">
                        ${prestamoData.total_financiamiento.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Modalidad de Pago</label>
                      <p className="font-medium">
                        {prestamoData.modalidad_pago === 'MENSUAL' ? 'Mensual' :
                         prestamoData.modalidad_pago === 'QUINCENAL' ? 'Quincenal' :
                         prestamoData.modalidad_pago === 'SEMANAL' ? 'Semanal' :
                         prestamoData.modalidad_pago}
                      </p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Número de Cuotas</label>
                      <p className="text-xl font-semibold">{prestamoData.numero_cuotas}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Cuota por Período</label>
                      <p className="text-xl font-semibold">${prestamoData.cuota_periodo.toFixed(2)}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Tasa de Interés</label>
                      <p className="font-medium">{(prestamoData.tasa_interes * 100).toFixed(2)}%</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Fecha de Requerimiento</label>
                      <p className="font-medium">{formatDate(prestamoData.fecha_requerimiento)}</p>
                    </div>
                    {prestamoData.fecha_aprobacion && (
                      <div>
                        <label className="text-sm text-gray-600">Fecha de Aprobación</label>
                        <p className="font-medium">{formatDate(prestamoData.fecha_aprobacion)}</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Información de Producto */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Building className="h-5 w-5" />
                      Producto
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">Modelo de Vehículo</label>
                      <p className="font-medium">{prestamoData.producto}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Analista Asignado</label>
                      <p className="font-medium">{prestamoData.producto_financiero}</p>
                    </div>
                  </CardContent>
                </Card>

                {/* Usuarios y Auditoría */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <Calendar className="h-5 w-5" />
                      Usuarios del Proceso
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <label className="text-sm text-gray-600">Proponente</label>
                      <p className="font-medium">{prestamoData.usuario_proponente}</p>
                      <p className="text-xs text-gray-500">{formatDate(prestamoData.fecha_registro)}</p>
                    </div>
                    {prestamoData.usuario_aprobador && (
                      <div>
                        <label className="text-sm text-gray-600">Aprobador</label>
                        <p className="font-medium">{prestamoData.usuario_aprobador}</p>
                        {prestamoData.fecha_aprobacion && (
                          <p className="text-xs text-gray-500">{formatDate(prestamoData.fecha_aprobacion)}</p>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Observaciones */}
                {prestamoData.observaciones && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Observaciones</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm">{prestamoData.observaciones}</p>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            {activeTab === 'amortizacion' && (
              <TablaAmortizacionPrestamo prestamo={prestamoData} />
            )}

            {activeTab === 'auditoria' && (
              <Card>
                <CardHeader>
                  <CardTitle>Historial de Auditoría</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-600">
                    Historial completo de cambios (implementar con useAuditoriaPrestamo)
                  </p>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Footer */}
          <div className="sticky bottom-0 bg-white border-t p-4 flex justify-end">
            <Button onClick={onClose}>Cerrar</Button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

