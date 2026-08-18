import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { DollarSign, Loader2, AlertCircle, Pencil } from 'lucide-react'
import { Card, CardContent } from '../ui/card'
import {
  getTasaHoy,
  getTasaPorFecha,
  getEstadoTasa,
  editarUnaTasa,
  type FuenteTasaEdicion,
} from '../../services/tasaCambioService'
import { toast } from 'sonner'
import { getErrorMessage } from '../../types/errors'

function hoyIsoLocal(): string {
  return new Date().toISOString().split('T')[0]
}

/**
 * Formulario de tasas por fecha de pago. Hay que elegir fecha y qué tasas editar.
 */
export function AgregarTasaFechaPagoPanel() {
  const queryClient = useQueryClient()
  const [fechaTasaForm, setFechaTasaForm] = useState(hoyIsoLocal)
  const [editarEuro, setEditarEuro] = useState(false)
  const [editarBcv, setEditarBcv] = useState(false)
  const [editarBinance, setEditarBinance] = useState(false)
  const [tasaForm, setTasaForm] = useState('')
  const [tasaBcvForm, setTasaBcvForm] = useState('')
  const [tasaBinanceForm, setTasaBinanceForm] = useState('')
  const [isGuardandoTasa, setIsGuardandoTasa] = useState(false)

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

  const { data: estadoTasa } = useQuery({
    queryKey: ['tasa-estado-banner-pagos'],
    queryFn: getEstadoTasa,
    staleTime: 60_000,
    refetchOnWindowFocus: true,
  })

  const { data: filaFecha } = useQuery({
    queryKey: ['tasa-por-fecha-edicion', fechaTasaForm],
    queryFn: async () => {
      if (!fechaTasaForm.trim()) return null
      try {
        return await getTasaPorFecha(fechaTasaForm.trim())
      } catch {
        return null
      }
    },
    enabled: Boolean(fechaTasaForm.trim()),
    staleTime: 15_000,
  })

  const esFinDeSemana = Boolean(estadoTasa?.fin_de_semana_caracas)
  const fechaViernesRef = (estadoTasa?.fecha_referencia_viernes || '').slice(
    0,
    10
  )

  const marcarFuente = (fuente: FuenteTasaEdicion, on: boolean) => {
    if (fuente === 'euro') {
      setEditarEuro(on)
      if (!on) setTasaForm('')
      else if (filaFecha?.tasa_oficial != null) {
        setTasaForm(String(filaFecha.tasa_oficial))
      }
    } else if (fuente === 'bcv') {
      setEditarBcv(on)
      if (!on) setTasaBcvForm('')
      else if (filaFecha?.tasa_bcv != null) {
        setTasaBcvForm(String(filaFecha.tasa_bcv))
      }
    } else {
      setEditarBinance(on)
      if (!on) setTasaBinanceForm('')
      else if (filaFecha?.tasa_binance != null) {
        setTasaBinanceForm(String(filaFecha.tasa_binance))
      }
    }
  }

  const handleGuardarTasa = async () => {
    if (!fechaTasaForm.trim()) {
      toast.error('Seleccione una fecha')
      return
    }
    if (!editarEuro && !editarBcv && !editarBinance) {
      toast.error('Marque al menos una tasa a editar: Euro, BCV o Binance')
      return
    }

    const cambios: Array<{ fuente: FuenteTasaEdicion; valor: number }> = []
    if (editarEuro) {
      const euroNum = parseFloat(tasaForm.replace(',', '.'))
      if (isNaN(euroNum) || euroNum <= 0) {
        toast.error('Ingrese el valor de Euro (mayor a 0)')
        return
      }
      cambios.push({ fuente: 'euro', valor: euroNum })
    }
    if (editarBcv) {
      const bcvNum = parseFloat(tasaBcvForm.replace(',', '.'))
      if (isNaN(bcvNum) || bcvNum <= 0) {
        toast.error('Ingrese el valor de BCV (mayor a 0)')
        return
      }
      cambios.push({ fuente: 'bcv', valor: bcvNum })
    }
    if (editarBinance) {
      const binNum = parseFloat(tasaBinanceForm.replace(',', '.'))
      if (isNaN(binNum) || binNum <= 0) {
        toast.error('Ingrese el valor de Binance (mayor a 0)')
        return
      }
      cambios.push({ fuente: 'binance', valor: binNum })
    }

    setIsGuardandoTasa(true)
    try {
      for (const c of cambios) {
        await editarUnaTasa(fechaTasaForm, c.fuente, c.valor)
      }
      const nombres = cambios
        .map(c =>
          c.fuente === 'euro' ? 'Euro' : c.fuente === 'bcv' ? 'BCV' : 'Binance'
        )
        .join(', ')
      toast.success(`${nombres} actualizada(s) para ${fechaTasaForm}`)
      await queryClient.invalidateQueries({
        queryKey: ['tasa-hoy-banner-pagos'],
      })
      await queryClient.invalidateQueries({
        queryKey: ['tasa-por-fecha-edicion'],
      })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo guardar la tasa')
    } finally {
      setIsGuardandoTasa(false)
    }
  }

  return (
    <Card className="border-amber-200 bg-gradient-to-br from-amber-50 to-amber-50/50 shadow-sm">
      <CardContent className="space-y-6 py-6">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Pencil className="h-5 w-5 text-amber-700" />
            <h3 className="text-lg font-bold text-gray-900">
              Editar tasas de una fecha
            </h3>
          </div>
          <p className="text-sm text-gray-700">
            1) Elija la <strong>fecha</strong>. 2) Marque <strong>qué tasas</strong>{' '}
            editar (Euro, BCV y/o Binance). 3) Escriba el valor y pulse Guardar.
            Las que no marque no se tocan.
          </p>
        </div>

        {esFinDeSemana ? (
          <div className="flex items-start gap-2 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950">
            <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <span>
              <strong>Fin de semana (Caracas):</strong> no es necesario
              registrar tasas de hoy. El sistema copia las del viernes
              {fechaViernesRef ? ` (${fechaViernesRef})` : ''} para sábado y
              domingo.
            </span>
          </div>
        ) : null}

        {tasaHoyBannerLoading ? (
          <div className="flex items-center gap-2 rounded-lg bg-white/80 p-4 text-sm text-amber-800">
            <Loader2 className="h-4 w-4 animate-spin text-amber-600" />
            Consultando tasa del día...
          </div>
        ) : tasaHoyBanner ? (
          <div className="flex flex-wrap items-center gap-3 rounded-lg bg-white/80 p-4">
            <DollarSign className="h-6 w-6 text-amber-700" />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-gray-600">
                {esFinDeSemana
                  ? 'Tasa vigente hoy (desde viernes)'
                  : 'Tasa vigente hoy'}
              </p>
              <p className="text-base font-semibold text-amber-900">
                {(tasaHoyBanner.fecha || '').slice(0, 10)} — Euro:{' '}
                {new Intl.NumberFormat('es-VE', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                }).format(tasaHoyBanner.tasa_oficial)}{' '}
                · BCV:{' '}
                {tasaHoyBanner.tasa_bcv != null
                  ? new Intl.NumberFormat('es-VE', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    }).format(tasaHoyBanner.tasa_bcv)
                  : '-'}{' '}
                · Binance:{' '}
                {tasaHoyBanner.tasa_binance != null
                  ? new Intl.NumberFormat('es-VE', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    }).format(tasaHoyBanner.tasa_binance)
                  : '-'}
              </p>
            </div>
          </div>
        ) : esFinDeSemana ? (
          <div className="flex items-start gap-2 rounded-lg bg-amber-100/60 p-4 text-sm text-amber-900">
            <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <span>
              No hay tasas completas del viernes
              {fechaViernesRef ? ` (${fechaViernesRef})` : ''} para copiar a
              hoy.
            </span>
          </div>
        ) : (
          <div className="flex items-start gap-2 rounded-lg bg-amber-100/60 p-4 text-sm text-amber-900">
            <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <span>No hay tasa cargada para hoy. Use el formulario.</span>
          </div>
        )}

        <div className="space-y-5 rounded-lg bg-white p-5 shadow-sm">
          <div className="max-w-xs">
            <label className="mb-2 block text-sm font-medium text-gray-700">
              1. Fecha
            </label>
            <input
              type="date"
              value={fechaTasaForm}
              onChange={e => {
                setFechaTasaForm(e.target.value)
                setTasaForm('')
                setTasaBcvForm('')
                setTasaBinanceForm('')
              }}
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 shadow-sm transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
            />
          </div>

          {filaFecha ? (
            <p className="text-xs text-gray-600">
              Valores actuales de esa fecha: Euro{' '}
              {filaFecha.tasa_oficial?.toFixed(2) ?? '-'} · BCV{' '}
              {filaFecha.tasa_bcv != null ? filaFecha.tasa_bcv.toFixed(2) : '-'}{' '}
              · Binance{' '}
              {filaFecha.tasa_binance != null
                ? filaFecha.tasa_binance.toFixed(2)
                : '-'}
            </p>
          ) : fechaTasaForm ? (
            <p className="text-xs text-amber-800">
              No hay fila para esa fecha. Si marca Euro, se crea.
            </p>
          ) : null}

          <div>
            <p className="mb-3 text-sm font-medium text-gray-700">
              2. Tasas a editar
            </p>
            <div className="flex flex-wrap gap-4">
              <label className="inline-flex items-center gap-2 text-sm font-medium text-gray-800">
                <input
                  type="checkbox"
                  checked={editarEuro}
                  onChange={e => marcarFuente('euro', e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-amber-700"
                />
                Euro
              </label>
              <label className="inline-flex items-center gap-2 text-sm font-medium text-gray-800">
                <input
                  type="checkbox"
                  checked={editarBcv}
                  onChange={e => marcarFuente('bcv', e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-amber-700"
                />
                BCV
              </label>
              <label className="inline-flex items-center gap-2 text-sm font-medium text-gray-800">
                <input
                  type="checkbox"
                  checked={editarBinance}
                  onChange={e => marcarFuente('binance', e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-amber-700"
                />
                Binance
              </label>
            </div>
          </div>

          {(editarEuro || editarBcv || editarBinance) && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {editarEuro ? (
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-gray-700">
                    Nuevo Euro (Bs. por 1 USD)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={tasaForm}
                    onChange={e => setTasaForm(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 shadow-sm focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                    placeholder="ej. 896.03"
                  />
                </div>
              ) : null}
              {editarBcv ? (
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-gray-700">
                    Nuevo BCV (Bs. por 1 USD)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={tasaBcvForm}
                    onChange={e => setTasaBcvForm(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 shadow-sm focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                  />
                </div>
              ) : null}
              {editarBinance ? (
                <div className="flex flex-col gap-2">
                  <label className="text-sm font-medium text-gray-700">
                    Nuevo Binance (Bs. por 1 USD)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={tasaBinanceForm}
                    onChange={e => setTasaBinanceForm(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 shadow-sm focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                  />
                </div>
              ) : null}
            </div>
          )}

          <button
            type="button"
            onClick={() => void handleGuardarTasa()}
            disabled={isGuardandoTasa}
            className="rounded-lg bg-amber-700 px-6 py-2.5 font-semibold text-white shadow-sm transition hover:bg-amber-800 disabled:cursor-not-allowed disabled:bg-gray-400"
          >
            {isGuardandoTasa ? 'Guardando…' : 'Guardar tasas marcadas'}
          </button>
        </div>
      </CardContent>
    </Card>
  )
}
