import React, { useState, useEffect, useRef } from 'react'

import { AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'

import { TasaCambioModal } from './TasaCambioModal'
import {
  getEstadoTasa,
  getTasaHoy,
  guardarTasa,
  type TasaCambioResponse,
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
  const [tasaHoyRow, setTasaHoyRow] = useState<TasaCambioResponse | null>(null)
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
            setTasaHoyRow(tasa)

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
              const b = tasa.tasa_bcv != null ? formatTasaBsUsd(tasa.tasa_bcv) : '—'
              const bn =
                tasa.tasa_binance != null ? formatTasaBsUsd(tasa.tasa_binance) : '—'
              toast.info(
                `Tasas del día (${fechaKey}): Euro ${formatTasaBsUsd(tasa.tasa_oficial)} · BCV ${b} · Binance ${bn} Bs./USD.`,
                { duration: 9000 }
              )
            }
          }
        } else {
          const parcial = await getTasaHoy()
          setTasaHoyRow(parcial)
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

  const handleGuardarTasa = async (p: {
    tasa_oficial: number
    tasa_bcv: number
    tasa_binance: number
  }) => {
    const resultado = await guardarTasa(p)

    setTasaHoyRow(resultado)

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
      `Tasas del día registradas: Euro ${formatTasaBsUsd(resultado.tasa_oficial)} · BCV ${formatTasaBsUsd(resultado.tasa_bcv ?? 0)} · Binance ${formatTasaBsUsd(resultado.tasa_binance ?? 0)} Bs./USD.`,
      { duration: 8000 }
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
                Ingreso obligatorio: tasas del día (Euro, BCV y Binance)
              </p>

              <p className="mt-1 text-sm text-amber-800">
                Desde las 01:00 (Caracas) debe registrar las tres tasas Bs./USD para
                continuar. Misma regla que el módulo «Tasa de cambio».
              </p>
            </div>

            <button
              type="button"
              onClick={() => setMostrarModal(true)}
              className="whitespace-nowrap rounded-lg bg-amber-600 px-4 py-2 font-semibold text-white transition hover:bg-amber-700"
            >
              Ingresar tasas
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
        tasaHoyRow={tasaHoyRow}
      />
    </>
  )
}
