import React, { useState, useEffect } from 'react'

import { AlertCircle, Check } from 'lucide-react'

import type { TasaCambioResponse } from '../services/tasaCambioService'

export type TasasMultifuenteGuardar = {
  tasa_oficial: number
  tasa_bcv?: number
}

interface TasaCambioModalProps {
  isOpen: boolean
  onClose?: () => void
  onSave: (tasas: TasasMultifuenteGuardar) => Promise<void>
  tasaHoyRow?: TasaCambioResponse | null
  /** No se puede cerrar hasta guardar (aviso forzado a itmaster). */
  cannotClose?: boolean
  /** Fecha valor BCV que hay que cargar (siguiente hábil). */
  fechaValorLabel?: string | null
  requireBcv?: boolean
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
  cannotClose = false,
  fechaValorLabel,
  requireBcv = false,
}) => {
  const [euro, setEuro] = useState('')
  const [bcv, setBcv] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (!isOpen) return
    setEuro(numOrEmpty(tasaHoyRow?.tasa_oficial))
    setBcv(numOrEmpty(tasaHoyRow?.tasa_bcv ?? null))
    setError(null)
    setSuccess(false)
  }, [isOpen, tasaHoyRow])

  const handleSave = async () => {
    setError(null)
    setSuccess(false)

    const euroN = parseFloat(euro.replace(',', '.'))
    const bcvTrim = bcv.trim()
    const bcvN = bcvTrim ? parseFloat(bcv.replace(',', '.')) : NaN

    if (Number.isNaN(euroN) || euroN <= 0) {
      setError('Ingrese la tasa Euro (número mayor a 0).')
      return
    }
    if (requireBcv && (!bcvTrim || Number.isNaN(bcvN) || bcvN <= 0)) {
      setError('Ingrese la tasa BCV (el automático no la pudo cargar).')
      return
    }
    if (bcvTrim && (Number.isNaN(bcvN) || bcvN <= 0)) {
      setError('La tasa BCV, si la indica, debe ser un número mayor a 0.')
      return
    }

    setLoading(true)
    try {
      const payload: TasasMultifuenteGuardar = { tasa_oficial: euroN }
      if (bcvTrim) payload.tasa_bcv = bcvN
      await onSave(payload)
      setSuccess(true)
      setTimeout(() => {
        setSuccess(false)
        if (onClose && !cannotClose) onClose()
      }, 1500)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al guardar la tasa'
      setError(msg)
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
            <h2 className="text-lg font-bold text-gray-900">
              {cannotClose ? 'Carga manual de BCV' : 'Tasas del día'}
            </h2>
            <p className="text-sm text-gray-600">
              Euro (manual) y BCV — Bs. por 1 USD
              {fechaValorLabel ? ` · fecha valor ${fechaValorLabel}` : ''}
            </p>
          </div>
        </div>

        <p className="mb-4 text-sm text-gray-700">
          {cannotClose
            ? 'El recuadro BCV no se pudo leer automáticamente esta tarde. Cargue Euro y BCV para la fecha valor indicada. El resto de usuarios no está bloqueado.'
            : 'El BCV se actualiza solo en días hábiles cuando publica la fecha valor del día siguiente. Aquí puede corregir Euro o BCV si hace falta.'}
        </p>

        <div className="mb-4 space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-gray-700">
              Euro / referencia
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
              {requireBcv ? 'BCV (obligatorio)' : 'BCV (opcional si ya la trajo el sistema)'}
            </label>
            <input
              type="text"
              inputMode="decimal"
              value={bcv}
              onChange={e => setBcv(e.target.value)}
              placeholder="Se llena sola al publicar el BCV"
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
            <p className="text-sm text-green-700">Tasas guardadas.</p>
          </div>
        )}

        <div className="flex gap-3">
          {onClose && !cannotClose ? (
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Cerrar
            </button>
          ) : null}
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={loading || success || !euro.trim() || (requireBcv && !bcv.trim())}
            className="flex-1 rounded-lg bg-orange-600 px-4 py-2 font-medium text-white transition hover:bg-orange-700 disabled:bg-gray-300"
          >
            {loading ? 'Guardando...' : 'Guardar'}
          </button>
        </div>
      </div>
    </div>
  )
}
