import React, { useState, useEffect } from 'react'

import { AlertCircle, Check } from 'lucide-react'

import type { TasaCambioResponse } from '../services/tasaCambioService'

export type TasasMultifuenteGuardar = {
  tasa_oficial: number
  tasa_bcv: number
  tasa_binance: number
}

interface TasaCambioModalProps {
  isOpen: boolean

  onClose?: () => void

  onSave: (tasas: TasasMultifuenteGuardar) => Promise<void>

  /** Fila de hoy si existe: prellena columnas ya guardadas (ingreso parcial). */
  tasaHoyRow?: TasaCambioResponse | null
}

function numOrEmpty(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return ''
  return String(v)
}

export const TasaCambioModal: React.FC<TasaCambioModalProps> = ({
  isOpen,

  onClose,

  onSave,

  tasaHoyRow,
}) => {
  const [euro, setEuro] = useState('')
  const [bcv, setBcv] = useState('')
  const [binance, setBinance] = useState('')

  const [loading, setLoading] = useState(false)

  const [error, setError] = useState<string | null>(null)

  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (!isOpen) return
    setEuro(numOrEmpty(tasaHoyRow?.tasa_oficial))
    setBcv(numOrEmpty(tasaHoyRow?.tasa_bcv ?? null))
    setBinance(numOrEmpty(tasaHoyRow?.tasa_binance ?? null))
    setError(null)
    setSuccess(false)
  }, [isOpen, tasaHoyRow])

  const handleSave = async () => {
    setError(null)

    setSuccess(false)

    const euroN = parseFloat(euro.replace(',', '.'))
    const bcvN = parseFloat(bcv.replace(',', '.'))
    const binN = parseFloat(binance.replace(',', '.'))

    if (
      Number.isNaN(euroN) ||
      euroN <= 0 ||
      Number.isNaN(bcvN) ||
      bcvN <= 0 ||
      Number.isNaN(binN) ||
      binN <= 0
    ) {
      setError(
        'Ingrese las tres tasas (números mayores a 0): Euro, BCV y Binance.'
      )

      return
    }

    setLoading(true)

    try {
      await onSave({
        tasa_oficial: euroN,
        tasa_bcv: bcvN,
        tasa_binance: binN,
      })

      setSuccess(true)

      setEuro('')
      setBcv('')
      setBinance('')

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
      <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-lg bg-white p-6 shadow-2xl">
        <div className="mb-4 flex items-center gap-3">
          <div className="rounded-full bg-orange-100 p-2">
            <AlertCircle className="h-6 w-6 text-orange-600" />
          </div>

          <div>
            <h2 className="text-lg font-bold text-gray-900">Tasas del día</h2>

            <p className="text-sm text-gray-600">
              Euro (oficial), BCV y Binance - Bs. por 1 USD (Caracas)
            </p>
          </div>
        </div>

        <p className="mb-4 text-sm text-gray-700">
          Desde las 01:00 debe registrarse cada fuente para el día en curso.
          Misma validación que en el módulo de tasas (sin valores de plantilla
          ni cero).
        </p>

        <div className="mb-4 space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Euro / referencia (tasa_oficial)
            </label>
            <input
              type="text"
              inputMode="decimal"
              value={euro}
              onChange={e => setEuro(e.target.value)}
              placeholder="Ej: 2850.50"
              disabled={loading || success}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-orange-500"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              BCV
            </label>
            <input
              type="text"
              inputMode="decimal"
              value={bcv}
              onChange={e => setBcv(e.target.value)}
              placeholder="Ej: 36.15"
              disabled={loading || success}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-orange-500"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Binance P2P
            </label>
            <input
              type="text"
              inputMode="decimal"
              value={binance}
              onChange={e => setBinance(e.target.value)}
              placeholder="Ej: 2855.00"
              disabled={loading || success}
              className="w-full rounded-lg border border-gray-300 px-4 py-2 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-orange-500"
            />
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {success && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3">
            <Check className="h-5 w-5 text-green-600" />

            <p className="text-sm text-green-700">
              ¡Tasas guardadas exitosamente!
            </p>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={handleSave}
            disabled={
              loading ||
              success ||
              !euro.trim() ||
              !bcv.trim() ||
              !binance.trim()
            }
            className="flex-1 rounded-lg bg-orange-600 px-4 py-2 font-medium text-white transition hover:bg-orange-700 disabled:bg-gray-300"
          >
            {loading ? 'Guardando...' : 'Guardar tasas'}
          </button>
        </div>
      </div>
    </div>
  )
}
