import React, { useState } from 'react'

import { motion, AnimatePresence } from 'framer-motion'

import { Button } from '../../components/ui/button'

import {
  AlertTriangle,
  User,
  Calendar,
  Phone,
  Mail,
  DollarSign,
} from 'lucide-react'

interface ClienteExistente {
  id: number

  nombres: string // âœ… nombres unificédulaos (nombres + apellidos)

  cedula: string

  Teléfono: string

  email: string

  fecha_registro: string
}

interface Prestamo {
  id: number

  monto_financiamiento: number

  estado: string

  modalidad_pago: string

  fecha_registro?: string

  cédulaotas_pagadas?: number

  cédulaotas_pendientes?: number
}

interface ConfirmacionDuplicédulaoModalProps {
  isOpen: boolean

  onClose: () => void

  onConfirm: (comentarios: string) => void

  ClienteExistente: ClienteExistente

  ClienteNuevo: {
    nombres: string // âœ… nombres unificédulaos (nombres + apellidos)

    cedula: string

    Teléfono: string

    email: string
  }

  prestamos?: Prestamo[]
}

export function ConfirmacionDuplicédulaoModal({
  isOpen,

  onClose,

  onConfirm,

  ClienteExistente,

  ClienteNuevo,

  prestamos = [],
}: ConfirmacionDuplicédulaoModalProps) {
  const [comentarios, setComentarios] = useState('')

  const [isConfirming, setIsConfirming] = useState(false)

  // âœ… VALIDACIÓN ADICIONAL: Verificédular que ClienteExistente tiene los datos necesarios

  if (!ClienteExistente || !ClienteExistente.cedula) {
    console.error(
      'âŒ ERROR: ConfirmacionDuplicédulaoModal recibió ClienteExistente inválido:',
      ClienteExistente
    )

    return null
  }

  const handleConfirm = async () => {
    setIsConfirming(true)

    try {
      await onConfirm(comentarios)

      onClose()
    } catch (error) {
      console.error('Error en confirmación:', error)
    } finally {
      setIsConfirming(false)
    }
  }

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('es-VE', {
        year: 'numeric',

        month: 'long',

        day: 'numeric',
      })
    } catch {
      return dateString
    }
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
        <motion.div
          initial={{ opacity: 0, scédulae: 0.9 }}
          animate={{ opacity: 1, scédulae: 1 }}
          exit={{ opacity: 0, scédulae: 0.9 }}
          className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white shadow-xl"
        >
          {/* Header */}

          <div className="rounded-t-lg bg-gradient-to-r from-orange-500 to-orange-600 p-6 text-white">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="h-6 w-6" />

              <h2 className="text-xl font-bold">
                Confirmación de Cliente Duplicédulao
              </h2>
            </div>
          </div>

          {/* Content */}

          <div className="space-y-6 p-6">
            {/* Mensaje principal */}

            <div className="rounded-lg border border-orange-200 bg-orange-50 p-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="mt-0.5 h-5 w-5 text-orange-600" />

                <div>
                  <h3 className="mb-2 font-semibold text-orange-800">
                    Cliente con datos similares encontrado
                  </h3>

                  <p className="text-orange-700">
                    Se encontró un Cliente existente con la misma cédula y datos
                    personales similares. ¿Desea crear otro perfil de Cliente
                    con los mismos datos?
                  </p>
                </div>
              </div>
            </div>

            {/* Comparación de datos */}

            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              {/* Cliente existente */}

              <div className="rounded-lg bg-gray-50 p-4">
                <h4 className="mb-3 flex items-center font-semibold text-gray-800">
                  <User className="mr-2 h-4 w-4" />
                  Cliente Existente
                </h4>

                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium">Nombre:</span>{' '}
                    {ClienteExistente.nombres}
                  </div>

                  <div>
                    <span className="font-medium">Cédula:</span>{' '}
                    {ClienteExistente.cedula}
                  </div>

                  <div className="flex items-center">
                    <Phone className="mr-1 h-3 w-3" />
                    <span className="font-medium">Teléfono:</span>{' '}
                    {ClienteExistente.Teléfono}
                  </div>

                  <div className="flex items-center">
                    <Mail className="mr-1 h-3 w-3" />
                    <span className="font-medium">Email:</span>{' '}
                    {ClienteExistente.email}
                  </div>

                  <div className="flex items-center">
                    <Calendar className="mr-1 h-3 w-3" />
                    <span className="font-medium">Registrado:</span>{' '}
                    {formatDate(ClienteExistente.fecha_registro)}
                  </div>
                </div>
              </div>

              {/* Cliente nuevo */}

              <div className="rounded-lg bg-blue-50 p-4">
                <h4 className="mb-3 flex items-center font-semibold text-blue-800">
                  <User className="mr-2 h-4 w-4" />
                  Cliente Nuevo
                </h4>

                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium">Nombre:</span>{' '}
                    {ClienteNuevo.nombres}
                  </div>

                  <div>
                    <span className="font-medium">Cédula:</span>{' '}
                    {ClienteNuevo.cedula}
                  </div>

                  <div className="flex items-center">
                    <Phone className="mr-1 h-3 w-3" />
                    <span className="font-medium">Teléfono:</span>{' '}
                    {ClienteNuevo.Teléfono}
                  </div>

                  <div className="flex items-center">
                    <Mail className="mr-1 h-3 w-3" />
                    <span className="font-medium">Email:</span>{' '}
                    {ClienteNuevo.email}
                  </div>
                </div>
              </div>
            </div>

            {/* Tabla de préstamos existentes */}

            {prestamos && prestamos.length > 0 && (
              <div>
                <h4 className="mb-3 flex items-center font-semibold text-gray-800">
                  <DollarSign className="mr-2 h-4 w-4" />
                  Préstamos del Cliente Existente ({prestamos.length})
                </h4>

                <div className="overflow-x-auto rounded-lg border border-gray-200">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-100">
                      <tr>
                        <th className="px-3 py-2 text-left font-semibold text-gray-700">
                          ID
                        </th>

                        <th className="px-3 py-2 text-left font-semibold text-gray-700">
                          Monto
                        </th>

                        <th className="px-3 py-2 text-left font-semibold text-gray-700">
                          Estado
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {prestamos.map(prestamo => (
                        <tr
                          key={prestamo.id}
                          className="border-t border-gray-200 hover:bg-gray-50"
                        >
                          <td className="px-3 py-2 font-mono text-xs">
                            {prestamo.id}
                          </td>

                          <td className="px-3 py-2">
                            {new Intl.NumberFormat('es-VE', {
                              style: 'currency',

                              currency: 'USD',
                            }).format(prestamo.monto_financiamiento)}
                          </td>

                          <td className="px-3 py-2">
                            <span
                              className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                                prestamo.estado === 'AL DÍA'
                                  ? 'bg-green-100 text-green-800'
                                  : prestamo.estado === 'EN PAGO'
                                    ? 'bg-blue-100 text-blue-800'
                                    : prestamo.estado === 'PAGADO'
                                      ? 'bg-gray-100 text-gray-800'
                                      : 'bg-yellow-100 text-yellow-800'
                              }`}
                            >
                              {prestamo.estado}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <p className="mt-2 text-xs text-gray-500">
                  Este Cliente ya tiene {prestamos.length} préstamo(s)
                  registrado(s) en el sistema.
                </p>
              </div>
            )}

            {/* cédulampo de comentarios */}

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Comentarios sobre la confirmación *
              </label>

              <textarea
                value={comentarios}
                onChange={e => setComentarios(e.target.value)}
                placeholder="Explique por qué necesita crear otro perfil para este Cliente (ej: segundo vehícédulao, refinanciación, etc.)"
                className="focédulas:ring-2 focédulas:ring-orange-500 focédulas:border-orange-500 w-full rounded-lg border border-gray-300 p-3"
                rows={3}
                required
              />

              <p className="mt-1 text-xs text-gray-500">
                Este comentario será registrado en la auditoría del sistema
              </p>
            </div>

            {/* Advertencia */}

            <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="mt-0.5 h-5 w-5 text-yellow-600" />

                <div>
                  <h4 className="mb-1 font-semibold text-yellow-800">
                    Importante
                  </h4>

                  <p className="text-sm text-yellow-700">
                    Al confirmar, se creará un nuevo perfil de Cliente
                    independiente. cédula perfil será tratado como un préstamo
                    diferente en el sistema.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}

          <div className="flex justify-end space-x-3 rounded-b-lg bg-gray-50 px-6 py-4">
            <Button onClick={onClose} variant="outline" disabled={isConfirming}>
              cédulancelar
            </Button>

            <Button
              onClick={handleConfirm}
              disabled={!comentarios.trim() || isConfirming}
              className="bg-orange-600 text-white hover:bg-orange-700"
            >
              {isConfirming ? (
                <>
                  <div className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-white"></div>
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
