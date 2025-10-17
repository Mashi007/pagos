import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Users,
  Plus,
  Edit,
  Trash2,
  Search,
  Filter,
  CheckCircle,
  XCircle,
  Save,
  X,
  Mail,
  Phone,
  Eye,
  RefreshCw,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { analistaService, type Analista, type AnalistaCreate } from '@/services/analistaService'

const ESPECIALIDADES = [
  'Vehículos Nuevos',
  'Vehículos Usados',
  'Vehículos Comerciales',
  'Motocicletas',
  'Camiones',
  'Otros'
]

export function AnalistasConfig() {
  const [analistaes, setAnalistaes] = useState<Analista[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingAnalista, setEditingAnalista] = useState<Analista | null>(null)
  const [viewingAnalista, setViewingAnalista] = useState<Analista | null>(null)

  // Form state
  const [formData, setFormData] = useState<AnalistaCreate>({
    nombre: '',
    activo: true
  })

  useEffect(() => {
    loadAnalistaes()
  }, [])

  const loadAnalistaes = async () => {
    try {
      setLoading(true)
      const data = await analistaService.listarAnalistasActivos()
      setAnalistaes(data)
    } catch (err: any) {
      console.error('Error al cargar analistaes:', err)
      if (err.response?.status === 503) {
        setError('Servicio temporalmente no disponible. Intenta nuevamente.')
      } else if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        setError('Error de conexión. Verifica que el servidor esté funcionando.')
      } else {
        setError('No se pudieron cargar los analistaes.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setError(null) // Limpiar errores previos
      
      if (editingAnalista) {
        await analistaService.actualizarAnalista(editingAnalista.id, formData)
      } else {
        await analistaService.crearAnalista(formData)
      }
      
      // Recargar la lista de analistaes para actualizar la tabla
      await loadAnalistaes()
      resetForm()
    } catch (err) {
      console.error('Error al guardar analista:', err)
      setError('Error al guardar el analista.')
    }
  }

  const handleView = (analista: Analista) => {
    setViewingAnalista(analista)
  }

  const handleEdit = (analista: Analista) => {
    setEditingAnalista(analista)
    setFormData({
      nombre: analista.nombre,
      activo: analista.activo
    })
    setShowForm(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de que deseas eliminar este analista?')) {
      return
    }
    
    try {
      await analistaService.eliminarAnalista(id)
      await loadAnalistaes()
    } catch (err) {
      console.error('Error al eliminar analista:', err)
      setError('Error al eliminar el analista.')
    }
  }

  const resetForm = () => {
    setFormData({
      nombre: '',
      activo: true
    })
    setEditingAnalista(null)
    setViewingAnalista(null)
    setShowForm(false)
  }

  const filteredAnalistaes = analistaes.filter(analista =>
    analista.nombre_completo.toLowerCase().includes(searchTerm.toLowerCase()) ||
    analista.nombre.toLowerCase().includes(searchTerm.toLowerCase())
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
            <Users className="mr-2 h-6 w-6" />
            Gestión de Analistaes
          </h3>
          <p className="text-gray-600 mt-1">
            Administra los analistaes comerciales del sistema
          </p>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Nuevo Analista
        </Button>
      </div>

      {/* Formulario */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>
              {editingAnalista ? 'Editar Analista' : 'Nuevo Analista'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <label className="text-sm font-medium">Nombre del Analista *</label>
                  <Input
                    value={formData.nombre}
                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                    placeholder="Nombre del analista"
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
                  {editingAnalista ? 'Actualizar' : 'Crear'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Modal de Visualización */}
      {viewingAnalista && (
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center">
                <Eye className="mr-2 h-5 w-5 text-blue-600" />
                Detalles del Analista
              </CardTitle>
              <Button variant="outline" size="sm" onClick={() => setViewingAnalista(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Nombre del Analista</label>
                <p className="text-lg font-semibold">{viewingAnalista.nombre_completo}</p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-500">Estado</label>
                <div className="mt-1">
                  <Badge variant={viewingAnalista.activo ? 'default' : 'destructive'}>
                    {viewingAnalista.activo ? (
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
              <Button variant="outline" onClick={() => setViewingAnalista(null)}>
                Cerrar
              </Button>
              <Button onClick={() => {
                handleEdit(viewingAnalista)
                setViewingAnalista(null)
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
              placeholder="Buscar analistaes..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1"
            />
          </div>
        </CardContent>
      </Card>

      {/* Lista de Analistaes */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre del Analista</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAnalistaes.map((analista) => (
                  <TableRow key={analista.id}>
                    <TableCell>
                      <div className="font-medium">{analista.nombre_completo}</div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={analista.activo ? 'default' : 'destructive'}>
                        {analista.activo ? (
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
                          onClick={() => handleView(analista)}
                          title="Ver detalles"
                          className="text-blue-600 hover:text-blue-700"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(analista)}
                          title="Editar analista"
                          className="text-green-600 hover:text-green-700"
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(analista.id)}
                          title="Eliminar analista"
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
              onClick={loadAnalistaes}
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
