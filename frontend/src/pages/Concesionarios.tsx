// frontend/src/pages/Concesionarios.tsx
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Building,
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
import { Concesionario, ConcesionarioUpdate, ConcesionarioCreate } from '@/services/concesionarioService'
import { useConcesionarios, useDeleteConcesionario, useUpdateConcesionario, useCreateConcesionario } from '@/hooks/useConcesionarios'
import toast from 'react-hot-toast'

export function Concesionarios() {
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingConcesionario, setEditingConcesionario] = useState<Concesionario | null>(null)
  const [formData, setFormData] = useState<ConcesionarioCreate>({
    nombre: '',
    activo: true
  })
  const [validationError, setValidationError] = useState<string>('')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  // Usar hooks de React Query
  const { 
    data: concesionariosData, 
    isLoading: loading, 
    error,
    refetch
  } = useConcesionarios({ limit: 1000 })
  
  const deleteConcesionarioMutation = useDeleteConcesionario()
  const updateConcesionarioMutation = useUpdateConcesionario()
  const createConcesionarioMutation = useCreateConcesionario()
  
  const concesionarios = concesionariosData?.items || []

  const handleEliminar = async (id: number) => {
    try {
      // Confirmar eliminación permanente
      const confirmar = window.confirm(
        '⚠️ ¿Estás seguro de que quieres ELIMINAR PERMANENTEMENTE este concesionario?\n\n' +
        'Esta acción NO se puede deshacer y el concesionario será borrado completamente de la base de datos.'
      )
      
      if (!confirmar) {
        return
      }
      
      await deleteConcesionarioMutation.mutateAsync(id)
    } catch (err) {
      console.error('Error:', err)
    }
  }

  const validateNombre = (nombre: string): string => {
    if (!nombre.trim()) {
      return 'El nombre es requerido'
    }
    
    // Limpiar espacios extras
    const nombreLimpio = nombre.trim().replace(/\s+/g, ' ')
    
    // Verificar cantidad de palabras (mínimo 2, máximo 4)
    const palabras = nombreLimpio.split(' ')
    
    if (palabras.length < 2) {
      return 'Debe ingresar al menos 2 palabras (Nombre y Apellido)'
    }
    
    if (palabras.length > 4) {
      return 'Debe ingresar máximo 4 palabras'
    }
    
    // Verificar que cada palabra tenga al menos 2 caracteres
    for (const palabra of palabras) {
      if (palabra.length < 2) {
        return 'Cada palabra debe tener al menos 2 caracteres'
      }
    }
    
    return ''
  }

  const formatNombre = (nombre: string): string => {
    // Limpiar espacios extras
    const nombreLimpio = nombre.trim().replace(/\s+/g, ' ')
    
    // Capitalizar primera letra de cada palabra
    return nombreLimpio.split(' ').map(word => {
      if (word.length === 0) return word
      return word[0].toUpperCase() + word.slice(1).toLowerCase()
    }).join(' ')
  }

  const handleEdit = (concesionario: Concesionario) => {
    setEditingConcesionario(concesionario)
    setFormData({
      nombre: concesionario.nombre,
      activo: concesionario.activo
    })
    setValidationError('')
    setShowCreateForm(true)
  }

  const handleCreateOrUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validar nombre
    const error = validateNombre(formData.nombre)
    if (error) {
      setValidationError(error)
      return
    }
    
    setValidationError('')
    
    try {
      // Formatear nombre (capitalizar primera letra de cada palabra)
      const nombreFormateado = formatNombre(formData.nombre)
      
      if (editingConcesionario) {
        // Al editar, mantener el estado actual
        await updateConcesionarioMutation.mutateAsync({
          id: editingConcesionario.id,
          data: { ...formData, nombre: nombreFormateado }
        })
        toast.success('✅ Concesionario actualizado exitosamente')
      } else {
        // Al crear, ya tiene activo: true por defecto
        await createConcesionarioMutation.mutateAsync({ ...formData, nombre: nombreFormateado })
        toast.success('✅ Concesionario creado exitosamente')
      }
      resetForm()
      refetch()
    } catch (err) {
      console.error('Error:', err)
      toast.error('❌ Error al guardar concesionario')
    }
  }

  const resetForm = () => {
    setFormData({
      nombre: '',
      activo: true
    })
    setValidationError('')
    setEditingConcesionario(null)
    setShowCreateForm(false)
  }

  const handleRefresh = () => {
    refetch()
  }

  // Filtrar concesionarios por término de búsqueda
  const filteredConcesionarios = (concesionarios || []).filter(concesionario =>
    concesionario.nombre.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Paginación
  const totalPages = Math.ceil(filteredConcesionarios.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage
  const paginatedConcesionarios = filteredConcesionarios.slice(startIndex, endIndex)

  // Resetear a página 1 cuando cambia el filtro de búsqueda
  useEffect(() => {
    setCurrentPage(1)
  }, [searchTerm])

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

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-red-500 mb-4">Error al cargar concesionarios</p>
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
          <h1 className="text-3xl font-bold tracking-tight">Concesionarios</h1>
          <p className="text-muted-foreground">
            Gestiona los concesionarios del sistema
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={() => {
            setEditingConcesionario(null)
            setFormData({ nombre: '', activo: true })
            setValidationError('')
            setShowCreateForm(true)
          }}>
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
            <div className="text-2xl font-bold">{concesionarios?.length || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Activos</CardTitle>
            <UserCheck className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {(concesionarios || []).filter(c => c.activo === true || c.activo === 1).length}
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
              {(concesionarios || []).filter(c => c.activo === false || c.activo === 2 || c.activo === 0).length}
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
              {paginatedConcesionarios.map((concesionario) => (
                <TableRow key={concesionario.id}>
                  <TableCell className="font-medium">{concesionario.id}</TableCell>
                  <TableCell>{concesionario.nombre}</TableCell>
                  <TableCell>
                    <Badge variant={(concesionario.activo === true || concesionario.activo === 1) ? "default" : "secondary"}>
                      {(concesionario.activo === true || concesionario.activo === 1) ? "Activo" : "Inactivo"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {concesionario.created_at 
                      ? (() => {
                          const date = new Date(concesionario.created_at)
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
                        onClick={() => handleEdit(concesionario)}
                        title="Editar concesionario"
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEliminar(concesionario.id)}
                        className="text-red-600 hover:text-red-700"
                        title="Eliminar concesionario"
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
              {searchTerm ? 'No se encontraron concesionarios con ese nombre' : 'No hay concesionarios disponibles'}
            </div>
          )}

          {/* Paginación */}
          {filteredConcesionarios.length > itemsPerPage && (
            <div className="flex items-center justify-between px-2 py-4 border-t">
              <div className="text-sm text-gray-500">
                Mostrando {startIndex + 1} a {Math.min(endIndex, filteredConcesionarios.length)} de {filteredConcesionarios.length} concesionarios
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                >
                  Anterior
                </Button>
                <div className="flex items-center space-x-1">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                    <Button
                      key={page}
                      variant={currentPage === page ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCurrentPage(page)}
                      className={currentPage === page ? 'bg-blue-600 text-white' : ''}
                    >
                      {page}
                    </Button>
                  ))}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                >
                  Siguiente
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Form Modal */}
      {showCreateForm && (
        <div 
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
          onClick={resetForm}
        >
          <div 
            className="bg-white rounded-lg shadow-xl max-w-md w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <Card>
              <CardHeader>
                <CardTitle>
                  {editingConcesionario ? 'Editar Concesionario' : 'Nuevo Concesionario'}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateOrUpdate} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Nombre del Concesionario *
                    </label>
                    <Input
                      value={formData.nombre}
                      onChange={(e) => {
                        setFormData({ ...formData, nombre: e.target.value })
                        setValidationError('') // Limpiar error al escribir
                      }}
                      placeholder="Ingrese nombre completo (2-4 palabras)"
                      required
                      autoFocus
                      className={validationError ? 'border-red-500' : ''}
                    />
                    {validationError && (
                      <p className="text-xs text-red-500 mt-1">
                        {validationError}
                      </p>
                    )}
                    {!editingConcesionario && !validationError && (
                      <p className="text-xs text-gray-500 mt-1">
                        Ejemplo: Juan Pérez (mínimo 2, máximo 4 palabras)
                      </p>
                    )}
                  </div>

                  {editingConcesionario && (
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
                  )}

                  <div className="flex items-center space-x-2 pt-4">
                    <Button 
                      type="submit" 
                      disabled={createConcesionarioMutation.isPending || updateConcesionarioMutation.isPending}
                      className="bg-blue-600 hover:bg-blue-700"
                    >
                      {createConcesionarioMutation.isPending || updateConcesionarioMutation.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          Guardando...
                        </>
                      ) : (
                        <>
                          <Edit className="h-4 w-4 mr-2" />
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
          </div>
        </div>
      )}
    </div>
  )
}
