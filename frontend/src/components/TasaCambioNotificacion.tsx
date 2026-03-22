import React, { useState, useEffect, useRef } from 'react'

import { AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'

import { TasaCambioModal } from './TasaCambioModal'
import {
  getEstadoTasa,
  getTasaHoy,
  guardarTasa,
} from '../services/tasaCambioService'

const STORAGE_PREFIX = 'rapicredit_tasa_vigente_toast_'

function formatTasaBsUsd(val: number): string {
  if (!Number.isFinite(val)) return String(val)
  return new Intl.NumberFormat('es-VE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(val)
}

interface TasaCambioNotificacionProps {
  onTasaCargada?: (tasa: number) => void
}

export const TasaCambioNotificacion: React.FC<TasaCambioNotificacionProps> = ({
  onTasaCargada,
}) => {
  const [mostrarModal, setMostrarModal] = useState(false)
  const [debeIngresar, setDebeIngresar] = useState(false)
  const [tasaActual, setTasaActual] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const ultimaFechaToastRef = useRef<string | null>(null)

  useEffect(() => {
    const verificarTasa = async () => {
      try {
        const estado = await getEstadoTasa()

        setDebeIngresar(estado.debe_ingresar && !estado.tasa_ya_ingresada)

        if (estado.tasa_ya_ingresada) {
          const tasa = await getTasaHoy()

          if (tasa) {
            setTasaActual(tasa.tasa_oficial)

            if (onTasaCargada) onTasaCargada(tasa.tasa_oficial)

            const fechaKey = (tasa.fecha || '').slice(0, 10)
            const storageKey = STORAGE_PREFIX + fechaKey
            const yaMostrada =
              typeof sessionStorage !== 'undefined' &&
              sessionStorage.getItem(storageKey) === '1'

            if (
              fechaKey &&
              !yaMostrada &&
              ultimaFechaToastRef.current !== fechaKey
            ) {
              ultimaFechaToastRef.current = fechaKey
              try {
                sessionStorage.setItem(storageKey, '1')
              } catch {
                /* ignore */
              }
              toast.info(
                `Tasa vigente del dia (${fechaKey}): ${formatTasaBsUsd(tasa.tasa_oficial)} Bs. por 1 USD (oficial ingresada hoy).`,
                { duration: 8000 }
              )
            }
          }
        }

        if (estado.debe_ingresar && !estado.tasa_ya_ingresada) {
          setMostrarModal(true)
        }
      } catch (err: unknown) {
        console.error('Error verificando tasa:', err)
      } finally {
        setLoading(false)
      }
    }

    void verificarTasa()

    const interval = setInterval(
      () => {
        void verificarTasa()
      },
      5 * 60 * 1000
    )

    return () => clearInterval(interval)
  }, [onTasaCargada])

  const handleGuardarTasa = async (tasa: number) => {
    const resultado = await guardarTasa(tasa)

    setTasaActual(resultado.tasa_oficial)

    setDebeIngresar(false)

    if (onTasaCargada) onTasaCargada(resultado.tasa_oficial)

    const fechaKey = (resultado.fecha || '').slice(0, 10)
    if (fechaKey) {
      ultimaFechaToastRef.current = fechaKey
      try {
        sessionStorage.setItem(STORAGE_PREFIX + fechaKey, '1')
      } catch {
        /* ignore */
      }
    }
    toast.success(
      `Tasa del dia registrada: ${formatTasaBsUsd(resultado.tasa_oficial)} Bs. por 1 USD.`,
      { duration: 7000 }
    )
  }

  if (!debeIngresar || loading) {
    return null
  }

  return (
    <>
      {debeIngresar && (
        <div className="sticky top-0 z-40 border-b-2 border-amber-300 bg-amber-50 p-4 shadow-md">
          <div className="mx-auto flex max-w-7xl items-center gap-3">
            <AlertTriangle className="h-6 w-6 flex-shrink-0 text-amber-600" />

            <div className="flex-1">
              <p className="font-bold text-amber-900">
                Ingreso obligatorio: tasa de cambio oficial
              </p>

              <p className="mt-1 text-sm text-amber-800">
                Debe ingresar la tasa de cambio oficial del dia (Caracas) para
                continuar. Se aplica a pagos en bolivares segun fecha de pago y
                tasa registrada.
              </p>
            </div>

            <button
              type="button"
              onClick={() => setMostrarModal(true)}
              className="whitespace-nowrap rounded-lg bg-amber-600 px-4 py-2 font-semibold text-white transition hover:bg-amber-700"
            >
              Ingresar tasa
            </button>
          </div>
        </div>
      )}

      <TasaCambioModal
        isOpen={mostrarModal}
        onClose={() => {
          if (debeIngresar) return

          setMostrarModal(false)
        }}
        onSave={handleGuardarTasa}
        currentTasa={tasaActual}
      />
    </>
  )
}
