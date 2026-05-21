import React, { useCallback, useEffect, useState } from 'react'
import { Loader2, RefreshCw, Trash2, Upload } from 'lucide-react'
import toast from 'react-hot-toast'

import {
  crearAcuerdoCobranza,
  crearCasoCobranza,
  actualizarCasoCobranza,
  cobranzaImagenUrl,
  eliminarImagenCobranza,
  ESTADO_ACUERDO_LABEL,
  MOTIVOS_COBRANZA_LABEL,
  obtenerCasoCobranza,
  sincronizarAcuerdosCobranza,
  subirImagenCobranza,
  type CobranzaCasoDetalle,
  type CobranzaPrestamoResumen,
  type MonedaAcuerdoCobranza,
  type MotivoCobranza,
} from '../../services/cobranzaService'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Badge } from '../ui/badge'
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

function formatCantidadMoneda(
  cantidad?: number | null,
  moneda?: string
): string {
  if (cantidad == null || Number.isNaN(cantidad)) return '-'
  const m = (moneda || 'USD').toUpperCase()
  if (m === 'BS') {
    return `Bs. ${cantidad.toLocaleString('es-VE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }
  return formatCurrency(cantidad)
}

function estadoAcuerdoBadge(estado: string) {
  const cls =
    estado === 'CUMPLIDO'
      ? 'bg-green-100 text-green-800'
      : estado === 'INCUMPLIDO'
        ? 'bg-red-100 text-red-800'
        : 'bg-amber-100 text-amber-800'
  return (
    <Badge className={cls}>
      {ESTADO_ACUERDO_LABEL[estado as keyof typeof ESTADO_ACUERDO_LABEL] ||
        estado}
    </Badge>
  )
}

export interface CobranzaGestionCasoProps {
  prestamo: CobranzaPrestamoResumen
  onCasoActualizado?: (prestamoId: number, casoId: number) => void
  className?: string
}

export function CobranzaGestionCaso({
  prestamo,
  onCasoActualizado,
  className,
}: CobranzaGestionCasoProps) {
  const [caso, setCaso] = useState<CobranzaCasoDetalle | null>(null)
  const [cargando, setCargando] = useState(false)
  const [motivoNuevo, setMotivoNuevo] = useState<MotivoCobranza>('ATRASO_CRONICO')
  const [obsNuevo, setObsNuevo] = useState('')
  const [fechaMensaje, setFechaMensaje] = useState(
    () => new Date().toISOString().slice(0, 10)
  )
  const [mensaje, setMensaje] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [moneda, setMoneda] = useState<MonedaAcuerdoCobranza>('USD')
  const [subiendoImg, setSubiendoImg] = useState(false)

  const cargarCaso = useCallback(async (casoId: number) => {
    setCargando(true)
    try {
      const det = await obtenerCasoCobranza(casoId)
      setCaso(det)
      return det
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al cargar caso')
      setCaso(null)
      return null
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => {
    setMotivoNuevo(
      prestamo.cuotas_atrasadas >= 3
        ? 'ATRASO_CRONICO'
        : prestamo.saldo_pendiente > 0
          ? 'NEGOCIACION'
          : 'OTRO'
    )
    setObsNuevo('')
    setMensaje('')
    setCantidad('')
    if (prestamo.caso_id) {
      void cargarCaso(prestamo.caso_id)
    } else {
      setCaso(null)
      setCargando(false)
    }
  }, [prestamo.id, prestamo.caso_id, cargarCaso, prestamo.cuotas_atrasadas, prestamo.saldo_pendiente])

  const abrirCaso = async () => {
    setCargando(true)
    try {
      const det = await crearCasoCobranza({
        prestamo_id: prestamo.id,
        motivo: motivoNuevo,
        observaciones: obsNuevo.trim() || undefined,
      })
      setCaso(det)
      onCasoActualizado?.(prestamo.id, det.id)
      toast.success('Caso de cobranza abierto.')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'No se pudo abrir el caso')
    } finally {
      setCargando(false)
    }
  }

  const guardarMotivo = async (motivo: MotivoCobranza) => {
    if (!caso) return
    try {
      const det = await actualizarCasoCobranza(caso.id, { motivo })
      setCaso(det)
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al guardar')
    }
  }

  const agregarAcuerdo = async () => {
    if (!caso || !mensaje.trim()) {
      toast.error('Ingrese el mensaje.')
      return
    }
    const cant = parseFloat(cantidad.replace(',', '.'))
    if (!cantidad.trim() || Number.isNaN(cant) || cant < 0) {
      toast.error('Ingrese la cantidad.')
      return
    }
    try {
      await crearAcuerdoCobranza(caso.id, {
        fecha: fechaMensaje,
        mensaje: mensaje.trim(),
        cantidad: cant,
        moneda,
      })
      const det = await sincronizarAcuerdosCobranza(caso.id)
      setCaso(det)
      setMensaje('')
      setCantidad('')
      toast.success('Mensaje registrado.')
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Error al registrar')
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

  const onSubirImagen = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!caso || !e.target.files?.length) return
    const file = e.target.files[0]
    setSubiendoImg(true)
    try {
      await subirImagenCobranza(caso.id, file)
      await cargarCaso(caso.id)
      toast.success('Imagen cargada.')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al subir')
    } finally {
      setSubiendoImg(false)
      e.target.value = ''
    }
  }

  const onEliminarImagen = async (imagenId: string) => {
    if (!caso || !window.confirm('Eliminar esta imagen?')) return
    try {
      await eliminarImagenCobranza(caso.id, imagenId)
      await cargarCaso(caso.id)
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al eliminar')
    }
  }

  return (
    <div className={cn('space-y-5', className)}>
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-200 pb-3">
        <div>
          <p className="text-lg font-semibold text-slate-900">
            Caso en gestion — Prestamo #{prestamo.id}
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

      {cargando && !caso && (
        <div className="flex items-center gap-2 py-6 text-slate-600">
          <Loader2 className="h-5 w-5 animate-spin" />
          Cargando caso...
        </div>
      )}

      {!cargando && !caso && (
        <div className="space-y-4 rounded-lg border border-dashed border-slate-300 bg-slate-50/80 p-4">
          <p className="text-sm text-slate-600">
            Marque el prestamo con el check en la tabla y abra el caso para
            registrar mensajes e imagenes de la negociacion.
          </p>
          <div>
            <label className="mb-1 block text-sm font-medium">Motivo</label>
            <Select
              value={motivoNuevo}
              onValueChange={v => setMotivoNuevo(v as MotivoCobranza)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(MOTIVOS_COBRANZA_LABEL) as MotivoCobranza[]).map(
                  k => (
                    <SelectItem key={k} value={k}>
                      {MOTIVOS_COBRANZA_LABEL[k]}
                    </SelectItem>
                  )
                )}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">
              Observaciones iniciales
            </label>
            <Textarea
              value={obsNuevo}
              onChange={e => setObsNuevo(e.target.value)}
              rows={3}
              placeholder="Contexto: atraso cronico, sobrepago, llamada..."
            />
          </div>
          <Button onClick={abrirCaso}>Iniciar gestion de cobranza</Button>
        </div>
      )}

      {caso && !cargando && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">Caso #{caso.id}</Badge>
          </div>

          <div className="grid grid-cols-2 gap-3 rounded-lg border bg-slate-50 p-3 text-sm sm:grid-cols-4">
            <div>
              <span className="text-slate-500">Pendiente actual</span>
              <p className="font-semibold text-amber-800">
                {formatCurrency(caso.saldo_pendiente_actual ?? 0)}
              </p>
            </div>
            <div>
              <span className="text-slate-500">Cuotas en atraso</span>
              <p className="font-medium">{caso.cuotas_atrasadas_actual ?? 0}</p>
            </div>
            <div>
              <span className="text-slate-500">Modalidad</span>
              <p className="font-medium">
                {caso.modalidad_pago === 'MENSUAL'
                  ? 'Mensual'
                  : caso.modalidad_pago || '-'}
              </p>
            </div>
            <div>
              <span className="text-slate-500">Cuotas</span>
              <p className="font-medium">{caso.numero_cuotas ?? '-'}</p>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">
              Motivo del caso
            </label>
            <Select
              value={caso.motivo}
              onValueChange={v => guardarMotivo(v as MotivoCobranza)}
            >
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(MOTIVOS_COBRANZA_LABEL) as MotivoCobranza[]).map(
                  k => (
                    <SelectItem key={k} value={k}>
                      {MOTIVOS_COBRANZA_LABEL[k]}
                    </SelectItem>
                  )
                )}
              </SelectContent>
            </Select>
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-slate-800">
              Bitacora de mensajes
            </h3>
            <div className="space-y-2 rounded-lg border p-3">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <div>
                  <label className="text-xs font-medium">Fecha</label>
                  <Input
                    type="date"
                    value={fechaMensaje}
                    onChange={e => setFechaMensaje(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs font-medium">Cantidad</label>
                  <Input
                    type="number"
                    min={0}
                    step="0.01"
                    placeholder="0.00"
                    value={cantidad}
                    onChange={e => setCantidad(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs font-medium">Moneda</label>
                  <Select
                    value={moneda}
                    onValueChange={v => setMoneda(v as MonedaAcuerdoCobranza)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="USD">USD</SelectItem>
                      <SelectItem value="BS">BS</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <label className="text-xs font-medium">Mensaje</label>
                <Textarea
                  placeholder="Detalle de la negociacion..."
                  value={mensaje}
                  onChange={e => setMensaje(e.target.value)}
                  rows={3}
                />
              </div>
              <Button size="sm" onClick={agregarAcuerdo}>
                Guardar mensaje
              </Button>
            </div>
            {caso.acuerdos.length > 0 && (
              <div className="mt-3 max-h-56 space-y-2 overflow-y-auto">
                {caso.acuerdos.map(a => (
                  <div
                    key={a.id}
                    className="rounded border border-slate-200 p-2 text-sm"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium">
                        {formatDate(a.fecha)} ·{' '}
                        {formatCantidadMoneda(a.cantidad, a.moneda)}
                      </span>
                      {estadoAcuerdoBadge(a.estado)}
                    </div>
                    <p className="mt-1 whitespace-pre-wrap text-slate-700">
                      {a.mensaje}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-800">
                Imagenes ({caso.imagenes.length}/10)
              </h3>
              {caso.imagenes.length < 10 && (
                <label className="cursor-pointer text-sm text-blue-600 hover:underline">
                  <input
                    type="file"
                    accept="image/*,application/pdf"
                    className="hidden"
                    onChange={onSubirImagen}
                    disabled={subiendoImg}
                  />
                  <span className="inline-flex items-center gap-1">
                    {subiendoImg ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Upload className="h-4 w-4" />
                    )}
                    Subir
                  </span>
                </label>
              )}
            </div>
            {caso.imagenes.length > 0 && (
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
                {caso.imagenes.map(img => {
                  const url = cobranzaImagenUrl(img.id)
                  const esPdf = img.content_type.includes('pdf')
                  return (
                    <div
                      key={img.id}
                      className="relative overflow-hidden rounded border"
                    >
                      {esPdf ? (
                        <a
                          href={url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex h-20 items-center justify-center text-xs text-blue-600"
                        >
                          PDF
                        </a>
                      ) : (
                        <a href={url} target="_blank" rel="noreferrer">
                          <img
                            src={url}
                            alt=""
                            className="h-20 w-full object-cover"
                          />
                        </a>
                      )}
                      <button
                        type="button"
                        className="absolute right-1 top-1 rounded bg-white/90 p-0.5 text-red-600"
                        onClick={() => onEliminarImagen(img.id)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
