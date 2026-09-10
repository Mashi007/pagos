import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Calendar, DollarSign, Loader2, Clock, RefreshCw } from 'lucide-react'
import { Card, CardContent } from '../ui/card'
import { Button } from '../ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table'
import {
  getTasaHoy,
  getTasaPorFecha,
  getEstadoTasa,
  getHistorialTasas,
  editarUnaTasa,
  guardarTasaPorFecha,
  capturarTasaBcvDesdeWidget,
  invalidateTasaLecturaClientCache,
  type TasaCambioResponse,
  type TasaCambioHistorial,
} from '../../services/tasaCambioService'
import { toast } from 'sonner'
import { getErrorMessage } from '../../types/errors'

function formatBsUsd(val: number): string {
  return new Intl.NumberFormat('es-VE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(val)
}

function fechaIso(v?: string | null): string {
  return (v || '').slice(0, 10)
}

function textoModoCarga(estado: {
  carga_un_dia_antes?: {
    fecha?: string
    modo?: string
    ventana_auto_desde?: string
    ventana_auto_hasta?: string
  }
  fecha_bcv_esperada?: string | null
} | undefined): { titulo: string; detalle: string; clase: string } {
  const carga = estado?.carga_un_dia_antes
  const fecha = fechaIso(carga?.fecha || estado?.fecha_bcv_esperada)
  const modo = carga?.modo
  if (modo === 'automatico_ok') {
    return {
      titulo: `Bot BCV listo para ${fecha}`,
      detalle:
        'El automático ya guardó el BCV. Puede corregir Euro o BCV a mano en cualquier fecha abajo.',
      clase: 'border-emerald-200 bg-emerald-50 text-emerald-950',
    }
  }
  if (modo === 'en_curso') {
    return {
      titulo: `Bot BCV ${carga?.ventana_auto_desde}–${carga?.ventana_auto_hasta} Caracas`,
      detalle: `Consultando el recuadro para ${fecha}. Puede cargar a mano si no entra.`,
      clase: 'border-sky-200 bg-sky-50 text-sky-950',
    }
  }
  if (modo === 'pendiente_ventana') {
    return {
      titulo: `Automático a las ${carga?.ventana_auto_desde} Caracas`,
      detalle: `El bot intentará ${fecha} a esa hora. Puede adelantar o corregir cualquier fecha a mano.`,
      clase: 'border-slate-200 bg-slate-50 text-slate-900',
    }
  }
  if (modo === 'requiere_manual') {
    return {
      titulo: 'Automático no cargó el BCV',
      detalle: `La ventana ${carga?.ventana_auto_desde}–${carga?.ventana_auto_hasta} ya pasó. Cargue a mano Euro y BCV (cualquier fecha).`,
      clase: 'border-amber-300 bg-amber-50 text-amber-950',
    }
  }
  if (modo === 'fin_de_semana') {
    return {
      titulo: 'Fin de semana: rige el viernes',
      detalle: `Sábado y domingo copian el viernes. Puede editar cualquier fecha hábil a mano.`,
      clase: 'border-blue-200 bg-blue-50 text-blue-950',
    }
  }
  return {
    titulo: 'Edición manual de tasas',
    detalle:
      'Elija cualquier fecha, edite Euro y/o BCV y guarde. El cambio queda en base de datos y se refleja al instante.',
    clase: 'border-slate-200 bg-slate-50 text-slate-900',
  }
}

function aplicarFilaAlFormulario(
  fila: TasaCambioResponse | null | undefined,
  setEuro: (v: string) => void,
  setBcv: (v: string) => void
) {
  setEuro(fila?.tasa_oficial != null ? String(fila.tasa_oficial) : '')
  setBcv(fila?.tasa_bcv != null ? String(fila.tasa_bcv) : '')
}

/**
 * Editor de tasas para cualquier fecha (Euro y BCV). Persiste en BD y refresca el front.
 */
export function AgregarTasaFechaPagoPanel() {
  const queryClient = useQueryClient()
  const [fechaTasaForm, setFechaTasaForm] = useState('')
  const [tasaForm, setTasaForm] = useState('')
  const [tasaBcvForm, setTasaBcvForm] = useState('')
  const [isGuardandoTasa, setIsGuardandoTasa] = useState(false)
  const [capturaBcvEnCurso, setCapturaBcvEnCurso] = useState(false)

  const { data: estadoTasa } = useQuery({
    queryKey: ['tasa-estado-banner-pagos'],
    queryFn: async () => {
      invalidateTasaLecturaClientCache()
      return getEstadoTasa()
    },
    staleTime: 15_000,
    refetchOnWindowFocus: true,
  })

  const fechaSiguiente = fechaIso(estadoTasa?.fecha_bcv_esperada)
  const fechaHoy = fechaIso(estadoTasa?.fecha_hoy)

  useEffect(() => {
    if (!fechaTasaForm && fechaHoy) {
      setFechaTasaForm(fechaHoy)
    }
  }, [fechaHoy, fechaTasaForm])

  const { data: tasaHoyBanner, isLoading: tasaHoyBannerLoading } = useQuery({
    queryKey: ['tasa-hoy-banner-pagos'],
    queryFn: async () => {
      try {
        return await getTasaHoy()
      } catch {
        return null
      }
    },
    staleTime: 15_000,
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

  const { data: filaFecha, isFetching: cargandoFecha } = useQuery({
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
    staleTime: 0,
  })

  const { data: historial = [], isFetching: cargandoHistorial } = useQuery({
    queryKey: ['tasa-historial-editor'],
    queryFn: () => getHistorialTasas(60),
    staleTime: 15_000,
  })

  useEffect(() => {
    aplicarFilaAlFormulario(filaFecha, setTasaForm, setTasaBcvForm)
  }, [fechaTasaForm, filaFecha?.id, filaFecha?.updated_at, filaFecha?.tasa_oficial, filaFecha?.tasa_bcv])

  const esFinDeSemana = Boolean(estadoTasa?.fin_de_semana_caracas)
  const fechaViernesRef = fechaIso(estadoTasa?.fecha_referencia_viernes)
  const aviso = textoModoCarga(estadoTasa)

  const aplicarFilaEnCaches = async (row: TasaCambioResponse) => {
    const f = fechaIso(row.fecha)
    queryClient.setQueryData(['tasa-por-fecha-edicion', f], row)
    if (f === fechaHoy) {
      queryClient.setQueryData(['tasa-hoy-banner-pagos'], row)
    }
    if (f === fechaSiguiente) {
      queryClient.setQueryData(['tasa-siguiente-habil', fechaSiguiente], row)
    }
    queryClient.setQueryData(
      ['tasa-historial-editor'],
      (prev: TasaCambioHistorial[] | undefined) => {
        const item: TasaCambioHistorial = {
          id: row.id,
          fecha: f,
          tasa_oficial: row.tasa_oficial,
          tasa_bcv: row.tasa_bcv,
          tasa_binance: row.tasa_binance,
          usuario_email: row.usuario_email,
          updated_at: row.updated_at,
        }
        const rest = (prev || []).filter(x => fechaIso(x.fecha) !== f)
        return [item, ...rest].sort((a, b) =>
          fechaIso(b.fecha).localeCompare(fechaIso(a.fecha))
        )
      }
    )
    aplicarFilaAlFormulario(row, setTasaForm, setTasaBcvForm)
    await queryClient.invalidateQueries({ queryKey: ['tasa-estado-banner-pagos'] })
    await queryClient.invalidateQueries({ queryKey: ['tasa-hoy-banner-pagos'] })
    await queryClient.invalidateQueries({ queryKey: ['tasa-por-fecha-edicion'] })
    await queryClient.invalidateQueries({ queryKey: ['tasa-siguiente-habil'] })
    await queryClient.invalidateQueries({ queryKey: ['tasa-historial-editor'] })
  }

  const handleCapturaBcvWidget = async () => {
    setCapturaBcvEnCurso(true)
    try {
      const res = await capturarTasaBcvDesdeWidget()
      if (res.omitido) {
        toast.info(res.mensaje || 'No se consultó el BCV.')
      } else {
        const fv = fechaIso(res.fecha_valor)
        const tasa =
          res.tasa_bcv != null ? formatBsUsd(Number(res.tasa_bcv)) : '—'
        toast.success(`BCV capturado para ${fv}: ${tasa} Bs./USD`)
        if (fv) setFechaTasaForm(fv)
      }
      invalidateTasaLecturaClientCache()
      await queryClient.invalidateQueries({ queryKey: ['tasa'] })
      await queryClient.invalidateQueries({ queryKey: ['tasa-hoy-banner-pagos'] })
      await queryClient.invalidateQueries({ queryKey: ['tasa-por-fecha-edicion'] })
      await queryClient.invalidateQueries({ queryKey: ['tasa-siguiente-habil'] })
      await queryClient.invalidateQueries({ queryKey: ['tasa-estado-banner-pagos'] })
      await queryClient.invalidateQueries({ queryKey: ['tasa-historial-editor'] })
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo capturar el BCV')
    } finally {
      setCapturaBcvEnCurso(false)
    }
  }

  const handleGuardarTasa = async () => {
    const fecha = fechaTasaForm.trim()
    if (!fecha) {
      toast.error('Seleccione la fecha a actualizar')
      return
    }
    const euroRaw = tasaForm.trim().replace(',', '.')
    const bcvRaw = tasaBcvForm.trim().replace(',', '.')
    const euroNum = euroRaw === '' ? null : parseFloat(euroRaw)
    const bcvNum = bcvRaw === '' ? null : parseFloat(bcvRaw)
    if (euroNum == null && bcvNum == null) {
      toast.error('Ingrese Euro y/o BCV (mayor a 0)')
      return
    }
    if (euroNum != null && (!Number.isFinite(euroNum) || euroNum <= 0)) {
      toast.error('Euro debe ser un número mayor a 0')
      return
    }
    if (bcvNum != null && (!Number.isFinite(bcvNum) || bcvNum <= 0)) {
      toast.error('BCV debe ser un número mayor a 0')
      return
    }

    setIsGuardandoTasa(true)
    try {
      let row: TasaCambioResponse
      if (euroNum != null && bcvNum != null) {
        row = await guardarTasaPorFecha(fecha, euroNum, { tasa_bcv: bcvNum })
      } else if (euroNum != null) {
        row = await editarUnaTasa(fecha, 'euro', euroNum)
      } else {
        row = await editarUnaTasa(fecha, 'bcv', bcvNum as number)
      }
      await aplicarFilaEnCaches(row)
      const partes = [
        euroNum != null ? `Euro ${formatBsUsd(row.tasa_oficial)}` : null,
        row.tasa_bcv != null ? `BCV ${formatBsUsd(row.tasa_bcv)}` : null,
      ].filter(Boolean)
      toast.success(`Actualizado ${fecha}: ${partes.join(' · ')} Bs./USD`)
    } catch (e) {
      toast.error(getErrorMessage(e) || 'No se pudo guardar la tasa')
    } finally {
      setIsGuardandoTasa(false)
    }
  }

  return (
    <div className="space-y-6">
      <div
        className={`flex items-start gap-3 rounded-lg border p-4 text-sm ${aviso.clase}`}
      >
        <Clock className="mt-0.5 h-4 w-4 flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{aviso.titulo}</p>
          <p className="mt-1">{aviso.detalle}</p>
        </div>
        <button
          type="button"
          onClick={() => void handleCapturaBcvWidget()}
          disabled={capturaBcvEnCurso}
          className="inline-flex shrink-0 items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-900 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {capturaBcvEnCurso ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Capturando…
            </>
          ) : (
            <>
              <RefreshCw className="h-4 w-4" />
              Capturar BCV
            </>
          )}
        </button>
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
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-200 bg-white shadow-sm">
        <CardContent className="space-y-6 py-6">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Calendar className="h-5 w-5 text-[#1e67eb]" />
              <h3 className="text-lg font-bold text-gray-900">
                Actualizar tasas de cualquier fecha
              </h3>
            </div>
            <p className="text-sm text-gray-700">
              Elija la fecha, edite Euro y/o BCV y pulse Guardar. El valor se
              escribe en la base de datos y se muestra de inmediato en esta
              pantalla y en el resto de la app.
            </p>
          </div>

          <div className="space-y-5 rounded-lg border border-slate-100 bg-slate-50/80 p-5">
            <div className="flex max-w-xl flex-wrap items-end gap-3">
              <div className="min-w-[14rem] flex-1">
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  Fecha
                </label>
                <input
                  type="date"
                  value={fechaTasaForm}
                  onChange={e => setFechaTasaForm(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-gray-900 shadow-sm transition focus:border-[#1e67eb] focus:ring-2 focus:ring-blue-100"
                />
              </div>
              <Button
                type="button"
                variant="outline"
                disabled={!fechaHoy}
                onClick={() => setFechaTasaForm(fechaHoy)}
              >
                Hoy
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={!fechaSiguiente}
                onClick={() => setFechaTasaForm(fechaSiguiente)}
              >
                Siguiente hábil
              </Button>
            </div>

            <p className="text-xs text-gray-600">
              {cargandoFecha ? (
                <span className="inline-flex items-center gap-1">
                  <Loader2 className="h-3 w-3 animate-spin" /> Cargando fila…
                </span>
              ) : filaFecha ? (
                <>
                  En BD: Euro {formatBsUsd(filaFecha.tasa_oficial)} · BCV{' '}
                  {filaFecha.tasa_bcv != null
                    ? formatBsUsd(filaFecha.tasa_bcv)
                    : '—'}
                  {filaFecha.usuario_email
                    ? ` · ${filaFecha.usuario_email}`
                    : ''}
                </>
              ) : fechaTasaForm ? (
                'No hay fila aún. Al guardar se crea (si solo BCV, se copia Euro del día previo).'
              ) : (
                'Seleccione una fecha.'
              )}
            </p>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
                  className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-gray-900 shadow-sm focus:border-[#1e67eb] focus:ring-2 focus:ring-blue-100"
                  placeholder="ej. 896.03"
                />
              </div>
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
                  className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-gray-900 shadow-sm focus:border-[#1e67eb] focus:ring-2 focus:ring-blue-100"
                  placeholder="del recuadro BCV"
                />
              </div>
            </div>

            <button
              type="button"
              onClick={() => void handleGuardarTasa()}
              disabled={isGuardandoTasa || !fechaTasaForm}
              className="inline-flex items-center gap-2 rounded-lg bg-[#1e67eb] px-6 py-2.5 font-semibold text-white shadow-sm transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-400"
            >
              {isGuardandoTasa ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Guardando…
                </>
              ) : (
                <>
                  <DollarSign className="h-4 w-4" />
                  Guardar tasas de {fechaTasaForm || 'la fecha'}
                </>
              )}
            </button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-slate-200 bg-white shadow-sm">
        <CardContent className="py-6">
          <h3 className="mb-3 text-base font-semibold text-gray-900">
            Historial (clic para editar)
          </h3>
          {cargandoHistorial && historial.length === 0 ? (
            <p className="flex items-center gap-2 text-sm text-slate-600">
              <Loader2 className="h-4 w-4 animate-spin" /> Cargando historial…
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Euro</TableHead>
                  <TableHead>BCV</TableHead>
                  <TableHead>Usuario</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {historial.map(row => {
                  const f = fechaIso(row.fecha)
                  const activa = f === fechaTasaForm
                  return (
                    <TableRow
                      key={row.id}
                      className={`cursor-pointer ${activa ? 'bg-blue-50' : ''}`}
                      onClick={() => setFechaTasaForm(f)}
                    >
                      <TableCell className="font-medium">{f}</TableCell>
                      <TableCell>{formatBsUsd(row.tasa_oficial)}</TableCell>
                      <TableCell>
                        {row.tasa_bcv != null ? formatBsUsd(row.tasa_bcv) : '—'}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {row.usuario_email || '—'}
                      </TableCell>
                    </TableRow>
                  )
                })}
                {historial.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={4}
                      className="text-center text-sm text-muted-foreground"
                    >
                      Sin historial.
                    </TableCell>
                  </TableRow>
                ) : null}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
