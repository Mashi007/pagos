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
  RefreshCw,
  Loader2,
  TrendingUp,
  TrendingDown,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { modeloVehiculoService, type ModeloVehiculo, type ModeloVehiculoCreate } from '@/services/modeloVehiculoService'
import { toast } from 'sonner'

export function ModelosVehiculosConfig() {
  const [modelos, setModelos] = useState<ModeloVehiculo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingModelo, setEditingModelo] = useState<ModeloVehiculo | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Form state
  const [formData, setFormData] = useState<ModeloVehiculoCreate>({
    modelo: '',
    activo: true
  })

  // Función para obtener fecha de hoy
  const getTodayDate = () => {
    const today = new Date()
    return today.toISOString().split('T')[0]
  }

  useEffect(() => {
    loadModelos()
  }, [])

  const loadModelos = async () => {
    try {
      setLoading(true)
      setError(null)
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
      toast.error('Error al cargar modelos de vehículos')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      setError(null)
      
      if (editingModelo) {
        await modeloVehiculoService.actualizarModelo(editingModelo.id, formData)
        toast.success('✅ Modelo actualizado exitosamente')
      } else {
        await modeloVehiculoService.crearModelo(formData)
        toast.success('✅ Modelo creado exitosamente')
      }
      
      await loadModelos()
      resetForm()
    } catch (err) {
      console.error('Error al guardar modelo:', err)
      setError('Error al guardar el modelo de vehículo.')
      toast.error('❌ Error al guardar modelo')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEdit = (modelo: ModeloVehiculo) => {
    setEditingModelo(modelo)
    setFormData({
      modelo: modelo.modelo,
      activo: modelo.activo
    })
    setShowForm(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('⚠️ ¿Estás seguro de que deseas eliminar este modelo de vehículo?\n\nEsta acción NO se puede deshacer.')) {
      return
    }
    
    try {
      await modeloVehiculoService.eliminarModelo(id)
      await loadModelos()
      toast.success('✅ Modelo eliminado exitosamente')
    } catch (err) {
      console.error('Error al eliminar modelo:', err)
      setError('Error al eliminar el modelo de vehículo.')
      toast.error('❌ Error al eliminar modelo')
    }
  }

  const resetForm = () => {
    setFormData({
      modelo: '',
      activo: true
    })
    setEditingModelo(null)
    setShowForm(false)
  }

  const handleRefresh = () => {
    loadModelos()
  }

  const filteredModelos = modelos.filter(modelo =>
    modelo.modelo.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Calcular KPIs
  const totalModelos = modelos.length
  const activosModelos = modelos.filter(m => m.activo).length
  const inactivosModelos = modelos.filter(m => !m.activo).length

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Cargando modelos...</span>
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Configuración de Modelos de Vehículos</h2>
          <p className="text-muted-foreground">
            Gestiona los modelos de vehículos del sistema
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={handleRefresh} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
          <Button onClick={() => setShowForm(true)}>
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
            <div className="text-2xl font-bold">{totalModelos}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Activos</CardTitle>
            <Car className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{activosModelos}</div>
            <p className="text-xs text-muted-foreground">
              <TrendingUp className="inline h-3 w-3 mr-1" />
              {totalModelos > 0 ? ((activosModelos / totalModelos) * 100).toFixed(1) : 0}% del total
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Inactivos</CardTitle>
            <Car className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{inactivosModelos}</div>
            <p className="text-xs text-muted-foreground">
              <TrendingDown className="inline h-3 w-3 mr-1" />
              {totalModelos > 0 ? ((inactivosModelos / totalModelos) * 100).toFixed(1) : 0}% del total
            </p>
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
        <CardHeader>
          <CardTitle>Buscar Modelos</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por nombre del modelo..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-sm"
            />
          </div>
        </CardContent>
      </Card>

      {/* Form */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>
              {editingModelo ? 'Editar Modelo' : 'Nuevo Modelo'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Modelo del Vehículo *
                </label>
                <Input
                  value={formData.modelo}
                  onChange={(e) => setFormData({ ...formData, modelo: e.target.value })}
                  placeholder="Ingrese el nombre del modelo"
                  required
                />
              </div>
              
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

              <div>
                <label className="block text-sm font-medium mb-2">
                  Fecha de Registro
                </label>
                <Input
                  type="date"
                  value={getTodayDate()}
                  disabled
                  className="bg-gray-100 text-gray-600"
                />
                <p className="text-xs text-gray-500 mt-1">
                  La fecha se establece automáticamente al día de hoy
                </p>
              </div>
              
              <div className="flex items-center space-x-2 pt-4">
                <Button 
                  type="submit" 
                  disabled={isSubmitting}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
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
      )}

      {/* Modelos Table */}
      <Card>
        <CardHeader>
          <CardTitle>Lista de Modelos de Vehículos</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Modelo de Vehículo</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Fecha Creación</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredModelos.map((modelo) => (
                <TableRow key={modelo.id}>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <Car className="h-4 w-4 text-gray-400" />
                      <div>
                        <div className="font-medium">{modelo.modelo}</div>
                        <div className="text-sm text-gray-500">ID: {modelo.id}</div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={modelo.activo ? "default" : "secondary"}>
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
                  <TableCell>
                    {modelo.created_at ? new Date(modelo.created_at).toLocaleDateString() : 'N/A'}
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
                        onClick={() => handleDelete(modelo.id)}
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
              {searchTerm ? 'No se encontraron modelos con ese criterio' : 'No hay modelos disponibles'}
            </div>
          )}
        </CardContent>
      </Card>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          <div className="flex items-center justify-between">
            <span>{error}</span>
            <Button 
              onClick={handleRefresh}
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