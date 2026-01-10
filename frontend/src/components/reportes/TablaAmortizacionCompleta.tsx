import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Search,
  Edit,
  Trash2,
  Save,
  X,
  FileText,
  User,
  DollarSign,
  Calendar,
  CreditCard,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { prestamoService } from '@/services/prestamoService'
import { cuotaService, type Cuota, type CuotaUpdate } from '@/services/cuotaService'
import { pagoService, type Pago } from '@/services/pagoService'
import { clienteService } from '@/services/clienteService'
import { usePrestamosByCedula } from '@/hooks/usePrestamos'
import { toast } from 'sonner'
import { formatCurrency, formatDate } from '@/utils'

interface ClienteInfo {
  id: number
  cedula: string
  nombres: string
  telefono: string
  email: string
}

interface PrestamoInfo {
  id: number
  total_financiamiento: number
  estado: string
  fecha_aprobacion: string | null
  numero_cuotas: number
  tasa_interes: number
}

export function TablaAmortizacionCompleta() {
  const [cedulaBuscar, setCedulaBuscar] = useState('')
  const [cedulaSeleccionada, setCedulaSeleccionada] = useState<string | null>(null)
  const [cuotaEditando, setCuotaEditando] = useState<Cuota | null>(null)
  const [pagoEditando, setPagoEditando] = useState<Pago | null>(null)
  const [mostrarDialogCuota, setMostrarDialogCuota] = useState(false)
  const [mostrarDialogPago, setMostrarDialogPago] = useState(false)
  const queryClient = useQueryClient()

  // Buscar cliente por cédula
  const { data: clienteInfo, isLoading: loadingCliente } = useQuery({
    queryKey: ['cliente-cedula', cedulaSeleccionada],
    queryFn: async () => {
      if (!cedulaSeleccionada) return null
      try {
        const response = await clienteService.getClientes({ cedula: cedulaSeleccionada }, 1, 1)
        return response.data?.[0] || null
      } catch (error) {
        console.error('Error buscando cliente:', error)
        return null
      }
    },
    enabled: !!cedulaSeleccionada,
  })

  // Obtener préstamos por cédula usando hook
  const { data: prestamos, isLoading: loadingPrestamos } = usePrestamosByCedula(cedulaSeleccionada || '')

  // Obtener cuotas de todos los préstamos
  const { data: todasLasCuotas, isLoading: loadingCuotas } = useQuery({
    queryKey: ['cuotas-prestamos', prestamos?.map(p => p.id)],
    queryFn: async () => {
      if (!prestamos || prestamos.length === 0) return []
      const cuotasPromises = prestamos.map(p => cuotaService.getCuotasByPrestamo(p.id))
      const cuotasArrays = await Promise.all(cuotasPromises)
      return cuotasArrays.flat()
    },
    enabled: !!prestamos && prestamos.length > 0,
  })

  // Obtener pagos por cédula
  const { data: pagosData, isLoading: loadingPagos } = useQuery({
    queryKey: ['pagos-cedula', cedulaSeleccionada],
    queryFn: () => pagoService.getAllPagos(1, 1000, { cedula: cedulaSeleccionada! }),
    enabled: !!cedulaSeleccionada,
  })

  const pagos = pagosData?.pagos || []

  // Mutaciones para editar
  const mutationActualizarCuota = useMutation({
    mutationFn: ({ cuotaId, data }: { cuotaId: number; data: CuotaUpdate }) =>
      cuotaService.updateCuota(cuotaId, data),
    onSuccess: () => {
      toast.success('Cuota actualizada exitosamente')
      queryClient.invalidateQueries({ queryKey: ['cuotas-prestamos'] })
      setMostrarDialogCuota(false)
      setCuotaEditando(null)
    },
    onError: (error: any) => {
      toast.error(`Error al actualizar cuota: ${error?.message || 'Error desconocido'}`)
    },
  })

  const mutationEliminarCuota = useMutation({
    mutationFn: (cuotaId: number) => cuotaService.deleteCuota(cuotaId),
    onSuccess: () => {
      toast.success('Cuota eliminada exitosamente')
      queryClient.invalidateQueries({ queryKey: ['cuotas-prestamos'] })
    },
    onError: (error: any) => {
      toast.error(`Error al eliminar cuota: ${error?.message || 'Error desconocido'}`)
    },
  })

  const mutationActualizarPago = useMutation({
    mutationFn: ({ pagoId, data }: { pagoId: number; data: Partial<Pago> }) =>
      pagoService.updatePago(pagoId, data),
    onSuccess: () => {
      toast.success('Pago actualizado exitosamente')
      queryClient.invalidateQueries({ queryKey: ['pagos-cedula'] })
      setMostrarDialogPago(false)
      setPagoEditando(null)
    },
    onError: (error: any) => {
      toast.error(`Error al actualizar pago: ${error?.message || 'Error desconocido'}`)
    },
  })

  const mutationEliminarPago = useMutation({
    mutationFn: (pagoId: number) => pagoService.deletePago(pagoId),
    onSuccess: () => {
      toast.success('Pago eliminado exitosamente')
      queryClient.invalidateQueries({ queryKey: ['pagos-cedula'] })
    },
    onError: (error: any) => {
      toast.error(`Error al eliminar pago: ${error?.message || 'Error desconocido'}`)
    },
  })

  const handleBuscar = () => {
    if (cedulaBuscar.trim()) {
      setCedulaSeleccionada(cedulaBuscar.trim().toUpperCase())
    } else {
      toast.error('Por favor ingresa una cédula')
    }
  }

  const handleEditarCuota = (cuota: Cuota) => {
    setCuotaEditando(cuota)
    setMostrarDialogCuota(true)
  }

  const handleEditarPago = (pago: Pago) => {
    setPagoEditando(pago)
    setMostrarDialogPago(true)
  }

  const getEstadoBadge = (estado: string) => {
    const estados: Record<string, { color: string; label: string }> = {
      PAGADO: { color: 'bg-green-500', label: 'Pagado' },
      PENDIENTE: { color: 'bg-yellow-500', label: 'Pendiente' },
      ATRASADO: { color: 'bg-red-500', label: 'Atrasado' },
      PARCIAL: { color: 'bg-blue-500', label: 'Parcial' },
      VENCIDA: { color: 'bg-red-500', label: 'Vencida' },
    }
    const config = estados[estado?.toUpperCase()] || { color: 'bg-gray-500', label: estado || 'N/A' }
    return <Badge className={`${config.color} text-white`}>{config.label}</Badge>
  }

  const totalFinanciamiento = prestamos?.reduce((sum, p) => sum + (p.total_financiamiento || 0), 0) || 0

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Tabla de Amortización por Cédula
          </CardTitle>
          <CardDescription>
            Busca una cédula para ver su tabla de amortización completa con opciones de edición y eliminación
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 mb-6">
            <Input
              placeholder="Ingresa la cédula del cliente"
              value={cedulaBuscar}
              onChange={(e) => setCedulaBuscar(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleBuscar()}
              className="max-w-md"
            />
            <Button onClick={handleBuscar} disabled={loadingCliente || loadingPrestamos}>
              <Search className="w-4 h-4 mr-2" />
              Buscar
            </Button>
          </div>

          {cedulaSeleccionada && (
            <>
              {/* Información del Cliente */}
              {(loadingCliente || loadingPrestamos) ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                  <span className="ml-2">Cargando información...</span>
                </div>
              ) : (
                <>
                  {clienteInfo && (
                    <Card className="mb-6 bg-blue-50">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <User className="w-5 h-5" />
                          Información del Cliente
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div>
                            <Label className="text-sm text-gray-600">Nombre Completo</Label>
                            <p className="font-semibold">{clienteInfo.nombres || 'N/A'}</p>
                          </div>
                          <div>
                            <Label className="text-sm text-gray-600">Cédula</Label>
                            <p className="font-semibold">{clienteInfo.cedula}</p>
                          </div>
                          <div>
                            <Label className="text-sm text-gray-600">Teléfono</Label>
                            <p className="font-semibold">{clienteInfo.telefono || 'N/A'}</p>
                          </div>
                          <div>
                            <Label className="text-sm text-gray-600">Email</Label>
                            <p className="font-semibold">{clienteInfo.email || 'N/A'}</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Resumen de Préstamos */}
                  {prestamos && prestamos.length > 0 && (
                    <Card className="mb-6 bg-green-50">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <DollarSign className="w-5 h-5" />
                          Resumen de Préstamos
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div>
                            <Label className="text-sm text-gray-600">Total de Préstamos</Label>
                            <p className="text-2xl font-bold">{prestamos.length}</p>
                          </div>
                          <div>
                            <Label className="text-sm text-gray-600">Total Financiamiento</Label>
                            <p className="text-2xl font-bold text-green-600">{formatCurrency(totalFinanciamiento)}</p>
                          </div>
                          <div>
                            <Label className="text-sm text-gray-600">Total Cuotas</Label>
                            <p className="text-2xl font-bold">{todasLasCuotas?.length || 0}</p>
                          </div>
                          <div>
                            <Label className="text-sm text-gray-600">Total Pagos</Label>
                            <p className="text-2xl font-bold">{pagos.length}</p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Tabla de Cuotas */}
                  {todasLasCuotas && todasLasCuotas.length > 0 && (
                    <Card className="mb-6">
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <CreditCard className="w-5 h-5" />
                          Tabla de Amortización - Cuotas
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="overflow-x-auto">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Préstamo ID</TableHead>
                                <TableHead>Cuota #</TableHead>
                                <TableHead>Fecha Vencimiento</TableHead>
                                <TableHead>Monto Cuota</TableHead>
                                <TableHead>Capital</TableHead>
                                <TableHead>Interés</TableHead>
                                <TableHead>Total Pagado</TableHead>
                                <TableHead>Capital Pendiente</TableHead>
                                <TableHead>Estado</TableHead>
                                <TableHead>Días Mora</TableHead>
                                <TableHead>Mora</TableHead>
                                <TableHead className="text-right">Acciones</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {todasLasCuotas.map((cuota) => (
                                <TableRow key={cuota.id}>
                                  <TableCell>{cuota.prestamo_id}</TableCell>
                                  <TableCell className="font-semibold">{cuota.numero_cuota}</TableCell>
                                  <TableCell>{formatDate(cuota.fecha_vencimiento)}</TableCell>
                                  <TableCell>{formatCurrency(cuota.monto_cuota)}</TableCell>
                                  <TableCell>{formatCurrency(cuota.monto_capital)}</TableCell>
                                  <TableCell>{formatCurrency(cuota.monto_interes)}</TableCell>
                                  <TableCell className="font-semibold">{formatCurrency(cuota.total_pagado)}</TableCell>
                                  <TableCell>{formatCurrency(cuota.capital_pendiente)}</TableCell>
                                  <TableCell>{getEstadoBadge(cuota.estado)}</TableCell>
                                  <TableCell>{cuota.dias_mora || 0}</TableCell>
                                  <TableCell>{formatCurrency(cuota.monto_mora || 0)}</TableCell>
                                  <TableCell className="text-right">
                                    <div className="flex gap-2 justify-end">
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => handleEditarCuota(cuota)}
                                        title="Editar Cuota"
                                      >
                                        <Edit className="w-4 h-4" />
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                        onClick={() => {
                                          if (window.confirm(`¿Estás seguro de eliminar la cuota #${cuota.numero_cuota}?`)) {
                                            mutationEliminarCuota.mutate(cuota.id)
                                          }
                                        }}
                                        title="Eliminar Cuota"
                                      >
                                        <Trash2 className="w-4 h-4" />
                                      </Button>
                                    </div>
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Tabla de Pagos */}
                  {pagos && pagos.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <DollarSign className="w-5 h-5" />
                          Pagos Realizados
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="overflow-x-auto">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>ID</TableHead>
                                <TableHead>Préstamo ID</TableHead>
                                <TableHead>Fecha Pago</TableHead>
                                <TableHead>Monto Pagado</TableHead>
                                <TableHead>Número de Documento</TableHead>
                                <TableHead>Institución</TableHead>
                                <TableHead>Estado</TableHead>
                                <TableHead>Conciliado</TableHead>
                                <TableHead>Fecha Registro</TableHead>
                                <TableHead className="text-right">Acciones</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {pagos.map((pago) => (
                                <TableRow key={pago.id}>
                                  <TableCell>{pago.id}</TableCell>
                                  <TableCell>{pago.prestamo_id || 'N/A'}</TableCell>
                                  <TableCell>{formatDate(pago.fecha_pago)}</TableCell>
                                  <TableCell className="font-semibold">{formatCurrency(pago.monto_pagado)}</TableCell>
                                  <TableCell className="font-mono text-sm">{pago.numero_documento}</TableCell>
                                  <TableCell>{pago.institucion_bancaria || 'N/A'}</TableCell>
                                  <TableCell>{getEstadoBadge(pago.estado)}</TableCell>
                                  <TableCell>
                                    {(pago.verificado_concordancia === 'SI' || pago.conciliado) ? (
                                      <Badge className="bg-green-500 text-white">SI</Badge>
                                    ) : (
                                      <Badge className="bg-gray-500 text-white">NO</Badge>
                                    )}
                                  </TableCell>
                                  <TableCell>{pago.fecha_registro ? formatDate(pago.fecha_registro) : 'N/A'}</TableCell>
                                  <TableCell className="text-right">
                                    <div className="flex gap-2 justify-end">
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => handleEditarPago(pago)}
                                        title="Editar Pago"
                                      >
                                        <Edit className="w-4 h-4" />
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="outline"
                                        className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                        onClick={() => {
                                          if (window.confirm(`¿Estás seguro de eliminar el pago ID ${pago.id}?`)) {
                                            mutationEliminarPago.mutate(pago.id)
                                          }
                                        }}
                                        title="Eliminar Pago"
                                      >
                                        <Trash2 className="w-4 h-4" />
                                      </Button>
                                    </div>
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {(!todasLasCuotas || todasLasCuotas.length === 0) && (!pagos || pagos.length === 0) && (
                    <Card>
                      <CardContent className="py-8 text-center">
                        <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                        <p className="text-gray-600">No se encontraron cuotas ni pagos para esta cédula</p>
                      </CardContent>
                    </Card>
                  )}
                </>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Dialog Editar Cuota */}
      <Dialog open={mostrarDialogCuota} onOpenChange={setMostrarDialogCuota}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Editar Cuota #{cuotaEditando?.numero_cuota}</DialogTitle>
            <p className="text-sm text-gray-600 mb-4">Modifica los datos de la cuota. Los cambios se guardarán inmediatamente.</p>
          </DialogHeader>
          {cuotaEditando && (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                const formData = new FormData(e.currentTarget)
                const data: CuotaUpdate = {
                  capital_pagado: parseFloat(formData.get('capital_pagado') as string) || cuotaEditando.capital_pagado,
                  interes_pagado: parseFloat(formData.get('interes_pagado') as string) || cuotaEditando.interes_pagado,
                  mora_pagada: parseFloat(formData.get('mora_pagada') as string) || cuotaEditando.mora_pagada,
                  estado: (formData.get('estado') as string) || cuotaEditando.estado,
                  observaciones: (formData.get('observaciones') as string) || cuotaEditando.observaciones || null,
                }
                mutationActualizarCuota.mutate({ cuotaId: cuotaEditando.id, data })
              }}
              className="space-y-4"
            >
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="capital_pagado">Capital Pagado</Label>
                  <Input
                    id="capital_pagado"
                    name="capital_pagado"
                    type="number"
                    step="0.01"
                    defaultValue={cuotaEditando.capital_pagado}
                  />
                </div>
                <div>
                  <Label htmlFor="interes_pagado">Interés Pagado</Label>
                  <Input
                    id="interes_pagado"
                    name="interes_pagado"
                    type="number"
                    step="0.01"
                    defaultValue={cuotaEditando.interes_pagado}
                  />
                </div>
                <div>
                  <Label htmlFor="mora_pagada">Mora Pagada</Label>
                  <Input
                    id="mora_pagada"
                    name="mora_pagada"
                    type="number"
                    step="0.01"
                    defaultValue={cuotaEditando.mora_pagada}
                  />
                </div>
                <div>
                  <Label htmlFor="estado">Estado</Label>
                  <select
                    id="estado"
                    name="estado"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    defaultValue={cuotaEditando.estado}
                  >
                    <option value="PENDIENTE">Pendiente</option>
                    <option value="PARCIAL">Parcial</option>
                    <option value="PAGADO">Pagado</option>
                    <option value="ATRASADO">Atrasado</option>
                    <option value="VENCIDA">Vencida</option>
                  </select>
                </div>
              </div>
              <div>
                <Label htmlFor="observaciones">Observaciones</Label>
                <Textarea
                  id="observaciones"
                  name="observaciones"
                  defaultValue={cuotaEditando.observaciones || ''}
                  rows={3}
                />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setMostrarDialogCuota(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={mutationActualizarCuota.isPending}>
                  {mutationActualizarCuota.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-2" />
                      Guardar Cambios
                    </>
                  )}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog Editar Pago */}
      <Dialog open={mostrarDialogPago} onOpenChange={setMostrarDialogPago}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Editar Pago ID {pagoEditando?.id}</DialogTitle>
            <p className="text-sm text-gray-600 mb-4">Modifica los datos del pago. Los números científicos se normalizarán automáticamente.</p>
          </DialogHeader>
          {pagoEditando && (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                const formData = new FormData(e.currentTarget)
                
                // Normalizar número de documento si es científico
                let numeroDocumento = (formData.get('numero_documento') as string) || pagoEditando.numero_documento
                if (numeroDocumento && (/[eE]/.test(numeroDocumento))) {
                  try {
                    const numeroFloat = parseFloat(numeroDocumento)
                    numeroDocumento = Math.floor(numeroFloat).toString()
                    toast.info(`Número de documento normalizado: ${numeroDocumento}`)
                  } catch (e) {
                    console.error('Error normalizando número:', e)
                  }
                }
                
                const data: Partial<Pago> = {
                  monto_pagado: parseFloat(formData.get('monto_pagado') as string) || pagoEditando.monto_pagado,
                  numero_documento: numeroDocumento,
                  fecha_pago: (formData.get('fecha_pago') as string) || pagoEditando.fecha_pago.toString(),
                  institucion_bancaria: (formData.get('institucion_bancaria') as string) || pagoEditando.institucion_bancaria || null,
                }
                mutationActualizarPago.mutate({ pagoId: pagoEditando.id, data })
              }}
              className="space-y-4"
            >
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="monto_pagado">Monto Pagado</Label>
                  <Input
                    id="monto_pagado"
                    name="monto_pagado"
                    type="number"
                    step="0.01"
                    defaultValue={pagoEditando.monto_pagado}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="fecha_pago">Fecha de Pago</Label>
                  <Input
                    id="fecha_pago"
                    name="fecha_pago"
                    type="date"
                    defaultValue={
                      typeof pagoEditando.fecha_pago === 'string'
                        ? pagoEditando.fecha_pago.split('T')[0]
                        : new Date(pagoEditando.fecha_pago).toISOString().split('T')[0]
                    }
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="numero_documento">Número de Documento</Label>
                  <Input
                    id="numero_documento"
                    name="numero_documento"
                    defaultValue={pagoEditando.numero_documento}
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Los números científicos se normalizarán automáticamente
                  </p>
                </div>
                <div>
                  <Label htmlFor="institucion_bancaria">Institución Bancaria</Label>
                  <Input
                    id="institucion_bancaria"
                    name="institucion_bancaria"
                    defaultValue={pagoEditando.institucion_bancaria || ''}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setMostrarDialogPago(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={mutationActualizarPago.isPending}>
                  {mutationActualizarPago.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-2" />
                      Guardar Cambios
                    </>
                  )}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
