import React, { useState, useEffect } from 'react'
import { AlertCircle, Check } from 'lucide-react'

interface TasaCambioModalProps {
  isOpen: boolean
  onClose?: () => void
  onSave: (tasa: number) => Promise<void>
  currentTasa?: number | null
}

export const TasaCambioModal: React.FC<TasaCambioModalProps> = ({
  isOpen,
  onClose,
  onSave,
  currentTasa,
}) => {
  const [tasa, setTasa] = useState<string>(currentTasa ? String(currentTasa) : '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (currentTasa) {
      setTasa(String(currentTasa))
    }
  }, [currentTasa])

  const handleSave = async () => {
    setError(null)
    setSuccess(false)

    const tasaNum = parseFloat(tasa)
    if (isNaN(tasaNum) || tasaNum <= 0) {
      setError('Ingrese una tasa válida (número mayor a 0)')
      return
    }

    setLoading(true)
    try {
      await onSave(tasaNum)
      setSuccess(true)
      setTasa('')
      // Mostrar éxito brevemente
      setTimeout(() => {
        setSuccess(false)
        if (onClose) onClose()
      }, 1500)
    } catch (err: any) {
      setError(err.message || 'Error al guardar la tasa')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-md p-6">
        {/* Encabezado */}
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-orange-100 rounded-full">
            <AlertCircle className="w-6 h-6 text-orange-600" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-gray-900">Tasa de Cambio Oficial</h2>
            <p className="text-sm text-gray-600">Banco Central de Venezuela</p>
          </div>
        </div>

        {/* Mensaje */}
        <p className="text-gray-700 text-sm mb-6">
          Ingrese la tasa oficial de cambio para hoy (BS / USD). Esta tasa será aplicada a todos los pagos en Bolívares del día.
        </p>

        {/* Input */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tasa de cambio (Bs./USD)
          </label>
          <input
            type="number"
            inputMode="decimal"
            step="0.01"
            min="0"
            value={tasa}
            onChange={(e) => setTasa(e.target.value)}
            placeholder="Ej: 2850.50"
            disabled={loading || success}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          />
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Success */}
        {success && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2">
            <Check className="w-5 h-5 text-green-600" />
            <p className="text-sm text-green-700">¡Tasa guardada exitosamente!</p>
          </div>
        )}

        {/* Botones */}
        <div className="flex gap-3">
          <button
            onClick={handleSave}
            disabled={loading || success || !tasa}
            className="flex-1 bg-orange-600 hover:bg-orange-700 disabled:bg-gray-300 text-white font-medium py-2 px-4 rounded-lg transition"
          >
            {loading ? 'Guardando...' : 'Guardar Tasa'}
          </button>
        </div>

        {/* Nota */}
        {currentTasa && (
          <p className="text-xs text-gray-500 mt-4 text-center">
            Tasa actual: <span className="font-semibold">{currentTasa}</span>
          </p>
        )}
      </div>
    </div>
  )
}
