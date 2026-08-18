import React, { useState, useEffect } from 'react'

import {
  TrendingUp,
  Calendar,
  Check,
  AlertCircle,
  Pencil,
  RefreshCw,
  Wrench,
} from 'lucide-react'

import { TasaCambioModal } from '../components/TasaCambioModal'

import { ModulePageHeader } from '../components/ui/ModulePageHeader'

import {
  getTasaHoy,
  getTasaPorFecha,
  guardarTasa,
  editarUnaTasa,
  getHistorialTasas,
  type FuenteTasaEdicion,
  getTasasProblematicas,
  rellenarTasasDesdeVecino,
  type RellenarTasasDesdeVecinoResponse,
  type TasasProblematicasResponse,
  type TasaCambioHistorial,
  type TasaCambioResponse,
} from '../services/tasaCambioService'
import { toast } from 'sonner'

export const AdminTasaCambioPage: React.FC = () => {
  const [tasaHoyRow, setTasaHoyRow] = useState<TasaCambioResponse | null>(null)

  const [historial, setHistorial] = useState<TasaCambioHistorial[]>([])

  const [mostrarModal, setMostrarModal] = useState(false)

  const [fechaTasaPago, setFechaTasaPago] = useState('')

  const [tasaParaFecha, setTasaParaFecha] = useState('')

  const [fuenteEdicion, setFuenteEdicion] =
    useState<FuenteTasaEdicion>('euro')

  const [filaFechaActual, setFilaFechaActual] =
    useState<TasaCambioResponse | null>(null)

  const [guardandoFecha, setGuardandoFecha] = useState(false)

  const [loading, setLoading] = useState(true)

  const [error, setError] = useState<string | null>(null)

  const [tasaGuardadaExito, setTasaGuardadaExito] = useState(false)

  const [mostrarFormAgregar, setMostrarFormAgregar] = useState(true)

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

      setTasaHoyRow(tasa)

      const hist = await getHistorialTasas(60)

      setHistorial(hist)
    } catch (err: any) {
      setError(err.message || 'Error al cargar datos')
    } finally {
      setLoading(false)
    }
  }

  const handleGuardarTasa = async (p: {
    tasa_oficial: number
    tasa_bcv: number
    tasa_binance: number
  }) => {
    try {
      const resultado = await guardarTasa(p)

      setTasaHoyRow(resultado)

      // Recargar historial

      const hist = await getHistorialTasas(60)

      setHistorial(hist)
    } catch (err: any) {
      throw err
    }
  }

  const etiquetaFuente = (f: FuenteTasaEdicion) =>
    f === 'euro' ? 'Euro' : f === 'bcv' ? 'BCV' : 'Binance'

  const cargarFilaFecha = async (fecha: string) => {
    if (!fecha.trim()) {
      setFilaFechaActual(null)
      return
    }
    try {
      const fila = await getTasaPorFecha(fecha.trim())
      setFilaFechaActual(fila)
    } catch {
      setFilaFechaActual(null)
    }
  }

  const abrirEdicionFecha = (fechaIso: string, fuente: FuenteTasaEdicion) => {
    const fecha = fechaIso.slice(0, 10)
    setFechaTasaPago(fecha)
    setFuenteEdicion(fuente)
    setMostrarFormAgregar(true)
    void (async () => {
      try {
        const fila = await getTasaPorFecha(fecha)
        setFilaFechaActual(fila)
        const actual =
          fuente === 'euro'
            ? fila?.tasa_oficial
            : fuente === 'bcv'
              ? fila?.tasa_bcv
              : fila?.tasa_binance
        setTasaParaFecha(
          actual != null && Number.isFinite(Number(actual))
            ? String(actual)
            : ''
        )
      } catch {
        setFilaFechaActual(null)
        setTasaParaFecha('')
      }
    })()
  }

  const handleGuardarTasaPorFechaPago = async () => {
    if (!fechaTasaPago.trim()) {
      toast.error('Seleccione la fecha')
      return
    }
    const tasaNum = parseFloat(tasaParaFecha.replace(',', '.'))
    if (Number.isNaN(tasaNum) || tasaNum <= 0) {
      toast.error('Ingrese un valor mayor que cero (Bs. por 1 USD)')
      return
    }
    setGuardandoFecha(true)
    try {
      const resultado = await editarUnaTasa(
        fechaTasaPago.trim(),
        fuenteEdicion,
        tasaNum
      )
      toast.success(
        `${etiquetaFuente(fuenteEdicion)} actualizada para ${fechaTasaPago}`
      )
      setFilaFechaActual(resultado)
      setTasaGuardadaExito(true)
      setTimeout(() => setTasaGuardadaExito(false), 3000)
      const hist = await getHistorialTasas(60)
      setHistorial(hist)
      const hoy = await getTasaHoy()
      setTasaHoyRow(hoy)
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
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
            <div>
              <p className="mb-1 text-sm text-gray-600">Euro (hoy)</p>

              <p className="text-2xl font-bold text-gray-900">
                {tasaHoyRow?.tasa_oficial != null
                  ? `${tasaHoyRow.tasa_oficial.toFixed(2)}`
                  : '-'}
              </p>

              <p className="mt-2 text-xs text-gray-500">Bs./USD</p>
              <button
                type="button"
                onClick={() =>
                  abrirEdicionFecha(
                    tasaHoyRow?.fecha ||
                      new Date().toISOString().slice(0, 10),
                    'euro'
                  )
                }
                className="mt-3 inline-flex items-center gap-1 rounded-md bg-amber-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-amber-700"
              >
                <Pencil className="h-3.5 w-3.5" />
                Editar Euro
              </button>
            </div>

            <div>
              <p className="mb-1 text-sm text-gray-600">BCV (hoy)</p>

              <p className="text-2xl font-bold text-gray-900">
                {tasaHoyRow?.tasa_bcv != null
                  ? `${tasaHoyRow.tasa_bcv.toFixed(2)}`
                  : '-'}
              </p>

              <p className="mt-2 text-xs text-gray-500">Bs./USD</p>
              <button
                type="button"
                onClick={() =>
                  abrirEdicionFecha(
                    tasaHoyRow?.fecha ||
                      new Date().toISOString().slice(0, 10),
                    'bcv'
                  )
                }
                className="mt-3 inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
              >
                <Pencil className="h-3.5 w-3.5" />
                Editar BCV
              </button>
            </div>

            <div>
              <p className="mb-1 text-sm text-gray-600">Binance (hoy)</p>

              <p className="text-2xl font-bold text-gray-900">
                {tasaHoyRow?.tasa_binance != null
                  ? `${tasaHoyRow.tasa_binance.toFixed(2)}`
                  : '-'}
              </p>

              <p className="mt-2 text-xs text-gray-500">Bs./USD</p>
              <button
                type="button"
                onClick={() =>
                  abrirEdicionFecha(
                    tasaHoyRow?.fecha ||
                      new Date().toISOString().slice(0, 10),
                    'binance'
                  )
                }
                className="mt-3 inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
              >
                <Pencil className="h-3.5 w-3.5" />
                Editar Binance
              </button>
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

              <button
                type="button"
                onClick={() => setMostrarModal(true)}
                className="mt-4 w-full rounded-lg bg-orange-600 px-4 py-2 font-semibold text-white transition hover:bg-orange-700"
              >
                {tasaHoyRow?.tasa_oficial != null
                  ? 'Actualizar tasas'
                  : 'Ingresar tasas'}
              </button>
            </div>
          </div>
        </div>

        {/* Editar una sola tasa en una fecha */}

        <div className="mb-6 rounded-lg border border-amber-200 bg-gradient-to-br from-amber-50 to-amber-50/50 p-6 shadow-sm">
          <div className="mb-6 flex items-start justify-between">
            <div>
              <h2 className="mb-1 flex items-center gap-2 text-lg font-bold text-gray-900">
                <Pencil className="h-5 w-5 text-amber-700" />
                Editar una tasa en una fecha
              </h2>
              <p className="text-sm text-gray-700">
                Elija la fecha y <strong>solo una</strong> fuente (Euro, BCV o
                Binance). Las otras dos no se modifican. Sirve para corregir
                hoy o un día pasado (p. ej. Euro = 896,03).
              </p>
            </div>
            {tasaGuardadaExito && (
              <div className="flex items-center gap-2 rounded-lg bg-green-100 px-3 py-2 text-sm text-green-700">
                <Check className="h-4 w-4" />
                Guardado
              </div>
            )}
          </div>

          <div className="space-y-4 rounded-lg bg-white p-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700">
                    Fecha
                  </label>
                  <input
                    type="date"
                    value={fechaTasaPago}
                    onChange={e => {
                      const v = e.target.value
                      setFechaTasaPago(v)
                      void cargarFilaFecha(v)
                    }}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 shadow-sm transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                  />
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700">
                    Tasa a cambiar
                  </label>
                  <select
                    value={fuenteEdicion}
                    onChange={e =>
                      setFuenteEdicion(e.target.value as FuenteTasaEdicion)
                    }
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 shadow-sm transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                  >
                    <option value="euro">Euro</option>
                    <option value="bcv">BCV</option>
                    <option value="binance">Binance</option>
                  </select>
                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-gray-700">
                    Nuevo valor (Bs. por 1 USD)
                  </label>
                  <input
                    type="text"
                    inputMode="decimal"
                    placeholder="ej. 896.03"
                    value={tasaParaFecha}
                    onChange={e => setTasaParaFecha(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 shadow-sm transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                  />
                </div>
              </div>

              {filaFechaActual ? (
                <p className="text-xs text-gray-600">
                  En esa fecha ahora: Euro{' '}
                  {filaFechaActual.tasa_oficial?.toFixed(2) ?? '-'} · BCV{' '}
                  {filaFechaActual.tasa_bcv != null
                    ? filaFechaActual.tasa_bcv.toFixed(2)
                    : '-'}{' '}
                  · Binance{' '}
                  {filaFechaActual.tasa_binance != null
                    ? filaFechaActual.tasa_binance.toFixed(2)
                    : '-'}
                </p>
              ) : fechaTasaPago ? (
                <p className="text-xs text-amber-800">
                  No hay fila para esa fecha. Si elige Euro, se crea. BCV o
                  Binance requieren que la fecha ya exista.
                </p>
              ) : null}

              <div className="flex gap-2 border-t border-gray-200 pt-4">
                <button
                  type="button"
                  disabled={guardandoFecha || !fechaTasaPago || !tasaParaFecha}
                  onClick={() => void handleGuardarTasaPorFechaPago()}
                  className="flex-1 rounded-lg bg-amber-700 px-4 py-2.5 font-semibold text-white shadow-sm transition hover:bg-amber-800 disabled:cursor-not-allowed disabled:bg-gray-300 disabled:text-gray-500"
                >
                  {guardandoFecha
                    ? 'Guardando…'
                    : `Guardar solo ${etiquetaFuente(fuenteEdicion)}`}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setFechaTasaPago('')
                    setTasaParaFecha('')
                    setFilaFechaActual(null)
                    setFuenteEdicion('euro')
                  }}
                  disabled={guardandoFecha}
                  className="rounded-lg border border-gray-300 px-4 py-2.5 font-semibold text-gray-700 transition hover:bg-gray-50 disabled:opacity-50"
                >
                  Limpiar
                </button>
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
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700">
                      Fecha
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700">
                      Euro
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700">
                      BCV
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700">
                      Binance
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700">
                      Ingresado por
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700">
                      Acciones
                    </th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-gray-200">
                  {historial.map(item => (
                    <tr key={item.id} className="transition hover:bg-gray-50">
                      <td className="px-4 py-4 text-sm font-medium text-gray-900">
                        {new Date(item.fecha).toLocaleDateString('es-VE')}
                      </td>
                      <td className="px-4 py-4 text-sm font-semibold text-orange-600">
                        {item.tasa_oficial.toFixed(2)}
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-800">
                        {item.tasa_bcv != null ? item.tasa_bcv.toFixed(2) : '-'}
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-800">
                        {item.tasa_binance != null
                          ? item.tasa_binance.toFixed(2)
                          : '-'}
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-600">
                        {item.usuario_email || '-'}
                      </td>
                      <td className="px-4 py-4">
                        <button
                          type="button"
                          onClick={() =>
                            abrirEdicionFecha(item.fecha, 'euro')
                          }
                          className="inline-flex items-center gap-1 rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-800 hover:bg-amber-100"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                          Editar
                        </button>
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
        tasaHoyRow={tasaHoyRow}
      />
    </div>
  )
}
