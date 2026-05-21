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
  type MotivoCobranza,
} from '../../services/cobranzaService'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Badge } from '../ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select'
import { Textarea } from '../ui/textarea'
import { formatCurrency, formatDate } from '../../utils'

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

export interface CobranzaNegociacionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  prestamo: CobranzaPrestamoResumen | null
  onCasoActualizado?: (prestamoId: number, casoId: number) => void
}

export function CobranzaNegociacionDialog({
  open,
  onOpenChange,
  prestamo,
  onCasoActualizado,
}: CobranzaNegociacionDialogProps) {
  const [caso, setCaso] = useState<CobranzaCasoDetalle | null>(null)
  const [cargando, setCargando] = useState(false)
  const [motivoNuevo, setMotivoNuevo] = useState<MotivoCobranza>('ATRASO_CRONICO')
  const [obsNuevo, setObsNuevo] = useState('')
  const [fechaAcuerdo, setFechaAcuerdo] = useState(
    () => new Date().toISOString().slice(0, 10)
  )
  const [fechaCompromiso, setFechaCompromiso] = useState('')
  const [notasAcuerdo, setNotasAcuerdo] = useState('')
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
    if (!open || !prestamo) {
      setCaso(null)
      return
    }
    setMotivoNuevo(
      prestamo.cuotas_atrasadas >= 3
        ? 'ATRASO_CRONICO'
        : prestamo.saldo_pendiente > 0
          ? 'NEGOCIACION'
          : 'OTRO'
    )
    setObsNuevo('')
    if (prestamo.caso_id) {
      void cargarCaso(prestamo.caso_id)
    } else {
      setCaso(null)
    }
  }, [open, prestamo, cargarCaso])

  const abrirCaso = async () => {
    if (!prestamo) return
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
    if (!caso || !notasAcuerdo.trim()) {
      toast.error('Ingrese las notas del acuerdo.')
      return
    }
    try {
      await crearAcuerdoCobranza(caso.id, {
        fecha_acuerdo: fechaAcuerdo,
        fecha_compromiso: fechaCompromiso || undefined,
        notas: notasAcuerdo.trim(),
      })
      const det = await sincronizarAcuerdosCobranza(caso.id)
      setCaso(det)
      setNotasAcuerdo('')
      toast.success('Acuerdo registrado.')
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
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Negociacion de pago</DialogTitle>
          <DialogDescription>
            {prestamo
              ? `Prestamo #${prestamo.id} · ${prestamo.nombres || prestamo.cedula}`
              : ''}
          </DialogDescription>
        </DialogHeader>

        {cargando && !caso && (
          <div className="flex items-center gap-2 py-8 text-slate-600">
            <Loader2 className="h-5 w-5 animate-spin" />
            Cargando...
          </div>
        )}

        {!cargando && !caso && prestamo && (
          <div className="space-y-4">
            <p className="text-sm text-slate-600">
              No hay caso activo para este prestamo. Abra uno para registrar
              acuerdos, notas e imagenes.
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

        {caso && (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Badge variant="secondary">Caso #{caso.id}</Badge>
              <Button variant="outline" size="sm" onClick={refrescarAcuerdos}>
                <RefreshCw className="mr-1 h-4 w-4" />
                Cruce con pagos
              </Button>
            </div>

            <div className="grid grid-cols-2 gap-3 rounded-lg border bg-slate-50 p-3 text-sm">
              <div>
                <span className="text-slate-500">Pendiente</span>
                <p className="font-semibold text-amber-800">
                  {formatCurrency(caso.saldo_pendiente_actual ?? 0)}
                </p>
              </div>
              <div>
                <span className="text-slate-500">Cuotas en atraso</span>
                <p className="font-medium">{caso.cuotas_atrasadas_actual ?? 0}</p>
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
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-800">
                  Bitacora de acuerdos
                </h3>
              </div>
              <div className="space-y-2 rounded-lg border p-3">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs font-medium">Fecha acuerdo</label>
                    <Input
                      type="date"
                      value={fechaAcuerdo}
                      onChange={e => setFechaAcuerdo(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium">
                      Compromiso de pago
                    </label>
                    <Input
                      type="date"
                      value={fechaCompromiso}
                      onChange={e => setFechaCompromiso(e.target.value)}
                    />
                  </div>
                </div>
                <Textarea
                  placeholder="Detalle de la negociacion: monto acordado, forma de pago, notas..."
                  value={notasAcuerdo}
                  onChange={e => setNotasAcuerdo(e.target.value)}
                  rows={3}
                />
                <Button size="sm" onClick={agregarAcuerdo}>
                  Guardar acuerdo
                </Button>
              </div>
              {caso.acuerdos.length > 0 && (
                <div className="mt-3 max-h-48 space-y-2 overflow-y-auto">
                  {caso.acuerdos.map(a => (
                    <div
                      key={a.id}
                      className="rounded border border-slate-200 p-2 text-sm"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="font-medium">
                          {formatDate(a.fecha_acuerdo)}
                          {a.fecha_compromiso
                            ? ` · compromiso ${formatDate(a.fecha_compromiso)}`
                            : ''}
                        </span>
                        {estadoAcuerdoBadge(a.estado)}
                      </div>
                      <p className="mt-1 whitespace-pre-wrap text-slate-700">
                        {a.notas}
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
                <div className="grid grid-cols-3 gap-2">
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
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
