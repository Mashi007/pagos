// frontend/src/pages/ModelosVehiculos.tsx
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Car,
  Plus,
  Search,
  Edit,
  Trash2,
  UserCheck,
  UserX,
  Loader2,
  RefreshCw
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ModeloVehiculo, ModeloVehiculoUpdate, ModeloVehiculoCreate } from '@/services/modeloVehiculoService'
import { configuracionGeneralService } from '@/services/configuracionGeneralService'
import { useModelosVehiculos, useDeleteModeloVehiculo, useUpdateModeloVehiculo, useCreateModeloVehiculo } from '@/hooks/useModelosVehiculos'
import toast from 'react-hot-toast'

export function ModelosVehiculos() {
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingModelo, setEditingModelo] = useState<ModeloVehiculo | null>(null)
  const [formData, setFormData] = useState<ModeloVehiculoCreate>({
    modelo: '',
    activo: true,
    precio: 0
  })
  const [moneda, setMoneda] = useState<string>('VES')
  const [archivoExcel, setArchivoExcel] = useState<File | null>(null)
  const [validationError, setValidationError] = useState<string>('')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  // Usar hooks de React Query
  const { 
    data: modelosData, 
    isLoading: loading, 
    error,
    refetch
  } = useModelosVehiculos({ limit: 1000 })
  
  const deleteModeloMutation = useDeleteModeloVehiculo()
  const updateModeloMutation = useUpdateModeloVehiculo()
  const createModeloMutation = useCreateModeloVehiculo()
  
  const modelos = modelosData?.items || []

  useEffect(() => {
    (async () => {
      try {
        const cfg = await configuracionGeneralService.obtenerConfiguracionGeneral()
        setMoneda(cfg.moneda)
      } catch {}
    })()
  }, [])

  const handleEliminar = async (id: number) => {
    try {
      // Confirmar eliminación permanente
      const confirmar = window.confirm(
        '⚠️ ¿Estás seguro de que quieres ELIMINAR PERMANENTEMENTE este modelo?\n\n' +
        'Esta acción NO se puede deshacer y el modelo será borrado completamente de la base de datos.'
      )
      
      if (!confirmar) {
        return
      }
      
      await deleteModeloMutation.mutateAsync(id)
    } catch (err) {
      console.error('Error:', err)
    }
  }

  const validateModelo = (modelo: string): string => {
    if (!modelo.trim()) {
      return 'El modelo es requerido'
    }
    
    return ''
  }

  const formatModelo = (modelo: string): string => {
    // Limpiar espacios extras
    const modeloLimpio = modelo.trim().replace(/\s+/g, ' ')
    
    // Capitalizar primera letra de cada palabra
    return modeloLimpio.split(' ').map(word => {
      if (word.length === 0) return word
      return word[0].toUpperCase() + word.slice(1).toLowerCase()
    }).join(' ')
  }

  const handleEdit = (modelo: ModeloVehiculo) => {
    setEditingModelo(modelo)
    setFormData({
      modelo: modelo.modelo,
      activo: modelo.activo,
      precio: Number(modelo.precio || 0)
    })
    setValidationError('')
    setShowCreateForm(true)
  }

  const handleCreateOrUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validar modelo (solo que no esté vacío)
    const error = validateModelo(formData.modelo)
    if (error) {
      setValidationError(error)
      return
    }
    
    setValidationError('')
    
    try {
      // Formatear modelo (capitalizar primera letra de cada palabra)
      const modeloFormateado = formatModelo(formData.modelo)
      
      if (editingModelo) {
        // Al editar, mantener el estado actual
        await updateModeloMutation.mutateAsync({
          id: editingModelo.id,
          data: { ...formData, modelo: modeloFormateado }
        })
        toast.success('✅ Modelo actualizado exitosamente')
      } else {
        // Al crear, ya tiene activo: true por defecto
        await createModeloMutation.mutateAsync({ ...formData, modelo: modeloFormateado })
        toast.success('✅ Modelo creado exitosamente')
      }
      resetForm()
      refetch()
    } catch (err) {
      console.error('Error:', err)
      toast.error('❌ Error al guardar modelo')
    }
  }

  const resetForm = () => {
    setFormData({
      modelo: '',
      activo: true,
      precio: 0
    })
    setValidationError('')
    setEditingModelo(null)
    setShowCreateForm(false)
  }

  const handleRefresh = () => {
    refetch()
  }

  // Filtrar modelos por término de búsqueda
  const filteredModelos = (modelos || []).filter(modelo =>
    modelo.modelo.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Paginación
  const totalPages = Math.ceil(filteredModelos.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const paginatedModelos = filteredModelos.slice(startIndex, endIndex)

  // Resetear a página 1 cuando cambia el filtro de búsqueda
  useEffect(() => {
    setCurrentPage(1)
  }, [searchTerm])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Cargando modelos de vehículos...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-red-500 mb-4">Error al cargar modelos de vehículos</p>
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Reintentar
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Modelos de Vehículos</h1>
          <p className="text-muted-foreground">
            Gestiona los modelos de vehículos del sistema
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={() => {
            setEditingModelo(null)
            setFormData({ modelo: '', activo: true, precio: 0 })
            setValidationError('')
            setShowCreateForm(true)
          }}>
            <Plus className="h-4 w-4 mr-2" />
            Nuevo Modelo
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Modelos</CardTitle>
            <Car className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{modelos?.length || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Activos</CardTitle>
            <UserCheck className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {(modelos || []).filter(m => m.activo === true || m.activo === 1).length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Inactivos</CardTitle>
            <UserX className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {(modelos || []).filter(m => m.activo === false || m.activo === 2 || m.activo === 0).length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mostrados</CardTitle>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{filteredModelos.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="p-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Buscar por modelo..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Modelos Table */}
      <Card>
        <CardHeader>
          <CardTitle>Lista de Modelos de Vehículos</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Modelo</TableHead>
                <TableHead>Precio ({moneda})</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Fecha Creación</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedModelos.map((modelo) => (
                <TableRow key={modelo.id}>
                  <TableCell className="font-medium">{modelo.id}</TableCell>
                  <TableCell>{modelo.modelo}</TableCell>
                  <TableCell>{modelo.precio != null ? Number(modelo.precio).toLocaleString('es-VE', { minimumFractionDigits: 2 }) : '-'}</TableCell>
                  <TableCell>
                    <Badge variant={(modelo.activo === true || modelo.activo === 1) ? "default" : "secondary"}>
                      {(modelo.activo === true || modelo.activo === 1) ? "Activo" : "Inactivo"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {modelo.created_at 
                      ? (() => {
                          const date = new Date(modelo.created_at)
                          return isNaN(date.getTime()) 
                            ? '01/10/2025' 
                            : date.toLocaleDateString('es-VE', { 
                                year: 'numeric', 
                                month: '2-digit', 
                                day: '2-digit' 
                              })
                        })()
                      : '01/10/2025'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(modelo)}
                        title="Editar modelo"
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEliminar(modelo.id)}
                        className="text-red-600 hover:text-red-700"
                        title="Eliminar modelo"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          
          {filteredModelos.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              {searchTerm ? 'No se encontraron modelos con ese nombre' : 'No hay modelos disponibles'}
            </div>
          )}

          {/* Paginación */}
          {filteredModelos.length > itemsPerPage && (
            <div className="flex items-center justify-between px-2 py-4 border-t">
              <div className="text-sm text-gray-500">
                Mostrando {startIndex + 1} a {Math.min(endIndex, filteredModelos.length)} de {filteredModelos.length} modelos
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                >
                  Anterior
                </Button>
                <div className="flex items-center space-x-1">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                    <Button
                      key={page}
                      variant={currentPage === page ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCurrentPage(page)}
                      className={currentPage === page ? 'bg-blue-600 text-white' : ''}
                    >
                      {page}
                    </Button>
                  ))}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Form Modal */}
      {showCreateForm && (
        <div 
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
          onClick={resetForm}
        >
          <div 
            className="bg-white rounded-lg shadow-xl max-w-md w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <Card>
              <CardHeader>
                <CardTitle>
                  {editingModelo ? 'Editar Modelo de Vehículo' : 'Nuevo Modelo de Vehículo'}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateOrUpdate} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Nombre del Modelo *
                    </label>
                    <Input
                      value={formData.modelo}
                      onChange={(e) => {
                        setFormData({ ...formData, modelo: e.target.value })
                        setValidationError('') // Limpiar error al escribir
                      }}
                      placeholder="Ingrese nombre del modelo"
                      required
                      autoFocus
                      className={validationError ? 'border-red-500' : ''}
                    />
                    {validationError && (
                      <p className="text-xs text-red-500 mt-1">
                        {validationError}
                      </p>
                    )}
                    {!editingModelo && !validationError && (
                      <p className="text-xs text-gray-500 mt-1">
                        Ejemplo: Toyota Corolla
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Precio ({moneda}) *
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      min={0}
                      value={formData.precio}
                      onChange={(e) => setFormData({ ...formData, precio: Number(e.target.value) })}
                      placeholder={`0.00`}
                      required
                    />
                  </div>

                  {editingModelo && (
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Estado *
                      </label>
                      <select
                        value={formData.activo ? 'ACTIVO' : 'INACTIVO'}
                        onChange={(e) => setFormData({ ...formData, activo: e.target.value === 'ACTIVO' })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        required
                      >
                        <option value="ACTIVO">Activo</option>
                        <option value="INACTIVO">Inactivo</option>
                      </select>
                    </div>
                  )}

                  <div className="flex items-center space-x-2 pt-4">
                    <Button 
                      type="submit" 
                      disabled={createModeloMutation.isPending || updateModeloMutation.isPending}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      {createModeloMutation.isPending || updateModeloMutation.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Guardando...
                        </>
                      ) : (
                        <>
                          <Edit className="h-4 w-4 mr-2" />
                          {editingModelo ? 'Actualizar' : 'Crear'} Modelo
                        </>
                      )}
                    </Button>
                    <Button type="button" variant="outline" onClick={resetForm}>
                      Cancelar
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Importación desde Excel */}
      <Card>
        <CardHeader>
          <CardTitle>Importar Modelos y Precios (Excel)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="text-sm text-gray-600">Columnas requeridas: <b>modelo</b>, <b>precio</b>. Opcional: <b>fecha_actualizacion</b>.</div>
          <input type="file" accept=".xlsx,.xls" onChange={(e) => setArchivoExcel(e.target.files?.[0] || null)} />
          <div className="flex items-center gap-2">
            <Button
              disabled={!archivoExcel}
              onClick={async () => {
                if (!archivoExcel) return
                try {
                  const svc = (await import('@/services/modeloVehiculoService')).modeloVehiculoService
                  const res = await svc.importarDesdeExcel(archivoExcel)
                  toast.success(`Importado: ${res.creados} creados, ${res.actualizados} actualizados`)
                  setArchivoExcel(null)
                  await refetch()
                } catch (err: any) {
                  toast.error(err?.response?.data?.detail || 'Error al importar')
                }
              }}
            >
              Cargar Excel
            </Button>
            <div className="text-xs text-gray-500">Moneda del sistema: {moneda}</div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
