import { useState, useEffect } from 'react'
import { Building, Plus, Search, Edit, Trash2, Save, X, Loader2, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { concesionarioService, Concesionario, ConcesionarioCreate } from '@/services/concesionarioService'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { toast } from 'sonner'

export function ConcesionariosConfig() {
  const [concesionarios, setConcesionarios] = useState<Concesionario[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingConcesionario, setEditingConcesionario] = useState<Concesionario | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Form state
  const [formData, setFormData] = useState<ConcesionarioCreate>({
    nombre: '',
    activo: true
  })

  // Función para obtener fecha de hoy
  const getTodayDate = () => {
    const today = new Date()
    return today.toISOString().split('T')[0]
  }

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
    setIsSubmitting(true)
    try {
      if (editingConcesionario) {
        await concesionarioService.actualizarConcesionario(editingConcesionario.id, formData)
        toast.success('✅ Concesionario actualizado exitosamente')
      } else {
        await concesionarioService.crearConcesionario(formData)
        toast.success('✅ Concesionario creado exitosamente')
      }
      await loadConcesionarios()
      resetForm()
    } catch (err) {
      console.error('Error al guardar concesionario:', err)
      toast.error('❌ Error al guardar concesionario')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEdit = (concesionario: Concesionario) => {
    setEditingConcesionario(concesionario)
    setFormData({
      nombre: concesionario.nombre,
      activo: concesionario.activo
    })
    setShowForm(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('⚠️ ¿Estás seguro de que deseas eliminar este concesionario?\n\nEsta acción NO se puede deshacer.')) {
      return
    }
    
    try {
      await concesionarioService.eliminarConcesionario(id)
      await loadConcesionarios()
      toast.success('✅ Concesionario eliminado exitosamente')
    } catch (err) {
      console.error('Error al eliminar concesionario:', err)
      toast.error('❌ Error al eliminar concesionario')
    }
  }

  const resetForm = () => {
    setFormData({
      nombre: '',
      activo: true
    })
    setEditingConcesionario(null)
    setShowForm(false)
  }

  const handleRefresh = () => {
    loadConcesionarios()
  }

  const filteredConcesionarios = concesionarios.filter(concesionario =>
    concesionario.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
    concesionario.id.toString().includes(searchTerm)
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Cargando concesionarios...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Configuración de Concesionarios</h2>
          <p className="text-muted-foreground">
            Gestiona los concesionarios del sistema
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={handleRefresh} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
          <Button onClick={() => setShowForm(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Nuevo Concesionario
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Concesionarios</CardTitle>
            <Building className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{concesionarios.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Activos</CardTitle>
            <Building className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {concesionarios.filter(c => c.activo).length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Inactivos</CardTitle>
            <Building className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {concesionarios.filter(c => !c.activo).length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mostrados</CardTitle>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{filteredConcesionarios.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card>
        <CardHeader>
          <CardTitle>Buscar Concesionarios</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por nombre o ID..."
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
              {editingConcesionario ? 'Editar Concesionario' : 'Nuevo Concesionario'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Nombre del Concesionario *
                </label>
                <Input
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Ingrese el nombre del concesionario"
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
                      {editingConcesionario ? 'Actualizar' : 'Crear'} Concesionario
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

      {/* Concesionarios Table */}
      <Card>
        <CardHeader>
          <CardTitle>Lista de Concesionarios</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Nombre</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Fecha Creación</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredConcesionarios.map((concesionario) => (
                <TableRow key={concesionario.id}>
                  <TableCell className="font-medium">{concesionario.id}</TableCell>
                  <TableCell>{concesionario.nombre}</TableCell>
                  <TableCell>
                    <Badge variant={concesionario.activo ? "default" : "secondary"}>
                      {concesionario.activo ? "Activo" : "Inactivo"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {concesionario.created_at 
                      ? new Date(concesionario.created_at).toLocaleDateString('es-VE', { 
                          year: 'numeric', 
                          month: '2-digit', 
                          day: '2-digit' 
                        })
                      : '01/10/2025'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(concesionario)}
                        title="Editar concesionario"
                        disabled={isSubmitting}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDelete(concesionario.id)}
                        className="text-red-600 hover:text-red-700"
                        title="Eliminar concesionario"
                        disabled={isSubmitting}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          
          {filteredConcesionarios.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              {searchTerm ? 'No se encontraron concesionarios con ese criterio' : 'No hay concesionarios disponibles'}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}