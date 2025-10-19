import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Car,
  Plus,
  Edit,
  Trash2,
  Search,
  CheckCircle,
  XCircle,
  Save,
  X,
  Eye,
  RefreshCw,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { modeloVehiculoService, type ModeloVehiculo, type ModeloVehiculoCreate } from '@/services/modeloVehiculoService'

export function ModelosVehiculosConfig() {
  const [modelos, setModelos] = useState<ModeloVehiculo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingModelo, setEditingModelo] = useState<ModeloVehiculo | null>(null)
  const [viewingModelo, setViewingModelo] = useState<ModeloVehiculo | null>(null)

  // Form state
  const [formData, setFormData] = useState<ModeloVehiculoCreate>({
    modelo: '',  // ✅ CORREGIDO: campo 'modelo', no 'nombre'
    activo: true
  })

  useEffect(() => {
    loadModelos()
  }, [])

  const loadModelos = async () => {
    try {
      setLoading(true)
      const data = await modeloVehiculoService.listarModelosActivos()
      setModelos(data)
    } catch (err: any) {
      console.error('Error al cargar modelos:', err)
      if (err.response?.status === 503) {
        setError('Servicio temporalmente no disponible. Intenta nuevamente.')
      } else if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        setError('Error de conexión. Verifica que el servidor esté funcionando.')
      } else {
        setError('No se pudieron cargar los modelos de vehículos.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setError(null) // Limpiar errores previos
      
      if (editingModelo) {
        await modeloVehiculoService.actualizarModelo(editingModelo.id, formData)
      } else {
        await modeloVehiculoService.crearModelo(formData)
      }
      
      // Recargar la lista de modelos para actualizar la tabla
      await loadModelos()
      resetForm()
    } catch (err) {
      console.error('Error al guardar modelo:', err)
      setError('Error al guardar el modelo de vehículo.')
    }
  }

  const handleView = (modelo: ModeloVehiculo) => {
    setViewingModelo(modelo)
  }

  const handleEdit = (modelo: ModeloVehiculo) => {
    setEditingModelo(modelo)
    setFormData({
      modelo: modelo.modelo,  // ✅ CORREGIDO: campo 'modelo', no 'nombre'
      activo: modelo.activo
    })
    setShowForm(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de que deseas eliminar este modelo de vehículo?')) {
      return
    }
    
    try {
      await modeloVehiculoService.eliminarModelo(id)
      await loadModelos()
    } catch (err) {
      console.error('Error al eliminar modelo:', err)
      setError('Error al eliminar el modelo de vehículo.')
    }
  }

  const resetForm = () => {
    setFormData({
      modelo: '',  // ✅ CORREGIDO: campo 'modelo', no 'nombre'
      activo: true
    })
    setEditingModelo(null)
    setViewingModelo(null)
    setShowForm(false)
  }

  const filteredModelos = modelos.filter(modelo =>
    (modelo.modelo && modelo.modelo.toLowerCase().includes(searchTerm.toLowerCase()))  // ✅ CORREGIDO: campo 'modelo', no 'nombre'
  )

  if (loading) {
    return <div className="text-center py-8"><LoadingSpinner size="lg" /></div>
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-2xl font-bold flex items-center">
            <Car className="mr-2 h-6 w-6" />
            Gestión de Modelos de Vehículos
          </h3>
          <p className="text-gray-600 mt-1">
            Administra los modelos de vehículos disponibles en el sistema
          </p>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Nuevo Modelo
        </Button>
      </div>

      {/* Formulario */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>
              {editingModelo ? 'Editar Modelo' : 'Nuevo Modelo'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <label className="text-sm font-medium">Modelo del Vehículo *</label>
                  <Input
                    value={formData.modelo}  // ✅ CORREGIDO: campo 'modelo', no 'nombre'
                    onChange={(e) => setFormData({ ...formData, modelo: e.target.value })}  // ✅ CORREGIDO: campo 'modelo', no 'nombre'
                    placeholder="Nombre del modelo"
                    required
                  />
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="activo"
                  checked={formData.activo}
                  onChange={(e) => setFormData({ ...formData, activo: e.target.checked })}
                  className="rounded"
                />
                <label htmlFor="activo" className="text-sm font-medium">
                  Activo
                </label>
              </div>
              <div className="flex justify-end space-x-2">
                <Button type="button" variant="outline" onClick={resetForm}>
                  <X className="mr-2 h-4 w-4" />
                  Cancelar
                </Button>
                <Button type="submit">
                  <Save className="mr-2 h-4 w-4" />
                  {editingModelo ? 'Actualizar' : 'Crear'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Modal de Visualización */}
      {viewingModelo && (
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center">
                <Eye className="mr-2 h-5 w-5 text-blue-600" />
                Detalles del Modelo
              </CardTitle>
              <Button variant="outline" size="sm" onClick={() => setViewingModelo(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Modelo del Vehículo</label>
                <p className="text-lg font-semibold">{viewingModelo.nombre}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Estado</label>
                <div className="mt-1">
                  <Badge variant={viewingModelo.activo ? 'default' : 'destructive'}>
                    {viewingModelo.activo ? (
                      <>
                        <CheckCircle className="mr-1 h-3 w-3" />
                        Activo
                      </>
                    ) : (
                      <>
                        <XCircle className="mr-1 h-3 w-3" />
                        Inactivo
                      </>
                    )}
                  </Badge>
                </div>
              </div>
            </div>
            <div className="flex justify-end space-x-2 mt-6">
              <Button variant="outline" onClick={() => setViewingModelo(null)}>
                Cerrar
              </Button>
              <Button onClick={() => {
                handleEdit(viewingModelo)
                setViewingModelo(null)
              }}>
                <Edit className="mr-2 h-4 w-4" />
                Editar
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Búsqueda */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center space-x-2">
            <Search className="h-4 w-4 text-gray-400" />
            <Input
              placeholder="Buscar modelos..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1"
            />
          </div>
        </CardContent>
      </Card>

      {/* Lista de Modelos */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Modelo del Vehículo</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredModelos.map((modelo) => (
                  <TableRow key={modelo.id}>
                    <TableCell>
                      <div className="font-medium">{modelo.modelo}</div>  {/* ✅ CORREGIDO: campo 'modelo', no 'nombre' */}
                    </TableCell>
                    <TableCell>
                      <Badge variant={modelo.activo ? 'default' : 'destructive'}>
                        {modelo.activo ? (
                          <>
                            <CheckCircle className="mr-1 h-3 w-3" />
                            Activo
                          </>
                        ) : (
                          <>
                            <XCircle className="mr-1 h-3 w-3" />
                            Inactivo
                          </>
                        )}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end space-x-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleView(modelo)}
                          title="Ver detalles"
                          className="text-blue-600 hover:text-blue-700"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(modelo)}
                          title="Editar modelo"
                          className="text-green-600 hover:text-green-700"
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(modelo.id)}
                          title="Eliminar modelo"
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
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

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          <div className="flex items-center justify-between">
            <span>{error}</span>
            <Button 
              onClick={loadModelos}
              variant="outline" 
              size="sm"
              className="ml-4"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Reintentar
            </Button>
          </div>
        </div>
      )}
    </motion.div>
  )
}
