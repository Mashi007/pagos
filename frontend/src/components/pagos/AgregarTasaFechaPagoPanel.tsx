import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { DollarSign, Loader2, Pencil, Clock } from 'lucide-react'
import { Card, CardContent } from '../ui/card'
import {
  getTasaHoy,
  getTasaPorFecha,
  getEstadoTasa,
  editarUnaTasa,
  invalidateTasaLecturaClientCache,
  type FuenteTasaEdicion,
  type TasaCambioEstado,
} from '../../services/tasaCambioService'
import { toast } from 'sonner'
import { getErrorMessage } from '../../types/errors'

function formatBsUsd(val: number): string {
  return new Intl.NumberFormat('es-VE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(val)
}

function textoModoCarga(estado: TasaCambioEstado | undefined): {
  titulo: string
  detalle: string
  clase: string
} {
  const carga = estado?.carga_un_dia_antes
  const fecha = (carga?.fecha || estado?.fecha_bcv_esperada || '').slice(0, 10)
  const modo = carga?.modo
  if (modo === 'automatico_ok') {
    return {
      titulo: `Automático listo para ${fecha}`,
      detalle:
        'El bot ya guardó el BCV del siguiente hábil (un día antes). Puede corregir Euro o BCV a mano si hace falta.',
      clase: 'border-emerald-200 bg-emerald-50 text-emerald-950',
    }
  }
  if (modo === 'en_curso') {
    return {
      titulo: `Bot BCV en ventana ${carga?.ventana_auto_desde}–${carga?.ventana_auto_hasta} Caracas`,
      detalle: `Consultando el recuadro para la fecha valor ${fecha}. Si no entra, use la carga manual abajo.`,
      clase: 'border-sky-200 bg-sky-50 text-sky-950',
    }
  }
  if (modo === 'pendiente_ventana') {
    return {
      titulo: `Automático a las ${carga?.ventana_auto_desde}–${carga?.ventana_auto_hasta} Caracas`,
      detalle: `Hoy se carga la tasa de ${fecha}. Puede adelantarla a mano cuando el BCV publique el recuadro.`,
      clase: 'border-slate-200 bg-slate-50 text-slate-900',
    }
  }
  if (modo === 'requiere_manual') {
    return {
      titulo: 'Automático no cargó el BCV',
      detalle: `La ventana de ${carga?.ventana_auto_desde}–${carga?.ventana_auto_hasta} ya pasó. Cargue a mano Euro y BCV para ${fecha}.`,
      clase: 'border-amber-300 bg-amber-50 text-amber-950',
    }
  }
  if (modo === 'fin_de_semana') {
    return {
      titulo: 'Fin de semana: rige el viernes',
      detalle: `Sábado y domingo copian el viernes. La próxima fecha valor es ${fecha} (se carga el viernes por la tarde, o a mano).`,
      clase: 'border-blue-200 bg-blue-50 text-blue-950',
    }
  }
  return {
    titulo: 'Carga un día hábil antes',
    detalle:
      'Euro y BCV se registran para el siguiente día hábil (fecha valor). El bot intenta el BCV por la tarde; si falla, use el formulario.',
    clase: 'border-amber-200 bg-amber-50 text-amber-950',
  }
}

/**
 * Carga de tasas un día hábil antes (manual o automática). Fecha valor = siguiente hábil.
 */
export function AgregarTasaFechaPagoPanel() {
  const queryClient = useQueryClient()
  const [fechaTasaForm, setFechaTasaForm] = useState('')
  const [editarEuro, setEditarEuro] = useState(true)
  const [editarBcv, setEditarBcv] = useState(true)
  const [tasaForm, setTasaForm] = useState('')
  const [tasaBcvForm, setTasaBcvForm] = useState('')
  const [isGuardandoTasa, setIsGuardandoTasa] = useState(false)
  const fechaDefaultAplicada = useRef(false)

  const { data: estadoTasa } = useQuery({
    queryKey: ['tasa-estado-banner-pagos'],
    queryFn: async () => {
      invalidateTasaLecturaClientCache()
      return getEstadoTasa()
    },
    staleTime: 30_000,
    refetchOnWindowFocus: true,
  })

  const fechaSiguiente = (estadoTasa?.fecha_bcv_esperada || '').slice(0, 10)
  const fechaHoy = (estadoTasa?.fecha_hoy || '').slice(0, 10)

  useEffect(() => {
    if (!fechaSiguiente || fechaDefaultAplicada.current) return
    fechaDefaultAplicada.current = true
    setFechaTasaForm(fechaSiguiente)
  }, [fechaSiguiente])

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

  const { data: filaSiguiente } = useQuery({
    queryKey: ['tasa-siguiente-habil', fechaSiguiente],
    queryFn: async () => {
      if (!fechaSiguiente) return null
      try {
        return await getTasaPorFecha(fechaSiguiente)
      } catch {
        return null
      }
    },
    enabled: Boolean(fechaSiguiente),
    staleTime: 15_000,
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

  useEffect(() => {
    if (!filaFecha) return
    if (editarEuro && filaFecha.tasa_oficial != null && !tasaForm) {
      setTasaForm(String(filaFecha.tasa_oficial))
    }
    if (editarBcv && filaFecha.tasa_bcv != null && !tasaBcvForm) {
      setTasaBcvForm(String(filaFecha.tasa_bcv))
    }
    // Solo rellenar vacíos al cambiar de fecha/fila.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filaFecha?.id, filaFecha?.fecha])

  const esFinDeSemana = Boolean(estadoTasa?.fin_de_semana_caracas)
  const fechaViernesRef = (estadoTasa?.fecha_referencia_viernes || '').slice(
    0,
    10
  )
  const aviso = textoModoCarga(estadoTasa)
  const esFechaSiguiente =
    Boolean(fechaTasaForm) && fechaTasaForm === fechaSiguiente

  const marcarFuente = (fuente: FuenteTasaEdicion, on: boolean) => {
    if (fuente === 'euro') {
      setEditarEuro(on)
      if (!on) setTasaForm('')
      else if (filaFecha?.tasa_oficial != null) {
        setTasaForm(String(filaFecha.tasa_oficial))
      }
    } else {
      setEditarBcv(on)
      if (!on) setTasaBcvForm('')
      else if (filaFecha?.tasa_bcv != null) {
        setTasaBcvForm(String(filaFecha.tasa_bcv))
      }
    }
  }

  const usarSiguienteHabil = () => {
    if (!fechaSiguiente) return
    setFechaTasaForm(fechaSiguiente)
    setTasaForm('')
    setTasaBcvForm('')
  }

  const handleGuardarTasa = async () => {
    if (!fechaTasaForm.trim()) {
      toast.error('Seleccione la fecha valor (siguiente hábil)')
      return
    }
    if (!editarEuro && !editarBcv) {
      toast.error('Marque al menos una tasa: Euro o BCV')
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

    setIsGuardandoTasa(true)
    try {
      for (const c of cambios) {
        await editarUnaTasa(fechaTasaForm, c.fuente, c.valor)
      }
      const nombres = cambios
        .map(c => (c.fuente === 'euro' ? 'Euro' : 'BCV'))
        .join(', ')
      toast.success(
        `${nombres} guardada(s) para ${fechaTasaForm} (un día hábil antes / fecha valor)`
      )
      await queryClient.invalidateQueries({
        queryKey: ['tasa-hoy-banner-pagos'],
      })
      await queryClient.invalidateQueries({
        queryKey: ['tasa-por-fecha-edicion'],
      })
      await queryClient.invalidateQueries({
        queryKey: ['tasa-siguiente-habil'],
      })
      await queryClient.invalidateQueries({
        queryKey: ['tasa-estado-banner-pagos'],
      })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo guardar la tasa')
    } finally {
      setIsGuardandoTasa(false)
    }
  }

  return (
    <div className="space-y-6">
      <div
        className={`flex items-start gap-2 rounded-lg border p-4 text-sm ${aviso.clase}`}
      >
        <Clock className="mt-0.5 h-4 w-4 flex-shrink-0" />
        <div>
          <p className="font-semibold">{aviso.titulo}</p>
          <p className="mt-1">{aviso.detalle}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardContent className="space-y-2 py-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Vigente hoy {fechaHoy ? `(${fechaHoy})` : ''}
            </p>
            {tasaHoyBannerLoading ? (
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <Loader2 className="h-4 w-4 animate-spin" />
                Consultando…
              </div>
            ) : tasaHoyBanner ? (
              <p className="text-base font-semibold text-slate-900">
                Euro {formatBsUsd(tasaHoyBanner.tasa_oficial)}
                {' · '}
                BCV{' '}
                {tasaHoyBanner.tasa_bcv != null
                  ? formatBsUsd(tasaHoyBanner.tasa_bcv)
                  : '—'}
              </p>
            ) : esFinDeSemana ? (
              <p className="text-sm text-slate-700">
                Copia del viernes
                {fechaViernesRef ? ` ${fechaViernesRef}` : ''}.
              </p>
            ) : (
              <p className="text-sm text-slate-700">Sin fila para hoy.</p>
            )}
            <p className="text-xs text-slate-500">
              Se usa en reportes Bs. con fecha de pago de hoy.
            </p>
          </CardContent>
        </Card>

        <Card className="border-amber-200 bg-amber-50/80 shadow-sm">
          <CardContent className="space-y-2 py-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
              Siguiente hábil {fechaSiguiente ? `(${fechaSiguiente})` : ''}
            </p>
            <p className="text-base font-semibold text-amber-950">
              Euro{' '}
              {filaSiguiente?.tasa_oficial != null
                ? formatBsUsd(filaSiguiente.tasa_oficial)
                : '—'}
              {' · '}
              BCV{' '}
              {filaSiguiente?.tasa_bcv != null
                ? formatBsUsd(filaSiguiente.tasa_bcv)
                : 'pendiente'}
            </p>
            <p className="text-xs text-amber-800">
              Carga de un día antes: bot BCV (tarde) o formulario manual.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-amber-200 bg-gradient-to-br from-amber-50 to-amber-50/50 shadow-sm">
        <CardContent className="space-y-6 py-6">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Pencil className="h-5 w-5 text-amber-700" />
              <h3 className="text-lg font-bold text-gray-900">
                Carga manual (fecha valor)
              </h3>
            </div>
            <p className="text-sm text-gray-700">
              Por defecto apunta al <strong>siguiente día hábil</strong>. Si solo
              marca BCV y no hay fila, el sistema copia el Euro del día previo
              (igual que el bot).
            </p>
          </div>

          <div className="space-y-5 rounded-lg bg-white p-5 shadow-sm">
            <div className="flex max-w-md flex-wrap items-end gap-3">
              <div className="min-w-[12rem] flex-1">
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Fecha valor
                </label>
                <input
                  type="date"
                  value={fechaTasaForm}
                  onChange={e => {
                    setFechaTasaForm(e.target.value)
                    setTasaForm('')
                    setTasaBcvForm('')
                  }}
                  className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 shadow-sm transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                />
              </div>
              <button
                type="button"
                onClick={usarSiguienteHabil}
                disabled={!fechaSiguiente || esFechaSiguiente}
                className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2.5 text-sm font-semibold text-amber-900 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Usar siguiente hábil
              </button>
            </div>

            {esFechaSiguiente ? (
              <p className="text-xs font-medium text-amber-800">
                Esta es la fecha de carga de un día antes (la que usa el bot
                BCV).
              </p>
            ) : null}

            {filaFecha ? (
              <p className="text-xs text-gray-600">
                Ya hay fila: Euro {filaFecha.tasa_oficial?.toFixed(2) ?? '-'} ·
                BCV{' '}
                {filaFecha.tasa_bcv != null
                  ? filaFecha.tasa_bcv.toFixed(2)
                  : '-'}
              </p>
            ) : fechaTasaForm ? (
              <p className="text-xs text-amber-800">
                No hay fila aún. Euro crea la fecha; BCV solo también (copia
                Euro del día anterior).
              </p>
            ) : (
              <p className="text-xs text-gray-500">
                Esperando fecha valor del calendario Caracas…
              </p>
            )}

            <div>
              <p className="mb-3 text-sm font-medium text-gray-700">
                Tasas a cargar
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
              </div>
            </div>

            {(editarEuro || editarBcv) && (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {editarEuro ? (
                  <div className="flex flex-col gap-2">
                    <label className="text-sm font-medium text-gray-700">
                      Euro (Bs. por 1 USD)
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
                      BCV (Bs. por 1 USD)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={tasaBcvForm}
                      onChange={e => setTasaBcvForm(e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-gray-900 shadow-sm focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                      placeholder="del recuadro BCV"
                    />
                  </div>
                ) : null}
              </div>
            )}

            <button
              type="button"
              onClick={() => void handleGuardarTasa()}
              disabled={isGuardandoTasa || !fechaTasaForm}
              className="inline-flex items-center gap-2 rounded-lg bg-amber-700 px-6 py-2.5 font-semibold text-white shadow-sm transition hover:bg-amber-800 disabled:cursor-not-allowed disabled:bg-gray-400"
            >
              {isGuardandoTasa ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Guardando…
                </>
              ) : (
                <>
                  <DollarSign className="h-4 w-4" />
                  Guardar para {fechaTasaForm || 'la fecha valor'}
                </>
              )}
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
