import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Building,
  Plus,
  Edit,
  Trash2,
  Search,
  Filter,
  CheckCircle,
  XCircle,
  Save,
  X,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { concesionarioService, type Concesionario, type ConcesionarioCreate } from '@/services/concesionarioService'

export function ConcesionariosConfig() {
  const [concesionarios, setConcesionarios] = useState<Concesionario[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingConcesionario, setEditingConcesionario] = useState<Concesionario | null>(null)

  // Form state
  const [formData, setFormData] = useState<ConcesionarioCreate>({
    nombre: '',
    responsable: '',
    activo: true
  })

  useEffect(() => {
    loadConcesionarios()
  }, [])

  const loadConcesionarios = async () => {
    try {
      setLoading(true)
      const data = await concesionarioService.listarConcesionariosActivos()
      setConcesionarios(data)
    } catch (err) {
      console.error('Error al cargar concesionarios:', err)
      setError('No se pudieron cargar los concesionarios.')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingConcesionario) {
        await concesionarioService.actualizarConcesionario(editingConcesionario.id, formData)
      } else {
        await concesionarioService.crearConcesionario(formData)
      }
      
      await loadConcesionarios()
      resetForm()
    } catch (err) {
      console.error('Error al guardar concesionario:', err)
      setError('Error al guardar el concesionario.')
    }
  }

  const handleEdit = (concesionario: Concesionario) => {
    setEditingConcesionario(concesionario)
    setFormData({
      nombre: concesionario.nombre,
      responsable: concesionario.responsable || '',
      activo: concesionario.activo
    })
    setShowForm(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de que deseas eliminar este concesionario?')) {
      return
    }
    
    try {
      await concesionarioService.eliminarConcesionario(id)
      await loadConcesionarios()
    } catch (err) {
      console.error('Error al eliminar concesionario:', err)
      setError('Error al eliminar el concesionario.')
    }
  }

  const resetForm = () => {
    setFormData({
      nombre: '',
      responsable: '',
      activo: true
    })
    setEditingConcesionario(null)
    setShowForm(false)
  }

  const filteredConcesionarios = concesionarios.filter(concesionario =>
    concesionario.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
    concesionario.responsable?.toLowerCase().includes(searchTerm.toLowerCase())
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
            <Building className="mr-2 h-6 w-6" />
            Gestión de Concesionarios
          </h3>
          <p className="text-gray-600 mt-1">
            Administra los concesionarios disponibles en el sistema
          </p>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Nuevo Concesionario
        </Button>
      </div>

      {/* Formulario */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>
              {editingConcesionario ? 'Editar Concesionario' : 'Nuevo Concesionario'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">Nombre del Concesionario *</label>
                  <Input
                    value={formData.nombre}
                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                    placeholder="Nombre del concesionario"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Responsable</label>
                  <Input
                    value={formData.responsable}
                    onChange={(e) => setFormData({ ...formData, responsable: e.target.value })}
                    placeholder="Nombre del responsable"
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
                  {editingConcesionario ? 'Actualizar' : 'Crear'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Búsqueda */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center space-x-2">
            <Search className="h-4 w-4 text-gray-400" />
            <Input
              placeholder="Buscar concesionarios..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1"
            />
          </div>
        </CardContent>
      </Card>

      {/* Lista de Concesionarios */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre del Concesionario</TableHead>
                  <TableHead>Responsable</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredConcesionarios.map((concesionario) => (
                  <TableRow key={concesionario.id}>
                    <TableCell>
                      <div className="font-medium">{concesionario.nombre}</div>
                    </TableCell>
                    <TableCell>
                      {concesionario.responsable || '-'}
                    </TableCell>
                    <TableCell>
                      <Badge variant={concesionario.activo ? 'default' : 'destructive'}>
                        {concesionario.activo ? (
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
                      <div className="flex items-center justify-end space-x-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(concesionario)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
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
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}
    </motion.div>
  )
}
