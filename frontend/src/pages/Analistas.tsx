// frontend/src/pages/Analistas.tsx
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
  RefreshCw
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Analista, AnalistaUpdate, AnalistaCreate } from '@/services/analistaService'
import { useAnalistas, useDeleteAnalista, useUpdateAnalista, useCreateAnalista } from '@/hooks/useAnalistas'
import toast from 'react-hot-toast'

export function Analistas() {
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingAnalista, setEditingAnalista] = useState<Analista | null>(null)
  const [formData, setFormData] = useState<AnalistaCreate>({
    nombre: ''
  })

  // Usar hooks de React Query
  const { 
    data: analistasData, 
    isLoading: loading, 
    error,
    refetch
  } = useAnalistas({ limit: 100 })
  
  const deleteAnalistaMutation = useDeleteAnalista()
  const updateAnalistaMutation = useUpdateAnalista()
  const createAnalistaMutation = useCreateAnalista()

  const analistas = analistasData?.items || []

  const handleEliminar = async (id: number) => {
    try {
      // Confirmar eliminación permanente
      const confirmar = window.confirm(
        '⚠️ ¿Estás seguro de que quieres ELIMINAR PERMANENTEMENTE este analista?\n\n' +
        'Esta acción NO se puede deshacer y el analista será borrado completamente de la base de datos.'
      )
      
      if (!confirmar) {
        return
      }
      
      await deleteAnalistaMutation.mutateAsync(id)
    } catch (err) {
      console.error('Error:', err)
    }
  }

  const handleEdit = (analista: Analista) => {
    setEditingAnalista(analista)
    setFormData({
      nombre: analista.nombre
    })
    setShowCreateForm(true)
  }

  const handleCreateOrUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingAnalista) {
        // Al editar, mantener el estado actual
        await updateAnalistaMutation.mutateAsync({
          id: editingAnalista.id,
          data: formData
        })
        toast.success('✅ Analista actualizado exitosamente')
      } else {
        // Al crear, usar activo: true por defecto
        await createAnalistaMutation.mutateAsync({
          ...formData,
          activo: true
        })
        toast.success('✅ Analista creado exitosamente')
      }
      resetForm()
      refetch()
    } catch (err) {
      console.error('Error:', err)
      toast.error('❌ Error al guardar analista')
    }
  }

  const resetForm = () => {
    setFormData({
      nombre: ''
    })
    setEditingAnalista(null)
    setShowCreateForm(false)
  }

  const handleRefresh = () => {
    refetch()
  }

  // Filtrar analistas por término de búsqueda
  const filteredAnalistas = analistas.filter(analista =>
    analista.nombre.toLowerCase().includes(searchTerm.toLowerCase())
  )

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
          <h1 className="text-3xl font-bold tracking-tight">Analistas</h1>
          <p className="text-muted-foreground">
            Gestiona los analistas del sistema
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={handleRefresh} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
          <Button onClick={() => setShowCreateForm(true)}>
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
            <div className="text-2xl font-bold">{analistas.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Activos</CardTitle>
            <UserCheck className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {analistas.filter(a => a.activo).length}
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
              {analistas.filter(a => !a.activo).length}
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
        <CardContent className="p-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Buscar por nombre..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

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
                    {analista.created_at 
                      ? (() => {
                          const date = new Date(analista.created_at)
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
                        onClick={() => handleEdit(analista)}
                        title="Editar analista"
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEliminar(analista.id)}
                        className="text-red-600 hover:text-red-700"
                        title="Eliminar analista"
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

      {/* Create/Edit Form Modal */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle>
              {editingAnalista ? 'Editar Analista' : 'Nuevo Analista'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateOrUpdate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Nombre del Analista *
                </label>
                <Input
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Ingrese el nombre del analista"
                  required
                  autoFocus
                />
                {!editingAnalista && (
                  <p className="text-xs text-gray-500 mt-1">
                    El analista se creará como "Activo" por defecto
                  </p>
                )}
              </div>

              <div className="flex items-center space-x-2 pt-4">
                <Button 
                  type="submit" 
                  disabled={createAnalistaMutation.isPending || updateAnalistaMutation.isPending}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {createAnalistaMutation.isPending || updateAnalistaMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <Edit className="h-4 w-4 mr-2" />
                      {editingAnalista ? 'Actualizar' : 'Crear'} Analista
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
    </div>
  )
}