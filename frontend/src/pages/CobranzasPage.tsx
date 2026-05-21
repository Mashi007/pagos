import React, { useCallback, useState } from 'react'
import {
  AlertTriangle,
  DollarSign,
  Eye,
  Upload,
  Loader2,
  RefreshCw,
  Search,
  Trash2,
  X,
} from 'lucide-react'
import toast from 'react-hot-toast'

import {
  buscarCobranzasPorCedula,
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
  type CobranzaBuscarResponse,
  type CobranzaCasoDetalle,
  type CobranzaPrestamoResumen,
  type MotivoCobranza,
} from '../services/cobranzaService'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'
import { Textarea } from '../components/ui/textarea'
import { formatCurrency, formatDate } from '../utils'
import { cn } from '../utils'

function modalidadLabel(v?: string | null): string {
  if (v === 'MENSUAL') return 'Mensual'
  if (v === 'QUINCENAL') return 'Quincenal'
  if (v === 'SEMANAL') return 'Semanal'
  return v || '-'
}

function estadoPrestamoBadge(estado: string) {
  const map: Record<string, string> = {
    APROBADO: 'bg-green-100 text-green-800',
    LIQUIDADO: 'bg-slate-100 text-slate-700',
    DRAFT: 'bg-gray-100 text-gray-700',
  }
  const labels: Record<string, string> = {
    APROBADO: 'Aprobado',
    LIQUIDADO: 'Liquidado',
    DRAFT: 'Borrador',
  }
  return (
    <Badge className={map[estado] || 'bg-blue-100 text-blue-800'}>
      {labels[estado] || estado}
    </Badge>
  )
}

function estadoAcuerdoBadge(estado: string) {
  const cls =
    estado === 'CUMPLIDO'
      ? 'bg-green-100 text-green-800'
      : estado === 'INCUMPLIDO'
        ? 'bg-red-100 text-red-800'
        : 'bg-amber-100 text-amber-800'
  return (
    <Badge className={cls}>{ESTADO_ACUERDO_LABEL[estado as keyof typeof ESTADO_ACUERDO_LABEL] || estado}</Badge>
  )
}

export default function CobranzasPage() {
  const [cedulaInput, setCedulaInput] = useState('')
  const [buscando, setBuscando] = useState(false)
  const [resultado, setResultado] = useState<CobranzaBuscarResponse | null>(null)
  const [caso, setCaso] = useState<CobranzaCasoDetalle | null>(null)
  const [prestamoSel, setPrestamoSel] = useState<CobranzaPrestamoResumen | null>(null)
  const [cargandoCaso, setCargandoCaso] = useState(false)
  const [motivoNuevo, setMotivoNuevo] = useState<MotivoCobranza>('ATRASO_CRONICO')
  const [obsNuevo, setObsNuevo] = useState('')
  const [fechaAcuerdo, setFechaAcuerdo] = useState(
    () => new Date().toISOString().slice(0, 10)
  )
  const [fechaCompromiso, setFechaCompromiso] = useState('')
  const [notasAcuerdo, setNotasAcuerdo] = useState('')
  const [subiendoImg, setSubiendoImg] = useState(false)

  const cargarCaso = useCallback(async (casoId: number) => {
    setCargandoCaso(true)
    try {
      const det = await obtenerCasoCobranza(casoId)
      setCaso(det)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Error al cargar caso'
      toast.error(msg)
      setCaso(null)
    } finally {
      setCargandoCaso(false)
    }
  }, [])

  const handleBuscar = async () => {
    if (!cedulaInput.trim()) {
      toast.error('Ingrese la cedula.')
      return
    }
    setBuscando(true)
    setCaso(null)
    setPrestamoSel(null)
    try {
      const res = await buscarCobranzasPorCedula(cedulaInput.trim())
      setResultado(res)
      if (!res.prestamos.length) {
        toast.error('No se encontraron prestamos para esta cedula.')
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Error al buscar'
      toast.error(msg)
      setResultado(null)
    } finally {
      setBuscando(false)
    }
  }

  const abrirPrestamo = async (p: CobranzaPrestamoResumen) => {
    setPrestamoSel(p)
    if (p.caso_id) {
      await cargarCaso(p.caso_id)
      return
    }
    setCaso(null)
    setMotivoNuevo(
      p.cuotas_atrasadas >= 3 ? 'ATRASO_CRONICO' : p.saldo_pendiente > 0 ? 'NEGOCIACION' : 'OTRO'
    )
  }

  const abrirCasoNuevo = async () => {
    if (!prestamoSel) return
    setCargandoCaso(true)
    try {
      const det = await crearCasoCobranza({
        prestamo_id: prestamoSel.id,
        motivo: motivoNuevo,
        observaciones: obsNuevo.trim() || undefined,
      })
      setCaso(det)
      toast.success('Caso de cobranza abierto.')
      if (resultado) {
        setResultado({
          ...resultado,
          prestamos: resultado.prestamos.map(pr =>
            pr.id === prestamoSel.id
              ? {
                  ...pr,
                  caso_id: det.id,
                  caso_estado: det.estado,
                  caso_motivo: det.motivo,
                }
              : pr
          ),
        })
      }
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'No se pudo crear el caso')
    } finally {
      setCargandoCaso(false)
    }
  }

  const guardarMotivo = async (motivo: MotivoCobranza) => {
    if (!caso) return
    try {
      const det = await actualizarCasoCobranza(caso.id, { motivo })
      setCaso(det)
      toast.success('Motivo actualizado.')
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
      toast.error(e instanceof Error ? e.message : 'Error al registrar acuerdo')
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
      toast.error(err instanceof Error ? err.message : 'Error al subir imagen')
    } finally {
      setSubiendoImg(false)
      e.target.value = ''
    }
  }

  const onEliminarImagen = async (imagenId: string) => {
    if (!caso) return
    if (!window.confirm('Eliminar esta imagen?')) return
    try {
      await eliminarImagenCobranza(caso.id, imagenId)
      await cargarCaso(caso.id)
      toast.success('Imagen eliminada.')
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Error al eliminar')
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Cobranzas</h1>
        <p className="mt-1 text-sm text-slate-600">
          Gestion de casos por mora, sobrepago u otras negociaciones. Busque por
          cedula y seleccione el prestamo para ver el detalle y la bitacora.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Search className="h-5 w-5" />
            Buscar por cedula
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Input
            placeholder="V32862424 o 32862424"
            value={cedulaInput}
            onChange={e => setCedulaInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleBuscar()}
            className="max-w-xs"
          />
          <Button onClick={handleBuscar} disabled={buscando}>
            {buscando ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Buscando...
              </>
            ) : (
              'Buscar'
            )}
          </Button>
        </CardContent>
      </Card>

      {resultado && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>
                Prestamos — {resultado.nombres || resultado.cedula}
              </CardTitle>
              <p className="text-sm text-slate-500">Cedula: {resultado.cedula}</p>
            </CardHeader>
            <CardContent>
              {resultado.prestamos.length === 0 ? (
                <p className="text-slate-500">Sin resultados.</p>
              ) : (
                <div className="overflow-hidden rounded-lg border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Cliente</TableHead>
                        <TableHead>Cedula</TableHead>
                        <TableHead>Monto</TableHead>
                        <TableHead>Modalidad</TableHead>
                        <TableHead>Cuotas</TableHead>
                        <TableHead>Estado</TableHead>
                        <TableHead className="whitespace-normal leading-tight">
                          Pendiente
                        </TableHead>
                        <TableHead className="text-right">Accion</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {resultado.prestamos.map(p => (
                        <TableRow
                          key={p.id}
                          className={cn(
                            prestamoSel?.id === p.id && 'bg-blue-50/80'
                          )}
                        >
                          <TableCell>
                            <div className="max-w-[10rem] text-sm font-medium leading-snug">
                              {p.nombres || '-'}
                            </div>
                          </TableCell>
                          <TableCell className="text-sm">{p.cedula}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <DollarSign className="h-4 w-4 shrink-0 text-green-600" />
                              <span className="font-semibold text-green-700">
                                {formatCurrency(p.total_financiamiento)}
                              </span>
                            </div>
                          </TableCell>
                          <TableCell>{modalidadLabel(p.modalidad_pago)}</TableCell>
                          <TableCell>{p.numero_cuotas ?? '-'}</TableCell>
                          <TableCell>{estadoPrestamoBadge(p.estado)}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <DollarSign className="h-4 w-4 shrink-0 text-amber-600" />
                              <span className="font-semibold text-amber-800">
                                {formatCurrency(p.saldo_pendiente)}
                              </span>
                            </div>
                            {p.cuotas_atrasadas > 0 && (
                              <div className="mt-0.5 flex items-center gap-1 text-xs text-orange-700">
                                <AlertTriangle className="h-3 w-3" />
                                {p.cuotas_atrasadas} en atraso
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-blue-600 hover:bg-blue-50"
                              title="Ver / gestionar cobranza"
                              onClick={() => abrirPrestamo(p)}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="min-h-[320px]">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Detalle del caso</CardTitle>
              {caso && (
                <Button variant="outline" size="sm" onClick={refrescarAcuerdos}>
                  <RefreshCw className="mr-1 h-4 w-4" />
                  Cruce pagos
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {!prestamoSel && (
                <p className="text-slate-500">
                  Seleccione un prestamo de la lista para ver o abrir un caso.
                </p>
              )}
              {prestamoSel && !caso && !cargandoCaso && (
                <div className="space-y-4">
                  <p className="text-sm text-slate-700">
                    Prestamo #{prestamoSel.id} — sin caso activo. Indique el motivo
                    de gestion.
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
                      Observaciones
                    </label>
                    <Textarea
                      value={obsNuevo}
                      onChange={e => setObsNuevo(e.target.value)}
                      rows={3}
                      placeholder="Contexto de la negociacion..."
                    />
                  </div>
                  <Button onClick={abrirCasoNuevo}>Abrir caso de cobranza</Button>
                </div>
              )}
              {cargandoCaso && (
                <div className="flex items-center gap-2 text-slate-600">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Cargando...
                </div>
              )}
              {caso && !cargandoCaso && (
                <div className="space-y-6">
                  <div className="rounded-lg border bg-slate-50 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="font-semibold text-slate-900">
                          {caso.nombres}
                        </p>
                        <p className="text-sm text-slate-600">
                          {caso.cedula} · Prestamo #{caso.prestamo_id}
                        </p>
                      </div>
                      <Badge variant="secondary">Caso #{caso.id}</Badge>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-slate-500">Financiamiento</span>
                        <p className="font-medium text-green-700">
                          {formatCurrency(caso.total_financiamiento_actual ?? 0)}
                        </p>
                      </div>
                      <div>
                        <span className="text-slate-500">Pendiente actual</span>
                        <p className="font-medium text-amber-800">
                          {formatCurrency(caso.saldo_pendiente_actual ?? 0)}
                        </p>
                      </div>
                      <div>
                        <span className="text-slate-500">Cuotas atrasadas</span>
                        <p className="font-medium">
                          {caso.cuotas_atrasadas_actual ?? 0}
                        </p>
                      </div>
                      <div>
                        <span className="text-slate-500">Modalidad / cuotas</span>
                        <p>
                          {modalidadLabel(caso.modalidad_pago)} /{' '}
                          {caso.numero_cuotas ?? '-'}
                        </p>
                      </div>
                    </div>
                    <div className="mt-3">
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
                  </div>

                  <div>
                    <div className="mb-2 flex items-center justify-between">
                      <h3 className="font-semibold text-slate-800">
                        Imagenes ({caso.imagenes.length}/10)
                      </h3>
                      {caso.imagenes.length < 10 && (
                        <label className="cursor-pointer">
                          <input
                            type="file"
                            accept="image/*,application/pdf"
                            className="hidden"
                            onChange={onSubirImagen}
                            disabled={subiendoImg}
                          />
                          <span className="inline-flex items-center gap-1 rounded-md border px-3 py-1.5 text-sm hover:bg-slate-50">
                            {subiendoImg ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Upload className="h-4 w-4" />
                            )}
                            Agregar
                          </span>
                        </label>
                      )}
                    </div>
                    {caso.imagenes.length === 0 ? (
                      <p className="text-sm text-slate-500">
                        Sin imagenes. Cargue evidencia de visitas o documentos.
                      </p>
                    ) : (
                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                        {caso.imagenes.map(img => {
                          const url = cobranzaImagenUrl(img.id)
                          const esPdf = img.content_type.includes('pdf')
                          return (
                            <div
                              key={img.id}
                              className="relative overflow-hidden rounded border bg-white"
                            >
                              {esPdf ? (
                                <a
                                  href={url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="flex h-24 items-center justify-center text-xs text-blue-600"
                                >
                                  PDF
                                </a>
                              ) : (
                                <a href={url} target="_blank" rel="noreferrer">
                                  <img
                                    src={url}
                                    alt={img.descripcion || 'Evidencia'}
                                    className="h-24 w-full object-cover"
                                  />
                                </a>
                              )}
                              <button
                                type="button"
                                className="absolute right-1 top-1 rounded bg-white/90 p-1 text-red-600 shadow"
                                onClick={() => onEliminarImagen(img.id)}
                                title="Eliminar"
                              >
                                <Trash2 className="h-3 w-3" />
                              </button>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>

                  <div>
                    <h3 className="mb-2 font-semibold text-slate-800">
                      Bitacora de acuerdos
                    </h3>
                    <p className="mb-3 text-xs text-slate-500">
                      Cumplido si hay pagos registrados desde la fecha de compromiso;
                      incumplido si vencio el plazo sin abonos.
                    </p>
                    <div className="mb-4 space-y-2 rounded border p-3">
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
                            Fecha compromiso pago
                          </label>
                          <Input
                            type="date"
                            value={fechaCompromiso}
                            onChange={e => setFechaCompromiso(e.target.value)}
                          />
                        </div>
                      </div>
                      <Textarea
                        placeholder="Notas del acuerdo..."
                        value={notasAcuerdo}
                        onChange={e => setNotasAcuerdo(e.target.value)}
                        rows={2}
                      />
                      <Button size="sm" onClick={agregarAcuerdo}>
                        Registrar acuerdo
                      </Button>
                    </div>
                    {caso.acuerdos.length === 0 ? (
                      <p className="text-sm text-slate-500">Sin acuerdos aun.</p>
                    ) : (
                      <div className="space-y-2">
                        {caso.acuerdos.map(a => (
                          <div
                            key={a.id}
                            className="rounded border border-slate-200 p-3 text-sm"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <span className="font-medium">
                                {formatDate(a.fecha_acuerdo)}
                                {a.fecha_compromiso
                                  ? ` → compromiso ${formatDate(a.fecha_compromiso)}`
                                  : ''}
                              </span>
                              {estadoAcuerdoBadge(a.estado)}
                            </div>
                            <p className="mt-2 whitespace-pre-wrap text-slate-700">
                              {a.notas}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-slate-600"
                    onClick={() => {
                      setPrestamoSel(null)
                      setCaso(null)
                    }}
                  >
                    <X className="mr-1 h-4 w-4" />
                    Cerrar detalle
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
