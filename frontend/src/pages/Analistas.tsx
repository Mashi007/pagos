import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  Users,
  Plus,
  Search,
  Edit,
  Trash2,
  UserCheck,
  UserX,
  Mail,
  Phone,
  Award,
  Loader2
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { analistaService, Analista } from '@/services/analistaService'
import { toast } from 'sonner'

export function Analistas() {
  const [analistas, setAnalistas] = useState<Analista[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingAnalista, setEditingAnalista] = useState<Analista | null>(null)

  // Cargar analistas al montar el componente
  useEffect(() => {
    cargarAnalistas()
  }, [])

  const cargarAnalistas = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await analistaService.listarAnalistas({ limit: 100 })
      setAnalistas(response.items)
    } catch (err) {
      setError('Error al cargar analistas')
      toast.error('Error al cargar analistas')
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

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
      
      await analistaService.eliminarAnalista(id)
      toast.success('✅ Analista eliminado PERMANENTEMENTE de la base de datos')
      cargarAnalistas() // Recargar lista
    } catch (err) {
      toast.error('❌ Error al eliminar analista permanentemente')
      console.error('Error:', err)
    }
  }

  const handleToggleActivo = async (analista: Analista) => {
    try {
      await analistaService.actualizarAnalista(analista.id, {
        activo: !analista.activo
      })
      toast.success(`Analista ${analista.activo ? 'desactivado' : 'activado'} exitosamente`)
      cargarAnalistas() // Recargar lista
    } catch (err) {
      toast.error('Error al cambiar estado del analista')
      console.error('Error:', err)
    }
  }

  // Filtrar analistas por término de búsqueda
  const analistasFiltrados = analistas.filter(analista =>
    analista.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (analista.apellido && analista.apellido.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (analista.email && analista.email.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Analistas</h1>
          <p className="text-gray-500 mt-1">
            Gestión de analistas y equipo de ventas
          </p>
        </div>
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Nuevo Analista
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Analistas</p>
                <p className="text-2xl font-bold">{analistas.length}</p>
              </div>
              <Users className="w-8 h-8 text-primary" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Activos</p>
                <p className="text-2xl font-bold text-green-600">
                  {analistas.filter(a => a.activo).length}
                </p>
              </div>
              <UserCheck className="w-8 h-8 text-green-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Inactivos</p>
                <p className="text-2xl font-bold text-red-600">
                  {analistas.filter(a => !a.activo).length}
                </p>
              </div>
              <UserX className="w-8 h-8 text-red-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Con Email</p>
                <p className="text-2xl font-bold text-purple-600">
                  {analistas.filter(a => a.email && a.email.trim() !== '').length}
                </p>
              </div>
              <Mail className="w-8 h-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Búsqueda */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Buscar analista por nombre, email o especialidad..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Tabla */}
      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Analista</TableHead>
                <TableHead>Contacto</TableHead>
                <TableHead>Especialidad</TableHead>
                <TableHead>Comisión</TableHead>
                <TableHead>Clientes</TableHead>
                <TableHead>Ventas Mes</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    <p className="text-gray-500">Cargando analistas...</p>
                  </TableCell>
                </TableRow>
              ) : error ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    <p className="text-red-500">{error}</p>
                    <Button onClick={cargarAnalistas} className="mt-2">
                      Reintentar
                    </Button>
                  </TableCell>
                </TableRow>
              ) : analistasFiltrados.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8">
                    <p className="text-gray-500">No se encontraron analistas</p>
                  </TableCell>
                </TableRow>
              ) : (
                analistasFiltrados.map((analista) => (
                <TableRow key={analista.id}>
                  <TableCell>
                    <div>
                      <p className="font-medium">{analista.nombre_completo}</p>
                      <p className="text-xs text-gray-500">ID: {analista.id}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      {analista.email && (
                        <div className="flex items-center text-sm">
                          <Mail className="w-3 h-3 mr-1 text-gray-400" />
                          {analista.email}
                        </div>
                      )}
                      {analista.telefono && (
                        <div className="flex items-center text-sm">
                          <Phone className="w-3 h-3 mr-1 text-gray-400" />
                          {analista.telefono}
                        </div>
                      )}
                      {!analista.email && !analista.telefono && (
                        <div className="text-sm text-gray-400">
                          Sin contacto
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {analista.especialidad ? (
                      <Badge variant="outline">{analista.especialidad}</Badge>
                    ) : (
                      <span className="text-gray-400">Sin especialidad</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {analista.comision_porcentaje ? (
                      `${analista.comision_porcentaje}%`
                    ) : (
                      <span className="text-gray-400">Sin comisión</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <span className="text-gray-400">-</span>
                  </TableCell>
                  <TableCell>
                    <span className="text-gray-400">-</span>
                  </TableCell>
                  <TableCell>
                    {analista.activo ? (
                      <Badge className="bg-green-600">Activo</Badge>
                    ) : (
                      <Badge variant="outline">Inactivo</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => setEditingAnalista(analista)}
                        title="Editar analista"
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleToggleActivo(analista)}
                        title={analista.activo ? "Desactivar" : "Activar"}
                      >
                        {analista.activo ? (
                          <UserX className="w-4 h-4 text-red-600" />
                        ) : (
                          <UserCheck className="w-4 h-4 text-green-600" />
                        )}
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleEliminar(analista.id)}
                        title="Eliminar analista"
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Formulario de Crear/Editar Analista */}
      {(showCreateForm || editingAnalista) && (
        <CrearEditarAnalistaForm
          analista={editingAnalista}
          onClose={() => {
            setShowCreateForm(false)
            setEditingAnalista(null)
          }}
          onSuccess={() => {
            cargarAnalistas()
            setShowCreateForm(false)
            setEditingAnalista(null)
          }}
        />
      )}
    </div>
  )
}

// Componente para crear/editar analista
interface CrearEditarAnalistaFormProps {
  analista?: Analista | null
  onClose: () => void
  onSuccess: () => void
}

function CrearEditarAnalistaForm({ analista, onClose, onSuccess }: CrearEditarAnalistaFormProps) {
  const [formData, setFormData] = useState({
    nombre: analista?.nombre || '',
    apellido: analista?.apellido || '',
    email: analista?.email || '',
    telefono: analista?.telefono || '',
    especialidad: analista?.especialidad || '',
    comision_porcentaje: analista?.comision_porcentaje?.toString() || '',
    notas: analista?.notas || ''
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!formData.nombre.trim()) {
      toast.error('El nombre es obligatorio')
      return
    }

    try {
      setLoading(true)
      
      const data = {
        nombre: formData.nombre.trim(),
        apellido: formData.apellido.trim() || undefined,
        email: formData.email.trim() || undefined,
        telefono: formData.telefono.trim() || undefined,
        especialidad: formData.especialidad.trim() || undefined,
        comision_porcentaje: formData.comision_porcentaje ? parseInt(formData.comision_porcentaje) : undefined,
        notas: formData.notas.trim() || undefined
      }

      if (analista) {
        await analistaService.actualizarAnalista(analista.id, data)
        toast.success('Analista actualizado exitosamente')
      } else {
        await analistaService.crearAnalista(data)
        toast.success('Analista creado exitosamente')
      }
      
      onSuccess()
    } catch (err) {
      toast.error(analista ? 'Error al actualizar analista' : 'Error al crear analista')
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <Card className="w-full max-w-md mx-4">
        <CardHeader>
          <CardTitle>
            {analista ? 'Editar Analista' : 'Nuevo Analista'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Nombre *</label>
              <Input
                value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                placeholder="Nombre del analista"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Apellido</label>
              <Input
                value={formData.apellido}
                onChange={(e) => setFormData({ ...formData, apellido: e.target.value })}
                placeholder="Apellido del analista"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="email@ejemplo.com"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Teléfono</label>
              <Input
                value={formData.telefono}
                onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                placeholder="+58 414-123-4567"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Especialidad</label>
              <Input
                value={formData.especialidad}
                onChange={(e) => setFormData({ ...formData, especialidad: e.target.value })}
                placeholder="Ej: Vehículos Nuevos, Usados"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Comisión (%)</label>
              <Input
                type="number"
                min="0"
                max="100"
                value={formData.comision_porcentaje}
                onChange={(e) => setFormData({ ...formData, comision_porcentaje: e.target.value })}
                placeholder="2.5"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Notas</label>
              <textarea
                className="w-full p-2 border rounded-md"
                rows={3}
                value={formData.notas}
                onChange={(e) => setFormData({ ...formData, notas: e.target.value })}
                placeholder="Notas adicionales..."
              />
            </div>
            
            <div className="flex justify-end space-x-2 pt-4">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    {analista ? 'Actualizando...' : 'Creando...'}
                  </>
                ) : (
                  analista ? 'Actualizar' : 'Crear'
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

