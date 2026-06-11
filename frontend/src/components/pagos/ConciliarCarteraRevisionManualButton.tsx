import { useCallback, useState } from 'react'



import { AlertTriangle, Loader2, Scale } from 'lucide-react'

import { toast } from 'sonner'



import { Button } from '../ui/button'

import { Input } from '../ui/input'

import {

  Dialog,

  DialogContent,

  DialogFooter,

  DialogHeader,

  DialogTitle,

} from '../ui/dialog'

import {

  revisionManualService,

  type CompararAbonosNotificacionesReferencia,

  type ConciliarCarteraRevisionResponse,

} from '../../services/revisionManualService'

import { getErrorMessage } from '../../types/errors'

import {

  abonosSuperanUmbralConfirmo,

  umbralConfirmaAbonosUsd,

} from '../../pages/notificaciones/notificacionesPageCells'

import type { ConciliarCarteraFaseTabla } from './ConciliarCarteraPagosProgreso'



type Props = {

  prestamoId: number

  cedula: string

  disabled?: boolean

  onEjecutarInicio?: () => void

  onProgresoTabla?: (fase: ConciliarCarteraFaseTabla) => void

  onEjecutarError?: () => void

  onExito?: (res: ConciliarCarteraRevisionResponse) => void | Promise<void>

}



type PasoDialogo = 'preview' | 'confirmar' | 'resultado'



export function ConciliarCarteraRevisionManualButton({

  prestamoId,

  cedula,

  disabled,

  onEjecutarInicio,

  onProgresoTabla,

  onEjecutarError,

  onExito,

}: Props) {

  const [open, setOpen] = useState(false)

  const [paso, setPaso] = useState<PasoDialogo>('preview')

  const [loadingPreview, setLoadingPreview] = useState(false)

  const [ejecutando, setEjecutando] = useState(false)

  const [preview, setPreview] =

    useState<CompararAbonosNotificacionesReferencia | null>(null)

  const [resultado, setResultado] = useState<ConciliarCarteraRevisionResponse | null>(

    null

  )

  const [loteSeleccionado, setLoteSeleccionado] = useState('')

  const [confirmacionMontos, setConfirmacionMontos] = useState('')

  const [confirmacionPrestamoId, setConfirmacionPrestamoId] = useState('')

  const [aceptaDestructivo, setAceptaDestructivo] = useState(false)



  const ced = cedula.trim()

  const pid = Number(prestamoId)



  const cerrar = useCallback(() => {

    setOpen(false)

    setPaso('preview')

    setPreview(null)

    setResultado(null)

    setLoteSeleccionado('')

    setConfirmacionMontos('')

    setConfirmacionPrestamoId('')

    setAceptaDestructivo(false)

  }, [])



  const cargarPreview = useCallback(

    async (lote?: string) => {

      if (!ced || !Number.isFinite(pid) || pid <= 0) return

      setLoadingPreview(true)

      setPreview(null)

      try {

        const res = await revisionManualService.getReferenciaAbonosNotificaciones(

          pid,

          lote?.trim() || undefined

        )

        setPreview(res)

        if (res.sin_cache) {

          toast.error(

            (res.advertencias && res.advertencias[0]) ||

              'Sin caché ABONOS. Use «Recalcular» en Notificaciones → General.'

          )

        }

        if (res.lote_aplicado) {

          setLoteSeleccionado(String(res.lote_aplicado))

        }

      } catch (e) {

        toast.error(

          getErrorMessage(e) ||

            'No se pudo leer ABONOS (Notificaciones → General).'

        )

        cerrar()

      } finally {

        setLoadingPreview(false)

      }

    },

    [ced, pid, cerrar]

  )



  const abrir = () => {

    setOpen(true)

    setPaso('preview')

    setResultado(null)

    setConfirmacionMontos('')

    setConfirmacionPrestamoId('')

    setAceptaDestructivo(false)

    void cargarPreview()

  }



  const irAConfirmar = () => {

    if (preview?.sin_cache) {

      toast.warning(

        'No hay caché ABONOS. Ejecute «Recalcular» en Notificaciones → General.'

      )

      return

    }

    if (requiereLote) {

      toast.warning('Seleccione el lote del crédito (caché Notificaciones → General).')

      return

    }

    setPaso('confirmar')

    setConfirmacionPrestamoId('')

    setAceptaDestructivo(false)

  }



  const ejecutar = async () => {

    if (!Number.isFinite(pid) || pid <= 0) return

    if (String(confirmacionPrestamoId).trim() !== String(pid)) {

      toast.error(`Escriba el ID del préstamo (${pid}) para confirmar.`)

      return

    }

    if (!aceptaDestructivo) {

      toast.error('Marque la casilla de confirmación destructiva.')

      return

    }



    setEjecutando(true)

    onEjecutarInicio?.()

    onProgresoTabla?.('borrando')

    const tOcr = window.setTimeout(() => onProgresoTabla?.('ocr'), 4000)

    const tCascada = window.setTimeout(() => onProgresoTabla?.('cascada'), 12000)

    try {

      const needConf =

        preview != null && abonosSuperanUmbralConfirmo(preview, preview.abonos_drive)

      const res: ConciliarCarteraRevisionResponse =

        await revisionManualService.conciliarCarteraPrestamo(pid, {

          ...(loteSeleccionado.trim() ? { lote: loteSeleccionado.trim() } : {}),

          ...(needConf

            ? { confirmacion_montos_altos: confirmacionMontos.trim() }

            : {}),

        })



      if (res.requiere_seleccion_lote) {

        onEjecutarError?.()

        const ref = res.referencia_abonos ?? res.drive

        if (ref && typeof ref === 'object') {

          setPreview(ref as CompararAbonosNotificacionesReferencia)

        }

        setPaso('preview')

        toast.warning(

          res.error ||

            'Seleccione el lote del crédito (caché Notificaciones → General).'

        )

        return

      }



      if (res.requiere_confirmacion_montos_altos) {

        onEjecutarError?.()

        setPaso('confirmar')

        toast.warning(

          res.error ||

            `ABONOS elevado (>${res.umbral_usd ?? umbralConfirmaAbonosUsd(preview)} USD). Escriba CONFIRMO.`

        )

        return

      }



      if (!res.ok) {

        onEjecutarError?.()

        toast.error(res.error || res.mensaje || 'No se pudo conciliar cartera.')

        return

      }



      setResultado(res)

      setPaso('resultado')



      if (res.advertencia_parcial) {

        toast.warning(

          res.mensaje || 'Conciliación parcial: revise pagos no recreados.'

        )

      } else if (res.cascada?.ok === false) {

        toast.warning(res.mensaje || 'Pagos recreados; revise la cascada.')

      } else {

        toast.success('Conciliación completada.')

      }



      await onExito?.(res)

    } catch (e) {

      onEjecutarError?.()

      const status = (e as { response?: { status?: number } })?.response?.status

      const msg = getErrorMessage(e)

      if (status === 409) {

        toast.warning(

          msg ||

            'Otra conciliación está en curso para este préstamo. Espere y reintente.'

        )

      } else {

        toast.error(msg || 'Error al conciliar cartera.')

      }

    } finally {

      window.clearTimeout(tOcr)

      window.clearTimeout(tCascada)

      setEjecutando(false)

    }

  }



  const requiereLote =

    Boolean(preview?.requiere_seleccion_lote) &&

    !loteSeleccionado.trim() &&

    !(preview?.lote_aplicado || '').toString().trim()



  const needConfirmo =

    preview != null && abonosSuperanUmbralConfirmo(preview, preview.abonos_drive)



  const confirmacionPrestamoOk =

    String(confirmacionPrestamoId).trim() === String(pid)



  const fmt = (n: number | null | undefined) =>

    n == null || Number.isNaN(Number(n)) ? '—' : `$${Number(n).toFixed(2)}`



  const fmtDiff = (n: number | null | undefined) => {

    if (n == null || Number.isNaN(Number(n))) return '—'

    const abs = Math.abs(Number(n))

    const sign = Number(n) > 0.02 ? '+' : Number(n) < -0.02 ? '−' : ''

    return `${sign}$${abs.toFixed(2)}`

  }



  const abonosResultado =

    resultado?.abonos_referencia_notificaciones ?? resultado?.abonos_drive

  const diffResultado =

    resultado?.diferencia_referencia_ocr_usd ?? resultado?.diferencia_drive_ocr_usd



  return (

    <>

      <Button

        type="button"

        variant="outline"

        size="sm"

        className="gap-2 border-amber-300 bg-amber-50 text-amber-950 hover:bg-amber-100"

        disabled={disabled || ejecutando}

        onClick={abrir}

        title="Reserva comprobantes, toma ABONOS de Notificaciones→General, recrea pagos por OCR y aplica cascada (solo admin)"

      >

        {ejecutando ? (

          <Loader2 className="h-4 w-4 animate-spin" />

        ) : (

          <Scale className="h-4 w-4" />

        )}

        Conciliar

      </Button>



      <Dialog open={open} onOpenChange={v => (v ? setOpen(true) : cerrar())}>

        <DialogContent className="max-w-lg">

          <DialogHeader>

            <DialogTitle>

              {paso === 'resultado'

                ? `Resultado conciliación (préstamo ${pid})`

                : `Conciliar cartera (préstamo ${pid})`}

            </DialogTitle>

          </DialogHeader>



          {paso === 'resultado' && resultado ? (

            <div className="space-y-3 text-sm">

              <div

                className={`rounded-lg border p-3 ${

                  resultado.advertencia_parcial

                    ? 'border-amber-300 bg-amber-50'

                    : 'border-green-300 bg-green-50'

                }`}

              >

                <p className="font-medium text-foreground">

                  {resultado.advertencia_parcial

                    ? 'Conciliación parcial'

                    : 'Conciliación completada'}

                </p>

                <p className="mt-1 text-muted-foreground">{resultado.mensaje}</p>

              </div>

              <ul className="space-y-2 rounded border bg-slate-50 p-3">

                <li>

                  <span className="text-muted-foreground">Pagos recreados (OCR):</span>{' '}

                  <strong>{fmt(resultado.total_pagos_recriados_usd)}</strong>

                  <span className="text-muted-foreground">

                    {' '}

                    ({resultado.ocr_ok}/{resultado.ocr_total})

                  </span>

                </li>

                <li>

                  <span className="text-muted-foreground">

                    ABONOS Notificaciones → General (referencia):

                  </span>{' '}

                  <strong>{fmt(abonosResultado)}</strong>

                </li>

                <li className="text-base">

                  <span className="text-muted-foreground">Diferencia OCR − ABONOS:</span>{' '}

                  <strong

                    className={

                      diffResultado != null && Math.abs(diffResultado) > 0.02

                        ? 'text-amber-800'

                        : 'text-green-800'

                    }

                  >

                    {fmtDiff(diffResultado)}

                  </strong>

                </li>

                {resultado.prestamo_estado_final ? (

                  <li>

                    <span className="text-muted-foreground">Estado préstamo:</span>{' '}

                    {resultado.prestamo_estado_previo &&

                    resultado.prestamo_estado_previo !==

                      resultado.prestamo_estado_final

                      ? `${resultado.prestamo_estado_previo} → `

                      : ''}

                    <strong>{resultado.prestamo_estado_final}</strong>

                  </li>

                ) : null}

              </ul>

              <div className="rounded border border-sky-200 bg-sky-50 p-3 text-sky-950">

                <p className="font-medium">¿Por qué la tabla puede verse igual?</p>

                <p className="mt-1 text-muted-foreground">

                  Conciliar <strong>no reemplaza</strong> los montos por ABONOS de

                  General. Recrea cada pago con el OCR del comprobante. Si cada

                  imagen sigue leyendo el mismo monto (p. ej. $177.00), la lista

                  se verá igual aunque en BD sí cambió: se borraron{' '}

                  <strong>{resultado.pagos_eliminados ?? '—'}</strong> pago(s) y se

                  crearon <strong>{resultado.ocr_ok ?? '—'}</strong> filas nuevas

                  {resultado.detalle?.length

                    ? ` (ID ${resultado.detalle

                        .filter(d => d.ok && d.pago_id)

                        .map(d => d.pago_id)

                        .join(', ')})`

                    : ''}

                  , con cascada reaplicada a cuotas.

                </p>

                {diffResultado != null && Math.abs(diffResultado) > 0.02 ? (

                  <p className="mt-2 text-amber-900">

                    ABONOS en General ({fmt(abonosResultado)}) ≠ total OCR (

                    {fmt(resultado.total_pagos_recriados_usd)}). Esa diferencia (

                    {fmtDiff(diffResultado)}) requiere <strong>cuadre manual</strong>{' '}

                    en revisión; Conciliar no ajusta montos sola.

                  </p>

                ) : null}

              </div>

              {resultado.advertencia_parcial ? (

                <p className="flex items-start gap-2 text-amber-900">

                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />

                  Cuadre manualmente los pagos que no se recrearon y la diferencia

                  con ABONOS si aplica.

                </p>

              ) : null}

            </div>

          ) : loadingPreview ? (

            <div className="flex items-center gap-2 py-6 text-muted-foreground">

              <Loader2 className="h-5 w-5 animate-spin" />

              Leyendo ABONOS (Notificaciones → General)…

            </div>

          ) : paso === 'confirmar' ? (

            <div className="space-y-3 text-sm">

              <p className="rounded border border-red-200 bg-red-50 p-3 text-red-900">

                Se borrarán <strong>todos los pagos de este préstamo</strong> y se

                recrearán desde comprobantes reservados. Esta acción no se puede

                deshacer con un clic.

              </p>

              <label className="flex items-start gap-2">

                <input

                  type="checkbox"

                  className="mt-1"

                  checked={aceptaDestructivo}

                  onChange={e => setAceptaDestructivo(e.target.checked)}

                />

                <span>

                  Entiendo que se eliminarán los pagos del préstamo {pid} y se

                  reconstruirá la cartera desde las imágenes reservadas.

                </span>

              </label>

              <div>

                <label className="mb-1 block font-medium">

                  Escriba el ID del préstamo ({pid}) para confirmar

                </label>

                <Input

                  value={confirmacionPrestamoId}

                  onChange={e => setConfirmacionPrestamoId(e.target.value)}

                  placeholder={String(pid)}

                  autoComplete="off"

                />

              </div>

              {needConfirmo && (

                <div>

                  <label className="mb-1 block font-medium text-amber-900">

                    ABONOS elevado (Notificaciones → General): escriba CONFIRMO

                  </label>

                  <Input

                    value={confirmacionMontos}

                    onChange={e => setConfirmacionMontos(e.target.value)}

                    placeholder="CONFIRMO"

                    autoComplete="off"

                  />

                </div>

              )}

            </div>

          ) : (

            <div className="space-y-3 text-sm">

              <p className="text-muted-foreground">

                <strong>Notificaciones → General es la referencia</strong> (misma

                caché que «Diferencia abono» en BD, no consulta Drive en vivo). Los

                montos que entran a cartera salen del{' '}

                <strong>OCR de cada comprobante</strong>, no del valor ABONOS

                directamente.

              </p>

              <ol className="list-decimal space-y-1 pl-5 text-muted-foreground">

                <li>Reserva imágenes en tabla temporal</li>

                <li>Borra pagos solo de este préstamo</li>

                <li>Recrea pagos con OCR (conciliado/visto)</li>

                <li>Cascada a cuotas</li>

                <li>Compara total OCR vs ABONOS (Notificaciones → General)</li>

              </ol>

              {preview?.sin_cache ? (

                <p className="rounded border border-amber-300 bg-amber-50 p-3 text-amber-950">

                  {(preview.advertencias && preview.advertencias[0]) ||

                    'Sin caché ABONOS. Vaya a Notificaciones → General y pulse «Recalcular».'}

                </p>

              ) : null}

              {preview && !preview.sin_cache ? (

                <ul className="space-y-1 rounded border bg-slate-50 p-3">

                  <li>

                    <span className="text-muted-foreground">

                      ABONOS (Notificaciones → General):

                    </span>{' '}

                    <strong>{fmt(preview.abonos_drive)}</strong>

                  </li>

                  <li>

                    <span className="text-muted-foreground">Total en cuotas BD:</span>{' '}

                    {fmt(preview.total_pagado_cuotas)}

                  </li>

                  <li>

                    <span className="text-muted-foreground">Diferencia ABONOS − cuotas:</span>{' '}

                    {fmt(preview.diferencia)}

                  </li>

                  {preview.cache_at ? (

                    <li className="text-xs text-muted-foreground">

                      Caché actualizada: {preview.cache_at}

                    </li>

                  ) : null}

                </ul>

              ) : null}



              {preview?.requiere_seleccion_lote &&

              (preview.opciones_lote?.length ?? 0) > 0 ? (

                <div>

                  <label className="mb-1 block font-medium">Lote (caché)</label>

                  <select

                    className="w-full rounded-md border px-2 py-1.5"

                    value={loteSeleccionado}

                    onChange={e => {

                      setLoteSeleccionado(e.target.value)

                      void cargarPreview(e.target.value)

                    }}

                  >

                    <option value="">— Elija lote —</option>

                    {preview.opciones_lote!.map(op => (

                      <option key={op.lote} value={op.lote}>

                        {op.lote} ({fmt(op.abonos)})

                      </option>

                    ))}

                  </select>

                </div>

              ) : null}

            </div>

          )}



          <DialogFooter className="gap-2">

            {paso === 'resultado' ? (

              <Button type="button" onClick={cerrar}>

                Cerrar

              </Button>

            ) : (

              <>

                <Button type="button" variant="outline" onClick={cerrar}>

                  Cancelar

                </Button>

                {paso === 'preview' ? (

                  <Button

                    type="button"

                    variant="default"

                    disabled={

                      loadingPreview ||

                      requiereLote ||

                      !preview ||

                      Boolean(preview?.sin_cache)

                    }

                    onClick={irAConfirmar}

                  >

                    Continuar

                  </Button>

                ) : (

                  <Button

                    type="button"

                    variant="destructive"

                    disabled={

                      ejecutando ||

                      !aceptaDestructivo ||

                      !confirmacionPrestamoOk ||

                      (needConfirmo && confirmacionMontos.trim().toUpperCase() !== 'CONFIRMO')

                    }

                    onClick={() => void ejecutar()}

                  >

                    {ejecutando ? (

                      <>

                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />

                        Conciliando…

                      </>

                    ) : (

                      'Ejecutar conciliación'

                    )}

                  </Button>

                )}

              </>

            )}

          </DialogFooter>

        </DialogContent>

      </Dialog>

    </>

  )

}

