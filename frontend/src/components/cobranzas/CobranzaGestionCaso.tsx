import React, { useCallback, useEffect, useRef, useState } from 'react'
import {
  ChevronDown,
  ChevronUp,
  Loader2,
  RefreshCw,
  Upload,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'

import {
  actualizarCasoCobranza,
  abrirSesionNotaCobranza,
  guardarNotaSesionCobranza,
  MOTIVOS_COBRANZA_LABEL,
  sincronizarAcuerdosCobranza,
  type CobranzaCasoDetalle,
  type CobranzaPrestamoResumen,
  type MonedaAcuerdoCobranza,
  type MotivoCobranza,
} from '../../services/cobranzaService'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'
import { Textarea } from '../ui/textarea'
import { formatCurrency, formatDate } from '../../utils'
import { cn } from '../../utils'

const MAX_ARCHIVOS_NOTA = 4
const TIPOS_ARCHIVO_ACEPTADOS = '.pdf,.jpg,.jpeg,.png'

function hoyIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function motivoInicial(p: CobranzaPrestamoResumen): MotivoCobranza {
  if (p.cuotas_atrasadas >= 3) return 'ATRASO_CRONICO'
  if (p.saldo_pendiente > 0) return 'NEGOCIACION'
  return 'OTRO'
}

export interface CobranzaGestionCasoProps {
  prestamo: CobranzaPrestamoResumen
  /** Cambia cada vez que se abre/fija la negociacion para crear una nota nueva en BD. */
  aperturaToken: number
  /** Si false, no abre sesion al montar (solo al expandir / token en modo embed). */
  autoIniciarSesion?: boolean
  formularioInicialExpandido?: boolean
  mostrarCabecera?: boolean
  onCasoActualizado?: (prestamoId: number, casoId: number) => void
  /** Tras guardar nota (p. ej. refrescar historial en el dialogo). */
  onNotaGuardada?: () => void
  className?: string
}

export function CobranzaGestionCaso({
  prestamo,
  aperturaToken,
  autoIniciarSesion = true,
  formularioInicialExpandido = true,
  mostrarCabecera = true,
  onCasoActualizado,
  onNotaGuardada,
  className,
}: CobranzaGestionCasoProps) {
  const [caso, setCaso] = useState<CobranzaCasoDetalle | null>(null)
  const [notaSesionId, setNotaSesionId] = useState<number | null>(null)
  const [cargando, setCargando] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [formularioExpandido, setFormularioExpandido] = useState(
    formularioInicialExpandido
  )
  const [motivoCaso, setMotivoCaso] = useState<MotivoCobranza>(() =>
    motivoInicial(prestamo)
  )
  const [mensaje, setMensaje] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [moneda, setMoneda] = useState<MonedaAcuerdoCobranza>('USD')
  const [archivos, setArchivos] = useState<File[]>([])
  const iniciandoRef = useRef(false)
  const inputArchivosRef = useRef<HTMLInputElement>(null)
  const idInputArchivos = `cobranza-adjuntos-${prestamo.id}`

  const limpiarFormularioNota = useCallback(() => {
    setMensaje('')
    setCantidad('')
    setMoneda('USD')
    setArchivos([])
  }, [])

  const iniciarSesion = useCallback(async () => {
    if (iniciandoRef.current) return
    iniciandoRef.current = true
    setCargando(true)
    limpiarFormularioNota()
    const motivo = motivoInicial(prestamo)
    setMotivoCaso(motivo)
    try {
      const sesion = await abrirSesionNotaCobranza({
        prestamo_id: prestamo.id,
        motivo,
      })
      setCaso(sesion.caso)
      setNotaSesionId(sesion.nota_id)
      setMotivoCaso(sesion.caso.motivo)
      onCasoActualizado?.(prestamo.id, sesion.caso.id)
    } catch (e: unknown) {
      toast.error(
        e instanceof Error ? e.message : 'Error al abrir sesion de nota'
      )
      setCaso(null)
      setNotaSesionId(null)
    } finally {
      setCargando(false)
      iniciandoRef.current = false
    }
  }, [prestamo, limpiarFormularioNota, onCasoActualizado])

  useEffect(() => {
    if (!autoIniciarSesion) return
    setFormularioExpandido(formularioInicialExpandido)
    void iniciarSesion()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo al abrir/fijar
  }, [prestamo.id, aperturaToken, autoIniciarSesion])

  const expandirFormulario = async () => {
    setFormularioExpandido(true)
    if (!notaSesionId) {
      await iniciarSesion()
    }
  }

  const onElegirArchivos = (e: React.ChangeEvent<HTMLInputElement>) => {
    const list = e.target.files
    if (!list?.length) return
    const nuevos = Array.from(list).slice(0, MAX_ARCHIVOS_NOTA)
    if (list.length > MAX_ARCHIVOS_NOTA) {
      toast.error(`Solo hasta ${MAX_ARCHIVOS_NOTA} archivos por nota.`)
    }
    setArchivos(nuevos)
    e.target.value = ''
  }

  const quitarArchivo = (idx: number) => {
    setArchivos(prev => prev.filter((_, i) => i !== idx))
  }

  const guardarNota = async () => {
    if (!notaSesionId) {
      toast.error('Espere a que se abra la sesion de la nota.')
      return
    }
    if (!mensaje.trim()) {
      toast.error('Ingrese el mensaje de la nota.')
      return
    }
    setGuardando(true)
    try {
      const cant = cantidad.trim()
        ? parseFloat(cantidad.replace(',', '.'))
        : undefined
      const det = await guardarNotaSesionCobranza(notaSesionId, {
        mensaje: mensaje.trim(),
        cantidad:
          cant != null && !Number.isNaN(cant) && cant >= 0 ? cant : undefined,
        moneda,
        archivos,
      })
      setCaso(det)
      onCasoActualizado?.(prestamo.id, det.id)
      setNotaSesionId(null)
      limpiarFormularioNota()
      setFormularioExpandido(false)
      onNotaGuardada?.()
      toast.success(`Nota guardada (${formatDate(hoyIso())}).`)
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al guardar nota')
    } finally {
      setGuardando(false)
    }
  }

  const guardarMotivo = async (motivo: MotivoCobranza) => {
    if (!caso) return
    try {
      const det = await actualizarCasoCobranza(caso.id, { motivo })
      setCaso(det)
      setMotivoCaso(motivo)
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al guardar')
    }
  }

  const refrescarAcuerdos = async () => {
    if (!caso) return
    try {
      const det = await sincronizarAcuerdosCobranza(caso.id)
      setCaso(det)
      toast.success('Estados actualizados segun pagos.')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al sincronizar')
    }
  }

  return (
    <div className={cn('space-y-5', className)}>
      {mostrarCabecera && (
        <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-200 pb-3">
          <div>
            <p className="text-lg font-semibold text-slate-900">
              Caso en gestion - Prestamo #{prestamo.id}
            </p>
            <p className="text-sm text-slate-600">
              {prestamo.nombres || prestamo.cedula} · Pendiente{' '}
              {formatCurrency(prestamo.saldo_pendiente)}
            </p>
          </div>
          {caso && (
            <Button variant="outline" size="sm" onClick={refrescarAcuerdos}>
              <RefreshCw className="mr-1 h-4 w-4" />
              Cruce con pagos
            </Button>
          )}
        </div>
      )}

      {cargando && formularioExpandido && (
        <div className="flex items-center gap-2 py-4 text-slate-600">
          <Loader2 className="h-5 w-5 animate-spin" />
          Abriendo nueva nota en el sistema...
        </div>
      )}

      <div className="overflow-hidden rounded-lg border-2 border-dashed border-blue-200 bg-blue-50/40">
        <button
          type="button"
          className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-blue-100/50"
          onClick={() =>
            formularioExpandido
              ? setFormularioExpandido(false)
              : void expandirFormulario()
          }
        >
          <span className="text-sm font-semibold text-slate-800">
            Nueva nota
          </span>
          {formularioExpandido ? (
            <ChevronUp className="h-5 w-5 text-slate-500" />
          ) : (
            <ChevronDown className="h-5 w-5 text-slate-500" />
          )}
        </button>

        {!formularioExpandido && (
          <div className="border-t border-blue-200 px-4 py-3">
            <p className="text-sm text-slate-600">
              Nota guardada. Revise el historial abajo o expanda para agregar
              otra.
            </p>
            <Button
              type="button"
              size="sm"
              className="mt-2"
              variant="outline"
              onClick={() => void expandirFormulario()}
            >
              Agregar otra nota
            </Button>
          </div>
        )}

        {formularioExpandido && (
          <div className="border-t border-blue-200 px-4 pb-4 pt-2">
            <p className="mb-3 text-xs text-slate-500">
              Al guardar se registran mensaje, monto y hasta {MAX_ARCHIVOS_NOTA}{' '}
              respaldos (PDF, JPG o PNG). La fecha es la del dia de guardado (
              {formatDate(hoyIso())}).
            </p>

            {!caso && !cargando && (
              <div className="mb-3">
                <label className="mb-1 block text-xs font-medium text-slate-600">
                  Motivo del caso (primera nota)
                </label>
                <Select
                  value={motivoCaso}
                  onValueChange={v => setMotivoCaso(v as MotivoCobranza)}
                >
                  <SelectTrigger className="h-9 bg-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(
                      Object.keys(MOTIVOS_COBRANZA_LABEL) as MotivoCobranza[]
                    ).map(k => (
                      <SelectItem key={k} value={k}>
                        {MOTIVOS_COBRANZA_LABEL[k]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {caso && (
              <div className="mb-3">
                <label className="mb-1 block text-xs font-medium text-slate-600">
                  Motivo del caso
                </label>
                <Select
                  value={caso.motivo}
                  onValueChange={v => guardarMotivo(v as MotivoCobranza)}
                >
                  <SelectTrigger className="h-9 bg-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(
                      Object.keys(MOTIVOS_COBRANZA_LABEL) as MotivoCobranza[]
                    ).map(k => (
                      <SelectItem key={k} value={k}>
                        {MOTIVOS_COBRANZA_LABEL[k]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
              <div className="sm:col-span-2">
                <label className="text-xs font-medium">
                  Cantidad (opcional)
                </label>
                <Input
                  type="number"
                  min={0}
                  step="0.01"
                  className="mt-1 bg-white"
                  placeholder="0.00"
                  value={cantidad}
                  onChange={e => setCantidad(e.target.value)}
                  disabled={cargando || !notaSesionId}
                />
              </div>
              <div>
                <label className="text-xs font-medium">Moneda</label>
                <Select
                  value={moneda}
                  onValueChange={v => setMoneda(v as MonedaAcuerdoCobranza)}
                  disabled={cargando || !notaSesionId}
                >
                  <SelectTrigger className="mt-1 bg-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="BS">BS</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="mb-3">
              <label className="text-xs font-medium">Mensaje</label>
              <Textarea
                className="mt-1 bg-white"
                placeholder="Detalle de la conversacion o acuerdo..."
                value={mensaje}
                onChange={e => setMensaje(e.target.value)}
                rows={3}
                disabled={cargando || !notaSesionId}
              />
            </div>

            <div className="mb-3">
              <p className="mb-2 text-xs font-semibold text-slate-700">
                Respaldos de la conversacion
              </p>
              <div
                className={cn(
                  'rounded-lg border-2 border-dashed p-4',
                  cargando || !notaSesionId
                    ? 'border-slate-200 bg-slate-100'
                    : 'border-blue-300 bg-white'
                )}
              >
                <input
                  ref={inputArchivosRef}
                  id={idInputArchivos}
                  type="file"
                  accept={TIPOS_ARCHIVO_ACEPTADOS}
                  multiple
                  className="sr-only"
                  onChange={onElegirArchivos}
                  disabled={
                    cargando ||
                    !notaSesionId ||
                    archivos.length >= MAX_ARCHIVOS_NOTA
                  }
                />
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="border-blue-400 bg-blue-50 text-blue-800 hover:bg-blue-100"
                    disabled={
                      cargando ||
                      !notaSesionId ||
                      archivos.length >= MAX_ARCHIVOS_NOTA
                    }
                    onClick={() => inputArchivosRef.current?.click()}
                  >
                    <Upload className="mr-2 h-4 w-4" />
                    Seleccionar archivos
                  </Button>
                  <span className="text-sm font-medium text-slate-600">
                    {archivos.length}/{MAX_ARCHIVOS_NOTA}
                  </span>
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  PDF, JPG o PNG · maximo {MAX_ARCHIVOS_NOTA} archivos por nota
                </p>
                {!notaSesionId && !cargando && (
                  <p className="mt-1 text-xs text-amber-700">
                    Espere a que se abra la sesion de la nota para adjuntar
                    archivos.
                  </p>
                )}
                {archivos.length > 0 && (
                  <ul className="mt-3 space-y-1 border-t border-slate-200 pt-3">
                    {archivos.map((f, i) => (
                      <li
                        key={`${f.name}-${i}`}
                        className="flex items-center justify-between rounded border border-slate-200 bg-slate-50 px-2 py-1.5 text-xs"
                      >
                        <span className="truncate font-medium text-slate-800">
                          {f.name}
                        </span>
                        <button
                          type="button"
                          className="ml-2 shrink-0 text-red-600 hover:text-red-800"
                          onClick={() => quitarArchivo(i)}
                          aria-label="Quitar archivo"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <Button
              onClick={guardarNota}
              disabled={guardando || cargando || !notaSesionId}
            >
              {guardando ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Guardando...
                </>
              ) : (
                'Guardar nota'
              )}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
