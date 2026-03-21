import React, { useState, useEffect } from 'react'
import { AlertTriangle } from 'lucide-react'
import { TasaCambioModal } from './TasaCambioModal'
import { getEstadoTasa, getTasaHoy, guardarTasa } from '../services/tasaCambioService'

interface TasaCambioNotificacionProps {
  onTasaCargada?: (tasa: number) => void
}

export const TasaCambioNotificacion: React.FC<TasaCambioNotificacionProps> = ({ onTasaCargada }) => {
  const [mostrarModal, setMostrarModal] = useState(false)
  const [debeIngresar, setDebeIngresar] = useState(false)
  const [tasaActual, setTasaActual] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

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
          }
        }

        // Si debe ingresar, mostrar modal
        if (estado.debe_ingresar && !estado.tasa_ya_ingresada) {
          setMostrarModal(true)
        }
      } catch (err: any) {
        console.error('Error verificando tasa:', err)
        // No mostrar error si no hay permisos (usuario no es admin)
      } finally {
        setLoading(false)
      }
    }

    verificarTasa()
    // Re-verificar cada 5 minutos
    const interval = setInterval(verificarTasa, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [onTasaCargada])

  const handleGuardarTasa = async (tasa: number) => {
    try {
      const resultado = await guardarTasa(tasa)
      setTasaActual(resultado.tasa_oficial)
      setDebeIngresar(false)
      if (onTasaCargada) onTasaCargada(resultado.tasa_oficial)
    } catch (err: any) {
      throw err
    }
  }

  // No mostrar nada si no debe ingresar o está cargando
  if (!debeIngresar || loading) {
    return null
  }

  return (
    <>
      {/* Banner de alerta (sticky) */}
      {debeIngresar && (
        <div className="sticky top-0 z-40 bg-amber-50 border-b-2 border-amber-300 p-4 shadow-md">
          <div className="max-w-7xl mx-auto flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0" />
            <div className="flex-1">
              <p className="font-bold text-amber-900">
                ⚠️ Ingreso obligatorio: Tasa de Cambio Oficial
              </p>
              <p className="text-sm text-amber-800 mt-1">
                Debe ingresar la tasa de cambio oficial del día para continuar. Esta tasa será aplicada a todos los pagos en Bolívares.
              </p>
            </div>
            <button
              onClick={() => setMostrarModal(true)}
              className="bg-amber-600 hover:bg-amber-700 text-white font-semibold py-2 px-4 rounded-lg whitespace-nowrap transition"
            >
              Ingresar Tasa
            </button>
          </div>
        </div>
      )}

      {/* Modal para ingresar tasa */}
      <TasaCambioModal
        isOpen={mostrarModal}
        onClose={() => {
          // No permitir cerrar sin guardar si debe ingresar
          if (debeIngresar) return
          setMostrarModal(false)
        }}
        onSave={handleGuardarTasa}
        currentTasa={tasaActual}
      />
    </>
  )
}
