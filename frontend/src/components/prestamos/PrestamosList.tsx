import { useState } from 'react'
import { Plus, Search, Filter, Edit, Eye, Trash2, DollarSign, Calendar, Lock, Calculator } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { usePrestamos, useDeletePrestamo } from '@/hooks/usePrestamos'
import { usePermissions } from '@/hooks/usePermissions'
import { CrearPrestamoForm } from './CrearPrestamoForm'
import { PrestamosKPIs } from './PrestamosKPIs'
import { EvaluacionRiesgoForm } from './EvaluacionRiesgoForm'
import { formatDate } from '@/utils'

export function PrestamosList() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [estado, setEstado] = useState<string | undefined>(undefined)
  const [showCrearPrestamo, setShowCrearPrestamo] = useState(false)
  const [showEvaluacion, setShowEvaluacion] = useState(false)
  const [editingPrestamo, setEditingPrestamo] = useState<any>(null)
  const [evaluacionPrestamo, setEvaluacionPrestamo] = useState<any>(null)
  const [deletePrestamoId, setDeletePrestamoId] = useState<number | null>(null)

  const { data, isLoading, error } = usePrestamos({ search, estado }, page)
  const deletePrestamo = useDeletePrestamo()
  const { canEditPrestamo, canDeletePrestamo, canApprovePrestamo, canViewEvaluacionRiesgo } = usePermissions()

  const getEstadoBadge = (estado: string) => {
    const badges = {
      DRAFT: 'bg-gray-100 text-gray-800 border-gray-300',
      EN_REVISION: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      APROBADO: 'bg-green-100 text-green-800 border-green-300',
      RECHAZADO: 'bg-red-100 text-red-800 border-red-300',
    }
    return badges[estado as keyof typeof badges] || badges.DRAFT
  }

  const handleEdit = (prestamo: any) => {
    setEditingPrestamo(prestamo)
    setShowCrearPrestamo(true)
  }

  const handleEvaluarRiesgo = (prestamo: any) => {
    setEvaluacionPrestamo(prestamo)
    setShowEvaluacion(true)
  }

  const handleDelete = async (id: number) => {
    if (window.confirm('¿Está seguro de eliminar este préstamo?')) {
      await deletePrestamo.mutateAsync(id)
    }
  }

  if (showCrearPrestamo) {
    return (
      <CrearPrestamoForm
        prestamo={editingPrestamo}
        onClose={() => {
          setShowCrearPrestamo(false)
          setEditingPrestamo(null)
        }}
        onSuccess={() => {
          setShowCrearPrestamo(false)
          setEditingPrestamo(null)
        }}
      />
    )
  }

  if (showEvaluacion) {
    return (
      <EvaluacionRiesgoForm
        prestamo={evaluacionPrestamo}
        onClose={() => {
          setShowEvaluacion(false)
          setEvaluacionPrestamo(null)
        }}
        onSuccess={() => {
          setShowEvaluacion(false)
          setEvaluacionPrestamo(null)
        }}
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* KPIs */}
      {data && data.data && <PrestamosKPIs prestamos={data.data} />}

      {/* Encabezado */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Préstamos</h1>
          <p className="text-gray-600 mt-1">Gestión de préstamos y financiamiento</p>
        </div>
        <Button 
          size="lg"
          onClick={() => setShowCrearPrestamo(true)}
          className="px-8 py-6 text-base font-semibold min-w-[200px]"
        >
          <Plus className="w-5 h-5 mr-2" />
          Nuevo Préstamo
        </Button>
      </div>

      {/* Filtros y búsqueda */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
                <Input
                  placeholder="Buscar por nombre, cédula..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={estado || 'ALL'} onValueChange={(value) => setEstado(value === 'ALL' ? undefined : value)}>
              <SelectTrigger className="w-[200px]">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">Todos los estados</SelectItem>
                <SelectItem value="DRAFT">Borrador</SelectItem>
                <SelectItem value="EN_REVISION">En Revisión</SelectItem>
                <SelectItem value="APROBADO">Aprobado</SelectItem>
                <SelectItem value="RECHAZADO">Rechazado</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Tabla de préstamos */}
      <Card>
        <CardHeader>
          <CardTitle>Lista de Préstamos</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <div className="text-center py-8">Cargando...</div>}
          
          {error && (
            <div className="text-center py-8 text-red-600">
              Error al cargar préstamos
            </div>
          )}

          {!isLoading && !error && data && (
            <>
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Cliente</TableHead>
                      <TableHead>Cédula</TableHead>
                      <TableHead>Monto</TableHead>
                      <TableHead>Modalidad</TableHead>
                      <TableHead>Cuotas</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Fecha</TableHead>
                      <TableHead className="text-right">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.data.map((prestamo: any) => (
                      <TableRow key={prestamo.id}>
                        <TableCell>
                          <div className="font-medium">{prestamo.nombres}</div>
                        </TableCell>
                        <TableCell>{prestamo.cedula}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            <DollarSign className="h-4 w-4 text-green-600" />
                            <span className="font-semibold">{prestamo.total_financiamiento.toFixed(2)}</span>
                          </div>
                        </TableCell>
                        <TableCell>{prestamo.modalidad_pago}</TableCell>
                        <TableCell>{prestamo.numero_cuotas}</TableCell>
                        <TableCell>
                          <Badge className={getEstadoBadge(prestamo.estado)}>
                            {prestamo.estado}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-sm text-gray-600">
                            <Calendar className="h-4 w-4" />
                            {formatDate(prestamo.fecha_registro)}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            {/* Botón Evaluar Riesgo - Solo Admin */}
                            {canViewEvaluacionRiesgo() && prestamo.estado === 'EN_REVISION' && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEvaluarRiesgo(prestamo)}
                                title="Evaluar riesgo"
                              >
                                <Calculator className="h-4 w-4 text-blue-600" />
                              </Button>
                            )}

                            {/* Botón Editar - Solo si tiene permisos */}
                            {canEditPrestamo(prestamo.estado) ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleEdit(prestamo)}
                                title="Editar préstamo"
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                            ) : (
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled
                                title={prestamo.estado === 'APROBADO' || prestamo.estado === 'RECHAZADO' 
                                  ? 'Solo administradores pueden editar préstamos aprobados/rechazados'
                                  : 'No tiene permisos para editar'}
                              >
                                <Lock className="h-4 w-4 text-gray-400" />
                              </Button>
                            )}
                            
                            {/* Botón Eliminar - Solo Admin */}
                            {canDeletePrestamo() ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDelete(prestamo.id)}
                                title="Eliminar préstamo"
                              >
                                <Trash2 className="h-4 w-4 text-red-600" />
                              </Button>
                            ) : null}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Paginación */}
              {data.total_pages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-gray-600">
                    Página {data.page} de {data.total_pages} ({data.total} total)
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(Math.max(1, page - 1))}
                      disabled={page === 1}
                    >
                      Anterior
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(Math.min(data.total_pages, page + 1))}
                      disabled={page === data.total_pages}
                    >
                      Siguiente
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
