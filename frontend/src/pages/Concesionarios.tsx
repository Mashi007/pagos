import { useState, useEffect } from 'react'
import { Building, Plus, Search, Edit, Trash2, MapPin, Phone, Mail, User, Loader2, UserCheck, UserX, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { concesionarioService, Concesionario } from '@/services/concesionarioService'
import { toast } from 'sonner'

export function Concesionarios() {
  const [concesionarios, setConcesionarios] = useState<Concesionario[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingConcesionario, setEditingConcesionario] = useState<Concesionario | null>(null)

  // Cargar concesionarios al montar el componente
  useEffect(() => {
    cargarConcesionarios()
  }, [])

  const cargarConcesionarios = async () => {
    try {
      setLoading(true)
      setError(null)
      console.log('🔄 Actualizando concesionarios...')
      console.log('📡 Llamando a API: /api/v1/concesionarios')
      
      const response = await concesionarioService.listarConcesionarios({ limit: 100 })
      console.log('✅ Respuesta API recibida:', response)
      console.log('📊 Total concesionarios:', response.total)
      console.log('📋 Items recibidos:', response.items?.length || 0)
      
      if (response.items && Array.isArray(response.items)) {
        setConcesionarios(response.items)
        console.log('✅ Concesionarios cargados exitosamente:', response.items.length)
      } else {
        console.warn('⚠️ Respuesta sin items válidos:', response)
        setConcesionarios([])
      }
    } catch (err) {
      console.error('❌ Error API:', err)
      setError('Error al cargar concesionarios')
      toast.error('Error al cargar concesionarios')
      setConcesionarios([])
    } finally {
      setLoading(false)
    }
  }

  const handleCreateConcesionario = async () => {
    try {
      await concesionarioService.crearConcesionario({})
      toast.success('Concesionario creado exitosamente')
      cargarConcesionarios()
      setShowCreateForm(false)
    } catch (err) {
      toast.error('Error al crear concesionario')
      console.error('Error:', err)
    }
  }

  const handleDeleteConcesionario = async (id: number) => {
    if (!confirm('¿Estás seguro de que deseas eliminar este concesionario?')) {
      return
    }
    
    try {
      await concesionarioService.eliminarConcesionario(id)
      toast.success('Concesionario eliminado exitosamente')
      cargarConcesionarios()
    } catch (err) {
      toast.error('Error al eliminar concesionario')
      console.error('Error:', err)
    }
  }

  // Filtrar concesionarios por término de búsqueda
  const concesionariosFiltrados = concesionarios.filter(concesionario =>
    concesionario.id.toString().includes(searchTerm)
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Concesionarios</h1>
          <p className="text-gray-500 mt-1">
            Gestión de concesionarios y alianzas comerciales
          </p>
        </div>
        <div className="flex space-x-3">
          <Button
            variant="outline"
            onClick={cargarConcesionarios}
            disabled={loading}
            className="flex items-center"
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
          <Button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center"
          >
            <Plus className="mr-2 h-4 w-4" />
            Nuevo Concesionario
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <Building className="h-8 w-8 text-blue-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Concesionarios</p>
                <p className="text-2xl font-bold text-gray-900">{concesionarios.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <UserCheck className="h-8 w-8 text-green-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Activos</p>
                <p className="text-2xl font-bold text-gray-900">{concesionarios.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center">
              <UserX className="h-8 w-8 text-red-600" />
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Inactivos</p>
                <p className="text-2xl font-bold text-gray-900">0</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="p-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Buscar por ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <Card>
          <CardContent className="p-6">
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <p className="text-red-800">{error}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading */}
      {loading && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              <span className="ml-2 text-gray-600">Cargando concesionarios...</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Table */}
      {!loading && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Building className="mr-2 h-5 w-5" />
              Lista de Concesionarios ({concesionariosFiltrados.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {concesionariosFiltrados.map((concesionario) => (
                  <TableRow key={concesionario.id}>
                    <TableCell className="font-medium">
                      Concesionario #{concesionario.id}
                    </TableCell>
                    <TableCell>
                      <Badge variant="default" className="bg-green-100 text-green-800">
                        Activo
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setEditingConcesionario(concesionario)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeleteConcesionario(concesionario.id)}
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
          </CardContent>
        </Card>
      )}

      {/* Create Form Modal */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Plus className="mr-2 h-5 w-5" />
              Nuevo Concesionario
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="text-center py-8">
                <Building className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600 mb-4">
                  Los concesionarios solo tienen ID. ¿Crear nuevo concesionario?
                </p>
              </div>
              <div className="flex justify-end space-x-2">
                <Button
                  variant="outline"
                  onClick={() => setShowCreateForm(false)}
                >
                  Cancelar
                </Button>
                <Button onClick={handleCreateConcesionario}>
                  Crear Concesionario
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Edit Modal */}
      {editingConcesionario && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Edit className="mr-2 h-5 w-5" />
              Editar Concesionario #{editingConcesionario.id}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="text-center py-8">
                <Building className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600 mb-4">
                  Los concesionarios solo tienen ID. ¿Actualizar concesionario?
                </p>
              </div>
              <div className="flex justify-end space-x-2">
                <Button
                  variant="outline"
                  onClick={() => setEditingConcesionario(null)}
                >
                  Cancelar
                </Button>
                <Button onClick={() => setEditingConcesionario(null)}>
                  Actualizar
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}