import { useState, useEffect } from 'react'
import { Building, Plus, Search, Edit, Trash2, Eye, Save, X, Loader2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { concesionarioService, Concesionario } from '@/services/concesionarioService'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { toast } from 'sonner'

export function ConcesionariosConfig() {
  const [concesionarios, setConcesionarios] = useState<Concesionario[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingConcesionario, setEditingConcesionario] = useState<Concesionario | null>(null)
  const [viewingConcesionario, setViewingConcesionario] = useState<Concesionario | null>(null)

  useEffect(() => {
    loadConcesionarios()
  }, [])

  const loadConcesionarios = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await concesionarioService.listarConcesionarios({ limit: 100 })
      setConcesionarios(response.items || [])
    } catch (err) {
      console.error('Error al cargar concesionarios:', err)
      setError('Error al cargar concesionarios')
      toast.error('Error al cargar concesionarios')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingConcesionario) {
        // Actualizar concesionario (solo id)
        await concesionarioService.actualizarConcesionario(editingConcesionario.id, {})
        toast.success('Concesionario actualizado exitosamente')
      } else {
        // Crear nuevo concesionario
        await concesionarioService.crearConcesionario({})
        toast.success('Concesionario creado exitosamente')
      }
      await loadConcesionarios()
      resetForm()
    } catch (err) {
      console.error('Error al guardar concesionario:', err)
      toast.error('Error al guardar concesionario')
    }
  }

  const handleView = (concesionario: Concesionario) => {
    setViewingConcesionario(concesionario)
  }

  const handleEdit = (concesionario: Concesionario) => {
    setEditingConcesionario(concesionario)
    setShowForm(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de que deseas eliminar este concesionario?')) {
      return
    }
    
    try {
      await concesionarioService.eliminarConcesionario(id)
      await loadConcesionarios()
      toast.success('Concesionario eliminado exitosamente')
    } catch (err) {
      console.error('Error al eliminar concesionario:', err)
      toast.error('Error al eliminar concesionario')
    }
  }

  const resetForm = () => {
    setEditingConcesionario(null)
    setViewingConcesionario(null)
    setShowForm(false)
  }

  const filteredConcesionarios = concesionarios.filter(concesionario =>
    concesionario.id.toString().includes(searchTerm)
  )

  if (loading) {
    return <div className="text-center py-8"><LoadingSpinner size="lg" /></div>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Concesionarios</h2>
          <p className="text-gray-600">Gestión de concesionarios del sistema</p>
        </div>
        <Button onClick={() => setShowForm(true)} className="flex items-center">
          <Plus className="mr-2 h-4 w-4" />
          Nuevo Concesionario
        </Button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
        <Input
          placeholder="Buscar por ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Building className="mr-2 h-5 w-5" />
            Lista de Concesionarios ({filteredConcesionarios.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredConcesionarios.map((concesionario) => (
                <TableRow key={concesionario.id}>
                  <TableCell className="font-medium">
                    Concesionario #{concesionario.id}
                  </TableCell>
                  <TableCell>
                    <div className="flex space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleView(concesionario)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(concesionario)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDelete(concesionario.id)}
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

      {/* Form Modal */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Save className="mr-2 h-5 w-5" />
              {editingConcesionario ? 'Editar Concesionario' : 'Nuevo Concesionario'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="text-center py-8">
                <p className="text-gray-600">
                  Los concesionarios solo tienen ID. {editingConcesionario ? 'Actualizar' : 'Crear'} concesionario?
                </p>
              </div>
              <div className="flex justify-end space-x-2">
                <Button type="button" variant="outline" onClick={resetForm}>
                  <X className="mr-2 h-4 w-4" />
                  Cancelar
                </Button>
                <Button type="submit">
                  <Save className="mr-2 h-4 w-4" />
                  {editingConcesionario ? 'Actualizar' : 'Crear'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* View Modal */}
      {viewingConcesionario && (
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle className="flex items-center">
                <Eye className="mr-2 h-5 w-5 text-blue-600" />
                Detalles del Concesionario
              </CardTitle>
              <Button variant="outline" size="sm" onClick={() => setViewingConcesionario(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-700">ID</label>
                <p className="text-lg font-semibold">Concesionario #{viewingConcesionario.id}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}