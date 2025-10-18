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
      
      await concesionarioService.eliminarConcesionario(id)
      toast.success('✅ Concesionario eliminado PERMANENTEMENTE de la base de datos')
      cargarConcesionarios() // Recargar lista
    } catch (err) {
      toast.error('❌ Error al eliminar concesionario permanentemente')
      console.error('Error:', err)
    }
  }

  const handleToggleActivo = async (concesionario: Concesionario) => {
    try {
      await concesionarioService.actualizarConcesionario(concesionario.id, {
        activo: !concesionario.activo
      })
      toast.success(`Concesionario ${concesionario.activo ? 'desactivado' : 'activado'} exitosamente`)
      cargarConcesionarios() // Recargar lista
    } catch (err) {
      toast.error('Error al cambiar estado del concesionario')
      console.error('Error:', err)
    }
  }

  // Filtrar concesionarios por término de búsqueda
  const concesionariosFiltrados = concesionarios.filter(concesionario =>
    (concesionario.nombre && concesionario.nombre.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (concesionario.direccion && concesionario.direccion.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (concesionario.email && concesionario.email.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (concesionario.responsable && concesionario.responsable.toLowerCase().includes(searchTerm.toLowerCase()))
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
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            onClick={cargarConcesionarios}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
          <Button onClick={() => setShowCreateForm(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Nuevo Concesionario
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Concesionarios</p>
                <p className="text-2xl font-bold">{concesionarios.length}</p>
                <p className="text-xs text-gray-400 mt-1">
                  {loading ? 'Cargando...' : 'Conectando con BD...'}
                </p>
              </div>
              <Building className="w-8 h-8 text-primary" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Activos</p>
                <p className="text-2xl font-bold text-green-600">
                  {concesionarios.filter(c => c.activo).length}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {loading ? 'Cargando...' : 'Pueden operar'}
                </p>
              </div>
              <Building className="w-8 h-8 text-green-600" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Inactivos</p>
                <p className="text-2xl font-bold text-red-600">
                  {concesionarios.filter(c => !c.activo).length}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {loading ? 'Cargando...' : 'No pueden operar'}
                </p>
              </div>
              <UserX className="w-8 h-8 text-red-600" />
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
              placeholder="Buscar concesionario por nombre o ubicación..."
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
                <TableHead>Concesionario</TableHead>
                <TableHead>Ubicación</TableHead>
                <TableHead>Contacto</TableHead>
                <TableHead>Responsable</TableHead>
                <TableHead>Clientes</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
                    <p className="text-gray-500">Cargando concesionarios...</p>
                  </TableCell>
                </TableRow>
              ) : error ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <p className="text-red-500">{error}</p>
                    <Button onClick={cargarConcesionarios} className="mt-2">
                      Reintentar
                    </Button>
                  </TableCell>
                </TableRow>
              ) : concesionariosFiltrados.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8">
                    <p className="text-gray-500">No se encontraron concesionarios</p>
                  </TableCell>
                </TableRow>
              ) : (
                concesionariosFiltrados.map((concesionario) => (
                <TableRow key={concesionario.id}>
                  <TableCell>
                    <div className="flex items-center space-x-3">
                      <Building className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="font-medium">{concesionario.nombre}</p>
                        <p className="text-xs text-gray-500">ID: {concesionario.id}</p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    {concesionario.direccion ? (
                      <div className="flex items-center text-sm">
                        <MapPin className="w-3 h-3 mr-1 text-gray-400" />
                        {concesionario.direccion}
                      </div>
                    ) : (
                      <span className="text-gray-400">Sin dirección</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      {concesionario.email && (
                        <div className="flex items-center text-sm">
                          <Mail className="w-3 h-3 mr-1 text-gray-400" />
                          {concesionario.email}
                        </div>
                      )}
                      {concesionario.telefono && (
                        <div className="flex items-center text-sm">
                          <Phone className="w-3 h-3 mr-1 text-gray-400" />
                          {concesionario.telefono}
                        </div>
                      )}
                      {!concesionario.email && !concesionario.telefono && (
                        <div className="text-sm text-gray-400">
                          Sin contacto
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {concesionario.responsable ? (
                      <div className="flex items-center text-sm">
                        <User className="w-3 h-3 mr-1 text-gray-400" />
                        {concesionario.responsable}
                      </div>
                    ) : (
                      <span className="text-gray-400">Sin responsable</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <span className="text-gray-400">-</span>
                  </TableCell>
                  <TableCell>
                    {concesionario.activo ? (
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
                        onClick={() => setEditingConcesionario(concesionario)}
                        title="Editar concesionario"
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleToggleActivo(concesionario)}
                        title={concesionario.activo ? "Desactivar" : "Activar"}
                      >
                        {concesionario.activo ? (
                          <UserX className="w-4 h-4 text-red-600" />
                        ) : (
                          <UserCheck className="w-4 h-4 text-green-600" />
                        )}
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleEliminar(concesionario.id)}
                        title="Eliminar concesionario"
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

      {/* Formulario de Crear/Editar Concesionario */}
      {(showCreateForm || editingConcesionario) && (
        <CrearEditarConcesionarioForm
          concesionario={editingConcesionario}
          onClose={() => {
            setShowCreateForm(false)
            setEditingConcesionario(null)
          }}
          onSuccess={() => {
            cargarConcesionarios()
            setShowCreateForm(false)
            setEditingConcesionario(null)
          }}
        />
      )}
    </div>
  )
}

// Componente para crear/editar concesionario
interface CrearEditarConcesionarioFormProps {
  concesionario?: Concesionario | null
  onClose: () => void
  onSuccess: () => void
}

function CrearEditarConcesionarioForm({ concesionario, onClose, onSuccess }: CrearEditarConcesionarioFormProps) {
  const [formData, setFormData] = useState({
    nombre: concesionario?.nombre || '',
    direccion: concesionario?.direccion || '',
    telefono: concesionario?.telefono || '',
    email: concesionario?.email || '',
    responsable: concesionario?.responsable || ''
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
        direccion: formData.direccion.trim() || undefined,
        telefono: formData.telefono.trim() || undefined,
        email: formData.email.trim() || undefined,
        responsable: formData.responsable.trim() || undefined
      }

      if (concesionario) {
        await concesionarioService.actualizarConcesionario(concesionario.id, data)
        toast.success('Concesionario actualizado exitosamente')
      } else {
        await concesionarioService.crearConcesionario(data)
        toast.success('Concesionario creado exitosamente')
      }
      
      onSuccess()
    } catch (err) {
      toast.error(concesionario ? 'Error al actualizar concesionario' : 'Error al crear concesionario')
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
            {concesionario ? 'Editar Concesionario' : 'Nuevo Concesionario'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Nombre *</label>
              <Input
                value={formData.nombre}
                onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
                placeholder="Nombre del concesionario"
                required
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Dirección</label>
              <Input
                value={formData.direccion}
                onChange={(e) => setFormData({ ...formData, direccion: e.target.value })}
                placeholder="Dirección del concesionario"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Teléfono</label>
              <Input
                value={formData.telefono}
                onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
                placeholder="+58 212-123-4567"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Email</label>
              <Input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="email@concesionario.com"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-1">Responsable</label>
              <Input
                value={formData.responsable}
                onChange={(e) => setFormData({ ...formData, responsable: e.target.value })}
                placeholder="Nombre del responsable"
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
                    {concesionario ? 'Actualizando...' : 'Creando...'}
                  </>
                ) : (
                  concesionario ? 'Actualizar' : 'Crear'
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

