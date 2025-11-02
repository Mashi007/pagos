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
  RefreshCw
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

  // Form state
  const [formData, setFormData] = useState<AnalistaCreate>({
    nombre: '',
    activo: true
  })
  const [archivoExcel, setArchivoExcel] = useState<File | null>(null)

  // Función para obtener fecha de hoy
  const getTodayDate = () => {
    const today = new Date()
    return today.toISOString().split('T')[0]
  }

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
        toast.success('✅ Analista actualizado exitosamente')
      } else {
        await createAnalistaMutation.mutateAsync(formData)
        toast.success('✅ Analista creado exitosamente')
      }
      
      resetForm()
      // Refrescar la lista automáticamente
      refetch()
    } catch (err) {
      console.error('Error al guardar analista:', err)
      toast.error('❌ Error al guardar analista')
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
      toast.success('✅ Analista eliminado exitosamente')
      // Refrescar la lista automáticamente
      refetch()
    } catch (err) {
      console.error('Error al eliminar analista:', err)
      toast.error('❌ Error al eliminar analista')
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
  const filteredAnalistas = analistas?.filter((analista: Analista) =>
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
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Analistas</CardTitle>
            <Users className="h-4 w-4 text-blue-600" />
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
              {analistas?.filter((a: Analista) => a.activo).length || 0}
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
              {analistas?.filter((a: Analista) => !a.activo).length || 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card>
        <CardContent>
          <Input
            placeholder="Buscar analista..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
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
                  Nombre Completo *
                </label>
                <Input
                  value={formData.nombre}
                  onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                  placeholder="Ingrese el nombre completo del analista"
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

      {/* Analistas Table */}
      <Card>
        <CardHeader>
          <CardTitle>Lista de Analistas ({analistas?.length || 0})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Analista</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Fecha Creación</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAnalistas.map((analista: Analista) => (
                <TableRow key={analista.id}>
                  <TableCell className="font-medium">{analista.id}</TableCell>
                  <TableCell>
                    <div className="font-semibold">{analista.nombre}</div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="default" className="bg-blue-600 text-white">
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
                        onClick={() => handleDelete(analista.id)}
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

      {/* Importación desde Excel */}
      <Card>
        <CardHeader>
          <CardTitle>Importar Analistas (Excel)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="text-sm text-gray-600">
            Columnas requeridas: <b>nombre</b>. Opcional: <b>activo</b> (por defecto: True).
          </div>
          <input 
            type="file" 
            accept=".xlsx,.xls" 
            onChange={(e) => setArchivoExcel(e.target.files?.[0] || null)} 
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          <div className="flex items-center gap-2">
            <Button
              disabled={!archivoExcel}
              onClick={async () => {
                if (!archivoExcel) return
                try {
                  const svc = (await import('@/services/analistaService')).analistaService
                  const res = await svc.importarDesdeExcel(archivoExcel)
                  const msg = `Importado: ${res.creados} creados, ${res.actualizados} actualizados`
                  if (res.errores && res.errores.length > 0) {
                    toast.success(msg)
                    toast.error(`Errores en ${res.errores.length} fila(s): ${res.errores.slice(0, 3).join(', ')}`)
                  } else {
                    toast.success(msg)
                  }
                  setArchivoExcel(null)
                  await refetch()
                } catch (err: any) {
                  toast.error(err?.response?.data?.detail || 'Error al importar')
                }
              }}
            >
              Cargar Excel
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}