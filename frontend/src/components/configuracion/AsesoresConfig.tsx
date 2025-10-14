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
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { asesorService, type Asesor, type AsesorCreate } from '@/services/asesorService'

const ESPECIALIDADES = [
  'Vehículos Nuevos',
  'Vehículos Usados',
  'Vehículos Comerciales',
  'Motocicletas',
  'Camiones',
  'Otros'
]

export function AsesoresConfig() {
  const [asesores, setAsesores] = useState<Asesor[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingAsesor, setEditingAsesor] = useState<Asesor | null>(null)

  // Form state
  const [formData, setFormData] = useState<AsesorCreate>({
    nombre: '',
    apellido: '',
    email: '',
    telefono: '',
    especialidad: '',
    comision_porcentaje: 0,
    activo: true,
    notas: ''
  })

  useEffect(() => {
    loadAsesores()
  }, [])

  const loadAsesores = async () => {
    try {
      setLoading(true)
      const data = await asesorService.listarAsesoresActivos()
      setAsesores(data)
    } catch (err) {
      console.error('Error al cargar asesores:', err)
      setError('No se pudieron cargar los asesores.')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingAsesor) {
        await asesorService.actualizarAsesor(editingAsesor.id, formData)
      } else {
        await asesorService.crearAsesor(formData)
      }
      
      await loadAsesores()
      resetForm()
    } catch (err) {
      console.error('Error al guardar asesor:', err)
      setError('Error al guardar el asesor.')
    }
  }

  const handleEdit = (asesor: Asesor) => {
    setEditingAsesor(asesor)
    setFormData({
      nombre: asesor.nombre,
      apellido: asesor.apellido,
      email: asesor.email,
      telefono: asesor.telefono || '',
      especialidad: asesor.especialidad || '',
      comision_porcentaje: asesor.comision_porcentaje || 0,
      activo: asesor.activo,
      notas: asesor.notas || ''
    })
    setShowForm(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Estás seguro de que deseas eliminar este asesor?')) {
      return
    }
    
    try {
      await asesorService.eliminarAsesor(id)
      await loadAsesores()
    } catch (err) {
      console.error('Error al eliminar asesor:', err)
      setError('Error al eliminar el asesor.')
    }
  }

  const resetForm = () => {
    setFormData({
      nombre: '',
      apellido: '',
      email: '',
      telefono: '',
      especialidad: '',
      comision_porcentaje: 0,
      activo: true,
      notas: ''
    })
    setEditingAsesor(null)
    setShowForm(false)
  }

  const filteredAsesores = asesores.filter(asesor =>
    asesor.nombre_completo.toLowerCase().includes(searchTerm.toLowerCase()) ||
    asesor.especialidad?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    asesor.email.toLowerCase().includes(searchTerm.toLowerCase())
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
            Gestión de Asesores
          </h3>
          <p className="text-gray-600 mt-1">
            Administra los asesores comerciales del sistema
          </p>
        </div>
        <Button onClick={() => setShowForm(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Nuevo Asesor
        </Button>
      </div>

      {/* Formulario */}
      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>
              {editingAsesor ? 'Editar Asesor' : 'Nuevo Asesor'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium">Nombre *</label>
                  <Input
                    value={formData.nombre}
                    onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                    placeholder="Nombre"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Apellido *</label>
                  <Input
                    value={formData.apellido}
                    onChange={(e) => setFormData({ ...formData, apellido: e.target.value })}
                    placeholder="Apellido"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Email *</label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="asesor@ejemplo.com"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Teléfono</label>
                  <Input
                    value={formData.telefono}
                    onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                    placeholder="+58-424-1234567"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Especialidad</label>
                  <select
                    value={formData.especialidad}
                    onChange={(e) => setFormData({ ...formData, especialidad: e.target.value })}
                    className="w-full p-2 border border-gray-300 rounded-md"
                  >
                    <option value="">Seleccionar especialidad</option>
                    {ESPECIALIDADES.map((esp) => (
                      <option key={esp} value={esp}>{esp}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium">Comisión (%)</label>
                  <Input
                    type="number"
                    min="0"
                    max="100"
                    value={formData.comision_porcentaje}
                    onChange={(e) => setFormData({ ...formData, comision_porcentaje: parseInt(e.target.value) || 0 })}
                    placeholder="5"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="text-sm font-medium">Notas</label>
                  <textarea
                    value={formData.notas}
                    onChange={(e) => setFormData({ ...formData, notas: e.target.value })}
                    placeholder="Notas adicionales sobre el asesor"
                    className="w-full p-2 border border-gray-300 rounded-md h-20 resize-none"
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
                  {editingAsesor ? 'Actualizar' : 'Crear'}
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
              placeholder="Buscar asesores..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1"
            />
          </div>
        </CardContent>
      </Card>

      {/* Lista de Asesores */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre Completo</TableHead>
                  <TableHead>Especialidad</TableHead>
                  <TableHead>Contacto</TableHead>
                  <TableHead>Comisión</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAsesores.map((asesor) => (
                  <TableRow key={asesor.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{asesor.nombre_completo}</div>
                        {asesor.notas && (
                          <div className="text-sm text-gray-500">{asesor.notas}</div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {asesor.especialidad ? (
                        <Badge variant="outline">{asesor.especialidad}</Badge>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <div className="flex items-center text-sm">
                          <Mail className="mr-1 h-3 w-3" />
                          {asesor.email}
                        </div>
                        {asesor.telefono && (
                          <div className="flex items-center text-sm text-gray-500">
                            <Phone className="mr-1 h-3 w-3" />
                            {asesor.telefono}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {asesor.comision_porcentaje ? (
                        <span className="font-medium">{asesor.comision_porcentaje}%</span>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={asesor.activo ? 'default' : 'destructive'}>
                        {asesor.activo ? (
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
                          onClick={() => handleEdit(asesor)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(asesor.id)}
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
