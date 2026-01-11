import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Edit, Save, X, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { formatCurrency } from '@/utils'
import { apiClient } from '@/services/api'

interface DiferenciaAbono {
  prestamo_id: number
  cedula: string
  nombres: string
  total_abonos_bd: number
  total_abonos_imagen: number
  diferencia: number
  detalle: string
}

export function ReporteDiferenciasAbonos() {
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [nuevoTotal, setNuevoTotal] = useState<string>('')
  const [editandoImagenId, setEditandoImagenId] = useState<number | null>(null)
  const [nuevoValorImagen, setNuevoValorImagen] = useState<string>('')
  const queryClient = useQueryClient()

  // Obtener diferencias de abonos
  const { data: diferencias, isLoading, error } = useQuery({
    queryKey: ['diferencias-abonos'],
    queryFn: async (): Promise<DiferenciaAbono[]> => {
      const response = await apiClient.get<DiferenciaAbono[]>('/api/v1/reportes/diferencias-abonos')
      return response
    },
    refetchInterval: 30000, // Refrescar cada 30 segundos
  })

  // Mutación para ajustar total_abonos_bd
  const ajustarAbono = useMutation({
    mutationFn: async ({ prestamoId, nuevoTotal }: { prestamoId: number; nuevoTotal: number }) => {
      const response = await apiClient.put(`/api/v1/reportes/diferencias-abonos/${prestamoId}/ajustar`, {
        nuevo_total_abonos: nuevoTotal,
      })
      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['diferencias-abonos'] })
      queryClient.invalidateQueries({ queryKey: ['prestamos'] })
      setEditandoId(null)
      setNuevoTotal('')
      toast.success('Total de abonos ajustado exitosamente. Los pagos han sido redistribuidos.')
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Error al ajustar total de abonos')
    },
  })

  // Mutación para actualizar valor de imagen
  const actualizarValorImagen = useMutation({
    mutationFn: async ({ cedula, valorImagen }: { cedula: string; valorImagen: number }) => {
      const response = await apiClient.put('/api/v1/reportes/diferencias-abonos/actualizar-valor-imagen', {
        cedula,
        valor_imagen: valorImagen,
      })
      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['diferencias-abonos'] })
      setEditandoImagenId(null)
      setNuevoValorImagen('')
      toast.success('Valor de imagen actualizado exitosamente.')
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Error al actualizar valor de imagen')
    },
  })

  const handleEditar = (diferencia: DiferenciaAbono) => {
    setEditandoId(diferencia.prestamo_id)
    setNuevoTotal(diferencia.total_abonos_bd.toString())
  }

  const handleCancelar = () => {
    setEditandoId(null)
    setNuevoTotal('')
  }

  const handleGuardar = (prestamoId: number) => {
    const total = parseFloat(nuevoTotal)
    if (isNaN(total) || total < 0) {
      toast.error('El total debe ser un número válido mayor o igual a 0')
      return
    }
    ajustarAbono.mutate({ prestamoId, nuevoTotal: total })
  }

  const handleEditarImagen = (diferencia: DiferenciaAbono) => {
    setEditandoImagenId(diferencia.prestamo_id)
    setNuevoValorImagen(diferencia.total_abonos_imagen.toString())
  }

  const handleCancelarImagen = () => {
    setEditandoImagenId(null)
    setNuevoValorImagen('')
  }

  const handleGuardarImagen = (cedula: string) => {
    const valor = parseFloat(nuevoValorImagen)
    if (isNaN(valor) || valor < 0) {
      toast.error('El valor debe ser un número válido mayor o igual a 0')
      return
    }
    actualizarValorImagen.mutate({ cedula, valorImagen: valor })
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            <span className="ml-2">Cargando diferencias...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-8">
          <div className="flex items-center justify-center text-red-600">
            <AlertCircle className="h-6 w-6 mr-2" />
            <span>Error al cargar diferencias de abonos</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!diferencias || diferencias.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Diferencias de Abonos</CardTitle>
          <CardDescription>
            Préstamos marcados para revisión con diferencias entre BD y valores de referencia
          </CardDescription>
        </CardHeader>
        <CardContent className="py-8">
          <div className="text-center text-gray-500">
            <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p className="text-lg font-medium">No hay diferencias pendientes</p>
            <p className="text-sm mt-2">
              Marca préstamos para revisar en la página de Préstamos para que aparezcan aquí.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-orange-600" />
          Diferencias de Abonos
        </CardTitle>
        <CardDescription>
          {diferencias.length} préstamo(s) con diferencias pendientes de revisión. Puedes ajustar el total de abonos
          y el sistema redistribuirá los pagos uniformemente.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Cédula</TableHead>
                <TableHead>Cliente</TableHead>
                <TableHead className="text-right">Total Abonos BD</TableHead>
                <TableHead className="text-right">Total Abonos Imagen</TableHead>
                <TableHead className="text-right">Diferencia</TableHead>
                <TableHead>Detalle</TableHead>
                <TableHead className="text-center">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {diferencias.map((diferencia) => (
                <TableRow key={diferencia.prestamo_id}>
                  <TableCell className="font-medium">{diferencia.cedula}</TableCell>
                  <TableCell>{diferencia.nombres}</TableCell>
                  <TableCell className="text-right">
                    {editandoId === diferencia.prestamo_id ? (
                      <Input
                        type="number"
                        value={nuevoTotal}
                        onChange={(e) => setNuevoTotal(e.target.value)}
                        className="w-32 text-right"
                        step="0.01"
                        min="0"
                      />
                    ) : (
                      <span className="font-semibold">{formatCurrency(diferencia.total_abonos_bd)}</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    {editandoImagenId === diferencia.prestamo_id ? (
                      <Input
                        type="number"
                        value={nuevoValorImagen}
                        onChange={(e) => setNuevoValorImagen(e.target.value)}
                        className="w-32 text-right"
                        step="0.01"
                        min="0"
                      />
                    ) : (
                      <div className="flex items-center justify-end gap-2">
                        <span className="text-gray-600">{formatCurrency(diferencia.total_abonos_imagen)}</span>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleEditarImagen(diferencia)}
                          className="h-6 w-6 p-0"
                          title="Editar valor de imagen"
                        >
                          <Edit className="h-3 w-3" />
                        </Button>
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Badge
                      variant={diferencia.diferencia > 100 ? 'destructive' : 'secondary'}
                      className="font-semibold"
                    >
                      {formatCurrency(diferencia.diferencia)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-gray-600">{diferencia.detalle}</span>
                  </TableCell>
                  <TableCell className="text-center">
                    {editandoImagenId === diferencia.prestamo_id ? (
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          size="sm"
                          variant="default"
                          onClick={() => handleGuardarImagen(diferencia.cedula)}
                          disabled={actualizarValorImagen.isPending}
                        >
                          {actualizarValorImagen.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Save className="h-4 w-4" />
                          )}
                        </Button>
                        <Button size="sm" variant="outline" onClick={handleCancelarImagen}>
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ) : editandoId === diferencia.prestamo_id ? (
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          size="sm"
                          variant="default"
                          onClick={() => handleGuardar(diferencia.prestamo_id)}
                          disabled={ajustarAbono.isPending}
                        >
                          {ajustarAbono.isPending ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Save className="h-4 w-4" />
                          )}
                        </Button>
                        <Button size="sm" variant="outline" onClick={handleCancelar}>
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => handleEditar(diferencia)}>
                        <Edit className="h-4 w-4 mr-1" />
                        Ajustar BD
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
