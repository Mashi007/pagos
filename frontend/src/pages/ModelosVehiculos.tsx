import { useState, useEffect } from 'react'
import { Car, Plus, Search, Edit, Trash2, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { modeloVehiculoService, ModeloVehiculo } from '@/services/modeloVehiculoService'
import { toast } from 'sonner'

export function ModelosVehiculos() {
  const [modelos, setModelos] = useState<ModeloVehiculo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingModelo, setEditingModelo] = useState<ModeloVehiculo | null>(null)

  // Cargar modelos al montar el componente
  useEffect(() => {
    console.log('🔄 Cargando modelos de vehículos desde API...')
    cargarModelos()
  }, [])

  const cargarModelos = async () => {
    try {
      setLoading(true)
      setError(null)
      console.log('📡 Llamando a API: /api/v1/modelos-vehiculos')
      
      // CONECTAR CON DATOS REALES DE LA BASE DE DATOS
      const response = await modeloVehiculoService.listarModelos({ limit: 100 })
      console.log('✅ Respuesta API:', response)
      setModelos(response.items)
      
      // TEMPORAL: Si falla la API, usar datos mock
      // const mockData = {
      //   items: [
      //     { id: 1, modelo: "Toyota Corolla", activo: true, created_at: "2025-01-01T00:00:00Z" },
      //     { id: 2, modelo: "Nissan Versa", activo: true, created_at: "2025-01-01T00:00:00Z" },
      //     { id: 3, modelo: "Hyundai Tucson", activo: true, created_at: "2025-01-01T00:00:00Z" },
      //     { id: 4, modelo: "Ford F-150", activo: true, created_at: "2025-01-01T00:00:00Z" },
      //     { id: 5, modelo: "Chevrolet Spark", activo: false, created_at: "2025-01-01T00:00:00Z" }
      //   ],
      //   total: 5,
      //   page: 1,
      //   page_size: 100,
      //   total_pages: 1
      // }
      // console.log('✅ Usando datos mock temporalmente:', mockData)
      // setModelos(mockData.items)
    } catch (err) {
      console.error('❌ Error API:', err)
      setError('Error al cargar modelos de vehículos')
      toast.error('Error al cargar modelos de vehículos')
    } finally {
      setLoading(false)
    }
  }

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
      
      await modeloVehiculoService.eliminarModelo(id)
      toast.success('✅ Modelo eliminado PERMANENTEMENTE de la base de datos')
      cargarModelos() // Recargar lista
    } catch (err) {
      toast.error('❌ Error al eliminar modelo permanentemente')
      console.error('Error:', err)
    }
  }

  const handleToggleActivo = async (modelo: ModeloVehiculo) => {
    try {
      await modeloVehiculoService.actualizarModelo(modelo.id, {
        activo: !modelo.activo
      })
      toast.success(`Modelo ${modelo.activo ? 'desactivado' : 'activado'} exitosamente`)
      cargarModelos() // Recargar lista
    } catch (err) {
      toast.error('Error al cambiar estado del modelo')
      console.error('Error:', err)
    }
  }

  // Filtrar modelos por término de búsqueda
  const modelosFiltrados = modelos.filter(modelo =>
    modelo.nombre.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Modelos de Vehículos</h1>
          <p className="text-gray-500 mt-1">
            Catálogo de modelos disponibles para financiamiento
          </p>
        </div>
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Agregar Modelo
        </Button>
      </div>

      {/* Stats Dashboard */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Modelos</p>
                <p className="text-2xl font-bold">{modelos.length}</p>
                <p className="text-xs text-gray-400 mt-1">
                  {modelos.length > 0 ? `${((modelos.filter(m => m.activo).length / modelos.length) * 100).toFixed(1)}% activos` : 'Sin datos'}
                </p>
              </div>
              <Car className="w-8 h-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Activos</p>
                <p className="text-2xl font-bold text-green-600">
                  {modelos.filter(m => m.activo).length}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Disponibles para financiamiento
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-600" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Inactivos</p>
                <p className="text-2xl font-bold text-red-600">
                  {modelos.filter(m => !m.activo).length}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  No disponibles temporalmente
                </p>
              </div>
              <XCircle className="w-8 h-8 text-red-600" />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Último Mes</p>
                <p className="text-2xl font-bold text-blue-600">
                  {modelos.filter(m => {
                    const fechaCreacion = new Date(m.created_at)
                    const haceUnMes = new Date()
                    haceUnMes.setMonth(haceUnMes.getMonth() - 1)
                    return fechaCreacion >= haceUnMes
                  }).length}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Modelos agregados
                </p>
              </div>
              <Plus className="w-8 h-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Resumen de Datos */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Car className="w-5 h-5 mr-2" />
            Resumen de Datos
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <h4 className="font-medium text-gray-900">Distribución por Estado</h4>
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-green-600">Activos</span>
                  <span className="font-medium">{modelos.filter(m => m.activo).length}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-red-600">Inactivos</span>
                  <span className="font-medium">{modelos.filter(m => !m.activo).length}</span>
                </div>
              </div>
            </div>
            
            <div className="space-y-2">
              <h4 className="font-medium text-gray-900">Actividad Reciente</h4>
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Última semana</span>
                  <span className="font-medium">
                    {modelos.filter(m => {
                      const fechaCreacion = new Date(m.created_at)
                      const haceUnaSemana = new Date()
                      haceUnaSemana.setDate(haceUnaSemana.getDate() - 7)
                      return fechaCreacion >= haceUnaSemana
                    }).length}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Último mes</span>
                  <span className="font-medium">
                    {modelos.filter(m => {
                      const fechaCreacion = new Date(m.created_at)
                      const haceUnMes = new Date()
                      haceUnMes.setMonth(haceUnMes.getMonth() - 1)
                      return fechaCreacion >= haceUnMes
                    }).length}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="space-y-2">
              <h4 className="font-medium text-gray-900">Estadísticas</h4>
              <div className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Tasa de activación</span>
                  <span className="font-medium text-green-600">
                    {modelos.length > 0 ? `${((modelos.filter(m => m.activo).length / modelos.length) * 100).toFixed(1)}%` : '0%'}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Promedio por mes</span>
                  <span className="font-medium">
                    {modelos.length > 0 ? Math.round(modelos.length / Math.max(1, Math.ceil((new Date().getTime() - new Date(Math.min(...modelos.map(m => new Date(m.created_at).getTime()))).getTime()) / (1000 * 60 * 60 * 24 * 30)))) : 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Búsqueda */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Buscar modelo de vehículo..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Tabla */}
      <Card>
        <CardContent className="pt-6">
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
              {loading ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    <p className="text-gray-500">Cargando modelos de vehículos...</p>
                  </TableCell>
                </TableRow>
              ) : error ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-8">
                    <p className="text-red-500">{error}</p>
                    <Button onClick={cargarModelos} className="mt-2">
                      Reintentar
                    </Button>
                  </TableCell>
                </TableRow>
              ) : modelosFiltrados.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-8">
                    <p className="text-gray-500">No se encontraron modelos de vehículos</p>
                  </TableCell>
                </TableRow>
              ) : (
                modelosFiltrados.map((modelo) => (
                <TableRow key={modelo.id}>
                  <TableCell>
                    <div className="flex items-center space-x-3">
                      <Car className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="font-medium">{modelo.nombre}</p>
                        <p className="text-xs text-gray-500">ID: {modelo.id}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {modelo.activo ? (
                      <Badge className="bg-green-600">Activo</Badge>
                    ) : (
                      <Badge variant="outline">Inactivo</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-gray-500">
                      {new Date(modelo.created_at).toLocaleDateString('es-VE', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                      })}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => setEditingModelo(modelo)}
                        title="Editar modelo"
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleToggleActivo(modelo)}
                        title={modelo.activo ? "Desactivar" : "Activar"}
                      >
                        {modelo.activo ? (
                          <XCircle className="w-4 h-4 text-red-600" />
                        ) : (
                          <CheckCircle className="w-4 h-4 text-green-600" />
                        )}
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleEliminar(modelo.id)}
                        title="Eliminar modelo"
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Formulario de Crear/Editar Modelo */}
      {(showCreateForm || editingModelo) && (
        <CrearEditarModeloForm
          modelo={editingModelo}
          onClose={() => {
            setShowCreateForm(false)
            setEditingModelo(null)
          }}
          onSuccess={() => {
            cargarModelos()
            setShowCreateForm(false)
            setEditingModelo(null)
          }}
        />
      )}
    </div>
  )
}

// Componente para crear/editar modelo
interface CrearEditarModeloFormProps {
  modelo?: ModeloVehiculo | null
  onClose: () => void
  onSuccess: () => void
}

function CrearEditarModeloForm({ modelo, onClose, onSuccess }: CrearEditarModeloFormProps) {
  const [formData, setFormData] = useState({
    nombre: modelo?.nombre || ''
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.nombre.trim()) {
      toast.error('El modelo es obligatorio')
      return
    }

    try {
      setLoading(true)
      
      const data = {
        nombre: formData.nombre.trim()
      }

      if (modelo) {
        await modeloVehiculoService.actualizarModelo(modelo.id, data)
        toast.success('Modelo actualizado exitosamente')
      } else {
        await modeloVehiculoService.crearModelo(data)
        toast.success('Modelo creado exitosamente')
      }
      
      onSuccess()
    } catch (err) {
      toast.error(modelo ? 'Error al actualizar modelo' : 'Error al crear modelo')
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <Card className="w-full max-w-md mx-4">
        <CardHeader>
          <CardTitle>
            {modelo ? 'Editar Modelo' : 'Nuevo Modelo'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Modelo *</label>
              <Input
                value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                placeholder="Nombre del modelo de vehículo"
                required
              />
            </div>
            
            <div className="flex justify-end space-x-2 pt-4">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    {modelo ? 'Actualizando...' : 'Creando...'}
                  </>
                ) : (
                  modelo ? 'Actualizar' : 'Crear'
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

