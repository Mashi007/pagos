import React, { useState, useEffect } from 'react'
import { TrendingUp, Calendar } from 'lucide-react'
import { TasaCambioModal } from '../components/TasaCambioModal'
import { getTasaHoy, guardarTasa, getHistorialTasas, TasaCambioHistorial } from '../services/tasaCambioService'

export const AdminTasaCambioPage: React.FC = () => {
  const [tasaHoy, setTasaHoy] = useState<number | null>(null)
  const [historial, setHistorial] = useState<TasaCambioHistorial[]>([])
  const [mostrarModal, setMostrarModal] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    cargarDatos()
  }, [])

  const cargarDatos = async () => {
    setLoading(true)
    setError(null)
    try {
      const tasa = await getTasaHoy()
      if (tasa) {
        setTasaHoy(tasa.tasa_oficial)
      }
      const hist = await getHistorialTasas(60)
      setHistorial(hist)
    } catch (err: any) {
      setError(err.message || 'Error al cargar datos')
    } finally {
      setLoading(false)
    }
  }

  const handleGuardarTasa = async (tasa: number) => {
    try {
      const resultado = await guardarTasa(tasa)
      setTasaHoy(resultado.tasa_oficial)
      // Recargar historial
      const hist = await getHistorialTasas(60)
      setHistorial(hist)
    } catch (err: any) {
      throw err
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-600">Cargando...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Encabezado */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-3 bg-orange-100 rounded-lg">
              <TrendingUp className="w-6 h-6 text-orange-600" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Tasa de Cambio Oficial</h1>
              <p className="text-gray-600">Gestiona las tasas diarias BS/USD</p>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Card de Tasa Actual */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-sm text-gray-600 mb-1">Tasa de Hoy</p>
              <p className="text-3xl font-bold text-gray-900">
                {tasaHoy ? `${tasaHoy.toFixed(2)}` : '-'}
              </p>
              <p className="text-xs text-gray-500 mt-2">Bs./USD</p>
            </div>

            <div>
              <p className="text-sm text-gray-600 mb-1">Fecha Actual</p>
              <p className="text-lg font-semibold text-gray-900">
                {new Date().toLocaleDateString('es-VE', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </p>
            </div>

            <div className="flex items-end">
              <button
                onClick={() => setMostrarModal(true)}
                className="w-full bg-orange-600 hover:bg-orange-700 text-white font-semibold py-2 px-4 rounded-lg transition"
              >
                {tasaHoy ? 'Actualizar Tasa' : 'Ingresar Tasa'}
              </button>
            </div>
          </div>
        </div>

        {/* Historial de Tasas */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="border-b border-gray-200 p-6">
            <div className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-gray-600" />
              <h2 className="text-xl font-bold text-gray-900">Historial de Tasas</h2>
            </div>
          </div>

          {historial.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-gray-600">No hay tasas registradas</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700">Fecha</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700">Tasa (BS/USD)</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700">Ingresado Por</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700">Actualizado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {historial.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-50 transition">
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">
                        {new Date(item.fecha).toLocaleDateString('es-VE')}
                      </td>
                      <td className="px-6 py-4 text-sm font-semibold text-orange-600">
                        {item.tasa_oficial.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {item.usuario_email || '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {item.updated_at
                          ? new Date(item.updated_at).toLocaleString('es-VE', {
                              year: 'numeric',
                              month: '2-digit',
                              day: '2-digit',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Modal */}
      <TasaCambioModal isOpen={mostrarModal} onClose={() => setMostrarModal(false)} onSave={handleGuardarTasa} currentTasa={tasaHoy} />
    </div>
  )
}
