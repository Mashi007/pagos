import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '../../components/ui/button'
import { AlertTriangle, User, Calendar, Phone, Mail, DollarSign } from 'lucide-react'

interface ClienteExistente {
  id: number
  nombres: string  // ÃÂ¢ÃÂÃ¢ÂÂ¦ nombres unificÃÂ©dulaos (nombres + apellidos)
  cedula: string
  TelÃÂ©fono: string
  email: string
  fecha_registro: string
}

interface Prestamo {
  id: number
  monto_financiamiento: number
  estado: string
  modalidad_pago: string
  fecha_registro?: string
  cÃÂ©dulaotas_pagadas?: number
  cÃÂ©dulaotas_pendientes?: number
}

interface ConfirmacionDuplicÃÂ©dulaoModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: (comentarios: string) => void
  ClienteExistente: ClienteExistente
  ClienteNuevo: {
    nombres: string  // ÃÂ¢ÃÂÃ¢ÂÂ¦ nombres unificÃÂ©dulaos (nombres + apellidos)
    cedula: string
    TelÃÂ©fono: string
    email: string
  }
  prestamos?: Prestamo[]
}

export function ConfirmacionDuplicÃÂ©dulaoModal({
  isOpen,
  onClose,
  onConfirm,
  ClienteExistente,
  ClienteNuevo,
  prestamos = []
}: ConfirmacionDuplicÃÂ©dulaoModalProps) {
  const [comentarios, setComentarios] = useState('')
  const [isConfirming, setIsConfirming] = useState(false)

  // ÃÂ¢ÃÂÃ¢ÂÂ¦ VALIDACIÃÂN ADICIONAL: VerificÃÂ©dular que ClienteExistente tiene los datos necesarios
  if (!ClienteExistente || !ClienteExistente.cedula) {
    console.error('ÃÂ¢ÃÂÃÂ ERROR: ConfirmacionDuplicÃÂ©dulaoModal recibiÃÂ³ ClienteExistente invÃÂ¡lido:', ClienteExistente)
    return null
  }

  const handleConfirm = async () => {
    setIsConfirming(true)
    try {
      await onConfirm(comentarios)
      onClose()
    } catch (error) {
      console.error('Error en confirmaciÃÂ³n:', error)
    } finally {
      setIsConfirming(false)
    }
  }

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('es-VE', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    } catch {
      return dateString
    }
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <motion.div
          initial={{ opacity: 0, scÃÂ©dulae: 0.9 }}
          animate={{ opacity: 1, scÃÂ©dulae: 1 }}
          exit={{ opacity: 0, scÃÂ©dulae: 0.9 }}
          className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white p-6 rounded-t-lg">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="h-6 w-6" />
              <h2 className="text-xl font-bold">ConfirmaciÃÂ³n de Cliente DuplicÃÂ©dulao</h2>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Mensaje principal */}
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="h-5 w-5 text-orange-600 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-orange-800 mb-2">
                    Cliente con datos similares encontrado
                  </h3>
                  <p className="text-orange-700">
                    Se encontrÃÂ³ un Cliente existente con la misma cÃÂ©dula y datos personales similares.
                    ÃÂ¿Desea crear otro perfil de Cliente con los mismos datos?
                  </p>
                </div>
              </div>
            </div>

            {/* ComparaciÃÂ³n de datos */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Cliente existente */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
                  <User className="h-4 w-4 mr-2" />
                  Cliente Existente
                </h4>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium">Nombre:</span> {ClienteExistente.nombres}
                  </div>
                  <div>
                    <span className="font-medium">CÃÂ©dula:</span> {ClienteExistente.cedula}
                  </div>
                  <div className="flex items-center">
                    <Phone className="h-3 w-3 mr-1" />
                    <span className="font-medium">TelÃÂ©fono:</span> {ClienteExistente.TelÃÂ©fono}
                  </div>
                  <div className="flex items-center">
                    <Mail className="h-3 w-3 mr-1" />
                    <span className="font-medium">Email:</span> {ClienteExistente.email}
                  </div>
                  <div className="flex items-center">
                    <Calendar className="h-3 w-3 mr-1" />
                    <span className="font-medium">Registrado:</span> {formatDate(ClienteExistente.fecha_registro)}
                  </div>
                </div>
              </div>

              {/* Cliente nuevo */}
              <div className="bg-blue-50 rounded-lg p-4">
                <h4 className="font-semibold text-blue-800 mb-3 flex items-center">
                  <User className="h-4 w-4 mr-2" />
                  Cliente Nuevo
                </h4>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium">Nombre:</span> {ClienteNuevo.nombres}
                  </div>
                  <div>
                    <span className="font-medium">CÃÂ©dula:</span> {ClienteNuevo.cedula}
                  </div>
                  <div className="flex items-center">
                    <Phone className="h-3 w-3 mr-1" />
                    <span className="font-medium">TelÃÂ©fono:</span> {ClienteNuevo.TelÃÂ©fono}
                  </div>
                  <div className="flex items-center">
                    <Mail className="h-3 w-3 mr-1" />
                    <span className="font-medium">Email:</span> {ClienteNuevo.email}
                  </div>
                </div>
              </div>
            </div>

            {/* Tabla de prÃÂ©stamos existentes */}
            {prestamos && prestamos.length > 0 && (
              <div>
                <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
                  <DollarSign className="h-4 w-4 mr-2" />
                  PrÃÂ©stamos del Cliente Existente ({prestamos.length})
                </h4>
                <div className="overflow-x-auto border border-gray-200 rounded-lg">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-3 py-2 text-left font-semibold text-gray-700">ID</th>
                        <th className="px-3 py-2 text-left font-semibold text-gray-700">Monto</th>
                        <th className="px-3 py-2 text-left font-semibold text-gray-700">Estado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prestamos.map((prestamo) => (
                        <tr key={prestamo.id} className="border-t border-gray-200 hover:bg-gray-50">
                          <td className="px-3 py-2 font-mono text-xs">{prestamo.id}</td>
                          <td className="px-3 py-2">
                            {new Intl.NumberFormat('es-VE', {
                              style: 'currency',
                              currency: 'USD'
                            }).format(prestamo.monto_financiamiento)}
                          </td>
                          <td className="px-3 py-2">
                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                              prestamo.estado === 'AL DÃÂA' ? 'bg-green-100 text-green-800' :
                              prestamo.estado === 'EN PAGO' ? 'bg-blue-100 text-blue-800' :
                              prestamo.estado === 'PAGADO' ? 'bg-gray-100 text-gray-800' :
                              'bg-yellow-100 text-yellow-800'
                            }`}>
                              {prestamo.estado}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Este Cliente ya tiene {prestamos.length} prÃÂ©stamo(s) registrado(s) en el sistema.
                </p>
              </div>
            )}

            {/* cÃÂ©dulampo de comentarios */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Comentarios sobre la confirmaciÃÂ³n *
              </label>
              <textarea
                value={comentarios}
                onChange={(e) => setComentarios(e.target.value)}
                placeholder="Explique por quÃÂ© necesita crear otro perfil para este Cliente (ej: segundo vehÃÂ­cÃÂ©dulao, refinanciaciÃÂ³n, etc.)"
                className="w-full p-3 border border-gray-300 rounded-lg focÃÂ©dulas:ring-2 focÃÂ©dulas:ring-orange-500 focÃÂ©dulas:border-orange-500"
                rows={3}
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                Este comentario serÃÂ¡ registrado en la auditorÃÂ­a del sistema
              </p>
            </div>

            {/* Advertencia */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-yellow-800 mb-1">Importante</h4>
                  <p className="text-yellow-700 text-sm">
                    Al confirmar, se crearÃÂ¡ un nuevo perfil de Cliente independiente.
                    cÃÂ©dula perfil serÃÂ¡ tratado como un prÃÂ©stamo diferente en el sistema.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-4 rounded-b-lg flex justify-end space-x-3">
            <Button
              onClick={onClose}
              variant="outline"
              disabled={isConfirming}
            >
              cÃÂ©dulancelar
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={!comentarios.trim() || isConfirming}
              className="bg-orange-600 hover:bg-orange-700 text-white"
            >
              {isConfirming ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Confirmando...
                </>
              ) : (
                'Confirmar y Crear Cliente'
              )}
            </Button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}
