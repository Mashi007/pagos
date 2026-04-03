import React, { useState, useEffect } from 'react'

import {
  TrendingUp,
  Calendar,
  Check,
  AlertCircle,
  Plus,
  RefreshCw,
  Wrench,
} from 'lucide-react'

import { TasaCambioModal } from '../components/TasaCambioModal'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

import {
  getTasaHoy,
  guardarTasa,
  guardarTasaPorFecha,
  getHistorialTasas,
  getTasasProblematicas,
  rellenarTasasDesdeVecino,
  type RellenarTasasDesdeVecinoResponse,
  type TasasProblematicasResponse,
  type TasaCambioHistorial,
} from '../services/tasaCambioService'
import { toast } from 'sonner'

export const AdminTasaCambioPage: React.FC = () => {
  const [tasaHoy, setTasaHoy] = useState<number | null>(null)

  const [historial, setHistorial] = useState<TasaCambioHistorial[]>([])

  const [mostrarModal, setMostrarModal] = useState(false)

  const [fechaTasaPago, setFechaTasaPago] = useState('')

  const [tasaParaFecha, setTasaParaFecha] = useState('')

  const [guardandoFecha, setGuardandoFecha] = useState(false)

  const [loading, setLoading] = useState(true)

  const [error, setError] = useState<string | null>(null)

  const [tasaGuardadaExito, setTasaGuardadaExito] = useState(false)

  const [mostrarFormAgregar, setMostrarFormAgregar] = useState(false)

  const [tasasProblematicasRes, setTasasProblematicasRes] =
    useState<TasasProblematicasResponse | null>(null)

  const [cargandoProblematicas, setCargandoProblematicas] = useState(false)

  const [propuestaRelleno, setPropuestaRelleno] =
    useState<RellenarTasasDesdeVecinoResponse | null>(null)

  const [rellenoEnCurso, setRellenoEnCurso] = useState(false)

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

  const handleGuardarTasaPorFechaPago = async () => {
    if (!fechaTasaPago.trim()) {
      toast.error('Seleccione la fecha de pago')
      return
    }
    const tasaNum = parseFloat(tasaParaFecha.replace(',', '.'))
    if (Number.isNaN(tasaNum) || tasaNum <= 0) {
      toast.error('Ingrese la tasa oficial (Bs. por 1 USD), mayor que cero')
      return
    }
    setGuardandoFecha(true)
    try {
      await guardarTasaPorFecha(fechaTasaPago.trim(), tasaNum)
      toast.success(`Tasa guardada para ${fechaTasaPago}`)
      setTasaParaFecha('')
      setFechaTasaPago('')
      setTasaGuardadaExito(true)
      setTimeout(() => setTasaGuardadaExito(false), 3000)
      const hist = await getHistorialTasas(60)
      setHistorial(hist)
      setMostrarFormAgregar(false)
    } catch (err: any) {
      toast.error(err?.message || 'No se pudo guardar la tasa')
    } finally {
      setGuardandoFecha(false)
    }
  }

  const consultarProblematicas = async (clearPropuesta = true) => {
    setCargandoProblematicas(true)
    if (clearPropuesta) setPropuestaRelleno(null)
    try {
      const res = await getTasasProblematicas()
      setTasasProblematicasRes(res)
      if (res.total === 0) {
        toast.success('No hay tasas problematicas en la tabla')
      }
    } catch (err: any) {
      toast.error(err?.message || 'No se pudo consultar')
      setTasasProblematicasRes(null)
    } finally {
      setCargandoProblematicas(false)
    }
  }

  const simularRelleno = async () => {
    setRellenoEnCurso(true)
    try {
      const res = await rellenarTasasDesdeVecino(true)
      setPropuestaRelleno(res)
      toast.message(
        `Simulacion: ${String(res.filas_con_propuesta)} de ${String(res.filas_problematicas)} filas con vecino valido`
      )
    } catch (err: any) {
      toast.error(err?.message || 'Error en simulacion')
    } finally {
      setRellenoEnCurso(false)
    }
  }

  const aplicarRelleno = async () => {
    if (
      !window.confirm(
        'Se actualizaran en la base de datos las tasas problematicas usando la tasa de la fecha valida mas cercana. ¿Continuar?'
      )
    ) {
      return
    }
    setRellenoEnCurso(true)
    try {
      const res = await rellenarTasasDesdeVecino(false)
      setPropuestaRelleno(res)
      toast.success(
        `Actualizadas ${String(res.filas_con_propuesta)} fila(s). Revise contra la fuente BCV si aplica.`
      )
      await consultarProblematicas(false)
      const hist = await getHistorialTasas(60)
      setHistorial(hist)
    } catch (err: any) {
      toast.error(err?.message || 'No se pudo aplicar')
    } finally {
      setRellenoEnCurso(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-600">Cargando...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-6xl">
        {/* Encabezado */}

        <div className="mb-8">
          <ModulePageHeader
            icon={TrendingUp}
            title="Tasa de Cambio Oficial"
            description="Gestiona las tasas diarias BS/USD"
          />
        </div>

        {/* Error */}

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Card de Tasa Actual */}

        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            <div>
              <p className="mb-1 text-sm text-gray-600">Tasa de Hoy</p>

              <p className="text-3xl font-bold text-gray-900">
                {tasaHoy ? `${tasaHoy.toFixed(2)}` : '-'}
              </p>

              <p className="mt-2 text-xs text-gray-500">Bs./USD</p>
            </div>

            <div>
              <p className="mb-1 text-sm text-gray-600">Fecha Actual</p>

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
                className="w-full rounded-lg bg-orange-600 px-4 py-2 font-semibold text-white transition hover:bg-orange-700"
              >
                {tasaHoy ? 'Actualizar Tasa' : 'Ingresar Tasa'}
              </button>
            </div>
          </div>
        </div>

        {/* Tasa por fecha de pago (bolívares / backfill) */}

        <div className="mb-6 rounded-lg border border-amber-200 bg-gradient-to-br from-amber-50 to-amber-50/50 p-6 shadow-sm">
          <div className="mb-6 flex items-start justify-between">
            <div>
              <h2 className="mb-1 flex items-center gap-2 text-lg font-bold text-gray-900">
                <Plus className="h-5 w-5 text-amber-700" />
                Agregar Tasa para Fecha de Pago
              </h2>
              <p className="text-sm text-gray-700">
                Use la <strong>fecha de pago</strong> del reporte o comprobante.
                Es la tasa oficial Bs./USD para convertir bolívares a dólares.
                Ideal para días pasados o faltantes que no cuentan con tasa
                registrada.
              </p>
            </div>
            {tasaGuardadaExito && (
              <div className="flex items-center gap-2 rounded-lg bg-green-100 px-3 py-2 text-sm text-green-700">
                <Check className="h-4 w-4" />
                Guardado
              </div>
            )}
          </div>

          {mostrarFormAgregar ? (
            <div className="space-y-4 rounded-lg bg-white p-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                {/* Fecha */}
                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700">
                    Fecha de Pago
                  </label>
                  <input
                    type="date"
                    value={fechaTasaPago}
                    onChange={e => setFechaTasaPago(e.target.value)}
                    max={new Date().toISOString().split('T')[0]}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 shadow-sm transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Seleccione la fecha del pago
                  </p>
                </div>

                {/* Tasa */}
                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700">
                    Tasa Oficial (Bs. por 1 USD)
                  </label>
                  <input
                    type="text"
                    inputMode="decimal"
                    placeholder="ej. 3105.75"
                    value={tasaParaFecha}
                    onChange={e => setTasaParaFecha(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 shadow-sm transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Mayor a 0; no use valores de plantilla SQL (ej. 99999.99)
                  </p>
                </div>

                {/* Validación */}
                <div className="flex items-end gap-2">
                  {fechaTasaPago && tasaParaFecha && (
                    <div className="flex items-center gap-1 rounded-lg bg-green-50 px-3 py-2 text-xs text-green-700">
                      <Check className="h-3.5 w-3.5" />
                      Listo
                    </div>
                  )}
                </div>
              </div>

              {/* Botones de acción */}
              <div className="flex gap-2 border-t border-gray-200 pt-4">
                <button
                  type="button"
                  disabled={guardandoFecha || !fechaTasaPago || !tasaParaFecha}
                  onClick={() => void handleGuardarTasaPorFechaPago()}
                  className="flex-1 rounded-lg bg-amber-700 px-4 py-2.5 font-semibold text-white shadow-sm transition hover:bg-amber-800 disabled:cursor-not-allowed disabled:bg-gray-300 disabled:text-gray-500"
                >
                  {guardandoFecha ? 'Guardando…' : 'Guardar Tasa'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMostrarFormAgregar(false)
                    setFechaTasaPago('')
                    setTasaParaFecha('')
                  }}
                  disabled={guardandoFecha}
                  className="rounded-lg border border-gray-300 px-4 py-2.5 font-semibold text-gray-700 transition hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancelar
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setMostrarFormAgregar(true)}
              className="w-full rounded-lg border-2 border-dashed border-amber-300 bg-amber-50 px-4 py-3 font-semibold text-amber-700 transition hover:border-amber-400 hover:bg-amber-100"
            >
              + Agregar nueva tasa por fecha
            </button>
          )}

          {/* Información de validación */}
          <div className="mt-4 flex gap-3 rounded-lg bg-blue-50 p-3 text-xs text-blue-700">
            <AlertCircle
              className="h-4 w-4 flex-shrink-0 text-blue-600"
              style={{ marginTop: '2px' }}
            />
            <div>
              <strong>Nota:</strong> Esta tasa se usará automáticamente para
              pagos registrados en Bs. con la misma fecha. Si el reporte tiene
              múltiples fechas, agrégalas todas. La API rechaza tasas de ejemplo
              tipo 99999.99 de scripts; use la tasa BCV real.
            </div>
          </div>
        </div>

        {/* Tasas invalidas / relleno desde vecino */}

        <div className="mb-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-start gap-2">
              <Wrench className="mt-0.5 h-5 w-5 shrink-0 text-slate-600" />
              <div>
                <h2 className="text-lg font-bold text-gray-900">
                  Tasas problematicas (0, negativas o placeholder)
                </h2>
                <p className="text-sm text-gray-600">
                  Detecta filas en{' '}
                  <code className="text-xs">tasas_cambio_diaria</code> que
                  rompen conversiones BS/USD. Puede simular o aplicar un relleno
                  copiando la tasa de la fecha valida mas cercana (no sustituye
                  verificar el dato oficial BCV).
                </p>
              </div>
            </div>
            <button
              type="button"
              disabled={cargandoProblematicas || rellenoEnCurso}
              onClick={() => void consultarProblematicas()}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
            >
              {cargandoProblematicas ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Consultar problematicas
            </button>
          </div>

          {tasasProblematicasRes != null && tasasProblematicasRes.total > 0 ? (
            <div className="space-y-4">
              <p className="text-sm font-medium text-amber-800">
                {tasasProblematicasRes.total} fecha(s) con tasa invalida o de
                ejemplo
              </p>
              <div className="max-h-48 overflow-auto rounded border border-slate-200">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-slate-100">
                    <tr>
                      <th className="px-3 py-2 text-left">Fecha</th>
                      <th className="px-3 py-2 text-left">Tasa actual</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {tasasProblematicasRes.filas.map(f => (
                      <tr key={f.fecha}>
                        <td className="px-3 py-2 font-mono">{f.fecha}</td>
                        <td className="px-3 py-2">
                          {f.tasa_oficial != null
                            ? f.tasa_oficial.toFixed(2)
                            : '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={rellenoEnCurso}
                  onClick={() => void simularRelleno()}
                  className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-900 disabled:bg-gray-400"
                >
                  Simular relleno desde vecino
                </button>
                <button
                  type="button"
                  disabled={rellenoEnCurso}
                  onClick={() => void aplicarRelleno()}
                  className="rounded-lg bg-orange-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-700 disabled:bg-gray-400"
                >
                  Aplicar relleno en BD
                </button>
              </div>
            </div>
          ) : tasasProblematicasRes != null ? (
            <p className="text-sm text-green-700">
              La ultima consulta no encontro filas problematicas.
            </p>
          ) : null}

          {propuestaRelleno != null && propuestaRelleno.cambios.length > 0 ? (
            <div className="mt-6 border-t border-slate-200 pt-4">
              <h3 className="mb-2 text-sm font-semibold text-slate-800">
                {propuestaRelleno.dry_run
                  ? 'Resultado simulacion'
                  : 'Ultimo resultado (aplicado)'}
              </h3>
              <p className="mb-2 text-xs text-slate-600">
                Con propuesta: {propuestaRelleno.filas_con_propuesta} /{' '}
                {propuestaRelleno.filas_problematicas}
              </p>
              <div className="max-h-56 overflow-auto rounded border border-slate-200">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-slate-50">
                    <tr>
                      <th className="px-2 py-1.5 text-left">Fecha</th>
                      <th className="px-2 py-1.5 text-left">Antes</th>
                      <th className="px-2 py-1.5 text-left">Propuesta</th>
                      <th className="px-2 py-1.5 text-left">OK</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {propuestaRelleno.cambios.map(c => (
                      <tr key={c.fecha}>
                        <td className="px-2 py-1.5 font-mono">{c.fecha}</td>
                        <td className="px-2 py-1.5">
                          {c.tasa_anterior != null
                            ? c.tasa_anterior.toFixed(2)
                            : '-'}
                        </td>
                        <td className="px-2 py-1.5">
                          {c.tasa_propuesta != null
                            ? c.tasa_propuesta.toFixed(2)
                            : '-'}
                        </td>
                        <td className="px-2 py-1.5">
                          {c.aplicable ? 'Si' : 'No'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </div>

        {/* Historial de Tasas */}

        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-200 p-6">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-gray-600" />

              <h2 className="text-xl font-bold text-gray-900">
                Historial de Tasas
              </h2>
            </div>
          </div>

          {historial.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-gray-600">No hay tasas registradas</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-gray-200 bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700">
                      Fecha
                    </th>

                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700">
                      Tasa (BS/USD)
                    </th>

                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700">
                      Ingresado Por
                    </th>

                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700">
                      Actualizado
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-gray-200">
                  {historial.map(item => (
                    <tr key={item.id} className="transition hover:bg-gray-50">
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

      <TasaCambioModal
        isOpen={mostrarModal}
        onClose={() => setMostrarModal(false)}
        onSave={handleGuardarTasa}
        currentTasa={tasaHoy}
      />
    </div>
  )
}
