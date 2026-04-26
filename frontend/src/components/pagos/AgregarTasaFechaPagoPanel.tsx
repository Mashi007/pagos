import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, DollarSign, Loader2, AlertCircle } from 'lucide-react'
import { Card, CardContent } from '../ui/card'
import {
  getTasaHoy,
  getTasaPorFecha,
  guardarTasaPorFecha,
} from '../../services/tasaCambioService'
import { toast } from 'sonner'
import { getErrorMessage } from '../../types/errors'

/**
 * Formulario «Agregar Tasa para Fecha de Pago» (Bs./USD por fecha de comprobante).
 * Antes en PagosList; también en la página **Tasa de cambio** (solo administrador).
 */
export function AgregarTasaFechaPagoPanel() {
  const queryClient = useQueryClient()
  const [fechaTasaForm, setFechaTasaForm] = useState('')
  const [tasaForm, setTasaForm] = useState('')
  const [tasaBcvForm, setTasaBcvForm] = useState('')
  const [tasaBinanceForm, setTasaBinanceForm] = useState('')
  const [isGuardandoTasa, setIsGuardandoTasa] = useState(false)
  const [tasaExistenteDialogo, setTasaExistenteDialogo] = useState<{
    fecha: string
    tasaActual: number
    tasaNueva: number
  } | null>(null)

  const { data: tasaHoyBanner, isLoading: tasaHoyBannerLoading } = useQuery({
    queryKey: ['tasa-hoy-banner-pagos'],
    queryFn: async () => {
      try {
        return await getTasaHoy()
      } catch {
        return null
      }
    },
    staleTime: 60_000,
    refetchOnWindowFocus: true,
  })

  const handleGuardarTasa = async () => {
    if (!fechaTasaForm.trim()) {
      toast.error('Seleccione una fecha')
      return
    }
    const tasaNum = parseFloat(tasaForm)
    if (isNaN(tasaNum) || tasaNum <= 0) {
      toast.error('Ingrese una tasa Euro válida mayor a 0')
      return
    }
    const bcvOpt = tasaBcvForm.trim() ? parseFloat(tasaBcvForm) : NaN
    const binOpt = tasaBinanceForm.trim() ? parseFloat(tasaBinanceForm) : NaN
    if (tasaBcvForm.trim() && (isNaN(bcvOpt) || bcvOpt <= 0)) {
      toast.error('Tasa BCV inválida (deje vacío si no aplica)')
      return
    }
    if (tasaBinanceForm.trim() && (isNaN(binOpt) || binOpt <= 0)) {
      toast.error('Tasa Binance inválida (deje vacío si no aplica)')
      return
    }
    const opts: { tasa_bcv?: number; tasa_binance?: number } = {}
    if (tasaBcvForm.trim() && !isNaN(bcvOpt) && bcvOpt > 0)
      opts.tasa_bcv = bcvOpt
    if (tasaBinanceForm.trim() && !isNaN(binOpt) && binOpt > 0)
      opts.tasa_binance = binOpt

    setIsGuardandoTasa(true)
    try {
      const tasaExistente = await getTasaPorFecha(fechaTasaForm)

      if (tasaExistente && tasaExistente.tasa_oficial !== tasaNum) {
        setTasaExistenteDialogo({
          fecha: fechaTasaForm,
          tasaActual: tasaExistente.tasa_oficial,
          tasaNueva: tasaNum,
        })
        setIsGuardandoTasa(false)
        return
      }

      await guardarTasaPorFecha(
        fechaTasaForm,
        tasaNum,
        Object.keys(opts).length ? opts : undefined
      )

      const accion = tasaExistente ? 'Tasa actualizada' : 'Tasa guardada'
      toast.success(`${accion} para ${fechaTasaForm}`)
      setFechaTasaForm('')
      setTasaForm('')
      setTasaBcvForm('')
      setTasaBinanceForm('')

      await queryClient.invalidateQueries({
        queryKey: ['tasa-hoy-banner-pagos'],
      })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo guardar la tasa')
    } finally {
      setIsGuardandoTasa(false)
    }
  }

  const handleConfirmarEditarTasa = async () => {
    if (!tasaExistenteDialogo) return

    setIsGuardandoTasa(true)
    try {
      const bcvOpt = tasaBcvForm.trim() ? parseFloat(tasaBcvForm) : NaN
      const binOpt = tasaBinanceForm.trim() ? parseFloat(tasaBinanceForm) : NaN
      const opts: { tasa_bcv?: number; tasa_binance?: number } = {}
      if (tasaBcvForm.trim() && !isNaN(bcvOpt) && bcvOpt > 0)
        opts.tasa_bcv = bcvOpt
      if (tasaBinanceForm.trim() && !isNaN(binOpt) && binOpt > 0)
        opts.tasa_binance = binOpt
      await guardarTasaPorFecha(
        tasaExistenteDialogo.fecha,
        tasaExistenteDialogo.tasaNueva,
        Object.keys(opts).length ? opts : undefined
      )

      toast.success(
        `Tasa actualizada de ${tasaExistenteDialogo.tasaActual.toFixed(2)} a ${tasaExistenteDialogo.tasaNueva.toFixed(2)}`
      )
      setFechaTasaForm('')
      setTasaForm('')
      setTasaBcvForm('')
      setTasaBinanceForm('')
      setTasaExistenteDialogo(null)

      await queryClient.invalidateQueries({
        queryKey: ['tasa-hoy-banner-pagos'],
      })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo actualizar la tasa')
    } finally {
      setIsGuardandoTasa(false)
    }
  }

  return (
    <>
      <Card className="border-amber-200 bg-gradient-to-br from-amber-50 to-amber-50/50 shadow-sm">
        <CardContent className="space-y-6 py-6">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Plus className="h-5 w-5 text-amber-700" />
              <h3 className="text-lg font-bold text-gray-900">
                Agregar Tasa para Fecha de Pago
              </h3>
            </div>
            <p className="text-sm text-gray-700">
              Use la <strong>fecha de pago</strong> del reporte.{' '}
              <strong>Euro</strong> es la tasa por defecto del sistema;
              opcionalmente cargue <strong>BCV</strong> y{' '}
              <strong>Binance</strong> para que el cliente elija la fuente al
              reportar en bolívares.
            </p>
          </div>

          {tasaHoyBannerLoading ? (
            <div className="flex items-center gap-2 rounded-lg bg-white/80 p-4 text-sm text-amber-800">
              <Loader2 className="h-4 w-4 animate-spin text-amber-600" />
              Consultando tasa del día...
            </div>
          ) : tasaHoyBanner ? (
            <div className="flex items-center gap-3 rounded-lg bg-white/80 p-4">
              <DollarSign className="h-6 w-6 text-amber-700" />
              <div className="min-w-0">
                <p className="text-xs font-medium text-gray-600">
                  Tasa Vigente Hoy
                </p>
                <p className="text-base font-semibold text-amber-900">
                  {(tasaHoyBanner.fecha || '').slice(0, 10)} - Euro: Bs.{' '}
                  {new Intl.NumberFormat('es-VE', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  }).format(tasaHoyBanner.tasa_oficial)}{' '}
                  por 1 USD
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-2 rounded-lg bg-amber-100/60 p-4 text-sm text-amber-900">
              <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>
                No hay tasa cargada para hoy. Regístrela con el formulario
                inferior.
              </span>
            </div>
          )}

          <div className="rounded-lg bg-white p-5 shadow-sm">
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  Fecha de Pago
                </label>
                <input
                  type="date"
                  value={fechaTasaForm}
                  onChange={e => setFechaTasaForm(e.target.value)}
                  max={new Date().toISOString().split('T')[0]}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 shadow-sm transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                  placeholder="Seleccione una fecha"
                />
                <p className="text-xs text-gray-500">Máximo: hoy</p>
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  Tasa Euro (Bs. por 1 USD)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="999999.99"
                  value={tasaForm}
                  onChange={e => setTasaForm(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 shadow-sm transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                  placeholder="ej. 3105.75"
                />
                <p className="text-xs text-gray-500">
                  Obligatoria; referencia por defecto
                </p>
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  Tasa BCV (opcional)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={tasaBcvForm}
                  onChange={e => setTasaBcvForm(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 shadow-sm transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                  placeholder="Vacío = no actualizar"
                />
              </div>

              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium text-gray-700">
                  Tasa Binance (opcional)
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={tasaBinanceForm}
                  onChange={e => setTasaBinanceForm(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 shadow-sm transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                  placeholder="Vacío = no actualizar"
                />
              </div>

              <div className="flex flex-col justify-end gap-2 xl:col-span-1">
                <button
                  type="button"
                  onClick={() => void handleGuardarTasa()}
                  disabled={isGuardandoTasa}
                  className="rounded-lg bg-amber-700 px-6 py-2.5 font-semibold text-white shadow-sm transition hover:bg-amber-800 focus:ring-2 focus:ring-amber-400 disabled:cursor-not-allowed disabled:bg-gray-400"
                >
                  {isGuardandoTasa ? 'Guardando...' : 'Guardar Tasa'}
                </button>
                <p className="text-center text-xs text-gray-500">
                  Se agregará al historial
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {tasaExistenteDialogo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-2xl">
            <h3 className="mb-2 text-lg font-bold text-gray-900">
              Tasa ya existe para esta fecha
            </h3>
            <p className="mb-6 text-sm text-gray-600">
              Ya hay una tasa registrada para {tasaExistenteDialogo.fecha}.
              ¿Deseas actualizarla?
            </p>

            <div className="mb-6 space-y-3 rounded-lg bg-amber-50 p-4">
              <div className="flex justify-between">
                <span className="text-sm text-gray-700">Tasa actual:</span>
                <span className="font-semibold text-amber-700">
                  {tasaExistenteDialogo.tasaActual.toFixed(2)} Bs/USD
                </span>
              </div>
              <div className="flex justify-between border-t border-amber-200 pt-3">
                <span className="text-sm text-gray-700">Tasa nueva:</span>
                <span className="font-semibold text-green-700">
                  {tasaExistenteDialogo.tasaNueva.toFixed(2)} Bs/USD
                </span>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setTasaExistenteDialogo(null)}
                disabled={isGuardandoTasa}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 font-semibold text-gray-700 transition hover:bg-gray-50 disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => void handleConfirmarEditarTasa()}
                disabled={isGuardandoTasa}
                className="flex-1 rounded-lg bg-green-600 px-4 py-2.5 font-semibold text-white transition hover:bg-green-700 disabled:bg-gray-400"
              >
                {isGuardandoTasa ? 'Actualizando...' : 'Actualizar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
