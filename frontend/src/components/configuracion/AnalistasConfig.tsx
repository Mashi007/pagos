// frontend/src/components/configuracion/AnalistasConfig.tsx
import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Users,
  Plus,
  Search,
  Edit,
  Trash2,
  UserCheck,
  UserX,
  Loader2,
  RefreshCw,
  Eye
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Analista, AnalistaCreate, AnalistaUpdate } from '@/services/analistaService'
import { useAnalistasActivos, useCreateAnalista, useUpdateAnalista, useDeleteAnalista } from '@/hooks/useAnalistas'
import toast from 'react-hot-toast'

export function AnalistasConfig() {
  const [searchTerm, setSearchTerm] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingAnalista, setEditingAnalista] = useState<Analista | null>(null)
  const [viewingAnalista, setViewingAnalista] = useState<Analista | null>(null)

  // Form state
  const [formData, setFormData] = useState<AnalistaCreate>({
    nombre: '',
    activo: true
  })

  // Usar hooks de React Query
  const { 
    data: analistas, 
    isLoading: loading, 
    error,
    refetch
  } = useAnalistasActivos()
  
  const createAnalistaMutation = useCreateAnalista()
  const updateAnalistaMutation = useUpdateAnalista()
  const deleteAnalistaMutation = useDeleteAnalista()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingAnalista) {
        await updateAnalistaMutation.mutateAsync({
          id: editingAnalista.id,
          data: formData
        })
      } else {
        await createAnalistaMutation.mutateAsync(formData)
      }
      
      resetForm()
    } catch (err) {
      console.error('Error al guardar analista:', err)
    }
  }

  const handleEdit = (analista: Analista) => {
    setEditingAnalista(analista)
    setFormData({
      nombre: analista.nombre,
      activo: analista.activo
    })
    setShowForm(true)
  }

  const handleView = (analista: Analista) => {
    setViewingAnalista(analista)
  }

  const handleDelete = async (id: number) => {
    try {
      const confirmar = window.confirm(
        '⚠️ ¿Estás seguro de que quieres ELIMINAR este analista?\n\n' +
        'Esta acción NO se puede deshacer.'
      )
      
      if (!confirmar) {
        return
      }
      
      await deleteAnalistaMutation.mutateAsync(id)
    } catch (err) {
      console.error('Error al eliminar analista:', err)
    }
  }

  const resetForm = () => {
    setFormData({
      nombre: '',
      activo: true
    })
    setEditingAnalista(null)
    setShowForm(false)
  }

  const handleRefresh = () => {
    refetch()
  }

  // Filtrar analistas por término de búsqueda
  const filteredAnalistas = analistas?.filter(analista =>
    analista.nombre.toLowerCase().includes(searchTerm.toLowerCase())
  ) || []

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Cargando analistas...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-red-500 mb-4">Error al cargar analistas</p>
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
          <h2 className="text-2xl font-bold tracking-tight">Configuración de Analistas</h2>
          <p className="text-muted-foreground">
            Gestiona los analistas del sistema
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={handleRefresh} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
          <Button onClick={() => setShowForm(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Nuevo Analista
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Analistas</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analistas?.length || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Activos</CardTitle>
            <UserCheck className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {analistas?.filter(a => a.activo).length || 0}
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
              {analistas?.filter(a => !a.activo).length || 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Mostrados</CardTitle>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{filteredAnalistas.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card>
        <CardHeader>
          <CardTitle>Buscar Analistas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar por nombre..."
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
              {editingAnalista ? 'Editar Analista' : 'Nuevo Analista'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Nombre Completo
                </label>
                <Input
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Ingrese el nombre completo del analista"
                  required
                />
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
                  Analista activo
                </label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Button type="submit" disabled={createAnalistaMutation.isPending || updateAnalistaMutation.isPending}>
                  {editingAnalista ? 'Actualizar' : 'Crear'} Analista
                </Button>
                <Button type="button" variant="outline" onClick={resetForm}>
                  Cancelar
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Analistas Table */}
      <Card>
        <CardHeader>
          <CardTitle>Lista de Analistas</CardTitle>
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
              {filteredAnalistas.map((analista) => (
                <TableRow key={analista.id}>
                  <TableCell className="font-medium">{analista.id}</TableCell>
                  <TableCell>{analista.nombre}</TableCell>
                  <TableCell>
                    <Badge variant={analista.activo ? "default" : "secondary"}>
                      {analista.activo ? "Activo" : "Inactivo"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {analista.created_at ? new Date(analista.created_at).toLocaleDateString() : 'N/A'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleView(analista)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEdit(analista)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDelete(analista.id)}
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
          
          {filteredAnalistas.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              {searchTerm ? 'No se encontraron analistas con ese nombre' : 'No hay analistas disponibles'}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}